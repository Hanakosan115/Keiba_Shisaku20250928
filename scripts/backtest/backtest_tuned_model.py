"""
チューニング済みLightGBMモデルでバックテスト
- lightgbm_model_tuned.pkl を使用
- 2024年データでテスト
"""
import pandas as pd
import json
import sys
import numpy as np
from collections import defaultdict
from itertools import combinations
import pickle
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv
from data_config import MAIN_CSV, MAIN_JSON

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

def calculate_person_stats(df, person_col, reference_date, months_back=12):
    """騎手・調教師の統計を計算"""
    person_stats = {}

    reference_date_parsed = pd.to_datetime(reference_date)
    start_date = reference_date_parsed - pd.DateOffset(months=months_back)

    period_df = df[
        (df['date_parsed'] >= start_date) &
        (df['date_parsed'] < reference_date_parsed)
    ].copy()

    period_df['rank_num'] = pd.to_numeric(period_df['Rank'], errors='coerce')
    period_df = period_df[period_df['rank_num'].notna()]

    for person in period_df[person_col].unique():
        if pd.isna(person) or person == '':
            continue

        person_races = period_df[period_df[person_col] == person]
        total_races = len(person_races)

        if total_races >= 10:
            wins = (person_races['rank_num'] == 1).sum()
            top3 = (person_races['rank_num'] <= 3).sum()

            person_stats[person] = {
                'win_rate': wins / total_races,
                'top3_rate': top3 / total_races,
                'races': total_races
            }

    return person_stats

print("=" * 80)
print("チューニング済みLightGBMモデル：バックテスト")
print("=" * 80)

# モデル読み込み
print("\nチューニング済みモデル読み込み中...")
model_path = r"C:\Users\bu158\Keiba_Shisaku20250928\lightgbm_model_tuned.pkl"
with open(model_path, 'rb') as f:
    model_data = pickle.load(f)
    model = model_data['model']
    feature_names = model_data['feature_names']
    params = model_data['params']

print(f"モデルパラメータ: num_leaves={params['num_leaves']}, learning_rate={params['learning_rate']}")

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(MAIN_CSV,
                 encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(MAIN_JSON)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年のデータ
target_races = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"対象: 2024年 {len(race_ids)}レース")

# ワイド戦略の結果
strategies = {
    'ワイド_1-2': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
    'ワイド_1軸流し': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
    'ワイド_BOX3頭': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
}

stats_cache = {}

for idx, race_id in enumerate(race_ids):
    if (idx + 1) % 500 == 0:
        print(f"  {idx + 1}/{len(race_ids)} レース処理中...")

    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_horses = race_horses.sort_values('Umaban')

    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue

    race_date_str = str(race_date)[:10]

    # 騎手・調教師統計
    if race_date_str not in stats_cache:
        stats_cache[race_date_str] = {
            'jockey': calculate_person_stats(df, 'JockeyName', race_date_str, months_back=12),
            'trainer': calculate_person_stats(df, 'TrainerName', race_date_str, months_back=12)
        }

    jockey_stats = stats_cache[race_date_str]['jockey']
    trainer_stats = stats_cache[race_date_str]['trainer']

    # 特徴量抽出
    horse_features = []
    horse_umabans = []

    for _, horse in race_horses.iterrows():
        horse_id = horse.get('horse_id')
        past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=10)

        # 過去成績
        if past_results and len(past_results) > 0:
            recent_ranks = []
            for race in past_results[:5]:
                if isinstance(race, dict):
                    past_rank = pd.to_numeric(race.get('rank'), errors='coerce')
                    if pd.notna(past_rank):
                        recent_ranks.append(past_rank)

            if recent_ranks:
                avg_rank = np.mean(recent_ranks)
                std_rank = np.std(recent_ranks) if len(recent_ranks) > 1 else 0
                min_rank = np.min(recent_ranks)
                max_rank = np.max(recent_ranks)
                recent_win_rate = sum(1 for r in recent_ranks if r == 1) / len(recent_ranks)
                recent_top3_rate = sum(1 for r in recent_ranks if r <= 3) / len(recent_ranks)
            else:
                avg_rank, std_rank, min_rank, max_rank = 8, 0, 10, 10
                recent_win_rate, recent_top3_rate = 0, 0
        else:
            avg_rank, std_rank, min_rank, max_rank = 8, 0, 10, 10
            recent_win_rate, recent_top3_rate = 0, 0

        # 騎手統計
        jockey_name = horse.get('JockeyName')
        if jockey_name in jockey_stats:
            jockey_win_rate = jockey_stats[jockey_name]['win_rate']
            jockey_top3_rate = jockey_stats[jockey_name]['top3_rate']
            jockey_races = jockey_stats[jockey_name]['races']
        else:
            jockey_win_rate, jockey_top3_rate, jockey_races = 0, 0, 0

        # 調教師統計
        trainer_name = horse.get('TrainerName')
        if trainer_name in trainer_stats:
            trainer_win_rate = trainer_stats[trainer_name]['win_rate']
            trainer_top3_rate = trainer_stats[trainer_name]['top3_rate']
            trainer_races = trainer_stats[trainer_name]['races']
        else:
            trainer_win_rate, trainer_top3_rate, trainer_races = 0, 0, 0

        # その他
        age = pd.to_numeric(horse.get('Age'), errors='coerce')
        age = age if pd.notna(age) else 5

        weight_diff = pd.to_numeric(horse.get('WeightDiff'), errors='coerce')
        weight_diff = weight_diff if pd.notna(weight_diff) else 0

        weight = pd.to_numeric(horse.get('Weight'), errors='coerce')
        weight = weight if pd.notna(weight) else 480

        ninki = pd.to_numeric(horse.get('Ninki'), errors='coerce')
        ninki = ninki if pd.notna(ninki) else 10

        odds = pd.to_numeric(horse.get('Odds_x'), errors='coerce')
        odds = odds if pd.notna(odds) and odds > 0 else 50

        waku = pd.to_numeric(horse.get('Waku'), errors='coerce')
        waku = waku if pd.notna(waku) else 5

        course_type = horse.get('course_type')
        course_turf = 1 if course_type == '芝' else 0
        course_dirt = 1 if course_type == 'ダート' else 0

        track_condition = horse.get('track_condition')
        track_good = 1 if track_condition == '良' else 0

        distance = pd.to_numeric(horse.get('distance'), errors='coerce')
        distance = distance if pd.notna(distance) else 1600

        feature_vector = [
            avg_rank, std_rank, min_rank, max_rank,
            recent_win_rate, recent_top3_rate,
            jockey_win_rate, jockey_top3_rate, jockey_races,
            trainer_win_rate, trainer_top3_rate, trainer_races,
            age, weight_diff, weight, np.log1p(odds), ninki, waku,
            course_turf, course_dirt, track_good, distance / 1000
        ]

        horse_features.append(feature_vector)
        horse_umabans.append(int(horse.get('Umaban', 0)))

    if len(horse_features) < 8:
        continue

    # 予測
    X = np.array(horse_features)
    predictions = model.predict(X)

    # 予測スコアが低い順にソート（スコアが低いほど良い）
    predicted_ranking = sorted(
        zip(horse_umabans, predictions),
        key=lambda x: x[1]
    )

    pred_1st = predicted_ranking[0][0]
    pred_2nd = predicted_ranking[1][0]
    pred_3rd = predicted_ranking[2][0]

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data or 'ワイド' not in payout_data:
        continue

    wide_data = payout_data['ワイド']
    winning_pairs = wide_data.get('馬番', [])
    payouts = wide_data.get('払戻金', [])

    if not winning_pairs or not payouts:
        continue

    # ワイド 1-2
    strategies['ワイド_1-2']['total'] += 1
    strategies['ワイド_1-2']['cost'] += 100

    hit_found = False
    pred_pair = set([pred_1st, pred_2nd])
    for i in range(0, len(winning_pairs), 2):
        if i + 1 < len(winning_pairs):
            winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
            if pred_pair == winning_pair:
                payout_amount = payouts[i // 2]
                if payout_amount:
                    strategies['ワイド_1-2']['hit'] += 1
                    strategies['ワイド_1-2']['return'] += payout_amount
                    hit_found = True
                break

    # ワイド 1軸流し（1-2, 1-3）
    strategies['ワイド_1軸流し']['total'] += 1
    strategies['ワイド_1軸流し']['cost'] += 200

    for pred_pair in [(pred_1st, pred_2nd), (pred_1st, pred_3rd)]:
        pair_set = set(pred_pair)
        for i in range(0, len(winning_pairs), 2):
            if i + 1 < len(winning_pairs):
                winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
                if pair_set == winning_pair:
                    payout_amount = payouts[i // 2]
                    if payout_amount:
                        strategies['ワイド_1軸流し']['hit'] += 1
                        strategies['ワイド_1軸流し']['return'] += payout_amount
                    break

    # ワイド BOX3頭
    strategies['ワイド_BOX3頭']['total'] += 1
    strategies['ワイド_BOX3頭']['cost'] += 300

    for pred_pair in combinations([pred_1st, pred_2nd, pred_3rd], 2):
        pair_set = set(pred_pair)
        for i in range(0, len(winning_pairs), 2):
            if i + 1 < len(winning_pairs):
                winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
                if pair_set == winning_pair:
                    payout_amount = payouts[i // 2]
                    if payout_amount:
                        strategies['ワイド_BOX3頭']['hit'] += 1
                        strategies['ワイド_BOX3頭']['return'] += payout_amount
                    break

print("\n" + "=" * 80)
print("【チューニング済みモデルの結果】2024年")
print("=" * 80)

print("\n戦略           | レース数 | 的中数 | 的中率 | 投資額     | 払戻額     | 回収率 | 損益")
print("-" * 90)

for name, result in strategies.items():
    if result['total'] > 0:
        hit_rate = result['hit'] / result['total'] * 100
        recovery = result['return'] / result['cost'] * 100 if result['cost'] > 0 else 0
        profit = result['return'] - result['cost']

        print(f"{name:15s} | {result['total']:4d}R | {result['hit']:4d}回 | {hit_rate:5.1f}% | "
              f"{result['cost']:10,}円 | {result['return']:10,}円 | {recovery:6.1f}% | {profit:+10,}円")

print("\n" + "=" * 80)
print("バックテスト完了")
print("=" * 80)
