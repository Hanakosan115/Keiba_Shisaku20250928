"""
期間指定データ収集スクリプト
使用例:
  py collect_by_period.py --year 2025 --month 2
  py collect_by_period.py --year 2024 --month all
  py collect_by_period.py --year 2023 --month 1-6
"""

import sys
import os
import argparse
import pandas as pd
from update_from_list import ListBasedUpdater

def main():
    parser = argparse.ArgumentParser(description='期間指定データ収集')
    parser.add_argument('--year', type=int, required=True, help='収集年 (例: 2025)')
    parser.add_argument('--month', type=str, default='all',
                       help='収集月 (例: 2, all, 1-6)')
    parser.add_argument('--force', action='store_true',
                       help='既存データも強制再収集')
    parser.add_argument('--stats-only', action='store_true',
                       help='統計データのみ追加（馬詳細を収集）')

    args = parser.parse_args()

    year = args.year
    month = args.month
    force_update = args.force
    collect_stats = args.stats_only or True  # デフォルトで統計収集

    print("="*60)
    print(f" データ収集: {year}年 {month}月")
    print("="*60)
    print()

    # データベース読み込み
    db_path = 'netkeiba_data_2020_2024_enhanced.csv'
    if not os.path.exists(db_path):
        print(f"エラー: {db_path} が見つかりません")
        sys.exit(1)

    print("データベース読み込み中...")
    df = pd.read_csv(db_path, low_memory=False)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # 期間でフィルター
    if month == 'all':
        df_target = df[df['date'].dt.year == year]
        month_str = "全月"
    elif '-' in str(month):
        # 範囲指定 (例: 1-6)
        start_month, end_month = map(int, month.split('-'))
        df_target = df[(df['date'].dt.year == year) &
                       (df['date'].dt.month >= start_month) &
                       (df['date'].dt.month <= end_month)]
        month_str = f"{start_month}月～{end_month}月"
    else:
        # 単月指定
        month_int = int(month)
        df_target = df[(df['date'].dt.year == year) &
                       (df['date'].dt.month == month_int)]
        month_str = f"{month_int}月"

    # レースID抽出
    race_ids = df_target['race_id'].unique().tolist()

    if len(race_ids) == 0:
        print(f"対象レースが見つかりません: {year}年{month_str}")
        sys.exit(1)

    print(f"\n対象レース数: {len(race_ids)}件")
    print(f"モード: {'強制更新' if force_update else '新規のみ'}")
    print(f"統計収集: {'ON' if collect_stats else 'OFF'}")
    print()

    # 統計データ状況確認
    if len(df_target) > 0:
        with_stats = df_target['total_starts'].notna().sum()
        stats_rate = (with_stats / len(df_target) * 100) if len(df_target) > 0 else 0
        print(f"現在の統計データ率: {stats_rate:.1f}% ({with_stats}/{len(df_target)})")
        print()

    # 推定時間計算
    # 1レースあたり平均3.5分（馬統計あり）、1分（馬統計なし）
    time_per_race = 3.5 if collect_stats else 1.0
    estimated_hours = (len(race_ids) * time_per_race) / 60

    print(f"推定所要時間: {estimated_hours:.1f}時間")
    print()

    confirm = input("実行しますか？ (y/n) [y]: ").strip().lower()

    if confirm == 'n':
        print("キャンセルしました")
        sys.exit(0)

    print()
    print("収集開始...")
    print()

    # Updater初期化
    updater = ListBasedUpdater(
        db_path=db_path,
        past_results_path='horse_past_results.csv'
    )

    # 収集実行
    updater._collect_races(
        race_ids,
        collect_horse_details=collect_stats,
        force_update=force_update
    )

    print()
    print("="*60)
    print(" 収集完了！")
    print("="*60)
    print()

    # 結果確認
    df_final = pd.read_csv(db_path, low_memory=False)
    df_final['date'] = pd.to_datetime(df_final['date'], errors='coerce')

    if month == 'all':
        df_result = df_final[df_final['date'].dt.year == year]
    elif '-' in str(month):
        start_month, end_month = map(int, month.split('-'))
        df_result = df_final[(df_final['date'].dt.year == year) &
                            (df_final['date'].dt.month >= start_month) &
                            (df_final['date'].dt.month <= end_month)]
    else:
        month_int = int(month)
        df_result = df_final[(df_final['date'].dt.year == year) &
                            (df_final['date'].dt.month == month_int)]

    print(f"結果:")
    print(f"  レース数: {df_result['race_id'].nunique()}件")
    print(f"  馬データ行数: {len(df_result):,}行")

    if collect_stats:
        stat_cols = ['father', 'mother_father', 'total_starts',
                     'total_win_rate', 'total_earnings']
        print(f"\n統計列カバー率:")
        for col in stat_cols:
            if col in df_result.columns:
                count = df_result[col].notna().sum()
                pct = count / len(df_result) * 100 if len(df_result) > 0 else 0
                print(f"  {col}: {pct:.1f}% ({count}/{len(df_result)})")

if __name__ == '__main__':
    main()
