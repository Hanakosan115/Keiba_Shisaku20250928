"""
訓練進捗確認スクリプト
"""

import os
import time

def check_training_progress():
    """訓練の進捗を確認"""
    print("=" * 80)
    print("訓練進捗確認")
    print("=" * 80)

    # モデルファイルの存在確認
    model_file = "lgbm_model_enhanced.pkl"

    if os.path.exists(model_file):
        file_size = os.path.getsize(model_file) / (1024 * 1024)  # MB
        mod_time = time.ctime(os.path.getmtime(model_file))
        print(f"\n✅ モデルファイル作成済み")
        print(f"  ファイル: {model_file}")
        print(f"  サイズ: {file_size:.2f} MB")
        print(f"  更新日時: {mod_time}")
        print("\n訓練完了！")
    else:
        print(f"\n⏳ モデルファイル未作成")
        print(f"  ファイル: {model_file}")
        print("\n訓練実行中...")

        # データファイルの確認
        data_file = "netkeiba_data_2020_2024_enhanced.csv"
        if os.path.exists(data_file):
            file_size = os.path.getsize(data_file) / (1024 * 1024)  # MB
            print(f"\n  データファイル: {data_file}")
            print(f"  データサイズ: {file_size:.2f} MB")
            print(f"\n  大規模データセットのため、特徴量抽出に時間がかかります")
            print(f"  推定時間: 10-20分")

    print("\n" + "=" * 80)

if __name__ == '__main__':
    check_training_progress()
