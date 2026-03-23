"""
Phase R10 特徴量計算
79特徴量（R9）→ 調教タイム特徴量に差し替え = 82特徴量

training_rank_num（R9）を削除し、より客観的なタイム特徴量に置換:
  training_3f_relative   : 同日・同コース・同馬場での3Fタイム偏差（マイナス=速い）
  training_last1f_rel    : 同日・同コース・同馬場での上がり1Fタイム偏差
  training_finish_score  : 脚色スコア（一杯=0, 強め=1, 末強め=2, 馬也=3, 不明=1）
  training_course_type   : コース種別（坂路=0, W=1, 芝=2, ダート=3, 不明=1）

使い方:
  py calculate_features_r10.py

前提:
  data/main/training_evaluations_v2.csv が存在すること
  data/phase_r8/ に R8 特徴量 CSV があること
"""

import os, sys, re, warnings
import pandas as pd
import numpy as np

warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

IN_DIR       = 'data/phase_r8'
OUT_DIR      = 'data/phase_r10'
TRAINING_V2  = 'data/main/training_evaluations_v2.csv'
COMPLETE_CSV = 'data/main/netkeiba_data_2020_2025_complete.csv'

DEFAULT_3F_REL    = 0.0
DEFAULT_1F_REL    = 0.0
DEFAULT_FINISH    = 1.0   # 不明→強め相当
DEFAULT_COURSE    = 1.0   # 不明→W相当

FINISH_MAP = {
    '一杯': 0, '強め': 1, '末強め': 2, '馬也': 3,
    '直強め': 2, '外強め': 1, '内強め': 1,
}
COURSE_MAP = {
    '坂路': 0, '美坂': 0, '栗坂': 0, '南坂': 0,
    'Ｗ': 1, '美Ｗ': 1, '栗Ｗ': 1, '南Ｗ': 1,
    '芝': 2, '美芝': 2, '栗芝': 2,
    'ダ': 3, '美ダ': 3, '栗ダ': 3,
}

os.makedirs(OUT_DIR, exist_ok=True)


# ======================================================================
# 1. タイムラップ文字列からタイム抽出
# ======================================================================
def parse_laps(laps_str: str):
    """
    "85.2(16.6)68.6(14.9)53.7(14.5)39.2(26.3)12.9(12.9)" のような文字列から
    3Fタイム と 1Fタイムを抽出する。

    ルール:
    - 数値パターン \\d+\\.\\d+ をすべて抽出（カッコ内含む）
    - 偶数インデックス = 累積タイム（遠い方から近い方へ）
    - 奇数インデックス = そのラップの単独タイム
    - cumulative[-1] = 1F累積タイム（= 上がり1F）
    - cumulative[-3] = 3F累積タイム（= 上がり3F）
    - `-` 始まりの計測なしは None を返す
    """
    if not isinstance(laps_str, str) or not laps_str.strip():
        return None, None

    # 計測なしは '-' 始まり or 空
    clean = laps_str.strip()
    # '-' の前後にある数値を除外するため、まず '-' を削除してから探す
    # ただし "-55.9(..." のように先頭 '-' = 計測開始地点なし（正常データ）→ 解析続行

    nums = re.findall(r'\d+\.\d+', clean)
    if len(nums) < 4:
        return None, None

    try:
        all_vals = [float(x) for x in nums]
        # 累積値 = 偶数インデックス
        cumulative = [all_vals[i] for i in range(0, len(all_vals), 2)]
        if len(cumulative) < 2:
            return None, None

        last1f = cumulative[-1]  # 上がり1F
        last3f = cumulative[-3] if len(cumulative) >= 3 else None  # 上がり3F

        # 妥当性チェック
        if last1f < 10 or last1f > 20:
            last1f = None
        if last3f is not None and (last3f < 30 or last3f > 70):
            last3f = None

        return last3f, last1f
    except Exception:
        return None, None


def classify_course(course: str) -> float:
    if not isinstance(course, str):
        return DEFAULT_COURSE
    for key, val in COURSE_MAP.items():
        if key in course:
            return float(val)
    return DEFAULT_COURSE


def classify_finish(finish: str) -> float:
    if not isinstance(finish, str):
        return DEFAULT_FINISH
    for key, val in FINISH_MAP.items():
        if key in finish:
            return float(val)
    return DEFAULT_FINISH


# ======================================================================
# 2. 調教データ読み込み・パース
# ======================================================================
print("調教タイムデータ読み込み中...")
tr = pd.read_csv(TRAINING_V2, low_memory=False)
tr['race_id'] = tr['race_id'].astype(str).str.strip()
tr['umaban']  = tr['umaban'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
print(f"  {len(tr):,}件")

# タイム抽出
print("  タイムラップ解析中...")
parsed = tr['training_laps'].apply(parse_laps)
tr['t3f'] = [x[0] for x in parsed]
tr['t1f'] = [x[1] for x in parsed]
tr['course_type']   = tr['training_course'].apply(classify_course)
tr['finish_score']  = tr['training_finish'].apply(classify_finish)

valid_3f = tr['t3f'].notna().mean() * 100
valid_1f = tr['t1f'].notna().mean() * 100
print(f"  3F有効率: {valid_3f:.1f}%  1F有効率: {valid_1f:.1f}%")
print(f"  コース分布: {tr['course_type'].value_counts().to_dict()}")
print(f"  脚色分布: {tr['finish_score'].value_counts().to_dict()}")

# ======================================================================
# 3. 同日・同コース・同馬場での相対タイム偏差を計算
# ======================================================================
print("  相対タイム計算中...")

# 日付を正規化（"2024/01/03(水)" → "2024/01/03"）
tr['training_date_clean'] = tr['training_date'].str.extract(r'(\d{4}/\d{2}/\d{2})')

# グループ: (日付, コース文字列, 馬場) で偏差値化
# 同一日・同一コース・同一馬場の中での相対位置
def make_relative(df, col, new_col):
    """グループ内の偏差（値 - グループ中央値）を計算。小さいほど速い（3F/1Fともに秒数）"""
    df = df.copy()
    grp = df.groupby(['training_date_clean', 'training_course', 'training_baba'])[col]
    df[new_col] = df[col] - grp.transform('median')
    return df

tr = make_relative(tr, 't3f', 't3f_rel')
tr = make_relative(tr, 't1f', 't1f_rel')

# Zスコア化（同グループ内stdで割る）は外れ値に強くするため任意だが
# 今回は生の偏差値（秒）のまま使用する（モデルが勝手に正規化するので問題なし）

# ======================================================================
# 4. (race_id, umaban) → horse_id マッピング
# ======================================================================
print("umaban → horse_id マッピング構築中...")
df_map = pd.read_csv(COMPLETE_CSV, usecols=['race_id', 'horse_id', '馬番'], low_memory=False)
df_map['race_id']  = df_map['race_id'].astype(str).str.strip()
df_map['horse_id'] = df_map['horse_id'].astype(str).str.strip()
df_map['umaban']   = (df_map['馬番']
                      .astype(str).str.replace(r'\.0$', '', regex=True).str.strip())
df_map = df_map[['race_id', 'umaban', 'horse_id']].drop_duplicates()

tr = tr.merge(df_map, on=['race_id', 'umaban'], how='left')
coverage = tr['horse_id'].notna().mean() * 100
print(f"  horse_id 付与率: {coverage:.1f}%")

# (race_id, horse_id) → 特徴量
tr_key = (tr.dropna(subset=['horse_id'])
            .groupby(['race_id', 'horse_id'])[
                ['t3f_rel', 't1f_rel', 'course_type', 'finish_score']
            ].first().reset_index())

# ======================================================================
# 5. R8 CSV に R10 特徴量を追加して R10 CSV として保存
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
    df['training_3f_relative']  = df['t3f_rel'].fillna(DEFAULT_3F_REL)
    df['training_last1f_rel']   = df['t1f_rel'].fillna(DEFAULT_1F_REL)
    df['training_finish_score'] = df['finish_score'].fillna(DEFAULT_FINISH)
    df['training_course_type']  = df['course_type'].fillna(DEFAULT_COURSE)

    # 中間列削除
    df = df.drop(columns=['t3f_rel', 't1f_rel', 'finish_score', 'course_type'], errors='ignore')

    cov = (df['training_3f_relative'] != DEFAULT_3F_REL).mean() * 100
    m3  = df['training_3f_relative'].mean()
    print(f"  training_3f_relative: mean={m3:.3f}  カバレッジ={cov:.1f}%")
    print(f"  新サイズ: {df.shape}")

    df.to_csv(out_path, index=False)
    print(f"  保存: {out_path}")

print("\n=== Phase R10 特徴量計算完了 ===")
print(f"出力先: {OUT_DIR}/")
print("次: py train_phase_r10.py")
