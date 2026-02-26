"""
レース分析モジュール
- 当日馬場傾向分析
- 想定隊列・ペース予測
"""

import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from collections import defaultdict


class TrackTendencyAnalyzer:
    """当日の馬場傾向を分析"""

    def __init__(self, df_history=None):
        """
        Args:
            df_history: 過去データ（基準タイム計算用）
        """
        self.df_history = df_history
        self.baseline_times = {}

        if df_history is not None:
            self._calculate_baseline_times()

    def _calculate_baseline_times(self):
        """条件別の基準タイムを計算"""
        df = self.df_history.copy()

        # タイム列を探す
        time_col = None
        for col in ['タイム', 'Time', 'time']:
            if col in df.columns:
                time_col = col
                break

        if time_col is None:
            return

        df['time_seconds'] = df[time_col].apply(self._parse_time)
        df_valid = df[df['time_seconds'].notna()]

        # 条件別にグループ化
        for (track, course, dist), group in df_valid.groupby(['track_name', 'course_type', 'distance']):
            if len(group) >= 10:
                times = group['time_seconds'].values
                # 外れ値除外（中央80%）
                times_sorted = np.sort(times)
                lower = int(len(times_sorted) * 0.1)
                upper = int(len(times_sorted) * 0.9)
                if upper > lower:
                    self.baseline_times[(track, course, dist)] = np.mean(times_sorted[lower:upper])

    def _parse_time(self, time_str):
        """タイム文字列を秒数に変換"""
        if pd.isna(time_str) or time_str == '' or time_str == '-':
            return np.nan
        try:
            time_str = str(time_str).strip()
            if ':' in time_str:
                parts = time_str.split(':')
                return int(parts[0]) * 60 + float(parts[1])
            return float(time_str)
        except:
            return np.nan

    def analyze_today_tendency(self, track_name, course_type, today_results):
        """
        当日の馬場傾向を分析

        Args:
            track_name: 競馬場名
            course_type: 芝/ダート
            today_results: 当日のレース結果リスト
                [{'passage': '1-1-1-1', 'rank': 1, 'time': '1:34.5', 'distance': 1600}, ...]

        Returns:
            {
                'front_bias': float,  # 前残り度 (-1.0〜1.0, 正が前有利)
                'time_tendency': float,  # 時計傾向 (負が速い)
                'sample_count': int,
                'description': str
            }
        """
        if not today_results or len(today_results) < 2:
            return {
                'front_bias': 0.0,
                'time_tendency': 0.0,
                'sample_count': 0,
                'description': 'データ不足'
            }

        # 前残り度を計算（4角順位と着順の相関）
        front_biases = []
        time_diffs = []

        for race in today_results:
            # 通過順から4角順位を取得
            passage = race.get('passage', '')
            if passage and '-' in str(passage):
                try:
                    corners = [int(x) for x in str(passage).split('-')]
                    last_corner = corners[-1]  # 4角順位
                    rank = race.get('rank', 0)

                    if rank and rank <= 5:  # 上位5頭で計算
                        # 4角順位が低い(前にいた)のに着順が良い = 前残り
                        front_biases.append(last_corner - rank)
                except:
                    pass

            # 時計傾向
            time_sec = self._parse_time(race.get('time'))
            distance = race.get('distance', 0)

            if time_sec and distance:
                key = (track_name, course_type, distance)
                if key in self.baseline_times:
                    baseline = self.baseline_times[key]
                    diff_pct = (time_sec - baseline) / baseline * 100
                    time_diffs.append(diff_pct)

        # 前残り度（正規化）
        if front_biases:
            # 正の値 = 前にいた馬が着順も良い = 前残り
            raw_bias = np.mean(front_biases)
            front_bias = np.clip(raw_bias / 3.0, -1.0, 1.0)  # -1〜1に正規化
        else:
            front_bias = 0.0

        # 時計傾向
        time_tendency = np.mean(time_diffs) if time_diffs else 0.0

        # 説明文生成
        description = self._generate_description(front_bias, time_tendency)

        return {
            'front_bias': round(front_bias, 2),
            'time_tendency': round(time_tendency, 2),
            'sample_count': len(today_results),
            'description': description
        }

    def _generate_description(self, front_bias, time_tendency):
        """傾向の説明文を生成"""
        parts = []

        # 前残り/差し有利
        if front_bias > 0.3:
            parts.append("前残り傾向")
        elif front_bias > 0.1:
            parts.append("やや前有利")
        elif front_bias < -0.3:
            parts.append("差し有利")
        elif front_bias < -0.1:
            parts.append("やや差し有利")
        else:
            parts.append("フラット")

        # 時計
        if time_tendency < -1.0:
            parts.append("高速馬場")
        elif time_tendency < -0.3:
            parts.append("やや速い")
        elif time_tendency > 1.0:
            parts.append("時計かかる")
        elif time_tendency > 0.3:
            parts.append("やや重い")
        else:
            parts.append("標準時計")

        return " / ".join(parts)

    def scrape_today_results(self, track_name, course_type='芝'):
        """
        当日のレース結果をスクレイピング

        Args:
            track_name: 競馬場名（東京, 中山, 阪神, etc.）
            course_type: 芝 or ダート

        Returns:
            list of race results
        """
        # 競馬場コード
        track_codes = {
            '札幌': '01', '函館': '02', '福島': '03', '新潟': '04',
            '東京': '05', '中山': '06', '中京': '07', '京都': '08',
            '阪神': '09', '小倉': '10'
        }

        track_code = track_codes.get(track_name)
        if not track_code:
            return []

        today = datetime.now()
        # 当日のレース一覧ページ
        # 実際のスクレイピングはnetkeiba等のサイト構造に依存

        results = []
        # TODO: 実際のスクレイピング実装
        # 現状はダミーデータを返す

        return results


class FormationPredictor:
    """想定隊列・ペース予測"""

    def __init__(self, df_history=None):
        self.df_history = df_history
        self.running_styles = {}  # 馬ID -> 脚質情報

        if df_history is not None:
            self._build_running_style_db()

    def _build_running_style_db(self):
        """各馬の脚質データベースを構築"""
        df = self.df_history.copy()

        # 通過順列を探す
        passage_col = None
        for col in ['通過', 'Passage', 'passage']:
            if col in df.columns:
                passage_col = col
                break

        if passage_col is None:
            return

        # 馬ごとに集計
        for horse_id, group in df.groupby('horse_id'):
            passages = group[passage_col].dropna()

            first_corners = []
            for p in passages:
                if '-' in str(p):
                    try:
                        first = int(str(p).split('-')[0])
                        first_corners.append(first)
                    except:
                        pass

            if len(first_corners) >= 3:
                avg_first = np.mean(first_corners)
                min_first = np.min(first_corners)

                # 脚質判定
                if avg_first <= 2:
                    style = '逃げ'
                    style_code = 1
                elif avg_first <= 4:
                    style = '先行'
                    style_code = 2
                elif avg_first <= 7:
                    style = '差し'
                    style_code = 3
                else:
                    style = '追込'
                    style_code = 4

                # テンの速さ（最小1角順位）
                early_speed = 10 - min_first  # 高いほど速い

                self.running_styles[horse_id] = {
                    'style': style,
                    'style_code': style_code,
                    'avg_first_corner': avg_first,
                    'min_first_corner': min_first,
                    'early_speed': max(1, early_speed),
                    'sample_count': len(first_corners)
                }

    def predict_formation(self, horses):
        """
        想定隊列を予測

        Args:
            horses: 出走馬リスト
                [{'horse_id': xxx, '馬名': yyy, '枠番': z}, ...]

        Returns:
            {
                'formation': [  # 1角想定順位
                    {'position': 1, 'horse_name': xxx, 'style': '逃げ', 'early_speed': 8},
                    ...
                ],
                'pace_prediction': 'ミドル',
                'pace_description': str,
                'front_runners': int,  # 逃げ馬数
                'pressers': int,  # 先行馬数
            }
        """
        # 各馬の脚質情報を取得
        horse_data = []

        for horse in horses:
            horse_id = horse.get('horse_id')
            horse_name = horse.get('馬名', horse.get('horse_name', '不明'))
            waku = horse.get('枠番', 0)

            try:
                waku = int(waku) if waku else 0
            except:
                waku = 0

            # 脚質情報を取得
            if horse_id and horse_id in self.running_styles:
                style_info = self.running_styles[horse_id]
            else:
                # デフォルト（中団）
                style_info = {
                    'style': '不明',
                    'style_code': 3,
                    'avg_first_corner': 5.0,
                    'early_speed': 5,
                    'sample_count': 0
                }

            horse_data.append({
                'horse_id': horse_id,
                'horse_name': horse_name,
                'waku': waku,
                **style_info
            })

        # 想定1角順位でソート（テンの速さ + 枠順補正）
        for h in horse_data:
            # 内枠補正（内枠ほど前に行きやすい）
            waku_bonus = (9 - h['waku']) * 0.3 if h['waku'] > 0 else 0
            h['predicted_position_score'] = h['early_speed'] + waku_bonus

        horse_data.sort(key=lambda x: x['predicted_position_score'], reverse=True)

        # 順位付け
        formation = []
        for i, h in enumerate(horse_data):
            formation.append({
                'position': i + 1,
                'horse_name': h['horse_name'],
                'style': h['style'],
                'early_speed': h['early_speed'],
                'waku': h['waku']
            })

        # ペース予測
        front_runners = sum(1 for h in horse_data if h['style'] == '逃げ')
        pressers = sum(1 for h in horse_data if h['style'] == '先行')
        closers = sum(1 for h in horse_data if h['style'] in ['差し', '追込'])

        pace, pace_desc = self._predict_pace(front_runners, pressers, closers, horse_data)

        return {
            'formation': formation,
            'pace_prediction': pace,
            'pace_description': pace_desc,
            'front_runners': front_runners,
            'pressers': pressers,
            'closers': closers
        }

    def _predict_pace(self, front_runners, pressers, closers, horse_data):
        """ペースを予測"""
        total = len(horse_data)

        # 逃げ馬のテン速度差を確認
        escape_horses = [h for h in horse_data if h['style'] == '逃げ']

        if front_runners == 0:
            # 逃げ馬なし → スローの上がり勝負
            return 'スロー', '逃げ馬不在でスローペース濃厚。上がり勝負。差し・追込有利。'

        elif front_runners == 1:
            # 逃げ馬1頭
            if pressers >= 3:
                # 先行馬多い → 突かれる
                return 'ミドル〜ハイ', f'逃げ馬1頭だが先行馬{pressers}頭。突かれてペース上がる可能性。'
            else:
                # 楽逃げ
                return 'スロー〜ミドル', '単騎逃げ濃厚。マイペースで運べる。逃げ馬要注意。'

        else:
            # 逃げ馬複数 → ハナ争い
            # テンの速さが拮抗しているか確認
            escape_speeds = [h['early_speed'] for h in escape_horses]
            speed_diff = max(escape_speeds) - min(escape_speeds)

            if speed_diff <= 2:
                return 'ハイ', f'逃げ馬{front_runners}頭でハナ争い必至。消耗戦。差し・追込有利。'
            else:
                return 'ミドル', f'逃げ馬{front_runners}頭だがテン差あり。隊列は決まりそう。'

    def format_formation_text(self, formation_result):
        """想定隊列をテキスト形式で出力"""
        lines = []
        lines.append("=" * 50)
        lines.append(" 想定隊列・ペース予測")
        lines.append("=" * 50)
        lines.append("")

        # ペース予測
        lines.append(f"【ペース予測】{formation_result['pace_prediction']}")
        lines.append(f"  {formation_result['pace_description']}")
        lines.append("")

        # 脚質構成
        lines.append(f"【脚質構成】逃げ:{formation_result['front_runners']} "
                    f"先行:{formation_result['pressers']} "
                    f"差し・追込:{formation_result['closers']}")
        lines.append("")

        # 想定隊列
        lines.append("【想定隊列（1角）】")
        formation = formation_result['formation']

        # グループ分け
        groups = [
            ("先頭集団", formation[:3]),
            ("中団", formation[3:len(formation)-3] if len(formation) > 6 else []),
            ("後方", formation[-3:] if len(formation) > 3 else [])
        ]

        for group_name, horses in groups:
            if horses:
                lines.append(f"  {group_name}:")
                for h in horses:
                    style_mark = {'逃げ': '◎', '先行': '○', '差し': '△', '追込': '▲'}.get(h['style'], '・')
                    lines.append(f"    {h['position']:2d}. {style_mark} {h['horse_name']} [{h['style']}]")

        lines.append("")
        lines.append("=" * 50)

        return "\n".join(lines)


# テスト用
if __name__ == '__main__':
    # ダミーデータでテスト
    horses = [
        {'horse_id': 1, '馬名': 'テスト馬A', '枠番': 1},
        {'horse_id': 2, '馬名': 'テスト馬B', '枠番': 3},
        {'horse_id': 3, '馬名': 'テスト馬C', '枠番': 5},
    ]

    predictor = FormationPredictor()
    result = predictor.predict_formation(horses)
    print(predictor.format_formation_text(result))
