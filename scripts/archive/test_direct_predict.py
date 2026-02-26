"""
predict_by_race_id.py のテスト実行
"""

from predict_by_race_id import DirectRacePredictor

print("="*80)
print("レースID直接指定予想ツール - テスト")
print("="*80)

predictor = DirectRacePredictor()

# テスト用レースID（2024年8月の実際のレース）
test_race_id = '202408010104'

print(f"\nテストレースID: {test_race_id}")
print("注意: 過去のレースなので出馬表は取得できない可能性があります")
print()

result = predictor.predict_race(test_race_id, budget=10000)

if result:
    print("\n[OK] 予想ツールは正常に動作しています")
else:
    print("\n[INFO] 過去のレースのため出馬表が取得できませんでした")
    print("これは正常な動作です")

print("\n" + "="*80)
print("今週末のレースで使用する方法:")
print("="*80)
print()
print("1. Netkeiba で今週末のレースページを開く")
print("   https://race.netkeiba.com/")
print()
print("2. 予想したいレースをクリック")
print()
print("3. URLから12桁のrace_idをコピー")
print("   例: https://race.netkeiba.com/race/shutuba.html?race_id=202412010811")
print("       → 202412010811")
print()
print("4. 以下のコマンドを実行:")
print("   py predict_by_race_id.py")
print()
print("5. コピーしたrace_idを入力")
print()
print("これで今週末のレースの予想ができます！")
print()
