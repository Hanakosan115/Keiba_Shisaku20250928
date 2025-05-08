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
import requests # type: ignore # 追加
from bs4 import BeautifulSoup # type: ignore # 追加
import re # 追加
import time # 追加
import traceback # 追加
import time as _time
from selenium import webdriver # type: ignore # 追加
from selenium.webdriver.common.by import By # type: ignore # type: ignore # 追加
from selenium.webdriver.support import expected_conditions as EC # type: ignore # 追加
from selenium.webdriver.support.ui import WebDriverWait # type: ignore # type: ignore # 追加
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException # type: ignore # 追加
from selenium.webdriver.chrome.service import Service as ChromeService # type: ignore # type: ignore # 追加

# --- Matplotlibの日本語設定 (Windows向け) ---
# 使用可能な日本語フォントを指定してください。
# 例: 'Meiryo', 'Yu Gothic', 'MS Gothic', 'TakaoPGothic' (Linux)など
# フォントがない場合は文字化けします。
try:
    plt.rcParams['font.family'] = 'Meiryo' # Windows標準のMeiryoを指定
    plt.rcParams['font.sans-serif'] = ['Meiryo', 'Yu Gothic', 'MS Gothic'] # 代替フォント
    plt.rcParams['axes.unicode_minus'] = False # 軸のマイナス記号を正しく表示
except Exception as e:
    print(f"日本語フォントの設定に失敗しました。グラフの日本語が文字化けする可能性があります。エラー: {e}", file=sys.stderr)
    # フォントが見つからない場合の代替フォントを設定（なければデフォルト）
    # plt.rcParams['font.family'] = 'sans-serif'

# --- requirements.txt に記載すべきライブラリ ---
# pandas
# numpy
# matplotlib
# --------------------------------------------

class HorseRacingAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("競馬データ分析ツール")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        # アプリケーションのアイコン設定（icon.icoをスクリプトと同じ場所に置くか、絶対パスを指定）
        # icon_path = os.path.join(os.path.dirname(__file__), "icon.ico") # スクリプトと同じ場所の場合
        # if os.path.exists(icon_path):
        #     self.root.iconbitmap(icon_path)
        # else:
        #     print("アイコンファイル 'icon.ico' が見つかりません。", file=sys.stderr)

        # スタイル設定
        self.style = ttk.Style()
        self.style.theme_use('clam') # よりモダンなテーマを使用 (clam, alt, default, classic)
        self.style.configure("TNotebook", background="#f0f0f0", tabmargins=[2, 5, 2, 0])
        self.style.configure("TNotebook.Tab", padding=[10, 5], font=("Meiryo UI", 10)) # フォント指定
        self.style.map("TNotebook.Tab", background=[("selected", "#ffffff"), ("active", "#e0e0e0")])
        self.style.configure("TFrame", background="#f0f0f0")
        self.style.configure("TButton", font=("Meiryo UI", 10), padding=5) # フォント指定
        self.style.configure("TLabel", font=("Meiryo UI", 10), background="#f0f0f0") # フォント指定
        self.style.configure("TLabelFrame", font=("Meiryo UI", 11, "bold"), background="#f0f0f0") # フォント指定
        self.style.configure("TLabelFrame.Label", font=("Meiryo UI", 11, "bold"), background="#f0f0f0") # フォント指定
        self.style.configure("TEntry", font=("Meiryo UI", 10)) # フォント指定
        self.style.configure("TCombobox", font=("Meiryo UI", 10)) # フォント指定
        self.style.configure("Treeview", font=("Meiryo UI", 9), rowheight=25) # フォント指定
        self.style.configure("Treeview.Heading", font=("Meiryo UI", 10, "bold")) # フォント指定

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
        self.tab_control.add(self.tab_results, text="結果検証") # より目的に合った名前に変更
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
        self.combined_data = pd.DataFrame() # 分析や予測に使う結合済みデータ用
        self.processed_data = pd.DataFrame() # ★ 前処理済みデータ用を追加
        self.payout_data = []             # ★ 払い戻しデータも初期化
        self.model = None # 予測モデル用
        self.settings = {} # load_settingsで初期化される
        
        self.horse_details_cache = {}     # 馬詳細情報のキャッシュ用辞書
        self.course_time_stats = {}       # コースタイム統計用辞書
        self.father_stats = {}            # 父統計用辞書
        self.mother_father_stats = {}     # 母父統計用辞書
        self.gate_stats = {}              # 枠番統計用辞書
        self.reference_times = {}         # 基準タイム用辞書

        # 設定ファイルのパスを決定（ensure_directories_existより前に実行）
        self.app_data_dir = os.path.join(os.path.expanduser("~"), "HorseRacingAnalyzer")
        self.settings_file = os.path.join(self.app_data_dir, "settings.json")

        # 設定の読み込み（デフォルト値の設定もここで行う）
        self.load_settings()
        self.load_cache_from_file() # ← ★ ここでキャッシュを読み込む
        self.load_model_from_file()
        # ↓↓↓ ここから設定値を使ってクラス属性を定義 ↓↓↓
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
        self.REQUEST_TIMEOUT = 20 # 固定値でもOK
        self.SELENIUM_WAIT_TIMEOUT = 30 # 固定値でもOK
        # 設定ファイルの値を使うか、デフォルト値を使う
        # self.settings.get(キー, デフォルト値) の形式
        self.SLEEP_TIME_PER_PAGE = float(self.settings.get("scrape_sleep_page", 0.7))
        self.SLEEP_TIME_PER_RACE = float(self.settings.get("scrape_sleep_race", 0.2))
        self.USER_AGENT = self.settings.get("user_agent", 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36') # デフォルト値も設定
        self.CHROME_DRIVER_PATH = self.settings.get("chrome_driver_path", None) # NoneならPATH検索
        self.SAVE_DIRECTORY = self.settings.get("data_dir", ".") # 保存先はdata_dirを使う
        self.PROCESSED_LOG_FILE = os.path.join(self.SAVE_DIRECTORY, "processed_race_ids.log")
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
        # ↑↑↑ ここまで追加・確認 ↑↑↑

        # Windows環境用のディレクトリ作成（設定読み込み後に行う）
        self.ensure_directories_exist()

        # 各タブの内容を初期化
        self.init_home_tab()
        self.init_data_tab()
        self.init_analysis_tab()
        self.init_prediction_tab()
        self.init_results_tab()
        self.init_settings_tab()

        # UIに設定値を反映
        self.reflect_settings_to_ui()
    
    # --- ★★★ キャッシュ保存用の一時的なメソッド ★★★ ---
    def save_cache_to_file(self, filename="horse_cache.pkl"):
        """現在の self.horse_details_cache の内容を指定ファイルに保存する"""
        # 必要なライブラリをインポート
        import pickle
        import os
        from tkinter import messagebox # メッセージボックス用にインポート

        if hasattr(self, 'horse_details_cache') and self.horse_details_cache:
            # 保存先ディレクトリ (dataフォルダ推奨)
            save_dir = self.settings.get("data_dir", "data") # dataフォルダをデフォルトに
            if not os.path.exists(save_dir):
                try:
                    os.makedirs(save_dir)
                    print(f"INFO: Created directory {save_dir}")
                except Exception as e:
                    print(f"ERROR: Failed to create directory {save_dir}: {e}")
                    messagebox.showerror("エラー", f"ディレクトリ作成失敗: {save_dir}")
                    save_dir = "." # 作成失敗時はカレントディレクトリ

            filepath = os.path.join(save_dir, filename)
            try:
                print(f"Attempting to save horse details cache to: {filepath}")
                print(f"Number of items in cache: {len(self.horse_details_cache)}")
                with open(filepath, 'wb') as f: # バイナリ書き込みモード ('wb')
                    pickle.dump(self.horse_details_cache, f, pickle.HIGHEST_PROTOCOL) # pickleで辞書を保存
                print(f"Successfully saved horse details cache to {filepath}")
                # 保存完了をユーザーに通知 (メインスレッドで実行)
                self.root.after(0, lambda path=filepath: messagebox.showinfo("キャッシュ保存完了", f"馬詳細キャッシュ ({len(self.horse_details_cache)}件) を保存しました:\n{path}"))
                self.root.after(0, lambda path=filepath: self.update_status(f"キャッシュ保存完了: {os.path.basename(path)}"))
            except Exception as e:
                print(f"ERROR: Failed to save horse details cache to {filepath}: {e}")
                self.root.after(0, lambda err=e, path=filepath: messagebox.showerror("キャッシュ保存エラー", f"キャッシュの保存中にエラーが発生しました:\n{path}\n{err}"))
                self.root.after(0, lambda err=e: self.update_status(f"エラー: キャッシュ保存失敗 ({type(err).__name__})"))
        else:
            print("WARN: No horse details cache found or cache is empty. Nothing to save.")
            self.root.after(0, lambda: messagebox.showwarning("キャッシュ保存", "保存するキャッシュデータが見つかりません。"))
    # --- ここまで一時的なメソッド ---
    
    # --- ★★★ キャッシュ読み込み用メソッド (新規追加) ★★★ ---
    def load_cache_from_file(self, filename="horse_cache.pkl"):
        """指定されたファイルから馬詳細キャッシュを読み込み、self.horse_details_cache を初期化する"""
        # 必要なライブラリをインポート (ファイル先頭推奨だが、ここでimport)
        import pickle
        import os

        # キャッシュファイルのパスを取得 (保存場所と合わせる)
        load_dir = self.settings.get("data_dir", "data") # 保存場所に合わせて "data" など
        filepath = os.path.join(load_dir, filename)

        if os.path.exists(filepath):
            try:
                print(f"INFO: Loading horse details cache from: {filepath}")
                with open(filepath, 'rb') as f: # バイナリ読み込みモード ('rb')
                    # ★★★ self.horse_details_cache に読み込んだデータを代入 ★★★
                    self.horse_details_cache = pickle.load(f)
                print(f"INFO: Successfully loaded {len(self.horse_details_cache)} items from cache.")
                self.update_status(f"馬詳細キャッシュ読み込み完了 ({len(self.horse_details_cache)}件)")
            except Exception as e:
                print(f"ERROR: Failed to load horse details cache from {filepath}: {e}")
                # messageboxはメインスレッドから呼ぶべきだが、初期化中なのでprintのみ
                # self.root.after(0, lambda err=e, path=filepath: messagebox.showerror("キャッシュ読込エラー", f"キャッシュファイルの読み込みに失敗しました:\n{path}\n{err}"))
                self.horse_details_cache = {} # 読み込み失敗時は空にする
                self.update_status("警告: キャッシュ読み込み失敗")
        else:
            print(f"INFO: Cache file not found at {filepath}. Initializing empty cache.")
            self.horse_details_cache = {} # ファイルがなければ空で初期化
            self.update_status("キャッシュファイルなし")
    # --- ここまでキャッシュ読み込みメソッド ---
    
    # --- 部品関数1: 開催日取得 (requests) ---
    def get_kaisai_dates(self,year, month):
        """指定年月の開催日リストを取得"""
        url = f'https://race.netkeiba.com/top/calendar.html?year={year}&month={month}'
        print(f"  開催日取得試行: {url}")
        headers = {'User-Agent': self.USER_AGENT}
        try:
            time.sleep(self.SLEEP_TIME_PER_PAGE) # ★待機
            r = requests.get(url, headers=headers, timeout=self.REQUEST_TIMEOUT)
            r.raise_for_status() # HTTPエラーチェック
            r.encoding = r.apparent_encoding # 文字化け対策
            soup = BeautifulSoup(r.content, 'lxml')
            kaisai_dates = []
            # カレンダーテーブル内の開催日リンクを探す
            selector = '.Calendar_Table .Week td > a[href*="kaisai_date="]'
            for a_tag in soup.select(selector):
                href = a_tag.get('href')
                match = re.search(r'kaisai_date=(\d{8})', href)
                if match:
                    kaisai_dates.append(match.group(1))
            unique_dates = sorted(list(set(kaisai_dates)))
            return unique_dates
        except requests.exceptions.Timeout:
            print(f"  タイムアウトエラー: {url}")
        except requests.exceptions.RequestException as e:
            print(f"  ページ取得エラー ({url}): {e}")
        except Exception as e:
            print(f"  予期せぬエラー (self,get_kaisai_dates) ({url}): {e}")
        return [] # エラー時は空リスト

    
    # --- 部品関数2: レースID取得 (Selenium) ---
    def get_race_ids(self, date_str):
        """指定日のレースIDリストと開催日をタプルのリストで取得"""
        url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={date_str}'
        driver = None # ★ 関数の最初に初期化
        options = webdriver.ChromeOptions()
        options.add_argument(f'--user-agent={self.USER_AGENT}')
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        race_data_list = []

        try: # ★★★ メインのtryブロック開始 ★★★
            # --- WebDriver初期化 ---
            print(f"    DEBUG: Initializing WebDriver...")
            try: # ★ WebDriver初期化専用のtry
                if self.CHROME_DRIVER_PATH and os.path.exists(self.CHROME_DRIVER_PATH):
                     service = ChromeService(executable_path=self.CHROME_DRIVER_PATH)
                     driver = webdriver.Chrome(service=service, options=options)
                elif self.CHROME_DRIVER_PATH:
                     print(f"    警告: 指定されたChromeDriverが見つかりません...")
                     driver = webdriver.Chrome(options=options)
                else:
                     print("    DEBUG: Initializing WebDriver using PATH...")
                     driver = webdriver.Chrome(options=options)
                print("    DEBUG: WebDriver initialization successful.")
            except WebDriverException as e_init: # ★ WebDriver初期化失敗をここで捕捉
                self.update_status(f"WebDriver初期化エラー: {date_str}")
                print(f"  WebDriverエラー (初期化中): {e_init}")
                print("  ChromeDriver/Chromeバージョン・パス設定を確認してください。")
                traceback.print_exc()
                driver = None # ★ 失敗したらNoneにする
            except Exception as e_init_other: # ★ その他の初期化エラー
                 self.update_status(f"WebDriver初期化中に予期せぬエラー: {date_str}")
                 print(f"  予期せぬエラー (WebDriver初期化中): {e_init_other}")
                 traceback.print_exc()
                 driver = None

            # --- WebDriver初期化成功後の処理 ---
            if driver: # ★ driverがNoneでないことを確認
                 print(f"    DEBUG: Driver instance created, getting URL: {url}")
                 driver.get(url)
                 wait = WebDriverWait(driver, self.SELENIUM_WAIT_TIMEOUT)
                 print(f"    DEBUG: Waiting for elements...")
                 try: # ★ wait.until を try...except で囲む
                     wait.until(EC.presence_of_element_located(
                         (By.CSS_SELECTOR, '#RaceTopRace, .RaceList_Box, .no_race, .alert')
                     ))
                     print(f"    DEBUG: Element found after wait!")
                 except TimeoutException:
                     print(f"  ★★★★★ TimeoutException occurred while waiting for elements on {url}")
                     # タイムアウトしても finally で閉じるのでここでは何もしない（空リストが返る）
                     # driver.quit() をここで呼ぶと finally で二重に呼ばれる可能性があるので注意

                 # ★ wait.untilが成功しても失敗しても、ページソース取得と解析を試みる
                 # （タイムアウトしても部分的に取得できる場合があるため）
                 time.sleep(self.SLEEP_TIME_PER_PAGE / 2)
                 print(f"    DEBUG: Page loaded (or timed out), getting source...")
                 try:
                     page_source = driver.page_source
                     print(f"    DEBUG: Page source length: {len(page_source)}")
                     soup = BeautifulSoup(page_source, 'lxml')
                     print(f"    DEBUG: BeautifulSoup parsing done.")

                     # --- レースID抽出処理 ---
                     selector = '.RaceList_DataItem > a:first-of-type'
                     print(f"    DEBUG: Selecting links with selector: {selector}")
                     found_links = soup.select(selector)
                     print(f"    DEBUG: Found {len(found_links)} links.")

                     if not found_links:
                        if soup.select_one('.no_race') or soup.select_one('.RaceList_Item02'):
                            print(f"      情報: {date_str} にはレースがありませんでした。")
                        else:
                            print(f"    警告: レースIDリンクが見つかりませんでした。 ({date_str})")
                     else:
                         print(f"    DEBUG: Extracting race IDs...")
                         for i, a_tag in enumerate(found_links):
                             href = a_tag.get('href')
                             if not href: continue
                             match = re.search(r'race_id=(\d+)', href)
                             if match:
                                 race_id = match.group(1)
                                 race_data_list.append((race_id, date_str))
                             else:
                                  match_alt = re.search(r'/race/result/(\d+)', href)
                                  if match_alt:
                                       race_id = match_alt.group(1)
                                       race_data_list.append((race_id, date_str))
                                  else:
                                       print(f"      警告: レースIDの抽出失敗({i+1}): {href}")
                         print(f"    DEBUG: Race ID extraction finished.")

                 except Exception as e_parse:
                      print(f"  ★★★★★ Error during page source processing or race ID extraction ({url}): {e_parse}")
                      traceback.print_exc()

            else: # driverがNoneの場合 (初期化失敗)
                 print("    エラー: WebDriverの初期化に失敗したため、処理をスキップします。")

        # ★★★ メインのtryブロックに対応するexceptとfinally ★★★
        except Exception as e_main: # 予期せぬエラー全般
            self.update_status(f"予期せぬエラー(get_race_ids): {date_str}")
            print(f"  予期せぬエラー (get_race_ids 全体): {e_main}")
            traceback.print_exc()
        finally: # ★ 必ず実行されるブロック
            if driver: # driverがNoneでなければ閉じる
                try:
                    driver.quit()
                    print(f"    DEBUG: WebDriver quit.")
                except Exception: pass

        # ★ 最終的に race_data_list を処理して返す
        unique_race_data = sorted(list(set(race_data_list)), key=lambda x: x[0])
        return unique_race_data
    
# --- 部品関数3: レース結果テーブル取得 (レース番号抽出・インデント調整版) ---
    def get_result_table(self, race_id):
        """レース結果ページ(db.netkeiba.com)からレース情報辞書と結果テーブルリストを取得"""
        url = f'https://db.netkeiba.com/race/{race_id}/'
        print(f"      結果取得試行: {url}")
        headers = {'User-Agent': self.USER_AGENT}
        race_info_dict = {'race_id': race_id} # race_idは最初に入れておく
        result_table = [] # ヘッダー行を含むリスト

        try:
            time.sleep(self.SLEEP_TIME_PER_RACE)
            r = requests.get(url, headers=headers, timeout=self.REQUEST_TIMEOUT)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.content, 'lxml')

            # === レース情報の抽出 ===
            try:
                data_intro_div = soup.select_one('div.data_intro')
                if data_intro_div:
                    # --- レース番号取得を追加 ---
                    race_num_dt = data_intro_div.select_one('dl.racedata dt')
                    if race_num_dt:
                        race_num_match = re.search(r'(\d+)', race_num_dt.get_text(strip=True))
                        if race_num_match:
                            race_info_dict['race_num'] = int(race_num_match.group(1))
                        else:
                            race_info_dict['race_num'] = None # 抽出失敗
                    else:
                        race_info_dict['race_num'] = None # dtタグが見つからない
                    # --- 追加ここまで ---

                    race_name_h1 = data_intro_div.select_one('h1')
                    if race_name_h1:
                        race_info_dict['race_name'] = race_name_h1.get_text(strip=True)

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
                            else:
                                race_info_dict['turn_detail'] = None
                                race_info_dict['turn'] = None
                            race_info_dict['distance'] = int(distance_match.group(1)) if distance_match else None
                            if not race_info_dict.get('course_type') or not race_info_dict.get('distance'): # キーが存在しない場合も考慮
                                 race_info_dict['course_full'] = course_text
                        if len(parts) >= 2 and ':' in parts[1]: race_info_dict['weather'] = parts[1].split(':', 1)[1].strip()
                        if len(parts) >= 3 and ':' in parts[2]: race_info_dict['track_condition'] = parts[2].split(':', 1)[1].strip()
                        if len(parts) >= 4 and ':' in parts[3]: race_info_dict['start_time'] = parts[3].split(':', 1)[1].strip()

                small_text_p = soup.select_one('p.smalltxt')
                if small_text_p:
                    small_text = small_text_p.get_text(strip=True)
                    date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', small_text)
                    if date_match: race_info_dict['date'] = date_match.group(1)
                    place_match = re.search(r'\d回(\S+?)\d日目', small_text)
                    if place_match: race_info_dict['track_name'] = place_match.group(1)

                print(f"      抽出したレース情報: {race_info_dict}")

            except Exception as e_info:
                print(f"      警告: レース情報の抽出中にエラー: {e_info}")
                traceback.print_exc() # エラー詳細表示

            # === 結果テーブルの取得処理 ===
            table_tag = soup.select_one('table.race_table_01.nk_tb_common')
            if not table_tag:
                print(f"      エラー: 結果テーブルが見つかりません。 ({race_id})")
                return race_info_dict, []

            header_cells = []
            horse_name_index = -1
            umaban_index = -1
            all_rows_in_table = table_tag.find_all('tr', recursive=False)
            if not all_rows_in_table:
                 print(f"      警告: 結果テーブル内に<tr>タグが見つかりません。({race_id})")
                 return race_info_dict, []

            header_row_tag = all_rows_in_table[0]
            header_th_tags = header_row_tag.find_all('th', recursive=False)
            if header_th_tags:
                header_cells = [th.get_text(strip=True).replace('<br>', '') for th in header_th_tags]
            else:
                header_td_tags = header_row_tag.find_all('td', recursive=False)
                if header_td_tags:
                     print(f"      情報: ヘッダー行に th がなく td で取得します。")
                     header_cells = [td.get_text(strip=True).replace('<br>', '') for td in header_td_tags]
            
            # ↓↓↓ ヘッダー確認デバッグプリントを追加 ↓↓↓
            # print(f"      DEBUG get_result_table: Raw Header Cells found: {header_cells}")
            # ↑↑↑ 追加 ↑↑↑

            if not header_cells:
                print(f"      エラー: ヘッダー行からセル(th/td)が取得できませんでした。({race_id})")
                return race_info_dict, []

            try: horse_name_index = next(i for i, h in enumerate(header_cells) if '馬名' in h)
            except StopIteration: print(f"      警告: ヘッダーに '馬名' 列が見つかりません。")
            try: umaban_index = next(i for i, h in enumerate(header_cells) if '馬番' in h)
            except StopIteration: print(f"      警告: ヘッダーに '馬番' 列が見つかりません。")

            header_with_url = list(header_cells)
            if horse_name_index != -1: header_with_url.insert(horse_name_index + 1, 'HorseName_url')
            result_table.append(header_with_url)

            data_tr_tags = all_rows_in_table[1:]
            if not data_tr_tags:
                print(f"      警告: データ行(tr)が見つかりません。({race_id})")
                return race_info_dict, result_table

            print(f"      DEBUG: ヘッダー行数: 1, データ行数: {len(data_tr_tags)}")

            for row_index, tr_tag in enumerate(data_tr_tags): # ★★★ enumerate を追加 ★★★
                td_tags = tr_tag.find_all('td', recursive=False)
                
                # ↓↓↓ 各行の生データ確認プリントを追加する場所 ↓↓↓
                current_row_texts = [td.get_text(strip=True) for td in td_tags]
                row_data = [] # 各行のデータを格納するリストをここで初期化
                print(f"      DEBUG get_result_table: Raw texts in row {row_index}: {current_row_texts}")
                # ↑↑↑ ここです！ ↑↑↑
                
                # 元のヘッダー列数と比較（URL追加前）
                if len(td_tags) != len(header_cells):
                     print(f"      警告: データ行のセル数({len(td_tags)})がヘッダー列数({len(header_cells)})と不一致。スキップ。")
                     continue

                for i, td_tag in enumerate(td_tags):
                    cell_span = td_tag.find('span')
                    cell_text = cell_span.get_text(strip=True) if cell_span else td_tag.get_text(strip=True)
                    row_data.append(cell_text)
                    if i == horse_name_index: # 馬名列の場合のみURLを追加
                        a_tag = td_tag.find('a')
                        href = a_tag['href'].strip() if a_tag and a_tag.has_attr('href') else None
                        row_data.append(href) # 必ず馬名テキストの直後に追加

                # 列数が期待通りか最終確認 (URL追加後)
                if len(row_data) == len(header_with_url):
                     result_table.append(row_data)
                else:
                      print(f"      警告: 最終的なデータ行の列数({len(row_data)})が期待値({len(header_with_url)})と不一致。スキップ。")


            print(f"      DEBUG get_result_table returning: info_keys={list(race_info_dict.keys())}, result_list_len={len(result_table)}")
            if len(result_table) > 0: print(f"       Header: {result_table[0]}")
            if len(result_table) > 1: print(f"       Data[0]: {result_table[1]}")

            return race_info_dict, result_table

        except requests.exceptions.Timeout:
            print(f"      タイムアウトエラー: {url}")
            return race_info_dict, []
        except requests.exceptions.RequestException as e:
            print(f"      ページ取得エラー ({url}): {e}")
            return race_info_dict, []
        except Exception as e:
            print(f"      ★★★★★ ERROR in get_result_table: {e}")
            traceback.print_exc()
            return race_info_dict, []
  
    # --- 部品関数4: 払い戻しテーブル取得 (requests) ---
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
    
    # --- 部品関数5: 出馬表テーブル取得 (shutuba_past.html 対応・リアルタイム予測考慮版) ---
    def get_shutuba_table(self, race_id):
        """
        shutuba_past.html から出馬表テーブルデータを辞書のリストで取得する。
        リアルタイム予測のための情報取得も意識する。
        """
        url = f'https://race.netkeiba.com/race/shutuba_past.html?race_id={race_id}' # ★ ターゲットURL
        print(f"      出馬表(過去走付)取得試行: {url}")
        driver = None
        # --- WebDriverセットアップ (元のコードと同じ) ---
        options = webdriver.ChromeOptions()
        options.add_argument(f'--user-agent={self.USER_AGENT}')
        #options.add_argument('--headless') # 必要ならコメント解除
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        # --- ここまでセットアップ ---
        shutuba_data_list = [] # 辞書のリストとして結果を格納

        try:
            # --- WebDriver起動 (元のコードと同じ) ---
            if self.CHROME_DRIVER_PATH and os.path.exists(self.CHROME_DRIVER_PATH):
                service = ChromeService(executable_path=self.CHROME_DRIVER_PATH)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                print("        警告: ChromeDriverのパスが設定されていないか無効です。環境変数PATHから探します。")
                driver = webdriver.Chrome(options=options)
            # --- ここまで起動 ---

            wait = WebDriverWait(driver, self.SELENIUM_WAIT_TIMEOUT)
            driver.get(url)

            # ★★★ テーブル要素のセレクタを確認・調整 ★★★
            # shutuba_past.html の主要な出馬表テーブルを特定するセレクタです。
            # 枠順確定後のページでもこのセレクタで正しいテーブルが取得できるか確認してください。
            table_selector = '.Shutuba_Table.Shutuba_Past5_Table'
            print(f"        Waiting for table element: {table_selector}")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, table_selector)))
            time.sleep(self.SLEEP_TIME_PER_PAGE / 2) # 描画完了待ち
            soup = BeautifulSoup(driver.page_source, 'lxml')
            table_tag = soup.select_one(table_selector)

            if not table_tag:
                print(f"        警告: 出馬表テーブルが見つかりませんでした ({race_id})。")
                return []

            # ★★★ 各馬の情報が含まれる行を取得するセレクタを確認・調整 ★★★
            # 通常は <tbody> の中の <tr class="HorseList"> かもしれません。これも確認してください。
            horse_rows_selector = 'tbody > tr.HorseList'
            horse_rows = table_tag.select(horse_rows_selector)
            print(f"        出馬表テーブルから {len(horse_rows)} 頭のデータを処理します (Selector: '{horse_rows_selector}')")
            # --- デバッグ用: HTMLの一部を表示 ---
            # if table_tag: print(f"DEBUG: Table HTML (snippet):\n{str(table_tag)[:500]}\n--------------------")

            for i, row_tag in enumerate(horse_rows): # enumerate を使って行番号を取得
                row_data = {'race_id': race_id} # 各行のデータを格納する辞書
                cells = row_tag.select('td') # その行の全セル(<td>)を取得
                
                # --- デバッグ用: 各行のセル数と内容を表示 ---
                # print(f"\n--- Processing Row {i+1} ---")
                # print(f"DEBUG: Number of cells found: {len(cells)}")
                # for cell_idx, cell in enumerate(cells):
                #     print(f"DEBUG: Cell {cell_idx}: {cell.get_text(strip=True)[:50]}") # 各セルのテキスト内容(最初の50文字)

                # --- 各情報をCSSセレクタやインデックスで取得 (ここを慎重に確認・調整！) ---
                # ブラウザの「検証」機能で、実際のHTML構造と照らし合わせてください。
                try:
                    # === 枠番 ===
                    waku_index = 0 # ★★★ インデックス番号を確認・調整 ★★★
                    if len(cells) > waku_index:
                        row_data['Waku'] = cells[waku_index].get_text(strip=True)
                        # print(f"DEBUG: Waku (Index {waku_index}): {row_data.get('Waku')}")
                    else: row_data['Waku'] = None

                    # === 馬番 ===
                    umaban_index = 1 # ★★★ インデックス番号を確認・調整 ★★★
                    if len(cells) > umaban_index:
                        row_data['Umaban'] = cells[umaban_index].get_text(strip=True)
                        # print(f"DEBUG: Umaban (Index {umaban_index}): {row_data.get('Umaban')}")
                    else: row_data['Umaban'] = None

                    # === 馬情報セル (馬名、父、母父、馬IDなどを含むセル) ===
                    horse_info_cell_index = 3 # ★★★ インデックス番号を確認・調整 ★★★
                    if len(cells) > horse_info_cell_index:
                        horse_info_td = cells[horse_info_cell_index]
                        # print(f"DEBUG: Horse Info Cell HTML (snippet): {str(horse_info_td)[:100]}") # デバッグ用

                        # --- 父 ---
                        father_selector = 'div.Horse01' # ★★★ CSSセレクタを確認・調整 ★★★
                        row_data['father'] = horse_info_td.select_one(father_selector).get_text(strip=True) if horse_info_td.select_one(father_selector) else None
                        # print(f"DEBUG: Father: {row_data.get('father')}")

                        # --- 馬名と馬ID ---
                        horse_link_selector = 'div.Horse02 > a' # ★★★ CSSセレクタを確認・調整 ★★★
                        horse_link = horse_info_td.select_one(horse_link_selector)
                        row_data['HorseName'] = horse_link.get_text(strip=True) if horse_link else None
                        horse_url = horse_link.get('href') if horse_link else None
                        horse_id_match = re.search(r'/horse/(\d+)', str(horse_url))
                        row_data['horse_id'] = horse_id_match.group(1) if horse_id_match else None
                        # print(f"DEBUG: HorseName: {row_data.get('HorseName')}")
                        # print(f"DEBUG: horse_id: {row_data.get('horse_id')}")

                        # --- 母父 ---
                        mf_selector = 'div.Horse04' # ★★★ CSSセレクタを確認・調整 ★★★
                        mf_div = horse_info_td.select_one(mf_selector)
                        if mf_div:
                            mf_text = mf_div.get_text(strip=True)
                            row_data['mother_father'] = mf_text[1:-1] if mf_text.startswith('(') and mf_text.endswith(')') else mf_text
                        else:
                            row_data['mother_father'] = None
                        # print(f"DEBUG: Mother's Father: {row_data.get('mother_father')}")
                        
                        # --- 調教師 ---
                        trainer_selector = 'div.Horse05 > a' # ★★★ CSSセレクタを確認・調整 ★★★
                        row_data['TrainerName'] = horse_info_td.select_one(trainer_selector).get_text(strip=True) if horse_info_td.select_one(trainer_selector) else None
                        # print(f"DEBUG: TrainerName: {row_data.get('TrainerName')}")

                        # --- 馬体重情報 (レース当日近くにならないと表示されない可能性あり) ---
                        weight_selector = 'div.Weight' # ★★★ CSSセレクタを確認・調整 ★★★
                        weight_div = horse_info_td.select_one(weight_selector)
                        row_data['WeightInfoShutuba'] = weight_div.get_text(strip=True).replace('\n','').replace('\r','') if weight_div else None
                        # print(f"DEBUG: WeightInfoShutuba: {row_data.get('WeightInfoShutuba')}")

                    else: # 馬情報セルが見つからない場合
                         print(f"        WARN: Horse Info cell not found at index {horse_info_cell_index} for row {i+1}")
                         # 不足しているキーをNoneで初期化
                         row_data.update({'father': None, 'HorseName': None, 'horse_id': None, 'mother_father': None, 'TrainerName': None, 'WeightInfoShutuba': None})


                    # === 騎手情報セル (性齢、騎手、斤量を含むセル) ===
                    jockey_cell_index = 4 # ★★★ インデックス番号を確認・調整 ★★★
                    if len(cells) > jockey_cell_index:
                        jockey_td = cells[jockey_cell_index]
                        # print(f"DEBUG: Jockey Info Cell HTML (snippet): {str(jockey_td)[:100]}") # デバッグ用

                        # --- 性齢 ---
                        sexage_selector = 'span.Barei' # ★★★ CSSセレクタを確認・調整 ★★★
                        row_data['SexAge'] = jockey_td.select_one(sexage_selector).get_text(strip=True) if jockey_td.select_one(sexage_selector) else None
                        # print(f"DEBUG: SexAge: {row_data.get('SexAge')}")

                        # --- 騎手 ---
                        jockey_selector = 'a' # ★★★ CSSセレクタを確認・調整 (td内のaタグという前提) ★★★
                        row_data['JockeyName'] = jockey_td.select_one(jockey_selector).get_text(strip=True) if jockey_td.select_one(jockey_selector) else None
                        # print(f"DEBUG: JockeyName: {row_data.get('JockeyName')}")

                        # --- 斤量 ---
                        load_selector = 'span' # ★★★ CSSセレクタを確認・調整 (td内の最後のspanという前提) ★★★
                        load_span = jockey_td.select(load_selector)[-1] if jockey_td.select(load_selector) else None
                        row_data['Load'] = load_span.get_text(strip=True) if load_span else None
                        # print(f"DEBUG: Load: {row_data.get('Load')}")

                    else: # 騎手情報セルが見つからない場合
                         print(f"        WARN: Jockey Info cell not found at index {jockey_cell_index} for row {i+1}")
                         # 不足しているキーをNoneで初期化
                         row_data.update({'SexAge': None, 'JockeyName': None, 'Load': None})

                    # --- 予測に不要な情報 (オッズ、人気、過去走など) の取得はコメントアウトまたは削除してもOK ---
                    # row_data['OddsShutuba'] = ...
                    # row_data['NinkiShutuba'] = ...

                    # 必要なキーが揃っているかチェックしてからリストに追加 (元のコードと同様)
                    required_keys = ['race_id', 'Waku', 'Umaban', 'HorseName', 'horse_id', 'father', 'mother_father', 'SexAge', 'Load', 'JockeyName'] # リアルタイム予測に必要な最低限のキー（例）
                    if all(key in row_data and pd.notna(row_data[key]) for key in required_keys): # Noneでないかもチェック
                        shutuba_data_list.append(row_data)
                        # print(f"DEBUG: Row {i+1} added to list.")
                    else:
                        print(f"        WARN: Row {i+1} data is incomplete or missing required keys. Skipping row. Data: {row_data}")

                except Exception as e_row:
                    print(f"        ERROR: Error processing row {i+1} in get_shutuba_table for {race_id}. Error: {type(e_row).__name__}: {e_row}")
                    # traceback.print_exc() # デバッグ時に詳細表示

        # (元のコードの TimeoutException, WebDriverException, Exception, finally 節)
        except TimeoutException:
            print(f"  Seleniumタイムアウトエラー (要素待機): {url}")
        except WebDriverException as e:
            print(f"  WebDriverエラー ({url}): {e}")
        except Exception as e:
            print(f"  予期せぬエラー (get_shutuba_table) ({url}): {e}")
            traceback.print_exc()
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass

        print(f"        出馬表データ取得完了: {len(shutuba_data_list)} 件")
        return shutuba_data_list # 辞書のリストを返す
    
    # --- 部品関数5: 出馬表テーブル取得 (shutuba_past.html 対応版) ---
    # def get_shutuba_table(self, race_id):
        """shutuba_past.html から出馬表テーブルデータを辞書のリストで取得"""
        url = f'https://race.netkeiba.com/race/shutuba_past.html?race_id={race_id}' # ★ URLは shutuba_past.html
        print(f"      出馬表(過去走付)取得試行: {url}")
        driver = None
        # --- WebDriverセットアップ ---
        options = webdriver.ChromeOptions()
        options.add_argument(f'--user-agent={self.USER_AGENT}')
        #options.add_argument('--headless') # 必要ならコメント解除
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        # --- ここまでセットアップ ---
        shutuba_data_list = [] # 辞書のリストとして結果を格納

        try:
            # --- WebDriver起動 ---
            if self.CHROME_DRIVER_PATH and os.path.exists(self.CHROME_DRIVER_PATH):
                 service = ChromeService(executable_path=self.CHROME_DRIVER_PATH)
                 driver = webdriver.Chrome(service=service, options=options)
            else:
                 print("      警告: ChromeDriverのパスが設定されていないか無効です。環境変数PATHから探します。")
                 driver = webdriver.Chrome(options=options)
            # --- ここまで起動 ---

            wait = WebDriverWait(driver, self.SELENIUM_WAIT_TIMEOUT)
            driver.get(url)

            # ★★★ テーブル要素のセレクタを shutuba_past.html 用に変更 ★★★
            table_selector = '.Shutuba_Table.Shutuba_Past5_Table' # クラス名を両方指定
            print(f"      Waiting for table element: {table_selector}")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, table_selector)))
            time.sleep(self.SLEEP_TIME_PER_PAGE / 2) # 描画完了待ち
            soup = BeautifulSoup(driver.page_source, 'lxml')
            table_tag = soup.select_one(table_selector) # ★ セレクタ変更

            if not table_tag:
                print(f"      警告: 出馬表(過去走付)テーブルが見つかりませんでした ({race_id})。")
                return []

            # tbody 内の各馬の行を取得
            horse_rows = table_tag.select('tbody > tr.HorseList')
            print(f"      出馬表(過去走付)テーブルから {len(horse_rows)} 頭のデータを処理します...")

            for row_tag in horse_rows:
                row_data = {'race_id': race_id} # 各行のデータを格納する辞書
                cells = row_tag.select('td') # その行の全セルを取得

                # --- 各情報をCSSセレクタやインデックスで取得 ---
                try:
                    # 枠 (インデックス 0)
                    row_data['Waku'] = cells[0].get_text(strip=True) if len(cells) > 0 else None
                    # 馬番 (インデックス 1)
                    row_data['Umaban'] = cells[1].get_text(strip=True) if len(cells) > 1 else None
                    # 印 (インデックス 2) - 必要なら取得
                    # mark_select = cells[2].select_one('select') if len(cells) > 2 else None
                    # row_data['Mark'] = mark_select.select_one('option[selected]').get_text(strip=True) if mark_select and mark_select.select_one('option[selected]') else None

                    # 馬情報セル (インデックス 3 と仮定) ★★★ 要確認 (0始まり) ★★★
                    horse_info_cell_index = 3
                    if len(cells) > horse_info_cell_index:
                        horse_info_td = cells[horse_info_cell_index]
                        # 父 (div.Horse01)
                        row_data['father'] = horse_info_td.select_one('div.Horse01').get_text(strip=True) if horse_info_td.select_one('div.Horse01') else None
                        # 馬名 (div.Horse02 > a)
                        horse_link = horse_info_td.select_one('div.Horse02 > a')
                        row_data['HorseName'] = horse_link.get_text(strip=True) if horse_link else None
                        # 馬ID (div.Horse02 > a の href)
                        horse_url = horse_link.get('href') if horse_link else None
                        horse_id_match = re.search(r'/horse/(\d+)', str(horse_url))
                        row_data['horse_id'] = horse_id_match.group(1) if horse_id_match else None
                        # 母父 (div.Horse04)
                        mf_div = horse_info_td.select_one('div.Horse04')
                        if mf_div:
                            mf_text = mf_div.get_text(strip=True)
                            row_data['mother_father'] = mf_text[1:-1] if mf_text.startswith('(') and mf_text.endswith(')') else mf_text
                        else:
                            row_data['mother_father'] = None
                        # 調教師 (div.Horse05 > a)
                        row_data['TrainerName'] = horse_info_td.select_one('div.Horse05 > a').get_text(strip=True) if horse_info_td.select_one('div.Horse05 > a') else None
                        # 馬体重 (div.Weight) - shutuba_past.html ではここにある
                        weight_div = horse_info_td.select_one('div.Weight')
                        row_data['WeightInfoShutuba'] = weight_div.get_text(strip=True).replace('\n','').replace('\r','') if weight_div else None
                        # オッズ (span#odds-*)
                        row_data['OddsShutuba'] = horse_info_td.select_one('span[id^="odds-"]').get_text(strip=True) if horse_info_td.select_one('span[id^="odds-"]') else None
                        # 人気 (span#ninki-*)
                        ninki_span = horse_info_td.select_one('span[id^="ninki-"]')
                        if ninki_span:
                             ninki_text = ninki_span.get_text(strip=True)
                             ninki_match = re.search(r'\(?(\d+)人気\)?', ninki_text)
                             row_data['NinkiShutuba'] = ninki_match.group(1) if ninki_match else ninki_text
                        else:
                             row_data['NinkiShutuba'] = None
                    else:
                         print(f"      WARN: Horse Info cell not found at index {horse_info_cell_index} for race {race_id}")
                         # 見つからない場合もキーだけは作っておく（エラー防止）
                         row_data.update({'father': None, 'HorseName': None, 'horse_id': None, 'mother_father': None, 'TrainerName': None, 'WeightInfoShutuba': None, 'OddsShutuba': None, 'NinkiShutuba': None})

                    # 騎手情報セル (インデックス 4 と仮定) ★★★ 要確認 (0始まり) ★★★
                    jockey_cell_index = 4
                    if len(cells) > jockey_cell_index:
                         jockey_td = cells[jockey_cell_index]
                         # 性齢 (span.Barei)
                         row_data['SexAge'] = jockey_td.select_one('span.Barei').get_text(strip=True) if jockey_td.select_one('span.Barei') else None
                         # 騎手 (a タグ)
                         row_data['JockeyName'] = jockey_td.select_one('a').get_text(strip=True) if jockey_td.select_one('a') else None
                         # 斤量 (最後の span タグ)
                         load_span = jockey_td.select('span')[-1] if jockey_td.select('span') else None
                         row_data['Load'] = load_span.get_text(strip=True) if load_span else None
                    else:
                         print(f"      WARN: Jockey Info cell not found at index {jockey_cell_index} for race {race_id}")
                         row_data.update({'SexAge': None, 'JockeyName': None, 'Load': None})

                    # 過去走データは今回は取得しない (必要なら別途追加)

                    # 必要なキーが揃っているかチェックしてからリストに追加
                    required_keys = ['race_id', 'Waku', 'Umaban', 'HorseName', 'horse_id', 'father', 'mother_father'] # 最低限のキー
                    if all(key in row_data and row_data[key] is not None for key in required_keys):
                        shutuba_data_list.append(row_data)
                    else:
                        print(f"      WARN: Row data is incomplete or missing required keys for race {race_id}. Skipping row. Data: {row_data}")

                except Exception as e_row:
                    print(f"      ERROR: Error processing row in get_shutuba_table for {race_id}. Error: {type(e_row).__name__}: {e_row}")
                    # traceback.print_exc() # 必要なら詳細表示

        except TimeoutException:
            print(f"  Seleniumタイムアウトエラー (要素待機): {url}")
        except WebDriverException as e:
            print(f"  WebDriverエラー ({url}): {e}")
        except Exception as e:
            print(f"  予期せぬエラー (get_shutuba_table) ({url}): {e}")
            traceback.print_exc()
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass

        print(f"      出馬表(過去走付)データ取得完了: {len(shutuba_data_list)} 件")
        return shutuba_data_list # 辞書のリストを返す

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
        print(f"      馬詳細取得試行: {url}")
        headers = {'User-Agent': self.USER_AGENT}
        horse_details = {'horse_id': horse_id} # 初期化

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
                         elif '獲得賞金' in header_text: horse_details['total_prize'] = value_text
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

                    # --- データ整形 ---
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

                horse_details['race_results'] = race_results_list
                print(f"      戦績テーブル取得・整形成功: {len(race_results_list)} レース分")
            else:
                print(f"      警告: 戦績テーブル (db_h_race_results) が見つかりません ({horse_id})")
                horse_details['race_results'] = []
                if 'error' not in horse_details: horse_details['error'] = ''
                horse_details['error'] += ' Race results table not found'
            # === 戦績テーブル取得・整形ロジックここまで ===

            # print(f"      馬詳細取得成功: {horse_details}") # デバッグ表示 (整形後)

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

    # --- 特徴量計算関数 (近走特徴量追加版) ---
    def calculate_original_index(self, horse_details, race_conditions):
        """
        馬の詳細情報とレース条件から、予測に使用する特徴量を計算・収集して返す。
        近走情報に着差と上がりタイムを追加。
        """
        # === 特徴量を格納する辞書 (近走情報を追加) ===
        features = {
            'Umaban': None, 'HorseName': None, 'Sex': None, 'Age': None,
            'Load': None, 'JockeyName': None, 'TrainerName': None,
            'father': None, 'mother_father': None, 'horse_id': None,
            # --- 近走関連 ---
            '近走1走前着順': None, '近走2走前着順': None, '近走3走前着順': None,
            '着差_1走前': None, '着差_2走前': None, '着差_3走前': None,       # ★★★ 追加 ★★★
            '上がり3F_1走前': None, '上がり3F_2走前': None, '上がり3F_3走前': None, # ★★★ 追加 ★★★
            # --- ここまで近走関連 ---
            '同条件出走数': 0, '同条件複勝率': 0.0,
            'タイム偏差値': None, '同コース距離最速補正': None,
            '基準タイム差': None, '基準タイム比': None,
            '父同条件複勝率': 0.0, '父同条件N数': 0,
            '母父同条件複勝率': 0.0, '母父同条件N数': 0,
            '斤量絶対値': None, '斤量前走差': None,
            '馬体重絶対値': None, '馬体重前走差': None,
            '枠番': None, '枠番_複勝率': 0.0, '枠番_N数': 0,
            '負担率': None,
            '距離区分': None, 'error': None
        }

        # horse_id を安全に取得
        horse_id_for_log = None
        if isinstance(horse_details, (pd.Series, dict)):
            horse_id_for_log = horse_details.get('horse_id')
        features['horse_id'] = horse_id_for_log

        # --- 基本情報を features に格納 ---
        if isinstance(horse_details, (pd.Series, dict)):
            features['Umaban'] = pd.to_numeric(horse_details.get('Umaban'), errors='coerce')
            features['HorseName'] = str(horse_details.get('HorseName', ''))
            features['Load'] = pd.to_numeric(horse_details.get('Load'), errors='coerce')
            features['JockeyName'] = str(horse_details.get('JockeyName', ''))
            features['TrainerName'] = str(horse_details.get('TrainerName', ''))
            features['father'] = str(horse_details.get('father', ''))
            features['mother_father'] = str(horse_details.get('mother_father', ''))
            features['馬体重絶対値'] = pd.to_numeric(horse_details.get('Weight'), errors='coerce')
            features['馬体重前走差'] = pd.to_numeric(horse_details.get('WeightDiff'), errors='coerce')
            features['枠番'] = pd.to_numeric(horse_details.get('枠番'), errors='coerce')
            sex_age_str = str(horse_details.get('SexAge',''))
            if len(sex_age_str) > 1:
                features['Sex'] = sex_age_str[0]
                features['Age'] = pd.to_numeric(sex_age_str[1:], errors='coerce')
            else: features['Sex'] = None; features['Age'] = None

        # --- レース条件の取得 ---
        target_course = race_conditions.get('course_type')
        target_distance = race_conditions.get('distance')
        target_track = race_conditions.get('track_name')
        target_baba = race_conditions.get('baba')

        # --- 距離区分計算 ---
        distance_group = None; target_distance_float = None
        if target_distance is not None:
            try:
                target_distance_float = float(target_distance)
                bins = [0, 1400, 1800, 2200, 2600, float('inf')]
                labels = ['1400m以下', '1401-1800m', '1801-2200m', '2201-2600m', '2601m以上']
                distance_cut_result = pd.cut([target_distance_float], bins=bins, labels=labels, right=True, include_lowest=True)
                if len(distance_cut_result) > 0 and pd.notna(distance_cut_result[0]): distance_group = distance_cut_result[0]
            except (ValueError, TypeError): target_distance_float = None
            except Exception as e: print(f"警告({horse_id_for_log}): 距離区分計算中にエラー: {e}"); distance_group = None
        features['距離区分'] = distance_group

        # --- 戦績リスト取得 ---
        race_results = None
        if isinstance(horse_details, (pd.Series, dict)):
            # ★ get_horse_details が返す戦績リストが格納されているキー名を確認 (仮に 'race_results')
            race_results = horse_details.get('race_results')
        if not isinstance(race_results, list): race_results = None

        # --- 各特徴量の計算 ---
        try:
            # === 1. 近走情報 (着順・着差・上がり) === (★★ キー名修正 ★★)
            try:
                if isinstance(race_results, list):
                    for i, result in enumerate(race_results[:3]): # 直近3走まで
                        if i >= 3: break # 念のため
                        idx = i + 1 # 1走前=1, 2走前=2, ...

                        # --- 着順 ---
                        rank = result.get('rank'); rank_str = result.get('rank_str', '?')
                        rank_val = None # 初期化
                        try: rank_val = int(float(rank))
                        except (ValueError, TypeError, TypeError):
                            if rank_str in ['中', '除', '取', '止']: rank_val = 99 # 特殊な着順は99
                            else: rank_val = None # 不明な場合はNone
                        features[f'近走{idx}走前着順'] = rank_val

                        # --- 着差 ---
                        # ★★★ キー名を 'diff' (小文字) に変更 (get_horse_detailsの格納キーに合わせる) ★★★
                        diff_val = result.get('diff')
                        diff_numeric = None # 初期化
                        if rank_val == 1: # 1着なら着差0
                            diff_numeric = 0.0
                        elif rank_val is not None and rank_val != 99: # 1着以外で有効な着順
                            # result.get('diff') で取得した値が既に数値ならそのまま使える
                            if pd.notna(diff_val) and isinstance(diff_val, (int, float)):
                                diff_numeric = round(float(diff_val), 3)
                            # 文字列の場合("クビ"など)は現状では None/NaN になる
                            else:
                                diff_numeric = pd.to_numeric(diff_val, errors='coerce')
                                if pd.notna(diff_numeric): diff_numeric = round(diff_numeric, 3)
                        features[f'着差_{idx}走前'] = diff_numeric # Noneまたは数値

                        # --- 上がり3Fタイム ---
                        # ★★★ キー名を 'agari' (小文字) に変更 (get_horse_detailsの格納キーに合わせる) ★★★
                        agari_val = result.get('agari')
                        agari_numeric = None # 初期化
                        if pd.notna(agari_val) and isinstance(agari_val, (int, float)):
                            agari_numeric = round(float(agari_val), 1)
                        # 文字列の場合も考慮して数値変換
                        elif isinstance(agari_val, str):
                             agari_numeric_conv = pd.to_numeric(agari_val, errors='coerce')
                             if pd.notna(agari_numeric_conv): agari_numeric = round(agari_numeric_conv, 1)
                        features[f'上がり3F_{idx}走前'] = agari_numeric # Noneまたは数値

                # else: race_results がない場合は初期値Noneのまま
            except Exception as e: print(f"警告({horse_id_for_log}): 近走情報取得エラー: {e}")
            
            # === 2. コース距離適性 ===
            # ... (変更なし) ...
            try:
                runs_on_condition = 0; place3_on_condition = 0; place3_rate = 0.0
                if target_course and target_distance_float is not None and target_track and isinstance(race_results, list):
                    for result in race_results:
                        try:
                            if (result.get('course_type') == target_course and
                                float(result.get('distance')) == target_distance_float and
                                result.get('place') == target_track):
                                runs_on_condition += 1
                                rank_val = pd.to_numeric(result.get('rank'), errors='coerce')
                                if pd.notna(rank_val) and rank_val <= 3: place3_on_condition += 1
                        except (ValueError, TypeError, TypeError): pass
                    if runs_on_condition > 0: place3_rate = place3_on_condition / runs_on_condition
                features['同条件出走数'] = runs_on_condition; features['同条件複勝率'] = round(place3_rate, 3)
            except Exception as e: print(f"警告({horse_id_for_log}): 適性計算エラー: {e}")


            # === 3. 持ちタイム === (基準タイム比較を追加)
            # ... (変更なし) ...
            try:
                time_dev = None; best_corrected_time_sec = None; runs_on_course_distance = 0; relevant_times = []
                reference_time = None; ref_time_diff = None; ref_time_ratio = None
                if target_course and target_distance_float is not None and hasattr(self, 'course_time_stats') and self.course_time_stats and isinstance(race_results, list):
                    baba_hosei = {'芝': {'良': 0.0, '稍重': 0.5, '重': 1.0, '不良': 1.5}, 'ダ': {'良': 0.0, '稍重': -0.3, '重': -0.8, '不良': -1.3}}
                    for result in race_results:
                        try:
                            past_course = result.get('course_type'); past_dist = float(result.get('distance')); past_time = float(result.get('time_sec')); past_baba = result.get('baba')
                            if (past_course == target_course and past_dist == target_distance_float and past_time > 0 and past_baba):
                                hosei = baba_hosei.get(past_course, {}).get(past_baba)
                                if hosei is not None: relevant_times.append(past_time - hosei); runs_on_course_distance += 1
                        except (ValueError, TypeError, TypeError): pass
                    if relevant_times: best_corrected_time_sec = min(relevant_times)
                    stats_key = (target_course, int(target_distance_float))
                    course_stats = self.course_time_stats.get(stats_key)
                    if best_corrected_time_sec is not None and course_stats and isinstance(course_stats.get('mean'), (int, float)) and isinstance(course_stats.get('std'), (int, float)):
                        mean_time = course_stats['mean']; std_dev_time = course_stats['std']
                        if std_dev_time > 0: time_dev = round(50 + 10 * (mean_time - best_corrected_time_sec) / std_dev_time, 1)
                if best_corrected_time_sec is not None:
                    race_name_for_class = str(horse_details.get('race_name', '')) if isinstance(horse_details, (pd.Series, dict)) else ''
                    race_class_level = self._get_race_class_level(race_name_for_class)
                    if (hasattr(self, 'reference_times') and self.reference_times and target_track and target_course and target_distance):
                        try:
                             ref_key = (race_class_level, target_track, target_course, int(target_distance))
                             reference_time = self.reference_times.get(ref_key)
                             if reference_time is not None and pd.notna(reference_time):
                                  ref_time_diff = reference_time - best_corrected_time_sec
                                  if reference_time > 0: ref_time_ratio = best_corrected_time_sec / reference_time
                        except Exception as e_ref_lookup: print(f"警告({horse_id_for_log}): 基準タイム参照エラー: {e_ref_lookup}")
                features['タイム偏差値'] = time_dev; features['同コース距離最速補正'] = round(best_corrected_time_sec, 2) if best_corrected_time_sec is not None else None
                features['基準タイム差'] = round(ref_time_diff, 3) if pd.notna(ref_time_diff) else None
                features['基準タイム比'] = round(ref_time_ratio, 3) if pd.notna(ref_time_ratio) else None
            except Exception as e: print(f"警告({horse_id_for_log}): タイム特徴量エラー: {e}")


            # === 4. 血統 ===
            # ... (変更なし) ...
            try:
                father = features.get('father'); mother_father = features.get('mother_father')
                father_place3_rate = 0.0; father_runs = 0
                if father and hasattr(self, 'father_stats') and self.father_stats and target_course and distance_group:
                    sire_data = self.father_stats.get(father); condition_key = (target_course, distance_group)
                    if sire_data and condition_key in sire_data:
                        stats = sire_data[condition_key]; father_place3_rate = stats.get('Place3Rate', 0.0); father_runs = stats.get('Runs', 0)
                        if not isinstance(father_place3_rate, (int, float)): father_place3_rate = 0.0
                features['父同条件複勝率'] = round(father_place3_rate, 3); features['父同条件N数'] = father_runs

                mother_father_place3_rate = 0.0; mother_father_runs = 0
                if mother_father and hasattr(self, 'mother_father_stats') and self.mother_father_stats and target_course and distance_group:
                    damsire_data = self.mother_father_stats.get(mother_father); condition_key = (target_course, distance_group)
                    if damsire_data and condition_key in damsire_data:
                        stats = damsire_data[condition_key]; mother_father_place3_rate = stats.get('Place3Rate', 0.0); mother_father_runs = stats.get('Runs', 0)
                        if not isinstance(mother_father_place3_rate, (int, float)): mother_father_place3_rate = 0.0
                features['母父同条件複勝率'] = round(mother_father_place3_rate, 3); features['母父同条件N数'] = mother_father_runs
            except Exception as e: print(f"警告({horse_id_for_log}): 血統計算エラー: {e}")

            # === 5. 斤量 === (★★ 特徴量に変更 - デバッグ再追加 ★★)
            try:
                load_abs = None; load_diff = None # 初期化
                load_abs_from_details = None
                load_key_to_get = 'Load' # horse_detailsから取得するキー名
                load_abs_numeric = None # 数値変換後を格納する変数も初期化
                burden_rate = None # 負担率も初期化

                # print(f"      DEBUG LOAD: Start processing for Umaban {horse_details.get('Umaban','N/A')}")
                # if isinstance(horse_details, (pd.Series, dict)):
                    # print(f"      DEBUG LOAD: Checking key '{load_key_to_get}' in horse_details...")
                    # load_abs_from_details = horse_details.get(load_key_to_get) # 今回の斤量を取得
                    # print(f"      DEBUG LOAD: Value got for key '{load_key_to_get}': {load_abs_from_details} (Type: {type(load_abs_from_details)})")
                # else:
                    # print(f"      WARN LOAD: horse_details is not Series or dict.")

                # pd.to_numeric で数値に変換
                load_abs_numeric = pd.to_numeric(load_abs_from_details, errors='coerce')
                # print(f"      DEBUG LOAD: Value after pd.to_numeric: {load_abs_numeric} (Type: {type(load_abs_numeric)})")
                features['斤量絶対値'] = load_abs_numeric # 格納
                # print(f"      DEBUG LOAD: Value stored in features['斤量絶対値']: {features['斤量絶対値']}")

                # ★ 次に前走差を計算
                # print(f"      DEBUG LOAD: Calculating load_diff...")
                if isinstance(race_results, list) and len(race_results) >= 2: # 前走データがあるか
                    try:
                        # 1走前の斤量を取得 (キー名は 'load'?)
                        previous_load_key = 'load' # ★ race_results内の実際のキー名に合わせてください
                        previous_load_val = race_results[1].get(previous_load_key)
                        # print(f"      DEBUG LOAD: Previous load value from race_results[1] for key '{previous_load_key}': {previous_load_val} (Type: {type(previous_load_val)})")

                        previous_load_numeric = pd.to_numeric(previous_load_val, errors='coerce') # 数値変換
                        # print(f"      DEBUG LOAD: Previous load after pd.to_numeric: {previous_load_numeric} (Type: {type(previous_load_numeric)})")

                        current_load_numeric_feat = features.get('斤量絶対値') # 格納済みの値
                        # print(f"      DEBUG LOAD: Current load from features['斤量絶対値']: {current_load_numeric_feat} (Type: {type(current_load_numeric_feat)})")

                        if pd.notna(current_load_numeric_feat) and pd.notna(previous_load_numeric):
                            load_diff = current_load_numeric_feat - previous_load_numeric
                            print(f"      DEBUG LOAD: Calculated load_diff: {load_diff}") # 計算結果表示
                        else:
                            print(f"      DEBUG LOAD: Cannot calculate load_diff (current or previous load is NaN/None).")

                    except (ValueError, TypeError, TypeError, IndexError) as e_diff:
                         print(f"      WARN LOAD: Error calculating load diff: {e_diff}")
                         pass
                else:
                    print(f"      DEBUG LOAD: Not enough race_results to calculate load_diff (len: {len(race_results) if isinstance(race_results, list) else 'N/A'}).")

                features['斤量前走差'] = round(load_diff, 1) if pd.notna(load_diff) else None
                print(f"      DEBUG LOAD: Final value stored in features['斤量前走差']: {features['斤量前走差']}") # 最終値確認

                # ★★★ 負担率の計算を追加 ★★★
                weight_abs_numeric = features.get('馬体重絶対値') # 格納済みの馬体重を取得
                # print(f"      DEBUG LOAD: Calculating burden rate. LoadAbs={load_abs_numeric}, WeightAbs={weight_abs_numeric}") # 修正: load_abs_numericを使う
                if pd.notna(load_abs_numeric) and pd.notna(weight_abs_numeric) and weight_abs_numeric > 0:
                    try:
                        burden_rate = load_abs_numeric / weight_abs_numeric # 修正: load_abs_numericを使う
                    except ZeroDivisionError: burden_rate = None
                features['負担率'] = round(burden_rate * 100, 1) if pd.notna(burden_rate) else None
                # print(f"      DEBUG LOAD: Final value stored in features['負担率']: {features['負担率']}")
                # ★★★★★★★★★★★★★★★★★

            except Exception as e: print(f"警告({horse_id_for_log}): 斤量/負担率特徴量エラー: {e}")
            
            # === 6. 馬体重 ===
            pass

            # === 7. 枠順 ===
            # ... (変更なし) ...
            try:
                waku_num = features.get('枠番')
                gate_place3_rate = 0.0; gate_runs = 0
                if (hasattr(self, 'gate_stats') and self.gate_stats and
                    target_track and target_course and target_distance and
                    pd.notna(waku_num) and isinstance(waku_num, (int, float, np.number))):
                    try:
                        stat_key = (target_track, target_course, int(target_distance), int(waku_num))
                        gate_data = self.gate_stats.get(stat_key)
                        if gate_data:
                            gate_place3_rate = gate_data.get('Place3Rate', 0.0)
                            gate_runs = gate_data.get('Runs', 0)
                    except Exception as e_lookup: print(f"警告({horse_id_for_log}): 枠番統計データの参照中にエラー: {e_lookup}")
                features['枠番_複勝率'] = round(gate_place3_rate, 3)
                features['枠番_N数'] = gate_runs
            except Exception as e: print(f"警告({horse_id_for_log}): 枠番統計特徴量エラー: {e}"); features['枠番_複勝率'] = 0.0; features['枠番_N数'] = 0


        except Exception as e: # 計算プロセス全体の予期せぬエラー
            print(f"!!! 重大エラー ({horse_id_for_log}): 特徴量計算プロセス全体で予期せぬエラーが発生 !!!"); traceback.print_exc()
            features['error'] = f"特徴量計算中に重大エラー: {e}"

        # デバッグプリント
        # print(f"Debug Features (Umaban: {features.get('Umaban','N/A')} ID: {features.get('horse_id','N/A')}): {features}")

        # 戻り値
        return 0.0, features

    # --- 持ちタイム指数用の統計計算メソッド (新規追加) ---
    def _calculate_course_time_stats(self):
        """
        読み込んだデータ全体から、コース種別・距離ごとの
        馬場補正済み走破タイムの平均と標準偏差を計算し、クラス変数に格納する。
        load_local_files や process_collection_results の最後に呼び出すことを想定。
        """
        print("コース・距離別のタイム統計データ（平均・標準偏差）を計算中...")
        self.update_status("タイム統計データ計算中...")
        start_calc_time = time.time()

        # 計算結果を格納するクラス変数を初期化
        self.course_time_stats = {}

        if self.combined_data is None or self.combined_data.empty:
            print("警告: タイム統計計算のためのデータがありません。")
            self.update_status("タイム統計計算不可 (データなし)")
            return

        # 必要な列が存在するか確認
        required_cols = ['course_type', 'distance', 'track_condition', 'Time', 'Rank'] # 'baba'->'track_condition', 'time_sec'->'Time'
        if not all(col in self.combined_data.columns for col in required_cols):
             missing = [c for c in required_cols if c not in self.combined_data.columns]
             print(f"警告: タイム統計計算に必要な列が不足しています: {missing}")
             self.update_status(f"タイム統計計算不可 (列不足: {missing})")
             return

        df = self.combined_data[required_cols].copy()

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
        df.dropna(subset=['time_sec_numeric', 'track_condition', 'course_type', 'distance', 'Rank'], inplace=True)
        df['distance_numeric'] = pd.to_numeric(df['distance'], errors='coerce')
        df['Rank_numeric'] = pd.to_numeric(df['Rank'], errors='coerce')
        df.dropna(subset=['distance_numeric', 'Rank_numeric'], inplace=True)
        df['distance_numeric'] = df['distance_numeric'].astype(int)
        df['Rank_numeric'] = df['Rank_numeric'].astype(int)
        df['course_type'] = df['course_type'].astype(str).str.strip()
        df['baba'] = df['track_condition'].astype(str).str.strip()
        # ---------------------------------

        # --- 馬場補正タイムを計算 ---
        baba_hosei = {
            '芝': {'良': 0.0, '稍重': 0.5, '重': 1.0, '不良': 1.5},
            'ダ': {'良': 0.0, '稍重': -0.3, '重': -0.8, '不良': -1.3} # ダートはマイナス
        }
        def get_hosei(row):
            course = row['course_type']; baba = row['baba']
            return baba_hosei.get(course, {}).get(baba, 0.0)
        df['hosei_value'] = df.apply(get_hosei, axis=1)
        df['corrected_time_sec'] = df['time_sec_numeric'] - df['hosei_value']
        # ----------------------------

        # --- 異常なタイムを除外 ---
        df_filtered = df[df['Rank_numeric'] <= 5]
        print(f"タイム統計計算: {len(df)}行からRank<=5の{len(df_filtered)}行を対象とします。")
        # --------------------------

        # --- コース種別と距離でグループ化し統計計算 ---
        try:
            stats = df_filtered.groupby(['course_type', 'distance_numeric'])['corrected_time_sec'].agg(
                mean='mean', std='std', count='size'
            ).reset_index()
            stats['std'] = stats['std'].apply(lambda x: x if pd.notna(x) and x > 0 else None)

            for _, row in stats.iterrows():
                key = (row['course_type'], row['distance_numeric'])
                std_dev = row['std'] if row['count'] >= 5 else None
                self.course_time_stats[key] = {'mean': row['mean'], 'std': std_dev, 'count': row['count']}

            end_calc_time = time.time()
            print(f"タイム統計データの計算完了。{len(self.course_time_stats)} 件のコース・距離データを生成。({end_calc_time - start_calc_time:.2f}秒)")
            self.update_status("タイム統計データ準備完了")

        except Exception as e:
            print(f"!!! Error during time stats calculation: {e}")
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

    # --- ★★★ モデル読み込みメソッド (新規追加) ★★★ ---
    def load_model_from_file(self, filename="trained_lgbm_model.pkl"):
        """指定されたファイルから学習済みモデルを読み込み、self.trained_model を初期化する"""
        # 必要なライブラリをインポート
        import pickle
        import os
        from tkinter import messagebox # ここでインポートするか、クラス冒頭で行うか

        load_dir = self.settings.get("data_dir", "data") # 保存場所と合わせる
        filepath = os.path.join(load_dir, filename)

        if os.path.exists(filepath):
            try:
                print(f"INFO: Loading trained model from: {filepath}")
                with open(filepath, 'rb') as f: # バイナリ読み込みモード ('rb')
                    self.trained_model = pickle.load(f) # self.trained_model に読み込む
                print(f"INFO: Successfully loaded trained model from {filepath}")
                model_info = type(self.trained_model).__name__ # 簡単なモデル情報
                self.update_status(f"学習済みモデル読み込み完了 ({model_info})")
            except Exception as e:
                print(f"ERROR: Failed to load trained model from {filepath}: {e}")
                self.trained_model = None # 読み込み失敗時はNone
                self.update_status("警告: 学習済みモデル読み込み失敗")
                # エラーメッセージ表示 (オプション)
                # self.root.after(0, lambda err=e, path=filepath: messagebox.showerror("モデル読込エラー", f"モデル読込エラー:\n{path}\n{err}"))
        else:
            print(f"INFO: Trained model file not found at {filepath}. Model is not loaded.")
            self.trained_model = None # ファイルがなければNone
            self.update_status("学習済みモデルなし")

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
                      df['date'] = pd.to_datetime(df['date'], errors='coerce')
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
    
    # --- ★★★ 学習データ準備メソッド (calculate_original_index 利用版 / timeエイリアス修正) ★★★ ---
    def _prepare_data_for_model(self):
        """
        self.processed_data の各行について calculate_original_index を実行し、
        その結果の特徴量と正解ラベルから学習用データ (X, y) を作成して返す。
        """
        print("モデル学習用のデータ準備を開始します (calculate_original_index を使用)...")
        self.update_status("学習データ準備中...")
        # ↓↓↓ time.time() -> _time.time() に修正 ↓↓↓
        start_time = _time.time() # ★ time ではなく _time を使う

        # 必要なモジュールをインポート (既にあれば不要)
        import pandas as pd # type: ignore
        import numpy as np # type: ignore
        # import time # ← ファイル先頭で _time としてインポート済みなら不要
        import traceback

        # processed_data と 必要な統計データの存在チェック
        required_attrs = ['processed_data', 'course_time_stats', 'father_stats',
                          'mother_father_stats', 'gate_stats', 'reference_times',
                          'horse_details_cache']
        missing_attrs = [attr for attr in required_attrs if not hasattr(self, attr) or getattr(self, attr) is None]

        if missing_attrs or self.processed_data.empty:
            print(f"エラー: 学習データ準備に必要なデータが不足しています: {missing_attrs}")
            if self.processed_data is not None and self.processed_data.empty: print("   (processed_data is empty)")
            self.update_status("エラー: データ準備不足")
            return None, None

        all_features_list = []
        target_list = []
        skipped_rows = 0
        num_rows = len(self.processed_data)
        print(f"INFO: processed_data の {num_rows} 行を処理します...")

        # processed_data を1行ずつ処理
        for index, row in self.processed_data.iterrows():
            if index > 0 and index % 500 == 0:
                 progress_percent = (index / num_rows) * 100
                 self.root.after(0, lambda i=index, n=num_rows, p=progress_percent: self.update_status(f"学習データ作成中... ({i}/{n} - {p:.0f}%)"))

            # 1. レース条件を作成
            race_conditions = {
                'course_type': row.get('course_type'),
                'distance': pd.to_numeric(row.get('distance'), errors='coerce'),
                'track_name': row.get('track_name'),
                'baba': row.get('track_condition')
            }
            if pd.isna(race_conditions['distance']): race_conditions['distance'] = None
            else: race_conditions['distance'] = int(race_conditions['distance'])

            # 2. horse_details を作成
            horse_details_for_calc = row.to_dict()
            horse_id = horse_details_for_calc.get('horse_id')
            if horse_id and pd.notna(horse_id):
                horse_id_str = str(int(horse_id)) if isinstance(horse_id, (int, float, np.number)) else str(horse_id)
                details_from_cache = self.horse_details_cache.get(horse_id_str)
                if details_from_cache and 'race_results' in details_from_cache:
                    horse_details_for_calc['race_results'] = details_from_cache['race_results']
                else: horse_details_for_calc['race_results'] = []
            else: horse_details_for_calc['race_results'] = []

            # 3. 特徴量計算を実行
            _, features = self.calculate_original_index(horse_details_for_calc, race_conditions)

            # 4. 正解ラベルを作成
            rank_val = pd.to_numeric(row.get('Rank'), errors='coerce')
            if pd.isna(rank_val): skipped_rows += 1; continue
            target = 1 if rank_val <= 3 else 0

            # 5. 結果をリストに追加
            if features.get('error') is None:
                all_features_list.append(features)
                target_list.append(target)
            else: skipped_rows += 1

        if skipped_rows > 0: print(f"INFO: {skipped_rows} rows were skipped.")
        if not all_features_list: print("エラー: 有効な特徴量データがありません。"); return None, None

        # DataFrame作成
        X = pd.DataFrame(all_features_list)
        y = pd.Series(target_list, index=X.index)

        # --- 学習に使用する特徴量を選択 ---
        feature_cols_final = [
            'Age', '斤量絶対値', '斤量前走差', '負担率', '馬体重絶対値', '馬体重前走差', '枠番',
            '同条件出走数', '同条件複勝率', '枠番_複勝率', '枠番_N数',
            'タイム偏差値', '基準タイム差', '基準タイム比', '同コース距離最速補正',
            '父同条件複勝率', '父同条件N数', '母父同条件複勝率', '母父同条件N数',
            '近走1走前着順', '着差_1走前', '上がり3F_1走前',
            '近走2走前着順', '着差_2走前', '上がり3F_2走前',
            '近走3走前着順', '着差_3走前', '上がり3F_3走前'
        ]
        feature_cols_final = [col for col in feature_cols_final if col in X.columns]
        X = X[feature_cols_final].copy()
        print(f"最終的な学習特徴量 ({len(feature_cols_final)}個): {feature_cols_final}")

        # --- 欠損値処理 ---
        print("最終的な特徴量データの欠損値を平均値で補完します...")
        missing_before = X.isnull().sum().sum()
        if missing_before > 0:
            cols_with_nan = X.columns[X.isnull().any()].tolist()
            print(f"  欠損値を含む列: {cols_with_nan}")
            for col in cols_with_nan:
                mean_val = X[col].mean(); mean_val = 0 if pd.isna(mean_val) else mean_val
                X[col].fillna(mean_val, inplace=True)
        missing_after = X.isnull().sum().sum()
        print(f"  補完前の欠損値数: {missing_before}, 補完後の欠損値数: {missing_after}")
        if missing_after > 0: print("警告: 欠損値補完後もNaNが残っています。要確認。")

        # ↓↓↓ time.time() -> _time.time() に修正 ↓↓↓
        end_time = _time.time() # ★ time ではなく _time を使う
        print(f"モデル学習用データの準備完了。Shape X: {X.shape}, y: {y.shape} ({end_time - start_time:.2f}秒)")
        self.root.after(0, lambda: self.update_status("学習データ準備完了"))
        return X, y
    
    # horse_racing_analyzer.py の HorseRacingAnalyzer クラス内
# 既存の train_and_evaluate_model メソッドをまるごと置き換えてください。

    # --- ★★★ モデル学習・評価メソッド ★★★ ---
    def train_and_evaluate_model(self):
        """
        準備された学習データ (X, y) を使ってLightGBMモデルを学習し、
        簡単な評価を行う。結果はログとメッセージボックスに表示。
        学習済みモデルは self.trained_model に保存。
        """
        # --- 必要なライブラリをインポート ---
        # (ファイル冒頭でインポート済みなら不要だが、念のため)
        try:
            import lightgbm as lgb # type: ignore
            from sklearn.model_selection import train_test_split # type: ignore # type: ignore
            from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, confusion_matrix # type: ignore
            import pandas as pd # type: ignore # type: ignore
            import traceback
            from tkinter import messagebox
            # ★↓ キャリブレーションプロット作成のために以下3行を追加しました
            from sklearn.calibration import calibration_curve # type: ignore
            import matplotlib.pyplot as plt # type: ignore
            import os # ファイルパスの操作用にosモジュールをインポート
        except ImportError as e:
            messagebox.showerror("ライブラリ不足", f"必要なライブラリが見つかりません: {e}\npip install lightgbm scikit-learn matplotlib でインストールしてください。")
            return
        # --- ここまでインポート ---

        print("\n--- Starting Model Training and Evaluation ---")
        self.update_status("モデル学習と評価を開始...")

        # 1. 学習データの準備
        # (このメソッドは DataFrame X と Series y を返す)
        X, y = self._prepare_data_for_model() # ユーザーさん定義のデータ準備メソッド

        if X is None or y is None or X.empty or y.empty:
            print("エラー: モデル学習に必要なデータが準備できませんでした。")
            self.root.after(0, lambda: self.update_status("エラー: 学習データ準備失敗"))
            self.root.after(0, lambda: messagebox.showerror("モデル学習エラー", "学習データの準備に失敗しました。"))
            return

        # 2. データの分割 (訓練用とテスト用)
        try:
            # test_size=0.2 で 20% をテストデータに
            # stratify=y で元のデータのクラス比率(3着内/外の割合)を保つ
            # random_state=42 で毎回同じように分割（再現性のため）
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            print(f"データを分割しました: 訓練データ {X_train.shape[0]}件, テストデータ {X_test.shape[0]}件")
        except Exception as e_split:
            print(f"!!! ERROR during data splitting: {e_split}")
            traceback.print_exc()
            self.root.after(0, lambda: self.update_status("エラー: データ分割失敗"))
            self.root.after(0, lambda err=e_split: messagebox.showerror("モデル学習エラー", f"データ分割中にエラーが発生しました:\n{err}"))
            return

        # 3. モデルの定義 (LightGBM Classifier)
        print("LightGBMモデルを定義します...")
        # objective='binary': 二値分類問題
        # metric='auc': 評価指標としてAUCを使う (早期停止用にも使える)
        # n_estimators: 木の数 (まずはデフォルト or 100程度)
        # random_state: 再現性のため
        lgb_clf = lgb.LGBMClassifier(objective='binary', metric='auc', n_estimators=100, random_state=42, verbosity=-1) # verbosity=-1 でログ抑制

        # 4. モデルの学習
        print("モデルの学習を開始します...")
        self.root.after(0, lambda: self.update_status("モデル学習中...")) # GUI更新はメインスレッドで
        try:
            # 訓練データで学習
            lgb_clf.fit(X_train, y_train)
            print("モデルの学習が完了しました。")
            self.root.after(0, lambda: self.update_status("モデル学習完了")) # GUI更新

            # ★ 学習済みモデルをクラス変数に保存 (後で予測に使うため)
            self.trained_model = lgb_clf
            print("学習済みモデルを self.trained_model に保存しました。")
            
            self.save_model_to_file() # ユーザーさん定義のモデル保存メソッド

        except Exception as e_fit:
            print(f"!!! ERROR during model training: {e_fit}")
            traceback.print_exc()
            self.root.after(0, lambda: self.update_status("エラー: モデル学習失敗"))
            self.root.after(0, lambda err=e_fit: messagebox.showerror("モデル学習エラー", f"モデル学習中にエラーが発生しました:\n{err}"))
            self.trained_model = None # 学習失敗時はNone
            return

        # 5. テストデータで予測 (確率を予測)
        print("テストデータで予測を実行します...")
        try:
            # predict_proba は [クラス0の確率, クラス1の確率] の numpy array を返す
            y_pred_proba = lgb_clf.predict_proba(X_test)[:, 1] # 3着以内(クラス1)に入る確率
        except Exception as e_pred:
            print(f"!!! ERROR during prediction: {e_pred}")
            traceback.print_exc()
            self.root.after(0, lambda: self.update_status("エラー: 予測実行失敗"))
            self.root.after(0, lambda err=e_pred: messagebox.showerror("モデル評価エラー", f"予測実行中にエラーが発生しました:\n{err}"))
            return

        # 6. モデルの評価 (簡単な指標)
        print("モデルの評価を行います...")
        self.root.after(0, lambda: self.update_status("モデル評価中...")) # GUI更新
        try:
            # AUCスコア (1に近いほど良い分類器)
            auc = roc_auc_score(y_test, y_pred_proba)
            print(f"  AUC Score: {auc:.4f}")

            # 確率を0/1に変換して他の指標も計算 (閾値0.5の場合)
            y_pred_binary = (y_pred_proba >= 0.5).astype(int)
            accuracy = accuracy_score(y_test, y_pred_binary)
            # zero_division=0 は、片方のクラスが全く予測されなかった場合に警告を抑制する
            precision = precision_score(y_test, y_pred_binary, zero_division=0) # 適合率: 1と予測した中で本当に1だった割合
            recall = recall_score(y_test, y_pred_binary, zero_division=0)    # 再現率: 本当に1の中で1と予測できた割合
            conf_matrix = confusion_matrix(y_test, y_pred_binary)
            # 混同行列の表示: [[TN, FP], [FN, TP]]
            # TN: 0と予測し実際も0, FP: 1と予測したが実際は0
            # FN: 0と予測したが実際は1, TP: 1と予測し実際も1

            print(f"  Accuracy (Threshold 0.5): {accuracy:.4f}")
            print(f"  Precision (Threshold 0.5): {precision:.4f}")
            print(f"  Recall (Threshold 0.5): {recall:.4f}")
            print(f"  Confusion Matrix (Threshold 0.5):\n{conf_matrix}")

            # --- ★ここからキャリブレーションプロットの描画コードを追加しました ---
            print("キャリブレーションプロットを作成します...")
            self.root.after(0, lambda: self.update_status("キャリブレーションプロット作成中..."))
            try:
                # calibration_curveの計算
                prob_true, prob_pred = calibration_curve(y_test, y_pred_proba, n_bins=10, strategy='uniform')

                # プロットの作成
                plt.figure(figsize=(8, 6))
                plt.plot(prob_pred, prob_true, marker='o', linewidth=1, label='LightGBM (本モデル)')
                plt.plot([0, 1], [0, 1], linestyle='--', color='gray', label='理想的なキャリブレーション')

                plt.xlabel("予測確率の区間平均 (Mean predicted probability)")
                plt.ylabel("実際の3着内率 (Fraction of positives)")
                plt.title("キャリブレーションプロット (Calibration Plot)")
                plt.legend(loc='lower right')
                plt.grid(True)
                
                plot_filename = "calibration_plot.png"
                # スクリプトを実行しているカレントワーキングディレクトリに保存
                plot_filepath = os.path.join(os.getcwd(), plot_filename) 

                plt.savefig(plot_filepath)
                print(f"キャリブレーションプロットを {plot_filepath} に保存しました。")
                self.root.after(0, lambda f_path=plot_filepath: self.update_status(f"プロット保存: {os.path.basename(f_path)}"))
                plt.close() # GUI環境でのフリーズを避けるため、表示せずに閉じる

            except Exception as e_calib_plot:
                print(f"!!! ERROR during calibration plot creation: {e_calib_plot}")
                traceback.print_exc()
                self.root.after(0, lambda: self.update_status("エラー: プロット作成失敗"))
            # --- ★キャリブレーションプロットの描画コードここまで ---

            # 結果をメッセージボックスで表示
            eval_result_text = f"モデル評価結果 (テストデータ):\n" \
                               f"AUC Score: {auc:.4f}\n" \
                               f"\n--- 閾値 0.5 での評価 ---\n" \
                               f"Accuracy (正解率): {accuracy:.4f}\n" \
                               f"Precision (適合率): {precision:.4f}\n" \
                               f"Recall (再現率): {recall:.4f}\n" \
                               f"\nConfusion Matrix:\n{conf_matrix}\n" \
                               f"(行: 実際の0/1, 列: 予測の0/1)\n\n" \
                               f"キャリブレーションプロットが calibration_plot.png として保存されました。" # ★メッセージに追記

            self.root.after(0, lambda text=eval_result_text: messagebox.showinfo("モデル評価結果", text)) # GUI更新
            self.root.after(0, lambda: self.update_status("モデル評価完了")) # GUI更新

        except Exception as e_eval:
            print(f"!!! ERROR during model evaluation: {e_eval}")
            traceback.print_exc()
            self.root.after(0, lambda: self.update_status("エラー: モデル評価失敗"))
            self.root.after(0, lambda err=e_eval: messagebox.showerror("モデル評価エラー", f"モデル評価中にエラーが発生しました:\n{err}"))

        print("--- Model Training and Evaluation Finished ---")
    # --- ここまでモデル学習・評価メソッド ---
    
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
        shutuba_list = self.get_shutuba_table(race_id)
        shutuba_df = self.format_shutuba_data(shutuba_list, race_id)

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
        
        train_button = ttk.Button(self.tab_data, text="モデル学習＆評価", command=self.train_and_evaluate_model)
        # ↓↓↓ pack() の正しいオプションを使う (例: タブの下部中央に配置) ↓↓↓
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

    # --- ローカルファイル読み込み ---
    def load_local_files(self, csv_path, json_path=None):
        """ローカルのCSVとJSONファイルを読み込み、統計計算を実行し、データを格納する"""
        # ★ 必要なライブラリ (pandas, os, json, tkinter) はファイル冒頭で import されている前提
        import pandas as pd # type: ignore
        import os
        import json
        from tkinter import messagebox
        import traceback # エラー詳細表示用にインポート
        import numpy as np # type: ignore # pd.NA を使う場合や型チェックで必要なら

        df_combined = None
        payout_data = []
        try:
            # --- CSVファイルの読み込み ---
            if csv_path and os.path.exists(csv_path):
                self.update_status(f"CSV読み込み中: {os.path.basename(csv_path)}")
                # ★ low_memory=False オプションを追加 (データ型推論の警告抑制に役立つことがある)
                try:
                     df_combined = pd.read_csv(csv_path, low_memory=False)
                     print(f"CSV読み込み成功: {df_combined.shape}")
                except pd.errors.EmptyDataError as e:
                     print(f"ERROR: CSVファイルが空か、読み込めませんでした: {csv_path}. Error: {e}")
                     self.root.after(0, lambda path=csv_path, err=e: messagebox.showerror("CSVエラー", f"CSVファイルが空か、読み込めませんでした:\n{path}\nエラー: {err}"))
                     self.root.after(0, lambda: self.update_status("エラー: CSV読み込み失敗"))
                     # データをクリアして終了
                     self.combined_data = pd.DataFrame(); self.payout_data = []
                     self.course_time_stats={}; self.father_stats={}; self.mother_father_stats={}; self.gate_stats={}; self.reference_times={}
                     if hasattr(self, 'processed_data'): self.processed_data = pd.DataFrame()
                     self.root.after(0, self.update_data_preview)
                     return # ★★★ return を追加 ★★★

                # --- データ型変換 (日付列など) ---
                date_cols = ['date', 'race_date'] # 可能性のある日付列名
                found_date_col = None

                for col in date_cols:
                    if col in df_combined.columns:
                        print(f"INFO: Processing date column '{col}'...")
                        try:
                            # ★★★ ここから日付変換の修正版 (format指定なし) ★★★
                            # 1. 文字列に変換し、前後の空白を除去 (念のため)
                            #    欠損値があるかもしれないので .astype(str) は注意が必要 -> fillna('') を使う
                            df_combined[col] = df_combined[col].fillna('').astype(str).str.strip()
                            # 2. 明らかに日付でないものや空文字列を pd.NA (Pandasの欠損値) に置換
                            df_combined[col] = df_combined[col].replace(['', '-', 'nan', 'NaT','None', 'null'], pd.NA, regex=False)

                            print(f"INFO: Attempting to convert column '{col}' to datetime using auto-parsing...")
                            # 3. Pandasの自動解析に任せる (errors='coerce' で失敗は NaT に)
                            converted_dates = pd.to_datetime(df_combined[col], errors='coerce')
                            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★

                            if converted_dates.notna().any(): # 1つでも変換成功したらOK
                                df_combined[col] = converted_dates # 変換結果を代入
                                print(f"INFO: Successfully converted '{col}' to datetime.")
                                found_date_col = col
                                nat_count = df_combined[col].isnull().sum()
                                total_count = len(df_combined[col])
                                print(f"DEBUG: NaT count in '{col}': {nat_count}/{total_count}")
                                if nat_count > 0:
                                     print(f"WARN: {nat_count} rows in '{col}' could not be converted to dates and are set to NaT.")
                                break # 最初に見つかった有効な日付列を使う
                            else:
                                # 自動解析でも全てNaTになった場合
                                print(f"WARN: Could not convert any values in '{col}' using auto-parsing.")
                                # found_date_col は None のまま
                        except Exception as e_date:
                            print(f"ERROR: An unexpected error occurred during date conversion for '{col}'. Error: {e_date}")
                            traceback.print_exc() # エラー詳細表示
                    # if col in df_combined.columns の終わり
                # for col in date_cols の終わり

                if found_date_col is None:
                    print("警告: 有効な日付列が見つかりませんでした。続行しますが、日付関連機能に影響が出る可能性があります。")
                    # 処理は中断せず、文字列のまま扱われることになる
                else:
                    print(f"INFO: Using '{found_date_col}' as the primary date column.")

                self.combined_data = df_combined.copy() # 処理済みのデータを格納

            elif csv_path: # ファイルパスは指定されたが見つからない場合
                 self.root.after(0, lambda: messagebox.showerror("ファイルエラー", f"指定されたCSVファイルが見つかりません:\n{csv_path}"))
                 self.root.after(0, lambda: self.update_status("エラー: 指定ファイルが見つかりません"))
                 self.combined_data = pd.DataFrame(); self.payout_data = []
                 self.course_time_stats={}; self.father_stats={}; self.mother_father_stats={}; self.gate_stats={}; self.reference_times={}
                 if hasattr(self, 'processed_data'): self.processed_data = pd.DataFrame()
                 self.root.after(0, self.update_data_preview); return
            else: # ファイルパスが指定されていない場合
                 print("情報: ローカルファイルパスが指定されていません。")
                 self.combined_data = pd.DataFrame(); self.payout_data = []
                 self.course_time_stats={}; self.father_stats={}; self.mother_father_stats={}; self.gate_stats={}; self.reference_times={}
                 if hasattr(self, 'processed_data'): self.processed_data = pd.DataFrame()
                 self.root.after(0, self.update_data_preview)
                 self.root.after(0, lambda: self.update_status("ファイルを選択してください")); return


            # --- JSONファイルの読み込み ---
            if json_path and os.path.exists(json_path):
                self.update_status(f"JSON読み込み中: {os.path.basename(json_path)}")
                try:
                    with open(json_path, 'r', encoding='utf-8') as f: payout_data = json.load(f)
                    print(f"JSON読み込み成功: {len(payout_data)} レース分")
                    self.payout_data = payout_data[:]
                except json.JSONDecodeError as e_json: print(f"ERROR: JSONデコード失敗: {e_json}"); self.payout_data = []
                except Exception as e_json_other: print(f"ERROR: JSON読込エラー: {e_json_other}"); self.payout_data = []
            elif json_path: print(f"警告: JSONファイルが見つかりません: {json_path}"); self.payout_data = []
            else: print("情報: 払い戻しJSONファイルは指定/検出されませんでした。"); self.payout_data = []

            # --- 統計計算 & データ前処理 ---
            if self.combined_data is not None and not self.combined_data.empty:
                self.update_status("各種統計データ計算中...")
                self._calculate_course_time_stats()
                if 'father' in self.combined_data.columns: self._calculate_sire_stats(sire_column='father')
                else: self.father_stats = {}
                if 'mother_father' in self.combined_data.columns: self._calculate_sire_stats(sire_column='mother_father')
                else: self.mother_father_stats = {}
                self._calculate_gate_stats()
                self._calculate_reference_times()
                self.preprocess_data_for_training() # ★ データ前処理を実行
            else:
                print("情報: combined_dataが空のため、統計計算と前処理をスキップします。")
                self.course_time_stats={}; self.father_stats={}; self.mother_father_stats={}; self.gate_stats={}; self.reference_times={}
                self.processed_data = pd.DataFrame()

            # --- UI更新 (統計計算・前処理完了後) ---
            final_data_ref = self.processed_data if hasattr(self, 'processed_data') and self.processed_data is not None and not self.processed_data.empty else self.combined_data
            if final_data_ref is not None and not final_data_ref.empty:
                 rows = final_data_ref.shape[0]
                 status_msg = f"ローカルデータ準備完了: {rows}行 (統計・前処理計算済)"
                 info_msg = f"データの読み込みと準備が完了しました。\nレースデータ: {rows}行\n払い戻しデータ:{len(self.payout_data)}レース分\n(統計・前処理計算済)"
                 self.root.after(0, lambda msg=status_msg: self.update_status(msg))
                 self.root.after(0, lambda msg=info_msg: messagebox.showinfo("読み込み完了", msg))
            else:
                 self.root.after(0, lambda: self.update_status("データ読み込み失敗またはデータなし"))
                 self.root.after(0, lambda: messagebox.showwarning("データなし", "指定されたファイルから有効なデータが読み込めませんでした。"))

            # --- 学習データ準備のテスト呼び出し (一時的 - 必要ならコメントアウト解除) ---
            # print("\n--- Testing _prepare_data_for_model ---")
            # X_train_sample, y_train_sample = self._prepare_data_for_model()
            # if X_train_sample is not None and y_train_sample is not None:
            #     print("Sample of prepared feature data (X):"); print(X_train_sample.head())
            #     print("\nSample of prepared target data (y):"); print(y_train_sample.head())
            #     print(f"\nShape of X: {X_train_sample.shape}, Shape of y: {y_train_sample.shape}")
            # else: print("Failed to prepare data for model.")
            # print("--- End Testing _prepare_data_for_model ---")
            # --- ここまでテスト呼び出し ---

            self.root.after(0, self.update_data_preview) # UI更新は必ず行う

        except FileNotFoundError: # 通常発生しないはず
             print(f"ERROR: FileNotFoundError (Should not happen): {csv_path}")
             self.root.after(0, lambda: messagebox.showerror("ファイルエラー", f"指定されたCSVファイルが見つかりません:\n{csv_path}"))
             # データクリア処理を追加
             self.combined_data = pd.DataFrame(); self.payout_data = []
             self.course_time_stats={}; self.father_stats={}; self.mother_father_stats={}; self.gate_stats={}; self.reference_times={}
             if hasattr(self, 'processed_data'): self.processed_data = pd.DataFrame()
             self.root.after(0, self.update_data_preview)
        except Exception as e:
            print(f"ERROR: An unexpected error occurred in load_local_files: {e}")
            traceback.print_exc()
            # messagebox はメインスレッドから呼び出す
            self.root.after(0, lambda err=e: self.handle_collection_error(err)) # 既存のエラー処理へ

    def process_collection_results(self, df_combined, payout_data, start_year, start_month, end_year, end_month):
        """データ収集完了後の処理 (UIスレッドで実行、統計計算追加)"""
        if df_combined is not None and not df_combined.empty:
            # データをクラス変数に格納
            self.combined_data = df_combined.copy()
            self.payout_data = payout_data[:]

            # --- ★★★ タイム統計データと血統統計データの計算を実行 ★★★ ---
            # combined_data が更新されたので統計を再計算する
            self.update_status("各種統計データ計算中...") # ステータスバー更新
            self._calculate_course_time_stats() # ← タイム統計

            # 血統統計 (父と母父)
            if self.combined_data is not None and not self.combined_data.empty:
                 # 父の統計計算
                 if 'father' in self.combined_data.columns:
                     print("父別統計計算開始...") # デバッグ用
                     self._calculate_sire_stats(sire_column='father')
                 else:
                     print("情報: combined_dataに'father'列がないため、父データの統計計算をスキップします。")
                     self.father_stats = {} # 列がない場合は空の辞書を設定

                 # ★★★ 母父の統計計算を追加 ★★★
                 if 'mother_father' in self.combined_data.columns:
                     print("母父別統計計算開始...") # デバッグ用
                     self._calculate_sire_stats(sire_column='mother_father')
                 else:
                     print("情報: combined_dataに'mother_father'列がないため、母父データの統計計算をスキップします。")
                     self.mother_father_stats = {} # 列がない場合は空の辞書を設定
                     
                 self._calculate_gate_stats()
                 self._calculate_reference_times()
                 self.preprocess_data_for_training()
                 
            else: # combined_data が空またはNoneの場合
                 print("情報: combined_dataが空のため、統計計算をスキップします。")
                 # 統計データもクリア (念のため)
                 self.course_time_stats = {}; self.father_stats = {}; self.mother_father_stats = {}
                 self.gate_stats = {} 
                 self.reference_times = {} 
            # --- ★★★ 計算実行ここまで ★★★ ---

            # プレビュー更新と完了メッセージ
            self.update_status(f"データ処理完了: {self.combined_data.shape[0]}行 {self.combined_data.shape[1]}列")
            messagebox.showinfo("データ処理完了", f"データの準備が完了しました。\nレースデータ: {self.combined_data.shape[0]}行\n払い戻しデータ:{len(self.payout_data)}レース分\n(各種統計計算済)") # メッセージ変更に各種統計計算済を追加
            self.update_data_preview()

            # --- 自動保存処理 (変更なし) ---
            # ... (自動保存ロジックは変更なし) ...
            if start_year: # netkeibaから取得した場合のみ自動保存
                save_dir = self.settings.get("data_dir", ".")
                if not os.path.exists(save_dir):
                     try: os.makedirs(save_dir)
                     except: save_dir = "." # ディレクトリ作成失敗時はカレントディレクトリに保存
                period_str = f"{start_year}{start_month:02d}_{end_year}{end_month:02d}"
                save_filename_base = "netkeiba_data" # 必要なら設定可能に
                results_filename = os.path.join(save_dir, f"{save_filename_base}_combined_{period_str}.csv")
                payouts_filename = os.path.join(save_dir, f"{save_filename_base}_payouts_{period_str}.json")
                try:
                    # ★ 保存するデータは self.combined_data (統計計算後)
                    # combined_dataに日付列が datetime型になっているか確認
                    date_col_to_save = None
                    if 'date' in self.combined_data.columns and pd.api.types.is_datetime64_any_dtype(self.combined_data['date']): date_col_to_save = 'date'
                    elif 'race_date' in self.combined_data.columns and pd.api.types.is_datetime64_any_dtype(self.combined_data['race_date']): date_col_to_save = 'race_date'

                    if date_col_to_save:
                         # 日付列をYYYY年MM月DD日 形式の文字列に変換して保存 (Excelなどで見やすくするため)
                         df_to_save = self.combined_data.copy()
                         df_to_save[date_col_to_save] = df_to_save[date_col_to_save].dt.strftime('%Y年%m月%d日')
                         df_to_save.to_csv(results_filename, index=False, encoding='utf-8-sig')
                    else:
                         # 日付列が特定できない、またはdatetime型でない場合はそのまま保存
                         self.combined_data.to_csv(results_filename, index=False, encoding='utf-8-sig')

                    print(f"収集データをCSVに保存しました: {results_filename}")
                    self.update_status(f"データ処理完了 (CSV保存済): {self.combined_data.shape[0]}行")
                    if self.payout_data:
                        with open(payouts_filename, 'w', encoding='utf-8') as f:
                            json.dump(self.payout_data, f, indent=2, ensure_ascii=False)
                        print(f"払い戻しデータをJSONに保存しました: {payouts_filename}")
                    messagebox.showinfo("データ保存完了", f"収集したデータは以下に保存されました:\nCSV: {results_filename}\nJSON: {payouts_filename}")
                except Exception as e: messagebox.showerror("自動保存エラー", f"収集データの自動保存エラー:\n{e}"); print(f"自動保存エラー: {e}")

        else: # df_combined が空の場合
            self.update_status("データ処理完了: 有効なデータがありませんでした。")
            messagebox.showwarning("データ処理完了", "有効なレースデータが見つかりませんでした。")
            # データをクリア
            self.combined_data = pd.DataFrame(); self.payout_data = []
            self.course_time_stats = {} # 統計データもクリア
            self.father_stats = {}; self.mother_father_stats = {} # 血統統計もクリア
            self.update_data_preview()

    def handle_collection_error(self, error):
        """データ収集/読み込みエラー発生時の処理 (UIスレッドで実行)"""
        error_message = f"{type(error).__name__}: {error}"
        self.update_status(f"エラー発生: {error_message}")
        messagebox.showerror("処理エラー", f"データの取得または読み込み中にエラーが発生しました:\n{error_message}")
        print("\n--- エラー詳細 ---")
        traceback.print_exc() # コンソールに詳細なエラーを出力
        print("-----------------\n")

    # ===========================================================
    # === データ取得/読み込み関連のメソッド (ここまで追加) ===
    # ===========================================================

    def init_analysis_tab(self):
        """データ分析タブの初期化（結果表示をテーブルに変更）"""
        left_frame = ttk.LabelFrame(self.tab_analysis, text="分析オプション")
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # 分析タイプ選択
        analysis_type_label = ttk.Label(left_frame, text="分析タイプ:")
        analysis_type_label.grid(row=0, column=0, sticky=tk.W, padx=10, pady=5)
        self.analysis_type_var = tk.StringVar(value="人気別分析") # デフォルト変更
        analysis_type_combo = ttk.Combobox(left_frame, textvariable=self.analysis_type_var, state="readonly", width=15)
        analysis_type_combo['values'] = ("人気別分析", "距離別分析", "コース種別分析", "騎手分析", "血統分析", "競馬場分析(未)", "特徴量重要度(未)", "オッズ分析(未)", "調教師分析(未)") # ← 血統分析を追加(未)削除
        analysis_type_combo.grid(row=0, column=1, sticky=tk.EW, padx=10, pady=5)

        # --- フィルターオプション ---
        filter_frame = ttk.LabelFrame(left_frame, text="フィルター")
        filter_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)
        # 競馬場フィルター
        track_label = ttk.Label(filter_frame, text="競馬場:")
        track_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.track_var = tk.StringVar(value="すべて")
        track_combo = ttk.Combobox(filter_frame, textvariable=self.track_var, width=10, state="readonly",
                                   values=("すべて", "東京", "中山", "阪神", "京都", "中京", "小倉", "福島", "新潟", "札幌", "函館"))
        track_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        # コース種別フィルター
        course_label = ttk.Label(filter_frame, text="コース:")
        course_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.course_var = tk.StringVar(value="すべて")
        course_combo = ttk.Combobox(filter_frame, textvariable=self.course_var, width=10, state="readonly",
                                    values=("すべて", "芝", "ダート", "障害"))
        course_combo.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        # 距離フィルター
        distance_label = ttk.Label(filter_frame, text="距離(m):")
        distance_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        distance_frame = ttk.Frame(filter_frame)
        distance_frame.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        self.min_distance_var = tk.StringVar(value="すべて")
        min_distance_combo = ttk.Combobox(distance_frame, textvariable=self.min_distance_var, width=7,
                                           values=["すべて"] + [str(dist) for dist in range(1000, 4001, 100)])
        min_distance_combo.grid(row=0, column=0, padx=2)
        distance_separator = ttk.Label(distance_frame, text="〜")
        distance_separator.grid(row=0, column=1, padx=2)
        self.max_distance_var = tk.StringVar(value="すべて")
        max_distance_combo = ttk.Combobox(distance_frame, textvariable=self.max_distance_var, width=7,
                                           values=["すべて"] + [str(dist) for dist in range(1000, 4001, 100)])
        max_distance_combo.grid(row=0, column=2, padx=2)

        # 分析実行ボタン
        analyze_button = ttk.Button(left_frame, text="分析実行", command=self.run_analysis)
        analyze_button.grid(row=2, column=0, columnspan=2, pady=20)

        # === 右側のフレーム（分析結果をテーブル表示） ===
        # ★★★ 変数名を self.analysis_result_frame に変更 ★★★
        self.analysis_result_frame = ttk.LabelFrame(self.tab_analysis, text="分析結果")
        self.analysis_result_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10) # ★ pack も変更後の変数名で

        # --- テーブル表示エリア ---
        # ★★★ 親ウィジェットを self.analysis_result_frame に変更 ★★★
        analysis_table_frame = ttk.Frame(self.analysis_result_frame)
        analysis_table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        y_scrollbar = ttk.Scrollbar(analysis_table_frame, orient=tk.VERTICAL)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar = ttk.Scrollbar(analysis_table_frame, orient=tk.HORIZONTAL)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.analysis_tree = ttk.Treeview(analysis_table_frame,
                                           yscrollcommand=y_scrollbar.set,
                                           xscrollcommand=x_scrollbar.set,
                                           height=15)
        self.analysis_tree.pack(fill=tk.BOTH, expand=True)
        y_scrollbar.config(command=self.analysis_tree.yview)
        x_scrollbar.config(command=self.analysis_tree.xview)

        # 結果保存ボタン (必要であれば後で実装)
        # save_result_button = ttk.Button(self.analysis_result_frame, text="結果を保存", command=self.save_analysis_result) # ★ 親を変更
        # save_result_button.pack(pady=10, anchor=tk.E)

    
    def init_prediction_tab(self):
        """予測タブの初期化"""
        # 左側のフレーム（予測設定）
        left_frame = ttk.LabelFrame(self.tab_prediction, text="予測設定")
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # --- レース選択 (改善) ---
        race_select_frame = ttk.LabelFrame(left_frame, text="予測対象レース")
        race_select_frame.grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)

        # TODO: 将来的には日付、競馬場からレースリストを動的に取得し選択できるようにする
        race_id_label = ttk.Label(race_select_frame, text="レースID入力:")
        race_id_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.predict_race_id_var = tk.StringVar()
        race_id_entry = ttk.Entry(race_select_frame, textvariable=self.predict_race_id_var, width=20)
        race_id_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)

        race_button = ttk.Button(race_select_frame, text="レース情報表示", command=self.fetch_race_info_for_prediction)
        race_button.grid(row=1, column=0, columnspan=2, pady=10)

        # --- 予測タイプ選択 ---
        prediction_type_frame = ttk.LabelFrame(left_frame, text="予測・購入馬券種")
        prediction_type_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)

        self.prediction_type_var = tk.StringVar(value="win") # 単勝をデフォルトに

        win_radio = ttk.Radiobutton(prediction_type_frame, text="単勝", variable=self.prediction_type_var, value="win")
        win_radio.pack(anchor=tk.W, padx=10, pady=2)
        place_radio = ttk.Radiobutton(prediction_type_frame, text="複勝", variable=self.prediction_type_var, value="place")
        place_radio.pack(anchor=tk.W, padx=10, pady=2)
        wide_radio = ttk.Radiobutton(prediction_type_frame, text="ワイド", variable=self.prediction_type_var, value="wide")
        wide_radio.pack(anchor=tk.W, padx=10, pady=2)
        uren_radio = ttk.Radiobutton(prediction_type_frame, text="馬連", variable=self.prediction_type_var, value="uren")
        uren_radio.pack(anchor=tk.W, padx=10, pady=2)
        utan_radio = ttk.Radiobutton(prediction_type_frame, text="馬単", variable=self.prediction_type_var, value="utan") # exacta -> utan
        utan_radio.pack(anchor=tk.W, padx=10, pady=2)
        sanfuku_radio = ttk.Radiobutton(prediction_type_frame, text="三連複", variable=self.prediction_type_var, value="sanfuku")
        sanfuku_radio.pack(anchor=tk.W, padx=10, pady=2)
        santan_radio = ttk.Radiobutton(prediction_type_frame, text="三連単", variable=self.prediction_type_var, value="santan") # trifecta -> santan
        santan_radio.pack(anchor=tk.W, padx=10, pady=2)

        # --- 戦略設定 (設定タブと連動させる) ---
        strategy_frame = ttk.LabelFrame(left_frame, text="購入戦略 (設定タブで変更)")
        strategy_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)

        min_ev_label = ttk.Label(strategy_frame, text="最小期待値:")
        min_ev_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.pred_min_ev_label = ttk.Label(strategy_frame, text=self.settings.get("min_expected_value", "N/A")) # 設定値を表示
        self.pred_min_ev_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        min_prob_label = ttk.Label(strategy_frame, text="最小確率:")
        min_prob_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.pred_min_prob_label = ttk.Label(strategy_frame, text=self.settings.get("min_probability", "N/A")) # 設定値を表示
        self.pred_min_prob_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        kelly_label = ttk.Label(strategy_frame, text="ケリー係数:")
        kelly_label.grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.pred_kelly_label = ttk.Label(strategy_frame, text=self.settings.get("kelly_fraction", "N/A")) # 設定値を表示
        self.pred_kelly_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        max_bet_label = ttk.Label(strategy_frame, text="最大賭け金比率:")
        max_bet_label.grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.pred_max_bet_label = ttk.Label(strategy_frame, text=self.settings.get("max_bet_ratio", "N/A")) # 設定値を表示
        self.pred_max_bet_label.grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)

        # 予測実行ボタン
        predict_button = ttk.Button(left_frame, text="予測実行", command=self.run_prediction)
        predict_button.grid(row=3, column=0, columnspan=2, pady=20)

        # 右側のフレーム（予測結果）
        right_frame = ttk.Frame(self.tab_prediction) # LabelFrameをやめてFrameに
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # レース情報表示
        race_info_frame = ttk.LabelFrame(right_frame, text="レース情報")
        race_info_frame.pack(fill=tk.X, padx=0, pady=(0, 5)) # パディング調整

        self.race_info_label = ttk.Label(race_info_frame, text="レース情報: 未選択", font=("Meiryo UI", 10, "bold"))
        self.race_info_label.pack(anchor=tk.W, padx=5, pady=2)

        self.race_details_label = ttk.Label(race_info_frame, text="")
        self.race_details_label.pack(anchor=tk.W, padx=5, pady=2)

        # 予測結果テーブル
        result_frame = ttk.LabelFrame(right_frame, text="予測結果 (上位表示)")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=5)

        y_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.prediction_tree = ttk.Treeview(result_frame, yscrollcommand=y_scrollbar.set, height=8) # 高さを指定
        self.prediction_tree.pack(fill=tk.BOTH, expand=True, padx=(5,0), pady=5) # 右側にスクロールバー分のスペース
        y_scrollbar.config(command=self.prediction_tree.yview)

        # 推奨馬券表示
        recommendation_frame = ttk.LabelFrame(right_frame, text="推奨馬券と購入額 (シミュレーション)")
        recommendation_frame.pack(fill=tk.X, padx=0, pady=5)

        self.recommendation_text = tk.Text(recommendation_frame, height=6, wrap=tk.WORD, font=("Meiryo UI", 9)) # フォント指定
        rec_scrollbar = ttk.Scrollbar(recommendation_frame, orient=tk.VERTICAL, command=self.recommendation_text.yview)
        self.recommendation_text.config(yscrollcommand=rec_scrollbar.set)
        rec_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.recommendation_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 結果保存ボタン
        save_prediction_button = ttk.Button(right_frame, text="予測結果を保存", command=self.save_prediction_result)
        save_prediction_button.pack(pady=10, anchor=tk.E)
        
        


    def init_results_tab(self):
        """結果検証タブの初期化"""
        # 左側のフレーム（結果分析オプション）
        left_frame = ttk.LabelFrame(self.tab_results, text="バックテスト設定") # 名前変更
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # --- 対象期間選択 ---
        period_frame = ttk.LabelFrame(left_frame, text="対象期間")
        period_frame.grid(row=0, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)

        current_year = datetime.now().year
        years = tuple(str(year) for year in range(2010, current_year + 1))
        months = tuple(f"{month:02d}" for month in range(1, 13))

        from_label = ttk.Label(period_frame, text="開始:")
        from_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.result_from_year_var = tk.StringVar(value=str(current_year - 5)) # 5年前
        from_year_combo = ttk.Combobox(period_frame, textvariable=self.result_from_year_var, width=5, state="readonly", values=years)
        from_year_combo.grid(row=0, column=1, padx=2, pady=2)
        self.result_from_month_var = tk.StringVar(value="01")
        from_month_combo = ttk.Combobox(period_frame, textvariable=self.result_from_month_var, width=3, state="readonly", values=months)
        from_month_combo.grid(row=0, column=2, padx=2, pady=2)

        to_label = ttk.Label(period_frame, text="終了:")
        to_label.grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.result_to_year_var = tk.StringVar(value=str(current_year))
        to_year_combo = ttk.Combobox(period_frame, textvariable=self.result_to_year_var, width=5, state="readonly", values=years)
        to_year_combo.grid(row=1, column=1, padx=2, pady=2)
        self.result_to_month_var = tk.StringVar(value=datetime.now().strftime("%m"))
        to_month_combo = ttk.Combobox(period_frame, textvariable=self.result_to_month_var, width=3, state="readonly", values=months)
        to_month_combo.grid(row=1, column=2, padx=2, pady=2)

        # --- 対象馬券種選択 ---
        bet_type_frame = ttk.LabelFrame(left_frame, text="対象馬券種")
        bet_type_frame.grid(row=1, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)

        self.res_win_var = tk.BooleanVar(value=True)
        win_check = ttk.Checkbutton(bet_type_frame, text="単勝", variable=self.res_win_var)
        win_check.grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)

        self.res_place_var = tk.BooleanVar(value=True)
        place_check = ttk.Checkbutton(bet_type_frame, text="複勝", variable=self.res_place_var)
        place_check.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)

        self.res_wide_var = tk.BooleanVar(value=True)
        wide_check = ttk.Checkbutton(bet_type_frame, text="ワイド", variable=self.res_wide_var)
        wide_check.grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)

        self.res_uren_var = tk.BooleanVar(value=True)
        uren_check = ttk.Checkbutton(bet_type_frame, text="馬連", variable=self.res_uren_var)
        uren_check.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)

        self.res_utan_var = tk.BooleanVar(value=True)
        utan_check = ttk.Checkbutton(bet_type_frame, text="馬単", variable=self.res_utan_var)
        utan_check.grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)

        self.res_sanfuku_var = tk.BooleanVar(value=True)
        sanfuku_check = ttk.Checkbutton(bet_type_frame, text="三連複", variable=self.res_sanfuku_var)
        sanfuku_check.grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)

        self.res_santan_var = tk.BooleanVar(value=True)
        santan_check = ttk.Checkbutton(bet_type_frame, text="三連単", variable=self.res_santan_var)
        santan_check.grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)

        # --- 分析タイプ選択 (グラフの種類) ---
        result_type_frame = ttk.LabelFrame(left_frame, text="グラフ表示")
        result_type_frame.grid(row=2, column=0, columnspan=2, sticky=tk.EW, padx=10, pady=10)

        result_type_label = ttk.Label(result_type_frame, text="分析タイプ:")
        result_type_label.pack(anchor=tk.W, padx=5, pady=2)

        self.result_type_var = tk.StringVar(value="収支推移") # デフォルト変更
        result_type_combo = ttk.Combobox(result_type_frame, textvariable=self.result_type_var, state="readonly", width=15)
        result_type_combo['values'] = ("収支推移", "月別収支", "年別収支", "馬券種別ROI", "的中率", "期待値別ROI") # 見直し
        result_type_combo.pack(anchor=tk.W, padx=5, pady=2)

        # バックテスト実行ボタン
        analyze_button = ttk.Button(left_frame, text="バックテスト実行", command=self.run_result_analysis)
        analyze_button.grid(row=3, column=0, columnspan=2, pady=20)

        # 右側のフレーム（分析結果）
        right_frame = ttk.Frame(self.tab_results) # LabelFrameをやめてFrameに
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # サマリー表示
        summary_frame = ttk.LabelFrame(right_frame, text="バックテスト結果サマリー")
        summary_frame.pack(fill=tk.X, padx=0, pady=(0,5)) # パディング調整

        self.summary_text = tk.Text(summary_frame, height=7, wrap=tk.WORD, font=("Meiryo UI", 9)) # フォント指定
        summary_scrollbar = ttk.Scrollbar(summary_frame, orient=tk.VERTICAL, command=self.summary_text.yview)
        self.summary_text.config(yscrollcommand=summary_scrollbar.set)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # グラフ表示エリア
        graph_frame = ttk.LabelFrame(right_frame, text="グラフ表示")
        graph_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=5)

        self.result_figure = plt.Figure(figsize=(6, 4), dpi=100)
        # self.result_figure.patch.set_facecolor('#f0f0f0') # 背景色
        self.result_canvas = FigureCanvasTkAgg(self.result_figure, graph_frame)
        self.result_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 結果保存ボタン
        save_result_analysis_button = ttk.Button(right_frame, text="結果を保存", command=self.save_result_analysis)
        save_result_analysis_button.pack(pady=10, anchor=tk.E)


    def init_settings_tab(self):
        """設定タブの初期化"""
        settings_frame = ttk.Frame(self.tab_settings, padding="10")
        settings_frame.pack(fill=tk.BOTH, expand=True)

        # 戦略設定
        strategy_frame = ttk.LabelFrame(settings_frame, text="購入戦略パラメータ")
        strategy_frame.pack(fill=tk.X, padx=10, pady=10)
        strategy_frame.columnconfigure(1, weight=1) # Entryを広げるため

        row_idx = 0
        # 最小期待値
        min_ev_label = ttk.Label(strategy_frame, text="最小期待値:")
        min_ev_label.grid(row=row_idx, column=0, sticky=tk.W, padx=10, pady=5)
        self.settings_min_ev_var = tk.StringVar()
        min_ev_entry = ttk.Entry(strategy_frame, textvariable=self.settings_min_ev_var, width=10)
        min_ev_entry.grid(row=row_idx, column=1, sticky=tk.W, padx=10, pady=5)
        min_ev_desc = ttk.Label(strategy_frame, text="この値以上の期待値を持つ馬券のみ購入対象とする (例: 1.1)")
        min_ev_desc.grid(row=row_idx, column=2, sticky=tk.W, padx=10, pady=5)
        row_idx += 1

        # 最小予測確率
        min_prob_label = ttk.Label(strategy_frame, text="最小予測確率:")
        min_prob_label.grid(row=row_idx, column=0, sticky=tk.W, padx=10, pady=5)
        self.settings_min_prob_var = tk.StringVar()
        min_prob_entry = ttk.Entry(strategy_frame, textvariable=self.settings_min_prob_var, width=10)
        min_prob_entry.grid(row=row_idx, column=1, sticky=tk.W, padx=10, pady=5)
        min_prob_desc = ttk.Label(strategy_frame, text="この値以上の予測確率を持つ馬券のみ購入対象とする (例: 0.1 = 10%)")
        min_prob_desc.grid(row=row_idx, column=2, sticky=tk.W, padx=10, pady=5)
        row_idx += 1

        # ケリー係数
        kelly_label = ttk.Label(strategy_frame, text="ケリー係数:")
        kelly_label.grid(row=row_idx, column=0, sticky=tk.W, padx=10, pady=5)
        self.settings_kelly_var = tk.StringVar()
        kelly_entry = ttk.Entry(strategy_frame, textvariable=self.settings_kelly_var, width=10)
        kelly_entry.grid(row=row_idx, column=1, sticky=tk.W, padx=10, pady=5)
        kelly_desc = ttk.Label(strategy_frame, text="ケリー基準で計算された投資比率に乗じる係数 (0 < kelly <= 1, 例: 0.5 = ハーフケリー)")
        kelly_desc.grid(row=row_idx, column=2, sticky=tk.W, padx=10, pady=5)
        row_idx += 1

        # 最大賭け金比率
        max_bet_label = ttk.Label(strategy_frame, text="最大投資比率:") # 名称変更
        max_bet_label.grid(row=row_idx, column=0, sticky=tk.W, padx=10, pady=5)
        self.settings_max_bet_var = tk.StringVar()
        max_bet_entry = ttk.Entry(strategy_frame, textvariable=self.settings_max_bet_var, width=10)
        max_bet_entry.grid(row=row_idx, column=1, sticky=tk.W, padx=10, pady=5)
        max_bet_desc = ttk.Label(strategy_frame, text="1レースあたりの最大投資額を総資金の割合で制限 (例: 0.05 = 5%)")
        max_bet_desc.grid(row=row_idx, column=2, sticky=tk.W, padx=10, pady=5)
        row_idx += 1

        # ディレクトリ設定
        dir_frame = ttk.LabelFrame(settings_frame, text="保存先ディレクトリ")
        dir_frame.pack(fill=tk.X, padx=10, pady=10, ipady=5)
        dir_frame.columnconfigure(1, weight=1) # Entryを広げるため

        row_idx = 0
        # データディレクトリ
        data_dir_label = ttk.Label(dir_frame, text="データ:")
        data_dir_label.grid(row=row_idx, column=0, sticky=tk.W, padx=10, pady=5)
        self.settings_data_dir_var = tk.StringVar()
        data_dir_entry = ttk.Entry(dir_frame, textvariable=self.settings_data_dir_var, width=40)
        data_dir_entry.grid(row=row_idx, column=1, sticky=tk.EW, padx=10, pady=5)
        data_dir_button = ttk.Button(dir_frame, text="参照", command=lambda: self.browse_directory(self.settings_data_dir_var))
        data_dir_button.grid(row=row_idx, column=2, padx=10, pady=5)
        row_idx += 1

        # モデルディレクトリ
        models_dir_label = ttk.Label(dir_frame, text="学習モデル:")
        models_dir_label.grid(row=row_idx, column=0, sticky=tk.W, padx=10, pady=5)
        self.settings_models_dir_var = tk.StringVar()
        models_dir_entry = ttk.Entry(dir_frame, textvariable=self.settings_models_dir_var, width=40)
        models_dir_entry.grid(row=row_idx, column=1, sticky=tk.EW, padx=10, pady=5)
        models_dir_button = ttk.Button(dir_frame, text="参照", command=lambda: self.browse_directory(self.settings_models_dir_var))
        models_dir_button.grid(row=row_idx, column=2, padx=10, pady=5)
        row_idx += 1

        # 結果ディレクトリ
        results_dir_label = ttk.Label(dir_frame, text="分析/予測結果:")
        results_dir_label.grid(row=row_idx, column=0, sticky=tk.W, padx=10, pady=5)
        self.settings_results_dir_var = tk.StringVar()
        results_dir_entry = ttk.Entry(dir_frame, textvariable=self.settings_results_dir_var, width=40)
        results_dir_entry.grid(row=row_idx, column=1, sticky=tk.EW, padx=10, pady=5)
        results_dir_button = ttk.Button(dir_frame, text="参照", command=lambda: self.browse_directory(self.settings_results_dir_var))
        results_dir_button.grid(row=row_idx, column=2, padx=10, pady=5)
        row_idx += 1

        # ボタンフレーム
        button_frame = ttk.Frame(settings_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=20)

        reset_settings_button = ttk.Button(button_frame, text="デフォルトに戻す", command=self.reset_settings)
        reset_settings_button.pack(side=tk.RIGHT, padx=10)

        save_settings_button = ttk.Button(button_frame, text="設定を保存", command=self.save_settings)
        save_settings_button.pack(side=tk.RIGHT, padx=10)

    # --- Helper Methods ---
    def update_status(self, text):
        """ステータスバーのテキストを更新"""
        self.status_var.set(text)
        self.root.update_idletasks() # 即時反映

    def run_in_thread(self, target_func, *args):
        """指定された関数を別スレッドで実行"""
        thread = threading.Thread(target=target_func, args=args, daemon=True)
        thread.start()

    # --- File/Directory Browsing ---
    def browse_file(self):
        """レース結果CSVファイル選択ダイアログを表示"""
        # 設定で指定されたデータディレクトリを初期ディレクトリにする
        initial_dir = self.settings.get("data_dir", ".")
        file_path = filedialog.askopenfilename(
            title="レース結果 CSVファイルを選択",
            initialdir=initial_dir,
            filetypes=[("CSVファイル", "*.csv"), ("すべてのファイル", "*.*")]
        )
        if file_path:
            self.file_path_var.set(file_path)
            # ファイル選択時に自動で読み込みを開始する（オプション）
            # self.fetch_data()

    def browse_directory(self, var):
        """ディレクトリ選択ダイアログを表示"""
        initial_dir = var.get() if os.path.isdir(var.get()) else os.path.expanduser("~")
        dir_path = filedialog.askdirectory(title="ディレクトリを選択", initialdir=initial_dir)
        if dir_path:
            var.set(dir_path)

    # --- Data Management ---
    def fetch_data(self):
        """データ取得/読み込み処理"""
        source = self.data_source_var.get()
        self.update_status(f"{source} からデータ取得/読み込み中...")

        if "ローカルファイル" in source:
            file_path = self.file_path_var.get()
             # ★★★ 修正箇所 ★★★
            # ファイルパスが空でもエラーにせず、そのまま _load_local_csv を呼び出す
            # (ファイルが存在しない場合のチェックは _load_local_csv 側で行う)
            # if not file_path or not os.path.exists(file_path):
            #     messagebox.showerror("ファイルエラー", "有効なCSVファイルが選択されていません。")
            #     self.update_status("エラー: ファイル未選択")
            #     return
            self.run_in_thread(self._load_local_csv, file_path) # ファイルパスを渡す
        else:
            # Web取得ロジック (変更なし)
            messagebox.showinfo("未実装", f"{source} からのデータ取得は現在実装されていません。\nローカルファイルを選択してください。")
            self.update_status("準備完了")


    def _load_local_csv(self, file_path):
        """ローカルCSVファイルの読み込み（別スレッドで実行）"""
        # !!! 重要 !!!
        # この関数はサンプルです。実際のCSVファイルの形式に合わせて、
        # pandas.read_csvの引数（encoding, header, usecolsなど）や、
        # 読み込み後のデータ前処理（列名変更、型変換、結合など）を実装する必要があります。
        # ここでは、generate_sample_dataで生成されるデータに近い形式を仮定します。
        try:
             # ★★★ 修正箇所 ★★★
            # ファイルパスが指定されているかチェック
            if file_path and os.path.exists(file_path):
                # --- ファイルパスがある場合：実際のCSV読み込み処理 ---
                self.update_status(f"ローカルファイル読み込み中: {os.path.basename(file_path)}")
                # 例: 複数のCSV（レース情報、馬情報、結果情報）を読み込む場合
                # ... (実際のCSV読み込み処理、現状はコメントアウトされている)

                # --- ここではサンプルデータの読み込みをシミュレート ---
                self.generate_sample_data() # ★ 将来的には実際のCSV読み込みに置き換える

                # --- データ結合と前処理 ---
                if self.result_data is not None and self.race_data is not None and self.horse_data is not None:
                     merged_data = pd.merge(self.result_data, self.race_data, on='race_id', how='left')
                     self.combined_data = pd.merge(merged_data, self.horse_data, on='horse_id', how='left')
                     # 前処理
                     self.combined_data['race_date'] = pd.to_datetime(self.combined_data['race_date'])
                     print("データ結合完了:", self.combined_data.shape)
                     print("結合データ Columns:", self.combined_data.columns.tolist())
                else:
                    self.combined_data = None

                # UI更新
                self.root.after(0, self.update_data_preview)
                self.root.after(0, lambda: self.update_status(f"ローカルファイル読み込み完了: {os.path.basename(file_path)}"))
                self.root.after(0, lambda: messagebox.showinfo("読み込み完了", f"データの読み込みが完了しました。\n結合データ: {self.combined_data.shape if self.combined_data is not None else 'N/A'}"))

            elif file_path and not os.path.exists(file_path):
                # --- ファイルパスはあるが存在しない場合：エラー表示 ---
                self.root.after(0, lambda: messagebox.showerror("ファイルエラー", f"指定されたファイルが見つかりません:\n{file_path}"))
                self.root.after(0, lambda: self.update_status("エラー: 指定ファイルが見つかりません"))
                # データクリア
                self.race_data, self.horse_data, self.result_data, self.combined_data = None, None, None, None
                self.root.after(0, self.update_data_preview)

            else:
                # --- ファイルパスが指定されていない場合：サンプルデータを生成 ---
                self.update_status("サンプルデータ生成中...")
                self.generate_sample_data()

                # --- データ結合と前処理 (サンプルデータ用) ---
                if self.result_data is not None and self.race_data is not None and self.horse_data is not None:
                     merged_data = pd.merge(self.result_data, self.race_data, on='race_id', how='left')
                     self.combined_data = pd.merge(merged_data, self.horse_data, on='horse_id', how='left')
                     self.combined_data['race_date'] = pd.to_datetime(self.combined_data['race_date'])
                     print("サンプルデータ結合完了:", self.combined_data.shape)
                else:
                    self.combined_data = None

                # UI更新
                self.root.after(0, self.update_data_preview)
                self.root.after(0, lambda: self.update_status("サンプルデータの読み込み完了"))
                self.root.after(0, lambda: messagebox.showinfo("サンプルデータ", f"サンプルデータを使用します。\n結合データ: {self.combined_data.shape if self.combined_data is not None else 'N/A'}"))


        except FileNotFoundError: # これは os.path.exists でチェックしてるので通常発生しないはず
            self.root.after(0, lambda: messagebox.showerror("ファイルエラー", f"ファイルが見つかりません:\n{file_path}"))
            self.root.after(0, lambda: self.update_status("エラー: ファイルが見つかりません"))
        except pd.errors.ParserError:
             self.root.after(0, lambda: messagebox.showerror("CSVパースエラー", f"CSVファイルの形式が正しくない可能性があります。\n{file_path}"))
             self.root.after(0, lambda: self.update_status("エラー: CSVパースエラー"))
        except Exception as e:
            import traceback
            traceback.print_exc() # 詳細なエラーをコンソールに出力
            self.root.after(0, lambda: messagebox.showerror("読み込みエラー", f"データの読み込み中にエラーが発生しました:\n{e}"))
            self.root.after(0, lambda: self.update_status(f"エラー: {e}"))
            # エラー発生時はデータをクリア
            self.race_data = None
            self.horse_data = None
            self.result_data = None
            self.combined_data = None
            self.root.after(0, self.update_data_preview)


    def _fetch_web_data(self, source, from_date, to_date):
        """Webからのデータ取得（別スレッドで実行）- 未実装"""
        # !!! 重要 !!!
        # この関数は未実装です。netkeiba等のサイトからデータを取得する場合、
        # WebスクレイピングやAPI利用のロジックをここに実装します。
        # サイトの利用規約を遵守し、適切なアクセス間隔を設定してください。
        import time
        print(f"Webデータ取得開始: {source} ({from_date} - {to_date})")
        time.sleep(3) # 処理シミュレーション

        # --- ここにスクレイピング等の処理 ---
        # 取得したデータを self.race_data, self.horse_data, self.result_data に格納
        # self.generate_sample_data() # サンプルデータで代用

        # --- データ結合と前処理 ---
        # _load_local_csvと同様の処理

        print("Webデータ取得完了（シミュレーション）")
        self.root.after(0, self.update_data_preview)
        self.root.after(0, lambda: self.update_status(f"{source}からのデータ取得完了"))
        self.root.after(0, lambda: messagebox.showinfo("取得完了", f"{source}からのデータ取得が完了しました。（シミュレーション）"))


    def update_data_preview(self):
        """データプレビューテーブルの更新"""
        data_type = self.data_type_var.get()
        df = None

        if data_type == "combined":
            df = self.combined_data
            if df is None: self.update_status("プレビュー: 結合データがありません")
        elif data_type == "race":
            df = self.race_data
            if df is None: self.update_status("プレビュー: レースデータがありません")
        elif data_type == "horse":
            df = self.horse_data
            if df is None: self.update_status("プレビュー: 馬データがありません")
        elif data_type == "result":
            df = self.result_data
            if df is None: self.update_status("プレビュー: 結果データがありません")

        # テーブルをクリア
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)
        self.preview_tree["columns"] = [] # 列情報もクリア

        if df is not None and not df.empty:
            # 列の設定
            columns = list(df.columns)
            self.preview_tree["columns"] = columns
            self.preview_tree["show"] = "headings"

            for col in columns:
                col_width = max(len(col) * 10, 80) # 列名の長さに基づいて幅を決定（最小80px）
                self.preview_tree.heading(col, text=col)
                self.preview_tree.column(col, width=col_width, anchor=tk.W)

            # データの追加 (表示件数を制限)
            max_rows = 100
            df_head = df.head(max_rows)
            for i, row in df_head.iterrows():
                # NaNやNoneを空文字列に変換して表示
                values = ["" if pd.isna(val) else val for val in row.values]
                self.preview_tree.insert("", "end", values=values)

            self.update_status(f"プレビュー: {data_type} データを {min(len(df), max_rows)}/{len(df)} 行表示中")
        else:
             self.update_status(f"プレビュー: 表示する {data_type} データがありません")


    def save_data(self):
        """表示中のデータをCSVファイルに保存"""
        data_type = self.data_type_var.get()
        df_to_save = None
        default_filename = "data.csv"

        if data_type == "combined" and self.combined_data is not None:
            df_to_save = self.combined_data
            default_filename = "combined_data.csv"
        elif data_type == "race" and self.race_data is not None:
            df_to_save = self.race_data
            default_filename = "race_data.csv"
        elif data_type == "horse" and self.horse_data is not None:
            df_to_save = self.horse_data
            default_filename = "horse_data.csv"
        elif data_type == "result" and self.result_data is not None:
            df_to_save = self.result_data
            default_filename = "result_data.csv"

        if df_to_save is not None and not df_to_save.empty:
            save_dir = self.settings.get("data_dir", ".")
            file_path = filedialog.asksaveasfilename(
                title=f"{data_type}データを保存",
                initialdir=save_dir,
                initialfile=default_filename,
                defaultextension=".csv",
                filetypes=[("CSVファイル", "*.csv"), ("すべてのファイル", "*.*")]
            )
            if file_path:
                try:
                    df_to_save.to_csv(file_path, index=False, encoding='utf-8-sig') # BOM付きUTF-8で保存
                    self.update_status(f"{data_type}データを保存しました: {file_path}")
                    messagebox.showinfo("データ保存", f"{data_type}データを保存しました。")
                except Exception as e:
                    messagebox.showerror("保存エラー", f"データの保存中にエラーが発生しました:\n{e}")
                    self.update_status(f"エラー: {data_type}データの保存失敗")
        else:
            messagebox.showwarning("データ保存", f"保存する{data_type}データがありません。")
            self.update_status(f"警告: 保存する{data_type}データなし")


    # --- Data Analysis ---
    
    def run_analysis(self):
        """分析実行処理（血統分析の前処理を追加）"""
        if self.combined_data is None or self.combined_data.empty:
             messagebox.showwarning("分析実行", "分析対象のデータが読み込まれていません。\nデータ管理タブでデータを読み込んでください。")
             return

        analysis_type = self.analysis_type_var.get()
        filters = {
            "track": self.track_var.get(),
            "course": self.course_var.get(),
            "min_dist": self.min_distance_var.get(),
            "max_dist": self.max_distance_var.get(),
        }

        # === ★★★ 血統分析の場合、父情報の前処理を行う ★★★ ===
        if analysis_type == "血統分析":
            # combined_data に 'father' 列が既にあるかチェック
            if 'father' not in self.combined_data.columns:
                messagebox.showinfo("血統情報準備", "血統分析のために、各馬の父情報を取得します。\nデータ量によっては時間がかかる場合があります。")
                self.update_status("血統情報の取得・マージ中...")
                # ★★★ 父情報取得・マージ処理を別スレッドで実行 ★★★
                # 処理完了後に _run_analysis_thread を呼び出すようにする
                self.run_in_thread(self._prepare_father_data_and_analyze, analysis_type, filters)
                return # 前処理スレッドに任せて、ここでは一旦終了
            else:
                print("情報: 既に父情報が存在するため、前処理をスキップします。")
                # 既に父情報があれば、通常通り分析スレッドを開始
                self.update_status(f"{analysis_type}の分析実行中...")
                self.run_in_thread(self._run_analysis_thread, analysis_type, filters)
        else:
            # 血統分析以外は、通常通り分析スレッドを開始
            self.update_status(f"{analysis_type}の分析実行中...")
            self.run_in_thread(self._run_analysis_thread, analysis_type, filters)
 
    def _run_analysis_thread(self, analysis_type, filters):
        """分析の非同期処理（人気別、距離別、コース種別、血統分析を追加）"""
        import time
        import pandas as pd # type: ignore
        import numpy as np # type: ignore
        # import matplotlib.pyplot as plt # テーブル表示のみなら不要かも
        import traceback

        try:
            start_time = _time.time()
            # print(f"\n--- Starting Analysis Thread ---")
            # print(f"DEBUG: Analysis type selected from GUI: '{self.analysis_type_var.get()}'...")
            analysis_type = self.analysis_type_var.get()
            self.root.after(0, lambda: self.update_status(f"{analysis_type} の分析実行中..."))

            if self.combined_data is None or self.combined_data.empty:
                # ... (データなし処理) ...
                return

            # --- フィルター適用 ---
            filtered_df = self.combined_data.copy()
            filter_text_parts = []
            # ... (フィルター処理: 競馬場, コース, 距離 - 変更なし) ...
            if filters["track"] != "すべて":
                if 'track_name' in filtered_df.columns:
                    filtered_df = filtered_df[filtered_df['track_name'] == filters["track"]]
                    filter_text_parts.append(f"競馬場={filters['track']}")
                else: print("警告: データに競馬場名列がありません。")
            selected_course = filters["course"] 
            if filters["course"] != "すべて":
                if 'course_type' in filtered_df.columns:
                    target_value = filters["course"]
                    if selected_course == 'ダート': target_value = 'ダ' #比較対象を変更
                    elif selected_course == '芝': target_value = '芝'
                    elif selected_course == '障害': target_value = '障'
                    filtered_df = filtered_df[filtered_df['course_type'].astype(str).str.strip() == target_value]
                    filter_text_parts.append(f"コース={filters['course']}")
                else: print("警告: データに 'course_type' 列がありません。")
            try: # 距離フィルター
                min_dist_str = filters["min_dist"]; max_dist_str = filters["max_dist"]
                apply_dist_filter = False; min_dist = 0; max_dist = float('inf')
                if min_dist_str != "すべて": min_dist = int(min_dist_str); apply_dist_filter = True
                if max_dist_str != "すべて": max_dist = int(max_dist_str); apply_dist_filter = True
                if apply_dist_filter and 'distance' in filtered_df.columns:
                    distance_col_numeric = pd.to_numeric(filtered_df['distance'], errors='coerce')
                    distance_filter = (distance_col_numeric >= min_dist) & (distance_col_numeric <= max_dist)
                    filtered_df = filtered_df[distance_filter.fillna(False)]
                    filter_text_parts.append(f"距離={min_dist_str}～{max_dist_str}m")
                elif apply_dist_filter: print("警告: データに 'distance' 列がありません。")
            except ValueError: messagebox.showwarning(...); self.update_status(...); return
            except Exception as e_dist_filter: print(f"ERROR: Error during distance filtering: {e_dist_filter}"); traceback.print_exc()

            # print(f"DEBUG: Final filtered_df shape before analysis: {filtered_df.shape}")

            if filtered_df.empty:
                 # ... (フィルター結果が空の場合の処理) ...
                 return

            # --- 分析タイプに応じた処理 ---
            analysis_result_df = pd.DataFrame()
            table_title = "分析結果"
            filter_str = f" ({', '.join(filter_text_parts)})" if filter_text_parts else ""

            if analysis_type == "人気別分析":
                # ... (人気別分析ロジック - 変更なし) ...
                print(f"  人気別分析: テーブル表示用データ\n{analysis_result_df}")
                table_title = f'人気別 成績{filter_str}'

            elif analysis_type == "距離別分析":
                # ... (距離別分析ロジック - 変更なし) ...
                print(f"  距離別分析: テーブル表示用データ\n{analysis_result_df}")
                table_title = f'距離別 成績{filter_str}'

            elif analysis_type == "コース種別分析":
                # ... (コース種別分析ロジック - 変更なし) ...
                print(f"  コース種別分析: テーブル表示用データ\n{analysis_result_df}")
                table_title = f'コース種別 成績{filter_str}'

            elif analysis_type == "騎手分析":
                # ... (騎手分析ロジック - 変更なし) ...
                print(f"  騎手分析: テーブル表示用データ (上位{len(analysis_result_df)}件)\n{analysis_result_df}")
                table_title = f'騎手別 成績 (騎乗10回以上){filter_str}'

            # === ★★★ 血統分析 (父別) の処理を追加 ★★★ ===
            elif analysis_type == "血統分析":
                required_cols = ['father', 'Rank'] # fatherとRank列が必要
                if not all(col in filtered_df.columns for col in required_cols):
                     missing_cols = [col for col in required_cols if col not in filtered_df.columns]
                     # 父情報がない場合は前処理を促すメッセージ
                     if 'father' in missing_cols:
                          messagebox.showerror("データエラー", "血統分析には父情報が必要です。\nデータ管理タブでデータを再取得するか、血統分析を再度実行して父情報を準備してください。")
                     else:
                          messagebox.showerror("データエラー", f"分析に必要な列({', '.join(missing_cols)})がデータに含まれていません。")
                     self.root.after(0, lambda: self.update_status("エラー: データ形式不正"))
                     return

                print(f"  血統分析 (父別){filter_str}: {len(filtered_df)} 行のデータで集計開始...")
                df_analysis = filtered_df.copy()
                # Rankを数値に変換、父がNaNや空の行を除外
                df_analysis['Rank'] = pd.to_numeric(df_analysis['Rank'], errors='coerce')
                df_analysis.dropna(subset=['father', 'Rank'], inplace=True)
                df_analysis = df_analysis[df_analysis['father'] != ''] # 空の父名を除外
                df_analysis['Rank'] = df_analysis['Rank'].astype(int)

                if df_analysis.empty:
                     self.root.after(0, lambda: messagebox.showinfo("分析結果", "フィルター条件に該当する有効な父・着順データがありません。")); self.root.after(0, lambda: self.update_status("分析完了: 対象データなし")); self.root.after(0, lambda: self._update_analysis_table(pd.DataFrame(), f"血統分析 (父別) (データなし){filter_str}")); return

                # 父でグループ化して集計
                analysis_result = df_analysis.groupby('father').agg(
                    Runs=('father', 'size'), Wins=('Rank', lambda x: (x == 1).sum()),
                    Place2=('Rank', lambda x: (x <= 2).sum()), Place3=('Rank', lambda x: (x <= 3).sum()),
                    Rank4over=('Rank', lambda x: (x >= 4).sum())
                )
                # 出走回数が少ない種牡馬を除外 (例: 10回以上)
                min_runs = 10
                analysis_result = analysis_result[analysis_result['Runs'] >= min_runs]

                if not analysis_result.empty:
                    analysis_result['成績'] = analysis_result.apply( lambda r: f"{int(r['Wins'])}-{int(r['Place2'] - r['Wins'])}-{int(r['Place3'] - r['Place2'])}-{int(r['Rank4over'])}", axis=1)
                    analysis_result['WinRate'] = analysis_result.apply(lambda r: r['Wins'] / r['Runs'] if r['Runs'] > 0 else 0, axis=1)
                    analysis_result['Place2Rate'] = analysis_result.apply(lambda r: r['Place2'] / r['Runs'] if r['Runs'] > 0 else 0, axis=1)
                    analysis_result['Place3Rate'] = analysis_result.apply(lambda r: r['Place3'] / r['Runs'] if r['Runs'] > 0 else 0, axis=1)
                    # 複勝率でソートし、上位 N 件を表示 (例: 上位30件)
                    analysis_result = analysis_result.sort_values('Place3Rate', ascending=False)
                    analysis_result_df = analysis_result[['成績', 'WinRate', 'Place2Rate', 'Place3Rate', 'Runs']].head(30).reset_index() # 父の名前も列に含める
                    print(f"  血統分析 (父別): テーブル表示用データ (上位{len(analysis_result_df)}件)\n{analysis_result_df}")
                else:
                     print(f"  血統分析 (父別): 出走回数{min_runs}回以上の種牡馬データがありません。")
                     analysis_result_df = pd.DataFrame()

                table_title = f'血統分析 (父別) (出走{min_runs}回以上){filter_str}'
            # === ★★★ 血統分析ここまで ★★★ ===

            # === 他の未実装分析タイプ ===
            else:
                 print(f"DEBUG: Analysis type '{analysis_type}' is not implemented or does not match.")
                 self.root.after(0, lambda: self._update_analysis_table(pd.DataFrame(), f"{analysis_type} (未実装)"))

            # --- 結果表示 (テーブル表示) ---
            # ★ analysis_type をチェックする条件に 血統分析 を追加 ★
            if analysis_type in ["人気別分析", "距離別分析", "コース種別分析", "騎手分析", "血統分析"]:
                 if not analysis_result_df.empty:
                     self.root.after(0, self._update_analysis_table, analysis_result_df, table_title)
                 # ★ analysis_type をチェックする条件に 血統分析 を追加 ★
                 elif analysis_type in ["人気別分析", "距離別分析", "コース種別分析", "騎手分析", "血統分析"]: # 集計結果が空だった場合
                     self.root.after(0, lambda: self._update_analysis_table(pd.DataFrame(), f"{analysis_type} (データなし){filter_str}"))
            # else: # 未実装の場合は上の else ブロックでテーブルクリア済み

            # --- ステータス更新 ---
            end_time = time.time()
            # print(f"  分析処理時間: {end_time - start_time:.2f} 秒")
            self.root.after(0, lambda: self.update_status(f"{analysis_type} の分析完了 ({end_time - start_time:.2f}秒)"))
            print(f"--- Analysis Thread for {analysis_type} finished ---")

        except Exception as e:
            print(f"!!! Error in _run_analysis_thread ({analysis_type}) !!!")
            self.root.after(0, lambda: messagebox.showerror("分析エラー", f"分析中にエラーが発生しました:\n{e}"))
            self.root.after(0, lambda: self.update_status(f"エラー: 分析失敗 ({e})"))
            self.root.after(0, lambda: self._update_analysis_table(pd.DataFrame(), "分析エラー"))
            traceback.print_exc()

    def _prepare_father_data_and_analyze(self, analysis_type, filters):
        """馬の父情報を取得・マージし、CSVに保存し、統計計算してから分析スレッドを開始する"""
        try:
            # ... (データチェック、父情報取得ループ、マージ処理 - 変更なし) ...
            # if self.combined_data is None or self.combined_data.empty: print("エラー: ..."); return
            # if 'horse_id' not in self.combined_data.columns: print("エラー: ..."); return
            # unique_horse_ids = self.combined_data['horse_id'].dropna().unique(); father_data = {}; num_total = len(unique_horse_ids)
            # print(f"父情報が必要な馬: {num_total} 頭")
            # for i, horse_id in enumerate(unique_horse_ids):
                # self.update_status(f"父情報取得中... ({i+1}/{num_total})")
                # details = self.get_horse_details(str(horse_id))
                # father_data[horse_id] = details.get('father')
                # time.sleep(0.05)
            # father_df = pd.DataFrame(father_data.items(), columns=['horse_id', 'father'])
            # self.combined_data['horse_id'] = self.combined_data['horse_id'].astype(str)
            # father_df['horse_id'] = father_df['horse_id'].astype(str)
            # print(f"DEBUG: Merging combined_data ...")
            # if 'father' in self.combined_data.columns: self.combined_data = self.combined_data.drop(columns=['father'])
            # self.combined_data = pd.merge(self.combined_data, father_df, on='horse_id', how='left')
            # print(f"DEBUG: combined_data shape after merge: {self.combined_data.shape}")
            # print(f"DEBUG: Count of non-null fathers after merge: {self.combined_data['father'].notna().sum()}")

            # --- 父情報をマージしたデータをCSVに上書き保存 ---
            # current_csv_path = self.file_path_var.get()
            # if current_csv_path and os.path.exists(os.path.dirname(current_csv_path)):
                # try:
                    # print(f"父情報を追加したデータをCSVに保存します: {current_csv_path}")
                    # self.update_status("父情報をCSVに保存中...")
                    # self.combined_data.to_csv(current_csv_path, index=False, encoding='utf-8-sig')
                    # print("CSVファイルの保存が完了しました。")
                    # self.root.after(0, lambda: messagebox.showinfo("情報", "血統情報をCSVファイルに保存しました。..."))
                # except Exception as e_save: print(f"ERROR: Failed to save combined_data ...: {e_save}"); messagebox.showerror(...)
            # else: print("警告: 現在のCSVファイルパスが無効なため、父情報はCSVに保存されませんでした。")

            # --- ★★★ 種牡馬(父)統計データの計算を実行 ★★★ ---
            if self.combined_data is not None and not self.combined_data.empty and 'father' in self.combined_data.columns:
                 self._calculate_sire_stats(sire_column='father') # ←★ ここで呼び出す！
            # --- ★★★ 計算実行ここまで ★★★ ---

            # 分析スレッドを実行
            self.update_status(f"{analysis_type}の分析実行中...")
            self.run_in_thread(self._run_analysis_thread, analysis_type, filters)

        except Exception as e:
            print(f"!!! Error in _prepare_father_data_and_analyze !!!")
            self.root.after(0, lambda: messagebox.showerror("前処理エラー", f"血統情報の準備中にエラーが発生しました:\n{e}"))
            self.root.after(0, lambda: self.update_status(f"エラー: 血統情報準備失敗 ({e})"))
            traceback.print_exc()

    def _update_analysis_table(self, result_df, title="分析結果"):
        """データ分析タブのテーブルを更新"""
        # ... (テーブルクリア、タイトル更新、データなしチェックは変更なし) ...

        columns = list(result_df.columns)
        self.analysis_tree["columns"] = columns
        self.analysis_tree["show"] = "headings"

        for col in columns:
            width = 100; anchor = tk.W; col_name = col

            # === 列ごとの表示設定 ===
            if col == 'NinkiGroup':         width = 100; anchor = tk.W; col_name = '人気'
            elif col == 'DistanceGroup':    width = 100; anchor = tk.W; col_name = '距離区分'
            elif col == 'course_type':      width = 80; anchor = tk.W; col_name = 'コース種別' # ★コース種別追加
            elif col == '成績':            width = 100; anchor = tk.CENTER; col_name = '成績'
            elif col == 'WinRate':         width = 80; anchor = tk.E; col_name = '勝率'
            elif col == 'Place2Rate':       width = 80; anchor = tk.E; col_name = '連対率'
            elif col == 'Place3Rate':       width = 80; anchor = tk.E; col_name = '複勝率'
            elif col == 'Runs':            width = 60; anchor = tk.E; col_name = 'N数'
            # 他の列の表示設定が必要ならここに追加

            self.analysis_tree.heading(col, text=col_name)
            self.analysis_tree.column(col, width=width, anchor=anchor)

        # === データ追加 (変更なし) ===
        for index, row in result_df.iterrows():
            display_values = []
            for col in columns:
                value = row[col]
                if 'Rate' in col: # 率をパーセント表示
                    try: value = f"{float(value):.1%}"
                    except (ValueError, TypeError): value = "N/A"
                elif col == 'Runs': # N数を整数表示
                     try: value = int(value)
                     except (ValueError, TypeError): value = "N/A"
                # 他の列はそのまま
                display_values.append(value if pd.notna(value) else "")
            self.analysis_tree.insert("", "end", values=display_values)

        print("分析結果テーブルを更新しました。")

    
    # --- Prediction ---
    def fetch_race_info_for_prediction(self):
        """予測タブでレースIDに基づいてレース情報を表示"""
        race_id = self.predict_race_id_var.get()
        if not race_id:
            messagebox.showwarning("レースID未入力", "予測対象のレースIDを入力してください。")
            return

        if self.combined_data is None or self.combined_data.empty:
            messagebox.showwarning("データ未読み込み", "データが読み込まれていません。\nデータ管理タブでデータを読み込んでください。")
            return

        self.update_status(f"レース情報検索中: {race_id}")
        self.run_in_thread(self._fetch_race_info_thread, race_id)
    
    def _fetch_race_info_thread(self, race_id):
        """レース情報の取得と表示、学習済みモデルでの予測確率計算"""
        # --- 必要なライブラリをインポート ---
        # (ファイル冒頭でインポート済みなら不要だが、念のため)
        import time
        import pandas as pd # type: ignore # type: ignore
        import numpy as np # type: ignore
        import traceback
        import re
        from tkinter import messagebox
        import tkinter as tk # tk を使うため (必要に応じて)
        # --- ここまでインポート ---

        try:
            # ★★★ 1. 学習済みモデルの存在チェック ★★★
            if not hasattr(self, 'trained_model') or self.trained_model is None:
                 # UI操作はメインスレッドで行う
                 self.root.after(0, lambda: messagebox.showwarning("モデル未学習", "学習済みモデルが読み込まれていません。\nデータ管理タブでモデルを学習させてください。"))
                 self.root.after(0, lambda: self.update_status("エラー: 学習済みモデルなし"))
                 return # モデルがないと予測できないので中断
            print("INFO: Trained model found. Proceeding with prediction calculation.")
            # ★★★★★★★★★★★★★★★★★★★★★★★★

            # --- データ準備: self.combined_data チェック ---
            if self.combined_data is None or self.combined_data.empty:
                 self.root.after(0, lambda: messagebox.showwarning("データ未読み込み", "データが読み込まれていません。\nデータ管理タブでデータを読み込んでください。"))
                 self.root.after(0, lambda: self.update_status("準備完了"))
                 return
            if 'race_id' not in self.combined_data.columns:
                 self.root.after(0, lambda: messagebox.showerror("データエラー", "結合データに 'race_id' 列が見つかりません。"))
                 self.root.after(0, lambda: self.update_status("エラー: データ形式不正"))
                 return
            # --- ここまでデータ準備 ---

            # --- race_df の作成 ---
            race_df = pd.DataFrame() # 初期化
            try:
                # race_id の型を文字列に統一してから比較 (元のデータを変更しないように修正)
                combined_data_race_id_str = self.combined_data['race_id'].astype(str)
                race_df = self.combined_data[combined_data_race_id_str == str(race_id)].copy()
            except KeyError:
                 self.root.after(0, lambda: messagebox.showerror("データエラー", f"レースID '{race_id}' の検索または列アクセス中にエラーが発生しました。"))
                 self.root.after(0, lambda: self.update_status(f"エラー: レースID検索失敗"))
                 return
            except Exception as e_filter:
                 self.root.after(0, lambda err=e_filter: messagebox.showerror("データエラー", f"レースデータ抽出中に予期せぬエラー:\n{err}"))
                 self.root.after(0, lambda: self.update_status(f"エラー: レースデータ抽出失敗"))
                 traceback.print_exc()
                 return
            # --- ここまで race_df 作成 ---

            # --- デバッグプリント (必要ならコメント解除) ---
            # print(f"\n--- Debug _fetch_race_info_thread (Start at top) ---")
            # print(f"Columns in self.combined_data (at start): {self.combined_data.columns.tolist()}")
            # print(f"--- Debug self.combined_data Check End ---")
            # print(f"\n--- Debug race_df Check ---")
            # print(f"Shape of race_df for race_id {race_id}: {race_df.shape}")
            # if not race_df.empty: print(f"Columns in race_df: {race_df.columns.tolist()}")
            # else: print("WARN: race_df is empty.")
            # print(f"--- Debug race_df Check End ---")
            # --- ここまでデバッグプリント ---

            if race_df.empty:
                 self.root.after(0, lambda: messagebox.showerror("レース情報エラー", f"指定されたレースID ({race_id}) の情報が見つかりません。"))
                 self.root.after(0, lambda: self.update_status(f"エラー: レースID {race_id} が見つかりません"))
                 return

            # --- レース基本情報を取得 ---
            race_info_row = race_df.iloc[0]
            race_date_dt = None; race_date_str = 'N/A'
            try:
                race_date_val = race_info_row.get('date')
                if pd.notna(race_date_val):
                     if isinstance(race_date_val, pd.Timestamp): race_date_dt = race_date_val
                     else: race_date_dt = pd.to_datetime(race_date_val)
                     race_date_str = race_date_dt.strftime('%Y年%m月%d日')
            except Exception as e_date: race_date_str = str(race_info_row.get('date', 'N/A'))
            track_name = str(race_info_row.get('track_name', 'N/A'))
            race_num_val = race_info_row.get('race_num'); race_num = int(race_num_val) if pd.notna(race_num_val) else '?'
            race_name = str(race_info_row.get('race_name', 'N/A'))
            course_type = str(race_info_row.get('course_type', ''))
            distance_val = race_info_row.get('distance'); distance = int(distance_val) if pd.notna(distance_val) else ''
            turn_detail = str(race_info_row.get('turn_detail', ''))
            weather = str(race_info_row.get('weather', 'N/A'))
            condition = str(race_info_row.get('track_condition', 'N/A'))
            race_info_text = f"{race_date_str} {track_name}{race_num}R {race_name}"
            race_details_text = f"{course_type}{turn_detail}{distance}m / 天候:{weather} / 馬場:{condition}"
            race_conditions = {
                 'course_type': course_type, 'distance': distance if isinstance(distance, int) else None,
                 'track_name': track_name, 'baba': condition
            }
            print(f"DEBUG: Race conditions for index calculation: {race_conditions}")
            # --- ここまでレース基本情報 ---

            # --- 出走馬情報をリスト化 & 詳細情報取得 & 特徴量計算 & 予測確率計算 ---
            horse_details_list = []
            num_horses = len(race_df)
            self.root.after(0, lambda status=f"{race_id}: 出走馬 {num_horses} 頭の予測確率を計算中...": self.update_status(status))

            # ★★★ 特徴量名のリスト (学習時と合わせる必要あり！) ★★★
            feature_cols_for_predict = [
                 'Age', '斤量絶対値', '斤量前走差', '負担率', '馬体重絶対値', '馬体重前走差', '枠番',
                 '同条件出走数', '同条件複勝率', '枠番_複勝率', '枠番_N数',
                 'タイム偏差値', '基準タイム差', '基準タイム比', '同コース距離最速補正',
                 '父同条件複勝率', '父同条件N数', '母父同条件複勝率', '母父同条件N数',
                 '近走1走前着順', '着差_1走前', '上がり3F_1走前',
                 '近走2走前着順', '着差_2走前', '上がり3F_2走前',
                 '近走3走前着順', '着差_3走前', '上がり3F_3走前'
             ]
            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

            for index, row in race_df.iterrows():
                 # --- 基本情報取得と整形 ---
                 umaban = row.get('Umaban')
                 horse_id = row.get('horse_id')
                 horse_name = row.get('HorseName', 'N/A')
                 sex_age_raw = row.get('SexAge')
                 load_val = row.get('Load')
                 jockey_name = row.get('JockeyName', 'N/A')
                 odds_val = row.get('Odds')
                 father_val = row.get('father', 'N/A')
                 mother_father_val = row.get('mother_father', 'N/A')
                 weight_val = row.get('Weight')
                 weight_diff_val = row.get('WeightDiff')
                 waku_val = row.get('枠番') # 正しいキー名
                 sex_age = sex_age_raw
                 if pd.isna(sex_age):
                      sex_val = row.get('Sex'); age_val = row.get('Age')
                      if pd.notna(sex_val) and pd.notna(age_val):
                           try: sex_age = f"{sex_val}{int(age_val)}"
                           except: sex_age = f"{sex_val or '?'}?歳"
                 sex_age = str(sex_age) if pd.notna(sex_age) else 'N/A'

                 horse_basic_info = {
                     "Umaban": umaban, "HorseName": horse_name, "SexAge": sex_age, "Load": load_val,
                     "JockeyName": jockey_name, "Odds": odds_val, "horse_id": horse_id,
                     "father": father_val, "mother_father": mother_father_val,
                     "Weight": weight_val, "WeightDiff": weight_diff_val, "枠番": waku_val, # キーを '枠番' に統一
                     "race_results": [], "近3走": "N/A", "予測確率": None, "error_detail": None # 指数 -> 予測確率
                 }
                 # --- ここまで基本情報 ---

                 predicted_proba = None
                 features = {}
                 error_detail = None

                 if horse_id and pd.notna(horse_id):
                     # --- 詳細情報取得 (キャッシュ利用) ---
                     horse_id_str = str(int(horse_id)) if isinstance(horse_id, (int, float, np.number)) else str(horse_id)
                     details_from_cache = self.horse_details_cache.get(horse_id_str)
                     if details_from_cache and 'race_results' in details_from_cache:
                         horse_basic_info['race_results'] = details_from_cache['race_results']
                         horse_basic_info['father'] = details_from_cache.get('father', horse_basic_info['father'])
                         horse_basic_info['mother_father'] = details_from_cache.get('mother_father', horse_basic_info['mother_father'])
                         # error_detail は calculate_original_index が返すものを優先するので、ここでは上書きしない
                         # horse_basic_info['error_detail'] = details_from_cache.get('error')
                     else: horse_basic_info['race_results'] = []
                     # --- ここまで詳細情報取得 ---

                     # --- 特徴量計算 ---
                     _, features = self.calculate_original_index(horse_basic_info, race_conditions) # 指数0.0は無視
                     # --- ここまで特徴量計算 ---

                     # ★★★ 予測確率の計算を追加 ★★★
                     if features.get('error') is None:
                         try:
                             # 1. 特徴量辞書から学習に使った特徴量を選択し、DataFrameに変換 (1行分)
                             feature_values = []
                             missing_feature_keys = [] # デバッグ用: 不足しているキーを記録
                             for col in feature_cols_for_predict:
                                 if col in features:
                                     feature_values.append(features.get(col))
                                 else:
                                     feature_values.append(None) # features辞書にキーがない場合はNone
                                     missing_feature_keys.append(col)
                             if missing_feature_keys:
                                  print(f"WARN: Keys missing in features dict for prediction (Umaban {umaban}): {missing_feature_keys}")


                             X_pred = pd.DataFrame([feature_values], columns=feature_cols_for_predict)

                             # 2. 欠損値処理 (暫定: 0で埋める)
                             missing_count = X_pred.isnull().sum().sum()
                             if missing_count > 0:
                                 # print(f"WARN: Filling {missing_count} NaN values with 0 for prediction (Umaban: {umaban}).")
                                 X_pred.fillna(0, inplace=True)

                             # 3. モデルで予測確率を計算
                             if hasattr(self, 'trained_model') and self.trained_model: # モデルが存在するか再確認
                                proba_result = self.trained_model.predict_proba(X_pred)
                                predicted_proba = proba_result[0, 1] # クラス1 (3着以内) の確率
                                # print(f"      予測確率計算完了: 馬番 {umaban} = {predicted_proba:.4f}")
                             else:
                                 print("ERROR: Trained model is not available for prediction.")
                                 predicted_proba = None

                         except Exception as e_pred_calc:
                             print(f"!!! ERROR during probability prediction for Umaban {umaban}: {e_pred_calc}")
                             traceback.print_exc()
                             error_detail = f"予測確率計算エラー: {type(e_pred_calc).__name__}"
                             predicted_proba = None
                     else:
                          error_detail = features.get('error')
                          predicted_proba = None
                     # ★★★★★★★★★★★★★★★★★★

                 else: # horse_id が None または NaN の場合
                     error_detail = 'horse_id not found or NaN in race_df'
                     print(f"   警告: 馬番 {umaban} の horse_id が見つかりません。(Value: {horse_id})")
                     predicted_proba = None

                 # --- 最終的な情報を horse_basic_info に格納 ---
                 # 近3走文字列作成
                 recent_results_str = "N/A"
                 # 'race_results' キーが basic_info に存在するか確認
                 rr_list = horse_basic_info.get('race_results', [])
                 if isinstance(rr_list, list) and rr_list:
                     recent_3 = []
                     for res in rr_list[:3]:
                         rank = res.get('rank'); rank_str = res.get('rank_str', '?')
                         try: rank_display = int(float(rank))
                         except: rank_display = rank_str if rank_str else '?'
                         recent_3.append(str(rank_display))
                     recent_results_str = "/".join(recent_3)
                 elif '近走1走前着順' in features: # features から取得する場合
                     r1 = features.get('近走1走前着順'); r2 = features.get('近走2走前着順'); r3 = features.get('近走3走前着順')
                     recent_3_f = [str(r) if pd.notna(r) and r != 99 else ('中' if r == 99 else '?') for r in [r1,r2,r3]]
                     recent_results_str = "/".join(recent_3_f)

                 horse_basic_info['近3走'] = recent_results_str
                 horse_basic_info['予測確率'] = round(predicted_proba, 4) if pd.notna(predicted_proba) else None # ★ 指数 -> 予測確率
                 horse_basic_info['error_detail'] = error_detail

                 horse_details_list.append(horse_basic_info)
            # --- ループ終了 ---

            # --- ソート (予測確率で降順ソート) ---
            try:
                 def get_sort_key(x):
                      p = x.get("予測確率"); return -float(p) if pd.notna(p) else float('inf') # 確率高い順、Noneは最後
                 horse_details_list.sort(key=get_sort_key)
            except Exception as sort_e: print(f"警告: 予測確率でのソート中にエラー: {sort_e}")
            # --- ここまでソート ---

            # --- UI 更新 ---
            # print(f"DEBUG: Passing {len(horse_details_list)} horses with prediction probabilities to _update_prediction_table")
            self.root.after(0, lambda text=f"レース情報: {race_info_text}": self.race_info_label.config(text=text))
            self.root.after(0, lambda text=race_details_text: self.race_details_label.config(text=text))
            self.root.after(0, lambda details=list(horse_details_list): self._update_prediction_table(details)) # ★ 予測確率を含むリストを渡す
            self.root.after(0, lambda status=f"予測確率 計算完了: {race_id}": self.update_status(status))
            if hasattr(self, 'recommendation_text') and self.recommendation_text:
                 if self.recommendation_text.winfo_exists():
                     try: self.root.after(0, lambda: self.recommendation_text.delete(1.0, tk.END))
                     except tk.TclError: pass
            # --- ここまで UI 更新 ---

        except Exception as e:
            # メソッド全体の予期せぬエラー
            print("!!! ERROR in _fetch_race_info_thread !!!")
            traceback.print_exc()
            self.root.after(0, lambda err=e: messagebox.showerror("レース情報エラー", f"レース情報の取得・表示中に予期せぬエラーが発生しました:\n{type(err).__name__}: {err}"))
            self.root.after(0, lambda err=e: self.update_status(f"エラー: レース情報処理失敗 ({type(err).__name__})"))
 
    def _update_prediction_table(self, horses_info):
        """予測タブの出走馬テーブルを更新 (血統・近走・予測確率表示)"""
        # テーブルクリア
        for item in self.prediction_tree.get_children():
            self.prediction_tree.delete(item)

        if not horses_info:
            print("表示する出走馬情報がありません。")
            # columns が設定されていないとエラーになる場合があるので空リストを設定
            self.prediction_tree["columns"] = []
            self.prediction_tree["displaycolumns"] = []
            return

        # === 列定義 (キー名は英語で統一) ===
        columns = ["Umaban", "HorseName", "SexAge", "Load", "JockeyName", "Odds", "father", "mother_father", "近3走", "予測確率"]
        self.prediction_tree["columns"] = columns
        # 表示する列も指定 (もし列定義と異なる場合) - 今回は同じなので不要かも
        # self.prediction_tree["displaycolumns"] = columns
        self.prediction_tree["show"] = "headings"

        # === 列幅とヘッダー設定 (★識別子を英語に、textは日本語に) ===
        self.prediction_tree.column("Umaban", width=40, anchor=tk.CENTER)
        self.prediction_tree.heading("Umaban", text="馬番") # ヘッダー表示は日本語
        self.prediction_tree.column("HorseName", width=120, anchor=tk.W)
        self.prediction_tree.heading("HorseName", text="馬名")
        self.prediction_tree.column("SexAge", width=50, anchor=tk.CENTER)
        self.prediction_tree.heading("SexAge", text="性齢")
        self.prediction_tree.column("Load", width=50, anchor=tk.E)
        self.prediction_tree.heading("Load", text="斤量")
        self.prediction_tree.column("JockeyName", width=80, anchor=tk.W)
        self.prediction_tree.heading("JockeyName", text="騎手")
        self.prediction_tree.column("Odds", width=70, anchor=tk.E)
        self.prediction_tree.heading("Odds", text="単勝オッズ")
        # ↓↓↓ 識別子を英語 'father' に修正 ↓↓↓
        self.prediction_tree.column("father", width=130, anchor=tk.W)
        self.prediction_tree.heading("father", text="父") # ヘッダー表示は「父」
        # ↓↓↓ 識別子を英語 'mother_father' に修正 ↓↓↓
        self.prediction_tree.column("mother_father", width=130, anchor=tk.W)
        self.prediction_tree.heading("mother_father", text="母父") # ヘッダー表示は「母父」
        # ↑↑↑ 修正ここまで ↑↑↑
        self.prediction_tree.column("近3走", width=60, anchor=tk.CENTER)
        self.prediction_tree.heading("近3走", text="近3走")
        self.prediction_tree.column("予測確率", width=70, anchor=tk.E)
        self.prediction_tree.heading("予測確率", text="予測確率")
        # --- ここまで設定 ---

        # === データ追加 ===
        for horse in horses_info:
            # 表示する値を取得 (★ '指数' -> '予測確率' に変更)
            pred_proba = horse.get('予測確率') # ★ キー名変更
            display_values = [
                horse.get("Umaban", 'N/A'),
                horse.get("HorseName", 'N/A'),
                horse.get("SexAge", 'N/A'),
                horse.get("Load", 'N/A'),
                horse.get("JockeyName", 'N/A'),
                f"{horse.get('Odds'):.1f}" if isinstance(horse.get('Odds'), (int, float)) else horse.get('Odds', 'N/A'),
                horse.get("father", 'N/A'),       # ←★ キー名を 'father' に変更
                horse.get("mother_father", 'N/A'), # ←★ キー名を 'mother_father' に変更
                horse.get("近3走", 'N/A'),
                f"{pred_proba:.4f}" if pd.notna(pred_proba) else 'N/A' # 小数点4桁表示
            ]
            # None を 'N/A' に変換 (より安全な方法)
            # pandasの欠損値NaNも考慮に入れる
            display_values = [str(v) if pd.notna(v) else 'N/A' for v in display_values]

            item_id = horse.get("Umaban")
            # item_id が None または空文字列、あるいは既存の場合の処理を改善
            if item_id is None or str(item_id).strip() == '':
                # 馬番がない場合、一意なIDを生成 (例: インデックスや乱数を使う)
                # ここでは乱数を使う例 (ただし衝突の可能性はゼロではない)
                import random
                item_id = f"no_umaban_{random.randint(1000,9999)}"
            else:
                 item_id = str(item_id) # 文字列に変換

            try:
                 # 既に同じ iid が存在するかチェックしてから insert or update
                 if not self.prediction_tree.exists(item_id):
                      self.prediction_tree.insert("", "end", values=display_values, iid=item_id)
                 else:
                      # 既に存在する場合、値を更新する
                      self.prediction_tree.item(item_id, values=display_values)
                      # print(f"    WARN: Item with iid='{item_id}' already exists. Updating values.")

            except tk.TclError as e:
                 # iid重複以外のTclErrorの可能性
                 print(f"    ERROR: TclError during insert/update for iid='{item_id}': {e}")
            except Exception as e:
                 print(f"    ERROR: Unexpected error during insert/update for iid='{item_id}': {e}")

# ↓↓↓ この関数定義全体をクラス内に追加してください ↓↓↓
    def run_prediction(self):
        """予測実行処理"""
        # レース情報が表示されているか（出走馬テーブルにデータがあるか）確認
        if not self.prediction_tree.get_children():
            messagebox.showwarning("予測実行", "予測対象のレース情報が表示されていません。\nレースIDを入力して「レース情報表示」ボタンを押してください。")
            return

        # TODO: 予測モデルがロードされているか確認
        # if self.model is None:
        #     messagebox.showwarning("予測実行", "予測モデルがロードされていません。\n設定タブでモデルをロードするか、学習させてください。")
        #     return

        prediction_type = self.prediction_type_var.get() # win, utan, santan など
        self.update_status(f"{prediction_type} の予測実行中...")

        # テーブルから現在の出走馬情報を取得
        horses_on_table = []
        for item_id in self.prediction_tree.get_children():
            values = self.prediction_tree.item(item_id)["values"]
            # テーブルの列構成に合わせてインデックスを調整する必要があるかもしれません
            # 現在の想定: ["Umaban", "HorseName", "SexAge", "Load", "JockeyName", "Odds", "父", "母父", "近3走", "指数"]
            horse_dict = {
                "Umaban": item_id, # iid (馬番)
                "HorseName": values[1] if len(values) > 1 else 'N/A',
                "Odds": values[5] if len(values) > 5 else 'N/A' # 単勝オッズの列インデックス
                # TODO: モデル予測に必要な他の特徴量も取得する
            }
            horses_on_table.append(horse_dict)

        if not horses_on_table:
            messagebox.showerror("予測エラー", "出走馬情報が見つかりません。")
            self.update_status("エラー: 出走馬情報なし")
            return

        # _run_prediction_thread にデータを渡して実行
        self.run_in_thread(self._run_prediction_thread, prediction_type, horses_on_table)
    # ↑↑↑ ここまでを追加 ↑↑↑

    def _update_prediction_result_table(self, predictions, columns):
        """予測結果テーブルの更新"""
        # テーブルクリア
        for item in self.prediction_tree.get_children():
            self.prediction_tree.delete(item)

        if not predictions: # 結果がない場合は列設定もしない
            self.prediction_tree["columns"] = []
            return

        # 列設定
        self.prediction_tree["columns"] = columns
        self.prediction_tree["show"] = "headings"

        # 列幅とアライメントを設定
        for col in columns:
            width = 80 # デフォルト幅
            anchor = tk.W # デフォルト左寄せ
            if "馬番" in col:
                width = 100 if "→" in col else 40 # 組み合わせなら広く
                anchor = tk.CENTER
            elif "馬名" in col:
                 width = 150 if "→" in col else 120
            elif "オッズ" in col:
                 width = 70
                 anchor = tk.E
            elif "確率" in col:
                 width = 70
                 anchor = tk.E
            elif "期待値" in col:
                 width = 60
                 anchor = tk.E

            self.prediction_tree.heading(col, text=col)
            self.prediction_tree.column(col, width=width, anchor=anchor)

        # データ追加
        for i, pred in enumerate(predictions):
             values = [pred.get(col, 'N/A') for col in columns]
             # 期待値や確率を小数点以下表示調整
             for j, col_name in enumerate(columns):
                 if col_name == "予測確率":
                     try: values[j] = f"{float(values[j]):.4f}"
                     except: pass
                 elif col_name == "期待値":
                     try: values[j] = f"{float(values[j]):.2f}"
                     except: pass
                 elif "オッズ" in col_name:
                     try: values[j] = f"{float(values[j]):.1f}"
                     except: pass

             self.prediction_tree.insert("", "end", values=values, iid=f"pred_{i}") # iidを付与


    def save_prediction_result(self):
        """予測結果と推奨馬券をテキストファイルに保存"""
        if not self.race_info_label.cget("text") or "未選択" in self.race_info_label.cget("text"):
             messagebox.showwarning("保存エラー", "保存する予測結果がありません。\nレースを選択して予測を実行してください。")
             return

        save_dir = self.settings.get("results_dir", ".")
        # ファイル名にレース情報を含める
        race_info_str = self.race_info_label.cget("text").replace("レース情報: ", "").replace(" ", "_").replace("/", "-")
        pred_type = self.prediction_type_var.get()
        default_filename = f"prediction_{race_info_str}_{pred_type}_{datetime.now().strftime('%Y%m%d%H%M')}.txt"

        file_path = filedialog.asksaveasfilename(
            title="予測結果を保存",
            initialdir=save_dir,
            initialfile=default_filename,
            defaultextension=".txt",
            filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")]
        )
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    # レース情報
                    f.write(f"{self.race_info_label.cget('text')}\n")
                    f.write(f"{self.race_details_label.cget('text')}\n\n")

                    # 予測結果テーブルの内容
                    f.write("--- 予測結果 ---\n")
                    columns = self.prediction_tree["columns"]
                    if columns:
                         f.write("\t".join(columns) + "\n")
                         for item_id in self.prediction_tree.get_children():
                             values = self.prediction_tree.item(item_id)["values"]
                             f.write("\t".join(map(str, values)) + "\n")
                    else:
                         f.write("予測結果はありません。\n")

                    # 推奨馬券
                    f.write("\n--- 推奨馬券 ---\n")
                    f.write(self.recommendation_text.get(1.0, tk.END))

                self.update_status(f"予測結果を保存しました: {file_path}")
                messagebox.showinfo("予測結果保存", "予測結果を保存しました。")
            except Exception as e:
                 messagebox.showerror("保存エラー", f"予測結果の保存中にエラーが発生しました:\n{e}")
                 self.update_status("エラー: 予測結果の保存失敗")


    # --- Result Verification (Backtesting) ---
    def run_result_analysis(self):
        """結果分析（バックテスト）実行処理"""
        if self.combined_data is None or self.combined_data.empty:
             messagebox.showwarning("バックテスト実行", "分析対象のデータが読み込まれていません。\nデータ管理タブでデータを読み込んでください。")
             return

        # TODO: 予測モデルがロードされているか確認
        # if self.model is None: ...

        analysis_type = self.result_type_var.get() # 表示するグラフの種類
        self.update_status(f"バックテスト実行中 ({analysis_type})...")

        # バックテスト条件を取得
        try:
             start_date = f"{self.result_from_year_var.get()}-{self.result_from_month_var.get()}-01"
             end_year = int(self.result_to_year_var.get())
             end_month = int(self.result_to_month_var.get())
             # 月末日を取得
             import calendar
             last_day = calendar.monthrange(end_year, end_month)[1]
             end_date = f"{end_year:04d}-{end_month:02d}-{last_day:02d}"
             start_dt = pd.to_datetime(start_date)
             end_dt = pd.to_datetime(end_date)
        except ValueError:
            messagebox.showerror("日付エラー", "バックテスト期間の開始日または終了日の形式が正しくありません。")
            self.update_status("エラー: 日付形式不正")
            return

        bet_types_to_run = {
            "win": self.res_win_var.get(),
            "place": self.res_place_var.get(),
            "wide": self.res_wide_var.get(),
            "uren": self.res_uren_var.get(),
            "utan": self.res_utan_var.get(),
            "sanfuku": self.res_sanfuku_var.get(),
            "santan": self.res_santan_var.get(),
        }

        if not any(bet_types_to_run.values()):
            messagebox.showwarning("バックテスト実行", "対象の馬券種が選択されていません。")
            return

        # バックテスト実行（スレッド）
        self.run_in_thread(self._run_result_analysis_thread, start_dt, end_dt, bet_types_to_run, analysis_type)

    def _run_result_analysis_thread(self, start_dt, end_dt, bet_types_to_run, analysis_type):
        """結果分析（バックテスト）の非同期処理（完全版・省略なし）"""
        import time
        import pandas as pd # type: ignore
        import numpy as np # type: ignore
        import matplotlib.pyplot as plt # type: ignore # グラフ表示用に必要
        import traceback

        # この関数内の try...except は、予期せぬエラー全体を捕捉するためのもの
        try:
            start_time = _time.time()
            self.root.after(0, lambda: self.update_status(f"バックテスト実行中 ({start_dt.date()}～{end_dt.date()})..."))
            print(f"\n--- バックテスト開始 ({start_dt.date()} ～ {end_dt.date()}) ---")

            # --- 1. 対象期間のデータ抽出 ---
            if self.combined_data is None or self.combined_data.empty:
                 self.root.after(0, lambda: messagebox.showwarning("データエラー", "データが読み込まれていません。")); self.root.after(0, lambda: self.update_status("準備完了")); return

            date_col = None
            if 'date' in self.combined_data.columns and pd.api.types.is_datetime64_any_dtype(self.combined_data['date']): date_col = 'date'
            elif 'race_date' in self.combined_data.columns and pd.api.types.is_datetime64_any_dtype(self.combined_data['race_date']): date_col = 'race_date'

            # デバッグプリントは一旦削除 (必要なら復活させる)
            # print(f"DEBUG: Filtering data between {start_dt} ...")

            if date_col is None:
                 self.root.after(0, lambda: messagebox.showerror("データエラー", "日付列が見つからないか、日付型ではありません。")); self.root.after(0, lambda: self.update_status("エラー: 日付列不正")); return

            try:
                 backtest_data = self.combined_data[
                     (self.combined_data[date_col] >= start_dt) &
                     (self.combined_data[date_col] <= end_dt)
                 ].copy()
                 # print(f"DEBUG: Shape of backtest_data after filtering: {backtest_data.shape}")
            except Exception as e_filter:
                 print(f"!!! Error during date filtering !!!"); traceback.print_exc()
                 self.root.after(0, lambda: messagebox.showerror("エラー", f"期間でのデータ絞り込み中にエラー:\n{e_filter}")); self.root.after(0, lambda: self.update_status("エラー: 期間フィルター失敗")); return

            if backtest_data.empty:
                self.root.after(0, lambda: messagebox.showinfo("バックテスト結果", "指定された期間に該当するレースデータがありません。"))
                self.root.after(0, lambda: self.update_status("バックテスト完了: 対象データなし"))
                return

            print(f"バックテスト対象レース数（推定）: {backtest_data['race_id'].nunique()}")
            self.update_status("バックテスト: 指数計算中(レース毎)...")
            print("バックテスト: レース毎に指数を計算します...")

            # --- 払い戻しデータ準備 ---
            payout_dict_for_sim = {p['race_id']: p for p in self.payout_data if 'race_id' in p}

            # --- 3. 購入シミュレーションループ ---
            simulation_results = []; total_investment = 0; total_return = 0; total_bets = 0; total_hits = 0
            unique_race_ids = backtest_data['race_id'].unique(); num_races_total = len(unique_race_ids)

            for i, race_id in enumerate(unique_race_ids):
                if i % 10 == 0: self.update_status(f"シミュレーション中... ({i}/{num_races_total})")
                race_df = backtest_data[backtest_data['race_id'] == race_id].copy();
                if race_df.empty: continue
                race_info_row = race_df.iloc[0]
                race_conditions = {
                    'course_type': race_info_row.get('course_type'),
                    'distance': pd.to_numeric(race_info_row.get('distance'), errors='coerce'),
                    'track_name': race_info_row.get('track_name'),
                    'baba': race_info_row.get('track_condition')
                }
                if pd.isna(race_conditions['distance']): continue;
                race_conditions['distance'] = int(race_conditions['distance'])

                race_indices = []
                for index, row in race_df.iterrows(): # 指数計算ループ
                    horse_id = row.get('horse_id'); umaban = row.get('Umaban');
                    if not horse_id: continue
                    # --- 指数計算（詳細取得含む）---
                    # この部分は時間がかかるので注意
                    details = self.get_horse_details(str(horse_id))
                    index_val, index_comp = self.calculate_original_index(details, race_conditions)
                    race_indices.append({'Umaban': umaban, 'Index': index_val})
                if not race_indices: continue

                race_indices.sort(key=lambda x: x.get('Index', -float('inf')), reverse=True) # Indexがない場合も考慮
                if not race_indices: continue

                # --- 購入判断 (戦略: 指数1位の複勝を100円) ---
                bet_target_umaban_obj = race_indices[0].get('Umaban')
                if bet_target_umaban_obj is None or not str(bet_target_umaban_obj).isdigit(): continue
                bet_target_umaban = int(bet_target_umaban_obj)
                bet_amount = 100
                total_investment += bet_amount; total_bets += 1

                # --- 結果照合 ---
                payout_info = payout_dict_for_sim.get(race_id); hit = False; pay = 0
                if payout_info and '複勝' in payout_info:
                    place_pay_info = payout_info['複勝']
                    if '馬番' in place_pay_info and '払戻金' in place_pay_info:
                        try:
                            payout_numbers = [int(n) for n in place_pay_info.get('馬番', []) if isinstance(n, str) and n.isdigit()]
                            payout_amounts = [int(p) for p in place_pay_info.get('払戻金', []) if p is not None]
                            if len(payout_numbers) == len(payout_amounts) and bet_target_umaban in payout_numbers:
                               hit_index = payout_numbers.index(bet_target_umaban); pay = payout_amounts[hit_index]
                               total_return += pay; total_hits += 1; hit = True
                        except (ValueError, IndexError, TypeError) as e_pay_parse: print(f"警告: レース {race_id} の複勝払戻情報の解析エラー: {e_pay_parse}")

                simulation_results.append({
                    'race_id': race_id,
                    'date': race_df[date_col].iloc[0],
                    'bet_type': '複勝',
                    'bet_target': bet_target_umaban,
                    'investment': bet_amount,
                    'return': pay,
                    'hit': hit
                })

            # --- 4. 結果集計 ---
            if total_bets > 0:
                profit = total_return - total_investment
                roi = total_return / total_investment if total_investment > 0 else 0
                hit_rate = total_hits / total_bets
            else:
                profit = 0; roi = 0; hit_rate = 0; total_investment = 0; total_return = 0; total_hits = 0 # num_races_totalは上で定義済み

            # --- 5. 結果表示 ---
            # サマリー表示
            summary = f"--- バックテスト結果 ({start_dt.date()} ～ {end_dt.date()}) ---\n"
            summary += f"対象レース数: {num_races_total}\n"
            summary += f"総購入レース数: {total_bets}\n"
            summary += f"総投資額: {total_investment:,.0f} 円\n"
            summary += f"総回収額: {total_return:,.0f} 円\n"
            summary += f"総収支: {profit:,.0f} 円\n"
            summary += f"回収率 (ROI): {roi:.1%}\n"
            summary += f"的中率: {hit_rate:.1%} ({total_hits}/{total_bets})\n"
            summary += "\n【実行戦略】\n- 指数1位の馬の複勝を100円購入\n"

            # === ★★★ UI更新処理を分離 ★★★ ===
            # サマリーテキストの更新を依頼
            self.root.after(0, self._update_summary_text, summary)
            # グラフ描画の更新を依頼
            graph_title = '収支推移 (指数1位複勝)' # グラフタイトルを生成
            self.root.after(0, self._draw_result_graph, simulation_results, analysis_type, graph_title)
            # === ★★★ 修正ここまで ★★★ ===

            # グラフ表示 (収支推移)
            self.result_figure.clear() # 先にクリア
            ax = self.result_figure.add_subplot(111)
            if simulation_results:
                 sim_df = pd.DataFrame(simulation_results)
                 sim_df['profit'] = sim_df['return'] - sim_df['investment']
                 sim_df['cumulative_profit'] = sim_df['profit'].cumsum()
                 # date列がdatetime型でない場合があるため変換を試みる
                 try:
                     sim_df['date'] = pd.to_datetime(sim_df['date'])
                     sim_df = sim_df.sort_values(by='date') # 日付でソートしてからプロット
                     ax.plot(sim_df['date'], sim_df['cumulative_profit'], marker='.', linestyle='-')
                 except Exception as e_plot:
                     print(f"グラフ描画エラー（日付データ）: {e_plot}")
                     ax.text(0.5, 0.5, 'グラフ描画エラー', ha='center', va='center')

                 ax.set_xlabel('日付')
                 ax.set_ylabel('累計収支 (円)')
                 ax.set_title('収支推移 (指数1位複勝)')
                 try: # autofmt_xdateがエラーを起こすことがあるためtry-except
                      self.result_figure.autofmt_xdate()
                 except:
                      pass
                 ax.grid(True, linestyle='--', alpha=0.6)
            else:
                 ax.text(0.5, 0.5, 'シミュレーション結果なし', ha='center', va='center')
                 ax.set_title('収支推移 (データなし)')

            self.root.after(0, self.result_canvas.draw) # グラフ描画をUIスレッドに依頼
            end_time = time.time()
            print(f"--- バックテスト完了 ({end_time - start_time:.2f} 秒) ---")
            self.root.after(0, lambda: self.update_status("バックテスト完了"))

        # === ここから except ブロック (省略せずに記述) ===
        except Exception as e:
            print(f"!!! Error in _run_result_analysis_thread !!!")
            traceback.print_exc()
            # エラー時もUI更新を試みる (lambdaを修正)
            self.root.after(0, lambda err=e: messagebox.showerror("バックテストエラー", f"バックテスト実行中にエラーが発生しました:\n{err}"))
            self.root.after(0, lambda err=e: self.update_status(f"エラー: バックテスト失敗 ({err})"))
            # エラー時は空のデータで表示をクリア
            self.root.after(0, self._update_summary_text, "エラーが発生しました。")
            self.root.after(0, self._draw_result_graph, [], "エラー", "エラー") # 空リストとエラータイトル

    # --- バックテスト結果表示用ヘルパーメソッド (新規追加) ---
    def _update_summary_text(self, summary_content):
        """結果検証タブのサマリーテキストエリアを更新"""
        try:
            self.summary_text.delete(1.0, tk.END)
            self.summary_text.insert(tk.END, summary_content)
            print("DEBUG: Summary text updated in UI.")
        except Exception as e:
            print(f"ERROR updating summary text: {e}")
            traceback.print_exc()

    def _draw_result_graph(self, simulation_results, analysis_type, title="収支推移"):
        """結果検証タブのグラフを描画"""
        print(f"DEBUG: Drawing result graph for type: {analysis_type}") #デバッグ用
        try:
            self.result_figure.clear()
            ax = self.result_figure.add_subplot(111)

            if analysis_type == "収支推移":
                if simulation_results: # 結果がある場合のみ描画
                    sim_df = pd.DataFrame(simulation_results)
                    # date列をdatetimeに変換し、ソート
                    try:
                        sim_df['date'] = pd.to_datetime(sim_df['date'])
                        sim_df = sim_df.sort_values(by='date')
                        sim_df['profit'] = sim_df['return'] - sim_df['investment']
                        sim_df['cumulative_profit'] = sim_df['profit'].cumsum()
                        # グラフ描画
                        ax.plot(sim_df['date'], sim_df['cumulative_profit'], marker='.', linestyle='-')
                        ax.set_xlabel('日付')
                        ax.set_ylabel('累計収支 (円)')
                        ax.set_title(title) # 引数で受け取ったタイトルを使用
                        self.result_figure.autofmt_xdate(rotation=30) # ラベル回転角度調整
                        ax.grid(True, linestyle='--', alpha=0.6)
                    except Exception as e_plot:
                        print(f"ERROR: Failed to plot profit curve: {e_plot}")
                        ax.text(0.5, 0.5, 'グラフ描画エラー', ha='center', va='center')
                        ax.set_title(title)
                else:
                    ax.text(0.5, 0.5, 'シミュレーション結果なし', ha='center', va='center')
                    ax.set_title(title + " (データなし)")

            # --- 他の分析タイプ（グラフ）もここに追加 ---
            elif analysis_type == "馬券種別ROI":
                 # TODO: investments_by_type, returns_by_type が必要
                 ax.text(0.5, 0.5, '馬券種別ROI\n(グラフ未実装)', ha='center', va='center')
                 ax.set_title("馬券種別ROI (未実装)")
            elif analysis_type == "的中率":
                 # TODO: hit_counts, bet_counts が必要
                 ax.text(0.5, 0.5, '的中率グラフ\n(未実装)', ha='center', va='center')
                 ax.set_title("的中率 (未実装)")
            # ... 他のグラフタイプ ...
            else:
                 ax.text(0.5, 0.5, f'{analysis_type}\n(グラフ未実装)', ha='center', va='center')
                 ax.set_title(f"{analysis_type} (未実装)")

            self.result_figure.tight_layout()
            self.result_canvas.draw() # ここで描画を更新
            print("DEBUG: Result graph drawn/updated.")

        except Exception as e:
            print(f"!!! Error in _draw_result_graph !!!")
            traceback.print_exc()
            try: # エラー時もクリアを試みる
                 self.result_figure.clear(); ax = self.result_figure.add_subplot(111)
                 ax.text(0.5, 0.5, 'グラフ描画エラー', ha='center', va='center'); ax.set_title("エラー")
                 self.result_canvas.draw()
            except: pass # クリアも失敗したら何もしない

    def save_result_analysis(self):
        """バックテスト結果のグラフとサマリーを保存"""
        save_dir = self.settings.get("results_dir", ".")
        analysis_type = self.result_type_var.get()
        start_date = self.result_from_year_var.get() + self.result_from_month_var.get()
        end_date = self.result_to_year_var.get() + self.result_to_month_var.get()
        base_filename = f"backtest_{start_date}-{end_date}_{analysis_type}_{datetime.now().strftime('%Y%m%d%H%M')}"

        # --- グラフ保存 ---
        graph_file_path = filedialog.asksaveasfilename(
            title="バックテストグラフを保存",
            initialdir=save_dir,
            initialfile=f"{base_filename}.png",
            defaultextension=".png",
            filetypes=[("PNG画像", "*.png"), ("JPEG画像", "*.jpg"), ("すべてのファイル", "*.*")]
        )
        if graph_file_path:
            try:
                self.result_figure.savefig(graph_file_path, bbox_inches='tight')
                self.update_status(f"バックテストグラフを保存しました: {graph_file_path}")
                # messagebox.showinfo("グラフ保存", "バックテストグラフを保存しました。") # 連続保存を考慮してコメントアウトも可
            except Exception as e:
                 messagebox.showerror("保存エラー", f"グラフの保存中にエラーが発生しました:\n{e}")
                 self.update_status("エラー: グラフ保存失敗")
                 return # グラフ保存失敗時はテキスト保存もしない

        # --- サマリーテキスト保存 ---
        summary_content = self.summary_text.get(1.0, tk.END).strip()
        if summary_content: # サマリーがあればテキストファイルも保存するか尋ねる
            if messagebox.askyesno("サマリー保存確認", "バックテストのサマリー結果もテキストファイルとして保存しますか？"):
                text_file_path = filedialog.asksaveasfilename(
                    title="バックテストサマリーを保存",
                    initialdir=save_dir,
                    initialfile=f"{base_filename}.txt", # 拡張子をtxtに
                    defaultextension=".txt",
                    filetypes=[("テキストファイル", "*.txt"), ("すべてのファイル", "*.*")]
                )
                if text_file_path:
                    try:
                        with open(text_file_path, "w", encoding="utf-8") as f:
                            f.write(summary_content)
                        self.update_status(f"グラフとサマリーを保存しました")
                        messagebox.showinfo("保存完了", "バックテストのグラフとサマリーを保存しました。")
                    except Exception as e:
                        messagebox.showerror("保存エラー", f"サマリーの保存中にエラーが発生しました:\n{e}")
                        self.update_status("エラー: サマリー保存失敗")
        elif graph_file_path: # グラフだけ保存した場合
             messagebox.showinfo("グラフ保存", "バックテストグラフを保存しました。")


    # --- Settings ---
    def get_default_settings(self):
        """デフォルト設定を返す"""
        app_data_dir = os.path.join(os.path.expanduser("~"), "HorseRacingAnalyzer")
        return {
            "min_expected_value": 1.1, # デフォルト値を少し下げる
            "min_probability": 0.05, # デフォルト値を少し下げる
            "kelly_fraction": 0.1,  # デフォルトをより安全な値に (10%ケリー)
            "max_bet_ratio": 0.05, # 5%
            "data_dir": os.path.join(app_data_dir, "data"),
            "models_dir": os.path.join(app_data_dir, "models"),
            "results_dir": os.path.join(app_data_dir, "results")
        }

    def load_settings(self):
        """設定ファイルの読み込み"""
        defaults = self.get_default_settings()
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)
                    # デフォルトにないキーや型が違う場合を考慮してマージ
                    valid_settings = defaults.copy()
                    for key, default_value in defaults.items():
                         if key in loaded_settings and type(loaded_settings[key]) == type(default_value):
                             valid_settings[key] = loaded_settings[key]
                         elif key in loaded_settings:
                              print(f"設定ファイル '{key}' の型が不正なためデフォルト値を使用します。", file=sys.stderr)
                    self.settings = valid_settings
                print("設定ファイルを読み込みました:", self.settings_file)
            except json.JSONDecodeError:
                 messagebox.showerror("設定エラー", f"設定ファイル ({self.settings_file}) が破損しています。デフォルト設定を使用します。")
                 self.settings = defaults
            except Exception as e:
                 messagebox.showwarning("設定読み込みエラー", f"設定ファイルの読み込み中にエラーが発生しました: {e}\nデフォルト設定を使用します。")
                 self.settings = defaults
        else:
            print("設定ファイルが見つからないため、デフォルト設定を使用します。")
            self.settings = defaults
            # 初回起動時などにデフォルト設定ファイルを作成する（オプション）
            # try:
            #     os.makedirs(self.app_data_dir, exist_ok=True)
            #     with open(self.settings_file, "w", encoding="utf-8") as f:
            #         json.dump(self.settings, f, indent=4)
            #     print("デフォルト設定ファイルを作成しました:", self.settings_file)
            # except Exception as e:
            #     print(f"デフォルト設定ファイルの作成に失敗しました: {e}", file=sys.stderr)

    def reflect_settings_to_ui(self):
        """現在の設定値を設定タブのUIに反映"""
        self.settings_min_ev_var.set(str(self.settings.get("min_expected_value", "")))
        self.settings_min_prob_var.set(str(self.settings.get("min_probability", "")))
        self.settings_kelly_var.set(str(self.settings.get("kelly_fraction", "")))
        self.settings_max_bet_var.set(str(self.settings.get("max_bet_ratio", "")))
        self.settings_data_dir_var.set(self.settings.get("data_dir", ""))
        self.settings_models_dir_var.set(self.settings.get("models_dir", ""))
        self.settings_results_dir_var.set(self.settings.get("results_dir", ""))

        # 予測タブの戦略表示も更新
        if hasattr(self, 'pred_min_ev_label'): # UI初期化後かチェック
            self.pred_min_ev_label.config(text=f"{self.settings.get('min_expected_value', 'N/A'):.2f}")
            self.pred_min_prob_label.config(text=f"{self.settings.get('min_probability', 'N/A'):.3f}")
            self.pred_kelly_label.config(text=f"{self.settings.get('kelly_fraction', 'N/A'):.2f}")
            self.pred_max_bet_label.config(text=f"{self.settings.get('max_bet_ratio', 'N/A'):.1%}")


    def save_settings(self):
        """UIから設定値を取得し、ファイルに保存"""
        try:
            new_settings = {
                "min_expected_value": float(self.settings_min_ev_var.get()),
                "min_probability": float(self.settings_min_prob_var.get()),
                "kelly_fraction": float(self.settings_kelly_var.get()),
                "max_bet_ratio": float(self.settings_max_bet_var.get()),
                "data_dir": self.settings_data_dir_var.get(),
                "models_dir": self.settings_models_dir_var.get(),
                "results_dir": self.settings_results_dir_var.get()
            }

            # 値のバリデーション (例)
            if not (0 < new_settings["kelly_fraction"] <= 1):
                 raise ValueError("ケリー係数は0より大きく1以下である必要があります。")
            if not (0 < new_settings["max_bet_ratio"] <= 1):
                 raise ValueError("最大投資比率は0より大きく1以下である必要があります。")
            if not (0 <= new_settings["min_probability"] < 1):
                 raise ValueError("最小予測確率は0以上1未満である必要があります。")
            if new_settings["min_expected_value"] <= 0:
                 raise ValueError("最小期待値は0より大きい必要があります。")

            # ディレクトリが存在するか確認し、なければ作成を試みる
            for dir_path in [new_settings["data_dir"], new_settings["models_dir"], new_settings["results_dir"]]:
                 if not os.path.exists(dir_path):
                     try:
                         os.makedirs(dir_path)
                         print(f"ディレクトリを作成しました: {dir_path}")
                     except Exception as e:
                         # 作成失敗しても設定は保存するが警告は出す
                         messagebox.showwarning("ディレクトリ作成失敗", f"指定されたディレクトリが見つからず、作成もできませんでした:\n{dir_path}\nエラー: {e}")

            # 設定ファイルに保存
            self.settings = new_settings # アプリ内部の設定を更新
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4, ensure_ascii=False)

            self.update_status("設定を保存しました。")
            messagebox.showinfo("設定保存", "設定を保存しました。")
            self.reflect_settings_to_ui() # 予測タブの表示も更新

        except ValueError as ve:
            messagebox.showerror("設定値エラー", f"入力値が不正です:\n{ve}")
        except Exception as e:
            messagebox.showerror("設定保存エラー", f"設定の保存中にエラーが発生しました:\n{e}")
            self.update_status("エラー: 設定保存失敗")

    def reset_settings(self):
        """設定をデフォルト値に戻す"""
        if messagebox.askyesno("設定リセット", "すべての設定をデフォルト値に戻しますか？\n保存されていない変更は失われます。", icon='warning'):
            self.settings = self.get_default_settings()
            self.reflect_settings_to_ui()
            # デフォルト設定をファイルに保存するかはオプション（上書き確認をしてもよい）
            # self.save_settings()
            self.update_status("設定をデフォルトにリセットしました。")
            messagebox.showinfo("設定リセット", "設定をデフォルト値にリセットしました。\n「設定を保存」ボタンを押して変更を確定してください。")


    # --- Sample Data Generation ---
    def generate_sample_data(self):
        """サンプルデータの生成（デバッグ/デモ用）"""
        print("サンプルデータを生成します...")
        # レースデータ
        num_races = 100
        race_ids = [f'2023{i:04d}' for i in range(1, num_races + 1)]
        tracks = ['東京', '中山', '阪神', '京都', '中京', '小倉', '福島', '新潟', '札幌', '函館']
        course_types = ['芝', 'ダート']
        weathers = ['晴', '曇', '小雨', '雨']
        conditions = ['良', '稍重', '重', '不良']
        race_data = {
            'race_id': race_ids,
            'race_date': pd.to_datetime([f'2023-{(i%12)+1:02d}-{(i%28)+1:02d}' for i in range(1, num_races + 1)]),
            'track': [random.choice(tracks) for _ in range(num_races)],
            'distance': [random.choice([1000, 1200, 1400, 1600, 1800, 2000, 2200, 2400, 2500, 3000, 3200]) for _ in range(num_races)],
            'course_type': [random.choice(course_types) for _ in range(num_races)],
            'weather': [random.choice(weathers) for _ in range(num_races)],
            'track_condition': [random.choice(conditions) for _ in range(num_races)]
            # TODO: レース名、グレードなどの列も必要に応じて追加
        }
        self.race_data = pd.DataFrame(race_data)

        # 馬データ
        num_horses = 200
        horse_ids = [f'H{i:04d}' for i in range(1, num_horses + 1)]
        sexes = ['牡', '牝', 'セ']
        fathers = [f'父馬{chr(65+random.randint(0,25))}' for _ in range(num_horses)] # 父馬A-Z
        mothers = [f'母馬{chr(65+random.randint(0,25))}' for _ in range(num_horses)] # 母馬A-Z
        horse_data = {
            'horse_id': horse_ids,
            'horse_name': [f'サンプル馬{i}' for i in range(1, num_horses + 1)],
            'birth_year': [random.randint(2018, 2021) for _ in range(num_horses)], # 生まれ年調整
            'sex': [random.choice(sexes) for _ in range(num_horses)],
            'father': fathers,
            'mother': mothers
            # TODO: 生産者、馬主などの列も必要に応じて追加
        }
        self.horse_data = pd.DataFrame(horse_data)

        # 結果データ
        num_results = 0
        results_list = []
        jockeys = [f'騎手{chr(65+i)}' for i in range(30)] # 騎手A-Z...
        for race_id in self.race_data['race_id']:
            horses_count = random.randint(8, 18)
            selected_horses = random.sample(self.horse_data['horse_id'].tolist(), horses_count)
            ranks = list(range(1, horses_count + 1))
            random.shuffle(ranks)
            # 単勝オッズ生成 (人気順になるように多少調整)
            win_probs = np.random.dirichlet(np.ones(horses_count) * random.uniform(0.5, 1.5)) # ディリクレ分布
            win_odds = np.round(1 / win_probs * 0.8, 1) # 控除率20%と仮定
            win_odds = np.clip(win_odds, 1.1, 500) # オッズ範囲制限
            odds_dict = {horse_id: odd for horse_id, odd in zip(selected_horses, win_odds)}

            for i, horse_id in enumerate(selected_horses):
                result = {
                    'race_id': race_id,
                    'horse_id': horse_id,
                    'jockey': random.choice(jockeys),
                    'weight': random.randint(440, 540), # 馬体重
                    'odds': odds_dict[horse_id], # 単勝オッズ
                    'rank': ranks[i]
                    # TODO: 斤量、上がりタイム、コーナー通過順位、配当金などの列も必要
                }
                results_list.append(result)
                num_results += 1

        self.result_data = pd.DataFrame(results_list)
        print(f"サンプルデータ生成完了: Races={len(self.race_data)}, Horses={len(self.horse_data)}, Results={len(self.result_data)}")

# --- Main Execution ---
def main():
    root = tk.Tk()
    # DPIスケーリング対応 (Windows)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1) # DPI Awareに設定
    except Exception as e:
        print(f"DPIスケーリング設定に失敗しました: {e}", file=sys.stderr)

    app = HorseRacingAnalyzerApp(root)

    # ウィンドウを閉じるときの処理
    def on_closing():
        # 必要なら設定を自動保存するなどの処理
        # if messagebox.askokcancel("終了確認", "アプリケーションを終了しますか？"):
        #     # app.save_settings() # 自動保存する場合
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    # スクリプトが直接実行された場合にmain関数を呼び出す
    
        # --- ★★★ ここからテストコードを追加 ★★★ ---
    try:
        # GUIなしでテストするために一時的にインスタンスを作成
        # Tkinterの初期化が必要な場合があるためダミーウィンドウを作成
        temp_root = tk.Tk()
        temp_root.withdraw() # ウィンドウは表示しない
        app_instance_for_test = HorseRacingAnalyzerApp(temp_root) # アプリのインスタンスを作成

        # テストしたい馬IDを指定 (例: 2015104498 はアーモンドアイ)
        test_horse_id = "2015104498"
        # print(f"\n--- Testing get_horse_details for horse_id: {test_horse_id} ---")

        # get_horse_details 関数を呼び出す
        details = app_instance_for_test.get_horse_details(test_horse_id)

        # 結果を出力
        # print("\n--- 馬詳細テスト結果 ---")
        # print(details)
        # print("----------------------\n")

        # テストが終わったらダミーウィンドウを破棄
        temp_root.destroy()

    except Exception as test_e:
        print(f"馬詳細テスト中にエラーが発生しました: {test_e}")
        import traceback
        traceback.print_exc()
    # --- ★★★ テストコード追加ここまで ★★★ ---
    
    main()

