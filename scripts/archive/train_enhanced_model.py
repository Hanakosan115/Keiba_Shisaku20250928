"""
強化版モデル訓練スクリプト

新特徴量:
1. クラス情報 (5次元)
2. ラップタイム (7次元)
3. 展開予想 (8次元)

合計: 32 (元) + 15 (新) = 47次元
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
import pickle
from sklearn.model_selection import train_test_split
import sys

sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

def parse_passage(passage_str):
    """Passage文字列から序盤の位置を抽出"""
    if pd.isna(passage_str) or passage_str == '':
        return None
    try:
        parts = str(passage_str).split('-')
        if len(parts) >= 1:
            return int(parts[0])
    except:
        pass
    return None

def classify_running_style(early_position):
    """序盤位置から脚質を分類"""
    if early_position is None:
        return None
    if early_position <= 2:
        return 'escape'
    elif early_position <= 5:
        return 'leading'
    elif early_position <= 10:
        return 'closing'
    else:
        return 'pursuing'

def get_running_style_features(df, horse_id, race_date_str, max_results=10):
    """DataFrameから直接脚質特徴量を計算"""
    race_date_parsed = pd.to_datetime(race_date_str)
    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')
    past_races = horse_races[horse_races['date_parsed'] < race_date_parsed]
    past_races = past_races.sort_values('date_parsed', ascending=False).head(max_results)

    if len(past_races) == 0:
        return {
            'escape_rate': 0, 'leading_rate': 0, 'closing_rate': 0, 'pursuing_rate': 0,
            'avg_agari': 0, 'has_past_results': 0
        }

    style_counts = {'escape': 0, 'leading': 0, 'closing': 0, 'pursuing': 0}
    agari_times = []

    for _, race in past_races.iterrows():
        passage = race.get('Passage')
        early_pos = parse_passage(passage)
        style = classify_running_style(early_pos)
        if style:
            style_counts[style] += 1

        agari = pd.to_numeric(race.get('Agari'), errors='coerce')
        if pd.notna(agari) and agari > 0:
            agari_times.append(agari)

    total = sum(style_counts.values())
    return {
        'escape_rate': style_counts['escape'] / total if total > 0 else 0,
        'leading_rate': style_counts['leading'] / total if total > 0 else 0,
        'closing_rate': style_counts['closing'] / total if total > 0 else 0,
        'pursuing_rate': style_counts['pursuing'] / total if total > 0 else 0,
        'avg_agari': np.mean(agari_times) if agari_times else 0,
        'has_past_results': 1 if total > 0 else 0
    }

def get_recent_ranks(df, horse_id, race_date_str, max_results=5):
    """過去成績から着順のみ取得"""
    race_date_parsed = pd.to_datetime(race_date_str)
    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')
    past_races = horse_races[horse_races['date_parsed'] < race_date_parsed]
    past_races = past_races.sort_values('date_parsed', ascending=False).head(max_results)

    ranks = []
    for _, race in past_races.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)
    return ranks

def calculate_person_stats(df, person_col, reference_date, months_back=12):
    """騎手・調教師の統計を計算"""
    person_stats = {}
    reference_date_parsed = pd.to_datetime(reference_date)
    start_date = reference_date_parsed - pd.DateOffset(months=months_back)

    period_df = df[
        (df['date_parsed'] >= start_date) &
        (df['date_parsed'] < reference_date_parsed)
    ].copy()

    period_df['rank_num'] = pd.to_numeric(period_df['Rank'], errors='coerce')
    period_df = period_df[period_df['rank_num'].notna()]

    for person in period_df[person_col].unique():
        if pd.isna(person) or person == '':
            continue

        person_races = period_df[period_df[person_col] == person]
        total_races = len(person_races)

        if total_races >= 10:
            wins = (person_races['rank_num'] == 1).sum()
            top3 = (person_races['rank_num'] <= 3).sum()

            person_stats[person] = {
                'win_rate': wins / total_races,
                'top3_rate': top3 / total_races,
                'races': total_races
            }

    return person_stats

print("="*80)
print("強化版LightGBMモデル訓練")
print("  - クラス情報")
print("  - ラップタイム")
print("  - 展開予想")
print("="*80)

# データ読み込み（強化版）
print("\nデータ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv',
                 encoding='utf-8', low_memory=False)

print(f"総データ数: {len(df):,}件")

# 新特徴量の確認
print("\n新特徴量の確認:")
new_features = [
    'laps', 'lap_count', 'pace_category', 'first_3f_avg', 'last_3f_avg',
    'pace_variance', 'pace_acceleration',
    'running_style', 'escape_count', 'leading_count', 'sashi_count',
    'oikomi_count', 'pace_prediction', 'development', 'pace_match_score'
]

for feat in new_features:
    if feat in df.columns:
        not_null = df[feat].notna().sum()
        pct = 100 * not_null / len(df)
        print(f"  {feat:20s}: {not_null:7d} ({pct:5.1f}%)")

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 訓練データ: 2020-2023年
train_df = df[
    (df['date_parsed'] >= '2020-01-01') &
    (df['date_parsed'] <= '2023-12-31')
].copy()

print(f"\n訓練データ: {len(train_df):,}件 (2020-2023年)")

# 特徴量抽出
print("\n特徴量抽出中（全特徴量含む）...")
train_races = train_df.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"訓練レース数: {len(train_races):,}レース")

# 統計キャッシュ
jockey_stats_cache = {}
trainer_stats_cache = {}

features_list = []
labels_list = []
groups_list = []

for idx, race_id in enumerate(train_races):
    if (idx + 1) % 1000 == 0:
        print(f"  {idx + 1}/{len(train_races)} レース処理中...")

    race_horses = train_df[train_df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue

    race_date_str = str(race_date)[:10]

    if race_date_str not in jockey_stats_cache:
        jockey_stats_cache[race_date_str] = calculate_person_stats(
            train_df, 'JockeyName', race_date_str, months_back=12
        )
        trainer_stats_cache[race_date_str] = calculate_person_stats(
            train_df, 'TrainerName', race_date_str, months_back=12
        )

    jockey_stats = jockey_stats_cache[race_date_str]
    trainer_stats = trainer_stats_cache[race_date_str]

    race_features = []
    race_labels = []

    for _, horse in race_horses.iterrows():
        rank = pd.to_numeric(horse.get('Rank'), errors='coerce')
        if pd.isna(rank):
            continue

        horse_id = horse.get('horse_id')

        # 過去成績
        recent_ranks = get_recent_ranks(train_df, horse_id, race_date_str, max_results=5)

        if recent_ranks:
            avg_rank = np.mean(recent_ranks)
            std_rank = np.std(recent_ranks) if len(recent_ranks) > 1 else 0
            min_rank = np.min(recent_ranks)
            max_rank = np.max(recent_ranks)
            recent_win_rate = sum(1 for r in recent_ranks if r == 1) / len(recent_ranks)
            recent_top3_rate = sum(1 for r in recent_ranks if r <= 3) / len(recent_ranks)
        else:
            avg_rank, std_rank, min_rank, max_rank = 8, 0, 10, 10
            recent_win_rate, recent_top3_rate = 0, 0

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

        odds = pd.to_numeric(horse.get('Odds'), errors='coerce')
        odds = odds if pd.notna(odds) and odds > 0 else 50

        waku = pd.to_numeric(horse.get('Waku'), errors='coerce')
        waku = waku if pd.notna(waku) else 5

        course_type = horse.get('course_type')
        course_turf = 1 if course_type == '芝' else 0
        course_dirt = 1 if course_type == 'ダート' else 0

        track_condition = horse.get('track_condition')
        track_good = 1 if track_condition == '良' else 0

        distance = pd.to_numeric(horse.get('distance'), errors='coerce')
        distance = distance if pd.notna(distance) else 1600

        # クラス関連特徴量
        race_class_rank = pd.to_numeric(horse.get('race_class_rank'), errors='coerce')
        race_class_rank = race_class_rank if pd.notna(race_class_rank) else 0

        prev_race_class_rank = pd.to_numeric(horse.get('prev_race_class_rank'), errors='coerce')
        prev_race_class_rank = prev_race_class_rank if pd.notna(prev_race_class_rank) else 0

        # クラス変動フラグ
        class_change = horse.get('class_change', 'same')
        is_promotion = 1 if class_change == 'promotion' else 0
        is_demotion = 1 if class_change == 'demotion' else 0
        is_debut = 1 if class_change == 'debut' else 0

        # クラス差分
        class_rank_diff = race_class_rank - prev_race_class_rank if prev_race_class_rank != 0 else 0

        # 【NEW!】ラップタイム特徴量
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

        # ペースカテゴリ
        pace_cat = horse.get('pace_category', 'medium')
        pace_slow = 1 if pace_cat == 'slow' else 0
        pace_fast = 1 if pace_cat == 'fast' else 0

        # 【NEW!】展開予想特徴量
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

        # 脚質エンコーディング
        run_style = horse.get('running_style', 'unknown')
        is_escape = 1 if run_style == 'escape' else 0
        is_leading = 1 if run_style == 'leading' else 0
        is_sashi = 1 if run_style == 'sashi' else 0

        # 展開予想エンコーディング
        dev = horse.get('development', 'neutral')
        is_front_collapse = 1 if dev == 'front_collapse' else 0
        is_front_runner = 1 if dev == 'front_runner' else 0

        # 特徴量ベクトル（47次元）
        feature_vector = [
            # 基本特徴量 (22次元)
            avg_rank, std_rank, min_rank, max_rank,
            recent_win_rate, recent_top3_rate,
            jockey_win_rate, jockey_top3_rate, jockey_races,
            trainer_win_rate, trainer_top3_rate, trainer_races,
            age, weight_diff, weight, np.log1p(odds), ninki, waku,
            course_turf, course_dirt, track_good, distance / 1000,
            # 脚質特徴量 (5次元)
            style_dist['escape_rate'],
            style_dist['leading_rate'],
            style_dist['closing_rate'],
            style_dist['pursuing_rate'],
            style_dist['avg_agari'],
            # クラス特徴量 (5次元)
            race_class_rank,
            is_promotion,
            is_demotion,
            is_debut,
            class_rank_diff,
            # ラップタイム特徴量 (7次元)
            first_3f_avg,
            last_3f_avg,
            pace_variance,
            pace_acceleration,
            lap_count,
            pace_slow,
            pace_fast,
            # 展開予想特徴量 (8次元)
            escape_count,
            leading_count,
            sashi_count,
            oikomi_count,
            pace_match_score,
            is_escape,
            is_leading,
            is_sashi
        ]

        race_features.append(feature_vector)
        race_labels.append(rank)

    if len(race_features) > 0:
        features_list.extend(race_features)
        labels_list.extend(race_labels)
        groups_list.extend([len(race_features)])

# データ準備
X = np.array(features_list)
y = np.array(labels_list)
groups = np.array(groups_list)

print(f"\n特徴量抽出完了")
print(f"  サンプル数: {len(X):,}")
print(f"  特徴量次元: {X.shape[1]}")
print(f"  レース数: {len(groups):,}")

# 訓練・検証分割（レース単位）
train_idx = int(len(groups) * 0.8)
X_train = X[:sum(groups[:train_idx])]
y_train = y[:sum(groups[:train_idx])]
X_val = X[sum(groups[:train_idx]):]
y_val = y[sum(groups[:train_idx]):]

print(f"\n訓練データ: {len(X_train):,}")
print(f"検証データ: {len(X_val):,}")

# LightGBMモデル訓練
print("\nLightGBMモデル訓練中...")

params = {
    'objective': 'regression',
    'metric': 'rmse',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': -1,
    'min_data_in_leaf': 50
}

train_data = lgb.Dataset(X_train, label=y_train)
val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

model = lgb.train(
    params,
    train_data,
    num_boost_round=1000,
    valid_sets=[train_data, val_data],
    valid_names=['train', 'valid'],
    callbacks=[lgb.early_stopping(stopping_rounds=50)]
)

print(f"\n最適なイテレーション数: {model.best_iteration}")
print(f"訓練RMSE: {model.best_score['train']['rmse']:.4f}")
print(f"検証RMSE: {model.best_score['valid']['rmse']:.4f}")

# モデル保存
model_file = 'lgbm_model_enhanced.pkl'
print(f"\nモデル保存中: {model_file}")
with open(model_file, 'wb') as f:
    pickle.dump(model, f)

print("\n完了！")
print("="*80)
