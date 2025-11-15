"""
ワイド戦略の最適化
- 予測スコア差によるフィルタリング
- オッズ範囲によるフィルタリング
- 組み合わせて最高の回収率を目指す
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
print("ワイド戦略の最適化")
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

# フィルタリング条件のパラメータ範囲
score_diff_thresholds = [0, 0.5, 1.0, 1.5, 2.0, 3.0]  # 1位と2位のスコア差
avg_odds_ranges = [
    (0, 999, "全て"),
    (0, 5, "1.0-5.0倍"),
    (2, 10, "2.0-10.0倍"),
    (3, 15, "3.0-15.0倍"),
    (5, 20, "5.0-20.0倍"),
    (10, 999, "10.0倍以上")
]

# 全組み合わせをテスト
results_all = []

# 統計キャッシュ
stats_cache = {}

print("\nフィルタリング条件の最適化中...")

for score_diff_threshold in score_diff_thresholds:
    for min_odds, max_odds, odds_label in avg_odds_ranges:

        # この条件での結果
        result = {
            'score_diff_threshold': score_diff_threshold,
            'odds_range': odds_label,
            'min_odds': min_odds,
            'max_odds': max_odds,
            'total': 0,
            'purchased': 0,
            'hit': 0,
            'return': 0,
            'cost': 0
        }

        for idx, race_id in enumerate(race_ids):
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
            horse_odds_list = []

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
                horse_odds_list.append(odds)

            if len(horse_features) < 8:
                continue

            # 予測
            X = np.array(horse_features)
            predictions = model.predict(X)

            # 予測スコアが低い順にソート
            predicted_ranking = sorted(
                zip(horse_umabans, predictions, horse_odds_list),
                key=lambda x: x[1]
            )

            # スコア差を計算
            score_1st = predicted_ranking[0][1]
            score_2nd = predicted_ranking[1][1]
            score_diff = score_2nd - score_1st  # スコアが低いほど良いので、2位-1位

            # 上位2頭の平均オッズ
            avg_top2_odds = (predicted_ranking[0][2] + predicted_ranking[1][2]) / 2

            # 総レース数をカウント
            result['total'] += 1

            # フィルタリング条件チェック
            if score_diff < score_diff_threshold:
                continue  # スコア差が小さい（自信がない）→ スキップ

            if not (min_odds <= avg_top2_odds < max_odds):
                continue  # オッズ範囲外 → スキップ

            # 条件を満たしたので購入
            result['purchased'] += 1

            # ワイド 1軸流し（1-2, 1-3）
            pred_1st = predicted_ranking[0][0]
            pred_2nd = predicted_ranking[1][0]
            pred_3rd = predicted_ranking[2][0]

            result['cost'] += 200  # 2点購入

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

            try:
                # 的中判定
                hit_found = False
                for pred_pair in [(pred_1st, pred_2nd), (pred_1st, pred_3rd)]:
                    pair_set = set(pred_pair)
                    for i in range(0, len(winning_pairs), 2):
                        if i + 1 < len(winning_pairs):
                            winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
                            if pair_set == winning_pair:
                                result['hit'] += 1
                                result['return'] += payouts[i // 2]
                                hit_found = True
                                break
                    if hit_found:
                        break
            except:
                pass

        # 結果を保存
        if result['purchased'] > 0:
            result['recovery'] = result['return'] / result['cost'] * 100 if result['cost'] > 0 else 0
            result['profit'] = result['return'] - result['cost']
            result['hit_rate'] = result['hit'] / result['purchased'] * 100
            result['purchase_rate'] = result['purchased'] / result['total'] * 100
            results_all.append(result)

# 結果を回収率順にソート
results_all.sort(key=lambda x: x['recovery'], reverse=True)

print("\n" + "=" * 80)
print("【フィルタリング条件別の結果 TOP20】")
print("=" * 80)

print("\nスコア差 | オッズ範囲 | 購入率 | 的中数 | 的中率 | 回収率 | 損益")
print("-" * 90)

for i, r in enumerate(results_all[:20], 1):
    print(f"{r['score_diff_threshold']:4.1f}以上 | {r['odds_range']:15s} | {r['purchase_rate']:5.1f}% | "
          f"{r['hit']:4d}回 | {r['hit_rate']:5.1f}% | {r['recovery']:6.1f}% | {r['profit']:+9,}円")

print("\n" + "=" * 80)
print("【ベスト戦略】")
print("=" * 80)

if results_all:
    best = results_all[0]
    print(f"\n条件:")
    print(f"  スコア差: {best['score_diff_threshold']}以上")
    print(f"  オッズ範囲: {best['odds_range']}")
    print(f"\n成績:")
    print(f"  購入レース: {best['purchased']}/{best['total']}レース ({best['purchase_rate']:.1f}%)")
    print(f"  的中: {best['hit']}回")
    print(f"  的中率: {best['hit_rate']:.1f}%")
    print(f"  投資額: {best['cost']:,}円")
    print(f"  払戻額: {best['return']:,}円")
    print(f"  回収率: {best['recovery']:.1f}%")
    print(f"  利益: {best['profit']:+,}円")

print("\n" + "=" * 80)
print("【ベースライン（フィルタなし）との比較】")
print("=" * 80)

baseline = [r for r in results_all if r['score_diff_threshold'] == 0 and r['odds_range'] == "全て"]
if baseline:
    base = baseline[0]
    best = results_all[0]

    print(f"\nベースライン（全レース購入）:")
    print(f"  回収率: {base['recovery']:.1f}%")
    print(f"  利益: {base['profit']:+,}円")

    print(f"\n最適化後:")
    print(f"  回収率: {best['recovery']:.1f}%")
    print(f"  利益: {best['profit']:+,}円")

    print(f"\n改善:")
    print(f"  回収率: {best['recovery'] - base['recovery']:+.1f}ポイント")
    print(f"  利益: {best['profit'] - base['profit']:+,}円")

print("\n" + "=" * 80)
print("最適化完了")
print("=" * 80)
