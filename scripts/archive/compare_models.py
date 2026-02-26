"""
ベースラインモデル vs 脚質特徴量込みモデルの比較
- 2位・3位の予測精度の改善を検証
- 3連系の的中率の改善を検証
"""
import pandas as pd

print("=" * 80)
print("モデル比較: ベースライン vs 脚質特徴量込み")
print("=" * 80)

# ベースラインモデルの結果（train_with_best_params.py + backtest_tuned_model.py）
baseline = {
    'name': 'ベースライン (22特徴量)',
    'features': 22,
    'accuracy': {
        '1st': 33.7,  # analyze_trifecta_accuracy.pyの結果
        '2nd': 18.2,
        '3rd': 14.2,
        'trio': 9.0,
        'trifecta': 1.9
    },
    'recovery': {
        'ワイド_1-2': 166.7,
        'ワイド_1軸流し': 159.9,
        'ワイド_BOX3頭': 142.6
    }
}

# 脚質特徴量込みモデルの結果はバックテスト後に追加

print("\n【ベースラインモデルの性能】")
print("-" * 80)
print(f"特徴量数: {baseline['features']}次元")
print(f"\n予測精度:")
print(f"  1位的中率: {baseline['accuracy']['1st']:.1f}%")
print(f"  2位的中率: {baseline['accuracy']['2nd']:.1f}% [低い]")
print(f"  3位的中率: {baseline['accuracy']['3rd']:.1f}% [低い]")
print(f"  3連複的中率: {baseline['accuracy']['trio']:.1f}%")
print(f"  3連単的中率: {baseline['accuracy']['trifecta']:.1f}%")

print(f"\n回収率:")
for strategy, rate in baseline['recovery'].items():
    print(f"  {strategy}: {rate:.1f}%")

print("\n" + "=" * 80)
print("脚質特徴量追加による改善ポイント:")
print("=" * 80)
print("""
【追加した特徴量】(+5次元)
1. escape_rate (逃げ率): 過去レースで序盤1-2位だった割合
2. leading_rate (先行率): 過去レースで序盤3-5位だった割合
3. closing_rate (差し率): 過去レースで序盤6-10位だった割合
4. pursuing_rate (追い込み率): 過去レースで序盤11位以下だった割合
5. avg_agari (平均上がり3F): 過去レースの上がり3Fの平均値

【期待される改善】
- 展開を考慮した予測が可能に
  例: 逃げ馬が多いレースでは、差し・追い込み馬の評価が上がる
- 脚質適性を反映
  例: 差し馬の評価が適切になり、2位・3位の予測精度向上
- オッズ・人気に過度に依存しない予測
  例: 不人気でも脚質が合えば上位に来る可能性を評価

【目標】
- 2位的中率: 18.2% → 22%以上
- 3位的中率: 14.2% → 18%以上
- 3連複的中率: 9.0% → 12%以上
""")

print("\n脚質特徴量込みモデルの訓練が完了したら、")
print("backtest_running_style_model.py を実行して結果を確認してください。")
