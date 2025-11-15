"""
改善版スコアリングシステムのバックテスト
- 騎手・調教師データを活用
- 従来手法との比較
"""
import pandas as pd
import json
import sys
from itertools import combinations
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv
from improved_scoring_system import calculate_improved_score

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

print("=" * 80)
print("改善版スコアリングシステムのバックテスト")
print("=" * 80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年のデータでテスト
target_races = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"対象: 2024年 {len(race_ids)}レース")

# 結果集計用
results = {
    'total': 0,
    'umaren_hit': 0,
    'umaren_return': 0,
    'umaren_cost': 0,
}

for idx, race_id in enumerate(race_ids):
    if (idx + 1) % 500 == 0:
        print(f"  {idx + 1}/{len(race_ids)} レース処理中...")

    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    # 馬番順にソート（データリーケージ防止）
    race_horses = race_horses.sort_values('Umaban')

    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue

    race_date_str = str(race_date)[:10]

    # 予測実行
    horses_scores = []

    for _, horse in race_horses.iterrows():
        horse_id = horse.get('horse_id')
        past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=5)

        # 馬のデータを準備
        horse_data = {
            'race_results': past_results,
            'jockey_name': horse.get('JockeyName'),
            'trainer_name': horse.get('TrainerName'),
            'weight_diff': horse.get('WeightDiff'),
            'sex': horse.get('Sex'),
            'age': horse.get('Age')
        }

        race_conditions = {
            'Distance': horse.get('distance'),
            'CourseType': horse.get('course_type'),
            'TrackCondition': horse.get('track_condition')
        }

        # 改善版スコア計算
        score = calculate_improved_score(horse_data, race_conditions, race_date_str)

        horses_scores.append({
            'umaban': int(horse.get('Umaban', 0)),
            'score': score
        })

    # スコア順にソート
    horses_scores.sort(key=lambda x: x['score'], reverse=True)

    top3 = [h['umaban'] for h in horses_scores[:3]]

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data:
        continue

    results['total'] += 1

    # 馬連
    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_pairs = umaren_data.get('馬番', [])
        payouts = umaren_data.get('払戻金', [])

        if winning_pairs and len(winning_pairs) >= 2:
            try:
                winning_pair = set([int(x) for x in winning_pairs[:2]])
                umaren_pairs = list(combinations(top3, 2))

                results['umaren_cost'] += len(umaren_pairs) * 100

                hit_found = False
                for pair in umaren_pairs:
                    if set(pair) == winning_pair:
                        hit_found = True
                        break

                if hit_found:
                    results['umaren_hit'] += 1
                    results['umaren_return'] += payouts[0]
            except:
                pass

# 結果出力
print("\n" + "=" * 80)
print("【改善版スコアリングの結果】2024年")
print("=" * 80)

print(f"\n総レース数: {results['total']:,}レース")

if results['umaren_cost'] > 0:
    umaren_recovery = (results['umaren_return'] / results['umaren_cost']) * 100
    print(f"\n【馬連】3頭BOX")
    print(f"  的中: {results['umaren_hit']:,}回 / {results['total']:,}レース")
    print(f"  的中率: {results['umaren_hit']/results['total']*100:.2f}%")
    print(f"  投資額: {results['umaren_cost']:,}円")
    print(f"  払戻額: {results['umaren_return']:,}円")
    print(f"  回収率: {umaren_recovery:.2f}%")
    print(f"  損益: {results['umaren_return'] - results['umaren_cost']:+,}円")

print("\n" + "=" * 80)
print("【従来手法との比較】")
print("=" * 80)

print("\n従来手法（過去成績のみ）:")
print("  的中: 582回")
print("  的中率: 17.3%")
print("  回収率: 64.6%")
print("  損益: -356,250円")

if results['total'] > 0 and results['umaren_cost'] > 0:
    print(f"\n改善版（騎手・調教師データ追加）:")
    print(f"  的中: {results['umaren_hit']}回")
    print(f"  的中率: {results['umaren_hit']/results['total']*100:.2f}%")
    print(f"  回収率: {umaren_recovery:.2f}%")
    print(f"  損益: {results['umaren_return'] - results['umaren_cost']:+,}円")

    print(f"\n【改善度】")
    hit_rate_diff = (results['umaren_hit']/results['total']*100) - 17.3
    recovery_diff = umaren_recovery - 64.6
    profit_diff = (results['umaren_return'] - results['umaren_cost']) - (-356250)

    print(f"  的中率: {hit_rate_diff:+.2f}ポイント")
    print(f"  回収率: {recovery_diff:+.2f}ポイント")
    print(f"  損益: {profit_diff:+,}円")

print("\n" + "=" * 80)
print("バックテスト完了")
print("=" * 80)
