"""
2025年9月～12月の週末レースID生成

戦略:
- 土日のみ（レース開催は主に週末）
- 主要競馬場を優先
- 開催パターンを考慮
"""

from datetime import datetime, timedelta

# 2025年9月1日～12月7日
start_date = datetime(2025, 9, 1)
end_date = datetime(2025, 12, 7)

# JRA競馬場コード
# 秋～冬は主に: 東京(05)・中山(06)・京都(08)・阪神(09)・中京(07)
# 夏は: 札幌(01)・函館(02)・新潟(04)・福島(03)
jra_places = {
    '05': '東京',
    '06': '中山',
    '07': '中京',
    '08': '京都',
    '09': '阪神',
    '01': '札幌',
    '02': '函館',
    '03': '福島',
    '04': '新潟',
    '10': '小倉'
}

race_ids = []

current_date = start_date

print("2025年9月～12月の週末レースID生成")
print("="*60)

while current_date <= end_date:
    # 土日のみ
    if current_date.weekday() in [5, 6]:  # 土=5, 日=6
        year = current_date.year
        date_str = current_date.strftime('%Y-%m-%d (%a)')

        # 各競馬場で開催される可能性のあるレースID
        # 開催回: 1-6回、日数: 1-12日、レース番号: 1-12R
        for place_code in jra_places.keys():
            for kai in range(1, 7):  # 1-6回開催
                for day in range(1, 13):  # 1-12日
                    for race_num in range(1, 13):  # 1-12R
                        race_id = f"{year}{place_code}{kai:02d}{day:02d}{race_num:02d}"
                        race_ids.append(race_id)

        print(f"{date_str}: 生成完了")

    current_date += timedelta(days=1)

print(f"\n生成されたレースID: {len(race_ids):,}件")
print("\nrace_ids_202509-12.txt に保存中...")

# ファイルに保存
with open('race_ids_202509-12.txt', 'w', encoding='utf-8') as f:
    for race_id in race_ids:
        f.write(f"{race_id}\n")

print("保存完了！")
print(f"\n次のステップ:")
print("  1. race_ids_202509-12.txt を確認")
print("  2. update_from_list.py を実行")
print("     (ファイル名を race_ids_202509-12.txt に変更)")
