"""
展開予想システム

Passageデータから脚質を分析し、レースの展開を予想する

脚質判定:
- 逃げ: 序盤1-3番手
- 先行: 序盤4-6番手
- 差し: 序盤7-12番手
- 追込: 序盤13番手以降
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple

class RacePaceAnalyzer:
    """レース展開分析クラス"""

    def __init__(self):
        # 脚質の定義
        self.style_ranges = {
            'escape': (1, 3),    # 逃げ
            'leading': (4, 6),   # 先行
            'sashi': (7, 12),    # 差し
            'oikomi': (13, 99)   # 追込
        }

    def parse_passage(self, passage_str: str) -> int:
        """
        Passageデータから序盤の位置を抽出

        Args:
            passage_str: "5-5" or "9-9-11-11" などの形式

        Returns:
            序盤の位置（整数）、解析失敗時は0
        """
        if pd.isna(passage_str) or not isinstance(passage_str, str):
            return 0

        try:
            # ハイフンで分割
            parts = passage_str.split('-')
            if len(parts) > 0:
                # 最初の数値を取得
                first_position = int(parts[0].strip())
                return first_position
        except (ValueError, AttributeError):
            return 0

        return 0

    def classify_running_style(self, first_position: int) -> str:
        """
        序盤位置から脚質を判定

        Args:
            first_position: 序盤の位置

        Returns:
            脚質 ('escape', 'leading', 'sashi', 'oikomi', 'unknown')
        """
        if first_position == 0:
            return 'unknown'

        for style, (min_pos, max_pos) in self.style_ranges.items():
            if min_pos <= first_position <= max_pos:
                return style

        return 'unknown'

    def analyze_race_pace(self, race_df: pd.DataFrame) -> Dict:
        """
        レース全体の脚質分布を分析

        Args:
            race_df: 同一レースのデータフレーム

        Returns:
            レース展開情報の辞書
        """
        # 各馬の脚質を判定
        styles = []
        for passage in race_df['Passage']:
            first_pos = self.parse_passage(passage)
            style = self.classify_running_style(first_pos)
            styles.append(style)

        # 脚質分布を集計
        style_counts = pd.Series(styles).value_counts()

        escape_count = style_counts.get('escape', 0)
        leading_count = style_counts.get('leading', 0)
        sashi_count = style_counts.get('sashi', 0)
        oikomi_count = style_counts.get('oikomi', 0)

        # ペース予想
        # 逃げ馬が多い → ハイペース → 前崩れ
        # 逃げ馬が少ない → スローペース → 前残り
        if escape_count >= 3:
            pace_prediction = 'fast'  # ハイペース
            development = 'front_collapse'  # 前崩れ
        elif escape_count == 0:
            pace_prediction = 'very_slow'  # 超スローペース
            development = 'front_runner'  # 前残り確定
        elif escape_count == 1:
            pace_prediction = 'slow'  # スローペース
            development = 'front_runner'  # 前残り
        else:  # escape_count == 2
            pace_prediction = 'medium'  # 平均ペース
            development = 'neutral'  # 中立

        return {
            'escape_count': int(escape_count),
            'leading_count': int(leading_count),
            'sashi_count': int(sashi_count),
            'oikomi_count': int(oikomi_count),
            'pace_prediction': pace_prediction,
            'development': development,
            'total_horses': len(race_df)
        }

    def calculate_pace_match_score(self, running_style: str, pace_prediction: str) -> float:
        """
        脚質とペースの相性スコアを計算

        Args:
            running_style: 馬の脚質
            pace_prediction: レースのペース予想

        Returns:
            相性スコア (0.0 - 1.0)
        """
        # 相性マトリックス
        compatibility = {
            'escape': {
                'very_slow': 1.0,  # 逃げ馬にとって超スローは最高
                'slow': 0.9,
                'medium': 0.7,
                'fast': 0.3  # ハイペースは不利
            },
            'leading': {
                'very_slow': 0.8,
                'slow': 0.9,
                'medium': 0.8,
                'fast': 0.5
            },
            'sashi': {
                'very_slow': 0.5,  # スローだと前が残る
                'slow': 0.6,
                'medium': 0.8,
                'fast': 1.0  # ハイペースで前が潰れると有利
            },
            'oikomi': {
                'very_slow': 0.4,
                'slow': 0.5,
                'medium': 0.7,
                'fast': 0.9  # ハイペースで前が潰れると有利
            },
            'unknown': {
                'very_slow': 0.5,
                'slow': 0.5,
                'medium': 0.5,
                'fast': 0.5
            }
        }

        return compatibility.get(running_style, {}).get(pace_prediction, 0.5)


def test_analyzer():
    """分析器のテスト"""
    print("=" * 80)
    print("展開予想システムテスト")
    print("=" * 80)

    analyzer = RacePaceAnalyzer()

    # テスト1: Passageパース
    print("\n【テスト1: Passageパース】")
    test_passages = ['1-1-1-1', '5-5', '10-9-7-6', '16-14', '']
    for passage in test_passages:
        first_pos = analyzer.parse_passage(passage)
        style = analyzer.classify_running_style(first_pos)
        print(f"  Passage: {passage:10s} → 序盤: {first_pos:2d} → 脚質: {style}")

    # テスト2: レース分析
    print("\n【テスト2: レース分析】")

    # サンプルレースデータ
    sample_race = pd.DataFrame({
        'Passage': ['1-1-1-1', '2-2-2-2', '5-5-5-5', '7-7-7-7',
                    '10-10-10-10', '12-12-12-12', '14-14-14-14', '16-16-16-16']
    })

    pace_info = analyzer.analyze_race_pace(sample_race)
    print(f"\n  脚質分布:")
    print(f"    逃げ: {pace_info['escape_count']}頭")
    print(f"    先行: {pace_info['leading_count']}頭")
    print(f"    差し: {pace_info['sashi_count']}頭")
    print(f"    追込: {pace_info['oikomi_count']}頭")
    print(f"\n  ペース予想: {pace_info['pace_prediction']}")
    print(f"  展開予想: {pace_info['development']}")

    # テスト3: 相性スコア
    print("\n【テスト3: 相性スコア】")
    test_combinations = [
        ('escape', 'slow'),   # 逃げ × スロー = 有利
        ('escape', 'fast'),   # 逃げ × ハイ = 不利
        ('sashi', 'fast'),    # 差し × ハイ = 有利
        ('sashi', 'slow'),    # 差し × スロー = 不利
    ]

    for style, pace in test_combinations:
        score = analyzer.calculate_pace_match_score(style, pace)
        print(f"  {style:8s} × {pace:10s} = {score:.2f}")

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


def add_pace_features_to_csv(input_csv: str, output_csv: str = None):
    """
    CSVに展開予想特徴量を追加

    Args:
        input_csv: 入力CSVファイル
        output_csv: 出力CSVファイル（Noneの場合は元ファイルを上書き）
    """
    print("=" * 80)
    print("展開予想特徴量の追加")
    print("=" * 80)

    # CSV読み込み
    print("\nCSV読み込み中...")
    df = pd.read_csv(input_csv, encoding='utf-8', low_memory=False)
    print(f"総レコード数: {len(df)}")

    # 分析器初期化
    analyzer = RacePaceAnalyzer()

    # 新しい列を初期化
    df['running_style'] = 'unknown'
    df['escape_count'] = 0
    df['leading_count'] = 0
    df['sashi_count'] = 0
    df['oikomi_count'] = 0
    df['pace_prediction'] = 'medium'
    df['development'] = 'neutral'
    df['pace_match_score'] = 0.5

    # レースごとに処理
    unique_races = df['race_id'].unique()
    print(f"ユニークなレース数: {len(unique_races)}")

    for i, race_id in enumerate(unique_races, 1):
        if i % 1000 == 0:
            print(f"  進捗: {i}/{len(unique_races)} ({100*i/len(unique_races):.1f}%)")

        # 同一レースのデータを取得
        race_mask = df['race_id'] == race_id
        race_df = df[race_mask].copy()

        # レース全体の展開分析
        pace_info = analyzer.analyze_race_pace(race_df)

        # 各馬の脚質と相性スコアを計算
        for idx in race_df.index:
            passage = df.loc[idx, 'Passage']
            first_pos = analyzer.parse_passage(passage)
            running_style = analyzer.classify_running_style(first_pos)
            pace_match = analyzer.calculate_pace_match_score(
                running_style,
                pace_info['pace_prediction']
            )

            # 特徴量を設定
            df.loc[idx, 'running_style'] = running_style
            df.loc[idx, 'escape_count'] = pace_info['escape_count']
            df.loc[idx, 'leading_count'] = pace_info['leading_count']
            df.loc[idx, 'sashi_count'] = pace_info['sashi_count']
            df.loc[idx, 'oikomi_count'] = pace_info['oikomi_count']
            df.loc[idx, 'pace_prediction'] = pace_info['pace_prediction']
            df.loc[idx, 'development'] = pace_info['development']
            df.loc[idx, 'pace_match_score'] = pace_match

    # CSV保存
    if output_csv is None:
        output_csv = input_csv

    print(f"\nCSV保存中: {output_csv}")
    df.to_csv(output_csv, index=False, encoding='utf-8')
    print("完了！")

    # 統計情報
    print("\n" + "=" * 80)
    print("特徴量統計")
    print("=" * 80)
    print(f"\n脚質分布:")
    print(df['running_style'].value_counts())
    print(f"\nペース予想分布:")
    print(df['pace_prediction'].value_counts())


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_analyzer()
    elif len(sys.argv) > 1 and sys.argv[1] == 'add':
        from data_config import MAIN_CSV
        output_file = "netkeiba_data_2020_2024_clean_with_class_and_pace.csv"
        add_pace_features_to_csv(MAIN_CSV, output_file)
    else:
        print("使用方法:")
        print("  テスト: py race_pace_analyzer.py test")
        print("  CSV追加: py race_pace_analyzer.py add")
