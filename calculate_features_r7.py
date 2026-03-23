# -*- coding: utf-8 -*-
"""
calculate_features_r7.py — Phase R7: 枠番バイアス + 騎手交代特徴量

data/phase_r6/ CSVs を元に以下を追加して data/phase_r7/ に保存する。

【追加特徴量（計4個、total 71個）】
  waku_win_rate      : 枠番×競馬場×距離帯×コース種別の歴史的勝率
                       （阪神短距離芝で1枠7.6% vs 8枠3.5% などのバイアスを捕捉）
  field_waku_rank    : レース内での waku_win_rate 相対ランク（R4スタイル）
  jockey_changed     : 前走からの騎手交代フラグ（0=継続, 1=交代）
  jockey_change_quality: 新騎手勝率 - 旧騎手勝率（正=昇格, 負=降格）

【使い方】
  py calculate_features_r7.py
  次: py train_phase_r7.py
"""
import os
import re
import pandas as pd
import numpy as np

IN_DIR        = 'data/phase_r6'
OUT_DIR       = 'data/phase_r7'
ENRICHED_PATH = 'data/main/netkeiba_data_2020_2025_enriched.csv'

os.makedirs(OUT_DIR, exist_ok=True)

print('=' * 60)
print('  Phase R7: 枠番バイアス + 騎手交代特徴量')
print('=' * 60)

# ============================================================
# Step 1: enriched CSV 読み込み
# ============================================================
print('\n[1/5] enriched CSV 読み込み中...')
df_en = pd.read_csv(
    ENRICHED_PATH,
    usecols=['race_id', 'horse_id', 'date', 'Rank', 'Waku',
             'JockeyName', 'course_type', 'distance', 'track_name'],
    low_memory=False,
)
df_en['race_id']   = df_en['race_id'].astype(str).str.strip()
df_en['horse_id']  = df_en['horse_id'].astype(str).str.strip()
df_en['date']      = pd.to_datetime(df_en['date'], errors='coerce')
df_en['Rank_n']    = pd.to_numeric(df_en['Rank'], errors='coerce')
df_en['win']       = (df_en['Rank_n'] == 1).astype(float)
df_en['Waku']      = pd.to_numeric(df_en['Waku'], errors='coerce')
df_en['distance']  = pd.to_numeric(df_en['distance'], errors='coerce')
df_en = df_en.dropna(subset=['date'])
print(f'  {len(df_en):,}行')

# 距離帯: short≤1400, mid 1401-1800, long>1800
df_en['dist_bucket'] = pd.cut(
    df_en['distance'],
    bins=[0, 1400, 1800, 99999],
    labels=['short', 'mid', 'long'],
)

# ============================================================
# Step 2: 枠番バイアス (waku_win_rate) 計算
# ============================================================
print('\n[2/5] 枠番バイアス計算中...')

# グローバル平均（全2020-2025年）: 構造的特徴のため全期間平均を使用
# track_name × course_type × dist_bucket × Waku
waku_valid = df_en.dropna(subset=['Waku', 'dist_bucket', 'track_name', 'course_type']).copy()

waku_stats = (
    waku_valid
    .groupby(['track_name', 'course_type', 'dist_bucket', 'Waku'], observed=True)['win']
    .agg(['mean', 'count'])
    .reset_index()
)
waku_stats.columns = ['track_name', 'course_type', 'dist_bucket', 'Waku',
                       'waku_win_rate', 'waku_count']

# 件数が少ない場合（50件未満）はコース×距離帯レベルに fallback
waku_broad = (
    waku_valid
    .groupby(['course_type', 'dist_bucket', 'Waku'], observed=True)['win']
    .mean()
    .reset_index()
    .rename(columns={'win': 'waku_wr_broad'})
)
waku_stats = waku_stats.merge(waku_broad, on=['course_type', 'dist_bucket', 'Waku'], how='left')

# 50件未満はbroad値で補完
mask_low = waku_stats['waku_count'] < 50
waku_stats.loc[mask_low, 'waku_win_rate'] = waku_stats.loc[mask_low, 'waku_wr_broad']
waku_stats = waku_stats.drop(columns=['waku_wr_broad', 'waku_count'])

print(f'  waku_stats: {len(waku_stats):,}件 ({waku_stats["waku_win_rate"].notna().sum():,}有効)')
print(f'  waku_win_rate 平均: {waku_stats["waku_win_rate"].mean():.4f}')
print(f'  waku_win_rate 範囲: {waku_stats["waku_win_rate"].min():.4f} - {waku_stats["waku_win_rate"].max():.4f}')

# 最大バイアス条件確認
pivot = waku_stats.pivot_table(
    index=['track_name', 'dist_bucket', 'course_type'],
    columns='Waku',
    values='waku_win_rate',
    observed=True,
).dropna()
pivot['range'] = pivot.max(axis=1) - pivot.min(axis=1)
top5 = pivot.sort_values('range', ascending=False).head(5)
print('\n  枠番バイアス Top5条件:')
print(top5.round(3).to_string())

# ============================================================
# Step 3: 騎手交代特徴量計算
# ============================================================
print('\n[3/5] 騎手交代特徴量計算中...')

# 騎手グローバル勝率
jockey_wr = (
    df_en
    .dropna(subset=['JockeyName'])
    .groupby('JockeyName')['win']
    .agg(['mean', 'count'])
    .reset_index()
)
jockey_wr.columns = ['JockeyName', 'jockey_global_wr', 'jockey_global_cnt']
# 30件未満は信頼性低い → 全体平均 (~6.5%) で代替
global_avg_wr = df_en['win'].mean()
jockey_wr.loc[jockey_wr['jockey_global_cnt'] < 30, 'jockey_global_wr'] = global_avg_wr
print(f'  騎手ユニーク数: {len(jockey_wr):,}人')
print(f'  全体平均勝率: {global_avg_wr:.4f}')

# 馬別・日付順で前走騎手を取得
jockey_df = (
    df_en[['race_id', 'horse_id', 'date', 'JockeyName']]
    .dropna(subset=['JockeyName'])
    .sort_values(['horse_id', 'date'])
    .copy()
)
jockey_df['prev_jockey'] = jockey_df.groupby('horse_id')['JockeyName'].shift(1)
jockey_df['jockey_changed'] = (
    (jockey_df['JockeyName'] != jockey_df['prev_jockey']).astype(float)
)
# 初出走（prev_jockey が NaN）は 0.0 としてデフォルト
jockey_df.loc[jockey_df['prev_jockey'].isna(), 'jockey_changed'] = 0.0

# jockey_change_quality = 現在の騎手勝率 - 前走騎手勝率
jockey_df = jockey_df.merge(
    jockey_wr[['JockeyName', 'jockey_global_wr']].rename(columns={'jockey_global_wr': 'cur_wr'}),
    on='JockeyName', how='left',
)
jockey_df = jockey_df.merge(
    jockey_wr[['JockeyName', 'jockey_global_wr']].rename(columns={'jockey_global_wr': 'prv_wr'}),
    left_on='prev_jockey', right_on='JockeyName', how='left', suffixes=('', '_prv'),
)
jockey_df['jockey_change_quality'] = (
    jockey_df['cur_wr'].fillna(global_avg_wr) -
    jockey_df['prv_wr'].fillna(global_avg_wr)
)
# prev_jockeyがない(初出走)は0.0
jockey_df.loc[jockey_df['prev_jockey'].isna(), 'jockey_change_quality'] = 0.0

horse_jockey = jockey_df[['race_id', 'horse_id', 'jockey_changed', 'jockey_change_quality']].copy()

valid_changed = horse_jockey['jockey_changed'].notna().sum()
changed_rate  = horse_jockey['jockey_changed'].mean()
print(f'  jockey_changed 有効: {valid_changed:,}件, 交代率: {changed_rate*100:.1f}%')
print(f'  jockey_change_quality 平均: {horse_jockey["jockey_change_quality"].mean():.4f}')
print(f'  jockey_change_quality 範囲: {horse_jockey["jockey_change_quality"].min():.4f} - {horse_jockey["jockey_change_quality"].max():.4f}')

# ============================================================
# Step 4: 各 split CSV に結合して保存
# ============================================================
NEW_FEATS = [
    'waku_win_rate',
    'field_waku_rank',
    'jockey_changed',
    'jockey_change_quality',
]

DEFAULTS = {
    'waku_win_rate':        0.065,   # 全体平均勝率
    'field_waku_rank':      0.5,     # 中央順位
    'jockey_changed':       0.0,     # デフォルト: 継続
    'jockey_change_quality': 0.0,    # デフォルト: 同等
}

print(f'\n[4/5] Split CSV を結合・保存中...')
for split in ['train_features', 'val_features', 'test_features']:
    in_path  = os.path.join(IN_DIR,  f'{split}.csv')
    out_path = os.path.join(OUT_DIR, f'{split}.csv')

    if not os.path.exists(in_path):
        print(f'  SKIP: {in_path} が見つかりません')
        continue

    print(f'\n  [{split}]')
    df = pd.read_csv(in_path, low_memory=False)
    df['race_id']  = df['race_id'].astype(str).str.strip()
    df['horse_id'] = df['horse_id'].astype(str).str.strip()
    print(f'  読み込み: {len(df):,}行 × {len(df.columns)}列')

    # 既存同名列を除去
    drop_cols = [c for c in NEW_FEATS if c in df.columns]
    if drop_cols:
        df = df.drop(columns=drop_cols)

    # ---- Waku/distance/course_type をenrichedから補完 ----
    en_cols = df_en[['race_id', 'horse_id', 'Waku', 'distance',
                      'course_type', 'track_name', 'dist_bucket']].drop_duplicates(
        subset=['race_id', 'horse_id']
    ).copy()

    df = df.merge(en_cols, on=['race_id', 'horse_id'], how='left',
                  suffixes=('', '_en'))
    # course_type / track_name の上書き優先度: 既存列 > enriched
    for col in ['course_type', 'track_name', 'distance']:
        if f'{col}_en' in df.columns:
            df[col] = df[col].fillna(df[f'{col}_en'])
            df = df.drop(columns=[f'{col}_en'])

    # ---- waku_win_rate をマージ ----
    df['Waku']      = pd.to_numeric(df.get('Waku', np.nan), errors='coerce')
    df['distance_r7'] = pd.to_numeric(df.get('distance', np.nan), errors='coerce')
    df['dist_bucket'] = pd.cut(
        df['distance_r7'],
        bins=[0, 1400, 1800, 99999],
        labels=['short', 'mid', 'long'],
    )

    # waku_stats は Waku が float → 合わせる
    waku_stats['Waku'] = waku_stats['Waku'].astype(float)
    df = df.merge(
        waku_stats,
        on=['track_name', 'course_type', 'dist_bucket', 'Waku'],
        how='left',
    )
    df['waku_win_rate'] = df['waku_win_rate'].fillna(DEFAULTS['waku_win_rate'])

    # ---- field_waku_rank: レース内 waku_win_rate の相対ランク ----
    # 1.0 = 最高 (最も有利な枠), 0.0 = 最低
    df['field_waku_rank'] = (
        df.groupby('race_id')['waku_win_rate']
        .rank(pct=True, ascending=True)
        .fillna(DEFAULTS['field_waku_rank'])
    )

    # ---- jockey change をマージ（race_id + horse_id 単位）----
    df = df.merge(
        horse_jockey[['race_id', 'horse_id', 'jockey_changed', 'jockey_change_quality']],
        on=['race_id', 'horse_id'], how='left',
    )

    # デフォルト値で補完
    for col, val in DEFAULTS.items():
        if col in df.columns:
            df[col] = df[col].fillna(val)

    # 不要列削除
    for col in ['Waku', 'dist_bucket', 'distance_r7']:
        if col in df.columns:
            df = df.drop(columns=[col])

    # 確認
    print(f'  waku_win_rate 有効率: {(df["waku_win_rate"] != DEFAULTS["waku_win_rate"]).mean()*100:.1f}%')
    print(f'  field_waku_rank 平均: {df["field_waku_rank"].mean():.3f}')
    print(f'  jockey_changed 交代率: {df["jockey_changed"].mean()*100:.1f}%')
    print(f'  jockey_change_quality 平均: {df["jockey_change_quality"].mean():.4f}')

    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f'  → {out_path} 保存完了 ({len(df):,}行 × {len(df.columns)}列)')

print('\n' + '=' * 60)
print('Phase R7 特徴量CSV作成完了')
print(f'出力先: {OUT_DIR}/')
print(f'新特徴量 ({len(NEW_FEATS)}個): {NEW_FEATS}')
print('次: py train_phase_r7.py')
