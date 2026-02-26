"""
CSVファイルの構造を確認するスクリプト
"""
import pandas as pd
import os

data_dir = r"C:\Users\bu158\HorseRacingAnalyzer\data"

# CSVファイルを探す
csv_files = []
for file in os.listdir(data_dir):
    if file.endswith('.csv') and 'combined' in file:
        csv_files.append(os.path.join(data_dir, file))

if csv_files:
    print(f"CSVファイル: {os.path.basename(csv_files[0])}")
    print("=" * 60)

    # 最初の数行を読み込む
    df = pd.read_csv(csv_files[0], encoding='utf-8', nrows=100)

    print(f"\n総行数（サンプル）: {len(df)}")
    print(f"\n列名一覧:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i}. {col}")

    print(f"\n\nデータの先頭3行:")
    print(df.head(3))

    print(f"\n\n重要な列の値の例:")
    if 'race_id' in df.columns:
        print(f"race_id: {df['race_id'].iloc[0]}")
    if 'Rank' in df.columns:
        print(f"Rank: {df['Rank'].iloc[0]}")
    if 'rank' in df.columns:
        print(f"rank: {df['rank'].iloc[0]}")
    if 'odds' in df.columns:
        print(f"odds: {df['odds'].iloc[0]}")
    if 'Odds' in df.columns:
        print(f"Odds: {df['Odds'].iloc[0]}")
    if 'umaban' in df.columns:
        print(f"umaban: {df['umaban'].iloc[0]}")
    if 'Umaban' in df.columns:
        print(f"Umaban: {df['Umaban'].iloc[0]}")

    # ユニークなrace_idの数を確認
    if 'race_id' in df.columns:
        unique_races = df['race_id'].nunique()
        print(f"\n\nサンプル内のユニークなレース数: {unique_races}")
else:
    print("CSVファイルが見つかりません")

input("\nEnterキーで終了...")
