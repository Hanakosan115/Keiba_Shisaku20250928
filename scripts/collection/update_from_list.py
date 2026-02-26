"""
レースIDリストから一括更新（horse_racing_analyzer.pyのロジック統合版）

使い方:
1. race_ids.txt にレースIDを1行ずつ書く
2. このスクリプトを実行
3. 自動でスクレイピング→DB追加

race_ids.txt の例:
202405011201
202405011202
202405011203
...
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import re
import traceback
import random
from datetime import datetime
import shutil

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import TimeoutException, WebDriverException
    from selenium.webdriver.chrome.service import Service as ChromeService
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("警告: Seleniumがインストールされていません。カレンダー機能が制限されます。")
    print("インストール方法: pip install selenium")

class ListBasedUpdater:
    """レースIDリストベース更新（詳細情報取得版）"""

    def __init__(self, db_path='netkeiba_data_2020_2024_enhanced.csv',
                 log_path=r'C:\Users\bu158\HorseRacingAnalyzer\data\processed_race_ids.log',
                 past_results_path='horse_past_results.csv',
                 chrome_driver_path=None):
        self.db_path = db_path
        self.log_path = log_path
        self.past_results_path = past_results_path
        self.chrome_driver_path = chrome_driver_path

        # User-Agentリスト（ランダム選択でブロック回避）
        self.USER_AGENTS = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
        ]

        self.REQUEST_TIMEOUT = 10
        self.SELENIUM_WAIT_TIMEOUT = 30
        self.session = requests.Session()
        self._update_user_agent()  # 初回User-Agent設定

        # JRA競馬場リスト（地方判定用）
        self.JRA_TRACKS = ['札幌', '函館', '福島', '新潟', '東京', '中山', '中京', '京都', '阪神', '小倉']

        # レート制限設定（高速化版）
        self.DELAY_RACE_MIN = 0.5        # レース結果取得の最小遅延（秒）
        self.DELAY_RACE_MAX = 1.5        # レース結果取得の最大遅延（秒）
        self.DELAY_HORSE_MIN = 0.5       # 馬情報取得の最小遅延（秒）
        self.DELAY_HORSE_MAX = 1.5       # 馬情報取得の最大遅延（秒）
        self.DELAY_PEDIGREE_MIN = 0.3    # 血統情報取得の最小遅延（秒）
        self.DELAY_PEDIGREE_MAX = 1.0    # 血統情報取得の最大遅延（秒）
        self.BATCH_SIZE = 10             # 何頭ごとに長時間休憩するか
        self.BATCH_COOLDOWN_MIN = 10     # バッチ休憩の最小時間（秒）
        self.BATCH_COOLDOWN_MAX = 20     # バッチ休憩の最大時間（秒）
        self.RACE_COOLDOWN_MIN = 1       # レース間の最小休憩（秒）
        self.RACE_COOLDOWN_MAX = 3       # レース間の最大休憩（秒）
        self.MAX_RETRIES = 3             # リトライ最大回数
        self.RETRY_BACKOFF_BASE = 2      # リトライ時の待機時間ベース（秒）

        # 進捗追跡用
        self.progress_file = 'collection_progress.json'
        self.horses_processed_count = 0  # 処理した馬の数

    def _update_user_agent(self):
        """User-Agentをランダムに変更"""
        user_agent = random.choice(self.USER_AGENTS)
        self.session.headers.update({'User-Agent': user_agent})

    def _random_delay(self, min_delay, max_delay, description=""):
        """
        ランダムな遅延を入れる（サーバー負荷対策）

        Args:
            min_delay: 最小遅延時間（秒）
            max_delay: 最大遅延時間（秒）
            description: 遅延の説明（ログ用）
        """
        delay = random.uniform(min_delay, max_delay)
        if description:
            print(f"      [{description}] {delay:.1f}秒待機中...", end='', flush=True)
        time.sleep(delay)
        if description:
            print(" 完了")

    def _batch_cooldown(self):
        """
        バッチ処理のクールダウン（10頭ごとに長時間休憩）
        """
        if self.horses_processed_count > 0 and self.horses_processed_count % self.BATCH_SIZE == 0:
            cooldown = random.uniform(self.BATCH_COOLDOWN_MIN, self.BATCH_COOLDOWN_MAX)
            print(f"\n      === バッチクールダウン ({self.horses_processed_count}頭処理済み): {cooldown:.0f}秒休憩 ===")
            time.sleep(cooldown)
            self._update_user_agent()  # 休憩後にUser-Agentも変更

    def _race_cooldown(self):
        """
        レース間のクールダウン
        """
        cooldown = random.uniform(self.RACE_COOLDOWN_MIN, self.RACE_COOLDOWN_MAX)
        print(f"      [レース間休憩] {cooldown:.1f}秒")
        time.sleep(cooldown)

    def _save_progress(self, processed_race_ids):
        """
        進捗を保存（中断・再開用）

        Args:
            processed_race_ids: 処理済みレースIDのリスト
        """
        import json
        progress_data = {
            'processed_race_ids': processed_race_ids,
            'horses_processed_count': self.horses_processed_count,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"      警告: 進捗保存エラー: {e}")

    def _load_progress(self):
        """
        進捗を読み込み（再開用）

        Returns:
            set: 処理済みレースIDのセット
        """
        import json
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress_data = json.load(f)
                    processed = set(progress_data.get('processed_race_ids', []))
                    self.horses_processed_count = progress_data.get('horses_processed_count', 0)
                    timestamp = progress_data.get('timestamp', '不明')
                    print(f"進捗ファイル検出: {len(processed)}件処理済み（最終更新: {timestamp}）")
                    return processed
            except Exception as e:
                print(f"警告: 進捗読み込みエラー: {e}")
        return set()

    def _retry_request(self, url, description="", retry_count=0):
        """
        リトライロジック付きHTTPリクエスト

        Args:
            url: リクエストURL
            description: リクエストの説明
            retry_count: 現在のリトライ回数

        Returns:
            requests.Response or None
        """
        try:
            r = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            r.raise_for_status()
            return r
        except requests.exceptions.RequestException as e:
            if retry_count < self.MAX_RETRIES:
                wait_time = self.RETRY_BACKOFF_BASE ** (retry_count + 1)
                print(f"\n      リトライ {retry_count + 1}/{self.MAX_RETRIES}: {wait_time}秒後に再試行 ({description})")
                time.sleep(wait_time)
                self._update_user_agent()  # User-Agentを変更してリトライ
                return self._retry_request(url, description, retry_count + 1)
            else:
                print(f"\n      エラー: 最大リトライ回数超過 ({description}): {e}")
                return None

    def get_result_table(self, race_id):
        """
        レース結果ページからレース情報辞書と結果テーブルリストを取得
        horse_racing_analyzer.pyのロジックを統合
        """
        url = f'https://db.netkeiba.com/race/{race_id}/'
        race_info_dict = {'race_id': race_id}
        result_table = []

        try:
            # ランダム遅延（レート制限対策）
            self._random_delay(self.DELAY_RACE_MIN, self.DELAY_RACE_MAX)

            # リトライロジック付きリクエスト
            r = self._retry_request(url, f"レース{race_id}")
            if r is None:
                return race_info_dict, []

            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.content, 'lxml')

            # === レース情報の抽出 ===
            try:
                data_intro_div = soup.select_one('div.data_intro')
                if data_intro_div:
                    # レース番号
                    race_num_dt = data_intro_div.select_one('dl.racedata dt')
                    if race_num_dt:
                        race_num_match = re.search(r'(\d+)', race_num_dt.get_text(strip=True))
                        if race_num_match:
                            race_info_dict['race_num'] = int(race_num_match.group(1))

                    # レース名
                    race_name_h1 = data_intro_div.select_one('h1')
                    if race_name_h1:
                        race_info_dict['race_name'] = race_name_h1.get_text(strip=True)

                    # コース情報
                    details_span = data_intro_div.select_one('p span')
                    if details_span:
                        details_text = details_span.get_text(strip=True)
                        parts = [p.strip() for p in details_text.split('/')]

                        if len(parts) >= 1:
                            course_text = parts[0]
                            course_type_match = re.search(r'([芝ダ障])', course_text)
                            turn_match = re.search(r'([左右内外])', course_text)
                            distance_match = re.search(r'(\d+)m', course_text)

                            race_info_dict['course_type'] = course_type_match.group(1) if course_type_match else None
                            if turn_match:
                                race_info_dict['turn_detail'] = turn_match.group(1)
                                race_info_dict['turn'] = turn_match.group(1) if turn_match.group(1) in ['右', '左'] else None
                            race_info_dict['distance'] = int(distance_match.group(1)) if distance_match else None

                        if len(parts) >= 2 and ':' in parts[1]:
                            race_info_dict['weather'] = parts[1].split(':', 1)[1].strip()
                        if len(parts) >= 3 and ':' in parts[2]:
                            race_info_dict['track_condition'] = parts[2].split(':', 1)[1].strip()
                        if len(parts) >= 4 and ':' in parts[3]:
                            race_info_dict['start_time'] = parts[3].split(':', 1)[1].strip()

                # 日付・競馬場
                small_text_p = soup.select_one('p.smalltxt')
                if small_text_p:
                    small_text = small_text_p.get_text(strip=True)
                    date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', small_text)
                    if date_match:
                        race_info_dict['date'] = date_match.group(1)
                    place_match = re.search(r'\d回(\S+?)\d日目', small_text)
                    if place_match:
                        race_info_dict['track_name'] = place_match.group(1)

            except Exception as e_info:
                print(f"      警告: レース情報の抽出中にエラー: {e_info}")

            # === 結果テーブルの取得 ===
            table_tag = soup.select_one('table.race_table_01.nk_tb_common')
            if not table_tag:
                return race_info_dict, []

            all_rows = table_tag.find_all('tr', recursive=False)
            if not all_rows:
                return race_info_dict, []

            # ヘッダー行
            header_row_tag = all_rows[0]
            header_th_tags = header_row_tag.find_all('th', recursive=False)
            if header_th_tags:
                header_cells = [th.get_text(strip=True).replace('<br>', '') for th in header_th_tags]
            else:
                header_td_tags = header_row_tag.find_all('td', recursive=False)
                if header_td_tags:
                    header_cells = [td.get_text(strip=True).replace('<br>', '') for td in header_td_tags]
                else:
                    return race_info_dict, []

            if not header_cells:
                return race_info_dict, []

            # 馬名列のインデックス検索
            horse_name_index = -1
            try:
                horse_name_index = next(i for i, h in enumerate(header_cells) if '馬名' in h)
            except StopIteration:
                pass

            # ヘッダーにURL列追加
            header_with_url = list(header_cells)
            if horse_name_index != -1:
                header_with_url.insert(horse_name_index + 1, 'HorseName_url')
            result_table.append(header_with_url)

            # データ行
            data_tr_tags = all_rows[1:]
            for tr_tag in data_tr_tags:
                td_tags = tr_tag.find_all('td', recursive=False)

                if len(td_tags) != len(header_cells):
                    continue

                row_data = []
                for i, td_tag in enumerate(td_tags):
                    cell_span = td_tag.find('span')
                    cell_text = cell_span.get_text(strip=True) if cell_span else td_tag.get_text(strip=True)
                    row_data.append(cell_text)

                    if i == horse_name_index:
                        a_tag = td_tag.find('a')
                        href = a_tag['href'].strip() if a_tag and a_tag.has_attr('href') else None
                        row_data.append(href)

                if len(row_data) == len(header_with_url):
                    result_table.append(row_data)

            return race_info_dict, result_table

        except requests.exceptions.Timeout:
            print(f"      タイムアウトエラー: {url}")
            return race_info_dict, []
        except requests.exceptions.RequestException as e:
            print(f"      ページ取得エラー ({url}): {e}")
            return race_info_dict, []
        except Exception as e:
            print(f"      予期せぬエラー (get_result_table): {e}")
            traceback.print_exc()
            return race_info_dict, []

    def scrape_race_result(self, race_id, collect_horse_details=True):
        """
        レース結果スクレイピング（詳細版 + 馬統計情報）

        Args:
            race_id: レースID
            collect_horse_details: 馬の詳細情報・統計値を取得するか（デフォルト: True）

        Returns:
            DataFrame: レース結果 + 馬統計情報
        """
        race_info, result_table = self.get_result_table(race_id)

        if not result_table or len(result_table) <= 1:
            return None

        try:
            # テーブルをDataFrameに変換
            df = pd.DataFrame(result_table[1:], columns=result_table[0])

            # レース情報を各行に追加
            for key, value in race_info.items():
                if key not in df.columns:
                    df[key] = value

            # horse_idの抽出
            if 'HorseName_url' in df.columns:
                df['horse_id'] = df['HorseName_url'].apply(
                    lambda x: x.strip('/').split('/')[-1] if x and '/' in str(x) else None
                )

                # 血統情報と馬の統計値を取得
                if collect_horse_details:
                    # 統計値列の初期化
                    stat_columns = [
                        'father', 'mother_father',
                        'total_starts', 'total_win_rate',
                        'turf_win_rate', 'dirt_win_rate',
                        'distance_similar_win_rate',
                        'grade_race_starts', 'is_local_transfer',
                        'avg_passage_position', 'running_style_category',
                        'prev_race_rank', 'prev_race_distance',
                        'days_since_last_race',
                        'heavy_track_win_rate', 'avg_last_3f',
                        'total_earnings'
                    ]
                    for col in stat_columns:
                        df[col] = None

                    # 過去戦績を保存するリスト
                    all_past_results = []

                    # 今回のレース距離とコース種別
                    current_distance = race_info.get('distance')
                    current_course_type = race_info.get('course_type')

                    print(f"      馬の詳細情報を取得中...")
                    for idx, row in df.iterrows():
                        horse_id = row.get('horse_id')
                        if horse_id and str(horse_id).isdigit():
                            # バッチクールダウン（10頭ごとに休憩）
                            self._batch_cooldown()

                            # 血統情報取得
                            pedigree = self._get_pedigree_info(horse_id)
                            df.at[idx, 'father'] = pedigree.get('father')
                            df.at[idx, 'mother_father'] = pedigree.get('mother_father')

                            # 馬の詳細情報と過去戦績取得
                            horse_details = self.get_horse_details(horse_id)

                            # 処理済み馬カウント
                            self.horses_processed_count += 1

                            if 'error' not in horse_details:
                                # 過去戦績を保存
                                race_results = horse_details.get('race_results', [])
                                all_past_results.extend(race_results)

                                # 統計値計算
                                stats = self.calculate_horse_stats(
                                    race_results,
                                    current_race_distance=current_distance,
                                    current_course_type=current_course_type
                                )

                                # 獲得賞金を追加
                                stats['total_earnings'] = horse_details.get('total_earnings', 0)

                                # 統計値をDataFrameに追加
                                for key, value in stats.items():
                                    if key in df.columns:
                                        df.at[idx, key] = value

                    # 過去戦績をCSVに保存（レース単位で保存）
                    if all_past_results:
                        self._save_past_results(all_past_results)

            return df

        except Exception as e:
            print(f"    DataFrame変換エラー: {e}")
            traceback.print_exc()
            return None

    def _get_pedigree_info(self, horse_id):
        """
        馬の血統情報を取得（血統専用ページから）
        /horse/ped/{horse_id}/ の5代血統表から father, mother_father を抽出

        5代血統表の構造:
        - Row 1-16: 父系 (Row 1 = 父)
        - Row 17-32: 母系 (Row 17 = 母, 母父)
        """
        url = f'https://db.netkeiba.com/horse/ped/{horse_id}/'
        pedigree_info = {}

        try:
            # ランダム遅延（レート制限対策）
            self._random_delay(self.DELAY_PEDIGREE_MIN, self.DELAY_PEDIGREE_MAX)

            # リトライロジック付きリクエスト
            r = self._retry_request(url, f"血統{horse_id}")
            if r is None:
                return pedigree_info

            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.content, 'lxml')

            # blood_table.detail を探す（5代血統表）
            blood_table = soup.select_one('table.blood_table.detail')

            if blood_table:
                rows = blood_table.find_all('tr')

                # 父: Row 1 (index 0), Cell 1
                if len(rows) > 0:
                    cells = rows[0].find_all(['td', 'th'])
                    if len(cells) > 0:
                        father_link = cells[0].find('a')
                        if father_link:
                            pedigree_info['father'] = father_link.get_text(strip=True)

                # 母父: Row 17 (index 16), Cell 2
                # Row 17 = 母系のスタート行（Cell 1 = 母, Cell 2 = 母父）
                if len(rows) > 16:
                    cells = rows[16].find_all(['td', 'th'])
                    if len(cells) > 1:
                        mother_father_link = cells[1].find('a')
                        if mother_father_link:
                            pedigree_info['mother_father'] = mother_father_link.get_text(strip=True)

        except Exception as e:
            # エラー時も処理を続行（血統情報がない馬もいる）
            pass

        return pedigree_info

    def get_horse_details(self, horse_id):
        """
        馬の詳細情報と過去戦績を取得
        - プロフィール: /horse/{horse_id}/
        - 過去戦績: /horse/result/{horse_id}/
        """
        if not horse_id or not str(horse_id).isdigit():
            return {'horse_id': horse_id, 'error': 'Invalid horse_id'}

        horse_details = {'horse_id': horse_id}

        try:
            # --- プロフィール情報取得 ---
            profile_url = f'https://db.netkeiba.com/horse/{horse_id}/'

            # ランダム遅延（レート制限対策）
            self._random_delay(self.DELAY_HORSE_MIN, self.DELAY_HORSE_MAX)

            # リトライロジック付きリクエスト
            r = self._retry_request(profile_url, f"馬{horse_id}プロフィール")
            if r is None:
                return {'horse_id': horse_id, 'error': 'Profile request failed'}

            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.content, 'lxml')

            # --- プロフィール情報抽出 ---
            profile_table = soup.select_one('table.db_prof_table')
            if profile_table:
                for row in profile_table.find_all('tr'):
                    th = row.find('th')
                    td = row.find('td')
                    if th and td:
                        header_text = th.get_text(strip=True)
                        value_text = td.get_text(strip=True)
                        if '生年月日' in header_text:
                            horse_details['birthday'] = value_text
                        elif '調教師' in header_text:
                            horse_details['trainer'] = value_text
                        elif '馬主' in header_text:
                            horse_details['owner'] = value_text
                        elif '生産者' in header_text:
                            horse_details['breeder'] = value_text
                        elif '獲得賞金' in header_text:
                            prize_match = re.search(r'([\d,]+)万円', value_text)
                            if prize_match:
                                horse_details['total_earnings'] = int(prize_match.group(1).replace(',', ''))

            # --- 過去戦績の取得（専用ページから）---
            race_results_list = []
            result_url = f'https://db.netkeiba.com/horse/result/{horse_id}/'

            # ランダム遅延（レート制限対策）
            self._random_delay(self.DELAY_HORSE_MIN, self.DELAY_HORSE_MAX)

            # リトライロジック付きリクエスト
            r_result = self._retry_request(result_url, f"馬{horse_id}過去戦績")
            if r_result is None:
                horse_details['race_results'] = []
                return horse_details

            r_result.encoding = r_result.apparent_encoding
            soup_result = BeautifulSoup(r_result.content, 'lxml')

            results_table = soup_result.select_one('table.db_h_race_results')

            if results_table:
                rows = results_table.select('tbody tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 20:
                        continue

                    try:
                        # コース種別と距離の抽出
                        course_dist_text = cells[13].get_text(strip=True)
                        course_type = course_dist_text[0] if course_dist_text else None
                        distance_match = re.search(r'(\d+)', course_dist_text)
                        distance = int(distance_match.group(1)) if distance_match else None

                        # 競馬場名の抽出
                        place_text = cells[1].get_text(strip=True)
                        place_match = re.search(r'\d*(\D+)\d*', place_text)
                        place = place_match.group(1) if place_match else None

                        race_result = {
                            'horse_id': horse_id,
                            'date': cells[0].get_text(strip=True),
                            'place': place,
                            'weather': cells[2].get_text(strip=True),
                            'race_num': cells[3].get_text(strip=True),
                            'race_name': cells[4].get_text(strip=True),
                            'num_horses': cells[5].get_text(strip=True),
                            'waku': cells[6].get_text(strip=True),
                            'umaban': cells[7].get_text(strip=True),
                            'odds': cells[8].get_text(strip=True),
                            'ninki': cells[9].get_text(strip=True),
                            'jockey': cells[10].get_text(strip=True),
                            'rank': cells[11].get_text(strip=True),
                            'load': cells[12].get_text(strip=True),
                            'course_type': course_type,
                            'distance': distance,
                            'baba': cells[14].get_text(strip=True),
                            'time': cells[15].get_text(strip=True),
                            'diff': cells[16].get_text(strip=True),
                            'passage': cells[18].get_text(strip=True),
                            'agari': cells[19].get_text(strip=True),
                            'weight': cells[22].get_text(strip=True).split('(')[0] if len(cells) > 22 else None,
                        }
                        race_results_list.append(race_result)
                    except (IndexError, ValueError, AttributeError):
                        continue

            horse_details['race_results'] = race_results_list

            # JRA vs 地方の判定
            if race_results_list:
                first_past_race = race_results_list[0]
                prev_place = first_past_race.get('place')
                horse_details['is_local_transfer'] = 1 if (prev_place and prev_place not in self.JRA_TRACKS) else 0

                jra_results = [r for r in race_results_list if r.get('place') in self.JRA_TRACKS]
                horse_details['num_jra_starts'] = len(jra_results)
            else:
                horse_details['is_local_transfer'] = 0
                horse_details['num_jra_starts'] = 0

        except requests.exceptions.RequestException as e:
            print(f"      警告: 馬ID {horse_id} の取得中に通信エラー: {e}")
            horse_details['error'] = f'Request Error: {e}'
        except Exception as e:
            print(f"      警告: 馬ID {horse_id} の処理中にエラー: {e}")
            horse_details['error'] = f'Unexpected Error: {e}'

        return horse_details

    def calculate_horse_stats(self, race_results, current_race_distance=None, current_course_type=None):
        """
        過去戦績から統計値を計算

        Args:
            race_results: 過去戦績のリスト
            current_race_distance: 今回のレース距離（同距離帯勝率計算用）
            current_course_type: 今回のコース種別（芝/ダート）

        Returns:
            統計値の辞書
        """
        stats = {}

        if not race_results:
            # デフォルト値を返す
            return {
                'total_starts': 0,
                'total_wins': 0,
                'total_win_rate': 0.0,
                'turf_starts': 0,
                'turf_wins': 0,
                'turf_win_rate': 0.0,
                'dirt_starts': 0,
                'dirt_wins': 0,
                'dirt_win_rate': 0.0,
                'distance_similar_win_rate': 0.0,
                'grade_race_starts': 0,
                'is_local_transfer': 0,
                'avg_passage_position': 0.0,
                'running_style_category': 'unknown',
                'prev_race_rank': None,
                'prev_race_distance': None,
                'days_since_last_race': None,
                'heavy_track_win_rate': 0.0,
                'avg_last_3f': 0.0,
                'total_earnings': 0,
            }

        # 基本統計
        stats['total_starts'] = len(race_results)
        stats['total_wins'] = sum(1 for r in race_results if self._parse_rank(r.get('rank')) == 1)
        stats['total_win_rate'] = stats['total_wins'] / stats['total_starts'] if stats['total_starts'] > 0 else 0.0

        # 芝/ダート別
        turf_races = [r for r in race_results if r.get('course_type') == '芝']
        dirt_races = [r for r in race_results if r.get('course_type') == 'ダ']

        stats['turf_starts'] = len(turf_races)
        stats['turf_wins'] = sum(1 for r in turf_races if self._parse_rank(r.get('rank')) == 1)
        stats['turf_win_rate'] = stats['turf_wins'] / stats['turf_starts'] if stats['turf_starts'] > 0 else 0.0

        stats['dirt_starts'] = len(dirt_races)
        stats['dirt_wins'] = sum(1 for r in dirt_races if self._parse_rank(r.get('rank')) == 1)
        stats['dirt_win_rate'] = stats['dirt_wins'] / stats['dirt_starts'] if stats['dirt_starts'] > 0 else 0.0

        # 同距離帯勝率（±200m）
        if current_race_distance:
            similar_distance_races = [
                r for r in race_results
                if r.get('distance') and abs(r.get('distance') - current_race_distance) <= 200
            ]
            similar_wins = sum(1 for r in similar_distance_races if self._parse_rank(r.get('rank')) == 1)
            stats['distance_similar_win_rate'] = similar_wins / len(similar_distance_races) if similar_distance_races else 0.0
        else:
            stats['distance_similar_win_rate'] = 0.0

        # 重賞経験
        grade_races = [r for r in race_results if self._is_grade_race(r.get('race_name', ''))]
        stats['grade_race_starts'] = len(grade_races)

        # 地方転入フラグ（最新レースが地方か）
        if race_results:
            first_race_place = race_results[0].get('place')
            stats['is_local_transfer'] = 1 if (first_race_place and first_race_place not in self.JRA_TRACKS) else 0
        else:
            stats['is_local_transfer'] = 0

        # 平均通過順位（走法判定）
        passage_positions = []
        for r in race_results:
            passage_str = r.get('passage', '')
            if passage_str:
                # 通過順位は "01-02-03" のような形式
                positions = passage_str.split('-')
                if positions and positions[0]:
                    try:
                        first_corner = int(positions[0])
                        passage_positions.append(first_corner)
                    except ValueError:
                        pass

        if passage_positions:
            avg_pos = sum(passage_positions) / len(passage_positions)
            stats['avg_passage_position'] = round(avg_pos, 2)

            # 走法カテゴリ判定
            if avg_pos <= 2.0:
                stats['running_style_category'] = '逃げ'
            elif avg_pos <= 5.0:
                stats['running_style_category'] = '先行'
            elif avg_pos <= 10.0:
                stats['running_style_category'] = '差し'
            else:
                stats['running_style_category'] = '追込'
        else:
            stats['avg_passage_position'] = 0.0
            stats['running_style_category'] = 'unknown'

        # 前走情報
        if race_results:
            prev_race = race_results[0]
            stats['prev_race_rank'] = self._parse_rank(prev_race.get('rank'))
            stats['prev_race_distance'] = prev_race.get('distance')

            # 前走からの間隔
            if prev_race.get('date'):
                try:
                    from datetime import datetime
                    prev_date_str = prev_race['date']
                    # 日付形式: "2025/12/07" など
                    prev_date = datetime.strptime(prev_date_str, '%Y/%m/%d')
                    today = datetime.now()
                    stats['days_since_last_race'] = (today - prev_date).days
                except:
                    stats['days_since_last_race'] = None
            else:
                stats['days_since_last_race'] = None
        else:
            stats['prev_race_rank'] = None
            stats['prev_race_distance'] = None
            stats['days_since_last_race'] = None

        # 重馬場勝率
        heavy_track_races = [r for r in race_results if r.get('baba') in ['重', '不良']]
        heavy_wins = sum(1 for r in heavy_track_races if self._parse_rank(r.get('rank')) == 1)
        stats['heavy_track_win_rate'] = heavy_wins / len(heavy_track_races) if heavy_track_races else 0.0

        # 平均上がり3F
        agari_values = []
        for r in race_results:
            agari_str = r.get('agari', '')
            if agari_str:
                try:
                    agari_values.append(float(agari_str))
                except ValueError:
                    pass

        stats['avg_last_3f'] = round(sum(agari_values) / len(agari_values), 2) if agari_values else 0.0

        # 獲得賞金（統計値として設定）
        stats['total_earnings'] = 0  # horse_detailsから取得する

        return stats

    def _parse_rank(self, rank_str):
        """着順文字列を数値に変換"""
        if not rank_str:
            return None
        try:
            return int(rank_str)
        except ValueError:
            return None

    def _is_grade_race(self, race_name):
        """レース名から重賞かどうかを判定"""
        if not race_name:
            return False
        grade_keywords = ['(G1)', '(G2)', '(G3)', '(GI)', '(GII)', '(GIII)', '(L)', '(OP)']
        return any(keyword in race_name for keyword in grade_keywords)

    def _save_past_results(self, past_results):
        """
        過去戦績をCSVに保存

        Args:
            past_results: 過去戦績のリスト
        """
        if not past_results:
            return

        try:
            past_df = pd.DataFrame(past_results)

            # 既存の過去戦績CSVに追記
            if os.path.exists(self.past_results_path):
                existing_past_df = pd.read_csv(self.past_results_path, encoding='utf-8-sig')

                # 重複削除（horse_id + date で判定）
                if 'horse_id' in existing_past_df.columns and 'date' in existing_past_df.columns:
                    # 既存データと新データを結合
                    combined = pd.concat([existing_past_df, past_df], ignore_index=True)
                    # 重複削除
                    combined = combined.drop_duplicates(subset=['horse_id', 'date'], keep='last')
                    combined.to_csv(self.past_results_path, index=False, encoding='utf-8-sig')
                else:
                    # 列がない場合は単純追記
                    past_df.to_csv(self.past_results_path, mode='a', header=False, index=False, encoding='utf-8-sig')
            else:
                # 新規作成
                past_df.to_csv(self.past_results_path, index=False, encoding='utf-8-sig')

        except Exception as e:
            print(f"      過去戦績保存エラー: {e}")

    # ==========================================
    # カレンダーベース方式（B案）
    # ==========================================

    def get_kaisai_dates(self, year, month):
        """
        指定年月の開催日リストを取得（カレンダーページから）

        Args:
            year: 年
            month: 月

        Returns:
            list: 開催日リスト ['20250601', '20250602', ...]
        """
        url = f'https://race.netkeiba.com/top/calendar.html?year={year}&month={month}'
        print(f"  開催日取得: {year}年{month}月")

        try:
            self._update_user_agent()  # User-Agentをランダム変更
            time.sleep(1.0)
            r = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.content, 'lxml')

            kaisai_dates = []
            # カレンダーテーブル内の開催日リンクを探す
            selector = '.Calendar_Table .Week td > a[href*="kaisai_date="]'
            for a_tag in soup.select(selector):
                href = a_tag.get('href')
                if href:
                    match = re.search(r'kaisai_date=(\d{8})', href)
                    if match:
                        kaisai_dates.append(match.group(1))

            unique_dates = sorted(list(set(kaisai_dates)))
            print(f"    開催日: {len(unique_dates)}日")
            return unique_dates

        except requests.exceptions.Timeout:
            print(f"    タイムアウトエラー: {url}")
        except requests.exceptions.RequestException as e:
            print(f"    ページ取得エラー: {e}")
        except Exception as e:
            print(f"    予期せぬエラー: {e}")
            traceback.print_exc()

        return []

    def get_race_ids_for_date(self, date_str):
        """
        指定日のレースIDリストを取得（全会場対応・修正版）

        Args:
            date_str: 開催日（例: '20250601'）

        Returns:
            list: レースIDリスト ['202506010101', '202506010102', ...]
        """
        all_race_ids = []

        # まずrequestsでカレンダーから会場情報を取得（高速）
        try:
            url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={date_str}'
            self._update_user_agent()
            time.sleep(0.3)
            r = self.session.get(url, timeout=self.REQUEST_TIMEOUT)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, 'lxml')

            # 全てのレースリンクを取得（複数会場対応）
            # パターン1: レース結果ページへのリンク
            for a_tag in soup.select('a[href*="/race/"]'):
                href = a_tag.get('href', '')

                # race_id=XXXX 形式
                match = re.search(r'race_id=(\d{12})', href)
                if match:
                    all_race_ids.append(match.group(1))
                    continue

                # /race/result/XXXX 形式
                match = re.search(r'/race/(?:result|shutuba)/(\d{12})', href)
                if match:
                    all_race_ids.append(match.group(1))
                    continue

                # /race/XXXX/ 形式
                match = re.search(r'/race/(\d{12})/', href)
                if match:
                    all_race_ids.append(match.group(1))

            # 重複削除・ソート
            unique_race_ids = sorted(list(set(all_race_ids)))

            if unique_race_ids:
                return unique_race_ids

        except Exception as e:
            print(f"      requests取得エラー ({date_str}): {e}")

        # requestsで取れない場合はSeleniumを試す
        if not SELENIUM_AVAILABLE:
            return []

        return self._get_race_ids_selenium(date_str)

    def _get_race_ids_selenium(self, date_str):
        """Selenium使用のフォールバック（JavaScript必要な場合）"""
        url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={date_str}'
        driver = None

        options = webdriver.ChromeOptions()
        options.add_argument(f'--user-agent={random.choice(self.USER_AGENTS)}')
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        try:
            driver = webdriver.Chrome(options=options)
            driver.get(url)
            # JavaScript読み込み待機（レースリスト表示に必要）
            time.sleep(5)

            soup = BeautifulSoup(driver.page_source, 'lxml')
            race_ids = []

            # 全レースリンクを抽出
            for a_tag in soup.select('a[href*="/race/"]'):
                href = a_tag.get('href', '')
                match = re.search(r'race_id=(\d{12})|/race/(?:result|shutuba)/(\d{12})|/race/(\d{12})/', href)
                if match:
                    race_id = match.group(1) or match.group(2) or match.group(3)
                    if race_id:
                        race_ids.append(race_id)

            return sorted(list(set(race_ids)))

        except Exception as e:
            print(f"      Seleniumエラー ({date_str}): {e}")
            return []
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass

    def collect_from_calendar(self, start_year, start_month, end_year, end_month, collect_horse_details=True):
        """
        カレンダーから期間指定でレースIDを取得して収集

        Args:
            start_year: 開始年
            start_month: 開始月
            end_year: 終了年
            end_month: 終了月
            collect_horse_details: 馬詳細情報を取得するか

        Returns:
            list: 収集されたレースIDのリスト
        """
        print("="*60)
        print("カレンダーベースでレースID収集")
        print("="*60)
        print(f"期間: {start_year}年{start_month}月 〜 {end_year}年{end_month}月")
        print()

        all_race_ids = []
        current_year = start_year
        current_month = start_month

        while not (current_year > end_year or (current_year == end_year and current_month > end_month)):
            # 開催日取得
            kaisai_dates = self.get_kaisai_dates(current_year, current_month)

            if not kaisai_dates:
                print(f"    {current_year}年{current_month}月: 開催日なし")
            else:
                print(f"    {current_year}年{current_month}月: {len(kaisai_dates)}日")

                for date_str in kaisai_dates:
                    race_ids = self.get_race_ids_for_date(date_str)
                    if race_ids:
                        print(f"      {date_str}: {len(race_ids)}レース")
                        all_race_ids.extend(race_ids)
                    time.sleep(0.5)  # 負荷軽減

            # 次の月へ
            if current_month == 12:
                current_month = 1
                current_year += 1
            else:
                current_month += 1

        print(f"\n合計レースID: {len(all_race_ids)}件")

        if all_race_ids:
            # 収集実行（A案のロジックを再利用）
            self._collect_races(all_race_ids, collect_horse_details)

        return all_race_ids

    def _collect_races(self, race_ids, collect_horse_details=True, force_update=False):
        """
        レースIDリストからデータを収集（内部用）

        Args:
            race_ids: レースIDのリスト
            collect_horse_details: 馬詳細情報を取得するか
            force_update: 既存レースも強制的に再収集して統計を更新するか
        """
        # 進捗ファイル読み込み（再開用）
        progress_race_ids = self._load_progress()

        # 既存データ確認
        existing_race_ids = set()
        if os.path.exists(self.db_path):
            try:
                existing_df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
                if 'race_id' in existing_df.columns:
                    existing_race_ids = set(existing_df['race_id'].astype(str).unique())
                print(f"[CSV] 既存レース: {len(existing_race_ids)}件")
            except Exception as e:
                print(f"[CSV] 読み込みエラー: {e}")

        # 重複除外（既存データ + 進捗ファイル）
        total = len(race_ids)

        if force_update:
            # 強制更新モード: 既存レースも再収集
            all_processed = progress_race_ids  # 進捗ファイルのみ除外
            update_count = len([rid for rid in race_ids if str(rid) in existing_race_ids and str(rid) not in progress_race_ids])
            print(f"更新対象: {update_count}件（既存レースの統計追加）")
        else:
            # 通常モード: 既存レースはスキップ
            all_processed = existing_race_ids | progress_race_ids

        race_ids = [rid for rid in race_ids if str(rid) not in all_processed]
        duplicate_count = total - len(race_ids)
        new_count = len(race_ids)

        if not force_update:
            print(f"重複: {duplicate_count}件")
            print(f"新規: {new_count}件")

        if new_count == 0:
            if force_update:
                print("\n更新対象レースがありません（全て処理済み）")
            else:
                print("\n新規レースがありません")
            return

        print(f"\n新規{new_count}件を取得...")

        # データ収集
        data_list = []
        success_count = 0
        fail_count = 0
        processed_in_session = []  # このセッションで処理したレースID

        for i, race_id in enumerate(race_ids, 1):
            print(f"[{i}/{new_count}] {race_id}...", end=' ')

            df = self.scrape_race_result(race_id, collect_horse_details=collect_horse_details)

            if df is not None and len(df) > 0:
                data_list.append(df)
                success_count += 1
                print("OK")
            else:
                fail_count += 1
                print("NG")

            # 処理済みリストに追加
            processed_in_session.append(str(race_id))

            # レース間クールダウン
            if i < new_count:  # 最後のレースでは不要
                self._race_cooldown()

            # 定期保存（10件ごと）
            if i % 10 == 0:
                # データ保存
                if data_list:
                    self._save_data(data_list)
                    data_list = []
                # 進捗保存
                self._save_progress(processed_in_session)
                print(f"      [進捗保存] {len(processed_in_session)}/{new_count}件完了")

        # 残りを保存
        if data_list:
            self._save_data(data_list)

        # 最終進捗保存
        if processed_in_session:
            self._save_progress(processed_in_session)

        print(f"\n{'='*60}")
        print(f"収集完了: 成功 {success_count}件 / 失敗 {fail_count}件")
        print(f"{'='*60}")

        # 全件完了時は進捗ファイルを削除
        if success_count + fail_count == new_count and os.path.exists(self.progress_file):
            try:
                os.remove(self.progress_file)
                print("進捗ファイルをクリア")
            except Exception:
                pass

    def update_from_file(self, filename='race_ids.txt'):
        """
        ファイルからレースIDを読み込んで更新

        Args:
            filename: レースIDリストファイル
        """
        print("="*60)
        print("レースIDリストから一括更新")
        print("="*60)

        # ファイル読み込み
        if not os.path.exists(filename):
            print(f"\nエラー: {filename} が見つかりません")
            print(f"\n{filename} を作成して、レースIDを1行ずつ記入してください")
            print("\n例:")
            print("  202405011201")
            print("  202405011202")
            print("  202405011203")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            race_ids = [line.strip() for line in f if line.strip() and line.strip().isdigit()]

        if not race_ids:
            print(f"\nエラー: {filename} にレースIDが見つかりません")
            return

        print(f"\nレースID読み込み: {len(race_ids)}件")

        # 既存データ確認
        existing_ids = self._get_existing_ids()
        new_ids = [rid for rid in race_ids if rid not in existing_ids]

        print(f"既存: {len(race_ids) - len(new_ids)}件")
        print(f"新規: {len(new_ids)}件")

        if not new_ids:
            print("\n全て既に登録済みです")
            return

        # スクレイピング
        print(f"\n新規{len(new_ids)}件を取得中...")
        print()

        all_data = []
        success = 0
        fail = 0

        for i, race_id in enumerate(new_ids, 1):
            print(f"[{i}/{len(new_ids)}] {race_id}...", end=" ")

            df = self.scrape_race_result(race_id)

            if df is not None and len(df) > 0:
                all_data.append(df)
                success += 1
                print(f"OK ({len(df)}頭)")
                # ログに書き込み
                self._write_to_log(race_id)
            else:
                fail += 1
                print("NG")

            # 10件ごとに保存
            if len(all_data) >= 10:
                self._save_data(all_data)
                print(f"  → {len(all_data)}件をDBに追加\n")
                all_data = []

            time.sleep(0.5)

        # 残り保存
        if all_data:
            self._save_data(all_data)
            print(f"\n  → {len(all_data)}件をDBに追加")

        print("\n" + "="*60)
        print(f"完了: 成功 {success}件 / 失敗 {fail}件")
        print("="*60)

    def _get_existing_ids(self):
        """既存レースID取得（CSVから - CSVが真実）"""
        existing_ids = set()

        # CSVから読み込み（優先）
        try:
            if os.path.exists(self.db_path):
                df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
                existing_ids = set(df['race_id'].astype(str).unique())
                print(f"[CSV] 既存レース: {len(existing_ids):,}件")
                return existing_ids
        except Exception as e:
            print(f"[警告] CSV読み込みエラー: {e}")

        # CSVがない場合のみログファイルから（フォールバック）
        try:
            if os.path.exists(self.log_path):
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    existing_ids = set(line.strip() for line in f if line.strip())
                print(f"[ログ] 既存レース: {len(existing_ids):,}件（CSVなし）")
                return existing_ids
        except Exception as e:
            print(f"[警告] ログ読み込みエラー: {e}")

        return set()

    def _write_to_log(self, race_id):
        """処理済みレースIDをログに書き込み"""
        try:
            # ログディレクトリ作成
            log_dir = os.path.dirname(self.log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            # 追記モードで書き込み
            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(f"{race_id}\n")
        except Exception as e:
            print(f"[警告] ログ書き込みエラー: {e}")

    def _save_data(self, data_list):
        """データ保存（改善版：バックアップ＋列統一）"""
        if not data_list:
            return

        try:
            new_df = pd.concat(data_list, ignore_index=True)

            if os.path.exists(self.db_path):
                # バックアップ作成
                import shutil
                from datetime import datetime
                backup_path = self.db_path.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
                shutil.copy2(self.db_path, backup_path)
                print(f"      バックアップ作成: {os.path.basename(backup_path)}")

                existing_df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)

                # 列の統一（既存列に新規列がない場合は追加）
                for col in new_df.columns:
                    if col not in existing_df.columns:
                        existing_df[col] = None

                for col in existing_df.columns:
                    if col not in new_df.columns:
                        new_df[col] = None

                # 列順を既存データに合わせる
                new_df = new_df[existing_df.columns]

                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            else:
                combined_df = new_df

            # 重複削除（race_id + 馬番）
            # 列名を統一してから重複削除（'馬番'と'Umaban'を統合）
            if '馬番' in combined_df.columns and 'Umaban' in combined_df.columns:
                # 両方の列が存在する場合、統合列を作成
                combined_df['_horse_number_unified'] = combined_df['馬番'].fillna(combined_df['Umaban'])
                combined_df = combined_df.drop_duplicates(subset=['race_id', '_horse_number_unified'], keep='last')
                # 統合列を削除
                combined_df = combined_df.drop(columns=['_horse_number_unified'])
            elif '馬番' in combined_df.columns:
                combined_df = combined_df.drop_duplicates(subset=['race_id', '馬番'], keep='last')
            elif 'Umaban' in combined_df.columns:
                combined_df = combined_df.drop_duplicates(subset=['race_id', 'Umaban'], keep='last')
            else:
                # 馬番列がない場合は馬名で重複削除を試みる
                if 'HorseName' in combined_df.columns:
                    combined_df = combined_df.drop_duplicates(subset=['race_id', 'HorseName'], keep='last')
                elif '馬名' in combined_df.columns:
                    combined_df = combined_df.drop_duplicates(subset=['race_id', '馬名'], keep='last')
                else:
                    # 最終手段: race_idのみで重複削除（推奨されない）
                    combined_df = combined_df.drop_duplicates(subset=['race_id'], keep='last')

            combined_df.to_csv(self.db_path, index=False, encoding='utf-8')

        except Exception as e:
            print(f"      エラー: データ保存中にエラー: {e}")
            traceback.print_exc()


def main():
    """
    メイン - ハイブリッド方式
    A案（リスト方式）とB案（カレンダー方式）を選択可能
    """
    print("="*60)
    print(" NetKeibaデータ収集ツール（ハイブリッド版）")
    print("="*60)
    print()
    print("収集方式を選択してください：")
    print()
    print("  [1] A案: レースIDリストから収集（高速・安定）")
    print("      → race_ids.txt から読み込み")
    print()
    print("  [2] B案: カレンダーから期間指定で収集（自動・柔軟）")
    print("      → 年月を指定して自動取得")
    print()
    print("  [3] 11-12月の新規レースを自動収集（2025年）")
    print("      → カレンダー方式で最新データ取得")
    print()
    print("  [0] 終了")
    print()

    choice = input("選択 [0-3]: ").strip()

    updater = ListBasedUpdater()

    if choice == '1':
        # A案: リスト方式
        filename = input("\nレースIDファイル名 [race_ids.txt]: ").strip()
        if not filename:
            filename = 'race_ids.txt'

        collect_stats = input("馬統計情報も収集しますか？ (y/n) [y]: ").strip().lower()
        collect_horse_details = collect_stats != 'n'

        # update_from_fileメソッドを改善版で呼び出し
        if not os.path.exists(filename):
            print(f"\nエラー: {filename} が見つかりません")
            return

        with open(filename, 'r', encoding='utf-8') as f:
            race_ids = [line.strip() for line in f if line.strip() and line.strip().isdigit()]

        if not race_ids:
            print(f"\nエラー: {filename} にレースIDが見つかりません")
            return

        print(f"\nレースID読み込み: {len(race_ids)}件")
        updater._collect_races(race_ids, collect_horse_details)

    elif choice == '2':
        # B案: カレンダー方式
        print("\n期間を指定してください：")
        start_year = int(input("開始年 [2025]: ").strip() or '2025')
        start_month = int(input("開始月 [1]: ").strip() or '1')
        end_year = int(input("終了年 [2025]: ").strip() or '2025')
        end_month = int(input("終了月 [12]: ").strip() or '12')

        collect_stats = input("馬統計情報も収集しますか？ (y/n) [y]: ").strip().lower()
        collect_horse_details = collect_stats != 'n'

        updater.collect_from_calendar(
            start_year, start_month,
            end_year, end_month,
            collect_horse_details=collect_horse_details
        )

    elif choice == '3':
        # 2025年11-12月の新規レース自動収集
        print("\n2025年11-12月の新規レースを収集します")
        confirm = input("実行しますか？ (y/n) [y]: ").strip().lower()

        if confirm != 'n':
            collect_stats = input("馬統計情報も収集しますか？ (y/n) [y]: ").strip().lower()
            collect_horse_details = collect_stats != 'n'

            updater.collect_from_calendar(
                2025, 11,
                2025, 12,
                collect_horse_details=collect_horse_details
            )
        else:
            print("キャンセルされました")

    elif choice == '0':
        print("終了します")
        return

    else:
        print(f"\n無効な選択: {choice}")
        return

    print("\n処理完了！")
    input("\nEnterキーを押して終了...")


if __name__ == '__main__':
    main()
