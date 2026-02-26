"""
競馬予想ツール - Value Betting対応版
既存のkeiba_yosou_tool.pyにValue Betting機能を追加

使い方:
    python keiba_yosou_tool_value_betting.py
"""
import sys
import os

# 既存のツールをインポート
from keiba_yosou_tool import *

# Value Bettingモジュールをインポート
from value_betting_module import ValueBettingAnalyzer

class KeibaYosouToolWithValue(KeibaYosouTool):
    """Value Betting機能を追加したツール"""

    def __init__(self, root):
        super().__init__(root)
        # Value Betting Analyzer初期化
        self.value_analyzer = ValueBettingAnalyzer(value_threshold=0.05)
        self.root.title("競馬予想ツール - Value Betting対応版")

    def setup_ui(self):
        """UI構築（親クラスのメソッドをオーバーライド）"""
        super().setup_ui()

        # Value Betting専用エリアを追加
        self._add_value_betting_section()

    def _add_value_betting_section(self):
        """Value Bettingセクションを追加"""
        # 既存のUI要素を探す
        main_frame = self.root.nametowidget('!frame')

        # Value Bettingフレームを追加
        value_frame = ttk.LabelFrame(main_frame, text="Value Betting推奨", padding="10")
        value_frame.grid(row=3, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))

        # Value閾値設定
        threshold_frame = ttk.Frame(value_frame)
        threshold_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(threshold_frame, text="Value閾値:").pack(side=tk.LEFT, padx=(0, 5))

        self.threshold_var = tk.DoubleVar(value=5.0)
        threshold_spinbox = ttk.Spinbox(
            threshold_frame,
            from_=0,
            to=20,
            increment=1,
            textvariable=self.threshold_var,
            width=10
        )
        threshold_spinbox.pack(side=tk.LEFT)
        ttk.Label(threshold_frame, text="%").pack(side=tk.LEFT, padx=(2, 10))

        # 予算設定
        ttk.Label(threshold_frame, text="予算:").pack(side=tk.LEFT, padx=(20, 5))
        self.budget_var = tk.IntVar(value=10000)
        budget_entry = ttk.Entry(threshold_frame, textvariable=self.budget_var, width=10)
        budget_entry.pack(side=tk.LEFT)
        ttk.Label(threshold_frame, text="円").pack(side=tk.LEFT, padx=(2, 0))

        # Value推奨表示エリア
        self.value_text = scrolledtext.ScrolledText(
            value_frame,
            height=15,
            width=80,
            font=('Courier New', 10)
        )
        self.value_text.pack(fill=tk.BOTH, expand=True)

    def _display_recommended_bets(self, predictions, race_id):
        """
        推奨馬券を表示（オーバーライド）
        Value Betting情報も追加
        """
        # 親クラスのメソッドを呼び出し
        super()._display_recommended_bets(predictions, race_id)

        # Value Betting推奨を生成
        self._generate_value_recommendations(predictions)

    def _generate_value_recommendations(self, predictions):
        """Value Betting推奨を生成して表示"""
        try:
            # Value閾値を取得
            threshold = self.threshold_var.get() / 100.0
            self.value_analyzer.value_threshold = threshold

            # 予算を取得
            budget = self.budget_var.get()

            # 馬データを準備
            horses_data = []
            predicted_ranks = []
            odds_list = []

            for pred in predictions:
                # スコアから予測順位を計算（スコアが高いほど順位が良い）
                horses_data.append({
                    'umaban': pred['umaban'],
                    'odds': pred['odds'],
                    'score': pred['score']
                })
                odds_list.append(pred['odds'])

            # スコアから順位を計算（降順でランク付け）
            scores = [h['score'] for h in horses_data]
            sorted_indices = np.argsort(scores)[::-1]
            ranks = np.empty(len(scores))
            ranks[sorted_indices] = np.arange(1, len(scores) + 1)

            for i, h in enumerate(horses_data):
                h['predicted_rank'] = ranks[i]

            # Value値を計算
            values = self.value_analyzer.calculate_values(ranks, odds_list)

            # Value情報を追加
            for i, h in enumerate(horses_data):
                h.update(values[i])

            # 推奨ベットを生成
            recommendations = self.value_analyzer.recommend_bets(horses_data, budget=budget)

            # フォーマットして表示
            formatted_text = self.value_analyzer.format_recommendation(recommendations)

            # テキストエリアに表示
            self.value_text.delete('1.0', tk.END)
            self.value_text.insert('1.0', formatted_text)

            # Value上位馬を強調表示
            value_horses = self.value_analyzer.get_value_bets(horses_data)
            if len(value_horses) > 0:
                best_value_horse = max(value_horses, key=lambda x: x['value'])
                highlight_text = f"\n\n★ 最高Value: {best_value_horse['umaban']}番 (+{best_value_horse['value']*100:.2f}%)"
                self.value_text.insert(tk.END, highlight_text)

        except Exception as e:
            error_msg = f"Value推奨生成エラー:\n{str(e)}"
            self.value_text.delete('1.0', tk.END)
            self.value_text.insert('1.0', error_msg)


def main():
    """メイン関数"""
    root = tk.Tk()
    app = KeibaYosouToolWithValue(root)
    root.mainloop()


if __name__ == "__main__":
    main()
