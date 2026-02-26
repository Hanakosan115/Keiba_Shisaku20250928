"""
データ構造を診断
"""
import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

print(f"総行数: {len(df):,}\n")

# January race IDs from the list file
with open('race_ids_2025_january_by_date.txt', 'r') as f:
    jan_race_ids = set([line.strip() for line in f if line.strip()])

print(f"1月レースID数 (リストファイル): {len(jan_race_ids)}\n")

# Find all rows for January race IDs
df_jan_by_id = df[df['race_id'].astype(str).isin(jan_race_ids)]

print(f"1月レースIDに該当する行数: {len(df_jan_by_id):,}")
print(f"ユニークレース数: {df_jan_by_id['race_id'].nunique()}")
print(f"平均馬数/レース: {len(df_jan_by_id) / df_jan_by_id['race_id'].nunique():.1f}頭\n")

# Check date format
print("date列のサンプル (最初の10行):")
print(df_jan_by_id['date'].head(20).tolist())

# Statistics coverage
stat_cols = ['father', 'mother_father', 'total_starts', 'total_win_rate',
             'turf_win_rate', 'dirt_win_rate', 'total_earnings']

print("\n統計列カバー率:")
for col in stat_cols:
    if col in df_jan_by_id.columns:
        count = df_jan_by_id[col].notna().sum()
        pct = count / len(df_jan_by_id) * 100 if len(df_jan_by_id) > 0 else 0
        print(f"  {col}: {count:,}/{len(df_jan_by_id):,} ({pct:.1f}%)")

# Sample of one race
sample_race = df_jan_by_id.iloc[0]['race_id']
sample_data = df[df['race_id'] == sample_race]
print(f"\n\nサンプルレース {sample_race}:")
print(f"  行数: {len(sample_data)}")
print(f"  father非NULL: {sample_data['father'].notna().sum()}")
print(f"  total_starts非NULL: {sample_data['total_starts'].notna().sum()}")
print(f"  HorseName非NULL: {sample_data['HorseName'].notna().sum()}")
