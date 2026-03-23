# -*- coding: utf-8 -*-
"""
calculate_features_r5.py — Phase R5: ペース・脚質特徴量を修正・追加

data/phase_r4/ CSVs を元に以下を追加して data/phase_r5/ に保存する。
フル再計算不要（数分〜10分程度）。

【修正・追加特徴量（計+7個、total 74個）】
  avg_first_corner_fixed  : 過去レースの1コーナー通過順平均（Passageから正しく計算）
  avg_last_corner_fixed   : 過去レースの最終コーナー通過順平均
  running_style_v2        : 修正脚質（avg_first_corner_fixedベース。77%差しバグを修正）
  slightly_heavy_win_rate : 稍重馬場勝率（従来は良/重の2値のみ）
  field_escape_count      : 出走馬中の逃げ・先行馬数（展開予測）
  field_pace_advantage    : この馬の脚質が展開上有利か（0〜1）
  avg_position_change_v2  : コーナー通過順の変化量（後方から追い込む度合い）

【使い方】
  py calculate_features_r5.py
  次: py train_phase_r5.py
"""
import os
import re
import pandas as pd
import numpy as np

IN_DIR  = 'data/phase_r4'
OUT_DIR = 'data/phase_r5'
ENRICHED_PATH = 'data/main/netkeiba_data_2020_2025_enriched.csv'

os.makedirs(OUT_DIR, exist_ok=True)

print('=' * 60)
print('  Phase R5: ペース・脚質特徴量 修正・追加')
print('=' * 60)

# ============================================================
# Step 1: enriched CSV から馬別・レース別ヒストリーを構築
# ============================================================
print('\n[1/5] enriched CSV 読み込み中...')
df_en = pd.read_csv(
    ENRICHED_PATH,
    usecols=['race_id', 'horse_id', 'date', 'Rank', 'Passage', 'track_condition'],
    low_memory=False,
)
print(f'  {len(df_en):,}行')

# race_id を文字列に統一
df_en['race_id']  = df_en['race_id'].astype(str).str.strip()
df_en['horse_id'] = df_en['horse_id'].astype(str).str.strip()
df_en['date']     = pd.to_datetime(df_en['date'], errors='coerce')
df_en = df_en.dropna(subset=['date']).sort_values(['horse_id', 'date'])

# ---- Passage パース：'4-4-3-3' → first_corner=4, last_corner=3 ----
def parse_passage_corners(s):
    """'4-4-3-3' → (first, last)。失敗時は (nan, nan)"""
    if pd.isna(s):
        return np.nan, np.nan
    parts = re.split(r'[-\s]', str(s).strip())
    nums = []
    for p in parts:
        try:
            nums.append(int(p))
        except ValueError:
            pass
    if len(nums) >= 2:
        return float(nums[0]), float(nums[-1])
    return np.nan, np.nan

print('[2/5] Passage をパース中（コーナー通過順位）...')
corners = df_en['Passage'].apply(parse_passage_corners)
df_en['first_corner'] = corners.apply(lambda x: x[0])
df_en['last_corner']  = corners.apply(lambda x: x[1])
df_en['pos_change']   = df_en['last_corner'] - df_en['first_corner']  # 負=前進

fc_valid = df_en['first_corner'].notna().sum()
print(f'  first_corner 有効: {fc_valid:,}件 / {len(df_en):,}件 '
      f'({fc_valid/len(df_en)*100:.1f}%)')
print(f'  first_corner 平均: {df_en["first_corner"].mean():.2f}  '
      f'中央値: {df_en["first_corner"].median():.2f}')

# ---- 稍重フラグ ----
SLIGHTLY_HEAVY_VALUES = {'稍重', '稍重 '}
df_en['is_slightly_heavy'] = df_en['track_condition'].isin(SLIGHTLY_HEAVY_VALUES).astype(int)

# ---- 勝利フラグ ----
df_en['Rank_num'] = pd.to_numeric(df_en['Rank'], errors='coerce')
df_en['is_win']   = (df_en['Rank_num'] == 1).astype(float)

# ============================================================
# Step 2: 馬別の累積（ルックバック）統計を計算
#   shift(1) で当該レースより前の情報のみを使う（データリーク防止）
# ============================================================
print('[3/5] 馬別ルックバック統計を計算中...')

def expanding_mean_shifted(series):
    """shift(1) した上で expanding().mean()（直前レースまでの平均）"""
    return series.shift(1).expanding().mean()

df_en = df_en.sort_values(['horse_id', 'date'])

grp = df_en.groupby('horse_id', sort=False)

df_en['avg_first_corner_fixed']  = grp['first_corner'].transform(expanding_mean_shifted)
df_en['avg_last_corner_fixed']   = grp['last_corner'].transform(expanding_mean_shifted)
df_en['avg_position_change_v2']  = grp['pos_change'].transform(expanding_mean_shifted)

# 稍重勝率（稍重レースでの勝利 / 稍重レース出走数）
df_en['sh_win_cum']   = grp['is_slightly_heavy'].transform(
    lambda s: (s * df_en.loc[s.index, 'is_win']).shift(1).expanding().sum()
)
df_en['sh_starts_cum'] = grp['is_slightly_heavy'].transform(
    lambda s: s.shift(1).expanding().sum()
)
df_en['slightly_heavy_win_rate'] = (
    df_en['sh_win_cum'] / df_en['sh_starts_cum'].clip(lower=1)
).where(df_en['sh_starts_cum'] > 0, other=np.nan)

# ---- running_style_v2（avg_first_corner_fixed ベース）----
def calc_running_style_v2(fc, pc):
    """
    fc = avg_first_corner_fixed  (NaN → 3=midpack)
    pc = avg_position_change_v2  (負=前進, 正=後退)
    1=逃げ  2=先行  3=差し  4=追い込み
    """
    if pd.isna(fc):
        return 3
    if fc <= 2.5:
        return 1  # 逃げ
    if fc <= 5.0:
        return 2  # 先行
    if not pd.isna(pc) and pc <= -3.0:
        return 4  # 追い込み（3馬身以上前進）
    return 3  # 差し

df_en['running_style_v2'] = [
    calc_running_style_v2(fc, pc)
    for fc, pc in zip(df_en['avg_first_corner_fixed'], df_en['avg_position_change_v2'])
]

print('  running_style_v2 分布:')
for v, name in [(1,'逃げ'),(2,'先行'),(3,'差し'),(4,'追い込み')]:
    cnt = (df_en['running_style_v2'] == v).sum()
    pct = cnt / len(df_en) * 100
    print(f'    {v}={name}: {cnt:,}件 ({pct:.1f}%)')

# ---- 結合キー用カラムを整備 ----
horse_stats = df_en[[
    'race_id', 'horse_id',
    'avg_first_corner_fixed',
    'avg_last_corner_fixed',
    'avg_position_change_v2',
    'slightly_heavy_win_rate',
    'running_style_v2',
]].copy()

# ============================================================
# Step 3: フィールドレベル特徴量（展開予測）
#   各レースの逃げ・先行馬数 → ペース圧力
# ============================================================
print('[4/5] フィールドレベル展開特徴量を計算中...')

# running_style_v2 を race_id でグループ集計
escape_count = (
    horse_stats.assign(is_escape=lambda x: x['running_style_v2'].isin([1, 2]).astype(int))
    .groupby('race_id')['is_escape']
    .sum()
    .rename('field_escape_count')
    .reset_index()
)
horse_stats = horse_stats.merge(escape_count, on='race_id', how='left')

# ペース優位性: 逃げ・先行馬が少ない（≤2）なら先行有利、多い（≥5）なら差し有利
# この馬自身のスタイルと組み合わせてスコア化
def calc_pace_advantage(style, escape_cnt):
    """
    style: 1=逃,2=先,3=差,4=追
    escape_cnt: 出走馬中の逃げ・先行馬数
    returns: 0.0〜1.0（1=有利）
    """
    if pd.isna(escape_cnt):
        return 0.5
    ec = int(escape_cnt)
    # 逃げ・先行 → 少頭数のスローなら有利
    if style in (1, 2):
        return max(0.0, 1.0 - (ec - 1) * 0.15)
    # 差し・追い込み → ハイペース（先行多）なら有利
    if style in (3, 4):
        return min(1.0, 0.3 + (ec - 2) * 0.1)
    return 0.5

horse_stats['field_pace_advantage'] = [
    calc_pace_advantage(s, e)
    for s, e in zip(horse_stats['running_style_v2'], horse_stats['field_escape_count'])
]

print(f'  field_escape_count 平均: {horse_stats["field_escape_count"].mean():.2f}  '
      f'(逃げ・先行馬数/レース)')
print(f'  field_pace_advantage 平均: {horse_stats["field_pace_advantage"].mean():.3f}')

# ============================================================
# Step 4: 各 split CSV に結合して保存
# ============================================================
NEW_FEATS = [
    'avg_first_corner_fixed',
    'avg_last_corner_fixed',
    'avg_position_change_v2',
    'running_style_v2',
    'slightly_heavy_win_rate',
    'field_escape_count',
    'field_pace_advantage',
]

for split in ['train_features', 'val_features', 'test_features']:
    in_path  = os.path.join(IN_DIR,  f'{split}.csv')
    out_path = os.path.join(OUT_DIR, f'{split}.csv')

    if not os.path.exists(in_path):
        print(f'  SKIP: {in_path} が見つかりません')
        continue

    print(f'\n[5/5] [{split}] 結合・保存中...')
    df = pd.read_csv(in_path, low_memory=False)
    df['race_id']  = df['race_id'].astype(str).str.strip()
    df['horse_id'] = df['horse_id'].astype(str).str.strip()
    print(f'  読み込み: {len(df):,}行 × {len(df.columns)}列')

    # 結合前に既存の同名列を除去
    drop_cols = [c for c in NEW_FEATS if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    df = df.merge(
        horse_stats[['race_id', 'horse_id'] + NEW_FEATS],
        on=['race_id', 'horse_id'],
        how='left',
    )

    # デフォルト値で欠損を埋める
    defaults = {
        'avg_first_corner_fixed':  5.0,
        'avg_last_corner_fixed':   5.0,
        'avg_position_change_v2':  0.0,
        'running_style_v2':        3,
        'slightly_heavy_win_rate': 0.0,
        'field_escape_count':      3.0,
        'field_pace_advantage':    0.5,
    }
    for col, val in defaults.items():
        if col in df.columns:
            df[col] = df[col].fillna(val)

    # running_style_v2 の分布確認
    print('  running_style_v2 分布:')
    for v, name in [(1,'逃げ'),(2,'先行'),(3,'差し'),(4,'追い込み')]:
        cnt = (df['running_style_v2'] == v).sum()
        pct = cnt / len(df) * 100
        print(f'    {v}={name}: {cnt:,}件 ({pct:.1f}%)')

    print(f'  avg_first_corner_fixed 平均: {df["avg_first_corner_fixed"].mean():.2f}')
    print(f'  slightly_heavy_win_rate 有効: {(df["slightly_heavy_win_rate"] > 0).sum():,}件')

    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f'  → {out_path} 保存完了 ({len(df):,}行 × {len(df.columns)}列)')

print('\n' + '=' * 60)
print('Phase R5 特徴量CSV作成完了')
print(f'出力先: {OUT_DIR}/')
print(f'新特徴量 ({len(NEW_FEATS)}個): {NEW_FEATS}')
print('次: py train_phase_r5.py')
