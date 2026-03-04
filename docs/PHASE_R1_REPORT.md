# Phase R1 作業レポート

**実施日**: 2026年3月4日
**ブランチ**: `improve/R1`
**目的**: Phase 14 ベースライン（AUC 0.7988、ROI 139.1%）を超える特徴量追加による性能改善

---

## 1. 実施内容

### 1-1. 追加した特徴量（7個）

| ID | 特徴量名 | 説明 | ソース |
|----|---------|------|--------|
| B-1 | `heavy_track_win_rate` | 道悪（重・不良）コースでの勝率 | 馬の過去成績 |
| B-2 | `kiryou` | 斤量（kg） | 当該レース情報 |
| B-3a | `is_female` | 牝馬フラグ（0/1） | 性齢文字列 |
| B-3b | `horse_age` | 馬齢 | 性齢文字列 |
| B-4a | `horse_weight` | 馬体重（kg） | 当該レース情報 |
| B-4b | `weight_change` | 馬体重増減（kg）前走比 | 当該レース情報 + 過去成績 |
| B-5 | `distance_change` | 前走距離差（m） | 当該レース距離 − 前走距離 |

### 1-2. 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `phase13_feature_engineering.py` | `calculate_horse_features_safe()` に3パラメータ追加・B-1〜B-5を実装 |
| `keiba_prediction_gui_v3.py` | `FEATURE_NAMES_JP` に7特徴量追加、2箇所の呼び出し更新、`get_race_from_database()` バグ修正 |
| `phase13_calculate_all_features.py` | 呼び出し更新・デフォルト辞書2箇所に7特徴量追加 |
| `calculate_features_standardized.py` | 標準化DB対応カラム名で呼び出し更新 |

### 1-3. 実行パイプライン

```
calculate_features_standardized.py   （2時間・283,925レース）
        ↓ data/phase14/{train,val,test}_features.csv（46特徴量）
phase3_train_model.py                （LightGBM再訓練）
        ↓ phase14_model_win.txt・phase14_model_place.txt
run_gui_backtest.py --year 2024      （2024 OOS バックテスト）
        ↓ backtest_gui_2024_{races,bets}.csv
```

---

## 2. 結果

### 2-1. モデル性能

| 指標 | Phase 14 ベースライン | Phase R1 | 変化 |
|------|---------------------|---------|------|
| 特徴量数 | 39 | **46** | +7 |
| Win AUC（2024 val） | 0.7988 | **0.7997** | +0.0009 |
| 訓練レコード数 | 190,995 | 190,995 | — |

### 2-2. 2024年 OOS バックテスト（GUI完全一致）

| 指標 | Phase 14 ベースライン | Phase R1 | 変化 |
|------|---------------------|---------|------|
| Rule4 件数 | 6,349 | **6,122** | −227（より選択的） |
| Rule4 的中率 | 16.3% | **17.5%** | +1.2pp |
| Rule4 ROI | 139.1% | **142.1%** | +3.0pp |
| Rule4 純損益 | +247,939円 | **+257,480円** | +9,541円 |

### 2-3. 条件別内訳（Phase R1・2024）

| 条件 | 件数 | 的中率 | ROI | 純損益 |
|------|-----|--------|-----|--------|
| 条件A（pred_win≥20% & odds 2〜10x） | 2,561 | 31.9% | 125.3% | +64,774円 |
| **条件B（pred_win≥10% & odds≥10x）** | 3,561 | 7.2% | **154.1%** | +192,706円 |
| **Rule4（A∪B）** | **6,122** | **17.5%** | **142.1%** | **+257,480円** |

### 2-4. 月次・競馬場別（Phase R1・2024）

**月次ROI（最良/最悪）**:
- 7月: 202.2%（最高）
- 6月: 164.7%
- 9月: 179.1%
- 8月: 112.5%（最低でもプラス）

**競馬場別ROI（上位）**:
- 福島: 234.5%
- 函館: 167.7%
- 新潟: 160.9%
- 中山: 152.1%

---

## 3. 発見したバグと修正

### バグ: `get_race_from_database()` が新特徴量に渡す値が常にデフォルト

**症状**: 初回バックテストでRule4件数が 6,349 → 1,006 に激減（ROIは181%に見えたが件数激減でほぼ無意味）

**原因**:
`keiba_prediction_gui_v3.py` の `get_race_from_database()` が:
- `'斤量': ''` をハードコード（DBから取得しない）
- `'性齢'`, `'馬体重'` キーが辞書に存在しない

→ `calculate_horse_features_safe()` に渡された時、全馬が以下のデフォルト値を使用:
- `horse_age = 0`（実際の競走馬は2〜8歳）
- `horse_weight = 0`（実際は400〜600kg）
- `kiryou = 55.0`（全馬同一）

→ 学習データと大きく乖離（OOD）し、確率分布が崩れ、10%閾値を超える馬が激減

**修正**（`keiba_prediction_gui_v3.py` L1187〜1191）:
```python
# 修正前
'斤量': '',

# 修正後
'斤量': row.get('斤量', ''),
'性齢': row.get('性齢', ''),
'馬体重': row.get('馬体重', ''),
```

---

## 4. 技術メモ

### horse_weight の2フォーマット対応

学習データ（standardized DB）とGUI/バックテスト（complete DB）で馬体重のフォーマットが異なる：

| ソース | フォーマット | 例 |
|--------|------------|-----|
| standardized DB（学習用） | 数値 | `460` |
| complete DB（GUI/バックテスト） | 文字列 | `"460(+2)"` |

`phase13_feature_engineering.py` の B-4 実装では両方に対応:
```python
m = re.match(r'(\d+)\(([+-]?\d+)\)', str(horse_weight_str))
if m:
    # GUI/complete DB形式: "460(+2)"
    features['horse_weight'] = int(m.group(1))
    features['weight_change'] = int(m.group(2))
else:
    # standardized DB形式: 460（数値）→ 前走との差分を過去成績から計算
    ...
```

### モデルバージョン管理

```
models/
├── phase14_baseline/     # AUC 0.7988・39特徴量
│   ├── model_win.txt
│   ├── model_place.txt
│   └── feature_list.pkl
└── phase_r1/             # AUC 0.7997・46特徴量（現在の有効版）
    ├── model_win.txt
    ├── model_place.txt
    └── feature_list.pkl

# 切り替え
py restore_model.py phase14_baseline   # ベースラインに戻す
py restore_model.py phase_r1           # Phase R1に戻す
```

---

## 5. 残課題・次フェーズ候補

### 5-1. 即座に検証可能

| 課題 | 内容 |
|------|------|
| 2025年 OOS バックテスト | Phase R1モデルで2025年も同様に検証（ベースラインは154.8%） |
| Place AUC 確認 | Phase R1の複勝モデルのAUC（ベースラインは0.7558）未確認 |
| 条件Aの閾値調整 | 現状ROI 125%と条件Bより低い。閾値（20%→25%）調整で改善の余地 |

### 5-2. Phase R2 候補（特徴量追加）

| 優先度 | ID | 内容 | 期待効果 |
|--------|-----|------|---------|
| 高 | C-1 | 血統詳細（種牡馬×距離×馬場種別） | 現在の father_win_rate より細分化 |
| 中 | C-2 | ペース適性（逃げ・先行・差し・追込の過去成績比率） | running_style_category を活用 |
| 中 | C-3 | 斤量差（同レース内の斤量相対位置） | 牝馬・ハンデ戦で有効 |
| 低 | D-1 | オッズドリフト特徴量 | odds_collector 蓄積後に実施 |

### 5-3. 運用面

| 課題 | 内容 |
|------|------|
| GUIの `性齢`・`斤量`・`馬体重` スクレイピング確認 | バックテストでは完全DBから取得、実運用ではスクレイピング。値が正しく取得できているか要確認 |
| 条件B ペーパートレード蓄積 | 現在開始してから間もないため、統計的有意性（200件以上）が必要 |
| `paper_trade_review.py` の GO/NO-GO 基準 | Phase R1モデルに更新したので、2026年の実績で再評価 |

---

## 6. モデル切り替え方法（まとめ）

```bash
# 現在のバージョン確認
py restore_model.py

# Phase R1（現在の有効モデル）
py restore_model.py phase_r1

# ベースラインに戻す場合
py restore_model.py phase14_baseline
```

---

*作成: 2026年3月4日*
