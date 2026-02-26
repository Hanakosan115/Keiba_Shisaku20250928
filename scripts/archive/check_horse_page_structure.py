"""
馬ページのHTML構造を確認
"""

import requests
from bs4 import BeautifulSoup
import time

horse_id = '2010105827'  # キズナ（実績豊富な馬）
url = f'https://db.netkeiba.com/horse/{horse_id}/'

print("="*60)
print(f"馬ページ構造確認")
print(f"URL: {url}")
print("="*60)

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
})

time.sleep(1)
r = session.get(url, timeout=10)
r.raise_for_status()
r.encoding = r.apparent_encoding

soup = BeautifulSoup(r.content, 'lxml')

# 全テーブルを探す
all_tables = soup.find_all('table')
print(f"\nページ内の全テーブル: {len(all_tables)}個\n")

for i, table in enumerate(all_tables, 1):
    table_class = table.get('class', [])
    table_id = table.get('id', '')
    print(f"テーブル {i}:")
    print(f"  class: {table_class}")
    print(f"  id: {table_id}")

    # テーブルの最初の数行
    rows = table.find_all('tr')[:3]
    if rows:
        print(f"  行数(サンプル): {len(rows)}")
        for j, row in enumerate(rows, 1):
            cells = [c.get_text(strip=True)[:20] for c in row.find_all(['th', 'td'])[:3]]
            print(f"    Row {j}: {cells}")

    # 「戦績」「レース」などのキーワードがあるか
    table_text = table.get_text()[:200]
    if '戦績' in table_text or 'レース' in table_text or '着順' in table_text:
        print(f"  ★ 戦績関連テーブル候補")

    print()

print("="*60)
