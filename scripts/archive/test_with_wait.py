"""
ページ読み込み待機を増やしてテスト
"""

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import re

date_str = '20251101'
url = f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date_str}&current_group=1020251101'

print(f"URL: {url}")
print()

options = webdriver.ChromeOptions()
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument("--log-level=3")
# ヘッドレスを無効にして実際のブラウザで確認
# options.add_argument('--headless')

driver = None
try:
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 30)

    print("ページアクセス中...")
    driver.get(url)

    print("初期待機（5秒）...")
    time.sleep(5)

    # RaceList_DataItemが表示されるまで待つ
    try:
        print("レースリスト要素の待機...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.RaceList_DataItem')))
        print("レースリスト要素が見つかりました")
    except:
        print("警告: レースリスト要素が見つかりませんでした")

    print("追加待機（10秒）...")
    time.sleep(10)

    # ページタイトルを確認
    print(f"\nページタイトル: {driver.title}")

    # HTMLを取得
    soup = BeautifulSoup(driver.page_source, 'lxml')

    # race_id リンクを検索
    race_ids = []
    for a in soup.find_all('a', href=True):
        match = re.search(r'race_id=(\d{12})', a['href'])
        if match:
            race_ids.append(match.group(1))

    unique_ids = sorted(list(set(race_ids)))

    print(f"\n取得したレースID: {len(unique_ids)}件")
    for rid in unique_ids[:10]:
        # レースIDの日付部分を抽出
        year = rid[:4]
        month = rid[4:6]
        day = rid[6:8]
        print(f"  {rid} ({year}年{month}月{day}日)")

    # スクリーンショット保存
    driver.save_screenshot('screenshot_race_list.png')
    print("\nスクリーンショット保存: screenshot_race_list.png")

    print("\n10秒間ブラウザを開いたまま待機します...")
    time.sleep(10)

except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()
finally:
    if driver:
        driver.quit()
