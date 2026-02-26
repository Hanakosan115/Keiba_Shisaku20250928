"""
特徴量エンジニアリング v2
- 着差データのパース
- クラス移動の判定
- 展開予測用特徴量
- 成長曲線（3歳馬の上昇度）
"""

import pandas as pd
import numpy as np
import re


def parse_diff_to_seconds(diff_str):
    """
    着差文字列を秒数に変換
    例: "クビ" -> 0.1, "1.1/4" -> 0.25, "3" -> 0.6, "大差" -> 5.0
    """
    if pd.isna(diff_str) or diff_str == '' or diff_str == 'nan':
        return 0.0

    diff_str = str(diff_str).strip()

    # 特殊表記
    special_map = {
        'クビ': 0.1,
        'ハナ': 0.05,
        'アタマ': 0.15,
        '大差': 5.0,
        '同着': 0.0,
        '降': 10.0,  # 降着
        '取': 10.0,  # 取消
        '除': 10.0,  # 除外
        '中': 10.0,  # 中止
    }

    for key, val in special_map.items():
        if key in diff_str:
            return val

    # 数値 + 馬身（例: "3", "1.1/4", "2.1/2"）
    try:
        # 分数表記を処理
        if '/' in diff_str:
            # "1.1/4" -> 1.25, "2.1/2" -> 2.5
            parts = diff_str.split('.')
            if len(parts) == 2:
                whole = float(parts[0]) if parts[0] else 0
                frac_parts = parts[1].split('/')
                if len(frac_parts) == 2:
                    frac = float(frac_parts[0]) / float(frac_parts[1])
                    return (whole + frac) * 0.2  # 1馬身 ≒ 0.2秒
            # "1/2" -> 0.5
            frac_parts = diff_str.split('/')
            if len(frac_parts) == 2:
                return (float(frac_parts[0]) / float(frac_parts[1])) * 0.2

        # 純粋な数値
        return float(diff_str) * 0.2  # 1馬身 ≒ 0.2秒
    except:
        return 0.0


def parse_passage(passage_str):
    """
    通過順をパースして位置情報を返す
    例: "5-5" -> [5, 5], "9-9-11-11" -> [9, 9, 11, 11]
    """
    if pd.isna(passage_str) or passage_str == '':
        return []

    try:
        positions = [int(x) for x in str(passage_str).split('-')]
        return positions
    except:
        return []


def extract_race_class(race_name):
    """
    レース名からクラスを抽出
    戻り値: 数値（高いほど上位クラス）
    """
    if pd.isna(race_name):
        return 0

    race_name = str(race_name)

    # G1/G2/G3
    if 'G1' in race_name or 'GI' in race_name or 'Ｇ１' in race_name:
        return 10
    if 'G2' in race_name or 'GII' in race_name or 'Ｇ２' in race_name:
        return 9
    if 'G3' in race_name or 'GIII' in race_name or 'Ｇ３' in race_name:
        return 8

    # リステッド/オープン
    if 'リステッド' in race_name or 'L' in race_name:
        return 7
    if 'オープン' in race_name or 'OP' in race_name:
        return 6

    # 条件戦
    if '3勝' in race_name or '1600万' in race_name:
        return 5
    if '2勝' in race_name or '1000万' in race_name:
        return 4
    if '1勝' in race_name or '500万' in race_name:
        return 3

    # 新馬/未勝利
    if '新馬' in race_name:
        return 2
    if '未勝利' in race_name:
        return 1

    return 3  # デフォルト


def calculate_running_style(df_horse_history):
    """
    馬の脚質を計算
    戻り値: 'S'(逃げ), 'P'(先行), 'D'(差し), 'H'(追込)
    """
    if len(df_horse_history) == 0:
        return 'D', 5.0  # デフォルト

    positions = []
    for _, row in df_horse_history.iterrows():
        passage = parse_passage(row.get('Passage', ''))
        if len(passage) > 0:
            positions.append(passage[0])  # 1コーナー通過順

    if len(positions) == 0:
        return 'D', 5.0

    avg_pos = np.mean(positions)

    if avg_pos <= 2.0:
        return 'S', avg_pos  # 逃げ
    elif avg_pos <= 4.0:
        return 'P', avg_pos  # 先行
    elif avg_pos <= 7.0:
        return 'D', avg_pos  # 差し
    else:
        return 'H', avg_pos  # 追込


def add_enhanced_features(df, historical_df=None):
    """
    データフレームに拡張特徴量を追加
    """
    df = df.copy()

    # 1. 着差を秒数に変換
    if 'Diff' in df.columns:
        df['diff_seconds'] = df['Diff'].apply(parse_diff_to_seconds)
    else:
        df['diff_seconds'] = 0.0

    # 2. レースクラスを抽出
    if 'race_name' in df.columns:
        df['race_class'] = df['race_name'].apply(extract_race_class)
    else:
        df['race_class'] = 3

    # 3. 通過順から脚質指標を計算
    if 'Passage' in df.columns:
        df['first_corner_pos'] = df['Passage'].apply(
            lambda x: parse_passage(x)[0] if len(parse_passage(x)) > 0 else 0
        )
        df['last_corner_pos'] = df['Passage'].apply(
            lambda x: parse_passage(x)[-1] if len(parse_passage(x)) > 0 else 0
        )
        # 位置変化（追い上げ/下げ）
        df['position_change'] = df['first_corner_pos'] - df['last_corner_pos']
    else:
        df['first_corner_pos'] = 0
        df['last_corner_pos'] = 0
        df['position_change'] = 0

    # 4. 年齢から成長ステージを計算
    if 'Age' in df.columns:
        df['age_numeric'] = pd.to_numeric(df['Age'], errors='coerce').fillna(4)
        df['is_young'] = (df['age_numeric'] <= 3).astype(int)
        df['is_peak'] = ((df['age_numeric'] >= 4) & (df['age_numeric'] <= 6)).astype(int)
        df['is_veteran'] = (df['age_numeric'] >= 7).astype(int)

    return df


def calculate_class_change(horse_id, current_race_class, historical_df):
    """
    馬のクラス移動を計算
    戻り値: +は昇級、-は降級、0は同クラス
    """
    if historical_df is None or len(historical_df) == 0:
        return 0

    horse_history = historical_df[historical_df['horse_id'] == horse_id]
    if len(horse_history) == 0:
        return 0

    # 直近のレースクラスを取得
    last_race = horse_history.sort_values('date', ascending=False).iloc[0]
    last_class = extract_race_class(last_race.get('race_name', ''))

    return current_race_class - last_class


def count_runners_by_style(race_horses_df):
    """
    レース内の脚質別頭数をカウント
    展開予測用
    """
    styles = {'S': 0, 'P': 0, 'D': 0, 'H': 0}

    for _, row in race_horses_df.iterrows():
        passage = parse_passage(row.get('Passage', ''))
        if len(passage) > 0:
            avg_pos = np.mean(passage[:2]) if len(passage) >= 2 else passage[0]
            if avg_pos <= 2.0:
                styles['S'] += 1
            elif avg_pos <= 4.0:
                styles['P'] += 1
            elif avg_pos <= 7.0:
                styles['D'] += 1
            else:
                styles['H'] += 1

    return styles


def calculate_pace_scenario(num_runners, styles):
    """
    展開シナリオを予測
    戻り値: 'H'(ハイペース), 'M'(ミドル), 'S'(スロー)
    """
    # 逃げ・先行馬が多い = ハイペース
    front_runners = styles['S'] + styles['P']
    front_ratio = front_runners / num_runners if num_runners > 0 else 0.3

    if front_ratio >= 0.4:
        return 'H'  # ハイペース（差し有利）
    elif front_ratio <= 0.2:
        return 'S'  # スローペース（逃げ・先行有利）
    else:
        return 'M'  # ミドルペース


if __name__ == '__main__':
    # テスト
    print("Testing parse_diff_to_seconds:")
    test_diffs = ['クビ', '1.1/4', '3', '大差', 'ハナ', '2.1/2', None, '']
    for diff in test_diffs:
        result = parse_diff_to_seconds(diff)
        print(f"  {diff!r} -> {result:.3f}")

    print("\nTesting parse_passage:")
    test_passages = ['5-5', '9-9-11-11', '1-1-1-1', None]
    for passage in test_passages:
        result = parse_passage(passage)
        print(f"  {passage!r} -> {result}")

    print("\nTesting extract_race_class:")
    test_names = ['G1天皇賞', '3歳未勝利', '4歳以上2勝クラス', 'リステッドOP']
    for name in test_names:
        result = extract_race_class(name)
        print(f"  {name!r} -> {result}")

    print("\nAll tests completed!")
