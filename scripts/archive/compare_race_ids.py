"""
既存レースIDと生成されたレースIDの比較
"""
import pandas as pd

# 既存CSVから2025年レースID取得
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', encoding='utf-8', low_memory=False)
existing_2025 = set(df[df['race_id'].astype(str).str.startswith('2025')]['race_id'].astype(str).unique())

# race_ids.txtから生成レースID取得
with open('race_ids.txt', 'r') as f:
    generated = set(line.strip() for line in f)

print(f"既存2025年レース: {len(existing_2025)}")
print(f"生成されたレースID: {len(generated)}")

overlap = existing_2025.intersection(generated)
print(f"重複: {len(overlap)}")
print(f"既存にあるが生成されていない: {len(existing_2025 - generated)}")
print(f"生成されたが未実施: {len(generated - existing_2025)}")

print("\n既存レースID（最初の10件）:")
for rid in sorted(list(existing_2025))[:10]:
    print(f"  {rid}")

print("\n生成されたレースID（最初の10件）:")
for rid in sorted(list(generated))[:10]:
    print(f"  {rid}")

print("\n重複しているレースID（最初の10件）:")
for rid in sorted(list(overlap))[:10]:
    print(f"  {rid}")
