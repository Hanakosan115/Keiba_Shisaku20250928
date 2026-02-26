# アーカイブファイルカタログ

作成日: 2026-01-07

## 📁 アクティブファイル（メイン）

### GUI・システム
- **keiba_prediction_gui_v3.py** - メイン予測GUI（Phase 9モデル、Win5対応）
- **smart_update_system.py** - スマートデータ更新システム（3層アプローチ）

### データ収集
- **collect_latest_2025.py** - 最新データ収集スクリプト
- **scrape_horse_selenium.py** - Selenium版馬データスクレイパー

---

## 📦 archive/data_processing/ (データ加工系)

### ラップタイム追加
- **add_lap_times_2024_2025.py** - 2024-2025年のラップタイム追加
- **add_lap_times_improved.py** - 改善版ラップタイム追加
- **add_lap_and_training_data.py** - ラップ＋調教データ追加
- **add_lap_and_training_full.py** - フル版ラップ＋調教

### 調教データ追加
- **add_training_2020_2023.py** - 2020-2023年調教データ追加
- **add_pace_indicators.py** - ペース指標追加

### データ統合
- **merge_2024_2025.py** - 2024-2025年データ統合
- **merge_all_data_2020_2025.py** - 全期間データ統合

### 配当データ
- **collect_payouts_2024_2025.py** - 配当データ収集

**機能**: データベースへの特徴量追加、データ統合

---

## 📊 archive/analysis/ (分析系)

### ROI分析
- **analyze_roi_from_predictions.py** - 予測からのROI分析
- **roi_analysis_fast.py** - 高速ROI分析
- **roi_simulation.py** - ROIシミュレーション

### その他分析
- **analyze_payout_format.py** - 配当フォーマット分析
- **calculate_track_bias.py** - コースバイアス計算
- **calculate_trainer_jockey_stats.py** - 調教師・騎手統計

**機能**: 的中率・ROI分析、統計計算

---

## 🧪 archive/backtesting/ (バックテスト・訓練系)

### バックテスト
- **backtest_phase2_phase3.py** - Phase 2/3バックテスト
- **backtest_phase2_phase3_dynamic.py** - 動的バックテスト
- **backtest_phase9.py** - Phase 9バックテスト

### モデル訓練
- **train_dual_models.py** - デュアルモデル訓練
- **train_phase9_model.py** - Phase 9モデル訓練

**機能**: モデル評価、モデル訓練

---

## 🔍 archive/debugging/ (デバッグ・チェック系)

### データチェック
- **check_available_data.py** - 利用可能データチェック
- **check_column_data.py** - カラムデータチェック
- **check_data_status.py** - データ状態チェック
- **check_data_years.py** - 年度別データチェック
- **check_2025_months.py** - 2025年月別チェック
- **check_date_format.py** - 日付フォーマットチェック
- **check_horse_records.py** - 馬記録チェック
- **check_odds_data.py** - オッズデータチェック
- **check_pedigree_data.py** - 血統データチェック
- **check_phase9_columns.py** - Phase 9カラムチェック
- **check_processed_races.py** - 処理済みレースチェック
- **check_training_columns.py** - 調教カラムチェック
- **check_years.py** - 年度チェック

### スクレイピングデバッグ
- **debug_horse_page.py** - 馬ページデバッグ
- **debug_lap_scraping.py** - ラップスクレイピングデバッグ
- **debug_payout.py** - 配当デバッグ
- **debug_race_horses.py** - レース馬デバッグ
- **debug_shutuba.py** - 出馬表デバッグ
- **debug_training_rank.py** - 調教ランクデバッグ

### 個別レーステスト
- **check_race.py** - レースチェック
- **check_race_202509050511.py** - 特定レースチェック
- **check_race_result.py** - レース結果チェック
- **test_race_202506050611.py** - 特定レーステスト

### 機能テスト
- **test_arima_kinen.py** - 有馬記念テスト
- **test_csv_fix_100races.py** - CSV修正テスト
- **test_date_comparison.py** - 日付比較テスト
- **test_encoding_fix.py** - エンコーディング修正テスト
- **test_feature_calculation.py** - 特徴量計算テスト
- **test_function_direct.py** - 関数直接テスト
- **test_future_race.py** - 未来レーステスト
- **test_gui_prediction.py** - GUI予測テスト
- **test_gui_prediction_logic.py** - GUI予測ロジックテスト
- **test_lap_parsing.py** - ラップ解析テスト
- **test_oikiri_page.py** - 追切ページテスト
- **test_smart_update_integration.py** - スマート更新統合テスト
- **test_status_code.py** - ステータスコードテスト
- **test_training_data.py** - 調教データテスト
- **test_training_scrape.py** - 調教スクレイピングテスト
- **verify_test_data.py** - テストデータ検証

### その他
- **check_advanced_features.py** - 高度機能チェック
- **check_dec21.py** - 12/21チェック
- **check_gui_datafile.py** - GUIデータファイルチェック
- **check_phase2a_data.py** - Phase 2Aデータチェック
- **check_progress.py** - 進捗チェック
- **check_training_2020_2023_progress.py** - 調教データ進捗チェック

**機能**: データ検証、デバッグ、動作確認

---

## 🌐 archive/scraping/ (スクレイピング補助)

- **scrape_result_page.py** - 結果ページスクレイピング
- **scrape_shutuba.py** - 出馬表スクレイピング
- **scrape_pedigree.py** - 血統スクレイピング
- **scrape_horse_latest.py** - 馬最新データスクレイピング
- **save_shutuba_html.py** - 出馬表HTML保存
- **extract_oikiri_data.py** - 追切データ抽出

**機能**: 各種ページスクレイピング、データ抽出

---

## 🖥️ archive/old_gui/ (旧GUI)

- **keiba_gui.py** - 初期版GUI
- **keiba_prediction_gui.py** - v1 GUI
- **keiba_prediction_gui_v2.py** - v2 GUI (Phase 2-8対応)
- **keiba_tool.py** - ツール版
- **keiba_tool_demo.py** - デモ版

**機能**: 旧バージョンのGUI（Phase 9以前）

---

## 🛠️ archive/utilities/ (ユーティリティ)

### 予測関連
- **predict_future_race.py** - 未来レース予測
- **predict_race.py** - レース予測

### クイック実行
- **quick_demo.py** - クイックデモ
- **quick_test.py** - クイックテスト

### データ取得
- **get_valid_race_ids.py** - 有効race_ID取得
- **list_sep5_races.py** - 9月5日レース一覧
- **show_available_races.py** - 利用可能レース表示

### メンテナンス
- **organize_files.py** - ファイル整理
- **cleanup_remaining.py** - 残存クリーンアップ
- **compare_parsing_logic.py** - 解析ロジック比較
- **run_full_scraping_fixed.py** - フルスクレイピング実行

**機能**: 各種ユーティリティスクリプト

---

## 🎯 主要機能まとめ

| カテゴリ | 主な用途 | 代表ファイル |
|---------|---------|-------------|
| データ加工 | 特徴量追加・統合 | add_lap_times_improved.py |
| 分析 | ROI・統計分析 | roi_analysis_fast.py |
| バックテスト | モデル評価・訓練 | backtest_phase9.py |
| デバッグ | データ検証・動作確認 | check_*.py, test_*.py |
| スクレイピング | データ収集 | scrape_*.py |
| GUI | インターフェース | keiba_prediction_gui_v*.py |

---

## ℹ️ 使用方法

必要に応じてarchiveフォルダから取り出して使用してください。
例：
```bash
# ROI分析を実行したい場合
py archive/analysis/roi_analysis_fast.py

# 特定レースをデバッグしたい場合
py archive/debugging/debug_shutuba.py
```

---

**注意**: アクティブファイル以外は過去の開発版・テスト版です。
現行システムは `keiba_prediction_gui_v3.py` を使用してください。
