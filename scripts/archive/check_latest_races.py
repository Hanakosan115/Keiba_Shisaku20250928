"""
最新のレースIDパターンを確認
"""

import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2025年8月のレース
df_2025_aug = df[(df['date_parsed'].dt.year == 2025) & (df['date_parsed'].dt.month == 8)]

if len(df_2025_aug) > 0:
    # ユニークなレースID
    unique_races = df_2025_aug['race_id'].unique()

    print("2025年8月のレースID（最新10件）:")
    for rid in sorted(unique_races)[-10:]:
        race_data = df_2025_aug[df_2025_aug['race_id'] == rid].iloc[0]
        print(f"  {rid}: {race_data.get('race_name', 'N/A')} - {race_data.get('date', 'N/A')}")

    print(f"\n合計: {len(unique_races)}レース")
else:
    print("2025年8月のデータなし")

# 最新のレース
latest_idx = df['date_parsed'].idxmax()
latest_race = df.loc[latest_idx]
print(f"\nDB最新レース:")
print(f"  ID: {latest_race['race_id']}")
print(f"  名前: {latest_race.get('race_name', 'N/A')}")
print(f"  日付: {latest_race['date_parsed'].strftime('%Y-%m-%d')}")
