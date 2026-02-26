"""
データの鮮度チェック - 直近レースデータの反映状況を確認
"""
import pandas as pd
from data_config import MAIN_CSV

print("=" * 80)
print("データ鮮度チェック")
print("=" * 80)

df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

print(f"\nデータ範囲: {df['date_parsed'].min()} ～ {df['date_parsed'].max()}")

# 10月下旬のレースをサンプル抽出
races_oct = df[(df['date_parsed'] >= '2024-10-20') & (df['date_parsed'] <= '2024-10-31')]
print(f"\n10月20-31日のレース数: {len(races_oct)} 出走頭数")

if len(races_oct) == 0:
    print("10月下旬のデータがありません！")
else:
    # 最初の5頭をチェック
    sample_horses = races_oct.head(10)

    print("\n" + "=" * 80)
    print("サンプル馬の直近レース反映状況（10月下旬出走馬）")
    print("=" * 80)

    for idx, race_horse in sample_horses.iterrows():
        horse_id = race_horse['horse_id']
        race_date = race_horse['date_parsed']
        race_date_str = str(race_horse['date'])[:10]

        # この馬の全レース
        horse_races = df[df['horse_id'] == horse_id].copy()
        horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')

        # レース日より前のデータ
        past_races = horse_races[horse_races['date_parsed'] < race_date]
        past_races = past_races.sort_values('date_parsed', ascending=False)

        print(f"\n馬ID: {horse_id}")
        print(f"出走日: {race_date_str}")
        print(f"過去レース数: {len(past_races)}件")

        if len(past_races) > 0:
            latest_past = past_races.iloc[0]
            latest_date = latest_past['date_parsed']
            days_gap = (race_date - latest_date).days

            print(f"最新の過去レース: {str(latest_past['date'])[:10]} ({days_gap}日前)")

            # 直近3走表示
            print("直近3走:")
            for i, (_, r) in enumerate(past_races.head(3).iterrows()):
                race_name = str(r.get('RaceName', 'N/A'))[:20]
                rank = r.get('Rank', 'N/A')
                date_str = str(r['date'])[:10]
                print(f"  {i+1}. {date_str} - {race_name} - {rank}着")

            # 2週間以内のレースがあるかチェック
            recent_races = past_races[past_races['date_parsed'] >= race_date - pd.Timedelta(days=14)]
            if len(recent_races) == 0 and days_gap > 14:
                print(f"  [!] 注意: 最新レースが{days_gap}日前（2週間以上前）")
        else:
            print("  [!] 警告: 過去レースデータなし（新馬？）")

# 月別のデータ件数確認（2024年）
print("\n" + "=" * 80)
print("2024年の月別データ件数")
print("=" * 80)
df_2024 = df[(df['date_parsed'] >= '2024-01-01') & (df['date_parsed'] <= '2024-12-31')]
monthly = df_2024.groupby(df_2024['date_parsed'].dt.to_period('M')).size()
for month, count in monthly.items():
    print(f"{month}: {count:,}頭")

# 具体的な問題の有無を診断
print("\n" + "=" * 80)
print("診断結果")
print("=" * 80)

# 11月のレースで10月のデータが参照できるかチェック
races_nov = df[(df['date_parsed'] >= '2024-11-01') & (df['date_parsed'] <= '2024-11-10')].head(20)
missing_recent_data_count = 0

for _, race_horse in races_nov.iterrows():
    horse_id = race_horse['horse_id']
    race_date = race_horse['date_parsed']

    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')
    past_races = horse_races[horse_races['date_parsed'] < race_date]

    if len(past_races) > 0:
        latest_past = past_races.sort_values('date_parsed', ascending=False).iloc[0]
        days_gap = (race_date - latest_past['date_parsed']).days

        # 30日以内に走っているのにデータに反映されていない可能性
        if days_gap > 30:
            missing_recent_data_count += 1

print(f"11月上旬出走馬20頭中、直近30日以内のレースデータがない馬: {missing_recent_data_count}頭")

if missing_recent_data_count > 5:
    print("\n[WARNING] データ鮮度に問題あり！")
    print("   -> 直近レースのデータが反映されていない可能性が高い")
    print("   -> これが予測精度に悪影響を与えている")
else:
    print("\n[OK] データ鮮度は概ね良好")
