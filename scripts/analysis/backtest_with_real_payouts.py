"""
実配当データを使った正確なバックテスト
"""
import pandas as pd
import numpy as np
import pickle
import lightgbm as lgb

print("="*80)
print(" 実配当データバックテスト")
print("="*80)
print()

# ========================================
# 1. データ読み込み
# ========================================
print("[1] データ読み込み...")

# レースデータ
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
df['year'] = df['race_id'].astype(str).str[:4]

# 払戻データ
with open('../../data/models/payout_cache_2024_2025.pkl', 'rb') as f:
    payout_data = pickle.load(f)

print(f"    レースデータ: {len(df):,}行")
print(f"    払戻データ: {len(payout_data):,}件")
print()

# ========================================
# 2. モデル学習
# ========================================
print("[2] 予測モデル学習...")

df_train = df[df['year'] == '2024'].copy()
df_test = df[df['year'] == '2025'].copy()

# ターゲット（3着以内）
df_train['rank'] = pd.to_numeric(df_train['着順'], errors='coerce')
df_test['rank'] = pd.to_numeric(df_test['着順'], errors='coerce')

df_train['target'] = (df_train['rank'] <= 3).astype(int)
df_test['target'] = (df_test['rank'] <= 3).astype(int)

# 特徴量
features = ['人気', '単勝', '馬体重', 'distance', 'total_starts', 'total_win_rate',
            'total_earnings', 'turf_win_rate', 'dirt_win_rate',
            'distance_similar_win_rate', 'prev_race_rank', 'days_since_last_race']

for feat in features:
    if feat in df_train.columns:
        df_train[feat] = pd.to_numeric(df_train[feat], errors='coerce')
        df_test[feat] = pd.to_numeric(df_test[feat], errors='coerce')

available_features = [f for f in features if f in df_train.columns]

for feat in available_features:
    median_val = df_train[feat].median()
    df_train[feat].fillna(median_val, inplace=True)
    df_test[feat].fillna(median_val, inplace=True)

df_train_clean = df_train[df_train['target'].notna()].copy()
df_test_clean = df_test[df_test['target'].notna() & df_test['rank'].notna()].copy()

X_train = df_train_clean[available_features].values
y_train = df_train_clean['target'].values

X_test = df_test_clean[available_features].values

# モデル学習
model = lgb.LGBMClassifier(n_estimators=100, random_state=42, verbose=-1)
model.fit(X_train, y_train)

# 予測確率
df_test_clean['prob'] = model.predict_proba(X_test)[:, 1]

print(f"    学習完了！")
print()

# ========================================
# 3. 払戻データとマッチング
# ========================================
print("[3] 払戻データとマッチング...")

def parse_multiple_payouts(payout_str):
    """払戻文字列から複数の金額を抽出"""
    try:
        # "110円230円400円" -> [110, 230, 400]
        # "2,880円" -> [2880]
        parts = [p for p in payout_str.split('円') if p.strip()]
        return [int(p.replace(',', '').strip()) for p in parts]
    except:
        return []

def parse_horse_numbers(horses_str, payout_count):
    """馬番文字列を分割（払戻数に合わせて）"""
    # '7613' with 3 payouts -> ['7', '6', '13']
    # '131415' with 3 payouts -> ['13', '14', '15']

    horses = []
    i = 0
    while i < len(horses_str) and len(horses) < payout_count:
        # 2桁を優先的に試す
        if i + 1 < len(horses_str):
            two_digit = int(horses_str[i:i+2])
            # 2桁が妥当な馬番（1-18）で、残り文字数とペイアウト数が合う
            if two_digit <= 18:
                remaining_chars = len(horses_str) - (i + 2)
                remaining_payouts = payout_count - len(horses) - 1
                if remaining_chars >= remaining_payouts:
                    horses.append(horses_str[i:i+2])
                    i += 2
                    continue
        # 1桁として処理
        horses.append(horses_str[i])
        i += 1

    return horses

def get_fukusho_payout(race_id, umaban, payout_data):
    """複勝払戻金を取得"""
    race_key = str(race_id)
    if race_key not in payout_data:
        return None

    race_payouts = payout_data[race_key]
    if '複勝' not in race_payouts:
        return None

    fukusho_list = race_payouts['複勝']
    for item in fukusho_list:
        horses_str = item['horses']
        payout_str = item['payout']

        # 払戻を分割
        payouts = parse_multiple_payouts(payout_str)
        if not payouts:
            continue

        # 馬番を分割
        horses = parse_horse_numbers(horses_str, len(payouts))

        # 馬番をマッチング
        umaban_str = str(int(umaban))  # '01' -> '1'
        if umaban_str in horses:
            idx = horses.index(umaban_str)
            # 払戻が1つしかない場合は全馬同じ配当
            if len(payouts) == 1:
                return payouts[0]
            # 複数ある場合は対応する配当
            if idx < len(payouts):
                return payouts[idx]

    return None

# 馬番取得
df_test_clean['umaban'] = pd.to_numeric(df_test_clean['馬番'], errors='coerce')

print(f"    マッチング中...")
print()

# ========================================
# 4. 戦略別バックテスト
# ========================================
results = []

# ========================================
# 戦略1: 複勝（予測TOP3）
# ========================================
print("--- 戦略1: 複勝（予測確率TOP3） ---")

race_groups = df_test_clean.groupby('race_id')

total_bet = 0
total_return = 0
races_bet = 0
wins = 0
matched_races = 0

for race_id, race_df in race_groups:
    # 払戻データがあるレースのみ
    if str(race_id) not in payout_data:
        continue

    matched_races += 1

    # 予測TOP3
    top3 = race_df.nlargest(3, 'prob')

    for _, horse in top3.iterrows():
        total_bet += 100

        # 3着以内なら払戻取得
        if horse['rank'] <= 3:
            payout = get_fukusho_payout(race_id, horse['umaban'], payout_data)
            if payout:
                wins += 1
                total_return += payout

    races_bet += 1

if races_bet > 0:
    hit_rate = wins / (races_bet * 3) * 100
    recovery = total_return / total_bet * 100

    print(f"  対象レース: {matched_races:,}レース")
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
# 戦略2: 複勝（予測確率50%以上）
# ========================================
print("--- 戦略2: 複勝（予測確率50%以上） ---")

total_bet = 0
total_return = 0
races_bet = 0
wins = 0

for race_id, race_df in race_groups:
    if str(race_id) not in payout_data:
        continue

    # 予測確率50%以上
    high_prob = race_df[race_df['prob'] >= 0.5]

    for _, horse in high_prob.iterrows():
        total_bet += 100
        races_bet += 1

        if horse['rank'] <= 3:
            payout = get_fukusho_payout(race_id, horse['umaban'], payout_data)
            if payout:
                wins += 1
                total_return += payout

if races_bet > 0:
    hit_rate = wins / races_bet * 100
    recovery = total_return / total_bet * 100

    print(f"  賭け数: {races_bet:,}頭")
    print(f"  的中数: {wins:,}")
    print(f"  的中率: {hit_rate:.2f}%")
    print(f"  総賭け金: {total_bet:,}円")
    print(f"  総払戻: {int(total_return):,}円")
    print(f"  回収率: {recovery:.1f}%")
    print(f"  損益: {int(total_return - total_bet):,}円")
    print()

    results.append({
        '戦略': '複勝（確率50%以上）',
        '回収率': f"{recovery:.1f}%",
        '的中率': f"{hit_rate:.2f}%",
        '損益': int(total_return - total_bet)
    })

# ========================================
# 戦略3: 複勝（予測確率60%以上）
# ========================================
print("--- 戦略3: 複勝（予測確率60%以上・厳選） ---")

total_bet = 0
total_return = 0
races_bet = 0
wins = 0

for race_id, race_df in race_groups:
    if str(race_id) not in payout_data:
        continue

    # 予測確率60%以上
    high_prob = race_df[race_df['prob'] >= 0.6]

    for _, horse in high_prob.iterrows():
        total_bet += 100
        races_bet += 1

        if horse['rank'] <= 3:
            payout = get_fukusho_payout(race_id, horse['umaban'], payout_data)
            if payout:
                wins += 1
                total_return += payout

if races_bet > 0:
    hit_rate = wins / races_bet * 100
    recovery = total_return / total_bet * 100

    print(f"  賭け数: {races_bet:,}頭")
    print(f"  的中数: {wins:,}")
    print(f"  的中率: {hit_rate:.2f}%")
    print(f"  総賭け金: {total_bet:,}円")
    print(f"  総払戻: {int(total_return):,}円")
    print(f"  回収率: {recovery:.1f}%")
    print(f"  損益: {int(total_return - total_bet):,}円")
    print()

    results.append({
        '戦略': '複勝（確率60%以上）',
        '回収率': f"{recovery:.1f}%",
        '的中率': f"{hit_rate:.2f}%",
        '損益': int(total_return - total_bet)
    })

# ========================================
# 5. 結果まとめ
# ========================================
print("="*80)
print("最終結果")
print("="*80)
print()

if len(results) > 0:
    results_df = pd.DataFrame(results)
    results_df['回収率_num'] = results_df['回収率'].str.replace('%', '').astype(float)
    results_df = results_df.sort_values('回収率_num', ascending=False)

    print(results_df[['戦略', '回収率', '的中率', '損益']].to_string(index=False))
    print()

    best = results_df.iloc[0]
    print(f"【最良戦略】: {best['戦略']}")
    print(f"  回収率: {best['回収率']}")
    print(f"  的中率: {best['的中率']}")
    print(f"  損益: {best['損益']:,}円")
    print()

    if best['回収率_num'] >= 100:
        print("[成功] 回収率100%超え！利益が出る可能性あり！")
    else:
        print("[結果] 回収率100%未満")
        print(f"  不足分: {100 - best['回収率_num']:.1f}%")

print()
print("="*80)
