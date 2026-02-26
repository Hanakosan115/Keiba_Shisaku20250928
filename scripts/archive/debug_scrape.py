"""
スクレイピングのデバッグ
"""

from update_from_list import ListBasedUpdater

updater = ListBasedUpdater()

race_id = '202505050812'

print(f"レースID: {race_id}")
print("スクレイピング中...\n")

df = updater.scrape_race_result(race_id)

if df is not None:
    print(f"成功: {len(df)}頭")
    print(f"\nデータ:")
    print(df.head())
else:
    print("失敗: Noneが返された")
