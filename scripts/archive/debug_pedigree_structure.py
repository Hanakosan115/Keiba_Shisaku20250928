"""
5代血統表の全構造を詳しく表示
"""

import requests
from bs4 import BeautifulSoup
import time

def main():
    horse_id = '2021105700'  # ダブルハートボンド
    url = f'https://db.netkeiba.com/horse/ped/{horse_id}/'

    print("="*60)
    print(f"5代血統表の全構造")
    print(f"馬: ダブルハートボンド")
    print(f"URL: {url}")
    print("="*60)

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        time.sleep(1)
        r = session.get(url, timeout=10)
        r.raise_for_status()
        r.encoding = r.apparent_encoding

        soup = BeautifulSoup(r.content, 'lxml')

        # blood_table.detail
        blood_table = soup.select_one('table.blood_table.detail')

        if blood_table:
            rows = blood_table.find_all('tr')
            print(f"\n全{len(rows)}行:")

            for i, row in enumerate(rows[:20], 1):  # 最初20行を詳細表示
                cells = row.find_all(['td', 'th'])
                print(f"\n--- Row {i}: {len(cells)} cells ---")

                for j, cell in enumerate(cells, 1):
                    # リンクを探す
                    links = cell.find_all('a')
                    if links:
                        for k, link in enumerate(links, 1):
                            horse_name = link.get_text(strip=True)
                            href = link.get('href', '')
                            print(f"  Cell {j}, Link {k}: {horse_name} ({href})")
                    else:
                        text = cell.get_text(strip=True)[:50]
                        print(f"  Cell {j}: {text}")

        else:
            print("\nblood_tableが見つかりません")

    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)

if __name__ == '__main__':
    main()
