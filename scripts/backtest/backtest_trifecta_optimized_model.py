"""
3連単特化モデルでバックテスト
- 2着・3着予測改善を検証
- 31次元特徴量（28 + 3連単特化7次元）
"""
import pandas as pd
import json
import sys
import numpy as np
from itertools import combinations
import pickle
from data_config import MAIN_CSV, MAIN_JSON
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

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
    """3連単特化特徴量を計算"""
    race_date_parsed = pd.to_datetime(race_date_str)

    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')

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

print("=" * 80)
print("3連単特化モデル：バックテスト")
print("=" * 80)

# モデル読み込み
print("\n3連単特化モデル読み込み中...")
model_path = r"C:\Users\bu158\Keiba_Shisaku20250928\lightgbm_model_trifecta_optimized_fixed.pkl"
with open(model_path, 'rb') as f:
    model_data = pickle.load(f)
    model = model_data['model']
    feature_names = model_data['feature_names']

print(f"特徴量数: {len(feature_names)}次元")

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(MAIN_JSON)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年のデータ
target_races = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"対象: 2024年 {len(race_ids)}レース")

# 戦略と精度分析用
strategies = {
    'ワイド_1-2': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
    'ワイド_1軸流し': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
    'ワイド_BOX3頭': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
}

accuracy_stats = {
    'first_correct': 0,
    'second_correct': 0,
    'third_correct': 0,
    'trio_hit': 0,
    'trifecta_hit': 0,
    'total': 0
}

stats_cache = {}

for idx, race_id in enumerate(race_ids):
    if (idx + 1) % 500 == 0:
        print(f"  {idx + 1}/{len(race_ids)} レース処理中...")

    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_horses = race_horses.sort_values('Umaban')

    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue

    race_date_str = str(race_date)[:10]

    # 騎手・調教師統計
    if race_date_str not in stats_cache:
        stats_cache[race_date_str] = {
            'jockey': calculate_person_stats(df, 'JockeyName', race_date_str, months_back=12),
            'trainer': calculate_person_stats(df, 'TrainerName', race_date_str, months_back=12)
        }

    jockey_stats = stats_cache[race_date_str]['jockey']
    trainer_stats = stats_cache[race_date_str]['trainer']

    # 特徴量抽出
    horse_features = []
    horse_umabans = []
    actual_ranks = []

    for _, horse in race_horses.iterrows():
        horse_id = horse.get('horse_id')

        # 実際の着順
        actual_rank = pd.to_numeric(horse.get('Rank'), errors='coerce')
        if pd.isna(actual_rank):
            continue
        actual_ranks.append(int(actual_rank))

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

        # 馬の統計取得（31次元）
        stats = calculate_trifecta_features(df, horse_id, race_date_str, max_results=10)

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

            # 3連単特化（7）★新規★
            stats['closing_success_rate'],
            stats['position_stability'],
            stats['close_finish_rate'],
            stats['second_place_rate'],
            stats['third_place_rate'],
            stats['front_collapse_rate'],
            stats['late_charge_rate'],
        ]

        horse_features.append(feature_vector)
        horse_umabans.append(int(horse.get('Umaban', 0)))

    if len(horse_features) < 8 or len(actual_ranks) != len(horse_features):
        continue

    # 予測
    X = np.array(horse_features)
    predictions = model.predict(X)

    # 予測スコアが低い順にソート
    predicted_ranking = sorted(
        zip(horse_umabans, predictions, actual_ranks),
        key=lambda x: x[1]
    )

    # 実際の着順でソート
    actual_ranking = sorted(
        zip(horse_umabans, actual_ranks),
        key=lambda x: x[1]
    )

    pred_1st = predicted_ranking[0][0]
    pred_2nd = predicted_ranking[1][0]
    pred_3rd = predicted_ranking[2][0]

    actual_1st = actual_ranking[0][0]
    actual_2nd = actual_ranking[1][0]
    actual_3rd = actual_ranking[2][0]

    # 的中判定
    trio_hit = set([pred_1st, pred_2nd, pred_3rd]) == set([actual_1st, actual_2nd, actual_3rd])
    trifecta_hit = (pred_1st == actual_1st and pred_2nd == actual_2nd and pred_3rd == actual_3rd)

    accuracy_stats['first_correct'] += (pred_1st == actual_1st)
    accuracy_stats['second_correct'] += (pred_2nd == actual_2nd)
    accuracy_stats['third_correct'] += (pred_3rd == actual_3rd)
    accuracy_stats['trio_hit'] += trio_hit
    accuracy_stats['trifecta_hit'] += trifecta_hit
    accuracy_stats['total'] += 1

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data or 'ワイド' not in payout_data:
        continue

    wide_data = payout_data['ワイド']
    winning_pairs = wide_data.get('馬番', [])
    payouts = wide_data.get('払戻金', [])

    if not winning_pairs or not payouts:
        continue

    # ワイド 1-2
    strategies['ワイド_1-2']['total'] += 1
    strategies['ワイド_1-2']['cost'] += 100

    pred_pair = set([pred_1st, pred_2nd])
    for i in range(0, len(winning_pairs), 2):
        if i + 1 < len(winning_pairs):
            winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
            if pred_pair == winning_pair:
                payout_amount = payouts[i // 2]
                if payout_amount:
                    strategies['ワイド_1-2']['hit'] += 1
                    strategies['ワイド_1-2']['return'] += payout_amount
                break

    # ワイド 1軸流し（1-2, 1-3）
    strategies['ワイド_1軸流し']['total'] += 1
    strategies['ワイド_1軸流し']['cost'] += 200

    for pred_pair in [(pred_1st, pred_2nd), (pred_1st, pred_3rd)]:
        pair_set = set(pred_pair)
        for i in range(0, len(winning_pairs), 2):
            if i + 1 < len(winning_pairs):
                winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
                if pair_set == winning_pair:
                    payout_amount = payouts[i // 2]
                    if payout_amount:
                        strategies['ワイド_1軸流し']['hit'] += 1
                        strategies['ワイド_1軸流し']['return'] += payout_amount
                    break

    # ワイド BOX3頭
    strategies['ワイド_BOX3頭']['total'] += 1
    strategies['ワイド_BOX3頭']['cost'] += 300

    for pred_pair in combinations([pred_1st, pred_2nd, pred_3rd], 2):
        pair_set = set(pred_pair)
        for i in range(0, len(winning_pairs), 2):
            if i + 1 < len(winning_pairs):
                winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
                if pair_set == winning_pair:
                    payout_amount = payouts[i // 2]
                    if payout_amount:
                        strategies['ワイド_BOX3頭']['hit'] += 1
                        strategies['ワイド_BOX3頭']['return'] += payout_amount
                    break

print("\n" + "=" * 80)
print("【3連単特化モデルの結果】2024年")
print("=" * 80)

# 予測精度
print("\n【予測精度】")
print("-" * 80)
total = accuracy_stats['total']
print(f"総レース数: {total}レース")
print(f"\n1位的中率: {accuracy_stats['first_correct'] / total * 100:.1f}%")
print(f"2位的中率: {accuracy_stats['second_correct'] / total * 100:.1f}%")
print(f"3位的中率: {accuracy_stats['third_correct'] / total * 100:.1f}%")
print(f"\n3連複（順不同）的中率: {accuracy_stats['trio_hit'] / total * 100:.1f}%")
print(f"3連単（順番通り）的中率: {accuracy_stats['trifecta_hit'] / total * 100:.1f}%")

# 回収率
print("\n【回収率】")
print("-" * 80)
print("戦略           | レース数 | 的中数 | 的中率 | 投資額     | 払戻額     | 回収率 | 損益")
print("-" * 90)

for name, result in strategies.items():
    if result['total'] > 0:
        hit_rate = result['hit'] / result['total'] * 100
        recovery = result['return'] / result['cost'] * 100 if result['cost'] > 0 else 0
        profit = result['return'] - result['cost']

        print(f"{name:15s} | {result['total']:4d}R | {result['hit']:4d}回 | {hit_rate:5.1f}% | "
              f"{result['cost']:10,}円 | {result['return']:10,}円 | {recovery:6.1f}% | {profit:+10,}円")

print("\n" + "=" * 80)
print("バックテスト完了")
print("=" * 80)
