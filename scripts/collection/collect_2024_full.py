"""
2024年全レース収集（馬統計あり）
"""
import sys
sys.path.append('.')
from update_from_list import ListBasedUpdater

print("="*60)
print(" 2024年全レース収集（馬統計あり）")
print("="*60)
print()

# race_ids読み込み
with open('race_ids_2024.txt', 'r') as f:
    race_ids = [line.strip() for line in f if line.strip()]

print(f"対象レース数: {len(race_ids):,}件")
print()

# Updater初期化
updater = ListBasedUpdater(
    db_path='netkeiba_data_2020_2024_enhanced.csv',
    past_results_path='horse_past_results.csv'
)

# 収集実行
print("収集開始...")
print("  - 馬統計: ON")
print("  - 高速化モード: ON")
print()

updater._collect_races(
    race_ids,
    collect_horse_details=True,  # 馬統計あり
    force_update=False
)

print()
print("="*60)
print(" 2024年収集完了")
print("="*60)
