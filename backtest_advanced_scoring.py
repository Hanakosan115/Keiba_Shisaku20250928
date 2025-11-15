"""
高度なスコアリングシステムのバックテスト
- コース適性（芝/ダート）
- 競馬場適性
- 馬場状態適性
- 脚質推定と適性
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

def estimate_running_style(passage_str):
    """
    通過順位から脚質を推定
    passage_str: "5-5" のような形式
    返り値: "逃げ", "先行", "差し", "追込", None
    """
    if pd.isna(passage_str) or passage_str == '':
        return None

    try:
        parts = str(passage_str).split('-')
        if len(parts) < 2:
            return None

        # 前半と後半の順位
        first_pos = int(parts[0])
        last_pos = int(parts[-1])

        # 脚質判定
        if first_pos <= 2:
            return "逃げ"
        elif first_pos <= 4:
            return "先行"
        elif last_pos < first_pos:  # 後半上がってきた
            return "差し"
        else:
            return "追込"
    except:
        return None

def precalculate_stats(df, target_year=2024):
    """
    騎手・調教師の統計を事前に一括計算
    """
    print("\n騎手・調教師の統計を事前計算中...")

    # 対象年のデータ
    target_df = df[df['date_parsed'].dt.year == target_year].copy()

    # 統計を月ごとに計算
    stats_cache = {}

    # 全ての騎手・調教師・月の組み合わせを収集
    jockeys = target_df['JockeyName'].unique()
    trainers = target_df['TrainerName'].unique()
    months = target_df['date_parsed'].dt.to_period('M').unique()

    print(f"  騎手数: {len(jockeys)}, 調教師数: {len(trainers)}, 月数: {len(months)}")

    # 騎手統計の計算
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

        # 騎手ごとの統計
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

    # 調教師統計の計算
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

        # 調教師ごとの統計
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

def calculate_course_fitness(horse_data, current_course_type):
    """
    馬のコース適性を評価（芝/ダート）
    """
    if pd.isna(current_course_type) or current_course_type == '':
        return 0

    race_results = horse_data.get('race_results', [])
    if not race_results:
        return 0

    # 同じコースタイプでの成績を集計
    same_course_ranks = []
    for race in race_results[:5]:
        if isinstance(race, dict):
            past_course = race.get('course_type')
            past_rank = pd.to_numeric(race.get('rank'), errors='coerce')

            if past_course == current_course_type and pd.notna(past_rank):
                same_course_ranks.append(past_rank)

    if not same_course_ranks:
        return 0

    # 平均着順からスコアを計算
    avg_rank = sum(same_course_ranks) / len(same_course_ranks)

    if avg_rank <= 2:
        return 15
    elif avg_rank <= 3:
        return 10
    elif avg_rank <= 5:
        return 5
    elif avg_rank > 8:
        return -10

    return 0

def calculate_track_fitness(horse_data, current_track_name):
    """
    競馬場適性を評価
    """
    if pd.isna(current_track_name) or current_track_name == '':
        return 0

    race_results = horse_data.get('race_results', [])
    if not race_results:
        return 0

    # 同じ競馬場での成績を集計
    same_track_ranks = []
    for race in race_results[:5]:
        if isinstance(race, dict):
            past_track = race.get('track_name')
            past_rank = pd.to_numeric(race.get('rank'), errors='coerce')

            if past_track == current_track_name and pd.notna(past_rank):
                same_track_ranks.append(past_rank)

    if len(same_track_ranks) < 2:  # 最低2回以上の実績が必要
        return 0

    # 平均着順からスコアを計算
    avg_rank = sum(same_track_ranks) / len(same_track_ranks)

    if avg_rank <= 2:
        return 12
    elif avg_rank <= 3:
        return 8
    elif avg_rank <= 5:
        return 4
    elif avg_rank > 8:
        return -8

    return 0

def calculate_track_condition_fitness(horse_data, current_condition):
    """
    馬場状態適性を評価
    """
    if pd.isna(current_condition) or current_condition == '':
        return 0

    race_results = horse_data.get('race_results', [])
    if not race_results:
        return 0

    # 同じ馬場状態での成績を集計
    same_condition_ranks = []
    for race in race_results[:5]:
        if isinstance(race, dict):
            past_condition = race.get('track_condition')
            past_rank = pd.to_numeric(race.get('rank'), errors='coerce')

            if past_condition == current_condition and pd.notna(past_rank):
                same_condition_ranks.append(past_rank)

    if not same_condition_ranks:
        return 0

    # 平均着順からスコアを計算
    avg_rank = sum(same_condition_ranks) / len(same_condition_ranks)

    if avg_rank <= 2:
        return 8
    elif avg_rank <= 3:
        return 5
    elif avg_rank <= 5:
        return 2
    elif avg_rank > 8:
        return -5

    return 0

def calculate_running_style_fitness(horse_data, race_distance):
    """
    脚質適性を評価
    - 短距離: 逃げ・先行有利
    - 長距離: 差し・追込有利
    """
    race_results = horse_data.get('race_results', [])
    if not race_results:
        return 0

    # 過去レースの脚質を推定
    running_styles = []
    for race in race_results[:3]:
        if isinstance(race, dict):
            passage = race.get('passage')
            style = estimate_running_style(passage)
            if style:
                running_styles.append(style)

    if not running_styles:
        return 0

    # 最も多い脚質を主な脚質とする
    main_style = max(set(running_styles), key=running_styles.count)

    # 距離による適性評価
    distance_num = pd.to_numeric(race_distance, errors='coerce')
    if pd.isna(distance_num):
        return 0

    if distance_num <= 1400:  # 短距離
        if main_style in ["逃げ", "先行"]:
            return 8
        else:
            return -3
    elif distance_num >= 2000:  # 長距離
        if main_style in ["差し", "追込"]:
            return 8
        else:
            return -3
    else:  # 中距離
        if main_style in ["先行", "差し"]:
            return 5
        else:
            return 0

    return 0

def calculate_advanced_score(horse_data, race_conditions, race_date, jockey_stats, trainer_stats):
    """
    高度なスコア計算
    """
    score = 50.0

    # 1. 馬の過去成績（従来通り）
    race_results = horse_data.get('race_results', [])

    if race_results and len(race_results) > 0:
        # 直近3走の平均着順
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

        # 距離適性
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

    # 2. 騎手統計（キャッシュから取得）
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

    # 3. 調教師統計（キャッシュから取得）
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

    # 4. 馬体重変化
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

    # 5. 年齢
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

    # ========================================
    # 新規追加要素
    # ========================================

    # 6. コース適性（芝/ダート）
    course_type = race_conditions.get('CourseType')
    course_score = calculate_course_fitness(horse_data, course_type)
    score += course_score

    # 7. 競馬場適性
    track_name = race_conditions.get('TrackName')
    track_score = calculate_track_fitness(horse_data, track_name)
    score += track_score

    # 8. 馬場状態適性
    track_condition = race_conditions.get('TrackCondition')
    condition_score = calculate_track_condition_fitness(horse_data, track_condition)
    score += condition_score

    # 9. 脚質適性
    running_style_score = calculate_running_style_fitness(horse_data, race_conditions.get('Distance'))
    score += running_style_score

    return max(0, score)

print("=" * 80)
print("高度なスコアリングシステムのバックテスト")
print("=" * 80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 騎手・調教師の統計を事前計算
jockey_stats, trainer_stats = precalculate_stats(df, target_year=2024)

# 2024年のデータでテスト
target_races = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"\n対象: 2024年 {len(race_ids)}レース")

# 結果集計用
results = {
    'total': 0,
    'umaren_hit': 0,
    'umaren_return': 0,
    'umaren_cost': 0,
}

for idx, race_id in enumerate(race_ids):
    if (idx + 1) % 500 == 0:
        print(f"  {idx + 1}/{len(race_ids)} レース処理中...")

    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    # 馬番順にソート（データリーケージ防止）
    race_horses = race_horses.sort_values('Umaban')

    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue

    race_date_str = str(race_date)[:10]

    # レース条件を取得
    race_course_type = race_horses.iloc[0].get('course_type')
    race_track_name = race_horses.iloc[0].get('track_name')
    race_track_condition = race_horses.iloc[0].get('track_condition')
    race_distance = race_horses.iloc[0].get('distance')

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
            'Distance': race_distance,
            'CourseType': race_course_type,
            'TrackCondition': race_track_condition,
            'TrackName': race_track_name
        }

        # 高度なスコア計算
        score = calculate_advanced_score(horse_data, race_conditions, race_date_str, jockey_stats, trainer_stats)

        horses_scores.append({
            'umaban': int(horse.get('Umaban', 0)),
            'score': score
        })

    # スコア順にソート
    horses_scores.sort(key=lambda x: x['score'], reverse=True)

    top3 = [h['umaban'] for h in horses_scores[:3]]

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data:
        continue

    results['total'] += 1

    # 馬連
    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_pairs = umaren_data.get('馬番', [])
        payouts = umaren_data.get('払戻金', [])

        if winning_pairs and len(winning_pairs) >= 2:
            try:
                winning_pair = set([int(x) for x in winning_pairs[:2]])
                umaren_pairs = list(combinations(top3, 2))

                results['umaren_cost'] += len(umaren_pairs) * 100

                hit_found = False
                for pair in umaren_pairs:
                    if set(pair) == winning_pair:
                        hit_found = True
                        break

                if hit_found:
                    results['umaren_hit'] += 1
                    results['umaren_return'] += payouts[0]
            except:
                pass

# 結果出力
print("\n" + "=" * 80)
print("【高度なスコアリングの結果】2024年")
print("=" * 80)

print(f"\n総レース数: {results['total']:,}レース")

if results['umaren_cost'] > 0:
    umaren_recovery = (results['umaren_return'] / results['umaren_cost']) * 100
    print(f"\n【馬連】3頭BOX")
    print(f"  的中: {results['umaren_hit']:,}回 / {results['total']:,}レース")
    print(f"  的中率: {results['umaren_hit']/results['total']*100:.2f}%")
    print(f"  投資額: {results['umaren_cost']:,}円")
    print(f"  払戻額: {results['umaren_return']:,}円")
    print(f"  回収率: {umaren_recovery:.2f}%")
    print(f"  損益: {results['umaren_return'] - results['umaren_cost']:+,}円")

print("\n" + "=" * 80)
print("【手法の比較】")
print("=" * 80)

print("\n従来手法（過去成績のみ）:")
print("  的中率: 17.3%")
print("  回収率: 64.6%")
print("  損益: -356,250円")

print("\n改善版（騎手・調教師追加）:")
print("  的中率: 20.31%")
print("  回収率: 68.62%")
print("  損益: -316,170円")

if results['total'] > 0 and results['umaren_cost'] > 0:
    print(f"\n高度版（コース・馬場・脚質追加）:")
    print(f"  的中率: {results['umaren_hit']/results['total']*100:.2f}%")
    print(f"  回収率: {umaren_recovery:.2f}%")
    print(f"  損益: {results['umaren_return'] - results['umaren_cost']:+,}円")

    print(f"\n【従来手法からの改善度】")
    hit_rate_diff = (results['umaren_hit']/results['total']*100) - 17.3
    recovery_diff = umaren_recovery - 64.6
    profit_diff = (results['umaren_return'] - results['umaren_cost']) - (-356250)

    print(f"  的中率: {hit_rate_diff:+.2f}ポイント")
    print(f"  回収率: {recovery_diff:+.2f}ポイント")
    print(f"  損益: {profit_diff:+,}円")

print("\n" + "=" * 80)
print("バックテスト完了")
print("=" * 80)
