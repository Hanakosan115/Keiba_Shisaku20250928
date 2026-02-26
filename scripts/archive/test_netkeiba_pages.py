"""
netkeibaの異なるページでラップタイム情報を探す
"""

import requests
from bs4 import BeautifulSoup
import re

def test_page(url, description):
    """指定されたURLをテストしてラップタイム情報を探す"""
    print("\n" + "=" * 80)
    print(f"テスト: {description}")
    print(f"URL: {url}")
    print("=" * 80)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        response.encoding = response.apparent_encoding

        # ラップタイムらしき数値パターン（10.0～20.0秒）
        lap_pattern = r'1[0-9]\.\d'
        matches = re.findall(lap_pattern, response.text)

        print(f"\nラップタイムらしき数値: {len(matches)}個")
        if matches:
            print(f"サンプル: {matches[:20]}")

        # "ラップ"という文字列
        if 'ラップ' in response.text:
            indices = [m.start() for m in re.finditer('ラップ', response.text)]
            print(f"\n'ラップ'の出現: {len(indices)}箇所")

            # 最初の出現箇所の前後を表示
            idx = indices[0]
            context = response.text[max(0, idx-100):min(len(response.text), idx+200)]
            print(f"コンテキスト:\n{context[:300]}")

        # ペースという文字列
        if 'ペース' in response.text:
            print(f"\n'ペース'が見つかりました")

        # 保存
        filename = f"test_{description.replace(' ', '_')}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"\n保存: {filename}")

        return True

    except Exception as e:
        print(f"\nエラー: {e}")
        return False


if __name__ == '__main__':
    race_id = "202411090411"  # 2024年11月9日 東京11R

    # 試すページの種類
    pages = [
        (f"https://race.netkeiba.com/race/result.html?race_id={race_id}", "結果ページ"),
        (f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}", "出馬表ページ"),
        (f"https://race.netkeiba.com/race/movie.html?race_id={race_id}", "動画ページ"),
        (f"https://race.netkeiba.com/race/newspaper.html?race_id={race_id}", "新聞ページ"),
        (f"https://race.netkeiba.com/race/oikiri.html?race_id={race_id}", "追い切りページ"),
        (f"https://db.netkeiba.com/race/{race_id}/", "DBページ"),
    ]

    for url, desc in pages:
        test_page(url, desc)
        print("\n待機中...")
        import time
        time.sleep(2)
