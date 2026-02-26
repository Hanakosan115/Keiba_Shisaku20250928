"""
カレンダーページから開催日を取得するテスト
"""

import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def get_kaisai_dates(year, month):
    """指定年月の開催日を取得"""
    url = f'https://race.netkeiba.com/top/calendar.html?year={year}&month={month}'

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()

        soup = BeautifulSoup(r.content, 'html.parser')

        kaisai_dates = []

        # カレンダーテーブルからリンクを探す
        for a_tag in soup.select('.Calendar_Table .Week > td > a'):
            href = a_tag.get('href', '')
            match = re.search(r'kaisai_date=(\d{8})', href)
            if match:
                kaisai_date = match.group(1)
                kaisai_dates.append(kaisai_date)

        return kaisai_dates

    except Exception as e:
        print(f"エラー: {e}")
        return []


if __name__ == '__main__':
    print("="*60)
    print("カレンダースクレイピングテスト")
    print("="*60)
    print()

    # 2025年9月～12月をテスト
    for month in [9, 10, 11, 12]:
        print(f"\n2025年{month}月:")
        kaisai_dates = get_kaisai_dates(2025, month)

        if kaisai_dates:
            print(f"  開催日数: {len(kaisai_dates)}日")
            print(f"  開催日: {', '.join(kaisai_dates[:5])}", end="")
            if len(kaisai_dates) > 5:
                print(f" ... ({len(kaisai_dates)}日)")
            else:
                print()
        else:
            print("  開催日が取得できませんでした")

    print("\n" + "="*60)
