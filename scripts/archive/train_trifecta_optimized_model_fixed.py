"""
3連単特化モデル - 2着・3着予測改善版（データリーク修正）
修正点: 訓練時も各レースの日付より前のデータのみから特徴量を計算
"""
import pandas as pd
import numpy as np
import lightgbm as lgb
import pickle
from data_config import MAIN_CSV

print("=" * 80)
print("3連単特化モデル訓練（データリーク修正版）")
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

def calculate_trifecta_features(df, horse_id, race_date_str, max_results=10):
    """3連単特化特徴量を計算（過去データのみ使用）"""
    race_date_parsed = pd.to_datetime(race_date_str)

    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')

    # レース日より前のデータのみ
    past_races = horse_races[horse_races['date_parsed'] < race_date_parsed]
    past_races = past_races.sort_values('date_parsed', ascending=False).head(max_results)

    if len(past_races) == 0:
        return {
            'avg_rank': 8, 'std_rank': 0, 'race_count': 0,
            'win_rate': 0, 'top3_rate': 0,
            'escape_rate': 0, 'leading_rate': 0, 'closing_rate': 0, 'pursuing_rate': 0,
            'avg_agari': 0,
            'closing_success_rate': 0, 'position_stability': 0, 'close_finish_rate': 0,
            'second_place_rate': 0, 'third_place_rate': 0,
            'front_collapse_rate': 0, 'late_charge_rate': 0,
        }

    ranks = pd.to_numeric(past_races['Rank'], errors='coerce').dropna()

    features = {
        'avg_rank': ranks.mean() if len(ranks) > 0 else 8,
        'std_rank': ranks.std() if len(ranks) > 1 else 0,
        'race_count': len(ranks),
        'win_rate': (ranks == 1).sum() / len(ranks) if len(ranks) > 0 else 0,
        'top3_rate': (ranks <= 3).sum() / len(ranks) if len(ranks) > 0 else 0,
    }

    # 脚質と3連単特化指標
    styles = {'escape': 0, 'leading': 0, 'closing': 0, 'pursuing': 0}
    agari_times = []
    closing_success = 0
    position_changes = []
    close_finishes = 0
    second_places = 0
    third_places = 0
    front_collapses = 0
    late_charges = 0

    for _, race in past_races.iterrows():
        passage = race.get('Passage')
        positions = parse_passage_full(passage)

        early_pos = positions[0]
        late_pos = positions[3]

        style = classify_running_style(early_pos)
        if style:
            styles[style] += 1

        agari = pd.to_numeric(race.get('Agari'), errors='coerce')
        if pd.notna(agari) and agari > 0:
            agari_times.append(agari)

        rank = pd.to_numeric(race.get('Rank'), errors='coerce')

        # 位置変化
        if early_pos is not None and late_pos is not None:
            position_changes.append(abs(late_pos - early_pos))

        # 差し脚評価
        if early_pos is not None and rank is not None:
            if early_pos > 8 and rank <= 3:
                closing_success += 1

            if style in ['closing', 'pursuing'] and rank <= 3:
                late_charges += 1

            if style in ['escape', 'leading'] and rank > 3:
                front_collapses += 1

        # 着順カウント
        if rank == 2:
            second_places += 1
        elif rank == 3:
            third_places += 1

        # 接戦判定
        diff = race.get('Diff', '')
        if isinstance(diff, str) and diff != '':
            try:
                diff_val = float(diff)
                if diff_val <= 1.0:
                    close_finishes += 1
            except:
                if 'クビ' in diff or 'ハナ' in diff or 'アタマ' in diff:
                    close_finishes += 1

    total_races = len(past_races)

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
            }

    return person_stats

print("\nデータ読み込み中...")
df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 訓練データ: 2020-2023年
train_df = df[(df['date_parsed'] >= '2020-01-01') & (df['date_parsed'] < '2024-01-01')]
print(f"訓練データ: {len(train_df):,}件")

# レース単位で特徴量抽出
print("\nレース単位の特徴量抽出中...")
X_train = []
y_train = []
race_groups = []

race_ids = train_df.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()
print(f"対象レース数: {len(race_ids):,}レース")

stats_cache = {}
processed = 0

for race_id in race_ids:
    processed += 1
    if processed % 1000 == 0:
        print(f"  進捗: {processed}/{len(race_ids)} ({processed/len(race_ids)*100:.1f}%)")

    race_data = train_df[train_df['race_id'] == race_id]
    race_horse_count = 0

    # レース日付取得
    race_date = race_data.iloc[0]['date']
    if pd.isna(race_date):
        continue
    race_date_str = str(race_date)[:10]

    # 騎手・調教師統計（キャッシュ）
    if race_date_str not in stats_cache:
        stats_cache[race_date_str] = {
            'jockey': calculate_person_stats(train_df, 'JockeyName', race_date_str, months_back=12),
            'trainer': calculate_person_stats(train_df, 'TrainerName', race_date_str, months_back=12)
        }

    jockey_stats = stats_cache[race_date_str]['jockey']
    trainer_stats = stats_cache[race_date_str]['trainer']

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

        # 馬の統計取得（過去データのみ）
        stats = calculate_trifecta_features(train_df, horse_id, race_date_str, max_results=10)

        # 騎手・調教師統計
        jockey = jockey_stats.get(horse.get('JockeyName'), {'win_rate': 0, 'top3_rate': 0})
        trainer = trainer_stats.get(horse.get('TrainerName'), {'win_rate': 0, 'top3_rate': 0})

        # 特徴量ベクトル作成（31次元）
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

            # 3連単特化（7）
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
            race_horse_count += 1

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

output_path = 'lightgbm_model_trifecta_optimized_fixed.pkl'
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
