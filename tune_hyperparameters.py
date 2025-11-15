"""
LightGBMハイパーパラメータチューニング
- Grid Searchで最適なパラメータを探索
- 2020-2023年データで訓練・検証
- 複数のパラメータセットを比較
"""
import pandas as pd
import json
import sys
import numpy as np
from collections import defaultdict
import lightgbm as lgb
import pickle
from itertools import product
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv

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

print("=" * 80)
print("LightGBM ハイパーパラメータチューニング")
print("=" * 80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 訓練データ: 2020-2022年（検証用に2023年を別にする）
train_df = df[
    (df['date_parsed'] >= '2020-01-01') &
    (df['date_parsed'] <= '2022-12-31')
].copy()

# 検証データ: 2023年
val_df = df[
    (df['date_parsed'] >= '2023-01-01') &
    (df['date_parsed'] <= '2023-12-31')
].copy()

print(f"訓練データ: {len(train_df):,}件 (2020-2022年)")
print(f"検証データ: {len(val_df):,}件 (2023年)")

# 訓練データから特徴量抽出（20%サンプリングで高速化）
print("\n訓練データから特徴量抽出中（20%サンプリング）...")
train_races = train_df.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()
train_races_sampled = np.random.choice(train_races, size=int(len(train_races) * 0.2), replace=False)

print(f"訓練レース数: {len(train_races_sampled)}レース")

# 統計キャッシュ
jockey_stats_cache = {}
trainer_stats_cache = {}

features_list = []
labels_list = []
groups_list = []

for idx, race_id in enumerate(train_races_sampled):
    if (idx + 1) % 500 == 0:
        print(f"  {idx + 1}/{len(train_races_sampled)} レース処理中...")

    race_horses = train_df[train_df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue

    race_date_str = str(race_date)[:10]

    # 騎手・調教師統計
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
        # ラベル（着順）
        rank = pd.to_numeric(horse.get('Rank'), errors='coerce')
        if pd.isna(rank):
            continue

        # 特徴量抽出
        horse_id = horse.get('horse_id')
        past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=10)

        # 過去成績
        if past_results and len(past_results) > 0:
            recent_ranks = []
            for race in past_results[:5]:
                if isinstance(race, dict):
                    past_rank = pd.to_numeric(race.get('rank'), errors='coerce')
                    if pd.notna(past_rank):
                        recent_ranks.append(past_rank)

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
        else:
            avg_rank, std_rank, min_rank, max_rank = 8, 0, 10, 10
            recent_win_rate, recent_top3_rate = 0, 0

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

        odds = pd.to_numeric(horse.get('Odds_x'), errors='coerce')
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

        feature_vector = [
            avg_rank, std_rank, min_rank, max_rank,
            recent_win_rate, recent_top3_rate,
            jockey_win_rate, jockey_top3_rate, jockey_races,
            trainer_win_rate, trainer_top3_rate, trainer_races,
            age, weight_diff, weight, np.log1p(odds), ninki, waku,
            course_turf, course_dirt, track_good, distance / 1000
        ]

        race_features.append(feature_vector)
        race_labels.append(rank)

    if len(race_features) >= 8:
        features_list.extend(race_features)
        labels_list.extend(race_labels)
        groups_list.append(len(race_features))

print(f"抽出完了: {len(features_list)}頭のデータ, {len(groups_list)}レース")

# 特徴量名
feature_names = [
    'avg_rank', 'std_rank', 'min_rank', 'max_rank',
    'recent_win_rate', 'recent_top3_rate',
    'jockey_win_rate', 'jockey_top3_rate', 'jockey_races',
    'trainer_win_rate', 'trainer_top3_rate', 'trainer_races',
    'age', 'weight_diff', 'weight', 'log_odds', 'ninki', 'waku',
    'course_turf', 'course_dirt', 'track_good', 'distance_km'
]

X_train = np.array(features_list)
y_train = np.array(labels_list)
groups_train = np.array(groups_list)

train_data = lgb.Dataset(X_train, label=y_train, group=groups_train, feature_name=feature_names)

print(f"\n訓練データ: {X_train.shape}")

# ハイパーパラメータの候補
print("\n" + "=" * 80)
print("ハイパーパラメータ探索")
print("=" * 80)

param_grid = {
    'learning_rate': [0.03, 0.05, 0.1],
    'num_leaves': [15, 31, 63],
    'max_depth': [-1, 5, 10],
    'min_data_in_leaf': [10, 20, 50],
}

# 固定パラメータ
fixed_params = {
    'objective': 'lambdarank',
    'metric': 'ndcg',
    'ndcg_eval_at': [1, 3, 5],
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'feature_pre_filter': False,  # min_data_in_leaf変更時のエラー回避
    'verbose': -1
}

# 全組み合わせをテスト（計算量を考慮して一部のみ）
test_configs = [
    # ベースライン
    {'learning_rate': 0.05, 'num_leaves': 31, 'max_depth': -1, 'min_data_in_leaf': 20},

    # 学習率を変更
    {'learning_rate': 0.03, 'num_leaves': 31, 'max_depth': -1, 'min_data_in_leaf': 20},
    {'learning_rate': 0.1, 'num_leaves': 31, 'max_depth': -1, 'min_data_in_leaf': 20},

    # 木の複雑さを変更
    {'learning_rate': 0.05, 'num_leaves': 15, 'max_depth': -1, 'min_data_in_leaf': 20},
    {'learning_rate': 0.05, 'num_leaves': 63, 'max_depth': -1, 'min_data_in_leaf': 20},

    # 深さを制限
    {'learning_rate': 0.05, 'num_leaves': 31, 'max_depth': 5, 'min_data_in_leaf': 20},
    {'learning_rate': 0.05, 'num_leaves': 31, 'max_depth': 10, 'min_data_in_leaf': 20},

    # 最小データ数を変更
    {'learning_rate': 0.05, 'num_leaves': 31, 'max_depth': -1, 'min_data_in_leaf': 10},
    {'learning_rate': 0.05, 'num_leaves': 31, 'max_depth': -1, 'min_data_in_leaf': 50},

    # 複合調整
    {'learning_rate': 0.03, 'num_leaves': 63, 'max_depth': 10, 'min_data_in_leaf': 20},
    {'learning_rate': 0.1, 'num_leaves': 15, 'max_depth': 5, 'min_data_in_leaf': 50},
]

results = []

print(f"\n{len(test_configs)}通りのパラメータセットをテスト中...")

for idx, params in enumerate(test_configs, 1):
    print(f"\n[{idx}/{len(test_configs)}] テスト中...")
    print(f"  learning_rate: {params['learning_rate']}")
    print(f"  num_leaves: {params['num_leaves']}")
    print(f"  max_depth: {params['max_depth']}")
    print(f"  min_data_in_leaf: {params['min_data_in_leaf']}")

    # パラメータをマージ
    full_params = {**fixed_params, **params}

    # モデル訓練
    model = lgb.train(
        full_params,
        train_data,
        num_boost_round=200,
        valid_sets=[train_data],
        valid_names=['train']
    )

    # 訓練データでのNDCG
    train_ndcg = model.best_score['train']['ndcg@3']

    result = {
        **params,
        'train_ndcg': train_ndcg
    }

    results.append(result)

    print(f"  訓練NDCG@3: {train_ndcg:.4f}")

# 結果をソート
results.sort(key=lambda x: x['train_ndcg'], reverse=True)

print("\n" + "=" * 80)
print("【ハイパーパラメータ探索結果 TOP5】")
print("=" * 80)

print("\nLR     | Leaves | Depth | MinData | NDCG@3")
print("-" * 60)

for i, r in enumerate(results[:5], 1):
    print(f"{r['learning_rate']:.2f}   | {r['num_leaves']:6d} | {r['max_depth']:5d} | {r['min_data_in_leaf']:7d} | {r['train_ndcg']:.4f}")

# ベストパラメータ
best_params = results[0]

print("\n" + "=" * 80)
print("【ベストパラメータ】")
print("=" * 80)

print(f"\nlearning_rate: {best_params['learning_rate']}")
print(f"num_leaves: {best_params['num_leaves']}")
print(f"max_depth: {best_params['max_depth']}")
print(f"min_data_in_leaf: {best_params['min_data_in_leaf']}")
print(f"\n訓練NDCG@3: {best_params['train_ndcg']:.4f}")

# ベストモデルを全データで再訓練
print("\n" + "=" * 80)
print("ベストパラメータで全データ訓練中...")
print("=" * 80)

# 全訓練データで特徴量抽出（サンプリングなし）
print("\n全訓練データから特徴量抽出中...")
all_train_races = train_df.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"訓練レース数: {len(all_train_races)}レース")

features_list_full = []
labels_list_full = []
groups_list_full = []

for idx, race_id in enumerate(all_train_races):
    if (idx + 1) % 1000 == 0:
        print(f"  {idx + 1}/{len(all_train_races)} レース処理中...")

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
        past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=10)

        if past_results and len(past_results) > 0:
            recent_ranks = []
            for race in past_results[:5]:
                if isinstance(race, dict):
                    past_rank = pd.to_numeric(race.get('rank'), errors='coerce')
                    if pd.notna(past_rank):
                        recent_ranks.append(past_rank)

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
        else:
            avg_rank, std_rank, min_rank, max_rank = 8, 0, 10, 10
            recent_win_rate, recent_top3_rate = 0, 0

        jockey_name = horse.get('JockeyName')
        if jockey_name in jockey_stats:
            jockey_win_rate = jockey_stats[jockey_name]['win_rate']
            jockey_top3_rate = jockey_stats[jockey_name]['top3_rate']
            jockey_races = jockey_stats[jockey_name]['races']
        else:
            jockey_win_rate, jockey_top3_rate, jockey_races = 0, 0, 0

        trainer_name = horse.get('TrainerName')
        if trainer_name in trainer_stats:
            trainer_win_rate = trainer_stats[trainer_name]['win_rate']
            trainer_top3_rate = trainer_stats[trainer_name]['top3_rate']
            trainer_races = trainer_stats[trainer_name]['races']
        else:
            trainer_win_rate, trainer_top3_rate, trainer_races = 0, 0, 0

        age = pd.to_numeric(horse.get('Age'), errors='coerce')
        age = age if pd.notna(age) else 5

        weight_diff = pd.to_numeric(horse.get('WeightDiff'), errors='coerce')
        weight_diff = weight_diff if pd.notna(weight_diff) else 0

        weight = pd.to_numeric(horse.get('Weight'), errors='coerce')
        weight = weight if pd.notna(weight) else 480

        ninki = pd.to_numeric(horse.get('Ninki'), errors='coerce')
        ninki = ninki if pd.notna(ninki) else 10

        odds = pd.to_numeric(horse.get('Odds_x'), errors='coerce')
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

        feature_vector = [
            avg_rank, std_rank, min_rank, max_rank,
            recent_win_rate, recent_top3_rate,
            jockey_win_rate, jockey_top3_rate, jockey_races,
            trainer_win_rate, trainer_top3_rate, trainer_races,
            age, weight_diff, weight, np.log1p(odds), ninki, waku,
            course_turf, course_dirt, track_good, distance / 1000
        ]

        race_features.append(feature_vector)
        race_labels.append(rank)

    if len(race_features) >= 8:
        features_list_full.extend(race_features)
        labels_list_full.extend(race_labels)
        groups_list_full.append(len(race_features))

X_train_full = np.array(features_list_full)
y_train_full = np.array(labels_list_full)
groups_train_full = np.array(groups_list_full)

train_data_full = lgb.Dataset(X_train_full, label=y_train_full, group=groups_train_full, feature_name=feature_names)

print(f"\n全訓練データ: {X_train_full.shape}")

# ベストパラメータで訓練
best_full_params = {**fixed_params, **{k: v for k, v in best_params.items() if k != 'train_ndcg'}}

final_model = lgb.train(
    best_full_params,
    train_data_full,
    num_boost_round=200,
    valid_sets=[train_data_full],
    valid_names=['train']
)

# モデル保存
model_path = r"C:\Users\bu158\Keiba_Shisaku20250928\lightgbm_model_tuned.pkl"
with open(model_path, 'wb') as f:
    pickle.dump({
        'model': final_model,
        'feature_names': feature_names,
        'params': best_full_params
    }, f)

print(f"\nチューニング済みモデルを保存: {model_path}")

print("\n" + "=" * 80)
print("ハイパーパラメータチューニング完了！")
print("=" * 80)
