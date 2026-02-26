"""
VPN接続時の血統情報取得テスト
"""

import requests
from bs4 import BeautifulSoup
import time

def main():
    horse_id = '2021105700'
    url = f'https://db.netkeiba.com/horse/{horse_id}/'

    print("="*60)
    print(f"血統情報取得テスト (VPN接続前提)")
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

        print(f"\nStatus: {r.status_code}")
        print(f"Content length: {len(r.text):,} characters")

        soup = BeautifulSoup(r.content, 'lxml')

        # 「キズナ」を探す（父馬）
        if 'キズナ' in r.text:
            print(f"\n血統情報が含まれています（'キズナ'発見）")

            # blood_tableを探す
            blood_table = soup.select_one('table.blood_table')
            print(f"\ntable.blood_table: {blood_table is not None}")

            if blood_table:
                print(f"\n--- blood_tableの内容 ---")

                # 父馬（1行目の1列目）
                father_tag = blood_table.select_one('tr:nth-of-type(1) td:nth-of-type(1) a')
                father = father_tag.get_text(strip=True) if father_tag else None
                print(f"父: {father}")

                # 母父（3行目の2列目）
                mother_father_tag = blood_table.select_one('tr:nth-of-type(3) td:nth-of-type(2) a')
                mother_father = mother_father_tag.get_text(strip=True) if mother_father_tag else None
                print(f"母父: {mother_father}")

                # テーブル構造を表示
                rows = blood_table.find_all('tr')[:5]
                print(f"\nテーブル構造 (最初5行):")
                for i, row in enumerate(rows, 1):
                    cells = row.find_all(['td', 'th'])
                    cell_texts = []
                    for cell in cells[:3]:
                        text = cell.get_text(strip=True)[:20]
                        # リンクがあればURLも表示
                        link = cell.find('a')
                        if link:
                            text += f" (link)"
                        cell_texts.append(text)
                    print(f"  Row {i}: {cell_texts}")
            else:
                # blood_tableがない場合、他のテーブルを探す
                print(f"\nblood_tableが見つかりません。他のテーブルを確認:")
                all_tables = soup.find_all('table')
                for i, table in enumerate(all_tables, 1):
                    table_class = table.get('class', [])
                    table_text = table.get_text()
                    if 'キズナ' in table_text or '父' in table_text:
                        print(f"\n  テーブル{i} (class={table_class}) に血統情報あり:")
                        rows = table.find_all('tr')[:3]
                        for j, row in enumerate(rows, 1):
                            cells = [c.get_text(strip=True)[:20] for c in row.find_all(['td', 'th'])[:3]]
                            print(f"    Row {j}: {cells}")
        else:
            print(f"\n血統情報が見つかりません")
            print(f"  ※VPN接続を確認してください")

    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)

if __name__ == '__main__':
    main()
