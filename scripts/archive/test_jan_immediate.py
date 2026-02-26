"""
2025年1月のレース10件テスト（即時出力版）
"""

import sys
import os

# 即座に出力
print("スクリプト開始", flush=True)

from update_from_list import ListBasedUpdater

print("モジュールインポート完了", flush=True)

# 進捗ファイルをクリア
for f in ['collection_progress.json', 'netkeiba_data_test.csv', 'horse_past_results_test.csv']:
    if os.path.exists(f):
        os.remove(f)
        print(f"削除: {f}", flush=True)

# 1月のレースIDを読み込み
print("レースID読み込み中...", flush=True)
with open('race_ids_2025_january_by_date.txt', 'r') as f:
    jan_races = [line.strip() for line in f if line.strip()]

print(f"読み込み完了: {len(jan_races)}件", flush=True)
print("="*60, flush=True)
print(" 2025年1月レース10件テスト", flush=True)
print("="*60, flush=True)

# 最初の10件
test_races = jan_races[:10]

print("\nテスト対象（10件）:", flush=True)
for i, rid in enumerate(test_races, 1):
    print(f"  {i}. {rid}", flush=True)

print("\n推定時間: 20-50分", flush=True)
print("収集開始...\n", flush=True)

# テスト用Updater
updater = ListBasedUpdater(
    db_path='netkeiba_data_test.csv',
    past_results_path='horse_past_results_test.csv'
)

# 馬統計付きで収集
updater._collect_races(test_races, collect_horse_details=True)

print("\n" + "="*60, flush=True)
print(" テスト完了！", flush=True)
print("="*60, flush=True)

# 結果確認
if os.path.exists('netkeiba_data_test.csv'):
    import pandas as pd
    df_test = pd.read_csv('netkeiba_data_test.csv', low_memory=False)

    races_collected = df_test['race_id'].unique()
    print(f"\n収集されたレース: {len(races_collected)}/{len(test_races)}件", flush=True)
    print(f"収集された馬データ: {len(df_test)}行", flush=True)

    # 統計列確認
    stat_cols = ['father', 'mother_father', 'total_starts', 'total_win_rate', 'total_earnings']
    print("\n統計列の状況:", flush=True)
    for col in stat_cols:
        if col in df_test.columns:
            count = df_test[col].notna().sum()
            pct = count / len(df_test) * 100 if len(df_test) > 0 else 0
            print(f"  {col}: {count}/{len(df_test)} ({pct:.1f}%)", flush=True)

    print("\n結果ファイル:", flush=True)
    print("  - netkeiba_data_test.csv", flush=True)
    print("  - horse_past_results_test.csv", flush=True)
else:
    print("\nエラー: テストDBが作成されませんでした", flush=True)

print("\n処理完了！", flush=True)
