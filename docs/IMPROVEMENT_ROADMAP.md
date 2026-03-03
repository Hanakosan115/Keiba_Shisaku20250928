# 的中率改善 — Implementation Roadmap

> Goal: 的中率の最大化（実装コスト問わず）
> Baseline: Rule4 的中率 16.3%（条件A 36.7% / 条件B 8.7%）、ROI 139.1%（2024 OOS）
> Last updated: 2026-03-04

---

## 0. 全改善案サマリー

| ID | 改善案 | 的中率↑ | ROI↑ | 難易度 | グループ |
|----|--------|--------|------|--------|---------|
| A-1 | 閾値引き上げ（pred_win 条件強化） | ↑↑↑ | △要確認 | ★ | ベット選択 |
| A-2 | 予測1位との確率差フィルター | ↑↑ | ↑ | ★ | ベット選択 |
| A-3 | Isotonic Regressionキャリブレーション | ↑ | ↑ | ★★ | ベット選択 |
| B-1 | heavy_track_win_rate（道悪勝率）追加 | ↑ | ↑ | ★ | 特徴量追加 |
| B-2 | 斤量追加 | ↑ | ↑ | ★ | 特徴量追加 |
| B-3 | 性別フラグ・馬齢追加 | ↑ | ↑ | ★ | 特徴量追加 |
| B-4 | 馬体重・増減追加 | ↑ | ↑ | ★ | 特徴量追加 |
| B-5 | 前走距離差追加 | ↑ | ↑ | ★ | 特徴量追加 |
| B-6 | 脚質カテゴリ（running_style）数値化 | ↑↑ | ↑↑ | ★★ | 特徴量追加 |
| B-7 | 直近3走トレンド（着順上昇/下降） | ↑↑ | ↑↑ | ★★ | 特徴量追加 |
| B-8 | 騎手 × 競馬場 組み合わせ勝率 | ↑↑ | ↑↑ | ★★ | 特徴量追加 |
| B-9 | 馬場状態別勝率（良/道悪ごと） | ↑↑ | ↑↑ | ★★ | 特徴量追加 |
| C-1 | 血統 × 芝/ダート 別勝率（父/母父） | ↑↑↑ | ↑↑↑ | ★★ | 新規情報生成 |
| C-2 | 血統 × 道悪/距離帯 別勝率 | ↑↑↑ | ↑↑↑ | ★★ | 新規情報生成 |
| C-3 | スピード指数（タイムをコース・馬場補正） | ↑↑↑ | ↑↑↑ | ★★★ | 新規情報生成 |
| C-4 | クラス強度補正マージン | ↑↑ | ↑↑ | ★★ | 新規情報生成 |
| C-5 | 相対ペース指数（前半/後半比） | ↑↑ | ↑↑ | ★★ | 新規情報生成 |
| C-6 | 展開スコア（レース全体の脚質構成） | ↑↑↑ | ↑↑↑ | ★★★★ | 新規情報生成 |
| D-1 | 訓練データに2023年追加 | ↑ | ↑ | ★ | データ改善 |
| D-2 | 直近データへの重み付け | ↑ | ↑ | ★★ | データ改善 |
| D-3 | ハイパーパラメータ再チューニング（Optuna） | ↑ | ↑ | ★★ | モデル改善 |
| D-4 | アンサンブル（LGB + XGB + CatBoost） | ↑↑ | ↑↑ | ★★★ | モデル改善 |
| D-5 | ランク学習（Learning to Rank） | ↑↑↑ | ↑↑↑ | ★★★ | モデル改善 |
| D-6 | コース種別・距離帯別モデル分離 | ↑↑↑ | ↑↑↑ | ★★★ | モデル改善 |
| D-7 | Neural Network ハイブリッド | ↑↑↑ | ↑↑↑ | ★★★★★ | モデル改善 |

---

## Group A: ベット選択の最適化

> モデルは変えずに「何を買うか」だけを変える。最速で的中率が変わる。

### A-1: 閾値引き上げ

```
現在:  条件A: pred_win ≥ 20% & odds 2–10x
       条件B: pred_win ≥ 10% & odds ≥ 10x

案:    条件A: pred_win ≥ 25–30%
       条件B: pred_win ≥ 12–15%
```

- **的中率への効果**: 条件Aなら36.7% → 推定45–50%+
- **トレードオフ**: ベット件数が半減する可能性。ROIは上がるが年間絶対利益は減るかもしれない
- **検証**: `backtest_threshold_search.py` を作成して2024/2025 OOS で全パターンを探索

### A-2: 確率差フィルター

```python
# 1位と2位の予測確率の差が5%以上のときのみベット
margin = pred_df.iloc[0]['勝率予測'] - pred_df.iloc[1]['勝率予測']
if margin >= 0.05:
    bet()
```

- **狙い**: 「この馬が圧倒的に強い」局面に絞る
- **的中率**: ↑↑ 単純な閾値引き上げより精密な絞り込みができる

### A-3: Isotonic Regressionキャリブレーション

LightGBM の出力確率はそのままでは真の的中率とずれている（過大/過小評価）。

```python
from sklearn.isotonic import IsotonicRegression

# 検証データ（2023年）でキャリブレーション
ir = IsotonicRegression(out_of_bounds='clip')
ir.fit(pred_win_val, true_win_val)

# 推論時に補正
calibrated_prob = ir.predict(raw_prob)
```

- **効果**: 予測確率が「pred_win = 30% と言ったら実際に30%勝つ」状態になる
- **閾値の意味が正確になる** → A-1/A-2と組み合わせると相乗効果

---

## Group B: 特徴量追加（DBに既存・コスト低）

> `phase13_feature_engineering.py` の `calculate_horse_features_safe()` に追記するだけ。

### B-1〜B-5: 即時追加可能（★）

```python
# B-1: heavy_track_win_rate（DBカラムそのまま）
heavy_races = horse_races[horse_races['track_condition'].isin(['重', '不良'])]
features['heavy_track_win_rate'] = (heavy_races['着順'] == 1).mean()

# B-2: 斤量
features['kiryou'] = float(race_info.get('斤量', 55))

# B-3: 性別・馬齢（"牡3" → sex=1, age=3）
seire = horse.get('性齢', '')
features['is_female'] = 1 if seire.startswith('牝') else 0
features['horse_age'] = int(re.search(r'\d+', seire).group()) if seire else 0

# B-4: 馬体重・増減（"460(+2)" → weight=460, change=+2）
weight_str = horse.get('馬体重', '')
m = re.match(r'(\d+)\(([+-]?\d+)\)', weight_str)
if m:
    features['horse_weight'] = int(m.group(1))
    features['weight_change'] = int(m.group(2))

# B-5: 前走距離差
prev_dist = horse_races.sort_values('date').iloc[-1]['distance'] if len(horse_races) > 0 else 0
features['distance_change'] = race_distance - prev_dist
```

### B-6: 脚質カテゴリ数値化（★★）

```python
# running_style_category の最頻値を数値化
style_map = {'front_runner': 1, 'stalker': 2, 'midpack': 3, 'closer': 4}
style_series = horse_races['running_style_category'].map(style_map).dropna()
features['running_style'] = style_series.mode()[0] if len(style_series) > 0 else 0

# 現在の脚質スコア（直近5走の平均通過順位 ≒ 脚質）
# avg_passage_position として既に存在するが、カテゴリ情報を追加することで質が上がる
```

**なぜ有効か**: 逃げ馬が多いレースに差し馬を買っても当たらない。脚質の数値化は展開予測の第一歩。

### B-7: 直近3走トレンド（★★）

```python
recent = horse_races.sort_values('date').tail(3)['着順'].tolist()
if len(recent) >= 2:
    # 正 = 着順改善（上昇傾向）、負 = 着順悪化（下降傾向）
    features['recent_trend'] = recent[0] - recent[-1]  # or linear regression slope
else:
    features['recent_trend'] = 0
```

### B-8: 騎手 × 競馬場 組み合わせ勝率（★★）

```python
# calculate_trainer_jockey_stats() を拡張
# jockey × track_name のグループ集計を追加
j_track = df.groupby(['騎手', 'track_name']).apply(
    lambda g: pd.Series({
        'jockey_track_win_rate': (g['着順'] == 1).mean(),
        'jockey_track_top3_rate': (g['着順'] <= 3).mean(),
    })
).reset_index()
```

**なぜ有効か**: 東京が得意な騎手、中山が得意な騎手は存在する。全体勝率より精密。

### B-9: 馬場状態別適性（★★）

```python
# 良/道悪での個別勝率を追加（現在の is_良 フラグより情報量多）
good_races = horse_races[horse_races['track_condition'] == '良']
features['good_track_win_rate'] = (good_races['着順'] == 1).mean() if len(good_races) > 0 else 0

heavy_races = horse_races[horse_races['track_condition'].isin(['重', '不良'])]
features['heavy_track_win_rate'] = (heavy_races['着順'] == 1).mean() if len(heavy_races) > 0 else 0
```

---

## Group C: 新規情報の生成

> DBを加工・変換して「現在の特徴量では表現できない情報」を作る。最もインパクト大。

### C-1 / C-2: 血統の細分化（★★ — 最重要）

**問題**: 現在の `father_win_rate` は「全場・全距離・全馬場」の平均。芝が得意/ダートが得意という情報が落ちている。

```python
# calculate_sire_stats(df) を拡張
def calculate_sire_stats(df):
    sire_stats = {}
    for father, group in df.groupby('father'):
        turf = group[group['course_type'] == '芝']
        dirt = group[group['course_type'] == 'ダート']
        heavy = group[group['track_condition'].isin(['重', '不良'])]
        short = group[group['distance'] <= 1400]
        long_ = group[group['distance'] >= 2000]

        sire_stats[father] = {
            'win_rate':          (group['着順'] == 1).mean(),    # 既存
            'top3_rate':         (group['着順'] <= 3).mean(),    # 既存
            'turf_win_rate':     (turf['着順'] == 1).mean(),     # 新規★
            'dirt_win_rate':     (dirt['着順'] == 1).mean(),     # 新規★
            'heavy_win_rate':    (heavy['着順'] == 1).mean(),    # 新規★
            'short_win_rate':    (short['着順'] == 1).mean(),    # 新規★
            'long_win_rate':     (long_['着順'] == 1).mean(),    # 新規★
        }
    return sire_stats

# → 同様に mother_father も拡張
# 追加特徴量: father_turf_win_rate, father_dirt_win_rate,
#             father_heavy_win_rate, father_short_win_rate, father_long_win_rate,
#             mother_father_turf_win_rate, mother_father_dirt_win_rate
```

**期待効果**: 「ディープインパクト産駒は芝中距離が強い」「ゴールドアリュール産駒はダートが強い」という情報をモデルが直接学習できるようになる。的中率への寄与が最も大きい改善の一つ。

### C-3: スピード指数（Speed Figure）（★★★ — 最大のポテンシャル）

**問題**: 現在の `avg_last_3f`（平均上がり3F）や `avg_diff_seconds`（着差）は距離・馬場・クラスが違う比較ができない。

```python
def calculate_speed_figure(time_seconds, distance, course_type, track_condition, class_level):
    """
    生タイムを「距離・馬場・コース・クラス」で補正してスピード指数に変換

    引数:
        time_seconds: レースタイム（秒）
        distance: 距離（m）
        course_type: '芝' or 'ダート'
        track_condition: '良', '稍重', '重', '不良'
        class_level: クラス（1=未勝利 〜 5=G1）
    戻り値:
        speed_figure: 数値（高いほど速い）
    """
    # Step 1: 基準タイム（各コース・距離のDBから計算した中央値）
    par_time = get_par_time(distance, course_type)  # 事前計算

    # Step 2: 馬場差補正（当日の馬場全体の速さ補正）
    track_adj = TRACK_CONDITION_ADJ[course_type][track_condition]  # 事前計算

    # Step 3: スピード指数
    raw_figure = (par_time - time_seconds + track_adj) * (1000 / distance) * 10

    # Step 4: クラス補正（オプション）
    return raw_figure + CLASS_BONUS[class_level]

# 追加特徴量:
# best_speed_figure    - 過去N走の最高指数
# recent_speed_figure  - 直近走の指数
# speed_figure_avg3    - 直近3走の平均指数
# speed_figure_trend   - 指数のトレンド（改善/悪化）
```

**なぜ最強か**:
- 「1400m良馬場 1:20.5」と「1600m稍重 1:36.0」が**同一スケールで比較できる**
- 馬の「本当の速さ」を初めて数値化できる
- 現在の39特徴量にはこれに相当するものが存在しない = 完全な新規情報

### C-4: クラス強度補正マージン（★★）

```python
# 現在の avg_diff_seconds はクラスを考慮しない
# G1 0.3秒差負け ≒ 未勝利 0.3秒差負け という扱いになっている

# 補正版
class_weight = {1: 0.5, 2: 0.7, 3: 0.9, 4: 1.1, 5: 1.3}  # クラス強度係数
adjusted_diff = avg_diff_seconds * class_weight[race_class]
features['class_adjusted_diff'] = adjusted_diff
```

### C-5: 相対ペース指数（★★）

```python
# first_3f_avg と last_3f_avg の比から「どんなペースが得意か」を判定
# 高値 = 前傾ペース（先行馬有利）、低値 = 後傾ペース（差し馬有利）

if 'first_3f_avg' in horse_races.columns and 'last_3f_avg' in horse_races.columns:
    pace_ratio = horse_races['first_3f_avg'] / horse_races['last_3f_avg'].replace(0, np.nan)
    features['pace_preference'] = pace_ratio.mean()  # 前傾/後傾の好み

    # 後半加速型の指標（上がりが速い = 差し・追込型）
    features['finish_strength'] = (horse_races['last_3f_avg'] - horse_races['first_3f_avg']).mean()
```

### C-6: 展開スコア — Pace Scenario Score（★★★★）

**最も複雑だが、競馬予想の本質に最も近い特徴量。**

```
展開スコアのロジック:
1. 同レースの全出走馬の脚質カテゴリを集計
   → 逃げ馬2頭、先行3頭、差し5頭、追込5頭 など

2. ペース予測
   → 逃げ馬が多い = ハイペース確定 → 差し・追込有利

3. 各馬の「この展開との相性スコア」を計算
   → 差し馬でハイペース展開 = 高スコア
   → 逃げ馬でハイペース展開 = 低スコア（競り合いで潰れる）

4. スコアを特徴量として追加
```

```python
def calculate_pace_scenario_score(horse_style, all_horse_styles):
    front_count = sum(1 for s in all_horse_styles if s in ['front_runner'])
    stalker_count = sum(1 for s in all_horse_styles if s in ['stalker'])

    # ハイペース度（逃げ馬が多いほど高い）
    pace_intensity = front_count * 2 + stalker_count

    # 脚質との相性
    style_benefit = {
        'front_runner': -pace_intensity * 0.5,  # ハイペースは逃げに不利
        'stalker':      -pace_intensity * 0.2,
        'midpack':       pace_intensity * 0.1,
        'closer':        pace_intensity * 0.4,  # ハイペースは追込に有利
    }
    return style_benefit.get(horse_style, 0)
```

**実装上の注意**: 現在の `predict_core()` は馬を1頭ずつ処理しているため、「同じレースの他馬情報」を参照する仕組みに変更が必要。バックテストのリーケージとは無関係（同レースの他馬情報は使ってよい）。

---

## Group D: モデル・データ改善

### D-1: 訓練データに2023年追加（★）

```python
# 現在: train = 2020-2022, val = 2023, test = 2024-2025
# 変更: train = 2020-2023, val = ランダム10%holdout, test = 2024-2025

train_df = df[df['year'] <= 2023]
val_df = train_df.sample(frac=0.1, random_state=42)
train_df = train_df.drop(val_df.index)
```

### D-2: 直近データへの重み付け（★★）

```python
# 古いデータより最近のデータを重視
# 2022年を基準に、1年経つごとに重みを0.8倍
df['sample_weight'] = df['year'].map({
    2020: 0.51,  # 0.8^3
    2021: 0.64,  # 0.8^2
    2022: 0.80,  # 0.8^1
    2023: 1.00,  # 基準
})
model.fit(X_train, y_train, sample_weight=df_train['sample_weight'])
```

### D-3: ハイパーパラメータ再チューニング — Optuna（★★）

```python
import optuna

def objective(trial):
    params = {
        'learning_rate':    trial.suggest_float('lr', 0.01, 0.1),
        'num_leaves':       trial.suggest_int('leaves', 31, 255),
        'min_child_samples':trial.suggest_int('min_child', 20, 100),
        'feature_fraction': trial.suggest_float('ff', 0.6, 1.0),
        'bagging_fraction': trial.suggest_float('bf', 0.6, 1.0),
        'lambda_l1':        trial.suggest_float('l1', 0, 1.0),
        'lambda_l2':        trial.suggest_float('l2', 0, 1.0),
    }
    # 2023年検証データでAUCを最大化
    return auc_on_val

study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=100)
```

### D-4: アンサンブル（★★★）

```python
# 複数モデルの予測を平均（各モデルの弱点を補い合う）
import xgboost as xgb
import catboost as cb

pred_lgb = model_lgb.predict(X_test)
pred_xgb = model_xgb.predict(X_test)
pred_cat = model_cat.predict(X_test)

# 単純平均（または検証セットで最適化した重み付け平均）
pred_ensemble = (pred_lgb * 0.5 + pred_xgb * 0.3 + pred_cat * 0.2)
```

**効果**: 個々のモデルの予測ブレが平均化され、安定性が向上。的中率のバラつきが減る。

### D-5: ランク学習 — Learning to Rank（★★★ — 重要）

**現在**: 二値分類（1着か否か）→ 各馬を独立に予測
**問題**: 「このレースの中で何位か」という相対的な問題を絶対的な確率で解いている

```python
# LightGBM の objective を binary → rank:pairwise に変更
params['objective'] = 'rank_xendcg'   # or 'lambdarank'

# group情報（同一レース内の馬を1グループとして扱う）
group = df_train.groupby('race_id').size().values
model = lgb.train(params, train_set, group=group)
```

**なぜ有効か**: 競馬は「確率的に強い馬を選ぶ」ではなく「このレースで相対的に最も強い馬を選ぶ」問題。ランク学習はこの構造に直接対応している。AUCが現在より高くなる可能性が高い。

### D-6: コース種別・距離帯別モデル分離（★★★）

```python
# 芝・ダートで完全に別モデルを訓練
model_turf = train(df[df['course_type'] == '芝'])
model_dirt = train(df[df['course_type'] == 'ダート'])

# 距離帯でさらに分離（オプション）
model_sprint = train(df[df['distance'] <= 1400])       # スプリント
model_mile   = train(df[(df['distance'] > 1400) & (df['distance'] <= 1800)])
model_inter  = train(df[(df['distance'] > 1800) & (df['distance'] <= 2200)])
model_long   = train(df[df['distance'] > 2200])        # 長距離
```

**なぜ有効か**: 芝とダートでは勝つ馬の特徴が根本的に異なる（血統・脚質・馬場適性）。1つのモデルで両方を学習すると、それぞれの特化したパターンが薄まる。

### D-7: Neural Network ハイブリッド（★★★★★）

```python
import torch
import torch.nn as nn

class HorseRacingNN(nn.Module):
    """
    Embedding + MLP ハイブリッドモデル
    - 騎手・競馬場・父馬名などカテゴリ変数を Embedding でベクトル化
    - 数値特徴量と連結して MLP で予測
    """
    def __init__(self, n_jockeys, n_tracks, n_fathers, n_numeric):
        super().__init__()
        self.jockey_emb  = nn.Embedding(n_jockeys, 16)  # 騎手 → 16次元ベクトル
        self.track_emb   = nn.Embedding(n_tracks, 8)    # 競馬場 → 8次元
        self.father_emb  = nn.Embedding(n_fathers, 32)  # 父馬 → 32次元

        self.mlp = nn.Sequential(
            nn.Linear(n_numeric + 16 + 8 + 32, 256),
            nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(), nn.Dropout(0.3),
            nn.Linear(128, 1),
            nn.Sigmoid()
        )

    def forward(self, numeric, jockey_id, track_id, father_id):
        j_vec = self.jockey_emb(jockey_id)
        t_vec = self.track_emb(track_id)
        f_vec = self.father_emb(father_id)
        x = torch.cat([numeric, j_vec, t_vec, f_vec], dim=1)
        return self.mlp(x)
```

**なぜ有効か**: 騎手・血統・競馬場を単純な勝率統計ではなくベクトル（embedding）として学習することで、「この騎手 × この血統 × この競馬場」という高次の組み合わせ効果をモデルが自動的に発見できる。LightGBMでは表現できない非線形パターンを捉える。

**注意**: GPU環境が必要、実装・チューニングに時間がかかる。

---

## Roadmap — 的中率最大化の実装順序

```
Phase R1 ─── 即時実施（1〜2日）
│   A-3  Isotonic Regressionキャリブレーション
│   B-1  heavy_track_win_rate 追加
│   B-2  斤量追加
│   B-3  性別・馬齢追加
│   B-4  馬体重・増減追加
│   B-5  前走距離差追加
│   → 再訓練 → バックテストで AUC・ROI 確認
│
Phase R2 ─── 特徴量の深化（3〜5日）
│   C-1  血統 × 芝/ダート/道悪/距離帯 細分化  ← 最重要
│   B-6  脚質カテゴリ数値化
│   B-7  直近3走トレンド
│   B-8  騎手 × 競馬場 組み合わせ勝率
│   B-9  馬場状態別適性
│   C-4  クラス強度補正マージン
│   C-5  相対ペース指数
│   → 再訓練 → バックテスト
│
Phase R3 ─── スピード指数（1週間）
│   C-3  スピード指数（基準タイム計算 + 馬場差補正）
│   D-1  訓練データに2023年追加
│   A-1  閾値最適化（バックテストで探索）
│   A-2  確率差フィルター
│   → 再訓練 → バックテスト
│
Phase R4 ─── モデル構造の改善（1〜2週間）
│   D-3  Optuna ハイパーパラメータ再チューニング
│   D-5  ランク学習（Learning to Rank）
│   D-6  芝/ダート別モデル分離
│   D-2  直近データへの重み付け
│   → バックテスト
│
Phase R5 ─── 高度な手法（1ヶ月〜）
│   C-6  展開スコア（アーキテクチャ変更）
│   D-4  アンサンブル（LGB + XGB + CatBoost）
│   D-7  Neural Networkハイブリッド
└
```

---

## 期待される的中率の推移

| フェーズ完了後 | 的中率（推定） | AUC（推定） | 備考 |
|--------------|-------------|-----------|------|
| 現状（Phase 14） | 16.3%（Rule4全体） | 0.7988 | 2024 OOS実績 |
| R1 完了 | 17–19% | 0.800–0.802 | DB列追加・再訓練 |
| R2 完了 | 19–22% | 0.802–0.807 | 血統細分化・脚質・展開 |
| R3 完了 | 22–27% | 0.807–0.813 | スピード指数が鍵 |
| R4 完了 | 25–30% | 0.810–0.818 | ランク学習・コース別モデル |
| R5 完了 | 28–35% | 0.815–0.825 | NNハイブリッド上限に近い |

> **競馬公開データでの実質上限**: AUC 0.82–0.83 前後（競馬の本質的なランダム性）
> 的中率30–35%達成は十分に現実的な目標

---

## Implementation Files Reference

| 作業 | ファイル |
|------|---------|
| 特徴量計算追加 | `phase13_feature_engineering.py` — `calculate_horse_features_safe()` |
| 血統統計拡張 | `phase13_feature_engineering.py` — `calculate_sire_stats()` |
| 訓練データ再計算 | `phase13_calculate_all_features.py` |
| モデル再訓練 | `phase13_train_model.py` |
| キャリブレーション | 新規 `calibrate_model.py` |
| 閾値バックテスト | 新規 `backtest_threshold_search.py` |
| GUI 日本語名追加 | `keiba_prediction_gui_v3.py` — `FEATURE_NAMES_JP` |
| バックテスト検証 | `run_gui_backtest.py` |

---

*Reference docs: `docs/PHASE14_FEATURE_ENGINEERING.md` / `docs/PHASE14_GUI_BACKTEST_2024.md`*
