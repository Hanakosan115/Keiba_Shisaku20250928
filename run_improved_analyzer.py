"""
改善版競馬分析ツール - 起動スクリプト

既存のhorse_racing_analyzer.pyを読み込み、改善版のロジックを適用して起動します
"""
import sys
import os
import tkinter as tk

# 既存のアプリケーションをインポート
from horse_racing_analyzer import HorseRacingAnalyzerApp, main

# 改善版の統合モジュールをインポート
from prediction_integration import (
    integrate_enhanced_methods,
    enhanced_fetch_race_info_thread,
    _update_enhanced_prediction_table,
    _create_enhanced_recommendation_text
)


def run_improved_app():
    """
    改善版アプリケーションの起動
    """
    print("=" * 60)
    print("競馬分析ツール - 改善版")
    print("=" * 60)
    print()
    print("【主な改善点】")
    print("1. 特徴量を50個以上→15個程度に削減（過学習防止）")
    print("2. オッズを基準とした乖離度分析")
    print("3. ◎○▲△印と自信度S/A/B/Cの自動付与")
    print("4. 前走との条件比較による穴馬検出")
    print("5. 過大評価馬の警告機能")
    print()
    print("=" * 60)
    print()

    root = tk.Tk()
    app = HorseRacingAnalyzerApp(root)

    # 改善版メソッドを既存アプリに統合
    print("改善版ロジックを適用中...")
    integrate_enhanced_methods(app)

    # ★重要★ クラスレベルで既存メソッドを置き換え
    # これにより、すべてのインスタンスで改善版メソッドが使われる

    # _fetch_race_info_thread を改善版に置き換え
    HorseRacingAnalyzerApp._fetch_race_info_thread = enhanced_fetch_race_info_thread

    # テーブル更新メソッドも改善版に置き換え
    app._update_prediction_table = app._update_enhanced_prediction_table

    # 推奨テキスト生成メソッドも改善版に置き換え
    app.create_recommendation_text = app._create_enhanced_recommendation_text

    print("既存の予測メソッドを改善版に置き換えました")

    print("改善版ロジックの適用完了！")
    print()
    print("【使い方】")
    print("1. 「予測」タブを開く")
    print("2. レースIDを入力（例: 202406010101）")
    print("3. 「レース情報表示」ボタンをクリック")
    print("4. 予測結果に「印」「自信度」「乖離度」が表示されます")
    print()
    print("起動しています...")
    print()

    root.mainloop()


if __name__ == "__main__":
    try:
        run_improved_app()
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        input("Enterキーを押して終了...")
