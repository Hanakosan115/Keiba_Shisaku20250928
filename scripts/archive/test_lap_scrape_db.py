"""
db.netkeiba.comからラップタイムを取得するテスト
"""

import requests
from bs4 import BeautifulSoup
import re

def scrape_lap_from_db(race_id):
    """DBページからラップタイムを取得"""
    url = f"https://db.netkeiba.com/race/{race_id}/"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    print(f"URL: {url}")
    print("=" * 80)

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding

        soup = BeautifulSoup(response.text, 'html.parser')

        # ラップタイムテーブルを探す
        lap_table = soup.find('table', summary='ラップタイム')
        if not lap_table:
            lap_table = soup.find('table', class_='result_table_02')

        if lap_table:
            print("\nラップタイムテーブル見つかりました！")
            print("-" * 80)

            # テーブルの内容を表示
            rows = lap_table.find_all('tr')
            print(f"行数: {len(rows)}")

            for i, row in enumerate(rows):
                cells = row.find_all(['td', 'th'])
                cell_texts = [cell.get_text(strip=True) for cell in cells]
                if cell_texts:
                    print(f"行 {i}: {cell_texts}")

            # ラップタイムの数値を抽出
            table_text = lap_table.get_text()
            lap_pattern = r'1[0-9]\.\d'
            laps = re.findall(lap_pattern, table_text)

            if laps:
                print(f"\n抽出したラップタイム: {laps}")
                return [float(lap) for lap in laps]
            else:
                print("\nラップタイム数値が見つかりませんでした")

        else:
            print("\nラップタイムテーブルが見つかりませんでした")

            # 代替: テーブル構造を確認
            all_tables = soup.find_all('table')
            print(f"\n全テーブル数: {len(all_tables)}")

            for i, table in enumerate(all_tables):
                summary = table.get('summary', '')
                class_name = table.get('class', '')
                print(f"  テーブル {i}: summary='{summary}', class='{class_name}'")

                # テーブルのキャプションを確認
                caption = table.find('caption')
                if caption:
                    print(f"    caption: {caption.get_text(strip=True)}")

        # HTMLを保存
        with open(f"lap_test_{race_id}.html", 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"\nHTML保存: lap_test_{race_id}.html")

        return None

    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    # 既存CSVのレースIDでテスト
    test_race_ids = [
        "202006010101",  # 2020年6月
        "202008010105",  # 2020年8月
        "202308050811",  # 2023年8月  (より新しいデータ)
    ]

    for race_id in test_race_ids:
        print("\n" + "=" * 80)
        print(f"レースID: {race_id}")
        print("=" * 80)

        result = scrape_lap_from_db(race_id)

        if result:
            print(f"\n成功: {len(result)}個のラップタイムを取得")
        else:
            print(f"\n失敗: ラップタイムを取得できませんでした")

        print("\n待機中...")
        import time
        time.sleep(2)
