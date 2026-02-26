"""
競馬予想システム - GUIツール
ダブルクリックで起動できるグラフィカルインターフェース
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import sys
import os
from io import StringIO

# 修正版のインポート
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from predict_by_race_id import DirectRacePredictor

class KeibaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("競馬予想システム - Value Betting Analyzer")
        self.root.geometry("900x700")

        # 予想エンジン
        self.predictor = DirectRacePredictor()

        # メインフレーム
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # タイトル
        title_label = ttk.Label(main_frame, text="🏇 競馬予想システム",
                               font=('Arial', 20, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=10)

        # 説明
        desc_label = ttk.Label(main_frame,
                              text="NetkeibaでレースIDをコピーして予想を実行",
                              font=('Arial', 10))
        desc_label.grid(row=1, column=0, columnspan=3, pady=5)

        # レースID入力
        ttk.Label(main_frame, text="レースID (12桁):",
                 font=('Arial', 11, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=10)

        self.race_id_entry = ttk.Entry(main_frame, width=30, font=('Arial', 12))
        self.race_id_entry.grid(row=2, column=1, sticky=tk.W, pady=10, padx=5)

        ttk.Label(main_frame, text="例: 202412070811",
                 font=('Arial', 9), foreground='gray').grid(row=2, column=2, sticky=tk.W)

        # 予算入力
        ttk.Label(main_frame, text="予算 (円):",
                 font=('Arial', 11, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=10)

        self.budget_entry = ttk.Entry(main_frame, width=30, font=('Arial', 12))
        self.budget_entry.insert(0, "10000")
        self.budget_entry.grid(row=3, column=1, sticky=tk.W, pady=10, padx=5)

        ttk.Label(main_frame, text="デフォルト: 10000円",
                 font=('Arial', 9), foreground='gray').grid(row=3, column=2, sticky=tk.W)

        # ボタンフレーム
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=20)

        # 予想実行ボタン
        self.predict_btn = ttk.Button(button_frame, text="🎯 予想実行",
                                     command=self.run_prediction,
                                     width=20)
        self.predict_btn.grid(row=0, column=0, padx=10)

        # クリアボタン
        clear_btn = ttk.Button(button_frame, text="🗑 クリア",
                              command=self.clear_results,
                              width=15)
        clear_btn.grid(row=0, column=1, padx=10)

        # ヘルプボタン
        help_btn = ttk.Button(button_frame, text="❓ 使い方",
                             command=self.show_help,
                             width=15)
        help_btn.grid(row=0, column=2, padx=10)

        # 結果表示エリア
        ttk.Label(main_frame, text="予想結果:",
                 font=('Arial', 11, 'bold')).grid(row=5, column=0, sticky=tk.W, pady=5)

        self.result_text = scrolledtext.ScrolledText(main_frame,
                                                     width=100,
                                                     height=25,
                                                     font=('Courier', 10))
        self.result_text.grid(row=6, column=0, columnspan=3, pady=10)

        # ステータスバー
        self.status_label = ttk.Label(main_frame, text="準備完了",
                                     relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)

        # 初期メッセージ
        self.show_initial_message()

    def show_initial_message(self):
        """初期メッセージを表示"""
        message = """
================================================================================
競馬予想システム - Value Betting Analyzer
================================================================================

【使い方】

1. Netkeiba でレースを探す
   https://race.netkeiba.com/

2. 予想したいレースのURLから「race_id」をコピー
   例: https://race.netkeiba.com/race/shutuba.html?race_id=202412070811
       → 202412070811 をコピー

3. 上の「レースID」欄に貼り付け

4. 予算を入力（デフォルト: 10000円）

5. 「予想実行」ボタンをクリック

6. 予想結果とValue Betting推奨が表示されます


【Valueの見方】
  +15%以上: 非常に良い！強く推奨
  +10~15%:  良い！推奨
  +5~10%:   まあまあ良い
  +0~5%:    わずかにプラス
  マイナス: 避けるべき


【推奨ベット】
  長期的に利益が出るように最適化された賭け方が表示されます。
  Kellyルールで資金配分を計算しています。


準備ができたら「予想実行」ボタンを押してください！

================================================================================
        """
        self.result_text.insert(tk.END, message)

    def clear_results(self):
        """結果をクリア"""
        self.result_text.delete(1.0, tk.END)
        self.show_initial_message()
        self.status_label.config(text="クリアしました")

    def show_help(self):
        """ヘルプを表示"""
        help_text = """
【レースIDの取得方法】

1. ブラウザで https://race.netkeiba.com/ を開く

2. カレンダーから今週末（土曜・日曜）をクリック

3. 予想したいレースをクリック

4. ブラウザのURLバーを見る:
   https://race.netkeiba.com/race/shutuba.html?race_id=202412070811
                                                    ^^^^^^^^^^^^
                                              この12桁をコピー

5. このツールの「レースID」欄に貼り付け


【競馬場コード】
  05: 東京   06: 中山   07: 中京
  08: 京都   09: 阪神   10: 福島
  01: 札幌   02: 函館


【Value Bettingとは】
  オッズと予想確率の差（ズレ）を見つけて、
  期待値がプラスの馬だけに賭ける戦略です。

  短期的には負けることもありますが、
  長期的には利益が出ることが数学的に保証されています。


【注意事項】
  - 出馬表は通常レース当日の朝9時頃公開されます
  - オッズは変動するので、レース直前に実行推奨
  - 余裕資金の範囲内で楽しんでください
  - 投資判断は自己責任でお願いします
        """
        messagebox.showinfo("使い方ヘルプ", help_text)

    def run_prediction(self):
        """予想を実行"""
        # 入力チェック
        race_id = self.race_id_entry.get().strip()
        budget_str = self.budget_entry.get().strip()

        if not race_id:
            messagebox.showerror("エラー", "レースIDを入力してください")
            return

        if len(race_id) != 12 or not race_id.isdigit():
            messagebox.showerror("エラー", "レースIDは12桁の数字である必要があります")
            return

        try:
            budget = int(budget_str)
            if budget <= 0:
                raise ValueError
        except:
            messagebox.showerror("エラー", "予算は正の整数で入力してください")
            return

        # ボタン無効化
        self.predict_btn.config(state='disabled')
        self.status_label.config(text="予想実行中... しばらくお待ちください")

        # 結果クリア
        self.result_text.delete(1.0, tk.END)

        # 別スレッドで実行
        thread = threading.Thread(target=self._execute_prediction,
                                 args=(race_id, budget))
        thread.daemon = True
        thread.start()

    def _execute_prediction(self, race_id, budget):
        """実際の予想処理（別スレッド）"""
        try:
            # 標準出力をキャプチャ
            old_stdout = sys.stdout
            sys.stdout = StringIO()

            # 予想実行
            result = self.predictor.predict_race(race_id, budget=budget)

            # 標準出力を取得
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            # 結果表示
            if result:
                self.root.after(0, self._display_result, output, "予想完了！")
            else:
                self.root.after(0, self._display_error, output)

        except Exception as e:
            sys.stdout = old_stdout
            self.root.after(0, self._display_error, f"エラーが発生しました:\n{str(e)}")

        finally:
            # ボタン再有効化
            self.root.after(0, lambda: self.predict_btn.config(state='normal'))

    def _display_result(self, output, status):
        """結果を表示"""
        self.result_text.insert(tk.END, output)
        self.status_label.config(text=status)
        self.result_text.see(tk.END)

    def _display_error(self, error_msg):
        """エラーを表示"""
        self.result_text.insert(tk.END, "\n" + "="*80 + "\n")
        self.result_text.insert(tk.END, "エラー\n")
        self.result_text.insert(tk.END, "="*80 + "\n\n")
        self.result_text.insert(tk.END, error_msg)
        self.result_text.insert(tk.END, "\n\n考えられる原因:\n")
        self.result_text.insert(tk.END, "  1. レースIDが間違っている\n")
        self.result_text.insert(tk.END, "  2. まだ出馬表が公開されていない\n")
        self.result_text.insert(tk.END, "  3. 既にレースが終了している\n")
        self.result_text.insert(tk.END, "\n出馬表は通常、レース当日の朝9時頃に公開されます。\n")
        self.status_label.config(text="エラーが発生しました")

def main():
    root = tk.Tk()
    app = KeibaGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
