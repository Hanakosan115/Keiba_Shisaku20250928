"""
カレンダーURLのテスト
"""

import requests
from bs4 import BeautifulSoup

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# テスト日付
test_dates = [
    '20240810',  # 2024年8月10日（土）- データベースにあるはず
    '20241102',  # 2024年11月2日（土）
    '20241201',  # 2024年12月1日（日）
]

for date_str in test_dates:
    print(f"\n{'='*60}")
    print(f"テスト日付: {date_str}")
    print('='*60)

    url = f'https://race.netkeiba.com/top/race_list.html?date={date_str}'

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = 'EUC-JP'

        print(f"ステータス: {resp.status_code}")

        soup = BeautifulSoup(resp.content, 'html.parser')

        # race_id を含むリンクを探す
        links = soup.select('a[href*="race_id"]')
        print(f"race_id リンク数: {len(links)}")

        if links:
            print("\nサンプルリンク:")
            for link in links[:5]:
                print(f"  {link.get('href')}")

        # 全リンクからrace関連を探す
        all_links = soup.find_all('a', href=True)
        race_links = [l.get('href') for l in all_links if '202' in l.get('href', '')][:10]

        if race_links and not links:
            print("\n202を含むリンク（レースIDかも）:")
            for link in race_links:
                print(f"  {link}")

        # HTMLの一部を表示
        text_content = soup.get_text()
        if 'レース' in text_content or 'race' in text_content.lower():
            print("\n[OK] ページにレース関連の文字列あり")
        else:
            print("\n[?] ページにレース関連の文字列が見つからない")

    except Exception as e:
        print(f"エラー: {e}")

print("\n" + "="*60)
print("テスト完了")
print("="*60)
