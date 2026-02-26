# プロジェクト ディレクトリ構造

**更新日**: 2026年2月21日
**Phase**: 13

---

## 📁 ディレクトリ構造

```
C:\Users\bu158\Keiba_Shisaku20250928\
│
├── docs/                          # ドキュメント（MDファイル）
│   ├── PHASE13_COMPLETE_SUMMARY.md
│   ├── PHASE13_ABCD_FINAL_REPORT.md
│   ├── PHASE13_LIMITATIONS_AND_RESTRICTIONS.md
│   ├── PHASE13_D_IMPLEMENTATION_PLAN.md
│   ├── PROJECT_HISTORY_PHASE1_TO_13.md
│   ├── DIRECTORY_STRUCTURE.md（このファイル）
│   └── （その他のMDファイル）
│
├── data/                          # データファイル
│   ├── race_data/                # レースデータ
│   ├── horse_data/               # 馬データ
│   └── payout_data/              # 払戻データ
│
├── archive/                       # アーカイブ（古いファイル）
│   ├── check_scripts/            # check_*.py
│   ├── debug_scripts/            # debug_*.py, test_*.py
│   ├── phase_old_backtests/      # Phase 10-12のバックテスト
│   └── old_scripts/              # 古い分析スクリプト
│
├── scripts/                       # ユーティリティスクリプト
│
├── __pycache__/                   # Pythonキャッシュ
│
└── （メインファイル）
```

---

## 📄 主要ファイル

### 実運用システム

#### GUIアプリケーション
- **keiba_prediction_gui_v3.py** (約4000行)
  - メインGUI
  - Phase 13対応
  - 15-20%確率帯機能実装済み

#### データ収集
- **scrape_shutuba.py**
  - 出馬表スクレイピング
- **scrape_result_page.py**
  - 結果ページスクレイピング
- **scrape_horse_selenium.py**
  - 馬詳細データ取得
- **scrape_odds.py**
  - オッズデータ取得

#### データ更新
- **smart_update_system.py**
  - 自動データ更新システム
- **auto_update_smart.py**
  - スマート更新

---

### Phase 13 関連ファイル

#### モデル・Calibration
- **phase13_model_win.pkl**
  - Phase 13単勝予測モデル
- **phase13_calibrators.pkl**
  - Calibratorファイル
- **phase13_feature_list.pkl**
  - 特徴量リスト

#### 訓練・テストデータ
- **phase13_train_2020_2022.csv**
  - 訓練データ（2020-2022年）
- **phase13_test_2024.csv**
  - テストデータ（2024年）
- **phase13_test_features.csv**
  - テスト特徴量

#### バックテスト結果
- **phase13_full_period_ALL_RACES_results.csv**
  - 全期間バックテスト結果（21,111レース）
- **phase13_full_period_backtest_results.csv**
  - サンプルバックテスト結果
- **phase13_exotic_bets_theoretical_results.csv**
  - 複勝・ワイド・馬連結果
- **phase13_win5_results.csv**
  - WIN5検証結果

#### スクリプト
- **phase13_feature_engineering.py**
  - 特徴量エンジニアリング
- **phase13_full_period_backtest.py**
  - 全期間バックテスト
- **phase13_full_period_ALL_RACES.py**
  - 全レースバックテスト
- **phase13_exotic_bets_theoretical.py**
  - 複勝・ワイド・馬連検証
- **phase13_win5_system.py**
  - WIN5予測システム

---

### データベース

#### メインデータベース
- **netkeiba_data_2020_2024_enhanced.csv** (約800MB)
  - メインデータベース
  - 2020-2026年2月のレースデータ
  - 289,336レース

#### バックアップ
- **netkeiba_data_2020_2024_enhanced_backup_YYYYMMDD_HHMMSS.csv**
  - 定期バックアップ

---

### 設定ファイル

- **data_config.py**
  - データ設定
- **settings.json**
  - GUI設定

---

## 🗂️ データフォルダ構成

### data/race_data/
レースデータを保存
- race_YYYYMMDD_RACEID.csv
- race_calendar_YYYYMM.json

### data/horse_data/
馬の詳細データを保存
- horse_HORSEID.csv
- horse_pedigree_HORSEID.json

### data/payout_data/
払戻データを保存（Phase 14で実装予定）
- payout_RACEID.json
- payout_cache.pkl

---

## 📦 アーカイブフォルダ

### archive/check_scripts/
一時的な確認スクリプト（約50個）
- check_*.py

### archive/debug_scripts/
デバッグ・テストスクリプト（約30個）
- debug_*.py
- test_*.py

### archive/phase_old_backtests/
Phase 10-12のバックテストスクリプト
- backtest_phase10.py
- backtest_phase11.py
- backtest_phase12.py

### archive/old_scripts/
Phase 13以前の分析スクリプト
- analyze_*.py
- compare_*.py
- verify_*.py

---

## 🚫 削除推奨ファイル

以下のファイルは削除しても問題ありません:

### 古いモデルファイル（Phase 12以前）
```
model_phase10_*.pkl
model_phase11_*.pkl
model_phase12_*.pkl
model_win_prediction.pkl
model_top3_prediction.pkl
```

### 古いキャッシュ
```
model_stats_cache.pkl
payout_cache.pkl（Phase 14で再構築）
```

### 一時ファイル
```
nul
col_info.txt
col_info2.txt
column_names.txt
```

### 重複バックアップ
古いバックアップファイル（最新5個のみ保持推奨）

---

## 📝 ファイル命名規則

### Phase 13関連
```
phase13_*.py          # Phase 13スクリプト
phase13_*.pkl         # Phase 13モデル
phase13_*.csv         # Phase 13データ
```

### スクレイピング
```
scrape_*.py           # スクレイピングスクリプト
```

### バックテスト
```
backtest_*.py         # バックテストスクリプト
backtest_*.csv        # バックテスト結果
```

### 分析
```
analyze_*.py          # 分析スクリプト
```

---

## 🔧 メンテナンス

### 定期的に実施すべきこと

#### 1. バックアップの整理（月次）
```bash
# 古いバックアップを削除（最新5個のみ保持）
cd C:\Users\bu158\Keiba_Shisaku20250928
ls -t netkeiba_data_*_backup_*.csv | tail -n +6 | xargs rm
```

#### 2. __pycache__のクリア（週次）
```bash
find . -type d -name "__pycache__" -exec rm -rf {} +
```

#### 3. アーカイブの圧縮（四半期）
```bash
# archiveフォルダを圧縮
tar -czf archive_backup_$(date +%Y%m%d).tar.gz archive/
```

---

## 🎯 推奨ディレクトリ使用法

### 新しいスクリプトを作成する際

1. **一時的な確認スクリプト**: `archive/check_scripts/`に直接作成
2. **Phase 14のスクリプト**: ルートに `phase14_*.py` として作成
3. **ドキュメント**: `docs/` に `.md` ファイルとして作成
4. **データファイル**: `data/` の適切なサブフォルダに保存

---

## 📊 ディスク使用量（推定）

```
netkeiba_data_2020_2024_enhanced.csv: 800MB
バックアップファイル（5個）: 4GB
phase13_*.csv: 200MB
archive/: 500MB
その他: 500MB
---
合計: 約6GB
```

---

**最終更新**: 2026年2月21日
**メンテナンス担当**: Claude Opus 4.6
