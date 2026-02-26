"""
レース一覧ページのHTML構造をデバッグ
"""

import requests
from bs4 import BeautifulSoup
import time

date_str = '20251101'
url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={date_str}'

print(f"URL: {url}")
print()

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
})

time.sleep(1.0)
r = session.get(url, timeout=10)
r.encoding = r.apparent_encoding

print(f"Status: {r.status_code}")
print()

soup = BeautifulSoup(r.content, 'lxml')

# セレクタテスト1: 元のセレクタ
selector1 = '.RaceList_DataItem > a:first-of-type'
links1 = soup.select(selector1)
print(f"セレクタ1 '{selector1}': {len(links1)}件")

# セレクタテスト2: より広範囲
selector2 = '.RaceList_DataItem a'
links2 = soup.select(selector2)
print(f"セレクタ2 '{selector2}': {len(links2)}件")

# セレクタテスト3: テーブル全体
selector3 = 'table a'
links3 = soup.select(selector3)
print(f"セレクタ3 '{selector3}': {len(links3)}件")

# リンク解析
if links2:
    print(f"\n最初の5つのリンク（セレクタ2）:")
    for i, link in enumerate(links2[:5], 1):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        print(f"  {i}. text='{text[:30]}' href='{href[:80]}'")

# "race_id" を含むリンクを探す
race_id_links = [a for a in soup.find_all('a') if 'race_id=' in str(a.get('href', ''))]
print(f"\n'race_id=' を含むリンク: {len(race_id_links)}件")

if race_id_links:
    print(f"\n最初の3つのrace_idリンク:")
    for i, link in enumerate(race_id_links[:3], 1):
        href = link.get('href', '')
        text = link.get_text(strip=True)
        print(f"  {i}. text='{text[:30]}' href='{href[:80]}'")

# "no_race" 要素の確認
no_race = soup.select_one('.no_race')
if no_race:
    print(f"\n'.no_race' 要素が見つかりました: {no_race.get_text(strip=True)}")
else:
    print(f"\n'.no_race' 要素は見つかりませんでした")

# RaceList_Item02 の確認
racelist_item = soup.select_one('.RaceList_Item02')
if racelist_item:
    print(f"\n'.RaceList_Item02' 要素が見つかりました: {racelist_item.get_text(strip=True)[:100]}")
else:
    print(f"\n'.RaceList_Item02' 要素は見つかりませんでした")

# HTMLファイルに保存（デバッグ用）
with open(f'debug_race_list_{date_str}.html', 'w', encoding='utf-8') as f:
    f.write(soup.prettify())
    print(f"\nHTML保存: debug_race_list_{date_str}.html")
