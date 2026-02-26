"""
データベースの実際の状況を確認
"""
import pandas as pd

print("="*60)
print(" データベース状況確認")
print("="*60)
print()

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

print(f"総行数: {len(df):,}行")
print(f"総レース数: {df['race_id'].nunique():,}件")
print()

# 年別データ
df['date'] = pd.to_datetime(df['date'], errors='coerce')

print("年別データ:")
print("-"*60)

for year in sorted(df['date'].dt.year.dropna().unique()):
    year_data = df[df['date'].dt.year == year]
    races = year_data['race_id'].nunique()
    rows = len(year_data)
    horses_with_name = year_data['HorseName'].notna().sum()
    with_stats = year_data['total_starts'].notna().sum()

    print(f"{int(year)}年:")
    print(f"  レース数: {races:,}件")
    print(f"  総行数: {rows:,}行")
    print(f"  HorseName有: {horses_with_name:,}行")
    print(f"  統計データ有: {with_stats:,}行 ({with_stats/rows*100:.1f}%)")
    print()

# 全体の統計カバー率
print("="*60)
print("全体の統計カバー率:")
print("-"*60)

stats_cols = ['total_starts', 'total_win_rate', 'total_earnings', 'father', 'mother_father']
for col in stats_cols:
    if col in df.columns:
        count = df[col].notna().sum()
        pct = count / len(df) * 100
        print(f"  {col:20s}: {pct:5.1f}% ({count:,}/{len(df):,})")

print()
print("="*60)
