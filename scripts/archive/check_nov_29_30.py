"""
CSV内の11月29-30日データを確認
"""

import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

df['race_id_str'] = df['race_id'].astype(str)

nov_29 = df[df['race_id_str'].str.startswith('20251129')]
nov_30 = df[df['race_id_str'].str.startswith('20251130')]

print("="*60)
print("CSV内の11月29-30日データ")
print("="*60)
print()

print(f"11月29日のレース: {len(nov_29['race_id'].unique())}件")
print(f"11月30日のレース: {len(nov_30['race_id'].unique())}件")
print(f"\n合計: {len(nov_29['race_id'].unique()) + len(nov_30['race_id'].unique())}件")

if len(nov_29) > 0 or len(nov_30) > 0:
    print("\nレースID例（最初の20件）:")
    all_nov = pd.concat([nov_29, nov_30])
    for rid in sorted(all_nov['race_id'].astype(str).unique())[:20]:
        race_data = all_nov[all_nov['race_id'].astype(str) == rid].iloc[0]
        print(f"  {rid}: {race_data.get('race_name', 'N/A')}")
else:
    print("\n→ 11月29-30日のデータは存在しません")

print()
print("="*60)
