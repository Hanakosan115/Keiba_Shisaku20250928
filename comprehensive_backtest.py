"""
包括的バックテスト - 全期間・年ごとの詳細分析
"""
import pandas as pd
import json
import sys
from itertools import combinations
from collections import defaultdict
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
            import numpy as np
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

print("=" * 80)
print("包括的バックテスト - 全期間分析")
print("=" * 80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 年ごとの範囲を定義
years = [
    ('2020年', '2020-01-01', '2020-12-31'),
    ('2021年', '2021-01-01', '2021-12-31'),
    ('2022年', '2022-01-01', '2022-12-31'),
    ('2023年', '2023-01-01', '2023-12-31'),
    ('2024年', '2024-01-01', '2024-12-31'),
    ('2025年(1-8月)', '2025-01-01', '2025-08-31'),
]

all_results = {}

for year_name, start_date, end_date in years:
    print(f"\n処理中: {year_name}")

    target_races = df[
        (df['date_parsed'] >= start_date) &
        (df['date_parsed'] <= end_date)
    ]

    race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

    if len(race_ids) == 0:
        print(f"  → データなし")
        continue

    print(f"  対象レース: {len(race_ids)}レース")

    # 結果集計用
    results = {
        '3box': {
            'total': 0,
            'umaren_hit': 0, 'umaren_return': 0, 'umaren_cost': 0,
            'umatan_hit': 0, 'umatan_return': 0, 'umatan_cost': 0,
            'wide_hit': 0, 'wide_return': 0, 'wide_cost': 0,
            'sanrenpuku_hit': 0, 'sanrenpuku_return': 0, 'sanrenpuku_cost': 0,
            'sanrentan_hit': 0, 'sanrentan_return': 0, 'sanrentan_cost': 0,
        }
    }

    for idx, race_id in enumerate(race_ids):
        if (idx + 1) % 500 == 0:
            print(f"    {idx + 1}/{len(race_ids)} レース処理中...")

        race_horses = df[df['race_id'] == race_id].copy()

        if len(race_horses) < 8:
            continue

        race_date = race_horses.iloc[0]['date']
        if pd.isna(race_date):
            continue

        race_date_str = str(race_date)[:10]

        # 予測実行
        horses_scores = []

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

            horses_scores.append({
                'umaban': int(horse.get('Umaban', 0)),
                'score': score
            })

        horses_scores.sort(key=lambda x: x['score'], reverse=True)

        top3 = [h['umaban'] for h in horses_scores[:3]]

        # 配当データ取得
        race_id_str = str(race_id)
        payout_data = payout_dict.get(race_id_str, {})

        if not payout_data:
            continue

        results['3box']['total'] += 1

        # 馬連
        if '馬連' in payout_data:
            umaren_data = payout_data['馬連']
            winning_pairs = umaren_data.get('馬番', [])
            payouts = umaren_data.get('払戻金', [])

            if winning_pairs and len(winning_pairs) >= 2:
                try:
                    winning_pair = set([int(x) for x in winning_pairs[:2]])
                    umaren_pairs = list(combinations(top3, 2))

                    results['3box']['umaren_cost'] += len(umaren_pairs) * 100

                    hit_found = False
                    for pair in umaren_pairs:
                        if set(pair) == winning_pair:
                            hit_found = True
                            break

                    if hit_found:
                        results['3box']['umaren_hit'] += 1
                        results['3box']['umaren_return'] += payouts[0]
                except:
                    pass

        # 馬単
        if '馬単' in payout_data:
            umatan_data = payout_data['馬単']
            winning_pairs = umatan_data.get('馬番', [])
            payouts = umatan_data.get('払戻金', [])

            if winning_pairs and len(winning_pairs) >= 2:
                try:
                    winning_pair = [int(x) for x in winning_pairs[:2]]

                    # 馬単は順序あり
                    from itertools import permutations
                    umatan_pairs = list(permutations(top3, 2))

                    results['3box']['umatan_cost'] += len(umatan_pairs) * 100

                    hit_found = False
                    for pair in umatan_pairs:
                        if list(pair) == winning_pair:
                            hit_found = True
                            break

                    if hit_found:
                        results['3box']['umatan_hit'] += 1
                        results['3box']['umatan_return'] += payouts[0]
                except:
                    pass

        # ワイド
        if 'ワイド' in payout_data:
            wide_data = payout_data['ワイド']
            winning_pairs_list = wide_data.get('馬番', [])
            payouts = wide_data.get('払戻金', [])

            umaren_pairs = list(combinations(top3, 2))
            results['3box']['wide_cost'] += len(umaren_pairs) * 100

            # ワイドは複数組合せがある場合がある
            total_wide_payout = 0
            for i, winning_pair_str in enumerate(winning_pairs_list):
                try:
                    if isinstance(winning_pair_str, list):
                        winning_pair = set([int(x) for x in winning_pair_str])
                    else:
                        # "1-2" のような文字列の場合
                        winning_pair = set([int(x) for x in str(winning_pair_str).split('-')])

                    for pair in umaren_pairs:
                        if set(pair) == winning_pair:
                            results['3box']['wide_hit'] += 1
                            if i < len(payouts):
                                total_wide_payout += payouts[i]
                            break
                except:
                    pass

            results['3box']['wide_return'] += total_wide_payout

        # 3連複
        if '3連複' in payout_data:
            sanrenpuku_data = payout_data['3連複']
            winning_trio = sanrenpuku_data.get('馬番', [])
            payouts = sanrenpuku_data.get('払戻金', [])

            if winning_trio and len(winning_trio) >= 3:
                try:
                    winning_set = set([int(x) for x in winning_trio[:3]])

                    results['3box']['sanrenpuku_cost'] += 100

                    if winning_set == set(top3):
                        results['3box']['sanrenpuku_hit'] += 1
                        results['3box']['sanrenpuku_return'] += payouts[0]
                except:
                    pass

        # 3連単
        if '3連単' in payout_data:
            sanrentan_data = payout_data['3連単']
            winning_trio = sanrentan_data.get('馬番', [])
            payouts = sanrentan_data.get('払戻金', [])

            if winning_trio and len(winning_trio) >= 3:
                try:
                    winning_order = [int(x) for x in winning_trio[:3]]

                    # 3連単は順序あり
                    from itertools import permutations
                    sanrentan_perms = list(permutations(top3, 3))

                    results['3box']['sanrentan_cost'] += len(sanrentan_perms) * 100

                    hit_found = False
                    for perm in sanrentan_perms:
                        if list(perm) == winning_order:
                            hit_found = True
                            break

                    if hit_found:
                        results['3box']['sanrentan_hit'] += 1
                        results['3box']['sanrentan_return'] += payouts[0]
                except:
                    pass

    all_results[year_name] = results

# 全期間の合計
print("\n" + "=" * 80)
print("全期間の結果を集計中...")
print("=" * 80)

total_results = {
    'total': 0,
    'umaren_hit': 0, 'umaren_return': 0, 'umaren_cost': 0,
    'umatan_hit': 0, 'umatan_return': 0, 'umatan_cost': 0,
    'wide_hit': 0, 'wide_return': 0, 'wide_cost': 0,
    'sanrenpuku_hit': 0, 'sanrenpuku_return': 0, 'sanrenpuku_cost': 0,
    'sanrentan_hit': 0, 'sanrentan_return': 0, 'sanrentan_cost': 0,
}

for year_name, res in all_results.items():
    r = res['3box']
    total_results['total'] += r['total']
    total_results['umaren_hit'] += r['umaren_hit']
    total_results['umaren_return'] += r['umaren_return']
    total_results['umaren_cost'] += r['umaren_cost']
    total_results['umatan_hit'] += r['umatan_hit']
    total_results['umatan_return'] += r['umatan_return']
    total_results['umatan_cost'] += r['umatan_cost']
    total_results['wide_hit'] += r['wide_hit']
    total_results['wide_return'] += r['wide_return']
    total_results['wide_cost'] += r['wide_cost']
    total_results['sanrenpuku_hit'] += r['sanrenpuku_hit']
    total_results['sanrenpuku_return'] += r['sanrenpuku_return']
    total_results['sanrenpuku_cost'] += r['sanrenpuku_cost']
    total_results['sanrentan_hit'] += r['sanrentan_hit']
    total_results['sanrentan_return'] += r['sanrentan_return']
    total_results['sanrentan_cost'] += r['sanrentan_cost']

# 結果出力
print("\n" + "=" * 80)
print("【全期間合計】")
print("=" * 80)
print(f"総レース数: {total_results['total']:,}レース")
print(f"期間: 2020年1月 ～ 2025年8月")

print("\n" + "-" * 80)
print("各券種の成績:")
print("-" * 80)

# 馬連
if total_results['umaren_cost'] > 0:
    umaren_recovery = (total_results['umaren_return'] / total_results['umaren_cost']) * 100
    print(f"\n【馬連】3頭BOX")
    print(f"  的中: {total_results['umaren_hit']:,}回 / {total_results['total']:,}レース")
    print(f"  的中率: {total_results['umaren_hit']/total_results['total']*100:.2f}%")
    print(f"  投資額: {total_results['umaren_cost']:,}円")
    print(f"  払戻額: {total_results['umaren_return']:,}円")
    print(f"  回収率: {umaren_recovery:.2f}%")
    print(f"  損益: {total_results['umaren_return'] - total_results['umaren_cost']:+,}円")

# 馬単
if total_results['umatan_cost'] > 0:
    umatan_recovery = (total_results['umatan_return'] / total_results['umatan_cost']) * 100
    print(f"\n【馬単】3頭BOX")
    print(f"  的中: {total_results['umatan_hit']:,}回 / {total_results['total']:,}レース")
    print(f"  的中率: {total_results['umatan_hit']/total_results['total']*100:.2f}%")
    print(f"  投資額: {total_results['umatan_cost']:,}円")
    print(f"  払戻額: {total_results['umatan_return']:,}円")
    print(f"  回収率: {umatan_recovery:.2f}%")
    print(f"  損益: {total_results['umatan_return'] - total_results['umatan_cost']:+,}円")

# ワイド
if total_results['wide_cost'] > 0:
    wide_recovery = (total_results['wide_return'] / total_results['wide_cost']) * 100
    print(f"\n【ワイド】3頭BOX")
    print(f"  的中: {total_results['wide_hit']:,}回")
    print(f"  的中率: {total_results['wide_hit']/(total_results['total']*3)*100:.2f}% (組合せベース)")
    print(f"  投資額: {total_results['wide_cost']:,}円")
    print(f"  払戻額: {total_results['wide_return']:,}円")
    print(f"  回収率: {wide_recovery:.2f}%")
    print(f"  損益: {total_results['wide_return'] - total_results['wide_cost']:+,}円")

# 3連複
if total_results['sanrenpuku_cost'] > 0:
    sanrenpuku_recovery = (total_results['sanrenpuku_return'] / total_results['sanrenpuku_cost']) * 100
    print(f"\n【3連複】3頭BOX")
    print(f"  的中: {total_results['sanrenpuku_hit']:,}回 / {total_results['total']:,}レース")
    print(f"  的中率: {total_results['sanrenpuku_hit']/total_results['total']*100:.2f}%")
    print(f"  投資額: {total_results['sanrenpuku_cost']:,}円")
    print(f"  払戻額: {total_results['sanrenpuku_return']:,}円")
    print(f"  回収率: {sanrenpuku_recovery:.2f}%")
    print(f"  損益: {total_results['sanrenpuku_return'] - total_results['sanrenpuku_cost']:+,}円")

# 3連単
if total_results['sanrentan_cost'] > 0:
    sanrentan_recovery = (total_results['sanrentan_return'] / total_results['sanrentan_cost']) * 100
    print(f"\n【3連単】3頭BOX")
    print(f"  的中: {total_results['sanrentan_hit']:,}回 / {total_results['total']:,}レース")
    print(f"  的中率: {total_results['sanrentan_hit']/total_results['total']*100:.2f}%")
    print(f"  投資額: {total_results['sanrentan_cost']:,}円")
    print(f"  払戻額: {total_results['sanrentan_return']:,}円")
    print(f"  回収率: {sanrentan_recovery:.2f}%")
    print(f"  損益: {total_results['sanrentan_return'] - total_results['sanrentan_cost']:+,}円")

# 合算回収率
print("\n" + "=" * 80)
print("【全券種合算】")
print("=" * 80)
total_investment = (total_results['umaren_cost'] + total_results['umatan_cost'] +
                   total_results['wide_cost'] + total_results['sanrenpuku_cost'] +
                   total_results['sanrentan_cost'])
total_payout = (total_results['umaren_return'] + total_results['umatan_return'] +
               total_results['wide_return'] + total_results['sanrenpuku_return'] +
               total_results['sanrentan_return'])

if total_investment > 0:
    combined_recovery = (total_payout / total_investment) * 100
    print(f"総投資額: {total_investment:,}円")
    print(f"総払戻額: {total_payout:,}円")
    print(f"総回収率: {combined_recovery:.2f}%")
    print(f"総損益: {total_payout - total_investment:+,}円")

# 年ごとの結果
print("\n" + "=" * 80)
print("【年ごとの詳細】")
print("=" * 80)

for year_name, res in all_results.items():
    r = res['3box']
    if r['total'] == 0:
        continue

    print(f"\n■ {year_name}")
    print(f"対象レース: {r['total']:,}レース")

    if r['umaren_cost'] > 0:
        print(f"  馬連: 的中率{r['umaren_hit']/r['total']*100:.1f}% 回収率{r['umaren_return']/r['umaren_cost']*100:.1f}%")
    if r['umatan_cost'] > 0:
        print(f"  馬単: 的中率{r['umatan_hit']/r['total']*100:.1f}% 回収率{r['umatan_return']/r['umatan_cost']*100:.1f}%")
    if r['wide_cost'] > 0:
        print(f"  ワイド: 的中{r['wide_hit']}回 回収率{r['wide_return']/r['wide_cost']*100:.1f}%")
    if r['sanrenpuku_cost'] > 0:
        print(f"  3連複: 的中率{r['sanrenpuku_hit']/r['total']*100:.1f}% 回収率{r['sanrenpuku_return']/r['sanrenpuku_cost']*100:.1f}%")
    if r['sanrentan_cost'] > 0:
        print(f"  3連単: 的中率{r['sanrentan_hit']/r['total']*100:.1f}% 回収率{r['sanrentan_return']/r['sanrentan_cost']*100:.1f}%")

    year_total_investment = r['umaren_cost'] + r['umatan_cost'] + r['wide_cost'] + r['sanrenpuku_cost'] + r['sanrentan_cost']
    year_total_payout = r['umaren_return'] + r['umatan_return'] + r['wide_return'] + r['sanrenpuku_return'] + r['sanrentan_return']
    if year_total_investment > 0:
        year_combined_recovery = (year_total_payout / year_total_investment) * 100
        print(f"  【合算】回収率{year_combined_recovery:.1f}% 損益{year_total_payout - year_total_investment:+,}円")

print("\n" + "=" * 80)

# 結果をJSONで保存
import json
output_data = {
    'total': total_results,
    'by_year': all_results
}

with open(r'C:\Users\bu158\Keiba_Shisaku20250928\comprehensive_backtest_results.json', 'w', encoding='utf-8') as f:
    json.dump(output_data, f, ensure_ascii=False, indent=2, default=str)

print("\n結果をJSONファイルに保存しました:")
print("→ comprehensive_backtest_results.json")
