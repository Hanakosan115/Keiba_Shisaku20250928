"""
2024年8-12月のレースIDを生成してファイルに保存
"""

# JRA競馬場コード
places = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10']

race_ids = []

for month in range(8, 13):  # 8-12月
    for place in places:
        for kai in range(1, 6):  # 1-5回開催
            for day in range(1, 13):  # 1-12日
                for race_num in range(1, 13):  # 1-12R
                    race_id = f"2024{place}{kai:02d}{day:02d}{race_num:02d}"
                    race_ids.append(race_id)

print(f"生成したレースID数: {len(race_ids):,}件")
print(f"サンプル: {race_ids[:10]}")

# ファイルに保存
with open('race_ids_2024_aug_dec.txt', 'w', encoding='utf-8') as f:
    for race_id in race_ids:
        f.write(f"{race_id}\n")

print(f"\nファイルに保存しました: race_ids_2024_aug_dec.txt")
