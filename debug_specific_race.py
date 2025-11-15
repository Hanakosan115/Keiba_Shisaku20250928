"""
特定のレースをデバッグ（サンプル検証と同じrace_id）
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

# サンプル検証と同じ方法でレース選択
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

print("Sample race IDs:", sample_race_ids)
print("=" * 80)

# 2番目のサンプルレース（202507010508）で詳細確認
race_id = sample_race_ids[1]  # Should be 202507010508
print(f"\nDebug race_id: {race_id}")
print("=" * 80)

# レースデータ
race_horses = df[df['race_id'] == race_id].copy()
print(f"\n[Actual Result]")
results = race_horses[['Umaban', 'HorseName', 'Rank', 'Ninki']].sort_values('Rank')
print(results.head(3).to_string(index=False))

# 配当データ確認
race_id_str = str(race_id)
if race_id_str in payout_dict:
    payout_data = payout_dict[race_id_str]
    print(f"\n[Payout Data]")
    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        print(f"Umaren horses: {umaren_data.get('馬番', [])}")
        print(f"Umaren payout: {umaren_data.get('払戻金', [])}")
else:
    print(f"\nNo payout data for race_id: {race_id_str}")
    sys.exit()

# 予測実行
analyzer = ImprovedHorseAnalyzer()
horses_predictions = []

for _, horse in race_horses.iterrows():
    odds = horse.get('Odds', 1.0)
    if pd.isna(odds) or odds <= 0:
        odds = horse.get('Odds_x', horse.get('Odds_y', 1.0))
    if pd.isna(odds) or odds <= 0:
        odds = 10.0

    horse_id = horse.get('horse_id')
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

print(f"\n[Prediction]")
predicted_horses = []
if honmei:
    print(f"1. {honmei['umaban']}")
    predicted_horses.append(honmei['umaban'])
if taikou:
    print(f"2. {taikou['umaban']}")
    predicted_horses.append(taikou['umaban'])
if ana:
    print(f"3. {ana['umaban']}")
    predicted_horses.append(ana['umaban'])
if renge:
    print(f"4. {renge['umaban']}")
    predicted_horses.append(renge['umaban'])
if hoshi:
    print(f"5. {hoshi['umaban']}")
    predicted_horses.append(hoshi['umaban'])

print(f"\nPredicted horses: {predicted_horses}")

# 5頭BOX生成と的中判定
if len(predicted_horses) == 5:
    h1, h2, h3, h4, h5 = predicted_horses
    umaren_pairs = list(combinations(predicted_horses, 2))

    print(f"\n[5-Horse BOX Umaren]")
    print(f"Bet pairs: {len(umaren_pairs)}")

    # 的中判定
    umaren_data = payout_data.get('馬連', {})
    winning_pairs = umaren_data.get('馬番', [])
    payouts = umaren_data.get('払戻金', [])

    if winning_pairs:
        try:
            winning_pair = set([int(x) for x in winning_pairs[:2]])
            print(f"Winning pair: {winning_pair}")

            hit_found = False
            for pair in umaren_pairs:
                if set(pair) == winning_pair:
                    print(f"\n[HIT!] Matched: {pair}")
                    print(f"Payout: {payouts[0] if payouts else 0} yen")
                    hit_found = True
                    break

            if not hit_found:
                print(f"\n[MISS]")
                print(f"Winning horses: {list(winning_pair)}")
                print(f"In prediction: {[w for w in winning_pair if w in predicted_horses]}")
        except Exception as e:
            print(f"\nError: {e}")
else:
    print(f"\nCannot create BOX - only {len(predicted_horses)} horses predicted")
