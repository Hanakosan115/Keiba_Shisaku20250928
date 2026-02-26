"""
的中判定ロジックの検証
なぜ馬連と馬単、3連複と3連単の的中数が同じになるのか？
"""
from itertools import combinations, permutations

print("=" * 80)
print("的中判定ロジックの検証")
print("=" * 80)

# 例：予測top3が [10, 5, 3] の場合
predicted_top3 = [10, 5, 3]

print(f"\n予測top3: {predicted_top3}")
print(f"  ◎ {predicted_top3[0]}番")
print(f"  ○ {predicted_top3[1]}番")
print(f"  ▲ {predicted_top3[2]}番")

# 馬連の組合せ（順序不問）
umaren_pairs = list(combinations(predicted_top3, 2))
print(f"\n馬連3頭BOXの組合せ（{len(umaren_pairs)}点）:")
for pair in umaren_pairs:
    print(f"  {pair}")

# 馬単の組合せ（順序あり）
umatan_pairs = list(permutations(predicted_top3, 2))
print(f"\n馬単3頭BOXの組合せ（{len(umatan_pairs)}点）:")
for pair in umatan_pairs:
    print(f"  {pair[0]}→{pair[1]}")

# 3連複の組合せ（順序不問）
sanrenpuku_combos = list(combinations(predicted_top3, 3))
print(f"\n3連複3頭BOXの組合せ（{len(sanrenpuku_combos)}点）:")
for combo in sanrenpuku_combos:
    print(f"  {combo}")

# 3連単の組合せ（順序あり）
sanrentan_perms = list(permutations(predicted_top3, 3))
print(f"\n3連単3頭BOXの組合せ（{len(sanrentan_perms)}点）:")
for perm in sanrentan_perms:
    print(f"  {perm[0]}→{perm[1]}→{perm[2]}")

print("\n" + "=" * 80)
print("【重要な発見】")
print("=" * 80)

# 実際の結果の例
actual_1st = 10
actual_2nd = 5
actual_3rd = 3

print(f"\n実際の結果: 1着={actual_1st}番, 2着={actual_2nd}番, 3着={actual_3rd}番")

# 馬連判定
umaren_hit = False
actual_umaren_pair = set([actual_1st, actual_2nd])
for pair in umaren_pairs:
    if set(pair) == actual_umaren_pair:
        umaren_hit = True
        break

print(f"\n馬連: {'的中' if umaren_hit else '不的中'}")

# 馬単判定
umatan_hit = False
actual_umatan_pair = (actual_1st, actual_2nd)
for pair in umatan_pairs:
    if pair == actual_umatan_pair:
        umatan_hit = True
        break

print(f"馬単: {'的中' if umatan_hit else '不的中'}")

# 3連複判定
sanrenpuku_hit = False
actual_sanrenpuku_set = set([actual_1st, actual_2nd, actual_3rd])
for combo in sanrenpuku_combos:
    if set(combo) == actual_sanrenpuku_set:
        sanrenpuku_hit = True
        break

print(f"3連複: {'的中' if sanrenpuku_hit else '不的中'}")

# 3連単判定
sanrentan_hit = False
actual_sanrentan_tuple = (actual_1st, actual_2nd, actual_3rd)
for perm in sanrentan_perms:
    if perm == actual_sanrentan_tuple:
        sanrentan_hit = True
        break

print(f"3連単: {'的中' if sanrentan_hit else '不的中'}")

print("\n" + "=" * 80)
print("【数学的考察】")
print("=" * 80)

print("""
■ 3頭BOXの場合の的中条件:

1. 馬連で的中する条件:
   実際の1着と2着の馬番が、予測top3の中に含まれている
   → {実際の1着, 実際の2着} ⊆ {予測top3}

2. 馬単で的中する条件（3頭BOX買いの場合）:
   実際の1着と2着の馬番が、予測top3の中に含まれている
   → 全順序を買うので、馬連と同じ条件で的中

3. 3連複で的中する条件:
   実際の1-2-3着の馬番が、予測top3と完全一致
   → {実際の1着, 2着, 3着} = {予測top3}

4. 3連単で的中する条件（3頭BOX買いの場合）:
   実際の1-2-3着の馬番が、予測top3と完全一致
   → 全順序を買うので、3連複と同じ条件で的中

■ 結論:
「3頭BOX」という買い方では、理論的に：
  - 馬連の的中 = 馬単の的中
  - 3連複の的中 = 3連単の的中

これは数学的に正しい！
""")

print("\n" + "=" * 80)
print("【実例で確認】")
print("=" * 80)

test_cases = [
    # (予測top3, 実際の1-2-3着)
    ([10, 5, 3], (10, 5, 3)),  # 完全一致
    ([10, 5, 3], (10, 5, 7)),  # 1-2着一致、3着外れ
    ([10, 5, 3], (5, 10, 3)),  # 順序違い
    ([10, 5, 3], (10, 7, 3)),  # 2着外れ
    ([10, 5, 3], (7, 8, 9)),   # 全外れ
]

for i, (predicted, actual) in enumerate(test_cases, 1):
    print(f"\nケース{i}: 予測{predicted} vs 実際{actual}")

    # 馬連判定
    umaren_hit = set([actual[0], actual[1]]).issubset(set(predicted))
    # 馬単判定（BOX買い）
    umatan_hit = actual[0] in predicted and actual[1] in predicted
    # 3連複判定
    sanrenpuku_hit = set(actual) == set(predicted)
    # 3連単判定（BOX買い）
    sanrentan_hit = set(actual) == set(predicted)

    print(f"  馬連: {'○' if umaren_hit else '×'}  馬単: {'○' if umatan_hit else '×'}  ", end="")
    print(f"3連複: {'○' if sanrenpuku_hit else '×'}  3連単: {'○' if sanrentan_hit else '×'}")

    print(f"  → 馬連と馬単: {'同じ' if umaren_hit == umatan_hit else '異なる'}")
    print(f"  → 3連複と3連単: {'同じ' if sanrenpuku_hit == sanrentan_hit else '異なる'}")

print("\n" + "=" * 80)
print("【最終結論】")
print("=" * 80)
print("""
バックテストで馬連と馬単、3連複と3連単の的中数が同じになるのは、
「3頭BOX」という買い方の性質上、**数学的に正しい**結果です。

ただし、これは以下の問題があります：

1. 実用的でない
   - 馬単6点、3連単6点を全て買うのは投資額が大きい
   - 通常は軸馬を決めてフォーメーション買いをする

2. 回収率が過大評価される
   - 馬単や3連単は高配当を取りやすい
   - BOX買いだと投資額も大きいが、それを考慮しても回収率が高く見える

3. より現実的な買い方を検証すべき
   - 例：◎を1着固定、○▲を2着流し（フォーメーション）
   - 例：◎○の2頭軸、▲以下を3着流し

推奨：フォーメーション買いのバックテストを追加で作成する
""")
