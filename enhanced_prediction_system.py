"""
改善版予測システム
追加特徴量: 騎手、馬体重、上がり3ハロン、天候適性など
"""
import pandas as pd
import json
import sys
import numpy as np
from itertools import combinations
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

def calculate_jockey_stats(jockey_name, race_date, df):
    """騎手の過去成績を計算"""
    if pd.isna(jockey_name):
        return {'win_rate': 0.0, 'top3_rate': 0.0, 'races': 0}

    # レース日より前のデータ
    jockey_races = df[
        (df['JockeyName'] == jockey_name) &
        (pd.to_datetime(df['date'], errors='coerce') < pd.to_datetime(race_date, errors='coerce'))
    ]

    total = len(jockey_races)
    if total == 0:
        return {'win_rate': 0.0, 'top3_rate': 0.0, 'races': 0}

    wins = (jockey_races['Rank'] == 1.0).sum()
    top3 = (jockey_races['Rank'] <= 3.0).sum()

    return {
        'win_rate': wins / total,
        'top3_rate': top3 / total,
        'races': total
    }

def calculate_enhanced_score(horse_basic_info, race_conditions, current_race_info, jockey_stats, df):
    """拡張版スコア計算"""
    score = 50.0

    race_results = horse_basic_info.get('race_results', [])

    if not race_results or len(race_results) == 0:
        return 30.0

    # === 1. 過去成績（基本） ===
    recent_ranks = []
    for race in race_results[:3]:
        if isinstance(race, dict):
            rank = pd.to_numeric(race.get('rank'), errors='coerce')
            if pd.notna(rank):
                recent_ranks.append(rank)

    if recent_ranks:
        avg_rank = sum(recent_ranks) / len(recent_ranks)
        if avg_rank <= 2:
            score += 30
        elif avg_rank <= 3:
            score += 20
        elif avg_rank <= 5:
            score += 10
        elif avg_rank <= 8:
            score += 5
        else:
            score -= 10

        # 成績安定性
        if len(recent_ranks) >= 2:
            std = np.std(recent_ranks)
            if std <= 1:
                score += 10
            elif std <= 2:
                score += 5
            elif std >= 5:
                score -= 5

    # === 2. 距離適性 ===
    current_distance = pd.to_numeric(race_conditions.get('Distance'), errors='coerce')
    if pd.notna(current_distance):
        distance_fit_score = 0
        distance_count = 0

        for race in race_results[:5]:
            if isinstance(race, dict):
                past_distance = pd.to_numeric(race.get('distance'), errors='coerce')
                past_rank = pd.to_numeric(race.get('rank'), errors='coerce')

                if pd.notna(past_distance) and pd.notna(past_rank):
                    distance_diff = abs(current_distance - past_distance)

                    if distance_diff <= 200:
                        if past_rank <= 3:
                            distance_fit_score += 15
                        elif past_rank <= 5:
                            distance_fit_score += 5
                        distance_count += 1

        if distance_count > 0:
            score += distance_fit_score / distance_count

    # === 3. 騎手能力（新規） ===
    if jockey_stats['races'] >= 20:  # 最低20レース以上の実績
        # 勝率による加点
        if jockey_stats['win_rate'] >= 0.15:  # 15%以上
            score += 15
        elif jockey_stats['win_rate'] >= 0.10:  # 10%以上
            score += 10
        elif jockey_stats['win_rate'] >= 0.05:  # 5%以上
            score += 5

        # 連対率による加点
        if jockey_stats['top3_rate'] >= 0.40:  # 40%以上
            score += 10
        elif jockey_stats['top3_rate'] >= 0.30:  # 30%以上
            score += 5

    # === 4. 馬体重（新規） ===
    current_weight = current_race_info.get('weight')
    weight_diff = current_race_info.get('weight_diff')

    if pd.notna(current_weight) and pd.notna(weight_diff):
        # 体重減少が大きいと減点
        if weight_diff <= -20:
            score -= 10
        elif weight_diff <= -10:
            score -= 5
        # 適度な増加は加点
        elif 0 < weight_diff <= 10:
            score += 5
        # 大幅増加は減点
        elif weight_diff > 20:
            score -= 5

    # === 5. 上がり3ハロン（末脚）評価（新規） ===
    agari_scores = []
    for race in race_results[:3]:
        if isinstance(race, dict):
            agari = race.get('agari')
            rank = pd.to_numeric(race.get('rank'), errors='coerce')
            if agari and pd.notna(rank):
                try:
                    agari_time = float(agari)
                    # 上がりが速い（34秒台以下）かつ好走していれば加点
                    if agari_time <= 34.0 and rank <= 3:
                        agari_scores.append(15)
                    elif agari_time <= 35.0 and rank <= 3:
                        agari_scores.append(10)
                    elif agari_time <= 36.0 and rank <= 5:
                        agari_scores.append(5)
                except:
                    pass

    if agari_scores:
        score += sum(agari_scores) / len(agari_scores)

    # === 6. 馬場適性（拡張） ===
    current_track_condition = race_conditions.get('TrackCondition')
    if current_track_condition:
        good_track_count = 0
        track_match_count = 0

        for race in race_results[:5]:
            if isinstance(race, dict):
                past_condition = race.get('track_condition')
                past_rank = pd.to_numeric(race.get('rank'), errors='coerce')

                if past_condition and pd.notna(past_rank):
                    if past_condition == current_track_condition:
                        track_match_count += 1
                        if past_rank <= 3:
                            good_track_count += 1

        if track_match_count > 0:
            match_rate = good_track_count / track_match_count
            if match_rate >= 0.6:
                score += 10
            elif match_rate >= 0.4:
                score += 5

    # === 7. 連続出走間隔 ===
    if len(race_results) >= 2:
        try:
            last_date = pd.to_datetime(race_results[0].get('date'), errors='coerce')
            second_last_date = pd.to_datetime(race_results[1].get('date'), errors='coerce')

            if pd.notna(last_date) and pd.notna(second_last_date):
                interval = (last_date - second_last_date).days

                # 中1週～中4週が理想
                if 14 <= interval <= 35:
                    score += 5
                # 連闘（中1週未満）は減点
                elif interval < 7:
                    score -= 10
                # 長期休養は減点
                elif interval > 90:
                    score -= 5
        except:
            pass

    return score

# データ読み込み
print("データ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

# 2025年6-8月を正しく抽出
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
target_races = df[
    (df['date_parsed'] >= '2025-06-01') &
    (df['date_parsed'] <= '2025-08-31')
]

print(f"\n対象期間: 2025年6月1日 ～ 2025年8月31日")

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()
print(f"8頭以上のレース: {len(race_ids)}レース\n")

# バックテスト実行
results = {
    '3box': {'total': 0, 'umaren_hit': 0, 'umaren_return': 0, 'umaren_cost': 0,
             'sanrenpuku_hit': 0, 'sanrenpuku_return': 0, 'sanrenpuku_cost': 0},
    '5box': {'total': 0, 'umaren_hit': 0, 'umaren_return': 0, 'umaren_cost': 0,
             'sanrenpuku_hit': 0, 'sanrenpuku_return': 0, 'sanrenpuku_cost': 0}
}

print("=" * 80)
print("拡張版バックテスト実行中...")
print("=" * 80)

for idx, race_id in enumerate(race_ids):
    if (idx + 1) % 100 == 0:
        print(f"処理中: {idx + 1}/{len(race_ids)} レース")

    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue

    race_date_str = str(race_date)[:10]

    # 予測実行
    horses_scores = []

    for _, horse in race_horses.iterrows():
        horse_id = horse.get('horse_id')
        jockey_name = horse.get('JockeyName')

        # 騎手成績を計算
        jockey_stats = calculate_jockey_stats(jockey_name, race_date_str, df)

        # 過去成績取得
        past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=5)

        horse_basic_info = {
            'HorseName': horse.get('HorseName'),
            'race_results': past_results
        }

        race_conditions = {
            'Distance': horse.get('distance'),
            'CourseType': horse.get('course_type'),
            'TrackCondition': horse.get('track_condition')
        }

        current_race_info = {
            'weight': horse.get('Weight'),
            'weight_diff': horse.get('WeightDiff'),
            'jockey': jockey_name
        }

        score = calculate_enhanced_score(horse_basic_info, race_conditions,
                                         current_race_info, jockey_stats, df)

        horses_scores.append({
            'umaban': int(horse.get('Umaban', 0)),
            'score': score
        })

    # スコア順にソート
    horses_scores.sort(key=lambda x: x['score'], reverse=True)

    top3 = [h['umaban'] for h in horses_scores[:3]]
    top5 = [h['umaban'] for h in horses_scores[:5]]

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data:
        continue

    # 3頭BOX評価
    results['3box']['total'] += 1

    # 馬連
    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_pairs = umaren_data.get('馬番', [])
        payouts = umaren_data.get('払戻金', [])

        if winning_pairs and len(winning_pairs) >= 2:
            try:
                winning_pair = set([int(x) for x in winning_pairs[:2]])
                umaren_pairs_3 = list(combinations(top3, 2))

                results['3box']['umaren_cost'] += len(umaren_pairs_3) * 100

                hit_found = False
                for pair in umaren_pairs_3:
                    if set(pair) == winning_pair:
                        hit_found = True
                        break

                if hit_found:
                    results['3box']['umaren_hit'] += 1
                    results['3box']['umaren_return'] += payouts[0]
            except:
                pass

    # 3連複
    if '3連複' in payout_data:
        sanrenpuku_data = payout_data['3連複']
        winning_trio = sanrenpuku_data.get('馬番', [])
        payouts = sanrenpuku_data.get('払戻金', [])

        if winning_trio and len(winning_trio) >= 3:
            try:
                winning_set = set([int(x) for x in winning_trio[:3]])

                results['3box']['sanrenpuku_cost'] += 100

                if winning_set == set(top3):
                    results['3box']['sanrenpuku_hit'] += 1
                    results['3box']['sanrenpuku_return'] += payouts[0]
            except:
                pass

    # 5頭BOX評価
    results['5box']['total'] += 1

    # 馬連
    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_pairs = umaren_data.get('馬番', [])
        payouts = umaren_data.get('払戻金', [])

        if winning_pairs and len(winning_pairs) >= 2:
            try:
                winning_pair = set([int(x) for x in winning_pairs[:2]])
                umaren_pairs_5 = list(combinations(top5, 2))

                results['5box']['umaren_cost'] += len(umaren_pairs_5) * 100

                hit_found = False
                for pair in umaren_pairs_5:
                    if set(pair) == winning_pair:
                        hit_found = True
                        break

                if hit_found:
                    results['5box']['umaren_hit'] += 1
                    results['5box']['umaren_return'] += payouts[0]
            except:
                pass

    # 3連複
    if '3連複' in payout_data:
        sanrenpuku_data = payout_data['3連複']
        winning_trio = sanrenpuku_data.get('馬番', [])
        payouts = sanrenpuku_data.get('払戻金', [])

        if winning_trio and len(winning_trio) >= 3:
            try:
                winning_set = set([int(x) for x in winning_trio[:3]])

                results['5box']['sanrenpuku_cost'] += len(list(combinations(top5, 3))) * 100

                if all(num in top5 for num in winning_set):
                    results['5box']['sanrenpuku_hit'] += 1
                    results['5box']['sanrenpuku_return'] += payouts[0]
            except:
                pass

print("\n" + "=" * 80)
print("【拡張版バックテスト結果】")
print("=" * 80)

print("\n■ 3頭BOX（◎○▲）")
print("-" * 80)
if results['3box']['total'] > 0:
    print(f"検証レース数: {results['3box']['total']}レース")

    if results['3box']['umaren_cost'] > 0:
        umaren_recovery = (results['3box']['umaren_return'] / results['3box']['umaren_cost']) * 100
        umaren_profit = results['3box']['umaren_return'] - results['3box']['umaren_cost']
        print(f"\n【馬連】")
        print(f"  的中: {results['3box']['umaren_hit']}回")
        print(f"  的中率: {results['3box']['umaren_hit']/results['3box']['total']*100:.1f}%")
        print(f"  投資額: {results['3box']['umaren_cost']:,}円")
        print(f"  払戻額: {results['3box']['umaren_return']:,}円")
        print(f"  回収率: {umaren_recovery:.1f}%")
        print(f"  損益: {umaren_profit:+,}円")

    if results['3box']['sanrenpuku_cost'] > 0:
        sanrenpuku_recovery = (results['3box']['sanrenpuku_return'] / results['3box']['sanrenpuku_cost']) * 100
        sanrenpuku_profit = results['3box']['sanrenpuku_return'] - results['3box']['sanrenpuku_cost']
        print(f"\n【3連複】")
        print(f"  的中: {results['3box']['sanrenpuku_hit']}回")
        print(f"  的中率: {results['3box']['sanrenpuku_hit']/results['3box']['total']*100:.1f}%")
        print(f"  投資額: {results['3box']['sanrenpuku_cost']:,}円")
        print(f"  払戻額: {results['3box']['sanrenpuku_return']:,}円")
        print(f"  回収率: {sanrenpuku_recovery:.1f}%")
        print(f"  損益: {sanrenpuku_profit:+,}円")

print("\n■ 5頭BOX（◎○▲△☆）")
print("-" * 80)
if results['5box']['total'] > 0:
    print(f"検証レース数: {results['5box']['total']}レース")

    if results['5box']['umaren_cost'] > 0:
        umaren_recovery = (results['5box']['umaren_return'] / results['5box']['umaren_cost']) * 100
        umaren_profit = results['5box']['umaren_return'] - results['5box']['umaren_cost']
        print(f"\n【馬連】")
        print(f"  的中: {results['5box']['umaren_hit']}回")
        print(f"  的中率: {results['5box']['umaren_hit']/results['5box']['total']*100:.1f}%")
        print(f"  投資額: {results['5box']['umaren_cost']:,}円")
        print(f"  払戻額: {results['5box']['umaren_return']:,}円")
        print(f"  回収率: {umaren_recovery:.1f}%")
        print(f"  損益: {umaren_profit:+,}円")

    if results['5box']['sanrenpuku_cost'] > 0:
        sanrenpuku_recovery = (results['5box']['sanrenpuku_return'] / results['5box']['sanrenpuku_cost']) * 100
        sanrenpuku_profit = results['5box']['sanrenpuku_return'] - results['5box']['sanrenpuku_cost']
        print(f"\n【3連複】")
        print(f"  的中: {results['5box']['sanrenpuku_hit']}回")
        print(f"  的中率: {results['5box']['sanrenpuku_hit']/results['5box']['total']*100:.1f}%")
        print(f"  投資額: {results['5box']['sanrenpuku_cost']:,}円")
        print(f"  払戻額: {results['5box']['sanrenpuku_return']:,}円")
        print(f"  回収率: {sanrenpuku_recovery:.1f}%")
        print(f"  損益: {sanrenpuku_profit:+,}円")

print("\n" + "=" * 80)
print("【改善点】")
print("=" * 80)
print("追加した特徴量:")
print("  1. 騎手の勝率・連対率")
print("  2. 馬体重の増減評価")
print("  3. 上がり3ハロン（末脚）の評価")
print("  4. 馬場適性の詳細分析")
print("  5. 出走間隔の評価")
print("=" * 80)
