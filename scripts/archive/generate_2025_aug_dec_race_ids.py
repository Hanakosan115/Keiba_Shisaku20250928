"""
2025年8-12月のレースIDを生成してファイルに保存
"""

# JRA競馬場コード
places = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10']

race_ids = []

for month in range(8, 13):  # 8-12月
    for place in places:
        for kai in range(1, 6):  # 1-5回開催
            for day in range(1, 13):  # 1-12日
                for race_num in range(1, 13):  # 1-12R
                    race_id = f"2025{place}{month:02d}{kai:02d}{day:02d}{race_num:02d}"
                    race_ids.append(race_id)

print(f"生成したレースID数: {len(race_ids):,}件")
print(f"最初の10件: {race_ids[:10]}")
print(f"最後の10件: {race_ids[-10:]}")
print()

# 月別の確認
for month in range(8, 13):
    month_ids = [rid for rid in race_ids if rid[6:8] == f"{month:02d}"]
    print(f"{month}月: {len(month_ids):,}件 (例: {month_ids[0] if month_ids else 'なし'})")

# ファイルに保存
with open('race_ids_2025_aug_dec.txt', 'w', encoding='utf-8') as f:
    for race_id in race_ids:
        f.write(f"{race_id}\n")

print(f"\nファイルに保存しました: race_ids_2025_aug_dec.txt")
