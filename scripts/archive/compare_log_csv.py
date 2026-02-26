"""
ログファイルとCSVの比較
"""

import pandas as pd

# ログファイル読み込み
log_path = r'C:\Users\bu158\HorseRacingAnalyzer\data\processed_race_ids.log'
with open(log_path, 'r') as f:
    log_ids = set(line.strip() for line in f if line.strip())

# CSV読み込み
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
csv_ids = set(df['race_id'].astype(str).unique())

print("="*60)
print("ログファイルとCSVデータベースの比較")
print("="*60)

print(f"\nログファイルのレースID: {len(log_ids):,}件")
print(f"CSVのレースID: {len(csv_ids):,}件")

# 差分確認
in_log_not_csv = log_ids - csv_ids
in_csv_not_log = csv_ids - log_ids

print(f"\nログにあってCSVにない: {len(in_log_not_csv):,}件")
print(f"CSVにあってログにない: {len(in_csv_not_log):,}件")

if in_log_not_csv:
    print(f"\nサンプル（ログにあってCSVにない）:")
    for rid in sorted(list(in_log_not_csv))[:10]:
        print(f"  {rid}")

# 最新のレースID（ログ）
latest_log = max(log_ids)
print(f"\nログの最新レースID: {latest_log}")

# 最新のレースID（CSV）
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
latest_csv_idx = df['date_parsed'].idxmax()
latest_csv = df.loc[latest_csv_idx, 'race_id']
latest_csv_date = df.loc[latest_csv_idx, 'date_parsed']

print(f"CSVの最新レースID: {latest_csv}")
print(f"CSVの最新日付: {latest_csv_date.strftime('%Y-%m-%d')}")

print("\n" + "="*60)
