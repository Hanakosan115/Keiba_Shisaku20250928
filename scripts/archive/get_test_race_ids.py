"""
2024年のテスト用race_id一覧を生成
"""
import pandas as pd
from data_config import MAIN_CSV

print("=" * 80)
print("2024年テスト用race_id一覧")
print("=" * 80)

# データ読み込み
df = pd.read_csv(MAIN_CSV, low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年データのみ
df_2024 = df[df['date_parsed'] >= '2024-01-01'].copy()

# race_idごとにグループ化
race_info = df_2024.groupby('race_id').agg({
    'date_parsed': 'first',
    'race_name': 'first',
    'track_name': 'first',
    'horse_id': 'count'  # 出走頭数
}).reset_index()

race_info.columns = ['race_id', 'date', 'race_name', 'track', 'horse_count']

# 出走頭数が10頭以上のレースのみ（予測に適切）
race_info = race_info[race_info['horse_count'] >= 10].copy()

# 月ごとに整理
race_info['month'] = race_info['date'].dt.to_period('M')

print(f"\n合計レース数: {len(race_info):,}")
print(f"月別分布:")
print(race_info['month'].value_counts().sort_index())

print("\n" + "=" * 80)
print("月別おすすめrace_id（各月5レース）")
print("=" * 80)

for month in sorted(race_info['month'].unique()):
    month_races = race_info[race_info['month'] == month].head(5)

    print(f"\n■ {month}")
    print(f"{'race_id':<15} | {'開催日':<12} | {'競馬場':<10} | {'レース名'}")
    print("-" * 80)

    for _, row in month_races.iterrows():
        race_id = str(row['race_id'])
        date = row['date'].strftime('%Y-%m-%d')
        track = str(row['track'])[:8]
        race_name = str(row['race_name'])[:30]

        print(f"{race_id:<15} | {date:<12} | {track:<10} | {race_name}")

# 特に重要なレース（レース名に重賞を示すキーワードを含む）
print("\n" + "=" * 80)
print("重賞・特別レース（推奨）")
print("=" * 80)

keywords = ['記念', '賞', '杯', 'ステークス', 'S', 'カップ']
important_races = race_info[
    race_info['race_name'].str.contains('|'.join(keywords), case=False, na=False)
].head(20)

print(f"\n{'race_id':<15} | {'開催日':<12} | {'競馬場':<10} | {'レース名'}")
print("-" * 80)

for _, row in important_races.iterrows():
    race_id = str(row['race_id'])
    date = row['date'].strftime('%Y-%m-%d')
    track = str(row['track'])[:8]
    race_name = str(row['race_name'])[:40]

    print(f"{race_id:<15} | {date:<12} | {track:<10} | {race_name}")

# 直近のレース（2024年後半）
print("\n" + "=" * 80)
print("2024年後半のレース（10月以降）")
print("=" * 80)

recent_races = race_info[race_info['date'] >= '2024-10-01'].head(20)

print(f"\n{'race_id':<15} | {'開催日':<12} | {'競馬場':<10} | {'レース名'}")
print("-" * 80)

for _, row in recent_races.iterrows():
    race_id = str(row['race_id'])
    date = row['date'].strftime('%Y-%m-%d')
    track = str(row['track'])[:8]
    race_name = str(row['race_name'])[:40]

    print(f"{race_id:<15} | {date:<12} | {track:<10} | {race_name}")

print("\n" + "=" * 80)
print("使い方")
print("=" * 80)
print("""
1. GUIツールの「レース予測」タブを開く
2. 上記のrace_idをコピー
3. 「race_id」欄に貼り付け
4. 「予測実行」をクリック

おすすめ:
- 重賞レースで試すと面白い結果が見られます
- 2024年後半のレースは最新データで精度確認できます
""")
