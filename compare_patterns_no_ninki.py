"""
全買い方パターンで963レース検証（Ninki未使用版）
"""
import pandas as pd
import json
import sys
from itertools import combinations, permutations
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from improved_analyzer import ImprovedHorseAnalyzer
from prediction_integration import get_horse_past_results_from_csv

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

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

def pattern_a_3box(honmei, taikou, ana):
    horses = [honmei, taikou, ana]
    umaren_pairs = list(combinations(horses, 2))
    sanrenpuku_trios = list(combinations(horses, 3))
    sanrentan_trios = list(permutations(horses, 3))
    return umaren_pairs, sanrenpuku_trios, sanrentan_trios, len(umaren_pairs), len(sanrenpuku_trios), len(sanrentan_trios)

def pattern_b_formation(honmei, taikou, ana, renge, hoshi):
    axis = [honmei, taikou]
    others = [ana, renge, hoshi]
    umaren_pairs = [(a, o) for a in axis for o in others]
    sanrenpuku_trios = [(honmei, taikou, o) for o in others]
    all_others = [taikou] + others
    sanrentan_trios = [(honmei, o1, o2) for o1, o2 in permutations(all_others, 2)]
    return umaren_pairs, sanrenpuku_trios, sanrentan_trios, len(umaren_pairs), len(sanrenpuku_trios), len(sanrentan_trios)

def pattern_c_5box(honmei, taikou, ana, renge, hoshi):
    horses = [honmei, taikou, ana, renge, hoshi]
    umaren_pairs = list(combinations(horses, 2))
    sanrenpuku_trios = list(combinations(horses, 3))
    sanrentan_trios = list(permutations(horses, 3))
    return umaren_pairs, sanrenpuku_trios, sanrentan_trios, len(umaren_pairs), len(sanrenpuku_trios), len(sanrentan_trios)

def pattern_d_honmei_nagashi(honmei, taikou, ana, renge, hoshi):
    others = [taikou, ana, renge, hoshi]
    umaren_pairs = [(honmei, o) for o in others]
    sanrenpuku_trios = [(honmei, o1, o2) for o1, o2 in combinations(others, 2)]
    sanrentan_trios = [(honmei, o1, o2) for o1, o2 in permutations(others, 2)]
    return umaren_pairs, sanrenpuku_trios, sanrentan_trios, len(umaren_pairs), len(sanrenpuku_trios), len(sanrentan_trios)

def pattern_e_top2_nagashi(honmei, taikou, ana, renge, hoshi):
    axis = [honmei, taikou]
    others = [ana, renge, hoshi]
    umaren_pairs = [(a, o) for a in axis for o in others]
    sanrenpuku_trios = [(a1, a2, o) for a1, a2 in combinations(axis, 2) for o in others]
    all_candidates = axis + others
    sanrentan_trios = []
    for first in axis:
        remaining = [h for h in all_candidates if h != first]
        sanrentan_trios.extend([(first, o1, o2) for o1, o2 in permutations(remaining, 2)])
    return umaren_pairs, sanrenpuku_trios, sanrentan_trios, len(umaren_pairs), len(sanrenpuku_trios), len(sanrentan_trios)

def validate_all_patterns(csv_path, payout_json_path):
    print("=" * 80)
    print("全買い方パターン比較検証【Ninki未使用版】")
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

    analyzer = ImprovedHorseAnalyzer()

    patterns = {
        'A_3BOX': {'name': 'パターンA: 3頭BOX（◎○▲）'},
        'B_FORM': {'name': 'パターンB: フォーメーション（GUI推奨）'},
        'C_5BOX': {'name': 'パターンC: 5頭BOX'},
        'D_HONMEI': {'name': 'パターンD: ◎軸流し'},
        'E_TOP2': {'name': 'パターンE: ◎○軸流し'}
    }

    for p in patterns:
        patterns[p].update({
            'umaren_invest': 0, 'umaren_return': 0, 'umaren_hits': 0,
            'sanrenpuku_invest': 0, 'sanrenpuku_return': 0, 'sanrenpuku_hits': 0,
            'sanrentan_invest': 0, 'sanrentan_return': 0, 'sanrentan_hits': 0
        })

    for idx, race_id in enumerate(race_ids):
        if (idx + 1) % 100 == 0:
            print(f"処理中: {idx + 1}/{len(race_ids)} レース")

        race_horses = df[df['race_id'] == race_id].copy()
        if len(race_horses) < 5:
            continue

        horses_predictions = []
        for _, horse in race_horses.iterrows():
            odds = horse.get('Odds', 1.0)
            if pd.isna(odds) or odds <= 0:
                odds = horse.get('Odds_x', horse.get('Odds_y', 1.0))
            if pd.isna(odds) or odds <= 0:
                odds = 10.0

            horse_id = horse.get('horse_id')
            race_id_str = str(race_id)
            if len(race_id_str) >= 8:
                race_date = f"{race_id_str[0:4]}-{race_id_str[4:6]}-{race_id_str[6:8]}"
            else:
                race_date = horse.get('date')

            past_results = get_horse_past_results_from_csv(horse_id, race_date, max_results=5)

            horse_basic_info = {
                'Odds': odds,
                # Ninkiを削除！
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

            features = analyzer.calculate_simplified_features(horse_basic_info, race_conditions)
            ai_prediction = analyzer.calculate_simple_ai_prediction(features)
            divergence_info = analyzer.calculate_divergence_score(features, ai_prediction)

            horses_predictions.append({
                'umaban': int(horse.get('Umaban', 0)),
                'odds': odds,
                'composite_score': ai_prediction * 0.6 + max(0, divergence_info['divergence']) * 2 * 0.4
            })

        if len(horses_predictions) < 5:
            continue

        # オッズから人気を推定（低い順に1番人気、2番人気...）
        horses_sorted_by_odds = sorted(horses_predictions, key=lambda x: x['odds'])
        for rank, horse in enumerate(horses_sorted_by_odds, 1):
            horse['estimated_popularity'] = rank

        horses_with_marks = analyzer.assign_marks_and_confidence(horses_predictions)

        honmei = next((h for h in horses_with_marks if h.get('mark') == '◎'), None)
        taikou = next((h for h in horses_with_marks if h.get('mark') == '○'), None)
        ana = next((h for h in horses_with_marks if h.get('mark') == '▲'), None)
        renge = next((h for h in horses_with_marks if h.get('mark') == '△'), None)
        hoshi = next((h for h in horses_with_marks if h.get('mark') == '☆'), None)

        if not (honmei and taikou and ana and renge and hoshi):
            continue

        h1, h2, h3, h4, h5 = honmei['umaban'], taikou['umaban'], ana['umaban'], renge['umaban'], hoshi['umaban']

        race_id_str = str(race_id)
        payout_data = payout_dict.get(race_id_str, {})
        if not payout_data:
            continue

        pattern_funcs = {
            'A_3BOX': lambda: pattern_a_3box(h1, h2, h3),
            'B_FORM': lambda: pattern_b_formation(h1, h2, h3, h4, h5),
            'C_5BOX': lambda: pattern_c_5box(h1, h2, h3, h4, h5),
            'D_HONMEI': lambda: pattern_d_honmei_nagashi(h1, h2, h3, h4, h5),
            'E_TOP2': lambda: pattern_e_top2_nagashi(h1, h2, h3, h4, h5)
        }

        for pattern_key, func in pattern_funcs.items():
            umaren_pairs, sanrenpuku_trios, sanrentan_trios, u_cnt, s3_cnt, s1_cnt = func()

            patterns[pattern_key]['umaren_invest'] += u_cnt * 100
            hit, payout = check_umaren_hit(umaren_pairs, payout_data)
            if hit and payout:
                patterns[pattern_key]['umaren_return'] += payout
                patterns[pattern_key]['umaren_hits'] += 1

            patterns[pattern_key]['sanrenpuku_invest'] += s3_cnt * 100
            hit, payout = check_sanrenpuku_hit(sanrenpuku_trios, payout_data)
            if hit and payout:
                patterns[pattern_key]['sanrenpuku_return'] += payout
                patterns[pattern_key]['sanrenpuku_hits'] += 1

            patterns[pattern_key]['sanrentan_invest'] += s1_cnt * 100
            hit, payout = check_sanrentan_hit(sanrentan_trios, payout_data)
            if hit and payout:
                patterns[pattern_key]['sanrentan_return'] += payout
                patterns[pattern_key]['sanrentan_hits'] += 1

    # 結果表示
    print("\n" + "=" * 80)
    print("【検証結果比較 - Ninki未使用版】")
    print("=" * 80)

    total_races = len(race_ids)

    for pattern_key, data in patterns.items():
        print(f"\n{data['name']}")
        print("-" * 80)

        total_invest = data['umaren_invest'] + data['sanrenpuku_invest'] + data['sanrentan_invest']
        total_return = data['umaren_return'] + data['sanrenpuku_return'] + data['sanrentan_return']
        total_profit = total_return - total_invest
        recovery_rate = (total_return / total_invest * 100) if total_invest > 0 else 0

        print(f"  総投資額: {total_invest:,}円 ({total_invest/total_races:.0f}円/レース)")
        print(f"  総払戻額: {total_return:,}円")
        print(f"  総回収率: {recovery_rate:.1f}%")
        print(f"  総損益: {total_profit:+,}円")

        print(f"\n  馬連: 投資{data['umaren_invest']:,}円 → 払戻{data['umaren_return']:,}円")
        print(f"    的中: {data['umaren_hits']}回 ({data['umaren_hits']/total_races*100:.1f}%)")
        print(f"    回収率: {data['umaren_return']/data['umaren_invest']*100 if data['umaren_invest'] > 0 else 0:.1f}%")

        print(f"\n  3連複: 投資{data['sanrenpuku_invest']:,}円 → 払戻{data['sanrenpuku_return']:,}円")
        print(f"    的中: {data['sanrenpuku_hits']}回 ({data['sanrenpuku_hits']/total_races*100:.1f}%)")
        print(f"    回収率: {data['sanrenpuku_return']/data['sanrenpuku_invest']*100 if data['sanrenpuku_invest'] > 0 else 0:.1f}%")

        print(f"\n  3連単: 投資{data['sanrentan_invest']:,}円 → 払戻{data['sanrentan_return']:,}円")
        print(f"    的中: {data['sanrentan_hits']}回 ({data['sanrentan_hits']/total_races*100:.1f}%)")
        print(f"    回収率: {data['sanrentan_return']/data['sanrentan_invest']*100 if data['sanrentan_invest'] > 0 else 0:.1f}%")

    print("\n" + "=" * 80)
    print("【回収率ランキング】")
    print("=" * 80)

    ranking = []
    for pattern_key, data in patterns.items():
        total_invest = data['umaren_invest'] + data['sanrenpuku_invest'] + data['sanrentan_invest']
        total_return = data['umaren_return'] + data['sanrenpuku_return'] + data['sanrentan_return']
        recovery_rate = (total_return / total_invest * 100) if total_invest > 0 else 0
        ranking.append((data['name'], recovery_rate, total_return - total_invest))

    ranking.sort(key=lambda x: x[1], reverse=True)

    for i, (name, rate, profit) in enumerate(ranking, 1):
        print(f"{i}位: {name}")
        print(f"     回収率 {rate:.1f}% | 損益 {profit:+,}円")

if __name__ == "__main__":
    csv_path = r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv"
    payout_json_path = r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json"

    validate_all_patterns(csv_path, payout_json_path)
