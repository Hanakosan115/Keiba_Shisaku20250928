"""
馬券購入戦略バックテスト
同一レースで複数の買い方を試して最適な戦略を見つける
"""
import pandas as pd
import json
import sys
import numpy as np
from itertools import combinations, permutations
import pickle
from data_config import MAIN_CSV, MAIN_JSON
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

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

print("=" * 80)
print("馬券購入戦略バックテスト")
print("脚質モデル（最優秀）で複数の買い方を比較")
print("=" * 80)

# モデル読み込み
print("\n脚質モデル読み込み中...")
with open('lightgbm_model_with_running_style.pkl', 'rb') as f:
    model_data = pickle.load(f)
    model = model_data['model']

# データ読み込み
print("データ読み込み中...")
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

# 戦略定義
strategies = {
    # 馬連・馬単
    '馬連_1-2': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 1},
    '馬単_1→2': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 1},
    'ワイド_1-2': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 1},
    'ワイド_1-3': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 1},
    'ワイド_BOX3頭': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 3},

    # 3連単
    '3連単_1着固定4頭流し': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 12},
    '3連単_1着固定6頭流し': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 30},

    # 3連複
    '3連複_1軸5頭流し': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 10},
    '3連複_1軸7頭流し': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 21},
    '3連複_BOX3頭': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 1},
    '3連複_BOX4頭': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 4},
    '3連複_BOX5頭': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 10},
    '3連複_BOX6頭': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0, 'points': 20},
}

# 確信度別の成績
confidence_levels = {
    'high': {'threshold': None, 'best_strategy': None, 'recovery': 0},
    'medium': {'threshold': None, 'best_strategy': None, 'recovery': 0},
    'low': {'threshold': None, 'best_strategy': None, 'recovery': 0},
}

stats_cache = {}
score_gaps = []  # 確信度（1位と2位のスコア差）を記録

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

        # 脚質特徴量
        style_features = get_running_style_features(df, horse_id, race_date_str, max_results=10)

        # 騎手・調教師統計
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

        # 特徴量ベクトル（28次元）
        feature_vector = [
            avg_rank, std_rank, min_rank, max_rank,
            recent_win_rate, recent_top3_rate,
            jockey_win_rate, jockey_top3_rate, jockey_races,
            trainer_win_rate, trainer_top3_rate, trainer_races,
            age, weight_diff, weight, np.log1p(odds), ninki, waku,
            course_turf, course_dirt, track_good, distance / 1000,
            style_features['escape_rate'], style_features['leading_rate'],
            style_features['closing_rate'], style_features['pursuing_rate'],
            style_features['avg_agari'], style_features['has_past_results']
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

    # 予測上位馬
    pred_horses = [h[0] for h in predicted_ranking[:8]]
    pred_scores = [h[1] for h in predicted_ranking[:8]]

    # 確信度（1位と2位のスコア差）
    score_gap = pred_scores[1] - pred_scores[0] if len(pred_scores) > 1 else 0
    score_gaps.append(score_gap)

    # 実際の着順
    actual_1st = actual_ranking[0][0]
    actual_2nd = actual_ranking[1][0]
    actual_3rd = actual_ranking[2][0]
    actual_trio = set([actual_1st, actual_2nd, actual_3rd])

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data:
        continue

    # 各戦略を試す

    # 馬連 (1着と2着を順不同で的中)
    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_umaren = umaren_data.get('馬番', [])  # ['1', '2'] のような文字列リスト
        payout_list = umaren_data.get('払戻金', [0])
        umaren_payout = payout_list[0] if payout_list and payout_list[0] is not None else 0

        strategies['馬連_1-2']['total'] += 1
        strategies['馬連_1-2']['cost'] += 100

        if len(pred_horses) >= 2 and len(winning_umaren) >= 2:
            pred_umaren = set([str(pred_horses[0]), str(pred_horses[1])])
            actual_umaren = set(winning_umaren[:2])
            if pred_umaren == actual_umaren:
                strategies['馬連_1-2']['hit'] += 1
                strategies['馬連_1-2']['return'] += umaren_payout

    # 馬単 (1着→2着を順番通りに的中)
    if '馬単' in payout_data:
        umatan_data = payout_data['馬単']
        winning_umatan = umatan_data.get('馬番', [])  # ['1', '2'] のような文字列リスト（順番重要）
        payout_list = umatan_data.get('払戻金', [0])
        umatan_payout = payout_list[0] if payout_list and payout_list[0] is not None else 0

        strategies['馬単_1→2']['total'] += 1
        strategies['馬単_1→2']['cost'] += 100

        if len(pred_horses) >= 2 and len(winning_umatan) >= 2:
            if [str(pred_horses[0]), str(pred_horses[1])] == winning_umatan[:2]:
                strategies['馬単_1→2']['hit'] += 1
                strategies['馬単_1→2']['return'] += umatan_payout

    # ワイド (3着以内の2頭を的中)
    if 'ワイド' in payout_data:
        wide_data = payout_data['ワイド']
        wide_horses = wide_data.get('馬番', [])  # ['1', '2', '1', '3', '2', '3'] のようなリスト
        wide_payouts = wide_data.get('払戻金', [])

        # ワイド_1-2
        strategies['ワイド_1-2']['total'] += 1
        strategies['ワイド_1-2']['cost'] += 100

        if len(pred_horses) >= 2:
            pred_wide = set([str(pred_horses[0]), str(pred_horses[1])])
            # ワイドの配当は複数あるので、ペアごとに確認
            for i in range(0, len(wide_horses), 2):
                if i + 1 < len(wide_horses):
                    actual_wide = set([wide_horses[i], wide_horses[i+1]])
                    if pred_wide == actual_wide:
                        payout = wide_payouts[i] if i < len(wide_payouts) else 0
                        strategies['ワイド_1-2']['hit'] += 1
                        strategies['ワイド_1-2']['return'] += payout if payout else 0
                        break

        # ワイド_1-3
        strategies['ワイド_1-3']['total'] += 1
        strategies['ワイド_1-3']['cost'] += 100

        if len(pred_horses) >= 3:
            pred_wide = set([str(pred_horses[0]), str(pred_horses[2])])
            for i in range(0, len(wide_horses), 2):
                if i + 1 < len(wide_horses):
                    actual_wide = set([wide_horses[i], wide_horses[i+1]])
                    if pred_wide == actual_wide:
                        payout = wide_payouts[i] if i < len(wide_payouts) else 0
                        strategies['ワイド_1-3']['hit'] += 1
                        strategies['ワイド_1-3']['return'] += payout if payout else 0
                        break

        # ワイド_BOX3頭 (1-2, 1-3, 2-3)
        strategies['ワイド_BOX3頭']['total'] += 1
        strategies['ワイド_BOX3頭']['cost'] += 100 * 3

        if len(pred_horses) >= 3:
            for combo in combinations(pred_horses[:3], 2):
                pred_wide = set([str(combo[0]), str(combo[1])])
                for i in range(0, len(wide_horses), 2):
                    if i + 1 < len(wide_horses):
                        actual_wide = set([wide_horses[i], wide_horses[i+1]])
                        if pred_wide == actual_wide:
                            payout = wide_payouts[i] if i < len(wide_payouts) else 0
                            strategies['ワイド_BOX3頭']['hit'] += 1
                            strategies['ワイド_BOX3頭']['return'] += payout if payout else 0
                            break

    # 3連単_1着固定4頭流し (1-2,3,4,5-2,3,4,5)
    if '3連単' in payout_data:
        trifecta_data = payout_data['3連単']
        winning_trifecta = trifecta_data.get('馬番', [])  # ['7', '1', '3'] のような文字列リスト
        payout_list = trifecta_data.get('払戻金', [0])
        trifecta_payout = payout_list[0] if payout_list and payout_list[0] is not None else 0

        strategies['3連単_1着固定4頭流し']['total'] += 1
        strategies['3連単_1着固定4頭流し']['cost'] += 100 * 12

        # 1-2,3,4,5-2,3,4,5のパターンを生成
        if len(pred_horses) >= 5 and len(winning_trifecta) >= 3:
            for second in pred_horses[1:5]:
                for third in pred_horses[1:5]:
                    if second != third:
                        # 文字列に変換して比較
                        if ([str(pred_horses[0]), str(second), str(third)] == winning_trifecta):
                            strategies['3連単_1着固定4頭流し']['hit'] += 1
                            strategies['3連単_1着固定4頭流し']['return'] += trifecta_payout
                            break

        # 3連単_1着固定6頭流し (1-2~7-2~7)
        strategies['3連単_1着固定6頭流し']['total'] += 1
        strategies['3連単_1着固定6頭流し']['cost'] += 100 * 30

        if len(pred_horses) >= 7 and len(winning_trifecta) >= 3:
            for second in pred_horses[1:7]:
                for third in pred_horses[1:7]:
                    if second != third:
                        # 文字列に変換して比較
                        if ([str(pred_horses[0]), str(second), str(third)] == winning_trifecta):
                            strategies['3連単_1着固定6頭流し']['hit'] += 1
                            strategies['3連単_1着固定6頭流し']['return'] += trifecta_payout
                            break

    # 3連複
    if '3連複' in payout_data:
        trio_data = payout_data['3連複']
        winning_trio_list = trio_data.get('馬番', [])  # ['1', '3', '7'] のような文字列リスト（ソート済み）
        winning_trio = set(winning_trio_list)  # セット比較用
        payout_list = trio_data.get('払戻金', [0])
        trio_payout = payout_list[0] if payout_list and payout_list[0] is not None else 0

        # 3連複_1軸5頭流し (1-2,3,4,5,6)
        strategies['3連複_1軸5頭流し']['total'] += 1
        strategies['3連複_1軸5頭流し']['cost'] += 100 * 10

        if len(pred_horses) >= 6:
            for combo in combinations(pred_horses[1:6], 2):
                # 文字列セットに変換して比較
                pred_trio = set([str(pred_horses[0]), str(combo[0]), str(combo[1])])
                if pred_trio == winning_trio:
                    strategies['3連複_1軸5頭流し']['hit'] += 1
                    strategies['3連複_1軸5頭流し']['return'] += trio_payout
                    break

        # 3連複_1軸7頭流し (1-2~8)
        strategies['3連複_1軸7頭流し']['total'] += 1
        strategies['3連複_1軸7頭流し']['cost'] += 100 * 21

        if len(pred_horses) >= 8:
            for combo in combinations(pred_horses[1:8], 2):
                # 文字列セットに変換して比較
                pred_trio = set([str(pred_horses[0]), str(combo[0]), str(combo[1])])
                if pred_trio == winning_trio:
                    strategies['3連複_1軸7頭流し']['hit'] += 1
                    strategies['3連複_1軸7頭流し']['return'] += trio_payout
                    break

        # BOX系
        for box_size in [3, 4, 5, 6]:
            strategy_name = f'3連複_BOX{box_size}頭'
            if len(pred_horses) >= box_size:
                strategies[strategy_name]['total'] += 1
                strategies[strategy_name]['cost'] += 100 * strategies[strategy_name]['points']

                # 文字列セットに変換して比較
                pred_box = set([str(h) for h in pred_horses[:box_size]])
                if pred_box.issuperset(winning_trio):
                    strategies[strategy_name]['hit'] += 1
                    strategies[strategy_name]['return'] += trio_payout

# 結果表示
print("\n" + "=" * 80)
print("【全戦略の結果】")
print("=" * 80)
print(f"{'戦略名':25s} | レース数 | 的中数 | 的中率 | 投資額 | 払戻額 | 回収率 | 損益")
print("-" * 100)

results = []
for name, result in strategies.items():
    if result['total'] > 0:
        hit_rate = result['hit'] / result['total'] * 100
        recovery = result['return'] / result['cost'] * 100 if result['cost'] > 0 else 0
        profit = result['return'] - result['cost']

        results.append({
            'name': name,
            'recovery': recovery,
            'hit_rate': hit_rate,
            'total': result['total'],
            'hit': result['hit'],
            'cost': result['cost'],
            'return': result['return'],
            'profit': profit
        })

        print(f"{name:25s} | {result['total']:4d}R | {result['hit']:4d}回 | {hit_rate:5.1f}% | "
              f"{result['cost']:>9,}円 | {result['return']:>9,}円 | {recovery:6.1f}% | {profit:>+10,}円")

# 最優秀戦略
print("\n" + "=" * 80)
print("【ランキング】")
print("=" * 80)

# 回収率順
results_by_recovery = sorted(results, key=lambda x: x['recovery'], reverse=True)
print("\n[回収率TOP5]")
for i, r in enumerate(results_by_recovery[:5], 1):
    print(f"{i}. {r['name']:25s}: {r['recovery']:6.1f}% (的中率: {r['hit_rate']:5.1f}%)")

# 的中率順
results_by_hit = sorted(results, key=lambda x: x['hit_rate'], reverse=True)
print("\n[的中率TOP5]")
for i, r in enumerate(results_by_hit[:5], 1):
    print(f"{i}. {r['name']:25s}: {r['hit_rate']:5.1f}% (回収率: {r['recovery']:6.1f}%)")

print("\n" + "=" * 80)
print("バックテスト完了")
print("=" * 80)
print("\n次のステップ: 予測確信度に応じた買い方の使い分けを分析")
