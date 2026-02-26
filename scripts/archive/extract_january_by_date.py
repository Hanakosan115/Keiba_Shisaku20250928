"""
実際の開催日から2025年1月のレースを抽出
"""

import pandas as pd

# CSVを読み込み
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

# 日付列を変換（エラーは無視）
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# 2025年1月のレースを抽出
df_jan = df[(df['date'] >= '2025-01-01') & (df['date'] < '2025-02-01')]

# ユニークなレースIDを取得
jan_races = df_jan['race_id'].unique()

print(f"2025年1月開催のレース: {len(jan_races)}件")
print()

if len(jan_races) > 0:
    print("サンプル（最初の10件）:")
    for i, rid in enumerate(jan_races[:10], 1):
        date_val = df_jan[df_jan['race_id']==rid]['date'].iloc[0]
        print(f"  {i}. {rid} - {date_val.strftime('%Y-%m-%d')}")

    print()

    # ファイルに保存
    filename = 'race_ids_2025_january_by_date.txt'
    with open(filename, 'w', encoding='utf-8') as f:
        for rid in jan_races:
            f.write(f"{rid}\n")

    print(f"ファイルに保存: {filename}")
    print()
    print("次のステップ:")
    print(f"  py update_from_list.py")
    print(f"  → オプション1")
    print(f"  → ファイル名: {filename}")
    print(f"  → 馬統計: y")
else:
    print("2025年1月のレースが見つかりませんでした")
    print()
    print("CSVのデータ範囲を確認:")
    df_2025 = df[df['date'].dt.year == 2025]
    if len(df_2025) > 0:
        print(f"  2025年のレース: {len(df_2025['race_id'].unique())}件")
        print(f"  期間: {df_2025['date'].min()} ～ {df_2025['date'].max()}")
    else:
        print("  2025年のデータが見つかりません")
