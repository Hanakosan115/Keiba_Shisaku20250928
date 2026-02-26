"""
未反映レースの自動更新

2,385件のレースを自動取得します
"""

from update_from_list import ListBasedUpdater
import time

print("="*60)
print("未反映レースの更新")
print("="*60)
print()
print("対象: 2,385件のレースID")
print("期間: 2019年1月 ～ 2025年8月")
print()
print("処理開始...")
print()

start_time = time.time()

updater = ListBasedUpdater()
updater.update_from_file('race_ids_missing.txt')

elapsed = time.time() - start_time
minutes = int(elapsed // 60)
seconds = int(elapsed % 60)

print(f"\n処理時間: {minutes}分{seconds}秒")
print("\n更新完了！")
