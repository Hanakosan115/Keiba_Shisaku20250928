"""
NetKeibaの馬ページから血統テーブルの実際の構造を調査
"""

import requests
from bs4 import BeautifulSoup
import time

def main():
    horse_id = '2021105700'
    url = f'https://db.netkeiba.com/horse/{horse_id}/'

    print("="*60)
    print(f"NetKeiba馬ページ構造調査")
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

        # 全てのテーブルを探す
        all_tables = soup.find_all('table')
        print(f"\nページ内の全テーブル: {len(all_tables)}個")

        for i, table in enumerate(all_tables, 1):
            table_class = table.get('class', [])
            table_id = table.get('id', '')
            table_summary = table.get('summary', '')

            print(f"\n--- テーブル {i} ---")
            print(f"  class: {table_class}")
            print(f"  id: {table_id}")
            print(f"  summary: {table_summary}")

            # テーブルの最初の数行を表示
            rows = table.find_all('tr')[:3]
            print(f"  行数(最初3行): {len(rows)}")

            for j, row in enumerate(rows, 1):
                cells = row.find_all(['th', 'td'])
                cell_texts = [cell.get_text(strip=True)[:20] for cell in cells[:3]]
                print(f"    行{j}: {cell_texts}")

            # 「父」「母父」などのキーワードがあるかチェック
            table_text = table.get_text()
            keywords = ['父', '母父', '血統', 'サンデーサイレンス', 'ディープインパクト']
            found_keywords = [kw for kw in keywords if kw in table_text]
            if found_keywords:
                print(f"  ★ 血統関連キーワード発見: {found_keywords}")

        # 血統情報を含む可能性のあるdivやsectionを探す
        print(f"\n\n血統関連の要素を検索:")
        blood_divs = soup.find_all(['div', 'section'], class_=lambda x: x and ('blood' in str(x).lower() or 'pedigree' in str(x).lower()))
        print(f"  blood/pedigree関連div/section: {len(blood_divs)}個")

        for div in blood_divs[:3]:
            print(f"    {div.name} class={div.get('class')}")

    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)

if __name__ == '__main__':
    main()
