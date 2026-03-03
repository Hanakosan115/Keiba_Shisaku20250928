"""
Phase 14: 複勝モデル用データ準備
目的変数を1-3着予測に変更
"""
import pandas as pd
import numpy as np
from datetime import datetime

print("="*80)
print("Phase 14: 複勝モデル用データ準備")
print("="*80)
print()

# 1. データ読み込み
print("[1/5] データ読み込み...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
print(f"  総レコード数: {len(df):,}")
print(f"  期間: {df['date'].min()} ~ {df['date'].max()}")
print()

# 2. 目的変数作成
print("[2/5] 目的変数作成...")

# Phase 13: 単勝（1着のみ）
df['target_win'] = (df['着順'] == 1).astype(int)

# Phase 14: 複勝（1-3着）
df['target_place'] = (df['着順'] <= 3).astype(int)

print(f"  単勝目的変数（target_win）:")
print(f"    1着: {df['target_win'].sum():,}件 ({df['target_win'].mean()*100:.1f}%)")
print(f"    2着以下: {(df['target_win']==0).sum():,}件")
print()
print(f"  複勝目的変数（target_place）:")
print(f"    1-3着: {df['target_place'].sum():,}件 ({df['target_place'].mean()*100:.1f}%)")
print(f"    4着以下: {(df['target_place']==0).sum():,}件")
print()

# 3. データ品質チェック
print("[3/5] データ品質チェック...")

# 欠損値確認
missing_rank = df['着順'].isna().sum()
print(f"  着順の欠損: {missing_rank:,}件")

if missing_rank > 0:
    print(f"  警告: 着順欠損のレコードを除外します")
    df = df[df['着順'].notna()].copy()
    print(f"  除外後: {len(df):,}レコード")
    print()

# レースごとの複勝圏内数を確認
race_place_counts = df.groupby('race_id')['target_place'].sum()
print(f"  レースごとの複勝圏内数:")
print(f"    平均: {race_place_counts.mean():.1f}頭")
print(f"    最小: {race_place_counts.min()}頭")
print(f"    最大: {race_place_counts.max()}頭")
print()

# 異常値確認（複勝圏内が0または10頭以上）
abnormal_races = race_place_counts[(race_place_counts == 0) | (race_place_counts >= 10)]
if len(abnormal_races) > 0:
    print(f"  警告: 異常なレース: {len(abnormal_races)}件")
    print(f"    （複勝圏内が0頭または10頭以上）")
    print()

# 4. 訓練・検証データ分割
print("[4/5] 訓練・検証データ分割...")

# 年度でソート（日本語形式の日付をパース）
def extract_year(date_str):
    import re
    s = str(date_str)
    match = re.search(r'(\d{4})年', s)
    if match:
        return int(match.group(1))
    # YYYY-MM-DD形式も試す
    match = re.search(r'^(\d{4})-', s)
    if match:
        return int(match.group(1))
    # race_idから抽出（最終手段）
    return None

df['year'] = df['date'].apply(extract_year)

# 訓練: 2020-2023
# 検証: 2024
# テスト: 2025（もしあれば）

df_train = df[df['year'].isin([2020, 2021, 2022, 2023])].copy()
df_val = df[df['year'] == 2024].copy()
df_test = df[df['year'] >= 2025].copy()

print(f"  訓練データ（2020-2023）: {len(df_train):,}レコード")
print(f"    複勝圏内: {df_train['target_place'].sum():,}件 ({df_train['target_place'].mean()*100:.1f}%)")
print()
print(f"  検証データ（2024）: {len(df_val):,}レコード")
print(f"    複勝圏内: {df_val['target_place'].sum():,}件 ({df_val['target_place'].mean()*100:.1f}%)")
print()

if len(df_test) > 0:
    print(f"  テストデータ（2025+）: {len(df_test):,}レコード")
    print(f"    複勝圏内: {df_test['target_place'].sum():,}件 ({df_test['target_place'].mean()*100:.1f}%)")
    print()

# 5. データ保存
print("[5/5] データ保存...")

# 訓練用データ
df_train.to_csv('data/phase14_train.csv', index=False, encoding='utf-8-sig')
print(f"  訓練データ: data/phase14_train.csv ({len(df_train):,}件)")

# 検証用データ
df_val.to_csv('data/phase14_val.csv', index=False, encoding='utf-8-sig')
print(f"  検証データ: data/phase14_val.csv ({len(df_val):,}件)")

if len(df_test) > 0:
    df_test.to_csv('data/phase14_test.csv', index=False, encoding='utf-8-sig')
    print(f"  テストデータ: data/phase14_test.csv ({len(df_test):,}件)")

# メタデータ保存
metadata = {
    'creation_date': datetime.now().isoformat(),
    'total_records': len(df),
    'train_records': len(df_train),
    'val_records': len(df_val),
    'test_records': len(df_test),
    'target_place_ratio': {
        'train': round(df_train['target_place'].mean(), 4),
        'val': round(df_val['target_place'].mean(), 4),
        'test': round(df_test['target_place'].mean(), 4) if len(df_test) > 0 else 0
    },
    'years': {
        'train': [2020, 2021, 2022, 2023],
        'val': [2024],
        'test': list(df_test['year'].unique()) if len(df_test) > 0 else []
    }
}

import json
with open('data/phase14_metadata.json', 'w', encoding='utf-8') as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

print(f"  メタデータ: data/phase14_metadata.json")
print()

# サマリー表示
print("="*80)
print("  データ準備完了")
print("="*80)
print()
print("【データセット概要】")
print(f"  訓練: {len(df_train):,}レコード（2020-2023年）")
print(f"  検証: {len(df_val):,}レコード（2024年）")
if len(df_test) > 0:
    print(f"  テスト: {len(df_test):,}レコード（2025年+）")
print()
print("【目的変数分布】")
print(f"  複勝圏内（1-3着）の割合:")
print(f"    訓練: {df_train['target_place'].mean()*100:.1f}%")
print(f"    検証: {df_val['target_place'].mean()*100:.1f}%")
print()
print("【次のステップ】")
print("  1. Phase 14用の特徴量エンジニアリング")
print("  2. LightGBMモデルの訓練")
print("  3. バックテスト検証")
print()
print("="*80)
print("完了")
print("="*80)
