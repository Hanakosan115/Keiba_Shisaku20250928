"""
アンサンブルモデル - 脚質モデル + 3連単モデル
複数の重み付けを試して最適な組み合わせを見つける
"""
import pandas as pd
import json
import sys
import numpy as np
from itertools import combinations
import pickle
from data_config import MAIN_CSV, MAIN_JSON
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

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

def get_running_style_features(df, horse_id, race_date_str, max_results=10):
    """脚質特徴量を計算（脚質モデル用）"""
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
        positions = parse_passage_full(passage)
        early_pos = positions[0]
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

def calculate_trifecta_features(df, horse_id, race_date_str, max_results=10):
    """3連単特化特徴量を計算"""
    race_date_parsed = pd.to_datetime(race_date_str)
    horse_races = df[df['horse_id'] == horse_id].copy()
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')
    past_races = horse_races[horse_races['date_parsed'] < race_date_parsed]
    past_races = past_races.sort_values('date_parsed', ascending=False).head(max_results)

    if len(past_races) == 0:
        return {
            'avg_rank': 8, 'std_rank': 0, 'race_count': 0, 'win_rate': 0, 'top3_rate': 0,
            'escape_rate': 0, 'leading_rate': 0, 'closing_rate': 0, 'pursuing_rate': 0, 'avg_agari': 0,
            'closing_success_rate': 0, 'position_stability': 0, 'close_finish_rate': 0,
            'second_place_rate': 0, 'third_place_rate': 0, 'front_collapse_rate': 0, 'late_charge_rate': 0,
        }

    ranks = pd.to_numeric(past_races['Rank'], errors='coerce').dropna()
    features = {
        'avg_rank': ranks.mean() if len(ranks) > 0 else 8,
        'std_rank': ranks.std() if len(ranks) > 1 else 0,
        'race_count': len(ranks),
        'win_rate': (ranks == 1).sum() / len(ranks) if len(ranks) > 0 else 0,
        'top3_rate': (ranks <= 3).sum() / len(ranks) if len(ranks) > 0 else 0,
    }

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
        if early_pos is not None and late_pos is not None:
            position_changes.append(abs(late_pos - early_pos))
        if early_pos is not None and rank is not None:
            if early_pos > 8 and rank <= 3:
                closing_success += 1
            if style in ['closing', 'pursuing'] and rank <= 3:
                late_charges += 1
            if style in ['escape', 'leading'] and rank > 3:
                front_collapses += 1
        if rank == 2:
            second_places += 1
        elif rank == 3:
            third_places += 1

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
    features['escape_rate'] = styles['escape'] / total_races
    features['leading_rate'] = styles['leading'] / total_races
    features['closing_rate'] = styles['closing'] / total_races
    features['pursuing_rate'] = styles['pursuing'] / total_races
    features['avg_agari'] = np.mean(agari_times) if agari_times else 0
    features['closing_success_rate'] = closing_success / total_races
    features['position_stability'] = 1 / (1 + np.mean(position_changes)) if position_changes else 0
    features['close_finish_rate'] = close_finishes / total_races
    features['second_place_rate'] = second_places / total_races
    features['third_place_rate'] = third_places / total_races
    features['front_collapse_rate'] = front_collapses / max(styles['escape'] + styles['leading'], 1)
    features['late_charge_rate'] = late_charges / max(styles['closing'] + styles['pursuing'], 1)

    return features

def get_recent_ranks(df, horse_id, race_date_str, max_results=5):
    """過去成績から着順のみ取得"""
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
print("アンサンブルモデル：バックテスト")
print("脚質モデル(28次元) + 3連単モデル(31次元)")
print("=" * 80)

# モデル読み込み
print("\n脚質モデル読み込み中...")
with open('lightgbm_model_with_running_style.pkl', 'rb') as f:
    running_style_data = pickle.load(f)
    running_style_model = running_style_data['model']

print("3連単モデル読み込み中...")
with open('lightgbm_model_trifecta_optimized_fixed.pkl', 'rb') as f:
    trifecta_data = pickle.load(f)
    trifecta_model = trifecta_data['model']

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(MAIN_JSON)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年のデータ
target_races = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()
print(f"対象: 2024年 {len(race_ids)}レース")

# 複数の重み設定を試す
weight_configs = [
    (0.5, 0.5, "5:5"),
    (0.6, 0.4, "6:4(脚質重視)"),
    (0.4, 0.6, "4:6(3連単重視)"),
    (0.7, 0.3, "7:3(脚質重視)"),
    (0.3, 0.7, "3:7(3連単重視)"),
]

best_recovery = 0
best_config = None
all_results = []

for w_running, w_trifecta, config_name in weight_configs:
    print(f"\n{'-' * 80}")
    print(f"重み設定: {config_name} (脚質:{w_running:.1f} / 3連単:{w_trifecta:.1f})")
    print(f"{'-' * 80}")

    strategies = {
        'ワイド_1-2': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
        'ワイド_1軸流し': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
        'ワイド_BOX3頭': {'cost': 0, 'return': 0, 'hit': 0, 'total': 0},
    }

    accuracy_stats = {
        'first_correct': 0, 'second_correct': 0, 'third_correct': 0,
        'trio_hit': 0, 'trifecta_hit': 0, 'total': 0
    }

    stats_cache = {}

    for idx, race_id in enumerate(race_ids):
        if (idx + 1) % 1000 == 0:
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

        # 特徴量抽出（両方のモデル用）
        horse_features_running = []
        horse_features_trifecta = []
        horse_umabans = []
        actual_ranks = []

        for _, horse in race_horses.iterrows():
            horse_id = horse.get('horse_id')

            # 実際の着順
            actual_rank = pd.to_numeric(horse.get('Rank'), errors='coerce')
            if pd.isna(actual_rank):
                continue
            actual_ranks.append(int(actual_rank))

            # 基本情報
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

            # 騎手・調教師統計
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

            # 脚質モデル用特徴量（28次元）
            running_features = get_running_style_features(df, horse_id, race_date_str, max_results=10)
            feature_running = [
                avg_rank, std_rank, min_rank, max_rank,
                recent_win_rate, recent_top3_rate,
                jockey_win_rate, jockey_top3_rate, jockey_races,
                trainer_win_rate, trainer_top3_rate, trainer_races,
                age, weight_diff, weight, np.log1p(odds), ninki, waku,
                course_turf, course_dirt, track_good, distance / 1000,
                running_features['escape_rate'], running_features['leading_rate'],
                running_features['closing_rate'], running_features['pursuing_rate'],
                running_features['avg_agari'], running_features['has_past_results']
            ]

            # 3連単モデル用特徴量（31次元）
            trifecta_features = calculate_trifecta_features(df, horse_id, race_date_str, max_results=10)
            jockey = jockey_stats.get(jockey_name, {'win_rate': 0, 'top3_rate': 0})
            trainer = trainer_stats.get(trainer_name, {'win_rate': 0, 'top3_rate': 0})

            feature_trifecta = [
                trifecta_features['avg_rank'], trifecta_features['std_rank'], trifecta_features['race_count'],
                trifecta_features['win_rate'], trifecta_features['top3_rate'],
                jockey['win_rate'], jockey['top3_rate'],
                trainer['win_rate'], trainer['top3_rate'],
                age, weight_diff, weight, np.log1p(odds), ninki,
                waku, course_turf, course_dirt, track_good, distance / 1000,
                trifecta_features['escape_rate'], trifecta_features['leading_rate'],
                trifecta_features['closing_rate'], trifecta_features['pursuing_rate'],
                trifecta_features['avg_agari'],
                trifecta_features['closing_success_rate'], trifecta_features['position_stability'],
                trifecta_features['close_finish_rate'], trifecta_features['second_place_rate'],
                trifecta_features['third_place_rate'], trifecta_features['front_collapse_rate'],
                trifecta_features['late_charge_rate'],
            ]

            horse_features_running.append(feature_running)
            horse_features_trifecta.append(feature_trifecta)
            horse_umabans.append(int(horse.get('Umaban', 0)))

        if len(horse_features_running) < 8 or len(actual_ranks) != len(horse_features_running):
            continue

        # 両方のモデルで予測
        X_running = np.array(horse_features_running)
        X_trifecta = np.array(horse_features_trifecta)

        pred_running = running_style_model.predict(X_running)
        pred_trifecta = trifecta_model.predict(X_trifecta)

        # アンサンブル予測（重み付け平均）
        pred_ensemble = w_running * pred_running + w_trifecta * pred_trifecta

        # 予測スコアが低い順にソート
        predicted_ranking = sorted(
            zip(horse_umabans, pred_ensemble, actual_ranks),
            key=lambda x: x[1]
        )

        # 実際の着順でソート
        actual_ranking = sorted(
            zip(horse_umabans, actual_ranks),
            key=lambda x: x[1]
        )

        pred_1st = predicted_ranking[0][0]
        pred_2nd = predicted_ranking[1][0]
        pred_3rd = predicted_ranking[2][0]

        actual_1st = actual_ranking[0][0]
        actual_2nd = actual_ranking[1][0]
        actual_3rd = actual_ranking[2][0]

        # 的中判定
        trio_hit = set([pred_1st, pred_2nd, pred_3rd]) == set([actual_1st, actual_2nd, actual_3rd])
        trifecta_hit = (pred_1st == actual_1st and pred_2nd == actual_2nd and pred_3rd == actual_3rd)

        accuracy_stats['first_correct'] += (pred_1st == actual_1st)
        accuracy_stats['second_correct'] += (pred_2nd == actual_2nd)
        accuracy_stats['third_correct'] += (pred_3rd == actual_3rd)
        accuracy_stats['trio_hit'] += trio_hit
        accuracy_stats['trifecta_hit'] += trifecta_hit
        accuracy_stats['total'] += 1

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

        # ワイド 1-2
        strategies['ワイド_1-2']['total'] += 1
        strategies['ワイド_1-2']['cost'] += 100

        pred_pair = set([pred_1st, pred_2nd])
        for i in range(0, len(winning_pairs), 2):
            if i + 1 < len(winning_pairs):
                winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
                if pred_pair == winning_pair:
                    payout_amount = payouts[i // 2]
                    if payout_amount:
                        strategies['ワイド_1-2']['hit'] += 1
                        strategies['ワイド_1-2']['return'] += payout_amount
                    break

        # ワイド 1軸流し（1-2, 1-3）
        strategies['ワイド_1軸流し']['total'] += 1
        strategies['ワイド_1軸流し']['cost'] += 200

        for pred_pair in [(pred_1st, pred_2nd), (pred_1st, pred_3rd)]:
            pair_set = set(pred_pair)
            for i in range(0, len(winning_pairs), 2):
                if i + 1 < len(winning_pairs):
                    winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
                    if pair_set == winning_pair:
                        payout_amount = payouts[i // 2]
                        if payout_amount:
                            strategies['ワイド_1軸流し']['hit'] += 1
                            strategies['ワイド_1軸流し']['return'] += payout_amount
                        break

        # ワイド BOX3頭
        strategies['ワイド_BOX3頭']['total'] += 1
        strategies['ワイド_BOX3頭']['cost'] += 300

        for pred_pair in combinations([pred_1st, pred_2nd, pred_3rd], 2):
            pair_set = set(pred_pair)
            for i in range(0, len(winning_pairs), 2):
                if i + 1 < len(winning_pairs):
                    winning_pair = set([int(winning_pairs[i]), int(winning_pairs[i+1])])
                    if pair_set == winning_pair:
                        payout_amount = payouts[i // 2]
                        if payout_amount:
                            strategies['ワイド_BOX3頭']['hit'] += 1
                            strategies['ワイド_BOX3頭']['return'] += payout_amount
                        break

    # 結果表示
    total = accuracy_stats['total']
    print(f"\n総レース数: {total}レース")
    print(f"1位的中率: {accuracy_stats['first_correct'] / total * 100:.1f}%")
    print(f"3連複的中率: {accuracy_stats['trio_hit'] / total * 100:.1f}%")
    print(f"3連単的中率: {accuracy_stats['trifecta_hit'] / total * 100:.1f}%")

    wide_12_recovery = strategies['ワイド_1-2']['return'] / strategies['ワイド_1-2']['cost'] * 100 if strategies['ワイド_1-2']['cost'] > 0 else 0
    print(f"ワイド_1-2回収率: {wide_12_recovery:.1f}%")

    # 最優秀設定を記録
    if wide_12_recovery > best_recovery:
        best_recovery = wide_12_recovery
        best_config = (w_running, w_trifecta, config_name)

    all_results.append({
        'config': config_name,
        'w_running': w_running,
        'w_trifecta': w_trifecta,
        'recovery': wide_12_recovery,
        'first_acc': accuracy_stats['first_correct'] / total * 100,
        'trio_acc': accuracy_stats['trio_hit'] / total * 100,
        'trifecta_acc': accuracy_stats['trifecta_hit'] / total * 100,
    })

# 最終結果
print("\n" + "=" * 80)
print("【アンサンブル結果サマリー】")
print("=" * 80)

for result in all_results:
    print(f"\n{result['config']:20s} | ワイド回収率: {result['recovery']:6.1f}% | "
          f"1位: {result['first_acc']:4.1f}% | 3連複: {result['trio_acc']:4.1f}% | 3連単: {result['trifecta_acc']:4.1f}%")

print("\n" + "=" * 80)
print("【最優秀設定】")
print("=" * 80)
print(f"重み設定: {best_config[2]}")
print(f"脚質モデル: {best_config[0]:.1f} / 3連単モデル: {best_config[1]:.1f}")
print(f"ワイド_1-2回収率: {best_recovery:.1f}%")

print("\n" + "=" * 80)
print("【比較: 単独モデル】")
print("=" * 80)
print("脚質モデル単独:   173.7%")
print("3連単モデル単独:   159.6%")
print(f"アンサンブル最優秀: {best_recovery:.1f}%")

if best_recovery > 173.7:
    print("\n✅ アンサンブルが単独モデルを上回りました！")
else:
    print("\n⚠️ アンサンブルは単独モデルを下回りました")

print("\n" + "=" * 80)
print("バックテスト完了")
print("=" * 80)
