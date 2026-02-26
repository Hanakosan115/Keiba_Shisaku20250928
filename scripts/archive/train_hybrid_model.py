"""
ハイブリッドモデル訓練（順位予測精度重視版）

- オッズ・人気は保持（市場の知恵を活用）
- 新特徴量追加（モメンタム、適性、休養）
- 重み付き学習（上位着順の予測精度を重視）
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
import pickle
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split

# ===== 重み付けパラメータ（調整可能） =====
# 順位ベースの重み付け（上位着順の予測精度を重視）
RANK_1_3_WEIGHT = 3.0   # 1-3着: 3倍重視
RANK_4_5_WEIGHT = 2.0   # 4-5着: 2倍重視
RANK_6_8_WEIGHT = 1.0   # 6-8着: 通常
RANK_9PLUS_WEIGHT = 0.5 # 9着以下: 軽く

def get_recent_ranks(df, horse_id, race_date_str, max_results=5):
    """指定日以前の過去成績を取得"""
    race_date = pd.to_datetime(race_date_str)

    horse_races = df[
        (df['horse_id'] == horse_id) &
        (df['date_parsed'] < race_date)
    ].sort_values('date_parsed', ascending=False).head(max_results)

    ranks = []
    for _, race in horse_races.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)

    return ranks

def get_all_ranks(df, horse_id, race_date_str):
    """全過去成績を取得"""
    race_date = pd.to_datetime(race_date_str)

    horse_races = df[
        (df['horse_id'] == horse_id) &
        (df['date_parsed'] < race_date)
    ]

    ranks = []
    for _, race in horse_races.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)

    return ranks

def get_distance_performance(df, horse_id, race_date_str, target_distance):
    """特定距離での過去成績"""
    race_date = pd.to_datetime(race_date_str)

    horse_races = df[
        (df['horse_id'] == horse_id) &
        (df['date_parsed'] < race_date)
    ].copy()

    # 距離を数値に変換
    horse_races['distance_num'] = pd.to_numeric(horse_races['distance'], errors='coerce')
    horse_races = horse_races[horse_races['distance_num'].notna()]

    # 同距離レース（±200m）
    distance_races = horse_races[
        (horse_races['distance_num'] >= target_distance - 200) &
        (horse_races['distance_num'] <= target_distance + 200)
    ]

    ranks = []
    for _, race in distance_races.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)

    return ranks if len(ranks) > 0 else None

def get_track_condition_performance(df, horse_id, race_date_str, target_condition):
    """特定馬場状態での過去成績"""
    race_date = pd.to_datetime(race_date_str)

    horse_races = df[
        (df['horse_id'] == horse_id) &
        (df['date_parsed'] < race_date) &
        (df['track_condition'] == target_condition)
    ]

    ranks = []
    for _, race in horse_races.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)

    return ranks if len(ranks) > 0 else None

def get_last_race_info(df, horse_id, race_date_str):
    """前走情報を取得"""
    race_date = pd.to_datetime(race_date_str)

    last_race = df[
        (df['horse_id'] == horse_id) &
        (df['date_parsed'] < race_date)
    ].sort_values('date_parsed', ascending=False).head(1)

    if len(last_race) == 0:
        return None, None

    last_rank = pd.to_numeric(last_race.iloc[0].get('Rank'), errors='coerce')
    last_date = last_race.iloc[0]['date_parsed']

    if pd.isna(last_rank) or pd.isna(last_date):
        return None, None

    days_since = (race_date - last_date).days

    return last_rank, days_since

def get_running_style_features(df, horse_id, race_date_str):
    """脚質分布を計算"""
    race_date = pd.to_datetime(race_date_str)

    horse_races = df[
        (df['horse_id'] == horse_id) &
        (df['date_parsed'] < race_date)
    ].tail(10)

    if len(horse_races) == 0:
        return {
            'escape_rate': 0.1,
            'leading_rate': 0.3,
            'closing_rate': 0.5,
            'pursuing_rate': 0.1,
            'avg_agari': 35.0
        }

    styles = horse_races['running_style'].value_counts()
    total = len(horse_races)

    escape_rate = styles.get('escape', 0) / total
    leading_rate = styles.get('leading', 0) / total
    closing_rate = styles.get('sashi', 0) / total
    pursuing_rate = styles.get('oikomi', 0) / total

    agari_vals = pd.to_numeric(horse_races['Agari'], errors='coerce').dropna()
    avg_agari = agari_vals.mean() if len(agari_vals) > 0 else 35.0

    return {
        'escape_rate': escape_rate,
        'leading_rate': leading_rate,
        'closing_rate': closing_rate,
        'pursuing_rate': pursuing_rate,
        'avg_agari': avg_agari
    }

def calculate_person_stats(df, person_col, race_date_str, months_back=12):
    """騎手・調教師統計を計算"""
    race_date = pd.to_datetime(race_date_str)
    cutoff_date = race_date - timedelta(days=months_back*30)

    recent_df = df[
        (df['date_parsed'] >= cutoff_date) &
        (df['date_parsed'] < race_date)
    ]

    person_stats = {}

    for person in recent_df[person_col].unique():
        person_races = recent_df[recent_df[person_col] == person]
        ranks = pd.to_numeric(person_races['Rank'], errors='coerce').dropna()

        if len(ranks) > 0:
            wins = (ranks == 1).sum()
            top3 = (ranks <= 3).sum()
            person_stats[person] = {
                'win_rate': wins / len(ranks),
                'top3_rate': top3 / len(ranks),
                'races': len(ranks)
            }

    return person_stats

print("="*80)
print("ハイブリッドLightGBMモデル訓練（順位予測精度重視版）")
print(f"  - オッズ・人気: 保持（市場の知恵を活用）")
print(f"  - 新特徴量: モメンタム、適性、休養")
print(f"  - 重み付き学習: 1-3着={RANK_1_3_WEIGHT}倍, 4-5着={RANK_4_5_WEIGHT}倍, 6-8着={RANK_6_8_WEIGHT}倍")
print("="*80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv',
                 encoding='utf-8', low_memory=False)

print(f"総データ数: {len(df):,}件")

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 訓練データ: 2020-2023年
train_df = df[
    (df['date_parsed'] >= '2020-01-01') &
    (df['date_parsed'] <= '2023-12-31')
].copy()

print(f"\n訓練データ: {len(train_df):,}件 (2020-2023年)")

# 特徴量抽出
print("\n特徴量抽出中（新特徴量含む）...")
train_races = train_df.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"訓練レース数: {len(train_races):,}レース")

# 統計キャッシュ
jockey_stats_cache = {}
trainer_stats_cache = {}

X_all = []
y_all = []
weights_all = []  # サンプル重み

for idx, race_id in enumerate(train_races):
    if (idx + 1) % 1000 == 0:
        print(f"  進捗: {idx+1}/{len(train_races)} レース ({100*(idx+1)/len(train_races):.1f}%)")

    race_horses = train_df[train_df['race_id'] == race_id]

    if len(race_horses) < 8:
        continue

    race_date_str = race_horses.iloc[0]['date']

    if race_date_str not in jockey_stats_cache:
        jockey_stats_cache[race_date_str] = calculate_person_stats(
            train_df, 'JockeyName', race_date_str, months_back=12
        )
        trainer_stats_cache[race_date_str] = calculate_person_stats(
            train_df, 'TrainerName', race_date_str, months_back=12
        )

    jockey_stats = jockey_stats_cache[race_date_str]
    trainer_stats = trainer_stats_cache[race_date_str]

    # レース距離・馬場
    race_distance = pd.to_numeric(race_horses.iloc[0].get('distance'), errors='coerce')
    race_distance = race_distance if pd.notna(race_distance) else 1600

    race_condition = race_horses.iloc[0].get('track_condition')

    race_features = []
    race_labels = []
    race_weights = []

    for _, horse in race_horses.iterrows():
        rank = pd.to_numeric(horse.get('Rank'), errors='coerce')
        if pd.isna(rank):
            continue

        horse_id = horse.get('horse_id')

        # オッズ取得
        odds = pd.to_numeric(horse.get('Odds'), errors='coerce')
        odds = odds if pd.notna(odds) and odds > 0 else 50

        # サンプル重み計算（上位着順を重視）
        if rank <= 3:
            sample_weight = RANK_1_3_WEIGHT  # 1-3着: 3倍重視
        elif rank <= 5:
            sample_weight = RANK_4_5_WEIGHT  # 4-5着: 2倍重視
        elif rank <= 8:
            sample_weight = RANK_6_8_WEIGHT  # 6-8着: 通常
        else:
            sample_weight = RANK_9PLUS_WEIGHT  # 9着以下: 軽く

        # ===== 基本的な過去成績 =====
        recent_ranks = get_recent_ranks(train_df, horse_id, race_date_str, max_results=5)
        all_ranks = get_all_ranks(train_df, horse_id, race_date_str)

        if recent_ranks and len(recent_ranks) >= 3:
            avg_rank = np.mean(recent_ranks)
            std_rank = np.std(recent_ranks) if len(recent_ranks) > 1 else 0
            min_rank = np.min(recent_ranks)
            max_rank = np.max(recent_ranks)
            recent_win_rate = sum(1 for r in recent_ranks if r == 1) / len(recent_ranks)
            recent_top3_rate = sum(1 for r in recent_ranks if r <= 3) / len(recent_ranks)

            # 最近3走の平均
            recent_3_avg = np.mean(recent_ranks[:3])
        else:
            avg_rank, std_rank, min_rank, max_rank = 8, 0, 10, 10
            recent_win_rate, recent_top3_rate = 0, 0
            recent_3_avg = 8.0

        # 全体平均
        if all_ranks and len(all_ranks) >= 5:
            overall_avg = np.mean(all_ranks)
        else:
            overall_avg = 8.0

        # ===== NEW! モメンタム（調子上昇度） =====
        momentum_score = overall_avg - recent_3_avg  # 正なら上昇傾向

        # ===== NEW! リバウンド検出 =====
        last_rank, days_since_last = get_last_race_info(train_df, horse_id, race_date_str)

        if last_rank is not None:
            is_rebound_candidate = 1 if last_rank > (overall_avg + 3) else 0
        else:
            is_rebound_candidate = 0
            last_rank = 10
            days_since_last = 90

        # ===== NEW! 距離適性 =====
        distance_ranks = get_distance_performance(train_df, horse_id, race_date_str, race_distance)

        if distance_ranks:
            distance_avg = np.mean(distance_ranks)
            distance_fit_score = overall_avg - distance_avg  # 正ならこの距離が得意
            distance_experience = len(distance_ranks)
        else:
            distance_avg = overall_avg
            distance_fit_score = 0.0
            distance_experience = 0

        # ===== NEW! 馬場適性 =====
        condition_ranks = get_track_condition_performance(train_df, horse_id, race_date_str, race_condition)

        if condition_ranks:
            condition_avg = np.mean(condition_ranks)
            condition_fit_score = overall_avg - condition_avg  # 正ならこの馬場が得意
            condition_experience = len(condition_ranks)
        else:
            condition_avg = overall_avg
            condition_fit_score = 0.0
            condition_experience = 0

        # ===== NEW! 休養・連闘フラグ =====
        is_fresh = 1 if days_since_last > 60 else 0  # 休み明け
        is_consecutive = 1 if days_since_last < 14 else 0  # 連闘

        # 脚質分布
        style_dist = get_running_style_features(train_df, horse_id, race_date_str)

        # 騎手統計
        jockey_name = horse.get('JockeyName')
        if jockey_name in jockey_stats:
            jockey_win_rate = jockey_stats[jockey_name]['win_rate']
            jockey_top3_rate = jockey_stats[jockey_name]['top3_rate']
            jockey_races = jockey_stats[jockey_name]['races']
        else:
            jockey_win_rate, jockey_top3_rate, jockey_races = 0, 0, 0

        # 調教師統計
        trainer_name = horse.get('TrainerName')
        if trainer_name in trainer_stats:
            trainer_win_rate = trainer_stats[trainer_name]['win_rate']
            trainer_top3_rate = trainer_stats[trainer_name]['top3_rate']
            trainer_races = trainer_stats[trainer_name]['races']
        else:
            trainer_win_rate, trainer_top3_rate, trainer_races = 0, 0, 0

        # その他の特徴量
        age = pd.to_numeric(horse.get('Age'), errors='coerce')
        age = age if pd.notna(age) else 5

        weight_diff = pd.to_numeric(horse.get('WeightDiff'), errors='coerce')
        weight_diff = weight_diff if pd.notna(weight_diff) else 0

        weight = pd.to_numeric(horse.get('Weight'), errors='coerce')
        weight = weight if pd.notna(weight) else 480

        ninki = pd.to_numeric(horse.get('Ninki'), errors='coerce')
        ninki = ninki if pd.notna(ninki) else 10

        waku = pd.to_numeric(horse.get('Waku'), errors='coerce')
        waku = waku if pd.notna(waku) else 5

        course_type = horse.get('course_type')
        course_turf = 1 if course_type == '芝' else 0
        course_dirt = 1 if course_type == 'ダート' else 0

        track_condition = horse.get('track_condition')
        track_good = 1 if track_condition == '良' else 0

        distance = pd.to_numeric(horse.get('distance'), errors='coerce')
        distance = distance if pd.notna(distance) else 1600

        # クラス関連
        race_class_rank = pd.to_numeric(horse.get('race_class_rank'), errors='coerce')
        race_class_rank = race_class_rank if pd.notna(race_class_rank) else 0

        prev_race_class_rank = pd.to_numeric(horse.get('prev_race_class_rank'), errors='coerce')
        prev_race_class_rank = prev_race_class_rank if pd.notna(prev_race_class_rank) else 0

        class_change = horse.get('class_change', 'same')
        is_promotion = 1 if class_change == 'promotion' else 0
        is_demotion = 1 if class_change == 'demotion' else 0
        is_debut = 1 if class_change == 'debut' else 0

        class_rank_diff = race_class_rank - prev_race_class_rank if prev_race_class_rank != 0 else 0

        # ラップタイム
        first_3f_avg = pd.to_numeric(horse.get('first_3f_avg'), errors='coerce')
        first_3f_avg = first_3f_avg if pd.notna(first_3f_avg) else 12.0

        last_3f_avg = pd.to_numeric(horse.get('last_3f_avg'), errors='coerce')
        last_3f_avg = last_3f_avg if pd.notna(last_3f_avg) else 12.0

        pace_variance = pd.to_numeric(horse.get('pace_variance'), errors='coerce')
        pace_variance = pace_variance if pd.notna(pace_variance) else 0.5

        pace_acceleration = pd.to_numeric(horse.get('pace_acceleration'), errors='coerce')
        pace_acceleration = pace_acceleration if pd.notna(pace_acceleration) else 0.0

        lap_count = pd.to_numeric(horse.get('lap_count'), errors='coerce')
        lap_count = lap_count if pd.notna(lap_count) else 8

        pace_cat = horse.get('pace_category', 'medium')
        pace_slow = 1 if pace_cat == 'slow' else 0
        pace_fast = 1 if pace_cat == 'fast' else 0

        # 展開予想
        escape_count = pd.to_numeric(horse.get('escape_count'), errors='coerce')
        escape_count = escape_count if pd.notna(escape_count) else 2

        leading_count = pd.to_numeric(horse.get('leading_count'), errors='coerce')
        leading_count = leading_count if pd.notna(leading_count) else 5

        sashi_count = pd.to_numeric(horse.get('sashi_count'), errors='coerce')
        sashi_count = sashi_count if pd.notna(sashi_count) else 8

        oikomi_count = pd.to_numeric(horse.get('oikomi_count'), errors='coerce')
        oikomi_count = oikomi_count if pd.notna(oikomi_count) else 3

        pace_match_score = pd.to_numeric(horse.get('pace_match_score'), errors='coerce')
        pace_match_score = pace_match_score if pd.notna(pace_match_score) else 0.5

        run_style = horse.get('running_style', 'unknown')
        is_escape = 1 if run_style == 'escape' else 0
        is_leading = 1 if run_style == 'leading' else 0
        is_sashi = 1 if run_style == 'sashi' else 0

        # ★ 特徴量ベクトル（57次元 = 元の47 + 新規10） ★
        feature_vector = [
            # 基本特徴量 (22次元) - オッズ・人気を保持
            avg_rank, std_rank, min_rank, max_rank,
            recent_win_rate, recent_top3_rate,
            jockey_win_rate, jockey_top3_rate, jockey_races,
            trainer_win_rate, trainer_top3_rate, trainer_races,
            age, weight_diff, weight, np.log1p(odds), ninki, waku,
            course_turf, course_dirt, track_good, distance / 1000,
            # 脚質特徴量 (5次元)
            style_dist['escape_rate'], style_dist['leading_rate'],
            style_dist['closing_rate'], style_dist['pursuing_rate'],
            style_dist['avg_agari'],
            # クラス特徴量 (5次元)
            race_class_rank, is_promotion, is_demotion, is_debut, class_rank_diff,
            # ラップタイム特徴量 (7次元)
            first_3f_avg, last_3f_avg, pace_variance, pace_acceleration,
            lap_count, pace_slow, pace_fast,
            # 展開予想特徴量 (8次元)
            escape_count, leading_count, sashi_count, oikomi_count,
            pace_match_score, is_escape, is_leading, is_sashi,
            # ★ NEW! モメンタム・適性特徴量 (10次元) ★
            momentum_score, is_rebound_candidate,
            distance_fit_score, distance_experience,
            condition_fit_score, condition_experience,
            is_fresh, is_consecutive, days_since_last / 30, last_rank,
        ]

        race_features.append(feature_vector)
        race_labels.append(rank)
        race_weights.append(sample_weight)

    if len(race_features) > 0:
        X_all.extend(race_features)
        y_all.extend(race_labels)
        weights_all.extend(race_weights)

X_all = np.array(X_all)
y_all = np.array(y_all)
weights_all = np.array(weights_all)

print(f"\n訓練サンプル数: {len(X_all):,}件")
print(f"特徴量次元: {X_all.shape[1]}次元（新特徴量10個追加）")
print(f"重み付きサンプル分布:")
print(f"  1-3着 (重み{RANK_1_3_WEIGHT}倍): {(weights_all == RANK_1_3_WEIGHT).sum():,}件")
print(f"  4-5着 (重み{RANK_4_5_WEIGHT}倍): {(weights_all == RANK_4_5_WEIGHT).sum():,}件")
print(f"  6-8着 (重み{RANK_6_8_WEIGHT}倍): {(weights_all == RANK_6_8_WEIGHT).sum():,}件")
print(f"  9着以下 (重み{RANK_9PLUS_WEIGHT}倍): {(weights_all == RANK_9PLUS_WEIGHT).sum():,}件")

# Train/Validationの分割
X_train, X_val, y_train, y_val, w_train, w_val = train_test_split(
    X_all, y_all, weights_all, test_size=0.2, random_state=42
)

print(f"訓練: {len(X_train):,}件, 検証: {len(X_val):,}件")

# LightGBMデータセット作成（重み付き）
train_data = lgb.Dataset(X_train, label=y_train, weight=w_train)
val_data = lgb.Dataset(X_val, label=y_val, weight=w_val, reference=train_data)

# パラメータ設定
params = {
    'objective': 'regression',
    'metric': 'rmse',
    'boosting_type': 'gbdt',
    'num_leaves': 63,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': -1,
    'seed': 42
}

print("\nモデル訓練中...")
model = lgb.train(
    params,
    train_data,
    num_boost_round=1000,
    valid_sets=[train_data, val_data],
    valid_names=['train', 'valid'],
    callbacks=[
        lgb.early_stopping(stopping_rounds=50),
        lgb.log_evaluation(period=100)
    ]
)

# モデル保存
model_file = 'lgbm_model_hybrid.pkl'
with open(model_file, 'wb') as f:
    pickle.dump(model, f)

print(f"\nモデル保存: {model_file}")

# 訓練結果
train_pred = model.predict(X_train)
val_pred = model.predict(X_val)

train_rmse = np.sqrt(np.mean((train_pred - y_train) ** 2))
val_rmse = np.sqrt(np.mean((val_pred - y_val) ** 2))

print("\n" + "="*80)
print("訓練結果")
print("="*80)
print(f"訓練RMSE: {train_rmse:.4f}")
print(f"検証RMSE: {val_rmse:.4f}")
print(f"ベストイテレーション: {model.best_iteration}")

# 重要度トップ15
feature_names = [
    'avg_rank', 'std_rank', 'min_rank', 'max_rank',
    'recent_win_rate', 'recent_top3_rate',
    'jockey_win_rate', 'jockey_top3_rate', 'jockey_races',
    'trainer_win_rate', 'trainer_top3_rate', 'trainer_races',
    'age', 'weight_diff', 'weight', 'log_odds', 'ninki', 'waku',
    'course_turf', 'course_dirt', 'track_good', 'distance',
    'escape_rate', 'leading_rate', 'closing_rate', 'pursuing_rate', 'avg_agari',
    'race_class_rank', 'is_promotion', 'is_demotion', 'is_debut', 'class_rank_diff',
    'first_3f_avg', 'last_3f_avg', 'pace_variance', 'pace_acceleration',
    'lap_count', 'pace_slow', 'pace_fast',
    'escape_count', 'leading_count', 'sashi_count', 'oikomi_count',
    'pace_match_score', 'is_escape', 'is_leading', 'is_sashi',
    'momentum_score', 'is_rebound', 'distance_fit', 'distance_exp',
    'condition_fit', 'condition_exp', 'is_fresh', 'is_consecutive',
    'days_since_norm', 'last_rank'
]

importance = model.feature_importance(importance_type='gain')
importance_df = pd.DataFrame({
    'feature': feature_names,
    'importance': importance
}).sort_values('importance', ascending=False)

print("\n重要度トップ15:")
for idx, row in importance_df.head(15).iterrows():
    print(f"  {row['feature']:20s}: {row['importance']:8.1f}")

print("\n新特徴量の重要度:")
new_features = importance_df[importance_df['feature'].str.contains(
    'momentum|rebound|distance_fit|condition_fit|fresh|consecutive|days_since|last_rank'
)]
for idx, row in new_features.iterrows():
    print(f"  {row['feature']:20s}: {row['importance']:8.1f}")

print("\n" + "="*80)
print("完了！")
print("="*80)
