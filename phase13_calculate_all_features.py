# -*- coding: utf-8 -*-
"""
Phase 13: 全レースの特徴量計算（リーケージ完全排除版）

238,176レース全てに対して、時系列を守った特徴量を計算する。
推定時間: 3-6時間
"""
import pandas as pd
import numpy as np
import pickle
import time
from datetime import datetime
from phase13_feature_engineering import (
    calculate_horse_features_safe,
    calculate_sire_stats,
    calculate_trainer_jockey_stats,
    normalize_date
)

print("=" * 80)
print("  Phase 13: 全レース特徴量計算（リーケージ排除版）")
print("=" * 80)
print()
print("推定時間: 3-6時間")
print("チェックポイント: 10,000レースごとに中間保存")
print()

# ===================================================================
# データ読み込み
# ===================================================================

print("[1/7] データ読み込み中...")
train_df = pd.read_csv('phase13_train_2020_2022.csv', low_memory=False)
val_df = pd.read_csv('phase13_val_2023.csv', low_memory=False)
test_df = pd.read_csv('phase13_test_2024.csv', low_memory=False)

print(f"  訓練: {len(train_df):,}レース")
print(f"  検証: {len(val_df):,}レース")
print(f"  テスト: {len(test_df):,}レース")
print(f"  合計: {len(train_df) + len(val_df) + len(test_df):,}レース")
print()

# 全データ結合（過去レース検索用）
df_all = pd.concat([train_df, val_df, test_df], ignore_index=True)
print(f"  全データ: {len(df_all):,}行")
print()

# ===================================================================
# 統計計算（訓練期間のみ）
# ===================================================================

print("[2/7] 訓練期間データで統計計算中...")
sire_stats = calculate_sire_stats(train_df)
trainer_jockey_stats = calculate_trainer_jockey_stats(train_df)
print(f"  種牡馬統計: {len(sire_stats)}頭")
print(f"  調教師統計: {len(trainer_jockey_stats['trainer'])}人")
print(f"  騎手統計: {len(trainer_jockey_stats['jockey'])}人")
print()

# ===================================================================
# 特徴量計算関数
# ===================================================================

def calculate_features_for_dataset(df, dataset_name, df_all_ref, sire_stats, trainer_jockey_stats):
    """
    データセット全体の特徴量を計算

    Args:
        df: 対象データセット（train/val/test）
        dataset_name: データセット名（ログ用）
        df_all_ref: 全データ（過去レース検索用）
        sire_stats: 種牡馬統計
        trainer_jockey_stats: 調教師・騎手統計

    Returns:
        pd.DataFrame: 特徴量付きデータフレーム
    """
    total = len(df)
    results = []
    errors = []

    start_time = time.time()
    checkpoint_interval = 10000

    print(f"  [{dataset_name}] 特徴量計算開始: {total:,}レース")
    print(f"  チェックポイント: {checkpoint_interval:,}レースごと")
    print()

    for idx, row in df.iterrows():
        if (idx + 1) % 100 == 0:
            elapsed = time.time() - start_time
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            remaining = (total - idx - 1) / rate if rate > 0 else 0
            print(f"\r  進捗: {idx+1:,}/{total:,} ({(idx+1)/total*100:.1f}%) "
                  f"| 速度: {rate:.1f}レース/秒 | 残り時間: {remaining/60:.1f}分", end='')

        race_id = row['race_id']
        horse_id = row['horse_id']
        cutoff_date = normalize_date(row['date'])

        if pd.isna(cutoff_date) or pd.isna(horse_id):
            errors.append({
                'race_id': race_id,
                'horse_id': horse_id,
                'error': 'cutoff_date or horse_id is NA'
            })
            # デフォルト特徴量で埋める
            features = {
                'total_starts': 0,
                'total_win_rate': 0.0,
                'total_earnings': 0,
                'turf_win_rate': 0.0,
                'dirt_win_rate': 0.0,
                'distance_similar_win_rate': 0.0,
                'prev_race_rank': 99,
                'days_since_last_race': 365,
                'avg_passage_position': 0.0,
                'avg_last_3f': 0.0,
                'grade_race_starts': 0,
                'father_win_rate': 0.0,
                'father_top3_rate': 0.0,
                'mother_father_win_rate': 0.0,
                'mother_father_top3_rate': 0.0,
                'avg_diff_seconds': 1.0,
                'min_diff_seconds': 1.0,
                'prev_diff_seconds': 1.0,
                'avg_first_corner': 5.0,
                'avg_last_corner': 5.0,
                'avg_position_change': 0.0,
                'class_change': 0,
                'current_class': 3,
                'trainer_win_rate': 0.0,
                'trainer_top3_rate': 0.0,
                'trainer_starts': 0,
                'jockey_win_rate': 0.0,
                'jockey_top3_rate': 0.0,
                'jockey_starts': 0,
                'track_win_rate': 0.0,
                'track_top3_rate': 0.0,
                'race_distance': 1600,
                'is_turf': 0,
                'is_dirt': 0,
                'is_良': 1,
                'is_稍重': 0,
                'is_重': 0,
                'is_不良': 0,
                'frame_number': 4,
                'heavy_track_win_rate': 0.0,
                'distance_change': 0.0,
                'kiryou': 55.0,
                'is_female': 0,
                'horse_age': 0,
                'horse_weight': 0,
                'weight_change': 0,
                # Phase R2
                'father_turf_win_rate': 0.0,
                'father_dirt_win_rate': 0.0,
                'father_heavy_win_rate': 0.0,
                'father_short_win_rate': 0.0,
                'father_long_win_rate': 0.0,
                'mother_father_turf_win_rate': 0.0,
                'mother_father_dirt_win_rate': 0.0,
                'mother_father_heavy_win_rate': 0.0,
                'mother_father_short_win_rate': 0.0,
                'mother_father_long_win_rate': 0.0,
                'running_style': 3,
                'recent_3race_improvement': 0.0,
                'jockey_track_win_rate': 0.0,
                'jockey_track_top3_rate': 0.0,
                'good_track_win_rate': 0.0,
                'finish_strength': 0.0,
            }
        else:
            features = calculate_horse_features_safe(
                horse_id, df_all_ref, cutoff_date, sire_stats, trainer_jockey_stats,
                trainer_name=row.get('調教師'),
                jockey_name=row.get('騎手'),
                race_track=row.get('track_name'),
                race_distance=row.get('distance'),
                race_course_type=row.get('course_type'),
                race_track_condition=row.get('track_condition'),
                current_frame=row.get('waku'),
                race_id=race_id,
                horse_kiryou=row.get('斤量'),
                horse_seire=row.get('性齢'),
                horse_weight_str=row.get('馬体重'),
            )

            if features is None:
                errors.append({
                    'race_id': race_id,
                    'horse_id': horse_id,
                    'error': 'calculate_horse_features_safe returned None'
                })
                # デフォルト特徴量
                features = {
                    'total_starts': 0,
                    'total_win_rate': 0.0,
                    'total_earnings': 0,
                    'turf_win_rate': 0.0,
                    'dirt_win_rate': 0.0,
                    'distance_similar_win_rate': 0.0,
                    'prev_race_rank': 99,
                    'days_since_last_race': 365,
                    'avg_passage_position': 0.0,
                    'avg_last_3f': 0.0,
                    'grade_race_starts': 0,
                    'father_win_rate': 0.0,
                    'father_top3_rate': 0.0,
                    'mother_father_win_rate': 0.0,
                    'mother_father_top3_rate': 0.0,
                    'avg_diff_seconds': 1.0,
                    'min_diff_seconds': 1.0,
                    'prev_diff_seconds': 1.0,
                    'avg_first_corner': 5.0,
                    'avg_last_corner': 5.0,
                    'avg_position_change': 0.0,
                    'class_change': 0,
                    'current_class': 3,
                    'trainer_win_rate': 0.0,
                    'trainer_top3_rate': 0.0,
                    'trainer_starts': 0,
                    'jockey_win_rate': 0.0,
                    'jockey_top3_rate': 0.0,
                    'jockey_starts': 0,
                    'track_win_rate': 0.0,
                    'track_top3_rate': 0.0,
                    'race_distance': 1600,
                    'is_turf': 0,
                    'is_dirt': 0,
                    'is_良': 1,
                    'is_稍重': 0,
                    'is_重': 0,
                    'is_不良': 0,
                    'frame_number': 4,
                    'heavy_track_win_rate': 0.0,
                    'distance_change': 0.0,
                    'kiryou': 55.0,
                    'is_female': 0,
                    'horse_age': 0,
                    'horse_weight': 0,
                    'weight_change': 0,
                    # Phase R2
                    'father_turf_win_rate': 0.0,
                    'father_dirt_win_rate': 0.0,
                    'father_heavy_win_rate': 0.0,
                    'father_short_win_rate': 0.0,
                    'father_long_win_rate': 0.0,
                    'mother_father_turf_win_rate': 0.0,
                    'mother_father_dirt_win_rate': 0.0,
                    'mother_father_heavy_win_rate': 0.0,
                    'mother_father_short_win_rate': 0.0,
                    'mother_father_long_win_rate': 0.0,
                    'running_style': 3,
                    'recent_3race_improvement': 0.0,
                    'jockey_track_win_rate': 0.0,
                    'jockey_track_top3_rate': 0.0,
                    'good_track_win_rate': 0.0,
                    'finish_strength': 0.0,
                }

        # race_id, horse_id, rank（正解ラベル）を含める
        result = {
            'race_id': race_id,
            'horse_id': horse_id,
            'rank': row.get('rank'),
            'date': cutoff_date,
        }
        result.update(features)
        results.append(result)

        # チェックポイント保存
        if (idx + 1) % checkpoint_interval == 0:
            print()
            print(f"  チェックポイント: {idx+1:,}レース完了")
            checkpoint_df = pd.DataFrame(results)
            checkpoint_file = f'phase13_{dataset_name}_features_checkpoint_{idx+1}.csv'
            checkpoint_df.to_csv(checkpoint_file, index=False)
            print(f"  保存: {checkpoint_file}")
            print()

    print()
    total_time = time.time() - start_time
    print(f"  完了: {total:,}レース ({total_time/60:.1f}分)")
    print(f"  エラー: {len(errors)}件")

    # エラーログ保存
    if len(errors) > 0:
        error_df = pd.DataFrame(errors)
        error_file = f'phase13_{dataset_name}_errors.csv'
        error_df.to_csv(error_file, index=False)
        print(f"  エラーログ: {error_file}")

    print()

    return pd.DataFrame(results)

# ===================================================================
# 訓練データ
# ===================================================================

print("[3/7] 訓練データ（2020-2022年）の特徴量計算...")
train_features = calculate_features_for_dataset(
    train_df, 'train', df_all, sire_stats, trainer_jockey_stats
)
train_features.to_csv('phase13_train_features.csv', index=False)
print(f"  保存: phase13_train_features.csv")
print()

# ===================================================================
# 検証データ
# ===================================================================

print("[4/7] 検証データ（2023年）の特徴量計算...")
val_features = calculate_features_for_dataset(
    val_df, 'val', df_all, sire_stats, trainer_jockey_stats
)
val_features.to_csv('phase13_val_features.csv', index=False)
print(f"  保存: phase13_val_features.csv")
print()

# ===================================================================
# テストデータ
# ===================================================================

print("[5/7] テストデータ（2024年）の特徴量計算...")
test_features = calculate_features_for_dataset(
    test_df, 'test', df_all, sire_stats, trainer_jockey_stats
)
test_features.to_csv('phase13_test_features.csv', index=False)
print(f"  保存: phase13_test_features.csv")
print()

# ===================================================================
# メタデータ保存
# ===================================================================

print("[6/7] メタデータ保存...")
metadata = {
    'calculation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'train_size': len(train_features),
    'val_size': len(val_features),
    'test_size': len(test_features),
    'num_sires': len(sire_stats),
    'num_trainers': len(trainer_jockey_stats['trainer']),
    'num_jockeys': len(trainer_jockey_stats['jockey']),
    'feature_count': len(train_features.columns) - 4,  # race_id, horse_id, rank, date除く
    'leakage_free': True,
    'cutoff_date_used': True,
}

with open('phase13_features_metadata.pkl', 'wb') as f:
    pickle.dump(metadata, f)
print(f"  保存: phase13_features_metadata.pkl")
print()

# ===================================================================
# 統計サマリー
# ===================================================================

print("[7/7] 特徴量統計サマリー...")
print()
print("【訓練データ】")
print(train_features.describe().T[['mean', 'std', 'min', 'max']].to_string())
print()

print("=" * 80)
print("  全特徴量計算完了")
print("=" * 80)
print()
print("【次のステップ】")
print("  py phase13_train_model.py")
print()
