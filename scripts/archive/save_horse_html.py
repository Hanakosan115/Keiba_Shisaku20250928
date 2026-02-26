"""
NetKeiba馬ページのHTMLを保存して確認
"""

import requests
import time

def main():
    horse_id = '2021105700'
    url = f'https://db.netkeiba.com/horse/{horse_id}/'

    print(f"Fetching: {url}")

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    try:
        time.sleep(1)
        r = session.get(url, timeout=10)
        r.raise_for_status()
        r.encoding = r.apparent_encoding

        output_file = f'horse_{horse_id}.html'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(r.text)

        print(f"\nHTMLを保存しました: {output_file}")
        print(f"ファイルサイズ: {len(r.text):,} 文字")

        # 血統関連キーワードを検索
        keywords = ['父', '母父', '血統', 'blood', 'pedigree']
        for keyword in keywords:
            count = r.text.count(keyword)
            if count > 0:
                print(f"  '{keyword}': {count}回出現")

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
