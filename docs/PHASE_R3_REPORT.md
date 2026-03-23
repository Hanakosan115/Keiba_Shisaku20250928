# Phase R3 実験レポート

> 作成日: 2026-03-07
> Phase R3: 死んでいた特徴量2個の修正（avg_last_3f / running_style）

---

## 1. 変更内容

### 修正した特徴量

| 特徴量 | 修正前 | 修正後 |
|--------|--------|--------|
| `avg_last_3f` | 常に0（`latest.get('avg_last_3f', 0.0)` → standardized CSV にデータなし） | enriched CSV の `Agari` 列から履歴平均を計算（≥25秒フィルタ）|
| `running_style` | 3か4しか出ない（`avg_first_corner` の閾値バグ。18頭立て等で機能しない） | `running_style_category` のmode（front_runner/stalker/midpack/closer → 1/2/3/4）|

### 変更ファイル

| ファイル | 変更内容 |
|---------|---------|
| `phase13_feature_engineering.py` | `avg_last_3f` 計算 → `Agari` 列から。`running_style` → `running_style_category` から |
| `calculate_features_standardized.py` | enriched CSV の `Agari` を (race_id, horse_id) でマージ追加 |
| `keiba_prediction_gui_v3.py` | `load_data()` 内でも同様に `Agari` をマージ（GUI予測にも反映） |

### パイプライン再実行

```
py calculate_features_standardized.py  # 2.1時間（283,925レース）
py optimize_hyperparams.py             # 80トライアル Optuna
py run_gui_backtest.py --year 2024
```

---

## 2. モデル性能比較

| 指標 | Phase R2-Optuna（修正前） | Phase R3（修正後） | 変化 |
|------|------------------------|------------------|------|
| 特徴量数 | 60 | 60 | ― |
| CV AUC | 0.8270 | **0.8289** | +0.0019 |
| Val AUC（2024 OOS） | 0.7656 | **0.7660** | +0.0004 |
| Best Iteration | 338 | 225 | ▼ |
| learning_rate | 0.0086 | 0.0102 | ↑ |
| num_leaves | 43 | 48 | ↑ |

AUC は両指標でわずかに改善。

---

## 3. 2024 OOS バックテスト結果

### Rule4 全体

| 指標 | Phase R2-Optuna | Phase R3 | 変化 |
|------|----------------|----------|------|
| 件数 | 5,730件 | 6,397件 | +667件 |
| 的中率 | 17.7% | 16.2% | ▼1.5pt |
| ROI | **148.0%** | 138.1% | **▼9.9pt** |
| 純損益 | +274,879円 | +243,427円 | ▼31,452円 |

### 条件別

| 条件 | R2-Optuna | R3 | 変化 |
|------|----------|-----|------|
| 条件A（pred≥20% odds 2-10x） | 126.7% | 124.5% | ▼2.2pt |
| 条件B（pred≥10% odds≥10x） | **163.2%** | 146.1% | **▼17.1pt** |

### オッズ帯別

| オッズ帯 | R2-Optuna | R3 | 変化 |
|---------|----------|-----|------|
| 2〜5x | 114.1% | 111.6% | ▼2.5pt |
| 5〜10x | 156.1% | 155.0% | ▼1.1pt |
| 10〜20x | 133.0% | 130.0% | ▼3.0pt |
| 20〜50x | 150.8% | 138.2% | ▼12.6pt |
| **50x超** | **289.2%** | **208.4%** | **▼80.8pt** |

### 月次（R3）

全12ヶ月でプラス（最低: 2月 +3,105円 ROI 106.7%）。

---

## 4. 考察

### ROIが下がった原因（仮説）

1. **高オッズ帯（50x超）の推奨馬が変わった**
   `running_style` と `avg_last_3f` の修正により、高オッズ馬への予測スコアが変化。ROI 289.2% → 208.4%（▼80.8pt）の急落が全体低下の主因。

2. **ベット件数が増加した（5,730 → 6,397）**
   モデルの予測確率分布が変化し、条件Bの対象馬が667件増えた。増加分の質が平均を下回った可能性。

3. **旧特徴量が2024に偶然フィット**
   `avg_last_3f=0` 固定・`running_style` が3or4固定でも、2024年OOSではたまたま高ROIを出していた可能性。

4. **AUCとROIの乖離**
   Val AUC は改善（+0.0004）しているが ROI は低下。AUC改善 ≠ ROI改善 であることを再確認。

### 特徴量の修正は正しいか

- `avg_last_3f` の修正は**正しい**（0固定では情報がない。Agariから計算することで馬の速度能力を反映）
- `running_style` の修正は**正しい**（threshold バグの修正。category分類の方が信頼性が高い）
- ただし2024 OOS 1年での比較では偶然性を排除できない

---

## 5. 判定と対応

### 現行有効モデル: Phase R2-Optuna（ROI 148.0%）を維持

Phase R3 は AUC で上回るが ROI で下回る。OOS 1年での判断は不確かなため、**Phase R2-Optuna を有効モデルとして維持**する。

Phase R3 モデルは `models/phase_r3/` に保存済み。

### 次のアクション候補

| 優先度 | タスク | 理由 |
|--------|--------|------|
| ★★★ | **Phase R2-Optuna で 2025 OOS バックテスト** | OOS を2年分にして信頼性向上 |
| ★★★ | **Phase R3 で 2025 OOS バックテスト** | R2 vs R3 を追加OOSで比較 |
| ★★ | running_style 特徴量のSHAP重要度確認 | R3でどう変化したか分析 |
| ★★ | レース内相対特徴量の追加（Phase R4候補） | AUCよりROIに効く可能性 |

---

## 6. モデルファイル

| フェーズ | ディレクトリ | Val AUC | ROI(2024) |
|--------|------------|---------|----------|
| Phase R2-Optuna | `models/phase_r2_optuna/` | 0.7656 | **148.0%** ← 現行 |
| Phase R3 | `models/phase_r3/` | 0.7660 | 138.1% |

---

_最終更新: 2026-03-07_
