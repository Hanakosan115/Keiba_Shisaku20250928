"""
購入戦略最適化バックテスト
- 改善版スコアリング（騎手・調教師データ）をベース
- 期待値フィルタリング（スコア差）
- オッズ範囲フィルタリング
- レース自信度判定（S/A/B/C）
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
    """改善版スコア計算（騎手・調教師データ追加）"""
    score = 50.0

    # 1. 馬の過去成績
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

    # 2. 騎手統計
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

    # 3. 調教師統計
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

    return max(0, score)

def calculate_race_confidence(horses_scores_with_odds):
    """
    レース自信度を算出
    返り値: "S", "A", "B", "C"
    """
    if len(horses_scores_with_odds) < 4:
        return "C"

    scores = [h['score'] for h in horses_scores_with_odds]

    # スコア差の計算
    score_1st = scores[0]  # 1位
    score_2nd = scores[1]  # 2位
    score_4th = scores[3]  # 4位

    score_diff_1_2 = score_1st - score_2nd  # 1位と2位の差
    score_diff_1_4 = score_1st - score_4th  # 1位と4位の差

    # スコアの標準偏差
    score_std = np.std(scores)

    # TOP3のオッズ
    top3_odds = [h['odds'] for h in horses_scores_with_odds[:3]]
    avg_odds = sum(top3_odds) / 3

    # 自信度判定
    confidence_score = 0

    # 1. スコア差が大きい（明確な強い馬がいる）
    if score_diff_1_2 >= 15:
        confidence_score += 3
    elif score_diff_1_2 >= 10:
        confidence_score += 2
    elif score_diff_1_2 >= 5:
        confidence_score += 1

    if score_diff_1_4 >= 30:
        confidence_score += 2
    elif score_diff_1_4 >= 20:
        confidence_score += 1

    # 2. スコアの分布が明確（混戦でない）
    if score_std >= 15:
        confidence_score += 2
    elif score_std >= 10:
        confidence_score += 1

    # 3. オッズが適正範囲（中穴～穴）
    if 3.0 <= avg_odds <= 10.0:
        confidence_score += 3
    elif 2.0 <= avg_odds <= 15.0:
        confidence_score += 2
    elif avg_odds < 2.0:
        confidence_score -= 1  # 本命すぎる

    # 自信度ランク決定
    if confidence_score >= 8:
        return "S"
    elif confidence_score >= 5:
        return "A"
    elif confidence_score >= 3:
        return "B"
    else:
        return "C"

print("=" * 80)
print("購入戦略最適化バックテスト")
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

# 結果集計用（自信度別）
results_by_confidence = {
    'S': {'total': 0, 'umaren_hit': 0, 'umaren_return': 0, 'umaren_cost': 0},
    'A': {'total': 0, 'umaren_hit': 0, 'umaren_return': 0, 'umaren_cost': 0},
    'B': {'total': 0, 'umaren_hit': 0, 'umaren_return': 0, 'umaren_cost': 0},
    'C': {'total': 0, 'umaren_hit': 0, 'umaren_return': 0, 'umaren_cost': 0}
}

# 戦略別結果（購入フィルタリング）
strategy_results = {
    'all': {'total': 0, 'umaren_hit': 0, 'umaren_return': 0, 'umaren_cost': 0},
    'S_only': {'total': 0, 'umaren_hit': 0, 'umaren_return': 0, 'umaren_cost': 0},
    'S_A': {'total': 0, 'umaren_hit': 0, 'umaren_return': 0, 'umaren_cost': 0},
    'S_A_B': {'total': 0, 'umaren_hit': 0, 'umaren_return': 0, 'umaren_cost': 0}
}

for idx, race_id in enumerate(race_ids):
    if (idx + 1) % 500 == 0:
        print(f"  {idx + 1}/{len(race_ids)} レース処理中...")

    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    # 馬番順にソート
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
        actual_odds = pd.to_numeric(horse.get('Odds_x'), errors='coerce')

        horses_scores.append({
            'umaban': int(horse.get('Umaban', 0)),
            'score': score,
            'odds': actual_odds if pd.notna(actual_odds) else 999.9
        })

    # スコア順にソート
    horses_scores.sort(key=lambda x: x['score'], reverse=True)

    # レース自信度を算出
    confidence = calculate_race_confidence(horses_scores)

    top3 = [h['umaban'] for h in horses_scores[:3]]

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data:
        continue

    # 馬連判定
    hit_found = False
    payout_amount = 0

    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_pairs = umaren_data.get('馬番', [])
        payouts = umaren_data.get('払戻金', [])

        if winning_pairs and len(winning_pairs) >= 2:
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

    # 自信度別に集計
    results_by_confidence[confidence]['total'] += 1
    results_by_confidence[confidence]['umaren_cost'] += 3 * 100  # 3点

    if hit_found and payout_amount:
        results_by_confidence[confidence]['umaren_hit'] += 1
        results_by_confidence[confidence]['umaren_return'] += payout_amount

    # 戦略別に集計（全レース）
    strategy_results['all']['total'] += 1
    strategy_results['all']['umaren_cost'] += 3 * 100

    if hit_found and payout_amount:
        strategy_results['all']['umaren_hit'] += 1
        strategy_results['all']['umaren_return'] += payout_amount

    # S のみ購入
    if confidence == 'S':
        strategy_results['S_only']['total'] += 1
        strategy_results['S_only']['umaren_cost'] += 3 * 100

        if hit_found and payout_amount:
            strategy_results['S_only']['umaren_hit'] += 1
            strategy_results['S_only']['umaren_return'] += payout_amount

    # S+A 購入
    if confidence in ['S', 'A']:
        strategy_results['S_A']['total'] += 1
        strategy_results['S_A']['umaren_cost'] += 3 * 100

        if hit_found and payout_amount:
            strategy_results['S_A']['umaren_hit'] += 1
            strategy_results['S_A']['umaren_return'] += payout_amount

    # S+A+B 購入
    if confidence in ['S', 'A', 'B']:
        strategy_results['S_A_B']['total'] += 1
        strategy_results['S_A_B']['umaren_cost'] += 3 * 100

        if hit_found and payout_amount:
            strategy_results['S_A_B']['umaren_hit'] += 1
            strategy_results['S_A_B']['umaren_return'] += payout_amount

# 結果出力
print("\n" + "=" * 80)
print("【自信度別の結果】2024年")
print("=" * 80)

print("\n自信度 | レース数 | 的中数 | 的中率 | 投資額 | 払戻額 | 回収率 | 損益")
print("-" * 80)

for conf in ['S', 'A', 'B', 'C']:
    res = results_by_confidence[conf]

    if res['total'] > 0:
        hit_rate = res['umaren_hit'] / res['total'] * 100
        if res['umaren_cost'] > 0:
            recovery = res['umaren_return'] / res['umaren_cost'] * 100
        else:
            recovery = 0
        profit = res['umaren_return'] - res['umaren_cost']

        print(f"  {conf}  | {res['total']:4d}R | {res['umaren_hit']:4d}回 | {hit_rate:5.1f}% | "
              f"{res['umaren_cost']:8,}円 | {res['umaren_return']:8,}円 | {recovery:6.1f}% | {profit:+9,}円")

print("\n" + "=" * 80)
print("【購入戦略別の結果】")
print("=" * 80)

strategy_names = {
    'all': '全レース購入',
    'S_only': 'S ランクのみ購入',
    'S_A': 'S+A ランク購入',
    'S_A_B': 'S+A+B ランク購入'
}

print("\n戦略 | 購入レース | 的中数 | 的中率 | 投資額 | 払戻額 | 回収率 | 損益")
print("-" * 80)

for strategy in ['all', 'S_only', 'S_A', 'S_A_B']:
    res = strategy_results[strategy]
    name = strategy_names[strategy]

    if res['total'] > 0:
        hit_rate = res['umaren_hit'] / res['total'] * 100
        if res['umaren_cost'] > 0:
            recovery = res['umaren_return'] / res['umaren_cost'] * 100
        else:
            recovery = 0
        profit = res['umaren_return'] - res['umaren_cost']

        print(f"{name:15s} | {res['total']:4d}R | {res['umaren_hit']:4d}回 | {hit_rate:5.1f}% | "
              f"{res['umaren_cost']:8,}円 | {res['umaren_return']:8,}円 | {recovery:6.1f}% | {profit:+9,}円")

print("\n" + "=" * 80)
print("【ベスト戦略の推奨】")
print("=" * 80)

# 最高回収率を探す
best_strategy = None
best_recovery = 0

for strategy, res in strategy_results.items():
    if res['umaren_cost'] > 0:
        recovery = res['umaren_return'] / res['umaren_cost'] * 100
        if recovery > best_recovery:
            best_recovery = recovery
            best_strategy = strategy

if best_strategy:
    print(f"\n最高回収率: {best_recovery:.2f}%")
    print(f"推奨戦略: {strategy_names[best_strategy]}")

    res = strategy_results[best_strategy]
    print(f"\n詳細:")
    print(f"  購入レース: {res['total']}レース (全{len(race_ids)}レース中)")
    print(f"  購入率: {res['total']/len(race_ids)*100:.1f}%")
    print(f"  的中: {res['umaren_hit']}回")
    print(f"  的中率: {res['umaren_hit']/res['total']*100:.1f}%")
    print(f"  投資額: {res['umaren_cost']:,}円")
    print(f"  払戻額: {res['umaren_return']:,}円")
    print(f"  回収率: {best_recovery:.2f}%")
    print(f"  損益: {res['umaren_return'] - res['umaren_cost']:+,}円")

print("\n" + "=" * 80)
print("分析完了")
print("=" * 80)
