"""
収集したデータに拡張情報を追加するスクリプト

追加する情報：
1. 父・母父（血統情報）
2. 勝率（芝・ダート・総合）
3. 過去レース情報（前走着順、前走距離、前走からの日数）
4. 脚質カテゴリ
5. 平均通過位置
6. ラップタイムとペース分析
7. 調教評価

使い方：
    py enhance_collected_data.py
"""
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

CSV_PATH = 'data/main/netkeiba_data_2020_2025_complete.csv'

def get_driver():
    """Seleniumドライバーを初期化"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    return webdriver.Chrome(options=options)

def scrape_horse_details(horse_id):
    """
    馬の詳細ページから血統と過去成績を取得（Selenium使用）

    Returns:
        dict: {
            'father': 父名,
            'mother_father': 母父名,
            'past_races': [過去レースのリスト],
            'turf_results': {勝, 2着, 3着, 総数},
            'dirt_results': {勝, 2着, 3着, 総数}
        }
    """
    url = f"https://db.netkeiba.com/horse/{horse_id}/"

    driver = None
    try:
        # Seleniumでページ取得
        driver = get_driver()
        driver.get(url)
        time.sleep(2)

        # BeautifulSoupで解析
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        result = {
            'father': None,
            'mother_father': None,
            'past_races': [],
            'turf_results': {'win': 0, 'place': 0, 'show': 0, 'total': 0},
            'dirt_results': {'win': 0, 'place': 0, 'show': 0, 'total': 0}
        }

        # 血統情報を取得
        pedigree_table = soup.find('table', class_='blood_table')
        if pedigree_table:
            rows = pedigree_table.find_all('tr')
            # Row 0: 父（class='b_ml'のtd）
            if len(rows) >= 1:
                father_cell = rows[0].find('td', class_='b_ml')
                if father_cell:
                    father_link = father_cell.find('a')
                    if father_link:
                        result['father'] = father_link.get_text(strip=True)

            # Row 2: 母父（class='b_ml'のtd）
            if len(rows) >= 3:
                mf_cell = rows[2].find('td', class_='b_ml')
                if mf_cell:
                    mf_link = mf_cell.find('a')
                    if mf_link:
                        result['mother_father'] = mf_link.get_text(strip=True)

        # 過去レース成績を取得
        race_table = soup.find('table', class_='db_h_race_results')
        if race_table:
            rows = race_table.find_all('tr')[1:]  # ヘッダー除く

            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 14:
                    continue

                try:
                    # 日付
                    date_text = cols[0].get_text(strip=True)

                    # 着順
                    rank_text = cols[11].get_text(strip=True)
                    rank = None
                    try:
                        rank = int(rank_text)
                    except:
                        pass

                    # コースタイプ
                    distance_text = cols[14].get_text(strip=True) if len(cols) > 14 else ''
                    is_turf = '芝' in distance_text
                    is_dirt = 'ダ' in distance_text

                    # 距離
                    distance_match = re.search(r'(\d+)', distance_text)
                    distance = int(distance_match.group(1)) if distance_match else None

                    # 通過順位
                    passage_text = cols[10].get_text(strip=True) if len(cols) > 10 else ''

                    # race_id
                    race_link = cols[4].find('a')
                    race_id = None
                    if race_link:
                        race_url = race_link.get('href', '')
                        race_id_match = re.search(r'race_id=(\d+)', race_url)
                        if race_id_match:
                            race_id = race_id_match.group(1)

                    result['past_races'].append({
                        'date': date_text,
                        'rank': rank,
                        'distance': distance,
                        'is_turf': is_turf,
                        'is_dirt': is_dirt,
                        'passage': passage_text,
                        'race_id': race_id
                    })

                    # 勝率計算用
                    if rank:
                        if is_turf:
                            result['turf_results']['total'] += 1
                            if rank == 1:
                                result['turf_results']['win'] += 1
                            elif rank == 2:
                                result['turf_results']['place'] += 1
                            elif rank == 3:
                                result['turf_results']['show'] += 1
                        elif is_dirt:
                            result['dirt_results']['total'] += 1
                            if rank == 1:
                                result['dirt_results']['win'] += 1
                            elif rank == 2:
                                result['dirt_results']['place'] += 1
                            elif rank == 3:
                                result['dirt_results']['show'] += 1

                except:
                    continue

        return result

    except Exception as e:
        print(f"    Error scraping horse {horse_id}: {e}")
        return None
    finally:
        if driver:
            driver.quit()

def calculate_horse_statistics(horse_details):
    """馬の統計情報を計算"""
    if not horse_details:
        return {}

    stats = {}

    # 芝勝率
    turf = horse_details['turf_results']
    if turf['total'] > 0:
        stats['turf_win_rate'] = turf['win'] / turf['total']
        stats['turf_place_rate'] = (turf['win'] + turf['place'] + turf['show']) / turf['total']
    else:
        stats['turf_win_rate'] = 0.0
        stats['turf_place_rate'] = 0.0

    # ダート勝率
    dirt = horse_details['dirt_results']
    if dirt['total'] > 0:
        stats['dirt_win_rate'] = dirt['win'] / dirt['total']
        stats['dirt_place_rate'] = (dirt['win'] + dirt['place'] + dirt['show']) / dirt['total']
    else:
        stats['dirt_win_rate'] = 0.0
        stats['dirt_place_rate'] = 0.0

    # 総合勝率
    total_starts = turf['total'] + dirt['total']
    total_wins = turf['win'] + dirt['win']
    if total_starts > 0:
        stats['total_win_rate'] = total_wins / total_starts
        stats['total_starts'] = total_starts
    else:
        stats['total_win_rate'] = 0.0
        stats['total_starts'] = 0

    # 平均通過位置（通過順位の平均）
    passages = []
    for race in horse_details['past_races']:
        passage = race.get('passage', '')
        # "1-1-1-1" のような形式から最初の数字を取得
        if passage:
            parts = passage.split('-')
            if parts and parts[0]:
                try:
                    passages.append(int(parts[0]))
                except:
                    pass

    if passages:
        stats['avg_passage_position'] = np.mean(passages)
    else:
        stats['avg_passage_position'] = None

    # 脚質カテゴリ（平均通過位置から推定）
    if stats['avg_passage_position']:
        if stats['avg_passage_position'] <= 3:
            stats['running_style_category'] = 'front_runner'
        elif stats['avg_passage_position'] <= 6:
            stats['running_style_category'] = 'stalker'
        elif stats['avg_passage_position'] <= 10:
            stats['running_style_category'] = 'midpack'
        else:
            stats['running_style_category'] = 'closer'
    else:
        stats['running_style_category'] = 'unknown'

    return stats

def enhance_dataframe(df):
    """
    DataFrameに拡張情報を追加
    """
    print("\n拡張情報の追加を開始します...")
    print(f"対象レコード数: {len(df):,}")

    # 2026年の新規データのみを対象
    df_2026 = df[df['race_id'].astype(str).str.startswith('2026')].copy()
    print(f"2026年データ: {len(df_2026):,}件")

    if len(df_2026) == 0:
        print("2026年のデータがありません")
        return df

    # ユニークなhorse_idを取得
    unique_horses = df_2026['horse_id'].dropna().unique()
    print(f"ユニークな馬: {len(unique_horses):,}頭")

    # 馬ごとに詳細情報を取得
    horse_data_cache = {}

    for i, horse_id in enumerate(unique_horses, 1):
        horse_id_str = str(int(horse_id))
        print(f"\r[{i}/{len(unique_horses)}] 馬ID: {horse_id_str} を処理中...", end='', flush=True)

        details = scrape_horse_details(horse_id_str)
        if details:
            stats = calculate_horse_statistics(details)
            horse_data_cache[horse_id] = {
                'father': details['father'],
                'mother_father': details['mother_father'],
                **stats
            }

        time.sleep(1.0)  # レート制限対策

        # 10頭ごとに改行
        if i % 10 == 0:
            print(f"\r[{i}/{len(unique_horses)}] 完了", flush=True)

    print(f"\n\n馬の詳細情報取得完了: {len(horse_data_cache)}頭")

    # DataFrameに情報を追加
    print("\nDataFrameに情報をマージ中...")

    new_columns = {
        'father': [],
        'mother_father': [],
        'total_starts': [],
        'total_win_rate': [],
        'turf_win_rate': [],
        'dirt_win_rate': [],
        'avg_passage_position': [],
        'running_style_category': []
    }

    for idx, row in df.iterrows():
        horse_id = row['horse_id']

        if pd.notna(horse_id) and horse_id in horse_data_cache:
            data = horse_data_cache[horse_id]
            new_columns['father'].append(data.get('father'))
            new_columns['mother_father'].append(data.get('mother_father'))
            new_columns['total_starts'].append(data.get('total_starts'))
            new_columns['total_win_rate'].append(data.get('total_win_rate'))
            new_columns['turf_win_rate'].append(data.get('turf_win_rate'))
            new_columns['dirt_win_rate'].append(data.get('dirt_win_rate'))
            new_columns['avg_passage_position'].append(data.get('avg_passage_position'))
            new_columns['running_style_category'].append(data.get('running_style_category'))
        else:
            # データがない場合は既存の値を保持
            new_columns['father'].append(row.get('father'))
            new_columns['mother_father'].append(row.get('mother_father'))
            new_columns['total_starts'].append(row.get('total_starts'))
            new_columns['total_win_rate'].append(row.get('total_win_rate'))
            new_columns['turf_win_rate'].append(row.get('turf_win_rate'))
            new_columns['dirt_win_rate'].append(row.get('dirt_win_rate'))
            new_columns['avg_passage_position'].append(row.get('avg_passage_position'))
            new_columns['running_style_category'].append(row.get('running_style_category'))

    # 新しいカラムを追加または更新
    for col, values in new_columns.items():
        df[col] = values

    print("完了！")

    return df

def main():
    print("="*80)
    print(" データ拡張スクリプト")
    print("="*80)
    print()

    # CSVを読み込み
    print(f"CSVを読み込み中: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, low_memory=False)
    print(f"総レコード数: {len(df):,}")

    # 拡張処理
    df_enhanced = enhance_dataframe(df)

    # 保存
    print(f"\n保存中: {CSV_PATH}")
    df_enhanced.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')

    print("\n✓ 完了！")

if __name__ == "__main__":
    main()
