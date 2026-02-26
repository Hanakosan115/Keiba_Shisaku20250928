"""
次世代統合モデル：展開予想＋トラックバイアス＋コース適性
- 40次元以上の高度な特徴量
- 的中率と回収率の両立を目指す
"""
import pandas as pd
import sys
import numpy as np
import lightgbm as lgb
import pickle
from collections import Counter
from data_config import MAIN_CSV, MAIN_JSON
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

# 競馬場の回り方向マスタ
TRACK_TURN_DIRECTION = {
    '東京': 'left',
    '中山': 'right',
    '阪神': 'right',
    '京都': 'right',
    '中京': 'left',
    '新潟': 'left',
    '福島': 'right',
    '小倉': 'right',
    '札幌': 'right',
    '函館': 'right'
}

def parse_passage_full(passage_str):
    """
    Passage文字列を完全解析
    "11-12-15-8" -> [11, 12, 15, 8] (4コーナー分)
    "5-5" -> [5, None, None, 5] (序盤と終盤のみ)
    """
    if pd.isna(passage_str) or passage_str == '':
        return [None, None, None, None]

    try:
        positions = [int(p) for p in str(passage_str).split('-')]

        if len(positions) == 2:
            # 序盤と終盤のみ
            return [positions[0], None, None, positions[1]]
        elif len(positions) == 4:
            # 4コーナー全て
            return positions
        elif len(positions) == 3:
            # 3つの場合
            return [positions[0], positions[1], None, positions[2]]
        else:
            return positions + [None] * (4 - len(positions))
    except:
        return [None, None, None, None]

def classify_running_style(early_position):
    """序盤位置から脚質を分類"""
    if early_position is None or early_position == 0:
        return None
    if early_position <= 2:
        return 'escape'
    elif early_position <= 5:
        return 'leading'
    elif early_position <= 10:
        return 'closing'
    else:
        return 'pursuing'

def get_race_pace_scenario(race_df):
    """
    レース全体の展開予想
    出走馬の脚質分布から予想ペースを判定
    """
    escape_count = 0
    leading_count = 0
    total_horses = len(race_df)

    for _, horse in race_df.iterrows():
        passage = horse.get('Passage')
        positions = parse_passage_full(passage)
        early_pos = positions[0]

        style = classify_running_style(early_pos)
        if style == 'escape':
            escape_count += 1
        elif style == 'leading':
            leading_count += 1

    # ペースシナリオ判定
    if escape_count >= 2:
        return 'high_pace', escape_count  # ハイペース（逃げ争い）
    elif escape_count == 1 and leading_count <= 2:
        return 'slow_pace', escape_count  # スローペース
    else:
        return 'average_pace', escape_count  # 平均ペース

def calculate_track_aptitude(df, horse_id, track_name, race_date_str):
    """特定競馬場での適性を計算"""
    race_date_parsed = pd.to_datetime(race_date_str)

    horse_races = df[(df['horse_id'] == horse_id) & (df['track_name'] == track_name)].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')

    past_races = horse_races[horse_races['date_parsed'] < race_date_parsed]

    if len(past_races) == 0:
        return 0, 0  # 実績なし

    ranks = []
    for _, race in past_races.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)

    if ranks:
        return np.mean(ranks), len(ranks)
    else:
        return 0, 0

def calculate_distance_aptitude(df, horse_id, target_distance, race_date_str, tolerance=200):
    """距離適性を計算（±tolerance m）"""
    race_date_parsed = pd.to_datetime(race_date_str)

    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')
    horse_races['distance_num'] = pd.to_numeric(horse_races['distance'], errors='coerce')

    # 距離が近いレースを抽出
    similar_distance = horse_races[
        (horse_races['distance_num'] >= target_distance - tolerance) &
        (horse_races['distance_num'] <= target_distance + tolerance) &
        (horse_races['date_parsed'] < race_date_parsed)
    ]

    if len(similar_distance) == 0:
        return 0, 0

    ranks = []
    for _, race in similar_distance.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)

    if ranks:
        return np.mean(ranks), len(ranks)
    else:
        return 0, 0

def calculate_turn_direction_aptitude(df, horse_id, turn_direction, race_date_str):
    """回り方向適性を計算"""
    race_date_parsed = pd.to_datetime(race_date_str)

    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')

    # 該当する回り方向の競馬場でのレースを抽出
    direction_tracks = [track for track, direction in TRACK_TURN_DIRECTION.items()
                       if direction == turn_direction]

    direction_races = horse_races[
        (horse_races['track_name'].isin(direction_tracks)) &
        (horse_races['date_parsed'] < race_date_parsed)
    ]

    if len(direction_races) == 0:
        return 0, 0

    ranks = []
    for _, race in direction_races.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)

    if ranks:
        return np.mean(ranks), len(ranks)
    else:
        return 0, 0

def get_running_style_features(df, horse_id, race_date_str, max_results=10):
    """脚質特徴量を計算"""
    race_date_parsed = pd.to_datetime(race_date_str)

    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')

    past_races = horse_races[horse_races['date_parsed'] < race_date_parsed]
    past_races = past_races.sort_values('date_parsed', ascending=False).head(max_results)

    if len(past_races) == 0:
        return {
            'escape_rate': 0, 'leading_rate': 0, 'closing_rate': 0, 'pursuing_rate': 0,
            'avg_agari': 0, 'has_past_results': 0,
            'position_change_ability': 0, 'agari_stability': 0
        }

    style_counts = {'escape': 0, 'leading': 0, 'closing': 0, 'pursuing': 0}
    agari_times = []
    position_changes = []

    for _, race in past_races.iterrows():
        # Passage解析
        passage = race.get('Passage')
        positions = parse_passage_full(passage)
        early_pos = positions[0]
        late_pos = positions[3]

        style = classify_running_style(early_pos)
        if style:
            style_counts[style] += 1

        # 位置取り変化能力
        if early_pos and late_pos:
            position_changes.append(early_pos - late_pos)  # 正なら前進

        # 上がり3F
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
        'has_past_results': 1 if total > 0 else 0,
        'position_change_ability': np.mean(position_changes) if position_changes else 0,
        'agari_stability': np.std(agari_times) if len(agari_times) > 1 else 0
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

print("=" * 80)
print("次世代統合モデル訓練：展開予想＋トラックバイアス＋適性分析")
print("=" * 80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(MAIN_CSV,
                 encoding='utf-8', low_memory=False)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 訓練データ: 2020-2023年
train_df = df[
    (df['date_parsed'] >= '2020-01-01') &
    (df['date_parsed'] <= '2023-12-31')
].copy()

print(f"訓練データ: {len(train_df):,}件 (2020-2023年)")

# 特徴量抽出
print("\n特徴量抽出中（40次元以上の高度な特徴量）...")
train_races = train_df.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"訓練レース数: {len(train_races)}レース")

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

    # レース情報
    track_name = race_horses.iloc[0].get('track_name', '')
    distance = pd.to_numeric(race_horses.iloc[0].get('distance'), errors='coerce')
    course_type = race_horses.iloc[0].get('course_type', '')

    # 回り方向
    turn_direction = TRACK_TURN_DIRECTION.get(track_name, 'unknown')

    # 展開予想
    pace_scenario, escape_count = get_race_pace_scenario(race_horses)

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

        # 基本的な過去成績
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

        # 脚質特徴量（8次元）
        style_features = get_running_style_features(train_df, horse_id, race_date_str, max_results=10)

        # コース適性（6次元）
        track_avg_rank, track_races = calculate_track_aptitude(train_df, horse_id, track_name, race_date_str)
        distance_avg_rank, distance_races = calculate_distance_aptitude(train_df, horse_id, distance, race_date_str)
        turn_avg_rank, turn_races = calculate_turn_direction_aptitude(train_df, horse_id, turn_direction, race_date_str)

        # ペース適性（2次元）
        horse_style = 'unknown'
        if style_features['escape_rate'] > 0.5:
            horse_style = 'escape'
        elif style_features['leading_rate'] > 0.4:
            horse_style = 'leading'
        elif style_features['closing_rate'] > 0.4:
            horse_style = 'closing'
        else:
            horse_style = 'pursuing'

        # ペース適性スコア
        pace_advantage = 0
        if pace_scenario == 'high_pace':
            if horse_style in ['closing', 'pursuing']:
                pace_advantage = 1
            elif horse_style in ['escape', 'leading']:
                pace_advantage = -1
        elif pace_scenario == 'slow_pace':
            if horse_style in ['escape', 'leading']:
                pace_advantage = 1
            elif horse_style in ['closing', 'pursuing']:
                pace_advantage = -1

        # 逃げ競合度
        escape_competition = 1 if horse_style == 'escape' and escape_count >= 2 else 0

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

        # その他基本情報
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

        course_turf = 1 if course_type == '芝' else 0
        course_dirt = 1 if course_type == 'ダート' else 0

        track_condition = horse.get('track_condition')
        track_good = 1 if track_condition == '良' else 0

        # 特徴量ベクトル（42次元）
        feature_vector = [
            # 基本成績（6次元）
            avg_rank, std_rank, min_rank, max_rank,
            recent_win_rate, recent_top3_rate,

            # 人的要因（6次元）
            jockey_win_rate, jockey_top3_rate, jockey_races,
            trainer_win_rate, trainer_top3_rate, trainer_races,

            # 馬体情報（5次元）
            age, weight_diff, weight, np.log1p(odds), ninki,

            # レース条件（4次元）
            waku, course_turf, course_dirt, track_good,

            # 距離（1次元）
            distance / 1000 if pd.notna(distance) else 1.6,

            # 脚質特徴（8次元）
            style_features['escape_rate'],
            style_features['leading_rate'],
            style_features['closing_rate'],
            style_features['pursuing_rate'],
            style_features['avg_agari'],
            style_features['has_past_results'],
            style_features['position_change_ability'],
            style_features['agari_stability'],

            # コース適性（6次元）
            track_avg_rank if track_avg_rank > 0 else 8,
            track_races,
            distance_avg_rank if distance_avg_rank > 0 else 8,
            distance_races,
            turn_avg_rank if turn_avg_rank > 0 else 8,
            turn_races,

            # 展開予想（4次元）
            1 if pace_scenario == 'high_pace' else 0,
            1 if pace_scenario == 'slow_pace' else 0,
            pace_advantage,
            escape_competition,

            # 回り方向（2次元）
            1 if turn_direction == 'left' else 0,
            1 if turn_direction == 'right' else 0
        ]

        race_features.append(feature_vector)
        race_labels.append(rank)

    if len(race_features) >= 8:
        features_list.extend(race_features)
        labels_list.extend(race_labels)
        groups_list.append(len(race_features))

print(f"\n抽出完了: {len(features_list)}頭のデータ, {len(groups_list)}レース")

# 特徴量名（42次元）
feature_names = [
    # 基本成績
    'avg_rank', 'std_rank', 'min_rank', 'max_rank',
    'recent_win_rate', 'recent_top3_rate',
    # 人的要因
    'jockey_win_rate', 'jockey_top3_rate', 'jockey_races',
    'trainer_win_rate', 'trainer_top3_rate', 'trainer_races',
    # 馬体情報
    'age', 'weight_diff', 'weight', 'log_odds', 'ninki',
    # レース条件
    'waku', 'course_turf', 'course_dirt', 'track_good',
    # 距離
    'distance_km',
    # 脚質特徴
    'escape_rate', 'leading_rate', 'closing_rate', 'pursuing_rate',
    'avg_agari', 'has_past_results', 'position_change_ability', 'agari_stability',
    # コース適性
    'track_aptitude', 'track_experience',
    'distance_aptitude', 'distance_experience',
    'turn_aptitude', 'turn_experience',
    # 展開予想
    'is_high_pace', 'is_slow_pace', 'pace_advantage', 'escape_competition',
    # 回り方向
    'is_left_turn', 'is_right_turn'
]

X_train = np.array(features_list)
y_train = np.array(labels_list)
groups_train = np.array(groups_list)

train_data = lgb.Dataset(X_train, label=y_train, group=groups_train, feature_name=feature_names)

print(f"訓練データ: {X_train.shape}")
print(f"特徴量数: {len(feature_names)}次元")

# モデル訓練
print("\n" + "=" * 80)
print("次世代モデル訓練中...")
print("=" * 80)

params = {
    'objective': 'lambdarank',
    'metric': 'ndcg',
    'ndcg_eval_at': [1, 3, 5],
    'learning_rate': 0.05,
    'num_leaves': 63,
    'max_depth': -1,
    'min_data_in_leaf': 20,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'feature_pre_filter': False,
    'verbose': 1
}

model = lgb.train(
    params,
    train_data,
    num_boost_round=200,
    valid_sets=[train_data],
    valid_names=['train']
)

print("\n訓練完了！")

# 特徴量の重要度
print("\n【特徴量の重要度 TOP20】")
importance = model.feature_importance(importance_type='gain')
feature_importance = sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True)

for i, (name, imp) in enumerate(feature_importance[:20], 1):
    print(f"{i:2d}. {name:25s}: {imp:10.0f}")

# モデルを保存
model_path = r"C:\Users\bu158\Keiba_Shisaku20250928\lightgbm_model_advanced.pkl"
with open(model_path, 'wb') as f:
    pickle.dump({
        'model': model,
        'feature_names': feature_names,
        'params': params
    }, f)

print(f"\n次世代モデルを保存: {model_path}")

print("\n" + "=" * 80)
print("訓練完了！")
print("=" * 80)
