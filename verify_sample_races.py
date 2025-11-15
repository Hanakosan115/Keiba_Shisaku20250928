"""
サンプルレースで結果を詳細確認
"""
import pandas as pd
import json
import sys
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from improved_analyzer import ImprovedHorseAnalyzer
from prediction_integration import get_horse_past_results_from_csv

# データ読み込み
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv", encoding='utf-8', low_memory=False)

with open(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json", 'r', encoding='utf-8') as f:
    payout_list = json.load(f)

payout_dict = {str(item.get('race_id', '')): item for item in payout_list}

# 6-8月のレースからランダムに5レース抽出
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

analyzer = ImprovedHorseAnalyzer()

print("=" * 80)
print("サンプルレース詳細検証")
print("=" * 80)

for race_id in sample_race_ids:
    print(f"\n{'='*80}")
    print(f"Race ID: {race_id}")
    print('='*80)

    race_horses = df[df['race_id'] == race_id].copy()

    # 実際の結果
    print("\n【実際の結果】")
    results = race_horses[['Umaban', 'HorseName', 'Rank', 'Ninki']].sort_values('Rank')
    print(results.head(3).to_string(index=False))

    # 予測
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
            year = race_id_str[0:4]
            month = race_id_str[4:6]
            day = race_id_str[6:8]
            race_date = f"{year}-{month}-{day}"
        else:
            race_date = horse.get('date')

        past_results = get_horse_past_results_from_csv(horse_id, race_date, max_results=5)

        horse_basic_info = {
            'Odds': odds,
            'Ninki': horse.get('Ninki'),
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
            'horse_name': horse.get('HorseName', ''),
            'odds': odds,
            'ai_prediction': ai_prediction,
            'divergence': divergence_info['divergence'],
            'composite_score': ai_prediction * 0.6 + max(0, divergence_info['divergence']) * 2 * 0.4
        })

    horses_with_marks = analyzer.assign_marks_and_confidence(horses_predictions)

    print("\n【予測】")
    for mark in ['◎', '○', '▲', '△', '☆']:
        horse = next((h for h in horses_with_marks if h.get('mark') == mark), None)
        if horse:
            print(f"{mark} {horse['umaban']}番 {horse['horse_name']}")

    # 予測馬番リスト
    predicted_horses = []
    for mark in ['◎', '○', '▲', '△', '☆']:
        horse = next((h for h in horses_with_marks if h.get('mark') == mark), None)
        if horse:
            predicted_horses.append(horse['umaban'])

    print(f"\n予測馬番: {predicted_horses}")

    # 配当確認
    race_id_str = str(race_id)
    if race_id_str in payout_dict:
        payout_data = payout_dict[race_id_str]

        print("\n【配当】")
        if '馬連' in payout_data:
            umaren = payout_data['馬連']
            print(f"馬連: {umaren['馬番']} → {umaren['払戻金'][0]:,}円")
            # 的中判定
            winning_pair = [int(x) for x in umaren['馬番']]
            if all(num in predicted_horses for num in winning_pair[:2]):
                print("  → ✓ 的中！")
            else:
                print(f"  → × 不的中（予測外: {[n for n in winning_pair[:2] if n not in predicted_horses]}）")

        if '3連複' in payout_data:
            sanrenpuku = payout_data['3連複']
            print(f"3連複: {sanrenpuku['馬番']} → {sanrenpuku['払戻金'][0]:,}円")
            winning_trio = [int(x) for x in sanrenpuku['馬番']]
            if all(num in predicted_horses for num in winning_trio[:3]):
                print("  → ✓ 的中！")
            else:
                print(f"  → × 不的中（予測外: {[n for n in winning_trio[:3] if n not in predicted_horses]}）")

        if '3連単' in payout_data:
            sanrentan = payout_data['3連単']
            print(f"3連単: {sanrentan['馬番']} → {sanrentan['払戻金'][0]:,}円")
            winning_trio = [int(x) for x in sanrentan['馬番']]
            if all(num in predicted_horses for num in winning_trio[:3]):
                print("  → ✓ 的中！")
            else:
                print(f"  → × 不的中（予測外: {[n for n in winning_trio[:3] if n not in predicted_horses]}）")
    else:
        print("\n配当データなし")

print("\n" + "=" * 80)
print("検証完了")
print("=" * 80)
