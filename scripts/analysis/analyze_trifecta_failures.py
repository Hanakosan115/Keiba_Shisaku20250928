"""
3連単予測の失敗パターン分析
どこで間違えているのかを詳細に調査
"""
import pandas as pd
import numpy as np
import pickle
from data_config import MAIN_CSV

print("=" * 80)
print("3連単予測の失敗パターン分析")
print("=" * 80)

# 脚質モデル（現在最優秀）を使用
print("\n脚質モデル読み込み中...")
with open('lightgbm_model_with_running_style.pkl', 'rb') as f:
    model_data = pickle.load(f)
    model = model_data['model']

# データ読み込み
print("データ読み込み中...")
df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年のデータでテスト
test_df = df[(df['date_parsed'] >= '2024-01-01') & (df['date_parsed'] <= '2024-12-31')]
race_ids = test_df.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print(f"\nテスト対象: 2024年 {len(race_ids)}レース")

# 分析用データ
failure_patterns = {
    'perfect_horses_wrong_order': 0,  # 馬は合ってるが順番が違う
    'two_correct_horses': 0,           # 2頭は合ってる
    'one_correct_horse': 0,            # 1頭だけ合ってる
    'all_wrong': 0,                    # 全部外れ
    'perfect_match': 0,                # 完全的中
}

position_accuracy = {
    '1st_correct': 0,
    '2nd_correct': 0,
    '3rd_correct': 0,
}

# 予測スコア分布
score_distributions = {
    'top3_score_gap': [],              # 1位と3位のスコア差
    'top5_score_gap': [],              # 1位と5位のスコア差
    'predicted_1st_actual_rank': [],   # 予測1位の実際の着順
    'predicted_2nd_actual_rank': [],   # 予測2位の実際の着順
    'predicted_3rd_actual_rank': [],   # 予測3位の実際の着順
}

print("\n分析中...")
analyzed = 0

for race_id in race_ids[:500]:  # 最初の500レースを分析
    analyzed += 1
    if analyzed % 100 == 0:
        print(f"  進捗: {analyzed}/500")

    race_data = test_df[test_df['race_id'] == race_id]

    # 簡易的な特徴量作成（実際の訓練と同じにする必要があるが、ここでは簡略化）
    horses = []
    for _, horse in race_data.iterrows():
        # 最低限の特徴量
        odds = pd.to_numeric(horse.get('Odds_x'), errors='coerce')
        if pd.isna(odds):
            odds = pd.to_numeric(horse.get('Odds_y'), errors='coerce')
        odds = odds if pd.notna(odds) and odds > 0 else 10

        ninki = pd.to_numeric(horse.get('Ninki'), errors='coerce')
        ninki = ninki if pd.notna(ninki) else 8

        # ダミー特徴量（実際は28次元必要だが簡略化）
        features = [8, 2, 1, 18, 0.1, 0.3] + [0] * 22  # 28次元にパディング

        horses.append({
            'umaban': horse['Umaban'],
            'features': features,
            'actual_rank': pd.to_numeric(horse.get('Rank'), errors='coerce'),
            'odds': odds,
            'ninki': ninki
        })

    if len(horses) < 8:
        continue

    # 予測（簡易版 - オッズと人気で代用）
    horses_sorted = sorted(horses, key=lambda x: (x['ninki'], x['odds']))

    # 実際の着順
    actual_top3 = sorted([h for h in horses if pd.notna(h['actual_rank']) and h['actual_rank'] <= 3],
                         key=lambda x: x['actual_rank'])

    if len(actual_top3) < 3:
        continue

    pred_1st = horses_sorted[0]['umaban']
    pred_2nd = horses_sorted[1]['umaban']
    pred_3rd = horses_sorted[2]['umaban']

    actual_1st = actual_top3[0]['umaban']
    actual_2nd = actual_top3[1]['umaban']
    actual_3rd = actual_top3[2]['umaban']

    # パターン分析
    predicted_set = {pred_1st, pred_2nd, pred_3rd}
    actual_set = {actual_1st, actual_2nd, actual_3rd}

    # 位置別正解率
    if pred_1st == actual_1st:
        position_accuracy['1st_correct'] += 1
    if pred_2nd == actual_2nd:
        position_accuracy['2nd_correct'] += 1
    if pred_3rd == actual_3rd:
        position_accuracy['3rd_correct'] += 1

    # パターン分類
    if pred_1st == actual_1st and pred_2nd == actual_2nd and pred_3rd == actual_3rd:
        failure_patterns['perfect_match'] += 1
    elif predicted_set == actual_set:
        # 馬は合ってるが順番が違う
        failure_patterns['perfect_horses_wrong_order'] += 1
    else:
        # 何頭合ってるか
        correct_horses = len(predicted_set & actual_set)
        if correct_horses == 2:
            failure_patterns['two_correct_horses'] += 1
        elif correct_horses == 1:
            failure_patterns['one_correct_horse'] += 1
        else:
            failure_patterns['all_wrong'] += 1

    # 予測馬の実際の着順を記録
    for h in horses:
        if h['umaban'] == pred_1st and pd.notna(h['actual_rank']):
            score_distributions['predicted_1st_actual_rank'].append(h['actual_rank'])
        if h['umaban'] == pred_2nd and pd.notna(h['actual_rank']):
            score_distributions['predicted_2nd_actual_rank'].append(h['actual_rank'])
        if h['umaban'] == pred_3rd and pd.notna(h['actual_rank']):
            score_distributions['predicted_3rd_actual_rank'].append(h['actual_rank'])

# 結果表示
print("\n" + "=" * 80)
print("【失敗パターン分析】")
print("=" * 80)

total = sum(failure_patterns.values())
print(f"\n分析レース数: {total}レース\n")

print("パターン別内訳:")
for pattern, count in failure_patterns.items():
    percentage = count / total * 100 if total > 0 else 0
    pattern_jp = {
        'perfect_match': '完全的中',
        'perfect_horses_wrong_order': '馬は合ってるが順番違い',
        'two_correct_horses': '2頭的中',
        'one_correct_horse': '1頭のみ的中',
        'all_wrong': '全部外れ'
    }
    print(f"  {pattern_jp[pattern]:20s}: {count:4d}回 ({percentage:5.1f}%)")

print("\n" + "=" * 80)
print("【位置別的中率】")
print("=" * 80)

for pos, count in position_accuracy.items():
    percentage = count / total * 100 if total > 0 else 0
    pos_jp = {'1st_correct': '1着', '2nd_correct': '2着', '3rd_correct': '3着'}
    print(f"  {pos_jp[pos]}が的中: {count:4d}回 ({percentage:5.1f}%)")

print("\n" + "=" * 80)
print("【予測馬の実際の着順分布】")
print("=" * 80)

for pred_pos, ranks in score_distributions.items():
    if ranks:
        avg_rank = np.mean(ranks)
        pos_jp = {
            'predicted_1st_actual_rank': '予測1位の馬',
            'predicted_2nd_actual_rank': '予測2位の馬',
            'predicted_3rd_actual_rank': '予測3位の馬'
        }
        print(f"\n{pos_jp[pred_pos]}:")
        print(f"  平均着順: {avg_rank:.2f}着")
        print(f"  着順分布: 1着={sum(1 for r in ranks if r==1)}回, "
              f"2着={sum(1 for r in ranks if r==2)}回, "
              f"3着={sum(1 for r in ranks if r==3)}回, "
              f"4着以下={sum(1 for r in ranks if r>=4)}回")

print("\n" + "=" * 80)
print("【改善の方向性】")
print("=" * 80)

perfect_horses = failure_patterns.get('perfect_horses_wrong_order', 0)
two_horses = failure_patterns.get('two_correct_horses', 0)

print("\n主要な問題点:")
if perfect_horses > 0:
    print(f"1. 馬の選定は正しいが順番が間違っている: {perfect_horses}回")
    print("   → 着順予測モデルの改善が必要")
    print("   → 2着・3着の特徴をより詳細に学習")

if two_horses > total * 0.3:
    print(f"\n2. 2頭は当たるが1頭外す: {two_horses}回 ({two_horses/total*100:.1f}%)")
    print("   → 3着圏内候補が広すぎる")
    print("   → より厳密な絞り込みロジックが必要")

print("\n" + "=" * 80)
print("分析完了")
print("=" * 80)
