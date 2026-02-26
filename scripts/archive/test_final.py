"""
最終テスト - 全16頭取得確認
"""
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import re

race_id = 202508040612
url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--log-level=3')
options.add_experimental_option('excludeSwitches', ['enable-logging'])

driver = None
try:
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    driver.get(url)
    time.sleep(3)

    soup = BeautifulSoup(driver.page_source, 'lxml')
    table = soup.find('table', class_='Shutuba_Table')

    if table:
        horse_rows = table.select('tr.HorseList')
        print(f"HorseList行数: {len(horse_rows)}\n")

        horses = []
        for row in horse_rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                # 枠番（cols[0]）
                waku = cols[0].get_text(strip=True)

                # 馬番（cols[1]）
                umaban = cols[1].get_text(strip=True)

                # 馬名（cols[3]）
                horse_link = cols[3].find('a')
                horse_name = horse_link.get_text(strip=True) if horse_link else cols[3].get_text(strip=True)

                horses.append((waku, umaban, horse_name))
                print(f"枠{waku} 馬番{umaban}: {horse_name}")

        print(f"\n[結果] {len(horses)}頭取得")

        # 重複チェック
        umaban_list = [h[1] for h in horses]
        unique_umaban = set(umaban_list)
        print(f"ユニークな馬番数: {len(unique_umaban)}")

        if len(unique_umaban) == 16:
            print("[成功] 全16頭、重複なし！")
        else:
            print(f"[警告] 重複あり: {len(horses)}頭 -> {len(unique_umaban)}ユニーク")

except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()

finally:
    if driver:
        driver.quit()
