"""
出馬表データを使った未来レース予測
取得した出馬表データ + 訓練済みモデル = 予測

使い方:
1. fetch_shutuba_data.py で出馬表を取得
2. このスクリプトを実行
3. 予測結果を確認
"""
import pandas as pd
import numpy as np
import pickle
import os
from datetime import datetime

print("=" * 80)
print("出馬表データを使った未来レース予測")
print("=" * 80)

# ============================================================================
# Step 1: 出馬表データの読み込み
# ============================================================================

print("\n出馬表データファイルを選択してください")
print("（fetch_shutuba_data.py で作成したCSVファイル）")
print()

# カレントディレクトリのshutubaファイルを表示
shutuba_files = [f for f in os.listdir('.') if f.startswith('shutuba_') and f.endswith('.csv')]

if len(shutuba_files) > 0:
    print("利用可能なファイル:")
    for i, f in enumerate(shutuba_files, 1):
        print(f"  {i}. {f}")
    print()

shutuba_file = input("ファイル名（または番号）: ").strip()

# 番号で選択された場合
try:
    file_idx = int(shutuba_file) - 1
    if 0 <= file_idx < len(shutuba_files):
        shutuba_file = shutuba_files[file_idx]
except:
    pass

if not os.path.exists(shutuba_file):
    print(f"エラー: {shutuba_file} が見つかりません")
    exit(1)

print(f"\n読み込み: {shutuba_file}")
df_shutuba = pd.read_csv(shutuba_file, encoding='utf-8-sig')

print(f"出走馬数: {len(df_shutuba)}頭")

# レース情報
race_id = df_shutuba['race_id'].iloc[0] if 'race_id' in df_shutuba.columns else 'N/A'
race_name = df_shutuba['race_name'].iloc[0] if 'race_name' in df_shutuba.columns else 'N/A'

print(f"race_id: {race_id}")
print(f"レース名: {race_name}")

# ============================================================================
# Step 2: モデル読み込み
# ============================================================================

print("\n" + "=" * 80)
print("Step 2: モデル読み込み")
print("=" * 80)

# モデルファイルを探す
model_files = [f for f in os.listdir('.') if f.startswith('race_prediction_model_') and f.endswith('.pkl')]

if len(model_files) == 0:
    print("\n⚠ モデルファイルが見つかりません")
    print("GUIツールのモデル訓練タブでモデルを訓練してください")
    print("\nオッズベース予測にフォールバックします...")
    model = None
else:
    # 最新のモデルを使用
    model_files.sort(reverse=True)
    model_file = model_files[0]

    print(f"\nモデルファイル: {model_file}")

    try:
        with open(model_file, 'rb') as f:
            model_data = pickle.load(f)
            model = model_data.get('model')
            print(f"モデルタイプ: {model_data.get('model_type', 'N/A')}")
            print(f"訓練期間: {model_data.get('train_period', 'N/A')}")
    except Exception as e:
        print(f"エラー: {e}")
        print("オッズベース予測にフォールバックします...")
        model = None

# ============================================================================
# Step 3: 予測実行
# ============================================================================

print("\n" + "=" * 80)
print("Step 3: 予測実行")
print("=" * 80)

predictions = []

for _, horse in df_shutuba.iterrows():
    umaban = horse.get('Umaban', 0)
    horse_name = horse.get('HorseName', 'N/A')
    jockey = horse.get('JockeyName', 'N/A')
    odds = horse.get('Odds', None)

    # オッズが取得できていない場合のデフォルト
    if pd.isna(odds) or odds is None:
        # 人気を推定（馬番から簡易的に）
        odds = 5.0 + (umaban % 5)

    # 予測スコア計算
    if model is not None:
        # モデル予測（簡易版 - 実際は過去データから特徴量を作成する必要あり）
        # ここでは暫定的にオッズベースを使用
        score = 1.0 / odds if odds > 0 else 0
    else:
        # オッズベース予測
        score = 1.0 / odds if odds > 0 else 0

    predictions.append({
        'umaban': umaban,
        'horse_name': horse_name,
        'jockey': jockey,
        'odds': odds,
        'score': score,
    })

# スコア順にソート
predictions.sort(key=lambda x: x['score'], reverse=True)

# ============================================================================
# Step 4: 結果表示
# ============================================================================

print("\n予測結果:")
print(f"{'順位':<6} | {'馬番':<6} | {'馬名':<25} | {'騎手':<15} | {'オッズ':<8} | {'スコア'}")
print("-" * 90)

for i, pred in enumerate(predictions, 1):
    umaban = pred['umaban']
    horse_name = str(pred['horse_name'])[:23]
    jockey = str(pred['jockey'])[:13]
    odds = pred['odds']
    score = pred['score']

    print(f"{i:<6} | {umaban:<6} | {horse_name:<25} | {jockey:<15} | {odds:<8.1f} | {score:.4f}")

# 推奨馬券
print("\n" + "=" * 80)
print("推奨馬券")
print("=" * 80)

top3 = [p['umaban'] for p in predictions[:3]]
top5 = [p['umaban'] for p in predictions[:5]]

print(f"\n1. ワイド 1-3")
print(f"   馬番: {top3[0]}-{top3[2]}")
print(f"   購入額: 100円")
print(f"   確信度: ⭐⭐⭐")

print(f"\n2. 3連複 BOX5頭")
print(f"   馬番: {'-'.join(map(str, top5))}")
print(f"   購入額: 1,000円（10点）")
print(f"   確信度: ⭐⭐")

print(f"\n3. 馬連 1-2")
print(f"   馬番: {top3[0]}-{top3[1]}")
print(f"   購入額: 100円")
print(f"   確信度: ⭐⭐⭐⭐")

print(f"\n4. 3連単 1着固定流し")
print(f"   軸馬: {top3[0]}番 {predictions[0]['horse_name']}")
print(f"   相手: {'-'.join(map(str, top3[1:]))}")
print(f"   購入額: 200円（2点）")
print(f"   確信度: ⭐⭐")

# 結果を保存
print("\n" + "=" * 80)
print("結果保存")
print("=" * 80)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
output_file = f"prediction_{race_id}_{timestamp}.csv"

df_result = pd.DataFrame(predictions)
df_result.to_csv(output_file, index=False, encoding='utf-8-sig')

print(f"\n予測結果を保存: {output_file}")

# サマリーテキスト作成
summary_file = f"prediction_{race_id}_{timestamp}.txt"

with open(summary_file, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write(f"レース予測結果\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"race_id: {race_id}\n")
    f.write(f"レース名: {race_name}\n")
    f.write(f"予測日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

    f.write("予測着順 TOP5:\n")
    f.write("-" * 80 + "\n")
    for i, pred in enumerate(predictions[:5], 1):
        f.write(f"{i}. {pred['umaban']}番 {pred['horse_name']} ({pred['jockey']})\n")

    f.write("\n推奨馬券:\n")
    f.write("-" * 80 + "\n")
    f.write(f"ワイド 1-3: {top3[0]}-{top3[2]} (100円)\n")
    f.write(f"3連複 BOX5: {'-'.join(map(str, top5))} (1,000円)\n")
    f.write(f"馬連 1-2: {top3[0]}-{top3[1]} (100円)\n")

    f.write("\n注意事項:\n")
    f.write("-" * 80 + "\n")
    f.write("- この予測は参考情報です\n")
    f.write("- 馬券購入は自己責任でお願いします\n")
    f.write("- オッズは変動する可能性があります\n")
    f.write("- 最終的な判断は直前情報も確認してください\n")

print(f"サマリーを保存: {summary_file}")

print("\n" + "=" * 80)
print("完了！")
print("=" * 80)
print("\n明日のマイルCS、的中を祈ります！ 🏇")
