"""
列名の正確な表現を確認（repr()で表示）
"""
import sys
sys.path.append('.')
from update_from_list import ListBasedUpdater
import pandas as pd

updater = ListBasedUpdater()

# テストレース
test_race_id = '202405010101'

print(f"Testing race_id: {test_race_id}")
print()

df = updater.scrape_race_result(test_race_id, collect_horse_details=False)

if df is not None and len(df) > 0:
    print(f"Rows: {len(df)}")
    print()

    # 列名をrepr()で表示（エンコーディング問題を検出）
    with open('column_names_output.txt', 'w', encoding='utf-8') as f:
        f.write(f"Total rows: {len(df)}\n")
        f.write(f"Total columns: {len(df.columns)}\n\n")
        f.write("Column names (with repr):\n")
        for i, col in enumerate(df.columns, 1):
            f.write(f"{i:2d}. {col} | repr: {repr(col)}\n")

        f.write("\n\nChecking deduplication logic:\n")
        f.write(f"'馬番' in df.columns: {'馬番' in df.columns}\n")
        f.write(f"'Umaban' in df.columns: {'Umaban' in df.columns}\n")

        f.write("\n\nColumns containing '馬' or '番':\n")
        for col in df.columns:
            if '馬' in col or '番' in col:
                f.write(f"  - {col} | repr: {repr(col)}\n")
                f.write(f"    Sample values: {df[col].head(3).tolist()}\n")

    print("Output written to: column_names_output.txt")
    print()

    # Critical check
    print("Deduplication check:")
    print(f"  '馬番' in df.columns: {'馬番' in df.columns}")
    print(f"  'Umaban' in df.columns: {'Umaban' in df.columns}")

else:
    print("Failed to scrape data")
