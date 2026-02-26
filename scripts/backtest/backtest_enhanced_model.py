"""
強化版モデルのバックテスト

2024年データで性能評価:
- 単勝的中率
- 回収率
- 3連複的中率
"""

import pandas as pd
import numpy as np
import pickle
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
print("強化版モデルバックテスト (2024年)")
print("="*80)

# モデル読み込み
print("\nモデル読み込み中...")
try:
    with open('lgbm_model_enhanced.pkl', 'rb') as f:
        model = pickle.load(f)
    print("OK 強化版モデル読み込み成功")
except FileNotFoundError:
    print("NG モデルファイルが見つかりません: lgbm_model_enhanced.pkl")
    print("   訓練が完了してから実行してください")
    sys.exit(1)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv',
                 encoding='utf-8', low_memory=False)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年データでテスト
test_df = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
].copy()

print(f"テストデータ: {len(test_df):,}件 (2024年)")

# テストレース抽出
test_races = test_df.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()
print(f"テストレース数: {len(test_races):,}レース")

# バックテスト実行
print("\nバックテスト実行中...")

# 統計キャッシュ（全データを使用）
jockey_stats_cache = {}
trainer_stats_cache = {}

# 結果記録
predictions_list = []
win_count = 0
total_races = 0
total_return = 0
total_bet = 0

sanrenpuku_hit = 0
sanrenpuku_total = 0
sanrenpuku_return = 0

for idx, race_id in enumerate(test_races):
    if (idx + 1) % 100 == 0:
        print(f"  {idx + 1}/{len(test_races)} レース処理中...")

    race_horses = test_df[test_df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue

    race_date_str = str(race_date)[:10]

    # 統計キャッシュ
    if race_date_str not in jockey_stats_cache:
        jockey_stats_cache[race_date_str] = calculate_person_stats(
            df, 'JockeyName', race_date_str, months_back=12
        )
        trainer_stats_cache[race_date_str] = calculate_person_stats(
            df, 'TrainerName', race_date_str, months_back=12
        )

    jockey_stats = jockey_stats_cache[race_date_str]
    trainer_stats = trainer_stats_cache[race_date_str]

    race_features = []
    horse_data = []

    for _, horse in race_horses.iterrows():
        rank = pd.to_numeric(horse.get('Rank'), errors='coerce')
        if pd.isna(rank):
            continue

        horse_id = horse.get('horse_id')

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

        # 脚質分布
        style_dist = get_running_style_features(df, horse_id, race_date_str)

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

        # その他の特徴量
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

        # クラス関連
        race_class_rank = pd.to_numeric(horse.get('race_class_rank'), errors='coerce')
        race_class_rank = race_class_rank if pd.notna(race_class_rank) else 0

        prev_race_class_rank = pd.to_numeric(horse.get('prev_race_class_rank'), errors='coerce')
        prev_race_class_rank = prev_race_class_rank if pd.notna(prev_race_class_rank) else 0

        class_change = horse.get('class_change', 'same')
        is_promotion = 1 if class_change == 'promotion' else 0
        is_demotion = 1 if class_change == 'demotion' else 0
        is_debut = 1 if class_change == 'debut' else 0

        class_rank_diff = race_class_rank - prev_race_class_rank if prev_race_class_rank != 0 else 0

        # ラップタイム特徴量
        first_3f_avg = pd.to_numeric(horse.get('first_3f_avg'), errors='coerce')
        first_3f_avg = first_3f_avg if pd.notna(first_3f_avg) else 12.0

        last_3f_avg = pd.to_numeric(horse.get('last_3f_avg'), errors='coerce')
        last_3f_avg = last_3f_avg if pd.notna(last_3f_avg) else 12.0

        pace_variance = pd.to_numeric(horse.get('pace_variance'), errors='coerce')
        pace_variance = pace_variance if pd.notna(pace_variance) else 0.5

        pace_acceleration = pd.to_numeric(horse.get('pace_acceleration'), errors='coerce')
        pace_acceleration = pace_acceleration if pd.notna(pace_acceleration) else 0.0

        lap_count = pd.to_numeric(horse.get('lap_count'), errors='coerce')
        lap_count = lap_count if pd.notna(lap_count) else 8

        pace_cat = horse.get('pace_category', 'medium')
        pace_slow = 1 if pace_cat == 'slow' else 0
        pace_fast = 1 if pace_cat == 'fast' else 0

        # 展開予想特徴量
        escape_count = pd.to_numeric(horse.get('escape_count'), errors='coerce')
        escape_count = escape_count if pd.notna(escape_count) else 2

        leading_count = pd.to_numeric(horse.get('leading_count'), errors='coerce')
        leading_count = leading_count if pd.notna(leading_count) else 5

        sashi_count = pd.to_numeric(horse.get('sashi_count'), errors='coerce')
        sashi_count = sashi_count if pd.notna(sashi_count) else 8

        oikomi_count = pd.to_numeric(horse.get('oikomi_count'), errors='coerce')
        oikomi_count = oikomi_count if pd.notna(oikomi_count) else 3

        pace_match_score = pd.to_numeric(horse.get('pace_match_score'), errors='coerce')
        pace_match_score = pace_match_score if pd.notna(pace_match_score) else 0.5

        run_style = horse.get('running_style', 'unknown')
        is_escape = 1 if run_style == 'escape' else 0
        is_leading = 1 if run_style == 'leading' else 0
        is_sashi = 1 if run_style == 'sashi' else 0

        dev = horse.get('development', 'neutral')
        is_front_collapse = 1 if dev == 'front_collapse' else 0
        is_front_runner = 1 if dev == 'front_runner' else 0

        # 特徴量ベクトル（47次元）
        feature_vector = [
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
            style_dist['avg_agari'],
            race_class_rank,
            is_promotion,
            is_demotion,
            is_debut,
            class_rank_diff,
            first_3f_avg,
            last_3f_avg,
            pace_variance,
            pace_acceleration,
            lap_count,
            pace_slow,
            pace_fast,
            escape_count,
            leading_count,
            sashi_count,
            oikomi_count,
            pace_match_score,
            is_escape,
            is_leading,
            is_sashi
        ]

        race_features.append(feature_vector)
        horse_data.append({
            'umaban': horse.get('Umaban'),
            'rank': rank,
            'odds': odds,
            'horse_name': horse.get('HorseName')
        })

    if len(race_features) == 0:
        continue

    # 予測
    X_race = np.array(race_features)
    predictions = model.predict(X_race)

    # 本命馬を選択（予測着順が最も良い馬）
    best_idx = np.argmin(predictions)
    predicted_horse = horse_data[best_idx]

    # 単勝評価
    total_races += 1
    total_bet += 100

    if predicted_horse['rank'] == 1:
        win_count += 1
        total_return += predicted_horse['odds'] * 100

    # 3連複評価（予測上位3頭）
    top3_indices = np.argsort(predictions)[:3]
    predicted_top3 = [horse_data[i]['umaban'] for i in top3_indices]
    actual_top3 = sorted([h['umaban'] for h in horse_data if h['rank'] <= 3])

    sanrenpuku_total += 1
    if sorted(predicted_top3) == actual_top3:
        sanrenpuku_hit += 1
        # 3連複配当は仮に100倍とする（実際の配当データがないため）
        sanrenpuku_return += 100 * 100

# 結果表示
print("\n" + "="*80)
print("バックテスト結果 (2024年)")
print("="*80)

print(f"\n【単勝】")
print(f"  総レース数: {total_races}")
print(f"  的中回数: {win_count}")
print(f"  的中率: {100*win_count/total_races:.2f}%" if total_races > 0 else "  的中率: 0.00%")
print(f"  総投資額: {total_bet:,}円")
print(f"  総払戻額: {total_return:,.0f}円")
print(f"  回収率: {100*total_return/total_bet:.2f}%" if total_bet > 0 else "  回収率: 0.00%")

print(f"\n【3連複（予測上位3頭）】")
print(f"  総レース数: {sanrenpuku_total}")
print(f"  的中回数: {sanrenpuku_hit}")
print(f"  的中率: {100*sanrenpuku_hit/sanrenpuku_total:.2f}%" if sanrenpuku_total > 0 else "  的中率: 0.00%")

print("\n" + "="*80)
print("完了")
print("="*80)
