"""
Value Betting デモ

実オッズデータを使った簡単なデモ
"""

import pandas as pd
import numpy as np
import pickle
from value_betting_module import ValueBettingAnalyzer

print("="*80)
print("Value Betting デモ")
print("="*80)

# オッズデータ読み込み
print("\nオッズデータ読み込み中...")
odds_df = pd.read_csv('odds_2024_sample_500.csv', encoding='utf-8')

# 最初のレースを分析
race_id = '202408010104'
race_odds = odds_df[odds_df['race_id'] == int(race_id)]

print(f"\nレースID: {race_id}")
print(f"出走頭数: {len(race_odds)}頭\n")

# 馬データ準備
horses_data = []
for _, row in race_odds.iterrows():
    umaban = row['Umaban']
    odds = row['odds_real']

    # 簡易予測（オッズの逆数をスコアとして使用）
    score = 1.0 / odds

    horses_data.append({
        'umaban': umaban,
        'odds': odds,
        'score': score
    })

# スコアから順位計算
scores = [h['score'] for h in horses_data]
sorted_indices = np.argsort(scores)[::-1]
ranks = np.empty(len(scores))
ranks[sorted_indices] = np.arange(1, len(scores) + 1)

for i, h in enumerate(horses_data):
    h['predicted_rank'] = ranks[i]

# Value分析
print("Value分析実行中...")
analyzer = ValueBettingAnalyzer(value_threshold=0.05)

predicted_ranks = [h['predicted_rank'] for h in horses_data]
odds_list = [h['odds'] for h in horses_data]

values = analyzer.calculate_values(predicted_ranks, odds_list)

for i, h in enumerate(horses_data):
    h.update(values[i])

# 推奨ベット生成
recommendations = analyzer.recommend_bets(horses_data, budget=10000)

# 結果表示
print("\n" + "="*80)
print("馬別 Value一覧（上位10頭）")
print("="*80)
print(f"{'馬番':^6} {'オッズ':^8} {'予測順位':^10} {'Value':^10}")
print("-"*60)

horses_sorted = sorted(horses_data, key=lambda x: x['value'], reverse=True)
for h in horses_sorted[:10]:
    print(f"{h['umaban']:^6} {h['odds']:^8.1f} "
          f"{h['predicted_rank']:^10.2f} {h['value']*100:^+9.2f}%")

# 推奨ベット表示
print("\n" + analyzer.format_recommendation(recommendations))

# 複数レースで試す
print("\n" + "="*80)
print("全500レースの統計")
print("="*80)

all_race_ids = odds_df['race_id'].unique()
total_value_bets = 0
total_races = len(all_race_ids)

for race_id in all_race_ids[:50]:  # 最初の50レースで統計
    race_odds = odds_df[odds_df['race_id'] == race_id]

    horses_data = []
    for _, row in race_odds.iterrows():
        umaban = row['Umaban']
        odds = row['odds_real']
        score = 1.0 / odds

        horses_data.append({
            'umaban': umaban,
            'odds': odds,
            'score': score
        })

    # スコアから順位計算
    scores = [h['score'] for h in horses_data]
    sorted_indices = np.argsort(scores)[::-1]
    ranks = np.empty(len(scores))
    ranks[sorted_indices] = np.arange(1, len(scores) + 1)

    for i, h in enumerate(horses_data):
        h['predicted_rank'] = ranks[i]

    # Value計算
    predicted_ranks = [h['predicted_rank'] for h in horses_data]
    odds_list = [h['odds'] for h in horses_data]

    values = analyzer.calculate_values(predicted_ranks, odds_list)

    for i, h in enumerate(horses_data):
        h.update(values[i])

    # Value馬をカウント
    value_horses = analyzer.get_value_bets(horses_data)
    total_value_bets += len(value_horses)

print(f"\n分析レース数: 50レース")
print(f"Value閾値5%超の馬: 合計{total_value_bets}頭")
print(f"レースあたり平均: {total_value_bets/50:.2f}頭")

print("\n" + "="*80)
print("デモ完了")
print("="*80)
print("\n次のステップ:")
print("  - GUI版: python keiba_yosou_tool_value_betting.py")
print("  - バックテスト: python backtest_place_value.py")
print("  - 詳細: VALUE_BETTING_README.md を参照")
