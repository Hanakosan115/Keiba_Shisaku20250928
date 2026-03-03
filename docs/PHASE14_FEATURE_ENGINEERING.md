# Phase 14 — Feature Engineering Reference

> Last updated: 2026-03-04
> Model: LightGBM Booster (win AUC 0.7988 / place AUC 0.7558)
> Training: 2020–2022 | Validation: 2023 | OOS Test: 2024–2025

---

## 1. Currently Used Features (39)

### 1-1. Horse Career Stats (5)

| Feature | Description |
|---------|-------------|
| `total_starts` | 通算出走数 |
| `total_win_rate` | 通算勝率 |
| `total_earnings` | 通算獲得賞金 |
| `turf_win_rate` | 芝勝率（全場・全距離） |
| `dirt_win_rate` | ダート勝率（全場・全距離） |

**問題点**: `turf_win_rate` / `dirt_win_rate` は距離・馬場状態を区別しない粗い集計値。

---

### 1-2. Distance & Recent Race (4)

| Feature | Description |
|---------|-------------|
| `distance_similar_win_rate` | 同距離帯（±200m）勝率 |
| `prev_race_rank` | 前走着順 |
| `days_since_last_race` | 前走からの日数 |
| `grade_race_starts` | 重賞出走数（クラス実績指標） |

---

### 1-3. Running Style & Pace (5)

| Feature | Description | Source column |
|---------|-------------|---------------|
| `avg_passage_position` | 平均道中通過順 | `通過` を parse して平均 |
| `avg_first_corner` | 平均1角通過順 | `通過` の1要素目 |
| `avg_last_corner` | 平均最終角通過順 | `通過` の最終要素 |
| `avg_position_change` | 平均順位変化（1角→最終） | 上記の差分 |
| `avg_last_3f` | 平均上がり3F タイム | `上がり` 列 |

**問題点**: `通過` 列から算出した数値統計のみ使用。脚質カテゴリ（逃げ/先行/差し/追込）は未使用。

---

### 1-4. Margin (3)

| Feature | Description |
|---------|-------------|
| `avg_diff_seconds` | 平均着差（秒換算） |
| `min_diff_seconds` | 最小着差（勝ち方の強さ指標） |
| `prev_diff_seconds` | 前走着差 |

---

### 1-5. Bloodline (4)

| Feature | Description | Source column |
|---------|-------------|---------------|
| `father_win_rate` | 父産駒の全体勝率 | `father` → `calculate_sire_stats()` |
| `father_top3_rate` | 父産駒の全体複勝率 | 同上 |
| `mother_father_win_rate` | 母父産駒の全体勝率 | `mother_father` → 同上 |
| `mother_father_top3_rate` | 母父産駒の全体複勝率 | 同上 |

**問題点**: 芝/ダート・距離帯・馬場状態を区別しない全体平均のみ。血統の本質的な得意条件が反映されない。

---

### 1-6. Class (2)

| Feature | Description |
|---------|-------------|
| `class_change` | クラス変化（昇降級フラグ） |
| `current_class` | 現クラス（数値） |

---

### 1-7. Trainer (3)

| Feature | Description |
|---------|-------------|
| `trainer_win_rate` | 調教師の全体勝率 |
| `trainer_top3_rate` | 調教師の全体複勝率 |
| `trainer_starts` | 調教師の出走数（サンプル規模） |

---

### 1-8. Jockey (3)

| Feature | Description |
|---------|-------------|
| `jockey_win_rate` | 騎手の全体勝率 |
| `jockey_top3_rate` | 騎手の全体複勝率 |
| `jockey_starts` | 騎手の出走数（サンプル規模） |

---

### 1-9. Course Affinity (2)

| Feature | Description |
|---------|-------------|
| `track_win_rate` | 同競馬場での過去勝率 |
| `track_top3_rate` | 同競馬場での過去複勝率 |

---

### 1-10. Race Conditions (8)

| Feature | Description |
|---------|-------------|
| `race_distance` | レース距離（m） |
| `is_turf` | 芝フラグ |
| `is_dirt` | ダートフラグ |
| `is_良` | 良馬場フラグ |
| `is_稍重` | 稍重馬場フラグ |
| `is_重` | 重馬場フラグ |
| `is_不良` | 不良馬場フラグ |
| `frame_number` | 枠番（1–8） |

**問題点**: 馬場状態は one-hot フラグのみ。「この馬が道悪で強いか」という馬場適性は別途必要。

---

## 2. DB Columns Available but Unused

DB には 57 カラムが収録されている。以下は現在の 39 特徴量に含まれていない列。

### 2-1. Running Style / Pace （展開・ペース系）

| Column | Values (example) | Notes |
|--------|-----------------|-------|
| `running_style_category` | `front_runner`, `stalker`, `midpack`, `closer` | 脚質カテゴリ。計算済み列として存在 |
| `pace_category` | `fast`, `medium`, `slow` | ペースカテゴリ |
| `first_3f_avg` | `12.3`（秒） | 前半3F平均タイム |
| `last_3f_avg` | `11.8`（秒） | 後半3F平均タイム |
| `pace_variance` | 数値 | ラップ分散（ペースの波） |
| `pace_acceleration` | 数値 | ラップ加速度（前傾/後傾） |

### 2-2. Track Condition Affinity （馬場適性系）

| Column | Values (example) | Notes |
|--------|-----------------|-------|
| `heavy_track_win_rate` | `0.12` | 道悪（重・不良）での過去勝率。**DBカラムとして計算済み** |
| `weather` | `晴`, `曇`, `雨`, `雪` | 天気 |

### 2-3. Horse Physical （馬体系）

| Column | Values (example) | Notes |
|--------|-----------------|-------|
| `馬体重` | `460(+2)` | 馬体重と前走比増減。parse が必要 |
| `斤量` | `56.0`（kg） | 負担重量。直接数値として利用可能 |
| `性齢` | `牡3`, `牝5` | 性別・年齢。parse で分離可能 |

### 2-4. Bloodline Detail （血統詳細系）

| Computable from | Feature idea | Notes |
|----------------|--------------|-------|
| `father` + `course_type` | 父産駒の芝/ダート別勝率 | `calculate_sire_stats()` を拡張 |
| `father` + `distance` | 父産駒の距離帯別勝率（短/中/長） | 同上 |
| `father` + `track_condition` | 父産駒の道悪勝率 | 同上 |
| `mother_father` + `course_type` | 母父産駒の芝/ダート別勝率 | 同上 |

### 2-5. Race History （前走・距離系）

| Column | Values (example) | Notes |
|--------|-----------------|-------|
| `prev_race_distance` | `1600`（m） | 前走距離。距離延長/短縮の計算に使える |
| `is_local_transfer` | `0`, `1` | 地方転入フラグ |

### 2-6. Training （調教系）

| Column | Values (example) | Notes |
|--------|-----------------|-------|
| `training_rank` | 数値 or カテゴリ | 調教評価ランク |
| `training_critic` | 数値 | 調教評価スコア |

---

## 3. Proposed New Features — Priority Ranking

### Priority A: 即時追加可能（DB列をほぼそのまま利用、計算コスト低）

| Feature | Derived from | Expected impact |
|---------|-------------|-----------------|
| `heavy_track_win_rate` | DBカラムそのまま | 道悪レースで大きく寄与 ★★★ |
| `kiryou` （斤量） | `斤量` 列そのまま | 軽量・牝馬斤量差で寄与 ★★☆ |
| `horse_weight` | `馬体重` をparse | 馬格情報 ★★☆ |
| `weight_change` | `馬体重` をparse | 仕上がり度合い ★★☆ |
| `sex_flag` | `性齢` をparse | 牝馬の距離・馬場傾向 ★★☆ |
| `horse_age` | `性齢` をparse | 3–5歳ピーク効果 ★★☆ |
| `distance_change` | `prev_race_distance` との差 | 延長/短縮（±400m以上で有効） ★★☆ |

---

### Priority B: 計算追加が必要（集計処理あり、実装1–2日）

| Feature | Derived from | Expected impact |
|---------|-------------|-----------------|
| `running_style_score` | `running_style_category` の最頻値を数値化 | 脚質傾向の数値表現 ★★★ |
| `preferred_pace_score` | `pace_category` × 過去成績の組み合わせ | 好ペース適性 ★★☆ |
| `recent_trend` | 直近3走の着順の線形傾向 | 調子の上昇/下降 ★★☆ |
| `jockey_track_win_rate` | 騎手 × 競馬場 の組み合わせ勝率 | 得意コースの騎手 ★★☆ |
| `track_condition_win_rate` | 馬場状態（良/道悪）ごとの過去勝率 | 馬場適性の定量化 ★★★ |

---

### Priority C: 血統の細分化（`calculate_sire_stats()` 拡張、実装2–3日）

| Feature | Description | Expected impact |
|---------|-------------|-----------------|
| `father_turf_win_rate` | 父産駒の芝勝率 | 現在の `father_win_rate` より精度高 ★★★ |
| `father_dirt_win_rate` | 父産駒のダート勝率 | 同上 ★★★ |
| `father_heavy_win_rate` | 父産駒の道悪勝率 | 道悪レースで特に有効 ★★★ |
| `father_dist_short_win_rate` | 父産駒の短距離（〜1400m）勝率 | ★★☆ |
| `father_dist_long_win_rate` | 父産駒の長距離（2000m〜）勝率 | ★★☆ |
| `mother_father_turf_win_rate` | 母父産駒の芝勝率 | ★★☆ |
| `mother_father_dirt_win_rate` | 母父産駒のダート勝率 | ★★☆ |

> 実装方針: `calculate_sire_stats(df)` に `course_type` / `track_condition` / distance_band の groupby を追加し、辞書を拡張する。

---

### Priority D: 展開スコア（レース全体情報が必要、実装難易度高）

| Feature | Description | Difficulty |
|---------|-------------|------------|
| `pace_scenario_score` | このレースの逃げ馬頭数から前後半ペースを推定し、各脚質との相性をスコア化 | 他馬情報が必要 ★ |
| `front_runner_count` | このレースの逃げ・先行馬の頭数 | レース単位の集計 ★ |

> **注意**: 展開スコアは「このレースの出走馬全体」を見る必要があるため、現在の馬単位の特徴量計算フローとは別処理が必要。バックテストのリーケージ防止にも注意が必要。

---

## 4. Implementation Notes

### Leakage Prevention Rule

```python
# calculate_horse_features_safe() 内
horse_races = df_all[
    (df_all['horse_id'] == horse_id_num) &
    (df_all['race_id'] != race_id_int) &   # 当該レース除外
    (df_dates < cutoff_dt)                  # current_date 以前のデータのみ
]
```

新規特徴量を追加する際も、必ず `horse_races`（リーケージ防止済みのスライス）から計算すること。

### Where to Add Features

| Task | File |
|------|------|
| 特徴量計算ロジック追加 | `phase13_feature_engineering.py` — `calculate_horse_features_safe()` |
| 種牡馬統計の拡張 | `phase13_feature_engineering.py` — `calculate_sire_stats()` |
| 訓練データの特徴量再計算 | `phase13_calculate_all_features.py` |
| モデル再訓練 | `phase13_train_model.py` |
| GUI 日本語名追加 | `keiba_prediction_gui_v3.py` — `FEATURE_NAMES_JP` (L.85–125) |
| SHAP 日本語名追加 | `keiba_prediction_gui_v3.py` — `FEATURE_NAMES_JP` |

### Recommended Implementation Order

```
Step 1: Priority A（DB列をそのまま追加）
        → backtest で AUC・ROI の変化を確認
Step 2: Priority C（血統細分化）
        → calculate_sire_stats() を拡張して再訓練
Step 3: Priority B（集計特徴量）
        → 脚質スコア・騎手×コース等を追加して再訓練
Step 4: Priority D（展開スコア）
        → データ構造の変更が必要なため最後に検討
```

---

## 5. Feature Count Projection

| Phase | Features | Win AUC (est.) | Notes |
|-------|----------|---------------|-------|
| Phase 14 (current) | 39 | 0.7988 | OOS confirmed |
| +Priority A | 39 + 7 = 46 | 0.800–0.803 | DB columns, no retraining of pipeline |
| +Priority C | 46 + 7 = 53 | 0.803–0.808 | Requires `calculate_sire_stats()` extension |
| +Priority B | 53 + 5 = 58 | 0.805–0.810 | Requires aggregation logic |
| +Priority D | 58 + 2 = 60 | TBD | Requires architecture change |

> AUC の競馬公開データでの実質上限: **0.81 前後**

---

*Reference: `phase13_feature_engineering.py` — `calculate_horse_features_safe()` / `calculate_sire_stats()`*
