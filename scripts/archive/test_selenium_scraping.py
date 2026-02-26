"""
Seleniumスクレイピングテスト - 全頭取得確認
"""
from selenium import webdriver
from bs4 import BeautifulSoup
import time

race_id = 202508040612
url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"

print(f"URL: {url}")
print("Seleniumで取得中...")

# Chromeオプション設定
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
    time.sleep(3)  # JavaScript実行を待つ

    soup = BeautifulSoup(driver.page_source, 'lxml')

    # テーブル取得
    table = soup.find('table', class_='Shutuba_Table')

    if not table:
        print("[エラー] テーブルが見つかりません")
    else:
        # tr.HorseListを取得
        horse_rows = table.select('tr.HorseList')
        print(f"\nHorseList行数: {len(horse_rows)}")

        for idx, row in enumerate(horse_rows, 1):
            cols = row.find_all('td')
            if len(cols) >= 4:
                # 馬番
                umaban_span = cols[0].find('span')
                umaban = umaban_span.get_text(strip=True) if umaban_span else cols[0].get_text(strip=True)

                # 馬名
                horse_link = cols[3].find('a')
                horse_name = horse_link.get_text(strip=True) if horse_link else cols[3].get_text(strip=True)

                print(f"  {idx}. 馬番{umaban}: {horse_name}")

        print(f"\n[結果] {len(horse_rows)}頭取得")

        if len(horse_rows) == 16:
            print("[成功] 全16頭取得成功！")
        elif len(horse_rows) == 8:
            print("[警告] 8頭のみ - JavaScriptが実行されていない可能性")
        else:
            print(f"[情報] {len(horse_rows)}頭取得")

except Exception as e:
    print(f"[エラー] {e}")
    import traceback
    traceback.print_exc()

finally:
    if driver:
        driver.quit()
        print("\nChromeDriverを終了しました")
