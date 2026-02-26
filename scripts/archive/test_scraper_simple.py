"""
シンプルなスクレイピングテスト
以前動いていたコードを参考に
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

race_id = '202408010104'
url = f'https://db.netkeiba.com/race/{race_id}/'

print(f'URL: {url}')

response = requests.get(url, headers=headers, timeout=10)
response.encoding = response.apparent_encoding

soup = BeautifulSoup(response.text, 'html.parser')

# テーブル取得
result_table = soup.find('table', class_='race_table_01')

if not result_table:
    print('テーブルが見つかりません')
    exit()

print(f'テーブル取得成功')

# レース名
race_title_elem = soup.find('h1', class_='raceTitle')
race_name = race_title_elem.text.strip() if race_title_elem else 'N/A'

# データ抽出
rows = result_table.find_all('tr')[1:]  # ヘッダー除く

horses = []

for row in rows:
    cols = row.find_all('td')

    if len(cols) < 13:
        continue

    try:
        rank = int(cols[0].text.strip())
        waku = int(cols[1].text.strip())
        umaban = int(cols[2].text.strip())

        # 馬名（4列目）
        horse_name = cols[4].text.strip()

        # オッズ（13列目 - インデックス12）
        odds_text = cols[12].text.strip()
        odds = float(odds_text)

        # 人気（14列目 - インデックス13）
        ninki_text = cols[13].text.strip()
        ninki = int(ninki_text)

        horses.append({
            'race_id': race_id,
            'race_name': race_name,
            'Rank': rank,
            'Waku': waku,
            'Umaban': umaban,
            'HorseName': horse_name,
            'Odds': odds,
            'Ninki': ninki
        })

    except (ValueError, IndexError) as e:
        print(f'エラー（行スキップ）: {e}')
        continue

print(f'\n取得: {len(horses)}頭')

if len(horses) > 0:
    df = pd.DataFrame(horses)
    print('\n上位3頭:')
    print(df[['Rank', 'Umaban', 'HorseName', 'Odds', 'Ninki']].head(3))
    print('\nSUCCESS!')
else:
    print('データ取得失敗')
