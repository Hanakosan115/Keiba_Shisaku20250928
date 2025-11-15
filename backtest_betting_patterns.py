"""
複数の買い方パターンを比較
- パターン1: 3頭BOX（現状）= 3点
- パターン2: 1位+2位の1点買い
- パターン3: 1位軸流し（2位、3位）= 2点
- パターン4: 1位+2位軸流し（3位、4位、5位）= 6点
- パターン5: スコア差によって買い方を変える（動的）
"""
import pandas as pd
import json
import sys
from itertools import combinations
import numpy as np
from collections import defaultdict
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

def precalculate_stats(df, target_year=2024):
    """騎手・調教師の統計を事前計算"""
    print("\n騎手・調教師の統計を事前計算中...")

    target_df = df[df['date_parsed'].dt.year == target_year].copy()
    jockeys = target_df['JockeyName'].unique()
    trainers = target_df['TrainerName'].unique()
    months = target_df['date_parsed'].dt.to_period('M').unique()

    print(f"  騎手数: {len(jockeys)}, 調教師数: {len(trainers)}, 月数: {len(months)}")

    jockey_stats = defaultdict(lambda: {'win_rate': 0, 'top3_rate': 0, 'races': 0})

    for month in sorted(months):
        month_start = month.to_timestamp()
        look_back_start = month_start - pd.DateOffset(months=6)

        period_df = df[
            (df['date_parsed'] >= look_back_start) &
            (df['date_parsed'] < month_start)
        ].copy()

        period_df['rank_num'] = pd.to_numeric(period_df['Rank'], errors='coerce')
        period_df = period_df[period_df['rank_num'].notna()]

        for jockey in period_df['JockeyName'].unique():
            if pd.isna(jockey) or jockey == '':
                continue

            jockey_races = period_df[period_df['JockeyName'] == jockey]
            total_races = len(jockey_races)

            if total_races >= 10:
                wins = (jockey_races['rank_num'] == 1).sum()
                top3 = (jockey_races['rank_num'] <= 3).sum()

                jockey_stats[(jockey, str(month))] = {
                    'win_rate': wins / total_races * 100,
                    'top3_rate': top3 / total_races * 100,
                    'races': total_races
                }

    trainer_stats = defaultdict(lambda: {'win_rate': 0, 'top3_rate': 0, 'races': 0})

    for month in sorted(months):
        month_start = month.to_timestamp()
        look_back_start = month_start - pd.DateOffset(months=6)

        period_df = df[
            (df['date_parsed'] >= look_back_start) &
            (df['date_parsed'] < month_start)
        ].copy()

        period_df['rank_num'] = pd.to_numeric(period_df['Rank'], errors='coerce')
        period_df = period_df[period_df['rank_num'].notna()]

        for trainer in period_df['TrainerName'].unique():
            if pd.isna(trainer) or trainer == '':
                continue

            trainer_races = period_df[period_df['TrainerName'] == trainer]
            total_races = len(trainer_races)

            if total_races >= 10:
                wins = (trainer_races['rank_num'] == 1).sum()
                top3 = (trainer_races['rank_num'] <= 3).sum()

                trainer_stats[(trainer, str(month))] = {
                    'win_rate': wins / total_races * 100,
                    'top3_rate': top3 / total_races * 100,
                    'races': total_races
                }

    print(f"  騎手統計: {len(jockey_stats)}件")
    print(f"  調教師統計: {len(trainer_stats)}件")

    return jockey_stats, trainer_stats

def calculate_improved_score(horse_data, race_conditions, race_date, jockey_stats, trainer_stats):
    """改善版スコア計算"""
    score = 50.0

    race_results = horse_data.get('race_results', [])

    if race_results and len(race_results) > 0:
        recent_ranks = []
        for race in race_results[:3]:
            if isinstance(race, dict):
                rank = pd.to_numeric(race.get('rank'), errors='coerce')
                if pd.notna(rank):
                    recent_ranks.append(rank)

        if recent_ranks:
            avg_rank = sum(recent_ranks) / len(recent_ranks)
            if avg_rank <= 2:
                score += 25
            elif avg_rank <= 3:
                score += 15
            elif avg_rank <= 5:
                score += 8
            elif avg_rank <= 8:
                score += 3
            else:
                score -= 8

            if len(recent_ranks) >= 2:
                std = np.std(recent_ranks)
                if std <= 1:
                    score += 8
                elif std <= 2:
                    score += 4
                elif std >= 5:
                    score -= 4

        current_distance = pd.to_numeric(race_conditions.get('Distance'), errors='coerce')
        if pd.notna(current_distance):
            distance_fit_score = 0
            distance_count = 0

            for race in race_results[:5]:
                if isinstance(race, dict):
                    past_distance = pd.to_numeric(race.get('distance'), errors='coerce')
                    past_rank = pd.to_numeric(race.get('rank'), errors='coerce')

                    if pd.notna(past_distance) and pd.notna(past_rank):
                        distance_diff = abs(current_distance - past_distance)

                        if distance_diff <= 200:
                            if past_rank <= 3:
                                distance_fit_score += 10
                            elif past_rank <= 5:
                                distance_fit_score += 3
                            distance_count += 1

            if distance_count > 0:
                score += distance_fit_score / distance_count

    jockey_name = horse_data.get('jockey_name')
    if jockey_name and not pd.isna(jockey_name):
        race_month = pd.to_datetime(race_date).to_period('M')
        jockey_key = (jockey_name, str(race_month))

        if jockey_key in jockey_stats:
            stats = jockey_stats[jockey_key]
            win_rate = stats['win_rate']

            if win_rate >= 15:
                score += 15
            elif win_rate >= 10:
                score += 10
            elif win_rate >= 7:
                score += 5
            elif win_rate >= 5:
                score += 2
            elif win_rate < 3:
                score -= 5

    trainer_name = horse_data.get('trainer_name')
    if trainer_name and not pd.isna(trainer_name):
        race_month = pd.to_datetime(race_date).to_period('M')
        trainer_key = (trainer_name, str(race_month))

        if trainer_key in trainer_stats:
            stats = trainer_stats[trainer_key]
            win_rate = stats['win_rate']

            if win_rate >= 12:
                score += 12
            elif win_rate >= 8:
                score += 8
            elif win_rate >= 5:
                score += 4
            elif win_rate >= 3:
                score += 2
            elif win_rate < 2:
                score -= 3

    weight_diff = horse_data.get('weight_diff')
    if weight_diff is not None and not pd.isna(weight_diff):
        weight_diff_num = pd.to_numeric(weight_diff, errors='coerce')
        if pd.notna(weight_diff_num):
            if -2 <= weight_diff_num <= 4:
                score += 5
            elif -5 <= weight_diff_num <= 8:
                score += 2
            elif weight_diff_num < -10 or weight_diff_num > 15:
                score -= 8
            elif weight_diff_num < -5 or weight_diff_num > 10:
                score -= 4

    age = horse_data.get('age')
    if age is not None and not pd.isna(age):
        age_num = pd.to_numeric(age, errors='coerce')
        if pd.notna(age_num):
            if 4 <= age_num <= 5:
                score += 3
            elif age_num == 3:
                score += 1
            elif age_num >= 7:
                score -= 5

    return max(0, score)

print("=" * 80)
print("複数の買い方パターンを比較")
print("=" * 80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

jockey_stats, trainer_stats = precalculate_stats(df, target_year=2024)

target_races = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"\n対象: 2024年 {len(race_ids)}レース")

# 買い方パターンごとの結果
patterns = {
    'BOX_3': {'name': '3頭BOX', 'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    'single_1_2': {'name': '1位+2位（1点）', 'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    'axis_1': {'name': '1位軸流し（2点）', 'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    'axis_1_2': {'name': '1位+2位軸流し（6点）', 'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    'dynamic': {'name': 'スコア差動的', 'total': 0, 'hit': 0, 'return': 0, 'cost': 0}
}

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

    # 予測実行
    horses_scores = []

    for _, horse in race_horses.iterrows():
        horse_id = horse.get('horse_id')
        past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=5)

        horse_data = {
            'race_results': past_results,
            'jockey_name': horse.get('JockeyName'),
            'trainer_name': horse.get('TrainerName'),
            'weight_diff': horse.get('WeightDiff'),
            'sex': horse.get('Sex'),
            'age': horse.get('Age')
        }

        race_conditions = {
            'Distance': horse.get('distance'),
            'CourseType': horse.get('course_type'),
            'TrackCondition': horse.get('track_condition')
        }

        score = calculate_improved_score(horse_data, race_conditions, race_date_str, jockey_stats, trainer_stats)

        horses_scores.append({
            'umaban': int(horse.get('Umaban', 0)),
            'score': score
        })

    horses_scores.sort(key=lambda x: x['score'], reverse=True)

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data or '馬連' not in payout_data:
        continue

    umaren_data = payout_data['馬連']
    winning_pairs = umaren_data.get('馬番', [])
    payouts = umaren_data.get('払戻金', [])

    if not winning_pairs or len(winning_pairs) < 2 or not payouts:
        continue

    try:
        winning_pair = set([int(x) for x in winning_pairs[:2]])
        payout_amount = payouts[0]
    except:
        continue

    # スコア差を計算
    if len(horses_scores) >= 4:
        score_diff_1_2 = horses_scores[0]['score'] - horses_scores[1]['score']
        score_diff_1_3 = horses_scores[0]['score'] - horses_scores[2]['score']
    else:
        continue

    # パターン1: 3頭BOX（3点）
    top3 = [h['umaban'] for h in horses_scores[:3]]
    box_pairs = list(combinations(top3, 2))

    patterns['BOX_3']['total'] += 1
    patterns['BOX_3']['cost'] += 3 * 100

    for pair in box_pairs:
        if set(pair) == winning_pair and payout_amount:
            patterns['BOX_3']['hit'] += 1
            patterns['BOX_3']['return'] += payout_amount
            break

    # パターン2: 1位+2位（1点）
    single_pair = (horses_scores[0]['umaban'], horses_scores[1]['umaban'])

    patterns['single_1_2']['total'] += 1
    patterns['single_1_2']['cost'] += 1 * 100

    if set(single_pair) == winning_pair and payout_amount:
        patterns['single_1_2']['hit'] += 1
        patterns['single_1_2']['return'] += payout_amount

    # パターン3: 1位軸流し（1-2, 1-3の2点）
    axis_pairs = [
        (horses_scores[0]['umaban'], horses_scores[1]['umaban']),
        (horses_scores[0]['umaban'], horses_scores[2]['umaban'])
    ]

    patterns['axis_1']['total'] += 1
    patterns['axis_1']['cost'] += 2 * 100

    for pair in axis_pairs:
        if set(pair) == winning_pair and payout_amount:
            patterns['axis_1']['hit'] += 1
            patterns['axis_1']['return'] += payout_amount
            break

    # パターン4: 1位+2位軸流し（1-3, 1-4, 1-5, 2-3, 2-4, 2-5の6点）
    if len(horses_scores) >= 5:
        axis_1_2_pairs = []
        for i in [0, 1]:  # 1位と2位
            for j in [2, 3, 4]:  # 3位、4位、5位
                axis_1_2_pairs.append((horses_scores[i]['umaban'], horses_scores[j]['umaban']))

        patterns['axis_1_2']['total'] += 1
        patterns['axis_1_2']['cost'] += 6 * 100

        for pair in axis_1_2_pairs:
            if set(pair) == winning_pair and payout_amount:
                patterns['axis_1_2']['hit'] += 1
                patterns['axis_1_2']['return'] += payout_amount
                break

    # パターン5: スコア差によって動的に変更
    # スコア差が大きい（明確な1位）→ 1位軸流し2点
    # スコア差が小さい（混戦）→ 3頭BOX3点
    if score_diff_1_2 >= 10:  # 明確な1位がいる
        dynamic_pairs = axis_pairs
        dynamic_cost = 2 * 100
    else:  # 混戦
        dynamic_pairs = box_pairs
        dynamic_cost = 3 * 100

    patterns['dynamic']['total'] += 1
    patterns['dynamic']['cost'] += dynamic_cost

    for pair in dynamic_pairs:
        if set(pair) == winning_pair and payout_amount:
            patterns['dynamic']['hit'] += 1
            patterns['dynamic']['return'] += payout_amount
            break

# 結果出力
print("\n" + "=" * 80)
print("【買い方パターン別の結果】2024年")
print("=" * 80)

print("\nパターン | レース数 | 的中数 | 的中率 | 投資額 | 払戻額 | 回収率 | 損益")
print("-" * 80)

best_pattern = None
best_recovery = 0

for key, res in patterns.items():
    name = res['name']

    if res['total'] > 0 and res['cost'] > 0:
        hit_rate = res['hit'] / res['total'] * 100
        recovery = res['return'] / res['cost'] * 100
        profit = res['return'] - res['cost']

        print(f"{name:20s} | {res['total']:4d}R | {res['hit']:4d}回 | {hit_rate:5.1f}% | "
              f"{res['cost']:8,}円 | {res['return']:8,}円 | {recovery:6.1f}% | {profit:+9,}円")

        if recovery > best_recovery:
            best_recovery = recovery
            best_pattern = name

print("\n" + "=" * 80)
print("【ベストパターン】")
print("=" * 80)

if best_pattern:
    print(f"\n最高回収率: {best_recovery:.2f}%")
    print(f"推奨買い方: {best_pattern}")

print("\n" + "=" * 80)
print("【予測精度の評価】")
print("=" * 80)

# 1位+2位の的中率で予測精度を評価
single_hit_rate = patterns['single_1_2']['hit'] / patterns['single_1_2']['total'] * 100
print(f"\n予測1位+2位の的中率: {single_hit_rate:.1f}%")

if single_hit_rate >= 25:
    print("評価: 予測精度は良好（25%以上）")
elif single_hit_rate >= 20:
    print("評価: 予測精度は普通（20-25%）")
elif single_hit_rate >= 15:
    print("評価: 予測精度はやや低い（15-20%）→ 改善の余地あり")
else:
    print("評価: 予測精度が低い（15%未満）→ スコアリングロジックの見直しが必要")

# 1位軸の的中率
axis_hit_rate = patterns['axis_1']['hit'] / patterns['axis_1']['total'] * 100
print(f"\n予測1位軸（1-2, 1-3）の的中率: {axis_hit_rate:.1f}%")

print("\n" + "=" * 80)
print("分析完了")
print("=" * 80)
