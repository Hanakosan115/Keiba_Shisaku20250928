# Phase C-2: GUI統合 完了レポート

**作成日**: 2026年2月23日
**対象ファイル**: `keiba_prediction_gui_v3.py`
**モデル**: Phase 14 LightGBM（単勝・複勝、39特徴量）

---

## 1. これまでの作業全体サマリー

### Phase 14 モデル訓練（Phase 3実行）

| 項目 | 値 |
|---|---|
| アルゴリズム | LightGBM (GBDT) |
| 特徴量数 | 39 |
| 訓練データ | 2020-2023年（191,527レコード） |
| 検証データ | 2024年（47,273レコード） |
| テストデータ | 2025年（36,398レコード） |
| 単勝 CV AUC | 0.7988 (±0.0033) |
| 単勝 検証 AUC | 0.7860 |
| 複勝 CV AUC | 0.7558 (±0.0020) |
| 複勝 検証 AUC | 0.7333 |

生成ファイル:
- `phase14_model_win.txt` / `phase14_model_place.txt`（LightGBM native形式）
- `phase14_feature_list.pkl`（39特徴量リスト）
- `phase14_model_metadata.json`

### Phase A: フラットベット検証

- **単勝**: 5〜50%確率帯で一貫して過小評価（実際的中率 > 予測確率）→ エッジあり
- **複勝**: 同様にエッジあり
- 出力: `phase_a_predictions.csv`

### Phase B: オッズ帯別ストレステスト

Favorite-Longshot Bias を考慮したペナルティ係数を適用：

| オッズ帯 | ペナルティ係数 |
|---|---|
| ～2.0x（本命） | 0.75 |
| 2.0〜5.0x | 0.85 |
| 5.0〜10.0x | 0.90 |
| 10.0x+（穴馬） | 0.93 |

主な発見:
- **本命（～2.0x）は全帯で赤字**（ペナ後69〜73%）
- **穴馬でモデル高確率 = 最大エッジ**（確率25〜30% × 10倍+ → ペナ後384%）
- 出力: `phase_b_results.csv`

### Phase C: 実運用ルール策定

| ルール | 件数/年 | 的中率 | 回収率(実) | 最大DD | 純損益 |
|---|---:|---:|---:|---:|---:|
| Rule1 保守高頻度 | 2,439 | 8.0% | 172.0% | 6.0% | +175,640円 |
| Rule2 中庸 | 914 | 18.9% | 222.8% | 3.2% | +112,210円 |
| Rule3 積極 | 477 | 22.9% | 239.4% | 2.5% | +66,500円 |
| **Rule4 複合最良** | **3,833** | **17.5%** | **158.8%** | **4.2%** | **+225,360円** |

*(初期資金50,000円、1点100円固定、2025年バックテスト)*

**推奨: Rule4 複合最良**
- `pred_win > 20% AND 2.0x ≤ odds < 10.0x`
- `OR pred_win > 10% AND odds ≥ 10.0x`

出力: `phase_c_rule_summary.csv`, `phase_c_bankroll_summary.csv`

---

## 2. Phase C-2: GUI統合 実施内容

### 変更ファイル
`keiba_prediction_gui_v3.py`（4,288行）

### 変更内容一覧

| # | 場所 | 変更前 | 変更後 |
|---|------|--------|--------|
| 1 | インポート(L21) | `backtest_phase2_phase3_dynamic` から `calculate_horse_features_dynamic` | `phase13_feature_engineering` から `calculate_horse_features_safe` + `import lightgbm as lgb` 追加 |
| 2 | `load_models()`(L110) | Phase 12 pkl / sklearn API | Phase 14 txt / `lgb.Booster()` |
| 3 | `predict_core()` 特徴量計算1回目(L1729) | `calculate_horse_features_dynamic(... horse_races_prefiltered=...)` + Phase10/V3/V4追加ブロック | `calculate_horse_features_safe(... race_id=race_id)` のみ |
| 4 | `predict_core()` 推論1回目(L1777) | `model_win.predict_proba(feat_df)[0, 1]` / `model_top3` | `model_win.predict(feat_df)[0]` / `model_place` |
| 5 | WIN5特徴量計算(L2438) | 同上 | 同上 |
| 6 | WIN5推論(L2499) | 同上 | 同上 |
| 7 | タイトル文字列 | "Phase 12 / 79特徴量" | "Phase 14 / 39特徴量 LightGBM + Rule4複合最良ベット戦略" |

### アーキテクチャの要点（疎結合設計）

```
GUI predict_core()
  ├─ calculate_horse_features_safe()  ← phase13_feature_engineering.py
  │    全特徴量を計算（39種）
  ├─ feat_df = DataFrame[model_features].fillna(0)
  │    ↑ phase14_feature_list.pkl の39特徴量でフィルタリング
  ├─ model_win.predict(feat_df)[0]    ← phase14_model_win.txt
  └─ model_place.predict(feat_df)[0]  ← phase14_model_place.txt
```

- モデルファイルが変わっても `phase14_feature_list.pkl` を差し替えるだけで対応可能
- Phase10/V3/V4の追加特徴量ブロック（79特徴量時代の遺産）を削除し39特徴量に統一
- `predict_proba()` (sklearn) → `predict()` (LightGBM Booster) への変換完了

### 技術的補足（Windowsでの注意事項）

- LightGBM の DLL は複数Pythonプロセス同時起動でデッドロック → **GUIは1プロセスのみ起動**
- `lgb.Booster(model_file=...)` は pkl より大幅高速（pkl は場合によりハング）
- cp932環境でのログ出力に注意（`≈` `◎` `▲` は UnicodeEncodeError になる場合あり）

---

## 3. 今後のロードマップ

### 優先度 高

#### Step 1: GUI動作確認（実施待ち）

```
手順:
1. GUIを起動: py keiba_prediction_gui_v3.py
2. 過去レースID（例: 202501020510）を入力して予想実行
3. 出力された勝率予測と、phase_a_predictions.csv の値を照合
4. 差異が5%未満なら統合成功
```

#### Step 2: ペーパートレード開始

- **期間**: 最低2週間（週2回のJRA開催 × 4〜6開催）
- **記録ファイル**: `paper_trade_log.csv`（未作成）
- **記録項目**: race_id、馬番、馬名、予測確率、実オッズ、Rule4該当可否、実際の着順、損益

```csv
date,race_id,uma_ban,uma_name,pred_win,pred_place,odds,rule4_hit,result_rank,pl
2026-03-01,202503010101,5,XXX,0.23,0.55,6.8,1,3,-100
```

### 優先度 中

#### Phase D-1: オッズドリフト特徴量の追加

- **目的**: 朝イチ（公開直後）オッズ vs 直前（5分前）オッズの変化率を特徴量化
- **仮説**: オッズが下がっている馬（資金流入あり）は「市場の情報を反映」している
- **実装案**:
  - GUIで「朝イチオッズ」入力欄を追加
  - `odds_drift = (odds_morning - odds_final) / odds_morning`
  - Phase 15モデルの特徴量として追加（再訓練必要）

#### Phase C-3: 月次分析グラフ

- `phase_c_operation.py` の日付NaT問題を修正
  - 現状: `pd.to_datetime()` が日本語日付 `2025年01月05日` を NaT に変換
  - 修正: `load_data()` の `_normalize_date()` をインポートして使用
- 月次損益グラフ（matplotlib）をGUIに追加

### 優先度 低（中長期）

#### Phase D-2: 月次モデル再訓練サイクル

- 実運用ログが1ヶ月分蓄積したら再訓練
- 訓練データに2025年を追加し、テストを2026年に移行
- モデルのAUCが0.78以下に落ちたら再訓練トリガー

#### Phase E: オッズ取得タイミング仕様化

- 推奨: レース発走5分前のオッズを使用
- GUIに「オッズ更新ボタン」を追加（現状は手入力）

---

## 4. 生成済みファイル一覧

| ファイル | 内容 | 状態 |
|---|---|---|
| `phase14_model_win.txt` | 単勝予測モデル（Phase 14） | 完成 |
| `phase14_model_place.txt` | 複勝予測モデル（Phase 14） | 完成 |
| `phase14_feature_list.pkl` | 39特徴量リスト | 完成 |
| `phase14_model_metadata.json` | 訓練メタデータ | 完成 |
| `phase_a_predictions.csv` | 2025年全馬の予測確率 | 完成 |
| `phase_b_results.csv` | オッズ帯別回収率集計 | 完成 |
| `phase_c_rule_summary.csv` | ルール別サマリー | 完成 |
| `phase_c_bankroll_summary.csv` | バンクロール試算 | 完成 |
| `phase_a_run.py` | Phase A 実行スクリプト | 完成 |
| `phase_b_stress_test.py` | Phase B 実行スクリプト | 完成 |
| `phase_c_operation.py` | Phase C 実行スクリプト | 完成 |
| `keiba_prediction_gui_v3.py` | GUI本体（Phase 14統合済み） | **完成（本日更新）** |
| `docs/PHASE_ABC_RESULTS_20260223.md` | Phase A/B/C 検証結果レポート | 完成 |
| `docs/PHASE_C2_GUI_INTEGRATION_20260223.md` | 本ファイル | **完成（本日）** |

---

## 5. 注意事項

1. **バックテスト結果は2025年過去データ** — 将来の成績を保証しない
2. **GUIが使うオッズはスクレイピング時点のもの** — 直前オッズとのズレに注意
3. **Rule4ペナルティ後回収率は約130〜140%想定** — 実運用では158.8%より低くなる
4. **月次でルール見直しを推奨** — 2ヶ月連続で回収率100%未満なら一時停止

---

*作成: 2026年2月23日*
