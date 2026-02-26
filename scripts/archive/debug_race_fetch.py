"""
レース情報取得のデバッグ
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re

session = requests.Session()

# 先週の日曜日（12月1日）のレースを試す
test_dates = [
    '20241201',  # 先週日曜
    '20241130',  # 先週土曜
    '20241124',  # 先々週日曜
]

print("="*80)
print("レース情報取得テスト")
print("="*80)

for date_str in test_dates:
    print(f"\n日付: {date_str}")

    # いくつかのURL形式を試す
    urls_to_try = [
        f"https://race.netkeiba.com/top/race_list.html?kaisai_date={date_str}",
        f"https://race.netkeiba.com/top/calendar.html?year={date_str[:4]}&month={date_str[4:6]}",
        f"https://race.netkeiba.com/top/?kaisai_date={date_str}",
        f"https://db.netkeiba.com/race/list/{date_str[:4]}/",
    ]

    for url in urls_to_try:
        print(f"\nURL試行: {url}")

    try:
        response = session.get(url, timeout=10)
        print(f"ステータスコード: {response.status_code}")
        print(f"エンコーディング: {response.encoding}")

        response.encoding = 'EUC-JP'
        soup = BeautifulSoup(response.content, 'html.parser')

        # いくつかの方法でレースリンクを探す

        # 方法1: race_id を含むリンク
        race_links_1 = soup.select('a[href*="race_id="]')
        print(f"方法1（race_id=）: {len(race_links_1)}件")

        # 方法2: /race/ を含むリンク
        race_links_2 = soup.find_all('a', href=re.compile(r'/race/'))
        print(f"方法2（/race/）: {len(race_links_2)}件")

        # 方法3: すべてのリンクを確認
        all_links = soup.find_all('a', href=True)
        print(f"全リンク数: {len(all_links)}件")

        # 最初の数件を表示
        if race_links_1:
            print("\n見つかったレースリンク（最初の3件）:")
            for i, link in enumerate(race_links_1[:3], 1):
                print(f"  {i}. {link.get('href')} - {link.text.strip()}")

        # HTMLの一部を保存（デバッグ用）
        if date_str == test_dates[0]:
            with open('debug_html_sample.txt', 'w', encoding='utf-8') as f:
                # 最初の5000文字だけ
                f.write(response.text[:5000])
            print("\nHTML サンプルを debug_html_sample.txt に保存しました")

    except Exception as e:
        print(f"エラー: {e}")

    print("-"*80)

print("\n" + "="*80)
print("テスト完了")
print("="*80)
