import os

import sys
import json
import pickle
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd # type: ignore
import numpy as np # type: ignore
import matplotlib.pyplot as plt # type: ignore
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg # type: ignore
import threading
import random
from datetime import datetime
import requests # type: ignore
from bs4 import BeautifulSoup # type: ignore
import re
import time
import traceback
import time as _time
from selenium import webdriver # type: ignore
from selenium.webdriver.common.by import By # type: ignore
from selenium.webdriver.support import expected_conditions as EC # type: ignore
from selenium.webdriver.support.ui import WebDriverWait # type: ignore
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException # type: ignore
from selenium.webdriver.chrome.service import Service as ChromeService # type: ignore

# --- Matplotlibの日本語設定 (Windows向け) ---
try:
    plt.rcParams['font.family'] = 'Meiryo'
    plt.rcParams['font.sans-serif'] = ['Meiryo', 'Yu Gothic', 'MS Gothic']
    plt.rcParams['axes.unicode_minus'] = False
except Exception as e:
    print(f"日本語フォントの設定に失敗しました。グラフの日本語が文字化けする可能性があります。エラー: {e}", file=sys.stderr)

class HorseRacingAnalyzerApp:
    # --- Pickle化されたファイルの読み込み/保存用ヘルパーメソッド ---
    def _load_pickle(self, file_path):
        """指定されたパスからpickleファイルをロードして返す"""
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
                print(f"INFO: Pickleファイルをロードしました: {file_path}")
                return data
            except Exception as e:
                print(f"ERROR: Pickleファイルのロード中に予期せぬエラーが発生しました: {file_path}. Error: {e}")
        else:
            print(f"INFO: Pickleファイルが見つかりません: {file_path}")
        return None

    def _save_pickle(self, data, file_path):
        """指定されたデータをpickleファイルとして保存する"""
        try:
            save_dir = os.path.dirname(file_path)
            if save_dir and not os.path.exists(save_dir):
                os.makedirs(save_dir)
                print(f"INFO: ディレクトリを作成しました: {save_dir}")
            with open(file_path, 'wb') as f:
                pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
            print(f"INFO: Pickleファイルに保存しました: {file_path}")
            return True
        except Exception as e:
            print(f"ERROR: Pickleファイルへの保存中にエラーが発生しました: {file_path}. Error: {e}")
        return False

    JRA_TRACKS = ["札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"]

    def __init__(self, root):
        self.root = root
        self.root.title("競馬データ分析ツール")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # スタイル設定
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure("TNotebook", background="#f0f0f0", tabmargins=[2, 5, 2, 0])
        self.style.configure("TNotebook.Tab", padding=[10, 5], font=("Meiryo UI", 10))
        self.style.map("TNotebook.Tab", background=[("selected", "#ffffff"), ("active", "#e0e0e0")])
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TButton", font=("Meiryo UI", 10), padding=5)
        self.style.configure("TLabel", font=("Meiryo UI", 10), background="#f0f0f0")
        self.style.configure("TLabelFrame", font=("Meiryo UI", 11, "bold"), background="#f0f0f0")
        self.style.configure("TLabelFrame.Label", font=("Meiryo UI", 11, "bold"), background="#f0f0f0")
        self.style.configure("TEntry", font=("Meiryo UI", 10))
        self.style.configure("TCombobox", font=("Meiryo UI", 10))
        self.style.configure("Treeview", font=("Meiryo UI", 9), rowheight=25)
        self.style.configure("Treeview.Heading", font=("Meiryo UI", 10, "bold"))

        # メインフレーム
        self.main_frame = ttk.Frame(self.root, padding="10 10 10 10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # タブコントロール
        self.tab_control = ttk.Notebook(self.main_frame)

        # タブの作成
        self.tab_home = ttk.Frame(self.tab_control, padding="10")
        self.tab_data = ttk.Frame(self.tab_control, padding="10")
        self.tab_analysis = ttk.Frame(self.tab_control, padding="10")
        self.tab_prediction = ttk.Frame(self.tab_control, padding="10")
        self.tab_results = ttk.Frame(self.tab_control, padding="10")
        self.tab_settings = ttk.Frame(self.tab_control, padding="10")

        # タブの追加
        self.tab_control.add(self.tab_home, text="ホーム")
        self.tab_control.add(self.tab_data, text="データ管理")
        self.tab_control.add(self.tab_analysis, text="データ分析")
        self.tab_control.add(self.tab_prediction, text="予測")
        self.tab_control.add(self.tab_results, text="結果検証")
        self.tab_control.add(self.tab_settings, text="設定")
        self.tab_control.pack(fill=tk.BOTH, expand=True)

        # ステータスバー
        self.status_var = tk.StringVar(value="準備完了")
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=3)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # データの初期化
        self.race_data = None
        self.horse_data = None
        self.result_data = None
        self.combined_data = pd.DataFrame()
        self.processed_data = pd.DataFrame()
        self.payout_data = []
        self.model = None
        self.settings = {}
        self.horse_details_cache = {}
        self.course_time_stats = {}
        self.father_stats = {}
        self.mother_father_stats = {}
        self.gate_stats = {}
        self.jockey_stats = {} # ★★★ 騎手統計用の辞書を追加 ★★★
        self.reference_times = {}
        self.trained_model = None
        self.model_features = []
        self.imputation_values_ = {}

        # 設定ファイルのパスを決定
        self.app_data_dir = os.path.join(os.path.expanduser("~"), "HorseRacingAnalyzer")
        self.settings_file = os.path.join(self.app_data_dir, "settings.json")

        # 設定の読み込み
        self.load_settings()
        self.load_cache_from_file()
        self.load_model_from_file()
        
        imputation_values_default_filename = "imputation_values.pkl"
        models_base_dir = self.settings.get("models_dir", self.settings.get("data_dir", os.path.join(self.app_data_dir, "models")))
        default_imputation_path = os.path.join(models_base_dir, imputation_values_default_filename)
        imputation_values_path = self.settings.get("imputation_values_path", default_imputation_path)
        loaded_imputation_values = self._load_pickle(imputation_values_path)
        if loaded_imputation_values is not None and isinstance(loaded_imputation_values, dict):
            self.imputation_values_ = loaded_imputation_values
        else:
            print(f"INFO: 欠損値補完ファイルが見つからないかロードに失敗 ({imputation_values_path})。学習時に新規作成されます。")

        # スクレイピング設定
        self.REQUEST_TIMEOUT = 20
        self.SELENIUM_WAIT_TIMEOUT = 30
        self.SLEEP_TIME_PER_PAGE = float(self.settings.get("scrape_sleep_page", 0.7))
        self.SLEEP_TIME_PER_RACE = float(self.settings.get("scrape_sleep_race", 0.2))
        self.USER_AGENT = self.settings.get("user_agent", 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36')
        self.CHROME_DRIVER_PATH = self.settings.get("chrome_driver_path", None)
        self.SAVE_DIRECTORY = self.settings.get("data_dir", ".")
        self.PROCESSED_LOG_FILE = os.path.join(self.SAVE_DIRECTORY, "processed_race_ids.log")

        self.ensure_directories_exist()

        # 各タブの初期化
        self.init_home_tab()
        self.init_data_tab()
        self.init_analysis_tab()
        self.init_prediction_tab()
        self.init_results_tab()
        self.init_settings_tab()

        self.reflect_settings_to_ui()

    def save_cache_to_file(self, filename="horse_cache.pkl"):
        """現在の self.horse_details_cache の内容を指定ファイルに保存する"""
        if hasattr(self, 'horse_details_cache') and self.horse_details_cache:
            save_dir = self.settings.get("data_dir", "data")
            if not os.path.exists(save_dir):
                try:
                    os.makedirs(save_dir)
                except Exception as e:
                    messagebox.showerror("エラー", f"ディレクトリ作成失敗: {save_dir}")
                    save_dir = "."
            filepath = os.path.join(save_dir, filename)
            try:
                with open(filepath, 'wb') as f:
                    pickle.dump(self.horse_details_cache, f, pickle.HIGHEST_PROTOCOL)
                self.root.after(0, lambda: messagebox.showinfo("キャッシュ保存完了", f"馬詳細キャッシュ ({len(self.horse_details_cache)}件) を保存しました:\n{filepath}"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("キャッシュ保存エラー", f"キャッシュの保存中にエラーが発生しました:\n{filepath}\n{e}"))
        else:
            self.root.after(0, lambda: messagebox.showwarning("キャッシュ保存", "保存するキャッシュデータが見つかりません。"))

    def load_cache_from_file(self, filename="horse_cache.pkl"):
        """指定されたファイルから馬詳細キャッシュを読み込む"""
        load_dir = self.settings.get("data_dir", "data")
        filepath = os.path.join(load_dir, filename)
        if os.path.exists(filepath):
            try:
                with open(filepath, 'rb') as f:
                    self.horse_details_cache = pickle.load(f)
                self.update_status(f"馬詳細キャッシュ読み込み完了 ({len(self.horse_details_cache)}件)")
            except Exception as e:
                self.horse_details_cache = {}
                self.update_status("警告: キャッシュ読み込み失敗")
        else:
            self.horse_details_cache = {}
            self.update_status("キャッシュファイルなし")

    def get_kaisai_dates(self,year, month):
        """指定年月の開催日リストを取得"""
        url = f'https://race.netkeiba.com/top/calendar.html?year={year}&month={month}'
        headers = {'User-Agent': self.USER_AGENT}
        try:
            time.sleep(self.SLEEP_TIME_PER_PAGE)
            r = requests.get(url, headers=headers, timeout=self.REQUEST_TIMEOUT)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.content, 'lxml')
            kaisai_dates = []
            selector = '.Calendar_Table .Week td > a[href*="kaisai_date="]'
            for a_tag in soup.select(selector):
                href = a_tag.get('href')
                match = re.search(r'kaisai_date=(\d{8})', href)
                if match:
                    kaisai_dates.append(match.group(1))
            return sorted(list(set(kaisai_dates)))
        except Exception as e:
            print(f"  開催日取得エラー ({url}): {e}")
        return []

    def get_race_ids(self, date_str):
        """指定日のレースIDリストを取得"""
        url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={date_str}'
        driver = None
        options = webdriver.ChromeOptions()
        options.add_argument(f'--user-agent={self.USER_AGENT}')
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        race_data_list = []
        try:
            if self.CHROME_DRIVER_PATH and os.path.exists(self.CHROME_DRIVER_PATH):
                 service = ChromeService(executable_path=self.CHROME_DRIVER_PATH)
                 driver = webdriver.Chrome(service=service, options=options)
            else:
                 driver = webdriver.Chrome(options=options)
            
            driver.get(url)
            wait = WebDriverWait(driver, self.SELENIUM_WAIT_TIMEOUT)
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, '#RaceTopRace, .RaceList_Box, .no_race, .alert')
            ))
            time.sleep(self.SLEEP_TIME_PER_PAGE / 2)
            soup = BeautifulSoup(driver.page_source, 'lxml')
            selector = '.RaceList_DataItem > a:first-of-type'
            for a_tag in soup.select(selector):
                href = a_tag.get('href')
                if not href: continue
                match = re.search(r'race_id=(\d+)', href)
                if match:
                    race_id = match.group(1)
                    race_data_list.append((race_id, date_str))
            return sorted(list(set(race_data_list)), key=lambda x: x[0])
        except Exception as e:
            print(f"  レースID取得エラー ({url}): {e}")
        finally:
            if driver:
                driver.quit()
        return []

    def get_result_table(self, race_id):
        """レース結果ページからレース情報と結果テーブルを取得"""
        url = f'https://db.netkeiba.com/race/{race_id}/'
        headers = {'User-Agent': self.USER_AGENT}
        race_info_dict = {'race_id': race_id}
        result_table = []
        try:
            time.sleep(self.SLEEP_TIME_PER_RACE)
            r = requests.get(url, headers=headers, timeout=self.REQUEST_TIMEOUT)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.content, 'lxml')
            
            data_intro_div = soup.select_one('div.data_intro')
            if data_intro_div:
                race_name_h1 = data_intro_div.select_one('h1')
                if race_name_h1: race_info_dict['race_name'] = race_name_h1.get_text(strip=True)
                details_span = data_intro_div.select_one('p span')
                if details_span:
                    details_text = details_span.get_text(strip=True)
                    parts = [p.strip() for p in details_text.split('/')]
                    if len(parts) >= 1:
                        course_text = parts[0]
                        course_type_match = re.search(r'([芝ダ障])', course_text)
                        distance_match = re.search(r'(\d+)m', course_text)
                        if course_type_match: race_info_dict['course_type'] = course_type_match.group(1)
                        if distance_match: race_info_dict['distance'] = int(distance_match.group(1))
                    if len(parts) >= 2: race_info_dict['weather'] = parts[1].split(':')[-1].strip()
                    if len(parts) >= 3: race_info_dict['track_condition'] = parts[2].split(':')[-1].strip()
            
            small_text_p = soup.select_one('p.smalltxt')
            if small_text_p:
                small_text = small_text_p.get_text(strip=True)
                date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', small_text)
                if date_match: race_info_dict['date'] = date_match.group(1)
                place_match = re.search(r'\d回(\S+?)\d日目', small_text)
                if place_match: race_info_dict['track_name'] = place_match.group(1)

            table_tag = soup.select_one('table.race_table_01.nk_tb_common')
            if table_tag:
                header_cells = [th.get_text(strip=True) for th in table_tag.select('tr:first-child th')]
                horse_name_index = header_cells.index('馬名') if '馬名' in header_cells else -1
                header_with_url = list(header_cells)
                if horse_name_index != -1: header_with_url.insert(horse_name_index + 1, 'HorseName_url')
                result_table.append(header_with_url)

                for tr_tag in table_tag.select('tr')[1:]:
                    row_data = []
                    td_tags = tr_tag.find_all('td', recursive=False)
                    for i, td_tag in enumerate(td_tags):
                        row_data.append(td_tag.get_text(strip=True))
                        if i == horse_name_index:
                            a_tag = td_tag.find('a')
                            row_data.append(a_tag['href'].strip() if a_tag and a_tag.has_attr('href') else None)
                    if len(row_data) == len(header_with_url):
                        result_table.append(row_data)

        except Exception as e:
            print(f"      結果テーブル取得エラー ({url}): {e}")
        return race_info_dict, result_table

    
    def get_pay_table(self, race_id): # self を追加
        """払い戻しテーブルデータをリストのリストで取得"""
        url = f'https://race.netkeiba.com/race/result.html?race_id={race_id}' # race.netkeiba.com を使用
        self.update_status(f"払戻取得試行: {race_id}")
        print(f"      払戻取得試行: {url}")
        headers = {'User-Agent': self.USER_AGENT}
        try:
            time.sleep(self.SLEEP_TIME_PER_PAGE)
            r = requests.get(url, headers=headers, timeout=self.REQUEST_TIMEOUT)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.content, 'lxml')
            pay_table = []

            # ★★★ '.Result_Pay_Back' の中の '.Payout_Detail_Table' を探すセレクタ ★★★
            payout_tables = soup.select('.Result_Pay_Back .Payout_Detail_Table')

            if not payout_tables:
                # 他の可能性も一応試す (db.netkeiba.com 用など)
                payout_tables = soup.select('.payout_block table')
                if not payout_tables:
                     payout_tables = soup.select('table.pay_table_01') # さらに別の可能性

            if not payout_tables:
                if soup.find(string=re.compile("出走取消|開催中止")):
                     print(f"        情報: 払い戻しが存在しないようです（取消/中止など） ({race_id})")
                else:
                     self.update_status(f"警告: 払戻テーブルが見つかりません ({race_id})")
                     print(f"      警告: 払い戻しテーブルが見つかりませんでした ({race_id})。HTML構造を確認してください。")
                return []

            # 見つかった全てのテーブルから行データを抽出
            for table_tag in payout_tables:
                for tr_tag in table_tag.select('tr'):
                    row_data = [tag.get_text('\n', strip=True) for tag in tr_tag.select('th, td')]
                    if row_data and any(row_data):
                        pay_table.append(row_data)

            # ★ 取得できたかデバッグプリントを追加（重要）
            if pay_table:
                  print(f"      DEBUG: get_pay_table成功 ({race_id}), {len(pay_table)}行")
            else:
                 print(f"      DEBUG: get_pay_table失敗 or データなし ({race_id})")


            return pay_table

        # ... (except節は変更なし) ...
        except Exception as e:
            self.update_status(f"予期せぬエラー(get_pay_table): {race_id}")
            print(f"      予期せぬエラー (get_pay_table) ({url}): {e}")
            traceback.print_exc()
        return []
    
    # --- 部品関数5: 出馬表テーブル取得 (レース共通情報取得強化・HTML構造対応版) ---
    def get_shutuba_table(self, race_id):
        """
        shutuba_past.html から出馬表テーブルデータとレース共通情報を取得する。
        返り値: {'race_details': dict, 'horse_list': list_of_dicts}
        race_details には、レース名、日付、場所、コース、距離、馬場状態などを含む。
        horse_list は各馬の情報（馬番、馬名、horse_idなど）の辞書のリスト。
        """
        url = f'https://race.netkeiba.com/race/shutuba_past.html?race_id={race_id}'
        print(f"      出馬表(共通情報付)取得試行: {url}")
        driver = None
        options = webdriver.ChromeOptions()
        options.add_argument(f'--user-agent={self.USER_AGENT}')
        # options.add_argument('--headless') # デバッグ中は表示した方が問題箇所を特定しやすいこともあります
        options.add_argument('--disable-gpu'); options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage'); options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        horse_data_list = []
        race_common_info = { 
            'race_id': race_id, 'RaceName': 'N/A', 'RaceDate': None, 'TrackName': 'N/A',
            'CourseType': 'N/A', 'Distance': None, 'Weather': 'N/A', 'TrackCondition': 'N/A',
            'RaceNum': 'N/A', 'Around': 'N/A'
            # 'baba' キーも race_conditions で使っているので、ここで初期化しても良い
        }

        try:
            if self.CHROME_DRIVER_PATH and os.path.exists(self.CHROME_DRIVER_PATH):
                service = ChromeService(executable_path=self.CHROME_DRIVER_PATH)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                print("        警告: ChromeDriverのパスが設定されていないか無効です。環境変数PATHから探します。")
                driver = webdriver.Chrome(options=options)
            
            driver.set_page_load_timeout(60) 
            # wait = WebDriverWait(driver, self.SELENIUM_WAIT_TIMEOUT) # 今回は特定の要素待機は使わない方針で進めてみる
            driver.get(url)
            time.sleep(self.SLEEP_TIME_PER_PAGE) # ページ描画のための十分な待機時間 (調整可能)
            self.last_scraped_page_title = driver.title 
            soup = BeautifulSoup(driver.page_source, 'lxml')

            # === ▼▼▼ 正しい開催日の取得ロジック (日付ナビゲーションの Active な要素から) ▼▼▼ ===
            date_str_from_page = None
            try:
                # class="Active" を持つ dd タグの中の a タグを探す
                # セレクタの具体性はページのHTML構造に依存するため、調整が必要な場合がある
                active_date_link_selector = "dl#RaceList_DateList dd.Active > a" # ユーザー提供のHTMLに基づくセレクタ
                active_date_tag = soup.select_one(active_date_link_selector)
                
                if active_date_tag and active_date_tag.has_attr('href'):
                    href_value = active_date_tag['href']
                    date_param_match = re.search(r'kaisai_date=(\d{8})', href_value)
                    if date_param_match:
                        yyyymmdd = date_param_match.group(1)
                        year = yyyymmdd[0:4]
                        month = yyyymmdd[4:6]
                        day = yyyymmdd[6:8]
                        date_str_from_page = f"{year}年{month}月{day}日" # YYYY年MM月DD日の形式で格納
                        race_common_info['RaceDate'] = date_str_from_page
                        print(f"INFO: ページの日付ナビゲーション(Active)から開催日を取得しました: {race_common_info['RaceDate']}")
                    else:
                        # hrefから直接取れない場合、リンクのテキストから取得試行も考えられるが、年情報がない
                        print(f"WARN: Activeな日付リンクのhrefからkaisai_dateを抽出できませんでした。リンクテキスト: '{active_date_tag.get_text(strip=True)}'")
                elif active_date_tag: # aタグは見つかったがhrefがない、または上記条件に合致しない場合
                     # 代替として、Activeなddタグ直下のaタグのtitle属性から日付を試みる (例: title="5月25日(日)")
                     # ただし、これには年情報がないため、他の情報源と組み合わせる必要がある。
                     # ここでは、より確実な情報源がない場合のフォールバックとしてレースIDからの推定を優先。
                     print(f"WARN: Activeな日付リンクのhrefからの日付抽出に失敗。リンクテキスト: '{active_date_tag.get_text(strip=True)}'")
                else:
                    print(f"WARN: Activeな日付リンク (selector: '{active_date_link_selector}') が見つかりません。")

            except Exception as e_date_nav:
                print(f"ERROR: 日付ナビゲーションからの日付取得中にエラー: {e_date_nav}")
                traceback.print_exc() # エラー詳細を表示

            # もし上記の方法で日付が取得できなかった場合、レースIDから推定 (フォールバック)
            if race_common_info.get('RaceDate') is None: # RaceDate がまだ None の場合のみ
                print(f"WARN: ページから開催日を特定できませんでした。レースIDの先頭8桁から推定します (精度注意)。")
                if len(race_id) >= 8:
                    year, month, day = race_id[0:4], race_id[4:6], race_id[6:8]
                    race_common_info['RaceDate'] = f"{year}年{month}月{day}日"
                else:
                    print(f"ERROR: レースIDが短いため日付を推定できません: {race_id}")
            # === ▲▲▲ 正しい開催日の取得ロジックここまで ▲▲▲ ===


            # --- レースヘッダーからの情報取得 (日付以外) ---
            race_header_box_selector = "div.RaceList_NameBox" 
            race_header_element = soup.select_one(race_header_box_selector)

            if race_header_element:
                # レース名
                try:
                    race_name_tag = race_header_element.select_one("div.RaceList_Item02 > h1.RaceName")
                    if race_name_tag:
                        # HTML構造によっては .contents[0] がうまく機能しないことがあるので .get_text() を優先
                        race_common_info['RaceName'] = race_name_tag.get_text(strip=True)
                        # icon部分を除去する処理が必要ならここに追加 (例: spanタグを除去)
                        icon_in_racename = race_name_tag.select_one("span.Icon_GradeType")
                        if icon_in_racename:
                             race_common_info['RaceName'] = race_common_info['RaceName'].replace(icon_in_racename.get_text(strip=True), "").strip()
                except Exception as e: print(f"        警告: レース名の取得に失敗: {e}")

                # レース番号
                try:
                    race_num_tag = race_header_element.select_one("div.RaceList_Item01 > span.RaceNum")
                    if race_num_tag:
                        race_common_info['RaceNum'] = race_num_tag.get_text(strip=True).replace('R', '')
                except Exception as e: print(f"        警告: レース番号の取得に失敗: {e}")

                # RaceData01 (コース、距離、回り、天候、馬場)
                try:
                    race_data01_tag = race_header_element.select_one("div.RaceList_Item02 > div.RaceData01")
                    if race_data01_tag:
                        text_data01_full = race_data01_tag.get_text(separator=" ", strip=True)
                        print(f"DEBUG get_shutuba_table: RaceData01 full text for regex: '{text_data01_full}'")
                        
                        course_match = re.search(r"(芝|ダ|障)\s*(\d+)m\s*\(?\s*(左|右|直|障)\s*[ABCD内外障TR]*\s*\)?", text_data01_full) # 回りも柔軟に
                        if course_match:
                            race_common_info['CourseType'] = course_match.group(1)
                            race_common_info['Distance'] = int(course_match.group(2))
                            around_text = course_match.group(3)
                            if around_text in ['左', '右', '直']:
                                race_common_info['Around'] = around_text
                            elif '障' in around_text : # 障害の場合
                                race_common_info['Around'] = '障' # またはNone/N/A
                        else: # よりシンプルなパターンでのフォールバック
                            course_type_dist_match = re.search(r"(芝|ダ|障)\s*(\d+)m", text_data01_full)
                            if course_type_dist_match:
                                race_common_info['CourseType'] = course_type_dist_match.group(1)
                                race_common_info['Distance'] = int(course_type_dist_match.group(2))
                            # 回りのフォールバック (括弧内の最初の文字など)
                            around_simple_match = re.search(r"\((左|右|直)\)", text_data01_full)
                            if around_simple_match: race_common_info['Around'] = around_simple_match.group(1)
                            elif "(右" in text_data01_full: race_common_info['Around'] = '右'
                            elif "(左" in text_data01_full: race_common_info['Around'] = '左'

                        weather_match = re.search(r"天候\s*:\s*(\S+)", text_data01_full)
                        if weather_match: race_common_info['Weather'] = weather_match.group(1).replace('(','').replace(')','') # カッコ除去

                        track_cond_match = re.search(r"馬場\s*:\s*(\S+)", text_data01_full)
                        if track_cond_match: race_common_info['TrackCondition'] = track_cond_match.group(1).replace('(','').replace(')','') # カッコ除去
                except Exception as e: print(f"        警告: RaceData01 (コース等) の正規表現解析に失敗: {e}")

                # RaceData02 (競馬場名など) - 日付は上で取得済みなのでここでは主に競馬場名
                try:
                    race_data02_tag = race_header_element.select_one("div.RaceList_Item02 > div.RaceData02")
                    if race_data02_tag:
                        text_data02_full_for_track = race_data02_tag.get_text(separator=" ", strip=True)
                        track_name_match = re.search(r'\d+回\s*(\S+?)\s*\d+日目', text_data02_full_for_track) # 空白も許容
                        if track_name_match:
                            race_common_info['TrackName'] = track_name_match.group(1)
                        else: # フォールバック
                            race_data02_spans = race_data02_tag.select("span")
                            if len(race_data02_spans) > 1 and race_data02_spans[1].get_text(strip=True):
                                race_common_info['TrackName'] = race_data02_spans[1].get_text(strip=True)
                            elif race_data02_spans and race_data02_spans[0].get_text(strip=True): # 最初のspanが競馬場名の場合も
                                race_common_info['TrackName'] = race_data02_spans[0].get_text(strip=True)
                except Exception as e: print(f"        警告: RaceData02 (場所) の解析に失敗: {e}")
                
                print(f"      抽出したレース共通情報 (日付はナビゲーション優先): {race_common_info}")
            else:
                print(f"        警告: レースヘッダー ({race_header_box_selector}) が見つかりませんでした。")
                # ヘッダーがない場合でも、日付はナビゲーションまたはIDから取得試行済み
                # 他の情報はN/Aのままになる

            # --- 出走馬テーブルの取得 (変更なし) ---
            table_selector = '.Shutuba_Table.Shutuba_Past5_Table'
            table_tag = soup.select_one(table_selector) 

            if not table_tag:
                print(f"        警告: 出馬表テーブルが見つかりませんでした ({race_id})。")
                return {'race_details': race_common_info, 'horse_list': []} 

            horse_rows_selector = 'tbody > tr.HorseList'
            horse_rows = table_tag.select(horse_rows_selector)
            print(f"        出馬表テーブルから {len(horse_rows)} 頭のデータを処理します (Selector: '{horse_rows_selector}')")

            for i, row_tag in enumerate(horse_rows):
                row_data = {'race_id': race_id} # 各行の辞書を初期化
                cells = row_tag.select('td')
                try:
                    # 各セルのインデックスと対応するキーを定義 (netkeibaの構造に基づく)
                    # これは現在のユーザー様のコードとほぼ同じはずです
                    waku_index = 0; umaban_index = 1; horse_info_cell_index = 3; jockey_cell_index = 4
                    
                    if len(cells) > waku_index: row_data['Waku'] = cells[waku_index].get_text(strip=True)
                    if len(cells) > umaban_index: row_data['Umaban'] = cells[umaban_index].get_text(strip=True)
                    
                    if len(cells) > horse_info_cell_index:
                        horse_info_td = cells[horse_info_cell_index]
                        father_selector = 'div.Horse01'; horse_link_selector = 'div.Horse02 > a'; 
                        mf_selector = 'div.Horse04'; trainer_selector = 'div.Horse05 > a'; 
                        weight_selector = 'div.Weight' # 出馬表段階の馬体重(増減)
                        
                        row_data['father'] = horse_info_td.select_one(father_selector).get_text(strip=True) if horse_info_td.select_one(father_selector) else None
                        horse_link = horse_info_td.select_one(horse_link_selector)
                        row_data['HorseName'] = horse_link.get_text(strip=True) if horse_link else None
                        horse_url = horse_link.get('href') if horse_link else None
                        horse_id_match = re.search(r'/horse/(\d+)', str(horse_url))
                        row_data['horse_id'] = horse_id_match.group(1) if horse_id_match else None
                        
                        mf_div = horse_info_td.select_one(mf_selector)
                        if mf_div: 
                            mf_text = mf_div.get_text(strip=True)
                            row_data['mother_father'] = mf_text[1:-1] if mf_text.startswith('(') and mf_text.endswith(')') else mf_text
                        else: row_data['mother_father'] = None
                        
                        row_data['TrainerName'] = horse_info_td.select_one(trainer_selector).get_text(strip=True) if horse_info_td.select_one(trainer_selector) else None
                        
                        weight_div = horse_info_td.select_one(weight_selector)
                        row_data['WeightInfoShutuba'] = weight_div.get_text(strip=True).replace('\n','').replace('\r','') if weight_div else None
                        
                        odds_span = horse_info_td.select_one('div.Popular > span[id^="odds-"]') # 単勝オッズ
                        row_data['Odds'] = odds_span.get_text(strip=True) if odds_span else None
                        
                        # 人気も取得できれば (div.Popular のテキストなどから)
                        # popular_div = horse_info_td.select_one('div.Popular')
                        # if popular_div:
                        #    ninki_match = re.search(r'(\d+)人気', popular_div.get_text(strip=True))
                        #    if ninki_match: row_data['NinkiShutuba'] = ninki_match.group(1)

                    if len(cells) > jockey_cell_index:
                        jockey_td = cells[jockey_cell_index]
                        sexage_selector = 'span.Barei'; jockey_selector = 'a'; load_selector = 'span' 
                        row_data['SexAge'] = jockey_td.select_one(sexage_selector).get_text(strip=True) if jockey_td.select_one(sexage_selector) else None
                        row_data['JockeyName'] = jockey_td.select_one(jockey_selector).get_text(strip=True) if jockey_td.select_one(jockey_selector) else None
                        load_spans = jockey_td.select(load_selector) 
                        row_data['Load'] = load_spans[-1].get_text(strip=True) if load_spans else None # 最後のspanが斤量と仮定
                    
                    required_keys = ['race_id', 'Umaban', 'HorseName', 'horse_id'] # 必須キー
                    if all(key in row_data and pd.notna(row_data[key]) for key in required_keys):
                        horse_data_list.append(row_data)
                    else:
                        print(f"        WARN: Row {i+1} data is incomplete or missing required keys. Skipping row. Data: {row_data}")
                except Exception as e_row:
                    print(f"        ERROR: Error processing row {i+1} in get_shutuba_table for {race_id}. Error: {type(e_row).__name__}: {e_row}")
                    traceback.print_exc() # エラー詳細表示
        
        except TimeoutException:
            print(f"  Seleniumタイムアウトエラー (要素待機またはページロード): {url}")
            # タイムアウト時は、それまでに取得できた情報で返す
        except WebDriverException as e:
            print(f"  WebDriverエラー ({url}): {e}")
            traceback.print_exc()
        except Exception as e:
            print(f"  予期せぬエラー (get_shutuba_table) ({url}): {e}"); traceback.print_exc()
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass

        print(f"      出馬表データ取得完了: {len(horse_data_list)} 件の馬情報、レース共通情報が一部でも取得できたか: {any(v != 'N/A' and pd.notna(v) and v != '' for k, v in race_common_info.items() if k != 'race_id')}")
        return {'race_details': race_common_info, 'horse_list': horse_data_list}

    # --- データ整形用ヘルパー関数 (shutuba_past.html 対応版) ---
    def format_shutuba_data(self, shutuba_data_list_of_dicts, race_id):
        """get_shutuba_tableの結果(辞書のリスト)をDataFrameに整形"""
        if not shutuba_data_list_of_dicts:
            print(f"      情報: 整形対象の出馬表データがありません ({race_id})。")
            return None
        try:
            df = pd.DataFrame(shutuba_data_list_of_dicts)
            print(f"      INFO: DataFrame created from list of dicts. Shape: {df.shape}")
            # print(f"      DEBUG: Initial columns: {df.columns.tolist()}") # 初期列名確認

            # --- 必要な列が存在するか確認し、なければ作成 (Noneで埋める) ---
            expected_cols = ['race_id', 'Waku', 'Umaban', 'HorseName', 'horse_id',
                             'SexAge', 'Load', 'JockeyName', 'TrainerName',
                             'father', 'mother_father', 'WeightInfoShutuba', 'OddsShutuba', 'NinkiShutuba']
            for col in expected_cols:
                if col not in df.columns:
                    print(f"      WARN: Column '{col}' not found in initial DataFrame for {race_id}. Creating with None.")
                    df[col] = None # Noneで作成

            # --- 型変換と整形 ---
            df['race_id'] = df['race_id'].astype(str)
            df['Waku'] = pd.to_numeric(df['Waku'], errors='coerce')
            df['Umaban'] = pd.to_numeric(df['Umaban'], errors='coerce')
            df['HorseName'] = df['HorseName'].astype(str).fillna('')
            df['horse_id'] = df['horse_id'].astype(str).fillna('')
            df['Load'] = pd.to_numeric(df['Load'], errors='coerce')
            df['JockeyName'] = df['JockeyName'].astype(str).fillna('')
            df['TrainerName'] = df['TrainerName'].astype(str).fillna('')
            df['father'] = df['father'].astype(str).fillna('')
            df['mother_father'] = df['mother_father'].astype(str).fillna('')
            df['OddsShutuba'] = pd.to_numeric(df['OddsShutuba'], errors='coerce')
            df['NinkiShutuba'] = pd.to_numeric(df['NinkiShutuba'], errors='coerce')

            # WeightInfoShutuba から Weight と Diff を抽出
            if 'WeightInfoShutuba' in df.columns:
                 df['WeightInfo_str'] = df['WeightInfoShutuba'].astype(str).fillna('')
                 # 体重抽出
                 df['WeightShutuba'] = df['WeightInfo_str'].str.extract(r'(\d+)', expand=False)
                 df['WeightShutuba'] = pd.to_numeric(df['WeightShutuba'], errors='coerce')
                 # 増減抽出
                 df['WeightDiffShutuba'] = df['WeightInfo_str'].str.extract(r'\(([-+]?\d+)\)', expand=False)
                 df['WeightDiffShutuba'] = pd.to_numeric(df['WeightDiffShutuba'], errors='coerce')
                 df.drop(columns=['WeightInfoShutuba', 'WeightInfo_str'], inplace=True, errors='ignore')
            else:
                 df['WeightShutuba'] = None
                 df['WeightDiffShutuba'] = None

            # SexAge から Sex と Age を抽出
            if 'SexAge' in df.columns:
                 df['SexAge_str'] = df['SexAge'].astype(str).fillna('')
                 df['Sex'] = df['SexAge_str'].str[0]
                 df['Age'] = pd.to_numeric(df['SexAge_str'].str[1:], errors='coerce')
                 df.drop(columns=['SexAge', 'SexAge_str'], inplace=True, errors='ignore')
            else:
                 df['Sex'] = ''
                 df['Age'] = None

            print(f"      INFO: 出馬表DataFrameの整形完了。Shape: {df.shape}")
            # print(f"      DEBUG: Final columns: {df.columns.tolist()}")

            # --- 不要な列や期待しないデータ型の列があればここでドロップ ---
            # 例: df = df.drop(columns=['Mark'], errors='ignore')

            return df

        except Exception as e:
            print(f"      エラー: 出馬表DataFrameの整形中にエラー ({race_id}): {e}")
            traceback.print_exc()
        return None
           
    # --- データ整形用ヘルパー関数 (辞書のリストを受け取るように変更) ---
    def format_shutuba_data(self, shutuba_data_list_of_dicts, race_id):
        """get_shutuba_tableの結果(辞書のリスト)をDataFrameに整形"""
        if not shutuba_data_list_of_dicts:
            print(f"      情報: 整形対象の出馬表データがありません ({race_id})。")
            return None
        try:
            # 辞書のリストから直接 DataFrame を作成
            df = pd.DataFrame(shutuba_data_list_of_dicts)
            print(f"      INFO: DataFrame created from list of dicts. Shape: {df.shape}")

            # --- 必要な列が存在するか確認し、なければ作成 (空文字で埋める) ---
            expected_cols = ['race_id', 'Waku', 'Umaban', 'HorseName', 'horse_id',
                             'SexAge', 'Load', 'JockeyName', 'TrainerName',
                             'father', 'mother_father', 'OddsShutuba', 'NinkiShutuba']
            for col in expected_cols:
                if col not in df.columns:
                    print(f"      WARN: Column '{col}' not found in initial DataFrame for {race_id}. Creating with empty strings.")
                    df[col] = '' # 空の列を追加

            # --- 列の選択と並び替え ---
            # 必要に応じて列の順番を定義
            # output_cols = ['race_id', 'Waku', 'Umaban', ..., 'father', 'mother_father']
            # df = df[output_cols]

            # --- 型変換と整形 ---
            df['race_id'] = df['race_id'].astype(str)
            df['Waku'] = pd.to_numeric(df['Waku'], errors='coerce')
            df['Umaban'] = pd.to_numeric(df['Umaban'], errors='coerce')
            df['HorseName'] = df['HorseName'].astype(str).fillna('')
            df['horse_id'] = df['horse_id'].astype(str).fillna('')
            df['Load'] = pd.to_numeric(df['Load'], errors='coerce')
            df['JockeyName'] = df['JockeyName'].astype(str).fillna('')
            df['TrainerName'] = df['TrainerName'].astype(str).fillna('')
            df['father'] = df['father'].astype(str).fillna('')
            df['mother_father'] = df['mother_father'].astype(str).fillna('')
            df['OddsShutuba'] = pd.to_numeric(df['OddsShutuba'], errors='coerce')
            df['NinkiShutuba'] = pd.to_numeric(df['NinkiShutuba'], errors='coerce')

            # SexAge から Sex と Age を抽出
            if 'SexAge' in df.columns:
                 # 事前に文字列型にしておく
                 df['SexAge_str'] = df['SexAge'].astype(str).fillna('')
                 df['Sex'] = df['SexAge_str'].str[0]
                 # 年齢部分が数値でない場合も考慮
                 df['Age'] = pd.to_numeric(df['SexAge_str'].str[1:], errors='coerce')
                 df.drop(columns=['SexAge', 'SexAge_str'], inplace=True, errors='ignore') # 元の列は削除
            else:
                 df['Sex'] = ''
                 df['Age'] = None


            print(f"      INFO: 出馬表DataFrameの整形完了。Shape: {df.shape}")
            # print(f"      DEBUG: Final columns: {df.columns.tolist()}") # 列名確認

            return df

        except Exception as e:
            print(f"      エラー: 出馬表DataFrameの整形中にエラー ({race_id}): {e}")
            traceback.print_exc()
        return None

# --- 部品関数6: 馬詳細情報取得 (戦績整形機能追加版) ---
    def get_horse_details(self, horse_id):
        """馬の個別ページから詳細情報(プロフィール、血統、整形済み戦績)を取得して辞書で返す"""
        if not horse_id or not str(horse_id).isdigit():
            print(f"      警告: 無効な馬IDです: {horse_id}")
            return {'horse_id': horse_id, 'error': 'Invalid horse_id'}

        url = f'https://db.netkeiba.com/horse/{horse_id}/'
        print(f"      馬詳細取得試行: {url} (get_horse_details)")
        headers = {'User-Agent': self.USER_AGENT}
        horse_details = {'horse_id': horse_id} 

        try:
            time.sleep(0.5) # アクセス負荷軽減のための待機

            r = requests.get(url, headers=headers, timeout=self.REQUEST_TIMEOUT)
            r.raise_for_status()
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
                         # 主要な情報を抽出・格納 (キー名は英語推奨だが分かりやすさ優先)
                         if '生年月日' in header_text: horse_details['birthday'] = value_text
                         elif '調教師' in header_text: horse_details['trainer_prof'] = value_text
                         elif '馬主' in header_text: horse_details['owner_prof'] = value_text
                         elif '生産者' in header_text: horse_details['breeder'] = value_text
                         elif '産地' in header_text: horse_details['birthplace'] = value_text
                         elif 'セリ取引価格' in header_text: horse_details['market_price'] = value_text
                         elif '獲得賞金' in header_text:
                            # 賞金から「万円」を除去し数値化
                            prize_match = re.search(r'([\d,]+)万円', value_text)
                            if prize_match:
                                horse_details['total_prize'] = pd.to_numeric(prize_match.group(1).replace(',', ''), errors='coerce')
                            else:
                                horse_details['total_prize'] = pd.to_numeric(value_text.replace(',', '').replace('万円',''), errors='coerce')

                         elif '通算成績' in header_text: horse_details['total_成績'] = value_text
                         elif '主な勝鞍' in header_text: horse_details['main_wins'] = value_text
            else:
                print(f"      警告: プロフィールテーブルが見つかりません ({horse_id})")
                if 'error' not in horse_details: horse_details['error'] = ''
                horse_details['error'] += ' Profile table not found'

            # --- 血統情報抽出 ---
            blood_table = soup.select_one('table.blood_table')
            if blood_table:
                father_tag = blood_table.select_one('tr:nth-of-type(1) td:nth-of-type(1) a')
                horse_details['father'] = father_tag.get_text(strip=True) if father_tag else None
                mother_tag = blood_table.select_one('tr:nth-of-type(3) td:nth-of-type(1) a')
                horse_details['mother'] = mother_tag.get_text(strip=True) if mother_tag else None
                mother_father_tag = blood_table.select_one('tr:nth-of-type(3) td:nth-of-type(2) a')
                horse_details['mother_father'] = mother_father_tag.get_text(strip=True) if mother_father_tag else None
            else:
                print(f"      警告: 血統テーブル (blood_table) が見つかりません ({horse_id})")
                horse_details['father'] = None
                horse_details['mother'] = None
                horse_details['mother_father'] = None
                if 'error' not in horse_details: horse_details['error'] = ''
                horse_details['error'] += ' Blood table not found'

            # === ここから戦績テーブルの取得と整形ロジック ===
            race_results_list = []
            results_table = soup.select_one('table.db_h_race_results')

            if results_table:
                rows = results_table.select('tbody tr')
                if not rows:
                     rows = results_table.select('tr')[1:] # ヘッダー行スキップ

                print(f"      戦績テーブルから {len(rows)} 行のデータを処理します...")

                for i, row in enumerate(rows):
                    cells = row.find_all('td')
                    # 列数は変動する可能性があるため、インデックスアクセス前に長さを確認
                    # 主要な列だけ取得し、インデックスは固定と仮定（要調整の可能性あり）
                    if len(cells) < 23: # 最低限必要な列数 (上がりまで) を仮定
                        print(f"        警告: 行 {i+1} のセル数が不足 ({len(cells)} < 23)。スキップします。")
                        continue

                    # --- 各セルの情報を取得 ---
                    date_str = cells[0].get_text(strip=True)
                    kaisai_str = cells[1].get_text(strip=True)
                    weather_str = cells[2].get_text(strip=True)
                    race_num_str = cells[3].get_text(strip=True)
                    race_name_str = cells[4].get_text(strip=True)
                    num_horses_str = cells[6].get_text(strip=True)
                    waku_str = cells[7].get_text(strip=True)
                    umaban_str = cells[8].get_text(strip=True)
                    odds_str = cells[9].get_text(strip=True)
                    ninki_str = cells[10].get_text(strip=True)
                    rank_str = cells[11].get_text(strip=True)
                    jockey_str = cells[12].get_text(strip=True)
                    load_str = cells[13].get_text(strip=True)
                    distance_str = cells[14].get_text(strip=True)
                    baba_str = cells[15].get_text(strip=True)
                    time_str = cells[17].get_text(strip=True)
                    diff_str = cells[18].get_text(strip=True)
                    passage_str = cells[20].get_text(strip=True)
                    pace_str = cells[21].get_text(strip=True) # ペースは分割が必要かも
                    agari_str = cells[22].get_text(strip=True)
                    # 馬体重と賞金は列が存在しない場合もあるため、lenでチェック
                    weight_str = cells[23].get_text(strip=True) if len(cells) > 23 else None
                    winner_second_str = cells[26].get_text(strip=True) if len(cells) > 26 else None
                    prize_money_str = cells[27].get_text(strip=True) if len(cells) > 27 else None

                    race_result = {}
                    try:
                        race_result['date'] = pd.to_datetime(date_str, format='%Y/%m/%d')
                    except ValueError:
                        race_result['date'] = None

                    race_result['kaisai_info'] = kaisai_str
                    kaisai_match = re.match(r'(\d+)?(\D+)(\d+)?', kaisai_str) if kaisai_str else None
                    if kaisai_match:
                        race_result['place'] = kaisai_match.group(2)
                        race_result['kaisuu'] = int(kaisai_match.group(1)) if kaisai_match.group(1) else None
                        race_result['nichisuu'] = int(kaisai_match.group(3)) if kaisai_match.group(3) else None
                    else:
                         race_result['place'] = kaisai_str
                         race_result['kaisuu'] = None
                         race_result['nichisuu'] = None

                    race_result['weather'] = weather_str
                    race_result['race_num'] = int(race_num_str) if race_num_str and race_num_str.isdigit() else None
                    race_result['race_name'] = race_name_str
                    race_result['num_horses'] = int(num_horses_str) if num_horses_str and num_horses_str.isdigit() else None
                    race_result['waku'] = int(waku_str) if waku_str and waku_str.isdigit() else None
                    race_result['umaban'] = int(umaban_str) if umaban_str and umaban_str.isdigit() else None
                    race_result['odds'] = pd.to_numeric(odds_str, errors='coerce')
                    race_result['ninki'] = pd.to_numeric(ninki_str, errors='coerce')

                    race_result['rank_str'] = rank_str
                    race_result['rank'] = pd.to_numeric(rank_str, errors='coerce')

                    race_result['jockey'] = jockey_str
                    race_result['load'] = pd.to_numeric(load_str, errors='coerce')

                    race_result['distance_str'] = distance_str
                    if distance_str:
                        course_type_match = re.search(r'([芝ダ障])', distance_str)
                        distance_val_match = re.search(r'(\d+)', distance_str)
                        race_result['course_type'] = course_type_match.group(1) if course_type_match else None
                        race_result['distance'] = int(distance_val_match.group(1)) if distance_val_match else None
                    else:
                        race_result['course_type'] = None
                        race_result['distance'] = None

                    race_result['baba'] = baba_str
                    race_result['time_str'] = time_str
                    try:
                        if time_str and ':' in time_str:
                            parts = time_str.split(':')
                            minutes = int(parts[0])
                            seconds = float(parts[1])
                            race_result['time_sec'] = minutes * 60 + seconds
                        elif time_str:
                             race_result['time_sec'] = float(time_str)
                        else:
                             race_result['time_sec'] = None
                    except ValueError:
                         race_result['time_sec'] = None

                    race_result['diff_str'] = diff_str
                    race_result['diff'] = pd.to_numeric(diff_str, errors='coerce')

                    race_result['passage'] = passage_str
                    race_result['pace'] = pace_str
                    race_result['agari'] = pd.to_numeric(agari_str, errors='coerce')

                    race_result['weight_str'] = weight_str
                    weight_match = re.match(r'(\d+)\(([-+]?\d+)\)', weight_str) if weight_str else None
                    if weight_match:
                        race_result['weight_val'] = int(weight_match.group(1))
                        race_result['weight_diff'] = int(weight_match.group(2))
                    else:
                        race_result['weight_val'] = pd.to_numeric(weight_str, errors='coerce') # 体重のみの場合
                        race_result['weight_diff'] = None

                    race_result['winner_second'] = winner_second_str

                    race_result['prize_money_str'] = prize_money_str
                    try:
                         prize_num_str = prize_money_str.replace(',', '') if prize_money_str else '0'
                         race_result['prize_money'] = float(prize_num_str) if prize_num_str else 0.0
                    except ValueError:
                         race_result['prize_money'] = 0.0

                    race_results_list.append(race_result)

                # --- 地方転入馬関連情報とJRA戦績の追加 ---
                if race_results_list: # 1走でも過去走があれば
                    first_past_race = race_results_list[0] # 最新の過去走 (日付降順ソート済みが前提)
                    prev_place = first_past_race.get('place')
                    if prev_place and prev_place not in self.JRA_TRACKS:
                        horse_details['is_transfer_from_local_1ago'] = 1
                        horse_details['prev_race_track_type_1ago'] = 'NAR' # より具体的に分類も可能
                    elif prev_place:
                        horse_details['is_transfer_from_local_1ago'] = 0
                        horse_details['prev_race_track_type_1ago'] = 'JRA'
                    else:
                        horse_details['is_transfer_from_local_1ago'] = 0 # 不明時は中央扱い
                        horse_details['prev_race_track_type_1ago'] = 'Unknown'
                    
                    jra_results_for_horse = [r for r in race_results_list if isinstance(r, dict) and r.get('place') in self.JRA_TRACKS]
                    horse_details['jra_race_results'] = jra_results_for_horse # JRA限定の戦績リスト
                    horse_details['num_jra_starts'] = len(jra_results_for_horse)
                else: # 過去走データがない場合
                    horse_details['is_transfer_from_local_1ago'] = 0 # 新馬などは中央扱い
                    horse_details['prev_race_track_type_1ago'] = 'NoPastData'
                    horse_details['jra_race_results'] = []
                    horse_details['num_jra_starts'] = 0

                horse_details['race_results'] = race_results_list # 全戦績も保持
                print(f"      戦績テーブル取得・整形成功: {len(race_results_list)} レース分 (get_horse_details)")
            else:
                print(f"      警告: 戦績テーブル (db_h_race_results) が見つかりません ({horse_id})")
                horse_details['race_results'] = []
                horse_details['is_transfer_from_local_1ago'] = 0
                horse_details['prev_race_track_type_1ago'] = 'NoPastData'
                horse_details['jra_race_results'] = []
                horse_details['num_jra_starts'] = 0
                if 'error' not in horse_details: horse_details['error'] = ''
                horse_details['error'] += ' Race results table not found'

        except requests.exceptions.Timeout:
            print(f"      タイムアウトエラー (馬詳細): {url}")
            horse_details['error'] = 'Timeout'
        except requests.exceptions.RequestException as e:
            if e.response is not None and e.response.status_code == 404:
                 print(f"      情報: 馬ページが見つかりません (404): {url}")
                 horse_details['error'] = 'Not Found (404)'
            else:
                print(f"      ページ取得エラー (馬詳細) ({url}): {e}")
                horse_details['error'] = f'RequestException: {e}'
        except Exception as e:
            print(f"      ★★★★★ ERROR in get_horse_details ({horse_id}): {e}")
            traceback.print_exc()
            horse_details['error'] = f'Unexpected Error: {e}'

        return horse_details
  
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # ★ STEP 1.1：ここから騎手データ集計関数を追加 ★
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    def _calculate_jockey_stats(self):
        """
        読み込んだデータ全体から、騎手ごとに、
        競馬場・コース種別・距離別の成績（複勝率など）を集計し、
        クラス変数 self.jockey_stats に格納する。
        """
        print("騎手別のコース成績データを計算中...")
        self.update_status("騎手成績データ計算中...")
        start_calc_time = time.time()

        self.jockey_stats = {} # 初期化

        if self.combined_data is None or self.combined_data.empty:
            print("警告: 騎手統計計算のためのデータがありません。")
            self.update_status("騎手成績計算不可 (データなし)")
            return

        required_cols = ['JockeyName', 'track_name', 'course_type', 'distance', 'Rank']
        if not all(col in self.combined_data.columns for col in required_cols):
             missing = [c for c in required_cols if c not in self.combined_data.columns]
             print(f"警告: 騎手統計計算に必要な列が不足しています: {missing}")
             self.update_status(f"騎手成績計算不可 (列不足: {missing})")
             return

        df = self.combined_data.copy()

        # データ前処理
        df.dropna(subset=required_cols, inplace=True)
        df = df[df['JockeyName'] != '']
        df['JockeyName'] = df['JockeyName'].astype(str).str.strip()
        df['track_name'] = df['track_name'].astype(str).str.strip()
        df['course_type'] = df['course_type'].astype(str).str.strip()
        df['distance_numeric'] = pd.to_numeric(df['distance'], errors='coerce')
        df['Rank_numeric'] = pd.to_numeric(df['Rank'], errors='coerce')
        df.dropna(subset=['distance_numeric', 'Rank_numeric'], inplace=True)
        df['distance_int'] = df['distance_numeric'].astype(int)
        df['Rank_int'] = df['Rank_numeric'].astype(int)

        if df.empty:
            print("警告: 騎手統計計算の対象となる有効なデータがありません。")
            return

        # 騎手、競馬場、コース、距離でグループ化し、成績を集計
        try:
            stats = df.groupby(['JockeyName', 'track_name', 'course_type', 'distance_int']).agg(
                Runs=('Rank_int', 'size'),
                Place3=('Rank_int', lambda x: (x <= 3).sum())
            ).reset_index()

            stats['Place3Rate'] = stats.apply(lambda r: r['Place3'] / r['Runs'] if r['Runs'] > 0 else 0, axis=1)

            # 辞書形式で格納 { 騎手名: { (競馬場, コース, 距離): {'Runs': N, 'Place3Rate': R}, ... }, ... }
            jockey_stats_dict = {}
            for _, row in stats.iterrows():
                jockey = row['JockeyName']
                track = row['track_name']
                course = row['course_type']
                distance = row['distance_int']
                runs = row['Runs']
                place3_rate = row['Place3Rate']

                if jockey not in jockey_stats_dict:
                    jockey_stats_dict[jockey] = {}
                key = (track, course, distance)
                
                # 信頼性のため、最低騎乗回数を設ける (例: 5回以上)
                if runs >= 5:
                    jockey_stats_dict[jockey][key] = {'Runs': int(runs), 'Place3Rate': place3_rate}

            self.jockey_stats = jockey_stats_dict

            end_calc_time = time.time()
            print(f"騎手別成績データの計算完了。{len(self.jockey_stats)} 人の騎手データを生成。({end_calc_time - start_calc_time:.2f}秒)")
            self.update_status("騎手成績データ準備完了")

        except Exception as e:
            print(f"!!! Error during jockey stats calculation: {e}")
            traceback.print_exc()
            self.jockey_stats = {}
            self.update_status("エラー: 騎手成績計算失敗")

    # --- (中略) --- _calculate_sire_stats, _calculate_gate_stats などは変更なし ---
    
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # ★ STEP 1.3：ここから特徴量計算関数を修正 ★
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    def calculate_original_index(self, horse_details, race_conditions):
        """
        馬の詳細情報とレース条件から、予測に使用する特徴量を計算・収集して返す。
        【騎手・馬のコース適性特徴量を追加】
        """
        features = {
            'Umaban': np.nan, 'HorseName': '', 'Sex': np.nan, 'Age': np.nan,
            'Load': np.nan, 'JockeyName': '', 'TrainerName': '',
            'father': '', 'mother_father': '', 'horse_id': None,
            '近走1走前着順': np.nan, '近走2走前着順': np.nan, '近走3走前着順': np.nan,
            '着差_1走前': np.nan, '着差_2走前': np.nan, '着差_3走前': np.nan,
            '上がり3F_1走前': np.nan, '上がり3F_2走前': np.nan, '上がり3F_3走前': np.nan,
            'タイム偏差値': np.nan, '同コース距離最速補正': np.nan,
            '基準タイム差': np.nan, '基準タイム比': np.nan,
            '父同条件複勝率': 0.0, '父同条件N数': 0,
            '母父同条件複勝率': 0.0, '母父同条件N数': 0,
            '斤量絶対値': np.nan, '斤量前走差': np.nan,
            '馬体重絶対値': np.nan, '馬体重前走差': np.nan,
            '枠番': np.nan, '枠番_複勝率': 0.0, '枠番_N数': 0,
            '負担率': np.nan, '距離区分': None, 'race_class_level': np.nan,
            'time_dev_x_race_level': np.nan,
            'is_transfer_from_local_1ago': 0, 'prev_race_track_type_1ago': 'Unknown',
            'num_jra_starts': 0, 'jra_rank_1ago': np.nan,
            'OddsShutuba': np.nan, 'NinkiShutuba': np.nan,
            # ★★★ 新しい特徴量を追加 ★★★
            '騎手コース複勝率': 0.0, '騎手コースN数': 0,
            '馬コース複勝率': 0.0, '馬コースN数': 0,
            'error': None
        }

        if not isinstance(horse_details, dict):
            features['error'] = "horse_details is not a dictionary"
            return 0.0, features

        # 基本情報
        features['horse_id'] = str(horse_details.get('horse_id')).split('.')[0] if pd.notna(horse_details.get('horse_id')) else None
        features['Umaban'] = pd.to_numeric(horse_details.get('Umaban', horse_details.get('馬番')), errors='coerce')
        sex_age_str = str(horse_details.get('SexAge', horse_details.get('性齢', ''))).strip()
        if sex_age_str and re.match(r'([牡牝セせんセン騙])(\d+)', sex_age_str):
            match = re.match(r'([牡牝セせんセン騙])(\d+)', sex_age_str)
            sex_map = {'牡': 0, '牝': 1, 'セ': 2, 'せ': 2, 'ん': 2, 'セン': 2, '騙': 2}
            features['Sex'] = sex_map.get(match.group(1), np.nan)
            features['Age'] = pd.to_numeric(match.group(2), errors='coerce')
        features['Load'] = pd.to_numeric(horse_details.get('Load', horse_details.get('斤量')), errors='coerce')
        features['JockeyName'] = str(horse_details.get('JockeyName', '')) # ★騎手名を取得
        features['father'] = str(horse_details.get('father', ''))
        features['mother_father'] = str(horse_details.get('mother_father', ''))

        # レース条件
        target_course = race_conditions.get('CourseType', race_conditions.get('course_type'))
        target_distance_raw = race_conditions.get('Distance', race_conditions.get('distance'))
        target_track = race_conditions.get('TrackName', race_conditions.get('track_name'))
        target_distance_float = float(pd.to_numeric(target_distance_raw, errors='coerce')) if pd.notna(target_distance_raw) else None

        if target_distance_float is not None:
            bins = [0, 1400, 1800, 2200, 2600, float('inf')]
            labels = ['1400m以下', '1401-1800m', '1801-2200m', '2201-2600m', '2601m以上']
            features['距離区分'] = str(pd.cut([target_distance_float], bins=bins, labels=labels, right=True, include_lowest=True)[0])
        
        race_results_for_calc = horse_details.get('race_results', [])
        if not isinstance(race_results_for_calc, list): race_results_for_calc = []
        
        features['race_class_level'] = self._get_race_class_level(str(race_conditions.get('RaceName', '')))
        
        try:
            # 近走情報など...
            for i in range(3):
                if len(race_results_for_calc) > i and isinstance(race_results_for_calc[i], dict):
                    features[f'近走{i+1}走前着順'] = pd.to_numeric(race_results_for_calc[i].get('rank'), errors='coerce')
                    features[f'着差_{i+1}走前'] = pd.to_numeric(race_results_for_calc[i].get('diff'), errors='coerce')
                    features[f'上がり3F_{i+1}走前'] = pd.to_numeric(race_results_for_calc[i].get('agari'), errors='coerce')

            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
            # ★ ここから新しい特徴量の計算ロジックを追加 ★
            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
            
            # === 1. 騎手のコース適性 ===
            jockey_name_calc = features.get('JockeyName')
            if (jockey_name_calc and target_track and target_course and pd.notna(target_distance_float) and
                hasattr(self, 'jockey_stats') and self.jockey_stats):
                
                jockey_data = self.jockey_stats.get(str(jockey_name_calc), {})
                # 完全一致するキーを探す
                cond_key = (str(target_track), str(target_course), int(target_distance_float))
                
                if cond_key in jockey_data:
                    stats = jockey_data[cond_key]
                    features['騎手コース複勝率'] = round(stats.get('Place3Rate', 0.0), 3)
                    features['騎手コースN数'] = int(stats.get('Runs', 0))

            # === 2. 馬自身のコース適性 ===
            horse_course_runs = 0
            horse_course_place3 = 0
            if race_results_for_calc and target_track and target_course and pd.notna(target_distance_float):
                for past_race in race_results_for_calc:
                    if isinstance(past_race, dict):
                        # 過去レースの条件を取得
                        past_track = past_race.get('place')
                        past_course = past_race.get('course_type')
                        past_dist = pd.to_numeric(past_race.get('distance'), errors='coerce')
                        
                        # 今回のレース条件と一致するかチェック
                        if (str(past_track) == str(target_track) and
                            str(past_course) == str(target_course) and
                            past_dist == target_distance_float):
                            
                            horse_course_runs += 1
                            rank = pd.to_numeric(past_race.get('rank'), errors='coerce')
                            if pd.notna(rank) and rank <= 3:
                                horse_course_place3 += 1
            
            features['馬コースN数'] = horse_course_runs
            if horse_course_runs > 0:
                features['馬コース複勝率'] = round(horse_course_place3 / horse_course_runs, 3)

        except Exception as e_main_calc:
            print(f"!!! ERROR: 特徴量計算メインブロックでエラー: {e_main_calc}")
            traceback.print_exc()
            features['error'] = f"CalcError: {type(e_main_calc).__name__}"

        # --- 最終的な型担保とログ出力 ---
        final_feature_log_display = {}
        for f_key_disp, f_val_disp in features.items():
            # Sex, 距離区分, prev_race_track_type_1ago はカテゴリカルなのでそのまま
            if f_key_disp not in ['HorseName', 'JockeyName', 'TrainerName', 'father', 'mother_father', 'horse_id', 
                                  '距離区分', 'prev_race_track_type_1ago', 'error', 'Sex']:
                if not isinstance(f_val_disp, (int, float, np.integer, np.floating)) and pd.notna(f_val_disp):
                    # print(f"WARN ({horse_id_for_log}): 特徴量 '{f_key_disp}' が最終的に非数値: {f_val_disp} (型: {type(f_val_disp)})。np.nan にします。")
                    features[f_key_disp] = np.nan # モデル学習のため数値以外はNaNに
            final_feature_log_display[f_key_disp] = features[f_key_disp]

        print(f"--- 特徴量計算結果 (馬番 {umaban_for_log_debug}, horse_id {horse_id_for_log}) ---")
        for k_log, v_log in final_feature_log_display.items():
            if pd.isna(v_log) or (isinstance(v_log, float) and np.isnan(v_log)):
                 print(f"  features['{k_log}']: nan")
            elif isinstance(v_log, float):
                 print(f"  features['{k_log}']: {v_log:.3f}")
            else:
                 print(f"  features['{k_log}']: {v_log}")
        print("--------------------------------------------------")

        return 0.0, features

    def _calculate_course_time_stats(self):    
        """
        読み込んだデータ全体から、競馬場・コース種別・距離ごとの
        馬場補正済み走破タイムの平均と標準偏差を計算し、クラス変数に格納する。
        """
        print("競馬場・コース・距離別のタイム統計データ（平均・標準偏差）を計算中...")
        self.update_status("タイム統計データ計算中...")
        start_calc_time = time.time() # time.time() を使う (timeモジュールをインポート済みと仮定)

        self.course_time_stats = {} # 初期化

        if self.combined_data is None or self.combined_data.empty:
            print("警告: タイム統計計算のためのデータがありません。")
            self.update_status("タイム統計計算不可 (データなし)")
            return

        # === "競馬場名" 列の特定 ===
        actual_track_name_col = None
        possible_track_name_cols = ['track_name', '開催場所', '競馬場'] # CSVの列名に合わせて調整
        for col_name in possible_track_name_cols:
            if col_name in self.combined_data.columns:
                actual_track_name_col = col_name
                print(f"INFO: _calculate_course_time_stats - 使用する競馬場名の列: '{actual_track_name_col}'")
                break
        
        if actual_track_name_col is None:
            print(f"CRITICAL ERROR: _calculate_course_time_stats - 競馬場名に相当する列が見つかりません。候補: {possible_track_name_cols}")
            print(f"  combined_dataの列名: {self.combined_data.columns.tolist()}")
            self.update_status("エラー: タイム統計計算失敗 (競馬場名列なし)")
            return
        # === "競馬場名" 列の特定ここまで ===

        # 必要な列を定義 (actual_track_name_col を使用)
        required_cols = [actual_track_name_col, 'course_type', 'distance', 'track_condition', 'Time', 'Rank']
        if not all(col in self.combined_data.columns for col in required_cols):
            missing = [c for c in required_cols if c not in self.combined_data.columns]
            print(f"警告: タイム統計計算に必要な他の列が不足しています: {missing}")
            print(f"  combined_dataの列名: {self.combined_data.columns.tolist()}")
            self.update_status(f"タイム統計計算不可 (列不足: {missing})")
            return

        df = self.combined_data[required_cols].copy()
        # df 内の競馬場名の列名を 'track_name' に統一
        df.rename(columns={actual_track_name_col: 'track_name'}, inplace=True)

        # === Time文字列からtime_secを計算する処理 ===
        def time_str_to_sec(time_str):
            try:
                if isinstance(time_str, (int, float)): return float(time_str)
                if pd.isna(time_str) or not isinstance(time_str, str): return None
                parts = time_str.split(':')
                if len(parts) == 2: return int(parts[0]) * 60 + float(parts[1])
                elif len(parts) == 1: return float(parts[0])
                else: return None
            except ValueError: return None
        df['time_sec_numeric'] = df['Time'].apply(time_str_to_sec)
        # === time_sec計算 ここまで ===

        # --- データ型変換と欠損値処理 ---
        df.dropna(subset=['time_sec_numeric', 'track_condition', 'course_type', 'distance', 'Rank', 'track_name'], inplace=True)
        df['distance_numeric'] = pd.to_numeric(df['distance'], errors='coerce')
        df['Rank_numeric'] = pd.to_numeric(df['Rank'], errors='coerce')
        df.dropna(subset=['distance_numeric', 'Rank_numeric'], inplace=True) # 数値変換後のNaNも除去
        
        # astype(int) の前に NaN がないことを保証する
        if df['distance_numeric'].isnull().any() or df['Rank_numeric'].isnull().any():
            print("WARN: distance_numeric または Rank_numeric にNaNが含まれるため、int変換をスキップまたはエラーの可能性があります。")
            # 必要であればここでさらにNaN行を除去するか、エラー処理
            df.dropna(subset=['distance_numeric', 'Rank_numeric'], inplace=True)


        df['distance_numeric'] = df['distance_numeric'].astype(int)
        df['Rank_numeric'] = df['Rank_numeric'].astype(int)
        df['track_name'] = df['track_name'].astype(str).str.strip()
        df['course_type'] = df['course_type'].astype(str).str.strip()
        df['baba'] = df['track_condition'].astype(str).str.strip()
        # ---------------------------------

        # --- 馬場補正タイムを計算 ---
        baba_hosei = {
            '芝': {'良': 0.0, '稍重': 0.5, '重': 1.0, '不良': 1.5},
            'ダ': {'良': 0.0, '稍重': -0.3, '重': -0.8, '不良': -1.3}
        }
        def get_hosei(row):
            course = row['course_type']; baba = row['baba']
            return baba_hosei.get(course, {}).get(baba, 0.0)
        df['hosei_value'] = df.apply(get_hosei, axis=1)
        df['corrected_time_sec'] = df['time_sec_numeric'] - df['hosei_value']
        # ----------------------------

        # --- 異常なタイムを除外 ---
        df_filtered = df[df['Rank_numeric'] <= 5] # 上位5着までを対象
        print(f"タイム統計計算: {len(df)}行からRank<=5の{len(df_filtered)}行を対象とします。")
        # --------------------------

        if df_filtered.empty:
            print("警告: タイム統計計算の対象となるデータがありません (フィルター後)。")
            self.update_status("タイム統計計算不可 (対象データなし)")
            return

        # --- 競馬場、コース種別、距離でグループ化し統計計算 ---
        try:
            if 'track_name' not in df_filtered.columns:
                print("CRITICAL ERROR: _calculate_course_time_stats - 'track_name' column is missing in df_filtered before groupby.")
                self.update_status("エラー: タイム統計計算失敗 (track_name列なし)")
                return

            stats = df_filtered.groupby(['track_name', 'course_type', 'distance_numeric'])['corrected_time_sec'].agg(
                mean='mean', std='std', count='size'
            ).reset_index()
            
            stats['std_revised'] = stats.apply(
                lambda x: x['std'] if pd.notna(x['std']) and x['std'] > 0 and x['count'] >= 5 else np.nan,
                axis=1
            )

            for _, row in stats.iterrows():
                key = (str(row['track_name']), str(row['course_type']), int(row['distance_numeric']))
                self.course_time_stats[key] = {
                    'mean': row['mean'] if pd.notna(row['mean']) else np.nan,
                    'std': row['std_revised'],
                    'count': int(row['count'])
                }

            end_calc_time = time.time()
            print(f"タイム統計データの計算完了。{len(self.course_time_stats)} 件の(競馬場・コース・距離)別データを生成。({end_calc_time - start_calc_time:.2f}秒)")
            
            # === ▼▼▼ デバッグログ追加 ▼▼▼ ===
            print(f"--- DEBUG: _calculate_course_time_stats 結果の一部 (上位5件と主要条件) ---")
            preview_count = 0
            specific_keys_to_check = [
                ('東京', '芝', 1600),
                ('中山', '芝', 2500),
                ('京都', 'ダ', 1200),
                ('東京', 'ダ', 1400),
                # ユーザー様のデータに存在する可能性のある他の条件も追加すると良いでしょう
                # 例: ('新潟', '障', 3290) # ログで見た障害レースの条件
            ]
            displayed_specific_keys = set()

            for k, v in self.course_time_stats.items():
                if preview_count < 5:
                    print(f"  Key: {k}, Value: {v}")
                    preview_count += 1
                    if k in specific_keys_to_check:
                        displayed_specific_keys.add(k)
                elif k in specific_keys_to_check and k not in displayed_specific_keys:
                    print(f"  Key (Specific): {k}, Value: {v}")
                    displayed_specific_keys.add(k)
                
                # 全ての特定キーを表示し、かつ最初の5件も表示したらループを抜ける
                if preview_count >=5 and len(displayed_specific_keys) >= len(specific_keys_to_check):
                    all_specific_keys_found_or_checked = True
                    for sp_key_check in specific_keys_to_check:
                        if sp_key_check not in displayed_specific_keys and sp_key_check in self.course_time_stats:
                             all_specific_keys_found_or_checked = False # まだ表示していない特定キーがある
                             break
                    if all_specific_keys_found_or_checked:
                        break
            
            # ループ後に、まだ表示されていない特定キーがあれば表示 (存在確認も兼ねて)
            for sp_key in specific_keys_to_check:
                if sp_key not in displayed_specific_keys:
                    if sp_key in self.course_time_stats:
                        print(f"  Key (Specific - Final Check): {sp_key}, Value: {self.course_time_stats[sp_key]}")
                    else:
                        print(f"  Key (Specific - Not Found in stats): {sp_key} はcourse_time_statsに存在しません。")

            if not self.course_time_stats:
                print("  self.course_time_stats は空です。")
            print(f"-------------------------------------------------------------------------------")
            # === ▲▲▲ デバッグログ追加ここまで ▲▲▲ ===

            self.update_status("タイム統計データ準備完了")

        except Exception as e:
            print(f"!!! Error during time stats calculation (in _calculate_course_time_stats): {e}")
            traceback.print_exc()
            self.course_time_stats = {}
            self.update_status("エラー: タイム統計計算失敗")
    
    # --- 血統指数用の種牡馬成績集計メソッド (新規追加) ---
    def _calculate_sire_stats(self, sire_column='father'): # 父(father) または 母父(mother_father) を指定
        """
        読み込んだデータ全体から、指定された種牡馬列ごとに、
        コース種別・距離区分別の産駒成績（複勝率など）を集計し、クラス変数に格納する。
        """
        stats_attr_name = f"{sire_column}_stats" # 格納するクラス変数名 (例: self.father_stats)
        print(f"{sire_column} ごとの産駒成績データを計算中...")
        self.update_status(f"{sire_column} 成績データ計算中...")
        start_calc_time = time.time()

        # 計算結果を格納するクラス変数を初期化
        setattr(self, stats_attr_name, {}) # 例: self.father_stats = {}

        if self.combined_data is None or self.combined_data.empty:
            print(f"警告: {stats_attr_name} 計算のためのデータがありません。")
            self.update_status(f"{sire_column} 成績計算不可 (データなし)")
            return

        # 必要な列が存在するか確認
        required_cols = [sire_column, 'course_type', 'distance', 'Rank']
        if not all(col in self.combined_data.columns for col in required_cols):
             missing = [c for c in required_cols if c not in self.combined_data.columns]
             print(f"警告: {stats_attr_name} 計算に必要な列が不足しています: {missing}")
             self.update_status(f"{sire_column} 成績計算不可 (列不足: {missing})")
             return

        df = self.combined_data.copy()

        # --- データ前処理 ---
        df[sire_column] = df[sire_column].fillna('Unknown').astype(str).str.strip() # 種牡馬名を文字列化、欠損は'Unknown'
        df['course_type'] = df['course_type'].astype(str).str.strip()
        df['distance_numeric'] = pd.to_numeric(df['distance'], errors='coerce')
        df['Rank_numeric'] = pd.to_numeric(df['Rank'], errors='coerce')
        df.dropna(subset=[sire_column, 'course_type', 'distance_numeric', 'Rank_numeric'], inplace=True)
        df = df[df[sire_column] != ''] # 空の種牡馬名を除外
        df['distance_numeric'] = df['distance_numeric'].astype(int)
        df['Rank_numeric'] = df['Rank_numeric'].astype(int)
        # --------------------

        # --- 距離区分を作成 ---
        bins = [0, 1400, 1800, 2200, 2600, float('inf')]
        labels = ['1400m以下', '1401-1800m', '1801-2200m', '2201-2600m', '2601m以上']
        df['DistanceGroup'] = pd.cut(df['distance_numeric'], bins=bins, labels=labels, right=True)
        # --------------------

        # --- 種牡馬、コース種別、距離区分でグループ化し、成績を集計 ---
        try:
            # observed=False にしないと、データがない組み合わせは結果に出てこない
            stats = df.groupby([sire_column, 'course_type', 'DistanceGroup'], observed=False).agg(
                Runs=('Rank_numeric', 'size'),         # 出走回数
                Place3=('Rank_numeric', lambda x: (x <= 3).sum()) # 3着内回数
            ).reset_index()

            # 複勝率を計算
            stats['Place3Rate'] = stats.apply(lambda r: r['Place3'] / r['Runs'] if r['Runs'] > 0 else 0, axis=1)

            # 結果を辞書形式で格納 { 種牡馬名: { (コース, 距離区分): {'Runs': N, 'Place3Rate': R}, ... }, ... }
            sire_stats_dict = {}
            for _, row in stats.iterrows():
                sire = row[sire_column]
                course = row['course_type']
                dist_group = row['DistanceGroup']
                runs = row['Runs']
                place3_rate = row['Place3Rate']

                if sire not in sire_stats_dict:
                    sire_stats_dict[sire] = {}
                key = (course, dist_group)
                # 信頼性のため、最低出走回数を設ける (例: 5回以上)
                if runs >= 5:
                    sire_stats_dict[sire][key] = {'Runs': int(runs), 'Place3Rate': place3_rate}
                # else: # 走回数が少ないデータは格納しない (あるいは別のデフォルト値を入れる)
                #     sire_stats_dict[sire][key] = {'Runs': int(runs), 'Place3Rate': None} # 例: 複勝率はNone

            setattr(self, stats_attr_name, sire_stats_dict) # 計算結果をクラス変数にセット

            end_calc_time = time.time()
            print(f"{sire_column} 別成績データの計算完了。{len(getattr(self, stats_attr_name))} 件の種牡馬データを生成。({end_calc_time - start_calc_time:.2f}秒)")
            self.update_status(f"{sire_column} 成績データ準備完了")

        except Exception as e:
            print(f"!!! Error during sire stats calculation ({sire_column}): {e}")
            traceback.print_exc()
            setattr(self, stats_attr_name, {}) # エラー時は空にする
            self.update_status(f"エラー: {sire_column} 成績計算失敗")
    # --- ★★★ 枠番別統計計算メソッド (新規追加) ★★★ ---
    def _calculate_gate_stats(self):
        """
        読み込んだデータ全体から、コース・距離・枠番ごとの
        成績（複勝率など）を集計し、クラス変数 self.gate_stats に格納する。
        """
        print("コース・距離・枠番別の成績統計データを計算中...")
        self.update_status("枠番統計データ計算中...")
        start_calc_time = time.time()

        # 計算結果を格納するクラス変数を初期化
        self.gate_stats = {} # キー: (競馬場, コース, 距離, 枠番), 値: {'Runs': N, 'Place3Rate': R}

        if self.combined_data is None or self.combined_data.empty:
            print("警告: 枠番統計計算のためのデータがありません。")
            self.update_status("枠番統計計算不可 (データなし)")
            return

        # --- 必要な列名を確認 ('Waku' または '枠番') ---
        waku_col_name = None
        if 'Waku' in self.combined_data.columns:
            waku_col_name = 'Waku'
        elif '枠番' in self.combined_data.columns:
            waku_col_name = '枠番'
            print("INFO: Using '枠番' column for gate stats.")
        else:
            print("警告: 枠番統計計算に必要な列 ('Waku' または '枠番') が見つかりません。")
            self.update_status("枠番統計計算不可 (列不足)")
            return

        required_cols = ['track_name', 'course_type', 'distance', waku_col_name, 'Rank']
        if not all(col in self.combined_data.columns for col in required_cols):
             missing = [c for c in required_cols if c not in self.combined_data.columns]
             print(f"警告: 枠番統計計算に必要な他の列が不足しています: {missing}")
             self.update_status(f"枠番統計計算不可 (列不足: {missing})")
             return
        # --- ここまで列名確認 ---

        df = self.combined_data[required_cols].copy()

        # --- データ前処理 ---
        try:
            df.dropna(subset=required_cols, inplace=True) # 必要な列の欠損を除外
            df['track_name'] = df['track_name'].astype(str).str.strip()
            df['course_type'] = df['course_type'].astype(str).str.strip()
            df['distance_numeric'] = pd.to_numeric(df['distance'], errors='coerce')
            df[waku_col_name + '_numeric'] = pd.to_numeric(df[waku_col_name], errors='coerce')
            df['Rank_numeric'] = pd.to_numeric(df['Rank'], errors='coerce')
            # 数値変換失敗や必要な情報が欠損した行を除外
            df.dropna(subset=['distance_numeric', waku_col_name + '_numeric', 'Rank_numeric'], inplace=True)

            # 枠番と着順は整数のはず
            df[waku_col_name + '_int'] = df[waku_col_name + '_numeric'].astype(int)
            df['Rank_int'] = df['Rank_numeric'].astype(int)
            df['distance_int'] = df['distance_numeric'].astype(int)

            # 枠番が1～8のデータのみに絞る (競馬の枠番は最大8枠)
            df = df[(df[waku_col_name + '_int'] >= 1) & (df[waku_col_name + '_int'] <= 8)]

        except Exception as e_prep:
            print(f"!!! ERROR during gate stats data preparation: {e_prep}")
            traceback.print_exc()
            self.gate_stats = {}
            self.update_status("エラー: 枠番統計データ準備失敗")
            return
        # --- ここまで前処理 ---

        if df.empty:
            print("警告: 枠番統計計算の対象となる有効なデータがありません。")
            self.update_status("枠番統計計算不可 (有効データなし)")
            return

        # --- 競馬場、コース、距離、枠番でグループ化し、成績を集計 ---
        try:
            group_keys = ['track_name', 'course_type', 'distance_int', waku_col_name + '_int']
            stats = df.groupby(group_keys).agg(
                Runs=('Rank_int', 'size'),             # 出走回数
                Place3=('Rank_int', lambda x: (x <= 3).sum()) # 3着内回数
            ).reset_index()

            # 複勝率を計算
            stats['Place3Rate'] = stats.apply(lambda r: r['Place3'] / r['Runs'] if r['Runs'] > 0 else 0, axis=1)

            # 結果を辞書形式で格納 { (競馬場, コース, 距離, 枠番): {'Runs': N, 'Place3Rate': R}, ... }
            temp_gate_stats = {}
            min_runs_threshold = 10 # 例: 最低10走以上のデータのみ採用（信頼性のため）

            for _, row in stats.iterrows():
                runs = row['Runs']
                if runs >= min_runs_threshold: # 最低出走回数を満たす場合のみ格納
                    # キーを作成
                    key = (row['track_name'], row['course_type'], row['distance_int'], row[waku_col_name + '_int'])
                    # 値を格納 (複勝率は丸める)
                    temp_gate_stats[key] = {'Runs': int(runs), 'Place3Rate': round(row['Place3Rate'], 3)}

            self.gate_stats = temp_gate_stats # 計算結果をクラス変数にセット

            end_calc_time = time.time()
            print(f"枠番別統計データの計算完了。{len(self.gate_stats)} 件の有効な条件データを生成。({end_calc_time - start_calc_time:.2f}秒)")
            self.update_status("枠番統計データ準備完了")

        except Exception as e:
            print(f"!!! Error during gate stats calculation: {e}")
            traceback.print_exc()
            self.gate_stats = {} # エラー時は空にする
            self.update_status("エラー: 枠番統計計算失敗")
    # --- ここまで枠番統計計算メソッド ---
    
    # --- ★★★ 基準タイム計算メソッド (新規追加) ★★★ ---
    def _calculate_reference_times(self):
        """
        手持ちデータ全体から、クラス・コース・距離ごとの基準タイム（勝ち馬の平均馬場補正タイム）を計算し、
        クラス変数 self.reference_times に格納する。
        """
        print("クラス・コース・距離別の基準タイムを計算中...")
        self.update_status("基準タイム計算中...")
        start_calc_time = time.time()

        self.reference_times = {} # 初期化 (キー: (クラスLv, 場, 種, 距), 値: 平均補正タイム)

        if self.combined_data is None or self.combined_data.empty:
            print("警告: 基準タイム計算のためのデータがありません。")
            self.update_status("基準タイム計算不可 (データなし)")
            return

        # --- 必要な列を確認 ---
        required_cols = ['race_name', 'track_name', 'course_type', 'distance', 'track_condition', 'Time', 'Rank']
        if not all(col in self.combined_data.columns for col in required_cols):
             missing = [c for c in required_cols if c not in self.combined_data.columns]
             print(f"警告: 基準タイム計算に必要な列が不足しています: {missing}")
             self.update_status(f"基準タイム計算不可 (列不足: {missing})")
             return
        # --- ここまで列確認 ---

        df = self.combined_data[required_cols].copy()

        # --- データ前処理 ---
        try:
            df.dropna(subset=required_cols, inplace=True)
            # タイム文字列を秒に変換 (共通ヘルパー関数を使用)
            df['time_sec'] = df['Time'].apply(self._time_str_to_sec)
            # クラスを判定して数値化 (ヘルパー関数を使用)
            df['race_class'] = df['race_name'].apply(self._get_race_class_level)
            # 必要な列の型変換と欠損値処理
            df['distance_int'] = pd.to_numeric(df['distance'], errors='coerce')
            df['Rank_int'] = pd.to_numeric(df['Rank'], errors='coerce')
            df.dropna(subset=['time_sec', 'race_class', 'distance_int', 'Rank_int', 'track_condition', 'course_type', 'track_name'], inplace=True)
            df['distance_int'] = df['distance_int'].astype(int)
            df['Rank_int'] = df['Rank_int'].astype(int)
            df['track_name'] = df['track_name'].astype(str).str.strip()
            df['course_type'] = df['course_type'].astype(str).str.strip()
            df['baba'] = df['track_condition'].astype(str).str.strip() # 'baba' 列名を使用

            # 馬場補正タイムを計算
            baba_hosei = {'芝': {'良': 0.0, '稍重': 0.5, '重': 1.0, '不良': 1.5}, 'ダ': {'良': 0.0, '稍重': -0.3, '重': -0.8, '不良': -1.3}}
            def get_hosei(row): return baba_hosei.get(row['course_type'], {}).get(row['baba'], 0.0)
            df['hosei_value'] = df.apply(get_hosei, axis=1)
            df['corrected_time_sec'] = df['time_sec'] - df['hosei_value']

            # 基準タイム計算の対象データ (勝ち馬に限定)
            df_filtered = df[df['Rank_int'] == 1].copy()
            if df_filtered.empty:
                print("警告: 基準タイム計算の対象となる勝ち馬データがありません。")
                self.update_status("基準タイム計算不可 (対象データなし)")
                return

        except Exception as e_prep:
            print(f"!!! ERROR during reference time data preparation: {e_prep}")
            traceback.print_exc()
            self.reference_times = {}
            self.update_status("エラー: 基準タイム データ準備失敗")
            return
        # --- ここまで前処理 ---

        # --- クラス、競馬場、コース、距離でグループ化し、平均補正タイムを計算 ---
        try:
            group_keys = ['race_class', 'track_name', 'course_type', 'distance_int']
            stats = df_filtered.groupby(group_keys)['corrected_time_sec'].agg(
                mean_time='mean',
                count='size' # データ数も集計
            ).reset_index()

            min_races_threshold = 5 # 例: 最低5レース分の勝ち馬データがある条件のみ採用
            temp_reference_times = {}
            for _, row in stats.iterrows():
                if row['count'] >= min_races_threshold: # 最低レース数を満たす場合のみ
                    # キー: (クラスレベル, 競馬場名, コース種別, 距離(int))
                    key = (int(row['race_class']), row['track_name'], row['course_type'], int(row['distance_int']))
                    # 値: 平均補正タイム (秒)
                    temp_reference_times[key] = round(row['mean_time'], 3) # 小数点3位まで

            self.reference_times = temp_reference_times # 計算結果をクラス変数にセット

            end_calc_time = time.time()
            print(f"基準タイムの計算完了。{len(self.reference_times)} 件の有効な条件データを生成。({end_calc_time - start_calc_time:.2f}秒)")
            self.update_status("基準タイム準備完了")

        except Exception as e:
            print(f"!!! Error during reference time calculation: {e}")
            traceback.print_exc()
            self.reference_times = {} # エラー時は空にする
            self.update_status("エラー: 基準タイム計算失敗")
    # --- ここまで基準タイム計算メソッド ---

    # --- ★★★ レースクラス判定ヘルパー関数 (クラス内に追加) ★★★ ---
    def _get_race_class_level(self, race_name):
        """レース名からクラスレベルを簡易的に判定して返す (1:新馬/未勝利 - 9:G1)"""
        if not isinstance(race_name, str): return 1 # 不明時は最低クラス
        rn = race_name.upper().replace(' ','').replace('　','') # 大文字化、全角半角スペース除去
        # G1/G2/G3 (国際表記含む)
        if 'G1' in rn or 'GI' in rn: return 9
        if 'G2' in rn or 'GII' in rn: return 8
        if 'G3' in rn or 'GIII' in rn: return 7
        # リステッド
        if '(L)' in rn or 'リステッド' in rn: return 6
        # オープン特別 (OP) - 判定難しいが、ステークス名などから類推
        if 'オープン' in rn or '(OP)' in rn or ('ステークス' in rn and not any(g in rn for g in ['G1','G2','G3','(L)','GI','GII','GIII'])) or 'Ｓ' in rn: return 5
        # 条件クラス (数字が優先されるように順番に注意)
        if '3勝クラス' in rn or '1600万下' in rn: return 4
        if '2勝クラス' in rn or '1000万下' in rn: return 3
        if '1勝クラス' in rn or '500万下' in rn: return 2
        # 新馬・未勝利
        if '未勝利' in rn or '新馬' in rn: return 1
        # それ以外 (地方交流重賞などは別途考慮が必要かも)
        # print(f"WARN: Could not determine race class for '{race_name}'. Defaulting to 1.")
        return 1 # 不明な場合は最低クラス扱い

    # --- ★★★ タイム文字列変換ヘルパー関数 (クラス内に追加 or 共通化) ★★★ ---
    def _time_str_to_sec(self, time_str):
        """タイム文字列 (M:SS.s or SS.s) を秒に変換"""
        try:
            if isinstance(time_str, (int, float)): return float(time_str) # 既に数値ならそのまま返す
            if pd.isna(time_str) or not isinstance(time_str, str): return None # NaN や文字列以外は None
            time_str = time_str.strip() # 前後の空白除去
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2: # 分:秒.秒
                     minutes = int(parts[0])
                     seconds = float(parts[1])
                     return minutes * 60 + seconds
                else: # 不正な形式
                     return None
            else: # 秒.秒 の形式
                return float(time_str)
        except (ValueError, TypeError): # 変換失敗
            return None

# --- ★★★ モデル保存メソッド (新規追加) ★★★ ---
    def save_model_to_file(self, filename="trained_lgbm_model.pkl"):
        """学習済みの self.trained_model を指定ファイルに保存する"""
        if hasattr(self, 'trained_model') and self.trained_model:
            # 保存先ディレクトリは設定から取得 (dataフォルダ推奨)
            save_dir = self.settings.get("data_dir", "data") # dataフォルダをデフォルトに
            if not os.path.exists(save_dir):
                try: os.makedirs(save_dir); print(f"INFO: Created directory {save_dir}")
                except Exception as e: save_dir = "."; print(f"WARN: Failed to create directory {save_dir}. Saving to current directory. Error: {e}")

            filepath = os.path.join(save_dir, filename)
            try:
                print(f"INFO: Saving trained model to: {filepath}")
                with open(filepath, 'wb') as f: # バイナリ書き込みモード ('wb')
                    pickle.dump(self.trained_model, f, pickle.HIGHEST_PROTOCOL)
                print(f"INFO: Successfully saved trained model to {filepath}")
                # GUIへの通知 (オプション)
                self.root.after(0, lambda path=os.path.basename(filepath): self.update_status(f"学習済みモデル保存完了: {path}"))
                # self.root.after(0, lambda path=filepath: messagebox.showinfo("モデル保存完了", f"学習済みモデルを保存しました:\n{path}"))
            except Exception as e:
                print(f"ERROR: Failed to save trained model to {filepath}: {e}")
                self.root.after(0, lambda err=e, path=filepath: messagebox.showerror("モデル保存エラー", f"モデルの保存中にエラー:\n{path}\n{err}"))
                self.root.after(0, lambda err=e: self.update_status(f"エラー: モデル保存失敗 ({type(err).__name__})"))
        else:
            print("WARN: No trained model found to save.")
            # messagebox.showwarning("モデル保存", "保存する学習済みモデルが見つかりません。")
    
    # --- ★★★ モデル読み込みメソッド (修正版) ★★★ ---
    def load_model_from_file(self, model_filename="trained_lgbm_model.pkl", features_filename="model_features.pkl"):
        """
        指定されたファイルから学習済みモデルと特徴量リストを読み込み、
        self.trained_model と self.model_features を初期化する。
        _load_pickle ヘルパーメソッドを使用する。
        """
        import os # osモジュールをインポート (既にあれば不要)
        # from tkinter import messagebox # messagebox は必要に応じて

        # --- 学習済みモデルの読み込み ---
        # 保存先ディレクトリは settings から取得 (models_dir優先、なければdata_dir、それもなければデフォルト)
        model_load_dir = self.settings.get("models_dir", self.settings.get("data_dir", os.path.join(self.app_data_dir, "models")))
        model_filepath = os.path.join(model_load_dir, model_filename)

        print(f"INFO: Loading trained model from: {model_filepath}")
        loaded_model = self._load_pickle(model_filepath) # ★ self._load_pickle を使用

        if loaded_model is not None:
            self.trained_model = loaded_model
            model_info = type(self.trained_model).__name__
            self.update_status(f"学習済みモデル読み込み完了 ({model_info})")
            print(f"INFO: Successfully loaded trained model: {model_filepath}")
        else:
            self.trained_model = None # ロード失敗またはファイルなし
            self.update_status("警告: 学習済みモデルの読み込み失敗またはファイルなし")
            print(f"WARN: Failed to load trained model or file not found: {model_filepath}")
            # messagebox.showwarning("モデル読込エラー", f"学習済みモデルファイルが見つからないか、読み込みに失敗しました:\n{model_filepath}") # UIスレッドから呼ぶべき

        # --- 特徴量リストの読み込み ---
        # モデルと同じディレクトリに保存されていると想定
        features_filepath = os.path.join(model_load_dir, features_filename)
        
        print(f"INFO: Loading model features from: {features_filepath}")
        loaded_features = self._load_pickle(features_filepath) # ★ self._load_pickle を使用

        if loaded_features is not None and isinstance(loaded_features, list):
            self.model_features = loaded_features
            self.update_status(f"モデル特徴量ロード完了 ({len(self.model_features)}個)") # ステータス更新は最後の方が良いかも
            print(f"INFO: Successfully loaded model features ({len(self.model_features)} features): {features_filepath}")
        else:
            self.model_features = [] # ロード失敗またはファイルなしの場合は空リスト
            # self.update_status("警告: モデル特徴量リストの読み込み失敗またはファイルなし") # ステータスはモデルロード成功/失敗で代表させるか
            print(f"WARN: Failed to load model features or file not found: {features_filepath}. Initializing as empty list.")
            if self.trained_model is not None: # モデルはあるのに特徴量リストがないのは問題
                 print(f"CRITICAL WARN: Model loaded, but feature list is missing! Predictions may fail or be incorrect.")
                 # messagebox.showwarning("特徴量リストエラー", f"学習済みモデルは読み込めましたが、対応する特徴量リストファイルが見つからないか、読み込みに失敗しました:\n{features_filepath}\n予測が正しく行えない可能性があります。")

        # 最終的なステータス表示 (モデルがロードされたかどうかを主眼に)
        if self.trained_model is not None and self.model_features:
             self.update_status(f"学習済みモデル ({type(self.trained_model).__name__}) と特徴量 ({len(self.model_features)}個) をロードしました。")
        elif self.trained_model is not None:
             self.update_status(f"学習済みモデル ({type(self.trained_model).__name__}) をロードしましたが、特徴量リストがありません。")
        else:
             self.update_status("学習済みモデルのロードに失敗しました。")

    # --- データ整形用ヘルパー関数 ---
    def format_result_data(self,result_table_list, race_id):
        """self.get_result_tableの結果をDataFrameに整形(馬ID抽出含む)"""
        if not result_table_list or len(result_table_list) < 2:
            return None
        # ↓↓↓ デバッグプリント追加 ↓↓↓
        print(f"      DEBUG format_result_data: Received header: {result_table_list[0]}")
        # ↑↑↑ ここまで追加 ↑↑↑
        header = [h.replace(' ', '').replace('\n', '') for h in result_table_list[0]]
        data_rows = result_table_list[1:]
        try:
            # 列名の重複チェックとリネーム
            if len(header) != len(set(header)):
                new_header = []
                counts = {}
                for h in header:
                    norm_h = h.strip()
                    if norm_h in counts:
                        counts[norm_h] += 1
                        new_header.append(f"{norm_h}_{counts[norm_h]}")
                    else:
                        counts[norm_h] = 0
                        new_header.append(norm_h)
                header = new_header

            # DataFrame作成 (列数が一致するか確認)
            if len(data_rows[0]) != len(header):
                 print(f"      警告: 結果テーブルのヘッダー({len(header)})とデータ({len(data_rows[0])})の列数が不一致です。スキップします。({race_id})")
                 print(f"      Header: {header}")
                 print(f"      Data[0]: {data_rows[0]}")
                 return None

            df = pd.DataFrame(data_rows, columns=header)

            # ★★★★★★★★★★★★★★★★★★
            if 'HorseName_url' in df.columns: # get_result_tableで追加した列があるか確認
                # '/horse/xxxxxxxxxx/' のような形式から数字を抽出
                # ★ 正規表現修正: 間に / があってもなくても対応 r'/horse/(\d+)/?'
                df['horse_id'] = df['HorseName_url'].astype(str).str.extract(r'/horse/(\d+)')
                # 抽出できなかったものは NaN になる
                print(f"      馬IDを抽出しました。抽出成功: {df['horse_id'].notna().sum()}件 / 欠損: {df['horse_id'].isnull().sum()}")
                # 不要になったURL列を削除 (オプション)
                # df = df.drop(columns=['HorseName_url'], errors='ignore')
            else:
                print("      警告: HorseName_url 列が見つかりません。馬IDを抽出できません。")
                df['horse_id'] = None # とりあえず列だけ作成(NaNで埋まる)
            # ★★★★★★★★★★★★★★★★★★

            # 列名統一マップ (より多くの可能性を考慮)
            rename_map = {
                '着順': 'Rank', '枠': 'Waku', '馬番': 'Umaban', '馬名': 'HorseName',
                '性齢': 'SexAge', '斤量': 'Load', '騎手': 'JockeyName', 'タイム': 'Time',
                '着差': 'Diff', 'ﾀｲﾑ指数': 'TimeIndex', '通過': 'Passage', '上がり': 'Agari', # '後3F'だけでなく
                '単勝': 'Odds', '人気': 'Ninki', '馬体重': 'WeightInfo', '馬体重(増減)': 'WeightInfo',
                '調教師': 'TrainerName', '厩舎': 'TrainerName',
                # 他に必要そうな列名があれば追加
            }
            df.rename(columns=lambda x: rename_map.get(x.strip(), x.strip()), inplace=True)

        # データクリーニング
            df['race_id'] = race_id
            numeric_cols = ['Rank', 'Waku', 'Umaban', 'Load', 'Ninki', 'Odds', 'Agari', 'TimeIndex']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            if 'WeightInfo' in df.columns:
                df['Weight'] = df['WeightInfo'].str.extract(r'(\d+)', expand=False).astype(float)
                df['WeightDiff'] = df['WeightInfo'].str.extract(r'\(([-+]?\d+)\)', expand=False).astype(float)
                # df.drop('WeightInfo', axis=1, inplace=True, errors='ignore') # 元列を残す場合もある

            if 'SexAge' in df.columns:
                 df['Sex'] = df['SexAge'].str[0]
                 df['Age'] = pd.to_numeric(df['SexAge'].str[1:], errors='coerce')

            # リンクからID抽出 (オプション)
            # id_cols = {'HorseName': 'horse_id', 'JockeyName': 'jockey_id', 'TrainerName': 'trainer_id'}
            # for col, id_col in id_cols.items():
            #     if col in df.columns:
            #         # df[id_col] = df[col].apply(lambda x: ...) # BeautifulSoupでaタグのhrefを取得する処理が必要

            # 着順に数字以外(除外、中止など)が含まれる場合NaNにする
            if 'Rank' in df.columns:
                 df['Rank'] = pd.to_numeric(df['Rank'], errors='coerce')


            print(f"      DEBUG format_result_data: Columns returned: {df.columns.tolist()}") # ★追加
            return df

        except ValueError as ve:
             print(f"    エラー: 結果DataFrame作成時の列数不一致など ({race_id}): {ve}")
        except Exception as e:
            print(f"    エラー: 結果DataFrameの整形中にエラー ({race_id}): {e}")
            traceback.print_exc()
        return None
     
    # --- ★★★ データ前処理メソッド (近走特徴量追加 - get_horse_details利用版) ★★★ ---
    def preprocess_data_for_training(self):
        """
        self.combined_data に get_horse_details を使って取得した近走特徴量
        （着順、着差、上がり）を追加し、結果を self.processed_data に格納する。
        注意: この処理は馬の頭数によっては時間がかかる場合があります。
        """
        print("データ前処理開始: 近走特徴量 (get_horse_details利用) を追加します...")
        self.root.after(0, lambda: self.update_status("データ前処理中 (詳細情報取得)...")) # GUI更新はメインスレッドへ
        start_time = _time.time()

        # --- 必要なモジュールをインポート ---
        import pandas as pd # type: ignore # type: ignore
        import numpy as np # type: ignore
        import traceback
        import re
        # --- ここまでインポート ---


        if self.combined_data is None or self.combined_data.empty:
            print("警告: 前処理対象のデータがありません。")
            self.root.after(0, lambda: self.update_status("前処理スキップ (データなし)"))
            self.processed_data = None
            return

        # --- 必要な列を確認 ---
        required_cols = ['horse_id', 'date', 'Rank']
        if not all(col in self.combined_data.columns for col in required_cols):
            missing = [c for c in required_cols if c not in self.combined_data.columns]
            print(f"警告: 前処理に必要な基本列が不足しています: {missing}")
            self.root.after(0, lambda status=f"前処理スキップ (列不足: {missing})": self.update_status(status))
            self.processed_data = None
            return
        # --- 列確認ここまで ---

        try:
            df = self.combined_data.copy() # 元データをコピーして処理

            # --- 日付列をdatetime型に ---
            if not pd.api.types.is_datetime64_any_dtype(df['date']):
                 print("INFO: Converting 'date' column to datetime for preprocessing.")
                 try:
                      df['date'] = pd.to_datetime(df['date'], format='%Y年%m月%d日', errors='coerce')
                      if df['date'].isnull().any():
                           print(f"警告: 日付変換に失敗した行が {df['date'].isnull().sum()} 件あります。これらの行を除外します。")
                           df.dropna(subset=['date'], inplace=True)
                 except Exception as e_date:
                      print(f"ERROR: 日付変換中に予期せぬエラー: {e_date}. 処理を中断します。")
                      self.root.after(0, lambda: self.update_status("エラー: 日付変換失敗"))
                      self.processed_data = None
                      return
            # --- ここまで日付処理 ---

            # --- ユニークな馬IDリストを作成 ---
            unique_horse_ids = df['horse_id'].dropna().astype(str).unique()
            num_unique_horses = len(unique_horse_ids)
            print(f"INFO: 対象となるユニーク馬ID数: {num_unique_horses}")
            if num_unique_horses == 0:
                 print("警告: 有効な馬IDが見つかりませんでした。")
                 self.root.after(0, lambda: self.update_status("前処理スキップ (馬IDなし)"))
                 self.processed_data = None
                 return

            # --- 馬詳細情報のキャッシュ（クラス変数として保持）---
            if not hasattr(self, 'horse_details_cache'):
                self.horse_details_cache = {}
            print(f"INFO: 現在の馬詳細キャッシュ数: {len(self.horse_details_cache)}")

            # --- 不足している馬の詳細情報を取得 ---
            missing_ids = [hid for hid in unique_horse_ids if hid not in self.horse_details_cache]
            num_missing = len(missing_ids)
            if num_missing > 0:
                print(f"INFO: {num_missing} 頭分の馬詳細情報を新たに取得します...")
                sleep_interval = getattr(self, 'SLEEP_TIME_PER_HORSE', 0.6)
                for i, horse_id in enumerate(missing_ids):
                    self.root.after(0, lambda status=f"詳細情報取得中... ({i+1}/{num_missing}) ID: {horse_id}": self.update_status(status))
                    print(f"   取得中 ({i+1}/{num_missing}): {horse_id}")
                    details = self.get_horse_details(str(horse_id))
                    self.horse_details_cache[horse_id] = details
                    _time.sleep(sleep_interval)
                print(f"INFO: {num_missing} 頭分の馬詳細情報を取得・キャッシュしました。")
            else:
                print("INFO: 必要な馬詳細情報はキャッシュに存在します。")

            # --- 近走特徴量計算用のヘルパー関数 ---
            def get_past_performance(horse_id, lap_num, feature_key):
                details = self.horse_details_cache.get(str(horse_id))
                if details and 'race_results' in details and isinstance(details['race_results'], list):
                    results = details['race_results']
                    if len(results) >= lap_num:
                        past_result = results[lap_num - 1]
                        if feature_key == 'rank':
                            rank = past_result.get('rank'); rank_str = past_result.get('rank_str', '?')
                            try: return int(float(rank))
                            except: return 99 if rank_str in ['中', '除', '取', '止'] else None
                        elif feature_key == 'diff':
                            rank_val = get_past_performance(horse_id, lap_num, 'rank')
                            diff_val = past_result.get('diff') # キー名は 'diff' を想定
                            if rank_val == 1: return 0.0
                            if rank_val is None or rank_val == 99: return None
                            if isinstance(diff_val, str):
                                if diff_val == 'クビ': return 0.1
                                if diff_val == 'ハナ': return 0.05
                                if diff_val == 'アタマ': return 0.01
                                if diff_val == '同着': return 0.0
                            diff_numeric = pd.to_numeric(diff_val, errors='coerce')
                            return round(diff_numeric, 3) if pd.notna(diff_numeric) else None
                        elif feature_key == 'agari':
                            agari_val = past_result.get('agari') # キー名は 'agari' を想定
                            agari_numeric = pd.to_numeric(agari_val, errors='coerce')
                            return round(agari_numeric, 1) if pd.notna(agari_numeric) else None
                return None

            # --- applyを使って近走特徴量列を追加 ---
            n_laps = 3
            print(f"INFO: Calculating features for previous {n_laps} laps using horse details cache...")
            self.root.after(0, lambda: self.update_status("データ前処理中 (近走特徴量計算)..."))
            for n in range(1, n_laps + 1):
                df[f'rank_{n}ago'] = df['horse_id'].astype(str).apply(lambda x: get_past_performance(x, n, 'rank'))
                df[f'diff_{n}ago'] = df['horse_id'].astype(str).apply(lambda x: get_past_performance(x, n, 'diff'))
                df[f'agari_{n}ago'] = df['horse_id'].astype(str).apply(lambda x: get_past_performance(x, n, 'agari'))
                print(f"INFO: Calculated features for {n} lap(s) ago.")

            # --- 結果をクラス変数に格納 ---
            self.processed_data = df
            print(f"INFO: self.processed_data に前処理済みデータを格納しました。Shape: {self.processed_data.shape}")
            added_cols = [f'{k}_{n}ago' for n in range(1, n_laps+1) for k in ['rank','diff','agari']]
            print(f"      追加された近走特徴量 (例): {added_cols}")
            if not self.processed_data.empty:
                 print(f"      Example of added features (first 5 rows):\n{self.processed_data[added_cols].head().to_string()}")

            end_time = _time.time()
            print(f"データ前処理完了。 ({end_time - start_time:.2f}秒)")
            self.root.after(0, lambda: self.update_status("データ前処理完了 (近走特徴量追加)"))

        except Exception as e:
            print(f"!!! ERROR during data preprocessing (adding past performance): {e}")
            traceback.print_exc()
            self.processed_data = None
            self.root.after(0, lambda status=f"エラー: データ前処理失敗 ({type(e).__name__})": self.update_status(status))

        # --- ★★★ レースクラス判定ヘルパー関数 (クラス内に追加 - 変更なし) ★★★ ---
    def _get_race_class_level(self, race_name):
        # ... (前回のコードと同じ) ...
        if not isinstance(race_name, str): return 1
        rn = race_name.upper().replace(' ','').replace('　','')
        if 'G1' in rn or 'GI' in rn: return 9
        if 'G2' in rn or 'GII' in rn: return 8
        if 'G3' in rn or 'GIII' in rn: return 7
        if '(L)' in rn or 'リステッド' in rn: return 6
        if 'オープン' in rn or '(OP)' in rn or ('ステークス' in rn and not any(g in rn for g in ['G1','G2','G3','(L)','GI','GII','GIII'])) or 'Ｓ' in rn: return 5
        if '3勝クラス' in rn or '1600万下' in rn: return 4
        if '2勝クラス' in rn or '1000万下' in rn: return 3
        if '1勝クラス' in rn or '500万下' in rn: return 2
        if '未勝利' in rn or '新馬' in rn: return 1
        return 1

    # --- ★★★ タイム文字列変換ヘルパー関数 (クラス内に追加 or 共通化 - 変更なし) ★★★ ---
    def _time_str_to_sec(self, time_str):
        # ... (前回のコードと同じ) ...
        try:
            if isinstance(time_str, (int, float)): return float(time_str)
            if pd.isna(time_str) or not isinstance(time_str, str): return None
            time_str = time_str.strip()
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 2: return int(parts[0]) * 60 + float(parts[1])
                else: return None
            else: return float(time_str)
        except (ValueError, TypeError): return None
    
# --- ★★★ 学習データ準備メソッド (calculate_original_index 利用版 / train_and_evaluate_model連携対応 / race_resultsフィルタリング追加) ★★★ ---
    def _prepare_data_for_model(self, target_column_name='target_rank_within_3'):
        """
        self.combined_data (または適切な入力データ) の各行について 
        calculate_original_index を実行し、その結果の全特徴量と、
        指定されたターゲット列から作成した正解ラベルを含む単一のDataFrameを返す。
        馬の過去戦績(race_results)は、そのレースの開催日より前のもののみを使用する。
        """
        print("モデル学習用のデータ準備を開始します (calculate_original_index を使用)...")
        self.update_status("学習データ準備中...")
        start_time = _time.time() # time ではなく _time を使う (ファイル冒頭で import time as _time を想定)

        import pandas as pd # 関数内でのimportは通常非推奨だが、既存コードに合わせる
        import numpy as np
        import traceback

        # 特徴量計算の元となるデータを指定 (self.combined_data を想定)
        # ユーザー様が preprocess_data_for_training の結果 (self.processed_data) を使いたい場合は、
        # ここを self.processed_data に変更してください。
        # ただし、その場合 self.processed_data にも 'date', 'horse_id', 'Rank' などの基本列が必要。
        input_data_for_feature_engineering = self.combined_data
        if input_data_for_feature_engineering is None or input_data_for_feature_engineering.empty:
            print(f"エラー: 特徴量計算の元となるデータ (input_data_for_feature_engineering) が空です。")
            self.update_status("エラー: 元データなし (学習準備)")
            return None
        
        # calculate_original_index が内部で参照する統計データの存在チェック
        required_attrs_for_calc = ['course_time_stats', 'father_stats',
                                   'mother_father_stats', 'gate_stats', 'reference_times',
                                   'horse_details_cache']
        missing_attrs = [attr for attr in required_attrs_for_calc if not hasattr(self, attr) or getattr(self, attr) is None or (isinstance(getattr(self,attr),dict) and not getattr(self,attr))]
        if missing_attrs:
            # horse_details_cache は空でも処理は続行できる場合があるが、他は計算に影響大
            log_level_stats = print if any(attr != 'horse_details_cache' for attr in missing_attrs) else lambda x: None #キャッシュ以外がないならエラー
            if any(attr != 'horse_details_cache' for attr in missing_attrs):
                 print(f"CRITICAL_ERROR: 特徴量計算に必要な統計データが不足または空です: {missing_attrs}")
                 self.update_status("エラー: 統計データ不足 (学習準備)")
                 return None
            else: # キャッシュのみ空の場合
                 print(f"WARN: horse_details_cacheが空です。馬詳細情報の取得に時間がかかる可能性があります。")


        all_features_list = []
        target_values_list = []
        skipped_rows_count = 0
        num_total_rows = len(input_data_for_feature_engineering)
        print(f"INFO: 入力データ (input_data_for_feature_engineering) の {num_total_rows} 行を処理します...")

        # 入力データを1行ずつ処理
        for index, row_data in input_data_for_feature_engineering.iterrows():
            if index > 0 and index % 500 == 0:
                progress_percent = (index / num_total_rows) * 100
                self.root.after(0, lambda i=index, n=num_total_rows, p=progress_percent: self.update_status(f"特徴量生成中... ({i}/{n} - {p:.0f}%)"))

            # 1. レース条件 (race_conditions) を作成
            #    row_data (入力DataFrameの1行) から必要な情報を抽出
            #    CSVの列名に合わせてキーを取得 ('track_condition', 'date' など)
            race_conditions = {
                'race_id': row_data.get('race_id'), # ★ race_id も追加しておく
                'course_type': row_data.get('course_type'),
                'distance': pd.to_numeric(row_data.get('distance'), errors='coerce'),
                'track_name': row_data.get('track_name'), # CSVの列名を想定
                'baba': row_data.get('track_condition'), # CSVの列名 'track_condition' を 'baba' に
                'RaceDate': pd.to_datetime(row_data.get('date'), errors='coerce'), # CSVの 'date' 列を 'RaceDate' に
                'RaceName': row_data.get('race_name'), # CSVの列名
                'RaceNum': str(row_data.get('race_num','')).replace('R',''), # CSVの列名
                'Around': row_data.get('turn', row_data.get('回り')), # CSVの列名 (turn or 回り)
                'Weather': row_data.get('weather') # CSVの列名
            }
            if pd.isna(race_conditions['distance']): race_conditions['distance'] = None
            else:
                try: race_conditions['distance'] = int(race_conditions['distance'])
                except (ValueError, TypeError): race_conditions['distance'] = None
            
            if pd.NaT == race_conditions['RaceDate']: # pd.NaT は to_datetime で変換失敗時の値
                print(f"WARN ({row_data.get('race_id')}): 行 {index} の日付が不正なためスキップします。Date: {row_data.get('date')}")
                skipped_rows_count +=1
                continue # 日付がなければフィルタリングできないのでスキップ

            # 2. 馬の詳細情報 (horse_details_for_calc) を作成
            horse_details_for_calc = row_data.to_dict() # 現在のレースの行データ(出馬表情報に相当)がベース
            horse_id_current_row = horse_details_for_calc.get('horse_id')

            if horse_id_current_row and pd.notna(horse_id_current_row):
                horse_id_str_current_row = str(horse_id_current_row).split('.')[0]
                
                # キャッシュから馬の固定情報（全過去戦績、血統など）を取得
                details_from_cache_learn = self.horse_details_cache.get(horse_id_str_current_row)
                
                if details_from_cache_learn and isinstance(details_from_cache_learn, dict):
                    # 過去戦績をキャッシュから取得
                    if 'race_results' in details_from_cache_learn and isinstance(details_from_cache_learn['race_results'], list):
                        horse_details_for_calc['race_results'] = details_from_cache_learn['race_results']
                    else:
                        horse_details_for_calc['race_results'] = []
                    
                    # 他の馬の固定情報もキャッシュから取得 (get_horse_details が返すものを想定)
                    # これらは calculate_original_index が horse_details から直接参照する
                    if 'father' in details_from_cache_learn: horse_details_for_calc['father'] = details_from_cache_learn['father']
                    if 'mother_father' in details_from_cache_learn: horse_details_for_calc['mother_father'] = details_from_cache_learn['mother_father']
                    # get_horse_details で取得している他のプロフィール情報も必要ならここでマージ
                    # horse_details_for_calc.update(details_from_cache_learn) # ただしキー重複に注意
                else:
                    # print(f"WARN ({horse_id_str_current_row}): 学習データ準備中、キャッシュに馬詳細なし。過去走情報は利用できません。")
                    horse_details_for_calc['race_results'] = []
            else: # horse_id がない場合
                # print(f"WARN: 行 {index} に horse_id がないため、過去走情報を取得できません。")
                horse_details_for_calc['race_results'] = []

            # === ▼▼▼ ここから race_results のフィルタリング処理を追加 ▼▼▼ ===
            if 'race_results' in horse_details_for_calc and isinstance(horse_details_for_calc['race_results'], list):
                current_race_date_for_filter = race_conditions.get('RaceDate') # この行のレース開催日
                
                if pd.notna(current_race_date_for_filter):
                    filtered_results_for_learning = []
                    for past_race_result_learn in horse_details_for_calc['race_results']:
                        if isinstance(past_race_result_learn, dict) and pd.notna(past_race_result_learn.get('date')):
                            past_race_date_learn = pd.to_datetime(past_race_result_learn.get('date'), errors='coerce')
                            if pd.notna(past_race_date_learn) and past_race_date_learn < current_race_date_for_filter:
                                filtered_results_for_learning.append(past_race_result_learn)
                    
                    # # デバッグ用にフィルタリング状況を出力してもよい
                    # if len(horse_details_for_calc['race_results']) != len(filtered_results_for_learning) and index < 10: # 最初の数件だけログ出すなど
                    #     print(f"DEBUG_PREPARE_FILTER ({horse_id_current_row}): 学習データ race_results フィルタリング。元:{len(horse_details_for_calc['race_results'])}, 後:{len(filtered_results_for_learning)} (レース日:{current_race_date_for_filter.strftime('%Y-%m-%d') if pd.notna(current_race_date_for_filter) else '不明'})")
                    horse_details_for_calc['race_results'] = filtered_results_for_learning
                else:
                    # current_race_date_for_filter が NaT の場合はフィルタリングできない
                    # print(f"WARN PREPARE ({horse_id_current_row}): current_race_date_for_filter がNaTのため、race_results フィルタリングスキップ。")
                    horse_details_for_calc['race_results'] = [] # 安全のため空にする
            elif 'race_results' in horse_details_for_calc: # リスト型ではなかった場合
                 # print(f"WARN PREPARE ({horse_id_current_row}): horse_details_for_calc['race_results'] がリスト型ではありません。型: {type(horse_details_for_calc['race_results'])}。")
                 horse_details_for_calc['race_results'] = []
            else: # 'race_results' キー自体が存在しない場合
                horse_details_for_calc['race_results'] = []
            # === ▲▲▲ race_results のフィルタリング処理ここまで ▲▲▲ ===

            # 3. 特徴量計算を実行
            #    calculate_original_index に渡す horse_details は、この時点の horse_details_for_calc
            #    これには、出馬表由来の情報(row_data)と、キャッシュから取得した馬の固定情報(過去戦績、血統など)が含まれる。
            _, calculated_features_dict = self.calculate_original_index(horse_details_for_calc, race_conditions)

            # 4. 正解ラベル (target) を作成
            rank_value = pd.to_numeric(row_data.get('Rank'), errors='coerce') # 元のrow_dataからRankを取得
            if pd.isna(rank_value):
                skipped_rows_count += 1
                continue 
            target_label = 1 if rank_value <= 3 else 0

            # 5. 計算された特徴量と正解ラベルをリストに追加
            if calculated_features_dict.get('error') is None:
                calculated_features_dict['race_id'] = row_data.get('race_id') # race_id も特徴量DFに残す
                # horse_id は calculate_original_index 内で features['horse_id'] に設定済みのはず
                all_features_list.append(calculated_features_dict)
                target_values_list.append(target_label)
            else:
                skipped_rows_count += 1
        
        self.root.after(0, lambda: self.update_status(f"特徴量生成完了。DataFrame作成中..."))

        if skipped_rows_count > 0:
            print(f"INFO: 特徴量生成中に {skipped_rows_count} 行がスキップされました (Rank欠損、日付不正、または特徴量計算エラー)。")
        
        if not all_features_list:
            print("エラー: 有効な特徴量データが1行も生成されませんでした。")
            self.update_status("エラー: 特徴量生成失敗 (学習準備)")
            return None

        features_df = pd.DataFrame(all_features_list)

        if len(target_values_list) == len(features_df):
            features_df[target_column_name] = target_values_list
        else:
            print(f"エラー: 特徴量リスト ({len(features_df)}件) とターゲットリスト ({len(target_values_list)}件) の長さが一致しません。")
            self.update_status("エラー: データ準備中の不整合 (学習準備)")
            return None
        
        # === ▼▼▼ デバッグログ追加 (前回提案通り) ▼▼▼ ===
        print(f"\n--- DEBUG: _prepare_data_for_model ---")
        print(f"--- 生成された features_df の情報 ---")
        print(f"  Shape: {features_df.shape}")
        # print(f"  Columns: {features_df.columns.tolist()}") # 必要なら表示
        if 'タイム偏差値' in features_df.columns:
            print(f"  タイム偏差値 dtype: {features_df['タイム偏差値'].dtype}")
            # print(f"  タイム偏差値 unique values (上位20件, NaN含む): {features_df['タイム偏差値'].unique()[:20]}") # 全部は多いのでコメントアウトも可
            print(f"  タイム偏差値 NaN数: {features_df['タイム偏差値'].isnull().sum()} / 全体: {len(features_df)}")
        else:
            print("  タイム偏差値 列が存在しません。")
        # 他の特徴量のNaN数も確認すると良い
        # for col_check_nan in ['Age', '斤量絶対値', '馬体重絶対値', '斤量前走差', '馬体重前走差', '枠番', '負担率']:
        #    if col_check_nan in features_df.columns:
        #        print(f"  {col_check_nan} NaN数: {features_df[col_check_nan].isnull().sum()} / 全体: {len(features_df)}")
        #    else:
        #        print(f"  {col_check_nan} 列が存在しません。")
        print(f"--- DEBUGログここまで (_prepare_data_for_model) ---\n")
        # === ▲▲▲ デバッグログ追加ここまで ▲▲▲ ===
            
        end_time = _time.time()
        print(f"モデル学習用の元データ (特徴量 + ターゲット列) の準備完了。Shape: {features_df.shape} ({end_time - start_time:.2f}秒)")
        self.root.after(0, lambda: self.update_status("学習用データ準備完了"))
        
        return features_df
    
    # --- ★★★ モデル学習・評価メソッド ★★★ ---
    def train_and_evaluate_model(self, processed_data, target_column='target_rank_within_3'):
        """
        LightGBMモデルの学習、評価、保存、キャリブレーションプロット作成を行う。
        データ型の前処理を追加。
        """
        # --- 必要なライブラリをインポート (ファイル冒頭にあるか確認) ---
        import pandas as pd
        import numpy as np
        import lightgbm as lgb
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, confusion_matrix
        from sklearn.calibration import CalibrationDisplay
        import matplotlib.pyplot as plt
        # import joblib # joblibは現在未使用のようですが、pickleの代わりにも使えます
        import os
        import traceback
        from tkinter import messagebox
        # --- ここまでインポート ---

        try:
            self.update_status("モデル学習と評価を開始します...")
            print("\n--- Starting Model Training and Evaluation ---")

            if processed_data is None or processed_data.empty:
                messagebox.showerror("学習エラー", "学習に使用するデータがありません。")
                self.update_status("エラー: 学習データなし")
                return

            # 特徴量 (X) とターゲット (y) を準備
            # target_columnと、予測に使うべきでない列を除外
            cols_to_drop_for_X = [
                target_column, 'race_id', 'horse_id', 'HorseName', 'date', # 基本ID・結果・日付系
                'Time', 'Rank','Diff', 'Ninki', 'Odds', 'Odds_x', 'Odds_y', # レース結果やオッズそのもの
                'Umaban', 'Waku', # 枠番は統計特徴量(枠番_複勝率)を使う想定
                'SexAge', 'JockeyName', 'TrainerName', # これらも統計特徴量化を推奨
                'father', 'mother_father', # これらも統計特徴量化を推奨
                'WeightInfo', 'WeightInfoShutuba', # 馬体重(絶対値), 馬体重前走差 になっているはず
                # ターゲットになりうる列 (もしあれば)
                'target_exacta', 'target_quinella', 'target_trifecta', 
                'payout_win', 'payout_place', 'payout_exacta', 'payout_quinella', 'payout_trifecta',
                'text_race_results', # テキストデータ
                'error' # エラーフラグも特徴量によっては不要
            ]
            # processed_dataに実際に存在する列のみをドロップ対象にする
            existing_cols_to_drop_for_X = [col for col in cols_to_drop_for_X if col in processed_data.columns]
            
            X = processed_data.drop(columns=existing_cols_to_drop_for_X, errors='ignore').copy()
            
            if target_column not in processed_data.columns:
                messagebox.showerror("学習エラー", f"ターゲット列 '{target_column}' がデータに存在しません。")
                self.update_status(f"エラー: ターゲット列 '{target_column}' なし")
                return
            y = processed_data[target_column].astype(int)

            # 初期特徴量リストの保存 (get_dummies前)
            # self.model_features は get_dummies 後の最終的な特徴量リストにすべきなので、
            # ここでは一時的なリストとして保持するか、get_dummies後に再設定します。
            # print(f"初期学習特徴量 (get_dummies前) ({len(X.columns)}個): {X.columns.tolist()}") # ログ出力は変更

            # --- ★★★ データ型前処理と欠損値処理 ★★★ ---
            print("特徴量データのデータ型前処理と欠損値補完を開始します...")
            
            # ★★★ 修正点: prev_race_track_type_1ago をダミー変数化 ★★★
            if 'prev_race_track_type_1ago' in X.columns:
                print("  処理中: prev_race_track_type_1ago 列のダミー変数化")
                try:
                    X = pd.get_dummies(X, columns=['prev_race_track_type_1ago'], prefix='prev_track_type', dummy_na=True)
                    # dummy_na=True にすると、'prev_track_type_nan' のような列が作られる
                    print(f"    prev_race_track_type_1ago をダミー変数化しました。新しい列(一部): {[col for col in X.columns if 'prev_track_type' in col][:5]}")
                except Exception as e_dummy:
                    print(f"    エラー: prev_race_track_type_1ago のダミー変数化に失敗: {e_dummy}")
                    # エラーが発生した場合、この列を除外するか、処理を中断するか検討
                    X = X.drop(columns=['prev_race_track_type_1ago'], errors='ignore')
                    print("    prev_race_track_type_1ago 列を除外して処理を続行します。")
            # ★★★ 修正ここまで ★★★

            # 1. カテゴリカル変数の処理 (Sex, 距離区分など)
            if 'Sex' in X.columns:
                print("  処理中: Sex列")
                # calculate_original_indexで数値(0,1,2)に変換済みのはずなので、ここでは型確認と欠損値処理
                X['Sex'] = pd.to_numeric(X['Sex'], errors='coerce')
                sex_fill_value = X['Sex'].mode()[0] if not X['Sex'].mode().empty else -1 # 最頻値、なければ-1
                self.imputation_values_['Sex'] = sex_fill_value # 補完値を保存
                X['Sex'] = X['Sex'].fillna(sex_fill_value)
                print(f"    Sex列のユニーク値 (処理後): {X['Sex'].unique()}")

            if '距離区分' in X.columns:
                print("  処理中: 距離区分列")
                # calculate_original_index でカテゴリ文字列が設定される想定
                distance_category_mapping = {
                    '1400m以下': 0, '1401-1800m': 1, '1801-2200m': 2, 
                    '2201-2600m': 3, '2601m以上': 4
                }
                X['距離区分'] = X['距離区分'].map(distance_category_mapping)
                dist_fill_value = X['距離区分'].mode()[0] if not X['距離区分'].mode().empty else -1 # 最頻値、なければ-1
                self.imputation_values_['距離区分'] = dist_fill_value # 補完値を保存
                X['距離区分'] = X['距離区分'].fillna(dist_fill_value)
                print(f"    距離区分列のユニーク値 (マッピング後): {X['距離区分'].unique()}")

            # 2. 数値であるべき特徴量の欠損値処理と型変換
            #    calculate_original_index で数値型になっているはずだが、念のため
            #    'error'列はここでは処理しない (特徴量リストに含まれない想定)

            # 3. 全ての数値列に対して欠損値を平均値で補完
            print("  数値列の欠損値を学習時の平均値で補完/0で補完します...")
            if not hasattr(self, 'imputation_values_') or not self.imputation_values_:
                 self.imputation_values_ = {} # 初回学習などのために初期化

            nan_count_before_numeric_fill = X.isnull().sum().sum()
            cols_filled_with_mean = []
            cols_filled_with_zero = []

            for col in X.columns: # X.columns は get_dummies 後
                if X[col].isnull().any(): # 欠損値がある列のみ処理
                    # まず数値型に強制変換 (文字列などが混入している場合NaNになる)
                    X.loc[:, col] = pd.to_numeric(X[col], errors='coerce')
                    
                    # 学習時(初回)の補完値計算と保存
                    if col not in self.imputation_values_:
                        mean_val = X[col].mean()
                        if pd.isna(mean_val): # 列全体がNaNまたは全て数値変換失敗
                            self.imputation_values_[col] = 0 # フォールバックとして0
                            print(f"    警告: 列 '{col}' の平均値が計算できませんでした。学習時の補完値を0とします。")
                        else:
                            self.imputation_values_[col] = mean_val
                    
                    # 保存された補完値で埋める
                    fill_value_for_col = self.imputation_values_[col]
                    X.loc[:, col] = X[col].fillna(fill_value_for_col)
                    
                    if fill_value_for_col == 0 and pd.isna(X[col].mean()): # 0で補完したが元々平均が計算不能だった場合
                        cols_filled_with_zero.append(col)
                    else:
                        cols_filled_with_mean.append(col)
                else: # 欠損値がない列も、数値型であることを確認し、学習時の平均値を記録
                    X.loc[:, col] = pd.to_numeric(X[col], errors='coerce')
                    if col not in self.imputation_values_:
                         if X[col].isnull().all(): # 全てNaNになった場合
                             self.imputation_values_[col] = 0
                             print(f"    警告: 列 '{col}' は全て数値変換に失敗しました。学習時の補完値を0とします。")
                         else:
                             self.imputation_values_[col] = X[col].mean() # (NaN除去後の)平均
            
            if cols_filled_with_mean: print(f"    平均値で補完した列: {cols_filled_with_mean}")
            if cols_filled_with_zero: print(f"    0で補完した列: {cols_filled_with_zero}")
            
            nan_count_after_numeric_fill = X.isnull().sum().sum()
            print(f"  数値列補完前の欠損値総数: {nan_count_before_numeric_fill}, 補完後: {nan_count_after_numeric_fill}")

            if nan_count_after_numeric_fill > 0:
                print(f"!!! 重大な警告: 欠損値補完後もNaNが残っています: {X.columns[X.isnull().any()].tolist()}")
                # さらに強制的に0で埋めるか、エラーにするか
                X = X.fillna(0)
                print("    残存NaNを0で強制的に補完しました。")


            # 最終確認: object型が残っていないか
            object_cols_remaining = X.select_dtypes(include=['object']).columns.tolist()
            if object_cols_remaining:
                print(f"!!! 重大な警告: 処理後もobject型の列が残っています: {object_cols_remaining}。LightGBM学習時にエラーが発生します。")
                for obj_col in object_cols_remaining: print(f"    '{obj_col}' の値のサンプル: {X[obj_col].unique()[:5]}")
                messagebox.showerror("データ型エラー", f"以下の特徴量が数値に変換されていません: {', '.join(object_cols_remaining)}")
                self.update_status(f"エラー: object型が残存")
                return
            
            self.model_features = list(X.columns) # ★★★ get_dummies 後の最終的な特徴量リストを保存 ★★★
            print(f"データ型処理後の最終的な学習特徴量 ({len(self.model_features)}個)") # ログ出力変更
            # --- ★★★ データ型前処理と欠損値処理ここまで ★★★ ---


            if X.empty or len(X) != len(y):
                messagebox.showerror("学習エラー", "特徴量データまたはターゲットデータが空、または行数が一致しません。")
                self.update_status("エラー: 学習データ準備失敗")
                return

            print(f"モデル学習用データの準備完了。Shape X: {X.shape}, y: {y.shape}")

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
            print(f"データを分割しました: 訓練データ {len(X_train)}件, テストデータ {len(X_test)}件")

            print("LightGBMモデルを定義します...")
            lgbm_params = {
                'objective': 'binary', 'metric': 'auc', 'boosting_type': 'gbdt',
                'n_estimators': 1000, 'learning_rate': 0.05, 'num_leaves': 31,
                'max_depth': -1, 'min_child_samples': 20, 'subsample': 0.8,
                'colsample_bytree': 0.8, 'random_state': 42, 'n_jobs': -1, 'verbose': -1,
            }
            self.trained_model = lgb.LGBMClassifier(**lgbm_params)

            print("モデルの学習を開始します...")
            self.trained_model.fit(X_train, y_train,
                                   eval_set=[(X_test, y_test)],
                                   eval_metric='auc',
                                   callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=-1)])
            print("モデルの学習が完了しました。")
            self.update_status("モデル学習完了。評価中...")
            print("学習済みモデルを self.trained_model に保存しました。")

            # ... (以降のモデル保存、評価、プロット部分は前回提示したコードと同じなので省略しません) ...
            model_save_dir = self.settings.get("models_dir") # settings.json の "models_dir" を使う
            if not model_save_dir or not os.path.isdir(os.path.expanduser(model_save_dir)):
                default_models_dir = os.path.join(self.app_data_dir, "models")
                print(f"WARN: settingsのmodels_dir '{model_save_dir}' が無効または未設定のため、保存先を {default_models_dir} に設定します。")
                model_save_dir = default_models_dir
            
            if not os.path.exists(os.path.expanduser(model_save_dir)):
                try:
                    os.makedirs(os.path.expanduser(model_save_dir))
                    print(f"INFO: 保存用ディレクトリを作成しました: {os.path.expanduser(model_save_dir)}")
                except Exception as e_mkdir_model:
                    print(f"ERROR: モデル保存ディレクトリ作成失敗 ({os.path.expanduser(model_save_dir)}): {e_mkdir_model}")
                    print(f"WARN: 保存先をカレントディレクトリに変更します。")
                    model_save_dir = "." 
            else:
                 model_save_dir = os.path.expanduser(model_save_dir)

            model_filename = "trained_lgbm_model.pkl"
            features_filename = "model_features.pkl"
            imputation_filename = "imputation_values.pkl" # ★★★ 補完値ファイル名 ★★★

            model_filepath = os.path.join(model_save_dir, model_filename)
            features_filepath = os.path.join(model_save_dir, features_filename)
            imputation_filepath = os.path.join(model_save_dir, imputation_filename) # ★★★

            save_success_model = False
            save_success_features = False
            save_success_imputation = False # ★★★

            # モデルの保存 (pickleを使用)
            if self.trained_model is not None:
                save_success_model = self._save_pickle(self.trained_model, model_filepath)
            else:
                print("WARN: self.trained_model が None のため、モデルの保存をスキップしました。")

            # 特徴量リストの保存 (pickleを使用)
            if self.model_features: # self.model_features は get_dummies 後に更新されている
                save_success_features = self._save_pickle(self.model_features, features_filepath)
            else:
                print("WARN: self.model_features が空のため、特徴量リストの保存をスキップしました。")
            
            # ★★★ 欠損値補完のための値の保存 ★★★
            if hasattr(self, 'imputation_values_') and self.imputation_values_:
                save_success_imputation = self._save_pickle(self.imputation_values_, imputation_filepath)
                if not save_success_imputation:
                     print(f"ERROR: imputation_values_ の保存に失敗しました。 Path: {imputation_filepath}")
            else:
                print("WARN: self.imputation_values_ が存在しないか空のため、補完値の保存をスキップしました。")
            # ★★★ 修正ここまで ★★★

            # settings ファイルにパスを記録 (保存が成功した場合のみ)
            settings_updated = False
            if save_success_model:
                if self.settings.get("trained_model_path") != model_filepath:
                    self.settings["trained_model_path"] = model_filepath
                    settings_updated = True
            if save_success_features:
                if self.settings.get("model_features_path") != features_filepath:
                    self.settings["model_features_path"] = features_filepath
                    settings_updated = True
            if save_success_imputation: # ★★★
                if self.settings.get("imputation_values_path") != imputation_filepath:
                    self.settings["imputation_values_path"] = imputation_filepath
                    settings_updated = True
            
            if settings_updated: # settingsの内容が実際に更新された場合のみ保存
                self.save_settings()

            print("テストデータで予測を実行します...")
            y_pred_proba = self.trained_model.predict_proba(X_test)[:, 1]
            y_pred_binary = (y_pred_proba >= 0.5).astype(int) # 閾値0.5で2値化
            print("モデルの評価を行います...")
            auc = roc_auc_score(y_test, y_pred_proba)
            accuracy = accuracy_score(y_test, y_pred_binary)
            precision = precision_score(y_test, y_pred_binary, zero_division=0)
            recall = recall_score(y_test, y_pred_binary, zero_division=0)
            cm = confusion_matrix(y_test, y_pred_binary)
            eval_results_text = (
                f"モデル評価結果 (テストデータ):\n\nAUC Score: {auc:.4f}\n\n"
                f"--- 閾値 0.5 での評価 ---\nAccuracy (正解率): {accuracy:.4f}\n"
                f"Precision (適合率): {precision:.4f}\nRecall (再現率): {recall:.4f}\n\n"
                f"Confusion Matrix:\n{cm}\n(行: 実際の0/1, 列: 予測の0/1)"
            )
            print(f"  AUC Score: {auc:.4f}\n  Accuracy (Threshold 0.5): {accuracy:.4f}\n  Precision (Threshold 0.5): {precision:.4f}\n  Recall (Threshold 0.5): {recall:.4f}\n  Confusion Matrix (Threshold 0.5):\n{cm}")

            try:
                print("キャリブレーションプロットを作成します...")
                fig, ax = plt.subplots()
                CalibrationDisplay.from_estimator(self.trained_model, X_test, y_test, n_bins=10, ax=ax, strategy='uniform')
                ax.set_title('キャリブレーションプロット (テストデータ)')
                ax.set_xlabel('予測された3着以内確率の平均値'); ax.set_ylabel('観測された3着以内率')
                plt.grid(True)
                plot_save_dir = self.settings.get("plot_dir", self.settings.get("data_dir", "."))
                if not os.path.exists(plot_save_dir):
                    try: os.makedirs(plot_save_dir)
                    except Exception as e_mkdir_plot:
                        print(f"WARN: プロット保存ディレクトリ ({plot_save_dir}) 作成失敗: {e_mkdir_plot}"); plot_save_dir = "." 
                plot_filename = "calibration_plot.png"
                plot_filepath = os.path.join(plot_save_dir, plot_filename)
                plt.savefig(plot_filepath)
                print(f"キャリブレーションプロットを保存しました: {plot_filepath}")
                eval_results_text_with_plot_path = f"{eval_results_text}\n\nキャリブレーションプロットが {plot_filepath} として保存されました。"
                self.root.after(0, lambda: messagebox.showinfo("モデル評価結果", eval_results_text_with_plot_path))
                plt.close(fig)
            except PermissionError as e_perm:
                print(f"!!! ERROR during calibration plot creation (PermissionError): {e_perm}"); traceback.print_exc()
                self.root.after(0, lambda: messagebox.showerror("プロット保存エラー", f"キャリブレーションプロットの保存中にアクセス権限エラーが発生しました。\n詳細: {e_perm}\n\n{eval_results_text}"))
            except Exception as e_plot:
                print(f"!!! ERROR during calibration plot creation: {e_plot}"); traceback.print_exc()
                self.root.after(0, lambda: messagebox.showerror("プロット作成エラー", f"キャリブレーションプロットの作成・保存中にエラー:\n{e_plot}\n\n{eval_results_text}"))
            self.update_status("モデル学習と評価が完了しました。")
        except Exception as e:
            print(f"!!! FATAL ERROR in train_and_evaluate_model !!!"); traceback.print_exc()
            self.root.after(0, lambda: messagebox.showerror("モデル学習エラー", f"モデル学習・評価中に予期せぬエラー:\n{e}"))
            self.update_status(f"エラー: モデル学習失敗 ({e})")
        finally:
            print("--- Model Training and Evaluation Finished ---")
    
    
    def start_model_training_process(self):
        """
        モデル学習プロセスの開始点。
        データ準備とモデル学習・評価を順に実行する。
        """
        if not hasattr(self, 'combined_data') or self.combined_data is None or self.combined_data.empty:
            messagebox.showerror("データエラー", "学習の元となるデータ (combined_data) が読み込まれていません。\nデータ管理タブでデータを読み込んでください。")
            self.update_status("エラー: 元データ未読み込み")
            return

        # データ準備とモデル学習・評価をスレッドで実行
        self.run_in_thread(self._run_training_pipeline_thread)

    def _run_training_pipeline_thread(self):
        """
        データ準備からモデル学習・評価までを一連のパイプラインとして実行する (スレッド内処理)。
        """
        try:
            self.update_status("学習データ準備中...")
            print("INFO: _run_training_pipeline_thread: データ準備を開始します。")
            # 1. _prepare_data_for_model を呼び出して、特徴量とターゲットが結合されたDataFrameを取得
            #    target_column_name は train_and_evaluate_model のデフォルト値と合わせる
            target_col = 'target_rank_within_3' 
            prepared_data = self._prepare_data_for_model(target_column_name=target_col)

            if prepared_data is None or prepared_data.empty:
                # _prepare_data_for_model 内でエラーメッセージ表示とステータス更新が行われているはず
                print("ERROR: _run_training_pipeline_thread: _prepare_data_for_model が有効なデータを返しませんでした。")
                # self.root.after(0, lambda: messagebox.showerror("学習中止", "モデル学習用のデータの準備に失敗しました。ログを確認してください。"))
                # self.root.after(0, lambda: self.update_status("エラー: 学習データ準備失敗"))
                return

            # 2. 準備されたデータを train_and_evaluate_model に渡す
            #    processed_data 引数と target_column 引数を指定
            print(f"INFO: _run_training_pipeline_thread: モデル学習・評価を開始します。データShape: {prepared_data.shape}")
            self.train_and_evaluate_model(processed_data=prepared_data, target_column=target_col)
            
            # train_and_evaluate_model 内で最終的なステータス更新が行われる想定

        except Exception as e:
            print(f"!!! FATAL ERROR in _run_training_pipeline_thread !!!")
            traceback.print_exc() # トレースバックをコンソールに出力
            # GUIへのエラー通知 (メインスレッド経由)
            self.root.after(0, lambda err=e: messagebox.showerror("学習プロセスエラー", f"モデル学習プロセス全体で予期せぬエラーが発生しました:\n{type(err).__name__}: {err}"))
            self.root.after(0, lambda err=e: self.update_status(f"致命的エラー: 学習プロセス失敗 ({type(err).__name__})"))
    
    def format_shutuba_data(self,shutuba_table_list, race_id):
        """self.get_shutuba_tableの結果をDataFrameに整形"""
        if not shutuba_table_list or len(shutuba_table_list) < 2:
            return None
        header = [h.replace(' ', '').replace('\n', '') for h in shutuba_table_list[0]]
        data_rows = shutuba_table_list[1:]
        try:
            # 列名統一マップ (出馬表用)
            rename_map = {
                '枠': 'Waku', '馬番': 'Umaban', '印': 'Mark', '馬名': 'HorseName',
                '性齢': 'SexAge', '斤量': 'Load', '騎手': 'JockeyName', '厩舎': 'TrainerName',
                '馬体重(増減)': 'WeightInfoShutuba', '馬体重': 'WeightInfoShutuba', # 事前発表の場合
                'オッズ': 'OddsShutuba', '単勝': 'OddsShutuba', # 結果とかぶらないように
                '人気': 'NinkiShutuba'
            }
            # 提供されたコードで取得したヘッダーに合わせて調整
            header_renamed = [rename_map.get(h.strip(), h.strip()) for h in header]

            # DataFrame作成 (列数が一致するか確認)
            if len(data_rows[0]) != len(header_renamed):
                 print(f"      警告: 出馬表テーブルのヘッダー({len(header_renamed)})とデータ({len(data_rows[0])})の列数が不一致です。スキップします。({race_id})")
                 print(f"      Header: {header_renamed}")
                 print(f"      Data[0]: {data_rows[0]}")
                 return None

            df = pd.DataFrame(data_rows, columns=header_renamed)

            df['race_id'] = race_id
            # 型変換など (結果データと同様に)
            numeric_cols = ['Waku', 'Umaban', 'Load', 'OddsShutuba', 'NinkiShutuba']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            if 'WeightInfoShutuba' in df.columns:
                df['WeightShutuba'] = df['WeightInfoShutuba'].str.extract(r'(\d+)', expand=False).astype(float)
                # 増減情報は出馬表段階でないことが多い
                # df['WeightDiffShutuba'] = df['WeightInfoShutuba'].str.extract(r'\(([-+]?\d+)\)', expand=False).astype(float)
                # df.drop('WeightInfoShutuba', axis=1, inplace=True, errors='ignore')

            if 'SexAge' in df.columns:
                 df['Sex'] = df['SexAge'].str[0]
                 df['Age'] = pd.to_numeric(df['SexAge'].str[1:], errors='coerce')

            # 馬ID, 騎手IDなどをリンクから取得 (オプション)

            return df

        except ValueError as ve:
             print(f"    エラー: 出馬表DataFrame作成時の列数不一致など ({race_id}): {ve}")
        except Exception as e:
            print(f"    エラー: 出馬表DataFrameの整形中にエラー ({race_id}): {e}")
            traceback.print_exc()
        return None

    def format_payout_data(self, payouts_list, race_id): 
        """self.get_pay_tableの結果を整形して辞書で返す"""
        payouts_dict = {'race_id': race_id}
        if not payouts_list: return payouts_dict
        print(f"      DEBUG PAYOUT Start: Processing {len(payouts_list)} rows for {race_id}")
        current_type = None
        #bet_type_keywords = ['単勝', '複勝', '枠連', '馬連', 'ワイド', '馬単', '三連複', '三連単']

        for i, row_orig in enumerate(payouts_list):
            # print(f"        DEBUG PAYOUT Row {i} Original: {row_orig}")
            try:
                row = [cell.strip() for cell in row_orig if isinstance(cell, str)]
                row = [cell for cell in row if cell]
                # print(f"        DEBUG PAYOUT Row {i} Stripped: {row}")
                if not row: continue

                bet_type_jp = row[0].strip()
                # print(f"        DEBUG PAYOUT Row {i} repr(bet_type_jp): {repr(bet_type_jp)}") # ★ reprで確認
                # ★ 3連複・3連単の判定のため 'in' を使う判定に戻す
                
                # ★★★ is_bet_type の判定方法を変更 ★★★
                is_bet_type = False
                if bet_type_jp == '単勝': is_bet_type = True
                elif bet_type_jp == '複勝': is_bet_type = True
                elif bet_type_jp == '枠連': is_bet_type = True
                elif bet_type_jp == '馬連': is_bet_type = True
                elif bet_type_jp == 'ワイド': is_bet_type = True
                elif bet_type_jp == '馬単': is_bet_type = True
                elif bet_type_jp == '3連複': is_bet_type = True # ★直接比較
                elif bet_type_jp == '3連単': is_bet_type = True # ★直接比較
                # ★★★★★★★★★★★★★★★★★★★★★★★★★

                # print(f"        DEBUG PAYOUT Row {i}: bet_type_jp='{bet_type_jp}', is_bet_type={is_bet_type}, current_type='{current_type}'")

                temp_current_type = None
                data_cells = []

                if is_bet_type:
                    temp_current_type = bet_type_jp
                    data_cells = row[1:]
                    current_type = temp_current_type # is_bet_type の時だけ更新
                    # print(f"        DEBUG PAYOUT Row {i}: Found bet_type '{current_type}', data_cells={data_cells}")
                elif current_type in ['複勝', 'ワイド'] and len(row) >= 2:
                    temp_current_type = current_type
                    data_cells = row
                    # print(f"        DEBUG PAYOUT Row {i}: Continuing bet_type '{current_type}', data_cells={data_cells}")
                else:
                    # print(f"        DEBUG PAYOUT Row {i}: Skipping unknown row format.")
                    continue

                if not current_type: continue
                # print(f"        DEBUG PAYOUT Row {i}: Determined Type='{current_type}'")

                if len(data_cells) >= 2:
                    numbers_str = data_cells[0]
                    payouts_str = data_cells[1]
                    ninki_str = data_cells[2] if len(data_cells) > 2 else None

                    num_list = numbers_str.split('\n')
                    payout_list_cleaned = [p.replace(',', '').replace('円', '') for p in payouts_str.split('\n')]
                    ninki_list_cleaned = [n.replace('人気', '') for n in ninki_str.split('\n')] if ninki_str else [None] * len(num_list)

                   #  print(f"        DEBUG PAYOUT Row {i}: numbers={num_list}, payouts_cleaned={payout_list_cleaned}, ninki_cleaned={ninki_list_cleaned}")

                    payout_vals = [int(p) if p and p.isdigit() else None for p in payout_list_cleaned]
                    ninki_vals = [int(n) if n and n.isdigit() else None for n in ninki_list_cleaned]

                    # print(f"        DEBUG PAYOUT Row {i}: payout_vals={payout_vals}, ninki_vals={ninki_vals}")
                    # print(f"        DEBUG PAYOUT Row {i}: len(num_list)={len(num_list)}, len(payout_vals)={len(payout_vals)}, len(ninki_vals)={len(ninki_vals)}") # ★デバッグプリント追加済

                    # --- 辞書への格納 ---
                    type_key = current_type
                    if type_key not in payouts_dict:
                        payouts_dict[type_key] = {'馬番': [], '払戻金': []}
                        # 人気キーは実際に値がある場合のみ、後で作成する

                    # ★★★★★ リスト長を合わせる処理 (ワイド対応版) ★★★★★
                    target_len = len(num_list)
                    payout_vals_extended = []
                    ninki_vals_extended = [] # ここでは初期化のみ

                    # --- 払い戻しリスト長の調整 ---
                    if len(payout_vals) == target_len:
                        payout_vals_extended = payout_vals
                    elif len(payout_vals) == 1 and target_len > 1:
                        payout_vals_extended = payout_vals * target_len
                    elif type_key == 'ワイド' and target_len == 6 and len(payout_vals) == 3:
                        payout_vals_extended = [p for p in payout_vals for _ in range(2)] # [p1,p1, p2,p2, p3,p3]
                    else:
                        payout_vals_extended = [None] * target_len
                        if payout_vals:
                             print(f"      警告: 払い戻しリスト長異常 ({race_id}, {type_key}) - Num:{len(num_list)}, Pay:{len(payout_vals)}")

                    # --- 人気リスト長の調整 ---
                    ninki_exists = any(n is not None for n in ninki_vals) # None以外の人気があるか
                    if ninki_exists:
                        if len(ninki_vals) == target_len:
                            ninki_vals_extended = ninki_vals
                        elif len(ninki_vals) == 1 and target_len > 1:
                            ninki_vals_extended = ninki_vals * target_len
                        elif type_key == 'ワイド' and target_len == 6 and len(ninki_vals) == 3:
                            ninki_vals_extended = [n for n in ninki_vals for _ in range(2)]
                        else:
                            ninki_vals_extended = [None] * target_len
                            if ninki_vals:
                                 print(f"      警告: 人気リスト長異常 ({race_id}, {type_key}) - Num:{len(num_list)}, Ninki:{len(ninki_vals)}")
                    else:
                         ninki_vals_extended = [None] * target_len

                    # デバッグ表示
                    # print(f"        DEBUG PAYOUT Row {i}: Extended lengths - Pay:{len(payout_vals_extended)}, Ninki:{len(ninki_vals_extended)}")

                    # --- 調整後のリストで辞書を更新 ---
                    payouts_dict[type_key]['馬番'].extend(num_list)
                    payouts_dict[type_key]['払戻金'].extend(payout_vals_extended)
                    # 人気リストは、None以外の値が調整後にも存在する場合のみ追加
                    if any(n is not None for n in ninki_vals_extended):
                        if '人気' not in payouts_dict[type_key]:
                            payouts_dict[type_key]['人気'] = []
                        payouts_dict[type_key]['人気'].extend(ninki_vals_extended)
                    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★

                    # print(f"        DEBUG PAYOUT Row {i}: Updated dict[{type_key}]: {payouts_dict[type_key]}")

            except Exception as e_pay:

                 # print(f"      警告: 払い戻しデータ行の処理中にエラー発生 ({race_id}): {e_pay} - Row Original: {row_orig}")
                 traceback.print_exc()

        # --- ループ後の整形処理 ---
        # (リスト長チェックは不要になったのでコメントアウトまたは削除)
        # for key in list(payouts_dict.keys()):
        #     if key != 'race_id':
        #          len_b = len(payouts_dict[key].get('馬番', []))
        #          len_p = len(payouts_dict[key].get('払戻金', []))
        #          len_n = len(payouts_dict[key].get('人気', [])) if '人気' in payouts_dict[key] else len_b
        #          if not (len_b == len_p == len_n):
        #               print(f"      警告: 最終的な払い戻しデータのリスト長不一致 ({race_id}, {key}) - 馬番:{len_b}, 払戻:{len_p}, 人気:{len_n}")
        #          if '人気' in payouts_dict[key]:
        #              if all(n is None for n in payouts_dict[key]['人気']):
        #                  del payouts_dict[key]['人気']

        print(f"      DEBUG: format_payout_dataの結果 (race_id: {race_id}): {payouts_dict}")
        return payouts_dict        

    # ここまで貼ってあった ここは655行

    # --- データ取得・結合・整形メイン関数 (horse_idマージ修正・デバッグ強化版) ---
    def scrape_and_process_race_data(self, race_id, date_str): # date_str は現状未使用
        """指定されたrace_idのレースデータを取得・整形して返す"""
        print(f"      処理開始: {race_id}")

        # 1. 出馬表取得
        shutuba_data_dict = self.get_shutuba_table(race_id)

        race_common_info_from_shutuba = {}
        shutuba_horse_list_for_format = []

        if shutuba_data_dict and isinstance(shutuba_data_dict, dict):
            race_common_info_from_shutuba = shutuba_data_dict.get('race_details', {})
            shutuba_horse_list_for_format = shutuba_data_dict.get('horse_list', [])
        shutuba_df = self.format_shutuba_data(shutuba_horse_list_for_format, race_id)

        # 2. レース結果とレース情報を取得
        race_info_dict, result_list = self.get_result_table(race_id)
        result_df = self.format_result_data(result_list, race_id) # horse_id はここで抽出されるはず

        # 3. 払い戻し取得
        payout_list = self.get_pay_table(race_id)
        payout_dict = self.format_payout_data(payout_list, race_id)

        # 4. データの結合とレース情報の追加
        combined_df = None
        base_df = result_df # 結果DFがベース (horse_id が含まれるはず)

        if base_df is not None:
            # レース情報を列として追加
            if race_info_dict:
                print(f"      レース情報を結合します: {list(race_info_dict.keys())}")
                for key, value in race_info_dict.items():
                    base_df[key] = value
            else:
                print(f"      警告: レース情報辞書が空です ({race_id})")

        # --- 出馬表と結果+レース情報を結合 ---
        if shutuba_df is not None and base_df is not None:
            try:
                merge_on_cols = ['Umaban']
                if 'race_id' in base_df.columns and 'race_id' in shutuba_df.columns:
                    merge_on_cols.append('race_id')

                # キー列の型を合わせる
                for col in merge_on_cols:
                    if col == 'Umaban':
                        base_df[col] = pd.to_numeric(base_df[col], errors='coerce')
                        shutuba_df[col] = pd.to_numeric(shutuba_df[col], errors='coerce')
                    else:
                        base_df[col] = base_df[col].astype(str)
                        shutuba_df[col] = shutuba_df[col].astype(str)

                # 不要列を削除してからマージ
                cols_to_drop_from_shutuba = ['HorseName', 'SexAge', 'Load', 'JockeyName', 'TrainerName', 'Sex', 'Age', 'WeightShutuba', 'WeightDiffShutuba', 'OddsShutuba', 'NinkiShutuba']
                shutuba_df_merged = shutuba_df.drop(columns=[col for col in cols_to_drop_from_shutuba if col in shutuba_df.columns], errors='ignore')

                # ★★★ デバッグ強化: drop 前後の horse_id を確認 ★★★
                print(f"      DEBUG TYPE before drop: shutuba_df_merged['horse_id'] exists: {'horse_id' in shutuba_df_merged.columns}, dtype: {shutuba_df_merged['horse_id'].dtype if 'horse_id' in shutuba_df_merged.columns else 'N/A'}")
                if 'horse_id' in shutuba_df_merged.columns:
                    # drop を実行
                    shutuba_df_merged = shutuba_df_merged.drop(columns=['horse_id'])
                    print("      DEBUG MERGE: Dropped 'horse_id' from shutuba_df_merged.")
                    # drop 後の状態を確認
                    print(f"      DEBUG TYPE after drop: shutuba_df_merged['horse_id'] exists: {'horse_id' in shutuba_df_merged.columns}") # dropされたか確認
                else:
                     print("      DEBUG MERGE: 'horse_id' not found in shutuba_df_merged before drop.")
                # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

                # マージ前の列名と base_df の horse_id 型を確認
                print(f"      DEBUG TYPE before merge: base_df['horse_id'] exists: {'horse_id' in base_df.columns}, dtype: {base_df['horse_id'].dtype if 'horse_id' in base_df.columns else 'N/A'}") # 追加
                print(f"      DEBUG MERGE: Columns in base_df (results+info): {base_df.columns.tolist()}")
                print(f"      DEBUG MERGE: Columns in shutuba_df_merged (after dropping horse_id): {shutuba_df_merged.columns.tolist()}")
                print(f"      DEBUG MERGE: Merging on columns: {merge_on_cols}")

                # マージ実行
                combined_df = pd.merge(base_df, shutuba_df_merged, on=merge_on_cols, how='left')

                # マージ後の列名を確認
                print(f"      DEBUG MERGE: Columns in combined_df after merge: {combined_df.columns.tolist()}") # ここで horse_id が一つのはず

                print(f"      結合完了: {combined_df.shape}")

            except Exception as e_merge:
                print(f"      エラー: 出馬表と結果の結合中にエラー ({race_id}): {e_merge}")
                combined_df = base_df
                traceback.print_exc()

        elif base_df is not None:
            print("      情報: 結果(レース情報含む)データのみ取得しました。")
            combined_df = base_df
        # else: combined_df は None のまま

        print(f"      処理完了: {race_id}")

        # ★★★ デバッグプリントを修正 (Agari も確認) ★★★
        if combined_df is not None and not combined_df.empty:
            # 表示したい列名をリストアップ (Agari を追加)
            # ↓↓↓ この行を追加 ↓↓↓
            print(f"      DEBUG scrape_and_process: Final combined_df columns: {combined_df.columns.tolist()}")
            # ↑↑↑ ここまで追加 ↑↑↑
            
            cols_to_print = ['HorseName', 'horse_id', 'father', 'mother_father', 'Rank', 'Diff', 'Agari','date']
            existing_cols = [col for col in cols_to_print if col in combined_df.columns] # 実際に存在する列だけを選ぶ
            if existing_cols:
                print("      DEBUG SCRAPE: Checking combined_df head for available columns:")
                try:
                    print(combined_df[existing_cols].head()) # 存在する列だけ表示
                except Exception as e_print:
                    print(f"      ERROR printing combined_df head: {e_print}")
            else:
                # もしリストアップした列が一つも存在しない場合
                print(f"      WARN: None of {cols_to_print} found in combined_df. All columns: {combined_df.columns.tolist()}")
        elif combined_df is not None: print(f"      WARN: combined_df is empty.")
        else: print(f"      WARN: combined_df is None.")
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★

        return combined_df, payout_dict

    # --- 期間指定データ収集メイン関数 ---
    def collect_race_data_for_period(self, start_year, start_month, end_year, end_month):
        """指定された期間のレースデータを収集し、DataFrameと払い戻しリストを返す"""
        all_combined_results_list = []
        all_payouts_list = []
        processed_race_ids = set()
        processed_log_file_path = self.PROCESSED_LOG_FILE

        # --- 処理済レースIDの読み込み ---
        try:
            if os.path.exists(processed_log_file_path):
                with open(processed_log_file_path, "r", encoding="utf-8") as f:
                    processed_race_ids = set(line.strip() for line in f if line.strip())
                self.update_status(f"処理済レースID {len(processed_race_ids)}件読込")
                print(f"処理済みレースIDを {len(processed_race_ids)} 件読み込みました。({processed_log_file_path})")
        except Exception as e:
            self.update_status(f"エラー: 処理済ID読込失敗")
            print(f"処理済みレースIDファイルの読み込みエラー: {e}")

        current_year = start_year
        current_month = start_month
        total_processed_in_run = 0
        log_file_handle = None

        try:
            log_file_handle = open(processed_log_file_path, "a", encoding="utf-8")
            # debug_target_date_processed = False # デバッグフラグは不要なので削除

            while not (current_year > end_year or (current_year == end_year and current_month > end_month)):
                # if debug_target_date_processed: # デバッグ用break削除
                #     break

                month_str = f"{current_year}年{current_month}月"
                self.update_status(f"{month_str} 処理開始...")
                print(f"\n--- {month_str} の処理を開始 ---")

                kaisai_dates = self.get_kaisai_dates(current_year, current_month) # 変数名 kaisai_dates に戻す

                if not kaisai_dates:
                    self.update_status(f"{month_str} 開催日なし")
                    print("  開催日が見つかりませんでした。")
                else:
                    self.update_status(f"{month_str} 開催日 {len(kaisai_dates)}日 取得")
                    print(f"  開催日 ({len(kaisai_dates)}日): {', '.join(kaisai_dates)}")

                    # ↓↓↓ ★★★★★ ここにデバッグコードを追加/有効化 ★★★★★ ↓↓↓
                    target_date_str = "20180331" # ← ★テストしたい日付に変更★
                    process_target_date_only = False # ★ Trueにすると有効になる

                    if process_target_date_only:
                        if target_date_str.startswith(f"{current_year}{current_month:02d}"):
                            if target_date_str in kaisai_dates:
                                print(f"  デバッグ: {target_date_str} のみ処理します。")
                                # kaisai_dates を上書きせず、処理対象リストを変える
                                # kaisai_dates_to_process = [target_date_str] # 使用後は前に＃入れる！！！
                            else:
                                print(f"  デバッグ: {target_date_str} は開催日リストに含まれていません。この月はスキップします。")
                                kaisai_dates = [] # ★ kaisai_datesを空にする
                        else:
                             print(f"  デバッグ: ターゲット年月でないため {month_str} をスキップします。")
                             kaisai_dates = [] # ★ kaisai_datesを空にする

                        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

                    # ↓↓↓ このループ全体が対象 ↓↓↓
                    for date_str_loop in kaisai_dates: # ★ ループ変数名を変更 (date_str は内側で使うため)
                        self.update_status(f"{date_str_loop} レースID取得中...")

                        # ★★★ get_race_ids は (race_id, date_str) のリストを返すと想定 ★★★
                        race_data_list_on_date = self.get_race_ids(date_str_loop) # 戻り値を受け取る

                        if not race_data_list_on_date:
                             pass
                        else:
                             self.update_status(f"{date_str_loop}: レースID {len(race_data_list_on_date)}件 取得")
                             print(f"    取得したレースID: {len(race_data_list_on_date)}件")

                             num_races_on_date = len(race_data_list_on_date)
                             # ★★★ ループで race_id と date_str を受け取る ★★★
                             for i, (race_id, date_str) in enumerate(race_data_list_on_date): # ★ タプルを展開
                                 # ↓↓↓ 比較するのは race_id のみ ↓↓↓
                                 if race_id in processed_race_ids:
                                     continue

                                 self.update_status(f"{date_str} [{i+1}/{num_races_on_date}]: {race_id} 処理中...")
                                 try:
                                     # ★★★ scrape_and_process_race_data に date_str も渡す ★★★
                                     combined_df, payout_dict = self.scrape_and_process_race_data(race_id, date_str)

                                     if combined_df is not None: all_combined_results_list.append(combined_df)
                                     if payout_dict and len(payout_dict) > 1: all_payouts_list.append(payout_dict)

                                     # ↓↓↓ ログに記録するのは race_id のみ ↓↓↓
                                     processed_race_ids.add(race_id)
                                     total_processed_in_run += 1
                                     log_file_handle.write(f"{race_id}\n") # ★ race_id のみ書き込み
                                     log_file_handle.flush()

                                 except Exception as e_scrape:
                                      self.update_status(f"エラー: データ処理中 ({race_id})")
                                      print(f"\n!!!!!!!!! エラー発生 (race_id: {race_id}) !!!!!!!!!")
                                      traceback.print_exc()
                                      print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")

                                 time.sleep(self.SLEEP_TIME_PER_RACE)
             
                    
                # 次の月へ (正しいインデント位置)
                if current_month == 12:
                    current_month = 1; current_year += 1
                else:
                    current_month += 1
            # --- while ループ終了 ---
    
        except KeyboardInterrupt:
            print("\nKeyboardInterrupt: 処理を中断します...")
            self.update_status("処理中断 (Ctrl+C)")
        except Exception as e_main:
             print(f"\n!!!!!!!!! メインループで予期せぬエラー !!!!!!!!!")
             self.update_status(f"エラー: メインループ異常終了")
             traceback.print_exc()
        finally:
            if log_file_handle:
                try:
                    log_file_handle.close()
                    print("処理済みログファイルを閉じました。")
                except Exception as e_close:
                     print(f"処理済みログファイルのクローズエラー: {e_close}")

        self.update_status(f"データ収集完了/中断 ({total_processed_in_run}レース処理)")
        print("\n--- データ収集ループ終了 ---")

        # データ結合処理 (変更なし)
        if not all_combined_results_list:
            print("収集されたレース結果データがありません。")
            final_combined_df = pd.DataFrame()
        else:
            try:
                 final_combined_df = pd.concat(all_combined_results_list, ignore_index=True)
                 print(f"最終的な結合レースデータ: {final_combined_df.shape}")
            except Exception as e_concat:
                self.update_status("エラー: データ結合失敗")
                print(f"エラー: 最終データの結合中にエラー: {e_concat}")
                traceback.print_exc()
                final_combined_df = pd.DataFrame()

        return final_combined_df, all_payouts_list
    
       
    def ensure_directories_exist(self):
        """アプリケーション用のディレクトリを作成"""
        # 設定ファイルで定義されたパスを使用
        data_dir = self.settings.get("data_dir", os.path.join(self.app_data_dir, "data"))
        models_dir = self.settings.get("models_dir", os.path.join(self.app_data_dir, "models"))
        results_dir = self.settings.get("results_dir", os.path.join(self.app_data_dir, "results"))

        # ディレクトリが存在しない場合は作成
        for directory in [self.app_data_dir, data_dir, models_dir, results_dir]:
            if not os.path.exists(directory):
                try:
                    os.makedirs(directory)
                    print(f"ディレクトリを作成しました: {directory}")
                except Exception as e:
                    self.update_status(f"エラー: ディレクトリ作成失敗 {directory} ({e})")
                    messagebox.showerror("ディレクトリ作成エラー", f"ディレクトリの作成に失敗しました:\n{directory}\nエラー: {e}")

    def init_home_tab(self):
        """ホームタブの初期化"""
        # タイトルとロゴ
        title_frame = ttk.Frame(self.tab_home)
        title_frame.pack(fill=tk.X, padx=20, pady=20)

        title_label = ttk.Label(title_frame, text="競馬データ分析ツール", font=("Meiryo UI", 24, "bold"))
        title_label.pack(pady=10)

        subtitle_label = ttk.Label(title_frame, text="プラス収支を目指すデータ分析と戦略提案", font=("Meiryo UI", 14))
        subtitle_label.pack(pady=5)

        # 機能概要
        features_frame = ttk.LabelFrame(self.tab_home, text="主な機能")
        features_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        features = [
            "競馬データの収集と管理 (netkeiba, JRA-VAN, ローカルCSV等)",
            "データに基づいた多角的な分析 (特徴量重要度, コース適性, 血統など)",
            "機械学習モデル等による着順予測",
            "期待値とケリー基準に基づいた馬券購入戦略の提案",
            "過去データを用いたバックテストによる戦略の検証",
            "資金管理と収益性分析"
        ]

        for i, feature in enumerate(features):
            feature_label = ttk.Label(features_frame, text=f"• {feature}", font=("Meiryo UI", 12))
            feature_label.grid(row=i, column=0, sticky=tk.W, padx=20, pady=5)

        # クイックスタートボタン
        button_frame = ttk.Frame(self.tab_home)
        button_frame.pack(fill=tk.X, padx=20, pady=20)

        start_button = ttk.Button(button_frame, text="データ管理を開始", command=lambda: self.tab_control.select(1))
        start_button.pack(side=tk.LEFT, padx=10)

        analysis_button = ttk.Button(button_frame, text="分析を開始", command=lambda: self.tab_control.select(2))
        analysis_button.pack(side=tk.LEFT, padx=10)

        prediction_button = ttk.Button(button_frame, text="予測を開始", command=lambda: self.tab_control.select(3))
        prediction_button.pack(side=tk.LEFT, padx=10)

    def init_data_tab(self):
        """データ管理タブの初期化"""
        # 左側のフレーム（データソース選択）
        left_frame = ttk.LabelFrame(self.tab_data, text="データソース")
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10) # expand=False

        # データソースオプション
        source_label = ttk.Label(left_frame, text="データソースの選択:")
        source_label.grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)

        self.data_source_var = tk.StringVar(value="ローカルファイル") # デフォルトを変更
        source_combo = ttk.Combobox(left_frame, textvariable=self.data_source_var, state="readonly", width=15)
        source_combo['values'] = ("netkeiba (期間指定)", "JRA-VAN (未実装)", "JRDB (未実装)", "ローカルファイル")
        source_combo.grid(row=0, column=1, sticky=tk.EW, padx=10, pady=5)
        source_combo.bind("<<ComboboxSelected>>", self.toggle_local_file_widgets) # 選択変更時のイベント

        # 期間選択 (netkeiba等用、ローカルファイルでは使わないかも)
        period_label = ttk.Label(left_frame, text="データ期間 (Web取得用):")
        period_label.grid(row=1, column=0, sticky=tk.W, padx=10, pady=5)

        self.period_frame = ttk.Frame(left_frame) # period_frameをクラス変数に
        self.period_frame.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)

        from_label = ttk.Label(self.period_frame, text="開始:")
        from_label.grid(row=0, column=0, sticky=tk.W)

        current_year = datetime.now().year
        years = tuple(str(year) for year in range(2010, current_year + 1))
        months = tuple(f"{month:02d}" for month in range(1, 13))

        self.from_year_var = tk.StringVar(value=str(current_year - 5)) # 5年前に設定
        from_year_combo = ttk.Combobox(self.period_frame, textvariable=self.from_year_var, width=5, state="readonly", values=years)
        from_year_combo.grid(row=0, column=1, padx=2)

        self.from_month_var = tk.StringVar(value="01")
        from_month_combo = ttk.Combobox(self.period_frame, textvariable=self.from_month_var, width=3, state="readonly", values=months)
        from_month_combo.grid(row=0, column=2, padx=2)

        to_label = ttk.Label(self.period_frame, text="終了:")
        to_label.grid(row=0, column=3, sticky=tk.W, padx=5)

        self.to_year_var = tk.StringVar(value=str(current_year))
        to_year_combo = ttk.Combobox(self.period_frame, textvariable=self.to_year_var, width=5, state="readonly", values=years)
        to_year_combo.grid(row=0, column=4, padx=2)

        self.to_month_var = tk.StringVar(value=datetime.now().strftime("%m"))
        to_month_combo = ttk.Combobox(self.period_frame, textvariable=self.to_month_var, width=3, state="readonly", values=months)
        to_month_combo.grid(row=0, column=5, padx=2)

        # ローカルファイル選択
        self.file_label = ttk.Label(left_frame, text="レース結果 CSV:") # ラベルもクラス変数に
        self.file_label.grid(row=2, column=0, sticky=tk.W, padx=10, pady=5)

        self.file_frame = ttk.Frame(left_frame) # file_frameもクラス変数に
        self.file_frame.grid(row=2, column=1, sticky=tk.EW, padx=10, pady=5)
        left_frame.columnconfigure(1, weight=1) # 横幅に追従させる

        self.file_path_var = tk.StringVar()
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path_var, width=30) # entryもクラス変数に
        self.file_entry.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.browse_button = ttk.Button(self.file_frame, text="参照", command=self.browse_file) # buttonもクラス変数に
        self.browse_button.pack(side=tk.LEFT)

        # データ取得/読み込みボタン
        fetch_button = ttk.Button(left_frame, text="データ取得 / 読み込み", command=self.start_data_fetching)
        fetch_button.grid(row=3, column=0, columnspan=2, pady=20)
        
        train_button = ttk.Button(self.tab_data, text="モデル学習＆評価", command=self.start_model_training_process)
        train_button.pack(side=tk.BOTTOM, pady=15) # side=tk.BOTTOM で下部に配置
        
        # --- 一時的なキャッシュ保存ボタン ---
        save_cache_button = ttk.Button(self.tab_data, text="今のキャッシュを保存", command=self.save_cache_to_file)
        save_cache_button.pack(pady=10) # または grid() などで配置
        # --- ここまで ---

        # 右側のフレーム（データプレビュー）
        right_frame = ttk.LabelFrame(self.tab_data, text="データプレビュー") 
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10) 

        # データタイプ選択 (結合データも表示できるように変更)
        data_type_frame = ttk.Frame(right_frame)
        data_type_frame.pack(fill=tk.X, padx=10, pady=5)

        self.data_type_var = tk.StringVar(value="combined") # デフォルトを結合データに
        combined_radio = ttk.Radiobutton(data_type_frame, text="結合データ", variable=self.data_type_var, value="combined", command=self.update_data_preview)
        combined_radio.pack(side=tk.LEFT, padx=5)
        race_radio = ttk.Radiobutton(data_type_frame, text="レースデータ (Raw)", variable=self.data_type_var, value="race", command=self.update_data_preview)
        race_radio.pack(side=tk.LEFT, padx=5)
        horse_radio = ttk.Radiobutton(data_type_frame, text="馬データ (Raw)", variable=self.data_type_var, value="horse", command=self.update_data_preview)
        horse_radio.pack(side=tk.LEFT, padx=5)
        result_radio = ttk.Radiobutton(data_type_frame, text="結果データ (Raw)", variable=self.data_type_var, value="result", command=self.update_data_preview)
        result_radio.pack(side=tk.LEFT, padx=5)


        # データプレビューテーブル
        preview_frame = ttk.Frame(right_frame)
        preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        y_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.VERTICAL)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar = ttk.Scrollbar(preview_frame, orient=tk.HORIZONTAL)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.preview_tree = ttk.Treeview(preview_frame,
                                        yscrollcommand=y_scrollbar.set,
                                        xscrollcommand=x_scrollbar.set,
                                        height=10) # 高さを指定
        self.preview_tree.pack(fill=tk.BOTH, expand=True)
        y_scrollbar.config(command=self.preview_tree.yview)
        x_scrollbar.config(command=self.preview_tree.xview)

        # データ保存ボタン (結合データの保存も考慮)
        save_button = ttk.Button(right_frame, text="表示中データを保存", command=self.save_data)
        save_button.pack(pady=10, anchor=tk.E)

        # 初期状態でローカルファイルウィジェットを表示
        self.toggle_local_file_widgets()

    def toggle_local_file_widgets(self, event=None):
        """データソースに応じてウィジェットの表示/非表示を切り替える"""
        source = self.data_source_var.get()
        if "ローカルファイル" in source:
            # ローカルファイル関連を有効化
            self.file_label.grid()
            self.file_frame.grid()
            # 期間選択関連を無効化 (グレーアウト)
            for widget in self.period_frame.winfo_children():
                widget.configure(state=tk.DISABLED)
        else:
            # ローカルファイル関連を無効化
            self.file_label.grid_remove()
            self.file_frame.grid_remove()
            # 期間選択関連を有効化
            for widget in self.period_frame.winfo_children():
                widget.configure(state=tk.NORMAL if isinstance(widget, (ttk.Label, ttk.Combobox)) else tk.DISABLED) # Comboboxはreadonlyにするかも


    # ===========================================================
    # === データ取得/読み込み関連のメソッド (ここから追加) ===
    # ===========================================================

    def start_data_fetching(self):
        """データソースに応じてデータ取得/読み込み処理を開始"""
        source = self.data_source_var.get()
        # print(f"DEBUG: データソースとして認識された値は → '{source}'")
        self.update_status(f"{source} から処理開始...")

        if "netkeiba" in source: # "netkeiba (期間指定)" が選択された場合
            try:
                start_year = int(self.from_year_var.get())
                start_month = int(self.from_month_var.get())
                end_year = int(self.to_year_var.get())
                end_month = int(self.to_month_var.get())
                # 簡単な期間チェック
                start_date = datetime(start_year, start_month, 1)
                end_date = datetime(end_year, end_month, 1)
                if start_date > end_date:
                     messagebox.showerror("期間エラー", "開始年月が終了年月より後になっています。")
                     self.update_status("エラー: 期間設定不正")
                     return
                # 未来の日付チェック (オプション)
                # if end_date > datetime.now():
                #    if not messagebox.askyesno("未来日付確認", "終了年月が未来の日付ですが、よろしいですか？\n(まだ存在しないデータは取得できません)"):
                #        self.update_status("処理中断")
                #        return

                self.update_status(f"netkeibaデータ収集開始: {start_year}/{start_month} - {end_year}/{end_month}")
                # ★ netkeiba収集処理を別スレッドで実行
                self.run_in_thread(self.run_netkeiba_collection, start_year, start_month, end_year, end_month)

            except ValueError:
                messagebox.showerror("期間エラー", "期間の年または月が正しく選択されていません。")
                self.update_status("エラー: 期間設定不正")

        elif "ローカルファイル" in source: # "ローカルファイル" が選択された場合
            csv_file_path = self.file_path_var.get()
            json_file_path = None
            # JSONファイルのパスをCSVファイル名から類推する例
            if csv_file_path:
                 base, _ = os.path.splitext(csv_file_path)
                 # 命名規則の候補をいくつか試す
                 potential_json_names = [
                     base.replace("_combined_", "_payouts_") + ".json",
                     base.replace("_results_", "_payouts_") + ".json",
                     base + "_payouts.json" # 単純に末尾に追加
                 ]
                 for potential_json in potential_json_names:
                     if os.path.exists(potential_json):
                          json_file_path = potential_json
                          print(f"関連JSONファイルを自動検出: {json_file_path}")
                          break # 見つかったらループ終了


            if not csv_file_path or not os.path.exists(csv_file_path):
                messagebox.showerror("ファイルエラー", "有効なCSVファイルが選択されていません。")
                self.update_status("エラー: CSVファイル未選択")
                return

            self.update_status(f"ローカルファイル読み込み開始: {os.path.basename(csv_file_path)}")
            # ★ ローカルファイル読み込み処理を別スレッドで実行
            self.run_in_thread(self.load_local_files, csv_file_path, json_file_path) # JSONパスも渡す

        else: # その他の未実装ソースが選択された場合
            messagebox.showinfo("未実装", f"{source} からのデータ取得は現在実装されていません。")
            self.update_status("準備完了")

    def run_netkeiba_collection(self, start_year, start_month, end_year, end_month):
        """netkeibaデータ収集をバックグラウンドで実行し、結果を格納・保存する"""
        try:
            # ★ 移植したデータ収集メイン関数を呼び出す (selfを付ける)
            final_combined_df, final_payouts_list = self.collect_race_data_for_period(
                start_year, start_month, end_year, end_month
            )
            
            # ↓↓↓ ここで戻り値を確認 ↓↓↓
            print("DEBUG run_netkeiba_collection: collect_race_data_for_period completed.")
            print(f"  final_combined_df is DataFrame: {isinstance(final_combined_df, pd.DataFrame)}")
            if isinstance(final_combined_df, pd.DataFrame):
                print(f"  final_combined_df shape: {final_combined_df.shape}")
            print(f"  final_payouts_list is list: {isinstance(final_payouts_list, list)}")
            if isinstance(final_payouts_list, list):
                print(f"  final_payouts_list length: {len(final_payouts_list)}")
            # ↑↑↑ ここまで追加 ↑↑↑
            
            # 処理完了後にUIスレッドでデータを格納・表示更新
            self.root.after(0, self.process_collection_results, final_combined_df, final_payouts_list, start_year, start_month, end_year, end_month)

        except Exception as e:
             # ↓↓↓ このデバッグプリントを追加 ↓↓↓
             print(f"DEBUG run_netkeiba_collection: 捕捉したエラー e は -> {repr(e)}")
             # ↑↑↑ repr(e) でエラーオブジェクトの詳細な表現を出力 ↑↑↑
             # ★ エラー発生時もUIスレッドでメッセージ表示
             self.root.after(0, self.handle_collection_error, e)

    def load_local_files(self, csv_path, json_path=None):
        """ローカルのCSVとJSONファイルを読み込み、統計計算を実行し、データを格納する"""
        try:
            if csv_path and os.path.exists(csv_path):
                self.update_status(f"CSV読み込み中: {os.path.basename(csv_path)}")
                df_combined = pd.read_csv(csv_path, low_memory=False)
                
                # 日付列の変換
                date_cols = ['date', 'race_date']
                for col in date_cols:
                    if col in df_combined.columns:
                        df_combined[col] = pd.to_datetime(df_combined[col], format='%Y年%m月%d日', errors='coerce')
                        break
                self.combined_data = df_combined
            else:
                messagebox.showerror("ファイルエラー", "有効なCSVファイルが選択されていません。")
                return

            if json_path and os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.payout_data = json.load(f)
            
            # --- 統計計算 & データ前処理 ---
            if self.combined_data is not None and not self.combined_data.empty:
                self.update_status("各種統計データ計算中...")
                self._calculate_course_time_stats()
                if 'father' in self.combined_data.columns: self._calculate_sire_stats(sire_column='father')
                if 'mother_father' in self.combined_data.columns: self._calculate_sire_stats(sire_column='mother_father')
                self._calculate_gate_stats()
                self._calculate_reference_times()
                
                # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
                # ★ ここで騎手統計の計算を呼び出す ★
                # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
                if 'JockeyName' in self.combined_data.columns:
                    self._calculate_jockey_stats()
                else:
                    self.jockey_stats = {}
                    print("INFO: combined_dataに'JockeyName'列がないため、騎手データの統計計算をスキップします。")
                
                self.preprocess_data_for_training()
            else:
                self.course_time_stats={}; self.father_stats={}; self.mother_father_stats={}; self.gate_stats={}; self.jockey_stats={}; self.reference_times={}
                self.processed_data = pd.DataFrame()

            self.update_status("ローカルデータ準備完了")
            messagebox.showinfo("読み込み完了", "データの読み込みと準備が完了しました。")
            self.update_data_preview()

        except Exception as e:
            self.handle_collection_error(e)

# 以下の部分は変更の必要はありませんが、ファイルの最後にmain関数や
# if __name__ == "__main__": があることを確認してください。
if __name__ == "__main__":
    root = tk.Tk()
    app = HorseRacingAnalyzerApp(root)
    root.mainloop()