"""
次世代統合モデル（42次元）のバックテスト
- 展開予想
- トラックバイアス
- コース適性
を含む高度な予測モデルの評価
"""
import pandas as pd
import numpy as np
import pickle
from datetime import datetime

# 競馬場の回り方向マスタデータ
TRACK_TURN_DIRECTION = {
    '東京': 'left',
    '中山': 'right',
    '阪神': 'right',
    '京都': 'right',
    '中京': 'left',
    '新潟': 'left',
    '福島': 'right',
    '小倉': 'right',
    '札幌': 'right',
    '函館': 'right'
}

def parse_passage_full(passage_str):
    """
    Passage文字列を完全解析
    "11-12-15-8" -> [11, 12, 15, 8] (4コーナー分)
    "5-5" -> [5, None, None, 5] (序盤と終盤のみ)
    """
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
    """序盤位置から脚質を分類"""
    if early_position is None or early_position == 0:
        return None
    if early_position <= 2:
        return 'escape'  # 逃げ
    elif early_position <= 5:
        return 'leading'  # 先行
    elif early_position <= 10:
        return 'closing'  # 差し
    else:
        return 'pursuing'  # 追い込み

def calculate_running_style_features(df, horse_id, race_date_str):
    """脚質特徴量を計算（過去レースから）"""
    race_date_parsed = pd.to_datetime(race_date_str)

    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')

    past_races = horse_races[horse_races['date_parsed'] < race_date_parsed]

    if len(past_races) == 0:
        return {
            'escape_rate': 0,
            'leading_rate': 0,
            'closing_rate': 0,
            'pursuing_rate': 0,
            'avg_agari': 0,
            'has_past_results': 0,
            'position_change_ability': 0,
            'agari_stability': 0
        }

    styles = {'escape': 0, 'leading': 0, 'closing': 0, 'pursuing': 0}
    agari_times = []
    position_changes = []

    for _, race in past_races.iterrows():
        passage = race.get('Passage')
        positions = parse_passage_full(passage)

        early_pos = positions[0]
        late_pos = positions[3]

        style = classify_running_style(early_pos)
        if style:
            styles[style] += 1

        agari = pd.to_numeric(race.get('Agari'), errors='coerce')
        if pd.notna(agari):
            agari_times.append(agari)

        if early_pos is not None and late_pos is not None:
            position_changes.append(late_pos - early_pos)

    total_races = len(past_races)

    return {
        'escape_rate': styles['escape'] / total_races,
        'leading_rate': styles['leading'] / total_races,
        'closing_rate': styles['closing'] / total_races,
        'pursuing_rate': styles['pursuing'] / total_races,
        'avg_agari': np.mean(agari_times) if agari_times else 0,
        'has_past_results': 1,
        'position_change_ability': np.mean(position_changes) if position_changes else 0,
        'agari_stability': np.std(agari_times) if len(agari_times) > 1 else 0
    }

def calculate_track_aptitude(df, horse_id, track_name, race_date_str):
    """特定競馬場での適性を計算"""
    race_date_parsed = pd.to_datetime(race_date_str)

    horse_races = df[(df['horse_id'] == horse_id) &
                     (df['track_name'] == track_name)].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')

    past_races = horse_races[horse_races['date_parsed'] < race_date_parsed]

    if len(past_races) == 0:
        return 0, 0

    ranks = []
    for _, race in past_races.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)

    if ranks:
        return np.mean(ranks), len(ranks)
    else:
        return 0, 0

def calculate_distance_aptitude(df, horse_id, target_distance, race_date_str, tolerance=200):
    """距離適性を計算（±tolerance m）"""
    race_date_parsed = pd.to_datetime(race_date_str)

    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')
    horse_races['distance_num'] = pd.to_numeric(horse_races['distance'], errors='coerce')

    similar_distance = horse_races[
        (horse_races['distance_num'] >= target_distance - tolerance) &
        (horse_races['distance_num'] <= target_distance + tolerance) &
        (horse_races['date_parsed'] < race_date_parsed)
    ]

    if len(similar_distance) == 0:
        return 0, 0

    ranks = []
    for _, race in similar_distance.iterrows():
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)

    if ranks:
        return np.mean(ranks), len(ranks)
    else:
        return 0, 0

def calculate_turn_aptitude(df, horse_id, turn_direction, race_date_str):
    """回り方向適性を計算"""
    race_date_parsed = pd.to_datetime(race_date_str)

    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')

    matching_races = []
    for _, race in horse_races.iterrows():
        if race['date_parsed'] >= race_date_parsed:
            continue
        track = race.get('track_name', '')
        if TRACK_TURN_DIRECTION.get(track) == turn_direction:
            matching_races.append(race)

    if len(matching_races) == 0:
        return 0, 0

    ranks = []
    for race in matching_races:
        rank = pd.to_numeric(race.get('Rank'), errors='coerce')
        if pd.notna(rank):
            ranks.append(rank)

    if ranks:
        return np.mean(ranks), len(ranks)
    else:
        return 0, 0

def get_race_pace_scenario(race_df):
    """レース全体の展開予想"""
    escape_count = 0
    leading_count = 0
    total_horses = len(race_df)

    for _, horse in race_df.iterrows():
        passage = horse.get('Passage')
        positions = parse_passage_full(passage)
        early_pos = positions[0]

        style = classify_running_style(early_pos)
        if style == 'escape':
            escape_count += 1
        elif style == 'leading':
            leading_count += 1

    if escape_count >= 2:
        return 'high_pace', escape_count
    elif escape_count == 1 and leading_count <= 2:
        return 'slow_pace', escape_count
    else:
        return 'average_pace', escape_count

def extract_features_advanced(df, race_id, umaban):
    """42次元の高度特徴量を抽出"""
    race_data = df[df['race_id'] == race_id]
    horse_data = race_data[race_data['Umaban'] == umaban]

    if len(horse_data) == 0:
        return None

    horse_data = horse_data.iloc[0]
    horse_id = horse_data.get('horse_id')
    race_date = horse_data.get('date')

    if pd.isna(horse_id) or pd.isna(race_date):
        return None

    race_date_parsed = pd.to_datetime(race_date)

    # 過去レース取得
    past_races = df[(df['horse_id'] == horse_id) &
                    (pd.to_datetime(df['date'], errors='coerce') < race_date_parsed)]

    # 基本成績
    if len(past_races) > 0:
        ranks = pd.to_numeric(past_races['Rank'], errors='coerce').dropna()
        if len(ranks) > 0:
            avg_rank = ranks.mean()
            std_rank = ranks.std() if len(ranks) > 1 else 0
            min_rank = ranks.min()
            max_rank = ranks.max()
            recent_win_rate = (ranks.tail(5) == 1).sum() / min(5, len(ranks))
            recent_top3_rate = (ranks.tail(5) <= 3).sum() / min(5, len(ranks))
        else:
            avg_rank = 8
            std_rank = 0
            min_rank = 8
            max_rank = 8
            recent_win_rate = 0
            recent_top3_rate = 0
    else:
        avg_rank = 8
        std_rank = 0
        min_rank = 8
        max_rank = 8
        recent_win_rate = 0
        recent_top3_rate = 0

    # 騎手統計
    jockey_name = horse_data.get('JockeyName')
    if pd.notna(jockey_name):
        jockey_races = df[(df['JockeyName'] == jockey_name) &
                         (pd.to_datetime(df['date'], errors='coerce') < race_date_parsed)]
        if len(jockey_races) > 0:
            jockey_ranks = pd.to_numeric(jockey_races['Rank'], errors='coerce').dropna()
            jockey_win_rate = (jockey_ranks == 1).sum() / len(jockey_ranks) if len(jockey_ranks) > 0 else 0
            jockey_top3_rate = (jockey_ranks <= 3).sum() / len(jockey_ranks) if len(jockey_ranks) > 0 else 0
            jockey_races_count = len(jockey_races)
        else:
            jockey_win_rate = 0
            jockey_top3_rate = 0
            jockey_races_count = 0
    else:
        jockey_win_rate = 0
        jockey_top3_rate = 0
        jockey_races_count = 0

    # 調教師統計
    trainer_name = horse_data.get('TrainerName')
    if pd.notna(trainer_name):
        trainer_races = df[(df['TrainerName'] == trainer_name) &
                          (pd.to_datetime(df['date'], errors='coerce') < race_date_parsed)]
        if len(trainer_races) > 0:
            trainer_ranks = pd.to_numeric(trainer_races['Rank'], errors='coerce').dropna()
            trainer_win_rate = (trainer_ranks == 1).sum() / len(trainer_ranks) if len(trainer_ranks) > 0 else 0
            trainer_top3_rate = (trainer_ranks <= 3).sum() / len(trainer_ranks) if len(trainer_ranks) > 0 else 0
            trainer_races_count = len(trainer_races)
        else:
            trainer_win_rate = 0
            trainer_top3_rate = 0
            trainer_races_count = 0
    else:
        trainer_win_rate = 0
        trainer_top3_rate = 0
        trainer_races_count = 0

    # 馬体情報
    age = pd.to_numeric(horse_data.get('Age'), errors='coerce')
    age = age if pd.notna(age) else 4

    weight_diff = pd.to_numeric(horse_data.get('WeightDiff'), errors='coerce')
    weight_diff = weight_diff if pd.notna(weight_diff) else 0

    weight = pd.to_numeric(horse_data.get('Weight'), errors='coerce')
    weight = weight if pd.notna(weight) else 480

    odds = pd.to_numeric(horse_data.get('Odds_x'), errors='coerce')
    if pd.isna(odds) or odds <= 0:
        odds = pd.to_numeric(horse_data.get('Odds_y'), errors='coerce')
    odds = odds if pd.notna(odds) and odds > 0 else 10

    ninki = pd.to_numeric(horse_data.get('Ninki'), errors='coerce')
    ninki = ninki if pd.notna(ninki) else 8

    waku = pd.to_numeric(horse_data.get('Waku'), errors='coerce')
    waku = waku if pd.notna(waku) else 4

    # レース条件
    course_type = horse_data.get('course_type', '')
    course_turf = 1 if '芝' in str(course_type) else 0
    course_dirt = 1 if 'ダ' in str(course_type) else 0

    track_condition = horse_data.get('track_condition', '')
    track_good = 1 if '良' in str(track_condition) else 0

    distance = pd.to_numeric(horse_data.get('distance'), errors='coerce')
    distance = distance if pd.notna(distance) else 1600

    track_name = horse_data.get('track_name', '')

    # 脚質特徴量
    style_features = calculate_running_style_features(df, horse_id, race_date)

    # コース適性
    track_avg_rank, track_races = calculate_track_aptitude(df, horse_id, track_name, race_date)
    distance_avg_rank, distance_races = calculate_distance_aptitude(df, horse_id, distance, race_date)

    turn_direction = TRACK_TURN_DIRECTION.get(track_name, 'unknown')
    turn_avg_rank, turn_races = calculate_turn_aptitude(df, horse_id, turn_direction, race_date)

    # 展開予想
    pace_scenario, escape_competition = get_race_pace_scenario(race_data)

    # この馬の脚質を判定
    passage = horse_data.get('Passage')
    positions = parse_passage_full(passage)
    horse_style = classify_running_style(positions[0])

    # ペース適性スコア
    pace_advantage = 0
    if pace_scenario == 'high_pace':
        if horse_style in ['closing', 'pursuing']:
            pace_advantage = 1
        elif horse_style in ['escape', 'leading']:
            pace_advantage = -1
    elif pace_scenario == 'slow_pace':
        if horse_style in ['escape', 'leading']:
            pace_advantage = 1
        elif horse_style in ['closing', 'pursuing']:
            pace_advantage = -1

    # 42次元特徴ベクトル
    feature_vector = [
        # 基本成績（6次元）
        avg_rank, std_rank, min_rank, max_rank,
        recent_win_rate, recent_top3_rate,

        # 人的要因（6次元）
        jockey_win_rate, jockey_top3_rate, jockey_races_count,
        trainer_win_rate, trainer_top3_rate, trainer_races_count,

        # 馬体情報（5次元）
        age, weight_diff, weight, np.log1p(odds), ninki,

        # レース条件（4次元）
        waku, course_turf, course_dirt, track_good,

        # 距離（1次元）
        distance / 1000,

        # 脚質特徴（8次元）
        style_features['escape_rate'],
        style_features['leading_rate'],
        style_features['closing_rate'],
        style_features['pursuing_rate'],
        style_features['avg_agari'],
        style_features['has_past_results'],
        style_features['position_change_ability'],
        style_features['agari_stability'],

        # コース適性（6次元）
        track_avg_rank if track_avg_rank > 0 else 8,
        track_races,
        distance_avg_rank if distance_avg_rank > 0 else 8,
        distance_races,
        turn_avg_rank if turn_avg_rank > 0 else 8,
        turn_races,

        # 展開予想（4次元）
        1 if pace_scenario == 'high_pace' else 0,
        1 if pace_scenario == 'slow_pace' else 0,
        pace_advantage,
        escape_competition,

        # 回り方向（2次元）
        1 if turn_direction == 'left' else 0,
        1 if turn_direction == 'right' else 0
    ]

    return feature_vector

print("=" * 80)
print("次世代統合モデル（42次元）のバックテスト")
print("=" * 80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)

print(f"総データ数: {len(df):,}件")

# テストデータ: 2024年
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
test_df = df[(df['date_parsed'] >= '2024-01-01') & (df['date_parsed'] <= '2024-12-31')].copy()

print(f"テストデータ（2024年）: {len(test_df):,}件")

# モデル読み込み
print("\nモデル読み込み中...")
with open('lightgbm_model_advanced.pkl', 'rb') as f:
    model_data = pickle.load(f)
    model = model_data['model']  # 辞書から実際のモデルを取得

print("モデル読み込み完了")

# レース単位で予測
print("\n予測実行中...")
race_ids = test_df['race_id'].unique()
print(f"テスト対象レース数: {len(race_ids)}レース")

results = []

for i, race_id in enumerate(race_ids):
    if (i + 1) % 500 == 0:
        print(f"  進捗: {i+1}/{len(race_ids)} レース処理完了")

    race_data = test_df[test_df['race_id'] == race_id]

    horses = []
    for _, horse in race_data.iterrows():
        umaban = horse['Umaban']
        features = extract_features_advanced(df, race_id, umaban)

        if features is not None:
            horses.append({
                'umaban': umaban,
                'features': features,
                'actual_rank': pd.to_numeric(horse.get('Rank'), errors='coerce')
            })

    if len(horses) == 0:
        continue

    # 予測
    X = np.array([h['features'] for h in horses])
    predictions = model.predict(X)

    for j, horse in enumerate(horses):
        horse['predicted_rank'] = predictions[j]

    # 予測着順でソート
    horses_sorted = sorted(horses, key=lambda x: x['predicted_rank'])

    # 実際の着順を取得
    actual_results = {}
    for horse in horses:
        if pd.notna(horse['actual_rank']):
            actual_results[int(horse['actual_rank'])] = horse['umaban']

    if len(actual_results) < 3:
        continue

    result = {
        'race_id': race_id,
        'predicted_1st': horses_sorted[0]['umaban'] if len(horses_sorted) > 0 else None,
        'predicted_2nd': horses_sorted[1]['umaban'] if len(horses_sorted) > 1 else None,
        'predicted_3rd': horses_sorted[2]['umaban'] if len(horses_sorted) > 2 else None,
        'actual_1st': actual_results.get(1),
        'actual_2nd': actual_results.get(2),
        'actual_3rd': actual_results.get(3)
    }

    results.append(result)

print(f"\n予測完了: {len(results)}レース")

# 的中率の計算
print("\n" + "=" * 80)
print("【予測精度】")
print("=" * 80)

hit_1st = sum(1 for r in results if r['predicted_1st'] == r['actual_1st'])
hit_2nd = sum(1 for r in results if r['predicted_2nd'] == r['actual_2nd'])
hit_3rd = sum(1 for r in results if r['predicted_3rd'] == r['actual_3rd'])

# 3連複: 順不同で一致
hit_trio = sum(1 for r in results if set([r['predicted_1st'], r['predicted_2nd'], r['predicted_3rd']]) ==
               set([r['actual_1st'], r['actual_2nd'], r['actual_3rd']]))

# 3連単: 順番通り
hit_trifecta = sum(1 for r in results if
                   r['predicted_1st'] == r['actual_1st'] and
                   r['predicted_2nd'] == r['actual_2nd'] and
                   r['predicted_3rd'] == r['actual_3rd'])

total_races = len(results)

print(f"\n総レース数: {total_races}レース")
print(f"\n1位的中率: {hit_1st / total_races * 100:.1f}%")
print(f"2位的中率: {hit_2nd / total_races * 100:.1f}%")
print(f"3位的中率: {hit_3rd / total_races * 100:.1f}%")
print(f"\n3連複（順不同）的中率: {hit_trio / total_races * 100:.1f}%")
print(f"3連単（順番通り）的中率: {hit_trifecta / total_races * 100:.1f}%")

# 回収率の計算（簡易版）
print("\n" + "=" * 80)
print("【回収率シミュレーション】")
print("=" * 80)
print("\n各レース100円ずつ購入と仮定")

strategies = {
    'ワイド_1-2': {'cost': 100, 'return': 0, 'hits': 0},
    'ワイド_1軸流し': {'cost': 0, 'return': 0, 'hits': 0},
    'ワイド_BOX3頭': {'cost': 300, 'return': 0, 'hits': 0}
}

for result in results:
    race_id = result['race_id']
    race_data = test_df[test_df['race_id'] == race_id]

    pred_1st = result['predicted_1st']
    pred_2nd = result['predicted_2nd']
    pred_3rd = result['predicted_3rd']

    actual_1st = result['actual_1st']
    actual_2nd = result['actual_2nd']
    actual_3rd = result['actual_3rd']

    # ワイド払戻を取得（簡易計算）
    # 実際のデータには払戻情報がないため、オッズから推定
    payouts = []

    for combo in [(actual_1st, actual_2nd), (actual_1st, actual_3rd), (actual_2nd, actual_3rd)]:
        horse1_data = race_data[race_data['Umaban'] == combo[0]]
        horse2_data = race_data[race_data['Umaban'] == combo[1]]

        if len(horse1_data) > 0 and len(horse2_data) > 0:
            odds1 = pd.to_numeric(horse1_data.iloc[0].get('Odds_x'), errors='coerce')
            odds2 = pd.to_numeric(horse2_data.iloc[0].get('Odds_x'), errors='coerce')

            if pd.notna(odds1) and pd.notna(odds2):
                wide_payout = int((odds1 + odds2) / 2 * 100 * 0.8)
                payouts.append(wide_payout)
            else:
                payouts.append(None)
        else:
            payouts.append(None)

    # 戦略1: ワイド1-2
    if set([pred_1st, pred_2nd]) <= set([actual_1st, actual_2nd, actual_3rd]):
        if len(payouts) > 0 and payouts[0]:
            strategies['ワイド_1-2']['return'] += payouts[0]
            strategies['ワイド_1-2']['hits'] += 1

    # 戦略2: ワイド1軸流し（1着予想を軸に、2,3着予想と組み合わせ）2点
    strategies['ワイド_1軸流し']['cost'] += 200
    hit_count = 0

    if set([pred_1st, pred_2nd]) <= set([actual_1st, actual_2nd, actual_3rd]):
        if payouts[0]:
            strategies['ワイド_1軸流し']['return'] += payouts[0]
            hit_count += 1

    if set([pred_1st, pred_3rd]) <= set([actual_1st, actual_2nd, actual_3rd]):
        if payouts[1]:
            strategies['ワイド_1軸流し']['return'] += payouts[1]
            hit_count += 1

    if hit_count > 0:
        strategies['ワイド_1軸流し']['hits'] += 1

    # 戦略3: ワイドBOX3頭（3点）
    hit_count = 0

    for i, combo in enumerate([(pred_1st, pred_2nd), (pred_1st, pred_3rd), (pred_2nd, pred_3rd)]):
        if set(combo) <= set([actual_1st, actual_2nd, actual_3rd]):
            if payouts[i]:
                strategies['ワイド_BOX3頭']['return'] += payouts[i]
                hit_count += 1

    if hit_count > 0:
        strategies['ワイド_BOX3頭']['hits'] += 1

print()
for name, stats in strategies.items():
    total_cost = stats['cost'] * total_races
    total_return = stats['return']
    recovery_rate = (total_return / total_cost * 100) if total_cost > 0 else 0
    profit = total_return - total_cost

    print(f"{name}:")
    print(f"  投資額: {total_cost:,}円")
    print(f"  払戻額: {total_return:,}円")
    print(f"  損益: {profit:+,}円")
    print(f"  回収率: {recovery_rate:.1f}%")
    print(f"  的中回数: {stats['hits']}回 ({stats['hits']/total_races*100:.1f}%)")
    print()

print("=" * 80)
print("バックテスト完了")
print("=" * 80)
