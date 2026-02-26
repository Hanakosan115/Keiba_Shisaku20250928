"""
自動更新システムのテスト
最近1日分だけ試す
"""

from auto_update_latest import AutoLatestUpdater

print("="*60)
print("自動更新システム - テスト実行")
print("="*60)

updater = AutoLatestUpdater()

# テスト: 最近1日分だけスキャン
print("\nテスト: 最近1日分のレースをスキャン\n")

race_ids = updater.scan_recent_races(days_back=1)

print(f"\n発見したレース: {len(race_ids)}件")

if race_ids:
    print(f"\nサンプル（最初の10件）:")
    for i, race_id in enumerate(race_ids[:10], 1):
        print(f"  {i}. {race_id}")

    # 1件だけスクレイピングテスト
    if race_ids:
        print(f"\nスクレイピングテスト: {race_ids[0]}")
        df = updater.scrape_race_result(race_ids[0])

        if df is not None and len(df) > 0:
            print(f"[OK] 取得成功: {len(df)}頭")
            print(f"  レース名: {df.iloc[0]['race_name']}")
            print(f"  日付: {df.iloc[0]['date']}")
        else:
            print("[NG] 取得失敗")

print("\n" + "="*60)
print("テスト完了")
print("="*60)
