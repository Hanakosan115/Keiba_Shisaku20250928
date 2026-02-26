"""
サンプルデータで回収率を高速計算

100レースでオッズを取得して回収率を推定
"""

import pandas as pd
import numpy as np
import pickle
from scrape_odds import OddsScraper
import time

print("=" * 80)
print("サンプルデータで回収率計算（100レース）")
print("=" * 80)

# モデル読み込み
print("\nモデル読み込み中...")
with open('lgbm_model_enhanced.pkl', 'rb') as f:
    model = pickle.load(f)

# データ読み込み
print("データ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', encoding='utf-8', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年データ
test_df = df[(df['date_parsed'] >= '2024-01-01') & (df['date_parsed'] <= '2024-12-31')].copy()
test_races = test_df.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"2024年総レース数: {len(test_races)}")

# サンプル: 最初の100レース
sample_races = test_races[:100]
print(f"サンプルレース数: {len(sample_races)}")

# オッズスクレイパー
scraper = OddsScraper()

# オッズ取得
print("\nオッズ取得中...")
odds_data_dict = {}

for i, race_id in enumerate(sample_races, 1):
    if i % 10 == 0:
        print(f"  {i}/{len(sample_races)} レース処理中...")

    odds_result = scraper.scrape_race_odds(race_id)
    if odds_result and odds_result['odds_data']:
        odds_data_dict[race_id] = odds_result['odds_data']

    time.sleep(2)  # サーバー負荷軽減

print(f"\nオッズ取得成功: {len(odds_data_dict)}/{len(sample_races)} レース")

# バックテスト（簡易版）
print("\nバックテスト実行中...")

# 必要な関数（train_enhanced_model.pyから）
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

# 統計キャッシュ
jockey_stats_cache = {}
trainer_stats_cache = {}

# 結果集計
win_count = 0
total_races = 0
total_return = 0
total_bet = 0

for race_id in sample_races:
    if race_id not in odds_data_dict:
        continue  # オッズがないレースはスキップ

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
        umaban = int(horse.get('Umaban'))

        # オッズ取得
        real_odds = odds_data_dict[race_id].get(umaban)
        if not real_odds:
            continue  # オッズがない馬はスキップ

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

        style_dist = get_running_style_features(df, horse_id, race_date_str)

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

        dev = horse.get('development', 'neutral')
        is_front_collapse = 1 if dev == 'front_collapse' else 0
        is_front_runner = 1 if dev == 'front_runner' else 0

        feature_vector = [
            avg_rank, std_rank, min_rank, max_rank,
            recent_win_rate, recent_top3_rate,
            jockey_win_rate, jockey_top3_rate, jockey_races,
            trainer_win_rate, trainer_top3_rate, trainer_races,
            age, weight_diff, weight, np.log1p(real_odds), ninki, waku,
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
            'umaban': umaban,
            'rank': rank,
            'odds': real_odds,
            'horse_name': horse.get('HorseName')
        })

    if len(race_features) == 0:
        continue

    # 予測
    X_race = np.array(race_features)
    predictions = model.predict(X_race)

    # 本命馬を選択
    best_idx = np.argmin(predictions)
    predicted_horse = horse_data[best_idx]

    # 単勝評価
    total_races += 1
    total_bet += 100

    if predicted_horse['rank'] == 1:
        win_count += 1
        total_return += predicted_horse['odds'] * 100

# 結果表示
print("\n" + "=" * 80)
print(f"サンプルバックテスト結果（{total_races}レース）")
print("=" * 80)

print(f"\n【単勝】")
print(f"  総レース数: {total_races}")
print(f"  的中回数: {win_count}")
print(f"  的中率: {100*win_count/total_races:.2f}%" if total_races > 0 else "  的中率: 0.00%")
print(f"  総投資額: {total_bet:,}円")
print(f"  総払戻額: {total_return:,.0f}円")
print(f"  回収率: {100*total_return/total_bet:.2f}%" if total_bet > 0 else "  回収率: 0.00%")

if total_races > 0:
    print(f"\n【推定（全3,358レース）】")
    estimated_total_races = 3358
    estimated_win_count = int(win_count / total_races * estimated_total_races)
    estimated_recovery = 100 * total_return / total_bet
    print(f"  推定的中回数: 約{estimated_win_count}回")
    print(f"  推定回収率: 約{estimated_recovery:.2f}%")

print("\n" + "=" * 80)
print("完了")
print("=" * 80)
