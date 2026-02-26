"""
未反映レースの更新実行

2,385件のレースを取得します
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
print("注意: 数時間かかる可能性があります")
print("      10件ごとにDB保存します")
print()

input("準備ができたらEnterキーを押してください...")

start_time = time.time()

updater = ListBasedUpdater()
updater.update_from_file('race_ids_missing.txt')

elapsed = time.time() - start_time
minutes = int(elapsed // 60)
seconds = int(elapsed % 60)

print(f"\n処理時間: {minutes}分{seconds}秒")
print("\n更新完了！")
input("\nEnterキーを押して終了...")
