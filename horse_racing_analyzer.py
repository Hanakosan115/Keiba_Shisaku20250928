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
import shap # type: ignore
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



class HorseRacingAnalyzerApp:
    # --- Pickle化されたファイルの読み込み/保存用ヘルパーメソッド ---
    def _load_pickle(self, file_path):
        """指定されたパスからpickleファイルをロードして返す"""
        import pickle
        import os # osモジュールをインポート
        if file_path and os.path.exists(file_path):
            try:
                with open(file_path, 'rb') as f:
                    data = pickle.load(f)
                print(f"INFO: Pickleファイルをロードしました: {file_path}")
                return data
            except pickle.UnpicklingError as e:
                print(f"ERROR: Pickleファイルのデコードに失敗しました: {file_path}. 内容が破損しているか、pickle形式ではありません。 Error: {e}")
            except EOFError as e:
                print(f"ERROR: Pickleファイルが空か、途中で終了しています: {file_path}. Error: {e}")
            except Exception as e:
                print(f"ERROR: Pickleファイルのロード中に予期せぬエラーが発生しました: {file_path}. Error: {e}")
        else:
            print(f"INFO: Pickleファイルが見つかりません: {file_path}")
        return None # ロード失敗時は None を返す

    def _save_pickle(self, data, file_path):
        """指定されたデータをpickleファイルとして保存する"""
        import pickle
        import os # osモジュールをインポート
        try:
            # 保存先ディレクトリが存在しない場合は作成
            save_dir = os.path.dirname(file_path)
            if save_dir and not os.path.exists(save_dir): # save_dirが空文字列でないことも確認
                os.makedirs(save_dir)
                print(f"INFO: ディレクトリを作成しました: {save_dir}")

            with open(file_path, 'wb') as f:
                pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
            print(f"INFO: Pickleファイルに保存しました: {file_path}")
            return True
        except Exception as e:
            print(f"ERROR: Pickleファイルへの保存中にエラーが発生しました: {file_path}. Error: {e}")
        return False
    
    def on_closing(self):
        """アプリケーション終了時の処理。キャッシュをファイルに保存する。"""
        print("アプリケーションを終了します。現在のキャッシュを保存中...")
        self.update_status("キャッシュを保存中...")
        try:
            # 既存のキャッシュ保存ロジックを呼び出す
            self.save_cache_to_file()
            print("キャッシュの保存が完了しました。")
        except Exception as e:
            print(f"終了時のキャッシュ保存中にエラーが発生しました: {e}")
            # エラーが発生しても、アプリケーションは終了させる
        
        self.root.destroy()
    
    def __init__(self, root):
        self.JRA_TRACKS = ["札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"]
        self.root = root
        self.root.title("競馬データ分析ツール")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # ★★★ ウィンドウを閉じる際の動作を、新しいon_closingメソッドに紐付け ★★★
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

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
        self.trained_model = None # 学習済みモデルを格納する属性 (self.model とは別に用意)
        self.model_features = []  # 学習済みモデルが使用した特徴量リスト
        self.imputation_values_ = {} # ★★★ 欠損値補完のための値を格納する辞書を初期化 ★★★

        # 設定ファイルのパスを決定（ensure_directories_existより前に実行）
        self.app_data_dir = os.path.join(os.path.expanduser("~"), "HorseRacingAnalyzer")
        self.settings_file = os.path.join(self.app_data_dir, "settings.json")

        # 設定の読み込み（デフォルト値の設定もここで行う）
        self.load_settings()
        self.load_cache_from_file() # ← ★ ここでキャッシュを読み込む
        self.load_model_from_file()
        
        imputation_values_default_filename = "imputation_values.pkl"
        models_base_dir = self.settings.get("models_dir", self.settings.get("data_dir", os.path.join(self.app_data_dir, "models")))
        default_imputation_path = os.path.join(models_base_dir, imputation_values_default_filename)
        
        imputation_values_path = self.settings.get("imputation_values_path", default_imputation_path)
        
        loaded_imputation_values = self._load_pickle(imputation_values_path)
        if loaded_imputation_values is not None and isinstance(loaded_imputation_values, dict):
            self.imputation_values_ = loaded_imputation_values
            print(f"INFO: 欠損値補完のための値をロードしました: {imputation_values_path} ({len(self.imputation_values_)} 列分)")
        else:
            print(f"INFO: 欠損値補完ファイルが見つからないかロードに失敗 ({imputation_values_path})。学習時に新規作成されます。")

        self.REQUEST_TIMEOUT = 20
        self.SELENIUM_WAIT_TIMEOUT = 30
        self.SLEEP_TIME_PER_PAGE = float(self.settings.get("scrape_sleep_page", 0.7))
        self.SLEEP_TIME_PER_RACE = float(self.settings.get("scrape_sleep_race", 0.2))
        self.USER_AGENT = self.settings.get("user_agent", 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36')
        self.CHROME_DRIVER_PATH = self.settings.get("chrome_driver_path", None)
        self.SAVE_DIRECTORY = self.settings.get("data_dir", ".")
        self.PROCESSED_LOG_FILE = os.path.join(self.SAVE_DIRECTORY, "processed_race_ids.log")
        
        self.ensure_directories_exist()
        self.init_home_tab()
        self.init_data_tab()
        self.init_analysis_tab()
        self.init_prediction_tab()
        self.init_results_tab()
        self.init_settings_tab()
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
    
    def get_result_table(self, race_id):
        """
        【真・最終改修版】レース結果ページから情報を取得する。
        ヘッダー解析ロジックを修正し、'着順'などが正しく読み取れるようにした。
        """
        url = f'https://db.netkeiba.com/race/{race_id}/'
        print(f"      結果取得試行: {url}")
        headers = {'User-Agent': self.USER_AGENT}
        race_info_dict = {'race_id': race_id}
        results_list_of_dicts = []

        try:
            time.sleep(self.SLEEP_TIME_PER_RACE)
            r = requests.get(url, headers=headers, timeout=self.REQUEST_TIMEOUT)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.content, 'lxml')

            # --- レース情報の抽出 (変更なし) ---
            try:
                data_intro_div = soup.select_one('div.data_intro')
                if data_intro_div:
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
                            distance_match = re.search(r'(\d+)m', course_text)
                            race_info_dict['course_type'] = course_type_match.group(1) if course_type_match else None
                            race_info_dict['distance'] = int(distance_match.group(1)) if distance_match else None
                        if len(parts) >= 2: race_info_dict['weather'] = parts[1].split(':')[-1].strip()
                        if len(parts) >= 3: race_info_dict['track_condition'] = parts[2].split(':')[-1].strip()
                small_text_p = soup.select_one('p.smalltxt')
                if small_text_p:
                    small_text = small_text_p.get_text(strip=True)
                    date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', small_text)
                    if date_match: race_info_dict['date'] = date_match.group(1)
                    place_match = re.search(r'\d回(\S+?)\d日目', small_text)
                    if place_match: race_info_dict['track_name'] = place_match.group(1)
            except Exception as e_info:
                print(f"      警告: レース情報の抽出中にエラー: {e_info}")

            # --- ★★★ ヘッダー解析ロジックを修正 ★★★ ---
            table_tag = soup.select_one('table.race_table_01.nk_tb_common')
            if not table_tag:
                print(f"      エラー: 結果テーブルが見つかりません。 ({race_id})")
                return race_info_dict, []

            header_row = table_tag.find('tr')
            # get_text(strip=True)で'着順'などを正しく取得するシンプルな方式に変更
            header_cells = [th.get_text(strip=True) for th in header_row.find_all('th')]
            print(f"      [DEBUG] Found Raw Header: {header_cells}")

            data_rows = table_tag.find_all('tr')[1:]
            for tr_tag in data_rows:
                row_dict = {}
                td_tags = tr_tag.find_all('td')
                
                for i, td in enumerate(td_tags):
                    if i < len(header_cells):
                        header_key = header_cells[i]
                        row_dict[header_key] = td.get_text(strip=True)
                        if header_key == '馬名':
                            a_tag = td.find('a')
                            row_dict['HorseName_url'] = a_tag['href'].strip() if a_tag and a_tag.has_attr('href') else None
                
                if row_dict:
                    results_list_of_dicts.append(row_dict)
            
            return race_info_dict, results_list_of_dicts

        except requests.exceptions.RequestException as e:
            print(f"      ページ取得エラー ({url}): {e}")
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
    
    # --- ★★★ 部品関数6: 馬詳細情報取得 (ブラウザ再利用 対応版) ★★★ ---
    def get_horse_details(self, horse_id, driver=None):
        """馬の個別ページから詳細情報(プロフィール、血統、整形済み戦績)を取得して辞書で返す"""
        if not horse_id or not str(horse_id).isdigit():
            print(f"      警告: 無効な馬IDです: {horse_id}")
            return {'horse_id': horse_id, 'error': 'Invalid horse_id'}

        url = f'https://db.netkeiba.com/horse/{horse_id}/'
        
        # --- WebDriverの管理 ---
        # driverが外から渡されなかった場合のみ、この関数内で起動・終了する
        manage_driver_internally = False
        if driver is None:
            manage_driver_internally = True
            print(f"      馬詳細取得試行 (内部WebDriver): {url}")
            options = webdriver.ChromeOptions()
            options.add_argument(f'--user-agent={self.USER_AGENT}')
            options.add_argument('--headless')
            options.add_argument('--disable-gpu'); options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage'); options.add_argument("--log-level=3")
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            try:
                if self.CHROME_DRIVER_PATH and os.path.exists(self.CHROME_DRIVER_PATH):
                    service = ChromeService(executable_path=self.CHROME_DRIVER_PATH)
                    driver = webdriver.Chrome(service=service, options=options)
                else:
                    driver = webdriver.Chrome(options=options)
            except Exception as e:
                print(f"      ★★★★★ WebDriverの初期化中にエラー: {e}")
                traceback.print_exc()
                return {'horse_id': horse_id, 'error': 'WebDriver init failed'}
        else:
            print(f"      馬詳細取得試行 (共有WebDriver): {url}")

        horse_details = {'horse_id': horse_id}
        try:
            driver.get(url)
            wait = WebDriverWait(driver, self.SELENIUM_WAIT_TIMEOUT)
            wait.until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, 'table.db_prof_table, table.race_results, table.db_h_race_results, #race_results_table')
            ))
            time.sleep(0.5)
            
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # (以降のプロフィール、血統、戦績の解析ロジックは変更ありません)
            profile_table = soup.select_one('table.db_prof_table')
            if profile_table:
                 profile_ths = {th.get_text(strip=True): th.find_next_sibling('td').get_text(strip=True) for th in profile_table.find_all('th')}
                 if '父' in profile_ths: horse_details['father'] = profile_ths['父']
                 if '母' in profile_ths: horse_details['mother'] = profile_ths['母']
                 if '母父' in profile_ths: horse_details['mother_father'] = profile_ths['母父']
                 for th_text, td_text in profile_ths.items():
                     if '生年月日' in th_text: horse_details['birthday'] = td_text
                     elif '調教師' in th_text: horse_details['trainer_prof'] = td_text
                     elif '馬主' in th_text: horse_details['owner_prof'] = td_text
                     elif '生産者' in th_text: horse_details['breeder'] = td_text
                     elif '産地' in th_text: horse_details['birthplace'] = td_text
                     elif 'セリ取引価格' in th_text: horse_details['market_price'] = td_text
                     elif '獲得賞金' in th_text:
                        prize_match = re.search(r'([\d,]+)万円', td_text)
                        if prize_match:
                            horse_details['total_prize'] = pd.to_numeric(prize_match.group(1).replace(',', ''), errors='coerce')
                        else:
                            horse_details['total_prize'] = pd.to_numeric(td_text.replace(',', '').replace('万円',''), errors='coerce')
                     elif '通算成績' in th_text: horse_details['total_成績'] = td_text
                     elif '主な勝鞍' in th_text: horse_details['main_wins'] = td_text
            
            if 'father' not in horse_details or not horse_details['father']:
                blood_table = soup.find('table', summary='血統情報') or soup.select_one('table.blood_table')
                if blood_table:
                    tds = blood_table.find_all('td')
                    if len(tds) > 4:
                        horse_details['father'] = tds[0].get_text(strip=True)
                        horse_details['mother'] = tds[2].get_text(strip=True)
                        horse_details['mother_father'] = tds[4].get_text(strip=True)

            race_results_list = []
            results_table = soup.find('table', id='race_results_table') or \
                            soup.select_one('table.db_h_race_results') or \
                            soup.select_one('table.race_results')
            if results_table:
                rows = results_table.select('tbody tr')
                if not rows: rows = results_table.find_all('tr')[1:]
                print(f"      戦績テーブルから {len(rows)} 行のデータを処理します...")
                for i, row in enumerate(rows):
                    # (データ整形部分は変更なし)
                    cells = row.find_all('td')
                    if len(cells) < 12: continue
                    date_str = cells[0].get_text(strip=True) if len(cells) > 0 else ''
                    kaisai_str = cells[1].get_text(strip=True) if len(cells) > 1 else ''
                    rank_str = cells[11].get_text(strip=True) if len(cells) > 11 else ''
                    load_str = cells[13].get_text(strip=True) if len(cells) > 13 else ''
                    distance_str = cells[14].get_text(strip=True) if len(cells) > 14 else ''
                    baba_str = cells[15].get_text(strip=True) if len(cells) > 15 else ''
                    time_str = cells[17].get_text(strip=True) if len(cells) > 17 else ''
                    diff_str = cells[18].get_text(strip=True) if len(cells) > 18 else ''
                    agari_str = cells[22].get_text(strip=True) if len(cells) > 22 else ''
                    weight_str = cells[23].get_text(strip=True) if len(cells) > 23 else ''
                    race_result = {}
                    try: race_result['date'] = pd.to_datetime(date_str, format='%Y/%m/%d')
                    except ValueError: race_result['date'] = None
                    kaisai_match = re.match(r'(\d+)?(\D+)(\d+)?', kaisai_str) if kaisai_str else None
                    if kaisai_match: race_result['place'] = kaisai_match.group(2)
                    else: race_result['place'] = kaisai_str
                    race_result['rank'] = pd.to_numeric(rank_str, errors='coerce')
                    race_result['load'] = pd.to_numeric(load_str, errors='coerce')
                    if distance_str:
                        course_type_match = re.search(r'([芝ダ障])', distance_str)
                        distance_val_match = re.search(r'(\d+)', distance_str)
                        race_result['course_type'] = course_type_match.group(1) if course_type_match else None
                        race_result['distance'] = int(distance_val_match.group(1)) if distance_val_match else None
                    race_result['baba'] = baba_str
                    try:
                        if time_str and ':' in time_str:
                            parts = time_str.split(':'); race_result['time_sec'] = int(parts[0]) * 60 + float(parts[1])
                        elif time_str: race_result['time_sec'] = float(time_str)
                    except ValueError: race_result['time_sec'] = None
                    race_result['diff'] = diff_str
                    race_result['agari'] = pd.to_numeric(agari_str, errors='coerce')
                    weight_match = re.match(r'(\d+)\(([-+]?\d+)\)', weight_str) if weight_str else None
                    if weight_match: race_result['weight_val'] = int(weight_match.group(1))
                    race_results_list.append(race_result)
                
                if race_results_list:
                    prev_place = race_results_list[0].get('place')
                    if prev_place and prev_place not in self.JRA_TRACKS: horse_details['is_transfer_from_local_1ago'] = 1
                    else: horse_details['is_transfer_from_local_1ago'] = 0
                else: horse_details['is_transfer_from_local_1ago'] = 0
                horse_details['race_results'] = race_results_list
                print(f"      戦績テーブル取得・整形成功: {len(race_results_list)} レース分")
            else:
                print(f"      警告: 戦績テーブルが見つかりませんでした ({horse_id})")
                horse_details['race_results'] = []

        except Exception as e:
            print(f"      ★★★★★ ERROR in get_horse_details ({horse_id}): {e}")
            traceback.print_exc()
            horse_details['error'] = f'Unexpected Error: {e}'
        finally:
            # --- この関数内で起動した場合のみ、ここで閉じる ---
            if manage_driver_internally and driver:
                try: driver.quit()
                except Exception: pass

        return horse_details
    
    # --- ★★★ 調教データ取得メソッド (新規追加) ★★★ ---
    def get_training_data(self, race_id, driver):
        """
        指定されたrace_idの調教データをnetkeiba.comから取得する。
        WebDriverを引数として受け取り、再利用する。
        """
        training_data_list = []
        try:
            url = f"https://race.netkeiba.com/race/oikiri.html?race_id={race_id}"
            print(f"      調教データ取得試行: {url}")
            driver.get(url)
            # テーブルが表示されるまで待機
            WebDriverWait(driver, self.SELENIUM_WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'table.Oikiri_Table'))
            )
            time.sleep(0.5) # 描画待機
            soup = BeautifulSoup(driver.page_source, 'lxml')
            
            table = soup.select_one('table.Oikiri_Table')
            if not table:
                print(f"      警告: 調教テーブルが見つかりませんでした ({race_id})。")
                return []

            rows = table.select('tr.HorseList')
            for row in rows:
                horse_name = row.select_one('div.HorseName a')
                horse_id_tag = horse_name['href'] if horse_name else None
                horse_id = re.search(r'/horse/(\d+)', str(horse_id_tag)).group(1) if horse_id_tag else None

                # 評価(A,B,Cなど)を取得
                evaluation_tag = row.select_one('td.Oikiri_Hyouka > div')
                evaluation = evaluation_tag.get_text(strip=True) if evaluation_tag else None

                # 追切時計(Oikiri_Clock)の各タイムを取得
                clock_td = row.select_one('td.Oikiri_Clock')
                times = {}
                if clock_td:
                    time_elements = clock_td.find_all('li')
                    if time_elements and len(time_elements) >= 2:
                        # 最後の2つのliタグが全体時計と上がりタイム
                        times['total_time_str'] = time_elements[-2].get_text(strip=True)
                        times['last_furlong_str'] = time_elements[-1].get_text(strip=True)
                
                training_data_list.append({
                    'horse_id': horse_id,
                    'training_evaluation': evaluation,
                    'training_total_time': pd.to_numeric(times.get('total_time_str'), errors='coerce'),
                    'training_last_furlong': pd.to_numeric(times.get('last_furlong_str'), errors='coerce')
                })

        except TimeoutException:
            print(f"      警告: 調教ページの読み込みがタイムアウトしました ({race_id})。")
        except Exception as e:
            print(f"      ★★★★★ 調教データ取得中に予期せぬエラー: {e}")
            traceback.print_exc()
            
        return training_data_list

    # --- ★★★ 調教データ特徴量化メソッド (新規追加) ★★★ ---
    def process_training_features(self, training_df):
        """
        調教データのDataFrameから、特徴量を生成する。
        - 評価を数値にマッピング
        - 全体時計、上がりタイムをランク（偏差値）に変換
        """
        if training_df.empty:
            return training_df

        # 評価を数値に変換 (S > A > B > C > D)
        eval_map = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
        training_df['training_eval_score'] = training_df['training_evaluation'].map(eval_map).fillna(2) # 評価なしはC相当

        # 全体時計のランク（速いほど高い値）
        if 'training_total_time' in training_df.columns and training_df['training_total_time'].notna().any():
            training_df['training_time_rank'] = training_df['training_total_time'].rank(method='min', ascending=True, na_option='bottom')
        else:
            training_df['training_time_rank'] = np.nan

        # 上がりタイムのランク（速いほど高い値）
        if 'training_last_furlong' in training_df.columns and training_df['training_last_furlong'].notna().any():
            training_df['training_last_furlong_rank'] = training_df['training_last_furlong'].rank(method='min', ascending=True, na_option='bottom')
        else:
            training_df['training_last_furlong_rank'] = np.nan
            
        return training_df
    
    def calculate_original_index(self, horse_details, race_conditions):
        """
        【特徴量 最終強化版 v2 - タイム指数導入】
        タイム指数に関連する特徴を追加し、予測の精度と差別化を大幅に向上させる。
        """
        # (メソッド前半の特徴量辞書の初期化部分は変更なし)
        features = {
            'horse_id': None, 'Umaban': np.nan, 'Age': np.nan, 'Sex': np.nan, 'Load': np.nan, 
            'JockeyName': '', 'TrainerName': '',
            'father': '', 'mother_father': '', 'NinkiShutuba': np.nan, 'OddsShutuba': np.nan,
            'rank_1ago': np.nan, 'diff_1ago': np.nan, 'agari_1ago': np.nan,
            'rank_2ago': np.nan, 'diff_2ago': np.nan, 'agari_2ago': np.nan,
            'rank_3ago': np.nan, 'diff_3ago': np.nan, 'agari_3ago': np.nan,
            'days_since_last_race': np.nan,
            'Weight': np.nan, 'WeightDiff': np.nan,
            'jockey_win_rate': 0.0, 'jockey_place_rate': 0.0,
            'jockey_recent_win_rate': 0.0, 'jockey_recent_place_rate': 0.0,
            'trainer_win_rate': 0.0, 'trainer_place_rate': 0.0,
            'trainer_recent_win_rate': 0.0, 'trainer_recent_place_rate': 0.0,
            'jockey_horse_win_rate': 0.0, 'jockey_horse_place_rate': 0.0,
            'jockey_track_course_win_rate': 0.0, 'jockey_track_course_place_rate': 0.0,
            'father_track_course_place_rate': 0.0,
            'mother_father_track_course_place_rate': 0.0,
            'same_jockey_last_race': 0,
            'avg_past_race_level': np.nan, 'level_diff_from_avg': np.nan,
            'is_first_time_track': 1, 'is_first_time_distance': 1,
            # ★★★ タイム指数関連の特徴量を追加 ★★★
            'time_deviation_value': np.nan,          # タイム偏差値
            'best_corrected_time_on_course': np.nan, # 同コース最速補正タイム
            'ref_time_diff': np.nan,                 # 基準タイムとの差
            'ref_time_ratio': np.nan,                # 基準タイム比
            'time_dev_x_race_level': np.nan,         # タイム偏差値とレースレベルの交互作用
            'error': None
        }

        if not isinstance(horse_details, dict):
            features['error'] = "horse_details is not a dictionary"; return 0.0, features

        # --- 1. 基本情報とレース条件の抽出 ---
        # (このセクションは変更ありません)
        features['horse_id'] = str(horse_details.get('horse_id')).split('.')[0] if pd.notna(horse_details.get('horse_id')) else None
        features['Umaban'] = pd.to_numeric(horse_details.get('Umaban'), errors='coerce')
        sex_age_str = str(horse_details.get('SexAge', '')).strip()
        if sex_age_str and re.match(r'([牡牝セせん])(\d+)', sex_age_str):
            match = re.match(r'([牡牝セせん])(\d+)', sex_age_str)
            sex_map = {'牡': 0, '牝': 1, 'セ': 2, 'せ': 2, 'ん': 2}
            features['Sex'] = sex_map.get(match.group(1), np.nan)
            features['Age'] = pd.to_numeric(match.group(2), errors='coerce')
        features['Load'] = pd.to_numeric(horse_details.get('Load'), errors='coerce')
        features['JockeyName'] = str(horse_details.get('JockeyName', ''))
        features['TrainerName'] = str(horse_details.get('TrainerName', ''))
        features['father'] = str(horse_details.get('father', ''))
        features['mother_father'] = str(horse_details.get('mother_father', ''))
        features['NinkiShutuba'] = pd.to_numeric(horse_details.get('NinkiShutuba', horse_details.get('Ninki')), errors='coerce')
        features['OddsShutuba'] = pd.to_numeric(horse_details.get('OddsShutuba', horse_details.get('Odds')), errors='coerce')
        
        weight_info = horse_details.get('WeightInfo', horse_details.get('WeightInfoShutuba', ''))
        if isinstance(weight_info, str) and '(' in weight_info:
            weight_match = re.match(r'(\d+)\(([-+]?\d+)\)', weight_info)
            if weight_match:
                features['Weight'] = int(weight_match.group(1))
                features['WeightDiff'] = int(weight_match.group(2))
        elif pd.notna(weight_info):
             features['Weight'] = pd.to_numeric(weight_info, errors='coerce')

        target_course = race_conditions.get('CourseType', '不明')
        target_distance = pd.to_numeric(race_conditions.get('Distance'), errors='coerce')
        target_track = race_conditions.get('TrackName', '不明')
        current_race_date = pd.to_datetime(race_conditions.get('RaceDate'), errors='coerce')
        current_race_level = self._get_race_class_level(str(race_conditions.get('RaceName', '')))
        target_baba = race_conditions.get('baba', '不明')

        # --- 2. 過去戦績データの処理 ---
        past_races_df = pd.DataFrame()
        if 'race_results' in horse_details and isinstance(horse_details['race_results'], list) and horse_details['race_results']:
            past_races_df = pd.DataFrame(horse_details['race_results'])
            past_races_df['date'] = pd.to_datetime(past_races_df['date'], errors='coerce')
            past_races_df = past_races_df.dropna(subset=['date']).sort_values('date', ascending=False)
        
        if not past_races_df.empty:
            for i in range(min(3, len(past_races_df))):
                features[f'rank_{i+1}ago'] = pd.to_numeric(past_races_df.iloc[i].get('rank'), errors='coerce')
                features[f'diff_{i+1}ago'] = pd.to_numeric(past_races_df.iloc[i].get('diff'), errors='coerce')
                features[f'agari_{i+1}ago'] = pd.to_numeric(past_races_df.iloc[i].get('agari'), errors='coerce')
            
            last_race_date = past_races_df.iloc[0]['date']
            if pd.notna(current_race_date) and pd.notna(last_race_date):
                features['days_since_last_race'] = (current_race_date - last_race_date).days
            
            last_jockey = past_races_df.iloc[0].get('jockey')
            if last_jockey and last_jockey == features['JockeyName']:
                features['same_jockey_last_race'] = 1

            if target_track != '不明':
                features['is_first_time_track'] = 1 if target_track not in past_races_df['place'].unique() else 0
            if pd.notna(target_distance):
                past_distances = pd.to_numeric(past_races_df['distance'], errors='coerce')
                features['is_first_time_distance'] = 1 if not (past_distances == target_distance).any() else 0

            if 'race_name' in past_races_df.columns:
                past_races_df['race_level'] = past_races_df['race_name'].apply(self._get_race_class_level)
                features['avg_past_race_level'] = past_races_df['race_level'].mean()
                if pd.notna(features['avg_past_race_level']):
                    features['level_diff_from_avg'] = current_race_level - features['avg_past_race_level']

        # ★★★ 3. タイム指数関連の特徴量計算 ★★★
        try:
            baba_hosei_map = {'芝': {'良': 0.0, '稍重': 0.5, '重': 1.0, '不良': 1.5}, 'ダ': {'良': 0.0, '稍重': -0.3, '重': -0.8, '不良': -1.3}}
            
            best_corrected_time = np.nan
            if not past_races_df.empty and target_course != '不明' and pd.notna(target_distance):
                same_dist_races = past_races_df[pd.to_numeric(past_races_df['distance'], errors='coerce') == target_distance]
                corrected_times = []
                for _, r in same_dist_races.iterrows():
                    time_sec = pd.to_numeric(r.get('time_sec'), errors='coerce')
                    past_course = r.get('course_type')
                    past_baba = r.get('baba')
                    if pd.notna(time_sec) and past_course == target_course and past_baba in baba_hosei_map.get(target_course, {}):
                        hosei = baba_hosei_map[target_course][past_baba]
                        corrected_times.append(time_sec - hosei)
                
                if corrected_times:
                    best_corrected_time = min(corrected_times)
                    features['best_corrected_time_on_course'] = round(best_corrected_time, 2)
            
            if pd.notna(best_corrected_time) and hasattr(self, 'course_time_stats') and target_track != '不明':
                stat_key = (target_track, target_course, int(target_distance))
                course_stats = self.course_time_stats.get(stat_key)
                if course_stats and pd.notna(course_stats.get('mean')) and pd.notna(course_stats.get('std')) and course_stats['std'] > 0:
                    mean_time = course_stats['mean']
                    std_time = course_stats['std']
                    features['time_deviation_value'] = round(50 + 10 * (mean_time - best_corrected_time) / std_time, 2)

            if hasattr(self, 'reference_times'):
                ref_key = (current_race_level, target_track, target_course, int(target_distance))
                ref_time = self.reference_times.get(ref_key)
                if ref_time and pd.notna(best_corrected_time):
                    features['ref_time_diff'] = round(best_corrected_time - ref_time, 2)
                    if ref_time > 0:
                        features['ref_time_ratio'] = round(best_corrected_time / ref_time, 4)

            if pd.notna(features.get('time_deviation_value')) and pd.notna(current_race_level):
                features['time_dev_x_race_level'] = features['time_deviation_value'] * current_race_level

        except Exception as e_time:
            print(f"WARN: タイム指数計算中にエラーが発生しました: {e_time}")

        # --- 4. 騎手・調教師・血統データ ---
        # (このセクションは変更ありません)
        jockey_name = features.get('JockeyName')
        trainer_name = features.get('TrainerName')
        if hasattr(self, 'jockey_stats') and jockey_name in self.jockey_stats:
            features['jockey_win_rate'] = self.jockey_stats[jockey_name].get('win_rate', 0.0)
            features['jockey_place_rate'] = self.jockey_stats[jockey_name].get('place_rate', 0.0)
        if hasattr(self, 'trainer_stats') and trainer_name in self.trainer_stats:
            features['trainer_win_rate'] = self.trainer_stats[trainer_name].get('win_rate', 0.0)
            features['trainer_place_rate'] = self.trainer_stats[trainer_name].get('place_rate', 0.0)
        
        if hasattr(self, 'father_stats') and features['father'] and target_track != '不明' and target_course != '不明':
            sire_stats_father = self.father_stats.get(features['father'], {})
            track_course_key = (target_track, target_course)
            if track_course_key in sire_stats_father:
                features['father_track_course_place_rate'] = sire_stats_father[track_course_key].get('Place3Rate', 0.0)
        
        if hasattr(self, 'mother_father_stats') and features['mother_father'] and target_track != '不明' and target_course != '不明':
            sire_stats_mf = self.mother_father_stats.get(features['mother_father'], {})
            track_course_key_mf = (target_track, target_course)
            if track_course_key_mf in sire_stats_mf:
                features['mother_father_track_course_place_rate'] = sire_stats_mf[track_course_key_mf].get('Place3Rate', 0.0)

        return 0.0, features   
    
    def _calculate_course_time_stats(self):
        """
        【改修版】ペース補正と、より堅牢なエラーハンドリング・ログ出力を備えたタイム統計計算メソッド。
        """
        print("ペース補正付きタイム統計データの計算を開始します...")
        self.update_status("タイム統計データ計算中 (ペース補正)...")
        start_calc_time = time.time()

        self.course_time_stats = {}

        if self.combined_data is None or self.combined_data.empty:
            print("警告: タイム統計計算のためのデータがありません。")
            self.update_status("タイム統計計算不可 (データなし)")
            return

        required_cols = ['track_name', 'course_type', 'distance', 'track_condition', 'Time', 'Rank', 'Passage']
        
        # --- 最初に必要な列が存在するかチェック ---
        missing_cols = [col for col in required_cols if col not in self.combined_data.columns]
        if missing_cols:
            print(f"!!! 重大な警告: タイム統計計算に必要な列が'combined_data'に不足しています: {missing_cols}")
            print("!!!         スクレイピングかデータ整形処理に問題がある可能性があります。")
            self.update_status(f"エラー: タイム統計計算不可 (列不足: {missing_cols})")
            return

        df = self.combined_data[required_cols].copy()
        
        # --- データの前処理と型変換 ---
        print(f"  STEP 1: データ前処理開始 (元データ: {len(df)}行)")
        df.dropna(subset=required_cols, inplace=True)
        print(f"  ...欠損行を除去後: {len(df)}行")
        
        df['time_sec_numeric'] = df['Time'].apply(self._time_str_to_sec)
        df['distance_numeric'] = pd.to_numeric(df['distance'], errors='coerce')
        df['Rank_numeric'] = pd.to_numeric(df['Rank'], errors='coerce')
        
        df.dropna(subset=['time_sec_numeric', 'distance_numeric', 'Rank_numeric'], inplace=True)
        print(f"  ...数値変換不能な行を除去後: {len(df)}行")

        if df.empty:
            print("警告: タイム統計計算の対象となる有効なデータがありません。")
            self.update_status("タイム統計計算不可 (有効データなし)")
            return
            
        df['distance_numeric'] = df['distance_numeric'].astype(int)
        df['Rank_numeric'] = df['Rank_numeric'].astype(int)
        df['track_name'] = df['track_name'].astype(str).str.strip()
        df['course_type'] = df['course_type'].astype(str).str.strip()
        df['baba'] = df['track_condition'].astype(str).str.strip()
        df['Passage_str'] = df['Passage'].astype(str)

        # --- 馬場状態によるタイム補正 ---
        print("  STEP 2: 馬場状態によるタイム補正を実行")
        baba_hosei = {'芝': {'良': 0.0, '稍重': 0.5, '重': 1.0, '不良': 1.5}, 'ダ': {'良': 0.0, '稍重': -0.3, '重': -0.8, '不良': -1.3}}
        df['hosei_value'] = df.apply(lambda row: baba_hosei.get(row['course_type'], {}).get(row['baba'], 0.0), axis=1)
        df['corrected_time_sec'] = df['time_sec_numeric'] - df['hosei_value']

        # --- レースペース指数の計算 ---
        print("  STEP 3: レースペース指数を計算")
        def calculate_pace_index(passage_str):
            try:
                positions = [int(p) for p in passage_str.split('-')]
                first_half_positions = positions[:len(positions)//2] if len(positions) > 1 else positions
                return np.mean(first_half_positions) if first_half_positions else np.nan
            except:
                return np.nan
        df['PaceIndex'] = df['Passage_str'].apply(calculate_pace_index)

        df_filtered = df[df['Rank_numeric'] <= 5].copy()
        df_filtered.dropna(subset=['PaceIndex'], inplace=True) # ペース指数を計算できたデータのみ対象
        print(f"  ...上位5着以内で、ペース指数が計算可能なデータに絞り込み: {len(df_filtered)}行")

        if df_filtered.empty:
            print("警告: ペース補正タイムの計算対象となるデータがありません。")
            self.update_status("タイム統計計算不可 (ペースデータ不足)")
            return

        # --- コース毎の平均ペースを計算し、ペース差によるタイム補正を実行 ---
        print("  STEP 4: ペース差によるタイム補正を実行")
        course_avg_pace = df_filtered.groupby(['track_name', 'course_type', 'distance_numeric'])['PaceIndex'].transform('mean')
        df_filtered['PaceDiff'] = course_avg_pace - df_filtered['PaceIndex']
        
        pace_correction_factor = 0.1
        df_filtered['pace_time_correction'] = df_filtered['PaceDiff'] * pace_correction_factor
        df_filtered['final_corrected_time'] = df_filtered['corrected_time_sec'] + df_filtered['pace_time_correction']

        # --- 最終的な統計量の計算 ---
        print("  STEP 5: 最終的な統計量を計算")
        try:
            stats = df_filtered.groupby(['track_name', 'course_type', 'distance_numeric'])['final_corrected_time'].agg(
                mean='mean', std='std', count='size'
            ).reset_index()
            
            stats['std_revised'] = stats.apply(lambda x: x['std'] if pd.notna(x['std']) and x['std'] > 0 and x['count'] >= 10 else np.nan, axis=1)

            for _, row in stats.iterrows():
                key = (str(row['track_name']), str(row['course_type']), int(row['distance_numeric']))
                self.course_time_stats[key] = {'mean': row['mean'], 'std': row['std_revised'], 'count': int(row['count'])}

            end_calc_time = time.time()
            print(f"タイム統計データ(ペース補正版)の計算完了。{len(self.course_time_stats)} 件生成。({end_calc_time - start_calc_time:.2f}秒)")
            self.update_status("タイム統計データ準備完了 (ペース補正済)")

        except Exception as e:
            print(f"!!! 最終統計計算中にエラー: {e}")
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
    
    # --- ★★★ 騎手・調教師成績集計メソッド (新規追加) ★★★ ---
    def _calculate_jockey_trainer_stats(self):
        """
        読み込んだデータ全体から、騎手ごと、調教師ごとの成績（勝率・複勝率）を
        集計し、クラス変数に格納する。
        """
        print("騎手・調教師別の成績データを計算中...")
        self.update_status("騎手・調教師成績を計算中...")

        self.jockey_stats = {}
        self.trainer_stats = {}

        if self.combined_data is None or self.combined_data.empty:
            print("警告: 騎手・調教師の成績計算のためのデータがありません。")
            return

        required_cols = ['JockeyName', 'TrainerName', 'Rank']
        if not all(col in self.combined_data.columns for col in required_cols):
            missing = [c for c in required_cols if c not in self.combined_data.columns]
            print(f"警告: 成績計算に必要な列が不足しています: {missing}")
            return

        df = self.combined_data.copy()
        df.dropna(subset=required_cols, inplace=True)
        df['Rank_num'] = pd.to_numeric(df['Rank'], errors='coerce')
        df.dropna(subset=['Rank_num'], inplace=True)

        # 騎手成績の集計
        jockey_agg = df.groupby('JockeyName').agg(
            Runs=('Rank_num', 'size'),
            Wins=('Rank_num', lambda x: (x == 1).sum()),
            Places=('Rank_num', lambda x: (x <= 3).sum())
        )
        jockey_agg['win_rate'] = jockey_agg['Wins'] / jockey_agg['Runs']
        jockey_agg['place_rate'] = jockey_agg['Places'] / jockey_agg['Runs']
        self.jockey_stats = jockey_agg.to_dict('index')

        # 調教師成績の集計
        trainer_agg = df.groupby('TrainerName').agg(
            Runs=('Rank_num', 'size'),
            Wins=('Rank_num', lambda x: (x == 1).sum()),
            Places=('Rank_num', lambda x: (x <= 3).sum())
        )
        trainer_agg['win_rate'] = trainer_agg['Wins'] / trainer_agg['Runs']
        trainer_agg['place_rate'] = trainer_agg['Places'] / trainer_agg['Runs']
        self.trainer_stats = trainer_agg.to_dict('index')

        print(f"騎手データ: {len(self.jockey_stats)}件, 調教師データ: {len(self.trainer_stats)}件 の集計が完了しました。")
    
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
   
    # --- ★★★ モデル読み込みメソッド (解説器の読み込みを追加した最終FIX版) ★★★ ---
    def load_model_from_file(self, model_filename="trained_lgbm_model.pkl", features_filename="model_features.pkl"):
        """
        指定されたファイルから学習済みモデルと特徴量リストを読み込み、
        self.trained_model と self.model_features を初期化する。
        ★★★ 修正点: SHAP解説器(shap_explainer.pkl)も一緒に読み込むように修正。 ★★★
        """
        import os
        
        # --- モデル、特徴量、解説器の保存先ディレクトリを取得 ---
        model_load_dir = self.settings.get("models_dir", self.settings.get("data_dir", os.path.join(self.app_data_dir, "models")))

        # --- 1. 学習済みモデルの読み込み ---
        model_filepath = os.path.join(model_load_dir, model_filename)
        print(f"INFO: Loading trained model from: {model_filepath}")
        loaded_model = self._load_pickle(model_filepath)
        if loaded_model is not None:
            self.trained_model = loaded_model
            print(f"INFO: Successfully loaded trained model: {model_filepath}")
        else:
            self.trained_model = None
            print(f"WARN: Failed to load trained model or file not found: {model_filepath}")

        # --- 2. 特徴量リストの読み込み ---
        features_filepath = os.path.join(model_load_dir, features_filename)
        print(f"INFO: Loading model features from: {features_filepath}")
        loaded_features = self._load_pickle(features_filepath)
        if loaded_features is not None and isinstance(loaded_features, list):
            self.model_features = loaded_features
            print(f"INFO: Successfully loaded model features ({len(self.model_features)} features): {features_filepath}")
        else:
            self.model_features = []
            print(f"WARN: Failed to load model features or file not found: {features_filepath}.")

        # ★★★ 3. SHAP解説器の読み込み (ここが最重要修正点) ★★★
        explainer_filename = "shap_explainer.pkl" # 解説器のファイル名
        explainer_filepath = self.settings.get("shap_explainer_path", os.path.join(model_load_dir, explainer_filename))
        print(f"INFO: Loading SHAP explainer from: {explainer_filepath}")
        loaded_explainer = self._load_pickle(explainer_filepath)
        if loaded_explainer is not None:
            self.shap_explainer = loaded_explainer
            print(f"INFO: Successfully loaded SHAP explainer: {explainer_filepath}")
        else:
            self.shap_explainer = None
            print(f"WARN: Failed to load SHAP explainer or file not found: {explainer_filepath}")

        # --- 最終的なステータス表示 ---
        if self.trained_model and self.model_features and self.shap_explainer:
             self.update_status(f"学習済みモデル、特徴量、解説器をロードしました。")
        elif self.trained_model:
             self.update_status(f"学習済みモデルはロードしましたが、特徴量または解説器がありません。")
        else:
             self.update_status("学習済みモデルのロードに失敗しました。")
    
    def format_result_data(self, results_list_of_dicts, race_id):
        """
        【最終改修版】辞書のリストからDataFrameを整形する。
        """
        if not results_list_of_dicts:
            return None
            
        try:
            df = pd.DataFrame(results_list_of_dicts)

            if 'HorseName_url' in df.columns:
                df['horse_id'] = df['HorseName_url'].astype(str).str.extract(r'/horse/(\d+)')

            # 列名統一マップ
            rename_map = {
                '着順': 'Rank', '枠': 'Waku', '馬番': 'Umaban', '馬名': 'HorseName',
                '性齢': 'SexAge', '斤量': 'Load', '騎手': 'JockeyName', 'タイム': 'Time',
                '着差': 'Diff', 'ﾀｲﾑ指数': 'TimeIndex', '通過': 'Passage', 'コーナー通過順': 'Passage',
                '上がり': 'Agari', '上り': 'Agari', '後3F': 'Agari',
                '単勝': 'Odds', '人気': 'Ninki', '馬体重': 'WeightInfo',
                '調教師': 'TrainerName', '厩舎': 'TrainerName'
            }
            df.rename(columns=lambda x: rename_map.get(x.strip(), x.strip()), inplace=True)

            df['race_id'] = race_id
            
            # --- 型変換処理 (存在しない列があってもエラーにならないように) ---
            numeric_cols = ['Rank', 'Waku', 'Umaban', 'Load', 'Ninki', 'Odds', 'Agari', 'TimeIndex']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            if 'WeightInfo' in df.columns:
                df['Weight'] = df['WeightInfo'].str.extract(r'(\d+)', expand=False)
                df['WeightDiff'] = df['WeightInfo'].str.extract(r'\(([-+]?\d+)\)', expand=False)
                df['Weight'] = pd.to_numeric(df['Weight'], errors='coerce')
                df['WeightDiff'] = pd.to_numeric(df['WeightDiff'], errors='coerce')

            if 'SexAge' in df.columns:
                 df['Sex'] = df['SexAge'].str[0]
                 df['Age'] = pd.to_numeric(df['SexAge'].str[1:], errors='coerce')

            return df

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
    
    def _prepare_data_for_model(self, data_df, target_column='is_within_3rd', is_prediction=False):
        """
        【再修正版】モデル学習/予測のためのデータを準備する。
        先に正解ラベルを分離し、後から特徴量とインデックスを合わせる方式に変更。
        """
        if data_df is None or data_df.empty:
            print("ERROR: _prepare_data_for_model に渡されたデータが空です。")
            return None, None

        print("モデル学習用のデータ準備を開始します (calculate_original_index を使用)...")
        
        # 先に正解ラベル(y)を分離しておく
        if not is_prediction:
            if target_column not in data_df.columns:
                print(f"ERROR: ターゲット列 '{target_column}' がデータに存在しません。")
                return None, None
            y = data_df[target_column].copy()
        else:
            y = None

        all_features_list = []
        total_races = data_df['race_id'].nunique()
        processed_races = 0

        # DataFrameをレースごとにグループ化してループ
        for race_id, race_df_group in data_df.groupby('race_id'):
            processed_races += 1
            if processed_races % 100 == 0:
                print(f"  特徴量計算中... ({processed_races}/{total_races})")

            race_info_row = race_df_group.iloc[0]
            race_conditions = {
                'race_id': race_id,
                'RaceName': race_info_row.get('race_name'),
                'RaceDate': pd.to_datetime(race_info_row.get('date'), errors='coerce'),
                'TrackName': race_info_row.get('track_name'),
                'CourseType': race_info_row.get('course_type'),
                'Distance': race_info_row.get('distance'),
                'Weather': race_info_row.get('weather'),
                'TrackCondition': race_info_row.get('track_condition'),
                'baba': race_info_row.get('track_condition')
            }

            for index, horse_row in race_df_group.iterrows():
                horse_details = horse_row.to_dict()
                horse_id_str = str(horse_details.get('horse_id', '')).split('.')[0]
                
                if horse_id_str and horse_id_str in self.horse_details_cache:
                    horse_details['race_results'] = self.horse_details_cache[horse_id_str].get('race_results', [])
                else:
                    horse_details['race_results'] = []

                _, features_dict = self.calculate_original_index(horse_details, race_conditions)
                
                # 元のDataFrameのインデックスを保持しておく
                features_dict['original_index'] = index
                all_features_list.append(features_dict)

        if not all_features_list:
            print("ERROR: 特徴量リストが空です。")
            return None, None
            
        # 特徴量データフレームを作成
        X = pd.DataFrame(all_features_list)
        X = X.set_index('original_index')
        X = X.drop(columns=['error'], errors='ignore')

        print("特徴量の計算が完了しました。")
        
        # 訓練時のみ、特徴量(X)のインデックスに正解ラベル(y)を合わせる
        if not is_prediction and y is not None:
            # y と X のインデックスを合わせる
            y = y.loc[X.index]
            # NaNが含まれる行を削除
            y = y.dropna()
            X = X.loc[y.index]

        return X, y
    
    def train_and_evaluate_model(self, df):
        """
        【同期修正版】データの前処理、モデルの学習、評価、保存を行う。
        予測時と完全に同じ特徴量エンジニアリングを保証する。
        """
        try:
            self.update_status("モデル学習を開始します...")
            print("INFO: モデル学習プロセス開始。")

            target = 'rank_binary'
            COLS_TO_DROP = ['rank_binary', 'horse_id', 'JockeyName', 'TrainerName', 'father', 'mother_father']
            CATEGORICAL_FEATURES = ['prev_race_track_type_1ago']

            df_model = df.drop(columns=[col for col in COLS_TO_DROP if col in df.columns and col != target], errors='ignore')

            for col in CATEGORICAL_FEATURES:
                if col in df_model.columns:
                    df_model[col] = df_model[col].astype('category')

            df_processed = pd.get_dummies(df_model, columns=CATEGORICAL_FEATURES, dummy_na=True)

            X = df_processed.drop(columns=[target])
            y = df_processed[target]

            self.imputation_values_ = X.median()
            X = X.fillna(self.imputation_values_)

            self.model_features = X.columns.tolist()
            print(f"INFO: 学習に使用する特徴量の数: {len(self.model_features)}")

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

            self.update_status("LightGBMモデルの学習中...")
            model = lgb.LGBMClassifier(random_state=42)
            model.fit(X_train, y_train)
            self.trained_model = model
            print("INFO: モデル学習完了！")

            y_pred_proba = model.predict_proba(X_test)[:, 1]
            auc = roc_auc_score(y_test, y_pred_proba)
            logloss = log_loss(y_test, y_pred_proba)
            self.update_status(f"学習完了！ AUC: {auc:.4f}, LogLoss: {logloss:.4f}")
            print(f"AUC Score: {auc:.4f}\nLog Loss: {logloss:.4f}")

            with open(self.MODEL_PATH, 'wb') as f:
                pickle.dump(model, f)
            with open(self.FEATURES_PATH, 'wb') as f:
                pickle.dump(self.model_features, f)
            with open(self.IMPUTATION_PATH, 'wb') as f:
                pickle.dump(self.imputation_values_, f)

            print(f"INFO: 学習済みモデル等を {self.MODEL_DIR} に保存しました。")
            self.load_model_and_features(force_reload=True)
            self.root.after(0, lambda: messagebox.showinfo("完了", "モデルの学習が完了しました。"))
            return True

        except Exception as e:
            print(f"!!! モデル学習中にエラーが発生: {e}")
            traceback.print_exc()
            self.root.after(0, lambda err=e: messagebox.showerror("エラー", f"モデル学習中にエラーが発生しました:\n{err}"))
            self.update_status(f"エラー: {e}")
            return False
        
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
        【最終修正版】モデル学習のメインスレッド。
        修正されたupdate_status関数と正しく連携する。
        """
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score, log_loss
        import lightgbm as lgb
        import shap
        
        try:
            self.update_status("データ準備を開始します。", clear_log=True)
            print("INFO: _run_training_pipeline_thread: データ準備を開始します。")

            if self.processed_data is None:
                print("ERROR: self.processed_dataが空のため、学習を開始できません。")
                self.update_status("エラー: 学習データがありません。", is_error=True)
                return

            target_data_df = self.processed_data.copy()
            if 'Rank' in target_data_df.columns:
                 target_data_df['is_within_3rd'] = (target_data_df['Rank'] <= 3).astype(int)
            else:
                print("ERROR: 目的変数 'Rank' がデータに存在しません。")
                self.update_status("エラー: 'Rank'列がありません。", is_error=True)
                return
            
            X, y = self._prepare_data_for_model(data_df=target_data_df, is_prediction=False)

            if X is None or y is None or X.empty or y.empty:
                print("ERROR: _run_training_pipeline_thread: _prepare_data_for_model が有効なデータを返しませんでした。")
                self.update_status("エラー: モデル学習用のデータ準備に失敗しました。", is_error=True)
                return
            
            cols_to_drop_before_training = ['horse_id', 'JockeyName', 'TrainerName', 'father', 'mother_father', 'HorseName']
            existing_cols_to_drop = [col for col in cols_to_drop_before_training if col in X.columns]
            if existing_cols_to_drop:
                X = X.drop(columns=existing_cols_to_drop)
                print(f"INFO: モデル学習から以下の文字列カラムを除外しました: {existing_cols_to_drop}")
            
            self.update_status(f"データ準備完了。特徴量: {X.shape[1]}、データ数: {X.shape[0]}。モデル学習を開始します...")

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

            self.imputation_values = X_train.select_dtypes(include=np.number).median()
            X_train = X_train.fillna(self.imputation_values)
            X_test = X_test.fillna(self.imputation_values)

            self.model = lgb.LGBMClassifier(random_state=42)
            self.model.fit(X_train, y_train)
            self.model_features = X.columns.tolist()
            
            self.update_status("モデル学習完了。評価を開始します...")

            y_pred_proba = self.model.predict_proba(X_test)[:, 1]
            auc_score = roc_auc_score(y_test, y_pred_proba)
            logloss = log_loss(y_test, y_pred_proba)
            
            result_message = f"学習完了！\nAUC Score: {auc_score:.4f}\nLog Loss: {logloss:.4f}"
            print(result_message)
            self.update_status(result_message)

            self.save_model_to_file()

            self.update_status("SHAPの計算を開始します...")
            self.explainer = shap.TreeExplainer(self.model)
            self.shap_values = self.explainer.shap_values(X_test)
            self.update_status("SHAPの計算完了。モデルが利用可能です。")
            
            self.update_status("キャリブレーションプロットを生成中...")
            self.plot_calibration_curve(y_test, y_pred_proba)
            self.update_status("キャリブレーションプロット生成完了。")

        except Exception as e:
            error_msg = f"!!! FATAL ERROR in _run_training_pipeline_thread !!!\n{traceback.format_exc()}"
            print(error_msg)
            self.update_status(f"致命的なエラー: {e}", is_error=True)
    
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
                            converted_dates = pd.to_datetime(df_combined[col], format='%Y年%m月%d日', errors='coerce')
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
                self._calculate_jockey_trainer_stats()
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
                 self._calculate_jockey_trainer_stats()
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

        # === 右側のフレーム（分析結果） ===
        right_frame = ttk.Frame(self.tab_analysis)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- テーブル表示エリア ---
        analysis_table_frame = ttk.LabelFrame(right_frame, text="分析結果テーブル")
        analysis_table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        y_scrollbar = ttk.Scrollbar(analysis_table_frame, orient=tk.VERTICAL)
        y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        x_scrollbar = ttk.Scrollbar(analysis_table_frame, orient=tk.HORIZONTAL)
        x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        self.analysis_tree = ttk.Treeview(analysis_table_frame,
                                           yscrollcommand=y_scrollbar.set,
                                           xscrollcommand=x_scrollbar.set,
                                           height=8) # 高さを少し調整
        self.analysis_tree.pack(fill=tk.BOTH, expand=True)
        y_scrollbar.config(command=self.analysis_tree.yview)
        x_scrollbar.config(command=self.analysis_tree.xview)
        
        self.analysis_graph_frame = ttk.LabelFrame(right_frame, text="グラフ表示")
        self.analysis_graph_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.analysis_figure = plt.Figure(figsize=(5, 4), dpi=100)
        self.analysis_canvas = FigureCanvasTkAgg(self.analysis_figure, master=self.analysis_graph_frame)
        self.analysis_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)

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
    
    def update_status(self, message, is_error=False, clear_log=False):
        """
        【改修版】ステータスバーとログエリアを更新する。
        エラー時の色変更とログクリア機能を追加。
        """
        def task():
            # ステータスバーの更新
            self.status_var.set(message)
            
            # ログエリアの更新
            if hasattr(self, 'log_text') and self.log_text:
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_message = f"[{current_time}] {message}\n"
                
                # ログのクリア
                if clear_log:
                    self.log_text.delete('1.0', tk.END)

                # エラー時の色変更
                if is_error:
                    # 'error' タグがなければ作成
                    if 'error' not in self.log_text.tag_names():
                        self.log_text.tag_config('error', foreground='red')
                    self.log_text.insert(tk.END, log_message, 'error')
                else:
                    self.log_text.insert(tk.END, log_message)
                
                self.log_text.see(tk.END) # 自動スクロール
            
            self.root.update_idletasks()

        if hasattr(self, 'root') and self.root:
            self.root.after(0, task)

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

    def run_prediction(self):
        """
        「予測実行」ボタンが押されたときに呼び出される。
        入力されたレースIDを取得し、予測スレッドを開始する。
        """
        import threading
        from tkinter import messagebox

        race_id = self.race_id_entry.get().strip()
        if not race_id:
            messagebox.showwarning("入力エラー", "レースIDを入力してください。")
            return
        
        if not race_id.isdigit():
            messagebox.showwarning("入力エラー", "レースIDは数字で入力してください。")
            return

        # 予測処理を別スレッドで実行してUIのフリーズを防ぐ
        thread = threading.Thread(target=self._fetch_race_info_thread, args=(race_id,))
        thread.daemon = True
        thread.start()

    def save_prediction_result(self):
        """
        「予測結果を保存」ボタンが押されたときに呼び出される。
        表示されている予測結果をCSVファイルに保存する。
        """
        import pandas as pd
        from tkinter import filedialog, messagebox
        import os

        if not hasattr(self, 'prediction_results_data') or not self.prediction_results_data:
            messagebox.showinfo("保存エラー", "保存する予測結果がありません。")
            return
        
        try:
            # 現在のレース情報をファイル名に使用
            race_info = self.race_info_label.cget("text").replace(" ", "_").replace(":", "")
            initial_filename = f"{race_info}_prediction.csv"

            # 保存ダイアログを開く
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSVファイル", "*.csv")],
                initialfile=initial_filename,
                title="予測結果を保存"
            )

            if filepath:
                df_to_save = pd.DataFrame(self.prediction_results_data)
                df_to_save.to_csv(filepath, index=False, encoding='utf-8-sig')
                messagebox.showinfo("保存完了", f"予測結果を以下のファイルに保存しました:\n{os.path.basename(filepath)}")
                self.update_status(f"予測結果を {os.path.basename(filepath)} に保存しました。")

        except Exception as e:
            messagebox.showerror("保存エラー", f"ファイルの保存中にエラーが発生しました:\n{e}")

    def run_result_analysis(self):
        """
        「バックテスト実行」ボタンが押されたときに呼び出される。
        （現在は未実装のため、メッセージのみ表示）
        """
        from tkinter import messagebox
        messagebox.showinfo("未実装", "この機能は現在実装されていません。")
        print("INFO: バックテスト機能は未実装です。")
    
    def _fetch_race_info_thread(self, race_id):
        driver = None
        try:
            self.root.after(0, lambda: self.update_status(f"レースID {race_id}: 予測処理準備中..."))
            
            options = webdriver.ChromeOptions()
            options.page_load_strategy = 'eager'
            options.add_argument(f'--user-agent={self.USER_AGENT}')
            options.add_argument('--headless')
            options.add_argument('--disable-gpu'); options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage'); options.add_argument("--log-level=3")
            options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])
            
            if self.CHROME_DRIVER_PATH and os.path.exists(self.CHROME_DRIVER_PATH):
                service = ChromeService(executable_path=self.CHROME_DRIVER_PATH)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                driver = webdriver.Chrome(options=options)
            
            if not all(hasattr(self, attr) and getattr(self, attr) for attr in ['trained_model', 'model_features']):
                self.root.after(0, lambda: messagebox.showwarning("モデル未ロード", "モデルが読み込まれていません。\nデータ管理タブでモデルを再学習してください。"))
                return

            web_data = self.get_shutuba_table(race_id, driver)
            if not (web_data and web_data.get('horse_list')):
                self.root.after(0, lambda: messagebox.showerror("情報取得エラー", "出走馬情報を取得できませんでした。"))
                return
            
            race_df = pd.DataFrame(web_data['horse_list'])
            race_conditions = web_data.get('race_details', {})
            race_conditions['RaceDate'] = pd.to_datetime(race_conditions.get('RaceDate'), format='%Y年%m月%d日', errors='coerce')
            
            final_gui_list = []
            for index, row_from_racedf in race_df.iterrows():
                umaban = row_from_racedf.get('Umaban'); horse_name = row_from_racedf.get('HorseName')
                self.root.after(0, lambda u=umaban, n=horse_name, i=index+1, t=len(race_df): self.update_status(f"予測中 ({i}/{t}): {u}番 {n}"))

                gui_info = { 'Umaban': umaban, 'HorseName': horse_name, 'SexAge': row_from_racedf.get('SexAge'), 'Load': row_from_racedf.get('Load'), 'JockeyName': row_from_racedf.get('JockeyName'), 'Odds': row_from_racedf.get('Odds'), '近3走': "データ無", '予測確率': None, 'shap_summary': "N/A", 'error_detail': None }
                
                horse_id_str = str(row_from_racedf.get('horse_id', '')).strip().split('.')[0]
                if not horse_id_str:
                    gui_info['error_detail'] = "馬IDなし"; final_gui_list.append(gui_info); continue

                horse_full_details = self.horse_details_cache.get(horse_id_str, {})
                
                horse_basic_info = dict(row_from_racedf)
                horse_basic_info.update(horse_full_details)
                
                _, features_dict = self.calculate_original_index(horse_basic_info, race_conditions)
                
                if features_dict.get('error'):
                    gui_info['error_detail'] = "特徴量計算エラー"
                else:
                    try:
                        X_pred_raw = pd.DataFrame([features_dict])
                        CATEGORICAL_FEATURES = ['prev_race_track_type_1ago']
                        for col in CATEGORICAL_FEATURES:
                            if col in X_pred_raw.columns:
                                X_pred_raw[col] = X_pred_raw[col].astype('category')
                        
                        X_pred_dummies = pd.get_dummies(X_pred_raw, columns=CATEGORICAL_FEATURES, dummy_na=True)
                        X_pred_aligned = X_pred_dummies.reindex(columns=self.model_features, fill_value=0)
                        X_pred_filled = X_pred_aligned.fillna(self.imputation_values_)
                        X_pred_final = X_pred_filled.fillna(0)

                        if X_pred_final.shape[1] != len(self.model_features):
                            raise RuntimeError(f"最終特徴量数が不一致です。予測: {X_pred_final.shape[1]}, 学習: {len(self.model_features)}")

                        gui_info['予測確率'] = self.trained_model.predict_proba(X_pred_final)[0, 1]

                        if self.shap_explainer:
                            shap_values = self.shap_explainer.shap_values(X_pred_final)
                            shap_values_for_class1 = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]
                            shap_df = pd.DataFrame({'feature': X_pred_final.columns, 'shap_value': shap_values_for_class1})
                            top_pos = shap_df[shap_df['shap_value'] > 0].nlargest(3, 'shap_value')
                            top_neg = shap_df[shap_df['shap_value'] < 0].nsmallest(3, 'shap_value')
                            pos_str = ", ".join([f"{r.feature}({r.shap_value:+.2f})" for r in top_pos.itertuples()])
                            neg_str = ", ".join([f"{r.feature}({r.shap_value:+.2f})" for r in top_neg.itertuples()])
                            gui_info['shap_summary'] = f"〇 {pos_str}\n× {neg_str}"
                            
                    except Exception as e:
                        print(f"!!! 予測計算中にエラーが発生 (馬番: {umaban}): {e}")
                        traceback.print_exc()
                        gui_info['error_detail'] = f"予測エラー: {type(e).__name__}"
                
                final_gui_list.append(gui_info)

            self.prediction_results_data = sorted(final_gui_list, key=lambda x: x.get('予測確率') or -1, reverse=True)
            self.root.after(0, lambda: self._update_prediction_table(self.prediction_results_data))
            self.root.after(0, lambda: self.update_status(f"予測完了: {race_id}"))

        except Exception as e_main_fetch:
            traceback.print_exc()
            self.root.after(0, lambda err=e_main_fetch: messagebox.showerror("予測処理エラー", f"予期せぬエラーが発生しました:\n{err}"))
        finally:
            if driver:
                try: driver.quit()
                except Exception: pass

    def _update_prediction_table(self, data):
        """予測結果テーブルを更新する"""
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        for item in data:
            prob = item.get('予測確率')
            prob_str = f"{prob:.1%}" if prob is not None else "N/A"
            
            values = (
                item.get('Umaban', ''),
                item.get('HorseName', ''),
                item.get('SexAge', ''),
                item.get('Load', ''),
                item.get('JockeyName', ''),
                item.get('Popular', ''),
                item.get('Odds', ''),
                item.get('近3走', ''),
                prob_str,
                item.get('shap_summary', 'N/A')
            )
            self.tree.insert('', 'end', values=values)
    
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
    
    # --- ★★★ 設定ファイル読み込みメソッド (最終FIX版) ★★★ ---
    def load_settings(self):
        """設定ファイルの読み込み"""
        defaults = self.get_default_settings()
        # ★★★ 修正点: まずデフォルトを読み込み、ファイルの内容で上書きする方式に変更 ★★★
        self.settings = defaults.copy() 

        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    loaded_settings = json.load(f)
                    # ファイルから読み込んだ設定で、デフォルト値を上書き
                    self.settings.update(loaded_settings)
                print("設定ファイルを読み込みました:", self.settings_file)
            except json.JSONDecodeError:
                 messagebox.showerror("設定エラー", f"設定ファイル ({self.settings_file}) が破損しています。デフォルト設定を使用します。")
            except Exception as e:
                 messagebox.showwarning("設定読み込みエラー", f"設定ファイルの読み込み中にエラーが発生しました: {e}\nデフォルト設定を使用します。")
        else:
            print("設定ファイルが見つからないため、デフォルト設定を使用します。")

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
    
    # ▼▼▼ plot_calibration_curve をこのコードに丸ごと置き換え ▼▼▼
    def plot_calibration_curve(self, y_true, y_prob):
        """
        【修正版】キャリブレーションプロットを、分析タブの既存のキャンバスに描画する。
        """
        try:
            from sklearn.calibration import calibration_curve
            
            # 既存のFigureをクリア
            self.analysis_figure.clear()
            
            # 新しいプロットを追加
            ax = self.analysis_figure.add_subplot(111)
            prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=10, strategy='uniform')
            
            ax.plot(prob_pred, prob_true, marker='o', linewidth=1, label='LightGBM')
            ax.plot([0, 1], [0, 1], linestyle='--', color='gray', label='Perfectly calibrated')
            
            ax.set_xlabel("Mean predicted probability")
            ax.set_ylabel("Fraction of positives")
            ax.set_title("Calibration plot")
            ax.legend()
            ax.grid(True)
            
            self.analysis_figure.tight_layout()
            
            # 既存のキャンバスを再描画
            self.analysis_canvas.draw()

        except ImportError:
            self.update_status("エラー: scikit-learnが必要です。", is_error=True)
            print("ERROR: scikit-learn is not installed. Please install it using 'pip install scikit-learn'")
        except Exception as e:
            self.update_status(f"キャリブレーションプロット作成エラー: {e}", is_error=True)
            print(f"!!! ERROR in plot_calibration_curve: {e}")
            traceback.print_exc()
   
def main():
    root = tk.Tk()
    # DPIスケーリング対応 (Windows)
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1) # DPI Awareに設定
    except Exception as e:
        print(f"DPIスケーリング設定に失敗しました: {e}", file=sys.stderr)

    app = HorseRacingAnalyzerApp(root)
    root.mainloop()

if __name__ == "__main__":
    # スクリプトが直接実行された場合にmain関数を呼び出す
    main()