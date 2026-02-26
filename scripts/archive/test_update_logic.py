"""
更新ロジックのテスト（10レース）
"""

import sys
import os

print("="*60)
print(" 更新ロジックテスト（10レース）")
print("="*60)
print()

from update_from_list import ListBasedUpdater

# 進捗ファイルクリア
for f in ['collection_progress.json']:
    if os.path.exists(f):
        os.remove(f)

# 1月のレースIDから10件
with open('race_ids_2025_january_by_date.txt', 'r') as f:
    jan_races = [line.strip() for line in f if line.strip()][:10]

print(f"テスト対象: {len(jan_races)}件")
print("モード: 強制更新（force_update=True）")
print()

# メインDB用Updater
updater = ListBasedUpdater(
    db_path='netkeiba_data_2020_2024_enhanced.csv',
    past_results_path='horse_past_results.csv'
)

print("収集開始...")
print()

# 強制更新モードで実行
updater._collect_races(
    jan_races,
    collect_horse_details=True,
    force_update=True
)

print()
print("="*60)
print(" テスト完了！")
print("="*60)
print()

# 結果確認
import pandas as pd
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

# テスト対象レースのデータを確認
test_race_ids = set(jan_races)
df_test = df[df['race_id'].astype(str).isin(test_race_ids)]

print(f"テスト対象レース: {len(df_test['race_id'].unique())}/{len(jan_races)}件")
print(f"馬データ行数: {len(df_test)}行")
print()

# 統計列確認
stat_cols = ['father', 'mother_father', 'total_starts', 'total_win_rate', 'total_earnings']
print("統計列:")
for col in stat_cols:
    if col in df_test.columns:
        count = df_test[col].notna().sum()
        pct = count / len(df_test) * 100 if len(df_test) > 0 else 0
        print(f"  {col}: {count}/{len(df_test)} ({pct:.1f}%)")
    else:
        print(f"  {col}: 列なし")
