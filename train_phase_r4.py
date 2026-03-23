"""
Phase R4 モデル訓練
60特徴量（R2-Optuna）+ 7個のレース内相対特徴量 = 67特徴量

追加特徴量:
  field_win_rate_rank   : total_win_rate のレース内正規化ランク
  field_jockey_rank     : jockey_win_rate のレース内正規化ランク
  field_trainer_rank    : trainer_win_rate のレース内正規化ランク
  field_earnings_rank   : total_earnings のレース内正規化ランク
  field_last3f_rank     : avg_last_3f のレース内正規化ランク（低いほど良い）
  field_diff_rank       : avg_diff_seconds のレース内正規化ランク（低いほど良い）
  field_size            : レース出走頭数

使い方:
  py train_phase_r4.py                    # 80トライアル Optuna（デフォルト）
  py train_phase_r4.py --trials 40        # 試行回数を減らす
  py train_phase_r4.py --no-optuna        # 最初からR2-Optunaパラメータで訓練（高速）
"""
import os
import sys
import json
import shutil
import pickle
import argparse
import warnings
import numpy as np
import pandas as pd
import lightgbm as lgb
import optuna
from sklearn.metrics import roc_auc_score, log_loss
from sklearn.model_selection import StratifiedKFold

warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ===================================================================
# 引数
# ===================================================================
parser = argparse.ArgumentParser()
parser.add_argument('--trials',    type=int,  default=80)
parser.add_argument('--no-optuna', action='store_true', help='Optunaスキップ、R2-Optunaパラメータを流用')
args = parser.parse_args()

print("=" * 80)
print("  Phase R4 モデル訓練（60 + 7 = 67特徴量）")
print("=" * 80)

# ===================================================================
# 特徴量リスト
# ===================================================================
with open('models/phase_r2_optuna/feature_list.pkl', 'rb') as f:
    BASE_FEATURES = pickle.load(f)   # R2-Optunaの60特徴量（固定）

R4_FEATURES = [
    'field_win_rate_rank',
    'field_jockey_rank',
    'field_trainer_rank',
    'field_earnings_rank',
    'field_last3f_rank',
    'field_diff_rank',
    'field_size',
]

FEATURE_LIST = BASE_FEATURES + R4_FEATURES
print(f"特徴量数: {len(BASE_FEATURES)}(R2) + {len(R4_FEATURES)}(R4) = {len(FEATURE_LIST)}")

# ===================================================================
# データ読み込み
# ===================================================================
print("\nデータ読み込み中...")
df_train = pd.read_csv('data/phase_r4/train_features.csv', low_memory=False)
df_val   = pd.read_csv('data/phase_r4/val_features.csv',   low_memory=False)
df_test  = pd.read_csv('data/phase_r4/test_features.csv',  low_memory=False)

# 存在する特徴量のみ使用
FEATURE_LIST = [f for f in FEATURE_LIST if f in df_train.columns and f in df_val.columns]
print(f"存在確認後の特徴量数: {len(FEATURE_LIST)}")

X_train       = df_train[FEATURE_LIST].fillna(0).values
y_train_win   = df_train['target_win'].values
y_train_place = df_train['target_place'].values

X_val         = df_val[FEATURE_LIST].fillna(0).values
y_val_win     = df_val['target_win'].values
y_val_place   = df_val['target_place'].values

print(f"訓練: {X_train.shape}, 検証: {X_val.shape}, テスト: {df_test.shape}")

# ===================================================================
# Optuna 目的関数
# ===================================================================
kfold = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

def objective(trial):
    params = {
        'objective':         'binary',
        'metric':            'binary_logloss',
        'boosting_type':     'gbdt',
        'verbose':           -1,
        'random_state':      42,
        'learning_rate':     trial.suggest_float('learning_rate', 0.005, 0.08, log=True),
        'num_leaves':        trial.suggest_int('num_leaves', 15, 127),
        'min_child_samples': trial.suggest_int('min_child_samples', 10, 150),
        'feature_fraction':  trial.suggest_float('feature_fraction', 0.5, 1.0),
        'bagging_fraction':  trial.suggest_float('bagging_fraction', 0.5, 1.0),
        'bagging_freq':      5,
        'lambda_l1':         trial.suggest_float('lambda_l1', 0.0, 10.0),
        'lambda_l2':         trial.suggest_float('lambda_l2', 0.0, 10.0),
        'min_gain_to_split': trial.suggest_float('min_gain_to_split', 0.0, 5.0),
    }

    cv_aucs = []
    for train_idx, val_idx in kfold.split(X_train, y_train_win):
        X_tr, X_vl = X_train[train_idx], X_train[val_idx]
        y_tr, y_vl = y_train_win[train_idx], y_train_win[val_idx]

        train_ds = lgb.Dataset(X_tr, label=y_tr)
        val_ds   = lgb.Dataset(X_vl, label=y_vl, reference=train_ds)
        model = lgb.train(
            params, train_ds, num_boost_round=3000,
            valid_sets=[val_ds], valid_names=['valid'],
            callbacks=[
                lgb.early_stopping(stopping_rounds=80, verbose=False),
                lgb.log_evaluation(period=0),
            ]
        )
        cv_aucs.append(roc_auc_score(y_vl, model.predict(X_vl, num_iteration=model.best_iteration)))

    trial.set_user_attr('best_iter', model.best_iteration)
    trial.set_user_attr('cv_std',    float(np.std(cv_aucs)))
    return float(np.mean(cv_aucs))


def print_callback(study, trial):
    if trial.number % 10 == 0 or trial.value == study.best_value:
        best = study.best_trial
        print(f"  Trial {trial.number:3d}: AUC={trial.value:.4f} | "
              f"best={best.value:.4f}(#{best.number}) | "
              f"lr={trial.params.get('learning_rate', 0):.4f} "
              f"leaves={trial.params.get('num_leaves', 0)} "
              f"iter={trial.user_attrs.get('best_iter', '?')}")

# ===================================================================
# ハイパーパラメータ決定
# ===================================================================
if args.no_optuna:
    # R2-Optuna のベストパラメータを流用
    best_params = {
        'objective':         'binary',
        'metric':            'binary_logloss',
        'boosting_type':     'gbdt',
        'verbose':           -1,
        'random_state':      42,
        'bagging_freq':      5,
        'learning_rate':     0.0086,
        'num_leaves':        43,
        'min_child_samples': 135,
        'feature_fraction':  0.861,
        'bagging_fraction':  0.935,
        'lambda_l1':         8.2,
        'lambda_l2':         5.8,
        'min_gain_to_split': 0.0018,
    }
    best_cv_auc   = None
    best_trial_no = -1
    study         = None
    print("\nOptuna スキップ（R2-Optuna パラメータを流用）")
else:
    print(f"\nOptuna 最適化開始（{args.trials}トライアル・5-Fold CV）")
    study = optuna.create_study(
        direction='maximize',
        sampler=optuna.samplers.TPESampler(seed=42),
        pruner=optuna.pruners.MedianPruner(n_startup_trials=10, n_warmup_steps=5),
    )
    study.optimize(objective, n_trials=args.trials, callbacks=[print_callback],
                   show_progress_bar=False)

    best       = study.best_trial
    best_cv_auc   = best.value
    best_trial_no = best.number
    best_params = {
        'objective':         'binary',
        'metric':            'binary_logloss',
        'boosting_type':     'gbdt',
        'verbose':           -1,
        'random_state':      42,
        'bagging_freq':      5,
        **best.params,
    }
    print(f"\n【最適化結果】Best CV AUC: {best_cv_auc:.4f} (Trial #{best_trial_no})")
    for k, v in best.params.items():
        print(f"  {k}: {v}")

# ===================================================================
# 最終モデル訓練（単勝）
# ===================================================================
print("\n単勝モデル訓練中...")
train_ds = lgb.Dataset(X_train, label=y_train_win)
val_ds   = lgb.Dataset(X_val,   label=y_val_win, reference=train_ds)

model_win = lgb.train(
    best_params, train_ds, num_boost_round=3000,
    valid_sets=[val_ds], valid_names=['valid'],
    callbacks=[
        lgb.early_stopping(stopping_rounds=100, verbose=False),
        lgb.log_evaluation(period=100),
    ]
)

val_auc_win = roc_auc_score(y_val_win, model_win.predict(X_val, num_iteration=model_win.best_iteration))
val_ll_win  = log_loss(y_val_win, model_win.predict(X_val, num_iteration=model_win.best_iteration))
print(f"  Win Val AUC: {val_auc_win:.4f}  LogLoss: {val_ll_win:.4f}  BestIter: {model_win.best_iteration}")

# ===================================================================
# 最終モデル訓練（複勝）
# ===================================================================
print("\n複勝モデル訓練中...")
train_place_ds = lgb.Dataset(X_train, label=y_train_place)
val_place_ds   = lgb.Dataset(X_val,   label=y_val_place, reference=train_place_ds)

model_place = lgb.train(
    best_params, train_place_ds, num_boost_round=3000,
    valid_sets=[val_place_ds], valid_names=['valid'],
    callbacks=[
        lgb.early_stopping(stopping_rounds=100, verbose=False),
        lgb.log_evaluation(period=100),
    ]
)

val_auc_place = roc_auc_score(y_val_place, model_place.predict(X_val, num_iteration=model_place.best_iteration))
print(f"  Place Val AUC: {val_auc_place:.4f}  BestIter: {model_place.best_iteration}")

# ===================================================================
# 特徴量重要度（上位20）
# ===================================================================
print("\n【特徴量重要度 Top 20】")
importance = pd.DataFrame({
    'feature':    FEATURE_LIST,
    'importance': model_win.feature_importance(importance_type='gain'),
}).sort_values('importance', ascending=False)

for _, row in importance.head(20).iterrows():
    tag = ' ★R4新規' if row['feature'] in R4_FEATURES else ''
    print(f"  {row['feature']:<35s} {row['importance']:>8.0f}{tag}")

# ===================================================================
# モデル保存（models/phase_r4/ のみ。アクティブモデルは更新しない）
# ===================================================================
print("\nモデル保存中...")
r4_dir = 'models/phase_r4'
os.makedirs(r4_dir, exist_ok=True)

model_win.save_model(  f'{r4_dir}/model_win.txt')
model_place.save_model(f'{r4_dir}/model_place.txt')
with open(f'{r4_dir}/feature_list.pkl', 'wb') as f:
    pickle.dump(FEATURE_LIST, f)

metadata = {
    'phase':        'R4',
    'num_features': len(FEATURE_LIST),
    'base_features':  BASE_FEATURES,
    'r4_features':    R4_FEATURES,
    'optuna_trials':  args.trials if not args.no_optuna else 0,
    'best_trial':     best_trial_no,
    'best_cv_auc':    best_cv_auc,
    'best_params':    best_params,
    'win_model': {
        'val_auc':       float(val_auc_win),
        'val_logloss':   float(val_ll_win),
        'best_iteration': model_win.best_iteration,
    },
    'place_model': {
        'val_auc':       float(val_auc_place),
        'best_iteration': model_place.best_iteration,
    },
}
with open(f'{r4_dir}/metadata.json', 'w', encoding='utf-8') as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

print(f"  保存先: {r4_dir}/")
print(f"    model_win.txt / model_place.txt / feature_list.pkl / metadata.json")

if study:
    with open(f'{r4_dir}/optuna_study.pkl', 'wb') as f:
        pickle.dump(study, f)
    print(f"    optuna_study.pkl")

# ===================================================================
# R2-Optuna との比較表示
# ===================================================================
print()
print("=" * 80)
print("  Phase R4 訓練完了")
print("=" * 80)
print()

try:
    with open('phase14_model_metadata.json', encoding='utf-8') as f:
        r2_meta = json.load(f)
    r2_auc = r2_meta.get('win_model', {}).get('val_auc', 0)
    r2_cv  = r2_meta.get('best_cv_auc', 0)
    print(f"【R2-Optuna vs R4 比較】")
    print(f"  指標              R2-Optuna    R4")
    print(f"  CV AUC         :  {r2_cv:.4f}     {best_cv_auc or '(スキップ)':>8}")
    print(f"  Val AUC(win)   :  {r2_auc:.4f}     {val_auc_win:.4f}  {'★改善' if val_auc_win > r2_auc else '▼低下'}")
    print(f"  特徴量数        :  {r2_meta.get('num_features', 60):>5}         {len(FEATURE_LIST):>5}")
except Exception:
    pass

print()
print("【次のステップ】")
print("  1. バックテストで ROI を比較:")
print()
print("     # R4 モデルをアクティブにしてバックテスト実行")
print("     copy models\\phase_r4\\model_win.txt     phase14_model_win.txt")
print("     copy models\\phase_r4\\model_place.txt   phase14_model_place.txt")
print("     copy models\\phase_r4\\feature_list.pkl  phase14_feature_list.pkl")
print("     py run_gui_backtest.py --year 2024")
print("     py run_gui_backtest.py --year 2025")
print()
print("  2. R2-Optuna の方が良ければ元に戻す:")
print("     copy models\\phase_r2_optuna\\model_win.txt     phase14_model_win.txt")
print("     copy models\\phase_r2_optuna\\model_place.txt   phase14_model_place.txt")
print("     copy models\\phase_r2_optuna\\feature_list.pkl  phase14_feature_list.pkl")
print()
print("  ※ GUIでR4モデルを使うには keiba_prediction_gui_v3.py への")
print("    add_relative_features() 統合が必要（別途対応）")
print()
