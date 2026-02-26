"""
直接スクレイピングしてCSV保存テスト
"""

import pandas as pd
from update_from_list import ListBasedUpdater

print("="*60)
print("直接スクレイピングテスト")
print("="*60)

# スクレイパー初期化
updater = ListBasedUpdater()

# テストレースID
race_id = '202507050211'

print(f"\nレースID: {race_id} をスクレイピング中...")

# スクレイピング実行
df = updater.scrape_race_result(race_id)

if df is not None and len(df) > 0:
    print(f"\nスクレイピング成功！")
    print(f"  レコード数: {len(df)}")
    print(f"  列数: {len(df.columns)}")

    # CSV保存
    output_file = 'test_direct_scraping.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\nCSV保存: {output_file}")

    # 重要列の確認
    important_cols = ['race_id', 'race_name', 'horse_name', 'horse_id', 'father', 'mother_father']

    print(f"\n主要データ確認:")
    for col in important_cols:
        if col in df.columns:
            sample_val = df.iloc[0][col] if len(df) > 0 else None
            print(f"  {col}: {sample_val}")

    # 血統情報の取得状況
    print(f"\n血統情報取得状況:")
    father_count = df['father'].notna().sum() if 'father' in df.columns else 0
    mother_father_count = df['mother_father'].notna().sum() if 'mother_father' in df.columns else 0
    print(f"  father取得: {father_count}/{len(df)} 頭")
    print(f"  mother_father取得: {mother_father_count}/{len(df)} 頭")

    # 最初の3頭の血統情報を表示
    print(f"\n血統情報サンプル（最初3頭）:")
    for i in range(min(3, len(df))):
        horse_name = df.iloc[i].get('horse_name', 'N/A')
        father = df.iloc[i].get('father', 'N/A')
        mother_father = df.iloc[i].get('mother_father', 'N/A')
        print(f"  {i+1}. {horse_name}: 父={father}, 母父={mother_father}")

    print(f"\n{'='*60}")
    print("テスト完了！")
    print(f"{'='*60}")

else:
    print(f"\nスクレイピング失敗")
