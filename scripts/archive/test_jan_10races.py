"""
2025年1月のレース10件テスト（実際の開催日ベース）
"""

from update_from_list import ListBasedUpdater
import os

# 進捗ファイルをクリア
for f in ['collection_progress.json', 'netkeiba_data_test.csv', 'horse_past_results_test.csv']:
    if os.path.exists(f):
        os.remove(f)

# 1月のレースIDを読み込み
with open('race_ids_2025_january_by_date.txt', 'r') as f:
    jan_races = [line.strip() for line in f if line.strip()]

print("="*60)
print(" 2025年1月レース10件テスト")
print("="*60)
print()
print(f"1月のレース総数: {len(jan_races)}件")
print()

# 最初の10件
test_races = jan_races[:10]

print("テスト対象（10件）:")
for i, rid in enumerate(test_races, 1):
    print(f"  {i}. {rid}")

print()
print("推定時間: 20-50分")
print()

# テスト用Updater
updater = ListBasedUpdater(
    db_path='netkeiba_data_test.csv',
    past_results_path='horse_past_results_test.csv'
)

print("収集開始...")
print()

# 馬統計付きで収集
updater._collect_races(test_races, collect_horse_details=True)

print()
print("="*60)
print(" テスト完了！")
print("="*60)
print()

# 結果確認
if os.path.exists('netkeiba_data_test.csv'):
    import pandas as pd
    df_test = pd.read_csv('netkeiba_data_test.csv', low_memory=False)

    races_collected = df_test['race_id'].unique()
    print(f"収集されたレース: {len(races_collected)}/{len(test_races)}件")
    print(f"収集された馬データ: {len(df_test)}行")
    print()

    # 統計列確認
    stat_cols = ['father', 'mother_father', 'total_starts', 'total_win_rate', 'total_earnings']
    print("統計列の状況:")
    for col in stat_cols:
        if col in df_test.columns:
            count = df_test[col].notna().sum()
            pct = count / len(df_test) * 100 if len(df_test) > 0 else 0
            print(f"  {col}: {count}/{len(df_test)} ({pct:.1f}%)")

    print()
    print("結果ファイル:")
    print("  - netkeiba_data_test.csv")
    print("  - horse_past_results_test.csv")
else:
    print("エラー: テストDBが作成されませんでした")
