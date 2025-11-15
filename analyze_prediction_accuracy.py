"""
予測精度の詳細分析
- スコア上位馬の実際の着順分布
- 的中時と不的中時の配当分布
- 予測と実際の相関分析
"""
import pandas as pd
import json
import sys
from itertools import combinations
import numpy as np
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

def calculate_horse_score(horse_basic_info, race_conditions):
    """過去成績のみで馬のスコアを計算"""
    score = 50.0

    race_results = horse_basic_info.get('race_results', [])

    if not race_results or len(race_results) == 0:
        return 30.0

    # 直近3走の平均着順
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

        if len(recent_ranks) >= 2:
            std = np.std(recent_ranks)
            if std <= 1:
                score += 10
            elif std <= 2:
                score += 5
            elif std >= 5:
                score -= 5

    # 距離適性
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

    return score

print("=" * 80)
print("予測精度の詳細分析")
print("=" * 80)

# データ読み込み（2024年のみを分析対象とする）
print("\nデータ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年のデータに絞る
target_races = df[
    (df['date_parsed'] >= '2024-01-01') &
    (df['date_parsed'] <= '2024-12-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"分析対象: 2024年 {len(race_ids)}レース")

# 分析用データ収集
prediction_results = []

for idx, race_id in enumerate(race_ids):
    if (idx + 1) % 500 == 0:
        print(f"  {idx + 1}/{len(race_ids)} レース処理中...")

    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    # 馬番順にソート（データリーケージ防止）
    race_horses = race_horses.sort_values('Umaban')

    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue

    race_date_str = str(race_date)[:10]

    # 予測実行
    horses_scores = []

    for _, horse in race_horses.iterrows():
        horse_id = horse.get('horse_id')
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

        score = calculate_horse_score(horse_basic_info, race_conditions)

        horses_scores.append({
            'umaban': int(horse.get('Umaban', 0)),
            'score': score,
            'actual_rank': pd.to_numeric(horse.get('Rank'), errors='coerce'),
            'ninki': pd.to_numeric(horse.get('Ninki'), errors='coerce')
        })

    # スコア順にソート
    horses_scores.sort(key=lambda x: x['score'], reverse=True)

    # 予測順位を付与
    for rank, horse in enumerate(horses_scores, 1):
        horse['predicted_rank'] = rank

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    umaren_payout = None
    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        if umaren_data.get('払戻金'):
            umaren_payout = umaren_data['払戻金'][0]

    # TOP3予測
    top3_predicted = [h['umaban'] for h in horses_scores[:3]]

    # 実際のTOP3
    actual_top3_horses = sorted(horses_scores, key=lambda x: x['actual_rank'] if pd.notna(x['actual_rank']) else 999)[:3]
    actual_top3 = [h['umaban'] for h in actual_top3_horses]

    # 的中判定
    is_hit = False
    if umaren_payout and len(actual_top3) >= 2:
        winning_pair = set(actual_top3[:2])
        predicted_pairs = list(combinations(top3_predicted, 2))
        for pair in predicted_pairs:
            if set(pair) == winning_pair:
                is_hit = True
                break

    # 結果を記録
    for horse in horses_scores:
        prediction_results.append({
            'race_id': race_id,
            'umaban': horse['umaban'],
            'predicted_rank': horse['predicted_rank'],
            'actual_rank': horse['actual_rank'],
            'score': horse['score'],
            'ninki': horse['ninki'],
            'in_top3_predicted': horse['umaban'] in top3_predicted,
            'in_top3_actual': horse['umaban'] in actual_top3,
            'umaren_payout': umaren_payout,
            'is_hit': is_hit
        })

# DataFrameに変換
results_df = pd.DataFrame(prediction_results)

print("\n" + "=" * 80)
print("【1. 予測精度分析】")
print("=" * 80)

# 予測順位別の実際の成績
print("\n■ 予測順位別の平均着順")
for pred_rank in range(1, 6):
    subset = results_df[results_df['predicted_rank'] == pred_rank]
    if len(subset) > 0:
        avg_actual_rank = subset['actual_rank'].mean()
        win_rate = (subset['actual_rank'] == 1).sum() / len(subset) * 100
        top3_rate = (subset['actual_rank'] <= 3).sum() / len(subset) * 100
        print(f"予測{pred_rank}位: 平均着順{avg_actual_rank:.2f} | 勝率{win_rate:.1f}% | 複勝率{top3_rate:.1f}%")

# TOP3予測の精度
print("\n■ TOP3予測の精度")
top3_predicted_horses = results_df[results_df['in_top3_predicted'] == True]
top3_actual_in_predicted = top3_predicted_horses['in_top3_actual'].sum()
print(f"予測TOP3のうち実際にTOP3に入った: {top3_actual_in_predicted}/{len(top3_predicted_horses)} ({top3_actual_in_predicted/len(top3_predicted_horses)*100:.1f}%)")

# スコアと着順の相関
print("\n■ スコアと着順の相関")
correlation = results_df[['score', 'actual_rank']].corr().iloc[0, 1]
print(f"相関係数: {correlation:.3f}")
print(f"(負の相関が強いほど良い: スコアが高いほど着順が良い)")

print("\n" + "=" * 80)
print("【2. 配当分析】")
print("=" * 80)

# 的中レースのみ抽出
hit_races = results_df[results_df['is_hit'] == True].drop_duplicates('race_id')
miss_races = results_df[results_df['is_hit'] == False].drop_duplicates('race_id')

print(f"\n的中レース数: {len(hit_races)}")
print(f"不的中レース数: {len(miss_races)}")

if len(hit_races) > 0:
    print("\n■ 的中時の配当分布")
    hit_payouts = hit_races['umaren_payout'].dropna()
    print(f"平均配当: {hit_payouts.mean():.0f}円")
    print(f"中央値: {hit_payouts.median():.0f}円")
    print(f"最高配当: {hit_payouts.max():.0f}円")
    print(f"最低配当: {hit_payouts.min():.0f}円")

    print("\n配当レンジ別の的中数:")
    print(f"  ~500円: {(hit_payouts < 500).sum()}回")
    print(f"  500-1000円: {((hit_payouts >= 500) & (hit_payouts < 1000)).sum()}回")
    print(f"  1000-2000円: {((hit_payouts >= 1000) & (hit_payouts < 2000)).sum()}回")
    print(f"  2000-5000円: {((hit_payouts >= 2000) & (hit_payouts < 5000)).sum()}回")
    print(f"  5000円~: {(hit_payouts >= 5000).sum()}回")

# 不的中時の正解配当
print("\n■ 不的中時の正解馬連配当（逃した配当）")
if len(miss_races) > 0:
    miss_payouts = miss_races['umaren_payout'].dropna()
    print(f"平均配当: {miss_payouts.mean():.0f}円")
    print(f"中央値: {miss_payouts.median():.0f}円")

    print("\n逃した配当レンジ別:")
    print(f"  ~500円: {(miss_payouts < 500).sum()}回")
    print(f"  500-1000円: {((miss_payouts >= 500) & (miss_payouts < 1000)).sum()}回")
    print(f"  1000-2000円: {((miss_payouts >= 1000) & (miss_payouts < 2000)).sum()}回")
    print(f"  2000-5000円: {((miss_payouts >= 2000) & (miss_payouts < 5000)).sum()}回")
    print(f"  5000円~: {(miss_payouts >= 5000).sum()}回")

print("\n" + "=" * 80)
print("【3. 人気と予測の関係】")
print("=" * 80)

# 予測TOP3に入った馬の人気分布
top3_pred = results_df[results_df['in_top3_predicted'] == True]
print("\n■ 予測TOP3の平均人気")
print(f"平均人気: {top3_pred['ninki'].mean():.1f}番人気")

print("\n人気別の予測TOP3入り率:")
for ninki_range in [(1, 3), (4, 6), (7, 9), (10, 18)]:
    subset = results_df[(results_df['ninki'] >= ninki_range[0]) & (results_df['ninki'] <= ninki_range[1])]
    if len(subset) > 0:
        in_top3_rate = subset['in_top3_predicted'].sum() / len(subset) * 100
        print(f"{ninki_range[0]}-{ninki_range[1]}番人気: {in_top3_rate:.1f}%がTOP3予測に入る")

print("\n" + "=" * 80)
print("【4. スコア分布分析】")
print("=" * 80)

print("\n■ 全体のスコア分布")
print(f"平均スコア: {results_df['score'].mean():.1f}")
print(f"中央値: {results_df['score'].median():.1f}")
print(f"標準偏差: {results_df['score'].std():.1f}")
print(f"最高スコア: {results_df['score'].max():.1f}")
print(f"最低スコア: {results_df['score'].min():.1f}")

print("\n■ 着順別の平均スコア")
for rank in range(1, 6):
    subset = results_df[results_df['actual_rank'] == rank]
    if len(subset) > 0:
        avg_score = subset['score'].mean()
        print(f"{rank}着の平均スコア: {avg_score:.1f}")

print("\n" + "=" * 80)
print("【5. 問題点のまとめ】")
print("=" * 80)

# 問題点を自動検出
issues = []

# 予測1位の勝率をチェック
pred1_subset = results_df[results_df['predicted_rank'] == 1]
if len(pred1_subset) > 0:
    pred1_win_rate = (pred1_subset['actual_rank'] == 1).sum() / len(pred1_subset) * 100
    if pred1_win_rate < 15:
        issues.append(f"⚠ 予測1位の勝率が低い ({pred1_win_rate:.1f}%) → スコアリング精度に問題")

# 配当の偏りをチェック
if len(hit_payouts) > 0:
    low_payout_rate = (hit_payouts < 500).sum() / len(hit_payouts) * 100
    if low_payout_rate > 50:
        issues.append(f"⚠ 的中の{low_payout_rate:.0f}%が低配当（500円未満） → 本命偏重")

# 人気馬への偏りをチェック
top3_avg_ninki = top3_pred['ninki'].mean()
if top3_avg_ninki < 5:
    issues.append(f"⚠ 予測TOP3の平均人気が{top3_avg_ninki:.1f}番人気 → 人気馬に偏りすぎ")

# スコア差をチェック
score_std = results_df['score'].std()
if score_std < 10:
    issues.append(f"⚠ スコアの標準偏差が{score_std:.1f}と小さい → 馬の区別がついていない")

if issues:
    print("\n検出された問題点:")
    for issue in issues:
        print(issue)
else:
    print("\n重大な問題は検出されませんでした。")

print("\n" + "=" * 80)
print("分析完了")
print("=" * 80)
