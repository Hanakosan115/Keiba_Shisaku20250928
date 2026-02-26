"""
2025年1月のレースIDを取得してテスト実行
"""

from update_from_list import ListBasedUpdater

def main():
    print("="*60)
    print(" 2025年1月レース収集（テスト用）")
    print("="*60)
    print()

    updater = ListBasedUpdater()

    # 2025年1月のレースIDを取得
    print("2025年1月の開催日を取得中...")
    race_ids = updater.collect_from_calendar(
        start_year=2025,
        start_month=1,
        end_year=2025,
        end_month=1,
        collect_horse_details=False  # まずレースIDのみ取得
    )

    print()
    print(f"取得したレースID: {len(race_ids)}件")

    if race_ids:
        # ファイルに保存
        filename = 'race_ids_2025_january.txt'
        with open(filename, 'w', encoding='utf-8') as f:
            for race_id in race_ids:
                f.write(f"{race_id}\n")

        print(f"ファイルに保存: {filename}")
        print()
        print("次のステップ:")
        print("1. CSVをバックアップ（念のため）")
        print("   copy netkeiba_data_2020_2024_enhanced.csv netkeiba_data_backup.csv")
        print()
        print("2. 1月のレースを馬統計付きで再収集")
        print("   py update_from_list.py")
        print("   → オプション1を選択")
        print(f"   → ファイル名: {filename}")
        print("   → 馬統計: y")

if __name__ == '__main__':
    main()
