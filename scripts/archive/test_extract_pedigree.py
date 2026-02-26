"""
血統専用ページから父・母父を抽出するテスト
"""

import requests
from bs4 import BeautifulSoup
import time
import re

def get_pedigree_from_ped_page(horse_id):
    """血統専用ページから父・母父を取得"""
    url = f'https://db.netkeiba.com/horse/ped/{horse_id}/'
    pedigree_info = {}

    try:
        time.sleep(0.5)
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

        r = session.get(url, timeout=10)
        r.raise_for_status()
        r.encoding = r.apparent_encoding

        soup = BeautifulSoup(r.content, 'lxml')

        # blood_table.detailを探す
        blood_table = soup.select_one('table.blood_table.detail')

        if blood_table:
            print(f"\n血統テーブル発見！")

            # 全ての行を取得
            rows = blood_table.find_all('tr')
            print(f"テーブル行数: {len(rows)}")

            # 父: 1行目の最初のセル
            if len(rows) > 0:
                cells = rows[0].find_all(['td', 'th'])
                if len(cells) > 0:
                    # 最初のセルから馬名だけを抽出（年や産地情報を除く）
                    cell_text = cells[0].get_text(strip=True)
                    # 馬名は最初のリンクから取得
                    link = cells[0].find('a')
                    if link:
                        father_name = link.get_text(strip=True)
                        pedigree_info['father'] = father_name
                        print(f"父: {father_name}")

            # 母父: 3行目（母の行）の2列目
            # 5代血統表の構造: Row 1=父, Row 3=母
            # 母父 = 母の父 = Row 3の次の行または同じ行の別セル

            # より確実な方法: 全行をスキャンして構造を理解
            print(f"\n全行の構造:")
            for i, row in enumerate(rows[:10], 1):
                cells = row.find_all(['td', 'th'])
                cell_count = len(cells)
                first_cell_text = cells[0].get_text(strip=True)[:30] if cells else ""
                print(f"  Row {i}: {cell_count} cells - {first_cell_text}")

            # 母父の抽出: 5代血統表は2セクション構造
            # Row 1-16: 父系（Row 1 = 父）
            # Row 17-32: 母系（Row 17 = 母、母父）

            # Row 17 (index 16) の2番目のセルを取得
            if len(rows) > 16:
                cells = rows[16].find_all(['td', 'th'])
                print(f"\nRow 17のセル数: {len(cells)}")

                # Cell 1: 母
                if len(cells) > 0:
                    mother_link = cells[0].find('a')
                    if mother_link:
                        mother_name = mother_link.get_text(strip=True)
                        print(f"母(Row17,Cell1): {mother_name}")

                # Cell 2: 母父
                if len(cells) > 1:
                    link = cells[1].find('a')
                    if link:
                        mother_father_name = link.get_text(strip=True)
                        pedigree_info['mother_father'] = mother_father_name
                        print(f"母父(Row17,Cell2): {mother_father_name}")

        else:
            print(f"\n血統テーブルが見つかりません")

    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()

    return pedigree_info

def main():
    print("="*60)
    print("血統情報抽出テスト")
    print("="*60)

    horse_id = '2021105700'
    pedigree = get_pedigree_from_ped_page(horse_id)

    print(f"\n{'='*60}")
    print(f"抽出結果:")
    print(f"  父: {pedigree.get('father', 'N/A')}")
    print(f"  母父: {pedigree.get('mother_father', 'N/A')}")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
