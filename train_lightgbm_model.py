"""
LightGBMによる機械学習モデルの訓練
- 2020-2023年のデータで訓練
- 2024年のデータでテスト
- ランク学習（LambdaRank）を使用
"""
import pandas as pd
import json
import sys
import numpy as np
from collections import defaultdict
import lightgbm as lgb
import pickle
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv

print("=" * 80)
print("LightGBM機械学習モデルの訓練")
print("=" * 80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 訓練データ: 2020-2023年
train_df = df[
    (df['date_parsed'] >= '2020-01-01') &
    (df['date_parsed'] <= '2023-12-31')
].copy()

print(f"訓練データ: {len(train_df):,}件 (2020-2023年)")

# 騎手・調教師の統計を事前計算（訓練データのみから）
print("\n騎手・調教師の統計を計算中...")

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

# 全期間の統計をキャッシュ（訓練時のみ使用）
jockey_stats_cache = {}
trainer_stats_cache = {}

# 全訓練データを使用（サンプリングなし）
print("訓練データの全レースを使用...")
sampled_races = train_df.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"訓練レース数: {len(sampled_races)}レース")

# 特徴量抽出
print("\n特徴量を抽出中...")

features_list = []
labels_list = []
groups_list = []

for idx, race_id in enumerate(sampled_races):
    if (idx + 1) % 1000 == 0:
        print(f"  {idx + 1}/{len(sampled_races)} レース処理中...")

    race_horses = train_df[train_df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue

    race_date_str = str(race_date)[:10]

    # 騎手・調教師統計（キャッシュから取得または計算）
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

        # 1. 過去成績の統計
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

        # 2. 騎手の統計
        jockey_name = horse.get('JockeyName')
        if jockey_name in jockey_stats:
            jockey_win_rate = jockey_stats[jockey_name]['win_rate']
            jockey_top3_rate = jockey_stats[jockey_name]['top3_rate']
            jockey_races = jockey_stats[jockey_name]['races']
        else:
            jockey_win_rate, jockey_top3_rate, jockey_races = 0, 0, 0

        # 3. 調教師の統計
        trainer_name = horse.get('TrainerName')
        if trainer_name in trainer_stats:
            trainer_win_rate = trainer_stats[trainer_name]['win_rate']
            trainer_top3_rate = trainer_stats[trainer_name]['top3_rate']
            trainer_races = trainer_stats[trainer_name]['races']
        else:
            trainer_win_rate, trainer_top3_rate, trainer_races = 0, 0, 0

        # 4. その他の特徴量
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

        # コースタイプをエンコード
        course_type = horse.get('course_type')
        course_turf = 1 if course_type == '芝' else 0
        course_dirt = 1 if course_type == 'ダート' else 0

        # 馬場状態をエンコード
        track_condition = horse.get('track_condition')
        track_good = 1 if track_condition == '良' else 0

        # 距離
        distance = pd.to_numeric(horse.get('distance'), errors='coerce')
        distance = distance if pd.notna(distance) else 1600

        # 特徴量ベクトル
        feature_vector = [
            avg_rank,           # 0: 平均着順
            std_rank,           # 1: 着順の標準偏差
            min_rank,           # 2: 最高着順
            max_rank,           # 3: 最低着順
            recent_win_rate,    # 4: 直近勝率
            recent_top3_rate,   # 5: 直近複勝率
            jockey_win_rate,    # 6: 騎手勝率
            jockey_top3_rate,   # 7: 騎手複勝率
            jockey_races,       # 8: 騎手レース数
            trainer_win_rate,   # 9: 調教師勝率
            trainer_top3_rate,  # 10: 調教師複勝率
            trainer_races,      # 11: 調教師レース数
            age,                # 12: 年齢
            weight_diff,        # 13: 馬体重変化
            weight,             # 14: 馬体重
            np.log1p(odds),     # 15: オッズ（対数変換）
            ninki,              # 16: 人気
            waku,               # 17: 枠番
            course_turf,        # 18: 芝コース
            course_dirt,        # 19: ダートコース
            track_good,         # 20: 馬場良
            distance / 1000     # 21: 距離（km単位）
        ]

        race_features.append(feature_vector)
        race_labels.append(rank)

    if len(race_features) >= 8:  # 最低8頭いるレースのみ
        features_list.extend(race_features)
        labels_list.extend(race_labels)
        groups_list.append(len(race_features))  # レースごとの馬数

print(f"\n抽出完了: {len(features_list)}頭のデータ, {len(groups_list)}レース")

# 特徴量名
feature_names = [
    'avg_rank', 'std_rank', 'min_rank', 'max_rank',
    'recent_win_rate', 'recent_top3_rate',
    'jockey_win_rate', 'jockey_top3_rate', 'jockey_races',
    'trainer_win_rate', 'trainer_top3_rate', 'trainer_races',
    'age', 'weight_diff', 'weight', 'log_odds', 'ninki', 'waku',
    'course_turf', 'course_dirt', 'track_good', 'distance_km'
]

# データセット作成
X = np.array(features_list)
y = np.array(labels_list)
groups = np.array(groups_list)

print(f"特徴量マトリクス: {X.shape}")
print(f"ラベル: {y.shape}")

# LightGBMのランク学習用データセット
train_data = lgb.Dataset(X, label=y, group=groups, feature_name=feature_names)

print("\nLightGBMモデルを訓練中...")

# パラメータ
params = {
    'objective': 'lambdarank',  # ランク学習
    'metric': 'ndcg',  # NDCG（Normalized Discounted Cumulative Gain）
    'ndcg_eval_at': [1, 3, 5],  # TOP1, TOP3, TOP5での評価
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': 1
}

# モデル訓練
model = lgb.train(
    params,
    train_data,
    num_boost_round=200,
    valid_sets=[train_data],
    valid_names=['train']
)

print("\n訓練完了！")

# 特徴量の重要度
print("\n【特徴量の重要度 TOP10】")
importance = model.feature_importance(importance_type='gain')
feature_importance = sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True)

for i, (name, imp) in enumerate(feature_importance[:10], 1):
    print(f"{i:2d}. {name:20s}: {imp:10.0f}")

# モデルを保存
model_path = r"C:\Users\bu158\Keiba_Shisaku20250928\lightgbm_model.pkl"
with open(model_path, 'wb') as f:
    pickle.dump({
        'model': model,
        'feature_names': feature_names
    }, f)

print(f"\nモデルを保存: {model_path}")

# 統計も保存（予測時に使用）
stats_path = r"C:\Users\bu158\Keiba_Shisaku20250928\model_stats_cache.pkl"
with open(stats_path, 'wb') as f:
    pickle.dump({
        'jockey_stats': jockey_stats_cache,
        'trainer_stats': trainer_stats_cache
    }, f)

print(f"統計キャッシュを保存: {stats_path}")

print("\n" + "=" * 80)
print("訓練完了！")
print("=" * 80)
