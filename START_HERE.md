# 作業再開ガイド

**最終更新**: 2026年2月24日（深夜）
**現在のステータス**: 実運用ツール全整備完了 → **あとはペーパートレードを開始するだけ**

---

## 今どこにいるか

```
Phase 14 ✅ → Phase A/B/C ✅ → GUI統合 ✅ → NaT修正 ✅ → 運用ツール整備 ✅
                                                                    ↓
                                                          今週末: ペーパートレード開始
```

**モデル・バックテスト・GUI・全ツールの整備が完了。**
次のアクションは「今週末のレースでペーパートレードを開始する」のみ。

---

## 今週末の運用手順

### 土日朝07:00（または手動）

```bash
# レーススケジュール取得
py odds_collector/schedule_fetch.py
```

### 各レース発走30分前

```bash
# オッズスナップショット取得
py odds_collector/odds_snapshot.py --timing 30min_before
```

### GUIで予測

```bat
競馬予想ツール.bat
```

Rule4 条件を確認:
- `pred_win > 20%` かつ `2.0x ≤ オッズ < 10.0x`
- または `pred_win > 10%` かつ `オッズ ≥ 10.0x`

### レース後に結果を記録

```bash
py paper_trade_add.py
```

入力する項目: 日付 / レースID / 馬名 / bet_type(win/place/both) /
pred_win / pred_place / オッズ / オッズ取得時刻 / ルール / 結果

### 月次レビュー（月初に実行）

```bash
py paper_trade_review.py
# または月次指定
py paper_trade_review.py --month 202603
```

出力: 損益サマリー / GO/NO-GO判定 / PSIドリフト確認 / Kelly比較

---

## 現在の状態まとめ

### 完成しているもの

| ファイル | 内容 |
|---|---|
| `phase14_model_win.txt` | 単勝予測モデル（AUC 0.7988） |
| `phase14_model_place.txt` | 複勝予測モデル（AUC 0.7558） |
| `phase14_feature_list.pkl` | 39特徴量リスト |
| `keiba_prediction_gui_v3.py` | GUI本体（Phase 14統合済み） |
| `phase_a_predictions.csv` | 2025年全馬の予測確率（検証用） |
| `phase_c_rule_summary.csv` | ベットルール別成績 |

### バックテスト結果（2025年テストデータ）

**推奨ベットルール: Rule4 複合最良**

| 条件 | 件数/年 | 的中率 | 回収率 | 純損益 |
|---|---:|---:|---:|---:|
| pred_win > 10% かつ odds ≥ 10.0x | 2,439 | 8.0% | 172% | +175,640円 |
| pred_win > 20% かつ odds ≥ 5.0x | 914 | 18.9% | 223% | +112,210円 |
| **Rule4（上2つの和集合）** | **3,833** | **17.5%** | **159%** | **+225,360円** |

*(初期資金50,000円、1点100円固定。ペナルティ適用後は約130〜140%想定)*

---

## 次のロードマップ

| 状態 | タスク | 内容 |
|---|---|---|
| ✅ | GUI ヘッドレス確認 | モデル読込・データ読込・予測 全項目OK |
| ✅ | Phase C-3 NaT修正 | `phase_c_operation.py` 月次バンクロール正常化 |
| ✅ | pandas FutureWarning修正 | `keiba_prediction_gui_v3.py` / `backtest_full_2020_2025.py` |
| ✅ | 複勝並行記録 + Kelly | `paper_trade_log.csv` / `paper_trade_add.py` 列追加 |
| ✅ | バックアップ削除 | 109件・12.95 GB 解放（残5件 584 MB） |
| ✅ | オッズ収集バッチ | `odds_collector/` 一式（SQLite・README・スケジューラ手順） |
| ✅ | 月次レビュースクリプト | `paper_trade_review.py`（PSI・GO/NO-GO・Kelly比較） |
| **今週末〜** | **ペーパートレード開始** | 上記「今週末の運用手順」参照 |
| 1〜2ヶ月後 | GO/NO-GO 判断 | 5基準すべてクリアでライブトレード移行検討 |
| 3〜6ヶ月後 | Phase D-1 + SHAP | オッズドリフト特徴量 + GUI予測根拠表示 |
| 長期 | Phase D-2 | 月次モデル再訓練サイクル |

---

## 詳細ドキュメント

| ファイル | 内容 |
|---|---|
| `docs/GEMINI_QA_RESPONSE_20260224.md` | **最新: Gemini Q&A回答まとめ・対応方針** |
| `docs/PROJECT_STATUS_20260224.md` | プロジェクト総括・提言A〜G |
| `docs/GEMINI_EVAL_RESPONSE_20260224.md` | Gemini提言評価への相談・逆提言 |
| `docs/GEMINI_FEEDBACK_20260224.md` | Geminiフィードバック対応（odds_recorded_time等） |
| `docs/PHASE_C3_SESSION_REPORT_20260224.md` | Phase C-3 NaT修正レポート |
| `docs/PHASE_C2_GUI_INTEGRATION_20260223.md` | Phase C-2 GUI統合 |
| `docs/PHASE_ABC_RESULTS_20260223.md` | Phase A/B/C 検証結果レポート |

---

## トラブルシューティング

### 「モデル読み込み失敗」と出た場合

以下のファイルが存在するか確認:

```bash
ls phase14_model_win.txt phase14_model_place.txt phase14_feature_list.pkl
```

### LightGBM の import が遅い / ハングする場合

- GUIは1プロセスのみ起動する（複数同時起動しない）
- 他の Python プロセスが動いていないか確認

### predict_proba エラーが出た場合

既に修正済みのはず。`keiba_prediction_gui_v3.py` の L1777 を確認:

```python
pred_win_proba = float(self.model_win.predict(feat_df)[0])   # ← これが正しい
pred_top3_proba = float(self.model_place.predict(feat_df)[0]) # ← これが正しい
```

---

*更新: 2026年2月24日（夜）*
