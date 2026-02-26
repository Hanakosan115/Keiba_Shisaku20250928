"""
3連単特化モデル - 2着・3着予測改善版
新特徴量:
1. 差し脚評価（後方から巻き返し成功率）
2. 位置取り安定性（コーナーでのブレの少なさ）
3. 接戦での粘り強さ
4. ペース別成績
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
import pickle
from data_config import MAIN_CSV

print("=" * 80)
print("3連単特化モデル訓練")
print("=" * 80)

def parse_passage_full(passage_str):
    """Passage文字列を完全解析"""
    if pd.isna(passage_str) or passage_str == '':
        return [None, None, None, None]
    try:
        positions = [int(p) for p in str(passage_str).split('-')]
        if len(positions) == 2:
            return [positions[0], None, None, positions[1]]
        elif len(positions) == 4:
            return positions
        else:
            return [None, None, None, None]
    except:
        return [None, None, None, None]

def classify_running_style(early_position):
    """脚質分類"""
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

def calculate_trifecta_features(horse_races):
    """3連単に特化した特徴量を計算"""
    if len(horse_races) == 0:
        return {
            # 基本成績
            'avg_rank': 8, 'std_rank': 0, 'race_count': 0,
            'win_rate': 0, 'top3_rate': 0,
            # 脚質
            'escape_rate': 0, 'leading_rate': 0, 'closing_rate': 0, 'pursuing_rate': 0,
            'avg_agari': 0,
            # 2着・3着特化
            'closing_success_rate': 0,      # 後方→3着以内率
            'position_stability': 0,         # 位置安定性
            'close_finish_rate': 0,          # 接戦成績
            'second_place_rate': 0,          # 2着率
            'third_place_rate': 0,           # 3着率
            'front_collapse_rate': 0,        # 先行→崩れ率
            'late_charge_rate': 0,           # 追い込み成功率
        }

    ranks = pd.to_numeric(horse_races['Rank'], errors='coerce').dropna()

    # 基本成績
    features = {
        'avg_rank': ranks.mean() if len(ranks) > 0 else 8,
        'std_rank': ranks.std() if len(ranks) > 1 else 0,
        'race_count': len(ranks),
        'win_rate': (ranks == 1).sum() / len(ranks) if len(ranks) > 0 else 0,
        'top3_rate': (ranks <= 3).sum() / len(ranks) if len(ranks) > 0 else 0,
    }

    # 脚質と位置取り分析
    styles = {'escape': 0, 'leading': 0, 'closing': 0, 'pursuing': 0}
    agari_times = []

    # 3連単特化指標
    closing_success = 0    # 後方→3着以内
    position_changes = []  # 位置変化
    close_finishes = 0     # 接戦（1秒差以内）
    second_places = 0      # 2着
    third_places = 0       # 3着
    front_collapses = 0    # 先行→4着以下
    late_charges = 0       # 差し・追込→3着以内

    for _, race in horse_races.iterrows():
        passage = race.get('Passage')
        positions = parse_passage_full(passage)

        early_pos = positions[0]
        late_pos = positions[3]

        # 脚質分類
        style = classify_running_style(early_pos)
        if style:
            styles[style] += 1

        # 上がり3F
        agari = pd.to_numeric(race.get('Agari'), errors='coerce')
        if pd.notna(agari) and agari > 0:
            agari_times.append(agari)

        # 着順
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')

        # 位置変化
        if early_pos is not None and late_pos is not None:
            position_changes.append(abs(late_pos - early_pos))

        # 差し脚評価（後方→好走）
        if early_pos is not None and rank is not None:
            if early_pos > 8 and rank <= 3:
                closing_success += 1

            # 差し・追込→3着以内
            if style in ['closing', 'pursuing'] and rank <= 3:
                late_charges += 1

            # 先行→崩れ
            if style in ['escape', 'leading'] and rank > 3:
                front_collapses += 1

        # 着順カウント
        if rank == 2:
            second_places += 1
        elif rank == 3:
            third_places += 1

        # 接戦判定（Diff列があれば）
        diff = race.get('Diff', '')
        if isinstance(diff, str) and diff != '':
            # "0.1"や"クビ"などの場合は接戦
            try:
                diff_val = float(diff)
                if diff_val <= 1.0:
                    close_finishes += 1
            except:
                if 'クビ' in diff or 'ハナ' in diff or 'アタマ' in diff:
                    close_finishes += 1

    total_races = len(horse_races)

    # 脚質率
    features['escape_rate'] = styles['escape'] / total_races
    features['leading_rate'] = styles['leading'] / total_races
    features['closing_rate'] = styles['closing'] / total_races
    features['pursuing_rate'] = styles['pursuing'] / total_races
    features['avg_agari'] = np.mean(agari_times) if agari_times else 0

    # 3連単特化特徴
    features['closing_success_rate'] = closing_success / total_races
    features['position_stability'] = 1 / (1 + np.mean(position_changes)) if position_changes else 0
    features['close_finish_rate'] = close_finishes / total_races
    features['second_place_rate'] = second_places / total_races
    features['third_place_rate'] = third_places / total_races
    features['front_collapse_rate'] = front_collapses / max(styles['escape'] + styles['leading'], 1)
    features['late_charge_rate'] = late_charges / max(styles['closing'] + styles['pursuing'], 1)

    return features

print("\nデータ読み込み中...")
df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 訓練データ: 2020-2023年
train_df = df[(df['date_parsed'] >= '2020-01-01') & (df['date_parsed'] < '2024-01-01')]
print(f"訓練データ: {len(train_df):,}件")

# 馬ごとの統計を事前計算
print("\n馬ごとの3連単特化特徴量を計算中...")
horse_stats = {}

for horse_id in train_df['horse_id'].dropna().unique():
    horse_races = train_df[train_df['horse_id'] == horse_id]
    horse_stats[horse_id] = calculate_trifecta_features(horse_races)

print(f"計算完了: {len(horse_stats):,}頭")

# 騎手・調教師統計
print("\n騎手・調教師統計計算中...")
jockey_stats = {}
for jockey in train_df['JockeyName'].dropna().unique():
    jockey_races = train_df[train_df['JockeyName'] == jockey]
    ranks = pd.to_numeric(jockey_races['Rank'], errors='coerce').dropna()
    if len(ranks) > 0:
        jockey_stats[jockey] = {
            'win_rate': (ranks == 1).sum() / len(ranks),
            'top3_rate': (ranks <= 3).sum() / len(ranks),
        }

trainer_stats = {}
for trainer in train_df['TrainerName'].dropna().unique():
    trainer_races = train_df[train_df['TrainerName'] == trainer]
    ranks = pd.to_numeric(trainer_races['Rank'], errors='coerce').dropna()
    if len(ranks) > 0:
        trainer_stats[trainer] = {
            'win_rate': (ranks == 1).sum() / len(ranks),
            'top3_rate': (ranks <= 3).sum() / len(ranks),
        }

# レース単位で特徴量抽出
print("\nレース単位の特徴量抽出中...")
X_train = []
y_train = []
race_groups = []  # 実際に追加されたレースごとの馬数を記録

race_ids = train_df.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()
print(f"対象レース数: {len(race_ids):,}レース")

processed = 0
for race_id in race_ids:
    processed += 1
    if processed % 1000 == 0:
        print(f"  進捗: {processed}/{len(race_ids)} ({processed/len(race_ids)*100:.1f}%)")

    race_data = train_df[train_df['race_id'] == race_id]
    race_horse_count = 0  # このレースで実際に追加された馬数

    for _, horse in race_data.iterrows():
        horse_id = horse.get('horse_id')

        # 基本情報
        age = pd.to_numeric(horse.get('Age'), errors='coerce')
        age = age if pd.notna(age) else 4

        weight_diff = pd.to_numeric(horse.get('WeightDiff'), errors='coerce')
        weight_diff = weight_diff if pd.notna(weight_diff) else 0

        weight = pd.to_numeric(horse.get('Weight'), errors='coerce')
        weight = weight if pd.notna(weight) else 480

        odds = pd.to_numeric(horse.get('Odds_x'), errors='coerce')
        if pd.isna(odds) or odds <= 0:
            odds = pd.to_numeric(horse.get('Odds_y'), errors='coerce')
        odds = odds if pd.notna(odds) and odds > 0 else 10

        ninki = pd.to_numeric(horse.get('Ninki'), errors='coerce')
        ninki = ninki if pd.notna(ninki) else 8

        waku = pd.to_numeric(horse.get('Waku'), errors='coerce')
        waku = waku if pd.notna(waku) else 4

        # レース条件
        course_type = horse.get('course_type', '')
        course_turf = 1 if '芝' in str(course_type) else 0
        course_dirt = 1 if 'ダ' in str(course_type) else 0

        track_condition = horse.get('track_condition', '')
        track_good = 1 if '良' in str(track_condition) else 0

        distance = pd.to_numeric(horse.get('distance'), errors='coerce')
        distance = distance if pd.notna(distance) else 1600

        # 馬の統計取得
        stats = horse_stats.get(horse_id, calculate_trifecta_features(pd.DataFrame()))

        # 騎手・調教師統計
        jockey = jockey_stats.get(horse.get('JockeyName'), {'win_rate': 0, 'top3_rate': 0})
        trainer = trainer_stats.get(horse.get('TrainerName'), {'win_rate': 0, 'top3_rate': 0})

        # 特徴量ベクトル作成（38次元）
        feature_vector = [
            # 基本成績（5）
            stats['avg_rank'], stats['std_rank'], stats['race_count'],
            stats['win_rate'], stats['top3_rate'],

            # 騎手・調教師（4）
            jockey['win_rate'], jockey['top3_rate'],
            trainer['win_rate'], trainer['top3_rate'],

            # 馬体・オッズ（5）
            age, weight_diff, weight, np.log1p(odds), ninki,

            # レース条件（4）
            waku, course_turf, course_dirt, track_good,

            # 距離（1）
            distance / 1000,

            # 脚質（5）
            stats['escape_rate'], stats['leading_rate'], stats['closing_rate'],
            stats['pursuing_rate'], stats['avg_agari'],

            # 3連単特化（7）★新規★
            stats['closing_success_rate'],
            stats['position_stability'],
            stats['close_finish_rate'],
            stats['second_place_rate'],
            stats['third_place_rate'],
            stats['front_collapse_rate'],
            stats['late_charge_rate'],
        ]

        # ターゲット
        rank = pd.to_numeric(horse.get('Rank'), errors='coerce')
        if pd.notna(rank):
            X_train.append(feature_vector)
            y_train.append(rank)
            race_horse_count += 1  # このレースで追加された馬をカウント

    # このレースで馬が追加されていればグループに記録
    if race_horse_count > 0:
        race_groups.append(race_horse_count)

X_train = np.array(X_train)
y_train = np.array(y_train)

print(f"\n訓練データ: {len(X_train):,}件")
print(f"特徴量次元: {X_train.shape[1]}次元")

# LightGBM訓練
print("\nLightGBMモデル訓練中...")
print(f"グループ数: {len(race_groups)}レース")
print(f"グループ合計: {sum(race_groups)}件 (X_trainと一致: {sum(race_groups) == len(X_train)})")

params = {
    'objective': 'lambdarank',
    'metric': 'ndcg',
    'ndcg_eval_at': [1, 3, 5],
    'num_leaves': 127,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': -1,
    'seed': 42
}

lgb_train = lgb.Dataset(X_train, y_train, group=race_groups)

model = lgb.train(
    params,
    lgb_train,
    num_boost_round=500,
    valid_sets=[lgb_train],
    valid_names=['train'],
)

print("訓練完了")

# モデル保存
feature_names = [
    'avg_rank', 'std_rank', 'race_count', 'win_rate', 'top3_rate',
    'jockey_win', 'jockey_top3', 'trainer_win', 'trainer_top3',
    'age', 'weight_diff', 'weight', 'log_odds', 'ninki',
    'waku', 'course_turf', 'course_dirt', 'track_good', 'distance',
    'escape_rate', 'leading_rate', 'closing_rate', 'pursuing_rate', 'avg_agari',
    'closing_success', 'position_stability', 'close_finish',
    'second_rate', 'third_rate', 'front_collapse', 'late_charge'
]

model_data = {
    'model': model,
    'feature_names': feature_names,
    'params': params
}

output_path = 'lightgbm_model_trifecta_optimized.pkl'
with open(output_path, 'wb') as f:
    pickle.dump(model_data, f)

print(f"\nモデル保存: {output_path}")

# 特徴量重要度
print("\n" + "=" * 80)
print("特徴量重要度 TOP10")
print("=" * 80)
importance = model.feature_importance(importance_type='gain')
feature_importance = sorted(zip(feature_names, importance), key=lambda x: x[1], reverse=True)

for i, (name, imp) in enumerate(feature_importance[:10], 1):
    print(f"{i:2d}. {name:25s}: {imp:>10,.0f}")

print("\n" + "=" * 80)
print("訓練完了")
print("=" * 80)
print("\n次のステップ: バックテストで効果を検証")
print("  python backtest_trifecta_optimized_model.py")
