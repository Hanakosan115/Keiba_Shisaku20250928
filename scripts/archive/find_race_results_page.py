"""
過去戦績の専用ページを探す
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

            # テーブルを探す
            tables = soup.find_all('table')
            print(f"  Tables: {len(tables)}")

            if tables:
                for i, table in enumerate(tables[:3], 1):
                    table_class = table.get('class', [])
                    print(f"\n  Table {i}: class={table_class}")

                    # 「着順」「レース名」などのキーワードチェック
                    table_text = table.get_text()
                    if '着順' in table_text or 'レース名' in table_text:
                        print(f"    ★ 過去戦績テーブル候補！")
                        rows = table.find_all('tr')[:3]
                        for j, row in enumerate(rows, 1):
                            cells = [c.get_text(strip=True)[:15] for c in row.find_all(['th', 'td'])[:5]]
                            print(f"      Row {j}: {cells}")

    except Exception as e:
        print(f"  Error: {e}")

def main():
    horse_id = '2010105827'  # キズナ

    print("="*60)
    print(f"過去戦績ページ候補を試す (horse_id: {horse_id})")
    print("="*60)

    # 候補URL
    urls = [
        f'https://db.netkeiba.com/horse/{horse_id}/',  # メインページ（再確認）
        f'https://db.netkeiba.com/horse/result/{horse_id}/',  # 戦績専用ページ候補
        f'https://db.netkeiba.com/horse/race/{horse_id}/',  # レース専用ページ候補
        f'https://race.netkeiba.com/horse/result.html?horse_id={horse_id}',  # race.netkeibaドメイン
    ]

    for url in urls:
        test_url(url, horse_id)

    print("\n" + "="*60)

if __name__ == '__main__':
    main()
