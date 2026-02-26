"""
高度なバックテスト - 複勝・三連系・予測スコアベース
"""
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
import lightgbm as lgb

print("="*80)
print(" 高度バックテスト - 複数の賭け式を検証")
print("="*80)
print()

# ========================================
# 1. データ読み込み
# ========================================
print("[1] データ読み込み...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
df['year'] = df['race_id'].astype(str).str[:4]

# 2024年で学習、2025年でテスト
df_train = df[df['year'] == '2024'].copy()
df_test = df[df['year'] == '2025'].copy()

print(f"    学習: {len(df_train):,}行")
print(f"    テスト: {len(df_test):,}行")
print()

# ========================================
# 2. モデル学習（3着以内を予測）
# ========================================
print("[2] 予測モデル学習中...")

# ターゲット作成（3着以内=1）
df_train['rank'] = pd.to_numeric(df_train['着順'], errors='coerce')
df_test['rank'] = pd.to_numeric(df_test['着順'], errors='coerce')

df_train['target_place'] = (df_train['rank'] <= 3).astype(int)
df_test['target_place'] = (df_test['rank'] <= 3).astype(int)

# 特徴量
features = ['人気', '単勝', '馬体重', 'distance', 'total_starts', 'total_win_rate',
            'total_earnings', 'turf_win_rate', 'dirt_win_rate',
            'distance_similar_win_rate', 'prev_race_rank', 'days_since_last_race']

# 欠損値処理
for feat in features:
    if feat in df_train.columns:
        df_train[feat] = pd.to_numeric(df_train[feat], errors='coerce')
        df_test[feat] = pd.to_numeric(df_test[feat], errors='coerce')

# 利用可能な特徴量を確認
available_features = [f for f in features if f in df_train.columns]
print(f"    利用可能な特徴量: {len(available_features)}個")

# 欠損値を中央値で埋める
for feat in available_features:
    median_val = df_train[feat].median()
    df_train[feat].fillna(median_val, inplace=True)
    df_test[feat].fillna(median_val, inplace=True)

# target_placeがNaNのものを除外
df_train_clean = df_train[df_train['target_place'].notna()].copy()
df_test_clean = df_test[df_test['target_place'].notna() & df_test['rank'].notna()].copy()

X_train = df_train_clean[available_features].values
y_train = df_train_clean['target_place'].values

X_test = df_test_clean[available_features].values
y_test = df_test_clean['target_place'].values

print(f"    学習データ: {len(X_train):,}行")
print(f"    テストデータ: {len(X_test):,}行")

# LightGBM学習
model = lgb.LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)
model.fit(X_train, y_train)

# 予測確率
df_test_clean['prob_place'] = model.predict_proba(X_test)[:, 1]

print(f"    学習完了！テストデータ: {len(df_test_clean):,}行")
print()

# ========================================
# 3. 賭け式別バックテスト
# ========================================
print("[3] 賭け式別バックテスト実行中...")
print()

# オッズ情報
df_test_clean['odds'] = pd.to_numeric(df_test_clean['単勝'], errors='coerce')

results = []

# ========================================
# 戦略1: 複勝（予測確率上位）
# ========================================
print("--- 戦略1: 複勝（予測確率TOP3） ---")

# レースごとにグループ化
race_groups = df_test_clean.groupby('race_id')

total_bet = 0
total_return = 0
races_bet = 0
wins = 0

for race_id, race_df in race_groups:
    # 予測確率上位3頭
    top3 = race_df.nlargest(3, 'prob_place')

    for _, horse in top3.iterrows():
        total_bet += 100  # 1頭100円

        # 3着以内なら的中（複勝配当は単勝の1/5と仮定）
        if horse['rank'] <= 3:
            wins += 1
            # 複勝配当 = 単勝オッズ / 5 * 賭け金（簡易計算）
            payout = max(horse['odds'] / 5, 1.1) * 100
            total_return += payout

    races_bet += 1

hit_rate = wins / (races_bet * 3) * 100
recovery = total_return / total_bet * 100

print(f"  賭け数: {races_bet * 3:,}（{races_bet:,}レース x 3頭）")
print(f"  的中数: {wins:,}")
print(f"  的中率: {hit_rate:.2f}%")
print(f"  総賭け金: {total_bet:,}円")
print(f"  総払戻: {int(total_return):,}円")
print(f"  回収率: {recovery:.1f}%")
print(f"  損益: {int(total_return - total_bet):,}円")
print()

results.append({
    '戦略': '複勝TOP3',
    '回収率': f"{recovery:.1f}%",
    '的中率': f"{hit_rate:.2f}%",
    '損益': int(total_return - total_bet)
})

# ========================================
# 戦略2: 単勝（予測確率TOP1のみ厳選）
# ========================================
print("--- 戦略2: 単勝（予測確率60%以上） ---")

total_bet = 0
total_return = 0
races_bet = 0
wins = 0

for race_id, race_df in race_groups:
    # 予測確率が60%以上の最上位馬のみ
    top1 = race_df.nlargest(1, 'prob_place').iloc[0]

    if top1['prob_place'] >= 0.6:
        total_bet += 100
        races_bet += 1

        if top1['rank'] == 1:
            wins += 1
            total_return += top1['odds'] * 100

if races_bet > 0:
    hit_rate = wins / races_bet * 100
    recovery = total_return / total_bet * 100

    print(f"  賭け数: {races_bet:,}レース")
    print(f"  的中数: {wins:,}")
    print(f"  的中率: {hit_rate:.2f}%")
    print(f"  総賭け金: {total_bet:,}円")
    print(f"  総払戻: {int(total_return):,}円")
    print(f"  回収率: {recovery:.1f}%")
    print(f"  損益: {int(total_return - total_bet):,}円")
    print()

    results.append({
        '戦略': '単勝（確率60%以上）',
        '回収率': f"{recovery:.1f}%",
        '的中率': f"{hit_rate:.2f}%",
        '損益': int(total_return - total_bet)
    })

# ========================================
# 戦略3: 三連複BOX（予測TOP5）
# ========================================
print("--- 戦略3: 三連複BOX（予測TOP5） ---")

total_bet = 0
total_return = 0
races_bet = 0
wins = 0

for race_id, race_df in race_groups:
    # 予測確率上位5頭
    top5 = race_df.nlargest(5, 'prob_place')

    # 5頭BOX = 10通り（5C3）
    bet_count = 10
    total_bet += bet_count * 100
    races_bet += 1

    # 実際の上位3着を取得
    actual_top3 = set(race_df.nsmallest(3, 'rank')['馬名'].values)
    predicted_top5 = set(top5['馬名'].values)

    # 3着以内が全て予測TOP5に含まれていれば的中
    if len(actual_top3 - predicted_top5) == 0:
        wins += 1
        # 三連複の平均配当を仮定（人気度合いで変動）
        avg_popularity = top5['人気'].mean()
        estimated_payout = max(1000, 5000 / avg_popularity) * 100  # 簡易計算
        total_return += estimated_payout

hit_rate = wins / races_bet * 100
recovery = total_return / total_bet * 100

print(f"  賭け数: {races_bet:,}レース（各10通り）")
print(f"  的中数: {wins:,}")
print(f"  的中率: {hit_rate:.2f}%")
print(f"  総賭け金: {total_bet:,}円")
print(f"  総払戻: {int(total_return):,}円")
print(f"  回収率: {recovery:.1f}%")
print(f"  損益: {int(total_return - total_bet):,}円")
print()

results.append({
    '戦略': '三連複BOX（TOP5）',
    '回収率': f"{recovery:.1f}%",
    '的中率': f"{hit_rate:.2f}%",
    '損益': int(total_return - total_bet)
})

# ========================================
# 戦略4: ワイド（予測TOP3の組み合わせ）
# ========================================
print("--- 戦略4: ワイド（予測TOP3の組み合わせ） ---")

total_bet = 0
total_return = 0
races_bet = 0
wins = 0

for race_id, race_df in race_groups:
    top3 = race_df.nlargest(3, 'prob_place')

    # 3頭から2頭選ぶ = 3通り
    bet_count = 3
    total_bet += bet_count * 100
    races_bet += 1

    # 実際の上位3着
    actual_top3_ranks = race_df.nsmallest(3, 'rank')['馬名'].values
    predicted_names = top3['馬名'].values

    # 予測3頭のうち2頭が3着以内なら的中
    matches = len(set(predicted_names) & set(actual_top3_ranks))

    if matches >= 2:
        wins += 1
        # ワイド平均配当を仮定
        avg_odds = top3['odds'].mean()
        estimated_payout = max(avg_odds * 30, 150) * 100
        total_return += estimated_payout

hit_rate = wins / races_bet * 100
recovery = total_return / total_bet * 100

print(f"  賭け数: {races_bet:,}レース（各3通り）")
print(f"  的中数: {wins:,}")
print(f"  的中率: {hit_rate:.2f}%")
print(f"  総賭け金: {total_bet:,}円")
print(f"  総払戻: {int(total_return):,}円")
print(f"  回収率: {recovery:.1f}%")
print(f"  損益: {int(total_return - total_bet):,}円")
print()

results.append({
    '戦略': 'ワイド（TOP3組合せ）',
    '回収率': f"{recovery:.1f}%",
    '的中率': f"{hit_rate:.2f}%",
    '損益': int(total_return - total_bet)
})

# ========================================
# 4. 結果まとめ
# ========================================
print("="*80)
print("最終結果まとめ")
print("="*80)
print()

results_df = pd.DataFrame(results)
results_df['回収率_num'] = results_df['回収率'].str.replace('%', '').astype(float)
results_df = results_df.sort_values('回収率_num', ascending=False)

print(results_df[['戦略', '回収率', '的中率', '損益']].to_string(index=False))
print()

# ベスト戦略
best = results_df.iloc[0]
print(f"【最良戦略】: {best['戦略']}")
print(f"  回収率: {best['回収率']}")
print(f"  的中率: {best['的中率']}")
print(f"  損益: {best['損益']:,}円")
print()

if best['回収率_num'] >= 100:
    print("✓ 回収率100%超え！この戦略は利益が出る可能性あり！")
else:
    print("× まだ回収率100%未満です")
    print("  改善案:")
    print("  1. 予測確率の閾値をさらに上げる（より厳選）")
    print("  2. オッズと予測確率の乖離を狙う（バリューベット）")
    print("  3. より多くの特徴量でモデル精度を上げる")

print()
