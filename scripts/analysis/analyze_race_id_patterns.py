"""
既存データからレースIDパターンを分析
実際に存在するレースの傾向を把握
"""

import pandas as pd
from collections import Counter

# データ読み込み
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

print("="*60)
print("レースIDパターン分析")
print("="*60)
print()

# レースIDを解析
df['year'] = df['race_id'].astype(str).str[:4]
df['place'] = df['race_id'].astype(str).str[4:6]
df['meeting'] = df['race_id'].astype(str).str[6:8]
df['day'] = df['race_id'].astype(str).str[8:10]
df['race_num'] = df['race_id'].astype(str).str[10:12]

# ユニークなレース
unique_races = df.drop_duplicates(subset=['race_id'])

print(f"総レース数: {len(unique_races):,}件")
print()

# 競馬場の分布
print("競馬場コード分布:")
place_counts = unique_races['place'].value_counts().sort_index()
place_names = {
    '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
    '05': '東京', '06': '中山', '07': '中京', '08': '京都',
    '09': '阪神', '10': '小倉'
}
for place, count in place_counts.items():
    place_name = place_names.get(place, '不明')
    print(f"  {place} ({place_name}): {count:,}件")
print()

# 開催回の分布
print("開催回コード分布:")
meeting_counts = unique_races['meeting'].value_counts().sort_index()
for meeting, count in meeting_counts.items():
    print(f"  {meeting}回: {count:,}件")
print()

# 日目の分布
print("日目コード分布:")
day_counts = unique_races['day'].value_counts().sort_index()
for day, count in day_counts.items():
    print(f"  {day}日目: {count:,}件")
print()

# レース番号の分布
print("レース番号分布:")
race_num_counts = unique_races['race_num'].value_counts().sort_index()
for race_num, count in race_num_counts.items():
    print(f"  {race_num}R: {count:,}件")
print()

# 2025年のデータを確認
df_2025 = unique_races[unique_races['year'] == '2025']
print(f"2025年データ: {len(df_2025)}レース")
if len(df_2025) > 0:
    print("2025年のレースID例:")
    for race_id in sorted(df_2025['race_id'].astype(str).unique())[:10]:
        print(f"  {race_id}")
print()

# 各競馬場で実際に使われている開催回を分析
print("競馬場ごとの開催回パターン（2024年）:")
df_2024 = unique_races[unique_races['year'] == '2024']
for place in sorted(df_2024['place'].unique()):
    meetings = sorted(df_2024[df_2024['place'] == place]['meeting'].unique())
    place_name = place_names.get(place, '不明')
    print(f"  {place} ({place_name}): {', '.join(meetings)}")
print()

print("="*60)
