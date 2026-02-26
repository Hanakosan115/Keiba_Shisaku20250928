"""
カレンダー機能のテスト
11月の開催日とレースIDを取得するだけ（データ収集はしない）
"""

from update_from_list import ListBasedUpdater

print("="*60)
print("カレンダー機能テスト")
print("="*60)

updater = ListBasedUpdater()

# 2025年11月の開催日取得
print("\n2025年11月の開催日を取得中...")
kaisai_dates = updater.get_kaisai_dates(2025, 11)

if kaisai_dates:
    print(f"\n開催日: {len(kaisai_dates)}日")
    for date in kaisai_dates[:5]:  # 最初の5日だけ表示
        print(f"  - {date}")

    if len(kaisai_dates) > 5:
        print(f"  ... 他 {len(kaisai_dates) - 5}日")

    # 最初の開催日のレースID取得
    print(f"\n{kaisai_dates[0]} のレースIDを取得中...")
    race_ids = updater.get_race_ids_for_date(kaisai_dates[0])

    if race_ids:
        print(f"\nレースID: {len(race_ids)}件")
        for rid in race_ids:
            print(f"  - {rid}")
    else:
        print("\nレースIDが取得できませんでした")
else:
    print("\n開催日が見つかりませんでした")

print(f"\n{'='*60}")
print("テスト完了")
print(f"{'='*60}")
