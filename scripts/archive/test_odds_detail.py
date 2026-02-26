"""
オッズ取得の詳細確認（3レース）
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def get_race_details_with_odds(race_id):
    """レース結果とオッズを詳細表示"""
    url = f"https://db.netkeiba.com/race/{race_id}/"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    response = requests.get(url, headers=headers, timeout=10)
    response.encoding = response.apparent_encoding

    soup = BeautifulSoup(response.text, 'html.parser')

    # レース結果テーブル
    result_table = soup.find('table', class_='race_table_01')
    if not result_table:
        result_table = soup.find('table', summary='レース結果')

    if not result_table:
        print(f"  テーブルが見つかりません")
        return None

    # ヘッダー行を取得
    header_row = result_table.find('tr')
    headers = [th.get_text(strip=True) for th in header_row.find_all('th')]

    print(f"\n  テーブル列数: {len(headers)}")
    print(f"  列ヘッダー: {headers[:15]}")  # 最初の15列

    # データ行を解析
    rows = result_table.find_all('tr')[1:]  # ヘッダーをスキップ

    results = []

    for i, row in enumerate(rows[:5]):  # 最初の5行だけ表示
        cells = row.find_all('td')

        if len(cells) < 5:
            continue

        # 各セルの内容を取得
        cell_data = [cell.get_text(strip=True) for cell in cells]

        print(f"\n  {i+1}着:")
        print(f"    セル数: {len(cells)}")

        # 主要情報を表示
        for j, data in enumerate(cell_data[:15]):  # 最初の15セル
            print(f"    [{j}] {data}")

        results.append(cell_data)

    return results

print("=" * 80)
print("オッズ取得詳細テスト（3レース）")
print("=" * 80)

test_races = [
    "202406010101",  # 2024年6月 札幌
    "202406020111",  # 2024年6月 東京
    "202406030211",  # 2024年6月 阪神
]

for race_id in test_races:
    print(f"\n{'='*80}")
    print(f"レースID: {race_id}")
    print(f"URL: https://db.netkeiba.com/race/{race_id}/")
    print("=" * 80)

    results = get_race_details_with_odds(race_id)

    time.sleep(2)

print("\n" + "=" * 80)
print("完了")
print("=" * 80)
