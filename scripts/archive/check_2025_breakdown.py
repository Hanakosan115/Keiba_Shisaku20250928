"""
2025年データの内訳を確認
"""
import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

# 2025年のレースIDを持つデータを抽出
df_2025 = df[df['race_id'].astype(str).str.startswith('2025')]

print(f"2025年データ概要:")
print(f"  総行数: {len(df_2025):,}")
print(f"  ユニークレース数: {df_2025['race_id'].nunique():,}")
print()

# 日付を変換
df['date'] = pd.to_datetime(df['date'], errors='coerce')
df_2025_with_date = df_2025.copy()
df_2025_with_date['date'] = pd.to_datetime(df_2025_with_date['date'], errors='coerce')

# 日付がある行とない行
print(f"日付情報:")
print(f"  日付あり: {df_2025_with_date['date'].notna().sum():,}行")
print(f"  日付なし: {df_2025_with_date['date'].isna().sum():,}行")
print()

# 月別に分類
df_2025_with_date['month'] = df_2025_with_date['date'].dt.month

print("月別レース数:")
month_counts = df_2025_with_date.groupby('month')['race_id'].nunique().sort_index()
for month, count in month_counts.items():
    if pd.notna(month):
        print(f"  {int(month)}月: {count}レース")

print(f"  月不明: {df_2025_with_date[df_2025_with_date['date'].isna()]['race_id'].nunique()}レース")
print()

# HorseNameの有無でデータの種類を確認
print("データの種類:")
with_horse = df_2025[df_2025['HorseName'].notna()]
without_horse = df_2025[df_2025['HorseName'].isna()]

print(f"  基本レース結果データ (HorseName あり): {len(with_horse):,}行 ({with_horse['race_id'].nunique():,}レース)")
print(f"  追加統計データ (HorseName なし): {len(without_horse):,}行 ({without_horse['race_id'].nunique():,}レース)")
print()

# 統計データのカバー率
print("追加統計データのカバー率:")
print(f"  father: {without_horse['father'].notna().sum():,}/{len(without_horse):,}")
print(f"  total_starts: {without_horse['total_starts'].notna().sum():,}/{len(without_horse):,}")
print()

# 1月のレースID確認
df_jan = df_2025_with_date[(df_2025_with_date['date'] >= '2025-01-01') &
                            (df_2025_with_date['date'] < '2025-02-01')]
print(f"1月データ (日付フィルター):")
print(f"  レース数: {df_jan['race_id'].nunique()}")
print(f"  総行数: {len(df_jan):,}")
print()

# レースIDのパターンを確認
print("2025年レースIDのサンプル (最初の20件):")
sample_races = sorted(df_2025['race_id'].unique())[:20]
for rid in sample_races:
    race_data = df_2025[df_2025['race_id'] == rid]
    print(f"  {rid}: {len(race_data)}行, HorseName={race_data['HorseName'].notna().sum()}, father={race_data['father'].notna().sum()}")
