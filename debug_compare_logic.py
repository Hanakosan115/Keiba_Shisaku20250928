"""
比較ロジックのデバッグ（1レースで詳細確認）
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

# データ読み込み
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv", encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

# 8月のレース1つ取得
df['race_id_str'] = df['race_id'].astype(str)
target_races = df[df['race_id_str'].str.startswith('202508')]
race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()
race_id = race_ids[0]

print(f"デバッグ対象race_id: {race_id}")
print("=" * 80)

# レースデータ
race_horses = df[df['race_id'] == race_id].copy()
print(f"\n【実際の結果】")
results = race_horses[['Umaban', 'HorseName', 'Rank']].sort_values('Rank')
print(results.head(3).to_string(index=False))

# 配当データ確認
race_id_str = str(race_id)
if race_id_str in payout_dict:
    payout_data = payout_dict[race_id_str]
    print(f"\n【配当データ】")
    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        print(f"馬連 馬番: {umaren_data.get('馬番', [])}")
        print(f"馬連 払戻金: {umaren_data.get('払戻金', [])}")

        # データ型確認
        winning_pairs = umaren_data.get('馬番', [])
        print(f"\n馬番のデータ型: {type(winning_pairs)}")
        if winning_pairs:
            print(f"馬番[0]のデータ型: {type(winning_pairs[0])}")
            print(f"馬番の長さ: {len(winning_pairs)}")
            print(f"馬番の内容: {winning_pairs}")

        # 変換テスト
        try:
            winning_pair = set([int(x) for x in winning_pairs[:2]])
            print(f"\n変換後の winning_pair: {winning_pair}")
        except Exception as e:
            print(f"\n変換エラー: {e}")
else:
    print(f"\n配当データなし")
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
    race_date = f"{race_id_str[0:4]}-{race_id_str[4:6]}-{race_id_str[6:8]}"
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

print(f"\n【予測】")
if honmei:
    print(f"◎ {honmei['umaban']}番")
if taikou:
    print(f"○ {taikou['umaban']}番")
if ana:
    print(f"▲ {ana['umaban']}番")
if renge:
    print(f"△ {renge['umaban']}番")
if hoshi:
    print(f"☆ {hoshi['umaban']}番")

# パターンC: 5頭BOX生成
h1, h2, h3, h4, h5 = honmei['umaban'], taikou['umaban'], ana['umaban'], renge['umaban'], hoshi['umaban']
horses = [h1, h2, h3, h4, h5]
umaren_pairs = list(combinations(horses, 2))

print(f"\n【5頭BOXの馬連組み合わせ】")
print(f"予測5頭: {horses}")
print(f"馬連ペア数: {len(umaren_pairs)}")
print(f"馬連ペア: {umaren_pairs[:5]}... (最初の5つ)")

# 的中判定のテスト
print(f"\n【的中判定テスト】")
umaren_data = payout_data['馬連']
winning_pairs = umaren_data.get('馬番', [])
payouts = umaren_data.get('払戻金', [])

print(f"実際の勝ち馬番: {winning_pairs}")

try:
    winning_pair = set([int(x) for x in winning_pairs[:2]])
    print(f"winning_pair (set): {winning_pair}")

    hit_found = False
    for pair in umaren_pairs:
        pair_set = set(pair)
        is_match = (pair_set == winning_pair)
        if is_match:
            print(f"\n[HIT] Match found! {pair} == {winning_pair}")
            print(f"Payout: {payouts[0] if payouts else 0} yen")
            hit_found = True
            break

    if not hit_found:
        print(f"\n[MISS] No match")
        print(f"Predicted {len(umaren_pairs)} pairs but {winning_pair} not in them")
        # 実際の勝ち馬が予測5頭に含まれているか確認
        winning_list = list(winning_pair)
        in_prediction = [w for w in winning_list if w in horses]
        print(f"勝ち馬のうち予測に含まれるもの: {in_prediction} / {len(winning_list)}")

except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()
