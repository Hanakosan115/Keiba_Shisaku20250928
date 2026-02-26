"""
複勝ベッティングのデバッグ
"""

import pandas as pd
import numpy as np
import pickle

print("="*80)
print("複勝ベッティングのデバッグ")
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

# 2024年データでテスト
df_test = df[df['date_parsed'] >= '2024-01-01'].copy()

# オッズあるレースのみ
test_race_ids = df_test['race_id'].unique()
odds_race_ids = odds_df['race_id'].unique()
valid_race_ids = [rid for rid in test_race_ids if rid in odds_race_ids]

print(f"有効なレース数: {len(valid_race_ids)}")

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

# 最初の3レースを詳しく見る
threshold = 0.05

for race_idx, race_id in enumerate(valid_race_ids[:3]):
    print(f"\n{'='*80}")
    print(f"レース {race_idx + 1}: {race_id}")
    print("="*80)

    # レースデータ取得
    race_data = df_test[df_test['race_id'] == race_id].copy()
    print(f"レースデータ: {len(race_data)}頭")

    if len(race_data) == 0:
        print("  → レースデータなし、スキップ")
        continue

    race_odds = odds_df[odds_df['race_id'] == race_id]
    print(f"オッズデータ: {len(race_odds)}頭")

    if len(race_odds) == 0:
        print("  → オッズデータなし、スキップ")
        continue

    # 馬ごとのデータ準備
    horses_data = []
    excluded_reasons = {
        'no_umaban_match': 0,
        'invalid_odds': 0,
        'missing_features': 0
    }

    for idx, row in race_data.iterrows():
        umaban = row['Umaban']

        # 実オッズ取得
        odds_row = race_odds[race_odds['Umaban'] == umaban]
        if len(odds_row) == 0:
            excluded_reasons['no_umaban_match'] += 1
            continue

        odds_real = odds_row.iloc[0]['odds_real']
        if pd.isna(odds_real) or odds_real <= 0:
            excluded_reasons['invalid_odds'] += 1
            continue

        # 特徴量取得
        features = []
        has_all_features = True
        missing_cols = []
        for col in feature_cols:
            val = row.get(col, np.nan)
            if pd.isna(val):
                has_all_features = False
                missing_cols.append(col)
            features.append(val)

        if not has_all_features:
            excluded_reasons['missing_features'] += 1
            if len(horses_data) == 0:  # 最初の1頭だけ詳細表示
                print(f"\n  馬番{umaban}: 特徴量不足")
                print(f"    欠損カラム: {missing_cols[:5]}...")  # 最初の5個だけ表示
            continue

        horses_data.append({
            'umaban': umaban,
            'horse_name': row.get('horse_name', ''),
            'features': features,
            'odds': odds_real,
            'actual_rank': row.get('rank', 99)
        })

    print(f"\n除外理由:")
    print(f"  馬番マッチなし: {excluded_reasons['no_umaban_match']}頭")
    print(f"  無効なオッズ: {excluded_reasons['invalid_odds']}頭")
    print(f"  特徴量不足: {excluded_reasons['missing_features']}頭")
    print(f"  → 有効な馬: {len(horses_data)}頭")

    if len(horses_data) < 3:
        print("  → 有効な馬が3頭未満、スキップ")
        continue

    # 予測
    X_race = np.array([h['features'] for h in horses_data])
    predicted_ranks = model.predict(X_race)

    # 予測順位をスコアに変換
    scores = np.array([1.0 / max(rank, 1.0) for rank in predicted_ranks])
    predicted_probs = scores / scores.sum()

    # Value計算
    for i, horse_data in enumerate(horses_data):
        horse_data['predicted_prob'] = predicted_probs[i]
        horse_data['predicted_rank'] = predicted_ranks[i]
        horse_data['market_prob'] = 1.0 / horse_data['odds']
        horse_data['value'] = horse_data['predicted_prob'] - horse_data['market_prob']

    # Value順にソート
    horses_data.sort(key=lambda x: x['value'], reverse=True)

    # 上位5頭のValue表示
    print(f"\nValue上位5頭:")
    print(f"  {'馬番':>4s} {'馬名':>12s} {'予測順位':>8s} {'オッズ':>6s} {'Value':>8s}")
    for i, h in enumerate(horses_data[:5]):
        print(f"  {h['umaban']:>4d} {h['horse_name'][:12]:>12s} {h['predicted_rank']:>8.2f} {h['odds']:>6.1f} {h['value']*100:>7.2f}%")

    # 閾値以上のValueを持つ馬を抽出
    value_horses = [h for h in horses_data if h['value'] >= threshold]

    print(f"\n閾値{threshold*100:.0f}%以上の馬: {len(value_horses)}頭")

    if len(value_horses) == 0:
        print("  → ベット対象なし")
        continue

    # 最もValueが高い馬にベット
    best_horse = max(value_horses, key=lambda x: x['value'])

    print(f"\nベット対象:")
    print(f"  馬番: {best_horse['umaban']}")
    print(f"  馬名: {best_horse['horse_name']}")
    print(f"  予測順位: {best_horse['predicted_rank']:.2f}")
    print(f"  オッズ: {best_horse['odds']:.1f}倍")
    print(f"  Value: {best_horse['value']*100:.2f}%")
    print(f"  実際の順位: {best_horse['actual_rank']}着")
    print(f"  結果: {'的中' if best_horse['actual_rank'] <= 3 else '不的中'}")

print("\n" + "="*80)
print("完了")
print("="*80)
