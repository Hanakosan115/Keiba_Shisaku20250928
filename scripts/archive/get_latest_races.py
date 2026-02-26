"""
最新のレースID取得
"""
import pandas as pd
from data_config import MAIN_CSV

df = pd.read_csv(MAIN_CSV, low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 最新月のレース
df_latest = df[df['date_parsed'] >= '2024-12-01'].copy()

races = df_latest.groupby('race_id').agg({
    'date_parsed': 'first',
    'race_name': 'first',
    'track_name': 'first',
    'horse_id': 'count'
}).reset_index()

races.columns = ['race_id', 'date', 'race_name', 'track', 'horse_count']
races = races[races['horse_count'] >= 10].head(15)

print("=" * 80)
print("2024年12月のレース（予測テスト用）")
print("=" * 80)
print()
print(f"{'race_id':<15} | {'レース名':<30} | {'日付':<12} | {'競馬場'}")
print("-" * 80)

for _, row in races.iterrows():
    race_id = str(row['race_id'])
    race_name = str(row['race_name'])[:28]
    date = str(row['date'])[:10]
    track = str(row['track'])
    print(f"{race_id:<15} | {race_name:<30} | {date:<12} | {track}")

print()
print("=" * 80)
print("GUIツールでこれらのrace_idを使って予測してみましょう！")
print("=" * 80)
