"""
最近のレースIDを探す
レース結果ページから実際に存在するレースを見つける
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

print("="*80)
print("最近のレースID検索")
print("="*80)

# 2024年11月末〜12月初のレースIDを推測して存在確認
# レースID形式: YYYYPPKKDDRR
# YYYY: 年, PP: 場所, KK: 回, DD: 日, RR: レース番号

year = '2024'
places = {
    '05': '東京',
    '06': '中山',
    '08': '京都',
    '09': '阪神',
    '10': '福島',
}

found_races = []

print("\n2024年11月-12月のレースを検索中...\n")

# 11月末〜12月初旬の範囲で探す
for place_code, place_name in places.items():
    for kai in ['04', '05', '06']:  # 4-6回開催
        for day in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10']:  # 1-10日目
            for race_num in ['11']:  # 11Rだけチェック（メインレース）
                race_id = f"{year}{place_code}{kai}{day}{race_num}"

                url = f'https://db.netkeiba.com/race/{race_id}/'

                try:
                    response = session.get(url, timeout=5)

                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')

                        # レース名を取得
                        race_title = soup.find('h1', class_='raceTitle')
                        if race_title:
                            race_name = race_title.text.strip()

                            # 日付を取得
                            race_data = soup.find('p', class_='smalltxt')
                            if not race_data:
                                race_data = soup.find('div', class_='racedata')

                            date_info = ''
                            if race_data:
                                date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', race_data.text)
                                if date_match:
                                    date_info = f"{date_match.group(1)}/{date_match.group(2).zfill(2)}/{date_match.group(3).zfill(2)}"

                            found_races.append({
                                'race_id': race_id,
                                'place': place_name,
                                'race_name': race_name,
                                'date': date_info
                            })

                            print(f"[見つかった] {race_id}: {date_info} {place_name} {race_name}")

                except:
                    pass

print("\n" + "="*80)
print(f"見つかったレース: {len(found_races)}件")
print("="*80)

if found_races:
    print("\n最近のレース一覧:")
    for i, race in enumerate(sorted(found_races, key=lambda x: x['race_id'], reverse=True)[:10], 1):
        print(f"{i:2d}. {race['date']} {race['place']:4s} {race['race_name']} (ID: {race['race_id']})")

    # 最新のレースIDを保存
    latest = sorted(found_races, key=lambda x: x['race_id'], reverse=True)[0]
    print(f"\n最新レースID: {latest['race_id']}")

    with open('latest_race_ids.txt', 'w', encoding='utf-8') as f:
        f.write("最近のレースID一覧\n")
        f.write("="*60 + "\n\n")
        for race in sorted(found_races, key=lambda x: x['race_id'], reverse=True):
            f.write(f"{race['race_id']}: {race['date']} {race['place']} {race['race_name']}\n")

    print("\nlatest_race_ids.txt に保存しました")

else:
    print("\nレースが見つかりませんでした")
    print("検索範囲を広げる必要があります")
