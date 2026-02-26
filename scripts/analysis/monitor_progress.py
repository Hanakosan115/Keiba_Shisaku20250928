"""
リアルタイム進捗モニター
"""
import pandas as pd
import os
import json
from datetime import datetime

print("="*60)
print(" 収集進捗モニター")
print("="*60)
print(f" 確認時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*60)
print()

# データベース状態
if os.path.exists('netkeiba_data_2020_2024_enhanced.csv'):
    df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
    total_rows = len(df)
    total_races = df['race_id'].nunique()

    print("[DATABASE]")
    print(f"  Total rows: {total_rows:,}")
    print(f"  Total races: {total_races:,}")

    # 統計データカバー率
    if 'total_starts' in df.columns:
        stats_coverage = df['total_starts'].notna().sum() / len(df) * 100
        print(f"  Stats coverage: {stats_coverage:.1f}%")
else:
    print("[DATABASE] Not created yet")
    total_races = 0

print()

# 進捗ファイル
if os.path.exists('collection_progress.json'):
    with open('collection_progress.json', 'r', encoding='utf-8') as f:
        progress = json.load(f)

    processed = len(progress.get('processed_race_ids', []))
    horses = progress.get('horses_processed_count', 0)
    timestamp = progress.get('timestamp', 'Unknown')

    print("[PROGRESS FILE]")
    print(f"  Processed races: {processed}")
    print(f"  Processed horses: {horses:,}")
    print(f"  Last update: {timestamp}")

    # 進捗率計算
    target = 3454  # 2024年の総レース数
    progress_pct = (total_races / target * 100) if target > 0 else 0
    remaining = target - total_races

    print()
    print("[PROGRESS]")
    print(f"  Complete: {total_races}/{target} ({progress_pct:.1f}%)")
    print(f"  Remaining: {remaining}")

    # 推定完了時刻（1レース平均3分として計算）
    if total_races > 5:  # テストレース除外
        est_minutes = remaining * 3
        est_hours = est_minutes / 60
        print(f"  Est. time remaining: {est_hours:.1f} hours")
else:
    print("[PROGRESS FILE] Not created yet")
    print()
    print("Collection hasn't started yet or still initializing...")

print()
print("="*60)
print(" このスクリプトを定期的に実行して進捗確認してください")
print(" 実行: py monitor_progress.py")
print("="*60)
