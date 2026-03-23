# -*- coding: utf-8 -*-
"""
Phase 13: リーケージ完全排除版 特徴量エンジニアリング

【目的】
訓練データ（2020-2022）、検証データ（2023）、テストデータ（2024）に対して、
時系列を守った特徴量を作成する。

【重要原則】
1. datetime.now()の使用禁止
2. 全ての特徴量計算で cutoff_date を使用
3. 未来データの参照を絶対に行わない
4. horse_data取得時は必ず race_date < cutoff_date でフィルタ
"""
import pandas as pd
import numpy as np
import warnings
import re
import json
import os
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

# Phase R7: 枠番バイアス lookup テーブルの読み込み
_WAKU_STATS_PATH = os.path.join(os.path.dirname(__file__) or '.', 'models', 'phase_r7', 'waku_stats.json')
_waku_lookup   = {}
_waku_fallback = {}
_waku_global_avg = 0.0725
try:
    with open(_WAKU_STATS_PATH, 'r', encoding='utf-8') as _f:
        _waku_data = json.load(_f)
    _waku_lookup     = _waku_data.get('waku_lookup', {})
    _waku_fallback   = _waku_data.get('waku_fallback', {})
    _waku_global_avg = _waku_data.get('global_avg', 0.0725)
except Exception:
    pass  # ファイルなしはデフォルト値を使用

# Phase R8: 父馬×競馬場 lookup テーブルの読み込み
_SIRE_TRACK_STATS_PATH = os.path.join(os.path.dirname(__file__) or '.', 'models', 'phase_r8', 'sire_track_stats.json')
_sire_track_father   = {}
_sire_track_mf       = {}
_sire_track_global   = 0.0727
try:
    with open(_SIRE_TRACK_STATS_PATH, 'r', encoding='utf-8') as _f:
        _sire_track_data = json.load(_f)
    _sire_track_father = _sire_track_data.get('father', {})
    _sire_track_mf     = _sire_track_data.get('mother_father', {})
    _sire_track_global = _sire_track_data.get('global_wr', 0.0727)
except Exception:
    pass  # ファイルなしはデフォルト値を使用

print("=" * 80)
print("  Phase 13: 特徴量エンジニアリング（リーケージ排除版）")
print("=" * 80)
print()

# ===================================================================
# ヘルパー関数
# ===================================================================

def normalize_date(date_str):
    """日付を YYYY-MM-DD 形式に正規化"""
    s = str(date_str)
    # 日本語形式: 2024年01月27日
    match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', s)
    if match:
        return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
    # ISO形式: 2024-01-27
    match = re.search(r'(\d{4}-\d{2}-\d{2})', s)
    if match:
        return match.group(1)
    return None

def parse_diff_to_seconds(diff_str):
    """着差を秒数に変換（Phase 10特徴量用）"""
    if pd.isna(diff_str) or diff_str == '':
        return 1.0
    s = str(diff_str).strip()
    if s in ['同着', 'ハナ', 'アタマ']:
        return 0.1
    if s in ['クビ']:
        return 0.2
    # 数値のみ（馬身）
    try:
        val = float(s)
        return val * 0.2  # 1馬身 = 0.2秒
    except:
        pass
    return 1.0

def parse_passage(passage_str):
    """通過順をリストに変換: '03-03-02-01' → [3, 3, 2, 1]"""
    if pd.isna(passage_str) or passage_str == '':
        return []
    parts = str(passage_str).replace(' ', '').split('-')
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except:
            pass
    return result

def extract_race_class(race_name):
    """レース名からクラスを抽出: G1=5, G2=4, G3=3, オープン=2, 未勝利=1"""
    if pd.isna(race_name):
        return 0
    name = str(race_name)
    if 'G1' in name or 'GⅠ' in name:
        return 5
    if 'G2' in name or 'GⅡ' in name:
        return 4
    if 'G3' in name or 'GⅢ' in name:
        return 3
    if 'オープン' in name or 'OP' in name:
        return 2
    if '未勝利' in name or '新馬' in name:
        return 1
    return 3  # デフォルト

# ===================================================================
# 統計計算（訓練期間のデータのみ使用）
# ===================================================================

def calculate_sire_stats(df_history):
    """種牡馬ごとの産駒成績を計算（訓練期間のデータのみ）"""
    sire_stats = {}
    for sire_type in ['father', 'mother_father']:
        if sire_type not in df_history.columns:
            continue
        sire_data = df_history[df_history[sire_type].notna()].copy()
        sire_data['rank'] = pd.to_numeric(sire_data['rank'], errors='coerce')
        sire_data_finished = sire_data[sire_data['rank'].notna()]

        def _wr(g):
            return (g['rank'] == 1).mean() if len(g) > 0 else 0.0

        for sire_name, group in sire_data_finished.groupby(sire_type):
            if sire_name not in sire_stats:
                sire_stats[sire_name] = {}
            total = len(group)
            wins = (group['rank'] == 1).sum()
            top3 = (group['rank'] <= 3).sum()
            sire_stats[sire_name][f'{sire_type}_win_rate']  = wins / total if total > 0 else 0.0
            sire_stats[sire_name][f'{sire_type}_top3_rate'] = top3 / total if total > 0 else 0.0

            # Phase R2: 血統細分化（芝・ダート・道悪・短距離・長距離）
            turf_g  = group[group['course_type'] == '芝']                               if 'course_type'     in group.columns else group.iloc[0:0]
            dirt_g  = group[group['course_type'] == 'ダート']                           if 'course_type'     in group.columns else group.iloc[0:0]
            heavy_g = group[group['track_condition'].isin(['重', '不良'])]              if 'track_condition' in group.columns else group.iloc[0:0]
            short_g = group[pd.to_numeric(group['distance'], errors='coerce') <= 1400]  if 'distance'        in group.columns else group.iloc[0:0]
            long_g  = group[pd.to_numeric(group['distance'], errors='coerce') >= 2000]  if 'distance'        in group.columns else group.iloc[0:0]

            sire_stats[sire_name][f'{sire_type}_turf_win_rate']  = _wr(turf_g)
            sire_stats[sire_name][f'{sire_type}_dirt_win_rate']  = _wr(dirt_g)
            sire_stats[sire_name][f'{sire_type}_heavy_win_rate'] = _wr(heavy_g)
            sire_stats[sire_name][f'{sire_type}_short_win_rate'] = _wr(short_g)
            sire_stats[sire_name][f'{sire_type}_long_win_rate']  = _wr(long_g)

    return sire_stats

def calculate_trainer_jockey_stats(df_history):
    """調教師・騎手の成績を計算（訓練期間のデータのみ）"""
    stats = {'trainer': {}, 'jockey': {}, 'jockey_track': {}}

    df_calc = df_history.copy()
    df_calc['rank'] = pd.to_numeric(df_calc['rank'], errors='coerce')
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

    # Phase R2: 騎手×競馬場統計 (B-8)
    if '騎手' in df_finished.columns and 'track_name' in df_finished.columns:
        for (jockey_name, track_name), grp in df_finished.groupby(['騎手', 'track_name']):
            key = f"{jockey_name}_{track_name}"
            ranks = pd.to_numeric(grp['rank'], errors='coerce').dropna()
            total = len(ranks)
            stats['jockey_track'][key] = {
                'win_rate':  (ranks == 1).sum() / total if total > 0 else 0.0,
                'top3_rate': (ranks <= 3).sum() / total if total > 0 else 0.0,
                'starts': total
            }

    return stats

# ===================================================================
# 特徴量計算（リーケージ排除版）
# ===================================================================

def calculate_horse_features_safe(
    horse_id, df_all, cutoff_date, sire_stats_dict, trainer_jockey_stats,
    trainer_name=None, jockey_name=None,
    race_track=None, race_distance=None, race_course_type=None,
    race_track_condition=None, current_frame=None,
    race_id=None,
    horse_kiryou=None, horse_seire=None, horse_weight_str=None
):
    """
    馬の特徴量を計算（リーケージ完全排除版）

    Args:
        horse_id: 馬ID
        df_all: 全レースデータ
        cutoff_date: カットオフ日付 ('YYYY-MM-DD')
        sire_stats_dict: 種牡馬統計dict
        trainer_jockey_stats: 調教師・騎手統計dict
        ...その他レース情報

    Returns:
        dict: 特徴量dict または None
    """
    try:
        horse_id_num = float(horse_id)
    except:
        return None

    # cutoff_date より前のレースのみ取得（リーケージ防止）
    cutoff_dt = pd.to_datetime(cutoff_date, errors='coerce')
    if pd.isna(cutoff_dt):
        return None

    # 日付正規化（呼び出し側で事前に実行されていることを期待）
    # df_all = df_all.copy()  # パフォーマンス最適化: コピー不要
    if 'date_normalized' not in df_all.columns:
        df_all['date_normalized'] = df_all['date'].apply(normalize_date)

    df_dates = pd.to_datetime(df_all['date_normalized'], errors='coerce')

    # レース除外 + 日付フィルタ
    if race_id:
        try:
            race_id_int = int(race_id)
            horse_races = df_all[
                (df_all['horse_id'] == horse_id_num) &
                (df_all['race_id'] != race_id_int) &
                (df_dates < cutoff_dt)
            ].copy()
        except:
            horse_races = df_all[
                (df_all['horse_id'] == horse_id_num) &
                (df_dates < cutoff_dt)
            ].copy()
    else:
        horse_races = df_all[
            (df_all['horse_id'] == horse_id_num) &
            (df_dates < cutoff_dt)
        ].copy()

    # 日付でソート
    if len(horse_races) > 0:
        horse_races = horse_races.sort_values('date_normalized', ascending=True)

    features = {}

    # ============================================================
    # 基本統計（DBに既にある値を使用、なければ計算）
    # ============================================================
    if len(horse_races) > 0:
        latest = horse_races.iloc[-1]

        # 基本成績
        features['total_starts'] = latest.get('total_starts', len(horse_races))
        features['total_win_rate'] = latest.get('total_win_rate', 0.0)
        features['total_earnings'] = latest.get('total_earnings', 0)
        features['turf_win_rate'] = latest.get('turf_win_rate', 0.0)
        features['dirt_win_rate'] = latest.get('dirt_win_rate', 0.0)

        # 距離適性（race_distance ±200m 以内の勝率）
        if race_distance is not None and 'distance' in horse_races.columns:
            try:
                dist_num = float(race_distance)
                hr_dist = pd.to_numeric(horse_races['distance'], errors='coerce')
                similar_races = horse_races[(hr_dist >= dist_num - 200) & (hr_dist <= dist_num + 200)].copy()
                if len(similar_races) > 0:
                    similar_races['rank'] = pd.to_numeric(similar_races['rank'], errors='coerce')
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

        # 前走着順
        prev_rank_val = latest.get('rank')
        features['prev_race_rank'] = pd.to_numeric(prev_rank_val, errors='coerce')
        if pd.isna(features['prev_race_rank']):
            features['prev_race_rank'] = 99

        # 前走からの日数
        features['days_since_last_race'] = latest.get('days_since_last_race', 365)

        # 通過順平均
        features['avg_passage_position'] = latest.get('avg_passage_position', 0.0)

        # 上がり3F平均（Agariカラムから計算。なければフォールバック）
        if 'Agari' in horse_races.columns:
            _agari = pd.to_numeric(horse_races['Agari'], errors='coerce').dropna()
            _agari = _agari[_agari >= 25]  # 25秒未満の異常値（ハロンタイム等）を除外
            features['avg_last_3f'] = float(_agari.mean()) if len(_agari) > 0 else 0.0
        else:
            features['avg_last_3f'] = latest.get('avg_last_3f', 0.0)

        # 重賞出走回数
        features['grade_race_starts'] = latest.get('grade_race_starts', 0)

        # 血統（種牡馬成績）
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

        # C-1: 血統細分化（Phase R2）
        _C1_KEYS = ['turf_win_rate', 'dirt_win_rate', 'heavy_win_rate', 'short_win_rate', 'long_win_rate']
        for _k in _C1_KEYS:
            features[f'father_{_k}']        = sire_stats_dict.get(father, {}).get(f'father_{_k}', 0.0) if father else 0.0
            features[f'mother_father_{_k}'] = sire_stats_dict.get(mother_father, {}).get(f'mother_father_{_k}', 0.0) if mother_father else 0.0

        # ============================================================
        # Phase 10特徴量: 着差、脚質、クラス
        # ============================================================

        # 1. 着差関連
        if '着差' in horse_races.columns:
            diffs = horse_races['着差'].apply(parse_diff_to_seconds)
            features['avg_diff_seconds'] = diffs.mean() if len(diffs) > 0 else 1.0
            features['min_diff_seconds'] = diffs.min() if len(diffs) > 0 else 1.0
            features['prev_diff_seconds'] = parse_diff_to_seconds(latest.get('着差', ''))
        else:
            features['avg_diff_seconds'] = 1.0
            features['min_diff_seconds'] = 1.0
            features['prev_diff_seconds'] = 1.0

        # C-4: class_adjusted_diff は訓練データで avg_diff_seconds と88.7%同値のため削除

        # 2. 通過順関連（脚質）
        if '通過' in horse_races.columns:
            first_corners = []
            last_corners = []
            for _, row in horse_races.iterrows():
                passage = parse_passage(row.get('通過', ''))
                if len(passage) > 0:
                    first_corners.append(passage[0])
                    last_corners.append(passage[-1])

            if first_corners:
                features['avg_first_corner'] = np.mean(first_corners)
                features['avg_last_corner'] = np.mean(last_corners)
                features['avg_position_change'] = np.mean([f - l for f, l in zip(first_corners, last_corners)])
                # Phase R5: コーナー特徴量（_fixed版・sign修正）
                _pc_v2 = np.mean([l - f for f, l in zip(first_corners, last_corners)])  # last-first（負=前進）
                features['avg_first_corner_fixed'] = features['avg_first_corner']
                features['avg_last_corner_fixed']  = features['avg_last_corner']
                features['avg_position_change_v2'] = _pc_v2
                _fc_r5 = features['avg_first_corner']
                if _fc_r5 <= 2.5:
                    features['running_style_v2'] = 1   # 逃げ
                elif _fc_r5 <= 5.0:
                    features['running_style_v2'] = 2   # 先行
                elif _pc_v2 <= -3.0:
                    features['running_style_v2'] = 4   # 追い込み
                else:
                    features['running_style_v2'] = 3   # 差し
            else:
                features['avg_first_corner'] = 5.0
                features['avg_last_corner'] = 5.0
                features['avg_position_change'] = 0.0
                features['avg_first_corner_fixed'] = 5.0
                features['avg_last_corner_fixed']  = 5.0
                features['avg_position_change_v2'] = 0.0
                features['running_style_v2'] = 3
        else:
            features['avg_first_corner'] = 5.0
            features['avg_last_corner'] = 5.0
            features['avg_position_change'] = 0.0
            features['avg_first_corner_fixed'] = 5.0
            features['avg_last_corner_fixed']  = 5.0
            features['avg_position_change_v2'] = 0.0
            features['running_style_v2'] = 3

        # B-6: 脚質カテゴリ（running_style_category優先・フォールバックは通過順）
        _cat_map = {'front_runner': 1, 'stalker': 2, 'midpack': 3, 'closer': 4}
        if 'running_style_category' in horse_races.columns:
            _valid_cats = horse_races['running_style_category'].dropna()
            _valid_cats = _valid_cats[_valid_cats.isin(_cat_map.keys())]
            if len(_valid_cats) > 0:
                features['running_style'] = _cat_map.get(_valid_cats.mode().iloc[0], 3)
            else:
                features['running_style'] = 3  # デフォルト: midpack
        else:
            _fc = features.get('avg_first_corner', 5.0)
            _lc = features.get('avg_last_corner', 5.0)
            if _fc <= 2.5:
                features['running_style'] = 1
            elif _fc <= 4.5:
                features['running_style'] = 2
            elif _lc < _fc - 1.5:
                features['running_style'] = 3
            else:
                features['running_style'] = 4

        # C-5: pace_preference は avg_position_change と完全同値のため削除

        # C-5: 末脚強度 — 3ポジション以上前進した割合（Phase R2）
        _strong = 0
        _total_p = 0
        if '通過' in horse_races.columns:
            for _, _r in horse_races.iterrows():
                _parts = [p for p in re.split(r'[-\s]', str(_r.get('通過', ''))) if p.isdigit()]
                if len(_parts) >= 2:
                    if int(_parts[0]) - int(_parts[-1]) >= 3:
                        _strong += 1
                    _total_p += 1
        features['finish_strength'] = _strong / _total_p if _total_p > 0 else 0.0

        # 3. クラス移動
        if race_track:
            # 現在のレースクラス vs 前走クラス
            # race_trackには実はrace_nameが入ってくることが多いので注意
            # 本来はrace_name引数が必要だが、ここでは簡易的に
            features['class_change'] = 0
            features['current_class'] = 3
        else:
            features['class_change'] = 0
            features['current_class'] = 3

        # ============================================================
        # Phase R1 追加特徴量 (B-1, B-5)
        # ============================================================

        # B-1: heavy_track_win_rate（道悪[重・不良]での過去勝率）
        if 'track_condition' in horse_races.columns:
            heavy_races = horse_races[horse_races['track_condition'].isin(['重', '不良'])].copy()
            heavy_races['rank'] = pd.to_numeric(heavy_races['rank'], errors='coerce')
            heavy_finished = heavy_races[heavy_races['rank'].notna()]
            features['heavy_track_win_rate'] = (
                (heavy_finished['rank'] == 1).sum() / len(heavy_finished)
                if len(heavy_finished) > 0 else 0.0
            )
        else:
            features['heavy_track_win_rate'] = latest.get('heavy_track_win_rate', 0.0)

        # Phase R5: slightly_heavy_win_rate（稍重馬場勝率）
        if 'track_condition' in horse_races.columns:
            _sh = horse_races[horse_races['track_condition'].str.strip().isin(['稍重'])].copy()
            _sh['rank_n'] = pd.to_numeric(_sh['rank'], errors='coerce')
            _sh_fin = _sh[_sh['rank_n'].notna()]
            features['slightly_heavy_win_rate'] = (
                (_sh_fin['rank_n'] == 1).sum() / len(_sh_fin) if len(_sh_fin) > 0 else 0.0
            )
        else:
            features['slightly_heavy_win_rate'] = 0.0

        # B-9: good_track_win_rate（良馬場勝率）（Phase R2）
        if 'track_condition' in horse_races.columns:
            good_races = horse_races[horse_races['track_condition'] == '良'].copy()
            good_races['rank'] = pd.to_numeric(good_races['rank'], errors='coerce')
            good_finished = good_races[good_races['rank'].notna()]
            features['good_track_win_rate'] = (
                (good_finished['rank'] == 1).sum() / len(good_finished)
                if len(good_finished) > 0 else 0.0
            )
        else:
            features['good_track_win_rate'] = 0.0

        # B-5: distance_change（前走との距離差）
        if race_distance is not None:
            try:
                prev_dist = pd.to_numeric(horse_races.iloc[-1].get('distance'), errors='coerce')
                features['distance_change'] = (
                    float(race_distance) - float(prev_dist)
                    if pd.notna(prev_dist) else 0.0
                )
            except Exception:
                features['distance_change'] = 0.0
        else:
            features['distance_change'] = 0.0

        # B-7: 直近3走トレンド（Phase R2）
        if len(horse_races) >= 2:
            _recent = horse_races.tail(3).copy()
            _recent['rank_num'] = pd.to_numeric(_recent['rank'], errors='coerce')
            _fin = _recent[_recent['rank_num'].between(1, 18)]
            if len(_fin) >= 2:
                features['recent_3race_improvement'] = float(
                    _fin['rank_num'].iloc[0] - _fin['rank_num'].iloc[-1]
                )
            else:
                features['recent_3race_improvement'] = 0.0
        else:
            features['recent_3race_improvement'] = 0.0

        # Phase R6: prev_agari_relative（前走上がり3F vs 同レースフィールド平均）
        try:
            if len(horse_races) > 0 and 'Agari' in horse_races.columns and df_all is not None:
                # 前走レースの Agari 取得
                _prev = horse_races.sort_values('date').iloc[-1]
                _prev_rid = _prev.get('race_id')
                _prev_agari = pd.to_numeric(_prev.get('Agari'), errors='coerce')
                if pd.notna(_prev_agari) and 20.0 <= _prev_agari <= 50.0 and _prev_rid is not None:
                    # 同レースの全馬 Agari 平均
                    try:
                        _prev_rid_val = float(_prev_rid)
                        _field = df_all[df_all['race_id'] == _prev_rid_val]['Agari']
                    except Exception:
                        _prev_rid_str = str(_prev_rid).strip()
                        _field = df_all[df_all['race_id'].astype(str).str.strip() == _prev_rid_str]['Agari']
                    _field_agari = pd.to_numeric(_field, errors='coerce')
                    _field_valid = _field_agari[(20.0 <= _field_agari) & (_field_agari <= 50.0)]
                    if len(_field_valid) >= 2:
                        features['prev_agari_relative'] = float(_prev_agari - _field_valid.mean())
                    else:
                        features['prev_agari_relative'] = 0.0
                else:
                    features['prev_agari_relative'] = 0.0
            else:
                features['prev_agari_relative'] = 0.0
        except Exception:
            features['prev_agari_relative'] = 0.0

    else:
        # データなし（デビュー前や新馬）
        features['total_starts'] = 0
        features['total_win_rate'] = 0.0
        features['total_earnings'] = 0
        features['turf_win_rate'] = 0.0
        features['dirt_win_rate'] = 0.0
        features['distance_similar_win_rate'] = 0.0
        features['prev_race_rank'] = 99
        features['days_since_last_race'] = 365
        features['avg_passage_position'] = 0.0
        features['avg_last_3f'] = 0.0
        features['grade_race_starts'] = 0
        features['father_win_rate'] = 0.0
        features['father_top3_rate'] = 0.0
        features['mother_father_win_rate'] = 0.0
        features['mother_father_top3_rate'] = 0.0
        features['avg_diff_seconds'] = 1.0
        features['min_diff_seconds'] = 1.0
        features['prev_diff_seconds'] = 1.0
        features['avg_first_corner'] = 5.0
        features['avg_last_corner'] = 5.0
        features['avg_position_change'] = 0.0
        features['class_change'] = 0
        features['current_class'] = 3
        features['heavy_track_win_rate'] = 0.0
        features['distance_change'] = 0.0
        # Phase R2 defaults
        features['father_turf_win_rate']        = 0.0
        features['father_dirt_win_rate']        = 0.0
        features['father_heavy_win_rate']       = 0.0
        features['father_short_win_rate']       = 0.0
        features['father_long_win_rate']        = 0.0
        features['mother_father_turf_win_rate']  = 0.0
        features['mother_father_dirt_win_rate']  = 0.0
        features['mother_father_heavy_win_rate'] = 0.0
        features['mother_father_short_win_rate'] = 0.0
        features['mother_father_long_win_rate']  = 0.0
        features['running_style']               = 3
        features['recent_3race_improvement']    = 0.0
        features['good_track_win_rate']         = 0.0
        features['finish_strength']             = 0.0
        # Phase R5 defaults
        features['avg_first_corner_fixed'] = 5.0
        features['avg_last_corner_fixed']  = 5.0
        features['avg_position_change_v2'] = 0.0
        features['running_style_v2']       = 3
        features['slightly_heavy_win_rate'] = 0.0
        # Phase R6 defaults
        features['prev_agari_relative'] = 0.0

    # ============================================================
    # Phase R1 追加特徴量 (B-2, B-3, B-4) — 現レース情報から取得
    # ============================================================

    # B-2: kiryou（斤量）
    if horse_kiryou is not None:
        try:
            features['kiryou'] = float(horse_kiryou)
        except (ValueError, TypeError):
            features['kiryou'] = 55.0
    else:
        features['kiryou'] = 55.0

    # B-3: is_female（牝馬フラグ）・horse_age（馬齢）
    if horse_seire:
        seire = str(horse_seire)
        features['is_female'] = 1 if seire.startswith('牝') else 0
        m = re.search(r'\d+', seire)
        features['horse_age'] = int(m.group()) if m else 0
    else:
        features['is_female'] = 0
        features['horse_age'] = 0

    # B-4: horse_weight（馬体重）・weight_change（前走比増減）
    if horse_weight_str:
        m = re.match(r'(\d+)\(([+-]?\d+)\)', str(horse_weight_str))
        if m:
            # "460(+2)" 形式（GUI スクレイピング）
            features['horse_weight'] = int(m.group(1))
            features['weight_change'] = int(m.group(2))
        else:
            # 数値のみ（標準化DB: horse_weight カラム）→ 履歴から増減を計算
            num_m = re.search(r'\d+', str(horse_weight_str))
            if num_m:
                current_w = int(num_m.group())
                features['horse_weight'] = current_w
                if len(horse_races) > 0 and 'horse_weight' in horse_races.columns:
                    try:
                        prev_w = pd.to_numeric(horse_races.iloc[-1].get('horse_weight'), errors='coerce')
                        features['weight_change'] = int(current_w - prev_w) if pd.notna(prev_w) else 0
                    except Exception:
                        features['weight_change'] = 0
                else:
                    features['weight_change'] = 0
            else:
                features['horse_weight'] = 0
                features['weight_change'] = 0
    else:
        features['horse_weight'] = 0
        features['weight_change'] = 0

    # ============================================================
    # 調教師・騎手成績
    # ============================================================
    if trainer_name and trainer_name in trainer_jockey_stats['trainer']:
        t_stats = trainer_jockey_stats['trainer'][trainer_name]
        features['trainer_win_rate'] = t_stats['win_rate']
        features['trainer_top3_rate'] = t_stats['top3_rate']
        features['trainer_starts'] = t_stats['starts']
    else:
        features['trainer_win_rate'] = 0.0
        features['trainer_top3_rate'] = 0.0
        features['trainer_starts'] = 0

    if jockey_name and jockey_name in trainer_jockey_stats['jockey']:
        j_stats = trainer_jockey_stats['jockey'][jockey_name]
        features['jockey_win_rate'] = j_stats['win_rate']
        features['jockey_top3_rate'] = j_stats['top3_rate']
        features['jockey_starts'] = j_stats['starts']
    else:
        features['jockey_win_rate'] = 0.0
        features['jockey_top3_rate'] = 0.0
        features['jockey_starts'] = 0

    # B-8: 騎手×競馬場統計（Phase R2）
    _jt_key = f"{jockey_name}_{race_track}" if jockey_name and race_track else None
    _jt_stats = trainer_jockey_stats.get('jockey_track', {})
    if _jt_key and _jt_key in _jt_stats:
        features['jockey_track_win_rate']  = _jt_stats[_jt_key]['win_rate']
        features['jockey_track_top3_rate'] = _jt_stats[_jt_key]['top3_rate']
    else:
        features['jockey_track_win_rate']  = features.get('jockey_win_rate', 0.0)
        features['jockey_track_top3_rate'] = features.get('jockey_top3_rate', 0.0)

    # ============================================================
    # コース・馬場条件
    # ============================================================
    # コース適性（過去の同コースでの成績）
    if race_track and 'track_name' in horse_races.columns and len(horse_races) > 0:
        track_races = horse_races[horse_races['track_name'] == race_track]
        if len(track_races) > 0:
            track_races['rank'] = pd.to_numeric(track_races['rank'], errors='coerce')
            track_finished = track_races[track_races['rank'].notna()]
            if len(track_finished) > 0:
                features['track_win_rate'] = (track_finished['rank'] == 1).sum() / len(track_finished)
                features['track_top3_rate'] = (track_finished['rank'] <= 3).sum() / len(track_finished)
            else:
                features['track_win_rate'] = 0.0
                features['track_top3_rate'] = 0.0
        else:
            features['track_win_rate'] = 0.0
            features['track_top3_rate'] = 0.0
    else:
        features['track_win_rate'] = 0.0
        features['track_top3_rate'] = 0.0

    # 距離
    if race_distance:
        try:
            features['race_distance'] = float(race_distance)
        except:
            features['race_distance'] = 1600
    else:
        features['race_distance'] = 1600

    # コース種別（芝/ダート）
    if race_course_type:
        features['is_turf'] = 1 if '芝' in race_course_type else 0
        features['is_dirt'] = 1 if 'ダート' in race_course_type else 0
    else:
        features['is_turf'] = 0
        features['is_dirt'] = 0

    # 馬場状態
    if race_track_condition:
        features['is_良'] = 1 if race_track_condition == '良' else 0
        features['is_稍重'] = 1 if race_track_condition == '稍重' else 0
        features['is_重'] = 1 if race_track_condition == '重' else 0
        features['is_不良'] = 1 if race_track_condition == '不良' else 0
    else:
        features['is_良'] = 1
        features['is_稍重'] = 0
        features['is_重'] = 0
        features['is_不良'] = 0

    # 枠番
    if current_frame:
        try:
            features['frame_number'] = int(current_frame)
        except:
            features['frame_number'] = 4
    else:
        features['frame_number'] = 4

    # ============================================================
    # Phase R7: 枠番バイアス + 騎手交代特徴量
    # ============================================================

    # waku_win_rate: 枠番×競馬場×距離帯×コース種別の歴史的勝率
    try:
        _waku = int(current_frame) if current_frame else 0
        _dist = float(race_distance) if race_distance else 0.0
        _ct   = str(race_course_type) if race_course_type else ''
        _tk   = str(race_track) if race_track else ''
        if _dist <= 1400:
            _db = 'short'
        elif _dist <= 1800:
            _db = 'mid'
        else:
            _db = 'long'
        _key1 = f'{_tk}|{_ct}|{_db}|{_waku}'
        _key2 = f'{_ct}|{_db}|{_waku}'
        if _key1 in _waku_lookup:
            features['waku_win_rate'] = _waku_lookup[_key1]
        elif _key2 in _waku_fallback:
            features['waku_win_rate'] = _waku_fallback[_key2]
        else:
            features['waku_win_rate'] = _waku_global_avg
    except Exception:
        features['waku_win_rate'] = _waku_global_avg

    # jockey_changed + jockey_change_quality
    try:
        _prev_jockey = None
        if len(horse_races) > 0:
            _jcol = None
            for _c in ['JockeyName', '騎手', 'jockey_name']:
                if _c in horse_races.columns:
                    _jcol = _c
                    break
            if _jcol:
                _last = horse_races.sort_values('date_normalized').iloc[-1]
                _prev_jockey = str(_last[_jcol]) if pd.notna(_last[_jcol]) else None

        if _prev_jockey is None:
            features['jockey_changed'] = 0.0
            features['jockey_change_quality'] = 0.0
        else:
            features['jockey_changed'] = 1.0 if (jockey_name and jockey_name != _prev_jockey) else 0.0
            _cur_wr  = trainer_jockey_stats.get('jockey', {}).get(jockey_name or '', {}).get('win_rate', _waku_global_avg)
            _prev_wr = trainer_jockey_stats.get('jockey', {}).get(_prev_jockey, {}).get('win_rate', _waku_global_avg)
            features['jockey_change_quality'] = float(_cur_wr - _prev_wr)
    except Exception:
        features['jockey_changed'] = 0.0
        features['jockey_change_quality'] = 0.0

    # ============================================================
    # Phase R8: 血統×競馬場 / 近況 / 馬個体×条件 特徴量
    # ============================================================

    # B: father_track_win_rate / mother_father_track_win_rate
    try:
        _father = str(sire_stats_dict.get('_father_name_', '')) if sire_stats_dict else ''
        # sire_statsに父馬名が入っていないので horse_races から取得
        _father_name = ''
        _mf_name = ''
        if len(horse_races) > 0:
            for _fc in ['father', 'Father']:
                if _fc in horse_races.columns:
                    _fv = horse_races[_fc].dropna()
                    if len(_fv) > 0:
                        _father_name = str(_fv.iloc[-1])
                    break
            for _mc in ['mother_father', 'MotherFather']:
                if _mc in horse_races.columns:
                    _mv = horse_races[_mc].dropna()
                    if len(_mv) > 0:
                        _mf_name = str(_mv.iloc[-1])
                    break
        _tk = str(race_track) if race_track else ''
        _f_key  = f'{_father_name}||{_tk}'
        _fo_key = f'{_father_name}||__overall__'
        _m_key  = f'{_mf_name}||{_tk}'
        _mo_key = f'{_mf_name}||__overall__'
        features['father_track_win_rate'] = float(
            _sire_track_father.get(_f_key,
            _sire_track_father.get(_fo_key, _sire_track_global)))
        features['mother_father_track_win_rate'] = float(
            _sire_track_mf.get(_m_key,
            _sire_track_mf.get(_mo_key, _sire_track_global)))
    except Exception:
        features['father_track_win_rate']        = _sire_track_global
        features['mother_father_track_win_rate'] = _sire_track_global

    # C: consecutive_losses / form_trend / best_distance_diff
    try:
        if len(horse_races) > 0:
            _hr_sorted = horse_races.sort_values('date_normalized')
            _ranks = pd.to_numeric(_hr_sorted.get('Rank', _hr_sorted.get('rank', None)), errors='coerce').fillna(99)

            # consecutive_losses: 直近の連続着外（3着以内なし）
            _c_loss = 0
            for _r in reversed(_ranks.values.tolist()):
                if _r <= 3:
                    break
                _c_loss += 1
            features['consecutive_losses'] = float(_c_loss)

            # form_trend: 直近3走の着順変化（正=改善）
            _recent = _ranks.values[-3:] if len(_ranks) >= 3 else _ranks.values
            if len(_recent) >= 2:
                features['form_trend'] = float(_recent[0] - _recent[-1]) / max(len(_recent)-1, 1)
            else:
                features['form_trend'] = 0.0

            # best_distance_diff: 得意距離帯との乖離
            _dists = pd.to_numeric(_hr_sorted.get('distance', None), errors='coerce').dropna()
            _is_win_hr = (_ranks <= 1).astype(float)
            if len(_dists) >= 3:
                _d_buckets = ((_dists // 200) * 200).astype(int)
                _dist_df = pd.DataFrame({'bucket': _d_buckets.values, 'win': _is_win_hr.values})
                _dist_agg = _dist_df.groupby('bucket')['win'].agg(['sum','count'])
                _dist_agg = _dist_agg[_dist_agg['count'] >= 3]
                if len(_dist_agg) > 0:
                    _best_d = int(_dist_agg['sum'].div(_dist_agg['count']).idxmax())
                    _cur_d  = float(race_distance) if race_distance else _best_d
                    features['best_distance_diff'] = abs(_cur_d - _best_d) / 1000.0
                else:
                    features['best_distance_diff'] = 0.0
            else:
                features['best_distance_diff'] = 0.0
        else:
            features['consecutive_losses'] = 0.0
            features['form_trend']         = 0.0
            features['best_distance_diff'] = 0.0
    except Exception:
        features['consecutive_losses'] = 0.0
        features['form_trend']         = 0.0
        features['best_distance_diff'] = 0.0

    # D: horse_waku_win_rate / large_field_win_rate
    try:
        if len(horse_races) > 0:
            _hr_sorted = horse_races.sort_values('date_normalized')
            _hr_ranks  = pd.to_numeric(_hr_sorted.get('Rank', _hr_sorted.get('rank', None)), errors='coerce').fillna(99)
            _hr_is_win = (_hr_ranks == 1).astype(float)

            # horse_waku_win_rate: この馬の現在枠番での過去勝率
            _waku_col = None
            for _wc in ['Waku', 'waku', '枠番']:
                if _wc in _hr_sorted.columns:
                    _waku_col = _wc
                    break
            if _waku_col and current_frame:
                _hw = pd.to_numeric(_hr_sorted[_waku_col], errors='coerce')
                _same_waku = (_hw == int(current_frame))
                if _same_waku.sum() >= 2:
                    features['horse_waku_win_rate'] = float(_hr_is_win[_same_waku].mean())
                else:
                    features['horse_waku_win_rate'] = _sire_track_global
            else:
                features['horse_waku_win_rate'] = _sire_track_global

            # large_field_win_rate: 12頭以上のレースでの過去勝率
            # field_size相当を race_id の group count で推定（近似）
            # 簡易版: horse_races のうちランダムサンプルで推定は困難なので
            # 近似として horses_count列があれば使用、なければグローバル値
            _fsize_col = None
            for _fsc in ['field_size', 'race_field_size', 'horses_count']:
                if _fsc in _hr_sorted.columns:
                    _fsize_col = _fsc
                    break
            if _fsize_col:
                _fsizes = pd.to_numeric(_hr_sorted[_fsize_col], errors='coerce').fillna(0)
                _large = (_fsizes >= 12)
                if _large.sum() >= 3:
                    features['large_field_win_rate'] = float(_hr_is_win[_large].mean())
                else:
                    features['large_field_win_rate'] = float(_hr_is_win.mean()) if len(_hr_is_win) > 0 else _sire_track_global
            else:
                # field_size列なし → 全体勝率で近似
                features['large_field_win_rate'] = float(_hr_is_win.mean()) if len(_hr_is_win) > 0 else _sire_track_global
        else:
            features['horse_waku_win_rate']  = _sire_track_global
            features['large_field_win_rate'] = _sire_track_global
    except Exception:
        features['horse_waku_win_rate']  = _sire_track_global
        features['large_field_win_rate'] = _sire_track_global

    return features

# ===================================================================
# メイン処理
# ===================================================================

if __name__ == '__main__':
    print("[1/6] データ読み込み中...")
    train_df = pd.read_csv('phase13_train_2020_2022.csv', low_memory=False)
    val_df = pd.read_csv('phase13_val_2023.csv', low_memory=False)
    test_df = pd.read_csv('phase13_test_2024.csv', low_memory=False)

    print(f"  訓練: {len(train_df):,}レース")
    print(f"  検証: {len(val_df):,}レース")
    print(f"  テスト: {len(test_df):,}レース")
    print()

    # 全データ結合（統計計算用）
    df_all = pd.concat([train_df, val_df, test_df], ignore_index=True)

    print("[2/6] 訓練期間データで統計計算中...")
    # 種牡馬・調教師・騎手の統計は訓練期間のみで計算
    sire_stats = calculate_sire_stats(train_df)
    trainer_jockey_stats = calculate_trainer_jockey_stats(train_df)
    print(f"  種牡馬統計: {len(sire_stats)}頭")
    print(f"  調教師統計: {len(trainer_jockey_stats['trainer'])}人")
    print(f"  騎手統計: {len(trainer_jockey_stats['jockey'])}人")
    print()

    print("[3/6] 訓練データの特徴量計算...")
    # ※この処理は非常に時間がかかる可能性があるため、
    #   実際には並列処理や進捗表示が必要
    print("  実装中: テスト実行のため、最初の100レースのみ処理します")
    print()

    # テスト実装: 最初の100レースの最初の馬のみ
    sample_races = train_df.head(100)
    for idx, row in sample_races.iterrows():
        race_id = row['race_id']
        horse_id = row['horse_id']
        cutoff_date = normalize_date(row['date'])

        if pd.isna(cutoff_date) or pd.isna(horse_id):
            continue

        features = calculate_horse_features_safe(
            horse_id, df_all, cutoff_date, sire_stats, trainer_jockey_stats,
            trainer_name=row.get('調教師'),
            jockey_name=row.get('騎手'),
            race_track=row.get('track_name'),
            race_distance=row.get('distance'),
            race_course_type=row.get('course_type'),
            race_track_condition=row.get('track_condition'),
            current_frame=row.get('waku'),
            race_id=race_id
        )

        if features:
            print(f"  [OK] race_id={race_id}, horse_id={horse_id}: {len(features)}個の特徴量")
            # 特徴量の一部を表示
            print(f"       total_starts={features['total_starts']}, total_win_rate={features['total_win_rate']:.3f}")
            break  # 1件のみ表示

    print()
    print("[4/6] 検証データの特徴量計算...")
    print("  スキップ（実装例のみ）")
    print()

    print("[5/6] テストデータの特徴量計算...")
    print("  スキップ（実装例のみ）")
    print()

    print("[6/6] 完了")
    print()
    print("=" * 80)
    print("  特徴量エンジニアリング（テスト）完了")
    print("=" * 80)
    print()
    print("【次のステップ】")
    print("1. 全レースに対して特徴量を計算")
    print("2. 特徴量をCSVに保存")
    print("   - phase13_train_features.csv")
    print("   - phase13_val_features.csv")
    print("   - phase13_test_features.csv")
    print("3. モデル訓練を実行")
    print()
