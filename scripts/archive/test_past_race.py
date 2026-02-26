"""
過去レース対応のテスト
"""

from predict_by_race_id import DirectRacePredictor

print("="*80)
print("過去レース対応テスト")
print("="*80)

predictor = DirectRacePredictor()

# 過去レースID
test_race_id = '202505050812'  # 2025年5月5日 東京8R

print(f"\nテストレースID: {test_race_id}")
print("これは過去のレースなので、結果ページから取得します\n")

result = predictor.predict_race(test_race_id, budget=10000)

if result:
    print("\n[成功] 過去レースの取得と予想ができました！")
else:
    print("\n[失敗] レース情報が取得できませんでした")
    print("レースIDを確認してください")

print("\n" + "="*80)
