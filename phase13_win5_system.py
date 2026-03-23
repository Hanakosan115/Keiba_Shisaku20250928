# -*- coding: utf-8 -*-
"""
Phase 13: WIN5予測システム

5レース全て的中させる超高配当馬券の予測
"""
import pandas as pd
import numpy as np
import pickle
import tkinter as tk
from keiba_prediction_gui_v3 import KeibaGUIv3
from phase13_feature_engineering import calculate_horse_features_safe, normalize_date, calculate_sire_stats, calculate_trainer_jockey_stats
from itertools import product
import json

print("=" * 80)
print("  Phase 13: WIN5予測システム")
print("=" * 80)
print()

# ===================================================================
# GUI準備
# ===================================================================

print("[1/7] GUI・データ準備...")
root = tk.Tk()
root.withdraw()
gui = KeibaGUIv3(root)

df_all = gui.df.copy()

# モデル読み込み
with open('phase13_model_win.pkl', 'rb') as f:
    model_win = pickle.load(f)
with open('phase13_feature_list.pkl', 'rb') as f:
    feature_cols = pickle.load(f)
with open('phase13_calibrators.pkl', 'rb') as f:
    calibrators = pickle.load(f)

calibrator_win = calibrators['win']

# 訓練データで統計計算
train_df = pd.read_csv('phase13_train_2020_2022.csv', low_memory=False)
sire_stats = calculate_sire_stats(train_df)
trainer_jockey_stats = calculate_trainer_jockey_stats(train_df)

print("  準備完了")
print()

# ===================================================================
# WIN5対象日のレース取得
# ===================================================================

print("[2/7] WIN5対象日のレースID取得...")
print()

# 2025年の土日のレースをサンプリング
df_all['date_normalized'] = df_all['date'].apply(normalize_date)
df_all['year'] = pd.to_datetime(df_all['date_normalized'], errors='coerce').dt.year

# 日付ごとにレースをグループ化
date_groups = df_all[df_all['year'] == 2025].groupby('date_normalized')

# WIN5対象日を選択（各日5レース以上ある日）
win5_dates = []
for date, group in date_groups:
    race_ids = group['race_id'].unique()
    if len(race_ids) >= 5:
        win5_dates.append((date, list(race_ids)))

# 最初の10日間をサンプル
win5_dates = win5_dates[:10]

print(f"  WIN5対象日: {len(win5_dates)}日")
print()

# ===================================================================
# WIN5バックテスト
# ===================================================================

print("[3/7] WIN5バックテスト実行...")
print()

win5_results = []
errors = []

for date_idx, (date, race_ids) in enumerate(win5_dates):
    print(f"  [{date_idx+1}/{len(win5_dates)}] {date}")

    # 5レースを選択（最初の5レース）
    target_races = race_ids[:5]

    # 各レースの予測
    daily_predictions = []
    all_success = True

    for race_id in target_races:
        try:
            horses, race_info = gui.get_race_from_database(str(int(race_id)))

            if not horses or len(horses) == 0:
                all_success = False
                break

            race_date = race_info.get('date', '')
            cutoff_date = normalize_date(race_date)

            if not cutoff_date:
                all_success = False
                break

            # 各馬の予測
            race_features = []
            for horse in horses:
                horse_id = horse.get('horse_id')
                if not horse_id:
                    continue

                features = calculate_horse_features_safe(
                    horse_id, df_all, cutoff_date, sire_stats, trainer_jockey_stats,
                    trainer_name=horse.get('調教師'),
                    jockey_name=horse.get('騎手'),
                    race_track=race_info.get('track_name'),
                    race_distance=race_info.get('distance'),
                    race_course_type=race_info.get('course_type'),
                    race_track_condition=race_info.get('track_condition'),
                    current_frame=horse.get('枠番'),
                    race_id=race_id
                )

                if features is None:
                    features = {feat: 0 for feat in feature_cols}

                for feat in feature_cols:
                    if feat not in features:
                        features[feat] = 0

                feat_df = pd.DataFrame([features])[feature_cols].fillna(0)

                pred_uncalib = model_win.predict_proba(feat_df)[0, 1]
                pred_calib = calibrator_win.transform([pred_uncalib])[0]

                race_features.append({
                    'horse_num': horse['馬番'],
                    'pred_win': pred_calib,
                    'actual_rank': horse.get('実際の着順'),
                })

            if len(race_features) == 0:
                all_success = False
                break

            race_df = pd.DataFrame(race_features)

            # 本命選択（勝率最高）
            best_idx = race_df['pred_win'].idxmax()
            honmei = race_df.loc[best_idx]

            # 実際の1着
            actual_winner = race_df[race_df['actual_rank'] == 1].iloc[0]['horse_num'] if len(race_df[race_df['actual_rank'] == 1]) > 0 else None

            # 的中判定
            hit = (honmei['horse_num'] == actual_winner)

            daily_predictions.append({
                'race_id': race_id,
                'pred_num': honmei['horse_num'],
                'pred_win_proba': honmei['pred_win'],
                'actual_winner': actual_winner,
                'hit': hit
            })

        except Exception as e:
            all_success = False
            errors.append({'race_id': race_id, 'error': str(e)})
            break

    if not all_success or len(daily_predictions) < 5:
        continue

    # WIN5的中判定（5レース全て的中）
    win5_hit = all([p['hit'] for p in daily_predictions])

    # 期待的中確率（5レースの勝率予測の積）
    expected_hit_proba = np.prod([p['pred_win_proba'] for p in daily_predictions])

    win5_results.append({
        'date': date,
        'race_ids': [p['race_id'] for p in daily_predictions],
        'predictions': [p['pred_num'] for p in daily_predictions],
        'actuals': [p['actual_winner'] for p in daily_predictions],
        'hit_flags': [p['hit'] for p in daily_predictions],
        'win5_hit': win5_hit,
        'expected_hit_proba': expected_hit_proba
    })

print()
print(f"  成功: {len(win5_results)}日")
print(f"  エラー: {len(errors)}件")
print()

# ===================================================================
# 結果分析
# ===================================================================

print("[4/7] 結果分析...")
print()

win5_df = pd.DataFrame(win5_results)

total_days = len(win5_df)
win5_hits = win5_df['win5_hit'].sum()
win5_hit_rate = win5_hits / total_days if total_days > 0 else 0

print("【WIN5成績】")
print(f"  対象日数: {total_days}日")
print(f"  WIN5的中: {win5_hits}日")
print(f"  WIN5的中率: {win5_hit_rate*100:.2f}%")
print()

# 期待的中確率の分布
print("【期待的中確率の分布】")
avg_expected = win5_df['expected_hit_proba'].mean()
max_expected = win5_df['expected_hit_proba'].max()
min_expected = win5_df['expected_hit_proba'].min()

print(f"  平均: {avg_expected*100:.4f}%")
print(f"  最大: {max_expected*100:.4f}%")
print(f"  最小: {min_expected*100:.4f}%")
print()

# ===================================================================
# 期待値計算
# ===================================================================

print("[5/7] 期待値計算...")
print()

# WIN5の平均配当を仮定（実績ベース）
# 2020-2025年の平均配当: 約100万円と仮定
AVG_WIN5_PAYOUT = 1000000

print(f"  想定平均配当: {AVG_WIN5_PAYOUT:,}円")
print()

# 期待値 = 的中確率 × 配当
expected_values = []
for _, row in win5_df.iterrows():
    ev = row['expected_hit_proba'] * AVG_WIN5_PAYOUT
    expected_values.append(ev)

win5_df['expected_value'] = expected_values

avg_ev = win5_df['expected_value'].mean()
max_ev = win5_df['expected_value'].max()

print(f"  平均期待値: {avg_ev:,.0f}円 (100円あたり{avg_ev/100:.2f}円)")
print(f"  最大期待値: {max_ev:,.0f}円")
print()

# 回収率計算
theoretical_recovery = (avg_ev / 100) * 100
print(f"  理論回収率: {theoretical_recovery:.1f}%")
print()

# ===================================================================
# 推奨買い目
# ===================================================================

print("[6/7] 推奨買い目分析...")
print()

# 期待値が高い日
high_ev_days = win5_df[win5_df['expected_value'] >= 1000].sort_values('expected_value', ascending=False)

if len(high_ev_days) > 0:
    print("【期待値1,000円以上の日】")
    for _, row in high_ev_days.head(5).iterrows():
        print(f"  {row['date']}: 期待値{row['expected_value']:,.0f}円 (的中確率{row['expected_hit_proba']*100:.4f}%)")
        print(f"    予想: {row['predictions']}")
        print(f"    結果: {row['actuals']}")
        print(f"    的中: {'全的中!' if row['win5_hit'] else '外れ'}")
        print()
else:
    print("  期待値1,000円以上の日はありませんでした")
    print()

# ===================================================================
# 結果保存
# ===================================================================

print("[7/7] 結果保存...")
win5_df.to_csv('phase13_win5_results.csv', index=False)
print("  保存: phase13_win5_results.csv")
print()

# ===================================================================
# サマリー
# ===================================================================

print("=" * 80)
print("  Phase 13: WIN5予測システム 結果")
print("=" * 80)
print()

print("【WIN5成績サマリー】")
print(f"  対象日数: {total_days}日")
print(f"  WIN5的中率: {win5_hit_rate*100:.2f}%")
print(f"  平均期待的中確率: {avg_expected*100:.4f}%")
print()

print("【期待値分析】")
print(f"  想定平均配当: {AVG_WIN5_PAYOUT:,}円")
print(f"  平均期待値: {avg_ev:,.0f}円")
print(f"  理論回収率: {theoretical_recovery:.1f}%")
print()

print("【結論】")
if theoretical_recovery >= 50:
    print(f"  理論回収率{theoretical_recovery:.1f}%")
    print("  → WIN5は超高配当のため、少額購入でも大きなリターンの可能性")
    print("  → 期待値が高い日を選んで購入するのが有効")
else:
    print(f"  理論回収率{theoretical_recovery:.1f}%")
    print("  → WIN5の的中は極めて困難")
    print("  → 娯楽として少額購入が推奨")

print()
print("【注意】")
print("  WIN5の配当は実際のレース結果や購入額により大きく変動します")
print("  この分析は平均配当100万円を仮定した理論計算です")
print()

print("=" * 80)
print()

root.destroy()
