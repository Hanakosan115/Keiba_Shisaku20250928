"""
既存2025年データの確認
"""
import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', encoding='utf-8', low_memory=False)

# 統計列リスト
stat_cols = [
    'father', 'mother_father',
    'total_starts', 'total_win_rate',
    'turf_win_rate', 'dirt_win_rate',
    'running_style_category',
    'prev_race_rank', 'grade_race_starts'
]

# 既存の統計列を確認
existing_stats = [col for col in stat_cols if col in df.columns]
print(f"既存の統計列: {len(existing_stats)}/{len(stat_cols)}")
for col in existing_stats:
    print(f"  - {col}")

print()

# 2025年データを抽出
df_2025 = df[df['race_id'].astype(str).str.startswith('2025')].copy()
print(f"2025年レコード数: {len(df_2025)}")
print(f"2025年レースID範囲: {df_2025['race_id'].min()} 〜 {df_2025['race_id'].max()}")

# ユニークレース数
unique_races = df_2025['race_id'].nunique()
print(f"ユニークレース数: {unique_races}")

print()

# 統計列の充填率
if existing_stats:
    print("統計列の充填状況:")
    for col in existing_stats:
        filled = df_2025[col].notna().sum()
        pct = filled / len(df_2025) * 100
        print(f"  {col}: {filled}/{len(df_2025)} ({pct:.1f}%)")
else:
    print("統計列は存在しません")
