"""
特徴量エンジニアリング
馬ごとに31の特徴量を抽出
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class FeatureEngineer:
    def __init__(self, df):
        """
        Args:
            df: 全レースデータ
        """
        self.df = df
        self.df['date_parsed'] = pd.to_datetime(self.df['date'], errors='coerce')

    def extract_features_for_race(self, race_id, race_horses):
        """
        レースの全馬の特徴量を抽出

        Args:
            race_id: レースID
            race_horses: 当該レースの馬データ (DataFrame)

        Returns:
            DataFrame: 特徴量付きデータ
        """
        features_list = []

        for _, horse in race_horses.iterrows():
            features = self._extract_horse_features(horse, race_id)
            features_list.append(features)

        return pd.DataFrame(features_list)

    def _extract_horse_features(self, horse, race_id):
        """
        1頭の馬の特徴量を抽出
        """
        horse_id = horse.get('horse_id', None)
        umaban = horse.get('Umaban', 0)

        features = {
            'race_id': race_id,
            'horse_id': horse_id,
            'umaban': umaban,
        }

        # ========================================
        # 基本情報
        # ========================================

        # 1. 年齢
        age = horse.get('Age', None)
        features['age'] = age if pd.notna(age) else 4

        # 2. 性別
        sex = horse.get('Sex', None)
        features['is_male'] = 1 if sex == '牡' else 0
        features['is_female'] = 1 if sex == '牝' else 0
        features['is_gelding'] = 1 if sex == 'セ' else 0

        # 3. 馬体重変化
        weight_diff = horse.get('WeightDiff', None)
        features['weight_diff'] = weight_diff if pd.notna(weight_diff) else 0

        # 4. 斤量
        load = horse.get('Load', None)
        features['load'] = load if pd.notna(load) else 56

        # 5. オッズ（対数変換）
        odds = horse.get('Odds', None)
        if pd.notna(odds) and odds > 0:
            features['log_odds'] = np.log1p(odds)
        else:
            features['log_odds'] = np.log1p(5.0)

        # 6. 人気
        ninki = horse.get('Ninki', None)
        features['ninki'] = ninki if pd.notna(ninki) else 8

        # 7. 枠番
        waku = horse.get('Waku', None)
        features['waku'] = waku if pd.notna(waku) else umaban

        # ========================================
        # レース条件
        # ========================================

        # 8. 距離
        distance = horse.get('distance', None)
        features['distance'] = distance if pd.notna(distance) else 1600

        # 9. コースタイプ（芝=1, ダート=0）
        course_type = horse.get('course_type', None)
        features['is_turf'] = 1 if course_type == '芝' else 0

        # 10. 馬場状態（良=0, 稍重=1, 重=2, 不良=3）
        track_condition = horse.get('track_condition', '良')
        track_map = {'良': 0, '稍': 1, '稍重': 1, '重': 2, '不良': 3}
        features['track_condition'] = track_map.get(track_condition, 0)

        # ========================================
        # 過去成績（近3走）
        # ========================================

        if horse_id:
            past_races = self._get_past_races(horse_id, race_id, n=3)

            if len(past_races) > 0:
                # 11-13. 近3走の着順
                for i in range(3):
                    if i < len(past_races):
                        rank = past_races.iloc[i].get('Rank', None)
                        features[f'past_rank_{i+1}'] = rank if pd.notna(rank) else 10
                    else:
                        features[f'past_rank_{i+1}'] = 10

                # 14. 平均着順
                ranks = [past_races.iloc[i].get('Rank', 10) for i in range(min(3, len(past_races)))]
                ranks = [r for r in ranks if pd.notna(r)]
                features['avg_rank_3races'] = np.mean(ranks) if len(ranks) > 0 else 10

                # 15. 最高着順
                features['best_rank_3races'] = min(ranks) if len(ranks) > 0 else 10

                # 16. 連対率（1-2着の割合）
                top2_count = sum([1 for r in ranks if r <= 2])
                features['top2_rate_3races'] = top2_count / len(ranks) if len(ranks) > 0 else 0

                # 17. 前走着順
                features['last_rank'] = past_races.iloc[0].get('Rank', 10) if len(past_races) > 0 else 10

                # 18. 前走からの日数
                last_date = past_races.iloc[0].get('date_parsed', None) if len(past_races) > 0 else None
                current_date = horse.get('date_parsed', None)
                if pd.notna(last_date) and pd.notna(current_date):
                    try:
                        # 日付の引き算（datetimeオブジェクトであることを確認）
                        days_since_last = (pd.to_datetime(current_date) - pd.to_datetime(last_date)).days
                        features['days_since_last_race'] = days_since_last
                    except (TypeError, AttributeError, ValueError):
                        features['days_since_last_race'] = 90
                else:
                    features['days_since_last_race'] = 90

                # 19. 脚質判定（通過順位から推定）
                running_style = self._estimate_running_style(past_races)
                features['running_style'] = running_style  # 0=逃げ, 1=先行, 2=差し, 3=追込

            else:
                # 過去データなし（新馬など）
                for i in range(3):
                    features[f'past_rank_{i+1}'] = 10
                features['avg_rank_3races'] = 10
                features['best_rank_3races'] = 10
                features['top2_rate_3races'] = 0
                features['last_rank'] = 10
                features['days_since_last_race'] = 90
                features['running_style'] = 2  # デフォルト=差し
        else:
            # horse_idなし
            for i in range(3):
                features[f'past_rank_{i+1}'] = 10
            features['avg_rank_3races'] = 10
            features['best_rank_3races'] = 10
            features['top2_rate_3races'] = 0
            features['last_rank'] = 10
            features['days_since_last_race'] = 90
            features['running_style'] = 2

        # ========================================
        # 騎手情報
        # ========================================

        jockey = horse.get('JockeyName', None)
        if jockey:
            jockey_stats = self._get_jockey_stats(jockey)

            # 20. 騎手勝率
            features['jockey_win_rate'] = jockey_stats.get('win_rate', 0.05)

            # 21. 騎手連対率
            features['jockey_top2_rate'] = jockey_stats.get('top2_rate', 0.15)
        else:
            features['jockey_win_rate'] = 0.05
            features['jockey_top2_rate'] = 0.15

        # ========================================
        # コース適性
        # ========================================

        if horse_id:
            # 22. 当該コースでの勝率
            course_stats = self._get_course_stats(horse_id, course_type, distance)
            features['course_win_rate'] = course_stats.get('win_rate', 0)

            # 23. 距離適性（±200m以内での成績）
            distance_stats = self._get_distance_stats(horse_id, distance)
            features['distance_win_rate'] = distance_stats.get('win_rate', 0)
        else:
            features['course_win_rate'] = 0
            features['distance_win_rate'] = 0

        # ========================================
        # その他
        # ========================================

        # 24-31. 血統情報（簡易版）
        father = horse.get('father', None)
        mother_father = horse.get('mother_father', None)

        # トップサイアーかどうか（簡易判定）
        top_sires = ['ディープインパクト', 'キングカメハメハ', 'ハーツクライ',
                     'ロードカナロア', 'オルフェーヴル', 'ドゥラメンテ']
        features['is_top_sire'] = 1 if father in top_sires else 0

        # 追加の特徴量（ダミー）
        features['feature_24'] = 0
        features['feature_25'] = 0
        features['feature_26'] = 0
        features['feature_27'] = 0
        features['feature_28'] = 0
        features['feature_29'] = 0
        features['feature_30'] = 0
        features['feature_31'] = 0

        return features

    def _get_past_races(self, horse_id, current_race_id, n=3):
        """過去n走を取得"""
        # 当該馬の全レースを取得（horse_idの型を合わせる - CSVは文字列）
        horse_id_str = str(int(horse_id)) if pd.notna(horse_id) else None
        if horse_id_str is None:
            return pd.DataFrame()

        horse_races = self.df[self.df['horse_id'] == horse_id_str].copy()

        # デバッグ: この馬のレース数
        if len(horse_races) == 0:
            print(f"    [past_races] horse_id={horse_id}: 履歴なし（0件）")
            return pd.DataFrame()
        else:
            print(f"    [past_races] horse_id={horse_id}: 履歴{len(horse_races)}件")

        # 現在のレースより前（race_idの型を合わせる）
        current_race = self.df[self.df['race_id'] == str(current_race_id)]
        if len(current_race) > 0:
            current_date = current_race.iloc[0].get('date_parsed', None)
            if pd.notna(current_date):
                before_filter = len(horse_races)
                horse_races = horse_races[horse_races['date_parsed'] < current_date]
                print(f"    [past_races] 日付フィルタ後: {len(horse_races)}件（{current_date}より前）")

        # 日付順にソート（新しい順）
        horse_races = horse_races.sort_values('date_parsed', ascending=False)

        result = horse_races.head(n)
        print(f"    [past_races] 最終結果: {len(result)}件")
        return result

    def _estimate_running_style(self, past_races):
        """脚質を推定（通過順位から）"""
        if len(past_races) == 0:
            return 2  # デフォルト=差し

        # 通過順位を解析（改善版：複数レースの平均を取る）
        # Passage列: "5-5" や "11-11" のような形式

        first_positions = []  # 最初のコーナーでの位置を収集

        for _, race in past_races.iterrows():
            passage = race.get('Passage', '')
            if pd.notna(passage) and passage:
                try:
                    # 最初の通過順位を取得
                    positions = str(passage).split('-')
                    if len(positions) > 0 and positions[0].isdigit():
                        first_pos = int(positions[0])
                        first_positions.append(first_pos)
                except:
                    pass

        # 平均位置を計算
        if len(first_positions) > 0:
            avg_position = sum(first_positions) / len(first_positions)
        else:
            avg_position = 8  # デフォルト

        # 脚質判定（平均位置に基づく）
        if avg_position <= 2.5:
            return 0  # 逃げ
        elif avg_position <= 5.0:
            return 1  # 先行
        elif avg_position <= 9.0:
            return 2  # 差し
        else:
            return 3  # 追込

    def _get_jockey_stats(self, jockey_name):
        """騎手の統計"""
        jockey_races = self.df[self.df['JockeyName'] == jockey_name]

        if len(jockey_races) == 0:
            return {'win_rate': 0.05, 'top2_rate': 0.15}

        total = len(jockey_races)
        wins = len(jockey_races[jockey_races['Rank'] == 1])
        top2 = len(jockey_races[jockey_races['Rank'] <= 2])

        return {
            'win_rate': wins / total if total > 0 else 0.05,
            'top2_rate': top2 / total if total > 0 else 0.15,
        }

    def _get_course_stats(self, horse_id, course_type, distance):
        """コース適性統計"""
        # horse_idの型を合わせる
        horse_id_str = str(int(horse_id)) if pd.notna(horse_id) else None
        if horse_id_str is None:
            return {'win_rate': 0}

        horse_races = self.df[
            (self.df['horse_id'] == horse_id_str) &
            (self.df['course_type'] == course_type)
        ]

        if len(horse_races) == 0:
            return {'win_rate': 0}

        wins = len(horse_races[horse_races['Rank'] == 1])

        return {'win_rate': wins / len(horse_races)}

    def _get_distance_stats(self, horse_id, target_distance):
        """距離適性統計"""
        if pd.isna(target_distance):
            return {'win_rate': 0}

        # target_distanceを数値型に変換（念のため）
        try:
            target_distance = float(target_distance)
        except (ValueError, TypeError):
            return {'win_rate': 0}

        # horse_idの型を合わせる
        horse_id_str = str(int(horse_id)) if pd.notna(horse_id) else None
        if horse_id_str is None:
            return {'win_rate': 0}

        # ±200m以内
        horse_races = self.df[
            (self.df['horse_id'] == horse_id_str) &
            (self.df['distance'].notna()) &
            (abs(pd.to_numeric(self.df['distance'], errors='coerce') - target_distance) <= 200)
        ]

        if len(horse_races) == 0:
            return {'win_rate': 0}

        wins = len(horse_races[horse_races['Rank'] == 1])

        return {'win_rate': wins / len(horse_races)}

def get_running_style_name(style_code):
    """脚質コードを名前に変換"""
    style_map = {0: '逃げ', 1: '先行', 2: '差し', 3: '追込'}
    return style_map.get(style_code, '差し')
