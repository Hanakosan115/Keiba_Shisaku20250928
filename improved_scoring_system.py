"""
改善版スコアリングシステム
- 過去成績に加えて騎手・調教師データを活用
- 馬体重変化を考慮
- より精度の高い予測を目指す
"""
import pandas as pd
import numpy as np
from functools import lru_cache

# グローバル変数でデータフレームをキャッシュ
_df_cache = None

def load_race_data():
    """レースデータを読み込み（初回のみ）"""
    global _df_cache
    if _df_cache is None:
        print("[INFO] CSVデータ読み込み中...")
        _df_cache = pd.read_csv(
            r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
            encoding='utf-8',
            low_memory=False
        )
        _df_cache['date_parsed'] = pd.to_datetime(_df_cache['date'], errors='coerce')
        print(f"[INFO] CSVデータ読み込み完了: {len(_df_cache):,}件")
    return _df_cache

def calculate_jockey_stats(jockey_name, reference_date, months_back=12):
    """
    騎手の過去成績を計算
    - 直近N ヶ月の勝率、連対率、複勝率
    """
    if pd.isna(jockey_name) or jockey_name == '':
        return {'win_rate': 0, 'top2_rate': 0, 'top3_rate': 0, 'races': 0}

    df = load_race_data()
    reference_date_parsed = pd.to_datetime(reference_date, errors='coerce')

    # 過去N ヶ月のデータを取得
    start_date = reference_date_parsed - pd.DateOffset(months=months_back)

    jockey_races = df[
        (df['JockeyName'] == jockey_name) &
        (df['date_parsed'] >= start_date) &
        (df['date_parsed'] < reference_date_parsed)
    ].copy()

    if len(jockey_races) == 0:
        return {'win_rate': 0, 'top2_rate': 0, 'top3_rate': 0, 'races': 0}

    # ランクを数値化
    jockey_races['rank_num'] = pd.to_numeric(jockey_races['Rank'], errors='coerce')
    valid_races = jockey_races[jockey_races['rank_num'].notna()]

    if len(valid_races) == 0:
        return {'win_rate': 0, 'top2_rate': 0, 'top3_rate': 0, 'races': 0}

    total_races = len(valid_races)
    wins = (valid_races['rank_num'] == 1).sum()
    top2 = (valid_races['rank_num'] <= 2).sum()
    top3 = (valid_races['rank_num'] <= 3).sum()

    return {
        'win_rate': wins / total_races * 100,
        'top2_rate': top2 / total_races * 100,
        'top3_rate': top3 / total_races * 100,
        'races': total_races
    }

def calculate_trainer_stats(trainer_name, reference_date, months_back=12):
    """
    調教師の過去成績を計算
    - 直近N ヶ月の勝率、連対率、複勝率
    """
    if pd.isna(trainer_name) or trainer_name == '':
        return {'win_rate': 0, 'top2_rate': 0, 'top3_rate': 0, 'races': 0}

    df = load_race_data()
    reference_date_parsed = pd.to_datetime(reference_date, errors='coerce')

    # 過去N ヶ月のデータを取得
    start_date = reference_date_parsed - pd.DateOffset(months=months_back)

    trainer_races = df[
        (df['TrainerName'] == trainer_name) &
        (df['date_parsed'] >= start_date) &
        (df['date_parsed'] < reference_date_parsed)
    ].copy()

    if len(trainer_races) == 0:
        return {'win_rate': 0, 'top2_rate': 0, 'top3_rate': 0, 'races': 0}

    # ランクを数値化
    trainer_races['rank_num'] = pd.to_numeric(trainer_races['Rank'], errors='coerce')
    valid_races = trainer_races[trainer_races['rank_num'].notna()]

    if len(valid_races) == 0:
        return {'win_rate': 0, 'top2_rate': 0, 'top3_rate': 0, 'races': 0}

    total_races = len(valid_races)
    wins = (valid_races['rank_num'] == 1).sum()
    top2 = (valid_races['rank_num'] <= 2).sum()
    top3 = (valid_races['rank_num'] <= 3).sum()

    return {
        'win_rate': wins / total_races * 100,
        'top2_rate': top2 / total_races * 100,
        'top3_rate': top3 / total_races * 100,
        'races': total_races
    }

def calculate_improved_score(horse_data, race_conditions, race_date):
    """
    改善版スコア計算

    Parameters:
    - horse_data: 馬の基本情報（過去成績、騎手、調教師など）
    - race_conditions: レース条件（距離、コースなど）
    - race_date: レース日付（文字列、YYYY-MM-DD形式）
    """
    score = 50.0

    # ========================================
    # 1. 馬の過去成績（従来通り）
    # ========================================
    race_results = horse_data.get('race_results', [])

    if not race_results or len(race_results) == 0:
        # 過去データなしはデフォルトスコア
        pass  # score = 50.0のまま
    else:
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
                score += 25
            elif avg_rank <= 3:
                score += 15
            elif avg_rank <= 5:
                score += 8
            elif avg_rank <= 8:
                score += 3
            else:
                score -= 8

            # 成績の安定性
            if len(recent_ranks) >= 2:
                std = np.std(recent_ranks)
                if std <= 1:
                    score += 8
                elif std <= 2:
                    score += 4
                elif std >= 5:
                    score -= 4

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
                                distance_fit_score += 10
                            elif past_rank <= 5:
                                distance_fit_score += 3
                            distance_count += 1

            if distance_count > 0:
                score += distance_fit_score / distance_count

    # ========================================
    # 2. 騎手の実績
    # ========================================
    jockey_name = horse_data.get('jockey_name')
    if jockey_name and not pd.isna(jockey_name):
        jockey_stats = calculate_jockey_stats(jockey_name, race_date, months_back=6)

        if jockey_stats['races'] >= 10:  # 最低10レース以上のデータがある場合
            # 勝率に応じてスコア追加
            win_rate = jockey_stats['win_rate']
            if win_rate >= 15:  # 勝率15%以上（トップ騎手）
                score += 15
            elif win_rate >= 10:
                score += 10
            elif win_rate >= 7:
                score += 5
            elif win_rate >= 5:
                score += 2
            elif win_rate < 3:
                score -= 5  # 勝率3%未満はマイナス

    # ========================================
    # 3. 調教師の実績
    # ========================================
    trainer_name = horse_data.get('trainer_name')
    if trainer_name and not pd.isna(trainer_name):
        trainer_stats = calculate_trainer_stats(trainer_name, race_date, months_back=6)

        if trainer_stats['races'] >= 10:  # 最低10レース以上のデータがある場合
            # 勝率に応じてスコア追加
            win_rate = trainer_stats['win_rate']
            if win_rate >= 12:  # 勝率12%以上（トップ調教師）
                score += 12
            elif win_rate >= 8:
                score += 8
            elif win_rate >= 5:
                score += 4
            elif win_rate >= 3:
                score += 2
            elif win_rate < 2:
                score -= 3  # 勝率2%未満はマイナス

    # ========================================
    # 4. 馬体重変化
    # ========================================
    weight_diff = horse_data.get('weight_diff')
    if weight_diff is not None and not pd.isna(weight_diff):
        weight_diff_num = pd.to_numeric(weight_diff, errors='coerce')
        if pd.notna(weight_diff_num):
            # 馬体重の変化を評価
            if -2 <= weight_diff_num <= 4:  # 理想的な範囲
                score += 5
            elif -5 <= weight_diff_num <= 8:  # 許容範囲
                score += 2
            elif weight_diff_num < -10 or weight_diff_num > 15:  # 大幅な増減
                score -= 8
            elif weight_diff_num < -5 or weight_diff_num > 10:
                score -= 4

    # ========================================
    # 5. 性別・年齢
    # ========================================
    sex = horse_data.get('sex')
    age = horse_data.get('age')

    if age is not None and not pd.isna(age):
        age_num = pd.to_numeric(age, errors='coerce')
        if pd.notna(age_num):
            # 年齢による調整
            if 4 <= age_num <= 5:  # ピーク年齢
                score += 3
            elif age_num == 3:  # 若馬
                score += 1
            elif age_num >= 7:  # 高齢馬
                score -= 5

    return max(0, score)  # 最低0点
