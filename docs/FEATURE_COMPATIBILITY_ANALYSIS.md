# 特徴量 互換性・品質分析レポート

**作成日**: 2026-03-05
**対象モデル**: Phase R2（64特徴量）
**ファイル**: `phase13_feature_engineering.py`

---

## 全64特徴量 一覧

凡例: ✅ 問題なし / ⚠️ 要注意 / ❌ 問題あり

---

### グループ1: 馬の基本成績（Phase 14 ベース・8個）

| # | 特徴量名 | 意味 | データソース | 状態 |
|---|---------|------|-------------|------|
| 1 | `total_starts` | 通算出走数 | DB `total_starts` or `len(horse_races)` | ✅ |
| 2 | `total_win_rate` | 通算勝率（全コース・全馬場の総合） | DB `total_win_rate` | ✅ |
| 3 | `total_earnings` | 通算獲得賞金 | DB `total_earnings` | ✅ |
| 4 | `turf_win_rate` | 芝での勝率（全期間・当該馬） | DB `turf_win_rate` | ⚠️ **DB集計値でリアルタイム計算ではない** |
| 5 | `dirt_win_rate` | ダートでの勝率（全期間・当該馬） | DB `dirt_win_rate` | ⚠️ **同上** |
| 6 | `distance_similar_win_rate` | 今回距離±200m以内の過去勝率 | `horse_races` 絞り込みで計算 | ✅ |
| 7 | `prev_race_rank` | 前走着順（数値。中止等は99） | `horse_races.iloc[-1]['rank']` | ✅ |
| 8 | `days_since_last_race` | 前走からの日数（休養・連闘の指標） | DB `days_since_last_race` | ⚠️ **DB集計値、未検証** |

> **注意**: `turf_win_rate` / `dirt_win_rate` / `days_since_last_race` はDBに事前集計されたカラムを参照。
> `calculate_features_standardized.py` 経由の場合、このカラムが標準化CSVに存在しない可能性があり、
> その場合 `latest.get('turf_win_rate', 0.0)` が常に 0.0 を返す。

---

### グループ2: 前走・レース傾向（Phase 14 ベース・3個）

| # | 特徴量名 | 意味 | データソース | 状態 |
|---|---------|------|-------------|------|
| 9  | `avg_passage_position` | 通過順の平均（脚質の粗い近似） | DB `avg_passage_position` | ⚠️ **DB集計値** |
| 10 | `avg_last_3f` | 上がり3Fタイム平均（秒） | DB `avg_last_3f` | ⚠️ **DB集計値・欠損多い可能性** |
| 11 | `grade_race_stars` | 重賞（G1/G2/G3）出走回数 | DB `grade_race_starts` | ✅ |

---

### グループ3: 血統・基本（Phase 14 ベース・4個）

| # | 特徴量名 | 意味 | データソース | 状態 |
|---|---------|------|-------------|------|
| 12 | `father_win_rate` | 父産駒の全体勝率（全コース・全距離の平均） | `sire_stats` 計算 | ✅ |
| 13 | `father_top3_rate` | 父産駒の全体複勝率 | `sire_stats` 計算 | ✅ |
| 14 | `mother_father_win_rate` | 母父産駒の全体勝率 | `sire_stats` 計算 | ✅ |
| 15 | `mother_father_top3_rate` | 母父産駒の全体複勝率 | `sire_stats` 計算 | ✅ |

---

### グループ4: 着差・脚質（Phase 14 ベース・6個）

| # | 特徴量名 | 意味 | データソース | 状態 |
|---|---------|------|-------------|------|
| 16 | `avg_diff_seconds` | 過去全レース着差の平均（秒換算） | `horse_races['着差']` から計算 | ✅ |
| 17 | `min_diff_seconds` | 過去最小着差（最も肉薄した着差） | 同上 | ✅ |
| 18 | `prev_diff_seconds` | 前走着差 | 同上（`latest['着差']`） | ✅ |
| 19 | `avg_first_corner` | 1コーナー平均通過順（小=前目） | `horse_races['通過']` パース | ✅ |
| 20 | `avg_last_corner` | 最終コーナー平均通過順 | 同上 | ✅ |
| 21 | `avg_position_change` | 1C〜最終Cの平均ポジション変化（正=後退、負=前進） | `avg_first_corner - avg_last_corner` | ⚠️ **符号に注意: 正=後退** |

---

### グループ5: クラス関連（Phase 14 ベース・2個）⚠️ 要注意

| # | 特徴量名 | 意味 | データソース | 状態 |
|---|---------|------|-------------|------|
| 22 | `class_change` | クラス変動 | **常に 0（未実装）** | ❌ **ノイズ** |
| 23 | `current_class` | 現在クラス | **常に 3（未実装）** | ❌ **ノイズ** |

> コード L407〜415 を確認すると、`if race_track:` の分岐で常に `0` / `3` が返される。
> `race_track` は競馬場名（track_name）であり、クラス情報ではないため、クラス計算が行われていない。
> LightGBM は定数列を無視するので実害は最小限だが、特徴量として意味をなしていない。

---

### グループ6: 調教師・騎手（Phase 14 ベース・6個）

| # | 特徴量名 | 意味 | データソース | 状態 |
|---|---------|------|-------------|------|
| 24 | `trainer_win_rate` | 調教師の全体勝率 | `trainer_jockey_stats` | ✅ |
| 25 | `trainer_top3_rate` | 調教師の全体複勝率 | 同上 | ✅ |
| 26 | `trainer_starts` | 調教師の出走数（信頼性指標） | 同上 | ✅ |
| 27 | `jockey_win_rate` | 騎手の全体勝率（全競馬場合算） | 同上 | ✅ |
| 28 | `jockey_top3_rate` | 騎手の全体複勝率 | 同上 | ✅ |
| 29 | `jockey_starts` | 騎手の出走数（信頼性指標） | 同上 | ✅ |

---

### グループ7: コース・馬場・枠（Phase 14 ベース・8個）

| # | 特徴量名 | 意味 | データソース | 状態 |
|---|---------|------|-------------|------|
| 30 | `track_win_rate` | 当該馬の今回競馬場での過去勝率 | `horse_races` 競馬場絞り込み | ✅ |
| 31 | `track_top3_rate` | 当該馬の今回競馬場での過去複勝率 | 同上 | ✅ |
| 32 | `race_distance` | レース距離（m） | 引数 `race_distance` | ✅ |
| 33 | `is_turf` | 芝フラグ（0/1） | 引数 `race_course_type` | ✅ |
| 34 | `is_dirt` | ダートフラグ（0/1） | 同上 | ✅ |
| 35 | `is_良` | 良馬場フラグ | 引数 `race_track_condition` | ✅ |
| 36 | `is_稍重` | 稍重フラグ | 同上 | ✅ |
| 37 | `is_重` | 重馬場フラグ | 同上 | ✅ |
| 38 | `is_不良` | 不良馬場フラグ | 同上 | ✅ |
| 39 | `frame_number` | 枠番（1〜8） | 引数 `current_frame` | ✅ |

> `is_turf`/`is_dirt` と `is_良`〜`is_不良` は同時に複数が1になり得ない排他的フラグ。
> 合計でも 10個（行数注記ずれ修正: 32〜39は8個）。

---

### グループ8: Phase R1 追加特徴量（7個）

| # | 特徴量名 | 意味 | データソース | 状態 |
|---|---------|------|-------------|------|
| 40 | `heavy_track_win_rate` | 重・不良馬場での過去勝率 | `horse_races` 馬場絞り込みで計算 | ✅ |
| 41 | `distance_change` | 今回距離 − 前走距離（m） | `race_distance - latest['distance']` | ✅ |
| 42 | `kiryou` | 斤量（kg）今回レースのもの | 引数 `horse_kiryou` | ✅ |
| 43 | `is_female` | 牝馬フラグ（牝=1、それ以外=0） | 引数 `horse_seire` からパース | ✅ |
| 44 | `horse_age` | 馬齢（歳） | 引数 `horse_seire` からパース | ✅ |
| 45 | `horse_weight` | 馬体重（kg） | 引数 `horse_weight_str` からパース | ✅ |
| 46 | `weight_change` | 馬体重増減（前走比・kg） | 同上 or DB `horse_weight` との差分 | ⚠️ **DB経由の場合のみ前走比計算。GUIは "460(+2)" 形式** |

---

### グループ9: Phase R2 追加特徴量・血統細分化（10個）

| # | 特徴量名 | 意味 | データソース | 状態 |
|---|---------|------|-------------|------|
| 47 | `father_turf_win_rate` | 父産駒の芝限定勝率 | `sire_stats` 芝データ絞り込み | ✅ |
| 48 | `father_dirt_win_rate` | 父産駒のダート限定勝率 | 同上 | ✅ |
| 49 | `father_heavy_win_rate` | 父産駒の道悪（重・不良）限定勝率 | 同上 | ✅ |
| 50 | `father_short_win_rate` | 父産駒の短距離（≤1400m）限定勝率 | 同上 | ✅ |
| 51 | `father_long_win_rate` | 父産駒の長距離（≥2000m）限定勝率 | 同上 | ✅ |
| 52 | `mother_father_turf_win_rate` | 母父産駒の芝限定勝率 | 同上 | ✅ |
| 53 | `mother_father_dirt_win_rate` | 母父産駒のダート限定勝率 | 同上 | ✅ |
| 54 | `mother_father_heavy_win_rate` | 母父産駒の道悪限定勝率 | 同上 | ✅ |
| 55 | `mother_father_short_win_rate` | 母父産駒の短距離限定勝率 | 同上 | ✅ |
| 56 | `mother_father_long_win_rate` | 母父産駒の長距離限定勝率 | 同上 | ✅ |

> C-1 系は `father_win_rate`（全体）の加重平均を細分化したもの。
> **既存の `father_win_rate` との相関が高い**が、情報の細分化なので冗長性ではなく補完関係。
> ただし `is_turf`/`is_dirt` フラグと組み合わせると同じ情報（芝ならturf_win_rateが有効）を
> 2系統（レース条件フラグ × 血統勝率）で持つことになる。LightGBMは交互作用を捉えるので問題は少ない。

---

### グループ10: Phase R2 追加特徴量・脚質・騎手・適性（8個）

| # | 特徴量名 | 意味 | データソース | 状態 |
|---|---------|------|-------------|------|
| 57 | `running_style` | 脚質カテゴリ（1逃/2先/3差/4追） | `avg_first_corner`, `avg_last_corner` から分類 | ⚠️ **後述** |
| 58 | `recent_3race_improvement` | 直近3走の着順改善量（最古−最新。正=上昇傾向） | `horse_races.tail(3)` | ⚠️ **後述** |
| 59 | `jockey_track_win_rate` | 騎手×競馬場の特化勝率 | `jockey_track` stats / フォールバック: `jockey_win_rate` | ⚠️ **後述** |
| 60 | `jockey_track_top3_rate` | 騎手×競馬場の特化複勝率 | 同上 | ⚠️ **同上** |
| 61 | `good_track_win_rate` | 良馬場での過去勝率 | `horse_races` 良馬場絞り込み | ✅ |
| 62 | `class_adjusted_diff` | クラス補正済み着差 | `avg_diff_seconds × (cur_class/prev_class)` | ❌ **後述** |
| 63 | `pace_preference` | ペース傾向 | `avg_position_change` と**完全同値** | ❌ **完全重複** |
| 64 | `finish_strength` | 末脚強度（3ポジション以上前進した割合） | `horse_races['通過']` 再パース | ✅ |

---

## 問題特徴量の詳細

### ❌ #63 `pace_preference` — 完全重複（最重大）

```python
# コード L392
features['pace_preference'] = features.get('avg_position_change', 0.0)
```

`avg_position_change` と**完全に同じ値**。LightGBMに同一列が2本入っている状態。
- 機械学習的影響: `avg_position_change` の特徴量重要度が実質2倍に水増しされる
- AUC後退の一因と推定される
- **対処**: `pace_preference` を削除するか、別の計算（first_3f/last_3f 比など）に差し替える

---

### ❌ #62 `class_adjusted_diff` — 標準化CSVでは `avg_diff_seconds` と同値

```python
# コード L351-354
_cur_cls  = extract_race_class(str(_cur_race_name))   # race_nameがなければ 0
_prev_cls = extract_race_class(str(latest.get('race_name', '')))
_cls_ratio = (_cur_cls / _prev_cls) if (_cur_cls > 0 and _prev_cls > 0) else 1.0  ← 0/0 → 1.0
features['class_adjusted_diff'] = features.get('avg_diff_seconds', 1.0) * _cls_ratio
```

`calculate_features_standardized.py` が生成するCSVに `race_name` 列が含まれない場合、
`_cur_race_name = ''` → `_cur_cls = 0` → `_cls_ratio = 1.0` → `class_adjusted_diff = avg_diff_seconds`。
**訓練データの大半で `avg_diff_seconds` と同値になっている可能性が高い。**

- **確認**: `data/phase14/train_features.csv` の `class_adjusted_diff` と `avg_diff_seconds` を比較
- **対処**: `race_name` 列が存在しないならこの特徴量は削除

---

### ⚠️ #57 `running_style` — 既存3特徴量から派生（高相関）

```python
if _fc <= 2.5:   running_style = 1  # 逃げ
elif _fc <= 4.5: running_style = 2  # 先行
elif _lc < _fc - 1.5: running_style = 3  # 差し
else:            running_style = 4  # 追込
```

`avg_first_corner`（#19）と `avg_last_corner`（#20）の**閾値ビニング**。
同一情報を連続値とカテゴリ値の両形式で持つ。
LightGBMは一般に連続値の方が効率的に利用できるため、追加効果は限定的。
ただし冗長性はあるが矛盾はない。

---

### ⚠️ #58 `recent_3race_improvement` — 符号の解釈注意

```python
features['recent_3race_improvement'] = float(
    _fin['rank_num'].iloc[0] - _fin['rank_num'].iloc[-1]
)
```

`tail(3)` を使うと `iloc[0]` = **3走前**、`iloc[-1]` = **直近**。
→ `3走前の着順 - 直近の着順` = **正 = 改善（着順が小さくなった）**。
解釈自体は正しいが、`recent_trend（ROADMAPの旧称）`と比べると直感的でない。
`prev_race_rank`（#7）との高相関にも注意。

---

### ⚠️ #59/#60 `jockey_track_win_rate/top3_rate` — 大半が `jockey_win_rate` に縮退

```python
if _jt_key and _jt_key in _jt_stats:
    features['jockey_track_win_rate'] = _jt_stats[_jt_key]['win_rate']
else:
    features['jockey_track_win_rate'] = features.get('jockey_win_rate', 0.0)  # フォールバック
```

訓練データにない騎手×競馬場コンビは全て `jockey_win_rate` と**同値**になる。
これが全データのうち何割かは未検証。未知コンビ率が高ければ `jockey_win_rate`（#27）の重複になる。

---

### ❌ #22/#23 `class_change`/`current_class` — 常に定数（Phase 14 からの既存バグ）

```python
# コード L411-415: race_track は競馬場名。クラス計算コードなし
if race_track:
    features['class_change'] = 0
    features['current_class'] = 3
```

`race_track` 引数はクラス名ではなく競馬場名（例: "東京"）のため、
実質的にすべてのレコードで `class_change=0`, `current_class=3` の定数列。
LightGBMは定数列を特徴量重要度=0として扱うので**実害はほぼない**が、無駄な列。

---

## 相関・冗長マップ

```
【脚質グループ — 5特徴量が同一ソースから派生】
avg_first_corner ──┬──> avg_position_change ──> pace_preference (完全重複❌)
avg_last_corner  ──┘──> running_style (ビニング⚠️)
                         avg_position_change (連続値)

【騎手グループ — フォールバック冗長】
jockey_win_rate ──────> jockey_track_win_rate (未知コンビは同値⚠️)
jockey_top3_rate ─────> jockey_track_top3_rate (同上⚠️)

【着差グループ — 縮退冗長】
avg_diff_seconds ─────> class_adjusted_diff (race_name欠損時は同値❌)

【血統グループ — 細分化の内部相関は許容範囲】
father_win_rate ──┬── father_turf_win_rate
                  ├── father_dirt_win_rate
                  ├── father_heavy_win_rate   ← 細分化は有益
                  ├── father_short_win_rate
                  └── father_long_win_rate

【馬場適性 — 補完関係】
heavy_track_win_rate  ←→ good_track_win_rate (相反だが補完✅)
is_重/is_不良          ←→ is_良 (フラグ列との交互作用)
```

---

## サマリー評価

| 問題レベル | 件数 | 対象特徴量 |
|---------|------|---------|
| ❌ 削除/修正必須 | 4 | `pace_preference`, `class_adjusted_diff`（縮退時）, `class_change`, `current_class` |
| ⚠️ 要確認 | 5 | `running_style`, `jockey_track_*×2`, `recent_3race_improvement`, `weight_change`（DB経由） |
| ⚠️ DB依存で欠損リスク | 3 | `turf_win_rate`, `dirt_win_rate`, `avg_last_3f` |
| ✅ 問題なし | 52 | 残り |

---

## 相性が悪い可能性のある組み合わせ

| 組み合わせ | 問題の種類 | 推奨対処 |
|---------|---------|---------|
| `avg_position_change` + `pace_preference` | 完全重複 → 重要度水増し | `pace_preference` を削除 |
| `avg_diff_seconds` + `class_adjusted_diff` | 縮退時に重複 | `race_name` 有無を確認して決定 |
| `avg_first_corner`/`avg_last_corner` + `running_style` | 連続値とビニングの二重表現 | どちらか一方（連続値優先） |
| `jockey_win_rate` + `jockey_track_win_rate` | 未知コンビで重複 | フォールバック値を 0.0 に変更するか削除 |
| `is_重`/`is_不良` + `heavy_track_win_rate` + `father_heavy_win_rate` | 同一条件の3重表現 | 許容範囲だが過多 |

---

## 次フェーズへの推奨アクション

### Step 1: 即時削除（1件確実）
```
pace_preference を特徴量リストから除外（avg_position_changの完全重複）
```

### Step 2: 実態確認（CSVを見て判断）
```python
import pandas as pd
df = pd.read_csv('data/phase14/train_features.csv')
print((df['class_adjusted_diff'] == df['avg_diff_seconds']).mean())  # 1.0 なら削除
print((df['jockey_track_win_rate'] == df['jockey_win_rate']).mean())  # 高ければフォールバック改善
```

### Step 3: 部分特徴量セットでの実験候補

| セット名 | 内容 | 目的 |
|---------|------|------|
| **A: ベース39のみ** | Phase14ベース（`class_change`/`current_class`除く37） | 基準値再確認 |
| **B: ベース + R1** | 37 + 7 = 44特徴量 | R1の純寄与確認 |
| **C: ベース + R1 + C-1血統のみ** | 44 + 10 = 54特徴量 | 血統細分化の寄与確認 |
| **D: 重複除去R2** | 64 − 4（重複・バグ） = 60特徴量 | 現状の最善 |

---

*Generated by Claude Sonnet 4.6 on 2026-03-05*
