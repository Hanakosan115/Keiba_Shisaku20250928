"""
血統専用ページを試す
"""

import requests
from bs4 import BeautifulSoup
import time

def test_url(url, horse_id):
    print(f"\n--- Testing: {url} ---")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        time.sleep(1)
        r = session.get(url, timeout=10)
        print(f"Status: {r.status_code}")

        if r.status_code == 200:
            soup = BeautifulSoup(r.content, 'lxml')

            # 「父」を探す
            if '父' in r.text:
                print(f"  Found '父' in page")

                # テーブルを探す
                tables = soup.find_all('table')
                print(f"  Tables: {len(tables)}")

                for i, table in enumerate(tables[:3], 1):
                    table_text = table.get_text()
                    if '父' in table_text:
                        print(f"    Table {i} contains '父'!")
                        rows = table.find_all('tr')[:3]
                        for j, row in enumerate(rows, 1):
                            cells = [c.get_text(strip=True)[:20] for c in row.find_all(['th', 'td'])[:3]]
                            print(f"      Row {j}: {cells}")
            else:
                print(f"  '父' not found")
        else:
            print(f"  HTTP Error: {r.status_code}")

    except Exception as e:
        print(f"  Error: {e}")

def main():
    horse_id = '2021105700'

    print("="*60)
    print(f"血統ページ候補を試す (horse_id: {horse_id})")
    print("="*60)

    # 候補URL
    urls = [
        f'https://db.netkeiba.com/horse/ped/{horse_id}/',
        f'https://db.netkeiba.com/horse/pedigree/{horse_id}/',
        f'https://www.netkeiba.com/horse/ped/{horse_id}/',
        f'https://www.netkeiba.com/db/horse/ped/{horse_id}/',
    ]

    for url in urls:
        test_url(url, horse_id)

    print("\n" + "="*60)

if __name__ == '__main__':
    main()
