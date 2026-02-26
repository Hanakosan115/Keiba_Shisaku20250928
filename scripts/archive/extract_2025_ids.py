"""
既存CSVから2025年レースIDを抽出
"""
import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', encoding='utf-8', low_memory=False)

# 2025年レースIDを抽出
races_2025 = df[df['race_id'].astype(str).str.startswith('2025')]['race_id'].astype(str).unique()
races_2025 = sorted(races_2025)

# ファイルに出力
with open('existing_2025_race_ids.txt', 'w') as f:
    f.write('\n'.join(races_2025))

print(f"{len(races_2025)}件の既存2025年レースIDを抽出しました")
print(f"出力ファイル: existing_2025_race_ids.txt")
print(f"\n最初の10件:")
for rid in races_2025[:10]:
    print(f"  {rid}")
