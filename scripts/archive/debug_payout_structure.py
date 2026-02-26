"""
配当データの構造を確認するデバッグスクリプト
"""
import json
from data_config import MAIN_JSON

print("=" * 80)
print("配当データ構造確認")
print("=" * 80)

# JSONファイル読み込み
with open(MAIN_JSON, 'r', encoding='utf-8') as f:
    payout_list = json.load(f)

print(f"\n総レース数: {len(payout_list)}")

# 最初の5レースのデータを詳細表示
for i, race_data in enumerate(payout_list[:5], 1):
    print(f"\n{'-' * 80}")
    print(f"レース {i}")
    print(f"{'-' * 80}")

    race_id = race_data.get('race_id', 'N/A')
    print(f"race_id: {race_id}")

    # 利用可能なキーを表示
    print(f"\n利用可能なキー: {list(race_data.keys())}")

    # 3連単データ
    if '3連単' in race_data:
        print(f"\n[3連単]")
        trifecta = race_data['3連単']
        print(f"  データ型: {type(trifecta)}")
        print(f"  キー: {list(trifecta.keys()) if isinstance(trifecta, dict) else 'N/A'}")
        print(f"  馬番: {trifecta.get('馬番', 'N/A')}")
        print(f"  払戻金: {trifecta.get('払戻金', 'N/A')}")
        print(f"  人気: {trifecta.get('人気', 'N/A')}")
    else:
        print("\n[3連単] データなし")

    # 3連複データ
    if '3連複' in race_data:
        print(f"\n[3連複]")
        trio = race_data['3連複']
        print(f"  データ型: {type(trio)}")
        print(f"  キー: {list(trio.keys()) if isinstance(trio, dict) else 'N/A'}")
        print(f"  馬番: {trio.get('馬番', 'N/A')}")
        print(f"  払戻金: {trio.get('払戻金', 'N/A')}")
        print(f"  人気: {trio.get('人気', 'N/A')}")
    else:
        print("\n[3連複] データなし")

    # ワイドデータ（参考）
    if 'ワイド' in race_data:
        print(f"\n[ワイド]")
        wide = race_data['ワイド']
        print(f"  データ型: {type(wide)}")
        print(f"  キー: {list(wide.keys()) if isinstance(wide, dict) else 'N/A'}")
        print(f"  馬番: {wide.get('馬番', 'N/A')}")
        print(f"  払戻金: {wide.get('払戻金', 'N/A')}")
    else:
        print("\n[ワイド] データなし")

# 統計情報
print(f"\n{'=' * 80}")
print("統計情報")
print(f"{'=' * 80}")

count_trifecta = sum(1 for race in payout_list if '3連単' in race)
count_trio = sum(1 for race in payout_list if '3連複' in race)
count_wide = sum(1 for race in payout_list if 'ワイド' in race)

print(f"\n3連単データあり: {count_trifecta}レース ({count_trifecta/len(payout_list)*100:.1f}%)")
print(f"3連複データあり: {count_trio}レース ({count_trio/len(payout_list)*100:.1f}%)")
print(f"ワイドデータあり: {count_wide}レース ({count_wide/len(payout_list)*100:.1f}%)")

print(f"\n{'=' * 80}")
print("確認完了")
print(f"{'=' * 80}")
