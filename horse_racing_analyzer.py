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
    
    def get_shutuba_table(self, race_id):
        """
        【人気取得ロジック修正版】
        shutuba_past.html から出馬表テーブルデータとレース共通情報を取得する。
        """
        url = f'https://race.netkeiba.com/race/shutuba_past.html?race_id={race_id}'
        print(f"      出馬表(共通情報付)取得試行: {url}")
        driver = None
        options = webdriver.ChromeOptions()
        options.add_argument(f'--user-agent={self.USER_AGENT}')
        options.add_argument('--headless')
        options.add_argument('--disable-gpu'); options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage'); options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        horse_data_list = []
        race_common_info = { 
            'race_id': race_id, 'RaceName': 'N/A', 'RaceDate': None, 'TrackName': 'N/A',
            'CourseType': 'N/A', 'Distance': None, 'Weather': 'N/A', 'TrackCondition': 'N/A',
            'RaceNum': 'N/A', 'Around': 'N/A'
        }

        try:
            if self.CHROME_DRIVER_PATH and os.path.exists(self.CHROME_DRIVER_PATH):
                service = ChromeService(executable_path=self.CHROME_DRIVER_PATH)
                driver = webdriver.Chrome(service=service, options=options)
            else:
                print("        警告: ChromeDriverのパスが設定されていないか無効です。環境変数PATHから探します。")
                driver = webdriver.Chrome(options=options)
            
            driver.set_page_load_timeout(60) 
            driver.get(url)
            time.sleep(self.SLEEP_TIME_PER_PAGE)
            soup = BeautifulSoup(driver.page_source, 'lxml')

            # === レース開催日の取得ロジック ===
            try:
                active_date_link_selector = "dl#RaceList_DateList dd.Active > a"
                active_date_tag = soup.select_one(active_date_link_selector)
                
                if active_date_tag and active_date_tag.has_attr('href'):
                    href_value = active_date_tag['href']
                    date_param_match = re.search(r'kaisai_date=(\d{8})', href_value)
                    if date_param_match:
                        yyyymmdd = date_param_match.group(1)
                        race_common_info['RaceDate'] = f"{yyyymmdd[0:4]}年{yyyymmdd[4:6]}月{yyyymmdd[6:8]}日"
                        print(f"INFO: ページの日付ナビゲーション(Active)から開催日を取得しました: {race_common_info['RaceDate']}")
            except Exception as e_date_nav:
                print(f"ERROR: 日付ナビゲーションからの日付取得中にエラー: {e_date_nav}")

            if race_common_info.get('RaceDate') is None:
                if len(race_id) >= 8:
                    year, month, day = race_id[0:4], race_id[4:6], race_id[6:8]
                    race_common_info['RaceDate'] = f"{year}年{month}月{day}日"

            # === レースヘッダーからの情報取得 ===
            race_header_element = soup.select_one("div.RaceList_NameBox")
            if race_header_element:
                try:
                    race_name_tag = race_header_element.select_one("div.RaceList_Item02 > h1.RaceName")
                    if race_name_tag:
                        race_common_info['RaceName'] = race_name_tag.get_text(strip=True)
                except Exception as e: print(f"        警告: レース名の取得に失敗: {e}")

                try:
                    race_num_tag = race_header_element.select_one("div.RaceList_Item01 > span.RaceNum")
                    if race_num_tag:
                        race_common_info['RaceNum'] = race_num_tag.get_text(strip=True).replace('R', '')
                except Exception as e: print(f"        警告: レース番号の取得に失敗: {e}")

                try:
                    race_data01_tag = race_header_element.select_one("div.RaceList_Item02 > div.RaceData01")
                    if race_data01_tag:
                        text_data01_full = race_data01_tag.get_text(separator=" ", strip=True)
                        course_match = re.search(r"(芝|ダ|障)\s*(\d+)m", text_data01_full)
                        if course_match:
                            race_common_info['CourseType'] = course_match.group(1)
                            race_common_info['Distance'] = int(course_match.group(2))
                        around_match = re.search(r"\((左|右|直)\)", text_data01_full)
                        if around_match: race_common_info['Around'] = around_match.group(1)
                        weather_match = re.search(r"天候\s*:\s*(\S+)", text_data01_full)
                        if weather_match: race_common_info['Weather'] = weather_match.group(1)
                        track_cond_match = re.search(r"馬場\s*:\s*(\S+)", text_data01_full)
                        if track_cond_match: race_common_info['TrackCondition'] = track_cond_match.group(1)
                except Exception as e: print(f"        警告: RaceData01 (コース等) の正規表現解析に失敗: {e}")

                try:
                    race_data02_tag = race_header_element.select_one("div.RaceList_Item02 > div.RaceData02")
                    if race_data02_tag:
                        track_name_match = re.search(r'\d+回\s*(\S+?)\s*\d+日目', race_data02_tag.get_text(strip=True))
                        if track_name_match:
                            race_common_info['TrackName'] = track_name_match.group(1)
                except Exception as e: print(f"        警告: RaceData02 (場所) の解析に失敗: {e}")
            
            # --- 出走馬テーブルの取得 ---
            table_tag = soup.select_one('.Shutuba_Table.Shutuba_Past5_Table') 
            if not table_tag:
                return {'race_details': race_common_info, 'horse_list': []} 

            horse_rows = table_tag.select('tbody > tr.HorseList')

            for i, row_tag in enumerate(horse_rows):
                row_data = {'race_id': race_id}
                cells = row_tag.select('td')
                try:
                    waku_index = 0; umaban_index = 1; horse_info_cell_index = 3; jockey_cell_index = 4
                    
                    if len(cells) > umaban_index: row_data['Umaban'] = cells[umaban_index].get_text(strip=True)
                    if len(cells) > waku_index: row_data['Waku'] = cells[waku_index].get_text(strip=True)
                    
                    if len(cells) > horse_info_cell_index:
                        horse_info_td = cells[horse_info_cell_index]
                        
                        horse_link = horse_info_td.select_one('div.Horse02 > a')
                        if horse_link:
                            row_data['HorseName'] = horse_link.get_text(strip=True)
                            horse_url = horse_link.get('href')
                            horse_id_match = re.search(r'/horse/(\d+)', str(horse_url))
                            if horse_id_match:
                                row_data['horse_id'] = horse_id_match.group(1)
                        
                        father_tag = horse_info_td.select_one('div.Horse01')
                        if father_tag: row_data['father'] = father_tag.get_text(strip=True)
                        
                        mf_tag = horse_info_td.select_one('div.Horse04')
                        if mf_tag: row_data['mother_father'] = mf_tag.get_text(strip=True).strip("()")
                        
                        odds_span = horse_info_td.select_one('div.Popular > span[id^="odds-"]')
                        if odds_span: row_data['Odds'] = odds_span.get_text(strip=True)

                        # ★★★★★★★★★★★★ ここが今回の修正ポイント ★★★★★★★★★★★★
                        # 人気のデータを取得するコードを有効化します
                        popular_div = horse_info_td.select_one('div.Popular')
                        if popular_div:
                           popular_text = popular_div.get_text(strip=True)
                           ninki_match = re.search(r'(\d+)人気', popular_text)
                           if ninki_match:
                               row_data['NinkiShutuba'] = ninki_match.group(1)
                        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
                    
                    if len(cells) > jockey_cell_index:
                        jockey_td = cells[jockey_cell_index]
                        row_data['SexAge'] = jockey_td.select_one('span.Barei').get_text(strip=True) if jockey_td.select_one('span.Barei') else None
                        row_data['JockeyName'] = jockey_td.select_one('a').get_text(strip=True) if jockey_td.select_one('a') else None
                        load_spans = jockey_td.select('span') 
                        row_data['Load'] = load_spans[-1].get_text(strip=True) if load_spans else None

                    horse_data_list.append(row_data)
                except Exception as e_row:
                    print(f"        ERROR: Error processing row {i+1} in get_shutuba_table: {e_row}")
        
        except Exception as e:
            traceback.print_exc()
        finally:
            if driver:
                driver.quit()

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
    
    def get_horse_details(self, horse_id):
        """【JRA実績分析対応版】馬の個別ページから詳細情報を取得し、JRAでの戦績を特別に分析・整形して返す"""
        if not horse_id or not str(horse_id).isdigit():
            print(f"      警告: 無効な馬IDです: {horse_id}")
            return {'horse_id': horse_id, 'error': 'Invalid horse_id'}

        url = f'https://db.netkeiba.com/horse/{horse_id}/'
        print(f"      馬詳細取得試行: {url} (get_horse_details)")
        headers = {'User-Agent': self.USER_AGENT}
        horse_details = {'horse_id': horse_id} 

        try:
            time.sleep(0.5) 

            r = requests.get(url, headers=headers, timeout=self.REQUEST_TIMEOUT)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.content, 'lxml')

            # --- プロフィール情報抽出 (変更なし) ---
            profile_table = soup.select_one('table.db_prof_table')
            if profile_table:
                 for row in profile_table.find_all('tr'):
                     th = row.find('th')
                     td = row.find('td')
                     if th and td:
                         header_text = th.get_text(strip=True)
                         value_text = td.get_text(strip=True)
                         if '生年月日' in header_text: horse_details['birthday'] = value_text
                         elif '調教師' in header_text: horse_details['trainer_prof'] = value_text
                         elif '馬主' in header_text: horse_details['owner_prof'] = value_text
                         elif '生産者' in header_text: horse_details['breeder'] = value_text
                         elif '産地' in header_text: horse_details['birthplace'] = value_text
                         elif 'セリ取引価格' in header_text: horse_details['market_price'] = value_text
                         elif '獲得賞金' in header_text:
                            prize_match = re.search(r'([\d,]+)万円', value_text)
                            if prize_match:
                                horse_details['total_prize'] = pd.to_numeric(prize_match.group(1).replace(',', ''), errors='coerce')
                            else:
                                horse_details['total_prize'] = pd.to_numeric(value_text.replace(',', '').replace('万円',''), errors='coerce')
                         elif '通算成績' in header_text: horse_details['total_成績'] = value_text
                         elif '主な勝鞍' in header_text: horse_details['main_wins'] = value_text
            
            # --- 血統情報抽出 (変更なし) ---
            blood_table = soup.select_one('table.blood_table')
            if blood_table:
                father_tag = blood_table.select_one('tr:nth-of-type(1) td:nth-of-type(1) a')
                horse_details['father'] = father_tag.get_text(strip=True) if father_tag else None
                mother_father_tag = blood_table.select_one('tr:nth-of-type(3) td:nth-of-type(2) a')
                horse_details['mother_father'] = mother_father_tag.get_text(strip=True) if mother_father_tag else None

            # === ★★★ ここからが修正・追加部分 ★★★ ===
            race_results_list = []
            results_table = soup.select_one('table.db_h_race_results')

            if results_table:
                rows = results_table.select('tbody tr')
                if not rows: rows = results_table.select('tr')[1:]

                for i, row in enumerate(rows):
                    cells = row.find_all('td')
                    if len(cells) < 23: continue # 最低限の列数チェック

                    kaisai_str = cells[1].get_text(strip=True)
                    place_match = re.search(r'(\D+)', kaisai_str.replace(' ',''))
                    place = place_match.group(1) if place_match else kaisai_str
                    
                    race_result = {
                        'date': pd.to_datetime(cells[0].get_text(strip=True), format='%Y/%m/%d', errors='coerce'),
                        'place': place,
                        'rank': pd.to_numeric(cells[11].get_text(strip=True), errors='coerce'),
                        # (他の戦績データもここで取得・整形)
                    }
                    race_results_list.append(race_result)

                # --- 地方転入馬関連情報とJRA戦績の追加 ---
                if race_results_list:
                    first_past_race = race_results_list[0] # 最新の過去走
                    prev_place = first_past_race.get('place')
                    # 前走が地方競馬かどうかのフラグ
                    if prev_place and prev_place not in self.JRA_TRACKS:
                        horse_details['is_transfer_from_local_1ago'] = 1
                    else:
                        horse_details['is_transfer_from_local_1ago'] = 0
                    
                    # JRAでの戦績のみを抽出
                    jra_results_for_horse = [r for r in race_results_list if isinstance(r, dict) and r.get('place') in self.JRA_TRACKS]
                    horse_details['jra_race_results'] = jra_results_for_horse
                    horse_details['num_jra_starts'] = len(jra_results_for_horse)
                else: # 過去走データがない新馬などの場合
                    horse_details['is_transfer_from_local_1ago'] = 0
                    horse_details['jra_race_results'] = []
                    horse_details['num_jra_starts'] = 0

                horse_details['race_results'] = race_results_list # 全戦績も保持
            else: # 戦績テーブル自体がない場合
                horse_details['race_results'] = []
                horse_details['is_transfer_from_local_1ago'] = 0
                horse_details['jra_race_results'] = []
                horse_details['num_jra_starts'] = 0
            # === ★★★ 修正・追加ここまで ★★★ ===

        except Exception as e:
            traceback.print_exc()
            horse_details['error'] = f'Unexpected Error: {e}'

        return horse_details
    
    def calculate_original_index(self, horse_details, race_conditions, race_members_df=None):
        """
        【最終進化版】展開・時計・馬場・経歴の全てを考慮する特徴量エンジン
        """
        features = {
            # --- 既存の特徴量 ---
            'Umaban': np.nan, 'HorseName': '', 'Sex': np.nan, 'Age': np.nan,
            'Load': np.nan, 'JockeyName': '', 'TrainerName': '',
            'father': '', 'mother_father': '', 'horse_id': None,
            '近走1走前着順': np.nan, '近走2走前着順': np.nan, '近走3走前着順': np.nan,
            '着差_1走前': np.nan, '上がり3F_1走前': np.nan,
            'タイム偏差値': np.nan, '同コース距離最速補正': np.nan,
            '父同条件複勝率': 0.0, '母父同条件複勝率': 0.0,
            '斤量絶対値': np.nan, '斤量前走差': np.nan,
            '馬体重絶対値': np.nan, '馬体重前走差': np.nan,
            '枠番': np.nan, '枠番_複勝率': 0.0,
            '負担率': np.nan, '距離区分': None, 'race_class_level': np.nan,
            'days_since_last_race': np.nan,
            'OddsShutuba': np.nan, 'NinkiShutuba': np.nan,
            '騎手コース複勝率': 0.0, '馬コース複勝率': 0.0,
            
            # --- ▼▼▼ ここからが新世界の特徴量 ▼▼▼ ---
            # 脚質・展開
            'leg_type': 4, # 脚質 (0:逃げ, 1:先行, 2:差し, 3:追込, 4:不明)
            'avg_4c_position': np.nan, # 平均4コーナー位置
            'hana_shucho_score': 0, # ハナ主張度スコア (0-100)
            'num_nige_horses': 0,
            'num_senko_horses': 0,
            'num_sashi_horses': 0,
            'num_oikomi_horses': 0,
            'num_high_hana_shucho': 0, # ハナ主張度の高い馬の数
            
            # 時計・ペース適性
            'time_dev_rank': np.nan, # メンバー内タイム偏差値ランク
            'last3f_rank': np.nan,   # メンバー内上がり3Fランク
            'avg_member_time_dev': np.nan,
            'avg_member_last3f': np.nan,
            
            # 道悪適性 (将来の実装用)
            'heavy_track_win_rate': 0.0,
            
            # 経歴
            'is_transfer': 0,
            'num_jra_starts': 0,
            'jra_rank_1ago': np.nan
            # --- ▲▲▲ 新特徴量ここまで ▲▲▲ ---
        }

        if not isinstance(horse_details, dict):
            return 0.0, features

        # --- 基本情報 ---
        features['horse_id'] = str(horse_details.get('horse_id')).split('.')[0] if pd.notna(horse_details.get('horse_id')) else None
        features['Umaban'] = pd.to_numeric(horse_details.get('Umaban'), errors='coerce')
        features['HorseName'] = str(horse_details.get('HorseName', ''))
        sex_age_str = str(horse_details.get('SexAge', '')).strip()
        if sex_age_str and re.match(r'([牡牝セ])(\d+)', sex_age_str):
            match = re.match(r'([牡牝セ])(\d+)', sex_age_str)
            sex_map = {'牡': 0, '牝': 1, 'セ': 2}
            features['Sex'] = sex_map.get(match.group(1), np.nan)
            features['Age'] = pd.to_numeric(match.group(2), errors='coerce')
        features['Load'] = pd.to_numeric(horse_details.get('Load'), errors='coerce')
        features['JockeyName'] = str(horse_details.get('JockeyName', ''))
        features['father'] = str(horse_details.get('father', ''))
        features['mother_father'] = str(horse_details.get('mother_father', ''))
        features['枠番'] = pd.to_numeric(horse_details.get('Waku'), errors='coerce')
        features['OddsShutuba'] = pd.to_numeric(horse_details.get('OddsShutuba'), errors='coerce')
        features['NinkiShutuba'] = pd.to_numeric(horse_details.get('NinkiShutuba'), errors='coerce')
        
        # --- 経歴特徴量 ---
        features['is_transfer'] = horse_details.get('is_transfer_from_local_1ago', 0)
        features['num_jra_starts'] = horse_details.get('num_jra_starts', 0)
        jra_results = horse_details.get('jra_race_results', [])
        if jra_results and isinstance(jra_results, list):
            features['jra_rank_1ago'] = pd.to_numeric(jra_results[0].get('rank'), errors='coerce')

        race_results_for_calc = horse_details.get('race_results', [])
        if not isinstance(race_results_for_calc, list): race_results_for_calc = []

        try:
            # === 個別能力の計算 ===
            # 近走情報
            for i in range(3):
                if len(race_results_for_calc) > i and isinstance(race_results_for_calc[i], dict):
                    features[f'近走{i+1}走前着順'] = pd.to_numeric(race_results_for_calc[i].get('rank'), errors='coerce')
                    if i == 0: 
                        features['着差_1走前'] = pd.to_numeric(race_results_for_calc[i].get('diff'), errors='coerce')
                        features['上がり3F_1走前'] = pd.to_numeric(race_results_for_calc[i].get('agari'), errors='coerce')
            
            # === タイム関連特徴量 (ご提供いただいたロジックを統合) ===
            target_course = race_conditions.get('CourseType', race_conditions.get('course_type'))
            target_distance_raw = race_conditions.get('Distance', race_conditions.get('distance'))
            target_track = race_conditions.get('TrackName', race_conditions.get('track_name'))
            target_distance_float = float(pd.to_numeric(target_distance_raw, errors='coerce')) if pd.notna(target_distance_raw) else None

            baba_hosei_map = {'芝': {'良': 0.0, '稍重': 0.5, '重': 1.0, '不良': 1.5}, 'ダ': {'良': 0.0, '稍重': -0.3, '重': -0.8, '不良': -1.3}}
            corrected_best_time = np.nan
            if race_results_for_calc and target_course and pd.notna(target_distance_float):
                corrected_times = []
                for r in race_results_for_calc:
                    time_sec = pd.to_numeric(r.get('time_sec'), errors='coerce')
                    if isinstance(r, dict) and pd.notna(time_sec) and pd.to_numeric(r.get('distance'), errors='coerce') == target_distance_float and r.get('course_type') == target_course:
                        hosei = baba_hosei_map.get(r.get('course_type'), {}).get(r.get('baba'), 0.0)
                        corrected_times.append(time_sec - hosei)
                if corrected_times:
                    corrected_best_time = min(corrected_times)
            features['同コース距離最速補正'] = round(corrected_best_time, 2) if pd.notna(corrected_best_time) else np.nan

            if pd.notna(corrected_best_time) and hasattr(self, 'course_time_stats') and target_track and target_course and pd.notna(target_distance_float):
                stat_key = (str(target_track), str(target_course), int(target_distance_float))
                course_stats = self.course_time_stats.get(stat_key)
                if course_stats and pd.notna(course_stats.get('mean')) and pd.notna(course_stats.get('std')) and course_stats['std'] > 0:
                    features['タイム偏差値'] = round(50 + 10 * (course_stats['mean'] - corrected_best_time) / course_stats['std'], 2)

            # === 脚質・ハナ主張度の計算 ===
            first_corner_positions = []
            avg_4c_pos = np.nan
            if race_results_for_calc:
                corner_positions = []
                for past_race in race_results_for_calc[:5]:
                    if isinstance(past_race, dict):
                        passage_str = past_race.get('passage')
                        if passage_str:
                            positions = [int(p) for p in re.findall(r'\d+', str(passage_str))]
                            if len(positions) > 0:
                                first_corner_positions.append(positions[0])
                                corner_positions.append(positions[-1])
                if corner_positions:
                    avg_4c_pos = np.mean(corner_positions)
                    features['avg_4c_position'] = avg_4c_pos

            # 脚質を4分類
            if pd.notna(avg_4c_pos):
                num_horses_avg = np.mean([pd.to_numeric(r.get('num_horses'), errors='coerce') for r in race_results_for_calc[:5] if r.get('num_horses')])
                if pd.notna(num_horses_avg):
                    if avg_4c_pos <= 2.5: features['leg_type'] = 0 # 逃げ
                    elif avg_4c_pos <= num_horses_avg * 0.4: features['leg_type'] = 1 # 先行
                    elif avg_4c_pos <= num_horses_avg * 0.7: features['leg_type'] = 2 # 差し
                    else: features['leg_type'] = 3 # 追込

            # ハナ主張度スコア
            if first_corner_positions:
                hana_scores = [(1 - (pos - 1) / 17) * 100 for pos in first_corner_positions]
                features['hana_shucho_score'] = np.mean(hana_scores) if hana_scores else 0

        except Exception as e_indiv:
            pass 

        # === レース全体の展開・時計レベルを計算 ===
        if race_members_df is not None and not race_members_df.empty:
            try:
                # 'index'列がない場合は作成
                if 'index' not in horse_details:
                     horse_details['index'] = features['horse_id'] 
                if 'index' not in race_members_df.columns:
                     race_members_df = race_members_df.set_index('horse_id', drop=False)
                     race_members_df.index.name = 'index'

                # 脚質ごとの頭数を集計
                leg_counts = race_members_df['leg_type'].value_counts()
                features['num_nige_horses'] = leg_counts.get(0, 0)
                features['num_senko_horses'] = leg_counts.get(1, 0)
                features['num_sashi_horses'] = leg_counts.get(2, 0)
                features['num_oikomi_horses'] = leg_counts.get(3, 0)
                
                # ハナ主張度の高い馬の数を集計 (スコア75以上)
                if 'hana_shucho_score' in race_members_df.columns:
                    features['num_high_hana_shucho'] = (race_members_df['hana_shucho_score'] >= 75).sum()

                # メンバー内ランク
                if 'タイム偏差値' in race_members_df.columns and horse_details['index'] in race_members_df.index:
                    features['time_dev_rank'] = race_members_df['タイム偏差値'].rank(ascending=False, method='min').loc[horse_details['index']]
                if '上がり3F_1走前' in race_members_df.columns and horse_details['index'] in race_members_df.index:
                    features['last3f_rank'] = race_members_df['上がり3F_1走前'].rank(ascending=True, method='min').loc[horse_details['index']]

                # メンバー平均値
                features['avg_member_time_dev'] = race_members_df['タイム偏差値'].mean()
                features['avg_member_last3f'] = race_members_df['上がり3F_1走前'].mean()

            except Exception as e_race_level:
                pass 
        
        return 0.0, features
     
    # --- 持ちタイム指数用の統計計算メソッド (修正・完全版) ---
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
    
    def _calculate_sire_stats(self, sire_column='father'):
        """
        【強化版】種牡馬ごとに、競馬場・コース種別・距離区分別の成績を集計する。
        """
        stats_attr_name = f"{sire_column}_stats"
        print(f"{sire_column} ごとの産駒成績データ（強化版）を計算中...")
        self.update_status(f"{sire_column} 成績データ計算中...")
        start_calc_time = time.time()

        setattr(self, stats_attr_name, {})

        if self.combined_data is None or self.combined_data.empty:
            print(f"警告: {stats_attr_name} 計算のためのデータがありません。")
            return

        required_cols = [sire_column, 'track_name', 'course_type', 'distance', 'Rank']
        if not all(col in self.combined_data.columns for col in required_cols):
             missing = [c for c in required_cols if c not in self.combined_data.columns]
             print(f"警告: {stats_attr_name} 計算に必要な列が不足しています: {missing}")
             return

        df = self.combined_data.copy()

        # データ前処理
        df.dropna(subset=required_cols, inplace=True)
        df[sire_column] = df[sire_column].fillna('Unknown').astype(str).str.strip()
        df = df[df[sire_column] != '']
        df['track_name'] = df['track_name'].astype(str).str.strip()
        df['course_type'] = df['course_type'].astype(str).str.strip()
        df['distance_numeric'] = pd.to_numeric(df['distance'], errors='coerce')
        df['Rank_numeric'] = pd.to_numeric(df['Rank'], errors='coerce')
        df.dropna(subset=['distance_numeric', 'Rank_numeric'], inplace=True)
        df['distance_numeric'] = df['distance_numeric'].astype(int)
        df['Rank_numeric'] = df['Rank_numeric'].astype(int)

        # 距離区分を作成
        bins = [0, 1400, 1800, 2200, 2600, float('inf')]
        labels = ['1400m以下', '1401-1800m', '1801-2200m', '2201-2600m', '2601m以上']
        df['DistanceGroup'] = pd.cut(df['distance_numeric'], bins=bins, labels=labels, right=True)

        try:
            # ★★★ グループ化のキーに 'track_name' を追加 ★★★
            stats = df.groupby([sire_column, 'track_name', 'course_type', 'DistanceGroup'], observed=False).agg(
                Runs=('Rank_numeric', 'size'),
                Place3=('Rank_numeric', lambda x: (x <= 3).sum())
            ).reset_index()

            stats['Place3Rate'] = stats.apply(lambda r: r['Place3'] / r['Runs'] if r['Runs'] > 0 else 0, axis=1)

            sire_stats_dict = {}
            for _, row in stats.iterrows():
                sire = row[sire_column]
                track = row['track_name']
                course = row['course_type']
                dist_group = row['DistanceGroup']
                runs = row['Runs']
                place3_rate = row['Place3Rate']

                if sire not in sire_stats_dict:
                    sire_stats_dict[sire] = {}
                
                # ★★★ キーを (競馬場, コース, 距離区分) に変更 ★★★
                key = (track, course, dist_group)
                if runs >= 5: # 最低出走回数
                    sire_stats_dict[sire][key] = {'Runs': int(runs), 'Place3Rate': place3_rate}

            setattr(self, stats_attr_name, sire_stats_dict)

            end_calc_time = time.time()
            print(f"{sire_column} 別成績データの計算完了。{len(getattr(self, stats_attr_name))} 件の種牡馬データを生成。({end_calc_time - start_calc_time:.2f}秒)")

        except Exception as e:
            print(f"!!! Error during sire stats calculation ({sire_column}): {e}")
            traceback.print_exc()
            setattr(self, stats_attr_name, {})

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

        # 必要な列を確認
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
    
    def load_model_from_file(self, model_filename="trained_lgbm_model_place.pkl", mode='place'):
    
        import os

        # モデルが保存されているディレクトリを取得
        model_load_dir = self.settings.get("models_dir", os.path.join(self.app_data_dir, "models"))
        
        # ★★★★★★★★★★★★ ここが今回の最重要修正ポイント ★★★★★★★★★★★★
        # ファイル名を 'mode' ('win' or 'place') を基準に生成するように修正します。
        # これで、保存時と読み込み時でファイル名が完全に一致します。
        
        # model_filename は trained_lgbm_model_win.pkl のように渡される想定
        # しかし、関連ファイルは mode を使って命名されている
        
        features_filename = f"model_features_{mode}.pkl"
        imputation_filename = f"imputation_values_{mode}.pkl"
        # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
        
        model_filepath = os.path.join(model_load_dir, model_filename)
        features_filepath = os.path.join(model_load_dir, features_filename)
        imputation_filepath = os.path.join(model_load_dir, imputation_filename)

        # --- 1. 学習済みモデルの読み込み ---
        print(f"INFO: Loading trained model ({mode}) from: {model_filepath}")
        loaded_model = self._load_pickle(model_filepath)

        # --- 2. 特徴量リストの読み込み ---
        print(f"INFO: Loading model features ({mode}) from: {features_filepath}")
        loaded_features = self._load_pickle(features_filepath)

        # --- 3. 欠損値補完のための値の読み込み ---
        print(f"INFO: Loading imputation values ({mode}) from: {imputation_filepath}")
        loaded_imputation_values = self._load_pickle(imputation_filepath)

        # --- 4. 読み込んだデータをselfの属性に格納 ---
        if loaded_model is not None:
            self.trained_model = loaded_model
            print(f"INFO: Successfully loaded trained model ({mode}): {model_filepath}")
        else:
            self.trained_model = None
            print(f"WARN: Failed to load trained model ({mode}) or file not found: {model_filepath}")

        if loaded_features is not None and isinstance(loaded_features, list):
            self.model_features = loaded_features
            print(f"INFO: Successfully loaded model features ({mode}, {len(self.model_features)} features): {features_filepath}")
        else:
            self.model_features = []
            print(f"WARN: Failed to load model features ({mode}) or file not found: {features_filepath}.")

        if loaded_imputation_values is not None and isinstance(loaded_imputation_values, dict):
            self.imputation_values_ = loaded_imputation_values
            print(f"INFO: 欠損値補完のための値をロードしました ({mode}): {imputation_filepath}")
        else:
            self.imputation_values_ = {}
            print(f"INFO: 欠損値補完ファイルが見つからないかロードに失敗 ({mode}): {imputation_filepath}")

        # --- 最終的なステータス表示 ---
        if self.trained_model is not None and self.model_features:
             self.update_status(f"モデル({mode})と特徴量({len(self.model_features)}個)をロードしました。")
        else:
             self.update_status(f"モデル({mode})のロードに失敗しました。")

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
        
    def preprocess_data_for_training(self):
        """
        【最終完成版・改】シンプルかつ確実な方法で全特徴量を計算する前処理エンジン。
        """
        if self.combined_data is None or self.combined_data.empty:
            print("INFO: 前処理するデータがありません。")
            self.processed_data = pd.DataFrame()
            return

        print("データ前処理開始: レース単位での展開・時計特徴量の計算を行います...")
        self.root.after(0, lambda: self.update_status("全データの特徴量計算中...（時間がかかります）"))
        
        try:
            # --- 1. 個別特徴量の計算 ---
            self.root.after(0, lambda: self.update_status("ステップ1/2: 各馬の個別能力を計算中..."))
            
            all_indiv_features = []
            grouped_by_race = self.combined_data.groupby('race_id')

            for i, (race_id, race_df) in enumerate(grouped_by_race):
                if (i + 1) % 20 == 0:
                    progress = (i + 1) / len(grouped_by_race) * 100
                    self.root.after(0, lambda p=progress: self.update_status(f"ステップ1/2... {p:.0f}%"))

                race_conditions = race_df.iloc[0].to_dict()
                for _, horse_row in race_df.iterrows():
                    _, indiv_features = self.calculate_original_index(horse_row.to_dict(), race_conditions, None)
                    indiv_features['race_id'] = race_id
                    indiv_features['horse_id'] = horse_row['horse_id'] # 結合キーとして horse_id を保持
                    all_indiv_features.append(indiv_features)
            
            indiv_features_df = pd.DataFrame(all_indiv_features)

            # --- 2. レースレベル特徴量の追加 ---
            self.root.after(0, lambda: self.update_status("ステップ2/2: レース展開を予測中..."))

            # レースごとに集計した特徴量を計算
            race_level_features = indiv_features_df.groupby('race_id').agg(
                num_nige_horses=('leg_type', lambda x: (x == 0).sum()),
                num_senko_horses=('leg_type', lambda x: (x == 1).sum()),
                num_sashi_horses=('leg_type', lambda x: (x == 2).sum()),
                num_oikomi_horses=('leg_type', lambda x: (x == 3).sum()),
                num_high_hana_shucho=('hana_shucho_score', lambda x: (x >= 75).sum()),
                avg_member_time_dev=('タイム偏差値', 'mean'),
                avg_member_last3f=('上がり3F_1走前', 'mean')
            ).reset_index()

            # 個別特徴量とレースレベル特徴量を結合
            final_df = pd.merge(indiv_features_df, race_level_features, on='race_id', how='left')

            # メンバー内ランクを計算
            final_df['time_dev_rank'] = final_df.groupby('race_id')['タイム偏差値'].rank(ascending=False, method='min')
            final_df['last3f_rank'] = final_df.groupby('race_id')['上がり3F_1走前'].rank(ascending=True, method='min')

            # 元データからRankをマージ
            rank_data = self.combined_data[['race_id', 'horse_id', 'Rank']].copy()
            final_df['horse_id'] = final_df['horse_id'].astype(str)
            rank_data['horse_id'] = rank_data['horse_id'].astype(str)
            final_df = pd.merge(final_df, rank_data, on=['race_id', 'horse_id'], how='left')

            self.processed_data = final_df
            print(f"INFO: self.processed_data に前処理済みデータを格納しました。Shape: {self.processed_data.shape}")
            self.root.after(0, lambda: self.update_status("全データの特徴量計算が完了しました。"))

        except Exception as e_outer:
            print("--- 致命的なエラーが発生しました (preprocess_data_for_training) ---")
            traceback.print_exc()
            self.root.after(0, lambda err=e_outer: messagebox.showerror("前処理エラー", f"データの前処理中に致命的なエラーが発生しました:\n{err}"))
     
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
        【改修版】指定されたターゲット列に応じて、学習・バックテスト用のデータを準備する。
        """
        if self.processed_data is None or self.processed_data.empty:
            print(f"ERROR: _prepare_data_for_model: self.processed_data が空です。")
            messagebox.showerror("データエラー", "特徴量計算の元となるデータ (processed_data) がありません。")
            return None

        # self.processed_data には元々の 'Rank' 列があると仮定
        if 'Rank' not in self.processed_data.columns:
            messagebox.showerror("データエラー", "学習に必要な 'Rank' (着順) 列がデータにありません。")
            return None
            
        # ターゲット列（目的変数）が存在しない場合は、ここで生成する
        if target_column_name not in self.processed_data.columns:
            print(f"INFO: ターゲット列 '{target_column_name}' がデータにないため、'Rank'列から生成します...")
            try:
                if target_column_name == 'target_rank_within_3':
                    # 3着以内なら1、それ以外は0
                    self.processed_data['target_rank_within_3'] = self.processed_data['Rank'].apply(lambda x: 1 if pd.notna(x) and 1 <= x <= 3 else 0)
                elif target_column_name == 'target_win':
                    # 1着なら1、それ以外は0
                    self.processed_data['target_win'] = self.processed_data['Rank'].apply(lambda x: 1 if pd.notna(x) and x == 1 else 0)
                else:
                     messagebox.showerror("エラー", f"未知のターゲット列名です: {target_column_name}")
                     return None
                print(f"INFO: ターゲット列 '{target_column_name}' の生成が完了しました。")
            except Exception as e:
                print(f"ERROR: ターゲット列の生成中にエラー: {e}")
                traceback.print_exc()
                return None
        
        # 不要な他のターゲット候補列を削除
        cols_to_drop = [
            col for col in ['target_win', 'target_rank_within_3'] 
            if col != target_column_name and col in self.processed_data.columns
        ]
        data_for_model = self.processed_data.drop(columns=cols_to_drop, errors='ignore').copy()
        
        print(f"モデル学習用の元データ (特徴量 + ターゲット列 '{target_column_name}') の準備完了。Shape: {data_for_model.shape}")
        return data_for_model
    
    def train_and_evaluate_model(self, processed_data, target_column='target_rank_within_3', mode='place'):
        """
        AIの思考（特徴量重要度）を可視化する機能を追加。
        """
        import pandas as pd
        import numpy as np
        import lightgbm as lgb
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score
        import os
        import traceback
        from tkinter import messagebox
        import matplotlib.pyplot as plt

        try:
            self.root.after(0, lambda: self.update_status(f"{mode}モデルの学習と評価を開始します..."))
            print(f"\n--- Starting Model Training and Evaluation (mode: {mode}) ---")

            if processed_data is None or processed_data.empty:
                self.root.after(0, lambda: messagebox.showerror("学習エラー", "学習に使用するデータがありません。"))
                return

            # AIが学習してよい特徴量のホワイトリストを更新
            leak_free_features = [
                # 基本情報
                'Age', 'Sex', 'Load', '枠番',
                '斤量絶対値', '斤量前走差', '馬体重絶対値', '馬体重前走差', '負担率',
                # 近走成績
                '近走1走前着順', '近走2走前着順', '近走3走前着順',
                '着差_1走前', '上がり3F_1走前',
                # タイム・能力
                'タイム偏差値', '同コース距離最速補正',
                # 血統・適性
                '父同条件複勝率', '母父同条件複勝率',
                '枠番_複勝率', '騎手コース複勝率', '馬コース複勝率',
                # レース条件
                '距離区分', 'race_class_level', 'days_since_last_race',
                # 事前オッズ
                'OddsShutuba', 'NinkiShutuba',
                
                # --- ▼▼▼ 新しく追加した特徴量 ▼▼▼ ---
                # 脚質・展開
                'leg_type',
                'avg_4c_position',
                'hana_shucho_score',
                'num_nige_horses',
                'num_senko_horses',
                'num_sashi_horses',
                'num_oikomi_horses',
                'num_high_hana_shucho',
                # 時計・ペース適性
                'time_dev_rank',
                'last3f_rank',
                'avg_member_time_dev',
                'avg_member_last3f',
                # 経歴
                'is_transfer',
                'num_jra_starts',
                'jra_rank_1ago'
                # --- ▲▲▲ 追加ここまで ▲▲▲ ---
            ]
            
            feature_columns_in_data = [col for col in leak_free_features if col in processed_data.columns]
            print(f"INFO: ホワイトリストに基づき、{len(feature_columns_in_data)}個のリークフリーな特徴量を選択しました。")
            
            X = processed_data[feature_columns_in_data].copy()
            y = processed_data[target_column].astype(int)

            # データ型前処理
            if '距離区分' in X.columns:
                X['距離区分'] = X['距離区分'].astype('category').cat.codes
            if 'leg_type' in X.columns:
                X['leg_type'] = X['leg_type'].astype('category').cat.codes

            for col in X.columns:
                X[col] = pd.to_numeric(X[col], errors='coerce')

            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
            
            imputation_values_for_this_model = X_train.mean().to_dict()
            
            X_train = X_train.fillna(imputation_values_for_this_model).fillna(0)
            X_test = X_test.fillna(imputation_values_for_this_model).fillna(0)
            
            final_feature_list = list(X.columns)

            print(f"モデル学習用データの準備完了。特徴量: {len(final_feature_list)}個, Shape X_train: {X_train.shape}")
            
            scale_pos_weight_value = y_train.value_counts()[0] / y_train.value_counts()[1] if y_train.value_counts().get(1, 0) > 0 else 1
            
            lgbm_params = {'objective': 'binary', 'metric': 'auc', 'n_estimators': 1000, 'random_state': 42, 'scale_pos_weight': scale_pos_weight_value}
            model = lgb.LGBMClassifier(**lgbm_params)

            print("モデルの学習を開始します...")
            model.fit(X_train, y_train,
                      eval_set=[(X_test, y_test)],
                      eval_metric='auc',
                      callbacks=[lgb.early_stopping(stopping_rounds=50, verbose=True)])
            print("モデルの学習が完了しました。")

            # --- 特徴量重要度の可視化 ---
            feature_importance = pd.DataFrame({
                'feature': final_feature_list,
                'importance': model.feature_importances_
            }).sort_values('importance', ascending=False)

            print(f"\n--- {mode.upper()}モデル 特徴量重要度 TOP 20 ---")
            print(feature_importance.head(20))
            print("---------------------------------------\n")

            self.root.after(0, self.plot_feature_importance, feature_importance, mode)
            
            # --- モデルと関連情報の保存 ---
            model_save_dir = self.settings.get("models_dir", os.path.join(self.app_data_dir, "models"))
            os.makedirs(os.path.expanduser(model_save_dir), exist_ok=True)
            
            self._save_pickle(model, os.path.join(model_save_dir, f"trained_lgbm_model_{mode}.pkl"))
            self._save_pickle(final_feature_list, os.path.join(model_save_dir, f"model_features_{mode}.pkl"))
            self._save_pickle(imputation_values_for_this_model, os.path.join(model_save_dir, f"imputation_values_{mode}.pkl"))
            
            y_pred_proba = model.predict_proba(X_test)[:, 1]
            auc = roc_auc_score(y_test, y_pred_proba)
            
            print(f"  {mode.upper()}モデル AUC Score: {auc:.4f}")

            if mode == 'place':
                self.trained_model = model
                self.model_features = final_feature_list
                self.imputation_values_ = imputation_values_for_this_model
                self.root.after(0, lambda: self.update_status(f"複勝モデルを更新しました (AUC: {auc:.4f})"))

        except Exception as e:
            traceback.print_exc()
            self.root.after(0, lambda err=e: messagebox.showerror("モデル学習エラー", f"モデル学習・評価中に予期せぬエラー:\n{err}"))
        finally:
            print(f"--- Model Training and Evaluation Finished (mode: {mode}) ---")

    def plot_feature_importance(self, importance_df, mode):
        """特徴量重要度のグラフを描画するヘルパーメソッド"""
        try:
            # 新しいウィンドウを作成
            win = tk.Toplevel(self.root)
            win.title(f"特徴量重要度 ({mode.upper()}モデル)")
            win.geometry("800x600")

            fig, ax = plt.subplots(figsize=(10, 8))
            
            # 上位20件をプロット
            top_20 = importance_df.head(20).sort_values('importance', ascending=True)
            
            ax.barh(top_20['feature'], top_20['importance'])
            ax.set_xlabel("重要度 (Importance)")
            ax.set_title(f"{mode.upper()}モデル 特徴量重要度 (TOP 20)")
            fig.tight_layout()

            canvas = FigureCanvasTkAgg(fig, master=win)
            canvas.draw()
            canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        except Exception as e:
            print(f"ERROR: 特徴量重要度グラフの描画中にエラー: {e}")
    
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
        【改修版】単勝(win)モデルと複勝(place)モデルの両方を学習するパイプライン。
        """
        try:
            # --- 1. 複勝モデル（3着以内確率）の学習 ---
            self.update_status("複勝モデルの学習データ準備中...")
            print("INFO: 複勝モデル(3着以内)の学習を開始します。")
            prepared_data_place = self._prepare_data_for_model(target_column_name='target_rank_within_3')

            if prepared_data_place is None or prepared_data_place.empty:
                print("ERROR: 複勝モデルの学習データ準備に失敗しました。")
                self.root.after(0, lambda: self.update_status("エラー: 複勝モデルの学習準備失敗"))
                return # 処理を中断

            # 複勝モデルを学習・評価・保存
            self.train_and_evaluate_model(processed_data=prepared_data_place, target_column='target_rank_within_3', mode='place')
            print("INFO: 複勝モデルの学習が完了しました。")


            # --- 2. 単勝モデル（1着確率）の学習 ---
            self.update_status("単勝モデルの学習データ準備中...")
            print("\nINFO: 単勝モデル(1着)の学習を開始します。")
            prepared_data_win = self._prepare_data_for_model(target_column_name='target_win')

            if prepared_data_win is None or prepared_data_win.empty:
                print("ERROR: 単勝モデルの学習データ準備に失敗しました。")
                self.root.after(0, lambda: self.update_status("エラー: 単勝モデルの学習準備失敗"))
                return # 処理を中断

            # 単勝モデルを学習・評価・保存
            self.train_and_evaluate_model(processed_data=prepared_data_win, target_column='target_win', mode='win')
            print("INFO: 単勝モデルの学習が完了しました。")
            
            self.root.after(0, lambda: self.update_status("全てのモデル学習が完了しました。"))

        except Exception as e:
            print(f"!!! FATAL ERROR in _run_training_pipeline_thread !!!")
            traceback.print_exc()
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
        """【日付健康診断・改】CSV読み込み時に日付列を診断し、不正なデータ数を報告する"""
        try:
            if csv_path and os.path.exists(csv_path):
                self.update_status(f"CSV読み込み中: {os.path.basename(csv_path)}")
                df_combined = pd.read_csv(csv_path, low_memory=False)
                
                # ★★★ ここからが修正ポイント ★★★
                date_col = 'date' if 'date' in df_combined.columns else 'race_date'
                if date_col in df_combined.columns:
                    # --- 日付データの健康診断 ---
                    initial_rows = len(df_combined)
                    # まず、どのくらいの行が元々空っぽかを確認
                    original_nulls = df_combined[date_col].isnull().sum()
                    
                    # pandasの自動解析を試みる
                    converted_dates = pd.to_datetime(df_combined[date_col], errors='coerce')
                    
                    # 変換に失敗した行（NaTになった行）の数を数える
                    failed_conversions = converted_dates.isnull().sum()
                    
                    # 元々空だった行を除いた、純粋な変換失敗数を計算
                    num_bad_data = failed_conversions - original_nulls
                    
                    print("\n--- 日付データ 健康診断レポート ---")
                    if num_bad_data > 0:
                        print(f"警告: {initial_rows:,.0f}行中、{num_bad_data:,.0f}行の日付データが不正な形式でした。")
                        print("INFO: これらの行は処理中に無視されます。")
                    else:
                        print("INFO: 全ての日付データは正常な形式です。")
                    print("---------------------------------\n")

                    # エラーを無視しつつ、変換した日付データを格納
                    df_combined[date_col] = converted_dates
                # ★★★ 修正ポイントここまで ★★★
                
                self.combined_data = df_combined
            else:
                self.root.after(0, lambda: messagebox.showerror("ファイルエラー", "有効なCSVファイルが選択されていません。"))
                return

            if json_path and os.path.exists(json_path):
                self.update_status("払い戻しJSON読み込み中...")
                with open(json_path, 'r', encoding='utf-8') as f:
                    self.payout_data = json.load(f)
            
            if self.combined_data is not None and not self.combined_data.empty:
                self.update_status("各種統計データ計算中...")
                # --- 統計計算処理 ---
                self._calculate_course_time_stats()
                if 'father' in self.combined_data.columns: self._calculate_sire_stats(sire_column='father')
                if 'mother_father' in self.combined_data.columns: self._calculate_sire_stats(sire_column='mother_father')
                self._calculate_gate_stats()
                self._calculate_reference_times()
                if 'JockeyName' in self.combined_data.columns: self._calculate_jockey_stats()
                # --- 全データの特徴量計算 ---
                self.preprocess_data_for_training()
            else:
                # データが空の場合の初期化処理
                self.course_time_stats={}; self.father_stats={}; self.mother_father_stats={}; self.gate_stats={}; self.jockey_stats={}; self.reference_times={}
                self.processed_data = pd.DataFrame()

            self.root.after(0, lambda: self.update_status("ローカルデータ準備完了"))
            self.root.after(0, lambda: messagebox.showinfo("読み込み完了", "データの読み込みと準備が完了しました。"))
            self.root.after(0, self.update_data_preview)

        except Exception as e:
            self.root.after(0, self.handle_collection_error, e)
    
    def process_collection_results(self, df_new_combined, new_payout_data, start_year, start_month, end_year, end_month):
        """【最終修正版】データ収集完了後の処理。ファイル保存時の日付エラーを完全に回避する。"""
        
        # --- 既存データと新規収集データを結合 ---
        if self.combined_data is not None and not self.combined_data.empty:
            print("既存データに新規収集データを結合します...")
            self.update_status("既存データと新規データを結合中...")
            try:
                date_col = 'date' if 'date' in self.combined_data.columns else 'race_date'
                self.combined_data[date_col] = pd.to_datetime(self.combined_data[date_col], errors='coerce')
                df_new_combined[date_col] = pd.to_datetime(df_new_combined[date_col], errors='coerce')

                updated_combined_data = pd.concat([self.combined_data, df_new_combined], ignore_index=True)
                updated_combined_data.drop_duplicates(subset=['race_id', 'horse_id'], keep='last', inplace=True)
                self.combined_data = updated_combined_data
            except Exception as e_concat:
                 print(f"!!! ERROR during data concatenation: {e_concat}")
                 self.root.after(0, lambda err=e_concat: messagebox.showerror("結合エラー", f"データの結合中にエラーが発生しました:\n{err}"))
                 self.combined_data = df_new_combined.copy()

            existing_payout_race_ids = {str(p.get('race_id')) for p in self.payout_data if p.get('race_id')}
            new_payouts_to_add = [p for p in new_payout_data if str(p.get('race_id')) not in existing_payout_race_ids]
            self.payout_data.extend(new_payouts_to_add)
            print(f"データ結合完了。現在の総レースデータ数: {self.combined_data.shape[0]}行")

        elif df_new_combined is not None and not df_new_combined.empty:
            self.combined_data = df_new_combined.copy()
            self.payout_data = new_payout_data[:]
        
        # --- 統計計算・UI更新 ---
        if self.combined_data is not None and not self.combined_data.empty:
            self.update_status("各種統計データ再計算中...")
            self._calculate_course_time_stats()
            if 'father' in self.combined_data.columns: self._calculate_sire_stats(sire_column='father')
            if 'mother_father' in self.combined_data.columns: self._calculate_sire_stats(sire_column='mother_father')
            self._calculate_gate_stats()
            self._calculate_reference_times()
            if 'JockeyName' in self.combined_data.columns: self._calculate_jockey_stats() 
            self.preprocess_data_for_training()
            
            self.root.after(0, lambda: self.update_status(f"データ処理完了: {self.combined_data.shape[0]}行"))
            self.root.after(0, lambda: messagebox.showinfo("データ処理完了", f"データの準備が完了しました。\nレースデータ: {self.combined_data.shape[0]}行\n(各種統計計算済)"))
            self.root.after(0, self.update_data_preview)
            
            # --- ▼▼▼ 自動ファイル保存処理 ▼▼▼ ---
            if start_year:
                try:
                    save_dir = self.settings.get("data_dir", ".")
                    if not os.path.exists(save_dir):
                        os.makedirs(save_dir)
                    
                    date_col = 'date' if 'date' in self.combined_data.columns else 'race_date'
                    
                    # ★★★ ここが修正ポイント ★★★
                    # pd.to_datetimeでエラーを無視し(coerce)、NaTになったものをdropna()で除去する
                    valid_dates = pd.to_datetime(self.combined_data[date_col], errors='coerce').dropna()
                    
                    if not valid_dates.empty:
                        min_date = valid_dates.min()
                        max_date = valid_dates.max()
                        period_str = f"{min_date.strftime('%Y%m')}_{max_date.strftime('%Y%m')}"
                    else:
                        period_str = f"{start_year}{start_month:02d}_{end_year}{end_month:02d}"
                    # ★★★ 修正ポイントここまで ★★★
                    
                    save_filename_base = "netkeiba_data"
                    results_filename = os.path.join(save_dir, f"{save_filename_base}_combined_{period_str}.csv")
                    payouts_filename = os.path.join(save_dir, f"{save_filename_base}_payouts_{period_str}.json")

                    df_to_save = self.combined_data.copy()
                    if date_col in df_to_save.columns:
                         # 日付でないデータは空文字にする
                         df_to_save[date_col] = pd.to_datetime(df_to_save[date_col], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S').fillna('')
                    
                    df_to_save.to_csv(results_filename, index=False, encoding='utf-8-sig')
                    print(f"収集・結合したデータを '{results_filename}' に保存しました。")
                    
                    if self.payout_data:
                        with open(payouts_filename, 'w', encoding='utf-8') as f:
                            json.dump(self.payout_data, f, indent=2, ensure_ascii=False)
                        print(f"払い戻しデータを '{payouts_filename}' に保存しました。")
                    
                    self.root.after(0, lambda: messagebox.showinfo("データ保存完了", f"収集・結合したデータは以下に保存されました:\nCSV: {results_filename}\nJSON: {payouts_filename}"))
                    
                    # キャッシュの保存
                    self.save_cache_to_file()
                    
                except Exception as e_save:
                    traceback.print_exc()
                    self.root.after(0, lambda err=e_save: messagebox.showerror("自動保存エラー", f"収集・結合データの自動保存中にエラーが発生しました:\n{err}"))
        else:
            self.update_status("データ処理完了: 有効なデータがありませんでした。")
            messagebox.showwarning("データ処理完了", "有効なレースデータが見つかりませんでした。")

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
        # メインフレーム
        prediction_frame = ttk.Frame(self.tab_prediction, padding="10")
        prediction_frame.pack(expand=True, fill="both")

        # --- レースID入力エリア ---
        input_frame = ttk.LabelFrame(prediction_frame, text="レース指定", padding="10")
        input_frame.pack(fill="x", pady=5)
        
        ttk.Label(input_frame, text="レースID:").pack(side="left", padx=(0, 5))
        
        self.race_id_entry = ttk.Entry(input_frame, width=30)
        self.race_id_entry.pack(side="left", expand=True, fill="x", padx=5)
        
        self.fetch_button = ttk.Button(input_frame, text="レース情報表示", command=self.fetch_race_info)
        self.fetch_button.pack(side="left", padx=5)

        # --- レース情報表示 ---
        race_info_frame = ttk.Frame(prediction_frame)
        race_info_frame.pack(fill="x", pady=5)
        
        self.race_info_label = ttk.Label(race_info_frame, text="ここにレース名が表示されます", font=("Meiryo UI", 12, "bold"))
        self.race_info_label.pack(anchor="w")
        
        self.race_details_label = ttk.Label(race_info_frame, text="ここにコース条件が表示されます")
        self.race_details_label.pack(anchor="w")

        # --- 結果表示エリア (PanedWindowで左右分割) ---
        paned_window = ttk.PanedWindow(prediction_frame, orient=tk.HORIZONTAL)
        paned_window.pack(expand=True, fill="both", pady=5)

        # 左側: 予測結果テーブル
        tree_frame = ttk.Frame(paned_window, padding=(0,0,5,0))
        paned_window.add(tree_frame, weight=3) # 幅の比率を調整
        
        # ★★★ ここからが表の定義です ★★★
        self.prediction_tree = ttk.Treeview(tree_frame, 
            columns=("Umaban", "HorseName", "SexAge", "Load", "JockeyName", "Odds", "NinkiShutuba", "place_proba", "win_proba"), 
            show="headings")
            
        # ヘッダー（列名）を設定
        self.prediction_tree.heading("Umaban", text="馬番")
        self.prediction_tree.heading("HorseName", text="馬名")
        self.prediction_tree.heading("SexAge", text="性齢")
        self.prediction_tree.heading("Load", text="斤量")
        self.prediction_tree.heading("JockeyName", text="騎手")
        self.prediction_tree.heading("Odds", text="オッズ")
        self.prediction_tree.heading("NinkiShutuba", text="人気")
        self.prediction_tree.heading("place_proba", text="複勝確率(%)")
        self.prediction_tree.heading("win_proba", text="単勝確率(%)")

        # 各列の幅とアライメントを設定
        self.prediction_tree.column("Umaban", width=40, anchor="center")
        self.prediction_tree.column("HorseName", width=150, anchor="w")
        self.prediction_tree.column("SexAge", width=50, anchor="center")
        self.prediction_tree.column("Load", width=50, anchor="center")
        self.prediction_tree.column("JockeyName", width=100, anchor="w")
        self.prediction_tree.column("Odds", width=60, anchor="e")
        self.prediction_tree.column("NinkiShutuba", width=40, anchor="center")
        self.prediction_tree.column("place_proba", width=80, anchor="e")
        self.prediction_tree.column("win_proba", width=80, anchor="e")
        # ★★★ ここまでが表の定義です ★★★

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.prediction_tree.yview)
        self.prediction_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.prediction_tree.pack(side="left", expand=True, fill="both")

        # 右側: 推奨馬券表示
        recommendation_frame = ttk.LabelFrame(paned_window, text="推奨買い目", padding="10")
        paned_window.add(recommendation_frame, weight=1) # 幅の比率を調整
        
        self.recommendation_text = tk.Text(recommendation_frame, wrap="word", height=15, font=("Meiryo UI", 10))
        self.recommendation_text.pack(expand=True, fill="both")
    
    def init_results_tab(self):
        """【UI改修版】結果検証タブの初期化。バックテスト結果表示用のUIを構築。"""
        # --- メインフレーム ---
        results_main_frame = ttk.Frame(self.tab_results, padding="5")
        results_main_frame.pack(fill=tk.BOTH, expand=True)

        # --- PanedWindowで左右に分割 ---
        paned_window = ttk.PanedWindow(results_main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True)

        # --- 左側の設定フレーム ---
        left_frame = ttk.LabelFrame(paned_window, text="バックテスト設定")
        paned_window.add(left_frame, weight=1) # 幅の比率

        # --- 対象期間選択フレーム ---
        period_frame = ttk.LabelFrame(left_frame, text="対象期間")
        period_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        current_dt = datetime.now()
        years = tuple(str(year) for year in range(2010, current_dt.year + 2))
        months = tuple(f"{month:02d}" for month in range(1, 13))
        days = tuple(f"{day:02d}" for day in range(1, 32))

        # --- 開始日 ---
        ttk.Label(period_frame, text="開始:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        from_frame = ttk.Frame(period_frame)
        from_frame.grid(row=0, column=1, sticky=tk.W)
        self.result_from_year_var = tk.StringVar(value=str(current_dt.year))
        ttk.Combobox(from_frame, textvariable=self.result_from_year_var, width=5, values=years, state="readonly").pack(side=tk.LEFT)
        self.result_from_month_var = tk.StringVar(value=current_dt.strftime("%m"))
        ttk.Combobox(from_frame, textvariable=self.result_from_month_var, width=3, values=months, state="readonly").pack(side=tk.LEFT, padx=2)
        self.result_from_day_var = tk.StringVar(value="01")
        ttk.Combobox(from_frame, textvariable=self.result_from_day_var, width=3, values=days, state="readonly").pack(side=tk.LEFT, padx=2)

        # --- 終了日 ---
        ttk.Label(period_frame, text="終了:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        to_frame = ttk.Frame(period_frame)
        to_frame.grid(row=1, column=1, sticky=tk.W)
        self.result_to_year_var = tk.StringVar(value=str(current_dt.year))
        ttk.Combobox(to_frame, textvariable=self.result_to_year_var, width=5, values=years, state="readonly").pack(side=tk.LEFT)
        self.result_to_month_var = tk.StringVar(value=current_dt.strftime("%m"))
        ttk.Combobox(to_frame, textvariable=self.result_to_month_var, width=3, values=months, state="readonly").pack(side=tk.LEFT, padx=2)
        self.result_to_day_var = tk.StringVar(value=current_dt.strftime("%d"))
        ttk.Combobox(to_frame, textvariable=self.result_to_day_var, width=3, values=days, state="readonly").pack(side=tk.LEFT, padx=2)

        # --- 分析タイプ選択 (グラフ表示用) ---
        analysis_type_frame = ttk.LabelFrame(left_frame, text="分析グラフ種別")
        analysis_type_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        self.result_type_var = tk.StringVar(value="収支推移")
        result_type_combo = ttk.Combobox(analysis_type_frame, textvariable=self.result_type_var, state="readonly")
        result_type_combo['values'] = ("収支推移", "馬券種別ROI", "的中率") # 将来の拡張用
        result_type_combo.pack(padx=5, pady=5, fill=tk.X)

        # --- 実行ボタン ---
        run_button = ttk.Button(left_frame, text="バックテスト実行", command=self.run_result_analysis)
        run_button.grid(row=2, column=0, pady=20, padx=10)
        
        # --- 保存ボタン ---
        save_button = ttk.Button(left_frame, text="結果を保存", command=self.save_result_analysis)
        save_button.grid(row=3, column=0, pady=10, padx=10)


        # --- 右側の結果表示フレーム ---
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=3) # 幅の比率

        # --- PanedWindowで上下に分割 ---
        right_paned_window = ttk.PanedWindow(right_frame, orient=tk.VERTICAL)
        right_paned_window.pack(fill=tk.BOTH, expand=True)

        # --- 上部: サマリー表示エリア ---
        summary_frame = ttk.LabelFrame(right_paned_window, text="バックテストサマリー")
        right_paned_window.add(summary_frame, weight=1)
        self.summary_text = tk.Text(summary_frame, wrap="word", height=8, font=("Meiryo UI", 10))
        self.summary_text.pack(expand=True, fill="both", padx=5, pady=5)
        self.summary_text.insert(tk.END, "ここにバックテストの集計結果が表示されます。")

        # --- 下部: グラフ表示エリア ---
        graph_frame = ttk.LabelFrame(right_paned_window, text="収支推移グラフ")
        right_paned_window.add(graph_frame, weight=3)
        self.result_figure = plt.Figure(figsize=(6, 4), dpi=100)
        self.result_canvas = FigureCanvasTkAgg(self.result_figure, master=graph_frame)
        self.result_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        # 初期グラフ描画
        self._draw_result_graph(None, "収支推移", "収支推移 (データ待機中)")

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
    
    def run_race_simulation(self, horses_info, n_simulations=10000):
        """
        【強化版】モンテカルロ法でレース着順を予測し、
        馬連・馬単・3連複・3連単の確率を計算して返す。
        """
        from collections import defaultdict
        import numpy as np

        sim_data = [{'umaban': int(h['Umaban']), 'win_proba': h['win_proba']} for h in horses_info if pd.notna(h.get('Umaban')) and pd.notna(h.get('win_proba'))]
        
        if not sim_data or sum(h['win_proba'] for h in sim_data) <= 0:
            return {'exacta': {}, 'quinella': {}, 'trio': {}, 'trifecta': {}}

        total_proba = sum(h['win_proba'] for h in sim_data)
        for h in sim_data:
            h['normalized_proba'] = h['win_proba'] / total_proba if total_proba > 0 else 0

        umabans = [h['umaban'] for h in sim_data]
        probabilities = [h['normalized_proba'] for h in sim_data]
        
        exacta_counts = defaultdict(int)
        quinella_counts = defaultdict(int)
        trio_counts = defaultdict(int)
        trifecta_counts = defaultdict(int)

        print(f"{n_simulations}回のレースシミュレーションを開始します...")
        for _ in range(n_simulations):
            simulated_order = np.random.choice(umabans, size=len(umabans), p=probabilities, replace=False)
            
            if len(simulated_order) >= 3:
                first = simulated_order[0]
                second = simulated_order[1]
                third = simulated_order[2]
                
                exacta_counts[(first, second)] += 1
                quinella_counts[tuple(sorted((first, second)))] += 1
                trifecta_counts[(first, second, third)] += 1
                trio_counts[tuple(sorted((first, second, third)))] += 1

        exacta_probabilities = {k: v / n_simulations for k, v in exacta_counts.items()}
        quinella_probabilities = {k: v / n_simulations for k, v in quinella_counts.items()}
        trio_probabilities = {k: v / n_simulations for k, v in trio_counts.items()}
        trifecta_probabilities = {k: v / n_simulations for k, v in trifecta_counts.items()}
        
        print("シミュレーションが完了しました。")
        return {
            'exacta': exacta_probabilities, 
            'quinella': quinella_probabilities,
            'trio': trio_probabilities,
            'trifecta': trifecta_probabilities
        }
    
    def fetch_race_info(self):
        """
        GUIからレースIDを取得し、別スレッドで予測処理を開始する司令塔。
        """
        race_id = self.race_id_entry.get().strip()
        if race_id and race_id.isdigit() and len(race_id) == 12:
            # 予測処理を別スレッドで実行し、GUIが固まるのを防ぐ
            thread = threading.Thread(target=self._fetch_race_info_thread, args=(race_id,))
            thread.daemon = True
            thread.start()
        else:
            messagebox.showwarning("入力エラー", "有効な12桁のレースIDを入力してください。")
    
    def _fetch_race_info_thread(self, race_id):
        """
        【最終修正版】単勝・複勝モデルをロードし、予測確率を計算後、
        モンテカルロ・シミュレーションを実行して馬連・馬単の確率も算出する。
        KeyErrorを修正。
        """
        import pandas as pd
        import numpy as np
        import traceback
        from tkinter import messagebox
        import tkinter as tk

        try:
            self.root.after(0, lambda: self.update_status(f"レースID {race_id}: 予測処理開始..."))
            print(f"--- _fetch_race_info_thread: START (Race ID: {race_id}) ---")

            # --- 1. 単勝・複勝モデルの両方をロード ---
            self.load_model_from_file(model_filename="trained_lgbm_model_win.pkl", mode='win')
            win_model = self.trained_model
            win_features = self.model_features
            win_imputation = self.imputation_values_
            if win_model is None or not win_features:
                self.root.after(0, lambda: messagebox.showerror("モデルエラー", "単勝予測モデル(trained_lgbm_model_win.pkl)が見つかりません。"))
                return

            self.load_model_from_file(model_filename="trained_lgbm_model_place.pkl", mode='place')
            place_model = self.trained_model
            place_features = self.model_features
            place_imputation = self.imputation_values_
            if place_model is None or not place_features:
                self.root.after(0, lambda: messagebox.showerror("モデルエラー", "複勝予測モデル(trained_lgbm_model_place.pkl)が見つかりません。"))
                return

            # --- 2. レース情報の取得 (Webから) ---
            self.root.after(0, lambda: self.update_status(f"レースID {race_id}: Webから出馬表情報取得中..."))
            web_data = self.get_shutuba_table(race_id)
            if not web_data or not web_data.get('horse_list'):
                self.root.after(0, lambda: messagebox.showerror("Web取得エラー", f"レースID {race_id} の出馬表をWebから取得できませんでした。"))
                return
            
            race_df = pd.DataFrame(web_data['horse_list'])
            race_conditions = web_data.get('race_details', {})
            race_date_str = race_conditions.get('RaceDate')
            race_conditions['RaceDate'] = pd.to_datetime(race_date_str, format='%Y年%m月%d日', errors='coerce') if race_date_str else pd.NaT
            race_conditions['baba'] = race_conditions.get('TrackCondition')
            
            # --- 3. GUIにレース基本情報を表示 ---
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
            self.root.after(0, lambda text=race_info_text: self.race_info_label.config(text=text))
            self.root.after(0, lambda text=race_details_text: self.race_details_label.config(text=text))

            # --- 4. 出走馬ごとの特徴量計算と確率予測 ---
            horse_details_list_for_gui = []
            for index, row in race_df.iterrows():
                horse_id = row.get('horse_id')
                if pd.isna(horse_id): continue
                
                horse_id_str = str(horse_id).split('.')[0]
                horse_full_details = self.horse_details_cache.get(horse_id_str)
                if not horse_full_details:
                    horse_full_details = self.get_horse_details(horse_id_str)
                    if isinstance(horse_full_details, dict) and not horse_full_details.get('error'):
                        self.horse_details_cache[horse_id_str] = horse_full_details
                
                horse_basic_info = dict(row)
                if isinstance(horse_full_details, dict):
                    horse_basic_info.update(horse_full_details)
                
                if 'race_results' in horse_basic_info and isinstance(horse_basic_info['race_results'], list):
                    predict_date = race_conditions.get('RaceDate')
                    if pd.notna(predict_date):
                        horse_basic_info['race_results'] = [r for r in horse_basic_info['race_results'] if isinstance(r, dict) and pd.to_datetime(r.get('date'), errors='coerce') < predict_date]

                _, features_dict = self.calculate_original_index(horse_basic_info, race_conditions)
                
                # ★★★★★★★★★★★★ ここが今回の最重要修正ポイント ★★★★★★★★★★★★
                def prepare_feature_vector(features, feature_list, imputation_values):
                    """
                    特徴量辞書から、モデルが学習した通りの特徴量ベクトル（DataFrame）を作成する。
                    足りない列はNaNで埋めてから、保存された平均値などで補完する。
                    """
                    # まず、存在する特徴だけでDataFrameを作成
                    X_pred = pd.DataFrame([features])
                    
                    # 学習時の特徴量リストに合わせて列を再編成（足りない列はNaNで追加される）
                    X_pred = X_pred.reindex(columns=feature_list)

                    if '距離区分' in X_pred.columns:
                        distance_map = {'1400m以下': 0, '1401-1800m': 1, '1801-2200m': 2, '2201-2600m': 3, '2601m以上': 4}
                        X_pred['距離区分'] = X_pred['距離区分'].map(distance_map)
                    
                    # 全ての列を数値型に変換
                    for col in X_pred.columns:
                        X_pred[col] = pd.to_numeric(X_pred[col], errors='coerce')

                    # 保存された補完値でNaNを埋める
                    X_pred = X_pred.fillna(imputation_values)
                    # それでも残ったNaNは0で埋める
                    X_pred = X_pred.fillna(0)
                    
                    return X_pred
                # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★

                # 単勝・複勝確率の予測
                X_win = prepare_feature_vector(features_dict, win_features, win_imputation)
                win_proba = win_model.predict_proba(X_win)[:, 1][0]
                
                X_place = prepare_feature_vector(features_dict, place_features, place_imputation)
                place_proba = place_model.predict_proba(X_place)[:, 1][0]
                
                current_horse_info = dict(row)
                current_horse_info.update({
                    'win_proba': win_proba,
                    'place_proba': place_proba,
                    '予測確率': place_proba # テーブル表示用は複勝確率
                })
                horse_details_list_for_gui.append(current_horse_info)

            # --- 5. モンテカルロ・シミュレーションの実行 ---
            self.update_status(f"レースID {race_id}: シミュレーション実行中...")
            simulation_results = self.run_race_simulation(horse_details_list_for_gui)
            
            # --- 6. 結果の表示 ---
            horse_details_list_for_gui.sort(key=lambda x: x.get('place_proba', 0), reverse=True)
            self.root.after(0, self._update_prediction_table, horse_details_list_for_gui)
            
            recommendation_text = self.create_recommendation_text(horse_details_list_for_gui, simulation_results)
            if hasattr(self, 'recommendation_text') and self.recommendation_text.winfo_exists():
                self.root.after(0, lambda: self.recommendation_text.delete(1.0, tk.END))
                self.root.after(0, lambda: self.recommendation_text.insert(tk.END, recommendation_text))
            
            self.root.after(0, lambda: self.update_status(f"予測完了: {race_id}"))

        except Exception as e:
            traceback.print_exc()
            self.root.after(0, lambda err=e: messagebox.showerror("予測処理エラー", f"予測処理中に予期せぬエラー: {err}"))
    
    def create_recommendation_text(self, horses_info, simulation_results):
        """
        【戦略判断機能つき・最終版】
        予測確率の分布を分析し、「絶対軸馬」「混戦」などのレースパターンを診断。
        パターンに応じて、軸1頭ながし、ボックス買い、ケンなどを自動で切り替えて推奨する。
        """
        text = "【AIレース診断＆推奨買い目】\n"
        text += "----------------------------------\n"

        # --- STEP 1: 予測データが十分にあるか確認 ---
        valid_horses = [h for h in horses_info if pd.notna(h.get('win_proba')) and pd.notna(h.get('place_proba'))]
        if len(valid_horses) < 5:
            return "予測データが不足しているため、買い目を生成できません。"

        # 単勝確率順にソート
        sorted_by_win_proba = sorted(valid_horses, key=lambda x: x.get('win_proba', 0), reverse=True)
        
        # --- STEP 2: レースパターンの診断 ---
        win_proba_top1 = sorted_by_win_proba[0].get('win_proba', 0)
        win_proba_top2 = sorted_by_win_proba[1].get('win_proba', 0)
        win_proba_top3 = sorted_by_win_proba[2].get('win_proba', 0)

        race_pattern = "不明"
        # パターン1: 「絶対軸馬」パターン
        if win_proba_top1 > 0.35 and (win_proba_top1 > win_proba_top2 * 1.8): # 1位が35%以上、かつ2位の1.8倍以上
            race_pattern = "絶対軸馬"
            text += f"診断: 信頼できる軸馬がいます (単勝確率: {win_proba_top1:.1%})\n"
            text += "推奨戦略: 軸1頭ながし\n\n"
        # パターン2: 「混戦」パターン
        elif win_proba_top1 < 0.25 and (win_proba_top1 - win_proba_top3) < 0.08: # 1位の確率が低く、1位と3位の差が小さい
            race_pattern = "混戦"
            text += f"診断: 上位人気は混戦模様です\n"
            text += "推奨戦略: ボックス買い\n\n"
        # パターン3: 上記以外は「標準」パターン
        else:
            race_pattern = "標準"
            text += f"診断: 標準的なレースです\n"
            text += "推奨戦略: 軸1頭ながし\n\n"

        # --- STEP 3: 診断パターンに応じた買い目を生成 ---
        if race_pattern == "絶対軸馬" or race_pattern == "標準":
            axis_horse = sorted_by_win_proba[0]
            sorted_by_place_proba = sorted(valid_horses, key=lambda x: x.get('place_proba', 0), reverse=True)
            opponent_horses = [h for h in sorted_by_place_proba if h.get('Umaban') != axis_horse.get('Umaban')][:5]
            
            axis_num = axis_horse.get('Umaban', '？')
            opponent_nums = [h.get('Umaban', '？') for h in opponent_horses]
            
            text += f"◎ 軸馬 (単勝確率1位): {axis_num} {axis_horse.get('HorseName', '')}\n"
            text += f"○ 相手 (複勝確率上位): {', '.join(map(str, opponent_nums))}\n\n"

            from itertools import permutations, combinations
            text += "◇ 3連複 (軸1頭ながし)\n"
            if len(opponent_nums) >= 2:
                for comb in combinations(opponent_nums, 2):
                    text += f"  {axis_num} - {comb[0]} - {comb[1]}\n"
            
            text += "\nＸ 3連単 (軸1着固定ながし)\n"
            if len(opponent_nums) >= 2:
                for perm in permutations(opponent_nums, 2):
                    text += f"  {axis_num} → {perm[0]} → {perm[1]}\n"

        elif race_pattern == "混戦":
            top3_horses = sorted_by_win_proba[:3]
            top3_numbers = [str(h.get('Umaban')) for h in top3_horses]
            
            text += f"◎ 注目馬 (単勝確率Top3): {', '.join(top3_numbers)}\n\n"
            
            from itertools import combinations, permutations
            text += "◇ 3連複 (ボックス)\n"
            if len(top3_numbers) == 3:
                text += f"  {'-'.join(top3_numbers)}\n"
            text += "\n"

            text += "Ｘ 3連単 (ボックス)\n"
            if len(top3_numbers) == 3:
                for perm in permutations(top3_numbers, 3):
                    text += f"  {'→'.join(perm)}\n"
        
        text += "----------------------------------\n"
        return text
   
    def _update_prediction_table(self, horse_details_list):
        """【改修版】予測結果テーブルを更新する。単勝・複勝確率を%表示する。"""
        # 既存の表示をクリア
        for item in self.prediction_tree.get_children():
            self.prediction_tree.delete(item)
        
        # 新しいデータを挿入
        for horse in horse_details_list:
            # ★★★ 表示する値のリストを変更 ★★★
            place_proba_percent = f"{horse.get('place_proba', 0) * 100:.1f}"
            win_proba_percent = f"{horse.get('win_proba', 0) * 100:.1f}"
            
            values_to_insert = (
                horse.get("Umaban", ""),
                horse.get("HorseName", ""),
                horse.get("SexAge", ""),
                horse.get("Load", ""),
                horse.get("JockeyName", ""),
                horse.get("Odds", ""),
                horse.get("NinkiShutuba", ""),
                place_proba_percent, # 複勝確率
                win_proba_percent  # 単勝確率
            )
            self.prediction_tree.insert("", "end", values=values_to_insert)

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
    
    def _prepare_feature_vector(self, df, feature_list, imputation_values):
        """予測用に特徴量ベクトルを準備する"""
        X = df.reindex(columns=feature_list).copy()
        if '距離区分' in X.columns:
            distance_map = {'1400m以下': 0, '1401-1800m': 1, '1801-2200m': 2, '2201-2600m': 3, '2601m以上': 4}
            X['距離区分'] = X['距離区分'].map(distance_map)
        for col in X.columns:
            X[col] = pd.to_numeric(X[col], errors='coerce')
        X = X.fillna(imputation_values).fillna(0)
        return X
    
    def run_result_analysis(self):
        """【UI改修版】結果分析（バックテスト）実行処理。年月日を正しく取得する。"""
        if self.processed_data is None or self.processed_data.empty:
             messagebox.showwarning("バックテスト実行", "分析対象のデータが読み込まれていません。\nデータ管理タブでデータを読み込んでください。")
             return
        
        if self.payout_data is None or not self.payout_data:
            messagebox.showwarning("バックテスト実行", "払い戻しデータ(JSON)が読み込まれていません。\n的中判定ができないため、処理を中断します。")
            return

        self.update_status("バックテスト実行準備中...")

        try:
             start_date_str = f"{self.result_from_year_var.get()}-{self.result_from_month_var.get()}-{self.result_from_day_var.get()}"
             end_date_str = f"{self.result_to_year_var.get()}-{self.result_to_month_var.get()}-{self.result_to_day_var.get()}"
             start_dt = pd.to_datetime(start_date_str)
             end_dt = pd.to_datetime(end_date_str)
        except ValueError:
            messagebox.showerror("日付エラー", "バックテスト期間の日付形式が正しくありません。（例: 2月31日など）")
            self.update_status("エラー: 日付形式不正")
            return
        
        # どのグラフを表示するかを取得
        analysis_type = self.result_type_var.get()
        
        # 処理を別スレッドで実行
        self.run_in_thread(self._run_result_analysis_thread, start_dt, end_dt, analysis_type)
    
    def _run_result_analysis_thread(self, start_dt, end_dt, analysis_type):
        """【最終版：ロジック完全統一】予測タブと同一の丁寧な特徴量計算を各レースで再現するバックテスト"""
        import pandas as pd
        import traceback
        from tkinter import messagebox
        from itertools import permutations, combinations
        from collections import defaultdict

        try:
            self.root.after(0, lambda: self.update_status("バックテスト準備中..."))
            print("\n--- ロジック完全統一バックテスト 開始 ---")

            # --- 1. 必要なモデルとデータのチェック ---
            self.load_model_from_file(model_filename="trained_lgbm_model_win.pkl", mode='win')
            win_model = self.trained_model
            win_features = self.model_features
            win_imputation = self.imputation_values_

            self.load_model_from_file(model_filename="trained_lgbm_model_place.pkl", mode='place')
            place_model = self.trained_model
            place_features = self.model_features
            place_imputation = self.imputation_values_

            if win_model is None or place_model is None:
                self.root.after(0, lambda: messagebox.showerror("モデルエラー", "単勝または複勝モデルが見つかりません。"))
                return

            # --- 2. 対象期間のレースIDと払い戻しデータを準備 ---
            date_col = 'date' if 'date' in self.combined_data.columns else 'race_date'
            self.combined_data[date_col] = pd.to_datetime(self.combined_data[date_col], errors='coerce')
            
            target_races_df = self.combined_data[
                (self.combined_data[date_col] >= start_dt) & (self.combined_data[date_col] <= end_dt)
            ]
            target_race_ids = target_races_df['race_id'].unique()

            if len(target_race_ids) == 0:
                self.root.after(0, lambda: messagebox.showinfo("バックテスト結果", "指定期間に該当するレースデータがありません。"))
                self.root.after(0, lambda: self.update_status("準備完了"))
                return

            payouts_map = {str(p['race_id']): p for p in self.payout_data if 'race_id' in p}

            # --- 3. バックテストループ開始 ---
            simulation_results = []
            total_investment = 0
            total_return = 0
            bet_counts = defaultdict(int)
            hit_counts = defaultdict(int)
            races_bet_on = 0

            for i, race_id in enumerate(target_race_ids):
                self.root.after(0, lambda: self.update_status(f"特徴量再計算中... {i+1}/{len(target_race_ids)}"))
                
                race_df = target_races_df[target_races_df['race_id'] == race_id].copy()
                if race_df.empty: continue

                race_conditions = race_df.iloc[0].to_dict()
                predict_date = race_conditions[date_col]

                # a. 【重要】馬ごとに詳細な特徴量を再計算
                features_for_race = []
                for _, horse_row in race_df.iterrows():
                    horse_details_for_calc = horse_row.to_dict()
                    horse_id_str = str(horse_details_for_calc.get('horse_id', '')).split('.')[0]
                    
                    if horse_id_str and horse_id_str in self.horse_details_cache:
                        horse_full_details = self.horse_details_cache[horse_id_str]
                        # データリーク防止：予測時点より未来の戦績を除外
                        if isinstance(horse_full_details.get('race_results'), list):
                            past_results = [r for r in horse_full_details['race_results'] 
                                            if isinstance(r, dict) and pd.to_datetime(r.get('date'), errors='coerce') < predict_date]
                            horse_details_for_calc['race_results'] = past_results
                    
                    _, features_dict = self.calculate_original_index(horse_details_for_calc, race_conditions)
                    features_for_race.append(features_dict)
                
                features_df = pd.DataFrame(features_for_race)

                # b. 予測確率を計算
                X_win = self._prepare_feature_vector(features_df, win_features, win_imputation)
                win_probas = win_model.predict_proba(X_win)[:, 1]
                X_place = self._prepare_feature_vector(features_df, place_features, place_imputation)
                place_probas = place_model.predict_proba(X_place)[:, 1]

                # c. 推奨馬券を生成
                horses_info = race_df[['Umaban', 'HorseName']].to_dict('records')
                for idx, horse in enumerate(horses_info):
                    horse['win_proba'] = win_probas[idx]
                    horse['place_proba'] = place_probas[idx]

                sorted_by_win_proba = sorted(horses_info, key=lambda x: x.get('win_proba', 0), reverse=True)
                if len(sorted_by_win_proba) < 3: continue
                
                win_proba_top1 = sorted_by_win_proba[0].get('win_proba', 0)
                win_proba_top2 = sorted_by_win_proba[1].get('win_proba', 0)
                
                bets_for_this_race = []
                if win_proba_top1 > 0.35 and (win_proba_top1 > win_proba_top2 * 1.8): # 絶対軸馬
                    axis_horse = sorted_by_win_proba[0]
                    opponents = [h for h in sorted(horses_info, key=lambda x: x['place_proba'], reverse=True) if h['Umaban'] != axis_horse['Umaban']][:5]
                    if len(opponents) >= 2:
                        for comb in combinations(opponents, 2): bets_for_this_race.append({'type': '三連複', 'numbers': tuple(sorted((int(axis_horse['Umaban']), int(comb[0]['Umaban']), int(comb[1]['Umaban']))))})
                        for perm in permutations(opponents, 2): bets_for_this_race.append({'type': '三連単', 'numbers': (int(axis_horse['Umaban']), int(perm[0]['Umaban']), int(perm[1]['Umaban']))})
                else: # 混戦・標準
                    top3_horses = sorted_by_win_proba[:3]
                    bets_for_this_race.append({'type': '三連複', 'numbers': tuple(sorted(int(h['Umaban']) for h in top3_horses))})
                    for perm in permutations(top3_horses, 3): bets_for_this_race.append({'type': '三連単', 'numbers': tuple(int(h['Umaban']) for h in perm)})

                # d. 結果照合と収支計算
                investment_this_race = 0; return_this_race = 0
                if bets_for_this_race:
                    payout_info = payouts_map.get(str(race_id))
                    if payout_info:
                        races_bet_on += 1
                        for bet in bets_for_this_race:
                            investment_this_race += 100; bet_counts[bet['type']] += 1
                            payout_type_jp = bet['type'].replace('三連複', '3連複').replace('三連単', '3連単')
                            if payout_type_jp in payout_info:
                                for idx, win_comb_str in enumerate(payout_info[payout_type_jp].get('馬番', [])):
                                    try:
                                        win_nums = tuple(int(n) for n in win_comb_str.replace('→', '-').split('-'))
                                        if bet['type'] == '三連複': win_nums = tuple(sorted(win_nums))
                                        if bet['numbers'] == win_nums:
                                            return_this_race += int(payout_info[payout_type_jp]['払戻金'][idx]); hit_counts[bet['type']] += 1; break
                                    except (ValueError, IndexError): continue
                
                total_investment += investment_this_race; total_return += return_this_race
                simulation_results.append({'date': predict_date, 'investment': investment_this_race, 'return': return_this_race})

            # --- 5. サマリー作成 ---
            roi = (total_return / total_investment * 100) if total_investment > 0 else 0
            summary = (f"推奨ロジック バックテスト ({start_dt.strftime('%Y/%m/%d')} - {end_dt.strftime('%Y/%m/%d')})\n" + "-"*34 + f"\n対象レース数: {len(target_race_ids)} R\n投資レース数: {races_bet_on} R\n" + f"総投資額: {total_investment:,.0f} 円\n総回収額: {total_return:,.0f} 円\n" + f"収支: {total_return - total_investment:,.0f} 円\n回収率 (ROI): {roi:.2f} %\n" + "-"*34 + "\n【馬券種別成績】\n")
            all_bet_types = sorted(list(set(list(bet_counts.keys()) + list(hit_counts.keys()))))
            for bet_type in all_bet_types:
                count = bet_counts.get(bet_type, 0); hit = hit_counts.get(bet_type, 0)
                hit_rate = (hit / count * 100) if count > 0 else 0
                summary += f"◆ {bet_type}:\n  - 的中率: {hit} / {count} ({hit_rate:.2f} %)\n"

            # --- 6. 結果をUIに反映 ---
            self.root.after(0, self._update_summary_text, summary)
            self.root.after(0, self._draw_result_graph, simulation_results, analysis_type, f"収支推移 ({start_dt.strftime('%Y/%m/%d')}～)")
            self.root.after(0, lambda: self.update_status("バックテストが完了しました。"))

        except Exception as e:
            traceback.print_exc()
            self.root.after(0, lambda err=e: messagebox.showerror("バックテストエラー", f"バックテスト処理中にエラーが発生しました:\n{err}"))

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
        try:
            self.result_figure.clear()
            ax = self.result_figure.add_subplot(111)

            if analysis_type == "収支推移":
                if simulation_results:
                    sim_df = pd.DataFrame(simulation_results)
                    if not sim_df.empty and 'date' in sim_df.columns:
                        sim_df['date'] = pd.to_datetime(sim_df['date'])
                        sim_df = sim_df.sort_values(by='date')
                        sim_df['profit'] = sim_df['return'] - sim_df['investment']
                        sim_df['cumulative_profit'] = sim_df['profit'].cumsum()
                        
                        ax.plot(sim_df['date'], sim_df['cumulative_profit'], marker='.', linestyle='-')
                        ax.set_xlabel('日付')
                        ax.set_ylabel('累計収支 (円)')
                        ax.set_title(title)
                        self.result_figure.autofmt_xdate(rotation=30)
                        ax.grid(True, linestyle='--', alpha=0.6)
                    else:
                        ax.text(0.5, 0.5, '描画データがありません', ha='center', va='center')
                else:
                    ax.text(0.5, 0.5, 'シミュレーション結果なし', ha='center', va='center')
                    ax.set_title(title + " (データ待機中)")
            else:
                 ax.text(0.5, 0.5, f'{analysis_type}\n(グラフ未実装)', ha='center', va='center')
                 ax.set_title(f"{analysis_type} (未実装)")

            self.result_figure.tight_layout()
            self.result_canvas.draw()
        except Exception as e:
            traceback.print_exc()
    
    def save_result_analysis(self):
        """バックテスト結果のグラフとサマリーを保存"""
        save_dir = self.settings.get("results_dir", ".")
        analysis_type = self.result_type_var.get()
        start_date_str = self.result_from_year_var.get() + self.result_from_month_var.get() + self.result_from_day_var.get()
        end_date_str = self.result_to_year_var.get() + self.result_to_month_var.get() + self.result_to_day_var.get()
        base_filename = f"backtest_{start_date_str}-{end_date_str}_{analysis_type}_{datetime.now().strftime('%Y%m%d%HM')}"

        summary_content = self.summary_text.get(1.0, tk.END).strip()
        if not summary_content or "表示されます" in summary_content:
            messagebox.showwarning("保存エラー", "保存するバックテスト結果がありません。")
            return

        # グラフとテキストをセットで保存するか確認
        if messagebox.askyesno("保存確認", "現在のバックテスト結果（サマリーとグラフ）を保存しますか？"):
            try:
                # テキスト保存
                text_file_path = os.path.join(save_dir, f"{base_filename}.txt")
                with open(text_file_path, "w", encoding="utf-8") as f:
                    f.write(summary_content)
                
                # グラフ保存
                graph_file_path = os.path.join(save_dir, f"{base_filename}.png")
                self.result_figure.savefig(graph_file_path, bbox_inches='tight')

                self.update_status(f"結果を保存しました: {save_dir}")
                messagebox.showinfo("保存完了", f"バックテスト結果を以下の2ファイルに保存しました:\n\n1. {os.path.basename(text_file_path)}\n2. {os.path.basename(graph_file_path)}")
            except Exception as e:
                messagebox.showerror("保存エラー", f"結果の保存中にエラーが発生しました:\n{e}")

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

