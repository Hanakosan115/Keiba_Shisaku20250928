"""
HTML構造の詳細調査
"""
from selenium import webdriver
from bs4 import BeautifulSoup
import time

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

        # 最初の4行を詳しく見る
        for idx in range(min(4, len(horse_rows))):
            row = horse_rows[idx]
            cols = row.find_all('td')

            print(f"=== 行{idx+1} ===")
            print(f"列数: {len(cols)}")

            # 各列の内容を表示
            for col_idx, col in enumerate(cols[:10]):  # 最初の10列
                text = col.get_text(strip=True)[:30]
                # エンコーディング問題を回避
                try:
                    print(f"  cols[{col_idx}]: {text}")
                except:
                    print(f"  cols[{col_idx}]: [encode error]")

            # HTMLも表示
            print(f"HTML (最初100文字): {str(row)[:100]}")
            print()

        # HTMLをファイルに保存
        with open('shutuba_table.html', 'w', encoding='utf-8') as f:
            f.write(str(table))
        print("HTMLをshutuba_table.htmlに保存しました")

except Exception as e:
    print(f"エラー: {e}")
    import traceback
    traceback.print_exc()

finally:
    if driver:
        driver.quit()
