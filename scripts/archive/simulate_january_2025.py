"""
2025年1月実戦シミュレーション
実際のレース結果で予測モデルの精度と収益性をテスト
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print(" 2025年1月 実戦シミュレーション")
print("="*80)
print()

# データ読み込み
print("📊 データ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# 1月のレースIDリストを読み込み
print("1月レースIDリスト読み込み中...")
with open('race_ids_2025_january_by_date.txt', 'r') as f:
    jan_race_ids = set([line.strip() for line in f if line.strip()])

print(f"1月レースID数: {len(jan_race_ids)}")
print()

# 訓練データ: 2020-2024年（2025年以外）
df_train = df[~df['race_id'].astype(str).str.startswith('2025')].copy()

# テストデータ: 2025年1月（レースIDベース）
df_test_all = df[df['race_id'].astype(str).isin(jan_race_ids)].copy()

# HorseNameとRankが入っている行のみ（実際のレース結果データ）
df_test = df_test_all[
    (df_test_all['HorseName'].notna()) &
    (df_test_all['Rank'].notna())
].copy()

print(f"訓練データ: {len(df_train):,}行 ({df_train['race_id'].nunique():,}レース)")
print(f"テストデータ（全行）: {len(df_test_all):,}行")
print(f"テストデータ（レース結果あり）: {len(df_test):,}行 ({df_test['race_id'].nunique():,}レース)")

# Rankを数値に変換してチェック
df_test['Rank'] = pd.to_numeric(df_test['Rank'], errors='coerce')
rank_1_count = (df_test['Rank'] == 1).sum()
print(f"1着の馬: {rank_1_count}頭")
print()

if len(df_test) == 0:
    print("⚠️ 2025年1月のデータが見つかりません")
    exit(1)

# 統計データのカバー率確認
stats_coverage = df_test['total_starts'].notna().sum() / len(df_test) * 100
print(f"統計データカバー率: {stats_coverage:.1f}%")
print()

if stats_coverage < 50:
    print("⚠️ 統計データが不足しています。collect_by_period.pyで1月のデータを収集してください。")
    exit(1)

# 特徴量作成
def create_features(data):
    """特徴量を作成"""
    features = data.copy()

    # 数値特徴量
    numeric_features = [
        'Umaban', 'Odds', 'Ninki', 'Weight', 'WeightDiff',
        'total_starts', 'total_win_rate', 'turf_win_rate', 'dirt_win_rate',
        'total_earnings', 'Age'
    ]

    # カテゴリ特徴量
    categorical_features = ['Sex', 'course_type', 'track_condition', 'father', 'mother_father']

    # 欠損値処理（数値列）
    for col in numeric_features:
        if col in features.columns:
            # 数値に変換（変換できない値はNaNに）
            features[col] = pd.to_numeric(features[col], errors='coerce')
            # 欠損値を中央値で埋める
            median_val = features[col].median()
            if pd.isna(median_val):
                median_val = 0
            features[col] = features[col].fillna(median_val)

    for col in categorical_features:
        if col in features.columns:
            features[col] = features[col].fillna('Unknown')

    return features, numeric_features, categorical_features

print("🔧 特徴量作成中...")
df_train_feat, num_feat, cat_feat = create_features(df_train)
df_test_feat, _, _ = create_features(df_test)

# ラベルエンコーディング
label_encoders = {}
for col in cat_feat:
    if col in df_train_feat.columns:
        le = LabelEncoder()
        df_train_feat[col] = le.fit_transform(df_train_feat[col].astype(str))

        # テストデータも同じエンコーダーで変換
        df_test_feat[col] = df_test_feat[col].astype(str).apply(
            lambda x: le.transform([x])[0] if x in le.classes_ else -1
        )
        label_encoders[col] = le

# 訓練データ準備
feature_cols = num_feat + cat_feat
feature_cols = [col for col in feature_cols if col in df_train_feat.columns]

X_train = df_train_feat[feature_cols]
y_train = (df_train_feat['Rank'] == 1).astype(int)

X_test = df_test_feat[feature_cols]
y_test = (df_test_feat['Rank'] == 1).astype(int)

print(f"特徴量数: {len(feature_cols)}")
print()

# モデル訓練
print("🤖 モデル訓練中...")
models = {
    'RandomForest': RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42),
    'GradientBoosting': GradientBoostingClassifier(n_estimators=100, max_depth=5, random_state=42)
}

predictions = {}
for name, model in models.items():
    print(f"  - {name}...", end=" ")
    model.fit(X_train, y_train)
    pred_proba = model.predict_proba(X_test)[:, 1]
    predictions[name] = pred_proba
    print("✓")

print()
print("="*80)
print(" シミュレーション結果")
print("="*80)
print()

# レースごとに予測
df_test_feat = df_test_feat.reset_index(drop=True)
df_test = df_test.reset_index(drop=True)

df_test_feat['race_id'] = df_test['race_id'].values
df_test_feat['actual_rank'] = pd.to_numeric(df_test['Rank'], errors='coerce')
df_test_feat['horse_name'] = df_test['HorseName'].values
df_test_feat['odds'] = pd.to_numeric(df_test['Odds'], errors='coerce')

for model_name, pred in predictions.items():
    df_test_feat[f'{model_name}_pred'] = pred

# レースごとに最も確率の高い馬を予測
results = []

for race_id in df_test_feat['race_id'].unique():
    race_data = df_test_feat[df_test_feat['race_id'] == race_id].copy()

    for model_name in models.keys():
        # 予測確率が最も高い馬
        top_pred_idx = race_data[f'{model_name}_pred'].idxmax()
        top_pred = race_data.loc[top_pred_idx]

        # 実際の1着馬
        actual_winner = race_data[race_data['actual_rank'] == 1]

        if len(actual_winner) > 0:
            actual_winner = actual_winner.iloc[0]

            results.append({
                'model': model_name,
                'race_id': race_id,
                'predicted_horse': top_pred['horse_name'],
                'predicted_odds': top_pred['odds'],
                'actual_winner': actual_winner['horse_name'],
                'actual_odds': actual_winner['odds'],
                'hit': top_pred['horse_name'] == actual_winner['horse_name']
            })

print(f"結果レコード数: {len(results)}")
print()

if len(results) == 0:
    print("⚠️ 予測結果が生成されませんでした。")
    print("デバッグ情報:")
    print(f"  - テストレース数: {df_test_feat['race_id'].nunique()}")
    print(f"  - actual_rankが1の行数: {(df_test_feat['actual_rank'] == 1).sum()}")
    print(f"  - actual_rankのユニーク値: {df_test_feat['actual_rank'].unique()[:10]}")
    exit(1)

results_df = pd.DataFrame(results)

# モデルごとの成績
print("📊 モデル別成績:")
print()

for model_name in models.keys():
    model_results = results_df[results_df['model'] == model_name]

    total_races = len(model_results)
    hits = model_results['hit'].sum()
    hit_rate = hits / total_races * 100 if total_races > 0 else 0

    # 全レースに100円ずつ賭けた場合の収支
    total_bet = total_races * 100

    # 的中したレースの払戻金
    hit_races = model_results[model_results['hit']]
    returns = (hit_races['predicted_odds'] * 100).sum()

    profit = returns - total_bet
    roi = (returns / total_bet - 1) * 100 if total_bet > 0 else 0

    print(f"【{model_name}】")
    print(f"  総レース数: {total_races}")
    print(f"  的中数: {hits}")
    print(f"  的中率: {hit_rate:.1f}%")
    print(f"  総投資額: {total_bet:,}円")
    print(f"  総払戻額: {returns:,.0f}円")
    print(f"  収支: {profit:+,.0f}円")
    print(f"  回収率: {roi:+.1f}%")
    print()

# 人気順での成績（ベースライン）
print("📊 ベースライン（1番人気を買い続けた場合）:")
print()

baseline_results = []
for race_id in df_test_feat['race_id'].unique():
    race_data = df_test_feat[df_test_feat['race_id'] == race_id].copy()

    # 1番人気（オッズ最小）
    favorite_idx = race_data['odds'].idxmin()
    favorite = race_data.loc[favorite_idx]

    # 実際の1着馬
    actual_winner = race_data[race_data['actual_rank'] == 1]

    if len(actual_winner) > 0:
        actual_winner = actual_winner.iloc[0]

        baseline_results.append({
            'race_id': race_id,
            'predicted_odds': favorite['odds'],
            'hit': favorite['horse_name'] == actual_winner['horse_name']
        })

baseline_df = pd.DataFrame(baseline_results)

total_races = len(baseline_df)
hits = baseline_df['hit'].sum()
hit_rate = hits / total_races * 100 if total_races > 0 else 0

total_bet = total_races * 100
hit_races = baseline_df[baseline_df['hit']]
returns = (hit_races['predicted_odds'] * 100).sum()
profit = returns - total_bet
roi = (returns / total_bet - 1) * 100 if total_bet > 0 else 0

print(f"  総レース数: {total_races}")
print(f"  的中数: {hits}")
print(f"  的中率: {hit_rate:.1f}%")
print(f"  総投資額: {total_bet:,}円")
print(f"  総払戻額: {returns:,.0f}円")
print(f"  収支: {profit:+,.0f}円")
print(f"  回収率: {roi:+.1f}%")
print()

print("="*80)
print()

# 的中レース詳細（RandomForestの場合）
print("🏆 的中レース詳細（RandomForest）:")
print()

rf_results = results_df[results_df['model'] == 'RandomForest']
rf_hits = rf_results[rf_results['hit']]

if len(rf_hits) > 0:
    print(f"的中レース数: {len(rf_hits)}件")
    print()

    for idx, row in rf_hits.head(10).iterrows():
        print(f"  レース{row['race_id']}: {row['predicted_horse']} ({row['predicted_odds']:.1f}倍) ✓")

    if len(rf_hits) > 10:
        print(f"  ... 他{len(rf_hits) - 10}件")
else:
    print("  的中レースなし")

print()
print("="*80)
print(" シミュレーション完了")
print("="*80)
