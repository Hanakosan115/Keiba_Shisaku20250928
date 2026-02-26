"""
NetKeibaのAJAX血統エンドポイントを試す
"""

import requests
import time

def main():
    horse_id = '2021105700'

    # AJAXエンドポイント
    ajax_url = 'https://db.netkeiba.com/horse/ajax_horse_pedigree.html'

    print("="*60)
    print(f"AJAX血統エンドポイントテスト")
    print(f"horse_id: {horse_id}")
    print("="*60)

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': f'https://db.netkeiba.com/horse/{horse_id}/'
    })

    try:
        time.sleep(1)

        # AJAXリクエストのパラメータ
        params = {
            'input': 'UTF-8',
            'output': 'json',
            'horse_id': horse_id
        }

        print(f"\nURL: {ajax_url}")
        print(f"Params: {params}")

        r = session.get(ajax_url, params=params, timeout=10)
        r.raise_for_status()

        print(f"\nStatus code: {r.status_code}")
        print(f"Content-Type: {r.headers.get('Content-Type')}")
        print(f"Response length: {len(r.text)} bytes")

        # JSONレスポンスを試みる
        try:
            json_data = r.json()
            print(f"\nJSON response:")
            print(f"  status: {json_data.get('status')}")
            if 'data' in json_data:
                html_data = json_data['data']
                print(f"  data length: {len(html_data)} characters")

                # HTMLから父と母父を抽出
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html_data, 'lxml')

                # 血統テーブルを探す
                blood_table = soup.find('table')
                if blood_table:
                    print(f"\n  ★ 血統テーブル発見！")

                    # 最初の数行を表示
                    rows = blood_table.find_all('tr')[:5]
                    print(f"  テーブル行数: {len(blood_table.find_all('tr'))}")

                    for i, row in enumerate(rows, 1):
                        cells = row.find_all(['td', 'th'])
                        cell_texts = [c.get_text(strip=True)[:30] for c in cells[:3]]
                        print(f"    Row {i}: {cell_texts}")
                else:
                    print(f"\n  血統テーブルが見つかりません")
                    print(f"  HTML preview: {html_data[:200]}")
        except ValueError:
            # JSONでない場合
            print(f"\nResponse (not JSON):")
            print(r.text[:500])

    except Exception as e:
        print(f"\nエラー: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "="*60)

if __name__ == '__main__':
    main()
