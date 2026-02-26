"""
2024年11-12月のレースID候補を生成
"""

# 2024年11-12月に開催される可能性のある競馬場と回数
# 秋〜冬の開催パターン
race_id_candidates = []

year = '2024'

# 11-12月の主要開催場所と予想される回数
# 秋競馬: 東京・阪神・中山など
patterns = [
    # 東京（05）: 秋は5-6回開催
    ('05', ['05', '06']),
    # 中山（06）: 秋は5-6回開催  
    ('06', ['05', '06']),
    # 阪神（09）: 秋は4-5回開催
    ('09', ['04', '05']),
    # 京都（08）: 秋は8回前後（データベースでは最大07）
    ('08', ['06', '07', '08']),
    # 福島（03）: 秋は3回前後
    ('03', ['03', '04']),
]

for place_code, kai_list in patterns:
    for kai in kai_list:
        # 各開催は通常1-12日程度
        for day in range(1, 13):
            day_str = f'{day:02d}'
            # 各日12レース
            for race_num in range(1, 13):
                race_str = f'{race_num:02d}'
                race_id = f'{year}{place_code}{kai}{day_str}{race_str}'
                race_id_candidates.append(race_id)

print(f'生成されたレースID候補: {len(race_id_candidates)}件')

# サンプル表示
print('\nサンプル（最初の20件）:')
for i, rid in enumerate(race_id_candidates[:20], 1):
    place = rid[4:6]
    kai = rid[6:8]
    day = rid[8:10]
    race = rid[10:12]
    place_names = {
        '05': '東京', '06': '中山', '08': '京都', '09': '阪神', '03': '福島'
    }
    name = place_names.get(place, '?')
    print(f'{i:2d}. {rid}: {name} {int(kai)}回 {int(day)}日目 {int(race)}R')

# ファイルに保存
with open('race_id_candidates_nov_dec_2024.txt', 'w') as f:
    for rid in race_id_candidates:
        f.write(rid + '\n')

print(f'\nrace_id_candidates_nov_dec_2024.txt に保存しました ({len(race_id_candidates)}件)')
