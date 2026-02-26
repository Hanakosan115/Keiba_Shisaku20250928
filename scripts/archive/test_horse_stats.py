"""
馬統計情報込みスクレイピングテスト
"""

import os
import pandas as pd
from update_from_list import ListBasedUpdater

print("="*60)
print("馬統計情報込みスクレイピングテスト")
print("="*60)

# テストファイルを削除
for f in ['test_horse_stats.csv', 'test_past_results.csv']:
    if os.path.exists(f):
        os.remove(f)
        print(f"削除: {f}")

# スクレイパー初期化
updater = ListBasedUpdater(
    db_path='test_horse_stats.csv',
    past_results_path='test_past_results.csv'
)

# テストレースID
race_id = '202507050211'
print(f"\nレースID: {race_id} をスクレイピング中...")
print("※ 16頭分の馬詳細情報と過去戦績を取得します（時間がかかります）\n")

# スクレイピング実行
df = updater.scrape_race_result(race_id, collect_horse_details=True)

if df is not None and len(df) > 0:
    print(f"\nスクレイピング成功！")
    print(f"  レコード数: {len(df)}")
    print(f"  列数: {len(df.columns)}")

    # CSV保存
    df.to_csv('test_horse_stats.csv', index=False, encoding='utf-8-sig')
    print(f"\nメインCSV保存: test_horse_stats.csv")

    # 統計値列の確認
    stat_cols = [
        'father', 'mother_father',
        'total_starts', 'total_win_rate',
        'turf_win_rate', 'dirt_win_rate',
        'distance_similar_win_rate',
        'grade_race_starts', 'is_local_transfer',
        'running_style_category',
        'prev_race_rank', 'prev_race_distance',
        'days_since_last_race',
        'total_earnings'
    ]

    print(f"\n統計値列の確認:")
    for col in stat_cols:
        if col in df.columns:
            non_null = df[col].notna().sum()
            print(f"  {col}: {non_null}/{len(df)} 取得")

    # サンプルデータ表示（1頭目）
    print(f"\nサンプルデータ（1頭目: ダブルハートボンド）:")
    first_horse = df.iloc[0]
    display_cols = [
        '馬名', 'father', 'mother_father',
        'total_starts', 'total_win_rate',
        'turf_win_rate', 'dirt_win_rate',
        'running_style_category',
        'prev_race_rank', 'grade_race_starts'
    ]
    for col in display_cols:
        if col in df.columns:
            val = first_horse[col]
            print(f"  {col}: {val}")

    # 過去戦績CSVの確認
    if os.path.exists('test_past_results.csv'):
        past_df = pd.read_csv('test_past_results.csv', encoding='utf-8-sig')
        print(f"\n過去戦績CSV:")
        print(f"  ファイル: test_past_results.csv")
        print(f"  過去レース数: {len(past_df)}")
        print(f"  列数: {len(past_df.columns)}")

        # ユニーク馬数
        unique_horses = past_df['horse_id'].nunique() if 'horse_id' in past_df.columns else 0
        print(f"  馬数: {unique_horses}")

    print(f"\n{'='*60}")
    print("テスト完了！")
    print(f"{'='*60}")

else:
    print(f"\nスクレイピング失敗")
