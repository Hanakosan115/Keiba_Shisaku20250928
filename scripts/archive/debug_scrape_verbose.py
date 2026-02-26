"""
詳細デバッグ
"""

import requests
from bs4 import BeautifulSoup
import traceback

race_id = '202505050812'
url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

print(f"URL: {url}\n")

try:
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    response = session.get(url, timeout=10)
    print(f"Status: {response.status_code}")

    response.encoding = 'EUC-JP'
    soup = BeautifulSoup(response.content, 'html.parser')

    # レース名
    h1_tags = soup.find_all('h1')
    print(f"H1 tags: {len(h1_tags)}")

    if len(h1_tags) > 1:
        race_name = h1_tags[1].text.strip()
        print(f"レース名: {race_name}")

    # テーブル
    result_table = soup.find('table', class_='race_table_01')
    print(f"テーブル: {'あり' if result_table else 'なし'}")

    if result_table:
        rows = result_table.find_all('tr')[1:]
        print(f"行数: {len(rows)}")

        if rows:
            first_row = rows[0]
            cols = first_row.find_all('td')
            print(f"列数: {len(cols)}")

            if len(cols) >= 19:
                print("\n最初の行のデータ:")
                print(f"  馬番: {cols[2].text.strip()}")

                horse_elem = cols[3].find('a')
                if horse_elem:
                    print(f"  馬名: {horse_elem.text.strip()}")
                else:
                    print(f"  馬名: リンクなし - {cols[3].text.strip()}")

except Exception as e:
    print(f"\nエラー発生:")
    print(traceback.format_exc())
