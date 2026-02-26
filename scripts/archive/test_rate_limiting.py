"""
レート制限機能のテストスクリプト
少数のレースで動作確認を行う
"""

from update_from_list import ListBasedUpdater
import pandas as pd

def main():
    print("="*60)
    print(" レート制限機能テスト")
    print("="*60)
    print()
    print("少数のレースでテスト実行します")
    print()

    # 既存の2025年レースIDから10件取得
    updater = ListBasedUpdater()

    # CSVから2025年のレースIDを取得
    try:
        df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
        df_2025 = df[df['race_id'].astype(str).str.startswith('2025')]

        # ランダムに10件選択
        sample_races = df_2025['race_id'].sample(n=min(10, len(df_2025))).tolist()

        print(f"テスト対象レース: {len(sample_races)}件")
        print()

        for i, race_id in enumerate(sample_races, 1):
            print(f"{i}. {race_id}")

        print()
        print("これらのレースで馬統計データを収集します")
        print("推定時間: 約20-50分")
        print()

        confirm = input("実行しますか？ (y/n) [y]: ").strip().lower()

        if confirm != 'n':
            # 馬統計データ収集
            updater._collect_races(
                [str(rid) for rid in sample_races],
                collect_horse_details=True
            )
        else:
            print("キャンセルされました")

    except FileNotFoundError:
        print("エラー: netkeiba_data_2020_2024_enhanced.csv が見つかりません")
        print()
        print("代わりに手動でレースIDを指定してください:")
        print()

        # 手動入力モード
        race_ids_input = input("レースIDをカンマ区切りで入力: ").strip()

        if race_ids_input:
            race_ids = [rid.strip() for rid in race_ids_input.split(',')]
            print(f"\nテスト対象: {len(race_ids)}件")

            updater._collect_races(race_ids, collect_horse_details=True)
        else:
            print("キャンセルされました")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
