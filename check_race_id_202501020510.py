"""
レースID 202501020510 の詳細確認
"""
import pandas as pd

df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv", encoding='utf-8', low_memory=False)

# レースID 202501020510 を検索
race_id = 202501020510
race_data = df[df['race_id'] == race_id].copy()

if len(race_data) == 0:
    print(f"レースID {race_id} が見つかりません")
else:
    print("=" * 80)
    print(f"レースID: {race_id}")
    print("=" * 80)

    # レース情報
    first_row = race_data.iloc[0]
    print(f"\nレース日付: {first_row.get('date')}")
    print(f"競馬場: {first_row.get('track_name')}")
    print(f"レース名: {first_row.get('race_name')}")
    print(f"距離: {first_row.get('distance')}m")
    print(f"コース: {first_row.get('course_type')}")

    # 出馬表
    print(f"\n出馬表（{len(race_data)}頭）:")
    print("-" * 80)

    results = race_data[['Umaban', 'HorseName', 'Rank', 'Ninki', 'Odds']].copy()
    results = results.sort_values('Umaban')

    for _, row in results.iterrows():
        rank = row.get('Rank', '-')
        ninki = row.get('Ninki', '-')
        odds = row.get('Odds', '-')
        print(f"{row['Umaban']:>2}番 {row['HorseName']:<20} 着順:{rank:>3} 人気:{ninki:>3} オッズ:{odds}")

    # 実際の1-2-3着
    print("\n" + "=" * 80)
    print("実際の結果:")
    print("=" * 80)

    top3 = race_data.sort_values('Rank').head(3)
    for _, row in top3.iterrows():
        print(f"{int(row['Rank'])}着: {row['Umaban']:>2}番 {row['HorseName']:<20} ({int(row.get('Ninki', 0))}番人気)")

    print("\n" + "=" * 80)
    print("【重要】レースIDと日付の整合性チェック")
    print("=" * 80)

    race_id_str = str(race_id)
    if len(race_id_str) >= 8:
        year_from_id = race_id_str[0:4]
        month_from_id = race_id_str[4:6]
        day_from_id = race_id_str[6:8]
        print(f"レースIDから推定: {year_from_id}年{month_from_id}月{day_from_id}日")

    actual_date = first_row.get('date')
    print(f"実際のレース日付: {actual_date}")

    if actual_date:
        if '2025-01-02' in str(actual_date):
            print("\n✓ レースIDと日付が一致")
        else:
            print("\n✗ **レースIDと日付が不一致！**")
            print("  → データに問題がある可能性")
