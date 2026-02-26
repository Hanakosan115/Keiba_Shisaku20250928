"""
確信度フィルタリング バックテスト（実モデル使用版）
実際のLightGBMモデルを使って予測し、確信度でフィルタリング
"""
import pandas as pd
import numpy as np
import json
import pickle
from data_config import MAIN_CSV, MAIN_JSON

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
    """脚質分類"""
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

def calculate_trifecta_features(df, horse_id, race_date_str, max_results=10):
    """3連単特化特徴量を計算（過去データのみ使用）"""
    race_date_parsed = pd.to_datetime(race_date_str)

    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')

    # レース日より前のデータのみ
    past_races = horse_races[horse_races['date_parsed'] < race_date_parsed]
    past_races = past_races.sort_values('date_parsed', ascending=False).head(max_results)

    if len(past_races) == 0:
        return {
            'avg_rank': 8, 'std_rank': 0, 'race_count': 0,
            'win_rate': 0, 'top3_rate': 0,
            'escape_rate': 0, 'leading_rate': 0, 'closing_rate': 0, 'pursuing_rate': 0,
            'avg_agari': 0,
            'closing_success_rate': 0, 'position_stability': 0, 'close_finish_rate': 0,
            'second_place_rate': 0, 'third_place_rate': 0,
            'front_collapse_rate': 0, 'late_charge_rate': 0,
        }

    ranks = pd.to_numeric(past_races['Rank'], errors='coerce').dropna()

    features = {
        'avg_rank': ranks.mean() if len(ranks) > 0 else 8,
        'std_rank': ranks.std() if len(ranks) > 1 else 0,
        'race_count': len(ranks),
        'win_rate': (ranks == 1).sum() / len(ranks) if len(ranks) > 0 else 0,
        'top3_rate': (ranks <= 3).sum() / len(ranks) if len(ranks) > 0 else 0,
    }

    # 脚質と3連単特化指標
    styles = {'escape': 0, 'leading': 0, 'closing': 0, 'pursuing': 0}
    agari_times = []
    closing_success = 0
    position_changes = []
    close_finishes = 0
    second_places = 0
    third_places = 0
    front_collapses = 0
    late_charges = 0

    for _, race in past_races.iterrows():
        passage = race.get('Passage')
        positions = parse_passage_full(passage)

        early_pos = positions[0]
        late_pos = positions[3]

        style = classify_running_style(early_pos)
        if style:
            styles[style] += 1

        agari = pd.to_numeric(race.get('Agari'), errors='coerce')
        if pd.notna(agari) and agari > 0:
            agari_times.append(agari)

        rank = pd.to_numeric(race.get('Rank'), errors='coerce')

        # 位置変化
        if early_pos is not None and late_pos is not None:
            position_changes.append(abs(late_pos - early_pos))

        # 差し脚評価
        if early_pos is not None and rank is not None:
            if early_pos > 8 and rank <= 3:
                closing_success += 1

            if style in ['closing', 'pursuing'] and rank <= 3:
                late_charges += 1

            if style in ['escape', 'leading'] and rank > 3:
                front_collapses += 1

        # 着順カウント
        if rank == 2:
            second_places += 1
        elif rank == 3:
            third_places += 1

        # 接戦判定
        diff = race.get('Diff', '')
        if isinstance(diff, str) and diff != '':
            try:
                diff_val = float(diff)
                if diff_val <= 1.0:
                    close_finishes += 1
            except:
                if 'クビ' in diff or 'ハナ' in diff or 'アタマ' in diff:
                    close_finishes += 1

    total_races = len(past_races)

    # 脚質率
    features['escape_rate'] = styles['escape'] / total_races
    features['leading_rate'] = styles['leading'] / total_races
    features['closing_rate'] = styles['closing'] / total_races
    features['pursuing_rate'] = styles['pursuing'] / total_races
    features['avg_agari'] = np.mean(agari_times) if agari_times else 0

    # 3連単特化特徴
    features['closing_success_rate'] = closing_success / total_races
    features['position_stability'] = 1 / (1 + np.mean(position_changes)) if position_changes else 0
    features['close_finish_rate'] = close_finishes / total_races
    features['second_place_rate'] = second_places / total_races
    features['third_place_rate'] = third_places / total_races
    features['front_collapse_rate'] = front_collapses / max(styles['escape'] + styles['leading'], 1)
    features['late_charge_rate'] = late_charges / max(styles['closing'] + styles['pursuing'], 1)

    return features

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
            }

    return person_stats

def load_payout_data(json_path):
    """配当データ読み込み"""
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)

    payout_dict = {}
    for race in payout_list:
        race_id = race.get('race_id')
        if race_id:
            payout_dict[str(race_id)] = race

    return payout_dict

print("=" * 80)
print("確信度フィルタリング バックテスト（実モデル使用版）")
print("=" * 80)

# モデル読み込み
print("\n3連単特化モデル読み込み中...")
with open('lightgbm_model_trifecta_optimized_fixed.pkl', 'rb') as f:
    model_data = pickle.load(f)
    model = model_data['model']
    feature_names = model_data['feature_names']

print(f"モデル特徴量: {len(feature_names)}次元")

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

payout_dict = load_payout_data(MAIN_JSON)

# 2024年のデータ
target_races = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()
print(f"対象: 2024年 {len(race_ids):,}レース")

# 全レースのデータを保存
race_results = []
stats_cache = {}
processed = 0

print("\nレースデータ収集中...")
for race_id in race_ids:
    processed += 1
    if processed % 500 == 0:
        print(f"  進捗: {processed}/{len(race_ids)} ({processed/len(race_ids)*100:.1f}%)")

    race_horses = df[df['race_id'] == race_id].copy()
    if len(race_horses) < 8:
        continue

    # レース日付取得
    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue
    race_date_str = str(race_date)[:10]

    # 騎手・調教師統計（キャッシュ）
    if race_date_str not in stats_cache:
        stats_cache[race_date_str] = {
            'jockey': calculate_person_stats(df, 'JockeyName', race_date_str, months_back=12),
            'trainer': calculate_person_stats(df, 'TrainerName', race_date_str, months_back=12)
        }

    jockey_stats = stats_cache[race_date_str]['jockey']
    trainer_stats = stats_cache[race_date_str]['trainer']

    # 各馬の特徴量を構築
    horse_features = []
    horse_umabans = []

    for _, horse in race_horses.iterrows():
        horse_id = horse.get('horse_id')
        umaban = int(horse.get('Umaban', 0))
        if umaban == 0:
            continue

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

        # 馬の統計取得（過去データのみ）
        stats = calculate_trifecta_features(df, horse_id, race_date_str, max_results=10)

        # 騎手・調教師統計
        jockey = jockey_stats.get(horse.get('JockeyName'), {'win_rate': 0, 'top3_rate': 0})
        trainer = trainer_stats.get(horse.get('TrainerName'), {'win_rate': 0, 'top3_rate': 0})

        # 特徴量ベクトル作成（31次元）
        feature_vector = [
            # 基本成績（5）
            stats['avg_rank'], stats['std_rank'], stats['race_count'],
            stats['win_rate'], stats['top3_rate'],

            # 騎手・調教師（4）
            jockey['win_rate'], jockey['top3_rate'],
            trainer['win_rate'], trainer['top3_rate'],

            # 馬体・オッズ（5）
            age, weight_diff, weight, np.log1p(odds), ninki,

            # レース条件（4）
            waku, course_turf, course_dirt, track_good,

            # 距離（1）
            distance / 1000,

            # 脚質（5）
            stats['escape_rate'], stats['leading_rate'], stats['closing_rate'],
            stats['pursuing_rate'], stats['avg_agari'],

            # 3連単特化（7）
            stats['closing_success_rate'],
            stats['position_stability'],
            stats['close_finish_rate'],
            stats['second_place_rate'],
            stats['third_place_rate'],
            stats['front_collapse_rate'],
            stats['late_charge_rate'],
        ]

        horse_features.append(feature_vector)
        horse_umabans.append(umaban)

    if len(horse_features) < 8:
        continue

    # モデル予測
    X = np.array(horse_features)
    pred_scores = model.predict(X)

    # 予測順位（スコアが低いほど上位）
    predicted_ranking = sorted(zip(horse_umabans, pred_scores), key=lambda x: x[1])

    pred_horses = [h[0] for h in predicted_ranking[:8]]
    pred_scores_sorted = [h[1] for h in predicted_ranking[:8]]

    # 確信度（1位と2位のスコア差の絶対値）
    score_gap = abs(pred_scores_sorted[1] - pred_scores_sorted[0]) if len(pred_scores_sorted) > 1 else 0

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data or 'ワイド' not in payout_data:
        continue

    wide_data = payout_data['ワイド']
    wide_horses = wide_data.get('馬番', [])
    wide_payouts = wide_data.get('払戻金', [])

    # ワイド_1-3の結果
    pred_wide = set([str(pred_horses[0]), str(pred_horses[2])])
    is_hit = False
    payout = 0

    for i in range(0, len(wide_horses), 2):
        if i + 1 < len(wide_horses):
            actual_wide = set([wide_horses[i], wide_horses[i+1]])
            if pred_wide == actual_wide:
                payout_value = wide_payouts[i] if i < len(wide_payouts) else 0
                if payout_value is not None:
                    payout = payout_value
                    is_hit = True
                    break

    race_results.append({
        'score_gap': score_gap,
        'is_hit': is_hit,
        'payout': payout,
        'cost': 100
    })

print(f"\n収集完了: {len(race_results):,}レース")

# 確信度でソート（大きい方が確信度高い）
race_results_sorted = sorted(race_results, key=lambda x: x['score_gap'], reverse=True)

# 複数の閾値でテスト
print("\n" + "=" * 80)
print("【確信度フィルタリング結果】")
print("=" * 80)
print(f"{'閾値':10s} | {'レース数':>8s} | {'的中数':>6s} | {'的中率':>6s} | {'投資額':>10s} | {'払戻額':>10s} | {'回収率':>7s}")
print("-" * 80)

thresholds = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
best_recovery = 0
best_threshold = 0

for percentile in thresholds:
    # 上位X%のレースのみ
    num_races = int(len(race_results_sorted) * (100 - percentile) / 100)
    if num_races == 0:
        continue

    selected_races = race_results_sorted[:num_races]

    total_races = len(selected_races)
    hit_count = sum(1 for r in selected_races if r['is_hit'])
    total_cost = sum(r['cost'] for r in selected_races)
    total_return = sum(r['payout'] for r in selected_races)

    hit_rate = hit_count / total_races * 100 if total_races > 0 else 0
    recovery = total_return / total_cost * 100 if total_cost > 0 else 0

    if recovery > best_recovery:
        best_recovery = recovery
        best_threshold = percentile

    threshold_label = f"全体" if percentile == 0 else f"上位{100-percentile}%"
    print(f"{threshold_label:10s} | {total_races:8d} | {hit_count:6d} | {hit_rate:5.1f}% | "
          f"{total_cost:>10,}円 | {total_return:>10,}円 | {recovery:6.1f}%")

print("\n" + "=" * 80)
print("【最適閾値】")
print("=" * 80)
print(f"最高回収率: {best_recovery:.1f}% (確信度 上位{100-best_threshold}%のレース)")
print("\n" + "=" * 80)
print("【前回（オッズベース）との比較】")
print("=" * 80)
print("前回の最高回収率: 93.2% (簡易オッズベーススコア)")
print(f"今回の最高回収率: {best_recovery:.1f}% (実モデル予測スコア)")
print("\n調教データなど追加情報で、さらなる改善の可能性あり！")
