"""
特定の開催日のレースID収集をテスト
"""

import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup

kaisai_date = '20251207'  # 2025年12月7日

url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={kaisai_date}'

print("="*60)
print(f"開催日 {kaisai_date} のレースID収集テスト")
print("="*60)
print()
print(f"URL: {url}")
print()

# Chromeオプション（ヘッドレス無効化してテスト）
chrome_options = Options()
# chrome_options.add_argument('--headless')  # ←コメントアウト
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')

driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 30)

try:
    print("ページ読み込み中...")
    driver.get(url)

    print("レース一覧待機中...")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#RaceTopRace')))

    print("JavaScript実行完了待機中（3秒）...")
    import time
    time.sleep(3)

    print("レースリンク存在確認中...")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.RaceList_DataItem > a')))

    soup = BeautifulSoup(driver.page_source, 'html.parser')

    print("レースID抽出中...")
    print()

    race_ids = []
    # セレクタを広範囲に変更
    for a_tag in soup.select('a[href*="race_id="]'):
        href = a_tag.get('href', '')
        match = re.search(r'race_id=(\d{12})', href)
        if match:
            race_id = match.group(1)
            if race_id not in race_ids:
                race_ids.append(race_id)

    print(f"取得レースID数: {len(race_ids)}件")
    print()

    if race_ids:
        print("レースID一覧:")
        for i, race_id in enumerate(race_ids, 1):
            # レースIDを分解
            year = race_id[:4]
            place = race_id[4:6]
            meeting = race_id[6:8]
            day = race_id[8:10]
            race_num = race_id[10:12]

            print(f"  [{i:2d}] {race_id}  (年:{year}, 場:{place}, 回:{meeting}, 日:{day}, R:{race_num})")

    print()
    print("="*60)

finally:
    driver.quit()
