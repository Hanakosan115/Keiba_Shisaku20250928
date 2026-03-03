# -*- coding: utf-8 -*-
"""
Phase 13 Step 3: モデル訓練（リーケージ排除版）

複数アルゴリズムを比較し、最良のモデルを選択する。
- LightGBM
- XGBoost
- CatBoost
- ロジスティック回帰（ベースライン）
"""
import pandas as pd
import numpy as np
import pickle
import lightgbm as lgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score, log_loss
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("Warning: XGBoost not available")

try:
    import catboost as cb
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False
    print("Warning: CatBoost not available")

print("=" * 80)
print("  Phase 13 Step 3: モデル訓練（複数アルゴリズム比較）")
print("=" * 80)
print()

# ===================================================================
# データ読み込み
# ===================================================================

print("[1/6] 特徴量データ読み込み中...")
train_df = pd.read_csv('phase13_train_features.csv')
val_df = pd.read_csv('phase13_val_features.csv')
test_df = pd.read_csv('phase13_test_features.csv')

print(f"  訓練: {len(train_df):,}レース")
print(f"  検証: {len(val_df):,}レース")
print(f"  テスト: {len(test_df):,}レース")
print()

# ===================================================================
# 特徴量とラベルの分離
# ===================================================================

print("[2/6] 特徴量とラベルの準備...")

# メタカラムを除外
meta_cols = ['race_id', 'horse_id', 'rank', 'date']
feature_cols = [c for c in train_df.columns if c not in meta_cols]

print(f"  特徴量数: {len(feature_cols)}")
print()

# 特徴量
X_train = train_df[feature_cols].fillna(0)
X_val = val_df[feature_cols].fillna(0)
X_test = test_df[feature_cols].fillna(0)

# ラベル: 勝利（1着）と複勝（3着以内）
y_train_win = (train_df['rank'] == 1).astype(int)
y_train_top3 = (train_df['rank'] <= 3).astype(int)

y_val_win = (val_df['rank'] == 1).astype(int)
y_val_top3 = (val_df['rank'] <= 3).astype(int)

y_test_win = (test_df['rank'] == 1).astype(int)
y_test_top3 = (test_df['rank'] <= 3).astype(int)

print(f"訓練データのクラス分布:")
print(f"  勝利: {y_train_win.sum():,} / {len(y_train_win):,} ({y_train_win.mean()*100:.2f}%)")
print(f"  複勝: {y_train_top3.sum():,} / {len(y_train_top3):,} ({y_train_top3.mean()*100:.2f}%)")
print()

# ===================================================================
# モデル訓練関数
# ===================================================================

def train_and_evaluate(model_name, model_win, model_top3, X_train, y_train_win, y_train_top3, X_val, y_val_win, y_val_top3):
    """
    モデルを訓練して評価する

    Returns:
        dict: 評価結果
    """
    print(f"  [{model_name}] 訓練中...")

    # 勝利モデル
    model_win.fit(X_train, y_train_win)
    pred_val_win = model_win.predict_proba(X_val)[:, 1]

    # 複勝モデル
    model_top3.fit(X_train, y_train_top3)
    pred_val_top3 = model_top3.predict_proba(X_val)[:, 1]

    # 評価
    auc_win = roc_auc_score(y_val_win, pred_val_win)
    auc_top3 = roc_auc_score(y_val_top3, pred_val_top3)
    logloss_win = log_loss(y_val_win, pred_val_win)
    logloss_top3 = log_loss(y_val_top3, pred_val_top3)

    # レース単位の本命的中率（勝率予測最高の馬を選択）
    val_df_temp = val_df.copy()
    val_df_temp['pred_win'] = pred_val_win

    best_horses = val_df_temp.groupby('race_id')['pred_win'].idxmax()
    honmei_correct = 0
    total_races = 0

    for race_id in val_df_temp['race_id'].unique():
        race_data = val_df_temp[val_df_temp['race_id'] == race_id]
        if len(race_data) == 0:
            continue
        best_idx = race_data['pred_win'].idxmax()
        best_horse = race_data.loc[best_idx]
        if best_horse['rank'] == 1:
            honmei_correct += 1
        total_races += 1

    honmei_rate = honmei_correct / total_races if total_races > 0 else 0

    results = {
        'model_name': model_name,
        'auc_win': auc_win,
        'auc_top3': auc_top3,
        'logloss_win': logloss_win,
        'logloss_top3': logloss_top3,
        'honmei_rate': honmei_rate,
        'honmei_correct': honmei_correct,
        'total_races': total_races
    }

    print(f"  [{model_name}] 完了")
    print(f"    勝利AUC: {auc_win:.4f}, 複勝AUC: {auc_top3:.4f}")
    print(f"    本命的中率: {honmei_rate*100:.2f}% ({honmei_correct}/{total_races})")
    print()

    return results, model_win, model_top3

# ===================================================================
# モデル訓練
# ===================================================================

print("[3/6] モデル訓練...")
print()

all_results = []

# 1. LightGBM
print("【1/4】 LightGBM")
lgb_win = lgb.LGBMClassifier(
    n_estimators=200,
    max_depth=8,
    learning_rate=0.05,
    num_leaves=64,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    verbose=-1
)
lgb_top3 = lgb.LGBMClassifier(
    n_estimators=200,
    max_depth=8,
    learning_rate=0.05,
    num_leaves=64,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42,
    verbose=-1
)
lgb_results, lgb_win_trained, lgb_top3_trained = train_and_evaluate(
    'LightGBM', lgb_win, lgb_top3, X_train, y_train_win, y_train_top3, X_val, y_val_win, y_val_top3
)
all_results.append(lgb_results)

# 2. XGBoost
if XGBOOST_AVAILABLE:
    print("【2/4】 XGBoost")
    xgb_win = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss'
    )
    xgb_top3 = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=8,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric='logloss'
    )
    xgb_results, xgb_win_trained, xgb_top3_trained = train_and_evaluate(
        'XGBoost', xgb_win, xgb_top3, X_train, y_train_win, y_train_top3, X_val, y_val_win, y_val_top3
    )
    all_results.append(xgb_results)

# 3. CatBoost
if CATBOOST_AVAILABLE:
    print("【3/4】 CatBoost")
    cat_win = cb.CatBoostClassifier(
        iterations=200,
        depth=8,
        learning_rate=0.05,
        random_state=42,
        verbose=False
    )
    cat_top3 = cb.CatBoostClassifier(
        iterations=200,
        depth=8,
        learning_rate=0.05,
        random_state=42,
        verbose=False
    )
    cat_results, cat_win_trained, cat_top3_trained = train_and_evaluate(
        'CatBoost', cat_win, cat_top3, X_train, y_train_win, y_train_top3, X_val, y_val_win, y_val_top3
    )
    all_results.append(cat_results)

# 4. ロジスティック回帰（ベースライン）
print("【4/4】 ロジスティック回帰")
lr_win = LogisticRegression(max_iter=1000, random_state=42)
lr_top3 = LogisticRegression(max_iter=1000, random_state=42)
lr_results, lr_win_trained, lr_top3_trained = train_and_evaluate(
    'LogisticRegression', lr_win, lr_top3, X_train, y_train_win, y_train_top3, X_val, y_val_win, y_val_top3
)
all_results.append(lr_results)

# ===================================================================
# 結果比較
# ===================================================================

print("[4/6] モデル比較...")
print()
results_df = pd.DataFrame(all_results)
results_df = results_df.sort_values('honmei_rate', ascending=False)

print("【検証データでの性能】")
print("-" * 80)
print(results_df[['model_name', 'auc_win', 'auc_top3', 'honmei_rate']].to_string(index=False))
print("-" * 80)
print()

# 最良モデル選択
best_model_name = results_df.iloc[0]['model_name']
print(f"最良モデル: {best_model_name}")
print()

# 最良モデルの取得
if best_model_name == 'LightGBM':
    best_win = lgb_win_trained
    best_top3 = lgb_top3_trained
elif best_model_name == 'XGBoost' and XGBOOST_AVAILABLE:
    best_win = xgb_win_trained
    best_top3 = xgb_top3_trained
elif best_model_name == 'CatBoost' and CATBOOST_AVAILABLE:
    best_win = cat_win_trained
    best_top3 = cat_top3_trained
else:
    best_win = lr_win_trained
    best_top3 = lr_top3_trained

# ===================================================================
# テストデータで最終評価
# ===================================================================

print("[5/6] テストデータで最終評価...")
pred_test_win = best_win.predict_proba(X_test)[:, 1]
pred_test_top3 = best_top3.predict_proba(X_test)[:, 1]

test_auc_win = roc_auc_score(y_test_win, pred_test_win)
test_auc_top3 = roc_auc_score(y_test_top3, pred_test_top3)

# レース単位の本命的中率
test_df_temp = test_df.copy()
test_df_temp['pred_win'] = pred_test_win

honmei_correct_test = 0
total_races_test = 0

for race_id in test_df_temp['race_id'].unique():
    race_data = test_df_temp[test_df_temp['race_id'] == race_id]
    if len(race_data) == 0:
        continue
    best_idx = race_data['pred_win'].idxmax()
    best_horse = race_data.loc[best_idx]
    if best_horse['rank'] == 1:
        honmei_correct_test += 1
    total_races_test += 1

honmei_rate_test = honmei_correct_test / total_races_test if total_races_test > 0 else 0

print(f"  勝利AUC: {test_auc_win:.4f}")
print(f"  複勝AUC: {test_auc_top3:.4f}")
print(f"  本命的中率: {honmei_rate_test*100:.2f}% ({honmei_correct_test}/{total_races_test})")
print()

# ===================================================================
# モデル保存
# ===================================================================

print("[6/6] モデル保存...")
with open('phase13_model_win.pkl', 'wb') as f:
    pickle.dump(best_win, f)
with open('phase13_model_top3.pkl', 'wb') as f:
    pickle.dump(best_top3, f)

# 特徴量リスト保存
with open('phase13_feature_list.pkl', 'wb') as f:
    pickle.dump(feature_cols, f)

# メタデータ
metadata = {
    'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'best_model': best_model_name,
    'feature_count': len(feature_cols),
    'train_size': len(train_df),
    'val_size': len(val_df),
    'test_size': len(test_df),
    'val_honmei_rate': results_df.iloc[0]['honmei_rate'],
    'test_honmei_rate': honmei_rate_test,
    'test_auc_win': test_auc_win,
    'test_auc_top3': test_auc_top3,
    'leakage_free': True,
}

with open('phase13_model_metadata.pkl', 'wb') as f:
    pickle.dump(metadata, f)

print(f"  保存完了")
print()

print("=" * 80)
print("  モデル訓練完了")
print("=" * 80)
print()
print("【結果サマリー】")
print(f"  最良モデル: {best_model_name}")
print(f"  検証データ本命的中率: {results_df.iloc[0]['honmei_rate']*100:.2f}%")
print(f"  テストデータ本命的中率: {honmei_rate_test*100:.2f}%")
print()
print("【次のステップ】")
print("  Step 4: Calibration（確率較正）")
print("  Step 5: Walk-Forward Validation")
print("  Step 6: 2026年2月検証")
print()
