"""
競馬予想ツール - GUI版
Netkeibaページ風 + 予測機能

使い方:
    python keiba_yosou_tool.py
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import pandas as pd
import numpy as np
import pickle
import json
import os
import threading
from datetime import datetime
from data_config import MAIN_CSV, MAIN_JSON
from feature_engineering import FeatureEngineer, get_running_style_name

class KeibaYosouTool:
    def __init__(self, root):
        self.root = root
        self.root.title("競馬予想ツール")
        self.root.geometry("1200x800")

        # データとモデル
        self.df = None
        self.payouts_data = None
        self.model = None

        self.setup_ui()
        self.load_data_and_model()

    def setup_ui(self):
        """UI構築"""
        # メインフレーム
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # ========================================
        # レース入力エリア
        # ========================================
        input_frame = ttk.LabelFrame(main_frame, text="レース選択", padding="10")
        input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        ttk.Label(input_frame, text="race_id:").grid(row=0, column=0, sticky=tk.W)

        self.race_id_entry = ttk.Entry(input_frame, width=20, font=('Arial', 12))
        self.race_id_entry.grid(row=0, column=1, padx=5)

        self.predict_btn = ttk.Button(input_frame, text="予測実行", command=self.run_prediction)
        self.predict_btn.grid(row=0, column=2, padx=5)

        ttk.Label(input_frame, text="例: 202501010811", font=('Arial', 9), foreground='gray').grid(row=0, column=3, padx=5)

        # クリアボタン
        ttk.Button(input_frame, text="クリア", command=self.clear_results).grid(row=0, column=4, padx=5)

        # ========================================
        # レース情報エリア
        # ========================================
        info_frame = ttk.LabelFrame(main_frame, text="レース情報", padding="10")
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 10))

        self.race_info_text = tk.Text(info_frame, height=4, width=100, font=('Arial', 10))
        self.race_info_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.race_info_text.config(state='disabled')

        # ========================================
        # 予測結果エリア（メイン）
        # ========================================
        result_frame = ttk.LabelFrame(main_frame, text="予測結果", padding="10")
        result_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)

        # 出馬表 + 予測テーブル
        table_container = ttk.Frame(result_frame)
        table_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        table_container.columnconfigure(0, weight=1)
        table_container.rowconfigure(0, weight=1)

        # Treeview（表形式）
        columns = ('予測順位', '馬番', '馬名', '騎手', '人気', 'オッズ', '近3走', '脚質', '予測%', '実際')
        self.result_table = ttk.Treeview(table_container, columns=columns, show='headings', height=18)

        # カラム設定
        self.result_table.heading('予測順位', text='予測順位')
        self.result_table.heading('馬番', text='馬番')
        self.result_table.heading('馬名', text='馬名')
        self.result_table.heading('騎手', text='騎手')
        self.result_table.heading('人気', text='人気')
        self.result_table.heading('オッズ', text='オッズ')
        self.result_table.heading('近3走', text='近3走')
        self.result_table.heading('脚質', text='脚質')
        self.result_table.heading('予測%', text='予測%')
        self.result_table.heading('実際', text='実際')

        self.result_table.column('予測順位', width=70, anchor='center')
        self.result_table.column('馬番', width=50, anchor='center')
        self.result_table.column('馬名', width=180, anchor='w')
        self.result_table.column('騎手', width=100, anchor='w')
        self.result_table.column('人気', width=50, anchor='center')
        self.result_table.column('オッズ', width=70, anchor='center')
        self.result_table.column('近3走', width=100, anchor='center')
        self.result_table.column('脚質', width=60, anchor='center')
        self.result_table.column('予測%', width=80, anchor='center')
        self.result_table.column('実際', width=60, anchor='center')

        # スクロールバー
        scrollbar = ttk.Scrollbar(table_container, orient='vertical', command=self.result_table.yview)
        self.result_table.configure(yscrollcommand=scrollbar.set)

        self.result_table.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

        # ========================================
        # 推奨馬券エリア
        # ========================================
        bet_frame = ttk.LabelFrame(main_frame, text="推奨馬券", padding="10")
        bet_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

        self.bet_text = tk.Text(bet_frame, height=6, width=100, font=('Arial', 11, 'bold'))
        self.bet_text.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.bet_text.config(state='disabled')

        # ========================================
        # ステータスバー
        # ========================================
        self.status_label = ttk.Label(main_frame, text="準備完了", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=4, column=0, sticky=(tk.W, tk.E), pady=(10, 0))

    def load_data_and_model(self):
        """データとモデルを読み込み"""
        self.update_status("データ読み込み中...")

        try:
            # データ読み込み
            self.df = pd.read_csv(MAIN_CSV, low_memory=False)
            self.df['date_parsed'] = pd.to_datetime(self.df['date'], errors='coerce')

            with open(MAIN_JSON, 'r', encoding='utf-8') as f:
                payouts_list = json.load(f)
                # リストを辞書に変換
                if isinstance(payouts_list, list):
                    self.payouts_data = {item['race_id']: item for item in payouts_list}
                else:
                    self.payouts_data = payouts_list

            self.update_status(f"データ読み込み完了: {len(self.df):,}行")

            # モデル読み込み
            # 最新のLightGBMモデルを探す（優先順位順）
            model_candidates = [
                'lightgbm_model_trifecta_optimized_fixed.pkl',  # 最新・最適化済み
                'lightgbm_model_advanced.pkl',  # 次世代モデル
                'lightgbm_model_trifecta_optimized.pkl',
                'lightgbm_model_with_running_style.pkl',
                'lightgbm_model_tuned.pkl',
                'lightgbm_model.pkl',
            ]

            model_files = [f for f in model_candidates if os.path.exists(f)]

            if len(model_files) > 0:
                model_files.sort(reverse=True)
                model_file = model_files[0]

                with open(model_file, 'rb') as f:
                    model_data = pickle.load(f)
                    self.model = model_data.get('model')

                self.update_status(f"モデル読み込み完了: {model_file}")
            else:
                self.update_status("モデル未訓練 - オッズベース予測を使用")

        except Exception as e:
            messagebox.showerror("エラー", f"データ読み込みエラー:\n{e}")
            self.update_status("エラー")

    def update_status(self, message):
        """ステータス更新"""
        self.status_label.config(text=message)
        self.root.update_idletasks()

    def _fetch_shutuba(self, race_id):
        """出馬表を取得（未来レース用・Selenium使用で全頭取得）"""
        try:
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            from selenium.webdriver.chrome.service import Service as ChromeService
            from bs4 import BeautifulSoup
            import time

            url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"

            print(f"\n=== Selenium使用で出馬表取得 ===")
            print(f"URL: {url}")

            # Chromeオプション設定
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')  # ヘッドレスモード
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--log-level=3')  # ログを最小化
            options.add_experimental_option('excludeSwitches', ['enable-logging'])
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

            driver = None
            try:
                # ChromeDriverを起動
                driver = webdriver.Chrome(options=options)
                driver.set_page_load_timeout(60)

                # ページロード
                driver.get(url)
                time.sleep(3)  # JavaScript実行を待つ

                # HTMLを取得
                soup = BeautifulSoup(driver.page_source, 'lxml')

            finally:
                if driver:
                    driver.quit()

            # レース名（複数のパターンを試す）
            race_title = soup.find('div', class_='RaceName')
            if not race_title:
                race_title = soup.find('h1', class_='RaceName')
            if not race_title:
                race_title = soup.find('h1')
            race_name = race_title.get_text(strip=True) if race_title else 'N/A'

            # レース詳細（距離、コース、馬場等）
            race_data = soup.find('div', class_='RaceData01')
            race_details = race_data.get_text(strip=True) if race_data else ''

            # 日付を抽出（発走時刻の前にある日付情報から）
            # Netkeibaのページから実際の開催日を取得
            race_date = None
            try:
                # ページのどこかに日付情報があるはず（例: "2025年11月23日"）
                import re
                date_pattern = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', str(soup))
                if date_pattern:
                    year = int(date_pattern.group(1))
                    month = int(date_pattern.group(2))
                    day = int(date_pattern.group(3))
                    race_date = f"{year:04d}-{month:02d}-{day:02d}"
            except:
                pass

            # 日付が取得できなかった場合は今日の日付を使用
            if not race_date:
                from datetime import datetime
                race_date = datetime.now().strftime("%Y-%m-%d")

            print(f"\n=== レース情報抽出 ===")
            print(f"レース名: {race_name}")
            print(f"レース詳細: {race_details}")
            print(f"レース日付: {race_date}")

            # 競馬場名を抽出
            race_data02 = soup.find('div', class_='RaceData02')
            track_info = race_data02.get_text(strip=True) if race_data02 else ''
            print(f"競馬場情報: {track_info}")

            # 競馬場名をパース
            # パターン1: "京都11R" → "京都"
            # パターン2: "4回京都6日目" → "京都"
            import re
            track_name = 'N/A'

            # パターン1を試す
            track_match = re.search(r'([^\d\s]+)\d+R', track_info)
            if track_match:
                track_name = track_match.group(1)
            else:
                # パターン2を試す（"4回京都6日目"）
                track_match = re.search(r'\d+回([^\d\s]+)\d+日目', track_info)
                if track_match:
                    track_name = track_match.group(1)

            # 距離・コースタイプを抽出
            distance_match = re.search(r'(\d+)m', race_details)
            distance = int(distance_match.group(1)) if distance_match else 1600

            course_type = '芝' if '芝' in race_details else 'ダ'

            # 馬場状態を抽出
            track_condition = '良'  # デフォルト
            for cond in ['不良', '重', '稍重', '良']:
                if cond in race_details:
                    track_condition = cond
                    break

            print(f"競馬場: {track_name}, 距離: {distance}m, コース: {course_type}, 馬場: {track_condition}")

            # 出走馬テーブル（Seleniumで全馬取得）
            table = soup.find('table', class_='Shutuba_Table')

            print(f"\n=== 出馬表データ抽出 ===")

            if not table:
                self.root.after(0, lambda: messagebox.showerror("エラー", f"出馬表が見つかりません\n\nrace_id: {race_id}\n\n可能性:\n- レースがまだ確定していない\n- race_idが間違っている"))
                return None

            horses = []

            # tr.HorseListクラスを持つ行を全て取得（Seleniumで動的ロード済み）
            horse_rows = table.select('tr.HorseList')
            print(f"HorseList行数: {len(horse_rows)}")

            for row_idx, row in enumerate(horse_rows, 1):
                try:
                    cols = row.find_all('td')
                    if len(cols) < 8:
                        continue

                    # 枠番（cols[0]）
                    waku_text = cols[0].get_text(strip=True)
                    waku = int(waku_text) if waku_text and waku_text.isdigit() else 1

                    # 馬番（cols[1]から取得）
                    umaban_text = cols[1].get_text(strip=True)
                    if not umaban_text or not umaban_text.isdigit():
                        continue
                    umaban = int(umaban_text)

                    print(f"  馬番{umaban}を抽出")

                    # 馬名とhorse_id（aタグから抽出）
                    horse_link = cols[3].find('a')
                    if horse_link:
                        horse_name = horse_link.get_text(strip=True)
                        href = horse_link.get('href', '')
                        horse_id_match = re.search(r'/horse/(\d+)', href)
                        horse_id = int(horse_id_match.group(1)) if horse_id_match else None
                    else:
                        horse_name = cols[3].get_text(strip=True)
                        horse_id = None

                    # 性齢（例: "牡5"）
                    sex_age = cols[4].get_text(strip=True)
                    sex = sex_age[0] if len(sex_age) > 0 else None
                    age = int(sex_age[1:]) if len(sex_age) > 1 and sex_age[1:].isdigit() else 4

                    # 斤量
                    load_text = cols[5].get_text(strip=True)
                    try:
                        load = float(load_text)
                    except:
                        load = 56.0

                    # 騎手
                    jockey_tag = cols[6].find('a')
                    jockey = jockey_tag.get_text(strip=True) if jockey_tag else cols[6].get_text(strip=True)

                    # 馬体重（例: "480(+2)"）
                    weight_text = cols[7].get_text(strip=True) if len(cols) > 7 else ''
                    weight_diff = 0
                    if weight_text:
                        weight_diff_match = re.search(r'\(([+-]?\d+)\)', weight_text)
                        if weight_diff_match:
                            weight_diff = int(weight_diff_match.group(1))

                    # 人気（未来レースでも発表されている場合がある）
                    ninki = None
                    if len(cols) > 8:
                        ninki_text = cols[8].get_text(strip=True)
                        if ninki_text and ninki_text.isdigit():
                            ninki = int(ninki_text)

                    # オッズ
                    odds_text = cols[9].get_text(strip=True) if len(cols) > 9 else ''
                    try:
                        odds = float(odds_text)
                    except:
                        # オッズ未発表の場合はデフォルト
                        odds = 5.0 + (umaban % 5)

                    horses.append({
                        'race_id': race_id,
                        'horse_id': horse_id,
                        'Umaban': umaban,
                        'Waku': waku,
                        'HorseName': horse_name,
                        'Sex': sex,
                        'Age': age,
                        'Load': load,
                        'WeightDiff': weight_diff,
                        'JockeyName': jockey,
                        'Odds': odds,
                        'Ninki': ninki,
                        'Rank': None,   # 未来レース
                        'race_name': race_name,
                        'date': race_date,
                        'track_name': track_name,
                        'distance': distance,
                        'course_type': course_type,
                        'weather': 'N/A',
                        'track_condition': track_condition,
                    })

                except Exception as e:
                    print(f"  行{row_idx}スキップ（エラー: {e}）")
                    continue

            if len(horses) == 0:
                self.root.after(0, lambda: messagebox.showerror("エラー", "出馬表データを抽出できませんでした"))
                return None

            # 期待される頭数をチェック
            expected_horses_match = re.search(r'(\d+)頭', track_info)
            if expected_horses_match:
                expected_horses = int(expected_horses_match.group(1))
                if len(horses) < expected_horses:
                    print(f"\n[警告] 期待される頭数({expected_horses}頭)より少ない({len(horses)}頭)です")
                elif len(horses) == expected_horses:
                    print(f"\n[成功] 全{expected_horses}頭のデータを取得しました！")

            print(f"\n出馬表取得完了: {len(horses)}頭")
            self.root.after(0, lambda: self.update_status(f"出馬表取得成功: {len(horses)}頭"))

            return pd.DataFrame(horses)

        except ImportError as e:
            self.root.after(0, lambda: messagebox.showerror("ライブラリ不足", f"必要なライブラリがインストールされていません\n\n{e}\n\n以下をインストールしてください:\npip install selenium beautifulsoup4 lxml"))
            return None

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: messagebox.showerror("取得エラー", f"出馬表の取得に失敗しました\n\n{e}\n\nrace_id: {race_id}"))
            return None

    def clear_results(self):
        """結果クリア"""
        # テーブルクリア
        for item in self.result_table.get_children():
            self.result_table.delete(item)

        # テキストクリア
        self.race_info_text.config(state='normal')
        self.race_info_text.delete('1.0', tk.END)
        self.race_info_text.config(state='disabled')

        self.bet_text.config(state='normal')
        self.bet_text.delete('1.0', tk.END)
        self.bet_text.config(state='disabled')

        self.race_id_entry.delete(0, tk.END)
        self.update_status("クリア完了")

    def run_prediction(self):
        """予測実行"""
        race_id_input = self.race_id_entry.get().strip()

        if not race_id_input:
            messagebox.showwarning("入力エラー", "race_idを入力してください")
            return

        try:
            race_id = int(race_id_input)
        except:
            messagebox.showerror("入力エラー", "race_idは数字で入力してください")
            return

        # バックグラウンドで実行
        self.predict_btn.config(state='disabled')
        self.update_status("予測中...")

        thread = threading.Thread(target=self._predict_background, args=(race_id,), daemon=True)
        thread.start()

    def _predict_background(self, race_id):
        """バックグラウンド予測処理"""
        try:
            # レースデータ取得（race_idの型を合わせる）
            # CSVのrace_idは文字列なので、検索時も文字列に変換
            race_id_str = str(race_id)
            race_horses = self.df[self.df['race_id'] == race_id_str].copy()

            print(f"\n=== レースデータ検索 ===")
            print(f"race_id: {race_id} (type: {type(race_id)})")
            print(f"race_id_str: {race_id_str} (type: {type(race_id_str)})")
            print(f"CSV内で見つかった行数: {len(race_horses)}")

            if len(race_horses) == 0:
                # 未来レース → 出馬表を取得
                self.root.after(0, lambda: self.update_status("未来レース: 出馬表を取得中..."))
                race_horses = self._fetch_shutuba(race_id)

                if race_horses is None or len(race_horses) == 0:
                    self.root.after(0, lambda: self.predict_btn.config(state='normal'))
                    return

            # 重複排除（念のため）
            if 'Umaban' in race_horses.columns:
                duplicates_before = len(race_horses)
                race_horses = race_horses.drop_duplicates(subset=['Umaban'], keep='first')
                duplicates_removed = duplicates_before - len(race_horses)
                if duplicates_removed > 0:
                    print(f"⚠ 重複馬番を{duplicates_removed}件削除しました")

            # date_parsed カラムを追加（feature_engineering で必要）
            if 'date' in race_horses.columns and 'date_parsed' not in race_horses.columns:
                race_horses['date_parsed'] = pd.to_datetime(race_horses['date'], errors='coerce')

            # 数値型の確認と変換（型の不一致を防ぐ）
            numeric_columns = ['Umaban', 'Waku', 'Age', 'Load', 'WeightDiff', 'Odds', 'distance', 'horse_id']
            for col in numeric_columns:
                if col in race_horses.columns:
                    race_horses[col] = pd.to_numeric(race_horses[col], errors='coerce')

            # レース情報
            race_info_row = race_horses.iloc[0]
            race_name = race_info_row.get('race_name', 'N/A')
            race_date = race_info_row.get('date', 'N/A')
            track_name = race_info_row.get('track_name', 'N/A')
            distance = race_info_row.get('distance', 'N/A')
            course_type = race_info_row.get('course_type', 'N/A')
            weather = race_info_row.get('weather', 'N/A')
            track_condition = race_info_row.get('track_condition', 'N/A')

            # レース情報を表示
            race_info_text = f"【{race_name}】\n"
            race_info_text += f"日付: {race_date}  |  場所: {track_name}  |  {course_type}{distance}m\n"
            race_info_text += f"天気: {weather}  |  馬場: {track_condition}  |  出走頭数: {len(race_horses)}頭"

            self.root.after(0, lambda: self._update_race_info(race_info_text))

            # 特徴量抽出
            self.root.after(0, lambda: self.update_status("特徴量抽出中..."))

            # デバッグ: 元データ確認
            print(f"\n=== デバッグ: race_horses ===")
            print(f"行数: {len(race_horses)}")
            print(f"馬番リスト: {race_horses['Umaban'].tolist()}")
            print(f"horse_idリスト: {race_horses['horse_id'].tolist() if 'horse_id' in race_horses.columns else 'horse_id列なし'}")

            feature_eng = FeatureEngineer(self.df)
            features_df = feature_eng.extract_features_for_race(race_id, race_horses)

            # デバッグ: 特徴量確認
            print(f"\n=== デバッグ: features_df ===")
            print(f"行数: {len(features_df)}")
            print(f"馬番リスト: {features_df['umaban'].tolist()}")

            # 重複チェック
            umaban_counts = features_df['umaban'].value_counts()
            duplicates = umaban_counts[umaban_counts > 1]
            if len(duplicates) > 0:
                print(f"⚠ 警告: 馬番の重複を検出！")
                print(f"重複馬番: {duplicates.to_dict()}")

            print(f"近3走サンプル:")
            for i in range(min(3, len(features_df))):
                umaban = features_df.iloc[i]['umaban']
                past = f"{features_df.iloc[i]['past_rank_1']}-{features_df.iloc[i]['past_rank_2']}-{features_df.iloc[i]['past_rank_3']}"
                horse_id = features_df.iloc[i].get('horse_id', 'N/A')
                print(f"  馬番{umaban} (horse_id={horse_id}): {past}")

            # オッズ確認
            print(f"\nオッズサンプル:")
            for i in range(min(3, len(features_df))):
                umaban = features_df.iloc[i]['umaban']
                log_odds = features_df.iloc[i]['log_odds']
                odds_recovered = np.exp(log_odds) - 1
                print(f"  馬番{umaban}: log_odds={log_odds:.3f}, 復元オッズ={odds_recovered:.1f}")

            # モデル予測
            predictions = []

            if self.model is not None:
                # モデルを使用した予測
                self.root.after(0, lambda: self.update_status("モデル予測中..."))

                # 特徴量ベクトルを作成
                feature_columns = [
                    'age', 'is_male', 'is_female', 'is_gelding', 'weight_diff', 'load',
                    'log_odds', 'ninki', 'waku', 'distance', 'is_turf', 'track_condition',
                    'past_rank_1', 'past_rank_2', 'past_rank_3', 'avg_rank_3races',
                    'best_rank_3races', 'top2_rate_3races', 'last_rank', 'days_since_last_race',
                    'running_style', 'jockey_win_rate', 'jockey_top2_rate',
                    'course_win_rate', 'distance_win_rate', 'is_top_sire',
                    'feature_24', 'feature_25', 'feature_26', 'feature_27',
                    'feature_28', 'feature_29', 'feature_30', 'feature_31'
                ]

                # 特徴量の欠損値を埋める
                for col in feature_columns:
                    if col not in features_df.columns:
                        features_df[col] = 0

                X = features_df[feature_columns].fillna(0).values

                try:
                    # モデルで予測
                    scores = self.model.predict(X)
                except Exception as e:
                    # モデル予測失敗 → オッズベースにフォールバック
                    print(f"モデル予測エラー: {e}")
                    # log_odds = log(1 + odds) なので、odds = exp(log_odds) - 1
                    odds_values = [np.exp(features_df.iloc[i]['log_odds']) - 1 for i in range(len(features_df))]
                    scores = [1.0 / max(o, 1.0) for o in odds_values]
            else:
                # モデルなし → オッズベース
                # log_odds = log(1 + odds) なので、odds = exp(log_odds) - 1
                odds_values = [np.exp(features_df.iloc[i]['log_odds']) - 1 for i in range(len(features_df))]
                scores = [1.0 / max(o, 1.0) for o in odds_values]

            # 予測結果を整形
            for i, (_, feature_row) in enumerate(features_df.iterrows()):
                # 元の馬データを取得
                horse = race_horses[race_horses['Umaban'] == feature_row['umaban']].iloc[0]

                umaban = feature_row['umaban']
                horse_name = horse.get('HorseName', 'N/A')
                jockey = horse.get('JockeyName', 'N/A')
                odds = horse.get('Odds', 10.0)
                ninki = horse.get('Ninki', None)
                actual_rank = horse.get('Rank', None)

                # 近3走
                past_ranks = f"{int(feature_row['past_rank_1'])}-{int(feature_row['past_rank_2'])}-{int(feature_row['past_rank_3'])}"

                # 脚質
                running_style = get_running_style_name(int(feature_row['running_style']))

                predictions.append({
                    'umaban': umaban,
                    'horse_name': horse_name,
                    'jockey': jockey,
                    'ninki': ninki,
                    'odds': odds,
                    'past_ranks': past_ranks,
                    'running_style': running_style,
                    'score': scores[i],
                    'actual_rank': actual_rank
                })

            # スコア順にソート
            predictions.sort(key=lambda x: x['score'], reverse=True)

            # スコアを確率（%）に変換
            total_score = sum([p['score'] for p in predictions])
            if total_score > 0:
                for pred in predictions:
                    pred['prob_pct'] = (pred['score'] / total_score) * 100
            else:
                for pred in predictions:
                    pred['prob_pct'] = 100.0 / len(predictions)

            # テーブルに表示
            self.root.after(0, lambda: self._display_predictions(predictions))

            # 推奨馬券を生成
            self.root.after(0, lambda: self._display_recommended_bets(predictions, race_id))

            self.root.after(0, lambda: self.update_status(f"予測完了: {race_name}"))

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("エラー", f"予測エラー:\n{e}"))
            self.root.after(0, lambda: self.update_status("予測エラー"))

        finally:
            self.root.after(0, lambda: self.predict_btn.config(state='normal'))

    def _update_race_info(self, text):
        """レース情報更新"""
        self.race_info_text.config(state='normal')
        self.race_info_text.delete('1.0', tk.END)
        self.race_info_text.insert('1.0', text)
        self.race_info_text.config(state='disabled')

    def _display_predictions(self, predictions):
        """予測結果を表示"""
        # クリア
        for item in self.result_table.get_children():
            self.result_table.delete(item)

        # データ挿入
        for i, pred in enumerate(predictions, 1):
            umaban = int(pred['umaban']) if pd.notna(pred['umaban']) else '-'
            horse_name = pred['horse_name']
            jockey = pred['jockey']
            ninki = int(pred['ninki']) if pd.notna(pred['ninki']) else '-'
            odds = f"{pred['odds']:.1f}" if pd.notna(pred['odds']) else '-'
            past_ranks = pred.get('past_ranks', '-')
            running_style = pred.get('running_style', '-')
            prob_pct = f"{pred.get('prob_pct', 0):.1f}%"
            actual = f"{int(pred['actual_rank'])}着" if pd.notna(pred['actual_rank']) else '-'

            # 色分け（TOP3）
            tag = ''
            if i == 1:
                tag = 'first'
            elif i == 2:
                tag = 'second'
            elif i == 3:
                tag = 'third'

            self.result_table.insert('', 'end', values=(i, umaban, horse_name, jockey, ninki, odds, past_ranks, running_style, prob_pct, actual), tags=(tag,))

        # タグの色設定
        self.result_table.tag_configure('first', background='#FFD700')  # 金
        self.result_table.tag_configure('second', background='#C0C0C0')  # 銀
        self.result_table.tag_configure('third', background='#CD7F32')  # 銅

    def _display_recommended_bets(self, predictions, race_id):
        """推奨馬券を表示"""
        top3 = [int(p['umaban']) for p in predictions[:3]]
        top5 = [int(p['umaban']) for p in predictions[:5]]

        bet_text = "【推奨馬券】\n\n"
        bet_text += f"1. ワイド 1-3:  {top3[0]}-{top3[2]}  (100円)  ⭐⭐⭐\n"
        bet_text += f"2. 3連複 BOX5頭:  {'-'.join(map(str, top5))}  (1,000円)  ⭐⭐\n"
        bet_text += f"3. 馬連 1-2:  {top3[0]}-{top3[1]}  (100円)  ⭐⭐⭐⭐\n\n"
        bet_text += f"合計購入額: 1,200円"

        # 的中判定（過去レースの場合）
        if pd.notna(predictions[0]['actual_rank']):
            actual_results = [(p['umaban'], p['actual_rank']) for p in predictions if pd.notna(p['actual_rank'])]
            actual_results.sort(key=lambda x: x[1])

            if len(actual_results) >= 3:
                actual_1st = actual_results[0][0]
                actual_2nd = actual_results[1][0]
                actual_3rd = actual_results[2][0]

                bet_text += f"\n\n【的中判定】\n"
                bet_text += f"実際の結果: {actual_1st}着 → {actual_2nd}着 → {actual_3rd}着\n"

                # 1着的中
                if top3[0] == actual_1st:
                    bet_text += f"✓ 1着的中！\n"
                else:
                    bet_text += f"✗ 1着外れ（予測: {top3[0]}番 → 実際: {actual_1st}番）\n"

                # ワイド1-3
                wide_pred = set([top3[0], top3[2]])
                wide_actual_candidates = [
                    set([actual_1st, actual_2nd]),
                    set([actual_1st, actual_3rd]),
                    set([actual_2nd, actual_3rd])
                ]
                if wide_pred in wide_actual_candidates:
                    bet_text += f"✓ ワイド1-3 的中！\n"
                else:
                    bet_text += f"✗ ワイド1-3 外れ\n"

                # 3連複BOX5頭
                box5_pred = set(top5)
                actual_top3 = set([actual_1st, actual_2nd, actual_3rd])
                if actual_top3.issubset(box5_pred):
                    bet_text += f"✓ 3連複BOX5頭 的中！\n"
                else:
                    bet_text += f"✗ 3連複BOX5頭 外れ\n"

        self.bet_text.config(state='normal')
        self.bet_text.delete('1.0', tk.END)
        self.bet_text.insert('1.0', bet_text)
        self.bet_text.config(state='disabled')

def main():
    root = tk.Tk()
    app = KeibaYosouTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()
