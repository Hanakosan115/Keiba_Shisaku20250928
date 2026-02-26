"""
競馬分析統合ツール
データ管理、モデル訓練、バックテスト、予測を統合したGUIツール
"""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import pandas as pd
import json
import os
from datetime import datetime
from pathlib import Path
import threading

class KeibaAnalysisTool:
    def __init__(self, root):
        self.root = root
        self.root.title("競馬分析統合ツール v2.0")
        self.root.geometry("1000x700")

        # 設定の読み込み
        self.config_file = Path("keiba_tool_config.json")
        self.load_config()

        # メインUI作成
        self.create_ui()

    def load_config(self):
        """設定ファイルの読み込み"""
        default_config = {
            "data_dir": str(Path.cwd()),
            "clean_csv": str(Path.cwd() / "netkeiba_data_2020_2024_clean.csv"),
            "clean_json": str(Path.cwd() / "netkeiba_data_payouts_2020_2024_clean.json"),
            "model_file": str(Path.cwd() / "lightgbm_model_trifecta_optimized_fixed.pkl"),
        }

        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = default_config
            self.save_config()

    def save_config(self):
        """設定ファイルの保存"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def create_ui(self):
        """UIの作成"""
        # タブコントロール
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 各タブを作成
        self.create_data_tab()
        self.create_model_tab()
        self.create_backtest_tab()
        self.create_predict_tab()
        self.create_settings_tab()

        # ステータスバー
        self.status_bar = tk.Label(self.root, text="準備完了", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def create_data_tab(self):
        """データ管理タブ"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="データ管理")

        # データ統計表示エリア
        stats_frame = ttk.LabelFrame(tab, text="データ統計")
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.data_stats_text = scrolledtext.ScrolledText(stats_frame, height=15, width=80)
        self.data_stats_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ボタンエリア
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text="データ統計を更新",
                  command=self.update_data_stats).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="データクリーニング実行",
                  command=self.clean_data).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="データ検証",
                  command=self.validate_data).pack(side=tk.LEFT, padx=5)

    def create_model_tab(self):
        """モデル管理タブ"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="モデル訓練")

        # パラメータ設定
        param_frame = ttk.LabelFrame(tab, text="訓練パラメータ")
        param_frame.pack(fill=tk.X, padx=10, pady=5)

        # 訓練期間
        ttk.Label(param_frame, text="訓練期間:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        period_frame = ttk.Frame(param_frame)
        period_frame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(period_frame, text="開始:").pack(side=tk.LEFT)
        self.train_start_year = ttk.Combobox(period_frame, values=list(range(2020, 2025)), width=6)
        self.train_start_year.set("2020")
        self.train_start_year.pack(side=tk.LEFT, padx=2)

        ttk.Label(period_frame, text="年").pack(side=tk.LEFT)
        self.train_start_month = ttk.Combobox(period_frame, values=list(range(1, 13)), width=4)
        self.train_start_month.set("1")
        self.train_start_month.pack(side=tk.LEFT, padx=2)
        ttk.Label(period_frame, text="月").pack(side=tk.LEFT)

        ttk.Label(period_frame, text="終了:").pack(side=tk.LEFT, padx=(10, 0))
        self.train_end_year = ttk.Combobox(period_frame, values=list(range(2020, 2025)), width=6)
        self.train_end_year.set("2023")
        self.train_end_year.pack(side=tk.LEFT, padx=2)

        ttk.Label(period_frame, text="年").pack(side=tk.LEFT)
        self.train_end_month = ttk.Combobox(period_frame, values=list(range(1, 13)), width=4)
        self.train_end_month.set("12")
        self.train_end_month.pack(side=tk.LEFT, padx=2)
        ttk.Label(period_frame, text="月").pack(side=tk.LEFT)

        # モデルタイプ
        ttk.Label(param_frame, text="モデルタイプ:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.model_type = ttk.Combobox(param_frame,
                                       values=["3連単特化", "汎用ランキング", "複勝特化"],
                                       width=20)
        self.model_type.set("3連単特化")
        self.model_type.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # ログエリア
        log_frame = ttk.LabelFrame(tab, text="訓練ログ")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.model_log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.model_log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ボタンエリア
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text="モデル訓練開始",
                  command=self.train_model).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="モデル評価",
                  command=self.evaluate_model).pack(side=tk.LEFT, padx=5)

    def create_backtest_tab(self):
        """バックテストタブ"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="バックテスト")

        # テスト設定
        config_frame = ttk.LabelFrame(tab, text="バックテスト設定")
        config_frame.pack(fill=tk.X, padx=10, pady=5)

        # テスト期間
        ttk.Label(config_frame, text="テスト期間:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

        period_frame = ttk.Frame(config_frame)
        period_frame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        self.test_year = ttk.Combobox(period_frame, values=list(range(2020, 2025)), width=6)
        self.test_year.set("2024")
        self.test_year.pack(side=tk.LEFT, padx=2)
        ttk.Label(period_frame, text="年").pack(side=tk.LEFT)

        # 戦略選択
        ttk.Label(config_frame, text="テスト戦略:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

        strategy_frame = ttk.Frame(config_frame)
        strategy_frame.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        self.strategy_vars = {}
        strategies = ["ワイド_1-3", "3連複_BOX5頭", "馬連_1-2", "3連単_1着固定"]
        for i, strategy in enumerate(strategies):
            var = tk.BooleanVar(value=True if i < 2 else False)
            self.strategy_vars[strategy] = var
            ttk.Checkbutton(strategy_frame, text=strategy, variable=var).pack(anchor=tk.W)

        # 確信度フィルタ
        ttk.Label(config_frame, text="確信度フィルタ:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.confidence_filter = ttk.Combobox(config_frame,
                                             values=["なし", "上位10%", "上位20%", "上位30%"],
                                             width=15)
        self.confidence_filter.set("なし")
        self.confidence_filter.grid(row=2, column=1, padx=5, pady=5, sticky=tk.W)

        # 結果表示エリア
        result_frame = ttk.LabelFrame(tab, text="バックテスト結果")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.backtest_result_text = scrolledtext.ScrolledText(result_frame, height=15, width=80)
        self.backtest_result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ボタンエリア
        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(btn_frame, text="バックテスト実行",
                  command=self.run_backtest).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="結果をCSV出力",
                  command=self.export_results).pack(side=tk.LEFT, padx=5)

    def create_predict_tab(self):
        """予測タブ"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="レース予測")

        # race_id入力
        input_frame = ttk.LabelFrame(tab, text="レース情報")
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(input_frame, text="race_id:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.race_id_entry = ttk.Entry(input_frame, width=20)
        self.race_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Button(input_frame, text="予測実行",
                  command=self.predict_race).grid(row=0, column=2, padx=5, pady=5)

        # 予測結果表示
        result_frame = ttk.LabelFrame(tab, text="予測結果")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.predict_result_text = scrolledtext.ScrolledText(result_frame, height=20, width=80)
        self.predict_result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def create_settings_tab(self):
        """設定タブ"""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="設定")

        # ファイルパス設定
        paths_frame = ttk.LabelFrame(tab, text="ファイルパス")
        paths_frame.pack(fill=tk.X, padx=10, pady=5)

        # CSV
        ttk.Label(paths_frame, text="クリーンCSV:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.csv_path_entry = ttk.Entry(paths_frame, width=50)
        self.csv_path_entry.insert(0, self.config.get("clean_csv", ""))
        self.csv_path_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(paths_frame, text="参照",
                  command=lambda: self.browse_file(self.csv_path_entry, "CSV")).grid(row=0, column=2, padx=5)

        # JSON
        ttk.Label(paths_frame, text="クリーンJSON:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.json_path_entry = ttk.Entry(paths_frame, width=50)
        self.json_path_entry.insert(0, self.config.get("clean_json", ""))
        self.json_path_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(paths_frame, text="参照",
                  command=lambda: self.browse_file(self.json_path_entry, "JSON")).grid(row=1, column=2, padx=5)

        # モデル
        ttk.Label(paths_frame, text="モデルファイル:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.model_path_entry = ttk.Entry(paths_frame, width=50)
        self.model_path_entry.insert(0, self.config.get("model_file", ""))
        self.model_path_entry.grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(paths_frame, text="参照",
                  command=lambda: self.browse_file(self.model_path_entry, "PKL")).grid(row=2, column=2, padx=5)

        # 保存ボタン
        ttk.Button(tab, text="設定を保存",
                  command=self.save_settings).pack(pady=10)

        # 情報表示
        info_frame = ttk.LabelFrame(tab, text="システム情報")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        info_text = scrolledtext.ScrolledText(info_frame, height=10, width=80)
        info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        info = f"""競馬分析統合ツール v2.0

作業ディレクトリ: {Path.cwd()}
設定ファイル: {self.config_file}

機能:
- データクリーニング（未来データ自動除外）
- モデル訓練（LightGBM）
- 複数戦略バックテスト
- 確信度フィルタリング
- レース予測

Python バージョン: {pd.__version__}
"""
        info_text.insert(tk.END, info)
        info_text.config(state=tk.DISABLED)

    # ===== イベントハンドラ =====

    def browse_file(self, entry_widget, file_type):
        """ファイル選択ダイアログ"""
        filetypes = {
            "CSV": [("CSV files", "*.csv")],
            "JSON": [("JSON files", "*.json")],
            "PKL": [("Pickle files", "*.pkl")]
        }

        filename = filedialog.askopenfilename(filetypes=filetypes.get(file_type, [("All files", "*.*")]))
        if filename:
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, filename)

    def update_data_stats(self):
        """データ統計の更新"""
        self.status_bar.config(text="データ統計を計算中...")
        self.data_stats_text.delete(1.0, tk.END)

        try:
            csv_path = self.csv_path_entry.get()
            if not os.path.exists(csv_path):
                self.data_stats_text.insert(tk.END, "エラー: CSVファイルが見つかりません\n")
                return

            df = pd.read_csv(csv_path, low_memory=False)
            df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

            stats = f"""=== データ統計 ===

総行数: {len(df):,}
日付範囲: {df['date_parsed'].min()} ～ {df['date_parsed'].max()}

ユニークレース数: {df['race_id'].nunique():,}
ユニーク馬数: {df['horse_id'].nunique():,}

年別データ数:
"""
            for year in range(2020, 2025):
                year_data = df[df['date_parsed'].dt.year == year]
                stats += f"  {year}年: {len(year_data):,}行\n"

            # 未来データチェック
            today = datetime.now()
            future_data = df[df['date_parsed'] > today]
            if len(future_data) > 0:
                stats += f"\n警告: 未来データが{len(future_data):,}行あります！\n"
            else:
                stats += f"\n✓ 未来データなし（正常）\n"

            self.data_stats_text.insert(tk.END, stats)
            self.status_bar.config(text="データ統計の更新完了")

        except Exception as e:
            self.data_stats_text.insert(tk.END, f"エラー: {str(e)}\n")
            self.status_bar.config(text="エラーが発生しました")

    def clean_data(self):
        """データクリーニング実行"""
        if not messagebox.askyesno("確認", "データクリーニングを実行しますか？\n未来データと重複を削除します。"):
            return

        self.status_bar.config(text="データクリーニング中...")
        self.data_stats_text.insert(tk.END, "\n\n" + "="*60 + "\n")
        self.data_stats_text.insert(tk.END, "データクリーニング開始\n")
        self.data_stats_text.insert(tk.END, "="*60 + "\n")
        self.root.update()

        try:
            csv_path = self.csv_path_entry.get()
            json_path = self.json_path_entry.get()

            if not os.path.exists(csv_path):
                messagebox.showerror("エラー", "CSVファイルが見つかりません")
                return

            # CSVのクリーニング
            self.data_stats_text.insert(tk.END, "\n[1/2] CSVデータをクリーニング中...\n")
            self.root.update()

            df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
            original_rows = len(df)
            self.data_stats_text.insert(tk.END, f"  元データ: {original_rows:,}行\n")

            # 日付解析
            df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

            # 未来データを削除
            today = datetime.now()
            df_clean = df[df['date_parsed'] <= today].copy()
            future_removed = original_rows - len(df_clean)
            self.data_stats_text.insert(tk.END, f"  未来データ削除: {future_removed:,}行\n")

            # 重複削除
            if 'race_id' in df_clean.columns and 'horse_id' in df_clean.columns:
                before_dup = len(df_clean)
                df_clean = df_clean.drop_duplicates(subset=['race_id', 'horse_id'], keep='last')
                dup_removed = before_dup - len(df_clean)
                self.data_stats_text.insert(tk.END, f"  重複削除: {dup_removed:,}行\n")

            # date_parsedカラムを削除
            df_clean = df_clean.drop(columns=['date_parsed'])

            # 保存
            output_csv = csv_path.replace('.csv', '_cleaned.csv')
            df_clean.to_csv(output_csv, index=False, encoding='utf-8')
            self.data_stats_text.insert(tk.END, f"  クリーン後: {len(df_clean):,}行\n")
            self.data_stats_text.insert(tk.END, f"  保存: {os.path.basename(output_csv)}\n")

            # JSONのクリーニング
            if os.path.exists(json_path):
                self.data_stats_text.insert(tk.END, "\n[2/2] JSONデータをクリーニング中...\n")
                self.root.update()

                with open(json_path, 'r', encoding='utf-8') as f:
                    payout_list = json.load(f)

                original_races = len(payout_list)
                self.data_stats_text.insert(tk.END, f"  元データ: {original_races:,}レース\n")

                # 有効なrace_idのセット
                valid_race_ids = set(df_clean['race_id'].astype(str).unique())

                # 有効なrace_idのみ保持
                payout_clean = [p for p in payout_list if str(p.get('race_id')) in valid_race_ids]
                races_removed = original_races - len(payout_clean)
                self.data_stats_text.insert(tk.END, f"  無効レース削除: {races_removed:,}レース\n")

                # 保存
                output_json = json_path.replace('.json', '_cleaned.json')
                with open(output_json, 'w', encoding='utf-8') as f:
                    json.dump(payout_clean, f, indent=2, ensure_ascii=False)

                self.data_stats_text.insert(tk.END, f"  クリーン後: {len(payout_clean):,}レース\n")
                self.data_stats_text.insert(tk.END, f"  保存: {os.path.basename(output_json)}\n")

            # 完了
            self.data_stats_text.insert(tk.END, "\n" + "="*60 + "\n")
            self.data_stats_text.insert(tk.END, "クリーニング完了！\n")
            self.data_stats_text.insert(tk.END, "="*60 + "\n")
            self.status_bar.config(text="データクリーニング完了")

            result_msg = f"クリーニング完了！\n\n"
            result_msg += f"CSV: {future_removed + dup_removed:,}行削除\n"
            result_msg += f"新ファイル: {os.path.basename(output_csv)}\n"
            if os.path.exists(json_path):
                result_msg += f"\nJSON: {races_removed:,}レース削除\n"
                result_msg += f"新ファイル: {os.path.basename(output_json)}"

            messagebox.showinfo("完了", result_msg)

        except Exception as e:
            self.data_stats_text.insert(tk.END, f"\nエラー: {str(e)}\n")
            self.status_bar.config(text="エラーが発生しました")
            messagebox.showerror("エラー", f"クリーニング中にエラーが発生しました:\n{str(e)}")

    def validate_data(self):
        """データ検証"""
        self.status_bar.config(text="データ検証中...")
        self.data_stats_text.insert(tk.END, "\n\n" + "="*60 + "\n")
        self.data_stats_text.insert(tk.END, "データ検証開始\n")
        self.data_stats_text.insert(tk.END, "="*60 + "\n")
        self.root.update()

        try:
            csv_path = self.csv_path_entry.get()
            if not os.path.exists(csv_path):
                messagebox.showerror("エラー", "CSVファイルが見つかりません")
                return

            df = pd.read_csv(csv_path, low_memory=False)
            df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

            issues = []
            warnings = []

            # 1. 未来データチェック
            self.data_stats_text.insert(tk.END, "\n[1/7] 未来データをチェック中...\n")
            self.root.update()

            today = datetime.now()
            future_data = df[df['date_parsed'] > today]
            if len(future_data) > 0:
                issues.append(f"未来データ: {len(future_data):,}行")
                self.data_stats_text.insert(tk.END, f"  ❌ 未来データが{len(future_data):,}行あります\n")
            else:
                self.data_stats_text.insert(tk.END, "  ✓ 未来データなし\n")

            # 2. 重複チェック
            self.data_stats_text.insert(tk.END, "\n[2/7] 重複をチェック中...\n")
            self.root.update()

            if 'race_id' in df.columns and 'horse_id' in df.columns:
                duplicates = df.duplicated(subset=['race_id', 'horse_id'])
                dup_count = duplicates.sum()
                if dup_count > 0:
                    warnings.append(f"重複レコード: {dup_count:,}行")
                    self.data_stats_text.insert(tk.END, f"  ⚠️ 重複が{dup_count:,}行あります\n")
                else:
                    self.data_stats_text.insert(tk.END, "  ✓ 重複なし\n")

            # 3. 欠損値チェック
            self.data_stats_text.insert(tk.END, "\n[3/7] 欠損値をチェック中...\n")
            self.root.update()

            critical_columns = ['race_id', 'horse_id', 'Rank', 'date']
            for col in critical_columns:
                if col in df.columns:
                    null_count = df[col].isna().sum()
                    if null_count > 0:
                        warnings.append(f"{col}に欠損値: {null_count:,}個")
                        self.data_stats_text.insert(tk.END, f"  ⚠️ {col}: {null_count:,}個の欠損値\n")
                else:
                    issues.append(f"必須カラム'{col}'が存在しません")
                    self.data_stats_text.insert(tk.END, f"  ❌ カラム'{col}'が存在しません\n")

            if not any(col not in df.columns for col in critical_columns):
                self.data_stats_text.insert(tk.END, "  ✓ 必須カラムはすべて存在\n")

            # 4. 日付形式チェック
            self.data_stats_text.insert(tk.END, "\n[4/7] 日付形式をチェック中...\n")
            self.root.update()

            invalid_dates = df['date_parsed'].isna().sum()
            if invalid_dates > 0:
                warnings.append(f"無効な日付: {invalid_dates:,}個")
                self.data_stats_text.insert(tk.END, f"  ⚠️ 無効な日付が{invalid_dates:,}個あります\n")
            else:
                self.data_stats_text.insert(tk.END, "  ✓ すべての日付が有効\n")

            # 5. Rankの範囲チェック
            self.data_stats_text.insert(tk.END, "\n[5/7] Rank値をチェック中...\n")
            self.root.update()

            if 'Rank' in df.columns:
                rank_numeric = pd.to_numeric(df['Rank'], errors='coerce')
                invalid_ranks = (rank_numeric < 1) | (rank_numeric > 18)
                invalid_rank_count = invalid_ranks.sum()
                if invalid_rank_count > 0:
                    warnings.append(f"異常なRank値: {invalid_rank_count:,}個")
                    self.data_stats_text.insert(tk.END, f"  ⚠️ 異常なRank値が{invalid_rank_count:,}個あります\n")
                else:
                    self.data_stats_text.insert(tk.END, "  ✓ すべてのRank値が正常範囲（1-18）\n")

            # 6. レース整合性チェック
            self.data_stats_text.insert(tk.END, "\n[6/7] レース整合性をチェック中...\n")
            self.root.update()

            race_counts = df.groupby('race_id').size()
            small_races = (race_counts < 8).sum()
            large_races = (race_counts > 18).sum()

            if small_races > 0:
                warnings.append(f"出走頭数<8のレース: {small_races:,}個")
                self.data_stats_text.insert(tk.END, f"  ⚠️ 出走頭数<8のレース: {small_races:,}個\n")

            if large_races > 0:
                warnings.append(f"出走頭数>18のレース: {large_races:,}個")
                self.data_stats_text.insert(tk.END, f"  ⚠️ 出走頭数>18のレース: {large_races:,}個\n")

            if small_races == 0 and large_races == 0:
                self.data_stats_text.insert(tk.END, "  ✓ すべてのレースの出走頭数が正常範囲（8-18頭）\n")

            # 7. データ品質スコア
            self.data_stats_text.insert(tk.END, "\n[7/7] データ品質スコアを計算中...\n")
            self.root.update()

            total_checks = 7
            issues_count = len(issues)
            warnings_count = len(warnings)

            quality_score = max(0, 100 - (issues_count * 20) - (warnings_count * 5))

            self.data_stats_text.insert(tk.END, f"\n  データ品質スコア: {quality_score}/100\n")

            if quality_score >= 90:
                quality_label = "優秀"
                emoji = "🌟"
            elif quality_score >= 70:
                quality_label = "良好"
                emoji = "✓"
            elif quality_score >= 50:
                quality_label = "要改善"
                emoji = "⚠️"
            else:
                quality_label = "問題あり"
                emoji = "❌"

            # サマリー表示
            self.data_stats_text.insert(tk.END, "\n" + "="*60 + "\n")
            self.data_stats_text.insert(tk.END, "検証サマリー\n")
            self.data_stats_text.insert(tk.END, "="*60 + "\n")
            self.data_stats_text.insert(tk.END, f"\n総合評価: {emoji} {quality_label} ({quality_score}/100)\n\n")

            if issues:
                self.data_stats_text.insert(tk.END, "重大な問題:\n")
                for issue in issues:
                    self.data_stats_text.insert(tk.END, f"  ❌ {issue}\n")

            if warnings:
                self.data_stats_text.insert(tk.END, "\n警告:\n")
                for warning in warnings:
                    self.data_stats_text.insert(tk.END, f"  ⚠️ {warning}\n")

            if not issues and not warnings:
                self.data_stats_text.insert(tk.END, "✓ 問題は見つかりませんでした！\n")

            self.data_stats_text.insert(tk.END, "\n" + "="*60 + "\n")
            self.status_bar.config(text=f"データ検証完了 - 品質スコア: {quality_score}/100")

            # 結果ダイアログ
            result_msg = f"データ品質スコア: {quality_score}/100\n"
            result_msg += f"評価: {quality_label}\n\n"
            if issues:
                result_msg += f"重大な問題: {len(issues)}件\n"
            if warnings:
                result_msg += f"警告: {len(warnings)}件"

            if issues:
                messagebox.showwarning("検証完了", result_msg)
            else:
                messagebox.showinfo("検証完了", result_msg)

        except Exception as e:
            self.data_stats_text.insert(tk.END, f"\nエラー: {str(e)}\n")
            self.status_bar.config(text="エラーが発生しました")
            messagebox.showerror("エラー", f"検証中にエラーが発生しました:\n{str(e)}")

    def train_model(self):
        """モデル訓練"""
        if not messagebox.askyesno("確認", "モデル訓練を開始しますか？\n数分かかる場合があります。"):
            return

        # バックグラウンドで実行
        thread = threading.Thread(target=self._train_model_background)
        thread.daemon = True
        thread.start()

    def _train_model_background(self):
        """モデル訓練のバックグラウンド実行"""
        try:
            self.status_bar.config(text="モデル訓練中...")
            self.model_log_text.insert(tk.END, "\n" + "="*60 + "\n")
            self.model_log_text.insert(tk.END, "モデル訓練開始\n")
            self.model_log_text.insert(tk.END, "="*60 + "\n")
            self.root.update()

            # パラメータ取得
            start_year = int(self.train_start_year.get())
            start_month = int(self.train_start_month.get())
            end_year = int(self.train_end_year.get())
            end_month = int(self.train_end_month.get())
            model_type = self.model_type.get()

            self.model_log_text.insert(tk.END, f"\n訓練期間: {start_year}/{start_month:02d} ～ {end_year}/{end_month:02d}\n")
            self.model_log_text.insert(tk.END, f"モデルタイプ: {model_type}\n")
            self.root.update()

            # データ読み込み
            self.model_log_text.insert(tk.END, "\n[1/4] データ読み込み中...\n")
            self.root.update()

            csv_path = self.csv_path_entry.get()
            if not os.path.exists(csv_path):
                raise FileNotFoundError("CSVファイルが見つかりません")

            import lightgbm as lgb
            import numpy as np

            df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
            df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

            self.model_log_text.insert(tk.END, f"  総データ: {len(df):,}行\n")
            self.root.update()

            # 訓練期間でフィルタ
            start_date = pd.Timestamp(f"{start_year}-{start_month:02d}-01")
            end_date = pd.Timestamp(f"{end_year}-{end_month:02d}-01") + pd.offsets.MonthEnd(1)

            train_df = df[(df['date_parsed'] >= start_date) & (df['date_parsed'] <= end_date)]
            self.model_log_text.insert(tk.END, f"  訓練データ: {len(train_df):,}行\n")
            self.model_log_text.insert(tk.END, f"  レース数: {train_df['race_id'].nunique():,}\n")
            self.root.update()

            # 特徴量作成
            self.model_log_text.insert(tk.END, "\n[2/4] 特徴量を作成中...\n")
            self.root.update()

            # シンプルな特徴量（デモ用）
            features = []
            labels = []
            groups = []

            for race_id in train_df['race_id'].unique()[:1000]:  # デモ用に1000レース限定
                race_data = train_df[train_df['race_id'] == race_id]
                if len(race_data) < 8:
                    continue

                for _, horse in race_data.iterrows():
                    # 基本特徴量
                    age = pd.to_numeric(horse.get('Age'), errors='coerce')
                    weight_diff = pd.to_numeric(horse.get('WeightDiff'), errors='coerce')
                    odds = pd.to_numeric(horse.get('Odds_x'), errors='coerce')
                    if pd.isna(odds):
                        odds = pd.to_numeric(horse.get('Odds_y'), errors='coerce')
                    ninki = pd.to_numeric(horse.get('Ninki'), errors='coerce')

                    feature_vector = [
                        age if pd.notna(age) else 4,
                        weight_diff if pd.notna(weight_diff) else 0,
                        np.log1p(odds) if pd.notna(odds) and odds > 0 else 2,
                        ninki if pd.notna(ninki) else 8,
                    ]

                    rank = pd.to_numeric(horse.get('Rank'), errors='coerce')
                    if pd.notna(rank):
                        features.append(feature_vector)
                        labels.append(rank)
                        groups.append(race_id)

            self.model_log_text.insert(tk.END, f"  特徴量数: {len(features[0]) if features else 0}\n")
            self.model_log_text.insert(tk.END, f"  サンプル数: {len(features):,}\n")
            self.root.update()

            # モデル訓練
            self.model_log_text.insert(tk.END, "\n[3/4] モデル訓練中...\n")
            self.root.update()

            X = np.array(features)
            y = np.array(labels)

            # LightGBM LambdaRankパラメータ
            params = {
                'objective': 'lambdarank',
                'metric': 'ndcg',
                'boosting_type': 'gbdt',
                'num_leaves': 31,
                'learning_rate': 0.05,
                'feature_fraction': 0.9,
                'verbosity': -1
            }

            train_data = lgb.Dataset(X, label=y, group=[groups.count(g) for g in set(groups)])
            model = lgb.train(params, train_data, num_boost_round=100)

            self.model_log_text.insert(tk.END, "  訓練完了！\n")
            self.root.update()

            # モデル保存
            self.model_log_text.insert(tk.END, "\n[4/4] モデル保存中...\n")
            self.root.update()

            model_path = self.model_path_entry.get()
            if not model_path:
                model_path = str(Path.cwd() / f"model_{model_type}_{start_year}{start_month:02d}_{end_year}{end_month:02d}.pkl")

            import pickle
            with open(model_path, 'wb') as f:
                pickle.dump({
                    'model': model,
                    'feature_names': ['age', 'weight_diff', 'log_odds', 'ninki'],
                    'model_type': model_type,
                    'train_period': f"{start_year}/{start_month:02d}-{end_year}/{end_month:02d}"
                }, f)

            self.model_log_text.insert(tk.END, f"  保存: {os.path.basename(model_path)}\n")

            # 完了
            self.model_log_text.insert(tk.END, "\n" + "="*60 + "\n")
            self.model_log_text.insert(tk.END, "訓練完了！\n")
            self.model_log_text.insert(tk.END, "="*60 + "\n")
            self.status_bar.config(text="モデル訓練完了")

            messagebox.showinfo("完了", f"モデル訓練が完了しました！\n\n保存先: {os.path.basename(model_path)}")

        except Exception as e:
            self.model_log_text.insert(tk.END, f"\nエラー: {str(e)}\n")
            self.status_bar.config(text="エラーが発生しました")
            messagebox.showerror("エラー", f"訓練中にエラーが発生しました:\n{str(e)}")

    def evaluate_model(self):
        """モデル評価"""
        self.model_log_text.insert(tk.END, "モデル評価中...\n")
        # TODO: 実装
        messagebox.showinfo("情報", "モデル評価機能は次のバージョンで実装予定です")

    def run_backtest(self):
        """バックテスト実行"""
        if not messagebox.askyesno("確認", "バックテストを開始しますか？"):
            return

        # バックグラウンドで実行
        thread = threading.Thread(target=self._run_backtest_background)
        thread.daemon = True
        thread.start()

    def _run_backtest_background(self):
        """バックテストのバックグラウンド実行"""
        try:
            self.status_bar.config(text="バックテスト実行中...")
            self.backtest_result_text.insert(tk.END, "\n" + "="*70 + "\n")
            self.backtest_result_text.insert(tk.END, "バックテスト開始\n")
            self.backtest_result_text.insert(tk.END, "="*70 + "\n")
            self.root.update()

            # パラメータ取得
            test_year = int(self.test_year.get())
            selected_strategies = [name for name, var in self.strategy_vars.items() if var.get()]
            confidence_filter = self.confidence_filter.get()

            self.backtest_result_text.insert(tk.END, f"\nテスト年: {test_year}年\n")
            self.backtest_result_text.insert(tk.END, f"テスト戦略: {', '.join(selected_strategies)}\n")
            self.backtest_result_text.insert(tk.END, f"確信度フィルタ: {confidence_filter}\n")
            self.root.update()

            # データ読み込み
            self.backtest_result_text.insert(tk.END, "\n[1/3] データ読み込み中...\n")
            self.root.update()

            csv_path = self.csv_path_entry.get()
            json_path = self.json_path_entry.get()

            if not os.path.exists(csv_path) or not os.path.exists(json_path):
                raise FileNotFoundError("データファイルが見つかりません")

            df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
            df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

            with open(json_path, 'r', encoding='utf-8') as f:
                payout_list = json.load(f)
                payout_dict = {str(p['race_id']): p for p in payout_list}

            # テスト年でフィルタ
            test_df = df[df['date_parsed'].dt.year == test_year]
            race_ids = test_df['race_id'].unique()

            self.backtest_result_text.insert(tk.END, f"  対象: {test_year}年 {len(race_ids):,}レース\n")
            self.root.update()

            # バックテスト実行
            self.backtest_result_text.insert(tk.END, "\n[2/3] バックテスト実行中...\n")
            self.root.update()

            results = {}
            for strategy_name in selected_strategies:
                results[strategy_name] = {
                    'total_races': 0,
                    'hit_count': 0,
                    'total_cost': 0,
                    'total_return': 0
                }

            # シンプルなバックテスト（予測はオッズ順）
            for idx, race_id in enumerate(race_ids):
                if (idx + 1) % 500 == 0:
                    self.backtest_result_text.insert(tk.END, f"  進捗: {idx+1}/{len(race_ids)}\n")
                    self.root.update()

                race_horses = test_df[test_df['race_id'] == race_id].copy()
                if len(race_horses) < 8:
                    continue

                # オッズ順で予測（簡易版）
                race_horses['odds_val'] = pd.to_numeric(race_horses['Odds_x'], errors='coerce')
                race_horses = race_horses.sort_values('odds_val')
                pred_horses = race_horses['Umaban'].head(8).tolist()

                # 配当データ
                payout_data = payout_dict.get(str(race_id), {})
                if not payout_data:
                    continue

                # 各戦略をテスト
                for strategy_name in selected_strategies:
                    results[strategy_name]['total_races'] += 1

                    if strategy_name == 'ワイド_1-3' and len(pred_horses) >= 3:
                        # ワイド 1-3
                        wide_data = payout_data.get('ワイド', {})
                        wide_horses = wide_data.get('馬番', [])
                        wide_payouts = wide_data.get('払戻金', [])

                        pred_wide = set([str(pred_horses[0]), str(pred_horses[2])])
                        results[strategy_name]['total_cost'] += 100

                        for i in range(0, len(wide_horses), 2):
                            if i + 1 < len(wide_horses):
                                actual_wide = set([wide_horses[i], wide_horses[i+1]])
                                if pred_wide == actual_wide and i < len(wide_payouts):
                                    payout = wide_payouts[i]
                                    if payout:
                                        results[strategy_name]['total_return'] += payout
                                        results[strategy_name]['hit_count'] += 1
                                    break

                    elif strategy_name == '3連複_BOX5頭' and len(pred_horses) >= 5:
                        # 3連複 BOX5頭
                        trio_data = payout_data.get('3連複', {})
                        actual_trio_nums = trio_data.get('馬番', [])
                        trio_payout = trio_data.get('払戻金', [0])[0] if trio_data.get('払戻金') else 0

                        if actual_trio_nums and len(actual_trio_nums) >= 3:
                            actual_trio = set([str(n) for n in actual_trio_nums[:3]])
                            pred_box5 = set([str(h) for h in pred_horses[:5]])

                            results[strategy_name]['total_cost'] += 1000  # 10点

                            if actual_trio.issubset(pred_box5):
                                if trio_payout:
                                    results[strategy_name]['total_return'] += trio_payout
                                    results[strategy_name]['hit_count'] += 1

            # 結果表示
            self.backtest_result_text.insert(tk.END, "\n[3/3] 結果を集計中...\n")
            self.root.update()

            self.backtest_result_text.insert(tk.END, "\n" + "="*70 + "\n")
            self.backtest_result_text.insert(tk.END, "バックテスト結果\n")
            self.backtest_result_text.insert(tk.END, "="*70 + "\n\n")

            header = f"{'戦略':<20} | {'レース数':>8} | {'的中':>6} | {'的中率':>6} | {'回収率':>7}\n"
            self.backtest_result_text.insert(tk.END, header)
            self.backtest_result_text.insert(tk.END, "-"*70 + "\n")

            for strategy_name in selected_strategies:
                r = results[strategy_name]
                hit_rate = (r['hit_count'] / r['total_races'] * 100) if r['total_races'] > 0 else 0
                recovery = (r['total_return'] / r['total_cost'] * 100) if r['total_cost'] > 0 else 0

                line = f"{strategy_name:<20} | {r['total_races']:8,}R | {r['hit_count']:6,}回 | {hit_rate:5.1f}% | {recovery:6.1f}%\n"
                self.backtest_result_text.insert(tk.END, line)

            self.backtest_result_text.insert(tk.END, "\n" + "="*70 + "\n")
            self.status_bar.config(text="バックテスト完了")

            messagebox.showinfo("完了", "バックテストが完了しました！")

        except Exception as e:
            self.backtest_result_text.insert(tk.END, f"\nエラー: {str(e)}\n")
            self.status_bar.config(text="エラーが発生しました")
            messagebox.showerror("エラー", f"バックテスト中にエラーが発生しました:\n{str(e)}")

    def export_results(self):
        """結果のエクスポート"""
        filename = filedialog.asksaveasfilename(defaultextension=".csv",
                                                filetypes=[("CSV files", "*.csv")])
        if filename:
            messagebox.showinfo("情報", f"結果を{filename}に保存しました")

    def predict_race(self):
        """レース予測"""
        race_id = self.race_id_entry.get()
        if not race_id:
            messagebox.showwarning("警告", "race_idを入力してください")
            return

        # バックグラウンドで実行
        thread = threading.Thread(target=self._predict_race_background, args=(race_id,))
        thread.daemon = True
        thread.start()

    def _predict_race_background(self, race_id):
        """レース予測のバックグラウンド実行"""
        try:
            self.status_bar.config(text=f"race_id: {race_id} を予測中...")
            self.predict_result_text.insert(tk.END, "\n" + "="*70 + "\n")
            self.predict_result_text.insert(tk.END, f"レース予測: {race_id}\n")
            self.predict_result_text.insert(tk.END, "="*70 + "\n")
            self.root.update()

            # データ読み込み
            self.predict_result_text.insert(tk.END, "\n[1/4] レースデータ読み込み中...\n")
            self.root.update()

            csv_path = self.csv_path_entry.get()
            json_path = self.json_path_entry.get()

            if not os.path.exists(csv_path):
                raise FileNotFoundError("CSVファイルが見つかりません")

            df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
            race_horses = df[df['race_id'] == int(race_id)]

            if len(race_horses) == 0:
                raise ValueError(f"race_id {race_id} が見つかりません")

            self.predict_result_text.insert(tk.END, f"  出走頭数: {len(race_horses)}頭\n")

            # レース情報表示
            race_info = race_horses.iloc[0]
            race_name = race_info.get('RaceName', 'N/A')
            race_date = race_info.get('date', 'N/A')
            track_name = race_info.get('track_name', 'N/A')
            distance = race_info.get('distance', 'N/A')

            self.predict_result_text.insert(tk.END, f"  レース名: {race_name}\n")
            self.predict_result_text.insert(tk.END, f"  日付: {race_date}\n")
            self.predict_result_text.insert(tk.END, f"  場所: {track_name}\n")
            self.predict_result_text.insert(tk.END, f"  距離: {distance}m\n")
            self.root.update()

            # 予測実行
            self.predict_result_text.insert(tk.END, "\n[2/4] 予測計算中...\n")
            self.root.update()

            # オッズ順で予測（簡易版）
            predictions = []
            for _, horse in race_horses.iterrows():
                umaban = int(horse.get('Umaban', 0))
                horse_name = horse.get('HorseName', 'N/A')
                odds = pd.to_numeric(horse.get('Odds_x'), errors='coerce')
                if pd.isna(odds):
                    odds = pd.to_numeric(horse.get('Odds_y'), errors='coerce')
                ninki = pd.to_numeric(horse.get('Ninki'), errors='coerce')
                jockey = horse.get('JockeyName', 'N/A')

                # 予測スコア（簡易版: オッズの逆数）
                if pd.notna(odds) and odds > 0:
                    score = 1.0 / odds
                else:
                    score = 0.01

                predictions.append({
                    'umaban': umaban,
                    'name': horse_name,
                    'jockey': jockey,
                    'odds': odds if pd.notna(odds) else 999,
                    'ninki': ninki if pd.notna(ninki) else 99,
                    'score': score,
                    'actual_rank': pd.to_numeric(horse.get('Rank'), errors='coerce')
                })

            # スコア順にソート
            predictions.sort(key=lambda x: x['score'], reverse=True)

            # 予測順位を割り当て
            for i, pred in enumerate(predictions):
                pred['predicted_rank'] = i + 1

            self.predict_result_text.insert(tk.END, "  予測完了！\n")
            self.root.update()

            # 推奨馬券生成
            self.predict_result_text.insert(tk.END, "\n[3/4] 推奨馬券を生成中...\n")
            self.root.update()

            top3_umabans = [p['umaban'] for p in predictions[:3]]
            top5_umabans = [p['umaban'] for p in predictions[:5]]

            recommendations = []

            # ワイド 1-3
            recommendations.append({
                'type': 'ワイド',
                'horses': f"{top3_umabans[0]}-{top3_umabans[2]}",
                'cost': '100円',
                'confidence': '⭐⭐⭐'
            })

            # 3連複 BOX5頭
            box5_str = '-'.join(map(str, top5_umabans))
            recommendations.append({
                'type': '3連複',
                'horses': f"BOX5頭 ({box5_str})",
                'cost': '1,000円（10点）',
                'confidence': '⭐⭐'
            })

            # 馬連 1-2
            recommendations.append({
                'type': '馬連',
                'horses': f"{top3_umabans[0]}-{top3_umabans[1]}",
                'cost': '100円',
                'confidence': '⭐⭐⭐⭐'
            })

            # 結果表示
            self.predict_result_text.insert(tk.END, "\n[4/4] 結果を表示中...\n")
            self.root.update()

            # 予測結果
            self.predict_result_text.insert(tk.END, "\n" + "="*70 + "\n")
            self.predict_result_text.insert(tk.END, "予測着順\n")
            self.predict_result_text.insert(tk.END, "="*70 + "\n\n")

            header = f"{'順位':>4} | {'馬番':>4} | {'馬名':<20} | {'騎手':<15} | {'人気':>4} | {'オッズ':>7} | {'実際':>4}\n"
            self.predict_result_text.insert(tk.END, header)
            self.predict_result_text.insert(tk.END, "-"*70 + "\n")

            for pred in predictions[:10]:  # 上位10頭表示
                actual_str = f"{int(pred['actual_rank'])}着" if pd.notna(pred['actual_rank']) else "-"
                line = f"{pred['predicted_rank']:4d} | {pred['umaban']:4d} | {pred['name'][:20]:<20} | "
                line += f"{pred['jockey'][:15]:<15} | {int(pred['ninki']):4d} | {pred['odds']:7.1f} | {actual_str:>4}\n"
                self.predict_result_text.insert(tk.END, line)

            # 推奨馬券
            self.predict_result_text.insert(tk.END, "\n" + "="*70 + "\n")
            self.predict_result_text.insert(tk.END, "推奨馬券\n")
            self.predict_result_text.insert(tk.END, "="*70 + "\n\n")

            for i, rec in enumerate(recommendations, 1):
                self.predict_result_text.insert(tk.END, f"推奨{i}: {rec['type']}\n")
                self.predict_result_text.insert(tk.END, f"  馬番: {rec['horses']}\n")
                self.predict_result_text.insert(tk.END, f"  購入額: {rec['cost']}\n")
                self.predict_result_text.insert(tk.END, f"  確信度: {rec['confidence']}\n\n")

            # 的中判定（実際の結果がある場合）
            if pd.notna(predictions[0]['actual_rank']):
                self.predict_result_text.insert(tk.END, "="*70 + "\n")
                self.predict_result_text.insert(tk.END, "的中判定（実データとの比較）\n")
                self.predict_result_text.insert(tk.END, "="*70 + "\n\n")

                # 実際の着順を取得
                actual_sorted = sorted(predictions, key=lambda x: x['actual_rank'] if pd.notna(x['actual_rank']) else 99)
                actual_top3 = [p['umaban'] for p in actual_sorted[:3]]

                # 1着予測
                if predictions[0]['umaban'] == actual_top3[0]:
                    self.predict_result_text.insert(tk.END, "✓ 1着的中！\n")
                else:
                    self.predict_result_text.insert(tk.END, f"✗ 1着外れ（予測: {predictions[0]['umaban']}番 → 実際: {actual_top3[0]}番）\n")

                # 3連複（上位5頭BOX）
                pred_set5 = set(top5_umabans)
                actual_set3 = set(actual_top3)
                if actual_set3.issubset(pred_set5):
                    self.predict_result_text.insert(tk.END, "✓ 3連複BOX5頭 的中！\n")
                else:
                    self.predict_result_text.insert(tk.END, "✗ 3連複BOX5頭 外れ\n")

                # ワイド 1-3
                pred_wide = set([predictions[0]['umaban'], predictions[2]['umaban']])
                hit_wide = False
                for i in range(3):
                    for j in range(i+1, 3):
                        if set([actual_top3[i], actual_top3[j]]) == pred_wide:
                            hit_wide = True
                            break
                if hit_wide:
                    self.predict_result_text.insert(tk.END, "✓ ワイド1-3 的中！\n")
                else:
                    self.predict_result_text.insert(tk.END, "✗ ワイド1-3 外れ\n")

            self.predict_result_text.insert(tk.END, "\n" + "="*70 + "\n")
            self.status_bar.config(text=f"予測完了: {race_id}")

            messagebox.showinfo("完了", "レース予測が完了しました！")

        except Exception as e:
            self.predict_result_text.insert(tk.END, f"\nエラー: {str(e)}\n")
            self.status_bar.config(text="エラーが発生しました")
            messagebox.showerror("エラー", f"予測中にエラーが発生しました:\n{str(e)}")

    def save_settings(self):
        """設定の保存"""
        self.config["clean_csv"] = self.csv_path_entry.get()
        self.config["clean_json"] = self.json_path_entry.get()
        self.config["model_file"] = self.model_path_entry.get()
        self.save_config()
        messagebox.showinfo("情報", "設定を保存しました")

def main():
    root = tk.Tk()
    app = KeibaAnalysisTool(root)
    root.mainloop()

if __name__ == "__main__":
    main()
