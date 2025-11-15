"""
詳細な予測結果表示（レースごと）
実際に的中したのか、外れたのかを明確に表示
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

# 2025年6-8月を正しく抽出
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
target_races = df[
    (df['date_parsed'] >= '2025-06-01') &
    (df['date_parsed'] <= '2025-08-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print("=" * 80)
print("詳細予測結果表示（サンプル20レース）")
print("=" * 80)

# 最初の20レースを表示
for idx, race_id in enumerate(race_ids[:20]):
    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue

    race_date_str = str(race_date)[:10]

    # レース情報
    first_row = race_horses.iloc[0]
    track_name = first_row.get('track_name', '')
    race_name = first_row.get('race_name', '')

    print(f"\n{'=' * 80}")
    print(f"#{idx+1}: レースID {race_id}")
    print(f"日付: {race_date_str} | {track_name} | {race_name}")
    print("=" * 80)

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
            'name': horse.get('HorseName', ''),
            'score': score,
            'actual_rank': horse.get('Rank')
        })

    # スコア順にソート
    horses_scores.sort(key=lambda x: x['score'], reverse=True)

    top3 = [h['umaban'] for h in horses_scores[:3]]
    top5 = [h['umaban'] for h in horses_scores[:5]]

    # 予測表示
    print("\n【予測】")
    print(f"  ◎○▲: {top3}")
    print(f"  Top5: {top5}")

    # 実際の結果
    print("\n【実際の結果】")
    actual_top3_horses = race_horses.sort_values('Rank').head(3)
    actual_top3 = []
    for _, horse in actual_top3_horses.iterrows():
        umaban = int(horse['Umaban'])
        rank = horse['Rank']
        name = horse['HorseName']
        actual_top3.append(umaban)
        print(f"  {rank}着: {umaban:>2}番 {name}")

    # 配当取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    # 的中判定
    print("\n【的中判定】")

    # 馬連
    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_pairs = umaren_data.get('馬番', [])
        payouts = umaren_data.get('払戻金', [])

        if winning_pairs and len(winning_pairs) >= 2:
            try:
                winning_pair = set([int(x) for x in winning_pairs[:2]])

                # 3頭BOX判定
                hit_3box = all(num in top3 for num in winning_pair)
                # 5頭BOX判定
                hit_5box = all(num in top5 for num in winning_pair)

                payout = payouts[0] if payouts else 0
                print(f"  馬連: {sorted(winning_pair)} → {payout:,}円")

                if hit_3box:
                    print(f"    → [的中] 3頭BOX")
                elif hit_5box:
                    print(f"    → [的中] 5頭BOX")
                else:
                    print(f"    → [不的中]")
            except:
                pass

    # 3連複
    if '3連複' in payout_data:
        sanrenpuku_data = payout_data['3連複']
        winning_trio = sanrenpuku_data.get('馬番', [])
        payouts = sanrenpuku_data.get('払戻金', [])

        if winning_trio and len(winning_trio) >= 3:
            try:
                winning_set = set([int(x) for x in winning_trio[:3]])

                # 3頭BOX判定
                hit_3box = (winning_set == set(top3))
                # 5頭BOX判定
                hit_5box = all(num in top5 for num in winning_set)

                payout = payouts[0] if payouts else 0
                print(f"  3連複: {sorted(winning_set)} → {payout:,}円")

                if hit_3box:
                    print(f"    → [的中] 3頭BOX")
                elif hit_5box:
                    print(f"    → [的中] 5頭BOX")
                else:
                    print(f"    → [不的中]")
            except:
                pass

print("\n" + "=" * 80)
print("サンプル20レース表示完了")
print("=" * 80)
