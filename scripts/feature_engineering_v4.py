"""
Feature Engineering V4 - 実践的特徴量
1. 当日馬場バイアス（内/外有利を動的判定）
2. 天気×馬場×血統の相性
3. 展開予想強化（逃げ馬競合、先行争い激化度）
4. 血統×条件適性
"""

import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime, timedelta


class TrackBiasAnalyzer:
    """当日の馬場バイアスを動的に判定"""

    def __init__(self, df_history):
        """過去データから基準バイアスを学習"""
        self.base_bias = self._calculate_base_bias(df_history)
        self.today_results = {}  # 当日レース結果を蓄積

    def _calculate_base_bias(self, df):
        """競馬場×馬場状態×コースタイプごとの枠番別勝率"""
        bias = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'top3': 0, 'runs': 0}))

        rank_col = 'Rank' if 'Rank' in df.columns else '着順'
        waku_col = 'Waku' if 'Waku' in df.columns else '枠番'

        for _, row in df.iterrows():
            track = row.get('track_name', '')
            condition = row.get('track_condition', '')
            course = row.get('course_type', '')

            try:
                waku = int(row.get(waku_col, 0))
                rank = int(row.get(rank_col, 99))
            except:
                continue

            if not track or waku < 1 or waku > 8:
                continue

            # 内枠(1-2), 中内(3-4), 中外(5-6), 外枠(7-8)
            if waku <= 2:
                waku_cat = 'inner'
            elif waku <= 4:
                waku_cat = 'mid_inner'
            elif waku <= 6:
                waku_cat = 'mid_outer'
            else:
                waku_cat = 'outer'

            key = (track, condition, course)
            bias[key][waku_cat]['runs'] += 1
            if rank == 1:
                bias[key][waku_cat]['wins'] += 1
            if rank <= 3:
                bias[key][waku_cat]['top3'] += 1

        # 勝率・複勝率を計算
        result = {}
        for key, waku_data in bias.items():
            result[key] = {}
            total_runs = sum(d['runs'] for d in waku_data.values())
            if total_runs < 100:
                continue
            for waku_cat, data in waku_data.items():
                if data['runs'] >= 20:
                    result[key][waku_cat] = {
                        'win_rate': data['wins'] / data['runs'],
                        'top3_rate': data['top3'] / data['runs'],
                        'runs': data['runs']
                    }
        return result

    def add_today_result(self, track, race_num, results):
        """当日のレース結果を追加（リアルタイムバイアス更新用）"""
        key = (track, datetime.now().strftime('%Y-%m-%d'))
        if key not in self.today_results:
            self.today_results[key] = []
        self.today_results[key].append({
            'race_num': race_num,
            'results': results  # [(waku, rank), ...]
        })

    def get_realtime_bias(self, track, condition, course_type):
        """当日のリアルタイムバイアスを計算"""
        key = (track, datetime.now().strftime('%Y-%m-%d'))

        if key not in self.today_results or len(self.today_results[key]) < 2:
            # 当日データ不足の場合は過去データから
            return self._get_historical_bias(track, condition, course_type)

        # 当日レース結果から枠番傾向を計算
        inner_score = 0
        outer_score = 0
        count = 0

        for race in self.today_results[key]:
            for waku, rank in race['results']:
                if rank <= 3:
                    if waku <= 4:
                        inner_score += (4 - rank)  # 1着=3, 2着=2, 3着=1
                    else:
                        outer_score += (4 - rank)
                    count += 1

        if count == 0:
            return self._get_historical_bias(track, condition, course_type)

        # バイアス方向を判定
        total = inner_score + outer_score
        if total == 0:
            return {'direction': 'neutral', 'strength': 0.0}

        inner_ratio = inner_score / total

        if inner_ratio >= 0.65:
            return {'direction': 'inner', 'strength': (inner_ratio - 0.5) * 2}
        elif inner_ratio <= 0.35:
            return {'direction': 'outer', 'strength': (0.5 - inner_ratio) * 2}
        else:
            return {'direction': 'neutral', 'strength': 0.0}

    def _get_historical_bias(self, track, condition, course_type):
        """過去データからバイアスを取得"""
        key = (track, condition, course_type)

        if key not in self.base_bias:
            return {'direction': 'neutral', 'strength': 0.0}

        data = self.base_bias[key]
        inner_rate = data.get('inner', {}).get('win_rate', 0.1)
        outer_rate = data.get('outer', {}).get('win_rate', 0.1)

        diff = inner_rate - outer_rate

        if diff > 0.03:
            return {'direction': 'inner', 'strength': min(diff * 5, 1.0)}
        elif diff < -0.03:
            return {'direction': 'outer', 'strength': min(-diff * 5, 1.0)}
        else:
            return {'direction': 'neutral', 'strength': 0.0}

    def calculate_bias_advantage(self, waku, bias_info):
        """枠番とバイアスから有利度を計算"""
        direction = bias_info['direction']
        strength = bias_info['strength']

        try:
            waku = int(waku)
        except:
            return 0.0

        if direction == 'neutral':
            return 0.0

        # 内枠有利の場合
        if direction == 'inner':
            if waku <= 2:
                return strength * 0.3
            elif waku <= 4:
                return strength * 0.15
            elif waku <= 6:
                return strength * -0.1
            else:
                return strength * -0.25

        # 外枠有利の場合
        if direction == 'outer':
            if waku >= 7:
                return strength * 0.3
            elif waku >= 5:
                return strength * 0.15
            elif waku >= 3:
                return strength * -0.1
            else:
                return strength * -0.25

        return 0.0


class WeatherImpactAnalyzer:
    """天気×馬場状態×血統の相性分析"""

    # 重馬場・不良馬場に強い血統（過去実績ベース）
    HEAVY_TRACK_SIRES = {
        'ゴールドアリュール', 'キングカメハメハ', 'クロフネ', 'サウスヴィグラス',
        'ダイワメジャー', 'パイロ', 'ヘニーヒューズ', 'マジェスティックウォリアー',
        'ホッコータルマエ', 'エスポワールシチー', 'カネヒキリ', 'スマートファルコン',
        'コパノリッキー', 'ドゥラメンテ', 'ルーラーシップ', 'ロードカナロア'
    }

    # 良馬場専用型（道悪苦手）
    GOOD_TRACK_ONLY_SIRES = {
        'ディープインパクト', 'ハーツクライ', 'ステイゴールド', 'キズナ',
        'エピファネイア', 'モーリス', 'リアルスティール'
    }

    def __init__(self, df_history):
        """過去データから天候別成績を学習"""
        self.sire_condition_stats = self._calculate_sire_condition_stats(df_history)

    def _calculate_sire_condition_stats(self, df):
        """血統×馬場状態の成績を計算"""
        stats = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'runs': 0, 'top3': 0}))

        rank_col = 'Rank' if 'Rank' in df.columns else '着順'

        for _, row in df.iterrows():
            father = row.get('father', '')
            condition = row.get('track_condition', '')

            if not father or not condition:
                continue

            try:
                rank = int(row.get(rank_col, 99))
            except:
                continue

            # 馬場状態をカテゴリ化
            if condition in ['良', '稍重']:
                cond_cat = 'good'
            else:  # 重, 不良
                cond_cat = 'heavy'

            stats[father][cond_cat]['runs'] += 1
            if rank == 1:
                stats[father][cond_cat]['wins'] += 1
            if rank <= 3:
                stats[father][cond_cat]['top3'] += 1

        # 比率計算
        result = {}
        for father, cond_data in stats.items():
            result[father] = {}
            for cond, data in cond_data.items():
                if data['runs'] >= 30:
                    result[father][cond] = {
                        'win_rate': data['wins'] / data['runs'],
                        'top3_rate': data['top3'] / data['runs'],
                        'runs': data['runs']
                    }
        return result

    def get_weather_condition_score(self, father, mother_father, track_condition, weather):
        """天気×馬場×血統から適性スコアを計算"""
        score = 0.0

        # 馬場状態判定
        is_heavy = track_condition in ['重', '不良']
        is_soft = track_condition == '稍重'

        # 天気判定（雨なら今後悪化の可能性）
        is_rainy = weather in ['雨', '小雨', '大雨']

        # 父の馬場適性
        if father:
            if is_heavy:
                if father in self.HEAVY_TRACK_SIRES:
                    score += 0.25
                elif father in self.GOOD_TRACK_ONLY_SIRES:
                    score -= 0.25

                # 過去データからの適性
                if father in self.sire_condition_stats:
                    heavy_data = self.sire_condition_stats[father].get('heavy', {})
                    good_data = self.sire_condition_stats[father].get('good', {})

                    if heavy_data and good_data:
                        heavy_rate = heavy_data.get('top3_rate', 0.2)
                        good_rate = good_data.get('top3_rate', 0.2)
                        diff = heavy_rate - good_rate
                        score += diff * 2  # 差をスケーリング

            elif not is_heavy and not is_soft:  # 良馬場
                if father in self.GOOD_TRACK_ONLY_SIRES:
                    score += 0.1
                elif father in self.HEAVY_TRACK_SIRES:
                    score -= 0.05  # 良馬場でも極端に不利ではない

        # 母父も考慮（影響は半分）
        if mother_father:
            if is_heavy:
                if mother_father in self.HEAVY_TRACK_SIRES:
                    score += 0.12
                elif mother_father in self.GOOD_TRACK_ONLY_SIRES:
                    score -= 0.12
            elif not is_heavy and not is_soft:
                if mother_father in self.GOOD_TRACK_ONLY_SIRES:
                    score += 0.05

        # 雨天時の追加調整
        if is_rainy and is_soft:
            # 稍重+雨=悪化傾向、道悪得意が有利に
            if father in self.HEAVY_TRACK_SIRES:
                score += 0.1

        return max(-0.5, min(0.5, score))


class EnhancedPacePredictor:
    """強化版展開予測"""

    def __init__(self, df_history):
        """過去データから脚質・展開パターンを学習"""
        self.horse_styles = self._calculate_horse_styles(df_history)
        self.pace_results = self._calculate_pace_results(df_history)

    def _calculate_horse_styles(self, df):
        """各馬の詳細な脚質を計算"""
        styles = {}

        # horse_idでグループ化
        if 'horse_id' not in df.columns:
            return styles

        grouped = df.groupby('horse_id')

        for horse_id, group in grouped:
            if pd.isna(horse_id):
                continue

            # 平均通過位置から脚質判定
            avg_pos = group['avg_passage_position'].mean() if 'avg_passage_position' in group.columns else None

            if pd.notna(avg_pos):
                if avg_pos <= 2.5:
                    style = 'escaper'      # 逃げ
                    aggression = 0.9
                elif avg_pos <= 4.5:
                    style = 'front'        # 先行
                    aggression = 0.6
                elif avg_pos <= 7.0:
                    style = 'stalker'      # 差し
                    aggression = 0.3
                else:
                    style = 'closer'       # 追込
                    aggression = 0.1
            else:
                style = 'unknown'
                aggression = 0.4

            # 逃げの実績（1角1番手率）
            escape_attempts = 0
            total_races = len(group)

            styles[horse_id] = {
                'style': style,
                'aggression': aggression,  # 前に行きたがる度合い
                'avg_position': avg_pos if pd.notna(avg_pos) else 5.0,
                'races': total_races
            }

        return styles

    def _calculate_pace_results(self, df):
        """ペース別の脚質別成績を計算"""
        # 簡易実装：逃げ馬の数と勝率の関係
        return {}

    def analyze_race_pace(self, race_horses):
        """レースの展開を詳細分析"""
        escapers = []      # 逃げ馬
        front_runners = [] # 先行馬
        stalkers = []      # 差し馬
        closers = []       # 追込馬

        for horse in race_horses:
            horse_id = horse.get('horse_id')
            if horse_id and horse_id in self.horse_styles:
                style_info = self.horse_styles[horse_id]
                style = style_info['style']

                entry = {
                    'horse_id': horse_id,
                    'name': horse.get('name', ''),
                    'waku': horse.get('waku', 0),
                    'aggression': style_info['aggression']
                }

                if style == 'escaper':
                    escapers.append(entry)
                elif style == 'front':
                    front_runners.append(entry)
                elif style == 'stalker':
                    stalkers.append(entry)
                else:
                    closers.append(entry)

        num_horses = len(race_horses)

        # 展開分析
        analysis = {
            'escapers_count': len(escapers),
            'front_count': len(front_runners),
            'stalker_count': len(stalkers),
            'closer_count': len(closers),
            'pace_prediction': 'medium',
            'front_competition': 'normal',
            'escape_success_prob': 0.5
        }

        # ペース予測
        total_front = len(escapers) + len(front_runners)
        front_ratio = total_front / max(num_horses, 1)

        if len(escapers) >= 3 or front_ratio >= 0.4:
            analysis['pace_prediction'] = 'high'
            analysis['front_competition'] = 'intense'
            analysis['escape_success_prob'] = 0.2
        elif len(escapers) == 0:
            analysis['pace_prediction'] = 'slow'
            analysis['front_competition'] = 'none'
            analysis['escape_success_prob'] = 0.0
        elif len(escapers) == 1 and len(front_runners) <= 2:
            analysis['pace_prediction'] = 'slow'
            analysis['front_competition'] = 'low'
            analysis['escape_success_prob'] = 0.7
        elif len(escapers) == 2:
            analysis['pace_prediction'] = 'medium_high'
            analysis['front_competition'] = 'moderate'
            analysis['escape_success_prob'] = 0.4

        # 内枠に逃げ馬がいるかチェック
        inner_escaper = any(e['waku'] <= 3 for e in escapers) if escapers else False
        if inner_escaper and len(escapers) == 1:
            analysis['escape_success_prob'] += 0.15

        return analysis

    def calculate_pace_advantage(self, horse_id, pace_analysis):
        """各馬のペースに対する有利度を計算"""
        if horse_id not in self.horse_styles:
            return 0.0

        style_info = self.horse_styles[horse_id]
        style = style_info['style']
        pace = pace_analysis['pace_prediction']
        competition = pace_analysis['front_competition']

        advantage = 0.0

        # ペースと脚質の相性
        if pace == 'high':
            if style == 'escaper':
                advantage = -0.35 if competition == 'intense' else -0.2
            elif style == 'front':
                advantage = -0.15
            elif style == 'stalker':
                advantage = 0.15
            else:  # closer
                advantage = 0.25

        elif pace == 'slow':
            if style == 'escaper':
                advantage = 0.35 if competition == 'low' else 0.2
            elif style == 'front':
                advantage = 0.2
            elif style == 'stalker':
                advantage = -0.1
            else:  # closer
                advantage = -0.3

        elif pace == 'medium_high':
            if style == 'escaper':
                advantage = -0.15
            elif style == 'stalker':
                advantage = 0.1
            elif style == 'closer':
                advantage = 0.15

        # 先行争いが激しい場合、差し追込に追加ボーナス
        if competition == 'intense':
            if style in ['stalker', 'closer']:
                advantage += 0.1

        return advantage


class DistanceAptitudeAnalyzer:
    """距離適性分析"""

    def __init__(self, df_history):
        self.horse_distance_stats = self._calculate_distance_stats(df_history)
        self.sire_distance_stats = self._calculate_sire_distance_stats(df_history)

    def _calculate_distance_stats(self, df):
        """各馬の距離別成績"""
        stats = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'runs': 0, 'top3': 0}))

        rank_col = 'Rank' if 'Rank' in df.columns else '着順'

        for _, row in df.iterrows():
            horse_id = row.get('horse_id')
            distance = row.get('distance')

            if pd.isna(horse_id) or pd.isna(distance):
                continue

            try:
                rank = int(row.get(rank_col, 99))
                distance = int(distance)
            except:
                continue

            # 距離カテゴリ
            if distance <= 1400:
                dist_cat = 'sprint'
            elif distance <= 1800:
                dist_cat = 'mile'
            elif distance <= 2200:
                dist_cat = 'intermediate'
            else:
                dist_cat = 'long'

            stats[horse_id][dist_cat]['runs'] += 1
            if rank == 1:
                stats[horse_id][dist_cat]['wins'] += 1
            if rank <= 3:
                stats[horse_id][dist_cat]['top3'] += 1

        result = {}
        for horse_id, dist_data in stats.items():
            result[horse_id] = {}
            for dist_cat, data in dist_data.items():
                if data['runs'] >= 2:
                    result[horse_id][dist_cat] = {
                        'win_rate': data['wins'] / data['runs'],
                        'top3_rate': data['top3'] / data['runs'],
                        'runs': data['runs']
                    }
        return result

    def _calculate_sire_distance_stats(self, df):
        """種牡馬の距離別成績"""
        stats = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'runs': 0}))

        rank_col = 'Rank' if 'Rank' in df.columns else '着順'

        for _, row in df.iterrows():
            father = row.get('father')
            distance = row.get('distance')

            if not father or pd.isna(distance):
                continue

            try:
                rank = int(row.get(rank_col, 99))
                distance = int(distance)
            except:
                continue

            if distance <= 1400:
                dist_cat = 'sprint'
            elif distance <= 1800:
                dist_cat = 'mile'
            elif distance <= 2200:
                dist_cat = 'intermediate'
            else:
                dist_cat = 'long'

            stats[father][dist_cat]['runs'] += 1
            if rank == 1:
                stats[father][dist_cat]['wins'] += 1

        result = {}
        for father, dist_data in stats.items():
            result[father] = {}
            for dist_cat, data in dist_data.items():
                if data['runs'] >= 50:
                    result[father][dist_cat] = data['wins'] / data['runs']
        return result

    def get_distance_aptitude(self, horse_id, father, distance):
        """距離適性スコアを計算"""
        try:
            distance = int(distance)
        except:
            return 0.0

        if distance <= 1400:
            dist_cat = 'sprint'
        elif distance <= 1800:
            dist_cat = 'mile'
        elif distance <= 2200:
            dist_cat = 'intermediate'
        else:
            dist_cat = 'long'

        score = 0.0

        # 馬自身の実績
        if horse_id in self.horse_distance_stats:
            horse_data = self.horse_distance_stats[horse_id]
            if dist_cat in horse_data:
                rate = horse_data[dist_cat]['top3_rate']
                # 平均複勝率22%との比較
                score += (rate - 0.22) * 2
            else:
                # この距離経験なし→少しマイナス
                score -= 0.05

        # 血統からの距離適性
        if father in self.sire_distance_stats:
            sire_data = self.sire_distance_stats[father]
            if dist_cat in sire_data:
                sire_rate = sire_data[dist_cat]
                avg_rate = 0.065  # 平均勝率
                score += (sire_rate - avg_rate) * 3

        return max(-0.4, min(0.4, score))


def calculate_v4_features(horse_data, race_info, race_horses,
                          track_bias_analyzer, weather_analyzer,
                          pace_predictor, distance_analyzer):
    """V4特徴量を一括計算"""

    features = {}

    horse_id = horse_data.get('horse_id')
    father = horse_data.get('father', '')
    mother_father = horse_data.get('mother_father', '')
    waku = horse_data.get('waku', 4)

    track = race_info.get('track_name', '')
    condition = race_info.get('track_condition', '良')
    weather = race_info.get('weather', '晴')
    course_type = race_info.get('course_type', '')
    distance = race_info.get('distance', 1600)

    # 1. 馬場バイアス
    bias_info = track_bias_analyzer.get_realtime_bias(track, condition, course_type)
    bias_advantage = track_bias_analyzer.calculate_bias_advantage(waku, bias_info)
    features['track_bias_advantage'] = bias_advantage
    features['track_bias_inner'] = 1 if bias_info['direction'] == 'inner' else 0
    features['track_bias_outer'] = 1 if bias_info['direction'] == 'outer' else 0
    features['track_bias_strength'] = bias_info['strength']

    # 2. 天気×馬場×血統
    weather_score = weather_analyzer.get_weather_condition_score(
        father, mother_father, condition, weather
    )
    features['weather_bloodline_score'] = weather_score
    features['is_heavy_track'] = 1 if condition in ['重', '不良'] else 0
    features['is_rainy'] = 1 if weather in ['雨', '小雨', '大雨'] else 0

    # 3. 展開予測
    pace_analysis = pace_predictor.analyze_race_pace(race_horses)
    pace_advantage = pace_predictor.calculate_pace_advantage(horse_id, pace_analysis)

    features['pace_advantage'] = pace_advantage
    features['escapers_count'] = pace_analysis['escapers_count']
    features['predicted_pace_high'] = 1 if pace_analysis['pace_prediction'] == 'high' else 0
    features['predicted_pace_slow'] = 1 if pace_analysis['pace_prediction'] == 'slow' else 0
    features['front_competition_intense'] = 1 if pace_analysis['front_competition'] == 'intense' else 0
    features['escape_success_prob'] = pace_analysis['escape_success_prob']

    # 4. 距離適性
    distance_score = distance_analyzer.get_distance_aptitude(horse_id, father, distance)
    features['distance_aptitude'] = distance_score

    return features


# テスト
if __name__ == '__main__':
    print("Feature Engineering V4")
    print("実装済み特徴量:")
    print("  - 当日馬場バイアス（リアルタイム更新対応）")
    print("  - 天気×馬場×血統の相性")
    print("  - 展開予測強化（逃げ馬競合分析）")
    print("  - 距離適性（馬・血統両面）")
