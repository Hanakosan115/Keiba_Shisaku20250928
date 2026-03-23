# -*- coding: utf-8 -*-
"""
Phase 14: 完全データベース（2020-2025）の特徴量計算

data/main/netkeiba_data_2020_2025_complete.csvに対して、
Phase 13と同じ39特徴量を計算する。

推定時間: 4-8時間（289,336レース）
チェックポイント: 10,000レースごとに中間保存
"""
import pandas as pd
import numpy as np
import pickle
import time
from datetime import datetime
import os
from phase13_feature_engineering import (
    calculate_horse_features_safe,
    calculate_sire_stats,
    calculate_trainer_jockey_stats,
    normalize_date
)

print("=" * 80)
print("  Phase 14: 完全データベース特徴量計算")
print("=" * 80)
print()
print("推定時間: 4-8時間")
print("チェックポイント: 10,000レースごとに中間保存")
print("Ctrl+Cで中断可能（次回は中断地点から再開）")
print()

# 出力ファイルのログ設定
log_file = open('calculate_features_complete_db.log', 'w', encoding='utf-8')

def log_print(msg):
    """コンソールとログファイルの両方に出力"""
    print(msg)
    log_file.write(msg + '\n')
    log_file.flush()

# ===================================================================
# データ読み込み
# ===================================================================

log_print("[1/7] 完全データベース読み込み中...")
df_all = pd.read_csv('data/main/netkeiba_data_2020_2025_complete.csv', low_memory=False)

log_print(f"  総レコード数: {len(df_all):,}")

# 年別確認
df_all['year'] = df_all['race_id'].astype(str).str[:4].astype(int)
year_counts = df_all['year'].value_counts().sort_index()
log_print("  年別レコード数:")
for year, count in year_counts.items():
    log_print(f"    {year}年: {count:,}")
log_print("")

# 2026年の不完全データを除外
df_all = df_all[df_all['year'] < 2026].copy()
log_print(f"  2026年除外後: {len(df_all):,}レコード")
log_print("")

# ===================================================================
# 統計計算（2020-2023訓練期間のみ）
# ===================================================================

log_print("[2/7] 訓練期間（2020-2023）で統計計算中...")
train_df = df_all[df_all['year'].isin([2020, 2021, 2022, 2023])]

sire_stats = calculate_sire_stats(train_df)
trainer_jockey_stats = calculate_trainer_jockey_stats(train_df)

log_print(f"  種牡馬統計: {len(sire_stats)}頭")
log_print(f"  調教師統計: {len(trainer_jockey_stats['trainer'])}人")
log_print(f"  騎手統計: {len(trainer_jockey_stats['jockey'])}人")
log_print("")

# ===================================================================
# チェックポイント確認
# ===================================================================

checkpoint_file = 'calculate_features_checkpoint.csv'
start_idx = 0

if os.path.exists(checkpoint_file):
    log_print("[3/7] チェックポイントファイル検出")
    log_print(f"  {checkpoint_file} が見つかりました")
    # 自動的に再開（バックグラウンド実行対応）
    checkpoint_df = pd.read_csv(checkpoint_file)
    start_idx = len(checkpoint_df)
    log_print(f"  {start_idx:,}レコード目から自動再開します")
    log_print("")
else:
    log_print("[3/7] 新規計算開始")
    log_print("")

# ===================================================================
# 特徴量計算
# ===================================================================

log_print("[4/7] 特徴量計算開始...")

total = len(df_all)
results = []
errors = []

start_time = time.time()
checkpoint_interval = 10000

log_print(f"  対象: {total:,}レース")
log_print(f"  開始インデックス: {start_idx:,}")
log_print("")

# チェックポイントデータがあれば読み込み
if start_idx > 0 and os.path.exists(checkpoint_file):
    checkpoint_df = pd.read_csv(checkpoint_file)
    results = checkpoint_df.to_dict('records')
    log_print(f"  既存データ読み込み: {len(results):,}件")
    log_print("")

for idx in range(start_idx, total):
    row = df_all.iloc[idx]

    if (idx + 1) % 100 == 0:
        elapsed = time.time() - start_time
        rate = (idx + 1 - start_idx) / elapsed if elapsed > 0 else 0
        remaining = (total - idx - 1) / rate if rate > 0 else 0
        print(f"\r  進捗: {idx+1:,}/{total:,} ({(idx+1)/total*100:.1f}%) "
              f"| 速度: {rate:.1f}レース/秒 | 残り時間: {remaining/60:.1f}分", end='')

    race_id = row['race_id']
    horse_id = row['horse_id']
    cutoff_date = normalize_date(row['date'])

    try:
        # 過去レース取得（cutoff_date以前）
        horse_past = df_all[
            (df_all['horse_id'] == horse_id) &
            (df_all['race_id'].astype(str) < str(race_id))
        ]

        # 特徴量計算
        features = calculate_horse_features_safe(
            row, horse_past, df_all,
            sire_stats, trainer_jockey_stats,
            cutoff_date=cutoff_date
        )

        # 基本情報追加
        features['race_id'] = race_id
        features['horse_id'] = horse_id
        features['target_win'] = 1 if row['着順'] == 1 else 0
        features['target_place'] = 1 if row['着順'] <= 3 else 0

        results.append(features)

    except Exception as e:
        errors.append({
            'race_id': race_id,
            'horse_id': horse_id,
            'error': str(e)
        })

    # チェックポイント保存
    if (idx + 1) % checkpoint_interval == 0:
        print()  # 改行
        log_print(f"  チェックポイント保存: {idx+1:,}レース")

        checkpoint_df = pd.DataFrame(results)
        checkpoint_df.to_csv(checkpoint_file, index=False, encoding='utf-8-sig')

        # エラーログ保存
        if errors:
            error_df = pd.DataFrame(errors)
            error_df.to_csv('calculate_features_errors.csv', index=False, encoding='utf-8-sig')
            log_print(f"  エラー: {len(errors)}件")

        log_print("")

print()  # 最終改行

# ===================================================================
# 最終保存
# ===================================================================

log_print("")
log_print("[5/7] 最終保存中...")

df_features = pd.DataFrame(results)

# 訓練・検証・テスト分割
log_print("  データ分割中...")
df_features['year'] = df_features['race_id'].astype(str).str[:4].astype(int)

df_train = df_features[df_features['year'].isin([2020, 2021, 2022, 2023])]
df_val = df_features[df_features['year'] == 2024]
df_test = df_features[df_features['year'] == 2025]

log_print(f"  訓練データ（2020-2023）: {len(df_train):,}")
log_print(f"  検証データ（2024）: {len(df_val):,}")
log_print(f"  テストデータ（2025）: {len(df_test):,}")
log_print("")

# ディレクトリ作成
os.makedirs('data/phase14', exist_ok=True)

# 保存
df_train.to_csv('data/phase14/train_features.csv', index=False, encoding='utf-8-sig')
df_val.to_csv('data/phase14/val_features.csv', index=False, encoding='utf-8-sig')
df_test.to_csv('data/phase14/test_features.csv', index=False, encoding='utf-8-sig')

log_print("  保存完了:")
log_print(f"    data/phase14/train_features.csv ({len(df_train):,})")
log_print(f"    data/phase14/val_features.csv ({len(df_val):,})")
log_print(f"    data/phase14/test_features.csv ({len(df_test):,})")
log_print("")

# エラーログ
if errors:
    error_df = pd.DataFrame(errors)
    error_df.to_csv('data/phase14/feature_errors.csv', index=False, encoding='utf-8-sig')
    log_print(f"  エラーログ: data/phase14/feature_errors.csv ({len(errors)}件)")
    log_print("")

# チェックポイントファイル削除
if os.path.exists(checkpoint_file):
    os.remove(checkpoint_file)
    log_print("  チェックポイントファイル削除")
    log_print("")

# ===================================================================
# サマリー
# ===================================================================

log_print("="*80)
log_print(" 特徴量計算完了")
log_print("="*80)
log_print("")
log_print(f"総処理レコード: {len(results):,}")
log_print(f"エラー: {len(errors)}件")
log_print(f"処理時間: {(time.time() - start_time)/3600:.1f}時間")
log_print("")
log_print("【次のステップ】")
log_print("  1. Phase 2: Phase 13再検証（data/phase14/val_features.csvを使用）")
log_print("  2. Phase 3: Phase 14モデル訓練")
log_print("  3. Phase 3: バックテスト検証")
log_print("")
log_print("="*80)

log_file.close()
