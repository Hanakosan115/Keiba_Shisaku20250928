"""
超効率的更新システムのテスト
"""

from auto_update_smart import SmartAutoUpdater

print("="*60)
print("超効率的更新システム - テスト")
print("="*60)

updater = SmartAutoUpdater()

# 先週1週間分のスキャンテスト
race_ids = updater.scan_weekend_only(weeks_back=1)

print(f"\n発見: {len(race_ids)}レース")

if race_ids:
    print(f"\nサンプル（最初の5件）:")
    for i, race_id in enumerate(race_ids[:5], 1):
        print(f"  {i}. {race_id}")

print("\n" + "="*60)
