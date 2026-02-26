"""
2025年9月～12月のデータ更新

注意: 241,920件のIDをチェックするため、かなり時間がかかります
      実在しないレースはスキップされます
"""

from update_from_list import ListBasedUpdater
import time

print("="*60)
print("2025年9月～12月のデータ更新")
print("="*60)
print()
print("注意: 241,920件のレースIDをチェックします")
print("      実在するレースのみ取得します")
print("      かなり時間がかかる可能性があります")
print()

input("準備ができたらEnterキーを押してください...")

start_time = time.time()

updater = ListBasedUpdater()
updater.update_from_file('race_ids_202509-12.txt')

elapsed = time.time() - start_time
minutes = int(elapsed // 60)
seconds = int(elapsed % 60)

print(f"\n処理時間: {minutes}分{seconds}秒")
print("\n処理完了！")
input("\nEnterキーを押して終了...")
