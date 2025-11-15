"""
2020年1月の異常な的中率の原因調査
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

print("=" * 80)
print("2020年1月の異常な的中率の原因調査")
print("=" * 80)

# データ読み込み
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# データの範囲を確認
print("\n【データ全体の範囲】")
print(f"最古のデータ: {df['date_parsed'].min()}")
print(f"最新のデータ: {df['date_parsed'].max()}")
print(f"総レコード数: {len(df):,}件")

# 2020年1月のレースを抽出
jan_2020_races = df[
    (df['date_parsed'] >= '2020-01-01') &
    (df['date_parsed'] <= '2020-01-31')
]

race_ids = jan_2020_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"\n【2020年1月】")
print(f"対象レース数: {len(race_ids)}レース")

# 2019年のデータがあるか確認
data_2019 = df[df['date_parsed'] < '2020-01-01']
print(f"\n【2019年以前のデータ】")
print(f"2019年以前のレコード数: {len(data_2019):,}件")
print(f"2019年以前のレース数: {data_2019['race_id'].nunique():,}レース")

if len(data_2019) > 0:
    print(f"最古の日付: {data_2019['date_parsed'].min()}")
    print(f"最新の日付: {data_2019['date_parsed'].max()}")
else:
    print("⚠️ 2019年以前のデータが存在しない！")
    print("   → 2020年1月のレースは過去データなしで予測している可能性")

# サンプルレースを詳細調査（最初の5レース）
print("\n" + "=" * 80)
print("【サンプルレース詳細調査】")
print("=" * 80)

for idx, race_id in enumerate(race_ids[:5], 1):
    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_date = race_horses.iloc[0]['date']
    race_date_str = str(race_date)[:10]

    first_row = race_horses.iloc[0]
    track_name = first_row.get('track_name', '')
    race_name = first_row.get('race_name', '')

    print(f"\n{'=' * 80}")
    print(f"レース #{idx}: {race_id}")
    print(f"日付: {race_date_str} | {track_name} | {race_name}")
    print("=" * 80)

    # 予測実行
    horses_scores = []
    past_data_stats = []

    for _, horse in race_horses.iterrows():
        horse_id = horse.get('horse_id')
        horse_name = horse.get('HorseName')

        # 過去データ取得
        past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=5)

        # 過去データの統計
        past_data_stats.append({
            'horse_id': horse_id,
            'horse_name': horse_name,
            'past_count': len(past_results),
            'actual_rank': horse.get('Rank'),
            'actual_ninki': horse.get('Ninki')
        })

        horse_basic_info = {
            'HorseName': horse_name,
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
            'name': horse_name,
            'score': score,
            'actual_rank': horse.get('Rank')
        })

    # 過去データの統計
    total_past_data = sum([stat['past_count'] for stat in past_data_stats])
    avg_past_data = total_past_data / len(past_data_stats) if past_data_stats else 0

    print(f"\n【過去データの状況】")
    print(f"出走馬数: {len(past_data_stats)}頭")
    print(f"過去データ総数: {total_past_data}件")
    print(f"1頭あたり平均: {avg_past_data:.1f}件")

    horses_with_no_data = [stat for stat in past_data_stats if stat['past_count'] == 0]
    print(f"過去データなし: {len(horses_with_no_data)}頭")

    if len(horses_with_no_data) > 0:
        print(f"  → 過去データなしの馬:")
        for stat in horses_with_no_data[:3]:
            print(f"     {stat['horse_name']} (実際: {stat['actual_rank']}着)")

    # スコア順にソート
    horses_scores.sort(key=lambda x: x['score'], reverse=True)

    top3 = [h['umaban'] for h in horses_scores[:3]]

    print(f"\n【予測】")
    print(f"TOP3: {top3}")
    for i, h in enumerate(horses_scores[:3], 1):
        print(f"  {i}位: {h['umaban']:>2}番 {h['name']:<20} スコア:{h['score']:.1f}")

    # 実際の結果
    actual_top3 = race_horses.sort_values('Rank').head(3)
    print(f"\n【実際の結果】")
    for _, row in actual_top3.iterrows():
        print(f"  {int(row['Rank'])}着: {int(row['Umaban']):>2}番 {row['HorseName']:<20}")

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    # 的中判定
    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_pairs = umaren_data.get('馬番', [])

        if winning_pairs and len(winning_pairs) >= 2:
            try:
                winning_pair = set([int(x) for x in winning_pairs[:2]])
                umaren_pairs = list(combinations(top3, 2))

                hit_found = False
                for pair in umaren_pairs:
                    if set(pair) == winning_pair:
                        hit_found = True
                        break

                print(f"\n【的中判定】")
                print(f"馬連: {'✓ 的中' if hit_found else '× 不的中'}")
                print(f"  実際の馬連: {sorted(winning_pair)}")
                print(f"  予測BOX: {[sorted(list(p)) for p in umaren_pairs]}")
            except:
                pass

print("\n" + "=" * 80)
print("【重要な発見】")
print("=" * 80)

# 全1月レースの過去データ統計
print("\n2020年1月全レースの過去データ統計を集計中...")

total_horses = 0
total_with_no_data = 0
total_past_records = 0

for race_id in race_ids:
    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_date = race_horses.iloc[0]['date']
    race_date_str = str(race_date)[:10]

    for _, horse in race_horses.iterrows():
        horse_id = horse.get('horse_id')
        past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=5)

        total_horses += 1
        total_past_records += len(past_results)

        if len(past_results) == 0:
            total_with_no_data += 1

print(f"\n【2020年1月全体の統計】")
print(f"総出走馬数: {total_horses}頭")
print(f"過去データなし: {total_with_no_data}頭 ({total_with_no_data/total_horses*100:.1f}%)")
print(f"過去データあり: {total_horses - total_with_no_data}頭 ({(total_horses - total_with_no_data)/total_horses*100:.1f}%)")
print(f"1頭あたり平均過去レース数: {total_past_records/total_horses:.2f}件")

print("\n" + "=" * 80)
print("【結論】")
print("=" * 80)

if len(data_2019) == 0:
    print("""
❌ CSVデータが2020年1月から始まっている
   → 2020年1月のレースには過去データがほとんどない
   → 過去データなし = デフォルトスコア30点
   → ランダムな予測になっている可能性

しかし、的中率が71.6%と異常に高い...

考えられる原因:
1. 過去データ取得ロジックに問題がある
   - 同じ2020年1月のレースを「過去データ」として参照している
   - 日付フィルタが機能していない

2. データリーケージ
   - 何らかの形で未来のデータを参照している

次のステップ: 過去データ取得関数を詳細にデバッグする必要がある
""")
else:
    print("""
✓ 2019年以前のデータが存在する
  → 過去データは正しく取得できているはず

しかし、的中率が71.6%と異常に高い...

次のステップ: 過去データ取得関数の日付フィルタを詳細に検証
""")

print("=" * 80)
