# -*- coding: utf-8 -*-
"""
calculate_features_r6.py — Phase R6: トラック日次バイアス・天候・前走末脚特徴量

data/phase_r5/ CSVs を元に以下を追加して data/phase_r6/ に保存する。

【追加特徴量（計6個、total 80個）】
  daily_front_bias      : 当日同場・同コース種別の前レース勝ち馬の1角通過順平均
                          （前有利→低値、後有利→高値。コース種別分離で精度向上）
  daily_prior_races     : バイアス計算に使った前レース数（信頼度指標・レース番号の代理）
  horse_style_vs_bias   : この馬の脚質 vs 当日バイアスの差（絶対値小=有利）
  is_rainy              : 天候が雨/小雨フラグ
  is_sunny              : 天候が晴フラグ
  prev_agari_relative   : 前走上がり3F vs 同レース馬場平均（負=末脚切れた）

【使い方】
  py calculate_features_r6.py
  次: py train_phase_r6.py
"""
import os
import re
import pandas as pd
import numpy as np

IN_DIR        = 'data/phase_r5'
OUT_DIR       = 'data/phase_r6'
ENRICHED_PATH = 'data/main/netkeiba_data_2020_2025_enriched.csv'

os.makedirs(OUT_DIR, exist_ok=True)

print('=' * 60)
print('  Phase R6: トラック日次バイアス・天候・末脚特徴量')
print('=' * 60)

# ============================================================
# Step 1: enriched CSV 読み込み
# ============================================================
print('\n[1/5] enriched CSV 読み込み中...')
df_en = pd.read_csv(
    ENRICHED_PATH,
    usecols=['race_id', 'horse_id', 'date', 'Rank', 'Passage',
             'Agari', 'Time', 'weather', 'track_condition', 'course_type'],
    low_memory=False,
)
df_en['race_id']  = df_en['race_id'].astype(str).str.strip()
df_en['horse_id'] = df_en['horse_id'].astype(str).str.strip()
df_en['date']     = pd.to_datetime(df_en['date'], errors='coerce')
df_en = df_en.dropna(subset=['date'])
print(f'  {len(df_en):,}行')

# race_id から day_key と race_no を抽出
# race_id 形式: YYYYVVKKDDNN (12桁)
df_en['day_key'] = df_en['race_id'].str[:10]   # 同一開催日グループ
df_en['race_no'] = pd.to_numeric(df_en['race_id'].str[10:12], errors='coerce')

# ---- Passage → 1角通過順 ----
def parse_first_corner(s):
    if pd.isna(s):
        return np.nan
    parts = re.split(r'[-\s]', str(s).strip())
    nums = [int(p) for p in parts if p.isdigit()]
    return float(nums[0]) if len(nums) >= 1 else np.nan

df_en['first_corner'] = df_en['Passage'].apply(parse_first_corner)
df_en['Rank_num']     = pd.to_numeric(df_en['Rank'], errors='coerce')
df_en['Agari_n']      = pd.to_numeric(df_en['Agari'], errors='coerce')

# 障害競走（Agari < 20.0）は除外して上がりタイムの信頼性を確保
VALID_AGARI = (df_en['Agari_n'] >= 20.0) & (df_en['Agari_n'] <= 50.0)

# ---- Time 文字列 → 秒 ----
def parse_time_to_sec(s):
    """'1:54.8' → 114.8"""
    if pd.isna(s):
        return np.nan
    s = str(s).strip()
    m = re.match(r'(\d+):(\d+\.\d+)', s)
    if m:
        return int(m.group(1)) * 60 + float(m.group(2))
    return np.nan

df_en['time_sec'] = df_en['Time'].apply(parse_time_to_sec)

# ============================================================
# Step 2: 勝ち馬1角通過順 → 日次バイアス計算
# ============================================================
print('\n[2/5] 日次トラックバイアス計算中（コースタイプ別）...')

# course_type も enriched CSV から取得して winners に紐付け
winners_raw = (
    df_en[df_en['Rank_num'] == 1]
    [['race_id', 'day_key', 'race_no', 'first_corner', 'weather', 'course_type']]
    .drop_duplicates('race_id')   # 同着1着は先頭1件のみ
    .sort_values(['day_key', 'race_no'])
    .copy()
)
print(f'  勝ち馬レコード: {len(winners_raw):,}件')
valid_fc = winners_raw['first_corner'].notna().sum()
print(f'  1角通過順有効: {valid_fc:,}件 ({valid_fc/len(winners_raw)*100:.1f}%)')

# コースタイプ別基準値（芝/ダート/障害で勝ち馬1角位置の分布が異なる）
# 障害は除外してフラット競走のみ（Passage信頼性の問題）
COURSE_BASELINES = {'芝': 5.1, 'ダート': 4.4}  # 実データから算出した平均
flat_winners = winners_raw[winners_raw['course_type'].isin(['芝', 'ダート'])].copy()

# ---- コースタイプ別 expanding mean（同日同コース前レース）----
# グループキー: day_key + course_type
flat_winners['day_course_key'] = flat_winners['day_key'] + '_' + flat_winners['course_type'].fillna('不明')
flat_winners = flat_winners.sort_values(['day_course_key', 'race_no'])

flat_winners['bias_expanding'] = flat_winners.groupby('day_course_key')['first_corner'].transform(
    lambda x: x.shift(1).expanding().mean()
)
flat_winners['prior_count'] = flat_winners.groupby('day_course_key')['first_corner'].transform(
    lambda x: x.shift(1).expanding().count()
)

# 全レース（障害含む）の race_id に対してコース別バイアスをマップ
race_bias = flat_winners[['race_id', 'bias_expanding', 'prior_count', 'weather']].rename(columns={
    'bias_expanding': 'daily_front_bias',
    'prior_count':    'daily_prior_races',
})

# 障害・非フラットレースは全件バイアス（day_key単位の全コース混合）で補完
all_winners = winners_raw.sort_values(['day_key', 'race_no'])
all_winners['bias_all'] = all_winners.groupby('day_key')['first_corner'].transform(
    lambda x: x.shift(1).expanding().mean()
)
all_winners['prior_all'] = all_winners.groupby('day_key')['first_corner'].transform(
    lambda x: x.shift(1).expanding().count()
)
fallback = all_winners[['race_id', 'bias_all', 'prior_all']].rename(columns={
    'bias_all': 'daily_front_bias_all',
    'prior_all': 'daily_prior_races_all',
})
race_bias = race_bias.merge(fallback, on='race_id', how='outer')
# コース別バイアスがNaNの場合は全コース混合で補完
mask = race_bias['daily_front_bias'].isna()
race_bias.loc[mask, 'daily_front_bias']  = race_bias.loc[mask, 'daily_front_bias_all']
race_bias.loc[mask, 'daily_prior_races'] = race_bias.loc[mask, 'daily_prior_races_all']
race_bias = race_bias.drop(columns=['daily_front_bias_all', 'daily_prior_races_all'])

# weatherは全レースに適用（fallbackに含まれる場合もあり）
if 'weather' not in race_bias.columns or race_bias['weather'].isna().any():
    race_bias = race_bias.merge(
        all_winners[['race_id','weather']].drop_duplicates('race_id'),
        on='race_id', how='left', suffixes=('', '_fallback')
    )
    if 'weather_fallback' in race_bias.columns:
        race_bias['weather'] = race_bias['weather'].fillna(race_bias['weather_fallback'])
        race_bias = race_bias.drop(columns=['weather_fallback'])

# 統計確認
print(f'  daily_front_bias 有効件数: {race_bias["daily_front_bias"].notna().sum():,}')
print(f'  daily_front_bias 平均: {race_bias["daily_front_bias"].mean():.2f}')
print(f'  daily_prior_races 中央値: {race_bias["daily_prior_races"].median():.0f}')

# ---- weather エンコード（weather は race_id 単位で同一）----
race_bias['is_rainy'] = race_bias['weather'].isin(['雨', '小雨']).astype(int)
race_bias['is_sunny'] = (race_bias['weather'] == '晴').astype(int)

print('\n  weather分布:')
print(race_bias['weather'].value_counts().to_string())

# ============================================================
# Step 3: 前走上がり3F 相対値（prev_agari_relative）
# ============================================================
print('\n[3/5] 前走上がり3F相対値計算中...')

# 平地かつ有効なAgariのみ使用
agari_df = df_en[VALID_AGARI][['race_id', 'horse_id', 'date', 'Agari_n']].copy()

# レース平均上がり
race_avg_agari = (
    agari_df
    .groupby('race_id')['Agari_n']
    .mean()
    .rename('race_avg_agari')
    .reset_index()
)
agari_df = agari_df.merge(race_avg_agari, on='race_id', how='left')
agari_df['agari_vs_field'] = agari_df['Agari_n'] - agari_df['race_avg_agari']
# 負 = この馬の上がりが速い（末脚切れた）

# 馬別・日付順に並べてshift(1)で前走情報を取得
agari_df = agari_df.sort_values(['horse_id', 'date'])
agari_df['prev_agari_relative'] = (
    agari_df
    .groupby('horse_id')['agari_vs_field']
    .transform(lambda x: x.shift(1))
)

horse_agari = agari_df[['race_id', 'horse_id', 'prev_agari_relative']].copy()

valid_pa = horse_agari['prev_agari_relative'].notna().sum()
print(f'  prev_agari_relative 有効: {valid_pa:,}件 ({valid_pa/len(horse_agari)*100:.1f}%)')
print(f'  prev_agari_relative 平均: {horse_agari["prev_agari_relative"].mean():.3f}')
print(f'  （負=前走末脚切れた、正=前走末脚鈍かった）')

# ============================================================
# Step 4: 各 split CSV に結合して保存
# ============================================================
NEW_FEATS = [
    'daily_front_bias',
    'daily_prior_races',
    'horse_style_vs_bias',   # 計算はマージ後
    'is_rainy',
    'is_sunny',
    'prev_agari_relative',
]

DEFAULTS = {
    'daily_front_bias':    4.57,   # 全体勝ち馬1角平均
    'daily_prior_races':   0.0,
    'horse_style_vs_bias': 0.0,
    'is_rainy':            0,
    'is_sunny':            0,
    'prev_agari_relative': 0.0,
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

    # ---- race_bias をマージ（race_id 単位）----
    df = df.merge(
        race_bias[['race_id', 'daily_front_bias', 'daily_prior_races', 'is_rainy', 'is_sunny']],
        on='race_id', how='left',
    )

    # ---- horse_agari をマージ（race_id + horse_id 単位）----
    df = df.merge(
        horse_agari[['race_id', 'horse_id', 'prev_agari_relative']],
        on=['race_id', 'horse_id'], how='left',
    )

    # ---- horse_style_vs_bias: 脚質 vs 当日バイアスの差 ----
    # avg_first_corner_fixed: 低=前、high=後  |  daily_front_bias: 低=前有利
    # 差が小さい（絶対値）→ 当日バイアスと脚質が一致 → 有利
    if 'avg_first_corner_fixed' in df.columns:
        df['horse_style_vs_bias'] = (
            df['avg_first_corner_fixed'] - df['daily_front_bias'].fillna(4.57)
        )
    else:
        df['horse_style_vs_bias'] = 0.0

    # デフォルト値で補完
    for col, val in DEFAULTS.items():
        if col in df.columns:
            df[col] = df[col].fillna(val)

    # 確認
    print(f'  daily_front_bias 有効率: {(df["daily_front_bias"] != 4.57).mean()*100:.1f}%')
    print(f'  is_rainy 割合: {df["is_rainy"].mean()*100:.1f}%')
    print(f'  is_sunny 割合: {df["is_sunny"].mean()*100:.1f}%')
    print(f'  prev_agari_relative 有効率: {(df["prev_agari_relative"] != 0.0).mean()*100:.1f}%')

    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f'  → {out_path} 保存完了 ({len(df):,}行 × {len(df.columns)}列)')

print('\n' + '=' * 60)
print('Phase R6 特徴量CSV作成完了')
print(f'出力先: {OUT_DIR}/')
print(f'新特徴量 ({len(NEW_FEATS)}個): {NEW_FEATS}')
print('次: py train_phase_r6.py')
