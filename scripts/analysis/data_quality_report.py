"""
データ品質レポート自動生成
収集完了後に実行して、データの健全性を確認
"""
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print(" DATA QUALITY REPORT")
print("="*80)
print(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)
print()

# データ読み込み
print("[1] Loading data...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

# race_idから年を抽出（dateカラムが不完全なため）
df['year'] = df['race_id'].astype(str).str[:4]

print(f"    Total rows: {len(df):,}")
print(f"    Total races: {df['race_id'].nunique():,}")
print()

# 基本統計
print("="*80)
print("[2] BASIC STATISTICS")
print("="*80)
print()

print("Rows by year:")
for year in sorted(df['year'].unique()):
    year_df = df[df['year'] == year]
    races = year_df['race_id'].nunique()
    rows = len(year_df)
    avg_horses = rows / races if races > 0 else 0
    print(f"  {year}: {races:,} races, {rows:,} rows ({avg_horses:.1f} horses/race)")

print()

# 欠損値チェック
print("="*80)
print("[3] MISSING VALUES CHECK")
print("="*80)
print()

# 重要カラムの欠損率
important_cols = [
    '着順', '馬番', '馬名', 'HorseName_url', '性齢', '斤量', '騎手',
    'タイム', '着差', '単勝', '人気', '馬体重', '調教師',
    'race_id', 'race_name', 'course_type', 'distance', 'track_condition',
    'horse_id', 'father', 'mother_father',
    'total_starts', 'total_win_rate', 'total_earnings'
]

print("Missing rate for important columns:")
for col in important_cols:
    if col in df.columns:
        missing_pct = df[col].isna().sum() / len(df) * 100
        status = "OK" if missing_pct < 10 else "WARNING" if missing_pct < 50 else "CRITICAL"
        print(f"  {col:25s}: {missing_pct:5.1f}% [{status}]")
    else:
        print(f"  {col:25s}: NOT FOUND")

print()

# 統計カラムのカバー率
print("="*80)
print("[4] STATISTICS COVERAGE")
print("="*80)
print()

stat_cols = [
    'total_starts', 'total_win_rate', 'turf_win_rate', 'dirt_win_rate',
    'total_earnings', 'father', 'mother_father',
    'distance_similar_win_rate', 'grade_race_starts', 'is_local_transfer',
    'avg_passage_position', 'running_style_category',
    'prev_race_rank', 'prev_race_distance', 'days_since_last_race',
    'heavy_track_win_rate', 'avg_last_3f'
]

print("Statistics columns coverage:")
for col in stat_cols:
    if col in df.columns:
        coverage = df[col].notna().sum() / len(df) * 100
        status = "GOOD" if coverage > 80 else "OK" if coverage > 50 else "POOR"
        print(f"  {col:30s}: {coverage:5.1f}% [{status}]")
    else:
        print(f"  {col:30s}: NOT FOUND")

print()

# データ整合性チェック
print("="*80)
print("[5] DATA CONSISTENCY CHECK")
print("="*80)
print()

# レースあたりの平均馬数
avg_horses_per_race = len(df) / df['race_id'].nunique()
print(f"Average horses per race: {avg_horses_per_race:.2f}")
if avg_horses_per_race >= 10:
    print("  Status: GOOD (expected 10-18 horses)")
elif avg_horses_per_race >= 5:
    print("  Status: OK (slightly low)")
else:
    print("  Status: WARNING (too low, data might be incomplete)")

print()

# 着順の範囲チェック
if '着順' in df.columns:
    df['着順_num'] = pd.to_numeric(df['着順'], errors='coerce')
    rank_stats = df['着順_num'].describe()
    print("Rank (着順) statistics:")
    print(f"  Min: {rank_stats['min']:.0f}")
    print(f"  Max: {rank_stats['max']:.0f}")
    print(f"  Mean: {rank_stats['mean']:.2f}")
    print(f"  Status: {'GOOD' if rank_stats['max'] <= 20 else 'WARNING'}")

print()

# 異常値チェック
print("="*80)
print("[6] OUTLIER CHECK")
print("="*80)
print()

# オッズの異常値
if '単勝' in df.columns:
    df['単勝_num'] = pd.to_numeric(df['単勝'], errors='coerce')
    odds_stats = df['単勝_num'].describe()
    print("Odds (単勝) statistics:")
    print(f"  Min: {odds_stats['min']:.1f}")
    print(f"  Max: {odds_stats['max']:.1f}")
    print(f"  Mean: {odds_stats['mean']:.1f}")
    print(f"  Median: {odds_stats['50%']:.1f}")
    extreme_odds = (df['単勝_num'] > 1000).sum()
    print(f"  Extreme odds (>1000): {extreme_odds} ({extreme_odds/len(df)*100:.2f}%)")

print()

# 重複チェック
print("="*80)
print("[7] DUPLICATE CHECK")
print("="*80)
print()

# race_id + 馬番での重複
if '馬番' in df.columns:
    duplicates = df.duplicated(subset=['race_id', '馬番'], keep=False).sum()
    print(f"Duplicates (race_id + 馬番): {duplicates}")
    print(f"  Status: {'GOOD' if duplicates == 0 else 'WARNING'}")
elif 'Umaban' in df.columns:
    duplicates = df.duplicated(subset=['race_id', 'Umaban'], keep=False).sum()
    print(f"Duplicates (race_id + Umaban): {duplicates}")
    print(f"  Status: {'GOOD' if duplicates == 0 else 'WARNING'}")
else:
    print("Cannot check duplicates - no horse number column found")

print()

# 最終評価
print("="*80)
print("[8] OVERALL ASSESSMENT")
print("="*80)
print()

issues = []

# チェック項目
if avg_horses_per_race < 10:
    issues.append("Low average horses per race")

missing_critical = 0
for col in ['race_id', '馬名', '着順']:
    if col in df.columns:
        if df[col].isna().sum() / len(df) > 0.1:
            issues.append(f"High missing rate in {col}")
            missing_critical += 1

stats_coverage = df['total_starts'].notna().sum() / len(df) * 100 if 'total_starts' in df.columns else 0
if stats_coverage < 70:
    issues.append(f"Low statistics coverage ({stats_coverage:.1f}%)")

if len(issues) == 0:
    print("OVERALL STATUS: EXCELLENT")
    print("  Data quality is high and ready for analysis!")
elif len(issues) <= 2:
    print("OVERALL STATUS: GOOD")
    print("  Minor issues detected:")
    for issue in issues:
        print(f"    - {issue}")
else:
    print("OVERALL STATUS: NEEDS ATTENTION")
    print("  Issues detected:")
    for issue in issues:
        print(f"    - {issue}")

print()
print("="*80)
print(" REPORT COMPLETE")
print("="*80)
print()
print("Recommendations:")
print("  1. Run this report after data collection completes")
print("  2. Address any CRITICAL or WARNING issues")
print("  3. Proceed to EDA once status is GOOD or better")
