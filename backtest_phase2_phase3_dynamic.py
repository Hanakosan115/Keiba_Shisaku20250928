"""
Phase 2 + Phase 3 + Phase 4 + Phase 5 動的特徴量計算バックテスト
predict_future_race.pyと同じロジックで特徴量を動的計算
全54特徴量（Phase 5A: 距離適性詳細 + Phase 5B: 相対上がり評価）
"""
import pandas as pd
import numpy as np
from sklearn.metrics import accuracy_score
import lightgbm as lgb
import warnings
import re
warnings.filterwarnings('ignore')

# カラム名ヘルパー（データソースによって異なる）
def get_rank_col(df):
    return 'Rank' if 'Rank' in df.columns else '着順'

def get_rank(df):
    rank_col = get_rank_col(df)
    return pd.to_numeric(df[rank_col], errors='coerce')

print("=" * 80)
print(" 大規模バックテスト: 全54特徴量 (2025年全データ)")
print(" Phase 5A: 距離適性詳細 + Phase 5B: 相対上がり評価")
print("=" * 80)
print()

# predict_future_race.pyの関数を再利用
def calculate_sire_stats(df_history):
    """種牡馬ごとの産駒成績を計算"""
    sire_stats = {}
    for sire_type in ['father', 'mother_father']:
        sire_data = df_history[df_history[sire_type].notna()].copy()
        sire_data['rank'] = get_rank(sire_data)
        sire_data_finished = sire_data[sire_data['rank'].notna()]
        grouped = sire_data_finished.groupby(sire_type)['rank']
        for sire_name, ranks in grouped:
            if sire_name not in sire_stats:
                sire_stats[sire_name] = {}
            total = len(ranks)
            wins = (ranks == 1).sum()
            top3 = (ranks <= 3).sum()
            sire_stats[sire_name][f'{sire_type}_win_rate'] = wins / total if total > 0 else 0.0
            sire_stats[sire_name][f'{sire_type}_top3_rate'] = top3 / total if total > 0 else 0.0
    return sire_stats

def calculate_trainer_jockey_stats(df_history):
    """調教師・騎手の成績を計算"""
    stats = {'trainer': {}, 'jockey': {}}

    # 着順を数値化
    df_calc = df_history.copy()
    df_calc['rank'] = get_rank(df_calc)
    df_finished = df_calc[df_calc['rank'].notna()]

    # 調教師統計
    if '調教師' in df_finished.columns:
        trainer_grouped = df_finished.groupby('調教師')['rank']
        for trainer_name, ranks in trainer_grouped:
            if pd.notna(trainer_name):
                total = len(ranks)
                wins = (ranks == 1).sum()
                top3 = (ranks <= 3).sum()
                stats['trainer'][trainer_name] = {
                    'win_rate': wins / total if total > 0 else 0.0,
                    'top3_rate': top3 / total if total > 0 else 0.0,
                    'starts': total
                }

    # 騎手統計
    if '騎手' in df_finished.columns:
        jockey_grouped = df_finished.groupby('騎手')['rank']
        for jockey_name, ranks in jockey_grouped:
            if pd.notna(jockey_name):
                total = len(ranks)
                wins = (ranks == 1).sum()
                top3 = (ranks <= 3).sum()
                stats['jockey'][jockey_name] = {
                    'win_rate': wins / total if total > 0 else 0.0,
                    'top3_rate': top3 / total if total > 0 else 0.0,
                    'starts': total
                }

    return stats

def calculate_horse_features_dynamic(horse_id, df_history, race_date, sire_stats_dict,
                                    trainer_jockey_stats, trainer_name=None, jockey_name=None,
                                    race_track=None, race_distance=None, race_course_type=None,
                                    race_track_condition=None, current_frame=None,
                                    race_id=None, horse_races_prefiltered=None):
    """馬の特徴量を動的計算（レース日時点の履歴のみ使用）"""
    try:
        horse_id_num = float(horse_id)
    except:
        return None

    if horse_races_prefiltered is not None:
        # 呼び出し元で既にhorse_id+日付フィルタ済みのデータを使用
        horse_races = horse_races_prefiltered.copy()
    else:
        # レース日より前のデータのみ（日付型を統一）
        race_date_dt = pd.to_datetime(race_date, errors='coerce')
        df_dates = pd.to_datetime(df_history['date'], errors='coerce')
        horse_races = df_history[
            (df_history['horse_id'] == horse_id_num) &
            (df_dates < race_date_dt)
        ].copy()

    features = {}

    # 基本統計
    if len(horse_races) > 0:
        latest = horse_races.sort_values('date', ascending=False).iloc[0]
        features['total_starts'] = latest.get('total_starts', 0)
        features['total_win_rate'] = latest.get('total_win_rate', 0.0)
        features['total_earnings'] = latest.get('total_earnings', 0)
        features['turf_win_rate'] = latest.get('turf_win_rate', 0.0)
        features['dirt_win_rate'] = latest.get('dirt_win_rate', 0.0)
        # distance_similar_win_rate: 現在のレース距離±200m以内での勝率を動的計算
        if race_distance is not None and 'distance' in horse_races.columns:
            try:
                dist_num = float(race_distance)
                hr_dist = pd.to_numeric(horse_races['distance'], errors='coerce')
                similar_races = horse_races[(hr_dist >= dist_num - 200) & (hr_dist <= dist_num + 200)].copy()
                if len(similar_races) > 0:
                    similar_races['rank'] = get_rank(similar_races)
                    similar_finished = similar_races[similar_races['rank'].notna()]
                    if len(similar_finished) > 0:
                        features['distance_similar_win_rate'] = (similar_finished['rank'] == 1).sum() / len(similar_finished)
                    else:
                        features['distance_similar_win_rate'] = 0.0
                else:
                    features['distance_similar_win_rate'] = 0.0
            except:
                features['distance_similar_win_rate'] = 0.0
        else:
            features['distance_similar_win_rate'] = latest.get('distance_similar_win_rate', 0.0)
        # カラム名対応
        prev_rank_val = latest.get('Rank') if 'Rank' in latest.index else latest.get('着順')
        features['prev_race_rank'] = pd.to_numeric(prev_rank_val, errors='coerce')
        if pd.isna(features['prev_race_rank']):
            features['prev_race_rank'] = 99
        features['days_since_last_race'] = latest.get('days_since_last_race', 365)
        features['avg_passage_position'] = latest.get('avg_passage_position', 0.0)
        features['avg_last_3f'] = latest.get('avg_last_3f', 0.0)
        features['grade_race_starts'] = latest.get('grade_race_starts', 0)

        # 血統
        father = latest.get('father')
        mother_father = latest.get('mother_father')
        if father and father in sire_stats_dict:
            features['father_win_rate'] = sire_stats_dict[father].get('father_win_rate', 0.0)
            features['father_top3_rate'] = sire_stats_dict[father].get('father_top3_rate', 0.0)
        else:
            features['father_win_rate'] = 0.0
            features['father_top3_rate'] = 0.0

        if mother_father and mother_father in sire_stats_dict:
            features['mother_father_win_rate'] = sire_stats_dict[mother_father].get('mother_father_win_rate', 0.0)
            features['mother_father_top3_rate'] = sire_stats_dict[mother_father].get('mother_father_top3_rate', 0.0)
        else:
            features['mother_father_win_rate'] = 0.0
            features['mother_father_top3_rate'] = 0.0

        # 直近3走平均着順
        if len(horse_races) >= 3:
            recent = horse_races.sort_values('date', ascending=False).head(3)
            recent['rank'] = get_rank(recent)
            finished = recent[recent['rank'].notna()]
            features['recent_avg_rank'] = finished['rank'].mean() if len(finished) > 0 else 99.0
        else:
            features['recent_avg_rank'] = 99.0

        # 馬体重変化
        if len(horse_races) >= 2:
            sorted_races = horse_races.sort_values('date', ascending=False)
            latest_weight_str = sorted_races.iloc[0].get('馬体重', sorted_races.iloc[0].get('馬の重', ''))
            prev_weight_str = sorted_races.iloc[1].get('馬体重', sorted_races.iloc[1].get('馬の重', ''))
            latest_match = re.search(r'(\d+)', str(latest_weight_str))
            prev_match = re.search(r'(\d+)', str(prev_weight_str))
            if latest_match and prev_match:
                features['weight_change'] = float(latest_match.group(1)) - float(prev_match.group(1))
                features['prev_weight'] = float(prev_match.group(1))
            else:
                features['weight_change'] = 0.0
                features['prev_weight'] = 0.0
        else:
            features['weight_change'] = 0.0
            features['prev_weight'] = 0.0
    else:
        # 新馬
        for key in ['total_starts', 'total_win_rate', 'total_earnings', 'turf_win_rate',
                    'dirt_win_rate', 'distance_similar_win_rate', 'avg_passage_position',
                    'avg_last_3f', 'grade_race_starts', 'father_win_rate', 'father_top3_rate',
                    'mother_father_win_rate', 'mother_father_top3_rate', 'weight_change', 'prev_weight']:
            features[key] = 0.0
        features['prev_race_rank'] = 99
        features['days_since_last_race'] = 365
        features['recent_avg_rank'] = 99.0

    # 調教師・騎手統計
    if trainer_name and trainer_name in trainer_jockey_stats['trainer']:
        features['trainer_win_rate'] = trainer_jockey_stats['trainer'][trainer_name]['win_rate']
        features['trainer_top3_rate'] = trainer_jockey_stats['trainer'][trainer_name]['top3_rate']
    else:
        features['trainer_win_rate'] = 0.0
        features['trainer_top3_rate'] = 0.0

    if jockey_name and jockey_name in trainer_jockey_stats['jockey']:
        features['jockey_win_rate'] = trainer_jockey_stats['jockey'][jockey_name]['win_rate']
        features['jockey_top3_rate'] = trainer_jockey_stats['jockey'][jockey_name]['top3_rate']
    else:
        features['jockey_win_rate'] = 0.0
        features['jockey_top3_rate'] = 0.0

    # Phase 2A特徴量: コース適性
    course_win_rate = 0.0
    course_top3_rate = 0.0
    course_starts = 0

    # race_course_typeが空文字列の場合もスキップ（str.contains()のエラー防止）
    if len(horse_races) > 0 and race_track and race_distance and race_course_type and race_course_type != '':
        same_course = horse_races[
            (horse_races['track_name'] == race_track) &
            (horse_races['distance'] == race_distance) &
            (horse_races['course_type'].astype(str).str.contains(race_course_type, na=False))
        ].copy()

        if len(same_course) > 0:
            same_course['rank'] = get_rank(same_course)
            same_course_finished = same_course[same_course['rank'].notna()]

            if len(same_course_finished) > 0:
                course_starts = len(same_course_finished)
                course_wins = (same_course_finished['rank'] == 1).sum()
                course_top3 = (same_course_finished['rank'] <= 3).sum()
                course_win_rate = course_wins / course_starts
                course_top3_rate = course_top3 / course_starts

    features['course_win_rate'] = course_win_rate
    features['course_top3_rate'] = course_top3_rate
    features['course_starts'] = course_starts

    # Phase 2A特徴量: 馬場状態適性
    condition_win_rate = 0.0
    condition_top3_rate = 0.0
    condition_starts = 0

    if len(horse_races) > 0 and race_track_condition:
        same_condition = horse_races[
            horse_races['track_condition'] == race_track_condition
        ].copy()

        if len(same_condition) > 0:
            same_condition['rank'] = get_rank(same_condition)
            same_condition_finished = same_condition[same_condition['rank'].notna()]

            if len(same_condition_finished) > 0:
                condition_starts = len(same_condition_finished)
                condition_wins = (same_condition_finished['rank'] == 1).sum()
                condition_top3 = (same_condition_finished['rank'] <= 3).sum()
                condition_win_rate = condition_wins / condition_starts
                condition_top3_rate = condition_top3 / condition_starts

    features['condition_win_rate'] = condition_win_rate
    features['condition_top3_rate'] = condition_top3_rate
    features['condition_starts'] = condition_starts

    # Phase 2A特徴量: 休養明け成績
    rest_win_rate = 0.0
    rest_top3_rate = 0.0
    rest_starts = 0

    if len(horse_races) > 0:
        rest_races = horse_races[
            pd.to_numeric(horse_races['days_since_last_race'], errors='coerce') >= 60
        ].copy()

        if len(rest_races) > 0:
            rest_races['rank'] = get_rank(rest_races)
            rest_races_finished = rest_races[rest_races['rank'].notna()]

            if len(rest_races_finished) > 0:
                rest_starts = len(rest_races_finished)
                rest_wins = (rest_races_finished['rank'] == 1).sum()
                rest_top3 = (rest_races_finished['rank'] <= 3).sum()
                rest_win_rate = rest_wins / rest_starts
                rest_top3_rate = rest_top3 / rest_starts

    features['rest_win_rate'] = rest_win_rate
    features['rest_top3_rate'] = rest_top3_rate
    features['rest_starts'] = rest_starts

    # Phase 2B-1特徴量: 枠順適性
    inner_frame_win_rate = 0.0
    outer_frame_win_rate = 0.0
    current_frame_win_rate = 0.0
    inner_frame_starts = 0
    outer_frame_starts = 0
    current_frame_starts = 0

    if len(horse_races) > 0 and '枠番' in horse_races.columns:
        horse_races['frame_num'] = pd.to_numeric(horse_races['枠番'], errors='coerce')

        # 内枠（1-4枠）での成績
        inner_races = horse_races[
            (horse_races['frame_num'] >= 1) & (horse_races['frame_num'] <= 4)
        ].copy()
        if len(inner_races) > 0:
            inner_races['rank'] = get_rank(inner_races)
            inner_finished = inner_races[inner_races['rank'].notna()]
            if len(inner_finished) > 0:
                inner_frame_starts = len(inner_finished)
                inner_wins = (inner_finished['rank'] == 1).sum()
                inner_frame_win_rate = inner_wins / inner_frame_starts

        # 外枠（5-8枠）での成績
        outer_races = horse_races[
            (horse_races['frame_num'] >= 5) & (horse_races['frame_num'] <= 8)
        ].copy()
        if len(outer_races) > 0:
            outer_races['rank'] = get_rank(outer_races)
            outer_finished = outer_races[outer_races['rank'].notna()]
            if len(outer_finished) > 0:
                outer_frame_starts = len(outer_finished)
                outer_wins = (outer_finished['rank'] == 1).sum()
                outer_frame_win_rate = outer_wins / outer_frame_starts

        # 該当枠での成績
        if current_frame is not None:
            try:
                current_frame_num = float(current_frame)
                current_frame_races = horse_races[
                    horse_races['frame_num'] == current_frame_num
                ].copy()
                if len(current_frame_races) > 0:
                    current_frame_races['rank'] = get_rank(current_frame_races)
                    current_frame_finished = current_frame_races[current_frame_races['rank'].notna()]
                    if len(current_frame_finished) > 0:
                        current_frame_starts = len(current_frame_finished)
                        current_frame_wins = (current_frame_finished['rank'] == 1).sum()
                        current_frame_win_rate = current_frame_wins / current_frame_starts
            except:
                pass

    features['inner_frame_win_rate'] = inner_frame_win_rate
    features['outer_frame_win_rate'] = outer_frame_win_rate
    features['current_frame_win_rate'] = current_frame_win_rate
    features['inner_frame_starts'] = inner_frame_starts
    features['outer_frame_starts'] = outer_frame_starts
    features['current_frame_starts'] = current_frame_starts

    # Phase 4A: トレンド特徴量
    consecutive_good_runs = 0  # 連続好走（3着以内）
    consecutive_bad_runs = 0   # 連続不振（6着以下）
    rank_improving_trend = 0   # 着順改善トレンド（直近3走）
    prev_rank_change = 0       # 前走比着順変化

    if len(horse_races) > 0:
        sorted_races = horse_races.sort_values('date', ascending=False)
        sorted_races['rank'] = get_rank(sorted_races)
        finished_races = sorted_races[sorted_races['rank'].notna()]

        if len(finished_races) > 0:
            # 連続好走・不振の計算
            for idx, race in finished_races.iterrows():
                rank = race['rank']
                if rank <= 3:
                    consecutive_good_runs += 1
                    consecutive_bad_runs = 0  # リセット
                elif rank >= 6:
                    consecutive_bad_runs += 1
                    consecutive_good_runs = 0  # リセット
                else:
                    break  # 中途半端な着順で連続終了

            # 直近3走での着順改善トレンド
            if len(finished_races) >= 3:
                recent_3 = finished_races.head(3)
                ranks = recent_3['rank'].tolist()
                # 着順が小さくなっていく（改善）場合にプラス
                if ranks[0] < ranks[1] < ranks[2]:
                    rank_improving_trend = 1
                elif ranks[0] > ranks[1] > ranks[2]:
                    rank_improving_trend = -1  # 悪化トレンド

            # 前走比着順変化
            if len(finished_races) >= 2:
                latest_rank = finished_races.iloc[0]['rank']
                prev_rank = finished_races.iloc[1]['rank']
                prev_rank_change = prev_rank - latest_rank  # プラスなら改善

    features['consecutive_good_runs'] = consecutive_good_runs
    features['consecutive_bad_runs'] = consecutive_bad_runs
    features['rank_improving_trend'] = rank_improving_trend
    features['prev_rank_change'] = prev_rank_change

    # Phase 4B: タイム指数（相対スピード評価）
    avg_time_seconds = 0.0  # 平均走破タイム（秒）
    best_time_seconds = 0.0  # 最速走破タイム（秒）
    time_consistency = 0.0   # タイムの安定性（標準偏差の逆数）

    if len(horse_races) > 0 and 'タイム' in horse_races.columns:
        # タイムを秒に変換する関数
        def time_to_seconds(time_str):
            try:
                if pd.isna(time_str) or time_str == '':
                    return None
                parts = str(time_str).split(':')
                if len(parts) == 2:
                    minutes = float(parts[0])
                    seconds = float(parts[1])
                    return minutes * 60 + seconds
            except:
                pass
            return None

        times_seconds = horse_races['タイム'].apply(time_to_seconds).dropna()

        if len(times_seconds) > 0:
            avg_time_seconds = times_seconds.mean()
            best_time_seconds = times_seconds.min()

            if len(times_seconds) > 1:
                time_std = times_seconds.std()
                time_consistency = 1.0 / (time_std + 0.1)  # 標準偏差の逆数（安定性指標）

    features['avg_time_seconds'] = avg_time_seconds
    features['best_time_seconds'] = best_time_seconds
    features['time_consistency'] = time_consistency

    # Phase 4D: 開催情報（レース日程パターン）
    race_day_of_week = 0  # 曜日（0=月曜...6=日曜）
    race_number_in_day = 0  # 1日の中での何レース目か

    if race_date:
        try:
            # 日付から曜日を計算
            race_day_of_week = pd.to_datetime(race_date).dayofweek
        except:
            race_day_of_week = 0

    # race_idから1日の中での何レース目かを取得
    # race_id形式: YYYYJJKKDDNN (JJ=競馬場, KK=開催回, DD=日目, NN=レース番号)
    if race_id is not None:
        try:
            race_id_str = str(int(float(race_id)))
            if len(race_id_str) >= 12:
                race_number_in_day = int(race_id_str[-2:])  # 最後の2桁
        except:
            race_number_in_day = 0

    features['race_day_of_week'] = race_day_of_week
    features['race_number_in_day'] = race_number_in_day

    # Phase 5A: 距離適性詳細
    short_distance_win_rate = 0.0  # 短距離（~1400m）
    mile_distance_win_rate = 0.0   # マイル（1401-1800m）
    medium_distance_win_rate = 0.0 # 中距離（1801-2200m）
    long_distance_win_rate = 0.0   # 長距離（2201m~）
    distance_change_large = 0      # 距離変化大（±200m以上）

    if len(horse_races) > 0 and 'distance' in horse_races.columns:
        horse_races['distance_num'] = pd.to_numeric(horse_races['distance'], errors='coerce')

        # 短距離での成績
        short_races = horse_races[horse_races['distance_num'] <= 1400].copy()
        if len(short_races) > 0:
            short_races['rank'] = get_rank(short_races)
            short_finished = short_races[short_races['rank'].notna()]
            if len(short_finished) > 0:
                short_wins = (short_finished['rank'] == 1).sum()
                short_distance_win_rate = short_wins / len(short_finished)

        # マイル距離での成績
        mile_races = horse_races[
            (horse_races['distance_num'] > 1400) & (horse_races['distance_num'] <= 1800)
        ].copy()
        if len(mile_races) > 0:
            mile_races['rank'] = get_rank(mile_races)
            mile_finished = mile_races[mile_races['rank'].notna()]
            if len(mile_finished) > 0:
                mile_wins = (mile_finished['rank'] == 1).sum()
                mile_distance_win_rate = mile_wins / len(mile_finished)

        # 中距離での成績
        medium_races = horse_races[
            (horse_races['distance_num'] > 1800) & (horse_races['distance_num'] <= 2200)
        ].copy()
        if len(medium_races) > 0:
            medium_races['rank'] = get_rank(medium_races)
            medium_finished = medium_races[medium_races['rank'].notna()]
            if len(medium_finished) > 0:
                medium_wins = (medium_finished['rank'] == 1).sum()
                medium_distance_win_rate = medium_wins / len(medium_finished)

        # 長距離での成績
        long_races = horse_races[horse_races['distance_num'] > 2200].copy()
        if len(long_races) > 0:
            long_races['rank'] = get_rank(long_races)
            long_finished = long_races[long_races['rank'].notna()]
            if len(long_finished) > 0:
                long_wins = (long_finished['rank'] == 1).sum()
                long_distance_win_rate = long_wins / len(long_finished)

        # 距離変化（前走との差）
        if len(horse_races) >= 2 and race_distance:
            try:
                sorted_races = horse_races.sort_values('date', ascending=False)
                latest_distance = pd.to_numeric(sorted_races.iloc[0]['distance'], errors='coerce')
                if pd.notna(latest_distance):
                    distance_diff = abs(float(race_distance) - latest_distance)
                    if distance_diff >= 200:
                        distance_change_large = 1
            except:
                pass

    features['short_distance_win_rate'] = short_distance_win_rate
    features['mile_distance_win_rate'] = mile_distance_win_rate
    features['medium_distance_win_rate'] = medium_distance_win_rate
    features['long_distance_win_rate'] = long_distance_win_rate
    features['distance_change_large'] = distance_change_large

    # Phase 5B: 相対上がり評価
    last_3f_rank_avg = 99.0        # レース内での上がり順位の平均
    fastest_last_3f_rate = 0.0     # 最速上がりを記録した割合
    relative_last_3f = 0.0         # 平均上がりタイム（小さいほど速い）

    # 上がりカラムを探す（「上り」または「上がり」）
    agari_col = None
    for col_candidate in ['上り', '上がり']:
        if col_candidate in horse_races.columns:
            agari_col = col_candidate
            break

    if len(horse_races) > 0 and agari_col:
        # 上がりタイムを数値化
        def parse_last_3f(last_3f_str):
            try:
                if pd.isna(last_3f_str) or last_3f_str == '':
                    return None
                return float(last_3f_str)
            except:
                return None

        horse_races['last_3f_num'] = horse_races[agari_col].apply(parse_last_3f)
        valid_last_3f = horse_races[horse_races['last_3f_num'].notna()].copy()

        if len(valid_last_3f) > 0:
            # 平均上がりタイム
            relative_last_3f = valid_last_3f['last_3f_num'].mean()

            # レース内での上がり順位を計算（各レースごと）
            last_3f_ranks = []
            fastest_count = 0

            # df_historyの上がりカラムも同じ名前を使う
            agari_col_hist = None
            for col_candidate in ['上り', '上がり']:
                if col_candidate in df_history.columns:
                    agari_col_hist = col_candidate
                    break

            if agari_col_hist:
                for race_id_val in valid_last_3f['race_id'].unique():
                    race_data = df_history[df_history['race_id'] == race_id_val].copy()
                    race_data['last_3f_num'] = race_data[agari_col_hist].apply(parse_last_3f)
                    race_data_valid = race_data[race_data['last_3f_num'].notna()]

                    if len(race_data_valid) > 0:
                        # 上がりタイムでランク付け（小さい方が速い）
                        race_data_valid = race_data_valid.copy()
                        race_data_valid['last_3f_rank'] = race_data_valid['last_3f_num'].rank(method='min')

                        # この馬の上がり順位を取得
                        horse_data = race_data_valid[race_data_valid['horse_id'] == horse_id_num]
                        if len(horse_data) > 0:
                            rank = horse_data.iloc[0]['last_3f_rank']
                            last_3f_ranks.append(rank)

                            # 最速上がりだったか
                            if rank == 1.0:
                                fastest_count += 1

            if len(last_3f_ranks) > 0:
                last_3f_rank_avg = np.mean(last_3f_ranks)
                fastest_last_3f_rate = fastest_count / len(last_3f_ranks)

    # last_3f_avgカラムからのフォールバック（上がりカラムがない場合）
    elif len(horse_races) > 0 and 'last_3f_avg' in horse_races.columns:
        avg_val = horse_races['last_3f_avg'].dropna()
        if len(avg_val) > 0:
            relative_last_3f = avg_val.mean()

    features['last_3f_rank_avg'] = last_3f_rank_avg
    features['fastest_last_3f_rate'] = fastest_last_3f_rate
    features['relative_last_3f'] = relative_last_3f

    # 欠損値処理
    for key in features:
        if pd.isna(features[key]):
            features[key] = 0.0

    return features


# メイン処理（このファイルを直接実行した場合のみ動作）
if __name__ == '__main__':
    # データ読み込み
    print("[1] データ読み込み中...")
    df = pd.read_csv('data/main/netkeiba_data_2024_2025.csv', low_memory=False)
    print(f"  総レコード数: {len(df):,}件")
    print()

    # 着順を数値化
    df['rank'] = get_rank(df)
    df['target'] = (df['rank'] <= 3).astype(int)
    df_finished = df[df['rank'].notna()].copy()

    # 2024年で訓練、2025年の最初の1000レースでテスト
    print("[2] データ分割...")
    df_train = df_finished[df_finished['race_id'].astype(str).str[:4] == '2024'].copy()

    # 2025年のレースをrace_id順に取得
    df_test_all = df_finished[df_finished['race_id'].astype(str).str[:4] == '2025'].copy()
    test_race_ids = sorted(df_test_all['race_id'].unique())  # 全レース
    df_test = df_test_all[df_test_all['race_id'].isin(test_race_ids)].copy()

    print(f"  訓練データ（2024年）: {len(df_train):,}件")
    print(f"  テストレース数: {len(test_race_ids):,}レース")
    print(f"  テストデータ: {len(df_test):,}件")
    print()

    # 血統統計を事前計算
    print("[3] 血統統計計算中...")
    sire_stats = calculate_sire_stats(df_train)
    print(f"  種牡馬統計: {len(sire_stats):,}種")
    print()

    # 調教師・騎手統計を事前計算
    print("[3-2] 調教師・騎手統計計算中...")
    trainer_jockey_stats = calculate_trainer_jockey_stats(df_train)
    print(f"  調教師統計: {len(trainer_jockey_stats['trainer']):,}人")
    print(f"  騎手統計: {len(trainer_jockey_stats['jockey']):,}人")
    print()

    # 特徴量リスト
    model_features = [
        'total_starts', 'total_win_rate', 'total_earnings',
        'turf_win_rate', 'dirt_win_rate', 'distance_similar_win_rate',
        'prev_race_rank', 'days_since_last_race',
        'trainer_win_rate', 'trainer_top3_rate', 'jockey_win_rate', 'jockey_top3_rate',
        'course_win_rate', 'course_top3_rate', 'course_starts',
        'condition_win_rate', 'condition_top3_rate', 'condition_starts',
        'rest_win_rate', 'rest_top3_rate', 'rest_starts',
        'inner_frame_win_rate', 'outer_frame_win_rate', 'current_frame_win_rate',
        'inner_frame_starts', 'outer_frame_starts', 'current_frame_starts',
        'recent_avg_rank', 'avg_passage_position', 'avg_last_3f', 'grade_race_starts',
        'father_win_rate', 'father_top3_rate', 'mother_father_win_rate', 'mother_father_top3_rate',
        'weight_change', 'prev_weight',
        # Phase 4A: トレンド特徴量
        'consecutive_good_runs', 'consecutive_bad_runs', 'rank_improving_trend', 'prev_rank_change',
        # Phase 4B: タイム指数
        'avg_time_seconds', 'best_time_seconds', 'time_consistency',
        # Phase 4D: 開催情報
        'race_day_of_week', 'race_number_in_day',
        # Phase 5A: 距離適性詳細
        'short_distance_win_rate', 'mile_distance_win_rate', 'medium_distance_win_rate',
        'long_distance_win_rate', 'distance_change_large',
        # Phase 5B: 相対上がり評価
        'last_3f_rank_avg', 'fastest_last_3f_rate', 'relative_last_3f'
    ]

    # 訓練データ準備（動的特徴量計算）
    print("[4] 訓練データ特徴量計算中（サンプリング: 最初の5000件）...")
    train_features_list = []
    train_targets = []

    # 訓練データから最初の5000件をサンプリング（計算時間短縮のため）
    df_train_sample = df_train.head(5000)

    for idx, row in df_train_sample.iterrows():
        horse_id = row['horse_id']
        race_date = row['date']
        trainer_name = row.get('調教師', None)
        jockey_name = row.get('騎手', None)
        race_track = row.get('track_name', None)
        race_distance = row.get('distance', None)
        race_course_type = row.get('course_type', None)
        race_track_condition = row.get('track_condition', None)
        current_frame = row.get('枠番', None)

        features = calculate_horse_features_dynamic(
            horse_id, df, race_date, sire_stats,
            trainer_jockey_stats, trainer_name, jockey_name,
            race_track, race_distance, race_course_type, race_track_condition, current_frame,
            race_id=row.get('race_id', None)
        )
        if features:
            train_features_list.append(features)
            train_targets.append(row['target'])

    X_train = pd.DataFrame(train_features_list)[model_features]
    y_train = np.array(train_targets)

    print(f"  訓練データ形状: {X_train.shape}")
    print()

    # モデル訓練
    print("[5] モデル訓練中...")
    model = lgb.LGBMClassifier(
        objective='binary',
        n_estimators=200,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
        random_state=42,
        verbose=-1
    )
    model.fit(X_train, y_train)
    print("  訓練完了")
    print()

    # テストデータの動的特徴量計算
    print("[6] テストデータ特徴量計算中...")
    test_features_list = []
    test_targets = []

    for idx, row in df_test.iterrows():
        horse_id = row['horse_id']
        race_date = row['date']
        trainer_name = row.get('調教師', None)
        jockey_name = row.get('騎手', None)
        race_track = row.get('track_name', None)
        race_distance = row.get('distance', None)
        race_course_type = row.get('course_type', None)
        race_track_condition = row.get('track_condition', None)
        current_frame = row.get('枠番', None)

        features = calculate_horse_features_dynamic(
            horse_id, df, race_date, sire_stats,
            trainer_jockey_stats, trainer_name, jockey_name,
            race_track, race_distance, race_course_type, race_track_condition, current_frame,
            race_id=row.get('race_id', None)
        )
        if features:
            test_features_list.append(features)
            test_targets.append(row['target'])

    X_test = pd.DataFrame(test_features_list)[model_features]
    y_test = np.array(test_targets)

    print(f"  テストデータ形状: {X_test.shape}")
    print()

    # 予測
    print("[7] 予測実行...")
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    y_pred = (y_pred_proba >= 0.5).astype(int)
    print()

    # 評価
    print("=" * 80)
    print(" 評価結果（動的特徴量計算）")
    print("=" * 80)
    print()

    accuracy = accuracy_score(y_test, y_pred)
    print(f"正解率（Accuracy）: {accuracy:.4f} ({accuracy*100:.2f}%)")
    print()

    # 予測確率別的中率
    df_test_result = pd.DataFrame({
        'pred_proba': y_pred_proba,
        'actual': y_test
    })

    print("予測確率別の的中率:")
    for threshold in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
        selected = df_test_result[df_test_result['pred_proba'] >= threshold]
        if len(selected) > 0:
            hit_rate = selected['actual'].sum() / len(selected)
            print(f"  予測確率 >= {threshold:.1f}: {len(selected):4d}件中 {selected['actual'].sum():4d}件的中 ({hit_rate*100:.1f}%)")

    print()

    # 特徴量重要度（上位20個）
    print("=" * 80)
    print(" 特徴量重要度 Top 20")
    print("=" * 80)
    print()

    feature_importance = pd.DataFrame({
        'feature': model_features,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    for idx, row in feature_importance.head(20).iterrows():
        print(f"  {row['feature']:30s}: {row['importance']:8.1f}")

    print()
    print("=" * 80)
    print(" バックテスト完了")
    print("=" * 80)
