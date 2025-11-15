"""
特定レースの詳細確認（オッズ未使用版）
"""
import pandas as pd
import json
import sys
from itertools import combinations
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

        # 成績安定性
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

# データ読み込み
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv", encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

# 6-8月のレースから1つ選択
df['race_id_str'] = df['race_id'].astype(str)
target_races = df[
    df['race_id_str'].str.startswith('202506') |
    df['race_id_str'].str.startswith('202507') |
    df['race_id_str'].str.startswith('202508')
]
race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

# 最初のレースを選択
race_id = race_ids[0]

print("=" * 80)
print(f"レース詳細確認: {race_id}")
print("=" * 80)

race_horses = df[df['race_id'] == race_id].copy()

# 実際の結果
print("\n【実際の結果】")
results = race_horses[['Umaban', 'HorseName', 'Rank', 'Ninki', 'Odds']].sort_values('Rank')
print(results.head(5).to_string(index=False))

# 予測実行
horses_scores = []
print("\n【各馬の評価（オッズ未使用）】")
print("-" * 80)

for _, horse in race_horses.iterrows():
    horse_id = horse.get('horse_id')
    race_id_str = str(race_id)
    if len(race_id_str) >= 8:
        race_date = f"{race_id_str[0:4]}-{race_id_str[4:6]}-{race_id_str[6:8]}"
    else:
        race_date = horse.get('date')

    past_results = get_horse_past_results_from_csv(horse_id, race_date, max_results=5)

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

    # 過去成績の要約
    recent_ranks = []
    for race in past_results[:3]:
        if isinstance(race, dict):
            rank = pd.to_numeric(race.get('rank'), errors='coerce')
            if pd.notna(rank):
                recent_ranks.append(int(rank))

    recent_str = '-'.join(map(str, recent_ranks)) if recent_ranks else 'なし'

    horses_scores.append({
        'umaban': int(horse.get('Umaban', 0)),
        'name': horse.get('HorseName', ''),
        'score': score,
        'recent': recent_str,
        'actual_rank': horse.get('Rank'),
        'actual_ninki': horse.get('Ninki'),
        'actual_odds': horse.get('Odds')
    })

    print(f"{horse.get('Umaban'):>2}番 {horse.get('HorseName'):<20} スコア: {score:>5.1f}  近3走: {recent_str:<10}")

# スコア順にソート
horses_scores.sort(key=lambda x: x['score'], reverse=True)

print("\n" + "=" * 80)
print("【予測（スコア順）】")
print("=" * 80)

print("\n◎○▲の予測:")
for i, horse in enumerate(horses_scores[:3]):
    mark = ['◎', '○', '▲'][i]
    print(f"{mark} {horse['umaban']:>2}番 {horse['name']:<20} (スコア: {horse['score']:.1f})")

print("\n上位5頭:")
for i, horse in enumerate(horses_scores[:5], 1):
    print(f"{i}位: {horse['umaban']:>2}番 {horse['name']:<20} (スコア: {horse['score']:.1f})")

# 推奨買い目
top3 = [h['umaban'] for h in horses_scores[:3]]
top5 = [h['umaban'] for h in horses_scores[:5]]

print("\n" + "=" * 80)
print("【推奨買い目】")
print("=" * 80)

print("\n3頭BOX（推奨）:")
print(f"  馬番: {sorted(top3)}")
umaren_3_pairs = list(combinations(top3, 2))
print(f"  馬連: {len(umaren_3_pairs)}点 ({sorted(umaren_3_pairs)})")
print(f"  3連複: 1点 ({sorted(top3)})")
print(f"  3連単: 6点")

print("\n5頭BOX:")
print(f"  馬番: {sorted(top5)}")
print(f"  馬連: 10点")
print(f"  3連複: 10点")
print(f"  3連単: 60点")

# 配当確認
race_id_str = str(race_id)
if race_id_str in payout_dict:
    payout_data = payout_dict[race_id_str]

    print("\n" + "=" * 80)
    print("【実際の配当】")
    print("=" * 80)

    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_pair = [int(x) for x in umaren_data['馬番'][:2]]
        payout = umaren_data['払戻金'][0]
        print(f"\n馬連: {winning_pair} → {payout:,}円")

        # 的中判定
        hit_3box = all(num in top3 for num in winning_pair)
        hit_5box = all(num in top5 for num in winning_pair)

        if hit_3box:
            print(f"  → ✓ 3頭BOXで的中！")
        elif hit_5box:
            print(f"  → ✓ 5頭BOXで的中！")
        else:
            print(f"  → × 不的中")
            missing = [n for n in winning_pair if n not in top5]
            print(f"     予測外の馬番: {missing}")

    if '3連複' in payout_data:
        sanrenpuku_data = payout_data['3連複']
        winning_trio = [int(x) for x in sanrenpuku_data['馬番'][:3]]
        payout = sanrenpuku_data['払戻金'][0]
        print(f"\n3連複: {winning_trio} → {payout:,}円")

        hit_3box = all(num in top3 for num in winning_trio)
        hit_5box = all(num in top5 for num in winning_trio)

        if hit_3box:
            print(f"  → ✓ 3頭BOXで的中！")
        elif hit_5box:
            print(f"  → ✓ 5頭BOXで的中！")
        else:
            print(f"  → × 不的中")

    if '3連単' in payout_data:
        sanrentan_data = payout_data['3連単']
        winning_trio = [int(x) for x in sanrentan_data['馬番'][:3]]
        payout = sanrentan_data['払戻金'][0]
        print(f"\n3連単: {winning_trio} → {payout:,}円")

        hit_3box = all(num in top3 for num in winning_trio)
        hit_5box = all(num in top5 for num in winning_trio)

        if hit_3box:
            print(f"  → ✓ 3頭BOXで的中！（順序は無視）")
        elif hit_5box:
            print(f"  → ✓ 5頭BOXで的中！（順序は無視）")
        else:
            print(f"  → × 不的中")

print("\n" + "=" * 80)
