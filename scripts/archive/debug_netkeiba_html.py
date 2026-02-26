"""
netkeibaのHTML構造を確認するデバッグスクリプト
"""

import requests
from bs4 import BeautifulSoup

def debug_race_page(race_id):
    """レースページのHTML構造を確認"""
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

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

        # ラップという文字を含む要素を全て探す
        print("\n'ラップ'を含む要素:")
        print("-" * 80)

        # 全テキストから"ラップ"を探す
        all_text = soup.get_text()
        if 'ラップ' in all_text:
            # "ラップ"の前後のテキストを抽出
            idx = all_text.find('ラップ')
            context = all_text[max(0, idx-50):min(len(all_text), idx+200)]
            print(f"テキスト内容:\n{context}\n")

        # div要素を探す
        for div in soup.find_all('div'):
            text = div.get_text(strip=True)
            if 'ラップ' in text or 'LAP' in text.upper():
                print(f"\nDIV要素:")
                print(f"  クラス: {div.get('class')}")
                print(f"  ID: {div.get('id')}")
                print(f"  テキスト: {text[:200]}")

        # table要素を探す
        for table in soup.find_all('table'):
            text = table.get_text(strip=True)
            if 'ラップ' in text or 'LAP' in text.upper():
                print(f"\nTABLE要素:")
                print(f"  クラス: {table.get('class')}")
                print(f"  テキスト: {text[:200]}")

        # span要素を探す
        for span in soup.find_all('span'):
            text = span.get_text(strip=True)
            if 'ラップ' in text:
                print(f"\nSPAN要素:")
                print(f"  クラス: {span.get('class')}")
                print(f"  テキスト: {text}")

        # ページの主要な構造を出力
        print("\n" + "=" * 80)
        print("主要なクラス名:")
        print("-" * 80)
        all_classes = set()
        for elem in soup.find_all(class_=True):
            classes = elem.get('class', [])
            if isinstance(classes, list):
                all_classes.update(classes)

        for cls in sorted(all_classes):
            if any(keyword in cls.lower() for keyword in ['race', 'data', 'lap', 'result', 'time']):
                print(f"  {cls}")

        # HTMLの一部を保存
        print("\n" + "=" * 80)
        print("HTML保存:")
        with open(f"debug_race_{race_id}.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print(f"  debug_race_{race_id}.html に保存しました")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # 最近のレースで確認
    race_id = "202411090411"  # 2024年11月9日 東京11R
    debug_race_page(race_id)
