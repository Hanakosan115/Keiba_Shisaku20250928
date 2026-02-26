# 48時間自動実行チェックリスト

**開始予定**: ユーザー承認後
**完了予定**: 48時間後
**目標**: 18-32時間分の作業を自動実行

---

## 📋 実行順序（優先度順）

### 🔴 Phase 1: 基盤整備（必須、5-7時間）

- [ ] **Task 1.1**: GUI/バックテスト共通化実装（2-3時間）
  - [ ] `predict_core()`メソッド追加
  - [ ] `get_recommended_bet_targets()`追加
  - [ ] `predict_race()`リファクタ
  - [ ] `backtest_gui_logic.py`書き換え
  - [ ] コード検証（文法エラーチェック）
  - 成果物: 修正された`keiba_prediction_gui_v3.py`, `backtest_gui_logic.py`

- [ ] **Task 1.2**: 修正後バックテスト検証（1時間）
  - [ ] 小規模バックテスト実行（100レース）
  - [ ] GUIとの一致確認スクリプト実行
  - [ ] データリーケージ解消確認
  - [ ] 検証レポート生成
  - 成果物: `docs/GUI_BACKTEST_VERIFICATION_REPORT.md`

- [ ] **Task 1.3**: Phase 13実運用マニュアル作成（1時間）
  - [ ] 実運用手順書作成
  - [ ] 資金管理ルール文書化
  - [ ] 運用ログテンプレート作成
  - [ ] リスク管理ガイド作成
  - 成果物: `docs/PHASE13_OPERATION_MANUAL.md`

- [ ] **Task 1.4**: Phase 13単勝の他確率帯検証（1-2時間）
  - [ ] 全確率帯で単勝回収率計算スクリプト実行
  - [ ] 100%超の確率帯を特定
  - [ ] 確率帯別の最適購入額算出
  - [ ] 結果ドキュメント作成
  - 成果物: `phase13_tansho_all_bands_results.csv`, `docs/PHASE13_OPTIMAL_BANDS.md`

**Phase 1完了時点**: Phase 13が完全実用化可能

---

### 🟡 Phase 2: システム改善（推奨、2-3時間）

- [ ] **Task 2.1**: fix_missing_horse_data.py修正（30分）
  - [ ] `scrape_horse_selenium.py`の関数確認
  - [ ] インポートエラー修正
  - [ ] 代替実装（必要に応じて）
  - 成果物: 修正された`fix_missing_horse_data.py`

- [ ] **Task 2.2**: recalculate_features.py修正（30分）
  - [ ] 全print文から絵文字削除
  - [ ] Unicode安全な出力に変更
  - [ ] 動作確認
  - 成果物: 修正された`recalculate_features.py`

- [ ] **Task 2.3**: 欠損データ補完実行（1時間）
  - [ ] 修正版スクリプト実行
  - [ ] 75件の父・母父データ取得
  - [ ] データベース更新
  - 成果物: 更新されたデータベース

- [ ] **Task 2.4**: 特徴量再計算実行（1時間）
  - [ ] 修正版スクリプト実行
  - [ ] 全特徴量を再計算
  - [ ] バックアップ作成
  - 成果物: 更新された特徴量データベース

**Phase 2完了時点**: システムの完全性向上、データ品質改善

---

### 🟢 Phase 3: Phase 14開発（時間次第、5-10時間）

- [ ] **Task 3.1**: Phase 14データ準備（1時間）
  - [ ] 目的変数を1-3着予測に変更
  - [ ] 訓練データ・検証データ分割
  - [ ] データ品質確認
  - 成果物: `data/phase14_training_data.csv`

- [ ] **Task 3.2**: Phase 14特徴量エンジニアリング（2-3時間）
  - [ ] Phase 13特徴量をベースに
  - [ ] 安定性重視の特徴量追加
  - [ ] 複勝率、連対率の計算
  - [ ] 展開・ペース指数の追加
  - 成果物: 拡張された特徴量セット

- [ ] **Task 3.3**: Phase 14モデル訓練（2-3時間）
  - [ ] LightGBMで複勝確率予測
  - [ ] ハイパーパラメータ調整
  - [ ] クロスバリデーション
  - [ ] モデル保存
  - 成果物: `model_phase14_fukusho_win.pkl`

- [ ] **Task 3.4**: Phase 14バックテスト検証（1-2時間）
  - [ ] 2020-2025年で検証
  - [ ] 確率帯別の複勝回収率計算
  - [ ] Phase 13との比較
  - [ ] 併用戦略の検討
  - 成果物: `phase14_fukusho_backtest_results.csv`

- [ ] **Task 3.5**: Phase 14ドキュメント作成（30分）
  - [ ] モデル仕様書
  - [ ] 検証結果レポート
  - [ ] Phase 13との比較
  - [ ] 実運用ガイド
  - 成果物: `docs/PHASE14_FUKUSHO_MODEL.md`

**Phase 3完了時点**: 複勝での収益化可能、Phase 13と多角化

---

### ⚪ Phase 4: 追加検証（余裕があれば、3-10時間）

- [ ] **Task 4.1**: ワイド・馬連検証準備（2-3時間）
  - [ ] Phase 13で全馬予測生成
  - [ ] 5,285レースの全馬（約75,000頭）
  - [ ] 予測結果保存
  - 成果物: `phase13_all_horses_predictions.csv`

- [ ] **Task 4.2**: ワイド・馬連検証実行（1時間）
  - [ ] 上位2-3頭の組み合わせ検証
  - [ ] 実払戻データと照合
  - [ ] 回収率計算
  - 成果物: `phase13_wide_umaren_results.csv`

- [ ] **Task 4.3**: 払戻データ追加収集（3-6時間）
  - [ ] 2020-2023年のレースID抽出
  - [ ] netkeiba.comからスクレイピング
  - [ ] データ構造の検証
  - [ ] 保存
  - 成果物: `data/payout_data/payout_2020_2026_COMPLETE.json`

**Phase 4完了時点**: 全券種検証完了、データ完全化

---

## 🔄 実行フロー

```
開始
 ↓
Phase 1 (必須)
 ├─ Task 1.1: GUI/バックテスト共通化 ✅
 ├─ Task 1.2: バックテスト検証 ✅
 ├─ Task 1.3: 実運用マニュアル ✅
 └─ Task 1.4: 単勝他確率帯検証 ✅
 ↓
Phase 2 (推奨)
 ├─ Task 2.1-2.2: スクリプト修正 ✅
 └─ Task 2.3-2.4: 欠損データ補完・特徴量再計算 ✅
 ↓
Phase 3 (時間次第)
 ├─ Task 3.1-3.2: データ準備・特徴量 ✅
 ├─ Task 3.3: モデル訓練 ✅
 ├─ Task 3.4: バックテスト検証 ✅
 └─ Task 3.5: ドキュメント ✅
 ↓
Phase 4 (余裕があれば)
 ├─ Task 4.1-4.2: ワイド・馬連検証 ⚠️
 └─ Task 4.3: 払戻データ拡充 ⚠️
 ↓
最終レポート生成
 ↓
完了
```

---

## ⏱️ タイムライン（推定）

| 時間 | タスク | 累積 |
|:---:|:---|:---:|
| 0-3h | Phase 1-1: GUI/バックテスト共通化 | 3h |
| 3-4h | Phase 1-2: バックテスト検証 | 4h |
| 4-5h | Phase 1-3: 実運用マニュアル | 5h |
| 5-7h | Phase 1-4: 単勝他確率帯検証 | 7h |
| **7h** | **Phase 1完了** | **7h** |
| 7-8h | Phase 2-1,2: スクリプト修正 | 8h |
| 8-9h | Phase 2-3: 欠損データ補完 | 9h |
| 9-10h | Phase 2-4: 特徴量再計算 | 10h |
| **10h** | **Phase 2完了** | **10h** |
| 10-11h | Phase 3-1: データ準備 | 11h |
| 11-14h | Phase 3-2: 特徴量エンジニアリング | 14h |
| 14-17h | Phase 3-3: モデル訓練 | 17h |
| 17-19h | Phase 3-4: バックテスト検証 | 19h |
| 19-20h | Phase 3-5: ドキュメント | 20h |
| **20h** | **Phase 3完了** | **20h** |
| 20-23h | Phase 4-1: 全馬予測生成 | 23h |
| 23-24h | Phase 4-2: ワイド・馬連検証 | 24h |
| 24-30h | Phase 4-3: 払戻データ拡充 | 30h |
| **30h** | **Phase 4完了** | **30h** |

**確実に完了**: Phase 1-2 (10時間)
**高確率で完了**: Phase 3 (20時間)
**時間次第**: Phase 4 (30時間)

---

## 📊 成功基準

### Minimum Success（最低限）
- ✅ Phase 1完了（7時間）
- Phase 13が実運用可能な状態

### Target Success（目標）
- ✅ Phase 1-2完了（10時間）
- ✅ Phase 3一部完了（15-20時間）
- Phase 13実運用 + Phase 14開発中

### Stretch Success（理想）
- ✅ Phase 1-3完了（20時間）
- ✅ Phase 4一部完了（25-30時間）
- 全券種検証完了、完全なシステム

---

## 🔍 各フェーズ完了時の確認事項

### Phase 1完了時
- [ ] GUI起動確認（エラーなし）
- [ ] バックテストが正常実行
- [ ] 実運用マニュアルの完全性
- [ ] 最適確率帯の特定

### Phase 2完了時
- [ ] 欠損データ0件
- [ ] 特徴量が最新状態
- [ ] データベース整合性

### Phase 3完了時
- [ ] Phase 14モデルファイル存在
- [ ] バックテスト結果で回収率100%超
- [ ] ドキュメント完全性

### Phase 4完了時
- [ ] 全券種の検証結果
- [ ] 払戻データ拡充完了

---

## 🚨 エラー時の対応

### 各タスクでエラーが発生した場合
1. エラー詳細をログに記録
2. 次のタスクに進む（スキップ）
3. 最終レポートで失敗タスクを報告

### 致命的エラー（Phase 1での失敗）
- Phase 1は最優先、エラー時は再試行
- 3回失敗したら詳細ログを残して次へ

---

## 📁 成果物の保存先

### ドキュメント
- `docs/GUI_BACKTEST_VERIFICATION_REPORT.md`
- `docs/PHASE13_OPERATION_MANUAL.md`
- `docs/PHASE13_OPTIMAL_BANDS.md`
- `docs/PHASE14_FUKUSHO_MODEL.md`
- `docs/48H_EXECUTION_REPORT.md`

### データファイル
- `phase13_tansho_all_bands_results.csv`
- `phase14_fukusho_backtest_results.csv`
- `phase13_all_horses_predictions.csv`
- `phase13_wide_umaren_results.csv`

### モデルファイル
- `model_phase14_fukusho_win.pkl`

### ログファイル
- `48h_execution_log.txt`
- `48h_progress.json`

---

**作成日**: 2026年2月21日
**開始待ち**: ユーザー承認後
**推定完了**: 48時間以内
