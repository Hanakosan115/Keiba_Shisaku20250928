"""
オッズ乖離度を活用したバックテスト
- スコアから期待オッズを計算
- 実際のオッズとの乖離度を算出
- 過小評価されている馬（お買い得馬）を狙う
"""
import pandas as pd
import json
import sys
from itertools import combinations
import numpy as np
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

def calculate_horse_score(horse_basic_info, race_conditions):
    """過去成績のみで馬のスコアを計算"""
    score = 50.0

    race_results = horse_basic_info.get('race_results', [])

    if not race_results or len(race_results) == 0:
        return 30.0

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
            score += 30
        elif avg_rank <= 3:
            score += 20
        elif avg_rank <= 5:
            score += 10
        elif avg_rank <= 8:
            score += 5
        else:
            score -= 10

        if len(recent_ranks) >= 2:
            std = np.std(recent_ranks)
            if std <= 1:
                score += 10
            elif std <= 2:
                score += 5
            elif std >= 5:
                score -= 5

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
                            distance_fit_score += 15
                        elif past_rank <= 5:
                            distance_fit_score += 5
                        distance_count += 1

        if distance_count > 0:
            score += distance_fit_score / distance_count

    return score

def score_to_fair_odds(score, all_scores):
    """
    スコアからフェアオッズを計算
    - レース内の相対的なスコアから勝率を推定
    - 勝率からオッズを計算
    """
    # スコアを確率に変換（ソフトマックス的なアプローチ）
    # より高いスコアには指数的に高い確率を与える
    exp_scores = [np.exp(s / 20.0) for s in all_scores]  # 20で割ってスケール調整
    total_exp = sum(exp_scores)

    probabilities = [exp_s / total_exp for exp_s in exp_scores]

    # 自分のスコアのインデックスを見つける
    score_idx = all_scores.index(score)
    win_prob = probabilities[score_idx]

    # 確率からオッズへ変換（控除率を考慮して0.8掛け）
    if win_prob > 0:
        fair_odds = (1.0 / win_prob) * 0.8  # 控除率20%を想定
    else:
        fair_odds = 999.9

    return max(1.0, fair_odds)  # 最低1.0倍

def calculate_deviation(actual_odds, fair_odds):
    """
    オッズ乖離度を計算
    乖離度 = 実際のオッズ / フェアオッズ

    > 1.0: 過小評価（お買い得）
    < 1.0: 過大評価（人気しすぎ）
    """
    if fair_odds <= 0:
        return 0
    return actual_odds / fair_odds

print("=" * 80)
print("オッズ乖離度を活用したバックテスト")
print("=" * 80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年のデータでテスト
target_races = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"対象: 2024年 {len(race_ids)}レース")

# 複数の乖離度閾値でテスト
deviation_thresholds = [1.0, 1.1, 1.2, 1.3, 1.5, 2.0]
results_by_threshold = {}

for threshold in deviation_thresholds:
    print(f"\n【乖離度閾値: {threshold}】処理中...")

    results = {
        'total': 0,
        'purchased': 0,
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

        # 予測実行
        horses_data = []

        for _, horse in race_horses.iterrows():
            horse_id = horse.get('horse_id')
            past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=5)

            horse_basic_info = {
                'HorseName': horse.get('HorseName'),
                'race_results': past_results
            }

            race_conditions = {
                'Distance': horse.get('distance'),
                'CourseType': horse.get('course_type'),
                'TrackCondition': horse.get('track_condition')
            }

            score = calculate_horse_score(horse_basic_info, race_conditions)
            actual_odds = pd.to_numeric(horse.get('Odds_x'), errors='coerce')

            horses_data.append({
                'umaban': int(horse.get('Umaban', 0)),
                'score': score,
                'actual_odds': actual_odds if pd.notna(actual_odds) else 999.9
            })

        # 全馬のスコアを取得
        all_scores = [h['score'] for h in horses_data]

        # 各馬のフェアオッズと乖離度を計算
        for horse in horses_data:
            fair_odds = score_to_fair_odds(horse['score'], all_scores)
            deviation = calculate_deviation(horse['actual_odds'], fair_odds)

            horse['fair_odds'] = fair_odds
            horse['deviation'] = deviation

        # 乖離度でソート（降順）
        horses_data.sort(key=lambda x: x['deviation'], reverse=True)

        # 乖離度が閾値以上の馬を抽出
        undervalued_horses = [h for h in horses_data if h['deviation'] >= threshold]

        # TOP3を選択（乖離度が高い順）
        if len(undervalued_horses) >= 3:
            top3 = [h['umaban'] for h in undervalued_horses[:3]]
        else:
            # 乖離度が閾値以上の馬が3頭未満の場合はスキップ
            results['total'] += 1
            continue

        results['total'] += 1
        results['purchased'] += 1

        # 配当データ取得
        race_id_str = str(race_id)
        payout_data = payout_dict.get(race_id_str, {})

        if not payout_data:
            continue

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

    results_by_threshold[threshold] = results

# 結果出力
print("\n" + "=" * 80)
print("【結果比較】乖離度閾値別")
print("=" * 80)

print("\n閾値 | 購入率 | 的中数 | 的中率 | 投資額 | 払戻額 | 回収率 | 損益")
print("-" * 80)

for threshold in deviation_thresholds:
    res = results_by_threshold[threshold]

    if res['total'] > 0:
        purchase_rate = res['purchased'] / res['total'] * 100
    else:
        purchase_rate = 0

    if res['purchased'] > 0:
        hit_rate = res['umaren_hit'] / res['purchased'] * 100
    else:
        hit_rate = 0

    if res['umaren_cost'] > 0:
        recovery = res['umaren_return'] / res['umaren_cost'] * 100
    else:
        recovery = 0

    profit = res['umaren_return'] - res['umaren_cost']

    print(f"{threshold:.1f} | {purchase_rate:5.1f}% | {res['umaren_hit']:4d}回 | {hit_rate:5.1f}% | "
          f"{res['umaren_cost']:8,}円 | {res['umaren_return']:8,}円 | {recovery:6.1f}% | {profit:+9,}円")

# ベスト閾値を特定
best_threshold = None
best_recovery = 0

for threshold, res in results_by_threshold.items():
    if res['umaren_cost'] > 0:
        recovery = res['umaren_return'] / res['umaren_cost'] * 100
        if recovery > best_recovery:
            best_recovery = recovery
            best_threshold = threshold

print("\n" + "=" * 80)
print("【ベスト戦略】")
print("=" * 80)

if best_threshold:
    res = results_by_threshold[best_threshold]
    print(f"\n最適な乖離度閾値: {best_threshold}")
    print(f"購入レース数: {res['purchased']}/{res['total']}レース ({res['purchased']/res['total']*100:.1f}%)")
    print(f"的中: {res['umaren_hit']}回")
    print(f"的中率: {res['umaren_hit']/res['purchased']*100:.1f}%")
    print(f"投資額: {res['umaren_cost']:,}円")
    print(f"払戻額: {res['umaren_return']:,}円")
    print(f"回収率: {best_recovery:.1f}%")
    print(f"損益: {res['umaren_return'] - res['umaren_cost']:+,}円")

print("\n" + "=" * 80)
print("【従来手法との比較】")
print("=" * 80)

print("\n従来手法（スコアTOP3を常に購入）:")
print("  回収率: 64.6% （2024年の実績）")
print("  購入率: 100%")

if best_threshold:
    print(f"\nオッズ乖離活用（閾値{best_threshold}）:")
    print(f"  回収率: {best_recovery:.1f}%")
    print(f"  購入率: {res['purchased']/res['total']*100:.1f}%")
    print(f"  改善度: {best_recovery - 64.6:+.1f}ポイント")

print("\n" + "=" * 80)
print("分析完了")
print("=" * 80)
