# セッション作業まとめ

> 作成日: 2026-03-14
> 対象セッション: Phase R7+Optuna 確認 → Phase R8 実装 → Phase R8+Optuna 完了

---

## 1. セッション開始時の状態

| 項目 | 値 |
|------|---|
| 有効モデル | Phase R7+Optuna（71特徴量） |
| Val AUC | 0.7875 |
| 2024 ROI | 161.1% |
| 2025 ROI | 186.4% |

---

## 2. 実施作業一覧

### 2-1. Phase R7+Optuna 状態確認・修正

| 作業 | 内容 |
|------|------|
| CLAUDE.md 数値修正 | R7の誤記（175.9%/232.4% → 正: 157.4%/184.5%）を訂正 |
| モデル整合性確認 | models/phase_r7/ = R7+Optunaモデルであることを確認 |
| リバート手順整備 | `py restore_model.py phase_r7_optuna` で即時戻し可能 |

---

### 2-2. Phase R8 特徴量設計・実装

**追加特徴量 7個（71 → 78特徴量）**

| カテゴリ | 特徴量名 | 内容 |
|---------|----------|------|
| B: 血統×競馬場 | `father_track_win_rate` | 父馬×競馬場の歴史的勝率 |
| B: 血統×競馬場 | `mother_father_track_win_rate` | 母父馬×競馬場の歴史的勝率 |
| C: 近況 | `consecutive_losses` | 直近の連続着外回数 |
| C: 近況 | `form_trend` | 直近3走の着順トレンド（正=改善） |
| C: 近況 | `best_distance_diff` | 得意距離帯との乖離（km単位） |
| D: 馬個体×条件 | `horse_waku_win_rate` | 馬個体の枠番別歴史的勝率 |
| D: 馬個体×条件 | `large_field_win_rate` | 大人数（≥12頭）レースでの歴史的勝率 |

**実装ファイル（新規作成）**

| ファイル | 役割 |
|---------|------|
| `calculate_features_r8.py` | enriched CSV → data/phase_r8/ CSV生成（expanding window、リーケージなし） |
| `train_phase_r8.py` | data/phase_r8/ → models/phase_r8/ モデル訓練（Optuna対応） |
| `models/phase_r8/sire_track_stats.json` | 血統×競馬場勝率テーブル（GUI実運用用） |
| `models/phase_r8_base/` | Optuna前R8のバックアップ |

**Phase R8 訓練結果（R7+Optunaパラメータ流用）**

| 指標 | R7+Optuna | R8 | 変化 |
|------|----------|----|------|
| Val AUC（単勝） | 0.7875 | **0.8245** | +0.0370 ↑ |
| 2024 Rule4 ROI | 161.1% | **176.1%** | +15.0pt ↑ |
| 2024 純損益 | +275,150円 | **+404,263円** | +129,113円 ↑ |
| 2025 Rule4 ROI | 186.4% | **180.4%** | -6.0pt ↓ |
| 2025 純損益 | +345,430円 | **+443,984円** | +98,554円 ↑ |

---

### 2-3. Phase R8+Optuna

**Optuna 設定**
- 試行数: 100トライアル
- 評価: 5-Fold Stratified CV（AUC最大化）
- ベースライン: R8（R7+Optunaパラメータ流用）から最適化

**ベストパラメータ**

| パラメータ | R7+Optuna | R8+Optuna |
|-----------|-----------|-----------|
| learning_rate | 0.01112 | **0.0369** |
| num_leaves | 37 | **30** |
| min_child_samples | 140 | （最適化） |
| Best CV AUC | 0.8393 | **0.8683** |

**Phase R8+Optuna 訓練結果**

| 指標 | R8（流用） | R8+Optuna | 変化 |
|------|-----------|-----------|------|
| Val AUC（単勝） | 0.8245 | **0.8256** | +0.0011 ↑ |
| 2024 Rule4 ROI | 176.1% | **179.8%** | +3.7pt ↑ |
| 2024 純損益 | +404,263円 | **+420,812円** | +16,549円 ↑ |
| 2025 Rule4 ROI | 180.4% | **178.1%** | -2.3pt ↓ |
| 2025 純損益 | +443,984円 | **+435,715円** | -8,269円 ↓ |

**2024年 条件別詳細（R8+Optuna）**

| 条件 | ROI |
|------|-----|
| 条件A（pred≥20% & 2〜10倍） | 143.3% |
| 条件B（pred≥10% & 10倍以上） | **223.2%** |
| 条件B うち 50倍超 | **401.0%** |
| Rule4合計 | **179.8%** |

---

### 2-4. GUI・phase13_feature_engineering.py への R8 特徴量統合

`phase13_feature_engineering.py` の `calculate_horse_features_safe()` 末尾に R8 特徴量計算を追加：

- `_SIRE_TRACK_STATS_PATH = 'models/phase_r8/sire_track_stats.json'` をモジュール起動時にロード
- `father_track_win_rate`: `_sire_track_father[f'{father}||{track}']` でルックアップ
- `mother_father_track_win_rate`: 同上（母父）
- `consecutive_losses`: 直近履歴から逆順カウント
- `form_trend`: 直近3走着順の傾き
- `best_distance_diff`: 得意距離バケット（200m刻み、≥3走）との差（km）
- `horse_waku_win_rate`: 枠番別過去勝率（≥2走）
- `large_field_win_rate`: 12頭以上レース過去勝率

---

### 2-5. モデルバージョン管理

| バージョン | 場所 | 復元コマンド |
|-----------|------|------------|
| R7+Optuna | `models/phase_r7/` | `py restore_model.py phase_r7_optuna` |
| R8（Optuna前） | `models/phase_r8_base/` | `py restore_model.py phase_r8_base` |
| **R8+Optuna（現行）** | `models/phase_r8/` + active files | — （現在有効） |

active files:
- `phase14_model_win.txt` = R8+Optuna 単勝モデル
- `phase14_model_place.txt` = R8+Optuna 複勝モデル
- `phase14_feature_list.pkl` = 78特徴量リスト

---

### 2-6. 2026-03-08 ペーパートレード結果分析

**対象**: 阪神・中山 計20レース
**ベット方式**: Rule4（条件A + 条件B）、1点100円

| # | レース | 的中馬 | 条件 | pred | odds | 払戻 |
|---|--------|--------|------|------|------|------|
| 3R中山ダ1800 | 3歳未勝利 | **ホノボノ** | 条件B | 19.8% | 17.9倍 | 1,520円 |
| 5R阪神ダ1800 | 3歳1勝C | **ペンダント** | 条件B | 10.6% | 18.2倍 | 1,560円 |
| 7R中山芝1600 | 3歳1勝C | **ディールメーカー** | 条件A | 36.7% | 3.6倍 | 280円 |

| 指標 | 値 |
|------|---|
| 総ベット数（確定） | 44 |
| 的中数 | 3 |
| 的中率 | 6.8% |
| 投資額 | 4,400円 |
| 払戻合計 | 3,360円 |
| 純損益 | **-1,040円** |
| 当日ROI | **76.4%** |

> 注記: バリオス（弥生賞 pred=40.0% odds=17.4倍 条件B）が的中していれば+1,640円追加。
> 1日単位の損益より、統計的蓄積（目標ROI 180%）で評価すること。

---

## 3. 全フェーズ ROI 推移まとめ

| フェーズ | 特徴量数 | Val AUC | 2024 ROI | 2025 ROI |
|---------|---------|---------|---------|---------|
| Phase 14 ベースライン | 39 | 0.7988 | 139.1% | 154.8% |
| Phase R1 | 46 | 0.7997 | 142.1% | — |
| Phase R2-Optuna | 60 | 0.7656 | 148.0% | 174.7% |
| Phase R4 | 67 | 0.7858 | 157.3% | 197.9% |
| Phase R7+Optuna | 71 | 0.7875 | 161.1% | 186.4% |
| Phase R8 | 78 | 0.8245 | 176.1% | 180.4% |
| **Phase R8+Optuna ★現行** | **78** | **0.8256** | **179.8%** | **178.1%** |

---

## 4. 現状のステータス

```
ペーパートレード継続中（R8+Optunaモデルで運用）
開始バンクロール: 50,000円
2026-03-08時点バンクロール: 48,960円（-1,040円）
```

**GO/NO-GO 達成状況（2026-03-14時点）**

| 基準 | 目標 | 現状 | 達成 |
|------|------|------|------|
| ペーパートレード期間 | 8週間以上 | ~1週間 | ❌ |
| ベット件数 | 200件以上 | ~44件 | ❌ |
| 実績回収率 | 100%以上 | 76.4% | ❌ |
| 最大ドローダウン | 15%以内 | 2.1% | ✅ |
| 95% CI下限 | 損益分岐以上 | 要計算 | — |

> まだ1週間・44ベットのみ。継続が最優先。

---

## 5. 次のアクション

| 優先度 | タスク |
|--------|--------|
| ★最優先 | **ペーパートレード継続**（毎週末 自動実行） |
| 随時 | `py paper_trade_review.py` で月次レビュー |
| 短期検討 | Phase R9 候補: オッズドリフト特徴量（odds_timeseries.db活用） |
| 中期 | GO/NO-GO 5基準クリア後 → ライブトレード移行検討 |

---

## 6. 主要ファイル変更履歴（このセッション）

| ファイル | 変更種別 | 内容 |
|---------|---------|------|
| `calculate_features_r8.py` | 新規作成 | Phase R8 特徴量計算スクリプト |
| `train_phase_r8.py` | 新規作成 | Phase R8 モデル訓練スクリプト（Optuna対応） |
| `models/phase_r8/` | 新規作成 | R8+Optunaモデル一式 |
| `models/phase_r8_base/` | 新規作成 | R8（Optuna前）バックアップ |
| `models/phase_r8/sire_track_stats.json` | 新規作成 | 血統×競馬場勝率テーブル |
| `phase13_feature_engineering.py` | 修正 | R8特徴量計算追加（末尾セクション） |
| `phase14_model_win.txt` | 更新 | R8+Optunaモデルに更新 |
| `phase14_model_place.txt` | 更新 | R8+Optunaモデルに更新 |
| `phase14_feature_list.pkl` | 更新 | 78特徴量リストに更新 |
| `CLAUDE.md` | 修正 | R7数値訂正・R8結果追記・ステータス更新 |
| `analyze_mar8.py` | 新規作成 | 3/8レース別分析スクリプト |
