"""
現在の戦略の限界を分析
- 的中レースと不的中レースの配当分布
- オッズ別の的中率・回収率
- 人気別の予測精度
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
print("現在の戦略の限界分析")
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

# 詳細分析用データ収集
analysis_data = []

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
        actual_odds = pd.to_numeric(horse.get('Odds_x'), errors='coerce')
        ninki = pd.to_numeric(horse.get('Ninki'), errors='coerce')

        horses_scores.append({
            'umaban': int(horse.get('Umaban', 0)),
            'score': score,
            'odds': actual_odds if pd.notna(actual_odds) else 999.9,
            'ninki': ninki if pd.notna(ninki) else 99
        })

    horses_scores.sort(key=lambda x: x['score'], reverse=True)

    top3 = [h['umaban'] for h in horses_scores[:3]]
    top3_odds = [h['odds'] for h in horses_scores[:3]]
    top3_ninki = [h['ninki'] for h in horses_scores[:3]]

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data:
        continue

    hit_found = False
    payout_amount = 0

    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_pairs = umaren_data.get('馬番', [])
        payouts = umaren_data.get('払戻金', [])

        if winning_pairs and len(winning_pairs) >= 2 and payouts:
            try:
                winning_pair = set([int(x) for x in winning_pairs[:2]])
                umaren_pairs = list(combinations(top3, 2))

                for pair in umaren_pairs:
                    if set(pair) == winning_pair:
                        hit_found = True
                        payout_amount = payouts[0]
                        break
            except:
                pass

    analysis_data.append({
        'race_id': race_id,
        'hit': hit_found,
        'payout': payout_amount if hit_found else (payouts[0] if payouts else 0),
        'avg_top3_odds': sum(top3_odds) / 3,
        'min_top3_odds': min(top3_odds),
        'max_top3_odds': max(top3_odds),
        'avg_top3_ninki': sum(top3_ninki) / 3,
    })

# DataFrameに変換
df_analysis = pd.DataFrame(analysis_data)

print("\n" + "=" * 80)
print("【1. 的中レースと不的中レースの比較】")
print("=" * 80)

hit_races = df_analysis[df_analysis['hit'] == True]
miss_races = df_analysis[df_analysis['hit'] == False]

print(f"\n的中レース数: {len(hit_races)}")
print(f"不的中レース数: {len(miss_races)}")

print("\n■ 的中レースの配当分布")
print(f"平均配当: {hit_races['payout'].mean():.0f}円")
print(f"中央値: {hit_races['payout'].median():.0f}円")
print(f"最高配当: {hit_races['payout'].max():.0f}円")
print(f"最低配当: {hit_races['payout'].min():.0f}円")

print("\n配当レンジ別:")
print(f"  ~500円: {(hit_races['payout'] < 500).sum()}回 ({(hit_races['payout'] < 500).sum()/len(hit_races)*100:.1f}%)")
print(f"  500-1000円: {((hit_races['payout'] >= 500) & (hit_races['payout'] < 1000)).sum()}回 ({((hit_races['payout'] >= 500) & (hit_races['payout'] < 1000)).sum()/len(hit_races)*100:.1f}%)")
print(f"  1000-2000円: {((hit_races['payout'] >= 1000) & (hit_races['payout'] < 2000)).sum()}回 ({((hit_races['payout'] >= 1000) & (hit_races['payout'] < 2000)).sum()/len(hit_races)*100:.1f}%)")
print(f"  2000-5000円: {((hit_races['payout'] >= 2000) & (hit_races['payout'] < 5000)).sum()}回 ({((hit_races['payout'] >= 2000) & (hit_races['payout'] < 5000)).sum()/len(hit_races)*100:.1f}%)")
print(f"  5000円~: {(hit_races['payout'] >= 5000).sum()}回 ({(hit_races['payout'] >= 5000).sum()/len(hit_races)*100:.1f}%)")

print("\n■ 不的中レースの正解配当（逃した配当）")
print(f"平均配当: {miss_races['payout'].mean():.0f}円")
print(f"中央値: {miss_races['payout'].median():.0f}円")

print("\n" + "=" * 80)
print("【2. TOP3予測馬のオッズ・人気分析】")
print("=" * 80)

print("\n■ 的中レースのTOP3")
print(f"平均オッズ: {hit_races['avg_top3_odds'].mean():.2f}倍")
print(f"平均人気: {hit_races['avg_top3_ninki'].mean():.1f}番人気")

print("\n■ 不的中レースのTOP3")
print(f"平均オッズ: {miss_races['avg_top3_odds'].mean():.2f}倍")
print(f"平均人気: {miss_races['avg_top3_ninki'].mean():.1f}番人気")

print("\n" + "=" * 80)
print("【3. オッズ範囲別の的中率・回収率】")
print("=" * 80)

odds_ranges = [
    (0, 2.0, "1.0-2.0倍（堅い）"),
    (2.0, 3.0, "2.0-3.0倍"),
    (3.0, 5.0, "3.0-5.0倍"),
    (5.0, 10.0, "5.0-10.0倍"),
    (10.0, 999, "10.0倍~（穴）")
]

print("\nオッズ範囲 | レース数 | 的中数 | 的中率 | 平均配当 | 期待回収率")
print("-" * 80)

for min_odds, max_odds, label in odds_ranges:
    subset = df_analysis[
        (df_analysis['avg_top3_odds'] >= min_odds) &
        (df_analysis['avg_top3_odds'] < max_odds)
    ]

    if len(subset) == 0:
        continue

    hit_count = subset['hit'].sum()
    hit_rate = hit_count / len(subset) * 100
    avg_payout = subset[subset['hit'] == True]['payout'].mean() if hit_count > 0 else 0

    # 期待回収率 = 的中率 × 平均配当 / 300円（3点購入）
    expected_recovery = (hit_rate / 100) * avg_payout / 300 * 100 if avg_payout > 0 else 0

    print(f"{label:20s} | {len(subset):4d}R | {hit_count:4d}回 | {hit_rate:5.1f}% | {avg_payout:7.0f}円 | {expected_recovery:6.1f}%")

print("\n" + "=" * 80)
print("【4. 問題点のまとめ】")
print("=" * 80)

# 本命偏重度をチェック
본명_rate = (hit_races['avg_top3_ninki'].mean() < 5.0)
low_payout_rate = (hit_races['payout'] < 1000).sum() / len(hit_races) * 100

issues = []

if hit_races['avg_top3_ninki'].mean() < 5.0:
    issues.append(f"本命偏重: TOP3の平均人気が{hit_races['avg_top3_ninki'].mean():.1f}番人気")

if low_payout_rate > 60:
    issues.append(f"低配当偏重: 的中の{low_payout_rate:.0f}%が1000円未満")

# 逃した高配当をチェック
high_payout_miss = miss_races[miss_races['payout'] >= 3000]
if len(high_payout_miss) > 100:
    issues.append(f"高配当の取りこぼし: 3000円以上の配当を{len(high_payout_miss)}回逃している")

if issues:
    print("\n検出された問題点:")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("\n重大な問題は検出されませんでした。")

print("\n" + "=" * 80)
print("【5. 改善可能性の評価】")
print("=" * 80)

# オッズ範囲で回収率100%超えがあるかチェック
best_odds_range = None
best_expected_recovery = 0

for min_odds, max_odds, label in odds_ranges:
    subset = df_analysis[
        (df_analysis['avg_top3_odds'] >= min_odds) &
        (df_analysis['avg_top3_odds'] < max_odds)
    ]

    if len(subset) == 0:
        continue

    hit_count = subset['hit'].sum()
    if hit_count == 0:
        continue

    hit_rate = hit_count / len(subset) * 100
    avg_payout = subset[subset['hit'] == True]['payout'].mean()
    expected_recovery = (hit_rate / 100) * avg_payout / 300 * 100

    if expected_recovery > best_expected_recovery:
        best_expected_recovery = expected_recovery
        best_odds_range = label

print(f"\n最も期待回収率が高いオッズ範囲: {best_odds_range}")
print(f"期待回収率: {best_expected_recovery:.1f}%")

if best_expected_recovery >= 100:
    print("\n結論: オッズフィルタリングで黒字化の可能性あり")
else:
    print(f"\n結論: 現在のアプローチでは黒字化が困難（最高でも{best_expected_recovery:.1f}%）")
    print("      根本的なロジック見直しが必要")

print("\n" + "=" * 80)
print("分析完了")
print("=" * 80)
