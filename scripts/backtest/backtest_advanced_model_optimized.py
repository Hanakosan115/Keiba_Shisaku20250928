"""
次世代統合モデル（42次元）のバックテスト - 最適化版
パフォーマンス改善:
1. 事前に馬ごとの統計情報を計算・キャッシュ
2. DataFrame操作の最小化
3. 進捗表示の追加
4. 回収率計算の追加
"""
import pandas as pd
import numpy as np
import pickle
import json
from datetime import datetime
from collections import defaultdict
from itertools import combinations
from data_config import MAIN_CSV, MAIN_JSON

print("=" * 80)
print("次世代統合モデル（42次元）のバックテスト - 最適化版")
print("=" * 80)

def load_payout_data(json_path):
    """払戻金データを読み込む"""
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

# 競馬場の回り方向マスタデータ
TRACK_TURN_DIRECTION = {
    '東京': 'left', '中山': 'right', '阪神': 'right', '京都': 'right',
    '中京': 'left', '新潟': 'left', '福島': 'right', '小倉': 'right',
    '札幌': 'right', '函館': 'right'
}

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

print("\nステップ1: データ読み込み")
df = pd.read_csv(MAIN_CSV,
                 encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(MAIN_JSON)

print(f"総データ数: {len(df):,}件")
print(f"払戻金データ: {len(payout_dict):,}レース")

# 日付パース
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# テストデータ: 2024年
test_df = df[(df['date_parsed'] >= '2024-01-01') & (df['date_parsed'] <= '2024-12-31')].copy()
print(f"テストデータ（2024年）: {len(test_df):,}件")

# 訓練データ: 2024年以前（統計計算用）
train_df = df[df['date_parsed'] < '2024-01-01'].copy()
print(f"訓練データ（2024年以前）: {len(train_df):,}件")

print("\nステップ2: 馬ごとの統計情報を事前計算")
print("これにより、バックテスト中の繰り返し計算を回避します...")

# 馬ごとの基本統計
horse_stats = {}

for horse_id in train_df['horse_id'].dropna().unique():
    horse_races = train_df[train_df['horse_id'] == horse_id]

    # 基本成績
    ranks = pd.to_numeric(horse_races['Rank'], errors='coerce').dropna()

    if len(ranks) > 0:
        stats = {
            'avg_rank': ranks.mean(),
            'std_rank': ranks.std() if len(ranks) > 1 else 0,
            'min_rank': ranks.min(),
            'max_rank': ranks.max(),
            'race_count': len(ranks),
            'win_count': (ranks == 1).sum(),
            'top3_count': (ranks <= 3).sum()
        }

        # 脚質分析
        styles = {'escape': 0, 'leading': 0, 'closing': 0, 'pursuing': 0}
        agari_times = []
        position_changes = []

        for _, race in horse_races.iterrows():
            passage = race.get('Passage')
            positions = parse_passage_full(passage)

            early_pos = positions[0]
            late_pos = positions[3]

            style = classify_running_style(early_pos)
            if style:
                styles[style] += 1

            agari = pd.to_numeric(race.get('Agari'), errors='coerce')
            if pd.notna(agari):
                agari_times.append(agari)

            if early_pos is not None and late_pos is not None:
                position_changes.append(late_pos - early_pos)

        total_races = len(horse_races)
        stats['escape_rate'] = styles['escape'] / total_races
        stats['leading_rate'] = styles['leading'] / total_races
        stats['closing_rate'] = styles['closing'] / total_races
        stats['pursuing_rate'] = styles['pursuing'] / total_races
        stats['avg_agari'] = np.mean(agari_times) if agari_times else 0
        stats['agari_stability'] = np.std(agari_times) if len(agari_times) > 1 else 0
        stats['position_change_ability'] = np.mean(position_changes) if position_changes else 0

        # 競馬場別成績（簡易版）
        stats['track_performance'] = {}
        for track in horse_races['track_name'].unique():
            track_races = horse_races[horse_races['track_name'] == track]
            track_ranks = pd.to_numeric(track_races['Rank'], errors='coerce').dropna()
            if len(track_ranks) > 0:
                stats['track_performance'][track] = {
                    'avg_rank': track_ranks.mean(),
                    'count': len(track_ranks)
                }

        # 距離別成績（簡易版）
        horse_races['distance_num'] = pd.to_numeric(horse_races['distance'], errors='coerce')
        stats['distance_performance'] = {}
        for distance in [1200, 1400, 1600, 1800, 2000, 2200, 2400]:
            dist_races = horse_races[
                (horse_races['distance_num'] >= distance - 200) &
                (horse_races['distance_num'] <= distance + 200)
            ]
            dist_ranks = pd.to_numeric(dist_races['Rank'], errors='coerce').dropna()
            if len(dist_ranks) > 0:
                stats['distance_performance'][distance] = {
                    'avg_rank': dist_ranks.mean(),
                    'count': len(dist_ranks)
                }

        horse_stats[horse_id] = stats

print(f"統計情報を計算した馬の数: {len(horse_stats):,}頭")

# 騎手・調教師統計も事前計算
print("\nステップ3: 騎手・調教師統計を事前計算")

jockey_stats = {}
for jockey in train_df['JockeyName'].dropna().unique():
    jockey_races = train_df[train_df['JockeyName'] == jockey]
    ranks = pd.to_numeric(jockey_races['Rank'], errors='coerce').dropna()

    if len(ranks) > 0:
        jockey_stats[jockey] = {
            'win_rate': (ranks == 1).sum() / len(ranks),
            'top3_rate': (ranks <= 3).sum() / len(ranks),
            'race_count': len(ranks)
        }

trainer_stats = {}
for trainer in train_df['TrainerName'].dropna().unique():
    trainer_races = train_df[train_df['TrainerName'] == trainer]
    ranks = pd.to_numeric(trainer_races['Rank'], errors='coerce').dropna()

    if len(ranks) > 0:
        trainer_stats[trainer] = {
            'win_rate': (ranks == 1).sum() / len(ranks),
            'top3_rate': (ranks <= 3).sum() / len(ranks),
            'race_count': len(ranks)
        }

print(f"騎手統計: {len(jockey_stats):,}人")
print(f"調教師統計: {len(trainer_stats):,}人")

print("\nステップ4: モデル読み込み")
with open('lightgbm_model_advanced.pkl', 'rb') as f:
    model_data = pickle.load(f)
    model = model_data['model']

print("モデル読み込み完了")

print("\nステップ5: バックテスト実行")
race_ids = test_df['race_id'].unique()
print(f"テスト対象レース数: {len(race_ids)}レース")

# 投資戦略の追跡
strategies = {
    'ワイド_1-2': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
    'ワイド_1軸流し': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
    'ワイド_BOX3頭': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
}

results = []
processed = 0

for race_id in race_ids:
    processed += 1
    if processed % 100 == 0:
        print(f"  進捗: {processed}/{len(race_ids)} レース ({processed/len(race_ids)*100:.1f}%)")

    race_data = test_df[test_df['race_id'] == race_id]

    # レース全体の展開予想
    escape_count = 0
    for _, horse in race_data.iterrows():
        horse_id = horse.get('horse_id')
        if horse_id in horse_stats:
            if horse_stats[horse_id]['escape_rate'] > 0.5:
                escape_count += 1

    if escape_count >= 2:
        pace_scenario = 'high_pace'
    elif escape_count == 1:
        pace_scenario = 'slow_pace'
    else:
        pace_scenario = 'average_pace'

    # 各馬の特徴量抽出
    horses = []
    for _, horse in race_data.iterrows():
        horse_id = horse.get('horse_id')
        umaban = horse['Umaban']

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

        track_name = horse.get('track_name', '')
        turn_direction = TRACK_TURN_DIRECTION.get(track_name, 'unknown')

        # 馬の統計情報を取得
        if horse_id in horse_stats:
            stats = horse_stats[horse_id]

            # 競馬場適性
            track_perf = stats['track_performance'].get(track_name, {'avg_rank': 8, 'count': 0})
            track_avg_rank = track_perf['avg_rank']
            track_races = track_perf['count']

            # 距離適性（最も近い距離帯を使用）
            distance_key = min(stats['distance_performance'].keys(),
                             key=lambda x: abs(x - distance),
                             default=None)
            if distance_key:
                dist_perf = stats['distance_performance'][distance_key]
                distance_avg_rank = dist_perf['avg_rank']
                distance_races = dist_perf['count']
            else:
                distance_avg_rank = 8
                distance_races = 0

            # 回り方向適性（簡易版：左/右で平均）
            turn_avg_rank = stats['avg_rank']  # 簡略化
            turn_races = stats['race_count']

            # ペース適性
            if pace_scenario == 'high_pace':
                if stats['closing_rate'] + stats['pursuing_rate'] > 0.5:
                    pace_advantage = 1
                else:
                    pace_advantage = -1
            elif pace_scenario == 'slow_pace':
                if stats['escape_rate'] + stats['leading_rate'] > 0.5:
                    pace_advantage = 1
                else:
                    pace_advantage = -1
            else:
                pace_advantage = 0

            feature_vector = [
                # 基本成績（6次元）
                stats['avg_rank'], stats['std_rank'], stats['min_rank'], stats['max_rank'],
                stats['win_count'] / max(stats['race_count'], 1),
                stats['top3_count'] / max(stats['race_count'], 1),

                # 騎手統計（3次元）
                jockey_stats.get(horse.get('JockeyName'), {}).get('win_rate', 0),
                jockey_stats.get(horse.get('JockeyName'), {}).get('top3_rate', 0),
                jockey_stats.get(horse.get('JockeyName'), {}).get('race_count', 0),

                # 調教師統計（3次元）
                trainer_stats.get(horse.get('TrainerName'), {}).get('win_rate', 0),
                trainer_stats.get(horse.get('TrainerName'), {}).get('top3_rate', 0),
                trainer_stats.get(horse.get('TrainerName'), {}).get('race_count', 0),

                # 馬体情報（5次元）
                age, weight_diff, weight, np.log1p(odds), ninki,

                # レース条件（4次元）
                waku, course_turf, course_dirt, track_good,

                # 距離（1次元）
                distance / 1000,

                # 脚質特徴（8次元）
                stats['escape_rate'], stats['leading_rate'], stats['closing_rate'], stats['pursuing_rate'],
                stats['avg_agari'], 1, stats['position_change_ability'], stats['agari_stability'],

                # コース適性（6次元）
                track_avg_rank, track_races, distance_avg_rank, distance_races,
                turn_avg_rank, turn_races,

                # 展開予想（4次元）
                1 if pace_scenario == 'high_pace' else 0,
                1 if pace_scenario == 'slow_pace' else 0,
                pace_advantage, escape_count,

                # 回り方向（2次元）
                1 if turn_direction == 'left' else 0,
                1 if turn_direction == 'right' else 0
            ]
        else:
            # 統計情報がない場合のデフォルト値
            feature_vector = [
                8, 0, 8, 8, 0, 0,  # 基本成績
                0, 0, 0, 0, 0, 0,  # 騎手・調教師
                age, weight_diff, weight, np.log1p(odds), ninki,  # 馬体情報
                waku, course_turf, course_dirt, track_good,  # レース条件
                distance / 1000,  # 距離
                0, 0, 0, 0, 0, 0, 0, 0,  # 脚質
                8, 0, 8, 0, 8, 0,  # コース適性
                1 if pace_scenario == 'high_pace' else 0,
                1 if pace_scenario == 'slow_pace' else 0,
                0, escape_count,  # 展開予想
                1 if turn_direction == 'left' else 0,
                1 if turn_direction == 'right' else 0  # 回り方向
            ]

        horses.append({
            'umaban': umaban,
            'features': feature_vector,
            'actual_rank': pd.to_numeric(horse.get('Rank'), errors='coerce')
        })

    if len(horses) == 0:
        continue

    # 予測
    X = np.array([h['features'] for h in horses])
    predictions = model.predict(X)

    for j, horse in enumerate(horses):
        horse['predicted_rank'] = predictions[j]

    # 予測着順でソート
    horses_sorted = sorted(horses, key=lambda x: x['predicted_rank'])

    # 実際の着順を取得
    actual_results = {}
    for horse in horses:
        if pd.notna(horse['actual_rank']):
            actual_results[int(horse['actual_rank'])] = horse['umaban']

    if len(actual_results) < 3:
        continue

    result = {
        'race_id': race_id,
        'predicted_1st': horses_sorted[0]['umaban'] if len(horses_sorted) > 0 else None,
        'predicted_2nd': horses_sorted[1]['umaban'] if len(horses_sorted) > 1 else None,
        'predicted_3rd': horses_sorted[2]['umaban'] if len(horses_sorted) > 2 else None,
        'actual_1st': actual_results.get(1),
        'actual_2nd': actual_results.get(2),
        'actual_3rd': actual_results.get(3)
    }

    results.append(result)

    # 回収率計算：払戻金データを取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if payout_data and 'ワイド' in payout_data:
        wide_data = payout_data['ワイド']
        winning_pairs = wide_data.get('馬番', [])
        payouts = wide_data.get('払戻金', [])

        if winning_pairs and payouts:
            pred_1st = horses_sorted[0]['umaban']
            pred_2nd = horses_sorted[1]['umaban']
            pred_3rd = horses_sorted[2]['umaban']

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

print(f"\n予測完了: {len(results)}レース")

# 的中率の計算
print("\n" + "=" * 80)
print("予測精度")
print("=" * 80)

hit_1st = sum(1 for r in results if r['predicted_1st'] == r['actual_1st'])
hit_2nd = sum(1 for r in results if r['predicted_2nd'] == r['actual_2nd'])
hit_3rd = sum(1 for r in results if r['predicted_3rd'] == r['actual_3rd'])

hit_trio = sum(1 for r in results if set([r['predicted_1st'], r['predicted_2nd'], r['predicted_3rd']]) ==
               set([r['actual_1st'], r['actual_2nd'], r['actual_3rd']]))

hit_trifecta = sum(1 for r in results if
                   r['predicted_1st'] == r['actual_1st'] and
                   r['predicted_2nd'] == r['actual_2nd'] and
                   r['predicted_3rd'] == r['actual_3rd'])

total_races = len(results)

print(f"\n総レース数: {total_races}レース")
print(f"\n1位的中率: {hit_1st / total_races * 100:.1f}%")
print(f"2位的中率: {hit_2nd / total_races * 100:.1f}%")
print(f"3位的中率: {hit_3rd / total_races * 100:.1f}%")
print(f"\n3連複（順不同）的中率: {hit_trio / total_races * 100:.1f}%")
print(f"3連単（順番通り）的中率: {hit_trifecta / total_races * 100:.1f}%")

# 回収率
print("\n" + "=" * 80)
print("【回収率】")
print("=" * 80)
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
