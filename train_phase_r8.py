"""
Phase R8 モデル訓練
71特徴量（R7+Optuna）+ 7個の新特徴量 = 78特徴量

追加特徴量:
  father_track_win_rate        : 父馬×競馬場 勝率（B）
  mother_father_track_win_rate : 母父×競馬場 勝率（B）
  consecutive_losses           : 連続着外回数（C）
  form_trend                   : 直近3走トレンド（C）
  best_distance_diff           : 得意距離との乖離（C）
  horse_waku_win_rate          : 馬個体の枠番勝率（D）
  large_field_win_rate         : 大人数レース勝率（D）

使い方:
  py train_phase_r8.py                  # R7+Optunaパラメータ流用
  py train_phase_r8.py --optuna 100     # Optuna最適化
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
parser.add_argument('--log', type=str, default='train_phase_r8.log')
args = parser.parse_args()

import datetime
log_f = open(args.log, 'w', encoding='utf-8')
def tee(msg):
    print(msg)
    log_f.write(msg + '\n')
    log_f.flush()

print("=" * 80)
print("  Phase R8 モデル訓練（71 + 7 = 78特徴量）")
print("=" * 80)

# 特徴量リスト
with open('models/phase_r7/feature_list.pkl', 'rb') as f:
    BASE_FEATURES = pickle.load(f)   # R7+Optunaの71特徴量

R8_FEATURES = [
    'father_track_win_rate',
    'mother_father_track_win_rate',
    'consecutive_losses',
    'form_trend',
    'best_distance_diff',
    'horse_waku_win_rate',
    'large_field_win_rate',
]

FEATURE_LIST = BASE_FEATURES + R8_FEATURES
print(f"特徴量数: {len(BASE_FEATURES)}(R7) + {len(R8_FEATURES)}(R8) = {len(FEATURE_LIST)}")

# データ
print("データ読み込み中...")
df_train = pd.read_csv('data/phase_r8/train_features.csv', low_memory=False)
df_val   = pd.read_csv('data/phase_r8/val_features.csv',   low_memory=False)
df_test  = pd.read_csv('data/phase_r8/test_features.csv',  low_memory=False)

# 存在確認
feats = [f for f in FEATURE_LIST if f in df_train.columns]
missing = [f for f in FEATURE_LIST if f not in df_train.columns]
if missing:
    print(f"  警告: 不足特徴量 {missing}")
    for f in missing:
        df_train[f] = 0
        df_val[f]   = 0
        df_test[f]  = 0

print(f"  train: {len(df_train):,}行  val: {len(df_val):,}行  test: {len(df_test):,}行")
print(f"  存在特徴量: {len(feats)}/{len(FEATURE_LIST)}")

X_tr = df_train[FEATURE_LIST].fillna(0)
y_tr = df_train['target_win']
X_vl = df_val[FEATURE_LIST].fillna(0)
y_vl = df_val['target_win']

# R7+Optunaのパラメータを読み込み（デフォルト）
with open('models/phase_r7/metadata.json') as f:
    r7_meta = json.load(f)
R7_BEST_PARAMS = r7_meta['best_params']

# Optuna最適化 or R7パラメータ流用
if args.optuna > 0:
    tee(f"\nOptuna最適化中（{args.optuna}試行）...")
    X_cv = pd.concat([X_tr, X_vl], ignore_index=True)
    y_cv = pd.concat([y_tr, y_vl], ignore_index=True)

    def objective(trial):
        params = {
            'objective': 'binary', 'metric': 'binary_logloss',
            'boosting_type': 'gbdt', 'verbose': -1, 'random_state': 42, 'bagging_freq': 5,
            'learning_rate':      trial.suggest_float('learning_rate', 0.005, 0.1, log=True),
            'num_leaves':         trial.suggest_int('num_leaves', 10, 150),
            'min_child_samples':  trial.suggest_int('min_child_samples', 20, 200),
            'feature_fraction':   trial.suggest_float('feature_fraction', 0.5, 1.0),
            'bagging_fraction':   trial.suggest_float('bagging_fraction', 0.5, 1.0),
            'lambda_l1':          trial.suggest_float('lambda_l1', 0.0, 10.0),
            'lambda_l2':          trial.suggest_float('lambda_l2', 0.0, 10.0),
            'min_gain_to_split':  trial.suggest_float('min_gain_to_split', 0.0, 1.0),
        }
        kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        aucs = []
        for tr_idx, vl_idx in kf.split(X_cv, y_cv):
            ds_tr = lgb.Dataset(X_cv.iloc[tr_idx], label=y_cv.iloc[tr_idx])
            ds_vl = lgb.Dataset(X_cv.iloc[vl_idx], label=y_cv.iloc[vl_idx])
            m = lgb.train(params, ds_tr, num_boost_round=1000, valid_sets=[ds_vl],
                          callbacks=[lgb.early_stopping(30, verbose=False),
                                     lgb.log_evaluation(-1)])
            aucs.append(roc_auc_score(y_cv.iloc[vl_idx], m.predict(X_cv.iloc[vl_idx])))
        return np.mean(aucs)

    def cb(study, trial):
        if trial.number % 10 == 0 or trial.value == study.best_value:
            b = study.best_trial
            tee(f"  [{datetime.datetime.now().strftime('%H:%M:%S')}] "
                f"Trial {trial.number:3d}: AUC={trial.value:.4f} | "
                f"best={b.value:.4f}(#{b.number}) "
                f"lr={b.params.get('learning_rate',0):.4f} "
                f"leaves={b.params.get('num_leaves',0)}")

    study = optuna.create_study(direction='maximize',
                                sampler=optuna.samplers.TPESampler(seed=42))
    study.optimize(objective, n_trials=args.optuna, callbacks=[cb])
    best = study.best_trial
    best_params = {'objective': 'binary', 'metric': 'binary_logloss',
                   'boosting_type': 'gbdt', 'verbose': -1,
                   'random_state': 42, 'bagging_freq': 5,
                   **best.params}
    os.makedirs('models/phase_r8', exist_ok=True)
    with open('models/phase_r8/optuna_study.pkl', 'wb') as f:
        pickle.dump(study, f)
    tee(f"\n最適化完了: Best CV AUC={best.value:.4f}")
    tee(f"ベストパラメータ: {best.params}")
else:
    best_params = R7_BEST_PARAMS.copy()
    tee(f"\nOptuna スキップ（R7+Optunaパラメータ流用）")
    tee(f"  lr={best_params.get('learning_rate',0):.4f}  "
        f"leaves={best_params.get('num_leaves',0)}")

# 単勝モデル訓練
tee("\n単勝モデル訓練中...")
tr_ds = lgb.Dataset(X_tr, label=y_tr)
vl_ds = lgb.Dataset(X_vl, label=y_vl, reference=tr_ds)
win_model = lgb.train(
    best_params, tr_ds, num_boost_round=3000,
    valid_sets=[vl_ds],
    callbacks=[lgb.log_evaluation(100), lgb.early_stopping(50, verbose=False)]
)
pred_vl = win_model.predict(X_vl)
win_auc  = roc_auc_score(y_vl, pred_vl)
win_ll   = log_loss(y_vl, pred_vl)
tee(f"  Win Val AUC: {win_auc:.4f}  LogLoss: {win_ll:.4f}  BestIter: {win_model.best_iteration}")

# 複勝モデル訓練
tee("\n複勝モデル訓練中...")
tr_p = lgb.Dataset(X_tr, label=df_train['target_place'])
vl_p = lgb.Dataset(X_vl, label=df_val['target_place'], reference=tr_p)
place_model = lgb.train(
    best_params, tr_p, num_boost_round=3000,
    valid_sets=[vl_p],
    callbacks=[lgb.log_evaluation(100), lgb.early_stopping(50, verbose=False)]
)
place_auc = roc_auc_score(df_val['target_place'], place_model.predict(X_vl))
tee(f"  Place Val AUC: {place_auc:.4f}  BestIter: {place_model.best_iteration}")

# 特徴量重要度
tee("\n【特徴量重要度 Top 25】")
imp = pd.Series(win_model.feature_importance(importance_type='gain'),
                index=FEATURE_LIST).sort_values(ascending=False)
for i, (feat, val) in enumerate(imp.head(25).items()):
    r8_mark = ' ★R8新規' if feat in R8_FEATURES else ''
    tee(f"  {feat:<45} {val:>10.0f}{r8_mark}")

tee("\n【R8特徴量ランキング】")
for feat in R8_FEATURES:
    rank_pos = list(imp.index).index(feat) + 1
    tee(f"  {rank_pos:3d}位 {feat:<45} gain={imp[feat]:>8.0f}")

# 比較
tee("\n【R7+Optuna vs R8 比較】")
tee(f"  {'指標':<20} {'R7+Optuna':>12} {'R8':>12}")
with open('models/phase_r7/metadata.json') as f:
    r7 = json.load(f)
tee(f"  {'Val AUC(win):':<20} {r7['win_model']['val_auc']:>12.4f} {win_auc:>12.4f}  "
    f"{'↑改善' if win_auc > r7['win_model']['val_auc'] else '▼低下'}")
tee(f"  {'特徴量数:':<20} {r7['num_features']:>12} {len(FEATURE_LIST):>12}")

# 保存
r8_dir = 'models/phase_r8'
os.makedirs(r8_dir, exist_ok=True)
win_model.save_model(f'{r8_dir}/model_win.txt')
place_model.save_model(f'{r8_dir}/model_place.txt')
with open(f'{r8_dir}/feature_list.pkl', 'wb') as f:
    pickle.dump(FEATURE_LIST, f)

meta = {
    'phase': 'R8',
    'num_features': len(FEATURE_LIST),
    'base_features': BASE_FEATURES,
    'r8_features': R8_FEATURES,
    'best_params': best_params,
    'win_model':   {'val_auc': win_auc, 'val_logloss': win_ll,
                    'best_iteration': win_model.best_iteration},
    'place_model': {'val_auc': place_auc,
                    'best_iteration': place_model.best_iteration},
}
with open(f'{r8_dir}/metadata.json', 'w', encoding='utf-8') as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)

tee("\n" + "=" * 80)
tee("  Phase R8 訓練完了")
tee("=" * 80)
tee(f"\n保存先: {r8_dir}/")
tee(f"\n【次のステップ】")
tee(f"  # R8モデルをアクティブにしてバックテスト:")
tee(f"  copy models\\phase_r8\\model_win.txt     phase14_model_win.txt")
tee(f"  copy models\\phase_r8\\model_place.txt   phase14_model_place.txt")
tee(f"  copy models\\phase_r8\\feature_list.pkl  phase14_feature_list.pkl")
tee(f"  py run_gui_backtest.py --year 2024")
tee(f"  py run_gui_backtest.py --year 2025")

log_f.close()
