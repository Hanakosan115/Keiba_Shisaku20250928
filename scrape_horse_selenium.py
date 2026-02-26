"""
Selenium版 - 馬の最新出走データをスクレイピング
JavaScriptで動的に読み込まれるレース成績を取得
"""
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup


def get_driver():
    """Seleniumドライバーを初期化"""
    options = Options()
    options.add_argument('--headless')  # ヘッドレスモード
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    driver = webdriver.Chrome(options=options)
    return driver


def scrape_horse_races_selenium(horse_id, since_date=None):
    """
    Seleniumを使って馬のレース履歴を取得

    Args:
        horse_id: 馬ID
        since_date: この日付以降のレースを取得（'YYYY年MM月DD日'形式）

    Returns:
        list: レースデータのリスト
    """
    url = f"https://db.netkeiba.com/horse/{horse_id}"
    driver = None

    try:
        driver = get_driver()
        driver.get(url)

        # ページ読み込み完了を待つ
        time.sleep(2)

        # レース成績テーブルが読み込まれるまで待機
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "db_h_race_results"))
            )
        except:
            print(f"  馬ID {horse_id}: レース成績テーブルの読み込みタイムアウト")
            return []

        # ページのHTMLを取得
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')

        # レース成績テーブル
        table = soup.find('table', class_='db_h_race_results')
        if not table:
            print(f"  馬ID {horse_id}: レース成績テーブルが見つかりません")
            return []

        rows = table.find_all('tr')[1:]  # ヘッダー除く
        new_races = []

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 14:
                continue

            # 日付
            date_text = cols[0].get_text(strip=True)
            try:
                race_date = datetime.strptime(date_text, '%Y/%m/%d')

                # since_date以降のデータのみ取得
                if since_date:
                    since_dt = datetime.strptime(since_date, '%Y年%m月%d日')
                    if race_date <= since_dt:
                        continue  # 既知のデータはスキップ
            except:
                continue

            # レースID
            race_link = cols[4].find('a')
            race_id = None
            if race_link:
                race_url = race_link.get('href', '')
                race_id_match = re.search(r'race_id=(\d+)', race_url)
                if race_id_match:
                    race_id = race_id_match.group(1)

            # 各種データを抽出
            track_name = cols[1].get_text(strip=True)
            race_name = cols[4].get_text(strip=True)

            # 距離
            distance_text = cols[14].get_text(strip=True) if len(cols) > 14 else ''
            distance_match = re.search(r'(\d+)', distance_text)
            distance = int(distance_match.group(1)) if distance_match else None

            # コースタイプ
            course_type = '芝' if '芝' in distance_text else 'ダート' if 'ダ' in distance_text else None

            # 馬場状態
            track_condition = cols[13].get_text(strip=True) if len(cols) > 13 else ''

            # 着順
            rank_text = cols[11].get_text(strip=True) if len(cols) > 11 else ''
            try:
                rank = int(rank_text)
            except:
                rank = None

            # 騎手
            jockey = cols[12].get_text(strip=True) if len(cols) > 12 else ''

            # 斤量
            weight_text = cols[5].get_text(strip=True)
            try:
                weight = float(weight_text)
            except:
                weight = None

            # タイム
            time_text = cols[7].get_text(strip=True) if len(cols) > 7 else ''

            # 通過順位
            passage_text = cols[10].get_text(strip=True) if len(cols) > 10 else ''

            # 単勝オッズ
            odds_text = cols[9].get_text(strip=True) if len(cols) > 9 else ''
            try:
                win_odds = float(odds_text)
            except:
                win_odds = None

            # 人気
            popularity_text = cols[10].get_text(strip=True) if len(cols) > 10 else ''

            new_races.append({
                'horse_id': horse_id,
                'race_id': race_id,
                'date': date_text,
                'track_name': track_name,
                'race_name': race_name,
                'distance': distance,
                'course_type': course_type,
                'track_condition': track_condition,
                '着順': rank_text,
                'rank': rank,
                '騎手': jockey,
                '斤量': weight,
                'タイム': time_text,
                '通過': passage_text,
                '単勝': win_odds,
                '人気': popularity_text,
            })

        return new_races

    except Exception as e:
        print(f"  馬ID {horse_id}: エラー - {e}")
        import traceback
        traceback.print_exc()
        return []

    finally:
        if driver:
            driver.quit()


# テスト
if __name__ == "__main__":
    print("=" * 80)
    print(" Selenium版 馬データ取得テスト")
    print("=" * 80)
    print()

    # マナエトレで テスト
    test_horse_id = "2022102691"

    print(f"テスト対象馬ID: {test_horse_id} (マナエトレ)")
    print("取得開始日: 2025年08月17日")
    print()

    races = scrape_horse_races_selenium(test_horse_id, "2025年08月17日")

    if races:
        print(f"OK: {len(races)}件の新規レースを取得しました")
        print()
        print("取得データ:")
        for i, race in enumerate(races[:5], 1):
            print(f"  {i}. {race['date']} - {race['race_name']} ({race['track_name']}) 着順:{race['着順']}")
    else:
        print("NG: データ取得失敗または新規レースなし")
