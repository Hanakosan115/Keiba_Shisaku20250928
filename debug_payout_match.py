"""
配当データと予測の照合をデバッグ
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

# 8月のレースを1つ取得
df['race_id_str'] = df['race_id'].astype(str)
august_races = df[df['race_id_str'].str.startswith('202508')]
race_id = august_races['race_id'].unique()[0]

print(f"デバッグ対象race_id: {race_id}")
print("=" * 60)

# レースデータ
race_horses = df[df['race_id'] == race_id].copy()
print(f"\n出走馬数: {len(race_horses)}")
print(f"馬番と着順:")
print(race_horses[['Umaban', 'HorseName', 'Rank']].to_string())

# 配当データ
race_id_str = str(race_id)
if race_id_str in payout_dict:
    payout_data = payout_dict[race_id_str]
    print(f"\n配当データあり")
    print(f"馬連データ: {payout_data.get('馬連', {})}")
    print(f"3連複データ: {payout_data.get('3連複', {})}")
else:
    print(f"\n配当データなし for race_id: {race_id_str}")
    print(f"payout_dictのキーサンプル: {list(payout_dict.keys())[:5]}")

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
    race_id_str_tmp = str(race_id)
    if len(race_id_str_tmp) >= 8:
        year = race_id_str_tmp[0:4]
        month = race_id_str_tmp[4:6]
        day = race_id_str_tmp[6:8]
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

honmei = next((h for h in horses_with_marks if h.get('mark') == '◎'), None)
taikou = next((h for h in horses_with_marks if h.get('mark') == '○'), None)
ana = next((h for h in horses_with_marks if h.get('mark') == '▲'), None)
renge = next((h for h in horses_with_marks if h.get('mark') == '△'), None)
hoshi = next((h for h in horses_with_marks if h.get('mark') == '☆'), None)

print(f"\n予測:")
if honmei:
    print(f"◎ {honmei['umaban']}番 {honmei['horse_name']}")
if taikou:
    print(f"○ {taikou['umaban']}番 {taikou['horse_name']}")
if ana:
    print(f"▲ {ana['umaban']}番 {ana['horse_name']}")
if renge:
    print(f"△ {renge['umaban']}番 {renge['horse_name']}")
if hoshi:
    print(f"☆ {hoshi['umaban']}番 {hoshi['horse_name']}")

# 馬連フォーメーションチェック
print(f"\n馬連フォーメーション:")
axis_horses = [honmei['umaban']]
if taikou:
    axis_horses.append(taikou['umaban'])
other_horses = []
if ana:
    other_horses.append(ana['umaban'])
if renge:
    other_horses.append(renge['umaban'])
if hoshi:
    other_horses.append(hoshi['umaban'])

print(f"軸: {axis_horses}")
print(f"相手: {other_horses}")

if race_id_str in payout_dict and '馬連' in payout_dict[race_id_str]:
    umaren_data = payout_dict[race_id_str]['馬連']
    print(f"\n実際の馬連結果:")
    print(f"  馬番: {umaren_data.get('馬番', [])}")
    print(f"  払戻金: {umaren_data.get('払戻金', [])}")

    # 的中判定
    for pair_str in umaren_data.get('馬番', []):
        pair_nums = sorted([int(p) for p in pair_str.split('-')])
        print(f"\n  組み合わせ: {pair_nums}")

        for axis in axis_horses:
            for other in other_horses:
                pred_pair = sorted([axis, other])
                if pred_pair == pair_nums:
                    print(f"    ✓ 的中！ {pred_pair}")
