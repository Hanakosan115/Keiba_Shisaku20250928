"""
get_horse_details()のデバッグ
"""

from update_from_list import ListBasedUpdater

print("="*60)
print("get_horse_details() デバッグ")
print("="*60)

updater = ListBasedUpdater()

# ダブルハートボンドの馬ID
horse_id = '2021105700'

print(f"\n馬ID: {horse_id}")
print(f"URL: https://db.netkeiba.com/horse/{horse_id}/\n")

# 馬詳細情報取得
horse_details = updater.get_horse_details(horse_id)

print(f"取得結果:")
print(f"  error: {horse_details.get('error', 'なし')}")
print(f"  birthday: {horse_details.get('birthday')}")
print(f"  trainer: {horse_details.get('trainer')}")
print(f"  owner: {horse_details.get('owner')}")
print(f"  total_earnings: {horse_details.get('total_earnings')}")
print(f"  is_local_transfer: {horse_details.get('is_local_transfer')}")
print(f"  num_jra_starts: {horse_details.get('num_jra_starts')}")

# 過去戦績
race_results = horse_details.get('race_results', [])
print(f"\n過去戦績:")
print(f"  レース数: {len(race_results)}")

if race_results:
    print(f"\n最初の3レース:")
    for i, r in enumerate(race_results[:3], 1):
        print(f"  {i}. {r.get('date')} {r.get('place')} {r.get('race_name')}")
        print(f"      {r.get('course_type')}{r.get('distance')}m 着順:{r.get('rank')}")
else:
    print(f"  過去戦績が取得できませんでした")
    print(f"\nデバッグ情報:")
    print(f"  horse_details keys: {list(horse_details.keys())}")

print(f"\n{'='*60}")
