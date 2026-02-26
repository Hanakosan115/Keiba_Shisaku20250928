"""
Feature Engineering V3
新規特徴量:
1. ペース予測（レース展開）
2. コース・枠バイアス
3. フォームサイクル（間隔適性）
"""

import pandas as pd
import numpy as np
from collections import defaultdict


class PacePredictor:
    """ペース予測: レースの展開を予測して各馬の有利不利を計算"""

    def __init__(self, df_history):
        """過去データから脚質分布を学習"""
        self.running_style_stats = self._calculate_running_style_stats(df_history)

    def _calculate_running_style_stats(self, df):
        """各馬の脚質を計算 - ベクトル化処理で高速化"""
        styles = {}

        # running_style_categoryから脚質マッピング
        style_mapping = {
            'front_runner': 'front',
            'stalker': 'stalker',
            'midpack': 'closer',
            'closer': 'late'
        }

        # 方法1: running_style_categoryカラムがある場合
        if 'running_style_category' in df.columns:
            valid_df = df[df['horse_id'].notna() & df['running_style_category'].notna()].copy()

            if len(valid_df) > 0:
                grouped = valid_df.groupby('horse_id').agg({
                    'running_style_category': lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else x.iloc[-1],
                    'avg_passage_position': 'mean'
                }).reset_index()

                for _, row in grouped.iterrows():
                    horse_id = row['horse_id']
                    style_raw = row['running_style_category']
                    style = style_mapping.get(style_raw, 'closer')
                    avg_first = row['avg_passage_position'] if pd.notna(row['avg_passage_position']) else 5.0

                    styles[horse_id] = {
                        'style': style,
                        'avg_first_position': avg_first
                    }

        # 方法2: Passageカラムから計算（'5-5', '3-3-2-1' 形式）
        passage_col = 'Passage' if 'Passage' in df.columns else '通過' if '通過' in df.columns else None
        if passage_col and len(styles) == 0:
            def get_first_position(passage):
                try:
                    if pd.isna(passage):
                        return None
                    parts = str(passage).split('-')
                    if len(parts) > 0:
                        return int(parts[0])
                except:
                    pass
                return None

            df_copy = df[df['horse_id'].notna()].copy()
            df_copy['first_pos'] = df_copy[passage_col].apply(get_first_position)
            valid_df = df_copy[df_copy['first_pos'].notna()]

            if len(valid_df) > 0:
                grouped = valid_df.groupby('horse_id')['first_pos'].mean().reset_index()
                grouped.columns = ['horse_id', 'avg_first']

                for _, row in grouped.iterrows():
                    horse_id = row['horse_id']
                    avg_first = row['avg_first']

                    # 脚質分類: 1-2=逃げ, 3-5=先行, 6-10=差し, 11+=追込
                    if avg_first <= 2:
                        style = 'front'
                    elif avg_first <= 5:
                        style = 'stalker'
                    elif avg_first <= 10:
                        style = 'closer'
                    else:
                        style = 'late'

                    styles[horse_id] = {
                        'style': style,
                        'avg_first_position': avg_first
                    }

        return styles

    def predict_pace(self, horse_ids, num_horses):
        """レースのペースを予測"""
        front_runners = 0
        stalkers = 0

        for hid in horse_ids:
            if hid in self.running_style_stats:
                style = self.running_style_stats[hid]['style']
                if style == 'front':
                    front_runners += 1
                elif style == 'stalker':
                    stalkers += 1

        # ペース予測ロジック
        front_ratio = front_runners / max(num_horses, 1)

        if front_runners >= 3 or front_ratio >= 0.2:
            return 'high'  # ハイペース（差し有利）
        elif front_runners == 0:
            return 'slow'  # スローペース（逃げ先行有利）
        else:
            return 'medium'  # ミドルペース

    def calculate_pace_advantage(self, horse_id, predicted_pace):
        """ペースに対する有利度を計算"""
        if horse_id not in self.running_style_stats:
            return 0.0

        style = self.running_style_stats[horse_id]['style']

        # ペースと脚質の相性
        advantages = {
            ('high', 'front'): -0.3,    # ハイペースで逃げは不利
            ('high', 'stalker'): -0.1,  # ハイペースで先行やや不利
            ('high', 'closer'): 0.2,    # ハイペースで差し有利
            ('high', 'late'): 0.3,      # ハイペースで追込有利
            ('slow', 'front'): 0.3,     # スローで逃げ有利
            ('slow', 'stalker'): 0.2,   # スローで先行有利
            ('slow', 'closer'): -0.1,   # スローで差しやや不利
            ('slow', 'late'): -0.3,     # スローで追込不利
            ('medium', 'front'): 0.1,
            ('medium', 'stalker'): 0.1,
            ('medium', 'closer'): 0.0,
            ('medium', 'late'): -0.1,
        }

        return advantages.get((predicted_pace, style), 0.0)


class CourseBiasAnalyzer:
    """コース・枠バイアス分析"""

    def __init__(self, df_history):
        """過去データからバイアスを計算"""
        self.bias_data = self._calculate_bias(df_history)

    def _calculate_bias(self, df):
        """競馬場×距離×枠番×馬場状態ごとの勝率を計算"""
        bias = defaultdict(lambda: {'wins': 0, 'runs': 0})

        df = df.copy()
        # カラム名対応
        rank_col = 'Rank' if 'Rank' in df.columns else '着順'
        df['rank'] = pd.to_numeric(df[rank_col], errors='coerce')

        waku_col = 'Waku' if 'Waku' in df.columns else '枠番'
        for _, row in df.iterrows():
            track = row.get('track_name', '')
            try:
                distance = int(row.get('distance', 0))
            except:
                distance = 0
            waku = row.get(waku_col, '')
            condition = row.get('track_condition', '')
            rank = row.get('rank')

            if pd.isna(rank) or not track or not distance:
                continue

            try:
                waku_num = int(waku)
                # 内枠(1-3)、中枠(4-6)、外枠(7-8)に分類
                if waku_num <= 3:
                    waku_cat = 'inner'
                elif waku_num <= 6:
                    waku_cat = 'middle'
                else:
                    waku_cat = 'outer'
            except:
                continue

            # 距離カテゴリ
            if distance <= 1400:
                dist_cat = 'sprint'
            elif distance <= 1800:
                dist_cat = 'mile'
            elif distance <= 2200:
                dist_cat = 'middle'
            else:
                dist_cat = 'long'

            key = (track, dist_cat, waku_cat, condition)
            bias[key]['runs'] += 1
            if rank == 1:
                bias[key]['wins'] += 1

        # 勝率計算
        result = {}
        for key, data in bias.items():
            if data['runs'] >= 30:  # 最低30レース
                result[key] = data['wins'] / data['runs']

        return result

    def get_gate_advantage(self, track, distance, waku, condition):
        """枠番の有利度を取得"""
        try:
            waku_num = int(waku)
            if waku_num <= 3:
                waku_cat = 'inner'
            elif waku_num <= 6:
                waku_cat = 'middle'
            else:
                waku_cat = 'outer'
        except:
            return 0.0

        try:
            distance = int(distance)
        except:
            return 0.0

        if distance <= 1400:
            dist_cat = 'sprint'
        elif distance <= 1800:
            dist_cat = 'mile'
        elif distance <= 2200:
            dist_cat = 'middle'
        else:
            dist_cat = 'long'

        key = (track, dist_cat, waku_cat, condition)

        if key in self.bias_data:
            # 平均勝率との差を返す（平均約6.5%）
            return (self.bias_data[key] - 0.065) * 10  # スケーリング

        return 0.0


class FormCycleAnalyzer:
    """フォームサイクル分析: 休養間隔による成績変化"""

    def __init__(self, df_history):
        """過去データから間隔適性を学習"""
        self.interval_stats = self._calculate_interval_stats(df_history)

    def _calculate_interval_stats(self, df):
        """各馬の間隔別成績を計算"""
        stats = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'runs': 0, 'top3': 0}))

        df = df.copy()
        # カラム名対応
        rank_col = 'Rank' if 'Rank' in df.columns else '着順'
        df['rank'] = pd.to_numeric(df[rank_col], errors='coerce')
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.sort_values(['horse_id', 'date'])

        prev_date = {}

        for _, row in df.iterrows():
            horse_id = row.get('horse_id')
            date = row.get('date')
            rank = row.get('rank')

            if pd.isna(horse_id) or pd.isna(date) or pd.isna(rank):
                continue

            if horse_id in prev_date:
                days = (date - prev_date[horse_id]).days

                # 間隔カテゴリ
                if days <= 14:
                    interval_cat = 'short'  # 中1-2週
                elif days <= 35:
                    interval_cat = 'normal'  # 中3-4週
                elif days <= 70:
                    interval_cat = 'refresh'  # 中5-9週
                else:
                    interval_cat = 'long'  # 中10週以上

                stats[horse_id][interval_cat]['runs'] += 1
                if rank == 1:
                    stats[horse_id][interval_cat]['wins'] += 1
                if rank <= 3:
                    stats[horse_id][interval_cat]['top3'] += 1

            prev_date[horse_id] = date

        # 各馬の最適間隔を計算
        result = {}
        for horse_id, intervals in stats.items():
            best_interval = None
            best_rate = 0
            for interval_cat, data in intervals.items():
                if data['runs'] >= 3:  # 最低3レース
                    rate = data['top3'] / data['runs']
                    if rate > best_rate:
                        best_rate = rate
                        best_interval = interval_cat

            if best_interval:
                result[horse_id] = {
                    'best_interval': best_interval,
                    'intervals': dict(intervals)
                }

        return result

    def get_interval_advantage(self, horse_id, days_since_last):
        """現在の間隔での有利度を計算"""
        if horse_id not in self.interval_stats:
            return 0.0

        # 現在の間隔カテゴリ
        if days_since_last <= 14:
            current_interval = 'short'
        elif days_since_last <= 35:
            current_interval = 'normal'
        elif days_since_last <= 70:
            current_interval = 'refresh'
        else:
            current_interval = 'long'

        horse_stats = self.interval_stats[horse_id]
        best_interval = horse_stats['best_interval']

        # 最適間隔との一致度
        if current_interval == best_interval:
            return 0.2  # 最適間隔

        # 間隔データがあれば、その間隔での成績から計算
        intervals = horse_stats['intervals']
        if current_interval in intervals:
            data = intervals[current_interval]
            if data['runs'] >= 2:
                rate = data['top3'] / data['runs']
                return (rate - 0.22) * 2  # 平均複勝率22%との差をスケーリング

        return 0.0


def calculate_v3_features(horse_id, race_horses, race_info, df_history,
                          pace_predictor, bias_analyzer, form_analyzer):
    """V3特徴量を計算"""
    features = {}

    # 1. ペース予測
    horse_ids = [h.get('horse_id') for h in race_horses if h.get('horse_id')]
    predicted_pace = pace_predictor.predict_pace(horse_ids, len(race_horses))
    pace_advantage = pace_predictor.calculate_pace_advantage(horse_id, predicted_pace)

    features['predicted_pace_high'] = 1 if predicted_pace == 'high' else 0
    features['predicted_pace_slow'] = 1 if predicted_pace == 'slow' else 0
    features['pace_advantage'] = pace_advantage

    # 2. コース・枠バイアス
    track = race_info.get('track_name', '')
    distance = race_info.get('distance', 1600)
    waku = race_info.get('waku', '')
    condition = race_info.get('track_condition', '')

    gate_advantage = bias_analyzer.get_gate_advantage(track, distance, waku, condition)
    features['gate_bias_advantage'] = gate_advantage

    # 3. フォームサイクル
    days_since_last = race_info.get('days_since_last', 30)
    interval_advantage = form_analyzer.get_interval_advantage(horse_id, days_since_last)
    features['interval_advantage'] = interval_advantage

    return features


# 使用例
if __name__ == '__main__':
    print("Feature Engineering V3")
    print("新規特徴量: ペース予測、コースバイアス、フォームサイクル")
