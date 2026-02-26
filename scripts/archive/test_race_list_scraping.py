"""
レース一覧ページからレースIDを取得するテスト
"""

import re
import requests
from bs4 import BeautifulSoup

def get_race_ids_from_date(kaisai_date):
    """開催日からレースIDを取得"""
    url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={kaisai_date}'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.content, 'html.parser')

        race_ids = []

        # レース一覧からIDを抽出
        for a_tag in soup.select('a[href*="race_id="]'):
            href = a_tag.get('href', '')
            match = re.search(r'race_id=(\d{12})', href)
            if match:
                race_id = match.group(1)
                if race_id not in race_ids:  # 重複排除
                    race_ids.append(race_id)

        return race_ids

    except Exception as e:
        print(f"エラー: {e}")
        return []


if __name__ == '__main__':
    print("="*60)
    print("レース一覧スクレイピングテスト")
    print("="*60)
    print()

    # 2025年9月6日（先ほどのカレンダーから取得した最初の開催日）でテスト
    test_date = '20250906'

    print(f"開催日: {test_date}")
    print()

    race_ids = get_race_ids_from_date(test_date)

    if race_ids:
        print(f"取得レースID数: {len(race_ids)}件")
        print()
        print("レースID一覧:")
        for race_id in race_ids[:20]:  # 最初の20件表示
            print(f"  {race_id}")
        if len(race_ids) > 20:
            print(f"  ... 他{len(race_ids) - 20}件")
    else:
        print("レースIDが取得できませんでした")
        print()
        print("requestsでは取得できない可能性があります（JavaScript動的生成）")

    print("\n" + "="*60)
