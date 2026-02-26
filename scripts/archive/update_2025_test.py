"""
2025年9月の最初の1週末だけテスト

まずこれで動作確認してから、全体を実行
"""

from update_from_list import ListBasedUpdater

print("="*60)
print("2025年9月 第1週末のデータ取得テスト")
print("="*60)

# 9月第1週末のレースIDだけ抽出
with open('race_ids_202509-12.txt', 'r', encoding='utf-8') as f:
    all_ids = [line.strip() for line in f if line.strip()]

# 9月6-7日のレースID（最初の週末）
test_ids = [rid for rid in all_ids if rid.startswith('20250906') or rid.startswith('20250907')]

print(f"\nテスト対象: {len(test_ids)}件のレースID")
print("（9月6-7日の全パターン）")

# 一時ファイルに保存
with open('race_ids_test_sep.txt', 'w', encoding='utf-8') as f:
    for rid in test_ids:
        f.write(f"{rid}\n")

print("\nrace_ids_test_sep.txt に保存しました")
print("\n実行中...")

updater = ListBasedUpdater()
updater.update_from_file('race_ids_test_sep.txt')

print("\n" + "="*60)
print("テスト完了！")
print("="*60)
print("\n結果が良ければ、update_2025_sep_dec.py で全期間を実行してください")
print("（ただし全期間は非常に時間がかかります）")
