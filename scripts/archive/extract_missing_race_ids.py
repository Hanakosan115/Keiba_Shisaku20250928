"""
ログにあってCSVにないレースIDを抽出
"""

import pandas as pd

print("="*60)
print("未反映レースID抽出")
print("="*60)

# ログファイル読み込み
log_path = r'C:\Users\bu158\HorseRacingAnalyzer\data\processed_race_ids.log'
with open(log_path, 'r', encoding='utf-8') as f:
    log_ids = set(line.strip() for line in f if line.strip() and line.strip().isdigit())

print(f"ログのレースID: {len(log_ids):,}件")

# CSV読み込み
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
csv_ids = set(df['race_id'].astype(str).unique())
# NaNや文字化けを除外
csv_ids = set(rid for rid in csv_ids if isinstance(rid, str) and rid.isdigit() and len(rid) == 12)

print(f"CSVのレースID: {len(csv_ids):,}件")

# 差分
missing_ids = log_ids - csv_ids

print(f"\n未反映レース: {len(missing_ids):,}件")

if missing_ids:
    # ファイルに保存
    output_file = 'race_ids_missing.txt'
    with open(output_file, 'w', encoding='utf-8') as f:
        for race_id in sorted(missing_ids):
            f.write(f"{race_id}\n")

    print(f"\n{output_file} に保存しました")

    # サンプル表示
    print(f"\nサンプル（最初の10件）:")
    for i, race_id in enumerate(sorted(missing_ids)[:10], 1):
        print(f"  {i}. {race_id}")

    print(f"\n最新のレースID: {max(missing_ids)}")
    print(f"最古のレースID: {min(missing_ids)}")
else:
    print("\n差分なし！全て最新です")

print("\n" + "="*60)
print("次のステップ:")
print("  py update_from_list.py を実行")
print("  （ファイル名を race_ids_missing.txt に変更）")
print("="*60)
