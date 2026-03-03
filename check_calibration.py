# -*- coding: utf-8 -*-
"""
check_calibration.py — Phase 14 勝率予測のキャリブレーション確認

「pred_win=30%と出ている馬は実際に30%で勝っているか？」を検証する。
過大/過小評価を可視化し、Kelly計算の精度に影響するか確認する。

使い方:
  py check_calibration.py              # 2024年テストデータ
  py check_calibration.py --year 2023  # 2023年で確認
"""
import sys, os, pickle, argparse, warnings
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
import lightgbm as lgb

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 引数 ────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument('--year', type=int, default=2024,
                    help='検証年（2023=val / 2024=test / 2025=live）')
args = parser.parse_args()

# ── データ選択 ────────────────────────────────────────────────
YEAR = args.year
file_map = {
    2023: 'phase13_val_features.csv',
    2024: 'phase13_test_features.csv',
}
if YEAR in file_map:
    data_file = file_map[YEAR]
else:
    # 2025: test_features には含まれていないため enriched CSV から近似
    print(f"[INFO] {YEAR}年の事前計算特徴量は未対応。2024年を使用します。")
    data_file = 'phase13_test_features.csv'
    YEAR = 2024

data_path = os.path.join(BASE_DIR, data_file)
if not os.path.exists(data_path):
    print(f"[ERROR] {data_path} が見つかりません。")
    sys.exit(1)

# ── モデル・特徴量 ───────────────────────────────────────────
print(f"Phase 14 モデル読み込み中...")
with open(os.path.join(BASE_DIR, 'phase14_feature_list.pkl'), 'rb') as f:
    FEATURES = pickle.load(f)
model_win = lgb.Booster(model_file=os.path.join(BASE_DIR, 'phase14_model_win.txt'))

# ── テストデータ ─────────────────────────────────────────────
print(f"{YEAR}年データ読み込み中...")
df = pd.read_csv(data_path, low_memory=False)
df['race_id_str'] = df['race_id'].apply(lambda x: str(int(x)))
df = df[df['race_id_str'].str[:4] == str(YEAR)].copy()
df['actual_rank'] = pd.to_numeric(df['rank'], errors='coerce')
print(f"  {len(df):,}行  {df['race_id_str'].nunique():,}レース")

# ── 予測 ────────────────────────────────────────────────────
X = df[FEATURES].fillna(0)
df['pred_win'] = model_win.predict(X)

# ── 実際の的中（rank==1）────────────────────────────────────
df['is_winner'] = (df['actual_rank'] == 1).astype(int)

# ── デシル別キャリブレーション ─────────────────────────────
print(f"\n{'═'*60}")
print(f"  【キャリブレーション確認】Phase 14 win model × {YEAR}年")
print(f"{'═'*60}")
print(f"\n  予測確率を10分位（デシル）に分け、実際の的中率と比較する。")
print(f"  理想: 予測確率 ≈ 実際的中率\n")

df['decile'] = pd.qcut(df['pred_win'], q=10, labels=False, duplicates='drop')

print(f"  {'デシル':>4} {'予測win(中央)':>14} {'実際的中率':>12} {'差':>8} {'件数':>6} {'評価'}")
print(f"  {'─'*60}")

calib_data = []
for dec in sorted(df['decile'].dropna().unique()):
    sub = df[df['decile'] == dec]
    pred_med = sub['pred_win'].median()
    actual_rate = sub['is_winner'].mean()
    diff = actual_rate - pred_med
    n = len(sub)
    eval_str = '≈適正' if abs(diff) < 0.02 else ('▲過小評価' if diff > 0 else '▼過大評価')
    print(f"  {int(dec)+1:>4}  {pred_med*100:>11.1f}%  {actual_rate*100:>10.1f}%  "
          f"{diff*100:>+7.1f}%  {n:>6}  {eval_str}")
    calib_data.append({'decile': int(dec)+1, 'pred_med': pred_med,
                       'actual_rate': actual_rate, 'diff': diff, 'n': n})

# ── 全体的な偏り ─────────────────────────────────────────────
df_calib = pd.DataFrame(calib_data)
mean_abs_err = df_calib['diff'].abs().mean()
bias = df_calib['diff'].mean()

print(f"\n  平均絶対誤差: {mean_abs_err*100:.2f}%pt")
print(f"  平均バイアス: {bias*100:+.2f}%pt  "
      f"({'全体的に過小評価' if bias > 0 else '全体的に過大評価' if bias < 0 else '偏りなし'})")

# ── 実用的な評価 ─────────────────────────────────────────────
print(f"\n{'─'*60}")
print(f"  【実用評価】")

# 予測20%以上の馬（条件A相当）でのキャリブレーション
high_pred = df[df['pred_win'] >= 0.20]
if len(high_pred) > 0:
    actual_hi = high_pred['is_winner'].mean()
    pred_hi   = high_pred['pred_win'].mean()
    print(f"  pred_win≥20%の馬: {len(high_pred):,}頭")
    print(f"    予測平均: {pred_hi*100:.1f}%  実際的中率: {actual_hi*100:.1f}%  "
          f"差: {(actual_hi-pred_hi)*100:+.1f}%pt")

# 予測10-20%の馬（条件B相当）
mid_pred = df[(df['pred_win'] >= 0.10) & (df['pred_win'] < 0.20)]
if len(mid_pred) > 0:
    actual_mi = mid_pred['is_winner'].mean()
    pred_mi   = mid_pred['pred_win'].mean()
    print(f"  pred_win 10-20%の馬: {len(mid_pred):,}頭")
    print(f"    予測平均: {pred_mi*100:.1f}%  実際的中率: {actual_mi*100:.1f}%  "
          f"差: {(actual_mi-pred_mi)*100:+.1f}%pt")

# ── Kelly計算への影響 ────────────────────────────────────────
print(f"\n  【Kelly計算への影響】")
print(f"  Kelly係数 = (p×b - q) / b  （p=勝率, b=オッズ-1, q=1-p）")

example_odds = 10.0
for p_pred in [0.10, 0.15, 0.20, 0.30]:
    b = example_odds - 1
    kelly_pred = (p_pred * b - (1 - p_pred)) / b
    # 実際の勝率はキャリブレーション後の値（ここでは近似として pred + bias を使用）
    p_actual = p_pred + bias
    kelly_actual = (p_actual * b - (1 - p_actual)) / b
    print(f"  p_pred={p_pred*100:.0f}%  odds={example_odds}x: "
          f"Kelly予測={kelly_pred*100:.1f}%  Kelly実際≈{kelly_actual*100:.1f}%  "
          f"差={( kelly_actual-kelly_pred)*100:+.1f}%")

print(f"\n  ※ バイアスが±2%pt以内なら現状の Kelly計算は実用上問題なし。")
print(f"  ※ バイアスが大きい場合は Isotonic Regression キャリブレーションを検討。")

# ── 過去実績との比較 ─────────────────────────────────────────
print(f"\n  【参考: GUIバックテストとの整合性確認】")
print(f"  バックテスト（GUI版）◎的中率 2024年: 35.0%")
actual_winner_rate = df['is_winner'].mean()
print(f"  テストデータ全体 is_winner 率: {actual_winner_rate*100:.1f}%  "
      f"（1レース1頭 = 1/出走頭数の期待値に対応）")
honmei_per_race = df.groupby('race_id_str')['pred_win'].idxmax()
honmei_hits = df.loc[honmei_per_race, 'is_winner'].mean()
print(f"  ◎（最高pred_win馬）の的中率: {honmei_hits*100:.1f}%")

print(f"\n{'═'*60}\n")
