import requests
from bs4 import BeautifulSoup
import re

race_id = '202408010104'
url = f'https://db.netkeiba.com/race/{race_id}/'

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
response = requests.get(url, headers=headers, timeout=10)
response.encoding = response.apparent_encoding
soup = BeautifulSoup(response.content, 'html.parser')

print('='*80)
print('NetKeiba レースページ構造分析')
print('='*80)

# レース名
print('\n[1] レース名:')
h1_tags = soup.find_all('h1')
if len(h1_tags) > 1:
    race_name = h1_tags[1].text.strip()
    print(f'   {race_name}')

# レースデータ（距離・馬場など）探索
print('\n[2] レースデータ候補:')
# diary_race_data
diary = soup.find('diary_race_data')
if diary:
    print(f'   diary_race_data: あり')

# p.smalltxt
smalltxt = soup.find('p', class_='smalltxt')
if smalltxt:
    text = smalltxt.text.strip()
    print(f'   p.smalltxt: {text[:80]}...')
    # 距離抽出
    distance_match = re.search(r'(\d+)m', text)
    if distance_match:
        print(f'   距離: {distance_match.group(1)}m')

# data_intro
data_intro = soup.find('div', class_='data_intro')
if data_intro:
    print(f'   div.data_intro: {data_intro.text.strip()[:80]}...')

# race_otherdata
race_other = soup.find('div', class_='race_otherdata')
if race_other:
    print(f'   div.race_otherdata: あり')

# テーブル構造
print('\n[3] 結果テーブル:')
table = soup.find('table', class_='race_table_01')
if table:
    rows = table.find_all('tr')
    print(f'   総行数: {len(rows)}')
    
    # ヘッダー
    if len(rows) > 0:
        headers_row = rows[0].find_all('th')
        print(f'   列数: {len(headers_row)}')
        print('   列名:')
        for i, th in enumerate(headers_row):
            print(f'     [{i:2d}] {th.text.strip()}')
    
    # サンプルデータ
    if len(rows) > 1:
        print('\n   サンプルデータ（1行目）:')
        sample = rows[1].find_all('td')
        for i, td in enumerate(sample):
            text = td.text.strip()
            # リンクがあるか確認
            link = td.find('a')
            if link:
                text += f' [LINK: {link.get("href", "")[:30]}]'
            print(f'     [{i:2d}] {text[:50]}')

print('\n' + '='*80)
