"""
Phase R6 モデル訓練
74特徴量（R5）+ 6個のトラック日次バイアス・天候・末脚特徴量 = 80特徴量

追加特徴量:
  daily_front_bias      : 当日同場前レース勝ち馬の1角通過順平均
  daily_prior_races     : バイアス計算使用前レース数
  horse_style_vs_bias   : 脚質 vs 当日バイアス差分
  is_rainy              : 天候雨フラグ
  is_sunny              : 天候晴フラグ
  prev_agari_relative   : 前走上がり3F vs フィールド平均

使い方:
  py train_phase_r6.py                    # R5パラメータ流用
  py train_phase_r6.py --optuna 100       # Optuna最適化
"""
import os, sys, json, pickle, argparse, warnings
import numpy as np
import pandas as pd
import lightgbm as lgb
import optuna
from sklearn.metrics import roc_auc_score, log_loss
from sklearn.model_selection import StratifiedKFold

warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

parser = argparse.ArgumentParser()
parser.add_argument('--optuna', type=int, default=0)
parser.add_argument('--log', type=str, default='train_phase_r6.log')
args = parser.parse_args()

import datetime
log_f = open(args.log, 'w', encoding='utf-8')
def tee(msg):
    print(msg)
    log_f.write(msg + '\n')
    log_f.flush()

print("=" * 80)
print("  Phase R6 モデル訓練（74 + 6 = 80特徴量）")
print("=" * 80)

# ===================================================================
# 特徴量リスト
# ===================================================================
with open('models/phase_r5/feature_list.pkl', 'rb') as f:
    BASE_FEATURES = pickle.load(f)   # R5の74特徴量

R6_FEATURES = [
    'daily_front_bias',
    'daily_prior_races',
    'horse_style_vs_bias',
    'is_rainy',
    'is_sunny',
    'prev_agari_relative',
]

FEATURE_LIST = BASE_FEATURES + R6_FEATURES
print(f"特徴量数: {len(BASE_FEATURES)}(R5) + {len(R6_FEATURES)}(R6) = {len(FEATURE_LIST)}")

# ===================================================================
# データ読み込み
# ===================================================================
print("\nデータ読み込み中...")
df_train = pd.read_csv('data/phase_r6/train_features.csv', low_memory=False)
df_val   = pd.read_csv('data/phase_r6/val_features.csv',   low_memory=False)
df_test  = pd.read_csv('data/phase_r6/test_features.csv',  low_memory=False)

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
# ハイパーパラメータ
# ===================================================================
kfold = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

with open('models/phase_r5/metadata.json', encoding='utf-8') as f:
    r5_meta = json.load(f)
R5_BEST_PARAMS = r5_meta['best_params']

if args.optuna > 0:
    print(f"\nOptuna 最適化開始（{args.optuna}トライアル・5-Fold CV）")

    def objective(trial):
        params = {
            'objective':         'binary',
            'metric':            'binary_logloss',
            'boosting_type':     'gbdt',
            'verbose':           -1,
            'random_state':      42,
            'bagging_freq':      5,
            'learning_rate':     trial.suggest_float('learning_rate', 0.005, 0.08, log=True),
            'num_leaves':        trial.suggest_int('num_leaves', 15, 127),
            'min_child_samples': trial.suggest_int('min_child_samples', 10, 150),
            'feature_fraction':  trial.suggest_float('feature_fraction', 0.5, 1.0),
            'bagging_fraction':  trial.suggest_float('bagging_fraction', 0.5, 1.0),
            'lambda_l1':         trial.suggest_float('lambda_l1', 0.0, 10.0),
            'lambda_l2':         trial.suggest_float('lambda_l2', 0.0, 10.0),
            'min_gain_to_split': trial.suggest_float('min_gain_to_split', 0.0, 5.0),
        }
        cv_aucs = []
        for tr_idx, vl_idx in kfold.split(X_train, y_train_win):
            ds_tr = lgb.Dataset(X_train[tr_idx], label=y_train_win[tr_idx])
            ds_vl = lgb.Dataset(X_train[vl_idx], label=y_train_win[vl_idx], reference=ds_tr)
            m = lgb.train(params, ds_tr, num_boost_round=3000,
                          valid_sets=[ds_vl], valid_names=['valid'],
                          callbacks=[lgb.early_stopping(80, verbose=False),
                                     lgb.log_evaluation(0)])
            cv_aucs.append(roc_auc_score(y_train_win[vl_idx],
                                         m.predict(X_train[vl_idx], num_iteration=m.best_iteration)))
        return float(np.mean(cv_aucs))

    def cb(study, trial):
        now = datetime.datetime.now().strftime('%H:%M:%S')
        if trial.number % 5 == 0 or trial.value == study.best_value:
            b = study.best_trial
            msg = (f"  [{now}] Trial {trial.number:3d}: AUC={trial.value:.4f} | "
                   f"best={b.value:.4f}(#{b.number}) "
                   f"lr={trial.params.get('learning_rate',0):.4f} "
                   f"leaves={trial.params.get('num_leaves',0)}")
            tee(msg)
        if trial.number % 10 == 9:
            tee(f"  [中間ベスト] {study.best_params}")

    study = optuna.create_study(direction='maximize',
                                sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=args.optuna, callbacks=[cb])
    best = study.best_trial
    best_params = {'objective': 'binary', 'metric': 'binary_logloss',
                   'boosting_type': 'gbdt', 'verbose': -1, 'random_state': 42,
                   'bagging_freq': 5, **best.params}
    tee(f"\n最適化完了: Best CV AUC={best.value:.4f}")
    tee(f"ベストパラメータ: {best.params}")
    with open('models/phase_r6/optuna_study.pkl', 'wb') as _f:
        pickle.dump(study, _f)
    tee("  optuna_study.pkl 保存済み")
else:
    # R5 ベストパラメータを流用（lr=0.0146, leaves=30）
    best_params = R5_BEST_PARAMS.copy()
    print("\nOptuna スキップ（R5パラメータを流用）")
    print(f"  lr={best_params.get('learning_rate',0):.4f}  "
          f"leaves={best_params.get('num_leaves',0)}")

# ===================================================================
# 単勝モデル訓練
# ===================================================================
print("\n単勝モデル訓練中...")
train_ds = lgb.Dataset(X_train, label=y_train_win)
val_ds   = lgb.Dataset(X_val,   label=y_val_win,   reference=train_ds)
model_win = lgb.train(
    best_params, train_ds, num_boost_round=3000,
    valid_sets=[val_ds], valid_names=['valid'],
    callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(100)],
)
val_auc_win = roc_auc_score(y_val_win, model_win.predict(X_val, num_iteration=model_win.best_iteration))
val_ll_win  = log_loss(y_val_win,      model_win.predict(X_val, num_iteration=model_win.best_iteration))
tee(f"  Win Val AUC: {val_auc_win:.4f}  LogLoss: {val_ll_win:.4f}  BestIter: {model_win.best_iteration}")

# ===================================================================
# 複勝モデル訓練
# ===================================================================
print("\n複勝モデル訓練中...")
tr_place = lgb.Dataset(X_train, label=y_train_place)
vl_place = lgb.Dataset(X_val,   label=y_val_place,  reference=tr_place)
model_place = lgb.train(
    best_params, tr_place, num_boost_round=3000,
    valid_sets=[vl_place], valid_names=['valid'],
    callbacks=[lgb.early_stopping(100, verbose=False), lgb.log_evaluation(100)],
)
val_auc_place = roc_auc_score(y_val_place, model_place.predict(X_val, num_iteration=model_place.best_iteration))
tee(f"  Place Val AUC: {val_auc_place:.4f}  BestIter: {model_place.best_iteration}")

# ===================================================================
# 特徴量重要度（上位25）
# ===================================================================
print("\n【特徴量重要度 Top 25】")
importance = pd.DataFrame({
    'feature':    FEATURE_LIST,
    'importance': model_win.feature_importance(importance_type='gain'),
}).sort_values('importance', ascending=False)

for _, row in importance.head(25).iterrows():
    tag = ' ★R6新規' if row['feature'] in R6_FEATURES else ''
    print(f"  {row['feature']:<45s} {row['importance']:>8.0f}{tag}")

# ===================================================================
# R6特徴量が上位にあるか確認
# ===================================================================
print("\n【R6特徴量ランキング】")
r6_imp = importance[importance['feature'].isin(R6_FEATURES)]
for _, row in r6_imp.iterrows():
    rank = (importance['importance'] >= row['importance']).sum()
    print(f"  {rank:3d}位 {row['feature']:<40s} gain={row['importance']:>8.0f}")

# ===================================================================
# モデル保存
# ===================================================================
print("\nモデル保存中...")
r6_dir = 'models/phase_r6'
os.makedirs(r6_dir, exist_ok=True)

model_win.save_model(  f'{r6_dir}/model_win.txt')
model_place.save_model(f'{r6_dir}/model_place.txt')
with open(f'{r6_dir}/feature_list.pkl', 'wb') as f:
    pickle.dump(FEATURE_LIST, f)

# R5 AUC 読み込み比較用
r5_auc = r5_meta.get('win_model', {}).get('val_auc', 0)

metadata = {
    'phase':          'R6',
    'num_features':   len(FEATURE_LIST),
    'base_features':  BASE_FEATURES,
    'r6_features':    R6_FEATURES,
    'best_params':    best_params,
    'win_model':  {'val_auc': float(val_auc_win),  'val_logloss': float(val_ll_win),
                   'best_iteration': model_win.best_iteration},
    'place_model': {'val_auc': float(val_auc_place),
                    'best_iteration': model_place.best_iteration},
}
with open(f'{r6_dir}/metadata.json', 'w', encoding='utf-8') as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)
print(f"  保存先: {r6_dir}/")

# ===================================================================
# R5 との比較
# ===================================================================
print()
print("=" * 80)
print("  Phase R6 訓練完了")
print("=" * 80)
print(f"\n【R5 vs R6 比較】")
print(f"  指標           R5          R6")
print(f"  Val AUC(win):  {r5_auc:.4f}      {val_auc_win:.4f}  "
      f"{'★改善' if val_auc_win > r5_auc else '▼低下'}")
print(f"  特徴量数:      {len(BASE_FEATURES):>5}         {len(FEATURE_LIST):>5}")

print()
print("【次のステップ】")
print("  # R6 モデルをアクティブにしてバックテスト:")
print("  copy models\\phase_r6\\model_win.txt     phase14_model_win.txt")
print("  copy models\\phase_r6\\model_place.txt   phase14_model_place.txt")
print("  copy models\\phase_r6\\feature_list.pkl  phase14_feature_list.pkl")
print("  py run_gui_backtest.py --year 2024")
print("  py run_gui_backtest.py --year 2025")
print()
