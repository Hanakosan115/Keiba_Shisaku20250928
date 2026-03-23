"""
WIN5 バックテストシミュレーション
2025年の日曜レースで、モデル予測によるWIN5的中をシミュレーション

WIN5 = 対象5レースすべての1着馬を当てる
対象レース: 日曜日の発走時刻が遅い最終5レース（JRA公式と同等の近似）

戦略:
  A) 各レース1頭（モデル最上位） → 1点買い
  B) 各レース2頭ボックス → 最大32点
  C) 各レース3頭ボックス → 最大243点
  D) 確信度ベース: 高確信レースは1頭、低確信は2-3頭
"""

import pandas as pd
import numpy as np
import pickle
import warnings
import sys
from itertools import product

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None
sys.path.append('scripts')

from feature_engineering_v2 import parse_diff_to_seconds, parse_passage, extract_race_class
from feature_engineering_v3 import PacePredictor, CourseBiasAnalyzer, FormCycleAnalyzer
from feature_engineering_v4 import (
    TrackBiasAnalyzer, WeatherImpactAnalyzer,
    EnhancedPacePredictor, DistanceAptitudeAnalyzer
)
warnings.filterwarnings('ignore')

from backtest_phase2_phase3_dynamic import (
    calculate_sire_stats,
    calculate_trainer_jockey_stats,
    calculate_horse_features_dynamic
)
from backtest_phase12 import add_phase10_features, add_v3_features, add_v4_features

print("=" * 70)
print("  WIN5 バックテストシミュレーション（2025年）")
print("=" * 70)


def load_models():
    print("\nLoading models...", flush=True)
    with open('model_phase12_win.pkl', 'rb') as f:
        model_win = pickle.load(f)
    with open('model_phase12_top3.pkl', 'rb') as f:
        model_top3 = pickle.load(f)
    with open('model_phase12_features.txt', 'r', encoding='utf-8') as f:
        feature_names = [line.strip() for line in f.readlines()]
    print(f"  Features: {len(feature_names)}", flush=True)
    return model_win, model_top3, feature_names


def load_data():
    print("\nLoading data...", flush=True)
    df = pd.read_csv('data/main/netkeiba_data_2020_2025_complete.csv',
                      low_memory=False, encoding='utf-8')
    print(f"  Records: {len(df):,}", flush=True)

    rank_col = '着順' if '着順' in df.columns else 'Rank'
    df['rank'] = pd.to_numeric(df[rank_col], errors='coerce')
    df = df[df['rank'].notna()]

    odds_col = '単勝' if '単勝' in df.columns else 'Odds'
    df['win_odds'] = pd.to_numeric(df[odds_col], errors='coerce')

    pop_col = '人気' if '人気' in df.columns else 'Pop'
    df['popularity'] = pd.to_numeric(df[pop_col], errors='coerce')

    umaban_col = '馬番' if '馬番' in df.columns else 'Umaban'
    df['umaban'] = pd.to_numeric(df[umaban_col], errors='coerce')

    def parse_date(date_str):
        try:
            if pd.isna(date_str):
                return None
            date_str = str(date_str)
            # 日本語形式 + ISO形式の混在対応
            import re as _re
            m = _re.search(r'(\d{4})\D+(\d{1,2})\D+(\d{1,2})', date_str)
            if m:
                return pd.Timestamp(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            return pd.to_datetime(date_str)
        except:
            return None

    df['date'] = df['date'].apply(parse_date)
    df = df[df['date'].notna()]
    print(f"  After cleaning: {len(df):,}", flush=True)
    return df


def get_win5_races(sunday_df):
    """
    日曜のWIN5対象レースを取得

    WIN5ルール:
    - 当日の最も発走時刻が遅い11Rを最終レグ(5レグ目)とする
    - それより前に発走する4レースを加えた計5レースが対象
    - 発走時刻順に並べて返す
    """
    race_info = sunday_df.groupby('race_id').first()[['start_time', 'track_name', 'race_num']].copy()

    # race_idからレース番号を取得（race_numがNaNの場合のフォールバック）
    race_info['race_num_int'] = pd.to_numeric(race_info['race_num'], errors='coerce')
    mask_na = race_info['race_num_int'].isna()
    if mask_na.any():
        race_info.loc[mask_na, 'race_num_int'] = race_info.index[mask_na].astype(str).str[-2:].astype(int)

    # start_timeを分単位の数値に変換（ソート用）
    def time_to_minutes(t):
        if pd.isna(t):
            return None
        try:
            parts = str(t).split(':')
            return int(parts[0]) * 60 + int(parts[1])
        except:
            return None

    race_info['time_min'] = race_info['start_time'].apply(time_to_minutes)

    # start_timeがない場合はrace_num_intで代替（10R=900, 11R=960 など仮想値）
    mask_no_time = race_info['time_min'].isna()
    if mask_no_time.any():
        race_info.loc[mask_no_time, 'time_min'] = race_info.loc[mask_no_time, 'race_num_int'] * 60 + 300

    # 最も遅い11Rを探す（5レグ目）
    races_11r = race_info[race_info['race_num_int'] == 11]
    if len(races_11r) == 0:
        return []

    leg5_id = races_11r['time_min'].idxmax()  # 最遅の11R
    leg5_time = races_11r.loc[leg5_id, 'time_min']

    # Leg5より前の全レースを時刻順にソートし、直前4レースを選ぶ
    before_leg5 = race_info[race_info['time_min'] < leg5_time].sort_values('time_min')
    if len(before_leg5) < 4:
        return []

    legs_1_to_4 = before_leg5.tail(4)
    win5_race_ids = legs_1_to_4.index.tolist() + [leg5_id]
    return win5_race_ids


def predict_race(race_df, train_df, horse_groups, model_win, model_top3,
                 feature_names, sire_stats, trainer_jockey_stats,
                 pace_predictor, bias_analyzer, form_analyzer,
                 track_bias_analyzer, weather_analyzer,
                 enhanced_pace_predictor, distance_analyzer):
    """1レースの予測を実行、馬ごとの予測確率を返す"""
    race_date = race_df.iloc[0]['date']
    race_info = {
        'race_name': race_df.iloc[0].get('race_name', ''),
        'track_name': race_df.iloc[0].get('track_name', ''),
        'distance': race_df.iloc[0].get('distance', 1600),
        'course_type': race_df.iloc[0].get('course_type', ''),
        'track_condition': race_df.iloc[0].get('track_condition', '良'),
        'weather': race_df.iloc[0].get('weather', '晴'),
    }
    race_id = race_df.iloc[0]['race_id']
    race_horses_ids = race_df['horse_id'].dropna().tolist()

    race_horses = []
    for _, r in race_df.iterrows():
        waku_col = '枠番' if '枠番' in r.index else 'Waku'
        race_horses.append({
            'horse_id': r.get('horse_id'),
            'name': r.get('HorseName', r.get('馬名', '')),
            'waku': r.get(waku_col, 4)
        })

    predictions = []
    for _, row in race_df.iterrows():
        horse_id = row.get('horse_id')
        if pd.isna(horse_id):
            continue

        course_type = race_info.get('course_type', '')
        if pd.isna(course_type) or course_type is None:
            course_type = ''
        course_type = str(course_type)

        frame = None
        for col in ['枠番', 'Waku', 'waku']:
            if col in row.index and pd.notna(row.get(col)):
                frame = row.get(col)
                break
        race_info['waku'] = frame

        trainer = None
        for col in ['調教師', 'TrainerName']:
            if col in row.index and pd.notna(row.get(col)):
                trainer = row.get(col)
                break

        jockey = None
        for col in ['騎手', 'JockeyName']:
            if col in row.index and pd.notna(row.get(col)):
                jockey = row.get(col)
                break

        # 事前グループから馬の過去レースを取得
        horse_df = horse_groups.get(horse_id)
        if horse_df is not None:
            horse_races = horse_df[horse_df['date'] < race_date]
        else:
            horse_races = train_df.iloc[0:0]

        try:
            features = calculate_horse_features_dynamic(
                horse_id=horse_id, df_history=train_df,
                race_date=race_date, sire_stats_dict=sire_stats,
                trainer_jockey_stats=trainer_jockey_stats,
                trainer_name=trainer, jockey_name=jockey,
                race_track=race_info['track_name'],
                race_distance=race_info['distance'],
                race_course_type=course_type,
                race_track_condition=race_info['track_condition'],
                current_frame=frame, race_id=race_id,
                horse_races_prefiltered=horse_races
            )
        except:
            continue

        if features is None:
            continue

        features = add_phase10_features(features, horse_races, race_info)
        features = add_v3_features(
            features, horse_id, race_horses_ids, race_info,
            pace_predictor, bias_analyzer, form_analyzer
        )
        horse_data = {
            'horse_id': horse_id,
            'father': row.get('father', ''),
            'mother_father': row.get('mother_father', ''),
            'waku': frame
        }
        features = add_v4_features(
            features, horse_data, race_info, race_horses,
            track_bias_analyzer, weather_analyzer,
            enhanced_pace_predictor, distance_analyzer
        )

        X = pd.DataFrame([features])[feature_names].fillna(0)
        win_proba = model_win.predict_proba(X)[0, 1]
        top3_proba = model_top3.predict_proba(X)[0, 1]

        predictions.append({
            'horse_id': horse_id,
            'horse_name': row.get('馬名', row.get('HorseName', '')),
            'umaban': row.get('umaban', 0),
            'rank': row['rank'],
            'win_odds': row['win_odds'] if pd.notna(row['win_odds']) else 0,
            'popularity': row.get('popularity', 0),
            'win_proba': win_proba,
            'top3_proba': top3_proba,
        })

    if not predictions:
        return None

    pred_df = pd.DataFrame(predictions).sort_values('win_proba', ascending=False)
    return pred_df


def run_win5_backtest(df, model_win, model_top3, feature_names):
    print("\nPreparing WIN5 backtest...", flush=True)

    df['year'] = df['date'].dt.year
    train_df = df[df['year'] < 2025].copy()
    test_df = df[df['year'] == 2025].copy()

    print(f"  Train: {len(train_df):,}", flush=True)
    print(f"  Test (2025): {len(test_df):,}", flush=True)

    # 分析器初期化
    print("  Initializing analyzers...", flush=True)
    sire_stats = calculate_sire_stats(train_df)
    trainer_jockey_stats = calculate_trainer_jockey_stats(train_df)
    pace_predictor = PacePredictor(train_df)
    bias_analyzer = CourseBiasAnalyzer(train_df)
    form_analyzer = FormCycleAnalyzer(train_df)
    track_bias_analyzer = TrackBiasAnalyzer(train_df)
    weather_analyzer = WeatherImpactAnalyzer(train_df)
    enhanced_pace_predictor = EnhancedPacePredictor(train_df)
    distance_analyzer = DistanceAptitudeAnalyzer(train_df)

    # 事前グループ化
    print("  Pre-grouping horse data...", flush=True)
    train_df['date'] = pd.to_datetime(train_df['date'], errors='coerce')
    horse_groups = dict(list(train_df.groupby('horse_id')))
    print(f"  Horse groups: {len(horse_groups):,}", flush=True)

    # 日曜日のみ抽出
    test_df['dayofweek'] = test_df['date'].dt.dayofweek
    sunday_df = test_df[test_df['dayofweek'] == 6].copy()
    sunday_dates = sorted(sunday_df['date'].unique())
    print(f"\n  Sunday dates in 2025: {len(sunday_dates)}", flush=True)

    # 各日曜のWIN5シミュレーション
    print("\nRunning WIN5 simulation...", flush=True)
    weekly_results = []

    for date_val in sunday_dates:
        date_str = pd.Timestamp(date_val).strftime('%Y-%m-%d')
        day_df = sunday_df[sunday_df['date'] == date_val]

        # WIN5対象の5レースを取得
        win5_race_ids = get_win5_races(day_df)
        if len(win5_race_ids) < 5:
            continue

        leg_results = []
        for leg_idx, race_id in enumerate(win5_race_ids):
            race_df = day_df[day_df['race_id'] == race_id]
            if len(race_df) < 5:
                leg_results.append(None)
                continue

            pred_df = predict_race(
                race_df, train_df, horse_groups,
                model_win, model_top3, feature_names,
                sire_stats, trainer_jockey_stats,
                pace_predictor, bias_analyzer, form_analyzer,
                track_bias_analyzer, weather_analyzer,
                enhanced_pace_predictor, distance_analyzer
            )
            if pred_df is None:
                leg_results.append(None)
                continue

            # 実際の勝ち馬
            winner = pred_df[pred_df['rank'] == 1]
            winner_name = str(winner.iloc[0]['horse_name'] or '?') if len(winner) > 0 else '?'
            winner_pop_val = winner.iloc[0]['popularity'] if len(winner) > 0 else 0
            winner_pop = int(winner_pop_val) if pd.notna(winner_pop_val) else 0
            winner_odds_val = winner.iloc[0]['win_odds'] if len(winner) > 0 else 0
            winner_odds = float(winner_odds_val) if pd.notna(winner_odds_val) else 0

            # モデル予測の上位馬
            top1 = pred_df.iloc[0]
            top1_won = (top1['rank'] == 1)
            top2_won = any(pred_df.head(2)['rank'] == 1)
            top3_won = any(pred_df.head(3)['rank'] == 1)
            top5_won = any(pred_df.head(5)['rank'] == 1)

            # 確信度に基づく選択数
            top1_proba = top1['win_proba']
            if top1_proba >= 0.40:
                confidence_n = 1  # 高確信 → 1頭
            elif top1_proba >= 0.25:
                confidence_n = 2  # 中確信 → 2頭
            else:
                confidence_n = 3  # 低確信 → 3頭
            confidence_won = any(pred_df.head(confidence_n)['rank'] == 1)

            race_name = str(race_df.iloc[0].get('race_name', '') or '')
            track_name = str(race_df.iloc[0].get('track_name', '') or '')

            leg_results.append({
                'race_id': race_id,
                'race_name': race_name,
                'track_name': track_name,
                'winner_name': winner_name,
                'winner_pop': winner_pop,
                'winner_odds': winner_odds,
                'top1_name': top1['horse_name'],
                'top1_proba': top1_proba,
                'top1_won': top1_won,
                'top2_won': top2_won,
                'top3_won': top3_won,
                'top5_won': top5_won,
                'confidence_n': confidence_n,
                'confidence_won': confidence_won,
                'num_horses': len(pred_df),
            })

        # 有効なレグが5つ揃わなければスキップ
        valid_legs = [l for l in leg_results if l is not None]
        if len(valid_legs) < 5:
            continue

        legs = valid_legs[:5]

        # 各戦略での的中判定
        all_top1 = all(l['top1_won'] for l in legs)
        all_top2 = all(l['top2_won'] for l in legs)
        all_top3 = all(l['top3_won'] for l in legs)
        all_top5 = all(l['top5_won'] for l in legs)
        all_confidence = all(l['confidence_won'] for l in legs)

        # 確信度ベース戦略の点数計算
        confidence_points = 1
        for l in legs:
            confidence_points *= l['confidence_n']

        # 人気薄勝ちの数
        upset_count = sum(1 for l in legs if l['winner_pop'] >= 4)

        weekly_results.append({
            'date': date_str,
            'legs': legs,
            'all_top1': all_top1,
            'all_top2': all_top2,
            'all_top3': all_top3,
            'all_top5': all_top5,
            'all_confidence': all_confidence,
            'confidence_points': confidence_points,
            'upset_count': upset_count,
            'avg_winner_pop': np.mean([l['winner_pop'] for l in legs]),
        })

        # 進捗
        status = '★的中' if all_top1 else ('○2頭内' if all_top2 else '×')
        print(f"  {date_str}: {status}  "
              f"Top1={sum(l['top1_won'] for l in legs)}/5  "
              f"Top2={sum(l['top2_won'] for l in legs)}/5  "
              f"Top3={sum(l['top3_won'] for l in legs)}/5  "
              f"荒れ={upset_count}",
              flush=True)

    return weekly_results


def analyze_win5_results(results):
    print(f"\n{'='*70}")
    print("  WIN5 バックテスト結果サマリー（2025年）")
    print(f"{'='*70}")

    n_weeks = len(results)
    print(f"\n  対象週数: {n_weeks}週")

    # === 戦略A: 各レース1頭（1点買い） ===
    hit_a = sum(1 for r in results if r['all_top1'])
    cost_a = n_weeks * 100
    print(f"\n  【戦略A】各レース1頭＝1点買い（{cost_a:,}円/年）")
    print(f"    的中: {hit_a}/{n_weeks}週 ({hit_a/n_weeks*100:.1f}%)")

    # === 戦略B: 各レース2頭（最大32点） ===
    hit_b = sum(1 for r in results if r['all_top2'])
    cost_b = n_weeks * 32 * 100
    print(f"\n  【戦略B】各レース2頭＝最大32点（{cost_b:,}円/年）")
    print(f"    的中: {hit_b}/{n_weeks}週 ({hit_b/n_weeks*100:.1f}%)")

    # === 戦略C: 各レース3頭（最大243点） ===
    hit_c = sum(1 for r in results if r['all_top3'])
    cost_c = n_weeks * 243 * 100
    print(f"\n  【戦略C】各レース3頭＝最大243点（{cost_c:,}円/年）")
    print(f"    的中: {hit_c}/{n_weeks}週 ({hit_c/n_weeks*100:.1f}%)")

    # === 戦略D: 確信度ベース（可変点数） ===
    hit_d = sum(1 for r in results if r['all_confidence'])
    total_points_d = sum(r['confidence_points'] for r in results)
    cost_d = total_points_d * 100
    avg_points_d = total_points_d / n_weeks if n_weeks > 0 else 0
    print(f"\n  【戦略D】確信度ベース（高→1頭, 中→2頭, 低→3頭）")
    print(f"    平均点数: {avg_points_d:.1f}点/週  総投資: {cost_d:,}円")
    print(f"    的中: {hit_d}/{n_weeks}週 ({hit_d/n_weeks*100:.1f}%)")

    # === 戦略E: 各レース5頭（最大3125点、参考） ===
    hit_e = sum(1 for r in results if r['all_top5'])
    cost_e = n_weeks * 3125 * 100
    print(f"\n  【戦略E】各レース5頭＝最大3125点（参考）")
    print(f"    的中: {hit_e}/{n_weeks}週 ({hit_e/n_weeks*100:.1f}%)")

    # === レグ別的中率 ===
    print(f"\n  {'─'*60}")
    print(f"  レグ別の1着的中率")
    print(f"  {'─'*60}")

    for strategy, label, key in [
        ('Top1', '1頭目', 'top1_won'),
        ('Top2', '2頭以内', 'top2_won'),
        ('Top3', '3頭以内', 'top3_won'),
    ]:
        leg_hits = [0] * 5
        for r in results:
            for i, leg in enumerate(r['legs'][:5]):
                if leg[key]:
                    leg_hits[i] += 1
        rates = [h / n_weeks * 100 for h in leg_hits]
        overall = sum(sum(1 for l in r['legs'][:5] if l[key]) for r in results)
        total_legs = n_weeks * 5
        print(f"  {label}: Leg1={rates[0]:.0f}% Leg2={rates[1]:.0f}% Leg3={rates[2]:.0f}% "
              f"Leg4={rates[3]:.0f}% Leg5={rates[4]:.0f}%  全体={overall}/{total_legs} ({overall/total_legs*100:.1f}%)")

    # === 荒れ度と予測の関係 ===
    print(f"\n  {'─'*60}")
    print(f"  荒れ度別のTop1的中レグ数")
    print(f"  {'─'*60}")

    for upset_n in range(6):
        weeks = [r for r in results if r['upset_count'] == upset_n]
        if not weeks:
            continue
        avg_top1 = np.mean([sum(l['top1_won'] for l in r['legs'][:5]) for r in weeks])
        hit_top2 = sum(1 for r in weeks if r['all_top2'])
        print(f"  荒れ={upset_n}回: {len(weeks)}週  平均Top1的中={avg_top1:.1f}/5  "
              f"2頭以内全的中={hit_top2}/{len(weeks)}")

    # === 週ごとの詳細結果 ===
    print(f"\n  {'─'*60}")
    print(f"  週ごとの詳細")
    print(f"  {'─'*60}")

    for r in results:
        top1_hits = sum(l['top1_won'] for l in r['legs'][:5])
        top2_hits = sum(l['top2_won'] for l in r['legs'][:5])
        mark = '★' if r['all_top1'] else ('◎' if r['all_top2'] else ('○' if r['all_top3'] else '　'))
        print(f"\n  {mark} {r['date']}  Top1={top1_hits}/5  Top2={top2_hits}/5  荒={r['upset_count']}")

        for i, leg in enumerate(r['legs'][:5]):
            hit_mark = '●' if leg['top1_won'] else ('○' if leg['top2_won'] else '×')
            tn = str(leg['track_name'] or '')
            rn = str(leg['race_name'] or '')
            wn = str(leg['winner_name'] or '?')
            t1n = str(leg['top1_name'] or '?')
            print(f"    Leg{i+1} {hit_mark} {tn:<4s} {rn[:20]:<20s} "
                  f"勝馬:{wn[:6]:<6s}({leg['winner_pop']}人気) "
                  f"予測1位:{t1n[:6]:<6s}(P={leg['top1_proba']:.2f})")

    # === 惜しかった週（4/5的中） ===
    print(f"\n  {'─'*60}")
    print(f"  惜しかった週（Top1で4/5的中）")
    print(f"  {'─'*60}")

    close_calls = [r for r in results if sum(l['top1_won'] for l in r['legs'][:5]) == 4]
    if close_calls:
        for r in close_calls:
            miss_legs = [l for l in r['legs'][:5] if not l['top1_won']]
            miss = miss_legs[0]
            mtn = str(miss['track_name'] or '')
            mrn = str(miss['race_name'] or '')
            mwn = str(miss['winner_name'] or '?')
            print(f"  {r['date']}: 外れ={mtn} {mrn[:15]} "
                  f"勝馬={mwn}({miss['winner_pop']}人気)")
    else:
        print("  該当なし")


def main():
    model_win, model_top3, feature_names = load_models()
    df = load_data()
    results = run_win5_backtest(df, model_win, model_top3, feature_names)

    # レグデータを保存（再分析用）
    import pickle as _pkl
    with open('win5_leg_results.pkl', 'wb') as f:
        _pkl.dump(results, f)
    print("  Saved: win5_leg_results.pkl", flush=True)

    analyze_win5_results(results)

    print(f"\n{'='*70}")
    print("  WIN5 Backtest Complete!")
    print(f"{'='*70}")


if __name__ == '__main__':
    main()
