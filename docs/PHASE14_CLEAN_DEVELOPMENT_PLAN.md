# Phase 14 クリーンルーム開発計画書

**作成日**: 2026年2月21日
**目的**: データリーケージなし、GUI完全一致の信頼できるモデル開発
**推定所要時間**: 10-15時間

---

## 🎯 目的

### 主目的
Phase 13の問題点を全て解決した、**完全に信頼できる**複勝予測モデルの開発

### 副目的
1. Phase 13の真の性能を再検証
2. GUI/バックテスト完全一致の検証基盤構築
3. データリーケージ検出システムの実装

---

## 🚨 Phase 13の問題点（詳細）

### 問題1: データリーケージの疑い
**症状**:
- `phase13_full_period_ALL_RACES_results.csv`の生成方法が不明
- `honmei_odds`が0のレースが多数（オッズ情報なしで予測）
- 全確率帯で100%超という非現実的な結果

**リスク**:
- `datetime.now()`で未来データを使用している可能性
- バックテスト時に結果を知った上で予測している可能性

**検証方法**:
```python
# レース日付でデータをフィルタしているか確認
# current_dateパラメータが正しく使われているか確認
```

---

### 問題2: GUIとバックテストの不一致
**症状**:
- GUI: 79個の特徴量
- Phase 13モデル: 39個の特徴量
- モデルファイル名の混乱（Phase 12 vs Phase 13）

**リスク**:
- バックテストとGUIが全く違う予測をしている
- 実運用時に期待した結果が出ない

**検証方法**:
```python
# 同じレースIDでGUI予測とバックテスト予測を比較
# 全てのカラム（勝率予測、複勝予測、印）が一致するか確認
```

---

### 問題3: 払戻データの構造問題
**症状**:
- 馬番が結合されている（"7613" → 本来は ['7','6','1','3']）
- マッチング精度が不明

**リスク**:
- 実際の払戻額と計算が合わない
- 回収率の過大評価

---

### 問題4: 検証の不足
**症状**:
- 既存のCSVファイルを集計しただけ
- 実際のGUI予測との照合なし
- 1レースごとの詳細検証なし

**リスク**:
- 全ての結果が信頼できない

---

## 📋 Phase 14 開発手順（詳細）

### Phase 1: 検証基盤構築（3-4時間）

#### Task 1.1: GUI/バックテスト一致検証スクリプト作成（1時間）

**ファイル**: `verify_gui_backtest_match.py`

**実装内容**:
```python
"""
GUIとバックテストの完全一致を検証
"""
import tkinter as tk
from keiba_prediction_gui_v3 import KeibaGUIv3
import pandas as pd

def verify_single_race(race_id):
    """1レースで完全一致を検証"""

    # 1. GUIで予測（predict_core使用）
    gui = KeibaGUIv3(root)
    horses, race_info = gui.get_race_from_database(race_id)
    has_odds = any(h.get('単勝オッズ', 0) > 0 for h in horses)

    # レース日付取得
    race_date = extract_race_date(race_info['date'])

    # GUI予測実行
    df_gui = gui.predict_core(race_id, horses, race_info, has_odds,
                               current_date=race_date)

    # 2. バックテストで予測（同じpredict_core使用）
    df_backtest = gui.predict_core(race_id, horses, race_info, has_odds,
                                    current_date=race_date)

    # 3. 完全一致確認
    assert df_gui.equals(df_backtest), "GUI and backtest mismatch!"

    # 4. 詳細比較
    for col in ['勝率予測', '複勝予測', '印']:
        if col in df_gui.columns:
            diff = (df_gui[col] != df_backtest[col]).sum()
            assert diff == 0, f"{col} mismatch: {diff} rows"

    return True

# 10レースでテスト
test_races = [
    "202401010101", "202401010102", "202401010103",
    "202401020201", "202401020202", "202401020203",
    "202402010101", "202402010102", "202402010103",
    "202403010101"
]

for race_id in test_races:
    print(f"Testing {race_id}...")
    verify_single_race(race_id)
    print(f"  OK: GUI and backtest match perfectly")
```

**成功基準**: 10レース全てで完全一致

---

#### Task 1.2: データリーケージ検出システム（1時間）

**ファイル**: `detect_data_leakage.py`

**実装内容**:
```python
"""
データリーケージを検出
"""
def check_leakage(df, race_id, current_date):
    """
    使用データが全てcurrent_date以前かチェック
    """
    # レース日付抽出
    race_date = extract_race_date_from_id(race_id)

    # current_dateがレース日付より未来ならエラー
    if current_date > race_date:
        raise ValueError(f"LEAKAGE: current_date {current_date} > race_date {race_date}")

    # 使用データの日付を全チェック
    data_dates = pd.to_datetime(df['date_normalized'], errors='coerce')
    future_data = data_dates > pd.to_datetime(current_date)

    if future_data.any():
        leak_count = future_data.sum()
        raise ValueError(f"LEAKAGE: {leak_count} records from future detected!")

    return True

# 全バックテスト実行時に強制チェック
```

**成功基準**: リーケージ検出機能が動作

---

#### Task 1.3: 10レース徹底検証（1-2時間）

**ファイル**: `phase14_pilot_verification.py`

**検証内容**:
1. GUI/バックテスト一致確認
2. リーケージチェック
3. 実払戻データとの照合
4. 回収率計算（保守的に）

**成果物**: `phase14_pilot_results.csv`

**成功基準**:
- 10レース全てで一致
- リーケージなし
- 回収率が現実的（50-120%程度）

---

### Phase 2: Phase 13 再検証（2-3時間）

#### Task 2.1: Phase 13を正しい方法で再実行（2時間）

**ファイル**: `phase13_clean_backtest.py`

**実装内容**:
```python
"""
Phase 13の再検証（リーケージなし、GUI一致版）
"""
# 1. GUIインスタンス作成
gui = KeibaGUIv3(root)

# 2. 対象レース（2024-2025年、払戻データあり）
race_ids = get_races_with_payout()

results = []
for race_id in race_ids:
    # レース日付取得
    race_date = extract_race_date(race_id)

    # リーケージチェック
    check_leakage(gui.df, race_id, race_date)

    # GUI predict_coreで予測
    horses, race_info = gui.get_race_from_database(race_id)
    has_odds = any(h.get('単勝オッズ', 0) > 0 for h in horses)

    df_pred = gui.predict_core(race_id, horses, race_info, has_odds,
                                current_date=race_date)  # 重要！

    # 推奨馬券取得
    targets = KeibaGUIv3.get_recommended_bet_targets(df_pred, has_odds)

    # 実払戻と照合
    payout = get_payout(race_id)
    recovery = calculate_recovery(targets, payout)

    results.append({
        'race_id': race_id,
        'honmei': targets['honmei'],
        'win_proba': targets['win_proba'],
        'recovery': recovery
    })

# 回収率集計
df_results = pd.DataFrame(results)
overall_recovery = df_results['recovery'].mean()
print(f"Phase 13 真の回収率: {overall_recovery:.1f}%")
```

**成功基準**:
- リーケージなしで実行
- 真の回収率を算出（おそらく80-120%）

---

#### Task 2.2: Phase 13結果の文書化（1時間）

**ファイル**: `docs/PHASE13_CLEAN_VERIFICATION.md`

**内容**:
- 旧結果（疑わしい219%）
- 新結果（正しい方法）
- 差分の分析
- 問題点の総括

---

### Phase 3: Phase 14 モデル開発（6-8時間）

#### Task 3.1: データ準備（1.5時間）

**ファイル**: `phase14_data_prep_clean.py`

**実装内容**:
```python
"""
Phase 14用データ準備（完全版）
"""
# 1. 完全なデータベース使用
df = pd.read_csv('data/main/netkeiba_data_2020_2025_complete.csv')

# 2. 目的変数: 1-3着
df['target_place'] = (df['着順'] <= 3).astype(int)

# 3. 時系列分割（リーケージ防止）
# 訓練: 2020-2023
# 検証: 2024
# テスト: 2025

df_train = df[df['year'].isin([2020, 2021, 2022, 2023])]
df_val = df[df['year'] == 2024]
df_test = df[df['year'] == 2025]

# 4. 未来データ混入チェック
assert df_train['year'].max() < df_val['year'].min()
assert df_val['year'].max() < df_test['year'].min()
```

**成功基準**:
- 訓練・検証・テストが時系列で完全分離
- リーケージチェック通過

---

#### Task 3.2: 特徴量エンジニアリング（2時間）

**ファイル**: `phase14_feature_engineering.py`

**特徴量**:
```python
# Phase 13と同じ基本特徴量
# + 複勝特化の追加特徴量

# 1. 安定性指標
- 複勝率（過去10走）
- 連対率の推移
- 着順の標準偏差（小さい方が安定）

# 2. 展開指標
- 逃げ・先行の有利不利
- ペース予測
- コース適性

# 3. 相対指標
- 出走馬の平均実力との差
- 人気と実力の乖離度
```

**成功基準**:
- 特徴量数を明確に記録
- 全レースで計算可能

---

#### Task 3.3: モデル訓練（2-3時間）

**ファイル**: `train_phase14_clean.py`

**実装内容**:
```python
"""
Phase 14モデル訓練（LightGBM）
"""
import lightgbm as lgb

# 1. データ読み込み
X_train = # 訓練データの特徴量
y_train = # target_place
X_val = # 検証データの特徴量
y_val = # target_place

# 2. LightGBM訓練
params = {
    'objective': 'binary',
    'metric': 'auc',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.8,
    'verbosity': -1
}

model = lgb.train(
    params,
    lgb.Dataset(X_train, y_train),
    num_boost_round=1000,
    valid_sets=[lgb.Dataset(X_val, y_val)],
    early_stopping_rounds=50
)

# 3. モデル保存
import pickle
with open('model_phase14_place.pkl', 'wb') as f:
    pickle.dump(model, f)

# 特徴量リスト保存
feature_list = X_train.columns.tolist()
with open('phase14_feature_list.pkl', 'wb') as f:
    pickle.dump(feature_list, f)
```

**成功基準**:
- AUC > 0.65（検証データ）
- 過学習なし

---

#### Task 3.4: バックテスト検証（2-3時間）

**ファイル**: `phase14_clean_backtest.py`

**実装内容**:
```python
"""
Phase 14バックテスト（完全版）
"""
# Phase 13と同じ検証基盤を使用

# 1. GUIにPhase 14モデルを読み込み可能にする
#    （またはpredict_coreを複勝版に修正）

# 2. 全レースでバックテスト
for race_id in test_races:
    # リーケージチェック
    race_date = extract_race_date(race_id)
    check_leakage(data, race_id, race_date)

    # 予測
    df_pred = predict_with_phase14(race_id, current_date=race_date)

    # 払戻照合
    payout = get_payout(race_id)
    recovery = calculate_fukusho_recovery(df_pred, payout)

# 3. 確率帯別の回収率
bands = [(0.15, 0.25), (0.25, 0.35), (0.35, 0.45), (0.45, 0.60)]
for min_p, max_p in bands:
    band_recovery = calculate_band_recovery(results, min_p, max_p)
    print(f"{min_p*100:.0f}-{max_p*100:.0f}%: {band_recovery:.1f}%")
```

**成功基準**:
- リーケージなし
- 複勝回収率 > 80%なら成功
- 複勝回収率 > 100%なら大成功

---

### Phase 4: 文書化（1-2時間）

#### Task 4.1: Phase 14完全レポート作成

**ファイル**: `docs/PHASE14_COMPLETE_REPORT.md`

**内容**:
1. 開発プロセスの全記録
2. Phase 13との比較
3. リーケージ防止策
4. 真の性能評価
5. 実運用ガイド

---

## ✅ 成功基準

### Minimum Success（最低限の成功）
- ✅ リーケージなしでバックテスト実行
- ✅ GUI/バックテスト完全一致
- ✅ Phase 13の真の性能判明

### Target Success（目標）
- ✅ 上記全て
- ✅ Phase 14複勝回収率 > 80%
- ✅ 検証基盤の構築

### Stretch Success（理想）
- ✅ 上記全て
- ✅ Phase 14複勝回収率 > 100%
- ✅ Phase 13単勝も100%超（正しい検証で）

---

## ⏱️ タイムライン

| Phase | タスク | 所要時間 | 累積 |
|:---:|:---|:---:|:---:|
| 1 | 検証基盤構築 | 3-4h | 4h |
| 2 | Phase 13再検証 | 2-3h | 7h |
| 3 | Phase 14開発 | 6-8h | 15h |
| 4 | 文書化 | 1-2h | 17h |

**総所要時間**: 12-17時間

---

## 📁 成果物リスト

### スクリプト
1. `verify_gui_backtest_match.py` - 一致検証
2. `detect_data_leakage.py` - リーケージ検出
3. `phase14_pilot_verification.py` - パイロット検証
4. `phase13_clean_backtest.py` - Phase 13再検証
5. `phase14_data_prep_clean.py` - データ準備
6. `phase14_feature_engineering.py` - 特徴量
7. `train_phase14_clean.py` - モデル訓練
8. `phase14_clean_backtest.py` - バックテスト

### モデルファイル
1. `model_phase14_place.pkl` - 複勝予測モデル
2. `phase14_feature_list.pkl` - 特徴量リスト
3. `phase14_metadata.json` - メタデータ

### ドキュメント
1. `PHASE13_CLEAN_VERIFICATION.md` - Phase 13再検証結果
2. `PHASE14_COMPLETE_REPORT.md` - Phase 14完全レポート
3. `LEAKAGE_PREVENTION_GUIDE.md` - リーケージ防止ガイド

### データファイル
1. `phase14_pilot_results.csv` - パイロット検証結果
2. `phase13_clean_results.csv` - Phase 13再検証結果
3. `phase14_backtest_results.csv` - Phase 14バックテスト結果

---

## 🚨 重要な注意事項

### 絶対に守ること
1. ✅ **リーケージチェックを必ず実行**
   - 全バックテストで`check_leakage()`呼び出し
   - current_dateは必ずレース日付

2. ✅ **GUI/バックテスト完全一致**
   - 同じpredict_core()を使用
   - パラメータを完全一致させる

3. ✅ **保守的な評価**
   - 80%でも「まあまあ」
   - 100%超えたら「すごい」
   - 150%超えたら「疑う」

### 絶対にやらないこと
1. ❌ 既存の結果を信じる
2. ❌ リーケージチェックをスキップ
3. ❌ 理論値で回収率計算
4. ❌ 都合の良い数値だけ報告

---

## 📊 期待される結果

### 現実的な予想

**Phase 13（単勝）再検証**:
- 旧結果: 143.9%（疑わしい）
- 新結果予想: 90-110%（現実的）
- もし120%超えたら本当にすごい

**Phase 14（複勝）**:
- 目標: 85%以上
- 期待: 90-100%
- 理想: 105%以上

---

## ✅ 実行前チェックリスト

作業開始前に確認:

- [ ] 完全なデータベースの場所確認（data/main/）
- [ ] GUIが正常動作することを確認
- [ ] Phase 13モデルファイルの場所確認
- [ ] 払戻データの準備確認
- [ ] ディスク容量確認（10GB以上推奨）
- [ ] バックアップ作成

---

## 🎯 最終ゴール

**信頼できるモデルとシステム**

1. Phase 13の真の性能を知る
2. Phase 14で堅実な複勝モデルを作る
3. リーケージのない検証基盤を構築
4. 実運用可能なシステムを完成させる

**楽観的な期待ではなく、厳格な検証による確実な成果を目指す**

---

**作成者**: Claude Opus 4.6
**作成日**: 2026年2月21日
**レビュー待ち**: ユーザー承認後に実行開始
