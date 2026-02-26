"""
正しいURL（race_list_sub.html）のHTML構造を確認
"""

from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import re

date_str = '20251101'

# テストする複数のURLパターン
urls = [
    f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date_str}',
    f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={date_str}&current_group=1020251101',
]

for url in urls:
    print(f"\n{'='*60}")
    print(f"URL: {url}")
    print(f"{'='*60}")

    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument("--log-level=3")

    driver = None
    try:
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 30)

        driver.get(url)
        time.sleep(2)  # ページ読み込み待機

        soup = BeautifulSoup(driver.page_source, 'lxml')

        # race_idを含むリンクを全検索
        all_links = soup.find_all('a', href=True)
        race_id_links = []

        for a in all_links:
            href = a['href']
            # race_id=XXXX の形式を探す
            match = re.search(r'race_id=(\d{12})', href)
            if match:
                race_id_links.append(match.group(1))

        unique_ids = sorted(list(set(race_id_links)))

        print(f"\nレースID: {len(unique_ids)}件")
        if unique_ids:
            print("\n取得したレースID:")
            for rid in unique_ids[:15]:
                print(f"  - {rid}")
            if len(unique_ids) > 15:
                print(f"  ... 他{len(unique_ids)-15}件")

        # HTMLを保存
        filename = f"debug_race_list_sub_{date_str}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print(f"\nHTML保存: {filename}")

    except Exception as e:
        print(f"エラー: {e}")
    finally:
        if driver:
            driver.quit()

    time.sleep(2)
