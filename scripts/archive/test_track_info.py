"""
馬場情報の取得テスト

netkeibaから以下の情報を取得：
1. 開催週数（開幕週 vs 最終週）
2. 馬場状態の詳細
3. 内外バイアス情報
4. 馬場コメント
"""

import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

def test_track_info(race_id):
    """レースIDから馬場情報を取得してテスト"""
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

        print("\n【基本情報】")
        print("-" * 80)

        # レース名とタイトル
        race_title = soup.find('h1')
        if race_title:
            print(f"レース名: {race_title.get_text(strip=True)}")

        # レースデータセクションを探す
        race_data = soup.find_all('div', class_='RaceData01')
        for data in race_data:
            text = data.get_text()
            print(f"レース情報: {text[:200]}")

        # diary_snap_cutセクション（レース情報詳細）
        diary = soup.find('div', class_='diary_snap_cut')
        if diary:
            print(f"\n詳細情報: {diary.get_text(strip=True)[:300]}")

        # テーブルから情報を抽出
        print("\n【テーブルデータ】")
        print("-" * 80)

        tables = soup.find_all('table')
        print(f"テーブル数: {len(tables)}")

        for i, table in enumerate(tables[:5]):  # 最初の5つのテーブルを確認
            caption = table.find('caption')
            summary = table.get('summary', '')
            class_name = table.get('class', '')

            if caption or summary:
                print(f"\nテーブル {i}:")
                if caption:
                    print(f"  キャプション: {caption.get_text(strip=True)}")
                if summary:
                    print(f"  サマリー: {summary}")
                print(f"  クラス: {class_name}")

                # テーブルの内容をサンプル表示
                rows = table.find_all('tr')[:3]
                for row in rows:
                    cells = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                    if cells:
                        print(f"    {cells}")

        # 開催情報を探す
        print("\n【開催情報】")
        print("-" * 80)

        # レースIDから開催情報を抽出
        # race_id format: YYYYMMDDKKVV (例: 202006010101)
        # YYYY: 年, MM: 月, DD: 日, KK: 競馬場コード, VV: レース番号

        year = race_id[:4]
        month = race_id[4:6]
        day = race_id[6:8]
        track_code = race_id[8:10]
        race_num = race_id[10:12]

        print(f"レースID解析:")
        print(f"  年月日: {year}年{month}月{day}日")
        print(f"  競馬場コード: {track_code}")
        print(f"  レース番号: {race_num}")

        # 競馬場コードから競馬場名を取得
        track_names = {
            '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
            '05': '東京', '06': '中山', '07': '中京', '08': '京都',
            '09': '阪神', '10': '小倉'
        }
        track_name = track_names.get(track_code, f'不明({track_code})')
        print(f"  競馬場: {track_name}")

        # 開催週数を探す
        # 開催情報は通常「○回○○○日」のような形式
        kaisai_pattern = r'(\d+)回.+?(\d+)日'
        all_text = soup.get_text()

        kaisai_match = re.search(kaisai_pattern, all_text)
        if kaisai_match:
            kai_num = kaisai_match.group(1)  # 何回目の開催
            day_num = kaisai_match.group(2)  # 何日目
            print(f"\n開催情報:")
            print(f"  第{kai_num}回開催")
            print(f"  {day_num}日目")

            # 開催週数を計算（通常3日で1週）
            week_num = (int(day_num) - 1) // 3 + 1
            print(f"  推定開催週: {week_num}週目")

        # 馬場状態を探す
        print("\n【馬場状態】")
        print("-" * 80)

        # 馬場状態のパターン: 芝:良、ダート:稍重 など
        track_condition_pattern = r'(芝|ダート)\s*:\s*([良稍重不]{1,2})'
        conditions = re.findall(track_condition_pattern, all_text)

        if conditions:
            for surface, condition in conditions:
                print(f"  {surface}: {condition}")
        else:
            print("  馬場状態が見つかりませんでした")

        # 天候を探す
        weather_pattern = r'天候\s*:\s*([晴曇雨雪]{1,2})'
        weather = re.search(weather_pattern, all_text)
        if weather:
            print(f"  天候: {weather.group(1)}")

        # コメントやバイアス情報を探す
        print("\n【コメント・バイアス】")
        print("-" * 80)

        # 内外、前後などのキーワードを探す
        bias_keywords = ['内', '外', '前', '後', '差し', '先行', '逃げ', '有利', '不利']
        for keyword in bias_keywords:
            if keyword in all_text:
                # キーワード周辺のテキストを抽出
                idx = all_text.find(keyword)
                context = all_text[max(0, idx-50):min(len(all_text), idx+100)]
                if len(context.strip()) > 10:
                    print(f"  '{keyword}': ...{context[:100]}...")
                    break

        # HTMLを保存
        with open(f"track_test_{race_id}.html", 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"\nHTML保存: track_test_{race_id}.html")

    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    # テスト用レースID
    test_race_ids = [
        "202006010101",  # 2020年6月 札幌
        "202008050811",  # 2020年8月 阪神
        "202309030211",  # 2023年9月 函館
    ]

    for race_id in test_race_ids:
        print("\n" + "=" * 80)
        print(f"レースID: {race_id}")
        print("=" * 80)
        test_track_info(race_id)
        print("\n待機中...")
        import time
        time.sleep(2)
