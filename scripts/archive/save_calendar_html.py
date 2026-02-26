"""
カレンダーページのHTMLを保存
"""

import requests

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

url = 'https://race.netkeiba.com/top/race_list.html?date=20240810'

resp = requests.get(url, headers=headers, timeout=10)
resp.encoding = 'EUC-JP'

# HTMLをファイルに保存
with open('calendar_page_20240810.html', 'w', encoding='utf-8') as f:
    f.write(resp.text)

print(f"HTMLを保存しました: calendar_page_20240810.html")
print(f"ファイルサイズ: {len(resp.text)} 文字")
