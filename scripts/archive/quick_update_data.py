"""
クイックデータ更新
2024年8月以降の最近のレースを取得
"""

from smart_update_system_v2 import SmartUpdaterV2
from datetime import datetime

print("="*80)
print("データベースクイック更新")
print("="*80)

updater = SmartUpdaterV2()

print("\n現在のデータベース状況:")
last_date = updater.get_last_update_date()

print(f"\n2024年8月以降のデータを取得します")
print("これには時間がかかります（20-30分程度）")
print()

choice = input("続行しますか？ (y/n): ").strip().lower()

if choice == 'y':
    # 2024年8月以降の主要レースを手動で指定
    # より確実な方法として、いくつかの確実なレースIDを指定
    print("\n主要なG1レース等を含む最近のデータを取得します...")

    # 8月〜12月の土日のレースIDを生成
    # より広い範囲で試す
    import re
    from datetime import timedelta

    # 2024年8月1日から現在まで
    start_date = datetime(2024, 8, 1)
    end_date = datetime(2024, 12, 7)

    print(f"期間: {start_date.date()} 〜 {end_date.date()}")

    # レースID候補を生成
    candidate_ids = updater.get_race_ids_in_period(start_date, end_date)

    print(f"\n生成されたレースID候補: {len(candidate_ids)}件")

    # 最大100レース取得（テスト的に）
    updater.update_database(target_race_ids=candidate_ids, max_races=100)

else:
    print("\nキャンセルしました")
