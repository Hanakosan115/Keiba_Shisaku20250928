"""
自動収集した11月のレースIDとCSVを突き合わせ
"""

import pandas as pd

# 自動収集で取得したレースIDファイルを読み込み
with open('race_ids_2025_sep_dec.txt', 'r', encoding='utf-8') as f:
    auto_collected_ids = set(line.strip() for line in f if line.strip())

# 11月29-30日のレースIDのみ抽出
nov_29_30_ids = [rid for rid in auto_collected_ids if rid.startswith('20251129') or rid.startswith('20251130')]

print("="*60)
print("11月29-30日のレースID確認")
print("="*60)
print()

print(f"自動収集した11月29-30日のレースID数: {len(nov_29_30_ids)}件")
print()
print("レースID一覧（最初の10件）:")
for rid in sorted(nov_29_30_ids)[:10]:
    print(f"  {rid}")
print()

# CSVを読み込み
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
csv_race_ids = set(df['race_id'].astype(str).unique())

print(f"CSV内の総レース数: {len(csv_race_ids):,}件")
print()

# 11月29-30日のレースIDがCSVに存在するかチェック
in_csv = [rid for rid in nov_29_30_ids if rid in csv_race_ids]
not_in_csv = [rid for rid in nov_29_30_ids if rid not in csv_race_ids]

print(f"CSV内に存在: {len(in_csv)}件")
print(f"CSV内に未存在: {len(not_in_csv)}件")
print()

if not_in_csv:
    print("未存在のレースID（最初の10件）:")
    for rid in sorted(not_in_csv)[:10]:
        print(f"  {rid}")
else:
    print("全て既にCSVに存在します")

print()
print("="*60)
