"""
バリューベット戦略のバックテスト

オッズなしモデルの予測と市場オッズを比較し、
バリュー（割安）がある馬のみに賭ける
"""

import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta

def get_recent_ranks(df, horse_id, race_date_str, max_results=5):
    """指定日以前の過去成績を取得"""
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

def get_running_style_features(df, horse_id, race_date_str):
    """脚質分布を計算"""
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
    """騎手・調教師統計を計算"""
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

print("="*80)
print("バリューベット戦略バックテスト")
print("  モデル: オッズなしモデル")
print("  戦略: 予測確率 > 市場確率 の時のみベット")
print("="*80)

# モデル読み込み
print("\nモデル読み込み中...")
with open('lgbm_model_no_odds.pkl', 'rb') as f:
    model = pickle.load(f)

print("モデル読み込み完了")

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv',
                 encoding='utf-8', low_memory=False)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年データでテスト
test_df = df[df['date_parsed'] >= '2024-01-01'].copy()
print(f"テストデータ: {len(test_df):,}件 (2024年)")

# レースごとに処理
test_races = test_df['race_id'].unique()
print(f"テストレース数: {len(test_races):,}レース")

# オッズをスクレイピングしたものを使う（scrape_odds.pyで取得）
# ここではtest_dfに既にodds_scrapedがある前提
# なければOddsカラムを使う
if 'odds_scraped' in test_df.columns:
    print("スクレイピングオッズを使用")
    test_df['odds_to_use'] = test_df['odds_scraped'].fillna(test_df['Odds'])
else:
    print("Oddsカラムを使用（一部データなし）")
    test_df['odds_to_use'] = test_df['Odds']

# 統計キャッシュ
jockey_stats_cache = {}
trainer_stats_cache = {}

# バリュー判定の閾値を複数テスト
value_thresholds = [0.0, 0.05, 0.10, 0.15, 0.20, 0.25, 0.30]

results_by_threshold = {}

for threshold in value_thresholds:
    results_by_threshold[threshold] = {
        'total_bets': 0,
        'total_wins': 0,
        'total_investment': 0,
        'total_return': 0,
        'bet_races': []
    }

print("\nバックテスト実行中...")

for idx, race_id in enumerate(test_races):
    if (idx + 1) % 500 == 0:
        print(f"  進捗: {idx+1}/{len(test_races)} ({100*(idx+1)/len(test_races):.1f}%)")

    race_horses = test_df[test_df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_date_str = race_horses.iloc[0]['date']

    # 統計計算（訓練データ＋過去のテストデータで計算）
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

    # 各馬の特徴量を抽出（オッズなし）
    horses_data = []

    for _, horse in race_horses.iterrows():
        horse_id = horse.get('horse_id')
        umaban = horse.get('Umaban')
        actual_rank = pd.to_numeric(horse.get('Rank'), errors='coerce')

        # オッズ取得
        odds = pd.to_numeric(horse.get('odds_to_use'), errors='coerce')
        if pd.isna(odds) or odds <= 0:
            odds = 50.0  # デフォルト

        # 過去成績
        historical_df = df[df['date_parsed'] < pd.to_datetime(race_date_str)]
        recent_ranks = get_recent_ranks(historical_df, horse_id, race_date_str, max_results=5)

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
        style_dist = get_running_style_features(historical_df, horse_id, race_date_str)

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

        # ラップタイム
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

        # 展開予想
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

        # 特徴量ベクトル（オッズなし、45次元）
        feature_vector = [
            avg_rank, std_rank, min_rank, max_rank,
            recent_win_rate, recent_top3_rate,
            jockey_win_rate, jockey_top3_rate, jockey_races,
            trainer_win_rate, trainer_top3_rate, trainer_races,
            age, weight_diff, weight, waku,
            course_turf, course_dirt, track_good, distance / 1000,
            style_dist['escape_rate'], style_dist['leading_rate'],
            style_dist['closing_rate'], style_dist['pursuing_rate'],
            style_dist['avg_agari'],
            race_class_rank, is_promotion, is_demotion, is_debut, class_rank_diff,
            first_3f_avg, last_3f_avg, pace_variance, pace_acceleration,
            lap_count, pace_slow, pace_fast,
            escape_count, leading_count, sashi_count, oikomi_count,
            pace_match_score, is_escape, is_leading, is_sashi,
        ]

        horses_data.append({
            'umaban': umaban,
            'features': feature_vector,
            'odds': odds,
            'actual_rank': actual_rank
        })

    if len(horses_data) == 0:
        continue

    # 予測実行
    X_race = np.array([h['features'] for h in horses_data])
    predicted_ranks = model.predict(X_race)

    # 予測順位から勝率を推定（簡易的に）
    # predicted_rank が小さいほど勝率が高い
    # 簡易式: win_prob ≈ 1 / (predicted_rank + offset)
    # より精密にはソフトマックスなどを使うべきだが、ここでは簡易版

    for i, horse_data in enumerate(horses_data):
        horse_data['predicted_rank'] = predicted_ranks[i]

    # レース内で相対的な勝率を計算（ソフトマックス的に）
    # スコア = 1 / predicted_rank
    scores = np.array([1.0 / max(h['predicted_rank'], 1.0) for h in horses_data])
    predicted_probs = scores / scores.sum()  # 合計1に正規化

    for i, horse_data in enumerate(horses_data):
        horse_data['predicted_prob'] = predicted_probs[i]
        horse_data['market_prob'] = 1.0 / horse_data['odds']  # 市場の暗黙勝率
        horse_data['value'] = horse_data['predicted_prob'] - horse_data['market_prob']

    # 各閾値でベット判定
    for threshold in value_thresholds:
        # バリューが閾値以上の馬を抽出
        value_horses = [h for h in horses_data if h['value'] >= threshold]

        if len(value_horses) == 0:
            continue

        # 最もバリューが高い馬にベット
        best_horse = max(value_horses, key=lambda x: x['value'])

        results_by_threshold[threshold]['total_bets'] += 1
        results_by_threshold[threshold]['total_investment'] += 100

        if best_horse['actual_rank'] == 1:
            results_by_threshold[threshold]['total_wins'] += 1
            results_by_threshold[threshold]['total_return'] += best_horse['odds'] * 100

print("\n" + "="*80)
print("バリューベット戦略結果")
print("="*80)

print("\n{:>10s} | {:>8s} | {:>8s} | {:>12s} | {:>12s} | {:>8s}".format(
    "閾値", "ベット数", "的中数", "投資額", "回収額", "回収率"
))
print("-" * 80)

for threshold in value_thresholds:
    result = results_by_threshold[threshold]
    total_bets = result['total_bets']
    total_wins = result['total_wins']
    total_investment = result['total_investment']
    total_return = result['total_return']

    if total_bets > 0:
        win_rate = 100 * total_wins / total_bets
        recovery_rate = 100 * total_return / total_investment
    else:
        win_rate = 0
        recovery_rate = 0

    print("{:>10.2f} | {:>8d} | {:>8d} | {:>12,d}円 | {:>12,.0f}円 | {:>7.1f}%".format(
        threshold, total_bets, total_wins, total_investment, total_return, recovery_rate
    ))

print("\n" + "="*80)
print("完了")
print("="*80)

# 最も回収率が高い閾値を表示
best_threshold = None
best_recovery = 0

for threshold in value_thresholds:
    result = results_by_threshold[threshold]
    if result['total_bets'] > 0:
        recovery = 100 * result['total_return'] / result['total_investment']
        if recovery > best_recovery:
            best_recovery = recovery
            best_threshold = threshold

if best_threshold is not None:
    print(f"\n最適閾値: {best_threshold:.2f} (回収率: {best_recovery:.1f}%)")
