"""
2025年1月のレースに統計データを追加（強制更新）
既存の240レースに馬統計を追加します
推定時間: 8.8-18.8時間
"""

import sys
import os

print("="*60, flush=True)
print(" 2025年1月 統計データ追加（強制更新）", flush=True)
print("="*60, flush=True)
print(flush=True)

from update_from_list import ListBasedUpdater

# 進捗ファイルをクリア確認
if os.path.exists('collection_progress.json'):
    confirm = input("進捗ファイルが存在します。続きから再開しますか？ (y/n) [y]: ").strip().lower()
    if confirm == 'n':
        os.remove('collection_progress.json')
        print("進捗ファイルを削除しました", flush=True)
    else:
        print("進捗ファイルから再開します", flush=True)
print(flush=True)

# 1月のレースIDを読み込み
print("レースID読み込み中...", flush=True)
with open('race_ids_2025_january_by_date.txt', 'r') as f:
    jan_races = [line.strip() for line in f if line.strip()]

print(f"1月のレース総数: {len(jan_races)}件", flush=True)
print(flush=True)
print("モード: 強制更新（既存レースの統計追加）", flush=True)
print("推定時間: 8.8-18.8時間", flush=True)
print("※10レースごとに進捗保存されます", flush=True)
print("※Ctrl+Cで中断→再実行で続きから再開できます", flush=True)
print(flush=True)

confirm = input("実行しますか？ (y/n) [y]: ").strip().lower()

if confirm != 'n':
    print(flush=True)
    print("統計データ収集開始...", flush=True)
    print(flush=True)

    # メインDB用Updater
    updater = ListBasedUpdater(
        db_path='netkeiba_data_2020_2024_enhanced.csv',
        past_results_path='horse_past_results.csv'
    )

    # 強制更新モードで馬統計付きで収集
    updater._collect_races(
        jan_races,
        collect_horse_details=True,
        force_update=True  # 既存レースも再収集
    )

    print(flush=True)
    print("="*60, flush=True)
    print(" 統計データ追加完了！", flush=True)
    print("="*60, flush=True)
    print(flush=True)

    # 結果確認
    import pandas as pd
    df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df_jan = df[(df['date'] >= '2025-01-01') & (df['date'] < '2025-02-01')]

    print(f"1月のレース: {len(df_jan['race_id'].unique())}件", flush=True)
    print(f"1月の馬データ: {len(df_jan)}行", flush=True)
    print(flush=True)

    # 統計列確認
    stat_cols = ['father', 'mother_father', 'total_starts', 'total_win_rate',
                'turf_win_rate', 'dirt_win_rate', 'total_earnings']
    print("統計列の状況:", flush=True)
    for col in stat_cols:
        if col in df_jan.columns:
            count = df_jan[col].notna().sum()
            pct = count / len(df_jan) * 100 if len(df_jan) > 0 else 0
            print(f"  {col}: {count}/{len(df_jan)} ({pct:.1f}%)", flush=True)
        else:
            print(f"  {col}: 列なし", flush=True)
else:
    print("キャンセルされました", flush=True)
