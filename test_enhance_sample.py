"""
拡張情報取得のサンプルテスト（50頭のみ）

修正版のロジックをテスト
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
    """馬の詳細ページから血統と過去成績を取得"""
    url = f"https://db.netkeiba.com/horse/{horse_id}/"

    driver = None
    try:
        driver = get_driver()
        driver.get(url)
        time.sleep(2)

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
            # Row 0: 父
            if len(rows) >= 1:
                father_cell = rows[0].find('td', class_='b_ml')
                if father_cell:
                    father_link = father_cell.find('a')
                    if father_link:
                        result['father'] = father_link.get_text(strip=True)

            # Row 2: 母父
            if len(rows) >= 3:
                mf_cell = rows[2].find('td', class_='b_ml')
                if mf_cell:
                    mf_link = mf_cell.find('a')
                    if mf_link:
                        result['mother_father'] = mf_link.get_text(strip=True)

        # 過去レース成績を取得
        race_table = soup.find('table', class_='db_h_race_results')
        if race_table:
            rows = race_table.find_all('tr')[1:]

            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 14:
                    continue

                try:
                    date_text = cols[0].get_text(strip=True)
                    rank_text = cols[11].get_text(strip=True)
                    rank = None
                    try:
                        rank = int(rank_text)
                    except:
                        pass

                    distance_text = cols[14].get_text(strip=True) if len(cols) > 14 else ''
                    is_turf = '芝' in distance_text
                    is_dirt = 'ダ' in distance_text

                    distance_match = re.search(r'(\d+)', distance_text)
                    distance = int(distance_match.group(1)) if distance_match else None

                    passage_text = cols[10].get_text(strip=True) if len(cols) > 10 else ''

                    result['past_races'].append({
                        'date': date_text,
                        'rank': rank,
                        'distance': distance,
                        'is_turf': is_turf,
                        'is_dirt': is_dirt,
                        'passage': passage_text
                    })

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
        print(f"\n    Error scraping horse {horse_id}: {e}")
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

    # 平均通過位置
    passages = []
    for race in horse_details['past_races']:
        passage = race.get('passage', '')
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

    # 脚質カテゴリ
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
    print(" サンプルテスト（50頭）")
    print("="*80)
    print()

    # CSVを読み込み
    print(f"CSVを読み込み中: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, low_memory=False)
    print(f"総レコード数: {len(df):,}")

    # father欠損のレコードを特定
    missing_features = df[df['father'].isna()]
    print(f"\nfather欠損レコード: {len(missing_features):,}件")

    # ユニークなhorse_idを取得（最初の50頭のみ）
    unique_horses = missing_features['horse_id'].dropna().unique()[:50]
    print(f"テスト対象: {len(unique_horses)}頭")

    # 馬ごとに詳細情報を取得
    print(f"\n拡張情報を取得中...")
    horse_data_cache = {}
    success_count = 0
    fail_count = 0

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
            success_count += 1
        else:
            fail_count += 1

        time.sleep(1.0)

        if i % 10 == 0:
            print(f"\r[{i}/{len(unique_horses)}] 完了 (成功: {success_count}, 失敗: {fail_count})", flush=True)

    print(f"\n\n処理完了")
    print(f"成功: {success_count}頭")
    print(f"失敗: {fail_count}頭")
    print(f"成功率: {success_count/len(unique_horses)*100:.1f}%")

    # DataFrameを更新（テストなので保存しない）
    print("\nDataFrame更新シミュレーション...")
    updated_count = 0
    updated_records = []

    for idx, row in df.iterrows():
        horse_id = row['horse_id']

        if pd.notna(horse_id) and horse_id in horse_data_cache:
            data = horse_data_cache[horse_id]
            will_update = False

            # 値が存在する場合のみ更新（Noneで上書きしない）
            if data.get('father') is not None:
                will_update = True
            if data.get('mother_father') is not None:
                will_update = True

            if will_update:
                updated_count += 1
                updated_records.append(idx)

    print(f"更新対象レコード数: {updated_count:,}件")
    print(f"\n✓ テスト成功！")
    print(f"\n推定: 全体12,176頭で成功率{success_count/len(unique_horses)*100:.1f}%なら")
    print(f"      約{int(12176 * success_count/len(unique_horses)):,}頭が成功")

if __name__ == "__main__":
    main()
