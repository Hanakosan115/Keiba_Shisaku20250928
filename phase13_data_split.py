# -*- coding: utf-8 -*-
"""
Phase 13: 正しい時系列分割によるデータ準備
リーケージ完全排除版
"""
import pandas as pd
import numpy as np
from datetime import datetime
import pickle

print("=" * 80)
print("  Phase 13: データ分割（時系列・リーケージ排除）")
print("=" * 80)
print()

# データ読み込み
print("[1/5] データ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
print(f"  総レコード数: {len(df):,}")
print()

# 日付正規化
print("[2/5] 日付処理中...")
# 日本語形式の日付を変換: 2024年01月27日 -> 2024-01-27
df['date_str'] = df['date'].astype(str).str.replace('年', '-').str.replace('月', '-').str.replace('日', '')
df['date_normalized'] = pd.to_datetime(df['date_str'], errors='coerce')
df = df.dropna(subset=['date_normalized'])
df = df.drop('date_str', axis=1)

# 年・月を抽出
df['year'] = df['date_normalized'].dt.year
df['month'] = df['date_normalized'].dt.month

print(f"  有効レコード数: {len(df):,}")
print()

# 年別レース数
print("年別レース数:")
year_counts = df['year'].value_counts().sort_index()
for year, count in year_counts.items():
    print(f"  {year}年: {count:,}レース")
print()

# 時系列分割
print("[3/5] 時系列分割実行...")
print()

train_df = df[df['year'].isin([2020, 2021, 2022])].copy()
val_df = df[df['year'] == 2023].copy()
test_df = df[df['year'] == 2024].copy()

print("分割結果:")
print(f"  訓練データ（2020-2022年）: {len(train_df):,}レース")
print(f"  検証データ（2023年）:      {len(val_df):,}レース")
print(f"  テストデータ（2024年）:    {len(test_df):,}レース")
print()

# 確認: 日付の重複がないか
train_max = train_df['date_normalized'].max()
val_min = val_df['date_normalized'].min()
val_max = val_df['date_normalized'].max()
test_min = test_df['date_normalized'].min()

print("日付範囲の確認:")
print(f"  訓練: {train_df['date_normalized'].min()} ～ {train_max}")
print(f"  検証: {val_min} ～ {val_max}")
print(f"  テスト: {test_min} ～ {test_df['date_normalized'].max()}")
print()

if train_max < val_min and val_max < test_min:
    print("[OK] 日付の重複なし - 正しい時系列分割")
else:
    print("[WARNING] 日付の重複あり")
print()

# 保存
print("[4/5] 分割データ保存中...")
train_df.to_csv('phase13_train_2020_2022.csv', index=False)
val_df.to_csv('phase13_val_2023.csv', index=False)
test_df.to_csv('phase13_test_2024.csv', index=False)
print("  保存完了")
print()

# メタデータ保存
print("[5/5] メタデータ保存中...")
metadata = {
    'split_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'train_period': '2020-2022',
    'val_period': '2023',
    'test_period': '2024',
    'train_size': len(train_df),
    'val_size': len(val_df),
    'test_size': len(test_df),
    'train_date_range': (str(train_df['date_normalized'].min()), str(train_max)),
    'val_date_range': (str(val_min), str(val_max)),
    'test_date_range': (str(test_min), str(test_df['date_normalized'].max())),
    'no_leakage_verified': train_max < val_min and val_max < test_min,
}

with open('phase13_split_metadata.pkl', 'wb') as f:
    pickle.dump(metadata, f)

print("  メタデータ保存完了")
print()

print("=" * 80)
print("  データ分割完了")
print("=" * 80)
print()
print("次のステップ:")
print("  1. phase13_train_2020_2022.csv で特徴量エンジニアリング")
print("  2. リーケージなし特徴量の作成")
print("  3. モデル訓練")
