"""
拡張情報欠損の全レコードを修正するスクリプト

father/mother_father等が欠損している全ての馬の情報を取得
"""
import pandas as pd
import numpy as np
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime

CSV_PATH = 'data/main/netkeiba_data_2020_2025_complete.csv'

def get_driver():
    """Seleniumドライバーを初期化（画像・CSS無効化でリクエスト削減）"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--log-level=3')
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])

    # 画像・CSS等の不要なリソースを無効化（JavaScriptは有効のまま）
    prefs = {
        'profile.default_content_setting_values': {
            'images': 2,        # 画像を読み込まない
            'plugins': 2,       # プラグイン無効
            'popups': 2,        # ポップアップ無効
            'geolocation': 2,   # 位置情報無効
            'notifications': 2, # 通知無効
            'media_stream': 2,  # メディア無効
        },
        'profile.managed_default_content_settings': {
            'images': 2
        }
    }
    options.add_experimental_option('prefs', prefs)
    options.add_argument('--blink-settings=imagesEnabled=false')

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

                    result['past_races'].append({
                        'date': date_text,
                        'rank': rank,
                        'distance': distance,
                        'is_turf': is_turf,
                        'is_dirt': is_dirt,
                        'passage': passage_text
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

def main():
    print("="*80)
    print(" 拡張情報欠損の全修正")
    print("="*80)
    print()

    # CSVを読み込み
    print(f"CSVを読み込み中: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, low_memory=False)
    print(f"総レコード数: {len(df):,}")

    # father欠損のレコードを特定
    missing_features = df[df['father'].isna()]
    print(f"\nfather欠損レコード: {len(missing_features):,}件")

    if len(missing_features) == 0:
        print("修正の必要なレコードはありません")
        return

    # ユニークなhorse_idを取得
    unique_horses = missing_features['horse_id'].dropna().unique()
    print(f"ユニークな馬: {len(unique_horses):,}頭")
    print(f"\n推定所要時間: 約{len(unique_horses) * 2 / 3600:.1f}時間")

    # 馬ごとに詳細情報を取得
    print(f"\n拡張情報を取得中...")
    horse_data_cache = {}

    for i, horse_id in enumerate(unique_horses, 1):
        horse_id_str = str(int(horse_id))
        print(f"\r[{i}/{len(unique_horses)}] 馬ID: {horse_id_str} を処理中...", end='', flush=True)

        details = scrape_horse_details(horse_id_str)
        # 血統データが実際に取得できた場合のみキャッシュに追加
        if details and (details.get('father') or details.get('mother_father')):
            stats = calculate_horse_statistics(details)
            horse_data_cache[horse_id] = {
                'father': details['father'],
                'mother_father': details['mother_father'],
                **stats
            }

        time.sleep(3.0)  # レート制限対策（安全優先）

        # 10頭ごとに改行
        if i % 10 == 0:
            success_count = len(horse_data_cache)
            print(f"\r[{i}/{len(unique_horses)}] 完了 ({success_count}頭成功)", flush=True)

    print(f"\n\n馬の詳細情報取得完了: {len(horse_data_cache)}頭")

    # DataFrameを更新
    print("\nDataFrameを更新中...")
    updated_count = 0

    for idx, row in df.iterrows():
        horse_id = row['horse_id']

        if pd.notna(horse_id) and horse_id in horse_data_cache:
            data = horse_data_cache[horse_id]
            # 値が存在する場合のみ更新（Noneで上書きしない）
            if data.get('father') is not None:
                df.at[idx, 'father'] = data.get('father')
            if data.get('mother_father') is not None:
                df.at[idx, 'mother_father'] = data.get('mother_father')
            if data.get('total_starts') is not None:
                df.at[idx, 'total_starts'] = data.get('total_starts')
            if data.get('total_win_rate') is not None:
                df.at[idx, 'total_win_rate'] = data.get('total_win_rate')
            if data.get('turf_win_rate') is not None:
                df.at[idx, 'turf_win_rate'] = data.get('turf_win_rate')
            if data.get('dirt_win_rate') is not None:
                df.at[idx, 'dirt_win_rate'] = data.get('dirt_win_rate')
            if data.get('avg_passage_position') is not None:
                df.at[idx, 'avg_passage_position'] = data.get('avg_passage_position')
            if data.get('running_style_category') is not None:
                df.at[idx, 'running_style_category'] = data.get('running_style_category')
            updated_count += 1

    print(f"更新レコード数: {updated_count:,}件")

    # バックアップを作成
    backup_path = CSV_PATH.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    print(f"\nバックアップを作成中: {backup_path}")
    import shutil
    shutil.copy(CSV_PATH, backup_path)

    # 保存
    print(f"\n保存中: {CSV_PATH}")
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')

    # 結果確認
    remaining_missing = df['father'].isna().sum()
    print(f"\n修正後のfather欠損: {remaining_missing:,}件")

    if remaining_missing == 0:
        print("\n完了！全ての拡張情報を取得しました")
    else:
        print(f"\n{remaining_missing:,}件の情報が取得できませんでした")

    print("\n処理完了")

if __name__ == "__main__":
    main()
