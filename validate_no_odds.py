"""
オッズ未使用での予測精度・回収率検証
過去成績と馬の特徴のみで予測
"""
import pandas as pd
import json
import sys
from itertools import combinations, permutations
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

def calculate_horse_score(horse_basic_info, race_conditions):
    """
    過去成績のみで馬のスコアを計算（オッズ不使用）
    """
    score = 50.0  # ベーススコア

    race_results = horse_basic_info.get('race_results', [])

    if not race_results or len(race_results) == 0:
        return 30.0  # 実績なし

    # 1. 直近3走の平均着順
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
                score += 10  # 非常に安定
            elif std <= 2:
                score += 5   # 安定
            elif std >= 5:
                score -= 5   # 不安定

    # 2. 距離適性
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

                    if distance_diff <= 200:  # 同距離圏
                        if past_rank <= 3:
                            distance_fit_score += 15
                        elif past_rank <= 5:
                            distance_fit_score += 5
                        distance_count += 1

        if distance_count > 0:
            score += distance_fit_score / distance_count

    # 3. 馬場・コース適性
    current_condition = race_conditions.get('TrackCondition', '良')
    current_course = race_conditions.get('CourseType', '芝')

    track_fit_score = 0
    track_count = 0

    for race in race_results[:5]:
        if isinstance(race, dict):
            past_condition = race.get('baba', '良')
            past_course = race.get('course_type', '芝')
            past_rank = pd.to_numeric(race.get('rank'), errors='coerce')

            if pd.notna(past_rank):
                # 同じ条件での実績
                if past_condition == current_condition and past_course == current_course:
                    if past_rank <= 3:
                        track_fit_score += 10
                    elif past_rank <= 5:
                        track_fit_score += 3
                    track_count += 1

    if track_count > 0:
        score += track_fit_score / track_count

    # 4. 休養明け減点
    if len(race_results) > 0 and isinstance(race_results[0], dict):
        last_race_date = pd.to_datetime(race_results[0].get('date'), errors='coerce')
        if pd.notna(last_race_date):
            # race_conditionsから現在のレース日を推定
            # ここでは簡易的に実装
            pass  # 休養日数の計算は省略

    return score

def check_umaren_hit(bet_pairs, payout_data):
    if '馬連' not in payout_data:
        return False, 0
    umaren_data = payout_data['馬連']
    winning_pairs = umaren_data.get('馬番', [])
    payouts = umaren_data.get('払戻金', [])
    if not winning_pairs or not payouts:
        return False, 0
    try:
        winning_pair = set([int(x) for x in winning_pairs[:2]])
        for pair in bet_pairs:
            if set(pair) == winning_pair:
                return True, payouts[0]
    except:
        pass
    return False, 0

def check_sanrenpuku_hit(bet_trios, payout_data):
    if '3連複' not in payout_data:
        return False, 0
    sanrenpuku_data = payout_data['3連複']
    winning_trios = sanrenpuku_data.get('馬番', [])
    payouts = sanrenpuku_data.get('払戻金', [])
    if not winning_trios or not payouts:
        return False, 0
    try:
        winning_trio = set([int(x) for x in winning_trios[:3]])
        for trio in bet_trios:
            if set(trio) == winning_trio:
                return True, payouts[0]
    except:
        pass
    return False, 0

def check_sanrentan_hit(bet_trios, payout_data):
    if '3連単' not in payout_data:
        return False, 0
    sanrentan_data = payout_data['3連単']
    winning_trios = sanrentan_data.get('馬番', [])
    payouts = sanrentan_data.get('払戻金', [])
    if not winning_trios or not payouts:
        return False, 0
    try:
        winning_trio = tuple([int(x) for x in winning_trios[:3]])
        for trio in bet_trios:
            if tuple(trio) == winning_trio:
                return True, payouts[0]
    except:
        pass
    return False, 0

def validate_no_odds(csv_path, payout_json_path):
    print("=" * 80)
    print("オッズ未使用での検証（過去成績のみ）")
    print("=" * 80)

    df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
    payout_dict = load_payout_data(payout_json_path)

    df['race_id_str'] = df['race_id'].astype(str)
    target_races = df[
        df['race_id_str'].str.startswith('202506') |
        df['race_id_str'].str.startswith('202507') |
        df['race_id_str'].str.startswith('202508')
    ]
    race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

    print(f"\n検証レース数: {len(race_ids)}レース\n")

    results = {
        'total_races': 0,
        'umaren_3box_invest': 0, 'umaren_3box_return': 0, 'umaren_3box_hits': 0,
        'sanrenpuku_3box_invest': 0, 'sanrenpuku_3box_return': 0, 'sanrenpuku_3box_hits': 0,
        'sanrentan_3box_invest': 0, 'sanrentan_3box_return': 0, 'sanrentan_3box_hits': 0,
        'umaren_5box_invest': 0, 'umaren_5box_return': 0, 'umaren_5box_hits': 0,
        'sanrenpuku_5box_invest': 0, 'sanrenpuku_5box_return': 0, 'sanrenpuku_5box_hits': 0,
        'sanrentan_5box_invest': 0, 'sanrentan_5box_return': 0, 'sanrentan_5box_hits': 0,
    }

    for idx, race_id in enumerate(race_ids):
        if (idx + 1) % 100 == 0:
            print(f"処理中: {idx + 1}/{len(race_ids)} レース")

        race_horses = df[df['race_id'] == race_id].copy()
        if len(race_horses) < 5:
            continue

        horses_scores = []
        for _, horse in race_horses.iterrows():
            horse_id = horse.get('horse_id')
            race_id_str = str(race_id)
            if len(race_id_str) >= 8:
                race_date = f"{race_id_str[0:4]}-{race_id_str[4:6]}-{race_id_str[6:8]}"
            else:
                race_date = horse.get('date')

            past_results = get_horse_past_results_from_csv(horse_id, race_date, max_results=5)

            horse_basic_info = {
                'Age': horse.get('Age'),
                'Sex': horse.get('Sex'),
                'Load': horse.get('Load'),
                'Waku': horse.get('Waku'),
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

        if len(horses_scores) < 5:
            continue

        # スコア順にソート
        horses_scores.sort(key=lambda x: x['score'], reverse=True)

        # 上位3頭と上位5頭
        top3 = [h['umaban'] for h in horses_scores[:3]]
        top5 = [h['umaban'] for h in horses_scores[:5]]

        race_id_str = str(race_id)
        payout_data = payout_dict.get(race_id_str, {})
        if not payout_data:
            continue

        results['total_races'] += 1

        # 3頭BOX
        umaren_3_pairs = list(combinations(top3, 2))
        sanrenpuku_3_trios = list(combinations(top3, 3))
        sanrentan_3_trios = list(permutations(top3, 3))

        results['umaren_3box_invest'] += len(umaren_3_pairs) * 100
        hit, payout = check_umaren_hit(umaren_3_pairs, payout_data)
        if hit and payout:
            results['umaren_3box_return'] += payout
            results['umaren_3box_hits'] += 1

        results['sanrenpuku_3box_invest'] += len(sanrenpuku_3_trios) * 100
        hit, payout = check_sanrenpuku_hit(sanrenpuku_3_trios, payout_data)
        if hit and payout:
            results['sanrenpuku_3box_return'] += payout
            results['sanrenpuku_3box_hits'] += 1

        results['sanrentan_3box_invest'] += len(sanrentan_3_trios) * 100
        hit, payout = check_sanrentan_hit(sanrentan_3_trios, payout_data)
        if hit and payout:
            results['sanrentan_3box_return'] += payout
            results['sanrentan_3box_hits'] += 1

        # 5頭BOX
        umaren_5_pairs = list(combinations(top5, 2))
        sanrenpuku_5_trios = list(combinations(top5, 3))
        sanrentan_5_trios = list(permutations(top5, 3))

        results['umaren_5box_invest'] += len(umaren_5_pairs) * 100
        hit, payout = check_umaren_hit(umaren_5_pairs, payout_data)
        if hit and payout:
            results['umaren_5box_return'] += payout
            results['umaren_5box_hits'] += 1

        results['sanrenpuku_5box_invest'] += len(sanrenpuku_5_trios) * 100
        hit, payout = check_sanrenpuku_hit(sanrenpuku_5_trios, payout_data)
        if hit and payout:
            results['sanrenpuku_5box_return'] += payout
            results['sanrenpuku_5box_hits'] += 1

        results['sanrentan_5box_invest'] += len(sanrentan_5_trios) * 100
        hit, payout = check_sanrentan_hit(sanrentan_5_trios, payout_data)
        if hit and payout:
            results['sanrentan_5box_return'] += payout
            results['sanrentan_5box_hits'] += 1

    # 結果表示
    print("\n" + "=" * 80)
    print("【結果：3頭BOX（過去成績のみ）】")
    print("=" * 80)

    total = results['total_races']

    print(f"\n検証レース数: {total}レース\n")

    print("馬連:")
    print(f"  投資: {results['umaren_3box_invest']:,}円")
    print(f"  払戻: {results['umaren_3box_return']:,}円")
    print(f"  的中: {results['umaren_3box_hits']}回 ({results['umaren_3box_hits']/total*100:.1f}%)")
    recovery = results['umaren_3box_return'] / results['umaren_3box_invest'] * 100 if results['umaren_3box_invest'] > 0 else 0
    print(f"  回収率: {recovery:.1f}%")
    print(f"  損益: {results['umaren_3box_return'] - results['umaren_3box_invest']:+,}円")

    print("\n3連複:")
    print(f"  投資: {results['sanrenpuku_3box_invest']:,}円")
    print(f"  払戻: {results['sanrenpuku_3box_return']:,}円")
    print(f"  的中: {results['sanrenpuku_3box_hits']}回 ({results['sanrenpuku_3box_hits']/total*100:.1f}%)")
    recovery = results['sanrenpuku_3box_return'] / results['sanrenpuku_3box_invest'] * 100 if results['sanrenpuku_3box_invest'] > 0 else 0
    print(f"  回収率: {recovery:.1f}%")
    print(f"  損益: {results['sanrenpuku_3box_return'] - results['sanrenpuku_3box_invest']:+,}円")

    print("\n3連単:")
    print(f"  投資: {results['sanrentan_3box_invest']:,}円")
    print(f"  払戻: {results['sanrentan_3box_return']:,}円")
    print(f"  的中: {results['sanrentan_3box_hits']}回 ({results['sanrentan_3box_hits']/total*100:.1f}%)")
    recovery = results['sanrentan_3box_return'] / results['sanrentan_3box_invest'] * 100 if results['sanrentan_3box_invest'] > 0 else 0
    print(f"  回収率: {recovery:.1f}%")
    print(f"  損益: {results['sanrentan_3box_return'] - results['sanrentan_3box_invest']:+,}円")

    total_3box_invest = results['umaren_3box_invest'] + results['sanrenpuku_3box_invest'] + results['sanrentan_3box_invest']
    total_3box_return = results['umaren_3box_return'] + results['sanrenpuku_3box_return'] + results['sanrentan_3box_return']
    total_3box_recovery = total_3box_return / total_3box_invest * 100 if total_3box_invest > 0 else 0

    print(f"\n【3頭BOX総合】")
    print(f"  総投資: {total_3box_invest:,}円")
    print(f"  総払戻: {total_3box_return:,}円")
    print(f"  総回収率: {total_3box_recovery:.1f}%")
    print(f"  総損益: {total_3box_return - total_3box_invest:+,}円")

    print("\n" + "=" * 80)
    print("【結果：5頭BOX（過去成績のみ）】")
    print("=" * 80)

    print("\n馬連:")
    print(f"  投資: {results['umaren_5box_invest']:,}円")
    print(f"  払戻: {results['umaren_5box_return']:,}円")
    print(f"  的中: {results['umaren_5box_hits']}回 ({results['umaren_5box_hits']/total*100:.1f}%)")
    recovery = results['umaren_5box_return'] / results['umaren_5box_invest'] * 100 if results['umaren_5box_invest'] > 0 else 0
    print(f"  回収率: {recovery:.1f}%")

    print("\n3連複:")
    print(f"  投資: {results['sanrenpuku_5box_invest']:,}円")
    print(f"  払戻: {results['sanrenpuku_5box_return']:,}円")
    print(f"  的中: {results['sanrenpuku_5box_hits']}回 ({results['sanrenpuku_5box_hits']/total*100:.1f}%)")
    recovery = results['sanrenpuku_5box_return'] / results['sanrenpuku_5box_invest'] * 100 if results['sanrenpuku_5box_invest'] > 0 else 0
    print(f"  回収率: {recovery:.1f}%")

    print("\n3連単:")
    print(f"  投資: {results['sanrentan_5box_invest']:,}円")
    print(f"  払戻: {results['sanrentan_5box_return']:,}円")
    print(f"  的中: {results['sanrentan_5box_hits']}回 ({results['sanrentan_5box_hits']/total*100:.1f}%)")
    recovery = results['sanrentan_5box_return'] / results['sanrentan_5box_invest'] * 100 if results['sanrentan_5box_invest'] > 0 else 0
    print(f"  回収率: {recovery:.1f}%")

    total_5box_invest = results['umaren_5box_invest'] + results['sanrenpuku_5box_invest'] + results['sanrentan_5box_invest']
    total_5box_return = results['umaren_5box_return'] + results['sanrenpuku_5box_return'] + results['sanrentan_5box_return']
    total_5box_recovery = total_5box_return / total_5box_invest * 100 if total_5box_invest > 0 else 0

    print(f"\n【5頭BOX総合】")
    print(f"  総投資: {total_5box_invest:,}円")
    print(f"  総払戻: {total_5box_return:,}円")
    print(f"  総回収率: {total_5box_recovery:.1f}%")
    print(f"  総損益: {total_5box_return - total_5box_invest:+,}円")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    csv_path = r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv"
    payout_json_path = r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json"

    validate_no_odds(csv_path, payout_json_path)
