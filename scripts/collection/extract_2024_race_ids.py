"""
バックアップDBから2024年のrace_idを抽出
"""
import pandas as pd

print("Extracting 2024 race IDs from backup...")

# バックアップから読み込み
df = pd.read_csv('netkeiba_data_OLD_BROKEN_20251217.csv', low_memory=False)
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年のrace_id抽出
df_2024 = df[(df['date'] >= '2024-01-01') & (df['date'] < '2025-01-01')]
race_ids_2024 = sorted(df_2024['race_id'].dropna().unique())

print(f"Found {len(race_ids_2024)} races in 2024")

# ファイルに保存
with open('race_ids_2024.txt', 'w') as f:
    for race_id in race_ids_2024:
        f.write(f"{race_id}\n")

print(f"Saved to race_ids_2024.txt")
print()
print("Sample IDs:")
for rid in race_ids_2024[:10]:
    print(f"  {rid}")
