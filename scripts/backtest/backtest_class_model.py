"""
クラス情報を含むモデルのバックテスト

新モデル vs 旧モデルの性能比較
"""

import pandas as pd
import numpy as np
import pickle
import json
from itertools import combinations
import sys

sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

def parse_passage(passage_str):
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
print("クラス情報モデル vs 旧モデル バックテスト比較")
print("="*80)

# モデル読み込み
print("\nモデル読み込み中...")

# 新モデル（クラス情報あり）
with open('lightgbm_model_with_class_info.pkl', 'rb') as f:
    new_model_data = pickle.load(f)
    new_model = new_model_data['model']
print("  新モデル（クラス情報あり）: OK")

# 旧モデル（脚質のみ）- 特徴量次元の問題でスキップ
has_old_model = False
print("  旧モデル: スキップ（新モデル単独でテスト）")

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_clean_with_class.csv',
                 encoding='utf-8', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年のデータでテスト
test_races = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
]

race_ids = test_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()
print(f"対象: 2024年 {len(race_ids):,}レース")

# 戦略定義
strategies = {
    'ワイド_1-3': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
    '3連複_BOX5頭': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
}

# 統計キャッシュ
stats_cache = {}

# 各モデルの結果
results = {
    'new_model': {'strategies': {k: v.copy() for k, v in strategies.items()}},
}

if has_old_model:
    results['old_model'] = {'strategies': {k: v.copy() for k, v in strategies.items()}}

print("\nバックテスト実行中...")

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

    if race_date_str not in stats_cache:
        stats_cache[race_date_str] = {
            'jockey': calculate_person_stats(df, 'JockeyName', race_date_str),
            'trainer': calculate_person_stats(df, 'TrainerName', race_date_str)
        }

    jockey_stats = stats_cache[race_date_str]['jockey']
    trainer_stats = stats_cache[race_date_str]['trainer']

    # 各馬の特徴量を計算
    horse_features_new = []
    horse_features_old = []
    umaban_list = []

    for _, horse in race_horses.iterrows():
        horse_id = horse.get('horse_id')
        umaban = horse.get('Umaban')
        umaban_list.append(umaban)

        # 過去成績
        recent_ranks = get_recent_ranks(df, horse_id, race_date_str, max_results=5)

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

        # 脚質
        style_dist = get_running_style_features(df, horse_id, race_date_str)

        # 騎手・調教師
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

        # その他
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

        # 旧モデル用特徴量（27次元）
        feature_old = [
            avg_rank, std_rank, min_rank, max_rank,
            recent_win_rate, recent_top3_rate,
            jockey_win_rate, jockey_top3_rate, jockey_races,
            trainer_win_rate, trainer_top3_rate, trainer_races,
            age, weight_diff, weight, np.log1p(odds), ninki, waku,
            course_turf, course_dirt, track_good, distance / 1000,
            style_dist['escape_rate'],
            style_dist['leading_rate'],
            style_dist['closing_rate'],
            style_dist['pursuing_rate'],
            style_dist['avg_agari']
        ]

        # 新モデル用特徴量（32次元 = 27 + 5）
        race_class_rank = pd.to_numeric(horse.get('race_class_rank'), errors='coerce')
        race_class_rank = race_class_rank if pd.notna(race_class_rank) else 0

        prev_race_class_rank = pd.to_numeric(horse.get('prev_race_class_rank'), errors='coerce')
        prev_race_class_rank = prev_race_class_rank if pd.notna(prev_race_class_rank) else 0

        class_change = horse.get('class_change', 'same')
        is_promotion = 1 if class_change == 'promotion' else 0
        is_demotion = 1 if class_change == 'demotion' else 0
        is_debut = 1 if class_change == 'debut' else 0

        class_rank_diff = race_class_rank - prev_race_class_rank if prev_race_class_rank != 0 else 0

        feature_new = feature_old + [
            race_class_rank,
            is_promotion,
            is_demotion,
            is_debut,
            class_rank_diff
        ]

        horse_features_new.append(feature_new)
        if has_old_model:
            horse_features_old.append(feature_old)

    if len(horse_features_new) == 0:
        continue

    # 予測
    X_new = np.array(horse_features_new)
    pred_new = new_model.predict(X_new)

    if has_old_model:
        X_old = np.array(horse_features_old)
        pred_old = old_model.predict(X_old)

    # 予測順位（スコアが低いほど上位）
    pred_rank_new = np.argsort(pred_new)
    top3_new = [umaban_list[i] for i in pred_rank_new[:3]]

    if has_old_model:
        pred_rank_old = np.argsort(pred_old)
        top3_old = [umaban_list[i] for i in pred_rank_old[:3]]

    # 実際の結果
    race_horses['Rank_num'] = pd.to_numeric(race_horses['Rank'], errors='coerce')
    actual_result = race_horses.dropna(subset=['Rank_num']).sort_values('Rank_num')
    actual_top3 = actual_result.head(3)['Umaban'].tolist()

    if len(actual_top3) < 3:
        continue

    # 馬券判定（ワイド1-3）
    wide_hit_new = len(set(top3_new) & set(actual_top3)) >= 2
    if has_old_model:
        wide_hit_old = len(set(top3_old) & set(actual_top3)) >= 2

    results['new_model']['strategies']['ワイド_1-3']['total'] += 1
    results['new_model']['strategies']['ワイド_1-3']['cost'] += 100
    if wide_hit_new:
        results['new_model']['strategies']['ワイド_1-3']['hit'] += 1

    if has_old_model:
        results['old_model']['strategies']['ワイド_1-3']['total'] += 1
        results['old_model']['strategies']['ワイド_1-3']['cost'] += 100
        if wide_hit_old:
            results['old_model']['strategies']['ワイド_1-3']['hit'] += 1

    # 3連複BOX5頭
    top5_new = [umaban_list[i] for i in pred_rank_new[:5]]
    sanrenpuku_hit_new = len(set(top5_new) & set(actual_top3)) == 3

    if has_old_model:
        top5_old = [umaban_list[i] for i in pred_rank_old[:5]]
        sanrenpuku_hit_old = len(set(top5_old) & set(actual_top3)) == 3

    results['new_model']['strategies']['3連複_BOX5頭']['total'] += 1
    results['new_model']['strategies']['3連複_BOX5頭']['cost'] += 1000
    if sanrenpuku_hit_new:
        results['new_model']['strategies']['3連複_BOX5頭']['hit'] += 1

    if has_old_model:
        results['old_model']['strategies']['3連複_BOX5頭']['total'] += 1
        results['old_model']['strategies']['3連複_BOX5頭']['cost'] += 1000
        if sanrenpuku_hit_old:
            results['old_model']['strategies']['3連複_BOX5頭']['hit'] += 1

# 結果表示
print("\n" + "="*80)
print("結果比較")
print("="*80)

print("\n【新モデル（クラス情報あり）】")
for strategy_name, stats in results['new_model']['strategies'].items():
    if stats['total'] > 0:
        hit_rate = 100 * stats['hit'] / stats['total']
        print(f"\n{strategy_name}:")
        print(f"  的中率: {hit_rate:.1f}% ({stats['hit']}/{stats['total']})")

if has_old_model:
    print("\n【旧モデル（脚質のみ）】")
    for strategy_name, stats in results['old_model']['strategies'].items():
        if stats['total'] > 0:
            hit_rate = 100 * stats['hit'] / stats['total']
            print(f"\n{strategy_name}:")
            print(f"  的中率: {hit_rate:.1f}% ({stats['hit']}/{stats['total']})")

    print("\n【改善効果】")
    for strategy_name in strategies.keys():
        new_rate = 100 * results['new_model']['strategies'][strategy_name]['hit'] / \
                   max(results['new_model']['strategies'][strategy_name]['total'], 1)
        old_rate = 100 * results['old_model']['strategies'][strategy_name]['hit'] / \
                   max(results['old_model']['strategies'][strategy_name]['total'], 1)
        diff = new_rate - old_rate

        print(f"\n{strategy_name}:")
        print(f"  的中率: {new_rate:.1f}% → {old_rate:.1f}% ({diff:+.1f}%)")

print("\n完了！")
