"""
3連系予測の精度を詳細分析
- 1-2-3位の予測精度
- スコア差と的中率の関係
- 最適な買い目絞り込み条件を探る
"""
import pandas as pd
import numpy as np
import pickle
import sys
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv
from collections import defaultdict

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
print("3連系予測精度の詳細分析")
print("=" * 80)

# モデル読み込み
print("\nモデル読み込み中...")
model_path = r"C:\Users\bu158\Keiba_Shisaku20250928\lightgbm_model_tuned.pkl"
with open(model_path, 'rb') as f:
    model_data = pickle.load(f)
    model = model_data['model']
    feature_names = model_data['feature_names']

# データ読み込み
print("データ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年のデータ
target_races = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"対象: 2024年 {len(race_ids)}レース")

# 統計
stats_cache = {}
results = []

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
        past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=10)

        # 実際の着順
        actual_rank = pd.to_numeric(horse.get('Rank'), errors='coerce')
        if pd.isna(actual_rank):
            continue
        actual_ranks.append(int(actual_rank))

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

    if len(horse_features) < 8 or len(actual_ranks) != len(horse_features):
        continue

    # 予測
    X = np.array(horse_features)
    predictions = model.predict(X)

    # 予測スコアが低い順にソート（スコアが低いほど良い）
    predicted_ranking = sorted(
        zip(horse_umabans, predictions, actual_ranks),
        key=lambda x: x[1]
    )

    # 実際の着順でソート
    actual_ranking = sorted(
        zip(horse_umabans, actual_ranks),
        key=lambda x: x[1]
    )

    # 予測1-2-3位
    pred_1st = predicted_ranking[0][0]
    pred_2nd = predicted_ranking[1][0]
    pred_3rd = predicted_ranking[2][0]

    # 実際の1-2-3位
    actual_1st = actual_ranking[0][0]
    actual_2nd = actual_ranking[1][0]
    actual_3rd = actual_ranking[2][0]

    # スコア差
    score_1st = predicted_ranking[0][1]
    score_2nd = predicted_ranking[1][1]
    score_3rd = predicted_ranking[2][1]
    score_4th = predicted_ranking[3][1] if len(predicted_ranking) > 3 else score_3rd + 1

    score_diff_1_2 = score_2nd - score_1st
    score_diff_2_3 = score_3rd - score_2nd
    score_diff_3_4 = score_4th - score_3rd

    # 的中判定
    trio_hit = set([pred_1st, pred_2nd, pred_3rd]) == set([actual_1st, actual_2nd, actual_3rd])
    trifecta_hit = (pred_1st == actual_1st and pred_2nd == actual_2nd and pred_3rd == actual_3rd)

    # 個別順位の的中
    first_correct = (pred_1st == actual_1st)
    second_correct = (pred_2nd == actual_2nd)
    third_correct = (pred_3rd == actual_3rd)

    results.append({
        'race_id': race_id,
        'score_diff_1_2': score_diff_1_2,
        'score_diff_2_3': score_diff_2_3,
        'score_diff_3_4': score_diff_3_4,
        'trio_hit': trio_hit,
        'trifecta_hit': trifecta_hit,
        'first_correct': first_correct,
        'second_correct': second_correct,
        'third_correct': third_correct,
    })

# 結果を分析
results_df = pd.DataFrame(results)

print("\n" + "=" * 80)
print("【全体の的中率】")
print("=" * 80)

print(f"\n総レース数: {len(results_df)}レース")
print(f"\n3連複（順不同）的中率: {results_df['trio_hit'].sum() / len(results_df) * 100:.1f}%")
print(f"3連単（順番通り）的中率: {results_df['trifecta_hit'].sum() / len(results_df) * 100:.1f}%")
print(f"\n1位的中率: {results_df['first_correct'].sum() / len(results_df) * 100:.1f}%")
print(f"2位的中率: {results_df['second_correct'].sum() / len(results_df) * 100:.1f}%")
print(f"3位的中率: {results_df['third_correct'].sum() / len(results_df) * 100:.1f}%")

print("\n" + "=" * 80)
print("【スコア差別の的中率】")
print("=" * 80)

# スコア差で分類
thresholds = [0.5, 1.0, 1.5, 2.0, 3.0]

print("\nスコア差1-2 | レース数 | 3連複的中率 | 3連単的中率")
print("-" * 70)

for threshold in thresholds:
    filtered = results_df[results_df['score_diff_1_2'] >= threshold]
    if len(filtered) > 0:
        trio_rate = filtered['trio_hit'].sum() / len(filtered) * 100
        trifecta_rate = filtered['trifecta_hit'].sum() / len(filtered) * 100
        print(f"{threshold:6.1f}以上 | {len(filtered):5d}R | {trio_rate:11.1f}% | {trifecta_rate:11.1f}%")

print("\n" + "=" * 80)
print("【推奨: スコア差による絞り込み】")
print("=" * 80)

# 最適な閾値を探す
best_threshold = None
best_trio_rate = 0

for threshold in np.arange(0.5, 5.0, 0.5):
    filtered = results_df[results_df['score_diff_1_2'] >= threshold]
    if len(filtered) >= 100:  # 十分なサンプル数
        trio_rate = filtered['trio_hit'].sum() / len(filtered) * 100
        if trio_rate > best_trio_rate:
            best_trio_rate = trio_rate
            best_threshold = threshold

if best_threshold:
    filtered = results_df[results_df['score_diff_1_2'] >= best_threshold]
    print(f"\nベスト閾値: スコア差 {best_threshold}以上")
    print(f"  対象レース: {len(filtered)}レース ({len(filtered)/len(results_df)*100:.1f}%)")
    print(f"  3連複的中率: {filtered['trio_hit'].sum() / len(filtered) * 100:.1f}%")
    print(f"  3連単的中率: {filtered['trifecta_hit'].sum() / len(filtered) * 100:.1f}%")

print("\n" + "=" * 80)
print("分析完了")
print("=" * 80)
