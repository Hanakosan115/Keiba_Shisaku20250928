"""
バックテストの日付整合性チェック
race_idから推定した日付と実際のdate列が一致しているか確認
"""
import pandas as pd
import sys

df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv", encoding='utf-8', low_memory=False)

print("=" * 80)
print("日付整合性チェック（6-8月データ）")
print("=" * 80)

# 6-8月のレースを抽出
df['race_id_str'] = df['race_id'].astype(str)
target_races = df[
    df['race_id_str'].str.startswith('202506') |
    df['race_id_str'].str.startswith('202507') |
    df['race_id_str'].str.startswith('202508')
]

# race_idごとにグループ化
race_groups = target_races.groupby('race_id')

mismatch_count = 0
match_count = 0
sample_mismatches = []

for race_id, group in race_groups:
    race_id_str = str(race_id)

    if len(race_id_str) >= 8:
        year_from_id = race_id_str[0:4]
        month_from_id = race_id_str[4:6]
        day_from_id = race_id_str[6:8]
        date_from_id = f"{year_from_id}-{month_from_id}-{day_from_id}"

        # 実際のdate列
        actual_date = group.iloc[0]['date']

        if pd.notna(actual_date):
            actual_date_str = str(actual_date)[:10]  # YYYY-MM-DD部分

            if date_from_id == actual_date_str:
                match_count += 1
            else:
                mismatch_count += 1
                if len(sample_mismatches) < 10:
                    sample_mismatches.append({
                        'race_id': race_id,
                        'from_id': date_from_id,
                        'actual': actual_date_str,
                        'race_name': group.iloc[0].get('race_name', 'N/A')
                    })

print(f"\n総レース数: {len(race_groups)}")
print(f"一致: {match_count}レース")
print(f"不一致: {mismatch_count}レース")
print(f"不一致率: {mismatch_count/len(race_groups)*100:.1f}%")

if sample_mismatches:
    print("\n" + "=" * 80)
    print("不一致サンプル（最大10件）:")
    print("=" * 80)
    for m in sample_mismatches:
        print(f"\nレースID: {m['race_id']}")
        print(f"  IDから推定: {m['from_id']}")
        print(f"  実際の日付: {m['actual']}")
        print(f"  レース名: {m['race_name']}")

print("\n" + "=" * 80)
print("【重要】")
if mismatch_count > 0:
    print("race_idと実際の日付が一致していないレースが存在します。")
    print("バックテストで日付フィルタが正しく機能していない可能性があります。")
else:
    print("すべてのレースでrace_idと日付が一致しています。")
print("=" * 80)
