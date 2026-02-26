"""
ラップタイム追加処理の進捗確認スクリプト
"""

import os

def check_progress():
    """処理の進捗を確認"""
    output_file = "netkeiba_data_2020_2024_clean_with_class_and_laps.csv"

    if not os.path.exists(output_file):
        print("まだCSVファイルが作成されていません。処理開始前または実行中です。")
        return

    # ファイルサイズを確認
    file_size = os.path.getsize(output_file) / (1024 * 1024)  # MB
    print(f"現在のファイルサイズ: {file_size:.2f} MB")

    # 行数を確認（簡易版）
    try:
        import pandas as pd
        df = pd.read_csv(output_file, nrows=1000)

        # ラップタイムが追加されているか確認
        if 'laps' in df.columns:
            # ラップタイムがある行の数を確認
            has_laps = df['laps'].notna().sum()
            print(f"\nサンプル1000行のうち、ラップタイムあり: {has_laps}行")
            print(f"ラップタイム取得率: {100*has_laps/len(df):.1f}%")

            # サンプルデータを表示
            print("\nサンプルデータ:")
            sample = df[df['laps'].notna()].head(3)
            for idx, row in sample.iterrows():
                print(f"  レースID: {row['race_id']}")
                print(f"  ラップ: {row['laps']}")
                print(f"  ペース: {row['pace_category']}")
                print()
        else:
            print("\nまだラップタイム列が追加されていません。")
    except Exception as e:
        print(f"\nエラー: {e}")

if __name__ == '__main__':
    print("=" * 80)
    print("ラップタイム追加処理 - 進捗確認")
    print("=" * 80)
    check_progress()
    print("\n" + "=" * 80)
    print("処理完了確認:")
    print("  完了サインを確認するには、出力ファイルの最終行を確認してください。")
    print("=" * 80)
