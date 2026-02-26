"""
バリューベット戦略の詳細分析
- どの馬に賭けたか
- 的中した3レースの詳細
"""

import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta

def get_recent_ranks(df, horse_id, race_date_str, max_results=5):
    race_date = pd.to_datetime(race_date_str)
    horse_races = df[
        (df['horse_id'] == horse_id) &
        (df['date_parsed'] < race_date)
    ].sort_values('date_parsed', ascending=False).head(max_results)

    ranks = []
    for _, race in horse_races.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)
    return ranks

def get_all_ranks(df, horse_id, race_date_str):
    race_date = pd.to_datetime(race_date_str)
    horse_races = df[
        (df['horse_id'] == horse_id) &
        (df['date_parsed'] < race_date)
    ]

    ranks = []
    for _, race in horse_races.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)
    return ranks if len(ranks) > 0 else None

def get_distance_performance(df, horse_id, race_date_str, target_distance):
    race_date = pd.to_datetime(race_date_str)
    horse_races = df[
        (df['horse_id'] == horse_id) &
        (df['date_parsed'] < race_date)
    ].copy()

    horse_races['distance_num'] = pd.to_numeric(horse_races['distance'], errors='coerce')
    horse_races = horse_races[horse_races['distance_num'].notna()]

    distance_races = horse_races[
        (horse_races['distance_num'] >= target_distance - 200) &
        (horse_races['distance_num'] <= target_distance + 200)
    ]

    ranks = []
    for _, race in distance_races.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)
    return ranks if len(ranks) > 0 else None

def get_track_condition_performance(df, horse_id, race_date_str, target_condition):
    race_date = pd.to_datetime(race_date_str)
    horse_races = df[
        (df['horse_id'] == horse_id) &
        (df['date_parsed'] < race_date) &
        (df['track_condition'] == target_condition)
    ]

    ranks = []
    for _, race in horse_races.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)
    return ranks if len(ranks) > 0 else None

def get_running_style_features(df, horse_id, race_date_str):
    race_date = pd.to_datetime(race_date_str)
    horse_races = df[
        (df['horse_id'] == horse_id) &
        (df['date_parsed'] < race_date)
    ].tail(10)

    if len(horse_races) == 0:
        return {
            'escape_rate': 0.1,
            'leading_rate': 0.3,
            'closing_rate': 0.5,
            'pursuing_rate': 0.1,
            'avg_agari': 35.0
        }

    styles = horse_races['running_style'].value_counts()
    total = len(horse_races)

    escape_rate = styles.get('escape', 0) / total
    leading_rate = styles.get('leading', 0) / total
    closing_rate = styles.get('sashi', 0) / total
    pursuing_rate = styles.get('oikomi', 0) / total

    agari_vals = pd.to_numeric(horse_races['Agari'], errors='coerce').dropna()
    avg_agari = agari_vals.mean() if len(agari_vals) > 0 else 35.0

    return {
        'escape_rate': escape_rate,
        'leading_rate': leading_rate,
        'closing_rate': closing_rate,
        'pursuing_rate': pursuing_rate,
        'avg_agari': avg_agari
    }

def calculate_person_stats(df, person_col, race_date_str, months_back=12):
    race_date = pd.to_datetime(race_date_str)
    cutoff_date = race_date - timedelta(days=months_back*30)

    recent_df = df[
        (df['date_parsed'] >= cutoff_date) &
        (df['date_parsed'] < race_date)
    ]

    person_stats = {}

    for person in recent_df[person_col].unique():
        person_races = recent_df[recent_df[person_col] == person]
        ranks = pd.to_numeric(person_races['Rank'], errors='coerce').dropna()

        if len(ranks) > 0:
            wins = (ranks == 1).sum()
            top3 = (ranks <= 3).sum()
            person_stats[person] = {
                'win_rate': wins / len(ranks),
                'top3_rate': top3 / len(ranks),
                'races': len(ranks)
            }

    return person_stats

def extract_features(horse, race_horses, df, race_date_str, race_distance, race_condition,
                     jockey_stats, trainer_stats, odds):
    horse_id = horse.get('horse_id')

    historical_df = df[df['date_parsed'] < pd.to_datetime(race_date_str)]
    recent_ranks = get_recent_ranks(historical_df, horse_id, race_date_str, max_results=5)
    all_ranks = get_all_ranks(historical_df, horse_id, race_date_str)

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

    if len(recent_ranks) >= 3 and all_ranks:
        recent_3_avg = np.mean(recent_ranks[:3])
        overall_avg = np.mean(all_ranks)
        momentum_score = overall_avg - recent_3_avg
    else:
        momentum_score = 0.0

    if len(recent_ranks) >= 2:
        last_race_rank = recent_ranks[0]
        usual_rank = avg_rank
        is_rebound = 1 if last_race_rank - usual_rank > 3 else 0
    else:
        is_rebound = 0

    distance_ranks = get_distance_performance(historical_df, horse_id, race_date_str, race_distance)
    if distance_ranks:
        distance_fit_score = avg_rank - np.mean(distance_ranks)
        distance_experience = len(distance_ranks)
    else:
        distance_fit_score = 0.0
        distance_experience = 0

    condition_ranks = get_track_condition_performance(historical_df, horse_id, race_date_str, race_condition)
    if condition_ranks:
        condition_fit_score = avg_rank - np.mean(condition_ranks)
        condition_experience = len(condition_ranks)
    else:
        condition_fit_score = 0.0
        condition_experience = 0

    if len(recent_ranks) > 0:
        last_race_date = historical_df[
            (historical_df['horse_id'] == horse_id) &
            (historical_df['date_parsed'] < pd.to_datetime(race_date_str))
        ].sort_values('date_parsed', ascending=False).iloc[0]['date_parsed']

        days_since = (pd.to_datetime(race_date_str) - last_race_date).days
        is_fresh = 1 if days_since >= 60 else 0
        is_consecutive = 1 if days_since < 14 else 0
        days_since_norm = days_since / 30.0
        last_rank = recent_ranks[0]
    else:
        is_fresh = 0
        is_consecutive = 0
        days_since_norm = 2.0
        last_rank = 10

    style_dist = get_running_style_features(historical_df, horse_id, race_date_str)

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

    age = pd.to_numeric(horse.get('Age'), errors='coerce')
    age = age if pd.notna(age) else 5

    weight_diff = pd.to_numeric(horse.get('WeightDiff'), errors='coerce')
    weight_diff = weight_diff if pd.notna(weight_diff) else 0

    weight = pd.to_numeric(horse.get('Weight'), errors='coerce')
    weight = weight if pd.notna(weight) else 480

    log_odds = np.log(odds) if odds > 0 else np.log(50)
    ninki = pd.to_numeric(horse.get('Ninki'), errors='coerce')
    ninki = ninki if pd.notna(ninki) else 10

    waku = pd.to_numeric(horse.get('Waku'), errors='coerce')
    waku = waku if pd.notna(waku) else 5

    course_type = horse.get('course_type')
    course_turf = 1 if course_type == '芝' else 0
    course_dirt = 1 if course_type == 'ダート' else 0

    track_condition = horse.get('track_condition')
    track_good = 1 if track_condition == '良' else 0

    distance = pd.to_numeric(horse.get('distance'), errors='coerce')
    distance = distance if pd.notna(distance) else 1600

    race_class_rank = pd.to_numeric(horse.get('race_class_rank'), errors='coerce')
    race_class_rank = race_class_rank if pd.notna(race_class_rank) else 0

    prev_race_class_rank = pd.to_numeric(horse.get('prev_race_class_rank'), errors='coerce')
    prev_race_class_rank = prev_race_class_rank if pd.notna(prev_race_class_rank) else 0

    class_change = horse.get('class_change', 'same')
    is_promotion = 1 if class_change == 'promotion' else 0
    is_demotion = 1 if class_change == 'demotion' else 0
    is_debut = 1 if class_change == 'debut' else 0

    class_rank_diff = race_class_rank - prev_race_class_rank if prev_race_class_rank != 0 else 0

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

    return [
        avg_rank, std_rank, min_rank, max_rank,
        recent_win_rate, recent_top3_rate,
        jockey_win_rate, jockey_top3_rate, jockey_races,
        trainer_win_rate, trainer_top3_rate, trainer_races,
        age, weight_diff, weight, log_odds, ninki, waku,
        course_turf, course_dirt, track_good, distance / 1000,
        style_dist['escape_rate'], style_dist['leading_rate'],
        style_dist['closing_rate'], style_dist['pursuing_rate'],
        style_dist['avg_agari'],
        race_class_rank, is_promotion, is_demotion, is_debut, class_rank_diff,
        first_3f_avg, last_3f_avg, pace_variance, pace_acceleration,
        lap_count, pace_slow, pace_fast,
        escape_count, leading_count, sashi_count, oikomi_count,
        pace_match_score, is_escape, is_leading, is_sashi,
        momentum_score, is_rebound,
        distance_fit_score, distance_experience,
        condition_fit_score, condition_experience,
        is_fresh, is_consecutive, days_since_norm, last_rank
    ]

print("="*80)
print("バリューベット戦略 詳細分析（閾値5%）")
print("="*80)

# モデル読み込み
print("\nモデル読み込み中...")
with open('lgbm_model_hybrid.pkl', 'rb') as f:
    model = pickle.load(f)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv',
                 encoding='utf-8', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 実オッズ読み込み
odds_df = pd.read_csv('odds_2024_sample_500.csv', encoding='utf-8')
odds_df['race_id'] = odds_df['race_id'].astype(str)
df['race_id'] = df['race_id'].astype(str)

odds_race_ids = odds_df['race_id'].unique()

# 統計キャッシュ
jockey_stats_cache = {}
trainer_stats_cache = {}

# 閾値5%でベットした馬の詳細
VALUE_THRESHOLD = 0.05
bet_details = []

print("\n分析中...")

for idx, race_id in enumerate(odds_race_ids):
    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_date_str = race_horses.iloc[0]['date']
    race_distance = pd.to_numeric(race_horses.iloc[0]['distance'], errors='coerce')
    race_distance = race_distance if pd.notna(race_distance) else 1600
    race_condition = race_horses.iloc[0]['track_condition']

    if race_date_str not in jockey_stats_cache:
        historical_df = df[df['date_parsed'] < pd.to_datetime(race_date_str)]
        jockey_stats_cache[race_date_str] = calculate_person_stats(
            historical_df, 'JockeyName', race_date_str, months_back=12
        )
        trainer_stats_cache[race_date_str] = calculate_person_stats(
            historical_df, 'TrainerName', race_date_str, months_back=12
        )

    jockey_stats = jockey_stats_cache[race_date_str]
    trainer_stats = trainer_stats_cache[race_date_str]

    horses_data = []

    for _, horse in race_horses.iterrows():
        umaban = horse.get('Umaban')
        actual_rank = pd.to_numeric(horse.get('Rank'), errors='coerce')
        horse_name = horse.get('HorseName')

        odds_match = odds_df[
            (odds_df['race_id'] == race_id) &
            (odds_df['Umaban'] == umaban)
        ]

        if len(odds_match) == 0:
            continue

        odds = odds_match.iloc[0]['odds_real']

        features = extract_features(
            horse, race_horses, df, race_date_str, race_distance, race_condition,
            jockey_stats, trainer_stats, odds
        )

        horses_data.append({
            'umaban': umaban,
            'horse_name': horse_name,
            'features': features,
            'odds': odds,
            'actual_rank': actual_rank
        })

    if len(horses_data) == 0:
        continue

    # 予測実行
    X_race = np.array([h['features'] for h in horses_data])
    predicted_ranks = model.predict(X_race)

    scores = np.array([1.0 / max(rank, 1.0) for rank in predicted_ranks])
    predicted_probs = scores / scores.sum()

    for i, horse_data in enumerate(horses_data):
        horse_data['predicted_prob'] = predicted_probs[i]
        horse_data['market_prob'] = 1.0 / horse_data['odds']
        horse_data['value'] = horse_data['predicted_prob'] - horse_data['market_prob']

    # バリューがある馬を抽出
    value_horses = [h for h in horses_data if h['value'] >= VALUE_THRESHOLD]

    if len(value_horses) == 0:
        continue

    # 最もバリューが高い馬
    best_horse = max(value_horses, key=lambda x: x['value'])

    bet_details.append({
        'race_id': race_id,
        'date': race_date_str,
        'umaban': best_horse['umaban'],
        'horse_name': best_horse['horse_name'],
        'odds': best_horse['odds'],
        'predicted_prob': best_horse['predicted_prob'],
        'market_prob': best_horse['market_prob'],
        'value': best_horse['value'],
        'actual_rank': best_horse['actual_rank'],
        'result': 'WIN' if best_horse['actual_rank'] == 1 else 'LOSE'
    })

# 結果表示
bets_df = pd.DataFrame(bet_details)

print(f"\n総ベット数: {len(bets_df)}レース")
print(f"的中数: {(bets_df['result'] == 'WIN').sum()}レース")

print("\n" + "="*80)
print("的中レース詳細")
print("="*80)

wins = bets_df[bets_df['result'] == 'WIN']

if len(wins) > 0:
    for idx, row in wins.iterrows():
        print(f"\n【的中{idx+1}】")
        print(f"  レースID: {row['race_id']}")
        print(f"  日付: {row['date']}")
        print(f"  馬名: {row['horse_name']} ({row['umaban']}番)")
        print(f"  オッズ: {row['odds']:.1f}倍")
        print(f"  予測確率: {row['predicted_prob']*100:.2f}%")
        print(f"  市場確率: {row['market_prob']*100:.2f}%")
        print(f"  バリュー: +{row['value']*100:.2f}%")
        print(f"  払戻: {row['odds'] * 100:.0f}円")

print("\n" + "="*80)
print("回収率計算")
print("="*80)

total_investment = len(bets_df) * 100
total_return = (bets_df[bets_df['result'] == 'WIN']['odds'] * 100).sum()
recovery_rate = 100 * total_return / total_investment if total_investment > 0 else 0

print(f"\n総投資: {total_investment:,}円")
print(f"総払戻: {total_return:,.0f}円")
print(f"回収率: {recovery_rate:.1f}%")
print(f"損益: {total_return - total_investment:+,.0f}円")

# 全ベット詳細をCSV保存
bets_df.to_csv('value_bets_detail.csv', index=False, encoding='utf-8')
print("\n詳細をvalue_bets_detail.csvに保存しました")

print("\n" + "="*80)
print("完了")
print("="*80)
