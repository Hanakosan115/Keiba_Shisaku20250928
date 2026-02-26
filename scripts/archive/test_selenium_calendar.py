"""
Selenium版カレンダー機能のテスト
"""

from update_from_list import ListBasedUpdater

print("="*60)
print("Selenium版カレンダー機能テスト")
print("="*60)
print()

updater = ListBasedUpdater()

# 2025年11月の開催日取得（requests版）
print("ステップ1: カレンダーから開催日取得（requests版）")
kaisai_dates = updater.get_kaisai_dates(2025, 11)

if kaisai_dates:
    print(f"[OK] 開催日: {len(kaisai_dates)}日")
    print(f"   {kaisai_dates[:3]}... 他{len(kaisai_dates)-3}日")
    print()

    # 最初の開催日のレースID取得（Selenium版）
    print(f"ステップ2: {kaisai_dates[0]} のレースID取得（Selenium版）")
    print(f"   ※ 初回はChromeDriver自動ダウンロードで時間がかかる場合があります")
    print()

    race_ids = updater.get_race_ids_for_date(kaisai_dates[0])

    if race_ids:
        print(f"[OK] レースID: {len(race_ids)}件取得成功！")
        print()
        print("取得したレースID:")
        for rid in race_ids:
            print(f"  - {rid}")
        print()
        print(f"{'='*60}")
        print("[SUCCESS] Selenium実装成功！カレンダー機能が使用可能です")
        print(f"{'='*60}")
    else:
        print("[FAIL] レースIDが取得できませんでした")
        print("   - ChromeDriverのセットアップを確認してください")
        print("   - Chromeブラウザがインストールされているか確認してください")
else:
    print("[FAIL] 開催日が取得できませんでした")
