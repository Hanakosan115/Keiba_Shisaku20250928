"""
実際のスクレイピング結果の列名を確認
"""
import sys
sys.path.append('.')
from update_from_list import ListBasedUpdater

print("テストレースをスクレイピング中...")
print()

updater = ListBasedUpdater()

# 2024年の適当なレースでテスト
test_race_id = '202405010101'

print(f"レースID: {test_race_id}")
print()

df = updater.scrape_race_result(test_race_id, collect_horse_details=False)

if df is not None and len(df) > 0:
    print(f"OK: {len(df)}行取得")
    print()
    print("列名一覧:")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2d}. {col}")
    print()
    print("馬番に関連する列:")
    for col in df.columns:
        if '馬' in col or 'uma' in col.lower() or '番' in col:
            print(f"  - {col}")
            print(f"    サンプル値: {df[col].head(3).tolist()}")
else:
    print("NG: データ取得失敗")
