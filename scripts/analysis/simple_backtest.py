"""
シンプルなバックテスト
LightGBMモデルの予測結果を使って回収率を計算
"""
import pandas as pd
import numpy as np

print("="*80)
print(" バックテスト - 賭け戦略シミュレーション")
print("="*80)
print()

# データ読み込み
print("[1] データ読み込み...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

# race_idから年を抽出
df['year'] = df['race_id'].astype(str).str[:4]

# 2025年のデータをテスト用に使用
df_test = df[df['year'] == '2025'].copy()

print(f"    テスト期間: 2025年")
print(f"    レース数: {df_test['race_id'].nunique():,}")
print(f"    出走数: {len(df_test):,}")
print()

# 必要なカラムの準備
print("[2] データ整形中...")
df_test['rank'] = pd.to_numeric(df_test['着順'], errors='coerce')
df_test['odds'] = pd.to_numeric(df_test['単勝'], errors='coerce')
df_test['popularity'] = pd.to_numeric(df_test['人気'], errors='coerce')

# 欠損値除去
df_test = df_test[df_test['rank'].notna() & df_test['odds'].notna()].copy()

print(f"    有効データ: {len(df_test):,}行")
print()

# レースごとにグループ化
print("[3] バックテスト実行中...")
print()

strategies = {
    '1番人気': lambda x: x['popularity'] == 1,
    '2番人気': lambda x: x['popularity'] == 2,
    '3番人気': lambda x: x['popularity'] == 3,
    '1-3番人気': lambda x: x['popularity'] <= 3,
    '4-6番人気': lambda x: (x['popularity'] >= 4) & (x['popularity'] <= 6),
    'オッズ3倍以下': lambda x: x['odds'] <= 3.0,
    'オッズ5倍以下': lambda x: x['odds'] <= 5.0,
    'オッズ10倍以下': lambda x: x['odds'] <= 10.0,
}

print("="*80)
print("戦略別バックテスト結果")
print("="*80)
print()

results = []

for strategy_name, condition in strategies.items():
    # 戦略に該当する馬を抽出
    bets = df_test[condition(df_test)].copy()

    if len(bets) == 0:
        continue

    # 賭けレース数
    races_bet = bets['race_id'].nunique()

    # 総賭け金（1レースあたり100円と仮定）
    total_bet = len(bets) * 100

    # 的中数
    wins = (bets['rank'] == 1).sum()

    # 的中率
    hit_rate = wins / len(bets) * 100

    # 払戻金
    winning_bets = bets[bets['rank'] == 1]
    total_return = (winning_bets['odds'] * 100).sum()

    # 回収率
    recovery_rate = (total_return / total_bet) * 100

    # 損益
    profit = total_return - total_bet

    results.append({
        '戦略': strategy_name,
        '賭け数': len(bets),
        'レース数': races_bet,
        '的中数': wins,
        '的中率': f"{hit_rate:.2f}%",
        '平均オッズ': f"{bets['odds'].mean():.2f}倍",
        '総賭け金': f"{total_bet:,}円",
        '総払戻': f"{int(total_return):,}円",
        '回収率': f"{recovery_rate:.1f}%",
        '損益': f"{int(profit):,}円"
    })

# 結果表示
results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))
print()

# ベスト戦略
print("="*80)
print("おすすめ戦略")
print("="*80)
print()

# 回収率でソート
results_df['回収率_num'] = results_df['回収率'].str.replace('%', '').astype(float)
best_strategy = results_df.loc[results_df['回収率_num'].idxmax()]

print(f"最高回収率の戦略: {best_strategy['戦略']}")
print(f"  回収率: {best_strategy['回収率']}")
print(f"  的中率: {best_strategy['的中率']}")
print(f"  損益: {best_strategy['損益']}")
print()

# 的中率が高い戦略
results_df['的中率_num'] = results_df['的中率'].str.replace('%', '').astype(float)
best_hit = results_df.loc[results_df['的中率_num'].idxmax()]

print(f"最高的中率の戦略: {best_hit['戦略']}")
print(f"  的中率: {best_hit['的中率']}")
print(f"  回収率: {best_hit['回収率']}")
print(f"  損益: {best_hit['損益']}")
print()

print("="*80)
print("まとめ")
print("="*80)
print()
print("・回収率100%を超える戦略があれば利益が出る可能性あり")
print("・的中率が高くてもオッズが低いと回収率は低くなる")
print("・中穴狙い（4-6番人気など）で高回収率になることもある")
print()
