"""
race_resultsデータを持つ馬を探すスクリプト
"""
import pickle
import os

cache_path = r"C:\Users\bu158\HorseRacingAnalyzer\data\horse_cache.pkl"

print("=" * 60)
print("race_resultsデータを持つ馬を検索中...")
print("=" * 60)

if not os.path.exists(cache_path):
    print(f"エラー: ファイルが見つかりません: {cache_path}")
    exit()

# キャッシュを読み込む
with open(cache_path, 'rb') as f:
    horse_cache = pickle.load(f)

print(f"\n総馬数: {len(horse_cache)}")

# race_resultsを持つ馬を探す
horses_with_data = []
horses_without_data = 0
max_races = 0
max_races_horse = None

for horse_id, data in horse_cache.items():
    if isinstance(data, dict) and 'race_results' in data:
        race_results = data.get('race_results', [])
        if len(race_results) > 0:
            horses_with_data.append({
                'horse_id': horse_id,
                'race_count': len(race_results),
                'data': data
            })

            if len(race_results) > max_races:
                max_races = len(race_results)
                max_races_horse = {
                    'horse_id': horse_id,
                    'race_count': len(race_results),
                    'data': data
                }
        else:
            horses_without_data += 1

print(f"\n[統計]")
print(f"race_resultsあり: {len(horses_with_data)}頭")
print(f"race_resultsなし: {horses_without_data}頭")

if horses_with_data:
    avg_races = sum([h['race_count'] for h in horses_with_data]) / len(horses_with_data)
    print(f"平均レース数: {avg_races:.1f}レース")
    print(f"最大レース数: {max_races}レース")

    # トップ5を表示
    print("\n" + "=" * 60)
    print("race_results保有数トップ5")
    print("=" * 60)

    horses_with_data.sort(key=lambda x: x['race_count'], reverse=True)

    for i, horse in enumerate(horses_with_data[:5], 1):
        data = horse['data']
        name = data.get('HorseName', 'N/A')
        print(f"\n{i}. 馬ID: {horse['horse_id']}")
        print(f"   馬名: {name}")
        print(f"   レース数: {horse['race_count']}")

    # 最も多くレースを走った馬の詳細
    if max_races_horse:
        print("\n" + "=" * 60)
        print("最多レース数の馬のrace_results詳細")
        print("=" * 60)

        data = max_races_horse['data']
        print(f"\n馬ID: {max_races_horse['horse_id']}")
        print(f"馬名: {data.get('HorseName', 'N/A')}")
        print(f"総レース数: {max_races_horse['race_count']}")

        race_results = data['race_results']
        print(f"\n最新5走:")
        for i, race in enumerate(race_results[:5], 1):
            if isinstance(race, dict):
                date = race.get('date', 'N/A')
                place = race.get('place', 'N/A')
                distance = race.get('distance', 'N/A')
                rank = race.get('rank', 'N/A')
                course_type = race.get('course_type', 'N/A')
                baba = race.get('baba', 'N/A')
                print(f"{i}走前: {date} {place} {course_type}{distance}m {baba} → {rank}着")

                # 全キーを表示（データ構造確認）
                if i == 1:
                    print(f"\n  [データ構造] 利用可能なキー:")
                    for key in race.keys():
                        print(f"    - {key}: {race[key]}")
else:
    print("\n警告: race_resultsデータを持つ馬が1頭も見つかりませんでした")

print("\n" + "=" * 60)
