"""
2025年1月レースでテスト実行（テスト用DB使用）
既存データに影響を与えずにテスト可能
"""

import pandas as pd
from update_from_list import ListBasedUpdater
import os

def main():
    print("="*60)
    print(" 2025年1月レース収集テスト")
    print("="*60)
    print()

    # 既存CSVから1月のレースIDを抽出
    print("既存CSVから2025年1月のレースIDを抽出中...")
    try:
        df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

        # 2025年1月のレースを抽出（race_idが202501で始まる）
        df['race_id_str'] = df['race_id'].astype(str)
        df_jan = df[df['race_id_str'].str.startswith('202501')]

        jan_race_ids = df_jan['race_id'].unique().tolist()

        print(f"2025年1月のレース: {len(jan_race_ids)}件")
        print()

        if len(jan_race_ids) == 0:
            print("エラー: 1月のレースが見つかりません")
            return

        # サンプル表示
        print("サンプル（最初の10件）:")
        for i, race_id in enumerate(jan_race_ids[:10], 1):
            print(f"  {i}. {race_id}")
        print()

        # テスト件数を選択
        print("テストする件数を選択:")
        print(f"  [1] 10件（推奨・クイックテスト）- 約20-50分")
        print(f"  [2] 50件（小規模テスト）- 約1.8-3.9時間")
        print(f"  [3] 全{len(jan_race_ids)}件（1月全件）")
        print()

        choice = input("選択 [1-3]: ").strip()

        if choice == '1':
            test_race_ids = jan_race_ids[:10]
            test_name = "10件テスト"
        elif choice == '2':
            test_race_ids = jan_race_ids[:50]
            test_name = "50件テスト"
        elif choice == '3':
            test_race_ids = jan_race_ids
            test_name = "1月全件"
        else:
            print("無効な選択です")
            return

        print()
        print(f"=== {test_name} ===")
        print(f"対象レース: {len(test_race_ids)}件")
        print()

        # テスト用DBを作成
        test_db = 'netkeiba_data_test.csv'

        if os.path.exists(test_db):
            confirm = input(f"{test_db} が既に存在します。上書きしますか？ (y/n) [y]: ").strip().lower()
            if confirm == 'n':
                print("キャンセルされました")
                return
            os.remove(test_db)

        print(f"テスト用DB: {test_db}")
        print()

        confirm = input("実行しますか？ (y/n) [y]: ").strip().lower()

        if confirm != 'n':
            # テスト用Updaterを作成（別DBを使用）
            updater = ListBasedUpdater(
                db_path=test_db,
                past_results_path='horse_past_results_test.csv'
            )

            # 馬統計付きで収集
            print()
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
            print(f"結果を確認:")
            print(f"  - レースデータ: {test_db}")
            print(f"  - 過去戦績: horse_past_results_test.csv")
            print()

            # 結果確認
            if os.path.exists(test_db):
                df_test = pd.read_csv(test_db, low_memory=False)
                print(f"収集されたレース: {len(df_test['race_id'].unique())}件")
                print(f"収集された馬データ: {len(df_test)}行")

                # 統計列の確認
                stat_cols = ['father', 'mother_father', 'total_starts', 'total_win_rate']
                available = [c for c in stat_cols if c in df_test.columns]

                if available:
                    print()
                    print("統計列の状況:")
                    for col in available:
                        count = df_test[col].notna().sum()
                        pct = count / len(df_test) * 100 if len(df_test) > 0 else 0
                        print(f"  {col}: {count}/{len(df_test)} ({pct:.1f}%)")
                else:
                    print()
                    print("警告: 統計列が見つかりません")
        else:
            print("キャンセルされました")

    except FileNotFoundError:
        print("エラー: netkeiba_data_2020_2024_enhanced.csv が見つかりません")
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
