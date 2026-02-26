"""
競馬予想 & データ管理システム - 統合GUIツール

機能:
1. レース予想（Value Betting）
2. データ更新（年月日選択で自動収集）
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkcalendar import DateEntry
import threading
import sys
import os
from io import StringIO
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

# 既存モジュール
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from predict_by_race_id import DirectRacePredictor


class DataUpdater:
    """データ更新クラス（1秒待機付き）"""

    def __init__(self, db_path='netkeiba_data_2020_2024_enhanced.csv',
                 log_path=r'C:\Users\bu158\HorseRacingAnalyzer\data\processed_race_ids.log'):
        self.db_path = db_path
        self.log_path = log_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def scrape_race_result(self, race_id):
        """レース結果スクレイピング"""
        url = f'https://db.netkeiba.com/race/{race_id}/'

        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')

            # レース名
            h1_tags = soup.find_all('h1')
            race_name = h1_tags[1].text.strip() if len(h1_tags) > 1 else 'N/A'

            # 日付・距離
            race_data_elements = soup.select('div.data_intro p')
            date_text = ''
            distance = ''

            if race_data_elements:
                for elem in race_data_elements:
                    text = elem.get_text(strip=True)
                    if '年' in text:
                        date_text = text.split()[0] if text else ''
                    elif 'm' in text:
                        distance = text

            # 結果テーブル
            result_table = soup.find('table', class_='race_table_01')
            if not result_table:
                return None

            rows = result_table.find_all('tr')[1:]

            results = []
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 19:
                    continue

                umaban = int(cols[2].text.strip())
                horse_elem = cols[3].find('a')
                horse_name = horse_elem.text.strip() if horse_elem else 'N/A'
                horse_id = horse_elem.get('href', '').split('/')[-1] if horse_elem else 'N/A'

                jockey_elem = cols[6].find('a')
                jockey = jockey_elem.text.strip() if jockey_elem else 'N/A'

                try:
                    odds = float(cols[12].text.strip())
                except:
                    odds = 0.0

                try:
                    popularity = int(cols[13].text.strip())
                except:
                    popularity = 0

                results.append({
                    'race_id': race_id,
                    'race_name': race_name,
                    'date': date_text,
                    'distance': distance,
                    '馬番': umaban,
                    'horse_id': horse_id,
                    'horse_name': horse_name,
                    'jockey': jockey,
                    'odds': odds,
                    'popularity': popularity,
                })

            return pd.DataFrame(results) if results else None

        except Exception as e:
            return None

    def get_existing_ids(self):
        """既存レースID取得（CSVが真実）"""
        existing_ids = set()

        # CSVから（優先）
        try:
            if os.path.exists(self.db_path):
                df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
                existing_ids = set(df['race_id'].astype(str).unique())
                return existing_ids
        except:
            pass

        # ログファイルから（フォールバック）
        try:
            if os.path.exists(self.log_path):
                with open(self.log_path, 'r', encoding='utf-8') as f:
                    existing_ids = set(line.strip() for line in f if line.strip())
                return existing_ids
        except:
            pass

        return set()

    def write_to_log(self, race_id):
        """ログに記録"""
        try:
            log_dir = os.path.dirname(self.log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            with open(self.log_path, 'a', encoding='utf-8') as f:
                f.write(f"{race_id}\n")
        except:
            pass

    def save_data(self, data_list):
        """データ保存"""
        if not data_list:
            return

        new_df = pd.concat(data_list, ignore_index=True)

        if os.path.exists(self.db_path):
            existing_df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        combined_df = combined_df.drop_duplicates(subset=['race_id', '馬番'], keep='last')
        combined_df.to_csv(self.db_path, index=False, encoding='utf-8')

    def generate_race_ids_for_dates(self, start_date, end_date):
        """
        日付範囲からレースID候補を生成

        レースIDパターン: YYYYPPKKDDRR
        - YYYY: 年
        - PP: 競馬場 (01-10)
        - KK: 開催回 (01-08)
        - DD: 日目 (01-12)
        - RR: レース番号 (01-12)
        """
        race_ids = []

        current = start_date
        while current <= end_date:
            # 土日のみ
            if current.weekday() in [5, 6]:  # 土曜=5, 日曜=6
                year = current.year

                # 各競馬場
                for place in ['01', '02', '05', '06', '07', '08', '09', '10']:
                    # 開催回（1-8回）
                    for meeting in ['01', '02', '03', '04', '05', '06', '07', '08']:
                        # 日目（1-12日目）
                        for day in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
                            # レース番号（1-12R）
                            for race_num in ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']:
                                race_id = f"{year}{place}{meeting}{day}{race_num}"
                                race_ids.append(race_id)

            current += timedelta(days=1)

        return race_ids


class KeibaManagerGUI:
    """競馬予想 & データ管理 統合GUI"""

    def __init__(self, root):
        self.root = root
        self.root.title("競馬予想 & データ管理システム")
        self.root.geometry("1000x750")

        # データ更新エンジン
        self.updater = DataUpdater()
        self.predictor = DirectRacePredictor()

        # ノートブック（タブ）
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)

        # タブ1: 予想
        self.prediction_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.prediction_tab, text="🎯 レース予想")

        # タブ2: データ更新
        self.update_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.update_tab, text="📊 データ更新")

        # 各タブを構築
        self.build_prediction_tab()
        self.build_update_tab()

    # ==========================================
    # タブ1: レース予想
    # ==========================================

    def build_prediction_tab(self):
        """予想タブを構築"""
        frame = ttk.Frame(self.prediction_tab, padding="10")
        frame.pack(fill='both', expand=True)

        # タイトル
        ttk.Label(frame, text="🏇 競馬予想システム",
                 font=('Arial', 20, 'bold')).pack(pady=10)

        # レースID入力
        input_frame = ttk.Frame(frame)
        input_frame.pack(pady=10, fill='x')

        ttk.Label(input_frame, text="レースID:", font=('Arial', 11, 'bold')).pack(side='left', padx=5)
        self.race_id_entry = ttk.Entry(input_frame, width=20, font=('Arial', 12))
        self.race_id_entry.pack(side='left', padx=5)
        ttk.Label(input_frame, text="例: 202412070811", foreground='gray').pack(side='left', padx=5)

        # 予算入力
        budget_frame = ttk.Frame(frame)
        budget_frame.pack(pady=10, fill='x')

        ttk.Label(budget_frame, text="予算:", font=('Arial', 11, 'bold')).pack(side='left', padx=5)
        self.budget_entry = ttk.Entry(budget_frame, width=20, font=('Arial', 12))
        self.budget_entry.insert(0, "10000")
        self.budget_entry.pack(side='left', padx=5)
        ttk.Label(budget_frame, text="円", foreground='gray').pack(side='left', padx=5)

        # ボタン
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        self.predict_btn = ttk.Button(btn_frame, text="🎯 予想実行",
                                      command=self.run_prediction, width=20)
        self.predict_btn.pack(side='left', padx=10)

        ttk.Button(btn_frame, text="🗑 クリア",
                  command=self.clear_prediction, width=15).pack(side='left', padx=10)

        # 結果表示
        ttk.Label(frame, text="予想結果:", font=('Arial', 11, 'bold')).pack(pady=5, anchor='w')
        self.pred_result = scrolledtext.ScrolledText(frame, width=110, height=25, font=('Courier', 9))
        self.pred_result.pack(pady=10, fill='both', expand=True)

        # 初期メッセージ
        self.pred_result.insert(tk.END, """
================================================================================
競馬予想システム - Value Betting Analyzer
================================================================================

【使い方】
1. NetKeibaでレースIDをコピー
2. 上の欄に貼り付け
3. 予算を入力（デフォルト: 10000円）
4. 「予想実行」ボタンをクリック

準備ができたら予想実行してください！
================================================================================
        """)

    def run_prediction(self):
        """予想実行"""
        race_id = self.race_id_entry.get().strip()
        budget_str = self.budget_entry.get().strip()

        if not race_id or len(race_id) != 12 or not race_id.isdigit():
            messagebox.showerror("エラー", "レースIDは12桁の数字で入力してください")
            return

        try:
            budget = int(budget_str)
            if budget <= 0:
                raise ValueError
        except:
            messagebox.showerror("エラー", "予算は正の整数で入力してください")
            return

        self.predict_btn.config(state='disabled')
        self.pred_result.delete(1.0, tk.END)
        self.pred_result.insert(tk.END, "予想実行中... しばらくお待ちください\n")

        thread = threading.Thread(target=self._execute_prediction, args=(race_id, budget))
        thread.daemon = True
        thread.start()

    def _execute_prediction(self, race_id, budget):
        """実際の予想処理"""
        try:
            old_stdout = sys.stdout
            sys.stdout = StringIO()

            result = self.predictor.predict_race(race_id, budget=budget)

            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            self.root.after(0, lambda: self.pred_result.delete(1.0, tk.END))
            self.root.after(0, lambda: self.pred_result.insert(tk.END, output))

        except Exception as e:
            sys.stdout = old_stdout
            self.root.after(0, lambda: self.pred_result.insert(tk.END, f"\nエラー: {str(e)}"))

        finally:
            self.root.after(0, lambda: self.predict_btn.config(state='normal'))

    def clear_prediction(self):
        """予想結果クリア"""
        self.pred_result.delete(1.0, tk.END)
        self.pred_result.insert(tk.END, "クリアしました。\n")

    # ==========================================
    # タブ2: データ更新
    # ==========================================

    def build_update_tab(self):
        """データ更新タブを構築"""
        frame = ttk.Frame(self.update_tab, padding="10")
        frame.pack(fill='both', expand=True)

        # タイトル
        ttk.Label(frame, text="📊 データ更新システム",
                 font=('Arial', 20, 'bold')).pack(pady=10)

        # 説明
        ttk.Label(frame, text="期間を選択して、未取得のレースデータを自動収集します",
                 font=('Arial', 10)).pack(pady=5)

        # 日付選択フレーム
        date_frame = ttk.LabelFrame(frame, text="期間選択", padding="10")
        date_frame.pack(pady=10, fill='x')

        # 開始日
        start_frame = ttk.Frame(date_frame)
        start_frame.pack(pady=5, fill='x')
        ttk.Label(start_frame, text="開始日:", font=('Arial', 11, 'bold')).pack(side='left', padx=5)
        self.start_date = DateEntry(start_frame, width=20, font=('Arial', 11),
                                     date_pattern='yyyy-mm-dd', locale='ja_JP')
        self.start_date.pack(side='left', padx=5)

        # 終了日
        end_frame = ttk.Frame(date_frame)
        end_frame.pack(pady=5, fill='x')
        ttk.Label(end_frame, text="終了日:", font=('Arial', 11, 'bold')).pack(side='left', padx=5)
        self.end_date = DateEntry(end_frame, width=20, font=('Arial', 11),
                                   date_pattern='yyyy-mm-dd', locale='ja_JP')
        self.end_date.pack(side='left', padx=5)

        # 便利ボタン
        quick_frame = ttk.Frame(date_frame)
        quick_frame.pack(pady=10, fill='x')
        ttk.Label(quick_frame, text="クイック選択:", font=('Arial', 10)).pack(side='left', padx=5)

        ttk.Button(quick_frame, text="先週末", command=lambda: self.set_last_weekend()).pack(side='left', padx=2)
        ttk.Button(quick_frame, text="今週末", command=lambda: self.set_this_weekend()).pack(side='left', padx=2)
        ttk.Button(quick_frame, text="先月", command=lambda: self.set_last_month()).pack(side='left', padx=2)
        ttk.Button(quick_frame, text="今月", command=lambda: self.set_this_month()).pack(side='left', padx=2)

        # 自動収集モード
        self.auto_mode_var = tk.BooleanVar(value=False)
        auto_check = ttk.Checkbutton(date_frame, text="完全自動モード（Selenium使用）",
                                     variable=self.auto_mode_var,
                                     command=self.toggle_auto_mode)
        auto_check.pack(pady=5)

        # 実行ボタン
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=10)

        self.update_btn = ttk.Button(btn_frame, text="▶ データ更新開始",
                                     command=self.start_data_update, width=25)
        self.update_btn.pack(side='left', padx=10)

        ttk.Button(btn_frame, text="⏹ 停止", command=self.stop_data_update, width=15).pack(side='left', padx=10)

        # プログレスバー
        self.progress = ttk.Progressbar(frame, mode='indeterminate')
        self.progress.pack(pady=10, fill='x')

        # 結果表示
        ttk.Label(frame, text="更新ログ:", font=('Arial', 11, 'bold')).pack(pady=5, anchor='w')
        self.update_result = scrolledtext.ScrolledText(frame, width=110, height=25, font=('Courier', 9))
        self.update_result.pack(pady=10, fill='both', expand=True)

        # 初期メッセージ
        self.update_result.insert(tk.END, """
================================================================================
データ更新システム
================================================================================

【使い方】
1. 開始日と終了日を選択
2. 「データ更新開始」をクリック
3. 自動で未取得レースを収集します

【注意】
- アクセス制限を避けるため、各レース間に1秒の待機時間があります
- 期間が長いと時間がかかります（1週末 = 約5-10分）
- VPN接続推奨

準備ができたら「データ更新開始」を押してください！
================================================================================
        """)

        self.update_running = False

    def toggle_auto_mode(self):
        """自動モードの切り替え"""
        if self.auto_mode_var.get():
            self.log("\n自動モード有効: カレンダーからレースIDを自動収集します\n")
        else:
            self.log("\n手動モード: 既存のレースIDパターンから推測します\n")

    def set_last_weekend(self):
        """先週末を設定"""
        today = datetime.now()
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday + 7)
        last_saturday = last_sunday - timedelta(days=1)
        self.start_date.set_date(last_saturday)
        self.end_date.set_date(last_sunday)

    def set_this_weekend(self):
        """今週末を設定"""
        today = datetime.now()
        days_until_saturday = (5 - today.weekday()) % 7
        this_saturday = today + timedelta(days=days_until_saturday)
        this_sunday = this_saturday + timedelta(days=1)
        self.start_date.set_date(this_saturday)
        self.end_date.set_date(this_sunday)

    def set_last_month(self):
        """先月を設定"""
        today = datetime.now()
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        self.start_date.set_date(last_month_start)
        self.end_date.set_date(last_month_end)

    def set_this_month(self):
        """今月を設定"""
        today = datetime.now()
        first_this_month = today.replace(day=1)
        self.start_date.set_date(first_this_month)
        self.end_date.set_date(today)

    def start_data_update(self):
        """データ更新開始"""
        if self.update_running:
            messagebox.showwarning("警告", "既に更新中です")
            return

        start = self.start_date.get_date()
        end = self.end_date.get_date()

        if start > end:
            messagebox.showerror("エラー", "開始日が終了日より後になっています")
            return

        self.update_running = True
        self.update_btn.config(state='disabled')
        self.progress.start()

        self.update_result.delete(1.0, tk.END)
        self.update_result.insert(tk.END, f"期間: {start} ～ {end}\n")
        self.update_result.insert(tk.END, "レースID候補を生成中...\n\n")

        thread = threading.Thread(target=self._execute_update, args=(start, end))
        thread.daemon = True
        thread.start()

    def _execute_update(self, start_date, end_date):
        """実際の更新処理"""
        try:
            # 自動モードかどうか
            if self.auto_mode_var.get():
                # Seleniumで自動収集
                self.log("完全自動モード: カレンダーからレースIDを収集中...\n")
                race_id_candidates = self.auto_collect_race_ids(start_date, end_date)
            else:
                # 既存のパターンベース生成
                self.log("手動モード: レースIDパターンから生成中...\n")
                race_id_candidates = self.updater.generate_race_ids_for_dates(start_date, end_date)

            self.log(f"レースID候補: {len(race_id_candidates):,}件\n")

            # デバッグ: レースID候補の最初の5件を表示
            if race_id_candidates:
                self.log("レースID候補例:\n")
                for rid in list(race_id_candidates)[:5]:
                    self.log(f"  {rid}\n")
                self.log("\n")

            # 既存ID取得
            existing_ids = self.updater.get_existing_ids()
            self.log(f"既存レース: {len(existing_ids):,}件\n")

            # 未取得ID抽出
            new_ids = [rid for rid in race_id_candidates if rid not in existing_ids]
            self.log(f"未取得レース: {len(new_ids):,}件\n\n")

            # デバッグ: 突き合わせ確認
            if race_id_candidates and not new_ids:
                self.log("デバッグ: 候補の最初の3件がCSVに存在するか確認:\n")
                for rid in list(race_id_candidates)[:3]:
                    exists = rid in existing_ids
                    self.log(f"  {rid}: {'存在' if exists else '未存在'}\n")
                self.log("\n")

            if not new_ids:
                self.log("全て取得済みです！\n")
                return

            self.log(f"データ収集開始... （1秒間隔）\n")
            self.log("="*60 + "\n\n")

            all_data = []
            success = 0
            fail = 0

            for i, race_id in enumerate(new_ids, 1):
                if not self.update_running:
                    self.log("\n\n中断されました\n")
                    break

                self.log(f"[{i}/{len(new_ids)}] {race_id}... ")

                df = self.updater.scrape_race_result(race_id)

                if df is not None and len(df) > 0:
                    all_data.append(df)
                    success += 1
                    self.log(f"OK ({len(df)}頭)\n")
                    self.updater.write_to_log(race_id)
                else:
                    fail += 1
                    self.log("NG\n")

                # 10件ごとに保存
                if len(all_data) >= 10:
                    self.updater.save_data(all_data)
                    self.log(f"  → {len(all_data)}件をDBに保存\n\n")
                    all_data = []

                # 1秒待機（アクセス制限回避）
                time.sleep(1.0)

            # 残り保存
            if all_data:
                self.updater.save_data(all_data)
                self.log(f"\n  → {len(all_data)}件をDBに保存\n")

            self.log("\n" + "="*60 + "\n")
            self.log(f"完了: 成功 {success}件 / 失敗 {fail}件\n")
            self.log("="*60 + "\n")

        except Exception as e:
            self.log(f"\n\nエラー: {str(e)}\n")

        finally:
            self.root.after(0, self._update_finished)

    def log(self, message):
        """ログ出力"""
        self.root.after(0, lambda: self.update_result.insert(tk.END, message))
        self.root.after(0, lambda: self.update_result.see(tk.END))

    def _update_finished(self):
        """更新完了"""
        self.update_running = False
        self.update_btn.config(state='normal')
        self.progress.stop()

    def stop_data_update(self):
        """更新停止"""
        if self.update_running:
            self.update_running = False
            self.log("\n\n停止要求を受け付けました...\n")

    def auto_collect_race_ids(self, start_date, end_date):
        """Seleniumを使ってカレンダーから自動的にレースIDを収集"""
        import re
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.chrome.options import Options

        def get_kaisai_dates(year, month):
            """カレンダーから開催日取得"""
            url = f'https://race.netkeiba.com/top/calendar.html?year={year}&month={month}'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            try:
                r = requests.get(url, headers=headers, timeout=10)
                r.raise_for_status()
                soup = BeautifulSoup(r.content, 'html.parser')
                kaisai_dates = []
                for a_tag in soup.select('.Calendar_Table .Week > td > a'):
                    href = a_tag.get('href', '')
                    match = re.search(r'kaisai_date=(\d{8})', href)
                    if match:
                        kaisai_dates.append(match.group(1))
                return kaisai_dates
            except:
                return []

        def get_race_ids_from_date(kaisai_date, driver):
            """レース一覧からレースID取得（開催日でフィルタ）"""
            url = f'https://race.netkeiba.com/top/race_list.html?kaisai_date={kaisai_date}'
            wait = WebDriverWait(driver, 30)
            try:
                driver.get(url)

                # ページ読み込み完了を待つ
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '#RaceTopRace')))

                # JavaScriptの実行完了を待つ（追加の待機）
                time.sleep(3)

                # さらに、レースリンクが実際に存在するまで待機
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.RaceList_DataItem > a')))

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                race_ids = []

                # すべての race_id リンクを探す（セレクタを変更）
                for a_tag in soup.select('a[href*="race_id="]'):
                    href = a_tag.get('href', '')
                    match = re.search(r'race_id=(\d{12})', href)
                    if match:
                        race_id = match.group(1)
                        if race_id not in race_ids:
                            race_ids.append(race_id)

                return race_ids
            except Exception as e:
                return []

        # Chromeドライバー起動
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        self.log("Chromeドライバー起動中...\n")
        driver = webdriver.Chrome(options=chrome_options)
        all_race_ids = []

        try:
            # 期間を月単位でループ
            current = start_date
            while current <= end_date:
                year = current.year
                month = current.month

                self.log(f"{year}年{month}月: ")
                kaisai_dates = get_kaisai_dates(year, month)

                if kaisai_dates:
                    self.log(f"{len(kaisai_dates)}日間開催\n")
                    for kaisai_date in kaisai_dates:
                        # 期間内かチェック
                        date_obj = datetime.strptime(kaisai_date, '%Y%m%d').date()
                        if start_date <= date_obj <= end_date:
                            race_ids = get_race_ids_from_date(kaisai_date, driver)
                            all_race_ids.extend(race_ids)
                            self.log(f"  {kaisai_date}: {len(race_ids)}レース\n")
                            time.sleep(0.5)
                else:
                    self.log("開催なし\n")

                # 次の月へ
                if month == 12:
                    current = current.replace(year=year+1, month=1)
                else:
                    current = current.replace(month=month+1)

                if current.day != 1:
                    current = current.replace(day=1)

        finally:
            driver.quit()
            self.log("Chromeドライバー終了\n\n")

        return all_race_ids


def main():
    root = tk.Tk()
    app = KeibaManagerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
