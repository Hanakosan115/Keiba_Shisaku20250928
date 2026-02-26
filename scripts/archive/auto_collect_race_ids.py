"""
カレンダーから完全自動でレースID収集

参考: https://github.com/scraproace/netkeiba_sample.git
"""

import re
import time
from bs4 import BeautifulSoup
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options


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

        for a_tag in soup.select('.Calendar_Table .Week > td > a'):
            href = a_tag.get('href', '')
            match = re.search(r'kaisai_date=(\d{8})', href)
            if match:
                kaisai_date = match.group(1)
                kaisai_dates.append(kaisai_date)

        return kaisai_dates

    except Exception as e:
        print(f"  エラー: {e}")
        return []


def get_race_ids_from_date(kaisai_date, driver=None):
    """開催日からレースIDを取得（Selenium使用）"""
    url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={kaisai_date}'

    close_driver = False
    if driver is None:
        # Chromeオプション設定（ヘッドレスモード）
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        driver = webdriver.Chrome(options=chrome_options)
        close_driver = True

    wait = WebDriverWait(driver, 30)

    try:
        driver.get(url)

        # ページ読み込み待機
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#RaceTopRace')))

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        race_ids = []

        for a_tag in soup.select('.RaceList_DataItem > a:first-of-type'):
            href = a_tag.get('href', '')
            match = re.search(r'race_id=(\d{12})', href)
            if match:
                race_id = match.group(1)
                if race_id not in race_ids:
                    race_ids.append(race_id)

        return race_ids

    except Exception as e:
        print(f"    エラー: {e}")
        return []

    finally:
        if close_driver:
            driver.quit()


def collect_race_ids_for_period(start_year, start_month, end_year, end_month):
    """期間のレースIDを全自動収集"""
    print("="*60)
    print("レースID自動収集システム")
    print("="*60)
    print()

    all_race_ids = []

    # Seleniumドライバーを1回だけ起動（高速化）
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    print("Chromeドライバー起動中...")
    driver = webdriver.Chrome(options=chrome_options)
    print("起動完了\n")

    try:
        # 年月ループ
        current_year = start_year
        current_month = start_month

        while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
            print(f"{current_year}年{current_month}月:")

            # カレンダーから開催日取得
            kaisai_dates = get_kaisai_dates(current_year, current_month)

            if not kaisai_dates:
                print("  開催日なし\n")
            else:
                print(f"  開催日: {len(kaisai_dates)}日")

                # 各開催日のレースID取得
                month_race_ids = []
                for kaisai_date in kaisai_dates:
                    print(f"    {kaisai_date}...", end=" ")

                    race_ids = get_race_ids_from_date(kaisai_date, driver)

                    if race_ids:
                        month_race_ids.extend(race_ids)
                        print(f"OK ({len(race_ids)}レース)")
                    else:
                        print("NG")

                    time.sleep(0.5)  # アクセス制限回避

                all_race_ids.extend(month_race_ids)
                print(f"  月間合計: {len(month_race_ids)}レース\n")

            # 次の月へ
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

    finally:
        driver.quit()
        print("\nChromeドライバー終了")

    print("\n" + "="*60)
    print(f"収集完了: 合計 {len(all_race_ids)}レース")
    print("="*60)

    return all_race_ids


def save_race_ids_to_file(race_ids, filename='race_ids_auto.txt'):
    """レースIDをファイルに保存"""
    with open(filename, 'w', encoding='utf-8') as f:
        for race_id in race_ids:
            f.write(f"{race_id}\n")
    print(f"\n保存完了: {filename}")


if __name__ == '__main__':
    # 2025年9月～12月を収集
    race_ids = collect_race_ids_for_period(2025, 9, 2025, 12)

    if race_ids:
        # ファイルに保存
        save_race_ids_to_file(race_ids, 'race_ids_2025_sep_dec.txt')

        print(f"\nレースID例（最初の10件）:")
        for race_id in race_ids[:10]:
            print(f"  {race_id}")

        print(f"\n次のステップ:")
        print(f"  1. VPN接続")
        print(f"  2. py update_from_list.py を実行")
        print(f"     または 統合GUIツールから更新")
    else:
        print("\nレースIDが取得できませんでした")

    input("\nEnterキーを押して終了...")
