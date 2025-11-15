"""
horse_cache.pklの構造を確認するスクリプト
"""
import pickle
import os

cache_path = r"C:\Users\bu158\HorseRacingAnalyzer\data\horse_cache.pkl"

print("=" * 60)
print("horse_cache.pkl 構造確認")
print("=" * 60)

if not os.path.exists(cache_path):
    print(f"エラー: ファイルが見つかりません: {cache_path}")
    input("\nEnterキーで終了...")
    exit()

# キャッシュを読み込む
print(f"\n読み込み中: {cache_path}")
with open(cache_path, 'rb') as f:
    horse_cache = pickle.load(f)

print(f"[OK] 読み込み完了")
print(f"総馬数: {len(horse_cache)}")

# サンプルデータを表示
print("\n" + "=" * 60)
print("サンプルデータ（最初の1頭）")
print("=" * 60)

# 最初の馬のデータを取得
sample_horse_id = list(horse_cache.keys())[0]
sample_data = horse_cache[sample_horse_id]

print(f"\n馬ID: {sample_horse_id}")
print(f"\nデータ構造:")
if isinstance(sample_data, dict):
    for key, value in sample_data.items():
        if isinstance(value, list):
            print(f"  {key}: リスト（{len(value)}件）")
            if len(value) > 0:
                print(f"    最初の要素: {value[0]}")
        elif isinstance(value, dict):
            print(f"  {key}: 辞書（{len(value)}個のキー）")
            print(f"    キー: {list(value.keys())[:5]}")
        else:
            print(f"  {key}: {value}")
else:
    print(f"データ型: {type(sample_data)}")
    print(f"内容: {sample_data}")

# race_resultsの詳細を確認
print("\n" + "=" * 60)
print("race_results の詳細（過去成績）")
print("=" * 60)

if isinstance(sample_data, dict) and 'race_results' in sample_data:
    race_results = sample_data['race_results']
    print(f"\n過去成績の件数: {len(race_results)}")

    if len(race_results) > 0:
        print(f"\n最新レースのデータ構造:")
        latest_race = race_results[0]
        if isinstance(latest_race, dict):
            for key, value in latest_race.items():
                print(f"  {key}: {value}")

        print(f"\n過去5走:")
        for i, race in enumerate(race_results[:5]):
            if isinstance(race, dict):
                date = race.get('date', 'N/A')
                track = race.get('place', 'N/A')
                distance = race.get('distance', 'N/A')
                rank = race.get('rank', 'N/A')
                course_type = race.get('course_type', 'N/A')
                baba = race.get('baba', 'N/A')
                print(f"  {i+1}走前: {date} {track} {course_type}{distance}m {baba} → {rank}着")

# 他の重要な情報
print("\n" + "=" * 60)
print("その他の重要情報")
print("=" * 60)

if isinstance(sample_data, dict):
    if 'father' in sample_data:
        print(f"\n父: {sample_data['father']}")
    if 'mother_father' in sample_data:
        print(f"母父: {sample_data['mother_father']}")
    if 'HorseName' in sample_data:
        print(f"馬名: {sample_data['HorseName']}")

# ランダムに数頭確認
print("\n" + "=" * 60)
print("ランダムサンプル（3頭）")
print("=" * 60)

import random
sample_ids = random.sample(list(horse_cache.keys()), min(3, len(horse_cache)))

for horse_id in sample_ids:
    data = horse_cache[horse_id]
    if isinstance(data, dict):
        name = data.get('HorseName', 'N/A')
        race_count = len(data.get('race_results', []))
        print(f"\n馬ID: {horse_id}")
        print(f"  馬名: {name}")
        print(f"  過去成績: {race_count}レース")

        if race_count > 0:
            latest = data['race_results'][0]
            if isinstance(latest, dict):
                print(f"  最新: {latest.get('date')} {latest.get('place')} {latest.get('rank')}着")

print("\n" + "=" * 60)
print("確認完了")
print("=" * 60)

input("\nEnterキーで終了...")
