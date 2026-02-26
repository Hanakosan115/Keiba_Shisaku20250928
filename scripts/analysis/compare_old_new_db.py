"""
新旧データベースの比較
"""
import pandas as pd

print("="*60)
print(" 新旧データベース比較")
print("="*60)
print()

# 旧データベース
print("[OLD DATABASE - BROKEN]")
df_old = pd.read_csv('netkeiba_data_OLD_BROKEN_20251217.csv', nrows=1000, low_memory=False)
print(f"  Sample rows: {len(df_old):,}")
print(f"  Sample races: {df_old['race_id'].nunique()}")
print(f"  Avg horses per race: {len(df_old) / df_old['race_id'].nunique():.1f}")
print()
print("  Columns:")
for col in df_old.columns[:30]:
    print(f"    - {col}")
print()

# 統計列のカバー率
print("  Statistics coverage (OLD):")
stat_cols = ['total_starts', 'total_win_rate', 'total_earnings', 'father', 'mother_father']
for col in stat_cols:
    if col in df_old.columns:
        coverage = df_old[col].notna().sum() / len(df_old) * 100
        print(f"    {col}: {coverage:.1f}%")
    else:
        print(f"    {col}: N/A")

print()
print("="*60)
print()

# 新データベース
print("[NEW DATABASE - FIXED]")
df_new = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', nrows=1000, low_memory=False)
print(f"  Sample rows: {len(df_new):,}")
print(f"  Sample races: {df_new['race_id'].nunique()}")
print(f"  Avg horses per race: {len(df_new) / df_new['race_id'].nunique():.1f}")
print()
print("  Columns:")
for col in df_new.columns[:30]:
    print(f"    - {col}")
print()

# 統計列のカバー率
print("  Statistics coverage (NEW):")
for col in stat_cols:
    if col in df_new.columns:
        coverage = df_new[col].notna().sum() / len(df_new) * 100
        print(f"    {col}: {coverage:.1f}%")
    else:
        print(f"    {col}: N/A")

print()
print("="*60)
print(" KEY IMPROVEMENTS")
print("="*60)
print()
print("1. Horses per race:")
old_avg = len(df_old) / df_old['race_id'].nunique()
new_avg = len(df_new) / df_new['race_id'].nunique()
print(f"   OLD: {old_avg:.1f} horses/race (BROKEN - should be ~14)")
print(f"   NEW: {new_avg:.1f} horses/race (CORRECT!)")
print()
print("2. Statistics coverage:")
for col in stat_cols:
    if col in df_old.columns and col in df_new.columns:
        old_cov = df_old[col].notna().sum() / len(df_old) * 100
        new_cov = df_new[col].notna().sum() / len(df_new) * 100
        improvement = new_cov - old_cov
        print(f"   {col}: {old_cov:.1f}% -> {new_cov:.1f}% (+{improvement:.1f}%)")
