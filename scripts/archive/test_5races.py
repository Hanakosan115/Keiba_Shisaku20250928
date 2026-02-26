"""
修正版で5レーステスト（全馬データ確認）
"""
import sys
sys.path.append('.')
from update_from_list import ListBasedUpdater
import pandas as pd

print("="*60)
print(" 5レース収集テスト（高速化版）")
print("="*60)
print()

# テスト用レースID（2024年5月東京）
test_race_ids = [
    '202405010101',
    '202405010102',
    '202405010103',
    '202405010104',
    '202405010105',
]

print(f"テストレース: {len(test_race_ids)}件")
print()

# Updater初期化
updater = ListBasedUpdater(
    db_path='netkeiba_data_2020_2024_enhanced.csv',
    past_results_path='horse_past_results.csv'
)

# 収集実行（馬統計なし - 高速テスト）
print("収集開始（馬統計なし）...")
print()

updater._collect_races(
    test_race_ids,
    collect_horse_details=False,  # 高速テスト用
    force_update=False
)

print()
print("="*60)
print(" 結果確認")
print("="*60)
print()

# 結果確認
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

print(f"総行数: {len(df):,}行")
print(f"総レース数: {df['race_id'].nunique()}件")
print()

print("レース別行数:")
for race_id in test_race_ids:
    race_df = df[df['race_id'] == race_id]
    print(f"  {race_id}: {len(race_df)}行")

print()
print("列名確認:")
key_cols = ['race_id', 'Umaban', '馬番', 'HorseName', '馬名', 'Rank']
for col in key_cols:
    if col in df.columns:
        print(f"  ✓ {col}")
    else:
        print(f"  ✗ {col}")

print()

# サンプルデータ表示
print("サンプルデータ（最初のレース）:")
first_race = df[df['race_id'] == test_race_ids[0]]
if len(first_race) > 0:
    display_cols = [col for col in ['race_id', 'Rank', '馬番', 'HorseName', 'Odds_x'] if col in first_race.columns]
    print(first_race[display_cols].head(10))
else:
    print("  データなし")

print()
print("="*60)
print(" テスト完了")
print("="*60)
