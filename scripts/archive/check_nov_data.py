"""
2025年11月のデータを確認
"""

import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

print("="*60)
print("データベース確認")
print("="*60)
print()

# 全体
print(f"CSV内総レース数: {len(df['race_id'].unique()):,}件")
print(f"CSV内総レコード数: {len(df):,}件")
print()

# 2025年11月のデータ
df['race_id_str'] = df['race_id'].astype(str)
df_nov = df[df['race_id_str'].str.startswith('202511')]

print(f"2025年11月のレース数: {len(df_nov['race_id'].unique())}件")

if len(df_nov) > 0:
    print("\n11月のレースID（最初の20件）:")
    for rid in sorted(df_nov['race_id'].astype(str).unique())[:20]:
        race_data = df_nov[df_nov['race_id'].astype(str) == rid].iloc[0]
        print(f"  {rid}: {race_data.get('race_name', 'N/A')}")
else:
    print("  → 11月のデータは存在しません")

print()

# ログファイルも確認
import os
log_path = r'C:\Users\bu158\HorseRacingAnalyzer\data\processed_race_ids.log'

if os.path.exists(log_path):
    with open(log_path, 'r', encoding='utf-8') as f:
        log_ids = set(line.strip() for line in f if line.strip())

    print(f"ログファイル内レース数: {len(log_ids):,}件")

    # 11月のレースIDを抽出
    nov_in_log = [rid for rid in log_ids if rid.startswith('202511')]
    print(f"ログ内の2025年11月レース数: {len(nov_in_log)}件")

    if nov_in_log:
        print("\nログ内の11月レースID（最初の20件）:")
        for rid in sorted(nov_in_log)[:20]:
            print(f"  {rid}")

print()
print("="*60)
