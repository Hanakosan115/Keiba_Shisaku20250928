"""
複勝ベッティング戦略のバックテスト

value betting戦略を複勝に適用
複勝オッズは単勝オッズから推定（実際のオッズデータがないため）
"""

import pandas as pd
import numpy as np
import pickle
from tqdm import tqdm

print("="*80)
print("複勝ベッティング戦略のバックテスト")
print("="*80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv',
                 encoding='utf-8', low_memory=False)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# モデル読み込み
print("モデル読み込み中...")
with open('lgbm_model_hybrid.pkl', 'rb') as f:
    model = pickle.load(f)

# 実オッズデータ読み込み
odds_df = pd.read_csv('odds_2024_sample_500.csv', encoding='utf-8')
odds_df['race_id'] = odds_df['race_id'].astype(str)

print(f"\n元データ: {len(df):,}件")
print(f"オッズデータ: {len(odds_df):,}件 ({odds_df['race_id'].nunique()}レース)")

# 2024年データでテスト
df_test = df[df['date_parsed'] >= '2024-01-01'].copy()
print(f"テストデータ: {len(df_test):,}件")

# オッズあるレースのみ
test_race_ids = df_test['race_id'].unique()
odds_race_ids = odds_df['race_id'].unique()
valid_race_ids = [rid for rid in test_race_ids if rid in odds_race_ids]

print(f"オッズあるテストレース: {len(valid_race_ids)}レース")

# 特徴量リスト
feature_cols = [
    'past_rank_avg', 'past_races', 'jockey_rank_avg', 'jockey_win_rate',
    'trainer_rank_avg', 'trainer_win_rate', 'age', 'weight', 'weight_diff',
    'odds', 'popularity', 'prize_total',
    'escape_rate', 'leading_rate', 'closing_rate', 'avg_agari', 'running_style_mode',
    'race_class_rank', 'is_promoted', 'is_demoted', 'class_rank_avg', 'class_experience',
    'first_3f_avg', 'last_3f_avg', 'pace_variance', 'pace_balance', 'accel_ability',
    'decel_resistance', 'lap_time_stability',
    'escape_count', 'leading_count', 'tracking_count', 'closing_count',
    'pace_match_score', 'style_advantage', 'competition_level', 'predicted_position',
    'momentum_score', 'is_rebound', 'distance_fit_score', 'distance_experience',
    'condition_fit_score', 'condition_experience', 'is_fresh', 'is_consecutive',
    'days_since_norm', 'last_rank',
    'avg_rank_1200', 'avg_rank_1400', 'avg_rank_1600', 'avg_rank_1800',
    'avg_rank_2000', 'avg_rank_2400', 'avg_rank_3000',
    'turf_avg_rank', 'dirt_avg_rank', 'good_avg_rank', 'soft_avg_rank'
]

# 複勝オッズ推定関数
def estimate_place_odds(win_odds, num_horses, place_positions=3):
    """
    単勝オッズから複勝オッズを推定

    複勝オッズは通常、単勝オッズの1/3～1/2程度
    出走頭数が少ない場合は比率が変わる
    """
    if num_horses <= 7:
        # 7頭以下の場合、複勝は2着まで（比率高め）
        place_odds = win_odds * 0.5
    else:
        # 8頭以上の場合、複勝は3着まで（比率低め）
        place_odds = win_odds * 0.35

    # 最低オッズ1.1倍
    return max(place_odds, 1.1)

# Value betting戦略でバックテスト
def backtest_place_value_strategy(value_thresholds):
    """
    Value betting戦略を複勝に適用
    """
    results = {}

    for threshold in value_thresholds:
        bet_count = 0
        win_count = 0
        total_investment = 0
        total_return = 0
        bet_details = []

        for race_id in tqdm(valid_race_ids, desc=f"閾値{threshold*100:.0f}%"):
            # レースデータ取得
            race_data = df_test[df_test['race_id'] == race_id].copy()
            if len(race_data) == 0:
                continue

            race_odds = odds_df[odds_df['race_id'] == race_id]
            if len(race_odds) == 0:
                continue

            # 馬ごとのデータ準備
            horses_data = []
            for idx, row in race_data.iterrows():
                umaban = row['Umaban']

                # 実オッズ取得
                odds_row = race_odds[race_odds['Umaban'] == umaban]
                if len(odds_row) == 0:
                    continue

                odds_real = odds_row.iloc[0]['odds_real']
                if pd.isna(odds_real) or odds_real <= 0:
                    continue

                # 特徴量取得
                features = []
                has_all_features = True
                for col in feature_cols:
                    val = row.get(col, np.nan)
                    if pd.isna(val):
                        has_all_features = False
                        break
                    features.append(val)

                if not has_all_features:
                    continue

                horses_data.append({
                    'umaban': umaban,
                    'horse_name': row.get('horse_name', ''),
                    'features': features,
                    'odds': odds_real,
                    'actual_rank': row.get('rank', 99)
                })

            if len(horses_data) < 3:
                continue

            # 予測
            X_race = np.array([h['features'] for h in horses_data])
            predicted_ranks = model.predict(X_race)

            # 予測順位をスコアに変換（順位が良いほど高スコア）
            scores = np.array([1.0 / max(rank, 1.0) for rank in predicted_ranks])
            predicted_probs = scores / scores.sum()

            # Value計算
            for i, horse_data in enumerate(horses_data):
                horse_data['predicted_prob'] = predicted_probs[i]
                horse_data['market_prob'] = 1.0 / horse_data['odds']
                horse_data['value'] = horse_data['predicted_prob'] - horse_data['market_prob']

            # 閾値以上のValueを持つ馬を抽出
            value_horses = [h for h in horses_data if h['value'] >= threshold]

            if len(value_horses) == 0:
                continue

            # 最もValueが高い馬にベット
            best_horse = max(value_horses, key=lambda x: x['value'])

            # 複勝オッズを推定
            num_horses = len(horses_data)
            place_odds = estimate_place_odds(best_horse['odds'], num_horses)

            # ベット
            bet_amount = 100
            bet_count += 1
            total_investment += bet_amount

            # 結果判定（1-3着なら的中）
            actual_rank = best_horse['actual_rank']
            is_win = actual_rank <= 3

            if is_win:
                win_count += 1
                payout = bet_amount * place_odds
                total_return += payout
                result = f"WIN({actual_rank}着)"
            else:
                result = f"LOSE({actual_rank}着)"

            # 詳細記録
            race_date = race_data.iloc[0]['date']
            bet_details.append({
                'race_id': race_id,
                'date': race_date,
                'umaban': best_horse['umaban'],
                'horse_name': best_horse['horse_name'],
                'win_odds': best_horse['odds'],
                'place_odds': place_odds,
                'predicted_prob': best_horse['predicted_prob'],
                'market_prob': best_horse['market_prob'],
                'value': best_horse['value'],
                'actual_rank': actual_rank,
                'result': result,
                'payout': payout if is_win else 0
            })

        # 結果集計
        hit_rate = (win_count / bet_count * 100) if bet_count > 0 else 0
        recovery_rate = (total_return / total_investment * 100) if total_investment > 0 else 0
        profit = total_return - total_investment

        results[threshold] = {
            'bet_count': bet_count,
            'win_count': win_count,
            'hit_rate': hit_rate,
            'total_investment': total_investment,
            'total_return': total_return,
            'recovery_rate': recovery_rate,
            'profit': profit,
            'bet_details': bet_details
        }

    return results

# テスト実行
print("\n" + "="*80)
print("バックテスト実行")
print("="*80)

value_thresholds = [0.0, 0.05, 0.10, 0.15, 0.20]
results = backtest_place_value_strategy(value_thresholds)

# 結果表示
print("\n" + "="*80)
print("複勝Value Betting戦略のバックテスト結果")
print("="*80)

print("\n{:>10s} | {:>8s} | {:>8s} | {:>12s} | {:>12s} | {:>8s}".format(
    "閾値", "ベット数", "的中数", "投資額", "回収額", "回収率"
))
print("-" * 80)

for threshold in value_thresholds:
    r = results[threshold]
    print("{:>9.0f}% | {:>8d} | {:>8d} | {:>12.0f}円 | {:>12.0f}円 | {:>7.1f}%".format(
        threshold * 100,
        r['bet_count'],
        r['win_count'],
        r['total_investment'],
        r['total_return'],
        r['recovery_rate']
    ))

# 最良の閾値の詳細を保存
best_threshold = max(results.keys(), key=lambda k: results[k]['recovery_rate'])
best_result = results[best_threshold]

print(f"\n最良の閾値: {best_threshold*100:.0f}%")
print(f"  ベット数: {best_result['bet_count']}")
print(f"  的中数: {best_result['win_count']}")
print(f"  的中率: {best_result['hit_rate']:.1f}%")
print(f"  回収率: {best_result['recovery_rate']:.1f}%")
print(f"  損益: {best_result['profit']:+.0f}円")

# 詳細をCSVに保存
bet_details_df = pd.DataFrame(best_result['bet_details'])
bet_details_df.to_csv('place_bets_detail.csv', index=False, encoding='utf-8-sig')
print(f"\nベット詳細を place_bets_detail.csv に保存しました")

# 単勝との比較データ出力
print("\n" + "="*80)
print("単勝 vs 複勝 比較（閾値5%の場合）")
print("="*80)

if 0.05 in results:
    place_result = results[0.05]
    print("\n【複勝】")
    print(f"  ベット数: {place_result['bet_count']}")
    print(f"  的中数: {place_result['win_count']}")
    print(f"  的中率: {place_result['hit_rate']:.1f}%")
    print(f"  回収率: {place_result['recovery_rate']:.1f}%")
    print(f"  損益: {place_result['profit']:+.0f}円")

    print("\n【単勝】（参考: 前回の結果）")
    print(f"  ベット数: 159")
    print(f"  的中数: 3")
    print(f"  的中率: 1.9%")
    print(f"  回収率: 112.8%")
    print(f"  損益: +2,030円")

    print("\n【改善点】")
    print(f"  的中率: 1.9% → {place_result['hit_rate']:.1f}% ({place_result['hit_rate']/1.9:.1f}倍)")
    print(f"  的中数: 3回 → {place_result['win_count']}回 ({place_result['win_count']/3:.1f}倍)")

print("\n" + "="*80)
print("完了")
print("="*80)
