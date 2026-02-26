"""
既存データの確認
"""
import pandas as pd
import os

files_to_check = [
    r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202510.csv",
    r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202511.csv",
]

print("=" * 80)
print("既存データファイルの確認")
print("=" * 80)

for filepath in files_to_check:
    filename = os.path.basename(filepath)
    print(f"\n[{filename}]")

    if not os.path.exists(filepath):
        print("  ファイルが存在しません")
        continue

    # ファイルサイズ
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"  サイズ: {size_mb:.2f} MB")

    try:
        # データ読み込み
        df = pd.read_csv(filepath, low_memory=False)
        print(f"  総行数: {len(df):,}")

        # 日付解析
        df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
        valid_dates = df[df['date_parsed'].notna()]

        if len(valid_dates) > 0:
            print(f"  日付範囲: {valid_dates['date_parsed'].min()} ～ {valid_dates['date_parsed'].max()}")

            # 2024年データ
            df_2024 = df[df['date_parsed'] >= '2024-01-01']
            print(f"  2024年データ: {len(df_2024):,}行")

            # 2025年データ
            df_2025 = df[df['date_parsed'] >= '2025-01-01']
            print(f"  2025年データ: {len(df_2025):,}行")

            if len(df_2025) > 0:
                print(f"    → 2025年範囲: {df_2025['date_parsed'].min()} ～ {df_2025['date_parsed'].max()}")
        else:
            print("  日付データが正しく解析できませんでした")

    except Exception as e:
        print(f"  エラー: {e}")

print("\n" + "=" * 80)
print("結論")
print("=" * 80)

print("""
次のステップ:
1. 上記のファイルに2025年データがあるか確認
2. 2025年データがあれば → update_main_data.py で直接マージ
3. 2025年データがなければ → 元ツールで新規スクレイピングが必要
""")
