"""
10月のデータが11月予測時に正しくリンクされているか確認
"""
import pandas as pd
from data_config import MAIN_CSV

print("=" * 80)
print("データリンケージ検証")
print("=" * 80)

df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 11月上旬のレースから馬を5頭サンプリング
nov_races = df[(df['date_parsed'] >= '2024-11-02') & (df['date_parsed'] <= '2024-11-10')]
sample_horses = nov_races['horse_id'].unique()[:5]

print(f"\n11月上旬出走馬のサンプル: {len(sample_horses)}頭")
print("=" * 80)

for horse_id in sample_horses:
    print(f"\n馬ID: {horse_id}")

    # この馬の全レース
    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')
    horse_races = horse_races.sort_values('date_parsed')

    # 11月のレース
    nov_race = horse_races[horse_races['date_parsed'] >= '2024-11-01'].iloc[0]
    nov_date = nov_race['date_parsed']

    print(f"  11月出走日: {nov_date.date()}")

    # その日より前の全レース
    past_races = horse_races[horse_races['date_parsed'] < nov_date]
    print(f"  過去レース総数: {len(past_races)}件")

    if len(past_races) > 0:
        # 10月のレース
        oct_races = past_races[(past_races['date_parsed'] >= '2024-10-01') &
                               (past_races['date_parsed'] <= '2024-10-31')]
        print(f"  10月のレース: {len(oct_races)}件")

        if len(oct_races) > 0:
            for _, r in oct_races.iterrows():
                print(f"    - {r['date_parsed'].date()}: {r.get('RaceName', 'N/A')[:20]} {r.get('Rank', 'N/A')}着")
        else:
            # 9月のレース確認
            sep_races = past_races[(past_races['date_parsed'] >= '2024-09-01') &
                                   (past_races['date_parsed'] <= '2024-09-30')]
            print(f"  9月のレース: {len(sep_races)}件")

        # 最新レース
        latest = past_races.iloc[-1]
        days_gap = (nov_date - latest['date_parsed']).days
        print(f"  最新レース: {latest['date_parsed'].date()} ({days_gap}日前)")

# 統計サマリー
print("\n" + "=" * 80)
print("統計サマリー")
print("=" * 80)

nov_sample = nov_races.head(50)  # 50頭サンプル
has_october_data = 0
total_checked = 0

for horse_id in nov_sample['horse_id'].unique():
    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')

    nov_race = horse_races[horse_races['date_parsed'] >= '2024-11-01']
    if len(nov_race) == 0:
        continue

    nov_date = nov_race.iloc[0]['date_parsed']
    past_races = horse_races[horse_races['date_parsed'] < nov_date]

    oct_races = past_races[(past_races['date_parsed'] >= '2024-10-01') &
                           (past_races['date_parsed'] <= '2024-10-31')]

    total_checked += 1
    if len(oct_races) > 0:
        has_october_data += 1

print(f"\n11月出走馬{total_checked}頭中:")
print(f"  10月データあり: {has_october_data}頭 ({has_october_data/total_checked*100:.1f}%)")
print(f"  10月データなし: {total_checked - has_october_data}頭 ({(total_checked-has_october_data)/total_checked*100:.1f}%)")

if has_october_data / total_checked < 0.5:
    print("\n[WARNING] 過半数の馬に10月データがありません！")
    print("  -> 馬が10月に出走していない（休養明け等）")
    print("  -> これは正常な可能性もある")
else:
    print("\n[OK] 多くの馬に10月データがあります")

# データの欠損ではなく、馬の出走パターンの問題かを確認
print("\n" + "=" * 80)
print("結論")
print("=" * 80)

# 10月のユニーク馬数
oct_horses = df[(df['date_parsed'] >= '2024-10-01') &
                (df['date_parsed'] <= '2024-10-31')]['horse_id'].nunique()
nov_horses = df[(df['date_parsed'] >= '2024-11-01') &
                (df['date_parsed'] <= '2024-11-10')]['horse_id'].nunique()

print(f"\n10月出走馬: {oct_horses}頭")
print(f"11月出走馬: {nov_horses}頭")

# 重複（10月も11月も走った馬）
oct_horse_set = set(df[(df['date_parsed'] >= '2024-10-01') &
                        (df['date_parsed'] <= '2024-10-31')]['horse_id'])
nov_horse_set = set(df[(df['date_parsed'] >= '2024-11-01') &
                        (df['date_parsed'] <= '2024-11-10')]['horse_id'])
both = oct_horse_set & nov_horse_set

print(f"両月に出走: {len(both)}頭 ({len(both)/nov_horses*100:.1f}%)")

if len(both) / nov_horses < 0.3:
    print("\n[結論] データ欠損ではなく、馬のローテーションの問題")
    print("  11月出走馬の多くは10月に走っていない")
    print("  -> 新馬、休養明け、ローテーション調整等")
    print("  -> これは正常。データ更新は不要かも")
else:
    print("\n[結論] 30%以上の馬が連闘")
    print("  データは正常にリンクされている可能性が高い")
