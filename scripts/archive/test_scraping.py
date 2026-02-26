"""
データ収集スクリプトの動作確認
"""

from smart_update_system_v2 import SmartUpdaterV2

print('='*80)
print('データ収集スクリプト動作確認')
print('='*80)

updater = SmartUpdaterV2()

# テストレース一覧
test_races = [
    ('202408010104', '2024年8月のレース'),
    ('202410030812', '2024年10月のレース'),
    ('202411090911', '2024年11月のレース'),
    ('202412010811', '2024年12月のレース（先週）'),
    ('202505050812', '2025年5月のレース（未来）'),
]

results = []

for race_id, description in test_races:
    print(f'\n【テスト】{description}')
    print(f'レースID: {race_id}')

    result = updater.scrape_race_result(race_id)

    if result is not None and len(result) > 0:
        print(f'[OK] 取得成功: {len(result)}頭')
        print(f'  レース名: {result.iloc[0]["race_name"]}')
        print(f'  日付: {result.iloc[0].get("date", "N/A")}')
        results.append(True)
    else:
        print('[NG] 取得失敗')
        results.append(False)

print('\n' + '='*80)
print('まとめ')
print('='*80)
print(f'取得成功: {sum(results)}/{len(results)}')
print(f'取得失敗: {len(results) - sum(results)}/{len(results)}')

# 成功したレースを確認
print('\n【成功したレース】')
for i, (race_id, desc) in enumerate(test_races):
    if results[i]:
        print(f'  {race_id}: {desc}')

print('\n【失敗したレース】')
for i, (race_id, desc) in enumerate(test_races):
    if not results[i]:
        print(f'  {race_id}: {desc}')
