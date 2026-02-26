"""
予測モデル ベースライン
シンプルで堅実なベースラインモデルを構築
"""
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print(" 予測モデル ベースライン構築")
print("="*80)
print()

# ========================================
# 1. データ読み込みと前処理
# ========================================
print("[1] データ読み込み...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

# race_idから年を抽出（dateカラムが不完全なため）
df['year'] = df['race_id'].astype(str).str[:4]

print(f"    Total rows: {len(df):,}")
print(f"    Total races: {df['race_id'].nunique():,}")
print()

# 2024をトレーニング、2025をテスト
df_train = df[df['year'] == '2024'].copy()
df_test = df[df['year'] == '2025'].copy()

print(f"    Training: {len(df_train):,} rows ({df_train['race_id'].nunique():,} races)")
print(f"    Test: {len(df_test):,} rows ({df_test['race_id'].nunique():,} races)")
print()

# ========================================
# 2. ターゲット作成
# ========================================
print("[2] ターゲット作成...")
df_train['rank'] = pd.to_numeric(df_train['着順'], errors='coerce')
df_test['rank'] = pd.to_numeric(df_test['着順'], errors='coerce')

# 1着を1、それ以外を0とする二値分類
df_train['target'] = (df_train['rank'] == 1).astype(int)
df_test['target'] = (df_test['rank'] == 1).astype(int)

print(f"    Training wins: {df_train['target'].sum():,} ({df_train['target'].mean()*100:.2f}%)")
print(f"    Test wins: {df_test['target'].sum():,} ({df_test['target'].mean()*100:.2f}%)")
print()

# ========================================
# 3. 特徴量選択
# ========================================
print("[3] 特徴量選択...")

# 使用する特徴量リスト
feature_candidates = [
    # 基本情報
    '人気', '単勝', '馬体重',

    # レース情報
    'distance',

    # 馬の統計
    'total_starts', 'total_win_rate', 'total_earnings',
    'turf_win_rate', 'dirt_win_rate',
    'distance_similar_win_rate',
    'grade_race_starts',

    # 前走情報
    'prev_race_rank', 'prev_race_distance', 'days_since_last_race',

    # 走法・位置取り
    'avg_passage_position', 'avg_last_3f',

    # 血統
    'heavy_track_win_rate',
]

# 実際に存在する特徴量のみ使用
available_features = [f for f in feature_candidates if f in df_train.columns]
print(f"    Available features: {len(available_features)}/{len(feature_candidates)}")
print()

# ========================================
# 4. 特徴量エンジニアリング
# ========================================
print("[4] 特徴量エンジニアリング...")

def engineer_features(df, features):
    """特徴量エンジニアリング"""
    X = df[features].copy()

    # 数値変換
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors='coerce')

    # 欠損値補完
    for col in X.columns:
        median_val = X[col].median()
        if pd.isna(median_val):
            median_val = 0
        X[col] = X[col].fillna(median_val)

    return X

X_train = engineer_features(df_train, available_features)
X_test = engineer_features(df_test, available_features)
y_train = df_train['target']
y_test = df_test['target']

print(f"    Training shape: {X_train.shape}")
print(f"    Test shape: {X_test.shape}")
print(f"    Features: {X_train.columns.tolist()}")
print()

# ========================================
# 5. モデル学習
# ========================================
print("="*80)
print("[5] モデル学習 & 評価")
print("="*80)
print()

results = []

# ===== モデル1: Logistic Regression =====
print("--- Logistic Regression ---")
lr = LogisticRegression(max_iter=1000, random_state=42)
lr.fit(X_train, y_train)

y_pred_lr = lr.predict(X_test)
y_proba_lr = lr.predict_proba(X_test)[:, 1]

acc_lr = accuracy_score(y_test, y_pred_lr)
prec_lr = precision_score(y_test, y_pred_lr, zero_division=0)
rec_lr = recall_score(y_test, y_pred_lr, zero_division=0)
f1_lr = f1_score(y_test, y_pred_lr, zero_division=0)
auc_lr = roc_auc_score(y_test, y_proba_lr)

print(f"  Accuracy: {acc_lr:.4f}")
print(f"  Precision: {prec_lr:.4f}")
print(f"  Recall: {rec_lr:.4f}")
print(f"  F1-score: {f1_lr:.4f}")
print(f"  ROC-AUC: {auc_lr:.4f}")
print()

results.append({
    'Model': 'Logistic Regression',
    'Accuracy': acc_lr,
    'Precision': prec_lr,
    'Recall': rec_lr,
    'F1-score': f1_lr,
    'ROC-AUC': auc_lr
})

# ===== モデル2: Random Forest =====
print("--- Random Forest ---")
rf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
rf.fit(X_train, y_train)

y_pred_rf = rf.predict(X_test)
y_proba_rf = rf.predict_proba(X_test)[:, 1]

acc_rf = accuracy_score(y_test, y_pred_rf)
prec_rf = precision_score(y_test, y_pred_rf, zero_division=0)
rec_rf = recall_score(y_test, y_pred_rf, zero_division=0)
f1_rf = f1_score(y_test, y_pred_rf, zero_division=0)
auc_rf = roc_auc_score(y_test, y_proba_rf)

print(f"  Accuracy: {acc_rf:.4f}")
print(f"  Precision: {prec_rf:.4f}")
print(f"  Recall: {rec_rf:.4f}")
print(f"  F1-score: {f1_rf:.4f}")
print(f"  ROC-AUC: {auc_rf:.4f}")
print()

results.append({
    'Model': 'Random Forest',
    'Accuracy': acc_rf,
    'Precision': prec_rf,
    'Recall': rec_rf,
    'F1-score': f1_rf,
    'ROC-AUC': auc_rf
})

# ===== モデル3: LightGBM =====
print("--- LightGBM ---")
lgb_train = lgb.Dataset(X_train, y_train)
lgb_test = lgb.Dataset(X_test, y_test, reference=lgb_train)

params = {
    'objective': 'binary',
    'metric': 'auc',
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'verbose': -1
}

gbm = lgb.train(
    params,
    lgb_train,
    num_boost_round=200,
    valid_sets=[lgb_test],
    callbacks=[lgb.early_stopping(stopping_rounds=20)]
)

y_proba_lgb = gbm.predict(X_test, num_iteration=gbm.best_iteration)
y_pred_lgb = (y_proba_lgb > 0.5).astype(int)

acc_lgb = accuracy_score(y_test, y_pred_lgb)
prec_lgb = precision_score(y_test, y_pred_lgb, zero_division=0)
rec_lgb = recall_score(y_test, y_pred_lgb, zero_division=0)
f1_lgb = f1_score(y_test, y_pred_lgb, zero_division=0)
auc_lgb = roc_auc_score(y_test, y_proba_lgb)

print(f"  Accuracy: {acc_lgb:.4f}")
print(f"  Precision: {prec_lgb:.4f}")
print(f"  Recall: {rec_lgb:.4f}")
print(f"  F1-score: {f1_lgb:.4f}")
print(f"  ROC-AUC: {auc_lgb:.4f}")
print()

results.append({
    'Model': 'LightGBM',
    'Accuracy': acc_lgb,
    'Precision': prec_lgb,
    'Recall': rec_lgb,
    'F1-score': f1_lgb,
    'ROC-AUC': auc_lgb
})

# ========================================
# 6. 結果比較
# ========================================
print("="*80)
print("[6] モデル比較")
print("="*80)
print()

results_df = pd.DataFrame(results)
print(results_df.to_string(index=False))
print()

best_model = results_df.loc[results_df['ROC-AUC'].idxmax(), 'Model']
best_auc = results_df['ROC-AUC'].max()
print(f"Best model: {best_model} (ROC-AUC: {best_auc:.4f})")
print()

# ========================================
# 7. 特徴量重要度（LightGBM）
# ========================================
print("="*80)
print("[7] 特徴量重要度 (LightGBM)")
print("="*80)
print()

importance_df = pd.DataFrame({
    'feature': X_train.columns,
    'importance': gbm.feature_importance()
})
importance_df = importance_df.sort_values('importance', ascending=False)

print("TOP 15 features:")
for idx, row in importance_df.head(15).iterrows():
    print(f"  {row['feature']:30s}: {row['importance']:6.0f}")
print()

# ========================================
# 8. 実戦シミュレーション
# ========================================
print("="*80)
print("[8] 実戦シミュレーション")
print("="*80)
print()

# LightGBMで予測確率を追加
df_test['pred_proba'] = y_proba_lgb

# レースごとに最高確率の馬を予測
race_predictions = []
for race_id in df_test['race_id'].unique():
    race_df = df_test[df_test['race_id'] == race_id].copy()

    if len(race_df) == 0:
        continue

    # 予測確率が最高の馬
    best_horse_idx = race_df['pred_proba'].idxmax()
    best_horse = race_df.loc[best_horse_idx]

    # 実際の1着馬
    actual_winner = race_df[race_df['target'] == 1]

    race_predictions.append({
        'race_id': race_id,
        'predicted_horse': best_horse.get('馬名', 'Unknown'),
        'predicted_rank': best_horse.get('rank', np.nan),
        'predicted_odds': best_horse.get('単勝', np.nan),
        'actual_winner': actual_winner['馬名'].iloc[0] if len(actual_winner) > 0 else 'Unknown',
        'correct': len(actual_winner) > 0 and best_horse.name in actual_winner.index
    })

pred_df = pd.DataFrame(race_predictions)
accuracy = pred_df['correct'].mean() * 100

print(f"Total races: {len(pred_df):,}")
print(f"Correct predictions: {pred_df['correct'].sum():,}")
print(f"Accuracy: {accuracy:.2f}%")
print()

# オッズ分布
pred_df['predicted_odds_num'] = pd.to_numeric(pred_df['predicted_odds'], errors='coerce')
avg_odds = pred_df['predicted_odds_num'].mean()
median_odds = pred_df['predicted_odds_num'].median()

print(f"Average predicted odds: {avg_odds:.2f}倍")
print(f"Median predicted odds: {median_odds:.2f}倍")
print()

# サンプル表示
print("Sample predictions:")
print(pred_df.head(10).to_string(index=False))
print()

# ========================================
# 9. 投資シミュレーション
# ========================================
print("="*80)
print("[9] 投資シミュレーション")
print("="*80)
print()

# 毎レース1000円ベット
bet_amount = 1000
total_bets = len(pred_df) * bet_amount
total_returns = 0

for idx, row in pred_df.iterrows():
    if row['correct']:
        odds = pd.to_numeric(row['predicted_odds'], errors='coerce')
        if not pd.isna(odds):
            total_returns += bet_amount * odds

profit = total_returns - total_bets
roi = (total_returns / total_bets - 1) * 100

print(f"Total bets: {total_bets:,}円 ({len(pred_df):,}レース x {bet_amount}円)")
print(f"Total returns: {total_returns:,.0f}円")
print(f"Profit/Loss: {profit:,.0f}円")
print(f"ROI: {roi:.2f}%")
print()

# ========================================
# 完了
# ========================================
print("="*80)
print(" ベースラインモデル構築完了")
print("="*80)
print()
print("Summary:")
print(f"  - Best model: {best_model}")
print(f"  - ROC-AUC: {best_auc:.4f}")
print(f"  - Race accuracy: {accuracy:.2f}%")
print(f"  - Investment ROI: {roi:.2f}%")
print()
print("Next steps:")
print("  1. データ品質レポートで特徴量を確認")
print("  2. EDAで有効な特徴量を探索")
print("  3. ハイパーパラメータチューニング")
print("  4. アンサンブルモデル構築")
