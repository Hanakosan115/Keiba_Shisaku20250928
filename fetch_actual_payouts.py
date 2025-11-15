"""
実際の配当データを取得してバックテストの精度を向上させるスクリプト
"""
import pandas as pd
import numpy as np
import time
import requests
from bs4 import BeautifulSoup
import json
import os
import pickle
from improved_analyzer import ImprovedHorseAnalyzer

# 設定
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
SLEEP_TIME = 1.0  # リクエスト間隔（秒）

def get_payout_data(race_id):
    """
    指定したrace_idの配当データを取得

    Returns:
        dict: {'単勝': {...}, '複勝': {...}, '馬連': {...}, ...}
    """
    url = f'https://race.netkeiba.com/race/result.html?race_id={race_id}'
    headers = {'User-Agent': USER_AGENT}

    try:
        time.sleep(SLEEP_TIME)
        r = requests.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        r.encoding = r.apparent_encoding
        soup = BeautifulSoup(r.content, 'lxml')

        payout_data = {'race_id': race_id}

        # 配当テーブルを取得
        payout_tables = soup.select('.Result_Pay_Back .Payout_Detail_Table')

        if not payout_tables:
            # 代替セレクタを試す
            payout_tables = soup.select('.payout_block table')
            if not payout_tables:
                payout_tables = soup.select('table.pay_table_01')

        if not payout_tables:
            print(f"  [警告] 配当データなし: {race_id}")
            return None

        current_type = None

        for table_tag in payout_tables:
            for tr_tag in table_tag.select('tr'):
                # thとtdを分けて取得
                th_tags = tr_tag.select('th')
                td_tags = tr_tag.select('td')

                # 券種ヘッダー行の判定（thが存在する場合）
                if th_tags:
                    header_text = th_tags[0].get_text(strip=True)
                    if '単勝' in header_text:
                        current_type = '単勝'
                    elif '複勝' in header_text:
                        current_type = '複勝'
                        # 複勝は同じ行にデータがある場合がある
                        if len(td_tags) >= 2:
                            # すぐにデータ処理へ
                            pass
                    elif '馬連' in header_text:
                        current_type = '馬連'
                    elif 'ワイド' in header_text:
                        current_type = 'ワイド'
                    elif '馬単' in header_text:
                        current_type = '馬単'
                    elif '三連複' in header_text or '3連複' in header_text:
                        current_type = '3連複'
                    elif '三連単' in header_text or '3連単' in header_text:
                        current_type = '3連単'
                    elif '枠連' in header_text:
                        current_type = '枠連'

                # データ行の処理（tdが2つ以上ある場合）
                if current_type and len(td_tags) >= 2:
                    # 複勝は特殊処理（3つのTD: 馬番, 配当, 人気）
                    if current_type == '複勝' and len(td_tags) >= 2:
                        numbers_td = td_tags[0]
                        payout_td = td_tags[1]  # 2番目のTDが配当

                        # 複勝は<div><span>構造なので、各<div><span>から馬番を抽出
                        div_tags = numbers_td.find_all('div')
                        numbers_list = []
                        for div in div_tags:
                            span = div.find('span')
                            if span:
                                num_text = span.get_text(strip=True)
                                if num_text:
                                    numbers_list.append(num_text)

                        # 配当は単一の<span>内に<br/>で区切られたテキスト
                        # HTMLを文字列に変換して<br/>で分割
                        payout_html = str(payout_td)
                        # <br>, <br/>, <br />などすべてのパターンを改行に置換
                        import re
                        payout_html = re.sub(r'<br\s*/?>', '\n', payout_html)
                        # BeautifulSoupで再パース
                        from bs4 import BeautifulSoup as BS
                        temp_soup = BS(payout_html, 'lxml')
                        payout_text = temp_soup.get_text(strip=True)
                        payout_list = [p.strip() for p in payout_text.split('\n') if p.strip()]

                        # 複勝データを登録
                        if len(numbers_list) == len(payout_list) and len(numbers_list) > 0:
                            if current_type not in payout_data:
                                payout_data[current_type] = []

                            for num_str, pay_str in zip(numbers_list, payout_list):
                                pay_str = pay_str.replace(',', '').replace('円', '').strip()
                                if num_str and pay_str and pay_str.isdigit():
                                    payout_data[current_type].append({
                                        '馬番': num_str,
                                        '払戻': int(pay_str)
                                    })
                    else:
                        # 複勝以外の通常処理
                        numbers_td = td_tags[0]
                        payout_td = td_tags[1]

                        # HTML要素をコピーして改行変換
                        import copy
                        numbers_td_copy = copy.copy(numbers_td)
                        payout_td_copy = copy.copy(payout_td)

                        # br タグで区切られている場合を考慮
                        for br in numbers_td_copy.find_all('br'):
                            br.replace_with('\n')
                        for br in payout_td_copy.find_all('br'):
                            br.replace_with('\n')

                        # separator引数でハイフンを保持
                        numbers_text = numbers_td_copy.get_text(separator=' ', strip=True)
                        payout_text = payout_td_copy.get_text(separator=' ', strip=True)

                        # ハイフンの前後のスペースを除去して正規化
                        numbers_text = numbers_text.replace(' - ', '-').replace('- ', '-').replace(' -', '-')

                        numbers_list = [n.strip() for n in numbers_text.split('\n') if n.strip()]
                        payout_list = [p.strip() for p in payout_text.split('\n') if p.strip()]

                        # リストが同じ長さの場合のみ処理
                        if len(numbers_list) == len(payout_list):
                            if current_type not in payout_data:
                                payout_data[current_type] = []

                            for num_str, pay_str in zip(numbers_list, payout_list):
                                num_str = num_str.strip()
                                # スペースをハイフンに変換（馬連・3連複などのため）
                                num_str = num_str.replace(' ', '-')
                                pay_str = pay_str.replace(',', '').replace('円', '').strip()

                                if num_str and pay_str and pay_str.isdigit():
                                    payout_data[current_type].append({
                                        '馬番': num_str,
                                        '払戻': int(pay_str)
                                    })
                        else:
                            # 長さが違う場合は単一データとして処理
                            numbers_str = numbers_td_copy.get_text(separator=' ', strip=True).replace(' ', '-')
                            payout_str = payout_td_copy.get_text(strip=True).replace(',', '').replace('円', '').strip()

                            if numbers_str and payout_str and payout_str.isdigit():
                                if current_type not in payout_data:
                                    payout_data[current_type] = []

                                payout_data[current_type].append({
                                    '馬番': numbers_str,
                                    '払戻': int(payout_str)
                                })

        return payout_data if len(payout_data) > 1 else None

    except Exception as e:
        print(f"  [エラー] {race_id}: {e}")
        return None


def load_payout_cache(cache_file='payout_cache.pkl'):
    """配当キャッシュを読み込む"""
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return {}


def save_payout_cache(cache, cache_file='payout_cache.pkl'):
    """配当キャッシュを保存"""
    with open(cache_file, 'wb') as f:
        pickle.dump(cache, f)


def fetch_payouts_for_races(race_ids, max_races=50):
    """
    指定したrace_idリストの配当データを取得

    Args:
        race_ids: レースIDのリスト
        max_races: 最大取得件数

    Returns:
        dict: {race_id: payout_data, ...}
    """
    cache_file = r'C:\Users\bu158\Keiba_Shisaku20250928\payout_cache.pkl'
    payout_cache = load_payout_cache(cache_file)

    print(f"\n配当データ取得開始（最大{max_races}レース）")
    print(f"キャッシュ済み: {len(payout_cache)}レース")

    new_fetched = 0

    for idx, race_id in enumerate(race_ids[:max_races]):
        # キャッシュチェック
        if race_id in payout_cache:
            continue

        print(f"[{idx+1}/{min(max_races, len(race_ids))}] {race_id} 取得中...")
        payout_data = get_payout_data(race_id)

        if payout_data:
            payout_cache[race_id] = payout_data
            new_fetched += 1

            # 10件ごとにキャッシュ保存
            if new_fetched % 10 == 0:
                save_payout_cache(payout_cache, cache_file)
                print(f"  → キャッシュ保存（計{len(payout_cache)}件）")

    # 最終保存
    save_payout_cache(payout_cache, cache_file)
    print(f"\n配当取得完了: 新規{new_fetched}件、総計{len(payout_cache)}件")

    return payout_cache


def main():
    """メイン処理"""
    print("=" * 60)
    print("実際の配当データ取得スクリプト")
    print("=" * 60)

    # CSVからrace_idリストを取得
    data_dir = r"C:\Users\bu158\HorseRacingAnalyzer\data"
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and 'combined' in f]

    if not csv_files:
        print("エラー: CSVファイルが見つかりません")
        return

    csv_path = os.path.join(data_dir, csv_files[0])
    print(f"\nCSV読み込み: {csv_files[0]}")

    df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
    race_ids = df['race_id'].unique()

    print(f"総レース数: {len(race_ids)}")

    # 配当データを取得（500レース）
    payout_cache = fetch_payouts_for_races(race_ids, max_races=500)

    # サンプル表示
    if payout_cache:
        sample_race_id = list(payout_cache.keys())[0]
        sample_data = payout_cache[sample_race_id]

        print(f"\n[サンプル] レースID: {sample_race_id}")
        for bet_type, data in sample_data.items():
            if bet_type != 'race_id':
                print(f"  {bet_type}: {data}")

    print("\n完了！payout_cache.pklに保存されました。")


if __name__ == "__main__":
    main()
