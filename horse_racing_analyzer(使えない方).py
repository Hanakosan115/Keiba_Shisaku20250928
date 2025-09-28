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
    
    # --- JRA競馬場リスト (クラス変数として定義しておくと便利) ---
    JRA_TRACKS = ["札幌", "函館", "福島", "新潟", "東京", "中山", "中京", "京都", "阪神", "小倉"]
    
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
        # models_dir を使うのが適切か、data_dir を使うか、設定に合わせる
        # ここでは settings から "models_dir" を参照し、なければ "data_dir"、それもなければ app_data_dir/models を使う
        models_base_dir = self.settings.get("models_dir", self.settings.get("data_dir", os.path.join(self.app_data_dir, "models")))
        default_imputation_path = os.path.join(models_base_dir, imputation_values_default_filename)
        
        imputation_values_path = self.settings.get("imputation_values_path", default_imputation_path) # 設定ファイルにパスがあればそれを使う
        
        loaded_imputation_values = self._load_pickle(imputation_values_path) # _load_pickle は既存のメソッドを想定
        if loaded_imputation_values is not None and isinstance(loaded_imputation_values, dict):
            self.imputation_values_ = loaded_imputation_values
            print(f"INFO: 欠損値補完のための値をロードしました: {imputation_values_path} ({len(self.imputation_values_)} 列分)")
        else:
            # self.imputation_values_ は既に {} で初期化されているので、ここではログ出力のみでOK
            print(f"INFO: 欠損値補完ファイルが見つからないかロードに失敗 ({imputation_values_path})。学習時に新規作成されます。")

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
    
    # horse_racing_analyzer.py 内の get_pay_table メソッドをこれで完全に置き換えてください
    def get_pay_table(self, race_id):
        """
        払い戻しテーブルデータをリストのリストで取得 (最終修正版)
        2017年の <dl class="pay_block"> 形式と、それ以降の形式に両対応する。
        """
        # db.netkeiba.com が最も情報が安定しているため、URLを固定
        url = f'https://db.netkeiba.com/race/{race_id}/'
        self.update_status(f"払戻取得試行: {race_id}")
        print(f"      払戻取得試行: {url}")
        headers = {'User-Agent': self.USER_AGENT}
        
        try:
            time.sleep(self.SLEEP_TIME_PER_PAGE) # サイト負荷軽減
            r = requests.get(url, headers=headers, timeout=self.REQUEST_TIMEOUT)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.content, 'lxml')
            
            payout_area = None
            
            # 払い戻し情報が含まれる可能性のあるエリアを、最も確実な順に探す
            # 1. <dl class="pay_block"> (2017年頃の形式)
            payout_area = soup.select_one('dl.pay_block')
            if payout_area:
                 print(f"        情報: 払い戻しエリアをセレクタ 'dl.pay_block' で発見。")
            
            # 2. <div class="Result_Pay_Back"> (比較的新しい形式)
            if not payout_area:
                payout_area = soup.select_one('div.Result_Pay_Back')
                if payout_area:
                    print(f"        情報: 払い戻しエリアをセレクタ 'div.Result_Pay_Back' で発見。")
            
            # 3. その他のフォールバック (div.payout_block など)
            if not payout_area:
                payout_area = soup.select_one('div.payout_block')
                if payout_area:
                     print(f"        情報: 払い戻しエリアをセレクタ 'div.payout_block' で発見。")


            if not payout_area:
                if soup.find(string=re.compile("出走取消|開催中止")):
                    print(f"        情報: 払い戻しが存在しないようです（取消/中止など） ({race_id})")
                else:
                    self.update_status(f"警告: 払戻テーブルが見つかりません ({race_id})")
                    print(f"      警告: 既知の払い戻しテーブル/エリアが見つかりませんでした ({race_id})。")
                    # 取得失敗時にHTMLを保存するデバッグコードは、原因が特定できたため一旦コメントアウトします。
                    # debug_dir = "debug_html"; os.makedirs(debug_dir, exist_ok=True)
                    # debug_filename = os.path.join(debug_dir, f"debug_payout_{race_id}.html");
                    # with open(debug_filename, "w", encoding="utf-8") as f: f.write(soup.prettify())
                    # print(f"        ★デバッグ: 取得失敗したページのHTMLを保存しました: {debug_filename}")
                return []

            pay_table = []
            # 見つかったエリア内の全てのテーブルから行データを抽出
            for table_tag in payout_area.find_all('table'):
                for tr_tag in table_tag.select('tr'):
                    row_data = [tag.get_text('\n', strip=True) for tag in tr_tag.select('th, td')]
                    if row_data and any(row_data):
                        pay_table.append(row_data)

            if pay_table:
                print(f"      DEBUG: get_pay_table成功 ({race_id}), {len(pay_table)}行のデータを抽出")
            else:
                print(f"      WARN: 払い戻しエリアは見つかりましたが、テーブル内容が空でした。({race_id})")

            return pay_table

        except requests.exceptions.Timeout:
            print(f"      タイムアウトエラー: {url}")
        except requests.exceptions.RequestException as e:
            print(f"      ページ取得エラー ({url}): {e}")
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
    
    def _run_result_analysis_thread(self, start_dt, end_dt, bet_types_to_run, analysis_type):
        """
        【最終確定版】
        - race_idのデータ型を文字列(str)に統一し、払い戻しデータの参照ミスを修正。
        - 払い戻しデータがなかったレース数をカウントし、サマリーに表示する機能を追加。
        """
        import time
        import pandas as pd
        import numpy as np
        import traceback
        from itertools import combinations

        try:
            start_time = time.time()
            
            # モデルのロード
            self.load_model_from_file(model_filename="trained_lgbm_model_win.pkl")
            if self.trained_model is None:
                messagebox.showerror("モデルエラー", "単勝予測モデル 'trained_lgbm_model_win.pkl' が見つかりません。")
                return
            
            # バックテスト用データの準備
            backtest_df_with_pred = self.prepare_data_for_backtest()
            if backtest_df_with_pred is None:
                self.root.after(0, self.update_status, "エラー: バックテスト準備失敗")
                return

            self.root.after(0, lambda: self.update_status(f"シミュレーション実行中..."))

            # 日付でデータを絞り込み
            date_col = 'date' if 'date' in backtest_df_with_pred.columns else 'race_date'
            sim_data = backtest_df_with_pred[
                (pd.to_datetime(backtest_df_with_pred[date_col], errors='coerce') >= start_dt) & 
                (pd.to_datetime(backtest_df_with_pred[date_col], errors='coerce') <= end_dt)
            ].copy()

            if sim_data.empty:
                self.root.after(0, lambda: messagebox.showinfo("バックテスト結果", "指定期間のレースデータがありません。"))
                return

            # race_idを文字列に統一し、辞書のキーとして確実に機能させる
            payout_dict_for_sim = {str(p['race_id']): p for p in self.payout_data if 'race_id' in p}
            sim_data['race_id'] = sim_data['race_id'].astype(str)
            
            simulation_results = []
            unique_race_ids = sim_data['race_id'].unique()
            
            N_TOP_HORSES = 3
            payout_not_found_count = 0 # 払い戻し情報が見つからなかったレース数

            for race_id in unique_race_ids:
                race_df = sim_data[sim_data['race_id'] == race_id]
                if len(race_df) < N_TOP_HORSES: continue

                top_n_horses = race_df.sort_values('predicted_proba', ascending=False).head(N_TOP_HORSES)
                top_n_umabans = [int(u) for u in top_n_horses['Umaban']]
                bet_combinations = list(combinations(top_n_umabans, 2))
                
                payout_info = payout_dict_for_sim.get(race_id, {})
                if not payout_info:
                    payout_not_found_count += 1
                    continue # 払い戻し情報がなければ当たり判定できないのでスキップ

                race_date = pd.to_datetime(top_n_horses[date_col].iloc[0], errors='coerce')

                # 馬連ボックス
                if bet_types_to_run.get("uren"):
                    investment = len(bet_combinations) * 100
                    pay = 0
                    hit = False
                    if '馬連' in payout_info and payout_info['馬連'].get('馬番'):
                        try:
                            win_combo = set(map(int, payout_info['馬連']['馬番'][0].split('-')))
                            if win_combo in [set(c) for c in bet_combinations]:
                                pay = int(payout_info['馬連']['払戻金'][0])
                                hit = True
                        except (ValueError, IndexError):
                            pass # データ形式が不正な場合はスキップ
                    simulation_results.append({'date': race_date, 'bet_type': '馬連ボックス', 'investment': investment, 'return': pay, 'hit': hit})

                # ワイドボックス
                if bet_types_to_run.get("wide"):
                    investment = len(bet_combinations) * 100
                    pay = 0
                    hit_count = 0
                    if 'ワイド' in payout_info and payout_info['ワイド'].get('馬番'):
                        try:
                            win_combos_set = [set(map(int, c.split('-'))) for c in payout_info['ワイド']['馬番']]
                            bet_combos_set = [set(c) for c in bet_combinations]
                            for i, win_combo in enumerate(win_combos_set):
                                if win_combo in bet_combos_set:
                                    pay += int(payout_info['ワイド']['払戻金'][i])
                                    hit_count += 1
                        except (ValueError, IndexError):
                            pass
                    simulation_results.append({'date': race_date, 'bet_type': 'ワイドボックス', 'investment': investment, 'return': pay, 'hit': hit_count > 0})
            
            if not simulation_results:
                self.root.after(0, lambda: messagebox.showinfo("バックテスト結果", "シミュレーション対象のベットがありませんでした。"))
                return

            sim_df = pd.DataFrame(simulation_results)
            total_investment = sim_df['investment'].sum()
            total_return = sim_df['return'].sum()
            profit = total_return - total_investment
            roi = total_return / total_investment if total_investment > 0 else 0
            
            summary = f"--- バックテスト結果 ({start_dt.date()} ～ {end_dt.date()}) ---\n"
            summary += f"総投資額: {total_investment:,.0f} 円\n総回収額: {total_return:,.0f} 円\n"
            summary += f"総収支: {profit:,.0f} 円\n回収率 (ROI): {roi:.1%}\n\n"
            summary += f"【実行戦略】\n- 各レースで予測確率上位{N_TOP_HORSES}頭の馬連・ワイドボックスを各100円購入\n\n"
            summary += "【馬券種別成績】\n"
            
            bet_types_in_result = sim_df['bet_type'].unique()
            for bet_type_name in sorted(bet_types_in_result):
                type_df = sim_df[sim_df['bet_type'] == bet_type_name]
                if not type_df.empty:
                    inv, ret, hit_rate = type_df['investment'].sum(), type_df['return'].sum(), type_df['hit'].mean()
                    type_roi = ret / inv if inv > 0 else 0
                    summary += f"- {bet_type_name}: 回収率 {type_roi:.1%}, 的中率 {hit_rate:.1%}\n"
            
            summary += f"\n(注: 払い戻し情報が見つからなかったレース数: {payout_not_found_count})\n"

            self.root.after(0, self._update_summary_text, summary)
            self.root.after(0, self._draw_result_graph, simulation_results, analysis_type, '収支推移 (上位3頭ボックス戦略)')

            end_time = time.time()
            print(f"--- バックテスト完了 ({end_time - start_time:.2f} 秒) ---")
            self.root.after(0, lambda: self.update_status("バックテスト完了"))

        except Exception as e:
            print(f"!!! Error in _run_result_analysis_thread !!!")
            traceback.print_exc()
            self.root.after(0, lambda err=e: messagebox.showerror("バックテストエラー", f"バックテスト実行中にエラーが発生しました:\n{err}"))
    
    def calculate_original_index(self, horse_details, race_conditions):
        """
        【特徴量強化版】
        オッズ順位、レース間隔などの強力な特徴量を追加し、モデルの予測精度向上を目指す。
        """
        # (features辞書の初期化)
        features = {
            'Umaban': np.nan, 'HorseName': '', 'Sex': np.nan, 'Age': np.nan,
            'Load': np.nan, 'JockeyName': '', 'TrainerName': '',
            'father': '', 'mother_father': '', 'horse_id': None,
            '近走1走前着順': np.nan, '近走2走前着順': np.nan, '近走3走前着順': np.nan,
            '着差_1走前': np.nan, '着差_2走前': np.nan, '着差_3走前': np.nan,
            '上がり3F_1走前': np.nan, '上がり3F_2走前': np.nan, '上がり3F_3走前': np.nan,
            '同条件出走数': 0, '同条件複勝率': 0.0,
            'タイム偏差値': np.nan,
            '同コース距離最速補正': np.nan,
            '基準タイム差': np.nan,
            '基準タイム比': np.nan,
            '父同条件複勝率': 0.0, '父同条件N数': 0,
            '母父同条件複勝率': 0.0, '母父同条件N数': 0,
            '斤量絶対値': np.nan, '斤量前走差': np.nan,
            '馬体重絶対値': np.nan, '馬体重前走差': np.nan,
            '枠番': np.nan, '枠番_複勝率': 0.0, '枠番_N数': 0,
            '負担率': np.nan,
            '距離区分': None,
            'race_class_level': np.nan,
            'odds_rank': np.nan,
            'days_since_last_race': np.nan,
            'time_dev_x_race_level': np.nan,
            'is_transfer_from_local_1ago': 0,
            'prev_race_track_type_1ago': 'Unknown',
            'num_jra_starts': 0,
            'jra_rank_1ago': np.nan,
            'OddsShutuba': np.nan,
            'NinkiShutuba': np.nan,
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
        
        # 新しい特徴量の計算
        features['odds_rank'] = pd.to_numeric(horse_details.get('Ninki'), errors='coerce')
        race_date = pd.to_datetime(race_conditions.get('RaceDate'), errors='coerce')
        if pd.notna(race_date) and race_results_for_calc and isinstance(race_results_for_calc[0], dict):
            last_race_date = pd.to_datetime(race_results_for_calc[0].get('date'), errors='coerce')
            if pd.notna(last_race_date):
                features['days_since_last_race'] = (race_date - last_race_date).days

        try:
            # 既存の特徴量計算
            for i in range(3):
                if len(race_results_for_calc) > i and isinstance(race_results_for_calc[i], dict):
                    features[f'近走{i+1}走前着順'] = pd.to_numeric(race_results_for_calc[i].get('rank'), errors='coerce')
                    features[f'着差_{i+1}走前'] = pd.to_numeric(race_results_for_calc[i].get('diff'), errors='coerce')
                    features[f'上がり3F_{i+1}走前'] = pd.to_numeric(race_results_for_calc[i].get('agari'), errors='coerce')
            
            features['斤量絶対値'] = features['Load']
            features['馬体重絶対値'] = pd.to_numeric(horse_details.get('Weight', horse_details.get('WeightShutuba')), errors='coerce')
            if race_results_for_calc and isinstance(race_results_for_calc[0], dict):
                prev_race = race_results_for_calc[0]
                prev_load = pd.to_numeric(prev_race.get('load'), errors='coerce')
                if pd.notna(features['斤量絶対値']) and pd.notna(prev_load):
                    features['斤量前走差'] = features['斤量絶対値'] - prev_load
                prev_weight = pd.to_numeric(prev_race.get('weight_val'), errors='coerce')
                if pd.notna(features['馬体重絶対値']) and pd.notna(prev_weight):
                    features['馬体重前走差'] = features['馬体重絶対値'] - prev_weight
            if pd.notna(features['斤量絶対値']) and pd.notna(features['馬体重絶対値']) and features['馬体重絶対値'] > 0:
                features['負担率'] = round(features['斤量絶対値'] / features['馬体重絶対値'], 3)

            baba_hosei_map = {'芝': {'良': 0.0, '稍重': 0.5, '重': 1.0, '不良': 1.5}, 'ダ': {'良': 0.0, '稍重': -0.3, '重': -0.8, '不良': -1.3}}
            best_corrected_time = np.nan
            if race_results_for_calc and target_course and pd.notna(target_distance_float):
                same_dist_races = [r for r in race_results_for_calc if isinstance(r, dict) and pd.to_numeric(r.get('distance'), errors='coerce') == target_distance_float]
                if same_dist_races:
                    corrected_times = []
                    for r in same_dist_races:
                        time_sec, past_course, past_baba = pd.to_numeric(r.get('time_sec'), errors='coerce'), r.get('course_type'), r.get('baba')
                        if pd.notna(time_sec) and past_course == target_course and past_baba in baba_hosei_map.get(target_course, {}):
                             corrected_times.append(time_sec - baba_hosei_map[target_course][past_baba])
                    if corrected_times:
                        best_corrected_time = min(corrected_times)
                        features['同コース距離最速補正'] = round(best_corrected_time, 2)

            if pd.notna(best_corrected_time) and hasattr(self, 'course_time_stats') and target_track and target_course:
                stat_key = (str(target_track), str(target_course), int(target_distance_float))
                course_stats = self.course_time_stats.get(stat_key)
                if course_stats and pd.notna(course_stats.get('mean')) and pd.notna(course_stats.get('std')) and course_stats['std'] > 0:
                    features['タイム偏差値'] = round(50 + 10 * (course_stats['mean'] - best_corrected_time) / course_stats['std'], 2)

            if features.get('father') and target_course and features.get('距離区分') and hasattr(self, 'father_stats'):
                sire_data = self.father_stats.get(str(features['father']), {})
                cond_key = (str(target_course), str(features['距離区分']))
                if cond_key in sire_data:
                    stats = sire_data[cond_key]
                    features['父同条件複勝率'], features['父同条件N数'] = round(stats.get('Place3Rate', 0.0), 3), int(stats.get('Runs', 0))

            features['枠番'] = pd.to_numeric(horse_details.get('Waku', horse_details.get('枠番')), errors='coerce')
            if pd.notna(features['枠番']) and target_track and target_course and pd.notna(target_distance_float) and hasattr(self, 'gate_stats'):
                stat_key_gate = (str(target_track), str(target_course), int(target_distance_float), int(features['枠番']))
                if stat_key_gate in self.gate_stats:
                    gate_data = self.gate_stats[stat_key_gate]
                    features['枠番_複勝率'], features['枠番_N数'] = round(gate_data.get('Place3Rate', 0.0), 3), int(gate_data.get('Runs', 0))

            if pd.notna(features.get('タイム偏差値')) and pd.notna(features.get('race_class_level')):
                features['time_dev_x_race_level'] = features['タイム偏差値'] * features['race_class_level']
                
        except Exception as e_main_calc:
            print(f"!!! ERROR: 特徴量計算メインブロックでエラー: {e_main_calc}")
            traceback.print_exc()
            features['error'] = f"CalcError: {type(e_main_calc).__name__}"

        return 0.0, features
    
    # --- 持ちタイム指数用の統計計算メソッド (修正・完全版・デバッグログ強化) ---
    def _calculate_course_time_stats(self):
        """
        読み込んだデータ全体から、競馬場・コース種別・距離ごとの
        馬場補正済み走破タイムの平均と標準偏差を計算し、クラス変数に格納する。
        """
        print("【DEBUG LOG】_calculate_course_time_stats: 競馬場・コース・距離別のタイム統計データ（平均・標準偏差）を計算中...")
        self.update_status("タイム統計データ計算中...")
        start_calc_time = time.time() # time.time() を使う

        self.course_time_stats = {} # 初期化

        if self.combined_data is None or self.combined_data.empty:
            print("【DEBUG LOG】_calculate_course_time_stats: 警告: タイム統計計算のためのデータがありません。")
            self.update_status("タイム統計計算不可 (データなし)")
            return

        actual_track_name_col = None
        possible_track_name_cols = ['track_name', '開催場所', '競馬場']
        for col_name in possible_track_name_cols:
            if col_name in self.combined_data.columns:
                actual_track_name_col = col_name
                print(f"【DEBUG LOG】_calculate_course_time_stats: 使用する競馬場名の列: '{actual_track_name_col}'")
                break
        
        if actual_track_name_col is None:
            print(f"【DEBUG LOG】_calculate_course_time_stats: CRITICAL ERROR: 競馬場名に相当する列が見つかりません。候補: {possible_track_name_cols}")
            self.update_status("エラー: タイム統計計算失敗 (競馬場名列なし)")
            return

        required_cols = [actual_track_name_col, 'course_type', 'distance', 'track_condition', 'Time', 'Rank']
        if not all(col in self.combined_data.columns for col in required_cols):
            missing = [c for c in required_cols if c not in self.combined_data.columns]
            print(f"【DEBUG LOG】_calculate_course_time_stats: 警告: タイム統計計算に必要な他の列が不足しています: {missing}")
            self.update_status(f"タイム統計計算不可 (列不足: {missing})")
            return

        df = self.combined_data[required_cols].copy()
        df.rename(columns={actual_track_name_col: 'track_name'}, inplace=True)

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

        df.dropna(subset=['time_sec_numeric', 'track_condition', 'course_type', 'distance', 'Rank', 'track_name'], inplace=True)
        df['distance_numeric'] = pd.to_numeric(df['distance'], errors='coerce')
        df['Rank_numeric'] = pd.to_numeric(df['Rank'], errors='coerce')
        df.dropna(subset=['distance_numeric', 'Rank_numeric'], inplace=True)
        
        if df.empty:
            print("【DEBUG LOG】_calculate_course_time_stats: 警告: タイム統計計算の対象となる有効なデータがありません (dropna後)。")
            self.update_status("タイム統計計算不可 (有効データなし)")
            return
            
        df['distance_numeric'] = df['distance_numeric'].astype(int)
        df['Rank_numeric'] = df['Rank_numeric'].astype(int)
        df['track_name'] = df['track_name'].astype(str).str.strip()
        df['course_type'] = df['course_type'].astype(str).str.strip()
        df['baba'] = df['track_condition'].astype(str).str.strip()

        baba_hosei = {
            '芝': {'良': 0.0, '稍重': 0.5, '重': 1.0, '不良': 1.5},
            'ダ': {'良': 0.0, '稍重': -0.3, '重': -0.8, '不良': -1.3}
        }
        def get_hosei(row):
            course = row['course_type']; baba = row['baba']
            return baba_hosei.get(course, {}).get(baba, 0.0)
        df['hosei_value'] = df.apply(get_hosei, axis=1)
        df['corrected_time_sec'] = df['time_sec_numeric'] - df['hosei_value']

        df_filtered = df[df['Rank_numeric'] <= 5]
        print(f"【DEBUG LOG】_calculate_course_time_stats: タイム統計計算: {len(df)}行からRank<=5の{len(df_filtered)}行を対象とします。")

        if df_filtered.empty:
            print("【DEBUG LOG】_calculate_course_time_stats: 警告: タイム統計計算の対象となるデータがありません (フィルター後)。")
            self.update_status("タイム統計計算不可 (対象データなし)")
            return

        try:
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
                    'std': row['std_revised'], # ここで NaN も許容する
                    'count': int(row['count'])
                }
                # デバッグログで格納される値を確認
                # print(f"【DEBUG LOG】_calculate_course_time_stats: Stored key: {key}, value: {self.course_time_stats[key]}")


            end_calc_time = time.time()
            print(f"【DEBUG LOG】_calculate_course_time_stats: タイム統計データの計算完了。{len(self.course_time_stats)} 件の(競馬場・コース・距離)別データを生成。({end_calc_time - start_calc_time:.2f}秒)")
            
            # 重要なキーの存在確認
            keys_to_check = [('京都', 'ダ', 1800), ('東京', '芝', 1600)] # 例
            for check_key in keys_to_check:
                if check_key in self.course_time_stats:
                    print(f"【DEBUG LOG】_calculate_course_time_stats: 確認キー {check_key} のデータ: {self.course_time_stats[check_key]}")
                else:
                    print(f"【DEBUG LOG】_calculate_course_time_stats: 確認キー {check_key} のデータは見つかりません。")

            self.update_status("タイム統計データ準備完了")

        except Exception as e:
            print(f"【DEBUG LOG】_calculate_course_time_stats: !!! Error during time stats calculation: {e}")
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
    
    # --- ★★★ 基準タイム計算メソッド (デバッグログ強化版) ★★★ ---
    def _calculate_reference_times(self):
        """
        手持ちデータ全体から、クラス・コース・距離ごとの基準タイム（勝ち馬の平均馬場補正タイム）を計算し、
        クラス変数 self.reference_times に格納する。
        """
        print("【DEBUG LOG】_calculate_reference_times: クラス・コース・距離別の基準タイムを計算中...")
        self.update_status("基準タイム計算中...")
        start_calc_time = time.time()

        self.reference_times = {} 

        if self.combined_data is None or self.combined_data.empty:
            print("【DEBUG LOG】_calculate_reference_times: 警告: 基準タイム計算のためのデータがありません。")
            self.update_status("基準タイム計算不可 (データなし)")
            return

        required_cols = ['race_name', 'track_name', 'course_type', 'distance', 'track_condition', 'Time', 'Rank']
        if not all(col in self.combined_data.columns for col in required_cols):
             missing = [c for c in required_cols if c not in self.combined_data.columns]
             print(f"【DEBUG LOG】_calculate_reference_times: 警告: 基準タイム計算に必要な列が不足しています: {missing}")
             self.update_status(f"基準タイム計算不可 (列不足: {missing})")
             return

        df = self.combined_data[required_cols].copy()

        try:
            df.dropna(subset=required_cols, inplace=True)
            df['time_sec'] = df['Time'].apply(self._time_str_to_sec)
            df['race_class_level_calc'] = df['race_name'].apply(self._get_race_class_level) # 新しい列名
            df['distance_int'] = pd.to_numeric(df['distance'], errors='coerce')
            df['Rank_int'] = pd.to_numeric(df['Rank'], errors='coerce')
            df.dropna(subset=['time_sec', 'race_class_level_calc', 'distance_int', 'Rank_int', 'track_condition', 'course_type', 'track_name'], inplace=True)
            
            if df.empty:
                print("【DEBUG LOG】_calculate_reference_times: 警告: 基準タイム計算の対象となる有効なデータがありません (dropna後)。")
                self.update_status("基準タイム計算不可 (有効データなし)")
                return

            df['distance_int'] = df['distance_int'].astype(int)
            df['Rank_int'] = df['Rank_int'].astype(int)
            df['track_name'] = df['track_name'].astype(str).str.strip()
            df['course_type'] = df['course_type'].astype(str).str.strip()
            df['baba'] = df['track_condition'].astype(str).str.strip() 

            baba_hosei = {'芝': {'良': 0.0, '稍重': 0.5, '重': 1.0, '不良': 1.5}, 'ダ': {'良': 0.0, '稍重': -0.3, '重': -0.8, '不良': -1.3}}
            def get_hosei(row): return baba_hosei.get(row['course_type'], {}).get(row['baba'], 0.0)
            df['hosei_value'] = df.apply(get_hosei, axis=1)
            df['corrected_time_sec'] = df['time_sec'] - df['hosei_value']

            df_filtered = df[df['Rank_int'] == 1].copy()
            if df_filtered.empty:
                print("【DEBUG LOG】_calculate_reference_times: 警告: 基準タイム計算の対象となる勝ち馬データがありません。")
                self.update_status("基準タイム計算不可 (対象データなし)")
                return

        except Exception as e_prep:
            print(f"【DEBUG LOG】_calculate_reference_times: !!! ERROR during reference time data preparation: {e_prep}")
            traceback.print_exc()
            self.reference_times = {}
            self.update_status("エラー: 基準タイム データ準備失敗")
            return

        try:
            group_keys = ['race_class_level_calc', 'track_name', 'course_type', 'distance_int']
            stats = df_filtered.groupby(group_keys)['corrected_time_sec'].agg(
                mean_time='mean',
                count='size' 
            ).reset_index()

            min_races_threshold = 5 
            temp_reference_times = {}
            for _, row in stats.iterrows():
                if row['count'] >= min_races_threshold: 
                    key = (int(row['race_class_level_calc']), str(row['track_name']), str(row['course_type']), int(row['distance_int']))
                    temp_reference_times[key] = round(row['mean_time'], 3)
                    # デバッグログで格納される値を確認
                    # print(f"【DEBUG LOG】_calculate_reference_times: Stored key: {key}, value: {temp_reference_times[key]}")


            self.reference_times = temp_reference_times 

            end_calc_time = time.time()
            print(f"【DEBUG LOG】_calculate_reference_times: 基準タイムの計算完了。{len(self.reference_times)} 件の有効な条件データを生成。({end_calc_time - start_calc_time:.2f}秒)")
            
            # 重要なキーの存在確認
            keys_to_check_ref = [(3, '京都', 'ダ', 1800), (9, '東京', '芝', 2400)] # 例
            for check_key_ref in keys_to_check_ref:
                if check_key_ref in self.reference_times:
                    print(f"【DEBUG LOG】_calculate_reference_times: 確認キー {check_key_ref} の基準タイム: {self.reference_times[check_key_ref]}")
                else:
                    print(f"【DEBUG LOG】_calculate_reference_times: 確認キー {check_key_ref} の基準タイムは見つかりません。")
            self.update_status("基準タイム準備完了")

        except Exception as e:
            print(f"【DEBUG LOG】_calculate_reference_times: !!! Error during reference time calculation: {e}")
            traceback.print_exc()
            self.reference_times = {} 
            self.update_status("エラー: 基準タイム計算失敗")

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
    
    def load_model_from_file(self, model_filename="trained_lgbm_model.pkl"):
        """
        指定されたファイルから学習済みモデルと、それに対応する特徴量リスト、
        欠損値補完値を読み込む。
        【改修】モデルファイル名に基づき、関連ファイル名も自動で解決するよう修正。
        """
        import os

        model_load_dir = self.settings.get("models_dir", os.path.join(self.app_data_dir, "models"))
        
        # ★★★★★★★★★★★★ エラー修正箇所 ★★★★★★★★★★★★
        # モデルファイル名から、特徴量リストと補完値のファイル名を自動生成する
        base_name, _ = os.path.splitext(model_filename)
        features_filename = f"{base_name}_features.pkl"
        imputation_filename = f"{base_name}_imputation_values.pkl"
        
        model_filepath = os.path.join(model_load_dir, model_filename)
        features_filepath = os.path.join(model_load_dir, features_filename)
        imputation_filepath = os.path.join(model_load_dir, imputation_filename)
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

        # --- 学習済みモデルの読み込み ---
        print(f"INFO: Loading trained model from: {model_filepath}")
        loaded_model = self._load_pickle(model_filepath)
        if loaded_model is not None:
            self.trained_model = loaded_model
            print(f"INFO: Successfully loaded trained model: {model_filepath}")
        else:
            self.trained_model = None
            print(f"WARN: Failed to load trained model or file not found: {model_filepath}")

        # --- 特徴量リストの読み込み ---
        print(f"INFO: Loading model features from: {features_filepath}")
        loaded_features = self._load_pickle(features_filepath)
        if loaded_features is not None and isinstance(loaded_features, list):
            self.model_features = loaded_features
            print(f"INFO: Successfully loaded model features ({len(self.model_features)} features): {features_filepath}")
        else:
            self.model_features = []
            print(f"WARN: Failed to load model features or file not found: {features_filepath}.")
            if self.trained_model is not None:
                 print(f"CRITICAL WARN: Model loaded, but feature list is missing!")

        # --- 欠損値補完のための値の読み込み ---
        print(f"INFO: Loading imputation values from: {imputation_filepath}")
        loaded_imputation_values = self._load_pickle(imputation_filepath)
        if loaded_imputation_values is not None and isinstance(loaded_imputation_values, dict):
            self.imputation_values_ = loaded_imputation_values
            print(f"INFO: 欠損値補完のための値をロードしました: {imputation_filepath} ({len(self.imputation_values_)} 列分)")
        else:
            self.imputation_values_ = {}
            print(f"INFO: 欠損値補完ファイルが見つからないかロードに失敗 ({imputation_filepath})。")

        # --- 最終的なステータス表示 ---
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
    
    def _prepare_data_for_model(self, target_column_name='target_rank_within_3'):
        """
        self.processed_data からモデル学習・バックテスト用のデータを準備する。
        ターゲット列を指定できるように引数を追加。
        """
        if self.processed_data is None or self.processed_data.empty:
            print("ERROR: _prepare_data_for_model: self.processed_data が空です。")
            return pd.DataFrame()

        # ターゲット列（目的変数）が存在するか確認
        if target_column_name not in self.processed_data.columns:
            print(f"ERROR: 指定されたターゲット列 '{target_column_name}' がデータに存在しません。")
            # ターゲット列を計算するロジックをここに集約
            try:
                print(f"INFO: ターゲット列 '{target_column_name}' を生成します...")
                if target_column_name == 'target_rank_within_3':
                    self.processed_data['target_rank_within_3'] = self.processed_data['Rank'].apply(lambda x: 1 if x in [1, 2, 3] else 0)
                elif target_column_name == 'target_win':
                    self.processed_data['target_win'] = self.processed_data['Rank'].apply(lambda x: 1 if x == 1 else 0)
                else:
                     messagebox.showerror("エラー", f"未知のターゲット列名です: {target_column_name}")
                     return pd.DataFrame()
                print(f"INFO: ターゲット列 '{target_column_name}' の生成が完了しました。")
            except Exception as e:
                print(f"ERROR: ターゲット列の生成中にエラー: {e}")
                return pd.DataFrame()

        # 不要な列を定義
        cols_to_drop = [
            col for col in ['target_win', 'target_rank_within_3'] 
            if col != target_column_name and col in self.processed_data.columns
        ]
        
        # ターゲット以外の目的変数を削除
        data_for_model = self.processed_data.drop(columns=cols_to_drop, errors='ignore').copy()
        
        print(f"モデル学習用の元データ (特徴量 + ターゲット列) の準備完了。Shape: {data_for_model.shape}")
        return data_for_model
   
    def train_and_evaluate_model(self, processed_data, target_column='target_rank_within_3', mode='place'):
        """
        LightGBMモデルの学習、評価、保存、キャリブレーションプロット作成を行う。
        クラス不均衡を是正する scale_pos_weight を追加。
        """
        import pandas as pd
        import numpy as np
        import lightgbm as lgb
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score, accuracy_score, precision_score, recall_score, confusion_matrix
        from sklearn.calibration import CalibrationDisplay
        import matplotlib.pyplot as plt
        import os
        import traceback
        from tkinter import messagebox

        try:
            self.update_status(f"モデル学習と評価を開始します (モード: {mode})...")
            print(f"\n--- Starting Model Training and Evaluation (mode: {mode}) ---")

            if processed_data is None or processed_data.empty:
                messagebox.showerror("学習エラー", "学習に使用するデータがありません。")
                self.update_status("エラー: 学習データなし")
                return

            cols_to_drop_for_X = [
                target_column, 'race_id', 'horse_id', 'HorseName', 'date',
                'Time', 'Rank','Diff', 'Ninki', 'Odds', 'Odds_x', 'Odds_y',
                'Umaban', 'Waku',
                'SexAge', 'JockeyName', 'TrainerName',
                'father', 'mother_father',
                'WeightInfo', 'WeightInfoShutuba',
                'target_exacta', 'target_quinella', 'target_trifecta', 
                'payout_win', 'payout_place', 'payout_exacta', 'payout_quinella', 'payout_trifecta',
                'text_race_results',
                'error'
            ]
            existing_cols_to_drop_for_X = [col for col in cols_to_drop_for_X if col in processed_data.columns]
            
            X = processed_data.drop(columns=existing_cols_to_drop_for_X, errors='ignore').copy()
            
            if target_column not in processed_data.columns:
                messagebox.showerror("学習エラー", f"ターゲット列 '{target_column}' がデータに存在しません。")
                self.update_status(f"エラー: ターゲット列 '{target_column}' なし")
                return
            y = processed_data[target_column].astype(int)

            print("特徴量データのデータ型前処理と欠損値補完を開始します...")
            
            if 'prev_race_track_type_1ago' in X.columns:
                try:
                    X = pd.get_dummies(X, columns=['prev_race_track_type_1ago'], prefix='prev_track_type', dummy_na=True)
                except Exception as e_dummy:
                    print(f"    エラー: prev_race_track_type_1ago のダミー変数化に失敗: {e_dummy}")
                    X = X.drop(columns=['prev_race_track_type_1ago'], errors='ignore')
            
            if 'Sex' in X.columns:
                X['Sex'] = pd.to_numeric(X['Sex'], errors='coerce')
                sex_fill_value = X['Sex'].mode()[0] if not X['Sex'].mode().empty else -1
                if 'Sex' not in self.imputation_values_: self.imputation_values_['Sex'] = sex_fill_value
                X['Sex'] = X['Sex'].fillna(self.imputation_values_['Sex'])

            if '距離区分' in X.columns:
                distance_category_mapping = {
                    '1400m以下': 0, '1401-1800m': 1, '1801-2200m': 2, 
                    '2201-2600m': 3, '2601m以上': 4
                }
                X['距離区分'] = X['距離区分'].map(distance_category_mapping)
                dist_fill_value = X['距離区分'].mode()[0] if not X['距離区分'].mode().empty else -1
                if '距離区分' not in self.imputation_values_: self.imputation_values_['距離区分'] = dist_fill_value
                X['距離区分'] = X['距離区分'].fillna(self.imputation_values_['距離区分'])

            if not hasattr(self, 'imputation_values_'): self.imputation_values_ = {}
            for col in X.columns:
                if X[col].dtype == 'object':
                    X.loc[:, col] = pd.to_numeric(X[col], errors='coerce')
                if X[col].isnull().any():
                    if col not in self.imputation_values_:
                        mean_val = X[col].mean()
                        self.imputation_values_[col] = 0 if pd.isna(mean_val) else mean_val
                    X.loc[:, col] = X[col].fillna(self.imputation_values_[col])
            
            self.model_features = list(X.columns)
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
            print(f"データを分割しました: 訓練データ {len(X_train)}件, テストデータ {len(X_test)}件")

            try:
                scale_pos_weight_value = y_train.value_counts()[0] / y_train.value_counts()[1]
                print(f"クラス不均衡是正のため scale_pos_weight を計算しました: {scale_pos_weight_value:.2f}")
            except (ZeroDivisionError, KeyError):
                print("警告: 訓練データに正例がありません。scale_pos_weight は使用しません。")
                scale_pos_weight_value = 1

            lgbm_params = {
                'objective': 'binary', 'metric': 'auc', 'boosting_type': 'gbdt',
                'n_estimators': 1000, 'learning_rate': 0.05, 'num_leaves': 31,
                'max_depth': -1, 'min_child_samples': 20, 'subsample': 0.8,
                'colsample_bytree': 0.8, 'random_state': 42, 'n_jobs': -1, 'verbose': -1,
                'scale_pos_weight': scale_pos_weight_value
            }
            self.trained_model = lgb.LGBMClassifier(**lgbm_params)

            print("モデルの学習を開始します...")
            self.trained_model.fit(X_train, y_train,
                                   eval_set=[(X_test, y_test)],
                                   eval_metric='auc',
                                   callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=-1)])
            print("モデルの学習が完了しました。")

            model_save_dir = self.settings.get("models_dir", os.path.join(self.app_data_dir, "models"))
            os.makedirs(os.path.expanduser(model_save_dir), exist_ok=True)
            
            # ★★★ 修正点: mode引数を使ってファイル名を決定 ★★★
            model_filename = f"trained_lgbm_model_{mode}.pkl"
            features_filename = f"trained_lgbm_model_{mode}_features.pkl"
            imputation_filename = f"trained_lgbm_model_{mode}_imputation_values.pkl"

            self._save_pickle(self.trained_model, os.path.join(model_save_dir, model_filename))
            self._save_pickle(self.model_features, os.path.join(model_save_dir, features_filename))
            self._save_pickle(self.imputation_values_, os.path.join(model_save_dir, imputation_filename))

            y_pred_proba = self.trained_model.predict_proba(X_test)[:, 1]
            y_pred_binary = (y_pred_proba >= 0.5).astype(int)
            
            auc = roc_auc_score(y_test, y_pred_proba)
            accuracy = accuracy_score(y_test, y_pred_binary)
            precision = precision_score(y_test, y_pred_binary, zero_division=0)
            recall = recall_score(y_test, y_pred_binary, zero_division=0)
            cm = confusion_matrix(y_test, y_pred_binary)
            eval_results_text = (
                f"モデル評価結果 ({mode}モデル):\n\nAUC Score: {auc:.4f}\n"
                f"Accuracy: {accuracy:.4f}\nPrecision: {precision:.4f}\nRecall: {recall:.4f}\n\n"
                f"Confusion Matrix:\n{cm}"
            )
            print(eval_results_text)
            self.root.after(0, lambda: messagebox.showinfo("モデル評価結果", eval_results_text))

        except Exception as e:
            print(f"!!! FATAL ERROR in train_and_evaluate_model !!!"); traceback.print_exc()
            self.root.after(0, lambda: messagebox.showerror("モデル学習エラー", f"モデル学習・評価中に予期せぬエラー:\n{e}"))
        finally:
            print(f"--- Model Training and Evaluation Finished (mode: {mode}) ---")
    
    def start_model_training_process(self):
        """
        モデル学習プロセスの開始点。
        データ準備とモデル学習・評価を順に実行する。
        """
        if not hasattr(self, 'combined_data') or self.combined_data is None or self.combined_data.empty:
            messagebox.showerror("データエラー", "学習の元となるデータ (combined_data) が読み込まれていません。\nデータ管理タブでデータを読み込んでください。")
            self.update_status("エラー: 元データ未読み込み")
            return

        # ★★★ 修正点: 引数なしで呼び出す ★★★
        self.run_in_thread(self._run_training_pipeline_thread)
    
    def _prepare_data_for_model(self, target_column_name='target_rank_within_3'):
        """
        self.processed_data からモデル学習・バックテスト用のデータを準備する。
        ターゲット列を指定できるように引数を追加。
        """
        if self.processed_data is None or self.processed_data.empty:
            print("ERROR: _prepare_data_for_model: self.processed_data が空です。")
            return pd.DataFrame()

        # ターゲット列（目的変数）が存在するか確認
        if target_column_name not in self.processed_data.columns:
            print(f"ERROR: 指定されたターゲット列 '{target_column_name}' がデータに存在しません。")
            # ターゲット列を計算するロジックをここに集約
            try:
                print(f"INFO: ターゲット列 '{target_column_name}' を生成します...")
                if target_column_name == 'target_rank_within_3':
                    self.processed_data['target_rank_within_3'] = self.processed_data['Rank'].apply(lambda x: 1 if x in [1, 2, 3] else 0)
                elif target_column_name == 'target_win':
                    self.processed_data['target_win'] = self.processed_data['Rank'].apply(lambda x: 1 if x == 1 else 0)
                else:
                     messagebox.showerror("エラー", f"未知のターゲット列名です: {target_column_name}")
                     return pd.DataFrame()
                print(f"INFO: ターゲット列 '{target_column_name}' の生成が完了しました。")
            except Exception as e:
                print(f"ERROR: ターゲット列の生成中にエラー: {e}")
                return pd.DataFrame()

        # 不要な列を定義
        cols_to_drop = [
            col for col in ['target_win', 'target_rank_within_3'] 
            if col != target_column_name and col in self.processed_data.columns
        ]
        
        # ターゲット以外の目的変数を削除
        data_for_model = self.processed_data.drop(columns=cols_to_drop, errors='ignore').copy()
        
        print(f"モデル学習用の元データ (特徴量 + ターゲット列) の準備完了。Shape: {data_for_model.shape}")
        return data_for_model
 
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
        """
        get_pay_tableの結果を整形して辞書で返す (最終完成版)
        複数行にまたがる複勝・ワイドのデータ処理に完全対応。
        """
        payouts_dict = {'race_id': race_id}
        if not payouts_list:
            return payouts_dict

        # 全ての馬券種を定義
        ALL_BET_TYPES = {'単勝', '複勝', '枠連', '馬連', 'ワイド', '馬単', '三連複', '三連単'}
        COMBINATION_TYPES = {'枠連', '馬連', 'ワイド', '馬単', '三連複', '三連単'}
        # 複数行になりうる馬券種
        MULTI_ROW_TYPES = {'複勝', 'ワイド'}

        current_type = None

        for i, row_orig in enumerate(payouts_list):
            try:
                row = [cell.strip() for cell in row_orig if isinstance(cell, str) and cell.strip()]
                if not row:
                    continue

                # 行の最初の要素が馬券種名かをチェック
                if row[0] in ALL_BET_TYPES:
                    # 最初の要素が馬券種名の場合 -> ヘッダー行
                    current_type = row[0]
                    data_cells = row[1:]
                # 継続行の判定を強化: current_typeが設定されており、かつ複数行になりうる馬券種であること
                elif current_type in MULTI_ROW_TYPES and row[0] not in ALL_BET_TYPES:
                    data_cells = row
                else:
                    # 上記以外は不明な行としてスキップ
                    continue
                
                if not current_type or len(data_cells) < 2:
                    continue
                
                numbers_str = data_cells[0]
                payout_str = data_cells[1].replace(',', '').replace('円', '')
                ninki_str = data_cells[2].replace('人気', '') if len(data_cells) > 2 else None

                payout_val = int(payout_str) if payout_str.isdigit() else None
                if payout_val is None:
                    continue
                
                ninki_val = int(ninki_str) if ninki_str and ninki_str.isdigit() else None
                if current_type not in payouts_dict:
                    payouts_dict[current_type] = {'馬番': [], '払戻金': []}
                    if ninki_val is not None:
                        payouts_dict[current_type]['人気'] = []
                
                if current_type in COMBINATION_TYPES:
                    combined_number = '-'.join(numbers_str.split('\n'))
                    payouts_dict[current_type]['馬番'].append(combined_number)
                    payouts_dict[current_type]['払戻金'].append(payout_val)
                    if '人気' in payouts_dict[current_type] and ninki_val is not None:
                        payouts_dict[current_type]['人気'].append(ninki_val)
                else: # 単勝・複勝
                    num_list = numbers_str.split('\n')
                    payouts_dict[current_type]['馬番'].extend(num_list)
                    payouts_dict[current_type]['払戻金'].extend([payout_val] * len(num_list))
                    if '人気' in payouts_dict[current_type] and ninki_val is not None:
                         payouts_dict[current_type]['人気'].extend([ninki_val] * len(num_list))

            except Exception as e_pay:
                print(f"      警告: 払い戻しデータ行の処理中にエラー発生 ({race_id}): {e_pay} - Row Original: {row_orig}")
                traceback.print_exc()
        
        return payouts_dict

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
        """
        レース情報の取得と表示、学習済みモデルでの予測確率計算。
        【改修】常にWebから最新の馬情報を取得し、キャッシュの古さを解消。
        【改修】オッズと予測確率から「単勝期待値」を計算するロジックを追加。
        【改修】推奨馬券を提示する機能を追加。
        【★★バグ修正★★】予測時に「距離区分」を数値に変換する処理を追加。
        """
        # --- 必要なライブラリをインポート ---
        import time
        import pandas as pd
        import numpy as np
        import traceback
        import re
        from tkinter import messagebox
        import tkinter as tk

        try:
            self.root.after(0, lambda: self.update_status(f"レースID {race_id}: 予測処理開始..."))
            print(f"--- _fetch_race_info_thread: START (Race ID: {race_id}) ---")

            # 1. 学習済みモデルと特徴量リストの存在チェック
            if not hasattr(self, 'trained_model') or self.trained_model is None:
                self.root.after(0, lambda: messagebox.showwarning("モデル未学習", "学習済みモデルが読み込まれていません。\nモデル学習タブでモデルを学習・ロードしてください。"))
                self.root.after(0, lambda: self.update_status("エラー: 学習済みモデルなし"))
                return
            if not hasattr(self, 'model_features') or not self.model_features:
                self.root.after(0, lambda: messagebox.showwarning("特徴量リスト未ロード", "モデル学習時の特徴量リストが読み込まれていません。\nモデルと共に保存されているはずです。"))
                self.root.after(0, lambda: self.update_status("エラー: 特徴量リストなし"))
                return
            feature_cols_for_predict = self.model_features
            print(f"INFO: 学習済みモデルと特徴量リスト ({len(feature_cols_for_predict)}個) を確認。")

            # 2. Webから出馬表とレース共通情報を取得
            self.root.after(0, lambda: self.update_status(f"レースID {race_id}: Webから出馬表情報取得中..."))
            web_data_from_get_shutuba = self.get_shutuba_table(race_id)
            if not web_data_from_get_shutuba or not web_data_from_get_shutuba.get('horse_list'):
                self.root.after(0, lambda: messagebox.showerror("Web取得エラー", f"レースID {race_id} の出馬表をWebから取得できませんでした。"))
                self.root.after(0, lambda: self.update_status(f"エラー: Web取得失敗"))
                return

            race_df = pd.DataFrame(web_data_from_get_shutuba['horse_list'])
            if race_df.empty:
                self.root.after(0, lambda: messagebox.showerror("Web取得エラー", f"レースID {race_id}: Webから出馬表データを取得しましたが内容が空でした。"))
                self.root.after(0, lambda: self.update_status(f"エラー: Web取得後データ空"))
                return
            
            # レース共通情報 (race_conditions) を作成
            race_conditions = web_data_from_get_shutuba.get('race_details', {})
            race_date_str = race_conditions.get('RaceDate')
            race_conditions['RaceDate'] = pd.to_datetime(race_date_str, format='%Y年%m月%d日', errors='coerce') if race_date_str else pd.NaT
            race_conditions['baba'] = race_conditions.get('TrackCondition')

            print(f"DEBUG: 予測に使用するレース共通情報: {race_conditions}")
            
            # 3. GUIにレース基本情報を表示
            race_date_for_display = race_conditions.get('RaceDate')
            race_date_str_display = race_date_for_display.strftime('%Y年%m月%d日') if pd.notna(race_date_for_display) else '日付不明'
            track_name_display = str(race_conditions.get('TrackName', '場所不明'))
            race_num_display = str(race_conditions.get('RaceNum', '?')).replace('R','')
            race_name_display = str(race_conditions.get('RaceName', 'レース名不明'))
            course_type_display = str(race_conditions.get('CourseType', '種別不明'))
            distance_val_display = race_conditions.get('Distance')
            distance_display_str = str(int(distance_val_display)) if pd.notna(distance_val_display) else '距離不明'
            turn_detail_display = str(race_conditions.get('Around', ''))
            weather_display = str(race_conditions.get('Weather', '天候不明'))
            condition_display = str(race_conditions.get('TrackCondition', '馬場不明'))
            race_info_text = f"{race_date_str_display} {track_name_display}{race_num_display}R {race_name_display}"
            race_details_text = f"{course_type_display}{turn_detail_display}{distance_display_str}m / 天候:{weather_display} / 馬場:{condition_display}"

            # 4. 出走馬ごとの処理ループ
            horse_details_list_for_gui = []
            num_horses_to_process = len(race_df)
            self.root.after(0, lambda status=f"{race_id}: {num_horses_to_process}頭の馬情報処理中...": self.update_status(status))

            for index, row_from_racedf in race_df.iterrows():
                umaban_val = row_from_racedf.get('Umaban')
                horse_name_val = row_from_racedf.get('HorseName')
                horse_id_val = row_from_racedf.get('horse_id')

                if pd.isna(horse_id_val):
                    error_info = dict(row_from_racedf)
                    error_info.update({'予測確率': None, '期待値': None, 'error_detail': 'horse_id欠損', '近3走': 'N/A'})
                    horse_details_list_for_gui.append(error_info)
                    continue
                
                horse_id_str = str(horse_id_val).strip().split('.')[0]
                
                # 常にWebから馬の最新詳細情報を取得
                horse_full_details = self.get_horse_details(horse_id_str)
                if isinstance(horse_full_details, dict) and not horse_full_details.get('error'):
                    self.horse_details_cache[horse_id_str] = horse_full_details

                horse_basic_info = dict(row_from_racedf)
                if isinstance(horse_full_details, dict):
                    horse_basic_info.update(horse_full_details)
                
                # 過去戦績をフィルタリング
                if 'race_results' in horse_basic_info and isinstance(horse_basic_info['race_results'], list):
                    predict_race_date = race_conditions.get('RaceDate')
                    if pd.notna(predict_race_date):
                        filtered_results = [pr for pr in horse_basic_info['race_results'] if pd.to_datetime(pr.get('date'), errors='coerce') < predict_race_date]
                        horse_basic_info['race_results'] = filtered_results
                else:
                    horse_basic_info['race_results'] = []

                # 特徴量計算
                _, features_dict = self.calculate_original_index(horse_basic_info, race_conditions)
                predicted_proba = None
                expected_value_win = None
                error_detail_calc = features_dict.get('error')

                if error_detail_calc is None:
                    try:
                        feature_values = {col: features_dict.get(col, np.nan) for col in feature_cols_for_predict}
                        X_pred = pd.DataFrame([feature_values])
                        
                        # ★★★★★★★★★★★★ エラー修正箇所 ★★★★★★★★★★★★
                        # 予測前に「距離区分」を学習時と同じルールで数値にマッピングする
                        if '距離区分' in X_pred.columns:
                            distance_map = {'1400m以下': 0, '1401-1800m': 1, '1801-2200m': 2, '2201-2600m': 3, '2601m以上': 4}
                            X_pred['距離区分'] = X_pred['距離区分'].map(distance_map)
                            print(f"DEBUG ({umaban_val}): Mapped '距離区分' to numeric. Value: {X_pred['距離区分'].iloc[0]}")
                        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

                        # 欠損値補完
                        if hasattr(self, 'imputation_values_') and self.imputation_values_:
                            for col in X_pred.columns:
                                if col in self.imputation_values_:
                                    X_pred[col] = X_pred[col].fillna(self.imputation_values_[col])
                            X_pred = X_pred.fillna(0)
                        else:
                            X_pred = X_pred.fillna(0)
                        
                        # 予測確率の計算
                        proba_result = self.trained_model.predict_proba(X_pred[feature_cols_for_predict])
                        predicted_proba = proba_result[0, 1]

                        # 単勝期待値の計算
                        odds_win = pd.to_numeric(row_from_racedf.get('Odds'), errors='coerce')
                        if pd.notna(predicted_proba) and pd.notna(odds_win) and odds_win > 0:
                            expected_value_win = predicted_proba * odds_win

                    except Exception as e_pred_calc:
                        print(f"!!! ERROR ({umaban_val}): 予測確率計算中にエラー: {e_pred_calc}"); traceback.print_exc()
                        error_detail_calc = f"予測計算エラー: {type(e_pred_calc).__name__}"
                
                # GUI表示用リストに追加
                current_horse_gui_info = dict(row_from_racedf)
                current_horse_gui_info['horse_id'] = horse_id_str
                current_horse_gui_info['father'] = horse_basic_info.get('father', 'N/A')
                current_horse_gui_info['mother_father'] = horse_basic_info.get('mother_father', 'N/A')
                recent_ranks = [str(r.get('rank_str', r.get('rank', '?'))) for r in horse_basic_info.get('race_results', [])[:3]]
                current_horse_gui_info['近3走'] = "/".join(recent_ranks) if recent_ranks else 'N/A'
                current_horse_gui_info['予測確率'] = round(predicted_proba, 4) if pd.notna(predicted_proba) else None
                current_horse_gui_info['期待値'] = round(expected_value_win, 2) if pd.notna(expected_value_win) else None
                current_horse_gui_info['error_detail'] = error_detail_calc
                horse_details_list_for_gui.append(current_horse_gui_info)

            # 5. 結果のソートとGUI更新
            horse_details_list_for_gui.sort(key=lambda x: (x.get('error_detail') is not None, -x.get('予測確率', 0) if pd.notna(x.get('予測確率')) else 0))
            
            self.root.after(0, lambda text=race_info_text: self.race_info_label.config(text=text))
            self.root.after(0, lambda text=race_details_text: self.race_details_label.config(text=text))
            self.root.after(0, self._update_prediction_table, horse_details_list_for_gui)
            
            recommendation_text = self.create_recommendation_text(horse_details_list_for_gui)
            if hasattr(self, 'recommendation_text') and self.recommendation_text.winfo_exists():
                self.root.after(0, lambda: self.recommendation_text.delete(1.0, tk.END))
                self.root.after(0, lambda: self.recommendation_text.insert(tk.END, recommendation_text))
            
            self.root.after(0, lambda: self.update_status(f"予測完了: {race_id}"))

        except Exception as e_main_fetch:
            print(f"!!! FATAL ERROR in _fetch_race_info_thread for race_id {race_id} !!!"); traceback.print_exc()
            self.root.after(0, lambda err=e_main_fetch: messagebox.showerror("予測処理エラー", f"レース情報の取得・予測処理中に予期せぬエラーが発生しました:\n{type(err).__name__}: {err}"))
            self.root.after(0, lambda err=e_main_fetch: self.update_status(f"致命的エラー: 予測処理失敗 ({type(err).__name__})"))
    
    def _update_prediction_table(self, horses_info):
        """
        予測タブの出走馬テーブルを更新 (血統・近走・予測確率表示)
        エラーハンドリングとログ出力を大幅に強化。
        """
        print(f"--- _update_prediction_table: START (Received {len(horses_info) if horses_info else 0} horses) ---")
        try:
            if not hasattr(self, 'prediction_tree') or not self.prediction_tree.winfo_exists():
                print("ERROR: _update_prediction_table: self.prediction_tree widget does not exist or has been destroyed. Cannot update table.")
                self.update_status("エラー: 予測テーブル描画失敗 (ウィジェット無)")
                return

            # テーブルクリア
            print("DEBUG: _update_prediction_table: Clearing existing items from prediction_tree...")
            try:
                # ウィジェットが存在することを確認してから子要素を削除
                if self.prediction_tree.winfo_exists():
                    existing_items = self.prediction_tree.get_children()
                    if existing_items:
                        self.prediction_tree.delete(*existing_items)
                    print(f"DEBUG: _update_prediction_table: Cleared {len(existing_items)} items from prediction_tree.")
                else:
                    print("WARN: _update_prediction_table: prediction_tree widget destroyed before clearing items.")
                    return # テーブルがなければ処理中断
            except Exception as e_clear:
                print(f"ERROR: _update_prediction_table: Failed to clear prediction_tree: {e_clear}")
                traceback.print_exc()
                # クリアに失敗しても、可能な限り処理を続けるか、ここでreturnするか検討
                # return 

            if not horses_info:
                print("INFO: _update_prediction_table: 表示する出走馬情報がありません。")
                if self.prediction_tree.winfo_exists():
                    self.prediction_tree["columns"] = []
                    self.prediction_tree["displaycolumns"] = [] 
                print("DEBUG: _update_prediction_table: END (no horses_info)")
                return

            # === 列定義と設定 ===
            columns = ["Umaban", "HorseName", "SexAge", "Load", "JockeyName", "Odds", "father", "mother_father", "近3走", "予測確率", "error_detail"]
            print(f"DEBUG: _update_prediction_table: Setting columns: {columns}")
            if self.prediction_tree.winfo_exists():
                self.prediction_tree["columns"] = columns
                self.prediction_tree["show"] = "headings"

                col_settings = {
                    "Umaban": {"text": "馬番", "width": 40, "anchor": tk.CENTER, "stretch": tk.NO},
                    "HorseName": {"text": "馬名", "width": 120, "anchor": tk.W, "stretch": tk.YES},
                    "SexAge": {"text": "性齢", "width": 50, "anchor": tk.CENTER, "stretch": tk.NO},
                    "Load": {"text": "斤量", "width": 50, "anchor": tk.E, "stretch": tk.NO},
                    "JockeyName": {"text": "騎手", "width": 80, "anchor": tk.W, "stretch": tk.NO},
                    "Odds": {"text": "単勝", "width": 60, "anchor": tk.E, "stretch": tk.NO},
                    "father": {"text": "父", "width": 120, "anchor": tk.W, "stretch": tk.NO},
                    "mother_father": {"text": "母父", "width": 120, "anchor": tk.W, "stretch": tk.NO},
                    "近3走": {"text": "近3走", "width": 70, "anchor": tk.CENTER, "stretch": tk.NO},
                    "予測確率": {"text": "予測確率", "width": 70, "anchor": tk.E, "stretch": tk.NO},
                    "error_detail": {"text": "エラー詳細", "width": 100, "anchor": tk.W, "stretch": tk.NO}
                }

                for col_id, setting in col_settings.items():
                    if col_id in columns: 
                        self.prediction_tree.column(col_id, width=setting["width"], anchor=setting["anchor"], stretch=setting.get("stretch", tk.NO))
                        self.prediction_tree.heading(col_id, text=setting["text"])
                print("DEBUG: _update_prediction_table: Columns and headings configured.")
            else:
                print("WARN: _update_prediction_table: prediction_tree widget does not exist. Cannot configure columns.")
                return

            # === データ追加 ===
            print(f"DEBUG: _update_prediction_table: Adding {len(horses_info)} horses to the table...")
            for i, horse_data in enumerate(horses_info):
                if not self.prediction_tree.winfo_exists():
                    print(f"ERROR: _update_prediction_table: prediction_tree destroyed during data insertion loop (horse {i+1}). Aborting.")
                    return

                # print(f"DEBUG: _update_prediction_table: Processing horse {i+1}: Umaban={horse_data.get('Umaban')}, Name={horse_data.get('HorseName')}")
                
                try:
                    umaban = str(horse_data.get("Umaban", ''))
                    horse_name = str(horse_data.get("HorseName", 'N/A'))
                    sex_age = str(horse_data.get("SexAge", 'N/A'))
                    load = str(horse_data.get("Load", 'N/A'))
                    jockey = str(horse_data.get("JockeyName", 'N/A'))
                    
                    odds_val = horse_data.get('Odds')
                    odds_display = f"{float(odds_val):.1f}" if pd.notna(odds_val) and isinstance(odds_val, (int, float, np.number)) else str(odds_val if pd.notna(odds_val) else 'N/A')

                    father_name = str(horse_data.get("father", 'N/A'))
                    mother_father_name = str(horse_data.get("mother_father", 'N/A'))
                    recent_3 = str(horse_data.get("近3走", 'N/A'))
                    
                    pred_proba_val = horse_data.get('予測確率')
                    pred_proba_display = 'N/A' # デフォルト
                    if horse_data.get('error_detail'):
                        pred_proba_display = 'エラー'
                    elif pd.notna(pred_proba_val):
                        try:
                            pred_proba_display = f"{float(pred_proba_val):.4f}" # NumPyの型も考慮
                        except (ValueError, TypeError):
                            pred_proba_display = '変換エラー' 
                            print(f"WARN: _update_prediction_table: Failed to format 予測確率 for Umaban {umaban}: {pred_proba_val}")

                    error_text = str(horse_data.get("error_detail", ''))

                    display_values = [
                        umaban, horse_name, sex_age, load, jockey, odds_display,
                        father_name, mother_father_name, recent_3, pred_proba_display, error_text
                    ]
                    
                    item_id = str(umaban) if umaban else f"no_umaban_{i}" # 馬番を基本IDに
                    unique_item_id = item_id
                    id_suffix = 0
                    while self.prediction_tree.exists(unique_item_id): # 万が一IDが重複したら末尾に数字を追加
                        id_suffix += 1
                        unique_item_id = f"{item_id}_{id_suffix}"
                    
                    # print(f"DEBUG: _update_prediction_table: Inserting item with iid='{unique_item_id}'")
                    self.prediction_tree.insert("", "end", values=display_values, iid=unique_item_id)

                except Exception as e_insert_row:
                    print(f"!!! ERROR: _update_prediction_table: Failed to process or insert row for horse {i+1} (Umaban: {horse_data.get('Umaban')}) !!!")
                    print(f"  Row data: {horse_data}")
                    print(f"  Error: {type(e_insert_row).__name__}: {e_insert_row}")
                    traceback.print_exc()
                    # 1行のエラーで全体を止めないようにする (ただし、根本原因の調査は必要)
                    try: # エラー情報をテーブルに表示する試み
                        error_display_values = [str(horse_data.get("Umaban", 'ERR')), "行処理エラー", "", "", "", "", "", "", "", "", str(e_insert_row)[:50]]
                        err_item_id = f"error_row_{i}"
                        if not self.prediction_tree.exists(err_item_id):
                             self.prediction_tree.insert("", "end", values=error_display_values, iid=err_item_id)
                    except:
                        pass # これ以上エラーを重ねない

            print(f"DEBUG: _update_prediction_table: Finished adding data to table. Total items: {len(self.prediction_tree.get_children())}")
            self.update_status(f"予測結果をテーブルに表示しました ({len(horses_info)}件)")

        except Exception as e_table_update_main:
            print(f"!!! FATAL ERROR in _update_prediction_table (main try-except) !!!")
            traceback.print_exc()
            try:
                messagebox.showerror("テーブル更新エラー", f"予測結果テーブルの更新中に予期せぬエラーが発生しました:\n{type(e_table_update_main).__name__}: {e_table_update_main}")
            except Exception as e_msgbox:
                print(f"ERROR: Failed to show error messagebox in _update_prediction_table: {e_msgbox}")
            self.update_status(f"エラー: テーブル更新失敗 ({type(e_table_update_main).__name__})")
        finally:
            print(f"--- _update_prediction_table: END ---")

    def create_recommendation_text(self, horses_info):
        """
        予測結果リストから、期待値に基づいた推奨買い目テキストを生成する。
        【改修】表示前に各値を数値に変換する処理を追加し、書式設定エラーを解消。
        """
        # 設定値を取得（設定タブで変更可能）
        min_expected_value = float(self.settings.get("min_expected_value", 1.2))
        
        recommendations = []
        for horse in horses_info:
            ev = horse.get('期待値')
            if pd.notna(ev) and ev >= min_expected_value:
                recommendations.append(horse)
        
        if not recommendations:
            return f"単勝期待値が {min_expected_value:.2f} を超える馬券は見つかりませんでした。"
            
        # 期待値の高い順にソート
        recommendations.sort(key=lambda x: x.get('期待値', 0), reverse=True)
        
        text = f"【推奨買い目 (単勝期待値 > {min_expected_value:.2f})】\n"
        text += "----------------------------------\n"
        for rec in recommendations:
            umaban = rec.get('Umaban', '?')
            name = rec.get('HorseName', '不明')
            
            # ★★★★★★★★★★★★ エラー修正箇所 ★★★★★★★★★★★★
            # 表示する前に、各値をfloat()で数値に変換する
            # 万が一、数値に変換できない値（例: 'N/A'）が入っていてもエラーにならないように try-except を使用
            try:
                odds = float(rec.get('Odds', 0.0))
            except (ValueError, TypeError):
                odds = 0.0
            
            try:
                proba = float(rec.get('予測確率', 0.0))
            except (ValueError, TypeError):
                proba = 0.0
            
            try:
                ev = float(rec.get('期待値', 0.0))
            except (ValueError, TypeError):
                ev = 0.0
            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

            text += f"◎ 馬番: {umaban} {name}\n"
            text += f"   単勝オッズ: {odds:.1f} 倍\n"
            text += f"   予測確率(参考): {proba:.2%}\n"
            text += f"   単勝期待値: {ev:.2f}\n"
            text += "----------------------------------\n"
            
        return text

    def prepare_data_for_backtest(self):
        """
        バックテスト用に、読み込んだデータ全体に予測確率を付与する。
        【バグ修正】_prepare_data_for_modelの戻り値(タプル)を正しく受け取るように修正。
        """
        self.update_status("バックテスト用データ準備中: 全レースの特徴量を計算...")
        print("INFO: バックテスト用データ準備中...")

        if self.combined_data is None or self.combined_data.empty:
            messagebox.showerror("データエラー", "バックテストの元になるデータがありません。")
            return None
        
        if self.trained_model is None or not self.model_features:
            messagebox.showerror("モデルエラー", "学習済みモデルまたは特徴量リストが読み込まれていません。")
            return None

        try:
            # ★★★★★★★★★★★★ エラー修正箇所 ★★★★★★★★★★★★
            # _prepare_data_for_modelが返す2つの値を、2つの変数で正しく受け取る
            featured_data, target_column_name = self._prepare_data_for_model(target_mode='win')
            
            # 受け取ったデータが空でないかチェック
            if featured_data is None or featured_data.empty:
                messagebox.showerror("特徴量生成エラー", "バックテスト用の特徴量生成に失敗しました。")
                return None
            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

            # ターゲット列（正解ラベル）は予測に不要なので、一旦除外
            X = featured_data.drop(columns=[target_column_name], errors='ignore')

            # ダミー変数化と列の整合性確保
            if 'prev_race_track_type_1ago' in X.columns:
                X = pd.get_dummies(X, columns=['prev_race_track_type_1ago'], prefix='prev_track_type', dummy_na=True)
            if '距離区分' in X.columns:
                distance_map = {'1400m以下': 0, '1401-1800m': 1, '1801-2200m': 2, '2201-2600m': 3, '2601m以上': 4}
                X['距離区分'] = X['距離区分'].map(distance_map)

            for col in self.model_features:
                if col not in X.columns:
                    X[col] = 0
            
            X = X[self.model_features]
            
            # 全データに対して予測確率を一括計算
            print(f"INFO: {len(X)}件のデータに対して予測確率を計算します...")
            self.update_status("全レースの予測値を一括計算中...")
            probabilities = self.trained_model.predict_proba(X)[:, 1]
            
            # 元のデータに予測確率を新しい列として結合（マージ）する
            featured_data['predicted_proba'] = probabilities
            
            merge_cols = ['race_id', 'horse_id', 'predicted_proba']
            if not all(k in featured_data.columns for k in ['race_id', 'horse_id']):
                self.combined_data.reset_index(drop=True, inplace=True)
                featured_data.reset_index(drop=True, inplace=True)
                backtest_df = self.combined_data.join(featured_data[merge_cols])
            else:
                self.combined_data['race_id'] = self.combined_data['race_id'].astype(str)
                self.combined_data['horse_id'] = self.combined_data['horse_id'].astype(str)
                featured_data['race_id'] = featured_data['race_id'].astype(str)
                featured_data['horse_id'] = featured_data['horse_id'].astype(str)
                backtest_df = pd.merge(self.combined_data, featured_data[merge_cols], on=['race_id', 'horse_id'], how='left')
            
            print("INFO: バックテスト用データの準備が完了しました。")
            self.update_status("バックテスト用データ準備完了。")
            
            return backtest_df

        except Exception as e:
            print(f"!!! ERROR in prepare_data_for_backtest: {e}")
            traceback.print_exc()
            messagebox.showerror("バックテスト準備エラー", f"バックテスト用データの準備中にエラーが発生しました:\n{e}")
            return None

    def run_prediction(self):
        """予測実行処理"""
        # レース情報が表示されているか（出走馬テーブルにデータがあるか）確認
        # このチェックは _fetch_race_info_thread 実行前には不要かもしれません。
        # race_id さえあれば _fetch_race_info_thread が情報を取得するため。
        # if not self.prediction_tree.get_children():
        #     messagebox.showwarning("予測実行", "予測対象のレース情報が表示されていません。\nレースIDを入力して「レース情報表示」ボタンを押してください。")
        #     return

        # 学習済みモデルの存在チェックは _fetch_race_info_thread 側で行っています。
        # if self.model is None: # self.model ではなく self.trained_model を想定
        #     messagebox.showwarning("予測実行", "予測モデルがロードされていません。\n設定タブでモデルをロードするか、学習させてください。")
        #     return

        # 予測タブにあるレースID入力フィールドから race_id を取得
        race_id = self.predict_race_id_var.get()
        if not race_id:
            messagebox.showerror("エラー", "レースIDが入力されていません。\n予測タブの「レースID」フィールドにIDを入力してください。")
            self.update_status("エラー: レースID未入力")
            return

        # prediction_type_var (win, utan, santan など) は、現在の _fetch_race_info_thread では
        # 直接使用されていません。_fetch_race_info_thread は主に「3着以内確率」を計算します。
        # もしこれらの券種別の予測を将来的に実装する場合は、_fetch_race_info_thread の改修や
        # 別途専用の予測ロジックが必要になります。
        prediction_type = self.prediction_type_var.get()
        self.update_status(f"レースID {race_id} の {prediction_type} 予測準備中...") # ステータス表示を少し変更

        # テーブルから現在の出走馬情報を取得する部分は、_fetch_race_info_thread が
        # race_id を元に情報を取得し直すため、ここでは不要になります。
        # horses_on_table = []
        # ... (中略) ...
        # if not horses_on_table:
        #     messagebox.showerror("予測エラー", "出走馬情報が見つかりません。")
        #     self.update_status("エラー: 出走馬情報なし")
        #     return

        # 既存の _fetch_race_info_thread を呼び出して予測処理を実行します。
        # このメソッドは引数として race_id を取ります。
        self.update_status(f"レースID {race_id} の予測実行中...")
        self.run_in_thread(self._fetch_race_info_thread, race_id) # 第2引数 horses_on_table は不要
        # ↑↑↑ 修正案ここまで ↑↑↑

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
    
    def run_result_analysis(self):
        """
        結果分析（バックテスト）実行処理。
        【改修】ボックス買い戦略に合わせて、馬連・ワイドのチェックボックスを見るように修正。
        """
        if self.processed_data is None or self.processed_data.empty:
             messagebox.showwarning("バックテスト実行", "分析対象のデータが読み込まれていません。\nデータ管理タブでデータを読み込んでください。")
             return

        if self.trained_model is None:
            messagebox.showwarning("バックテスト実行", "予測モデルがロードされていません。")
            return

        analysis_type = self.result_type_var.get()
        self.update_status(f"バックテスト実行準備中 ({analysis_type})...")

        try:
             start_date_str = f"{self.result_from_year_var.get()}-{self.result_from_month_var.get()}-01"
             end_year = int(self.result_to_year_var.get())
             end_month = int(self.result_to_month_var.get())
             import calendar
             last_day = calendar.monthrange(end_year, end_month)[1]
             end_date_str = f"{end_year:04d}-{end_month:02d}-{last_day:02d}"
             start_dt = pd.to_datetime(start_date_str)
             end_dt = pd.to_datetime(end_date_str)
        except ValueError:
            messagebox.showerror("日付エラー", "バックテスト期間の形式が正しくありません。"); return

        # ★★★★★★★★★★★★ エラー修正箇所 ★★★★★★★★★★★★
        # チェックする対象を、新しい戦略で使う「馬連」と「ワイド」に変更
        bet_types_to_run = {
            "uren": self.res_uren_var.get(),
            "wide": self.res_wide_var.get()
        }
        
        # エラーメッセージも新しい戦略に合わせて変更
        if not any(bet_types_to_run.values()):
            messagebox.showwarning("バックテスト実行", "対象の馬券種（馬連またはワイド）が選択されていません。")
            return
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
        
        # バックテスト実行（スレッド）
        # 呼び出すスレッド（_run_result_analysis_thread）は前回修正済みのため、ここは変更なし
        self.run_in_thread(self._run_result_analysis_thread, start_dt, end_dt, bet_types_to_run, analysis_type)
    
    def _run_result_analysis_thread(self, start_dt, end_dt, bet_types_to_run, analysis_type):
        """
        【デバッグモード】
        format_payout_dataで整形された払い戻しデータが正しいか、
        当たり判定ロジックがそれを正しく解釈できているかを確認する。
        """
        import time
        import pandas as pd
        import numpy as np
        import traceback
        from itertools import combinations

        try:
            start_time = time.time()
            
            # モデルのロードとバックテストデータの準備
            self.load_model_from_file(model_filename="trained_lgbm_model_win.pkl")
            if self.trained_model is None:
                messagebox.showerror("モデルエラー", "単勝予測モデル 'trained_lgbm_model_win.pkl' が見つかりません。")
                return
            
            backtest_df_with_pred = self.prepare_data_for_backtest()
            if backtest_df_with_pred is None:
                self.root.after(0, self.update_status, "エラー: バックテスト準備失敗")
                return

            date_col = 'date' if 'date' in backtest_df_with_pred.columns else 'race_date'
            sim_data = backtest_df_with_pred[
                (pd.to_datetime(backtest_df_with_pred[date_col], errors='coerce') >= start_dt) & 
                (pd.to_datetime(backtest_df_with_pred[date_col], errors='coerce') <= end_dt)
            ].copy()

            if sim_data.empty:
                self.root.after(0, lambda: messagebox.showinfo("バックテスト結果", "指定期間のレースデータがありません。"))
                return

            payout_dict_for_sim = {str(p['race_id']): p for p in self.payout_data if 'race_id' in p}
            sim_data['race_id'] = sim_data['race_id'].astype(str)
            unique_race_ids = sim_data['race_id'].unique()
            
            # ★★★★★★★★★★★★ ここからデバッグモード ★★★★★★★★★★★★
            print("\n" + "="*80)
            print("【バックテスト・デバッグモード開始】")
            print("いくつかのレースについて、当たり判定の内部データを確認します。")
            print("="*80 + "\n")
            
            debug_count = 0
            N_TOP_HORSES = 3

            for race_id in unique_race_ids:
                if debug_count >= 5: # 5レース分表示したら終了
                    break

                race_df = sim_data[sim_data['race_id'] == race_id]
                if len(race_df) < N_TOP_HORSES: continue

                top_n_horses = race_df.sort_values('predicted_proba', ascending=False).head(N_TOP_HORSES)
                top_n_umabans = [int(u) for u in top_n_horses['Umaban']]
                bet_combinations = list(combinations(top_n_umabans, 2))
                bet_combos_set = [set(c) for c in bet_combinations]

                payout_info = payout_dict_for_sim.get(race_id, {})
                
                print(f"--- [デバッグ対象レース] RACE ID: {race_id} ---")
                print(f"  [AI予測] 上位3頭の馬番: {top_n_umabans}")
                print(f"  [購入馬券] 組み合わせ: {bet_combos_set}")
                print(f"  [参照データ] このレースの払い戻し情報:")
                if not payout_info:
                    print("    -> 払い戻し情報が見つかりません。")
                else:
                    for key, value in payout_info.items():
                        if key != 'race_id':
                            print(f"    -> {key}: {value}")
                
                # 馬連の当たり判定デバッグ
                if '馬連' in payout_info and payout_info['馬連'].get('馬番'):
                    try:
                        win_combo_uren_str = payout_info['馬連']['馬番'][0]
                        win_combo_uren = set(map(int, win_combo_uren_str.split('-')))
                        is_hit_uren = win_combo_uren in bet_combos_set
                        print(f"  [馬連判定] 正解: {win_combo_uren} -> 的中: {is_hit_uren}")
                    except Exception as e:
                        print(f"  [馬連判定] 正解データの解析エラー: {e}")
                else:
                    print("  [馬連判定] -> 馬連の払い戻しデータなし")
                
                # ワイドの当たり判定デバッグ
                if 'ワイド' in payout_info and payout_info['ワイド'].get('馬番'):
                    try:
                        win_combos_wide_str = payout_info['ワイド']['馬番']
                        win_combos_wide = [set(map(int, c.split('-'))) for c in win_combos_wide_str]
                        hits = [bc for bc in bet_combos_set if bc in win_combos_wide]
                        print(f"  [ワイド判定] 正解: {win_combos_wide} -> 的中: {hits if hits else 'なし'}")
                    except Exception as e:
                        print(f"  [ワイド判定] 正解データの解析エラー: {e}")
                else:
                    print("  [ワイド判定] -> ワイドの払い戻しデータなし")

                print("-" * 50)
                debug_count += 1
            
            print("\n" + "="*80)
            print("【デバッグモード終了】")
            print("="*80 + "\n")
            
            self.root.after(0, lambda: messagebox.showinfo("デバッグ完了", "当たり判定のデバッグ情報をコンソールに出力しました。\nお手数ですが、コンソールの内容をコピーしてご提供ください。"))
            self.root.after(0, lambda: self.update_status("デバッグ完了"))
            return 
            # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
        
        except Exception as e:
            print(f"!!! Error in _run_result_analysis_thread !!!"); traceback.print_exc()
            self.root.after(0, lambda err=e: messagebox.showerror("バックテストエラー", f"バックテスト実行中にエラーが発生しました:\n{err}"))
 
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

def create_recommendation_text(self, horses_info):
        """
        予測結果リストから、期待値に基づいた推奨買い目テキストを生成する。
        """
        # 設定値を取得（設定タブで変更可能）
        min_expected_value = float(self.settings.get("min_expected_value", 1.2))
        
        recommendations = []
        for horse in horses_info:
            ev = horse.get('期待値')
            if pd.notna(ev) and ev >= min_expected_value:
                recommendations.append(horse)
        
        if not recommendations:
            return f"単勝期待値が {min_expected_value:.2f} を超える馬券は見つかりませんでした。"
            
        # 期待値の高い順にソート
        recommendations.sort(key=lambda x: x.get('期待値', 0), reverse=True)
        
        text = f"【推奨買い目 (単勝期待値 > {min_expected_value:.2f})】\n"
        text += "----------------------------------\n"
        for rec in recommendations:
            umaban = rec.get('Umaban', '?')
            name = rec.get('HorseName', '不明')
            odds = rec.get('Odds', 0)
            proba = rec.get('予測確率', 0)
            ev = rec.get('期待値', 0)
            text += f"◎ 馬番: {umaban} {name}\n"
            text += f"   単勝オッズ: {odds:.1f} 倍\n"
            text += f"   予測確率(参考): {proba:.2%}\n"
            text += f"   単勝期待値: {ev:.2f}\n"
            text += "----------------------------------\n"
            
        return text

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

