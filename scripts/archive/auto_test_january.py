"""
2025年1月レース10件自動テスト
"""

import pandas as pd
from update_from_list import ListBasedUpdater
import os

def main():
    print("="*60)
    print(" 2025年1月レース10件自動テスト")
    print("="*60)
    print()

    # 既存CSVから1月のレースIDを抽出
    print("既存CSVから2025年1月のレースIDを抽出中...")
    try:
        df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

        # 2025年1月のレースを抽出
        df['race_id_str'] = df['race_id'].astype(str)
        df_jan = df[df['race_id_str'].str.startswith('202501')]

        jan_race_ids = df_jan['race_id'].unique().tolist()

        print(f"2025年1月のレース: {len(jan_race_ids)}件")
        print()

        if len(jan_race_ids) == 0:
            print("エラー: 1月のレースが見つかりません")
            return

        # 最初の10件を使用
        test_race_ids = jan_race_ids[:10]

        print("テスト対象（10件）:")
        for i, race_id in enumerate(test_race_ids, 1):
            print(f"  {i}. {race_id}")
        print()

        # テスト用DB
        test_db = 'netkeiba_data_test.csv'

        if os.path.exists(test_db):
            print(f"既存の{test_db}を削除...")
            os.remove(test_db)

        if os.path.exists('horse_past_results_test.csv'):
            os.remove('horse_past_results_test.csv')

        if os.path.exists('collection_progress.json'):
            os.remove('collection_progress.json')

        print(f"テスト用DB: {test_db}")
        print("推定時間: 20-50分")
        print()

        # テスト用Updaterを作成
        updater = ListBasedUpdater(
            db_path=test_db,
            past_results_path='horse_past_results_test.csv'
        )

        # 馬統計付きで収集
        print("馬統計データ付きで収集開始...")
        print()

        updater._collect_races(
            [str(rid) for rid in test_race_ids],
            collect_horse_details=True
        )

        print()
        print("="*60)
        print(" テスト完了！")
        print("="*60)
        print()

        # 結果確認
        if os.path.exists(test_db):
            df_test = pd.read_csv(test_db, low_memory=False)
            print(f"収集されたレース: {len(df_test['race_id'].unique())}件")
            print(f"収集された馬データ: {len(df_test)}行")
            print()

            # 統計列の確認
            stat_cols = ['father', 'mother_father', 'total_starts', 'total_win_rate',
                        'turf_win_rate', 'dirt_win_rate', 'total_earnings']

            print("統計列の状況:")
            for col in stat_cols:
                if col in df_test.columns:
                    count = df_test[col].notna().sum()
                    pct = count / len(df_test) * 100 if len(df_test) > 0 else 0
                    print(f"  {col}: {count}/{len(df_test)} ({pct:.1f}%)")
                else:
                    print(f"  {col}: 列なし")

            print()
            print("結果ファイル:")
            print(f"  - {test_db}")
            print(f"  - horse_past_results_test.csv")
            print()
            print("問題なければ、本番実行に進めます！")

    except FileNotFoundError:
        print("エラー: netkeiba_data_2020_2024_enhanced.csv が見つかりません")
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
