"""
全サンプルレースを検証
"""
import pandas as pd
import json
import sys
from itertools import combinations
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from improved_analyzer import ImprovedHorseAnalyzer
from prediction_integration import get_horse_past_results_from_csv

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

# データ読み込み
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv", encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

df['race_id_str'] = df['race_id'].astype(str)
target_races = df[
    df['race_id_str'].str.startswith('202506') |
    df['race_id_str'].str.startswith('202507') |
    df['race_id_str'].str.startswith('202508')
]
race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

import random
random.seed(42)
sample_race_ids = random.sample(list(race_ids), min(5, len(race_ids)))

print("=" * 80)
print("ALL 5 SAMPLE RACES VERIFICATION")
print("=" * 80)

analyzer = ImprovedHorseAnalyzer()
hits = 0
misses = 0

for idx, race_id in enumerate(sample_race_ids, 1):
    race_horses = df[df['race_id'] == race_id].copy()

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
            'Odds': odds, 'Ninki': horse.get('Ninki'), 'Age': horse.get('Age'),
            'Sex': horse.get('Sex'), 'Load': horse.get('Load'), 'Waku': horse.get('Waku'),
            'HorseName': horse.get('HorseName'), 'race_results': past_results
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
            'composite_score': ai_prediction * 0.6 + max(0, divergence_info['divergence']) * 2 * 0.4
        })

    horses_with_marks = analyzer.assign_marks_and_confidence(horses_predictions)

    honmei = next((h for h in horses_with_marks if h.get('mark') == '◎'), None)
    taikou = next((h for h in horses_with_marks if h.get('mark') == '○'), None)
    ana = next((h for h in horses_with_marks if h.get('mark') == '▲'), None)
    renge = next((h for h in horses_with_marks if h.get('mark') == '△'), None)
    hoshi = next((h for h in horses_with_marks if h.get('mark') == '☆'), None)

    if not (honmei and taikou and ana and renge and hoshi):
        print(f"\nRace {idx}: {race_id} - SKIPPED (incomplete predictions)")
        continue

    predicted_horses = [honmei['umaban'], taikou['umaban'], ana['umaban'], renge['umaban'], hoshi['umaban']]

    # Get actual result
    results = race_horses[['Umaban', 'Rank']].sort_values('Rank')
    top3 = results.head(3)['Umaban'].tolist()

    # Get payout
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})
    umaren_data = payout_data.get('馬連', {})
    winning_pairs = umaren_data.get('馬番', [])
    payouts = umaren_data.get('払戻金', [])

    print(f"\nRace {idx}: {race_id}")
    print(f"  Top 3: {top3}")
    print(f"  Prediction: {predicted_horses}")

    if winning_pairs:
        try:
            winning_pair = set([int(x) for x in winning_pairs[:2]])
            umaren_pairs = list(combinations(predicted_horses, 2))

            hit_found = False
            for pair in umaren_pairs:
                if set(pair) == winning_pair:
                    hit_found = True
                    break

            if hit_found:
                print(f"  Umaren: {list(winning_pair)} -> [HIT] {payouts[0] if payouts else 0} yen")
                hits += 1
            else:
                print(f"  Umaren: {list(winning_pair)} -> [MISS]")
                in_pred = [w for w in winning_pair if w in predicted_horses]
                print(f"    In prediction: {in_pred} / 2")
                misses += 1
        except Exception as e:
            print(f"  Error: {e}")
    else:
        print(f"  No payout data")

print(f"\n" + "=" * 80)
print(f"SUMMARY: {hits} hits, {misses} misses ({hits}/{hits+misses} = {hits/(hits+misses)*100:.1f}%)")
print("=" * 80)
