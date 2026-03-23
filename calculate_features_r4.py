# -*- coding: utf-8 -*-
"""
calculate_features_r4.py — Phase R4: レース内相対特徴量を既存CSVに追加

既存の data/phase14/ CSVs に groupby(race_id) で相対特徴量を付与して
data/phase_r4/ に保存する。再スクレイプ不要（数分で完了）。

追加特徴量（計7個）:
  field_win_rate_rank   : total_win_rate のレース内正規化ランク（1=最良）
  field_jockey_rank     : jockey_win_rate のレース内正規化ランク
  field_trainer_rank    : trainer_win_rate のレース内正規化ランク
  field_earnings_rank   : total_earnings のレース内正規化ランク
  field_last3f_rank     : avg_last_3f のレース内正規化ランク（低いほど速い）
  field_diff_rank       : avg_diff_seconds のレース内正規化ランク（低いほど良い）
  field_size            : レース出走頭数（正規化なし）
"""
import os
import pandas as pd
import numpy as np

IN_DIR  = 'data/phase14'
OUT_DIR = 'data/phase_r4'
os.makedirs(OUT_DIR, exist_ok=True)

# (特徴量名, 昇順ランクが良い=True → ascending=True は低い値=rank1)
RELATIVE_SPECS = [
    ('total_win_rate',   False),   # 高いほど良い → ascending=False
    ('jockey_win_rate',  False),
    ('trainer_win_rate', False),
    ('total_earnings',   False),
    ('avg_last_3f',      True),    # 低いほど速い → ascending=True
    ('avg_diff_seconds', True),    # 低いほど良い → ascending=True
]


def add_relative_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    race_id でグループ化してレース内相対特徴量を追加する。
    正規化ランク = (N - rank) / (N - 1)  ∈ [0, 1]  （1 = 最良）
    N=1 の場合（1頭のみ）は 1.0 とする。
    """
    df = df.copy()

    # 出走頭数
    df['field_size'] = df.groupby('race_id')['race_id'].transform('count')

    for col, ascending in RELATIVE_SPECS:
        out_col = f'field_{col}_rank'
        if col not in df.columns:
            df[out_col] = 0.5  # フォールバック
            continue

        # NaN を中間値（0.5）で埋めてからランク計算
        filled = df[col].fillna(df[col].median())

        # pandas rank: ascending=True → 小さい値が rank 1
        raw_rank = filled.groupby(df['race_id']).rank(method='min', ascending=ascending)
        n = df['field_size']
        # 正規化: 1=最良(rank=1), 0=最悪(rank=N)
        df[out_col] = (n - raw_rank) / (n - 1).clip(lower=1)
        df[out_col] = df[out_col].clip(0.0, 1.0).fillna(0.5)

    return df


NEW_FEATS = ['field_win_rate_rank', 'field_jockey_rank', 'field_trainer_rank',
             'field_earnings_rank', 'field_last3f_rank', 'field_diff_rank', 'field_size']

RENAME = {
    'field_total_win_rate_rank':   'field_win_rate_rank',
    'field_jockey_win_rate_rank':  'field_jockey_rank',
    'field_trainer_win_rate_rank': 'field_trainer_rank',
    'field_total_earnings_rank':   'field_earnings_rank',
    'field_avg_last_3f_rank':      'field_last3f_rank',
    'field_avg_diff_seconds_rank': 'field_diff_rank',
}

for split in ['train_features', 'val_features', 'test_features']:
    in_path  = os.path.join(IN_DIR,  f'{split}.csv')
    out_path = os.path.join(OUT_DIR, f'{split}.csv')

    if not os.path.exists(in_path):
        print(f'  SKIP: {in_path} が見つかりません')
        continue

    print(f'[{split}] 読み込み中...')
    df = pd.read_csv(in_path, low_memory=False)
    print(f'  {len(df):,}行 × {len(df.columns)}列')

    print(f'  相対特徴量を計算中...')
    df = add_relative_features(df)

    # 内部列名をリネーム
    df = df.rename(columns=RENAME)

    added = [c for c in NEW_FEATS if c in df.columns]
    print(f'  追加された特徴量 ({len(added)}個): {added}')

    # サンプル確認
    sample = df[['race_id'] + added].head(5)
    print(sample.to_string(index=False))

    df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f'  → {out_path} 保存完了（{len(df):,}行 × {len(df.columns)}列）\n')

print('=' * 60)
print('Phase R4 特徴量CSV作成完了')
print(f'出力先: {OUT_DIR}/')
print(f'新特徴量: {NEW_FEATS}')
print('次: py train_phase_r4.py')
