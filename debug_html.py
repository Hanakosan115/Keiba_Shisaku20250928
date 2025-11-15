"""HTMLの構造を確認 - 3連複・3連単"""
import requests
from bs4 import BeautifulSoup
import time

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
race_id = '202006010101'
url = f'https://race.netkeiba.com/race/result.html?race_id={race_id}'

headers = {'User-Agent': USER_AGENT}
r = requests.get(url, headers=headers, timeout=30)
r.encoding = r.apparent_encoding
soup = BeautifulSoup(r.content, 'lxml')

# 配当テーブルを探す
payout_tables = soup.select('.Result_Pay_Back .Payout_Detail_Table')

if payout_tables:
    print("3連複・3連単のHTML構造確認:")
    print("=" * 60)

    target_types = ['三連複', '三連単', '3連複', '3連単']

    for table in payout_tables:
        rows = table.select('tr')
        for idx, row in enumerate(rows):
            th = row.select('th')
            td = row.select('td')

            if th:
                header_text = th[0].get_text(strip=True)
                # デバッグ：すべてのヘッダーを表示
                if idx < 15:  # 最初の15行だけ
                    print(f"[{idx}] TH: '{header_text}' (TH数:{len(th)}, TD数:{len(td)})")

                if any(t in header_text for t in target_types):
                    print(f"\n★ [{idx}] {header_text}ヘッダー行を発見！")
                    print(f"  TH数: {len(th)}, TD数: {len(td)}")

                    if len(td) >= 2:
                        print(f"\nTD[0] (馬番):")
                        print(td[0])

                        print(f"\nTD[1] (配当):")
                        print(td[1])

                        # 馬番の構造を確認
                        print(f"\n馬番の構造分析:")
                        print(f"  <li>要素数: {len(td[0].find_all('li'))}")
                        print(f"  <div>要素数: {len(td[0].find_all('div'))}")
                        print(f"  <span>要素数: {len(td[0].find_all('span'))}")
                        print(f"  テキスト: {td[0].get_text(strip=True)}")

                        # 配当の構造を確認
                        print(f"\n配当の構造分析:")
                        print(f"  <li>要素数: {len(td[1].find_all('li'))}")
                        print(f"  <span>要素数: {len(td[1].find_all('span'))}")
                        print(f"  <br>要素数: {len(td[1].find_all('br'))}")
                        print(f"  テキスト: {td[1].get_text(strip=True)}")
else:
    print("配当テーブルが見つかりません")
