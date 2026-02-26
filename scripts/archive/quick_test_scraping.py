"""
スクレイピング動作確認
"""

from smart_update_system import SmartUpdater

updater = SmartUpdater()

# テストレースID
test_race_id = '202408010104'
print(f'テストレースID: {test_race_id}')
print('='*60)

result = updater.scrape_race_result(test_race_id)

if result is not None and len(result) > 0:
    print(f'OK 取得成功: {len(result)}頭')
    print(f'\nレース名: {result.iloc[0]["race_name"]}')
    print(f'日付: {result.iloc[0]["date"]}')
    print('\n上位3頭:')
    for i in range(min(3, len(result))):
        row = result.iloc[i]
        print(f'  {row["Rank"]}着 {row["Umaban"]}番 {row["HorseName"]} ({row["Odds"]}倍)')
else:
    print('NG 取得失敗')

print('\n完了')
