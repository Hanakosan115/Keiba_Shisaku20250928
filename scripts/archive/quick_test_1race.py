"""
1レースのみでクイックテスト（2-5分）
"""

import pandas as pd
from update_from_list import ListBasedUpdater
import os
import sys

# 出力バッファを無効化
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)

def main():
    print("="*60)
    print(" 1レースクイックテスト")
    print("="*60)
    print()

    # 既存CSVから1月の最初のレースIDを取得
    print("レースID取得中...")
    df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
    df['race_id_str'] = df['race_id'].astype(str)
    df_jan = df[df['race_id_str'].str.startswith('202501')]
    jan_race_ids = df_jan['race_id'].unique().tolist()

    if len(jan_race_ids) == 0:
        print("エラー: 1月のレースが見つかりません")
        return

    # 最初の1件
    test_race_id = jan_race_ids[0]

    print(f"テスト対象: {test_race_id}")
    print("推定時間: 2-5分")
    print()

    # 既存ファイル削除
    for f in ['netkeiba_data_test.csv', 'horse_past_results_test.csv', 'collection_progress.json']:
        if os.path.exists(f):
            os.remove(f)

    # テスト用Updater
    updater = ListBasedUpdater(
        db_path='netkeiba_data_test.csv',
        past_results_path='horse_past_results_test.csv'
    )

    print("収集開始...")
    print()

    # 1レースのみ収集
    updater._collect_races(
        [str(test_race_id)],
        collect_horse_details=True
    )

    print()
    print("="*60)
    print(" テスト完了！")
    print("="*60)
    print()

    # 結果確認
    if os.path.exists('netkeiba_data_test.csv'):
        df_test = pd.read_csv('netkeiba_data_test.csv', low_memory=False)
        print(f"収集された馬データ: {len(df_test)}行")
        print()

        # 統計列確認
        stat_cols = ['father', 'mother_father', 'total_starts', 'total_win_rate']
        print("統計列:")
        for col in stat_cols:
            if col in df_test.columns:
                count = df_test[col].notna().sum()
                print(f"  ✓ {col}: {count}/{len(df_test)}件")
            else:
                print(f"  ✗ {col}: なし")
    else:
        print("エラー: テストDBが作成されませんでした")

if __name__ == '__main__':
    main()
