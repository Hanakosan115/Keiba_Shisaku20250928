"""
全券種総合バックテスト
単勝・複勝・馬連・馬単・ワイド・3連複・3連単
"""

import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta

# 前のスクリプトから関数をインポート（簡略化のため主要部分のみ記載）
exec(open('backtest_value_strategy.py', encoding='utf-8').read().split('print("="*80)')[0])

def estimate_place_odds_realistic(win_odds, num_horses):
    """改善された複勝オッズ推定"""
    if win_odds < 2.0:
        ratio = 0.15
    elif win_odds < 5.0:
        ratio = 0.20
    elif win_odds < 10.0:
        ratio = 0.25
    elif win_odds < 20.0:
        ratio = 0.30
    else:
        ratio = 0.35

    place_odds = win_odds * ratio
    return max(place_odds, 1.1)

def estimate_wide_payout(odds1, odds2, num_horses):
    """
    ワイドの理論配当を推定
    2頭が3着以内に入る（順不同）
    """
    prob1 = 1.0 / odds1
    prob2 = 1.0 / odds2

    # ワイドの的中確率（2頭とも3着以内）
    # 簡易計算: 各馬の3着以内確率を掛け合わせる
    place_prob1 = min(prob1 * 3, 0.5)  # 最大50%
    place_prob2 = min(prob2 * 3, 0.3)

    combined_prob = place_prob1 * place_prob2 * 2

    payout = (0.75 / combined_prob) if combined_prob > 0 else 50

    return max(payout, 1.5)

print("="*80)
print("全券種総合バックテスト")
print("="*80)

# モデル読み込み
print("\nモデル読み込み中...")
with open('lgbm_model_hybrid.pkl', 'rb') as f:
    model = pickle.load(f)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv',
                 encoding='utf-8', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 実オッズ読み込み
odds_df = pd.read_csv('odds_2024_sample_500.csv', encoding='utf-8')
odds_df['race_id'] = odds_df['race_id'].astype(str)
df['race_id'] = df['race_id'].astype(str)

print(f"総データ数: {len(df):,}件")
print(f"オッズデータ: {len(odds_df):,}件")

odds_race_ids = odds_df['race_id'].unique()
print(f"テストレース数: {len(odds_race_ids)}レース")

# 統計キャッシュ
jockey_stats_cache = {}
trainer_stats_cache = {}

# 結果格納（Value 5%閾値のみ）
threshold = 0.05
results = {
    'tansho': {'bets': 0, 'wins': 0, 'investment': 0, 'return': 0},
    'fukusho': {'bets': 0, 'wins': 0, 'investment': 0, 'return': 0},
    'wide': {'bets': 0, 'wins': 0, 'investment': 0, 'return': 0},
    'umaren': {'bets': 0, 'wins': 0, 'investment': 0, 'return': 0},
    'umatan': {'bets': 0, 'wins': 0, 'investment': 0, 'return': 0},
    'sanrenpuku': {'bets': 0, 'wins': 0, 'investment': 0, 'return': 0},
    'sanrentan': {'bets': 0, 'wins': 0, 'investment': 0, 'return': 0}
}

print("\nバックテスト実行中...")

for idx, race_id in enumerate(odds_race_ids):
    if (idx + 1) % 100 == 0:
        print(f"  進捗: {idx+1}/{len(odds_race_ids)}")

    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_date_str = race_horses.iloc[0]['date']
    race_distance = pd.to_numeric(race_horses.iloc[0]['distance'], errors='coerce')
    race_distance = race_distance if pd.notna(race_distance) else 1600
    race_condition = race_horses.iloc[0]['track_condition']

    if race_date_str not in jockey_stats_cache:
        historical_df = df[df['date_parsed'] < pd.to_datetime(race_date_str)]
        jockey_stats_cache[race_date_str] = calculate_person_stats(
            historical_df, 'JockeyName', race_date_str, months_back=12
        )
        trainer_stats_cache[race_date_str] = calculate_person_stats(
            historical_df, 'TrainerName', race_date_str, months_back=12
        )

    jockey_stats = jockey_stats_cache[race_date_str]
    trainer_stats = trainer_stats_cache[race_date_str]

    horses_data = []

    for _, horse in race_horses.iterrows():
        umaban = horse.get('Umaban')
        actual_rank = pd.to_numeric(horse.get('Rank'), errors='coerce')

        # 実オッズ取得
        odds_match = odds_df[
            (odds_df['race_id'] == race_id) &
            (odds_df['Umaban'] == umaban)
        ]

        if len(odds_match) == 0:
            continue

        odds = odds_match.iloc[0]['odds_real']

        # 特徴量抽出
        features = extract_features(
            horse, race_horses, df, race_date_str, race_distance, race_condition,
            jockey_stats, trainer_stats, odds
        )

        horses_data.append({
            'umaban': umaban,
            'features': features,
            'odds': odds,
            'actual_rank': actual_rank
        })

    if len(horses_data) == 0:
        continue

    # 予測実行
    X_race = np.array([h['features'] for h in horses_data])
    predicted_ranks = model.predict(X_race)

    # 順位をスコアに変換
    scores = np.array([1.0 / max(rank, 1.0) for rank in predicted_ranks])
    predicted_probs = scores / scores.sum()

    for i, horse_data in enumerate(horses_data):
        horse_data['predicted_prob'] = predicted_probs[i]
        horse_data['predicted_rank'] = predicted_ranks[i]
        horse_data['market_prob'] = 1.0 / horse_data['odds']
        horse_data['value'] = horse_data['predicted_prob'] - horse_data['market_prob']

    # Value閾値以上の馬を抽出
    value_horses = [h for h in horses_data if h['value'] >= threshold]

    if len(value_horses) == 0:
        continue

    # 最もValueが高い馬
    best_horse = max(value_horses, key=lambda x: x['value'])

    # 予測順位でソート
    horses_sorted = sorted(horses_data, key=lambda x: x['predicted_rank'])

    # 実際の1-3着
    actual_top3 = sorted(
        [h for h in horses_data if h['actual_rank'] <= 3],
        key=lambda x: x['actual_rank']
    )

    if len(actual_top3) < 3:
        continue

    actual_1st_uma = actual_top3[0]['umaban']
    actual_2nd_uma = actual_top3[1]['umaban']
    actual_3rd_uma = actual_top3[2]['umaban']

    # 単勝（Value馬）
    results['tansho']['bets'] += 1
    results['tansho']['investment'] += 100
    if best_horse['actual_rank'] == 1:
        results['tansho']['wins'] += 1
        results['tansho']['return'] += best_horse['odds'] * 100

    # 複勝（Value馬）
    results['fukusho']['bets'] += 1
    results['fukusho']['investment'] += 100
    if best_horse['actual_rank'] <= 3:
        results['fukusho']['wins'] += 1
        place_odds = estimate_place_odds_realistic(best_horse['odds'], len(horses_data))
        results['fukusho']['return'] += place_odds * 100

    # 以下、予測上位馬で勝負
    if len(horses_sorted) >= 2:
        pred_1st = horses_sorted[0]
        pred_2nd = horses_sorted[1]

        # ワイド（予測1-2位）
        results['wide']['bets'] += 1
        results['wide']['investment'] += 100

        pred_set = {pred_1st['umaban'], pred_2nd['umaban']}
        actual_set = {actual_1st_uma, actual_2nd_uma, actual_3rd_uma}

        # 2頭とも3着以内ならワイド的中
        if len(pred_set & actual_set) == 2:
            results['wide']['wins'] += 1
            payout = estimate_wide_payout(pred_1st['odds'], pred_2nd['odds'], len(horses_data))
            results['wide']['return'] += payout * 100

        # 馬連
        results['umaren']['bets'] += 1
        results['umaren']['investment'] += 100
        actual_12_set = {actual_1st_uma, actual_2nd_uma}
        if pred_set == actual_12_set:
            results['umaren']['wins'] += 1
            from backtest_exotic_bets import estimate_umaren_payout
            payout = estimate_umaren_payout(pred_1st['odds'], pred_2nd['odds'], len(horses_data))
            results['umaren']['return'] += payout * 100

        # 馬単
        results['umatan']['bets'] += 1
        results['umatan']['investment'] += 100
        if pred_1st['umaban'] == actual_1st_uma and pred_2nd['umaban'] == actual_2nd_uma:
            results['umatan']['wins'] += 1
            from backtest_exotic_bets import estimate_umatan_payout
            payout = estimate_umatan_payout(pred_1st['odds'], pred_2nd['odds'], len(horses_data))
            results['umatan']['return'] += payout * 100

    if len(horses_sorted) >= 3:
        pred_1st = horses_sorted[0]
        pred_2nd = horses_sorted[1]
        pred_3rd = horses_sorted[2]

        pred_set = {pred_1st['umaban'], pred_2nd['umaban'], pred_3rd['umaban']}
        actual_set = {actual_1st_uma, actual_2nd_uma, actual_3rd_uma}

        # 3連複
        results['sanrenpuku']['bets'] += 1
        results['sanrenpuku']['investment'] += 100
        if pred_set == actual_set:
            results['sanrenpuku']['wins'] += 1
            from backtest_exotic_bets import estimate_sanrenpuku_payout
            payout = estimate_sanrenpuku_payout(
                pred_1st['odds'], pred_2nd['odds'], pred_3rd['odds'], len(horses_data)
            )
            results['sanrenpuku']['return'] += payout * 100

        # 3連単
        results['sanrentan']['bets'] += 1
        results['sanrentan']['investment'] += 100
        if (pred_1st['umaban'] == actual_1st_uma and
            pred_2nd['umaban'] == actual_2nd_uma and
            pred_3rd['umaban'] == actual_3rd_uma):
            results['sanrentan']['wins'] += 1
            from backtest_exotic_bets import estimate_sanrentan_payout
            payout = estimate_sanrentan_payout(
                pred_1st['odds'], pred_2nd['odds'], pred_3rd['odds'], len(horses_data)
            )
            results['sanrentan']['return'] += payout * 100

print("\n" + "="*80)
print("全券種総合結果（Value 5%閾値）")
print("="*80)

print("\n{:>12s} | {:>8s} | {:>8s} | {:>8s} | {:>12s} | {:>12s} | {:>8s} | {:>10s}".format(
    "券種", "ベット数", "的中数", "的中率", "投資額", "回収額", "回収率", "損益"
))
print("-" * 100)

for bet_type, bet_name in [
    ('tansho', '単勝'),
    ('fukusho', '複勝'),
    ('wide', 'ワイド'),
    ('umaren', '馬連'),
    ('umatan', '馬単'),
    ('sanrenpuku', '3連複'),
    ('sanrentan', '3連単')
]:
    r = results[bet_type]
    bets = r['bets']
    wins = r['wins']
    investment = r['investment']
    ret = r['return']

    hit_rate = (wins / bets * 100) if bets > 0 else 0
    recovery = (ret / investment * 100) if investment > 0 else 0
    profit = ret - investment

    print("{:>12s} | {:>8d} | {:>8d} | {:>7.1f}% | {:>12,d}円 | {:>12,.0f}円 | {:>7.1f}% | {:>+10,.0f}円".format(
        bet_name, bets, wins, hit_rate, investment, ret, recovery, profit
    ))

print("\n" + "="*80)
print("完了")
print("="*80)
