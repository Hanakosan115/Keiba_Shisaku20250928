"""
2025年の予測可能なrace_id一覧
"""
import pandas as pd
from data_config import MAIN_CSV

print("=" * 80)
print("2025年 予測可能なレース一覧")
print("=" * 80)

# データ読み込み
df = pd.read_csv(MAIN_CSV, low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2025年データのみ
df_2025 = df[df['date_parsed'] >= '2025-01-01'].copy()

print(f"\n2025年データ: {len(df_2025):,}行")
print(f"日付範囲: {df_2025['date_parsed'].min()} ～ {df_2025['date_parsed'].max()}")

# race_idごとにグループ化
race_info = df_2025.groupby('race_id').agg({
    'date_parsed': 'first',
    'race_name': 'first',
    'track_name': 'first',
    'horse_id': 'count'
}).reset_index()

race_info.columns = ['race_id', 'date', 'race_name', 'track', 'horse_count']
race_info = race_info[race_info['horse_count'] >= 10].copy()

print(f"予測可能レース数: {len(race_info):,}")

# 月ごとに整理
race_info['month'] = race_info['date'].dt.to_period('M')

print(f"\n月別分布:")
month_counts = race_info['month'].value_counts().sort_index()
for month, count in month_counts.items():
    print(f"  {month}: {count}レース")

# 重賞レース
print("\n" + "=" * 80)
print("重賞・特別レース（おすすめ）")
print("=" * 80)

keywords = ['記念', '賞', '杯', 'ステークス', 'S', 'カップ', 'G']
important_races = race_info[
    race_info['race_name'].str.contains('|'.join(keywords), case=False, na=False)
]

if len(important_races) > 0:
    print(f"\n{len(important_races)}レース見つかりました\n")
    print(f"{'race_id':<15} | {'日付':<12} | {'競馬場':<10} | {'レース名'}")
    print("-" * 80)

    for _, row in important_races.head(20).iterrows():
        race_id = str(row['race_id'])
        date = str(row['date'])[:10]
        track = str(row['track'])[:8]
        race_name = str(row['race_name'])[:40]
        print(f"{race_id:<15} | {date:<12} | {track:<10} | {race_name}")
else:
    print("\n重賞レースが見つかりませんでした")

# 各月のサンプル
print("\n" + "=" * 80)
print("月別サンプルレース（各月5レース）")
print("=" * 80)

for month in sorted(race_info['month'].unique()):
    month_races = race_info[race_info['month'] == month].head(5)

    print(f"\n■ {month}")
    print(f"{'race_id':<15} | {'日付':<12} | {'競馬場':<10} | {'レース名'}")
    print("-" * 80)

    for _, row in month_races.iterrows():
        race_id = str(row['race_id'])
        date = str(row['date'])[:10]
        track = str(row['track'])[:8]
        race_name = str(row['race_name'])[:30]
        print(f"{race_id:<15} | {date:<12} | {track:<10} | {race_name}")

# 最新のレース
print("\n" + "=" * 80)
print("最新レース（2025年8月）")
print("=" * 80)

latest_races = race_info[race_info['date'] >= '2025-08-01'].head(20)

print(f"\n{'race_id':<15} | {'日付':<12} | {'競馬場':<10} | {'レース名'}")
print("-" * 80)

for _, row in latest_races.iterrows():
    race_id = str(row['race_id'])
    date = str(row['date'])[:10]
    track = str(row['track'])[:8]
    race_name = str(row['race_name'])[:40]
    print(f"{race_id:<15} | {date:<12} | {track:<10} | {race_name}")

print("\n" + "=" * 80)
print("使い方")
print("=" * 80)
print("""
GUIツールの「レース予測」タブで:
1. 上記のrace_idをコピー
2. race_id欄に貼り付け
3. 「予測実行」をクリック

推奨:
- 重賞レースで試すと面白い
- 2025年8月（最新）のレースで精度確認
""")
