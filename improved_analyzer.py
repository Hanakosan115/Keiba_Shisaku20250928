"""
競馬分析ツール改善版
オッズ乖離度ベースの予測システム
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any

class ImprovedHorseAnalyzer:
    """
    改善版の競馬分析エンジン

    【設計思想】
    1. オッズを最重要の基準値とする
    2. AIは「市場の見落とし」を検出する役割
    3. 特徴量はシンプルに（15-20個）
    4. 前走との条件比較を重視
    """

    def __init__(self):
        # 統計データ（既存のデータ構造を活用）
        self.jockey_stats = {}
        self.father_stats = {}
        self.gate_stats = {}
        self.course_stats = {}

    def calculate_simplified_features(self, horse_details: Dict, race_conditions: Dict) -> Dict:
        """
        【改善版】シンプルで効果的な特徴量のみを計算

        特徴量リスト（約15個）：
        1. オッズ（最重要）
        2. 人気
        3-5. 直近3走の着順
        6. 騎手実績
        7. 枠番
        8. 距離適性スコア
        9. 馬場適性スコア
        10. 斤量
        11. 前走からの間隔
        12. 馬体重変動
        13. 上がり3F（直近）
        14. 父の成績
        15. 前走との条件変化スコア
        """
        features = {}

        try:
            # ===== コア特徴量（必須） =====

            # 1-2. オッズと人気（最重要）
            # 既存コードとの互換性のため、OddsかOddsShutuba両方を試す
            odds_value = horse_details.get('OddsShutuba') or horse_details.get('Odds')
            features['odds'] = pd.to_numeric(odds_value, errors='coerce')

            ninki_value = horse_details.get('NinkiShutuba') or horse_details.get('Ninki')
            features['popularity'] = pd.to_numeric(ninki_value, errors='coerce')

            # オッズから期待勝率を計算
            if pd.notna(features['odds']) and features['odds'] > 0:
                features['odds_win_rate'] = 1.0 / features['odds']
            else:
                features['odds_win_rate'] = np.nan

            # 3. 基本情報
            features['age'] = pd.to_numeric(horse_details.get('Age'), errors='coerce')
            sex_map = {'牡': 0, '牝': 1, 'セ': 2}
            features['sex'] = sex_map.get(horse_details.get('Sex'), np.nan)
            features['weight'] = pd.to_numeric(horse_details.get('Load'), errors='coerce')
            features['gate'] = pd.to_numeric(horse_details.get('Waku'), errors='coerce')

            # 4-6. 直近3走の着順（シンプルに）
            race_results = horse_details.get('race_results', [])
            if not isinstance(race_results, list):
                race_results = []

            for i in range(3):
                if len(race_results) > i and isinstance(race_results[i], dict):
                    rank = pd.to_numeric(race_results[i].get('rank'), errors='coerce')
                    features[f'recent_rank_{i+1}'] = rank
                else:
                    features[f'recent_rank_{i+1}'] = np.nan

            # 直近成績の平均（安定性指標）
            recent_ranks = [features[f'recent_rank_{i+1}'] for i in range(3)]
            valid_ranks = [r for r in recent_ranks if pd.notna(r)]
            if valid_ranks:
                features['recent_rank_avg'] = np.mean(valid_ranks)
                features['recent_rank_std'] = np.std(valid_ranks) if len(valid_ranks) > 1 else 0
            else:
                features['recent_rank_avg'] = np.nan
                features['recent_rank_std'] = np.nan

            # 7. 前走からの間隔
            if race_results and isinstance(race_results[0], dict):
                current_date = pd.to_datetime(race_conditions.get('RaceDate'), errors='coerce')
                last_race_date = pd.to_datetime(race_results[0].get('date'), errors='coerce')
                if pd.notna(current_date) and pd.notna(last_race_date):
                    features['days_since_last'] = (current_date - last_race_date).days
                else:
                    features['days_since_last'] = np.nan
            else:
                features['days_since_last'] = np.nan

            # 8. 馬体重変動
            weight_diff = pd.to_numeric(horse_details.get('WeightDiff'), errors='coerce')
            features['weight_change'] = weight_diff

            # 9. 上がり3F（直近）
            if race_results and isinstance(race_results[0], dict):
                features['last_3f'] = pd.to_numeric(race_results[0].get('agari'), errors='coerce')
            else:
                features['last_3f'] = np.nan

            # ===== 条件適性の評価 =====

            # 10. 距離適性スコア
            current_distance = pd.to_numeric(race_conditions.get('Distance'), errors='coerce')
            features['distance_fitness'] = self._calculate_distance_fitness(
                race_results, current_distance
            )

            # 11. 馬場適性スコア
            current_condition = race_conditions.get('TrackCondition', '良')
            current_course_type = race_conditions.get('CourseType', '芝')
            features['track_fitness'] = self._calculate_track_fitness(
                race_results, current_condition, current_course_type
            )

            # 12. 前走との条件変化スコア（重要！穴馬発見に有効）
            features['condition_change_score'] = self._calculate_condition_change_score(
                race_results, race_conditions
            )

            # ===== 統計ベースの特徴量 =====

            # 13. 騎手実績
            jockey_name = horse_details.get('JockeyName')
            track_name = race_conditions.get('TrackName')
            course_type = race_conditions.get('CourseType')

            if jockey_name and track_name and course_type:
                jockey_key = (track_name, course_type)
                if jockey_name in self.jockey_stats:
                    jockey_data = self.jockey_stats[jockey_name].get(jockey_key, {})
                    features['jockey_win_rate'] = jockey_data.get('WinRate', 0.0)
                    features['jockey_place_rate'] = jockey_data.get('Place3Rate', 0.0)
                else:
                    features['jockey_win_rate'] = 0.0
                    features['jockey_place_rate'] = 0.0
            else:
                features['jockey_win_rate'] = 0.0
                features['jockey_place_rate'] = 0.0

            # 14. 父の成績（シンプルに）
            father = horse_details.get('father')
            if father and father in self.father_stats:
                # コース種別での成績のみ
                father_key = course_type
                father_data = self.father_stats[father].get(father_key, {})
                features['father_win_rate'] = father_data.get('WinRate', 0.0)
            else:
                features['father_win_rate'] = 0.0

            # 15. 枠番の有利不利
            if pd.notna(features['gate']) and track_name and course_type and pd.notna(current_distance):
                gate_key = (track_name, course_type, int(current_distance), int(features['gate']))
                if gate_key in self.gate_stats:
                    features['gate_advantage'] = self.gate_stats[gate_key].get('Place3Rate', 0.0)
                else:
                    features['gate_advantage'] = 0.0
            else:
                features['gate_advantage'] = 0.0

            # メタ情報
            features['horse_id'] = str(horse_details.get('horse_id', '')).split('.')[0]
            features['horse_name'] = horse_details.get('HorseName', '')

        except Exception as e:
            print(f"特徴量計算エラー: {e}")

        return features

    def _calculate_distance_fitness(self, race_results: List[Dict], current_distance: float) -> float:
        """
        距離適性スコアを計算

        ロジック：
        - 同距離での好走歴があれば高スコア
        - 距離が大きく変わる場合は低スコア
        """
        if pd.isna(current_distance) or not race_results:
            return 0.0

        score = 0.0
        count = 0

        for race in race_results[:5]:  # 直近5走
            if not isinstance(race, dict):
                continue

            past_distance = pd.to_numeric(race.get('distance'), errors='coerce')
            past_rank = pd.to_numeric(race.get('rank'), errors='coerce')

            if pd.isna(past_distance) or pd.isna(past_rank):
                continue

            # 距離差
            distance_diff = abs(current_distance - past_distance)

            # 同距離での好走は高評価
            if distance_diff <= 200:  # ±200m以内
                if past_rank <= 3:
                    score += 2.0
                elif past_rank <= 5:
                    score += 1.0
                count += 1

            # 距離変更のパターン評価
            elif distance_diff > 400:  # 大幅な距離変更
                # 長距離→短距離、短距離→長距離は減点
                score -= 0.5
                count += 1

        return score / count if count > 0 else 0.0

    def _calculate_track_fitness(self, race_results: List[Dict],
                                  current_condition: str, current_course_type: str) -> float:
        """
        馬場適性スコアを計算

        ロジック：
        - 同じ馬場状態・コース種別での好走歴を評価
        """
        if not race_results:
            return 0.0

        score = 0.0
        count = 0

        for race in race_results[:5]:
            if not isinstance(race, dict):
                continue

            past_condition = race.get('baba', '良')
            past_course_type = race.get('course_type', '芝')
            past_rank = pd.to_numeric(race.get('rank'), errors='coerce')

            if pd.isna(past_rank):
                continue

            # 同じコース種別での好走
            if past_course_type == current_course_type:
                if past_rank <= 3:
                    score += 1.5
                elif past_rank <= 5:
                    score += 0.5
                count += 1

            # 同じ馬場状態での好走
            if past_condition == current_condition:
                if past_rank <= 3:
                    score += 1.0
                count += 1

        return score / count if count > 0 else 0.0

    def _calculate_condition_change_score(self, race_results: List[Dict],
                                          race_conditions: Dict) -> float:
        """
        前走との条件変化スコアを計算

        【重要】これが穴馬発見のカギ！

        ロジック：
        - 不利な条件→有利な条件に変化 = プラス評価
        - 有利な条件→不利な条件に変化 = マイナス評価

        例：
        - 前走2400m惨敗 → 今回1800m = +2.0（距離短縮で復活の可能性）
        - 前走重馬場 → 今回良馬場 = +1.5（得意馬場に戻る）
        - 前走外枠 → 今回内枠 = +1.0（枠順改善）
        """
        if not race_results or not isinstance(race_results[0], dict):
            return 0.0

        score = 0.0
        last_race = race_results[0]

        # 1. 距離変更の評価
        current_distance = pd.to_numeric(race_conditions.get('Distance'), errors='coerce')
        last_distance = pd.to_numeric(last_race.get('distance'), errors='coerce')
        last_rank = pd.to_numeric(last_race.get('rank'), errors='coerce')

        if pd.notna(current_distance) and pd.notna(last_distance) and pd.notna(last_rank):
            distance_change = current_distance - last_distance

            # 前走惨敗 → 距離変更で復活の可能性
            if last_rank >= 10:
                if abs(distance_change) >= 400:  # 大幅な距離変更
                    score += 1.5  # 条件が合わなかっただけかも
                elif abs(distance_change) >= 200:
                    score += 1.0

        # 2. 馬場状態の変化
        current_condition = race_conditions.get('TrackCondition', '良')
        last_condition = last_race.get('baba', '良')

        condition_weights = {'良': 3, '稍重': 2, '重': 1, '不良': 0}
        current_weight = condition_weights.get(current_condition, 2)
        last_weight = condition_weights.get(last_condition, 2)

        if pd.notna(last_rank) and last_rank >= 8:
            # 前走惨敗 → 馬場改善
            if current_weight > last_weight:
                score += 1.0 * (current_weight - last_weight)

        # 3. コース種別の変化（芝⇔ダート）
        current_course_type = race_conditions.get('CourseType', '芝')
        last_course_type = last_race.get('course_type', '芝')

        if current_course_type != last_course_type:
            # コース替わりは大きな変化
            # 過去にこのコース種別で好走していれば高評価
            for race in race_results[1:6]:  # 2-6走前を確認
                if isinstance(race, dict):
                    past_course = race.get('course_type')
                    past_rank = pd.to_numeric(race.get('rank'), errors='coerce')
                    if past_course == current_course_type and pd.notna(past_rank) and past_rank <= 5:
                        score += 1.5
                        break

        return score

    def calculate_divergence_score(self, features: Dict, ai_prediction: float) -> Dict:
        """
        オッズ乖離度を計算

        Args:
            features: 特徴量辞書
            ai_prediction: AIによる勝率予測（0-1）

        Returns:
            {
                'odds_rate': オッズ期待勝率,
                'ai_rate': AI予測勝率,
                'divergence': 乖離度,
                'evaluation': 評価（'undervalued', 'fair', 'overvalued'）
            }
        """
        odds_rate = features.get('odds_win_rate', np.nan)

        if pd.isna(odds_rate) or pd.isna(ai_prediction):
            return {
                'odds_rate': odds_rate,
                'ai_rate': ai_prediction,
                'divergence': np.nan,
                'evaluation': 'unknown'
            }

        # 乖離度 = AI予測 - オッズ期待値
        divergence = ai_prediction - odds_rate

        # 評価判定
        if divergence > 0.10:  # AIがオッズより10%以上高評価
            evaluation = 'strong_undervalued'  # 強い過小評価（大穴候補）
        elif divergence > 0.05:
            evaluation = 'undervalued'  # 過小評価（穴候補）
        elif divergence > -0.05:
            evaluation = 'fair'  # 妥当
        elif divergence > -0.10:
            evaluation = 'overvalued'  # やや過大評価
        else:
            evaluation = 'strong_overvalued'  # 強い過大評価（危険）

        return {
            'odds_rate': odds_rate,
            'ai_rate': ai_prediction,
            'divergence': divergence,
            'evaluation': evaluation
        }

    def assign_marks_and_confidence(self, horses_data: List[Dict]) -> List[Dict]:
        """
        ◎○▲△印と自信度S/A/B/Cを自動付与

        Args:
            horses_data: 馬ごとの予測データリスト
                [{
                    'horse_name': '馬名',
                    'odds': オッズ,
                    'ai_prediction': AI予測確率,
                    'divergence': 乖離度,
                    'features': 特徴量辞書,
                    ...
                }]

        Returns:
            印と自信度を追加したリスト
        """
        # AI総合評価でソート（乖離度も考慮）
        scored_horses = []

        for horse in horses_data:
            # 総合スコア = AI予測 × 0.6 + 乖離度補正 × 0.4
            ai_pred = horse.get('ai_prediction', 0)
            divergence = horse.get('divergence', 0)

            # 乖離度補正（過小評価されている馬を優遇）
            divergence_bonus = max(0, divergence) * 2  # プラス乖離のみボーナス

            composite_score = ai_pred * 0.6 + divergence_bonus * 0.4

            horse['composite_score'] = composite_score
            scored_horses.append(horse)

        # スコア順にソート
        scored_horses.sort(key=lambda x: x['composite_score'], reverse=True)

        # 印の付与（5頭体制）
        for i, horse in enumerate(scored_horses):
            if i == 0:
                horse['mark'] = '◎'  # 本命
            elif i == 1:
                horse['mark'] = '○'  # 対抗
            elif i == 2:
                horse['mark'] = '▲'  # 単穴
            else:
                horse['mark'] = ''

            # 自信度の判定（上位3頭のみ一旦設定）
            if i < 3:
                horse['confidence'] = self._calculate_confidence(horse, i)

        # 4位と5位の馬に☆と△を割り当て（人気を考慮）
        if len(scored_horses) >= 5:
            fourth_fifth = scored_horses[3:5]

            # 人気順にソート（popularityが小さい方が人気が高い）
            fourth_fifth_sorted = sorted(fourth_fifth, key=lambda x: x.get('features', {}).get('popularity', 99))

            # より人気が高い方（popularityが小さい方）を堅実な連下として△
            fourth_fifth_sorted[0]['mark'] = '△'  # 連下（堅実）
            fourth_fifth_sorted[0]['confidence'] = self._calculate_confidence(fourth_fifth_sorted[0], 4)

            # より人気が低い方（popularityが大きい方）を穴馬として☆
            if len(fourth_fifth_sorted) >= 2:
                fourth_fifth_sorted[1]['mark'] = '☆'  # 穴馬
                fourth_fifth_sorted[1]['confidence'] = self._calculate_confidence(fourth_fifth_sorted[1], 3)
        elif len(scored_horses) == 4:
            scored_horses[3]['mark'] = '☆'
            scored_horses[3]['confidence'] = self._calculate_confidence(scored_horses[3], 3)

        return scored_horses

    def _calculate_confidence(self, horse: Dict, rank: int) -> str:
        """
        自信度S/A/B/Cを判定

        判定基準:
        S: 鉄板（オッズ1-2番人気 + AI評価1位 + 安定成績）
        A: 信頼度高（オッズとAI一致 or 穴で評価高）
        B: 中程度
        C: 低い（人気だけ、不安定）
        """
        popularity = horse.get('features', {}).get('popularity', 99)
        ai_prediction = horse.get('ai_prediction', 0)
        divergence = horse.get('divergence', 0)
        recent_rank_avg = horse.get('features', {}).get('recent_rank_avg', 99)
        recent_rank_std = horse.get('features', {}).get('recent_rank_std', 99)

        # S級判定（鉄板）
        if (popularity <= 2 and  # 1-2番人気
            rank == 0 and  # AI評価1位
            recent_rank_avg <= 3 and  # 直近平均3着以内
            recent_rank_std <= 2):  # 成績安定
            return 'S'

        # A級判定
        if rank == 0 and abs(divergence) < 0.05:  # AI1位でオッズと一致
            return 'A'

        if popularity >= 5 and divergence > 0.08:  # 5番人気以下で大きくプラス乖離
            return 'A'  # 掘り出し物

        if rank <= 1 and ai_prediction > 0.2:  # 上位2頭で予測確率高い
            return 'A'

        # B級判定
        if rank <= 2:  # 上位3頭
            return 'B'

        if divergence > 0.05:  # そこそこプラス乖離
            return 'B'

        # C級
        return 'C'

    def calculate_simple_ai_prediction(self, features: Dict) -> float:
        """
        簡易AI予測モデル
        特徴量からルールベースで勝率を推定

        Args:
            features: 特徴量辞書

        Returns:
            予測勝率（0-1）
        """
        # 基礎勝率（直近3走の成績から）
        base_rate = 0.1  # デフォルト10%

        recent_rank_avg = features.get('recent_rank_avg')
        if pd.notna(recent_rank_avg):
            # 平均着順から勝率を推定
            if recent_rank_avg <= 2:
                base_rate = 0.25  # 平均2着以内 → 25%
            elif recent_rank_avg <= 3:
                base_rate = 0.18  # 平均3着以内 → 18%
            elif recent_rank_avg <= 5:
                base_rate = 0.12  # 平均5着以内 → 12%
            elif recent_rank_avg <= 8:
                base_rate = 0.08  # 平均8着以内 → 8%
            else:
                base_rate = 0.05  # それ以下 → 5%

        # 調整係数の初期化
        multiplier = 1.0

        # 1. 成績安定性ボーナス
        recent_rank_std = features.get('recent_rank_std')
        if pd.notna(recent_rank_std):
            if recent_rank_std <= 1:
                multiplier *= 1.2  # 非常に安定 +20%
            elif recent_rank_std <= 2:
                multiplier *= 1.1  # 安定 +10%
            elif recent_rank_std >= 5:
                multiplier *= 0.9  # 不安定 -10%

        # 2. 距離適性ボーナス
        distance_fitness = features.get('distance_fitness')
        if pd.notna(distance_fitness) and distance_fitness > 0:
            multiplier *= (1.0 + distance_fitness * 0.2)  # 最大+20%

        # 3. 馬場適性ボーナス
        track_fitness = features.get('track_fitness')
        if pd.notna(track_fitness) and track_fitness > 0:
            multiplier *= (1.0 + track_fitness * 0.15)  # 最大+15%

        # 4. 騎手勝率ボーナス
        jockey_win_rate = features.get('jockey_win_rate')
        if pd.notna(jockey_win_rate) and jockey_win_rate > 0.1:
            multiplier *= (1.0 + (jockey_win_rate - 0.1) * 0.5)  # 騎手が強ければボーナス

        # 5. 前走からの間隔調整
        days_since_last = features.get('days_since_last')
        if pd.notna(days_since_last):
            if 14 <= days_since_last <= 56:  # 2週間～8週間が最適
                multiplier *= 1.05  # +5%
            elif days_since_last > 120:  # 4ヶ月以上休養
                multiplier *= 0.85  # -15%（休養明け）
            elif days_since_last < 7:  # 1週間未満
                multiplier *= 0.9  # -10%（間隔詰まり）

        # 6. 馬体重変動ペナルティ
        weight_change = features.get('weight_change')
        if pd.notna(weight_change):
            if abs(weight_change) > 10:  # ±10kg以上の変動
                multiplier *= 0.95  # -5%
            if weight_change < -15:  # 15kg以上減
                multiplier *= 0.9  # さらに-10%

        # 7. 条件変化ボーナス
        condition_change = features.get('condition_change_score')
        if pd.notna(condition_change) and condition_change > 0:
            multiplier *= (1.0 + condition_change * 0.1)

        # 最終予測勝率
        ai_prediction = base_rate * multiplier

        # 0-1の範囲に収める
        ai_prediction = max(0.01, min(0.95, ai_prediction))

        return ai_prediction

    def get_recent_3_results(self, race_results: List[Dict]) -> str:
        """
        直近3走の着順を取得

        Returns:
            例: "1-3-2" または "5-8-4"
        """
        if not race_results or len(race_results) == 0:
            return "-"

        results = []
        for race in race_results[:3]:  # 最新3走
            rank = race.get('rank')
            if pd.notna(rank):
                try:
                    results.append(str(int(rank)))
                except:
                    results.append('-')
            else:
                results.append('-')

        if not results:
            return "-"

        return "-".join(results)

    def determine_running_style(self, race_results: List[Dict]) -> str:
        """
        脚質を判定（逃げ/先行/差し/追込）

        判定方法:
        - 直近3走のPassage（通過順位）の1コーナー位置から判定
        - 1-3位: 逃げ
        - 4-6位: 先行
        - 7-10位: 差し
        - 11位以降: 追込

        Returns:
            "逃げ", "先行", "差し", "追込", または "-"
        """
        if not race_results or len(race_results) == 0:
            return "-"

        first_corner_positions = []

        for race in race_results[:3]:  # 最新3走
            passage = race.get('passage', '')
            if not passage or passage == '-':
                continue

            # Passageは "1-1-1-1" のような形式
            # 最初の数字が1コーナー位置
            try:
                parts = str(passage).split('-')
                if parts and parts[0]:
                    first_pos = int(parts[0])
                    first_corner_positions.append(first_pos)
            except:
                continue

        if not first_corner_positions:
            return "-"

        # 平均位置で判定
        avg_position = sum(first_corner_positions) / len(first_corner_positions)

        if avg_position <= 3:
            return "逃げ"
        elif avg_position <= 6:
            return "先行"
        elif avg_position <= 10:
            return "差し"
        else:
            return "追込"


def demo_usage():
    """使用例"""
    analyzer = ImprovedHorseAnalyzer()

    # サンプルデータ
    horse_details = {
        'OddsShutuba': 3.5,
        'NinkiShutuba': 2,
        'Age': 4,
        'Sex': '牡',
        'Load': 56,
        'Waku': 3,
        'HorseName': 'サンプルホース',
        'race_results': [
            {'rank': 5, 'date': '2024-01-15', 'distance': 2000, 'baba': '良', 'course_type': '芝'},
            {'rank': 2, 'date': '2023-12-10', 'distance': 1800, 'baba': '良', 'course_type': '芝'},
            {'rank': 8, 'date': '2023-11-05', 'distance': 2400, 'baba': '重', 'course_type': '芝'},
        ]
    }

    race_conditions = {
        'Distance': 1800,
        'TrackCondition': '良',
        'CourseType': '芝',
        'TrackName': '東京',
        'RaceDate': '2024-02-01'
    }

    # 特徴量計算
    features = analyzer.calculate_simplified_features(horse_details, race_conditions)
    print("計算された特徴量:")
    for key, value in features.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    demo_usage()
