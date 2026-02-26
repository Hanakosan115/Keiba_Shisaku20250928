"""
全特徴量を統合した最終データセット作成

ラップタイム特徴量と展開予想特徴量を統合
"""

import pandas as pd
import numpy as np

def merge_all_features():
    """全特徴量を統合"""
    print("=" * 80)
    print("全特徴量の統合")
    print("=" * 80)

    # 1. ラップタイムデータ読み込み
    print("\n1. ラップタイムデータ読み込み中...")
    lap_file = "netkeiba_data_2020_2024_clean_with_class_and_laps.csv"
    df_laps = pd.read_csv(lap_file, encoding='utf-8', low_memory=False)
    print(f"   読み込み: {len(df_laps)} レコード")

    # 重複除去
    before_dedup = len(df_laps)
    df_laps = df_laps.drop_duplicates(subset=['race_id', 'Umaban'], keep='first')
    after_dedup = len(df_laps)
    print(f"   重複除去: {before_dedup - after_dedup} 行削除")
    print(f"   最終: {len(df_laps)} レコード")
    print(f"   カラム数: {len(df_laps.columns)}")

    # ラップタイム関連カラムを抽出
    lap_columns = ['laps', 'lap_count', 'pace_category',
                   'first_3f_avg', 'last_3f_avg', 'pace_variance', 'pace_acceleration']

    available_lap_cols = [col for col in lap_columns if col in df_laps.columns]
    print(f"   ラップタイム特徴量: {available_lap_cols}")

    # 2. 展開予想データ読み込み
    print("\n2. 展開予想データ読み込み中...")
    pace_file = "netkeiba_data_2020_2024_clean_with_class_and_pace.csv"
    df_pace = pd.read_csv(pace_file, encoding='utf-8', low_memory=False)
    print(f"   読み込み: {len(df_pace)} レコード")

    # 重複除去
    before_dedup = len(df_pace)
    df_pace = df_pace.drop_duplicates(subset=['race_id', 'Umaban'], keep='first')
    after_dedup = len(df_pace)
    print(f"   重複除去: {before_dedup - after_dedup} 行削除")
    print(f"   最終: {len(df_pace)} レコード")
    print(f"   カラム数: {len(df_pace.columns)}")

    # 展開予想関連カラムを抽出
    pace_columns = ['running_style', 'escape_count', 'leading_count',
                    'sashi_count', 'oikomi_count', 'pace_prediction',
                    'development', 'pace_match_score']

    available_pace_cols = [col for col in pace_columns if col in df_pace.columns]
    print(f"   展開予想特徴量: {available_pace_cols}")

    # 3. マージ用のキーを確認
    print("\n3. データ統合...")

    # race_idとUmabanでマージできるか確認
    if 'race_id' in df_laps.columns and 'Umaban' in df_laps.columns:
        merge_keys = ['race_id', 'Umaban']
        print(f"   マージキー: {merge_keys}")

        # ラップタイムデータから展開予想カラムを取得
        pace_subset = df_pace[merge_keys + available_pace_cols].copy()

        # マージ
        df_merged = df_laps.merge(
            pace_subset,
            on=merge_keys,
            how='left',
            suffixes=('', '_pace')
        )

        print(f"   マージ後レコード数: {len(df_merged)}")
        print(f"   マージ後カラム数: {len(df_merged.columns)}")

        # 4. 統計情報
        print("\n" + "=" * 80)
        print("統合後の特徴量統計")
        print("=" * 80)

        # ラップタイム統計
        print("\nラップタイム特徴量:")
        for col in available_lap_cols:
            if col in df_merged.columns:
                not_null = df_merged[col].notna().sum()
                pct = 100 * not_null / len(df_merged)
                print(f"  {col:20s}: {not_null:7d} ({pct:5.1f}%)")

        # 展開予想統計
        print("\n展開予想特徴量:")
        for col in available_pace_cols:
            if col in df_merged.columns:
                not_null = df_merged[col].notna().sum()
                pct = 100 * not_null / len(df_merged)
                print(f"  {col:20s}: {not_null:7d} ({pct:5.1f}%)")

        # 5. 保存
        output_file = "netkeiba_data_2020_2024_enhanced.csv"
        print(f"\n5. 保存中: {output_file}")
        df_merged.to_csv(output_file, index=False, encoding='utf-8')

        # ファイルサイズ確認
        import os
        file_size = os.path.getsize(output_file) / (1024 * 1024)
        print(f"   ファイルサイズ: {file_size:.2f} MB")

        print("\n" + "=" * 80)
        print("完了！")
        print("=" * 80)

        # サンプルデータ表示
        print("\nサンプルデータ（最初の3行）:")
        sample_cols = ['race_id', 'Umaban', 'HorseName', 'Rank'] + \
                      available_lap_cols[:3] + available_pace_cols[:3]
        sample_cols = [col for col in sample_cols if col in df_merged.columns]
        print(df_merged[sample_cols].head(3))

        return df_merged

    else:
        print("エラー: マージキーが見つかりません")
        return None


if __name__ == '__main__':
    merge_all_features()
