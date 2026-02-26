"""
複勝オッズ推定の妥当性検証

実際の複勝オッズデータがないため、理論値と比較
"""

import pandas as pd
import numpy as np

# サンプルケースで検証
test_cases = [
    # (単勝オッズ, 出走頭数, 推定複勝オッズ, 実際の複勝オッズ目安)
    (1.5, 16, None, 1.1),   # 1番人気
    (3.0, 16, None, 1.3),   # 2番人気
    (5.0, 16, None, 1.7),   # 3番人気
    (10.0, 16, None, 2.5),  # 4-5番人気
    (20.0, 16, None, 4.0),  # 中穴
    (50.0, 16, None, 8.0),  # 大穴
    (100.0, 16, None, 15.0), # 超大穴
]

def estimate_place_odds_current(win_odds, num_horses):
    """現在の推定式"""
    if num_horses <= 7:
        place_odds = win_odds * 0.5
    else:
        place_odds = win_odds * 0.35
    return max(place_odds, 1.1)

def estimate_place_odds_realistic(win_odds, num_horses):
    """
    より現実的な推定式

    実際の複勝オッズは:
    - 1番人気: 単勝の1/5～1/10程度
    - 中穴: 単勝の1/3～1/4程度
    - 大穴: 単勝の1/2.5程度
    """
    if win_odds < 2.0:
        # 1番人気クラス
        ratio = 0.15
    elif win_odds < 5.0:
        # 2-3番人気クラス
        ratio = 0.20
    elif win_odds < 10.0:
        # 4-5番人気クラス
        ratio = 0.25
    elif win_odds < 20.0:
        # 中穴クラス
        ratio = 0.30
    else:
        # 大穴クラス
        ratio = 0.35

    place_odds = win_odds * ratio
    return max(place_odds, 1.1)

print("="*80)
print("複勝オッズ推定の検証")
print("="*80)

print("\n{:>8s} | {:>6s} | {:>10s} | {:>10s} | {:>10s}".format(
    "単勝", "頭数", "現在の推定", "改善推定", "実際目安"
))
print("-" * 60)

for win_odds, num_horses, _, actual_estimate in test_cases:
    current = estimate_place_odds_current(win_odds, num_horses)
    realistic = estimate_place_odds_realistic(win_odds, num_horses)

    print("{:>7.1f}倍 | {:>6d} | {:>9.2f}倍 | {:>9.2f}倍 | {:>9.1f}倍".format(
        win_odds, num_horses, current, realistic, actual_estimate
    ))

print("\n" + "="*80)
print("分析")
print("="*80)

print("\n現在の推定式の問題点:")
print("  - 単勝1.5倍 → 複勝0.53倍（現実では1.1倍程度）")
print("  - 単勝100倍 → 複勝35倍（現実では15倍程度）")
print("  - 全体的に複勝オッズを高く見積もりすぎ")
print("  → 回収率が異常に高くなる原因")

print("\n改善推定式:")
print("  - オッズレンジごとに異なる比率を適用")
print("  - 1番人気: 15%")
print("  - 2-3番人気: 20%")
print("  - 4-5番人気: 25%")
print("  - 中穴: 30%")
print("  - 大穴: 35%")

# 実際のケースで比較
print("\n" + "="*80)
print("実例での影響試算")
print("="*80)

# value_bets_detail.csvから的中した馬のオッズを見る
try:
    df = pd.read_csv('value_bets_detail.csv', encoding='utf-8-sig')
    wins = df[df['actual_rank'] <= 3].copy()

    print(f"\n的中数: {len(wins)}件")
    print("\n単勝オッズ別の分布:")

    wins['odds_range'] = pd.cut(wins['odds'],
                                  bins=[0, 5, 10, 20, 50, 200],
                                  labels=['1-5倍', '5-10倍', '10-20倍', '20-50倍', '50倍以上'])

    for range_name in ['1-5倍', '5-10倍', '10-20倍', '20-50倍', '50倍以上']:
        range_wins = wins[wins['odds_range'] == range_name]
        if len(range_wins) > 0:
            avg_odds = range_wins['odds'].mean()
            count = len(range_wins)

            old_place = estimate_place_odds_current(avg_odds, 16)
            new_place = estimate_place_odds_realistic(avg_odds, 16)

            print(f"\n  {range_name}: {count}件 (平均単勝 {avg_odds:.1f}倍)")
            print(f"    現在の推定複勝: {old_place:.2f}倍")
            print(f"    改善後の推定複勝: {new_place:.2f}倍")
            print(f"    差額: {(old_place - new_place) * 100 * count:.0f}円")

    # 総回収率への影響
    total_old = sum(estimate_place_odds_current(row['odds'], 16) * 100
                    for _, row in wins.iterrows())
    total_new = sum(estimate_place_odds_realistic(row['odds'], 16) * 100
                    for _, row in wins.iterrows())

    investment = len(df) * 100

    print(f"\n総投資: {investment:,}円")
    print(f"現在の推定回収: {total_old:,.0f}円 ({total_old/investment*100:.1f}%)")
    print(f"改善後の推定回収: {total_new:,.0f}円 ({total_new/investment*100:.1f}%)")

except Exception as e:
    print(f"\nエラー: {e}")

print("\n" + "="*80)
print("完了")
print("="*80)
