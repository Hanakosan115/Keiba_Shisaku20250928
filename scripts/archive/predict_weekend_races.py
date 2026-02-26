"""
週末レース一括予測スクリプト
複数のrace_idを指定して一括で予測し、結果をCSVに出力
"""
import pandas as pd
import numpy as np
import pickle
import json
from datetime import datetime
from data_config import MAIN_CSV, MAIN_JSON

print("=" * 80)
print("週末レース一括予測ツール")
print("=" * 80)

# ============================================================================
# 設定
# ============================================================================

# 予測したいrace_idのリスト（ここを編集）
RACE_IDS = [
    # 例: 2024年12月1日の中京競馬場
    # 202406050201,
    # 202406050202,
    # 202406050203,
]

# モデルファイルのパス
MODEL_FILE = input("\nモデルファイルのパス（空欄でオッズベース予測）: ").strip().strip('"')

USE_MODEL = False
if MODEL_FILE and MODEL_FILE != '':
    if not MODEL_FILE.endswith('.pkl'):
        print("エラー: モデルファイルは .pkl 形式である必要があります")
        exit(1)
    USE_MODEL = True
    print(f"モデル使用: {MODEL_FILE}")
else:
    print("オッズベース予測を使用します")

# race_idの入力（対話形式）
print("\n予測したいrace_idを入力してください（完了したら空欄でEnter）")
race_ids_input = []
while True:
    race_id = input(f"race_id #{len(race_ids_input) + 1}: ").strip()
    if race_id == '':
        break
    try:
        race_ids_input.append(int(race_id))
    except:
        print("  エラー: 数字を入力してください")

if len(race_ids_input) > 0:
    RACE_IDS = race_ids_input

if len(RACE_IDS) == 0:
    print("\nrace_idが指定されていません。スクリプトを編集してRACE_IDSを設定してください。")
    exit(0)

print(f"\n予測対象: {len(RACE_IDS)}レース")

# ============================================================================
# データ読み込み
# ============================================================================

print("\n" + "=" * 80)
print("データ読み込み")
print("=" * 80)

print(f"\nCSV読み込み: {MAIN_CSV}")
df = pd.read_csv(MAIN_CSV, low_memory=False)
print(f"  総行数: {len(df):,}")

print(f"\nJSON読み込み: {MAIN_JSON}")
with open(MAIN_JSON, 'r', encoding='utf-8') as f:
    payouts_data = json.load(f)
print(f"  レース数: {len(payouts_data):,}")

# モデル読み込み
model = None
if USE_MODEL:
    print(f"\nモデル読み込み: {MODEL_FILE}")
    try:
        with open(MODEL_FILE, 'rb') as f:
            model_data = pickle.load(f)
            model = model_data['model']
            print(f"  モデルタイプ: {model_data.get('model_type', 'N/A')}")
            print(f"  訓練期間: {model_data.get('train_period', 'N/A')}")
    except Exception as e:
        print(f"  エラー: {e}")
        print("  オッズベース予測にフォールバック")
        USE_MODEL = False

# ============================================================================
# 予測実行
# ============================================================================

print("\n" + "=" * 80)
print("予測実行")
print("=" * 80)

results = []

for idx, race_id in enumerate(RACE_IDS, 1):
    print(f"\n[{idx}/{len(RACE_IDS)}] race_id: {race_id}")

    # レースデータ取得
    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) == 0:
        print(f"  エラー: race_id {race_id} が見つかりません")
        continue

    print(f"  出走頭数: {len(race_horses)}頭")

    # レース情報
    race_info_row = race_horses.iloc[0]
    race_name = race_info_row.get('race_name', 'N/A')
    race_date = race_info_row.get('date', 'N/A')
    track_name = race_info_row.get('track_name', 'N/A')
    distance = race_info_row.get('distance', 'N/A')

    print(f"  レース名: {race_name}")
    print(f"  日付: {race_date}")
    print(f"  場所: {track_name}")
    print(f"  距離: {distance}m")

    # 予測
    predictions = []
    for _, horse in race_horses.iterrows():
        umaban = horse.get('Umaban', 0)
        horse_name = horse.get('HorseName', 'N/A')
        jockey = horse.get('JockeyName', 'N/A')
        odds = horse.get('Odds', 10.0)
        ninki = horse.get('Ninki', 8)

        if USE_MODEL:
            # モデル予測（簡易版 - 実際の特徴量エンジニアリングが必要）
            age = horse.get('Age', 4)
            weight_diff = horse.get('WeightDiff', 0)
            feature_vector = [
                age if pd.notna(age) else 4,
                weight_diff if pd.notna(weight_diff) else 0,
                np.log1p(odds) if pd.notna(odds) and odds > 0 else 2,
                ninki if pd.notna(ninki) else 8,
            ]
            # モデルで予測（ここは簡易版）
            score = 1.0 / odds  # 暫定的にオッズベース
        else:
            # オッズベース予測
            score = 1.0 / odds if pd.notna(odds) and odds > 0 else 0

        predictions.append({
            'umaban': umaban,
            'horse_name': horse_name,
            'jockey': jockey,
            'odds': odds,
            'ninki': ninki,
            'score': score,
            'actual_rank': horse.get('Rank', None)
        })

    # スコア順にソート
    predictions.sort(key=lambda x: x['score'], reverse=True)

    # 推奨馬券生成
    top3_umaban = [p['umaban'] for p in predictions[:3]]
    top5_umaban = [p['umaban'] for p in predictions[:5]]

    recommendation_wide = f"{top3_umaban[0]}-{top3_umaban[2]}"
    recommendation_trio = f"BOX5頭 ({'-'.join(map(str, top5_umaban))})"
    recommendation_umaren = f"{top3_umaban[0]}-{top3_umaban[1]}"

    print(f"  予測着順（TOP3）: {top3_umaban[0]}番 → {top3_umaban[1]}番 → {top3_umaban[2]}番")
    print(f"  推奨ワイド: {recommendation_wide}")
    print(f"  推奨3連複: {recommendation_trio}")

    # 結果記録
    result = {
        'race_id': race_id,
        'race_name': race_name,
        'race_date': race_date,
        'track_name': track_name,
        'distance': distance,
        'horse_count': len(race_horses),
        'pred_1st': top3_umaban[0],
        'pred_2nd': top3_umaban[1],
        'pred_3rd': top3_umaban[2],
        'pred_1st_name': predictions[0]['horse_name'],
        'pred_2nd_name': predictions[1]['horse_name'],
        'pred_3rd_name': predictions[2]['horse_name'],
        'pred_1st_odds': predictions[0]['odds'],
        'recommendation_wide': recommendation_wide,
        'recommendation_trio': recommendation_trio,
        'recommendation_umaren': recommendation_umaren,
    }

    # 実際の結果があれば追加
    if pd.notna(predictions[0]['actual_rank']):
        actual_ranks = [(p['umaban'], p['actual_rank']) for p in predictions if pd.notna(p['actual_rank'])]
        actual_ranks.sort(key=lambda x: x[1])
        if len(actual_ranks) >= 3:
            result['actual_1st'] = actual_ranks[0][0]
            result['actual_2nd'] = actual_ranks[1][0]
            result['actual_3rd'] = actual_ranks[2][0]
            result['hit_1st'] = (top3_umaban[0] == actual_ranks[0][0])
            result['hit_3rd'] = (top3_umaban[0] in [r[0] for r in actual_ranks[:3]])

    results.append(result)

# ============================================================================
# 結果の出力
# ============================================================================

print("\n" + "=" * 80)
print("結果の保存")
print("=" * 80)

# DataFrameに変換
df_results = pd.DataFrame(results)

# CSV出力
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_csv = f"weekend_predictions_{timestamp}.csv"
df_results.to_csv(output_csv, index=False, encoding='utf-8-sig')
print(f"\nCSV保存: {output_csv}")

# サマリー表示
print("\n" + "=" * 80)
print("予測サマリー")
print("=" * 80)

print(f"\n{'race_id':<15} | {'レース名':<30} | {'日付':<12} | {'予測TOP3'}")
print("-" * 100)
for _, row in df_results.iterrows():
    race_id = str(row['race_id'])
    race_name = str(row['race_name'])[:28]
    race_date = str(row['race_date'])
    pred_top3 = f"{row['pred_1st']}-{row['pred_2nd']}-{row['pred_3rd']}"
    print(f"{race_id:<15} | {race_name:<30} | {race_date:<12} | {pred_top3}")

# 的中率（実データがある場合のみ）
if 'hit_1st' in df_results.columns:
    hit_1st_count = df_results['hit_1st'].sum()
    hit_3rd_count = df_results['hit_3rd'].sum()
    total = len(df_results)

    print("\n" + "=" * 80)
    print("的中率（実データとの比較）")
    print("=" * 80)
    print(f"\n1着的中: {hit_1st_count}/{total} ({hit_1st_count/total*100:.1f}%)")
    print(f"3着以内的中: {hit_3rd_count}/{total} ({hit_3rd_count/total*100:.1f}%)")

print("\n" + "=" * 80)
print("完了！")
print("=" * 80)
print(f"\n結果ファイル: {output_csv}")
print("\n推奨馬券は目安です。実際の購入は自己責任でお願いします。")
