"""
データギャップの詳細分析
どの期間のデータが欠損しているかを特定
"""
import pandas as pd
from data_config import MAIN_CSV

print("=" * 80)
print("データギャップ分析")
print("=" * 80)

df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年9月-12月のデータを日別に集計
target_df = df[(df['date_parsed'] >= '2024-09-01') & (df['date_parsed'] <= '2024-12-31')]

print("\n2024年9月-12月の日別レース数:")
print("-" * 80)

daily_counts = target_df.groupby(target_df['date_parsed'].dt.date).size().reset_index()
daily_counts.columns = ['date', 'count']
daily_counts = daily_counts.sort_values('date')

# 日付の範囲を生成（全日）
date_range = pd.date_range(start='2024-09-01', end='2024-12-31', freq='D')

print(f"\n{'日付':12s} | {'出走頭数':>8s} | {'レース数推定':>10s} | {'状態':10s}")
print("-" * 50)

missing_dates = []
for date in date_range:
    date_only = date.date()
    count = daily_counts[daily_counts['date'] == date_only]['count'].values

    if len(count) > 0:
        horse_count = count[0]
        race_count = horse_count // 12  # 平均12頭/レースと仮定
        status = "OK" if horse_count > 50 else "少ない"
        print(f"{date_only} | {horse_count:8d}頭 | {race_count:7d}R程度 | {status}")
    else:
        print(f"{date_only} |        0頭 |         0R程度 | 欠損")
        missing_dates.append(date_only)

# 欠損期間のサマリー
print("\n" + "=" * 80)
print("欠損データサマリー")
print("=" * 80)

if len(missing_dates) == 0:
    print("\n[OK] データ欠損なし！")
else:
    print(f"\n欠損日数: {len(missing_dates)}日")

    # 連続した欠損期間をグループ化
    if len(missing_dates) > 0:
        print("\n欠損期間:")
        period_start = missing_dates[0]
        period_end = missing_dates[0]

        for i in range(1, len(missing_dates)):
            # 連続しているか確認
            if (missing_dates[i] - missing_dates[i-1]).days == 1:
                period_end = missing_dates[i]
            else:
                # 期間を出力
                if period_start == period_end:
                    print(f"  - {period_start}")
                else:
                    print(f"  - {period_start} 〜 {period_end}")
                period_start = missing_dates[i]
                period_end = missing_dates[i]

        # 最後の期間を出力
        if period_start == period_end:
            print(f"  - {period_start}")
        else:
            print(f"  - {period_start} 〜 {period_end}")

# データの最新日を確認
latest_date = df['date_parsed'].max()
print(f"\n現在のデータの最新日: {latest_date}")
print(f"今日の日付: 2024-11-22（想定）")

# 実際にスクレイピングが必要な期間を提案
print("\n" + "=" * 80)
print("推奨アクション")
print("=" * 80)

# 最新のデータがある日を探す（11月以降）
nov_data = df[df['date_parsed'] >= '2024-11-01']
if len(nov_data) > 0:
    nov_latest = nov_data['date_parsed'].max()
    print(f"\n11月のデータ最新日: {nov_latest.date()}")
    print(f"→ {nov_latest.date()}以降のデータを取得する必要がある")
else:
    print("\n11月のデータが全くありません")
    print("→ 2024-11-01以降のデータを取得する必要がある")

oct_data = df[(df['date_parsed'] >= '2024-10-01') & (df['date_parsed'] <= '2024-10-31')]
if len(oct_data) > 0:
    print(f"\n10月のデータ: {len(oct_data)}頭分あり")
    oct_latest = oct_data['date_parsed'].max()
    print(f"10月の最新日: {oct_latest.date()}")
else:
    print("\n10月のデータもありません")

print("\n" + "=" * 80)
print("スクレイピング必要期間（推定）")
print("=" * 80)

# 実用的な推奨
if len(nov_data) > 0:
    scrape_start = nov_data['date_parsed'].max().date()
    print(f"\n開始日: {scrape_start} の翌日")
    print(f"終了日: 2024-11-22（今日）")
    print(f"\n※ただし、安全のため2024-10-01から再取得することを推奨")
else:
    print("\n開始日: 2024-10-01")
    print(f"終了日: 2024-11-22（今日）")
