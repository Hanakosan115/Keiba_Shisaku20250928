# 競馬データ分析ガイド

## 概要
2024年データ収集完了後に使用する分析ツール一式です。

## ツール一覧

### 1. 統合分析スイート（推奨）
**ファイル**: `analysis_suite.py`

すべての分析ツールを一箇所から実行できる統合メニュー。

```bash
py analysis_suite.py
```

**機能**:
- データ品質レポート生成
- EDAダッシュボード起動
- ベースラインモデル学習
- 全自動分析（ワンクリックで全実行）
- 進捗モニター
- 新旧データベース比較

---

### 2. データ品質レポート
**ファイル**: `data_quality_report.py`

データ収集完了後、最初に実行すべきスクリプト。

```bash
py data_quality_report.py
```

**出力内容**:
- 基本統計（レース数、出走数、年別内訳）
- 欠損値チェック（重要カラムの欠損率）
- 統計カバー率（馬統計データの完全性）
- データ整合性チェック（平均出走頭数など）
- 異常値チェック（極端なオッズなど）
- 重複チェック
- 総合評価（EXCELLENT / GOOD / NEEDS ATTENTION）

**使用タイミング**:
- データ収集完了直後
- 追加収集後の確認
- モデル学習前の品質確認

---

### 3. EDAダッシュボード
**ファイル**: `eda_dashboard.py`

インタラクティブなデータ探索ダッシュボード（Streamlit）。

```bash
py -m streamlit run eda_dashboard.py
```

**主要機能**:

#### タブ1: データ概要
- 総レース数、出走数、統計カバー率
- 年別統計テーブル
- 年別レース数推移グラフ

#### タブ2: 勝率分析
- 人気別勝率・複勝率グラフ
- 馬場状態別勝率
- コース種別別勝率

#### タブ3: オッズ分析
- オッズ分布ヒストグラム
- オッズ帯別勝率
- オッズ統計（平均、中央値、最大）

#### タブ4: 距離・コース分析
- 距離帯別勝率（短距離、マイル、中距離、長距離）
- コース種別統計
- 距離別出走数

#### タブ5: 騎手・調教師分析
- 騎手別勝率TOP20
- 調教師別勝率TOP20
- 騎乗数・管理頭数

#### タブ6: 時系列分析
- 月別レース数推移
- 月別平均オッズ推移

**フィルター機能**:
- 年選択（複数選択可）
- コース種別選択
- 馬場状態選択

---

### 4. ベースラインモデル
**ファイル**: `baseline_model.py`

3つの機械学習モデルでベンチマークを構築。

```bash
py baseline_model.py
```

**処理内容**:

1. **データ分割**
   - トレーニング: 2024年以前
   - テスト: 2024年

2. **特徴量**
   - 基本情報（人気、オッズ、馬体重）
   - レース情報（距離）
   - 馬統計（出走数、勝率、獲得賞金）
   - 前走情報（着順、距離、間隔）
   - 走法・位置取り
   - 血統情報

3. **モデル**
   - Logistic Regression
   - Random Forest
   - LightGBM

4. **評価指標**
   - Accuracy（正解率）
   - Precision（適合率）
   - Recall（再現率）
   - F1-score
   - ROC-AUC

5. **実戦シミュレーション**
   - レースごとの予測
   - 的中率計算
   - 投資シミュレーション（ROI計算）

6. **特徴量重要度**
   - LightGBMベースの重要度TOP15

**出力例**:
```
Best model: LightGBM (ROC-AUC: 0.7234)
Race accuracy: 28.45%
Investment ROI: -12.34%
```

---

## 使用フロー

### 推奨ワークフロー

```
1. データ収集完了
   ↓
2. 統合分析スイート起動
   py analysis_suite.py
   ↓
3. オプション「1」でデータ品質レポート生成
   → データ品質を確認（GOOD以上を確認）
   ↓
4. オプション「2」でEDAダッシュボード起動
   → データを深く理解
   → 有効な特徴量を発見
   ↓
5. オプション「3」でベースラインモデル学習
   → ベンチマークを確立
   → 特徴量重要度を確認
   ↓
6. 改善サイクル
   - 新しい特徴量を追加
   - ハイパーパラメータチューニング
   - アンサンブルモデル構築
```

### クイックスタート（全自動）

統合スイートの「オプション4」で一気に実行:

```bash
py analysis_suite.py
# メニューで「4」を選択
# データ品質レポート → ベースラインモデル を自動実行
```

---

## 補助ツール

### 進捗モニター
**ファイル**: `monitor_progress.py`

データ収集中の進捗を確認。

```bash
py monitor_progress.py
```

**出力**:
- データベース状態（総行数、レース数）
- 統計カバー率
- 進捗率（対象/完了）
- 推定残り時間

### 新旧データベース比較
**ファイル**: `compare_old_new_db.py`

修正前後のデータベース品質を比較。

```bash
py compare_old_new_db.py
```

**出力**:
- 平均出走頭数の比較
- 統計カバー率の改善度

---

## トラブルシューティング

### エラー: `FileNotFoundError: netkeiba_data_2020_2024_enhanced.csv`
→ データ収集が完了していません。先に `collect_2024_full.py` を実行してください。

### エラー: `ModuleNotFoundError: No module named 'streamlit'`
→ Streamlitをインストール:
```bash
pip install streamlit
```

### エラー: `ModuleNotFoundError: No module named 'lightgbm'`
→ LightGBMをインストール:
```bash
pip install lightgbm
```

### ダッシュボードが開かない
→ 手動でブラウザを開いて `http://localhost:8501` にアクセス

---

## 次のステップ

ベースラインモデル構築後の改善案:

1. **特徴量エンジニアリング**
   - 騎手・調教師の統計データ追加
   - レース間隔の非線形変換
   - オッズと人気の交互作用項

2. **ハイパーパラメータチューニング**
   - GridSearchCV / RandomizedSearchCV
   - Optuna使用

3. **アンサンブルモデル**
   - Stacking（LightGBM + XGBoost + CatBoost）
   - Voting Classifier

4. **ディープラーニング**
   - LSTM（時系列データ活用）
   - Transformer

5. **実戦投資戦略**
   - Kelly Criterion（最適賭け金計算）
   - リスク管理
   - ポートフォリオ最適化

---

## ファイル構成

```
Keiba_Shisaku20250928/
├── analysis_suite.py           # 統合分析スイート（メイン）
├── data_quality_report.py      # データ品質レポート
├── eda_dashboard.py            # EDAダッシュボード
├── baseline_model.py           # ベースラインモデル
├── monitor_progress.py         # 進捗モニター
├── compare_old_new_db.py       # 新旧DB比較
├── ANALYSIS_GUIDE.md           # このファイル
└── netkeiba_data_2020_2024_enhanced.csv  # データベース（収集後生成）
```

---

**最終更新**: 2025-12-18
**作成者**: Claude Code
