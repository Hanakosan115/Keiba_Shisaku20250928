"""
update_from_list.py のテスト実行
"""

from update_from_list import ListBasedUpdater

print("="*60)
print("データ更新テスト")
print("="*60)

updater = ListBasedUpdater()
updater.update_from_file('race_ids_test.txt')

print("\n" + "="*60)
print("テスト完了")
print("="*60)
