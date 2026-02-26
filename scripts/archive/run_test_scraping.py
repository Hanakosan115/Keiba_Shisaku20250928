"""
血統情報込みの最終テスト
"""

import os
from update_from_list import ListBasedUpdater

# テストCSVを削除
test_csv = 'test_final.csv'
if os.path.exists(test_csv):
    os.remove(test_csv)
    print(f"削除: {test_csv}\n")

# スクレイピング実行
print("="*60)
print("血統情報込みスクレイピングテスト")
print("="*60)

updater = ListBasedUpdater(db_path=test_csv)
updater.update_from_file('test_race_ids_small.txt')

# 結果確認
if os.path.exists(test_csv):
    import pandas as pd
    df = pd.read_csv(test_csv, encoding='utf-8')

    print(f"\n{'='*60}")
    print(f"結果確認")
    print(f"{'='*60}")
    print(f"レコード数: {len(df)}")
    print(f"列数: {len(df.columns)}")

    # 重要な列をチェック
    important_cols = [
        'race_id', 'race_name', 'horse_name', 'horse_id',
        'father', 'mother_father', 'jockey', 'odds', 'weather'
    ]

    print(f"\n主要列の有無:")
    for col in important_cols:
        exists = col in df.columns
        print(f"  {col}: {'✓' if exists else '✗'}")

    # サンプルデータ表示
    if len(df) > 0:
        print(f"\nサンプルデータ（1行目）:")
        for col in important_cols:
            if col in df.columns:
                val = df.iloc[0][col]
                print(f"  {col}: {val}")

        # 血統情報の取得状況
        if 'father' in df.columns:
            father_count = df['father'].notna().sum()
            print(f"\n血統情報:")
            print(f"  father取得数: {father_count}/{len(df)}")

        if 'mother_father' in df.columns:
            mother_father_count = df['mother_father'].notna().sum()
            print(f"  mother_father取得数: {mother_father_count}/{len(df)}")

    print(f"\n{'='*60}")
    print("テスト完了！")
    print(f"{'='*60}")

else:
    print("\nCSVファイルが作成されませんでした")
