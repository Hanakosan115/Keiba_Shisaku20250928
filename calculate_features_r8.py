"""
Phase R8 特徴量計算
71特徴量（R7+Optuna）に 7特徴量追加 = 78特徴量

追加特徴量:
  B. 血統詳細
    father_track_win_rate        : 父馬×競馬場 の歴史的勝率
    mother_father_track_win_rate : 母父馬×競馬場 の歴史的勝率
  C. 近況
    consecutive_losses           : 直近の連続着外回数（3着以内なしの連続数）
    form_trend                   : 直近3走の着順トレンド（正=改善、負=悪化）
    best_distance_diff           : 得意距離帯との乖離（km）
  D. 馬個体×条件
    horse_waku_win_rate          : 馬個体の枠番別歴史的勝率
    large_field_win_rate         : 大人数（≥12頭）レースでの歴史的勝率

使い方:
  py calculate_features_r8.py
"""
import os, sys, warnings
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ENRICHED_PATH = 'data/main/netkeiba_data_2020_2025_enriched.csv'
IN_DIR        = 'data/phase_r7'
OUT_DIR       = 'data/phase_r8'
MIN_STARTS    = 10   # 最小件数（以下はフォールバック値使用）

os.makedirs(OUT_DIR, exist_ok=True)

# ======================================================================
# 1. enriched CSV 読み込み
# ======================================================================
print("enriched CSV 読み込み中...")
enr = pd.read_csv(ENRICHED_PATH, low_memory=False)
enr['rank_int']  = pd.to_numeric(enr['Rank'],     errors='coerce').fillna(99).astype(int)
enr['waku_int']  = pd.to_numeric(enr['Waku'],     errors='coerce').fillna(0).astype(int)
enr['dist_int']  = pd.to_numeric(enr['distance'], errors='coerce').fillna(0).astype(int)
enr['is_win']    = (enr['rank_int'] == 1).astype(float)
enr['is_top3']   = (enr['rank_int'] <= 3).astype(float)
enr['date_dt']   = pd.to_datetime(enr['date'], errors='coerce')
enr['father']    = enr['father'].fillna('unknown')
enr['mother_father'] = enr['mother_father'].fillna('unknown')
GLOBAL_WR = enr['is_win'].mean()
print(f"  {len(enr):,}行 / 勝率グローバル平均: {GLOBAL_WR:.4f}")

# レース別出走頭数（field_size相当）
race_sizes = enr.groupby('race_id')['horse_id'].count().rename('race_field_size')
enr = enr.merge(race_sizes, on='race_id', how='left')

# ======================================================================
# 2. B: 血統×競馬場 勝率
# ======================================================================
print("B: father_track_win_rate 計算中...")

def build_track_stats(group_col):
    stats = (enr.groupby([group_col, 'track_name'])
               .agg(wins=('is_win','sum'), starts=('is_win','count'))
               .reset_index())
    stats[f'{group_col}_track_win_rate'] = stats['wins'] / stats['starts'].clip(lower=1)
    # フォールバック: 個体全体勝率
    overall = (enr.groupby(group_col)
                  .agg(ow=('is_win','sum'), os=('is_win','count'))
                  .reset_index())
    overall[f'{group_col}_overall_wr'] = overall['ow'] / overall['os'].clip(lower=1)
    stats = stats.merge(overall[[group_col, f'{group_col}_overall_wr']], on=group_col, how='left')
    # MIN_STARTS 未満はフォールバック
    mask = stats['starts'] < MIN_STARTS
    stats.loc[mask, f'{group_col}_track_win_rate'] = (
        stats.loc[mask, f'{group_col}_overall_wr'].fillna(GLOBAL_WR))
    return stats[[group_col, 'track_name', f'{group_col}_track_win_rate']]

father_track_df = build_track_stats('father')
mf_track_df     = build_track_stats('mother_father')

# ======================================================================
# 3. C & D: 馬個体の時系列特徴量（リーケージなし）
# ======================================================================
print("C/D: 馬個体 per-race 特徴量計算中（expanding window）...")

enr = enr.sort_values(['horse_id', 'date_dt', 'race_id']).reset_index(drop=True)

def compute_horse_feats(group):
    n       = len(group)
    ranks   = group['rank_int'].values
    is_w    = group['is_win'].values
    is_t3   = group['is_top3'].values
    wakus   = group['waku_int'].values
    dists   = group['dist_int'].values
    fsizes  = group['race_field_size'].values

    consecutive_losses  = np.zeros(n)
    form_trend          = np.zeros(n)
    best_distance_diff  = np.zeros(n)
    horse_waku_wr       = np.full(n, GLOBAL_WR)
    large_field_wr      = np.full(n, GLOBAL_WR)

    c_loss = 0
    waku_w  = {}  # waku → wins
    waku_s  = {}  # waku → starts
    dist_w  = {}  # dist_bucket → wins
    dist_s  = {}  # dist_bucket → starts
    large_w = 0; large_s = 0   # ≥12頭

    for i in range(n):
        # ---------- 使用 (BEFORE this race) ----------
        consecutive_losses[i] = float(c_loss)

        # form_trend: 直近最大3走の着順変化（正=改善=着順番号が小さくなる方向）
        if i >= 2:
            past = ranks[max(0, i-3):i]   # 最大3走分
            form_trend[i] = float(past[0] - past[-1]) / max(len(past)-1, 1)

        # best_distance_diff
        if sum(dist_s.values()) > 0:
            best_d = max(dist_w.keys(),
                         key=lambda k: (dist_w[k] / dist_s[k]) if dist_s[k] >= 3 else 0.0)
            best_distance_diff[i] = abs(int(dists[i]) - best_d) / 1000.0  # km単位

        # horse_waku_win_rate
        w = int(wakus[i])
        if w > 0 and waku_s.get(w, 0) >= 2:
            horse_waku_wr[i] = waku_w[w] / waku_s[w]

        # large_field_win_rate
        if large_s >= 3:
            large_field_wr[i] = large_w / large_s

        # ---------- 更新 (AFTER) ----------
        if is_t3[i] > 0:
            c_loss = 0
        else:
            c_loss += 1

        d_bucket = (int(dists[i]) // 200) * 200
        dist_w[d_bucket]  = dist_w.get(d_bucket,  0) + int(is_w[i])
        dist_s[d_bucket]  = dist_s.get(d_bucket,  0) + 1

        if w > 0:
            waku_w[w] = waku_w.get(w, 0) + int(is_w[i])
            waku_s[w] = waku_s.get(w, 0) + 1

        if int(fsizes[i]) >= 12:
            large_w += int(is_w[i])
            large_s += 1

    out = group[['horse_id','race_id']].copy()
    out['consecutive_losses'] = consecutive_losses
    out['form_trend']          = form_trend
    out['best_distance_diff']  = best_distance_diff
    out['horse_waku_win_rate'] = horse_waku_wr
    out['large_field_win_rate']= large_field_wr
    return out

# 馬ごとに計算（全馬）
horse_feats = enr.groupby('horse_id', group_keys=False).apply(compute_horse_feats)
horse_feats = horse_feats.reset_index(drop=True)
print(f"  horse_feats: {len(horse_feats):,}行")

# ======================================================================
# 4. R7 CSVに結合して R8 CSV として保存
# ======================================================================
for split in ['train', 'val', 'test']:
    in_path  = f'{IN_DIR}/{split}_features.csv'
    out_path = f'{OUT_DIR}/{split}_features.csv'
    print(f"\n{split}: 読み込み中...")
    df = pd.read_csv(in_path, low_memory=False)
    print(f"  元サイズ: {df.shape}")

    # B: father_track_win_rate（enrichedから track_name列を使って結合）
    # R7 CSV に track_name があるのでそのまま使用
    if 'track_name' in df.columns and 'father' not in df.columns:
        # enrichedからfather列を取得（型統一してからmerge）
        enr_sub = enr[['race_id','horse_id','father','mother_father']].drop_duplicates().copy()
        enr_sub['race_id']  = enr_sub['race_id'].astype(str)
        enr_sub['horse_id'] = enr_sub['horse_id'].astype(str)
        df['race_id']  = df['race_id'].astype(str)
        df['horse_id'] = df['horse_id'].astype(str)
        df = df.merge(enr_sub, on=['race_id','horse_id'], how='left')

    if 'father' in df.columns and 'track_name' in df.columns:
        df['father']       = df['father'].fillna('unknown')
        df['mother_father']= df['mother_father'].fillna('unknown')
        df = df.merge(father_track_df, on=['father','track_name'], how='left')
        df = df.merge(mf_track_df,     on=['mother_father','track_name'], how='left')
        df['father_track_win_rate']        = df['father_track_win_rate'].fillna(GLOBAL_WR)
        df['mother_father_track_win_rate'] = df['mother_father_track_win_rate'].fillna(GLOBAL_WR)
    else:
        df['father_track_win_rate']        = GLOBAL_WR
        df['mother_father_track_win_rate'] = GLOBAL_WR

    # C & D: horse_feats 結合（型統一）
    merge_cols = ['horse_id','race_id',
                  'consecutive_losses','form_trend','best_distance_diff',
                  'horse_waku_win_rate','large_field_win_rate']
    hf = horse_feats[merge_cols].copy()
    hf['race_id']  = hf['race_id'].astype(str)
    hf['horse_id'] = hf['horse_id'].astype(str)
    df = df.merge(hf, on=['horse_id','race_id'], how='left')

    # フォールバック
    df['consecutive_losses']   = df['consecutive_losses'].fillna(0)
    df['form_trend']           = df['form_trend'].fillna(0)
    df['best_distance_diff']   = df['best_distance_diff'].fillna(0)
    df['horse_waku_win_rate']  = df['horse_waku_win_rate'].fillna(GLOBAL_WR)
    df['large_field_win_rate'] = df['large_field_win_rate'].fillna(GLOBAL_WR)

    # 不要列削除
    drop_cols = [c for c in ['father','mother_father'] if c in df.columns]
    df = df.drop(columns=drop_cols, errors='ignore')

    print(f"  新サイズ: {df.shape}")
    new_cols = ['father_track_win_rate','mother_father_track_win_rate',
                'consecutive_losses','form_trend','best_distance_diff',
                'horse_waku_win_rate','large_field_win_rate']
    for c in new_cols:
        if c in df.columns:
            print(f"    {c}: mean={df[c].mean():.4f}  null={df[c].isna().sum()}")

    df.to_csv(out_path, index=False)
    print(f"  保存: {out_path}")

print("\n=== Phase R8 特徴量計算完了 ===")
print(f"出力先: {OUT_DIR}/")
