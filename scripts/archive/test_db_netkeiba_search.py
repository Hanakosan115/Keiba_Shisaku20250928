"""
db.netkeiba.comでレース検索できるか確認
"""

import requests
from bs4 import BeautifulSoup
import time

# db.netkeibaのレース検索ページ候補
test_urls = [
    'https://db.netkeiba.com/?pid=race_top',
    'https://db.netkeiba.com/race/',
    'https://db.netkeiba.com/race/list/',
    'https://db.netkeiba.com/race/search/',
    'https://db.netkeiba.com/race/calendar/',
    'https://db.netkeiba.com/?pid=race_list&date=20251101',
]

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

for url in test_urls:
    print(f"\nTesting: {url}")
    try:
        time.sleep(1)
        r = session.get(url, timeout=10)
        print(f"  Status: {r.status_code}")

        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'lxml')

            # レース関連のリンクを探す
            race_links = soup.find_all('a', href=lambda x: x and '/race/' in x)
            print(f"  Race links: {len(race_links)}")

            if race_links:
                print(f"  Sample links:")
                for link in race_links[:3]:
                    print(f"    - {link.get('href')[:80]}")

    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "="*60)
