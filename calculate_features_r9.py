"""
Phase R9 特徴量計算
78特徴量（R8+Optuna）に 1特徴量追加 = 79特徴量

追加特徴量:
  training_rank_num : 調教評価数値（A=4, B=3, C=2, D=1, 不明=2）
                      data/main/training_evaluations.csv から取得

使い方:
  py calculate_features_r9.py
"""

import os, sys, warnings
import pandas as pd

warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

IN_DIR       = 'data/phase_r8'
OUT_DIR      = 'data/phase_r9'
TRAINING_CSV = 'data/main/training_evaluations.csv'
COMPLETE_CSV = 'data/main/netkeiba_data_2020_2025_complete.csv'

RANK_MAP     = {'A': 4, 'B': 3, 'C': 2, 'D': 1}
DEFAULT_RANK = 2.0   # 不明・未取得 → B相当

os.makedirs(OUT_DIR, exist_ok=True)

# ======================================================================
# 1. 調教データ読み込み
# ======================================================================
print("調教データ読み込み中...")
tr = pd.read_csv(TRAINING_CSV, low_memory=False)
tr['race_id'] = tr['race_id'].astype(str).str.strip()
tr['umaban']  = tr['umaban'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
tr['training_rank_num'] = tr['training_rank'].map(RANK_MAP).fillna(DEFAULT_RANK)
print(f"  {len(tr):,}件")
print(f"  rank分布: {tr['training_rank'].value_counts().to_dict()}")

# ======================================================================
# 2. umaban → horse_id マッピング構築（complete.csv 使用）
# ======================================================================
print("umaban → horse_id マッピング構築中...")
df_map = pd.read_csv(COMPLETE_CSV, usecols=['race_id', 'horse_id', '馬番'],
                     low_memory=False)
df_map['race_id']  = df_map['race_id'].astype(str).str.strip()
df_map['horse_id'] = df_map['horse_id'].astype(str).str.strip()
df_map['umaban']   = (df_map['馬番']
                      .astype(str).str.replace(r'\.0$', '', regex=True).str.strip())
df_map = df_map[['race_id', 'umaban', 'horse_id']].drop_duplicates()

# 調教データに horse_id を付加
tr = tr.merge(df_map, on=['race_id', 'umaban'], how='left')
coverage = tr['horse_id'].notna().mean() * 100
print(f"  horse_id 付与率: {coverage:.1f}%")

# (race_id, horse_id) → training_rank_num
tr_key = (tr.dropna(subset=['horse_id'])
            .groupby(['race_id', 'horse_id'])['training_rank_num']
            .first()
            .reset_index())

# ======================================================================
# 3. R8 CSV に training_rank_num を追加して R9 CSV として保存
# ======================================================================
for split in ['train', 'val', 'test']:
    in_path  = f'{IN_DIR}/{split}_features.csv'
    out_path = f'{OUT_DIR}/{split}_features.csv'
    print(f"\n{split}: 読み込み中...")
    df = pd.read_csv(in_path, low_memory=False)
    print(f"  元サイズ: {df.shape}")

    df['race_id']  = df['race_id'].astype(str).str.strip()
    df['horse_id'] = df['horse_id'].astype(str).str.strip()

    df = df.merge(tr_key, on=['race_id', 'horse_id'], how='left')
    df['training_rank_num'] = df['training_rank_num'].fillna(DEFAULT_RANK)

    hit = (df['training_rank_num'] != DEFAULT_RANK).mean() * 100
    mean_val = df['training_rank_num'].mean()
    dist = df['training_rank_num'].value_counts().sort_index().to_dict()
    print(f"  training_rank_num: mean={mean_val:.3f}  カバレッジ={hit:.1f}%")
    print(f"  分布: {dist}")
    print(f"  新サイズ: {df.shape}")

    df.to_csv(out_path, index=False)
    print(f"  保存: {out_path}")

print("\n=== Phase R9 特徴量計算完了 ===")
print(f"出力先: {OUT_DIR}/")
