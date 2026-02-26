"""
血統専用ページから父・母父を取得
"""

import requests
from bs4 import BeautifulSoup
import time

def main():
    horse_id = '2021105700'
    ped_url = f'https://db.netkeiba.com/horse/ped/{horse_id}/'

    print("="*60)
    print(f"血統専用ページテスト")
    print(f"URL: {ped_url}")
    print("="*60)

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        time.sleep(1)
        r = session.get(ped_url, timeout=10)
        r.raise_for_status()
        r.encoding = r.apparent_encoding

        print(f"\nStatus: {r.status_code}")
        print(f"Content length: {len(r.text):,} characters")

        soup = BeautifulSoup(r.content, 'lxml')

        # 「キズナ」を探す
        if 'キズナ' in r.text:
            print(f"\n血統情報発見（'キズナ'あり）")

            # 全テーブルを探す
            all_tables = soup.find_all('table')
            print(f"\nテーブル数: {len(all_tables)}")

            for i, table in enumerate(all_tables, 1):
                table_class = table.get('class', [])
                print(f"\nテーブル{i}: class={table_class}")

                # テーブルの内容を確認
                rows = table.find_all('tr')[:5]
                print(f"  行数(サンプル): {len(rows)}")

                for j, row in enumerate(rows, 1):
                    cells = row.find_all(['td', 'th'])
                    print(f"  Row {j}: {len(cells)} cells")

                    for k, cell in enumerate(cells[:3], 1):
                        text = cell.get_text(strip=True)[:30]
                        link = cell.find('a')
                        if link:
                            href = link.get('href', '')
                            print(f"    Cell {k}: {text} (link: {href[:40]})")
                        else:
                            print(f"    Cell {k}: {text}")

                # キズナが含まれているかチェック
                if 'キズナ' in table.get_text():
                    print(f"  -> このテーブルに'キズナ'あり！")

            # 5代血統表のタイトルを探す
            title = soup.find(['h1', 'h2', 'h3'], string=lambda x: x and '血統' in x)
            if title:
                print(f"\nタイトル: {title.get_text(strip=True)}")

        else:
            print(f"\n'キズナ'が見つかりません")
            print(f"VPN接続を確認してください")

    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)

if __name__ == '__main__':
    main()
