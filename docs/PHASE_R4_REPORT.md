# 作業レポート：Phase R4 — レース内相対特徴量

> 作成日: 2026-03-08

---

## 1. 概要

Phase R2-Optuna（60特徴量）に、同一レース内での馬間比較（相対特徴量）7個を追加した Phase R4 モデルを訓練・評価した。

**結論: R4 を正式採用。R2-Optuna より ROI・的中率ともに改善。**

---

## 2. 追加特徴量（7個）

| 特徴量名 | 元データ | 方向 | 意味 |
|----------|---------|------|------|
| `field_win_rate_rank` | `total_win_rate` | 高いほど良い | レース内勝率ランク（0〜1、1=最良） |
| `field_jockey_rank` | `jockey_win_rate` | 高いほど良い | 騎手勝率ランク |
| `field_trainer_rank` | `trainer_win_rate` | 高いほど良い | 調教師勝率ランク |
| `field_earnings_rank` | `total_earnings` | 高いほど良い | 賞金実績ランク |
| `field_last3f_rank` | `avg_last_3f` | 低いほど良い | 上がりタイムランク |
| `field_diff_rank` | `avg_diff_seconds` | 低いほど良い | タイム差ランク |
| `field_size` | - | - | レース出走頭数 |

正規化式: `(N - raw_rank) / (N - 1)` → 1=最良、0=最悪

---

## 3. 実施手順

1. `calculate_features_r4.py` — `data/phase14/` CSVs に相対特徴量を追加して `data/phase_r4/` に保存
   - train: 190,995行 / val: 47,181行 / test: 36,359行
2. `train_phase_r4.py --no-optuna` — R2-Optuna パラメータを流用して高速訓練
3. `keiba_prediction_gui_v3.py` — `_add_relative_features_for_race()` 追加 + `predict_core()` を2パス構造に変更
4. R4モデルをアクティブ化 (`phase14_model_*.txt` / `phase14_feature_list.pkl`)
5. 2024・2025 OOS バックテスト実行（並列）

---

## 4. モデル性能

### 訓練結果

| 指標 | R2-Optuna | R4（--no-optuna） | 変化 |
|------|-----------|-------------------|------|
| 特徴量数 | 60 | 67 | +7 |
| Win Val AUC | 0.7656 | **0.7858** | **+0.0202** |
| Place Val AUC | - | 0.7564 | - |
| Best Iteration (win) | 338 | 340 | +2 |

### 特徴量重要度 Top 5（Gain）

| 順位 | 特徴量 | Gain | 備考 |
|------|--------|------|------|
| 1 | `jockey_track_win_rate` | 301,622 | |
| 2 | `prev_race_rank` | 218,838 | |
| **3** | **`field_win_rate_rank`** | **153,578** | **★R4新規** |
| **4** | **`field_jockey_rank`** | **35,403** | **★R4新規** |
| 5 | `total_win_rate` | 34,308 | |

→ 新規特徴量が3位に入り、レース内相対情報の重要性を確認。

---

## 5. OOS バックテスト結果

### 2024年（out-of-sample）

| 指標 | R2-Optuna | **R4** | 変化 |
|------|-----------|--------|------|
| Rule4件数 | 5,730件 | 4,384件 | ▼1,346件（厳選化） |
| 的中率 | 17.7% | **22.7%** | **+5.0pt** |
| ROI | 148.0% | **157.3%** | **+9.3pt** |
| 純損益 | +274,879円 | +251,393円 | ▼23,486円 |
| 条件A ROI | 126.7% | 143.0% | +16.3pt |
| 条件B ROI | 163.2% | **171.1%** | **+7.9pt** |
| 50x超 ROI | 289.2% | **220.0%** | ▼69.2pt |

### 2025年（out-of-sample）

| 指標 | R2-Optuna | **R4** | 変化 |
|------|-----------|--------|------|
| Rule4件数 | 5,372件 | 3,729件 | ▼1,643件（厳選化） |
| 的中率 | 19.9% | **26.3%** | **+6.4pt** |
| ROI | 174.7% | **197.9%** | **+23.2pt** |
| 純損益 | +401,142円 | +365,046円 | ▼35,096円 |
| 条件A ROI | 142.4% | **149.2%** | **+6.8pt** |
| 条件B ROI | 196.9% | **249.9%** | **+53.0pt** |
| 50x超 ROI | 334.2% | **430.6%** | **+96.4pt** |

### オッズ帯別（2025年）

| オッズ帯 | 件数 | 的中率 | ROI |
|----------|------|--------|-----|
| 2x〜5x | 1,373件 | 43.6% | 136.6% |
| 5x〜10x | 552件 | 28.3% | 180.4% |
| 10x〜20x | 1,030件 | 15.1% | 207.6% |
| 20x〜50x | 604件 | 9.8% | 271.2% |
| 50x〜∞ | 170件 | 7.1% | **430.6%** |

---

## 6. 評価と考察

### 採用判定: ✅ R4 正式採用

**メリット:**
- ROI が 2 年連続で改善（2024: +9.3pt / 2025: +23.2pt）
- 的中率が大幅向上（高精度な絞り込み）
- 条件B（高オッズ帯）が特に強化 → 50x超 ROI 430.6%（2025）

**注意点:**
- 件数が減少（約70%水準）→ 純損益はやや減少
- 50x超 ROI は 2024 では R2-Optuna より低下（220% vs 289%）
- `--no-optuna` フラグを使ったため Optuna 最適化未実施（次フェーズ候補）

---

## 7. GUI 統合の変更点

`keiba_prediction_gui_v3.py` に以下の変更を加えた：

### 追加: `_add_relative_features_for_race()` 静的メソッド
- predict_core() 呼び出し時にレース内全馬の特徴量から相対値を計算
- 1頭の場合は全て 1.0 にフォールバック

### 変更: `predict_core()` を2パス構造に

```
【旧】1パス: 1馬ずつ特徴量計算 → 即予測
【新】Pass 1: 全馬の基本特徴量を収集
     ↓ _add_relative_features_for_race() でレース内相対特徴量を一括計算
     Pass 2: 全馬を予測 → 結果組み立て
```

この変更により、`model_features` に `field_*` 列が含まれていない場合（旧モデル）は相対特徴量計算をスキップするため、後方互換性も保たれる。

---

## 8. ファイル変更サマリー

| ファイル | 変更内容 |
|----------|---------|
| `calculate_features_r4.py` | 新規作成（R4相対特徴量CSV生成） |
| `train_phase_r4.py` | 新規作成（R4モデル訓練） |
| `keiba_prediction_gui_v3.py` | `_add_relative_features_for_race()` 追加・`predict_core()` 2パス化 |
| `phase14_model_win.txt` | R4モデルに更新（R2バックアップ: `.bak_r2`） |
| `phase14_model_place.txt` | R4モデルに更新 |
| `phase14_feature_list.pkl` | 67特徴量リストに更新 |
| `models/phase_r4/` | R4モデル一式保存 |

---

## 9. note.com ヘッダー画像アップロード修正（完了）

`note_publisher/post_to_note.py` の `_upload_header_image()` を完全書き直し。

### 問題
- `get_by_text('画像をアップロード')` が 0件を返す（ボタンがパネル内に隠れている）
- CropModal（`ReactModalPortal`）がその後のクリックをブロック

### 解決策
```
① button[aria-label="画像を追加"] をクリック → パネルを展開
② JS textContent 検索で「画像をアップロード」ボタンを取得
③ file_chooser でファイルセット
④ data-testid="cropper" 親を JS でウォークアップ → "保存" ボタンクリック
⑤ 30秒待機（画像反映に必要）
```

### 確認済みセレクタ
- ヘッダーボタン: `button[aria-label="画像を追加"]`
- クロップ検出: `document.querySelector('[data-testid="cropper"]')` から親要素を辿って `btn.textContent.trim() === "保存"` を検索

### 検証結果（task bevev637o）
```
[note] ヘッダー画像アップロード完了: Noteヘッダー用.png
[note] クロップモーダル「保存」ボタン: True
[note] クロップモーダル保存完了（画像反映待ち30秒）
```
→ exit code 0 で全工程完了。

---

## 10. 次のアクション候補

| 優先度 | タスク | 概要 |
|--------|--------|------|
| ★★ | **ペーパートレード継続** | R4モデルで週次運用 |
| ★ | Phase R4 Optuna最適化 | `py train_phase_r4.py` で80トライアル実行（`--no-optuna`版で十分な可能性あり） |
| ★ | Phase R5 候補 | オッズドリフト特徴量（D-1）、血統詳細（C-1） |

---

_最終更新: 2026-03-08（note.comヘッダー修正完了）_
