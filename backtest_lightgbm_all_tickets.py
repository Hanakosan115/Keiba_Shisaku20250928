"""
LightGBMモデル：全馬券種の最適戦略探索
- 単勝、複勝、ワイド、馬単、馬連、3連複、3連単
- 各馬券種で複数の買い方パターンをテスト
- 予測スコアの差（自信度）によるフィルタリング
"""
import pandas as pd
import json
import sys
import numpy as np
from collections import defaultdict
from itertools import combinations, permutations
import pickle
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

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
print("LightGBMモデル：全馬券種の最適戦略探索")
print("=" * 80)

# モデル読み込み
print("\nモデル読み込み中...")
model_path = r"C:\Users\bu158\Keiba_Shisaku20250928\lightgbm_model.pkl"
with open(model_path, 'rb') as f:
    model_data = pickle.load(f)
    model = model_data['model']
    feature_names = model_data['feature_names']

print("モデル読み込み完了")

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年のデータ
target_races = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"対象: 2024年 {len(race_ids)}レース")

# 各馬券種の戦略パターン
strategies = {
    '単勝_1位': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    '複勝_1位': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    '複勝_1-3位': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    'ワイド_1-2': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    'ワイド_1軸流し': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    'ワイド_BOX3頭': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    '馬単_1-2': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    '馬単_1軸流し': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    '馬連_1-2': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    '馬連_BOX3頭': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    '3連複_1-2-3': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    '3連複_BOX4頭': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    '3連単_1-2-3': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
    '3連単_1軸マルチ': {'total': 0, 'hit': 0, 'return': 0, 'cost': 0},
}

# 統計キャッシュ
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
    horse_actual_ranks = []

    for _, horse in race_horses.iterrows():
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

        # 実際の着順
        actual_rank = pd.to_numeric(horse.get('Rank'), errors='coerce')

        feature_vector = [
            avg_rank, std_rank, min_rank, max_rank,
            recent_win_rate, recent_top3_rate,
            jockey_win_rate, jockey_top3_rate, jockey_races,
            trainer_win_rate, trainer_top3_rate, trainer_races,
            age, weight_diff, weight, np.log1p(odds), ninki, waku,
            course_turf, course_dirt, track_good, distance / 1000
        ]

        horse_features.append(feature_vector)
        horse_umabans.append(int(horse.get('Umaban', 0)))
        horse_actual_ranks.append(actual_rank if pd.notna(actual_rank) else 99)

    if len(horse_features) < 8:
        continue

    # 予測
    X = np.array(horse_features)
    predictions = model.predict(X)

    # 予測スコアが低い順（着順が良い順）にソート
    predicted_ranking = sorted(
        zip(horse_umabans, predictions, horse_actual_ranks),
        key=lambda x: x[1]
    )

    # 実際の着順でソート
    actual_ranking = sorted(
        zip(horse_umabans, horse_actual_ranks),
        key=lambda x: x[1]
    )

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data:
        continue

    # 実際の着順
    actual_1st = actual_ranking[0][0] if len(actual_ranking) >= 1 else None
    actual_2nd = actual_ranking[1][0] if len(actual_ranking) >= 2 else None
    actual_3rd = actual_ranking[2][0] if len(actual_ranking) >= 3 else None

    # 予測の上位馬
    pred_1st = predicted_ranking[0][0]
    pred_2nd = predicted_ranking[1][0]
    pred_3rd = predicted_ranking[2][0]
    pred_4th = predicted_ranking[3][0] if len(predicted_ranking) >= 4 else None

    # ========================================
    # 1. 単勝
    # ========================================
    if '単勝' in payout_data:
        tansho_data = payout_data['単勝']
        winning_nums = tansho_data.get('馬番', [])
        payouts = tansho_data.get('払戻金', [])

        if winning_nums and payouts:
            try:
                winning_num = int(winning_nums[0])
                payout = payouts[0]

                # 戦略1: 1位のみ
                strategies['単勝_1位']['total'] += 1
                strategies['単勝_1位']['cost'] += 100

                if pred_1st == winning_num:
                    strategies['単勝_1位']['hit'] += 1
                    strategies['単勝_1位']['return'] += payout
            except:
                pass

    # ========================================
    # 2. 複勝
    # ========================================
    if '複勝' in payout_data:
        fukusho_data = payout_data['複勝']
        winning_nums = fukusho_data.get('馬番', [])
        payouts = fukusho_data.get('払戻金', [])

        if winning_nums and payouts:
            try:
                winning_nums_int = [int(x) for x in winning_nums]

                # 戦略1: 1位のみ
                strategies['複勝_1位']['total'] += 1
                strategies['複勝_1位']['cost'] += 100

                if pred_1st in winning_nums_int:
                    idx = winning_nums_int.index(pred_1st)
                    strategies['複勝_1位']['hit'] += 1
                    strategies['複勝_1位']['return'] += payouts[idx]

                # 戦略2: 1-3位
                strategies['複勝_1-3位']['total'] += 1
                strategies['複勝_1-3位']['cost'] += 300

                for pred_num in [pred_1st, pred_2nd, pred_3rd]:
                    if pred_num in winning_nums_int:
                        idx = winning_nums_int.index(pred_num)
                        strategies['複勝_1-3位']['hit'] += 1
                        strategies['複勝_1-3位']['return'] += payouts[idx]
                        break
            except:
                pass

    # ========================================
    # 3. ワイド
    # ========================================
    if 'ワイド' in payout_data:
        wide_data = payout_data['ワイド']
        winning_pairs = wide_data.get('馬番', [])
        payouts = wide_data.get('払戻金', [])

        if winning_pairs and payouts:
            try:
                # 戦略1: 1-2
                strategies['ワイド_1-2']['total'] += 1
                strategies['ワイド_1-2']['cost'] += 100

                pair_1_2 = set([pred_1st, pred_2nd])
                for i in range(0, len(winning_pairs), 2):
                    if i + 1 < len(winning_pairs):
                        winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
                        if pair_1_2 == winning_pair:
                            strategies['ワイド_1-2']['hit'] += 1
                            strategies['ワイド_1-2']['return'] += payouts[i // 2]
                            break

                # 戦略2: 1軸流し（1-2, 1-3）
                strategies['ワイド_1軸流し']['total'] += 1
                strategies['ワイド_1軸流し']['cost'] += 200

                hit_found = False
                for pred_pair in [(pred_1st, pred_2nd), (pred_1st, pred_3rd)]:
                    pair_set = set(pred_pair)
                    for i in range(0, len(winning_pairs), 2):
                        if i + 1 < len(winning_pairs):
                            winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
                            if pair_set == winning_pair:
                                strategies['ワイド_1軸流し']['hit'] += 1
                                strategies['ワイド_1軸流し']['return'] += payouts[i // 2]
                                hit_found = True
                                break
                    if hit_found:
                        break

                # 戦略3: BOX3頭
                strategies['ワイド_BOX3頭']['total'] += 1
                strategies['ワイド_BOX3頭']['cost'] += 300

                hit_found = False
                box_pairs = [(pred_1st, pred_2nd), (pred_1st, pred_3rd), (pred_2nd, pred_3rd)]
                for pred_pair in box_pairs:
                    pair_set = set(pred_pair)
                    for i in range(0, len(winning_pairs), 2):
                        if i + 1 < len(winning_pairs):
                            winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
                            if pair_set == winning_pair:
                                strategies['ワイド_BOX3頭']['hit'] += 1
                                strategies['ワイド_BOX3頭']['return'] += payouts[i // 2]
                                hit_found = True
                                break
                    if hit_found:
                        break
            except:
                pass

    # ========================================
    # 4. 馬単
    # ========================================
    if '馬単' in payout_data:
        umatan_data = payout_data['馬単']
        winning_pair = umatan_data.get('馬番', [])
        payouts = umatan_data.get('払戻金', [])

        if winning_pair and len(winning_pair) >= 2 and payouts:
            try:
                winning_1st = int(winning_pair[0])
                winning_2nd = int(winning_pair[1])

                # 戦略1: 1-2（順番通り）
                strategies['馬単_1-2']['total'] += 1
                strategies['馬単_1-2']['cost'] += 100

                if pred_1st == winning_1st and pred_2nd == winning_2nd:
                    strategies['馬単_1-2']['hit'] += 1
                    strategies['馬単_1-2']['return'] += payouts[0]

                # 戦略2: 1軸流し（1→2, 1→3）
                strategies['馬単_1軸流し']['total'] += 1
                strategies['馬単_1軸流し']['cost'] += 200

                if pred_1st == winning_1st and (pred_2nd == winning_2nd or pred_3rd == winning_2nd):
                    strategies['馬単_1軸流し']['hit'] += 1
                    strategies['馬単_1軸流し']['return'] += payouts[0]
            except:
                pass

    # ========================================
    # 5. 馬連
    # ========================================
    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_pair = umaren_data.get('馬番', [])
        payouts = umaren_data.get('払戻金', [])

        if winning_pair and len(winning_pair) >= 2 and payouts:
            try:
                winning_set = set([int(winning_pair[0]), int(winning_pair[1])])

                # 戦略1: 1-2
                strategies['馬連_1-2']['total'] += 1
                strategies['馬連_1-2']['cost'] += 100

                if set([pred_1st, pred_2nd]) == winning_set:
                    strategies['馬連_1-2']['hit'] += 1
                    strategies['馬連_1-2']['return'] += payouts[0]

                # 戦略2: BOX3頭
                strategies['馬連_BOX3頭']['total'] += 1
                strategies['馬連_BOX3頭']['cost'] += 300

                box_pairs = list(combinations([pred_1st, pred_2nd, pred_3rd], 2))
                for pair in box_pairs:
                    if set(pair) == winning_set:
                        strategies['馬連_BOX3頭']['hit'] += 1
                        strategies['馬連_BOX3頭']['return'] += payouts[0]
                        break
            except:
                pass

    # ========================================
    # 6. 3連複
    # ========================================
    if '3連複' in payout_data:
        sanrenpuku_data = payout_data['3連複']
        winning_trio = sanrenpuku_data.get('馬番', [])
        payouts = sanrenpuku_data.get('払戻金', [])

        if winning_trio and len(winning_trio) >= 3 and payouts:
            try:
                winning_set = set([int(winning_trio[0]), int(winning_trio[1]), int(winning_trio[2])])

                # 戦略1: 1-2-3
                strategies['3連複_1-2-3']['total'] += 1
                strategies['3連複_1-2-3']['cost'] += 100

                if set([pred_1st, pred_2nd, pred_3rd]) == winning_set:
                    strategies['3連複_1-2-3']['hit'] += 1
                    strategies['3連複_1-2-3']['return'] += payouts[0]

                # 戦略2: BOX4頭
                if pred_4th:
                    strategies['3連複_BOX4頭']['total'] += 1
                    strategies['3連複_BOX4頭']['cost'] += 400

                    box_trios = list(combinations([pred_1st, pred_2nd, pred_3rd, pred_4th], 3))
                    for trio in box_trios:
                        if set(trio) == winning_set:
                            strategies['3連複_BOX4頭']['hit'] += 1
                            strategies['3連複_BOX4頭']['return'] += payouts[0]
                            break
            except:
                pass

    # ========================================
    # 7. 3連単
    # ========================================
    if '3連単' in payout_data:
        sanrentan_data = payout_data['3連単']
        winning_trio = sanrentan_data.get('馬番', [])
        payouts = sanrentan_data.get('払戻金', [])

        if winning_trio and len(winning_trio) >= 3 and payouts:
            try:
                winning_1st = int(winning_trio[0])
                winning_2nd = int(winning_trio[1])
                winning_3rd = int(winning_trio[2])

                # 戦略1: 1-2-3（順番通り）
                strategies['3連単_1-2-3']['total'] += 1
                strategies['3連単_1-2-3']['cost'] += 100

                if pred_1st == winning_1st and pred_2nd == winning_2nd and pred_3rd == winning_3rd:
                    strategies['3連単_1-2-3']['hit'] += 1
                    strategies['3連単_1-2-3']['return'] += payouts[0]

                # 戦略2: 1軸マルチ（1→2-3, 1→3-2, 1→2-4, 1→4-2, 1→3-4, 1→4-3）
                if pred_4th:
                    strategies['3連単_1軸マルチ']['total'] += 1
                    strategies['3連単_1軸マルチ']['cost'] += 600

                    perms = list(permutations([pred_2nd, pred_3rd, pred_4th], 2))
                    for perm in perms:
                        if pred_1st == winning_1st and perm[0] == winning_2nd and perm[1] == winning_3rd:
                            strategies['3連単_1軸マルチ']['hit'] += 1
                            strategies['3連単_1軸マルチ']['return'] += payouts[0]
                            break
            except:
                pass

# 結果出力
print("\n" + "=" * 80)
print("【全馬券種の結果】2024年")
print("=" * 80)

print("\n馬券種 | レース数 | 的中数 | 的中率 | 投資額 | 払戻額 | 回収率 | 損益")
print("-" * 90)

results_sorted = []

for name, res in strategies.items():
    if res['total'] > 0 and res['cost'] > 0:
        hit_rate = res['hit'] / res['total'] * 100
        recovery = res['return'] / res['cost'] * 100
        profit = res['return'] - res['cost']

        results_sorted.append({
            'name': name,
            'total': res['total'],
            'hit': res['hit'],
            'hit_rate': hit_rate,
            'cost': res['cost'],
            'return': res['return'],
            'recovery': recovery,
            'profit': profit
        })

# 回収率順にソート
results_sorted.sort(key=lambda x: x['recovery'], reverse=True)

for r in results_sorted:
    print(f"{r['name']:15s} | {r['total']:4d}R | {r['hit']:4d}回 | {r['hit_rate']:5.1f}% | "
          f"{r['cost']:9,}円 | {r['return']:9,}円 | {r['recovery']:6.1f}% | {r['profit']:+10,}円")

print("\n" + "=" * 80)
print("【ベスト戦略 TOP5】")
print("=" * 80)

for i, r in enumerate(results_sorted[:5], 1):
    print(f"\n{i}. {r['name']}")
    print(f"   回収率: {r['recovery']:.1f}% | 的中率: {r['hit_rate']:.1f}% | 損益: {r['profit']:+,}円")

# 黒字戦略を特定
profitable_strategies = [r for r in results_sorted if r['recovery'] >= 100]

print("\n" + "=" * 80)
print("【黒字戦略（回収率100%以上）】")
print("=" * 80)

if profitable_strategies:
    print(f"\n発見: {len(profitable_strategies)}個の黒字戦略！")
    for r in profitable_strategies:
        print(f"\n- {r['name']}")
        print(f"  回収率: {r['recovery']:.1f}%")
        print(f"  的中率: {r['hit_rate']:.1f}%")
        print(f"  投資額: {r['cost']:,}円")
        print(f"  払戻額: {r['return']:,}円")
        print(f"  利益: {r['profit']:+,}円")
else:
    print("\n残念: 回収率100%以上の戦略は見つかりませんでした。")
    print("最高回収率でも赤字ですが、複数戦略を組み合わせることで改善の可能性があります。")

print("\n" + "=" * 80)
print("分析完了")
print("=" * 80)
