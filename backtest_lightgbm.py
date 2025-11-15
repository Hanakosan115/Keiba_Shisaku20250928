"""
LightGBMモデルによるバックテスト（2024年）
"""
import pandas as pd
import json
import sys
import numpy as np
from collections import defaultdict
from itertools import combinations
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
print("LightGBMモデルによるバックテスト（2024年）")
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

# 結果集計用
results = {
    'total': 0,
    'umaren_hit': 0,
    'umaren_return': 0,
    'umaren_cost': 0,
}

# 予測精度評価用
prediction_accuracy = {
    'top1_hit': 0,  # 予測1位が実際に1位
    'top1_top3': 0,  # 予測1位が実際にTOP3
    'top1_2_hit': 0,  # 予測1-2位が実際の馬連
}

# 統計キャッシュ（2024年のデータに基づいて計算）
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

    # 騎手・調教師統計（キャッシュから取得または計算）
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

        # 実際の着順（精度評価用）
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

    top3 = [h[0] for h in predicted_ranking[:3]]
    predicted_1st = predicted_ranking[0][0]
    predicted_1st_actual_rank = predicted_ranking[0][2]

    # 実際の1-2着
    actual_top2 = sorted(
        [(umaban, rank) for umaban, rank in zip(horse_umabans, horse_actual_ranks)],
        key=lambda x: x[1]
    )[:2]

    # 精度評価
    if predicted_1st_actual_rank == 1:
        prediction_accuracy['top1_hit'] += 1
    if predicted_1st_actual_rank <= 3:
        prediction_accuracy['top1_top3'] += 1

    # 予測1-2位と実際の1-2着が一致するか
    predicted_top2 = set([predicted_ranking[0][0], predicted_ranking[1][0]])
    actual_top2_set = set([h[0] for h in actual_top2])

    if predicted_top2 == actual_top2_set:
        prediction_accuracy['top1_2_hit'] += 1

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data:
        continue

    results['total'] += 1

    # 馬連
    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_pairs = umaren_data.get('馬番', [])
        payouts = umaren_data.get('払戻金', [])

        if winning_pairs and len(winning_pairs) >= 2 and payouts:
            try:
                winning_pair = set([int(x) for x in winning_pairs[:2]])
                umaren_pairs = list(combinations(top3, 2))

                results['umaren_cost'] += len(umaren_pairs) * 100

                hit_found = False
                for pair in umaren_pairs:
                    if set(pair) == winning_pair:
                        hit_found = True
                        break

                if hit_found:
                    results['umaren_hit'] += 1
                    results['umaren_return'] += payouts[0]
            except:
                pass

# 結果出力
print("\n" + "=" * 80)
print("【LightGBMモデルの結果】2024年")
print("=" * 80)

print(f"\n総レース数: {results['total']:,}レース")

if results['umaren_cost'] > 0:
    umaren_recovery = (results['umaren_return'] / results['umaren_cost']) * 100
    print(f"\n【馬連】3頭BOX")
    print(f"  的中: {results['umaren_hit']:,}回 / {results['total']:,}レース")
    print(f"  的中率: {results['umaren_hit']/results['total']*100:.2f}%")
    print(f"  投資額: {results['umaren_cost']:,}円")
    print(f"  払戻額: {results['umaren_return']:,}円")
    print(f"  回収率: {umaren_recovery:.2f}%")
    print(f"  損益: {results['umaren_return'] - results['umaren_cost']:+,}円")

print("\n" + "=" * 80)
print("【予測精度の評価】")
print("=" * 80)

if results['total'] > 0:
    top1_hit_rate = prediction_accuracy['top1_hit'] / results['total'] * 100
    top1_top3_rate = prediction_accuracy['top1_top3'] / results['total'] * 100
    top1_2_hit_rate = prediction_accuracy['top1_2_hit'] / results['total'] * 100

    print(f"\n予測1位が実際に1位: {prediction_accuracy['top1_hit']}回 ({top1_hit_rate:.1f}%)")
    print(f"予測1位が実際にTOP3: {prediction_accuracy['top1_top3']}回 ({top1_top3_rate:.1f}%)")
    print(f"予測1-2位が実際の馬連: {prediction_accuracy['top1_2_hit']}回 ({top1_2_hit_rate:.1f}%)")

print("\n" + "=" * 80)
print("【手法の比較】")
print("=" * 80)

print("\n従来手法（手動スコアリング）:")
print("  予測1-2位の的中率: 8.7%")
print("  馬連回収率: 68.6%")

if results['total'] > 0 and results['umaren_cost'] > 0:
    print(f"\nLightGBMモデル:")
    print(f"  予測1-2位の的中率: {top1_2_hit_rate:.1f}%")
    print(f"  馬連回収率: {umaren_recovery:.2f}%")

    print(f"\n【改善度】")
    print(f"  予測精度: {top1_2_hit_rate - 8.7:+.1f}ポイント")
    print(f"  回収率: {umaren_recovery - 68.6:+.1f}ポイント")

print("\n" + "=" * 80)
print("バックテスト完了")
print("=" * 80)
