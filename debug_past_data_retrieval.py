"""
過去データ取得のデバッグ - 2020年1月の1レースを詳細調査
"""
import pandas as pd
import sys
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv

# データ読み込み
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2020年1月の最初のレースを取得
jan_2020_races = df[
    (df['date_parsed'] >= '2020-01-01') &
    (df['date_parsed'] <= '2020-01-31')
]

race_ids = jan_2020_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print("=" * 80)
print("過去データ取得のデバッグ")
print("=" * 80)

# 最初のレースを選択
first_race_id = race_ids[0]
first_race_horses = df[df['race_id'] == first_race_id].copy()

race_date = first_race_horses.iloc[0]['date']
race_date_str = str(race_date)[:10]

print(f"\n対象レース: {first_race_id}")
print(f"レース日付: {race_date_str}")
print(f"競馬場: {first_race_horses.iloc[0].get('track_name')}")
print(f"レース名: {first_race_horses.iloc[0].get('race_name')}")

# 最初の3頭をテスト
test_horses = first_race_horses.head(3)

for idx, (_, horse) in enumerate(test_horses.iterrows(), 1):
    horse_id = horse.get('horse_id')
    horse_name = horse.get('HorseName')
    actual_rank = horse.get('Rank')

    print(f"\n{'-' * 80}")
    print(f"馬 #{idx}: {horse_name} (horse_id: {horse_id})")
    print(f"実際の着順: {actual_rank}着")

    # 過去データを取得
    past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=5)

    print(f"\n過去データ件数: {len(past_results)}件")

    if len(past_results) > 0:
        print("\n過去成績:")
        for i, past_race in enumerate(past_results, 1):
            past_date = past_race.get('date')
            past_rank = past_race.get('rank')
            past_place = past_race.get('place')
            print(f"  {i}. {past_date} {past_place} {past_rank}着")

        # 警告: 過去データの日付をチェック
        print("\n【警告チェック】")
        for past_race in past_results:
            past_date_parsed = pd.to_datetime(past_race.get('date'), errors='coerce')
            race_date_parsed = pd.to_datetime(race_date_str, errors='coerce')

            if past_date_parsed >= race_date_parsed:
                print(f"  !!! データリーケージ検出 !!!")
                print(f"      過去データ日付: {past_date_parsed}")
                print(f"      レース日付: {race_date_parsed}")
                print(f"      過去データが未来のデータを含んでいます！")
    else:
        print("  → 過去データなし（正常）")

# 同じ馬の全データを確認
print("\n" + "=" * 80)
print("同じ馬の全データを確認（デバッグ）")
print("=" * 80)

test_horse_id = test_horses.iloc[0]['horse_id']
test_horse_name = test_horses.iloc[0]['HorseName']

print(f"\n対象馬: {test_horse_name} (horse_id: {test_horse_id})")

# この馬のCSV内の全レコードを取得
all_records = df[df['horse_id'] == test_horse_id].copy()
all_records = all_records.sort_values('date_parsed')

print(f"CSV内の全レコード数: {len(all_records)}件")

if len(all_records) > 0:
    print(f"\n最古のレース: {all_records.iloc[0]['date']}")
    print(f"最新のレース: {all_records.iloc[-1]['date']}")

    print(f"\n最初の5件:")
    for idx, (_, rec) in enumerate(all_records.head(5).iterrows(), 1):
        print(f"  {idx}. {rec['date']} {rec.get('track_name')} {rec.get('Rank')}着")

# レース日付より前のデータを手動でフィルタ
race_date_parsed = pd.to_datetime(race_date_str, errors='coerce')
manual_past_data = all_records[all_records['date_parsed'] < race_date_parsed]

print(f"\n手動フィルタ結果:")
print(f"  レース日付より前のデータ: {len(manual_past_data)}件")

if len(manual_past_data) > 0:
    print(f"  これらは{race_date_str}より前:")
    for _, rec in manual_past_data.head(3).iterrows():
        print(f"    {rec['date']} {rec.get('track_name')}")

print("\n" + "=" * 80)
print("【結論】")
print("=" * 80)

if len(manual_past_data) == 0:
    print("""
正常: 2020年1月のレースには過去データがありません。
全馬がデフォルトスコア（30点）になるため、予測は実質ランダムです。

しかし、バックテストで的中率71.6%という異常な結果が出ています。

可能性:
1. 複数のレースを処理する中で、後半のレースが前半のレースを
   「過去データ」として参照している（同じ日の中で）
   → でも日付フィルタは "<" なので、同じ日は除外されるはず

2. 別の問題が存在する
   → 予測ロジック自体に問題がある可能性
   → または、バックテストの的中判定に問題がある

次のステップ: バックテストの的中判定ロジックを詳しく調査
""")
else:
    print(f"""
データリーケージの可能性:
過去データとして{len(manual_past_data)}件のデータが見つかりました。

詳細を確認してください。
""")

print("=" * 80)
