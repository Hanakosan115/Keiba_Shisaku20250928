"""
db.netkeibaの日付別レース一覧からレースIDを取得
"""

import requests
from bs4 import BeautifulSoup
import time
import re

date_str = '20251101'
url = f'https://db.netkeiba.com/race/list/{date_str}/'

print(f"URL: {url}")
print()

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

time.sleep(1)
r = session.get(url, timeout=10)
r.encoding = r.apparent_encoding

print(f"Status: {r.status_code}")
print()

if r.status_code == 200:
    soup = BeautifulSoup(r.content, 'lxml')

    # レースIDを含むリンクを探す
    race_id_links = []

    # パターン1: /race/{race_id}/
    for a in soup.find_all('a', href=True):
        href = a['href']
        match = re.search(r'/race/(\d{12})/', href)
        if match:
            race_id_links.append(match.group(1))

    # ユニーク化
    race_ids = sorted(list(set(race_id_links)))

    print(f"レースID: {len(race_ids)}件")
    print()

    if race_ids:
        print("取得したレースID:")
        for rid in race_ids:
            print(f"  - {rid}")
    else:
        print("レースIDが見つかりませんでした")

        # デバッグ: 全リンクを確認
        print("\n全リンク（最初の20件）:")
        for i, a in enumerate(soup.find_all('a', href=True)[:20], 1):
            href = a['href']
            text = a.get_text(strip=True)
            print(f"  {i}. href='{href[:60]}' text='{text[:30]}'")
