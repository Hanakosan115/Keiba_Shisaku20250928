"""
テスト予測（2024年12月のレース）
"""
import pandas as pd
import numpy as np
import json
from data_config import MAIN_CSV, MAIN_JSON

# 予測対象のrace_id（興味深いレースを選択）
RACE_IDS = [
    202406050209,  # 栄進ステークス(3勝)
    202406050210,  # 浜松ステークス(3勝)
    202406050211,  # 中京記念グランシャリオS(L)
]

print("=" * 80)
print("レース予測テスト")
print("=" * 80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(MAIN_CSV, low_memory=False)
with open(MAIN_JSON, 'r', encoding='utf-8') as f:
    payouts_data = json.load(f)

results = []

for idx, race_id in enumerate(RACE_IDS, 1):
    print(f"\n{'=' * 80}")
    print(f"[{idx}/{len(RACE_IDS)}] race_id: {race_id}")
    print("=" * 80)

    # レースデータ取得
    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) == 0:
        print(f"エラー: race_id {race_id} が見つかりません")
        continue

    # レース情報
    race_info_row = race_horses.iloc[0]
    race_name = race_info_row.get('race_name', 'N/A')
    race_date = race_info_row.get('date', 'N/A')
    track_name = race_info_row.get('track_name', 'N/A')
    distance = race_info_row.get('distance', 'N/A')

    print(f"\nレース名: {race_name}")
    print(f"日付: {race_date}")
    print(f"場所: {track_name}")
    print(f"距離: {distance}m")
    print(f"出走頭数: {len(race_horses)}頭")

    # 予測（オッズベース）
    predictions = []
    for _, horse in race_horses.iterrows():
        umaban = horse.get('Umaban', 0)
        horse_name = horse.get('HorseName', 'N/A')
        jockey = horse.get('JockeyName', 'N/A')
        odds = horse.get('Odds', 10.0)
        ninki = horse.get('Ninki', 8)
        actual_rank = horse.get('Rank', None)

        # オッズベース予測スコア
        score = 1.0 / odds if pd.notna(odds) and odds > 0 else 0

        predictions.append({
            'umaban': umaban,
            'horse_name': horse_name,
            'jockey': jockey,
            'odds': odds,
            'ninki': ninki,
            'score': score,
            'actual_rank': actual_rank
        })

    # スコア順にソート
    predictions.sort(key=lambda x: x['score'], reverse=True)

    # TOP5を表示
    print(f"\n予測着順（TOP5）:")
    print(f"{'順位':<6} | {'馬番':<6} | {'馬名':<20} | {'騎手':<15} | {'人気':<6} | {'オッズ':<8} | {'実際'}")
    print("-" * 80)

    for i, p in enumerate(predictions[:5], 1):
        umaban = p['umaban']
        horse_name = str(p['horse_name'])[:18]
        jockey = str(p['jockey'])[:13]
        ninki = p['ninki']
        odds = p['odds']
        actual = f"{p['actual_rank']}着" if pd.notna(p['actual_rank']) else 'N/A'

        print(f"{i:<6} | {umaban:<6} | {horse_name:<20} | {jockey:<15} | {ninki:<6} | {odds:<8.1f} | {actual}")

    # 推奨馬券
    top3_umaban = [p['umaban'] for p in predictions[:3]]
    top5_umaban = [p['umaban'] for p in predictions[:5]]

    print(f"\n推奨馬券:")
    print(f"  ワイド: {top3_umaban[0]}-{top3_umaban[2]} (100円)")
    print(f"  3連複: BOX5頭 ({'-'.join(map(str, top5_umaban))}) (1,000円)")
    print(f"  馬連: {top3_umaban[0]}-{top3_umaban[1]} (100円)")

    # 的中判定
    if pd.notna(predictions[0]['actual_rank']):
        print(f"\n的中判定:")

        # 実際の着順を取得
        actual_results = [(p['umaban'], p['actual_rank']) for p in predictions if pd.notna(p['actual_rank'])]
        actual_results.sort(key=lambda x: x[1])

        if len(actual_results) >= 3:
            actual_1st = actual_results[0][0]
            actual_2nd = actual_results[1][0]
            actual_3rd = actual_results[2][0]

            print(f"  実際の結果: {actual_1st}着 → {actual_2nd}着 → {actual_3rd}着")

            # 1着的中
            if top3_umaban[0] == actual_1st:
                print(f"  [O] 1着的中！ ({top3_umaban[0]}番)")
            else:
                print(f"  [X] 1着外れ（予測: {top3_umaban[0]}番 → 実際: {actual_1st}番）")

            # ワイド1-3
            wide_pred = set([top3_umaban[0], top3_umaban[2]])
            wide_actual_candidates = [
                set([actual_1st, actual_2nd]),
                set([actual_1st, actual_3rd]),
                set([actual_2nd, actual_3rd])
            ]
            if wide_pred in wide_actual_candidates:
                print(f"  [O] ワイド1-3 的中！")
            else:
                print(f"  [X] ワイド1-3 外れ")

            # 3連複BOX5頭
            box5_pred = set(top5_umaban)
            actual_top3 = set([actual_1st, actual_2nd, actual_3rd])
            if actual_top3.issubset(box5_pred):
                print(f"  [O] 3連複BOX5頭 的中！")
            else:
                print(f"  [X] 3連複BOX5頭 外れ")

            # 払戻金額（JSONから取得）
            race_id_str = str(race_id)
            if race_id_str in payouts_data:
                payout_info = payouts_data[race_id_str]
                print(f"\n  払戻情報:")

                if 'ワイド' in payout_info:
                    for wide_combo, payout in payout_info['ワイド'].items():
                        print(f"    ワイド {wide_combo}: {payout}円")

                if '3連複' in payout_info:
                    for trio_combo, payout in payout_info['3連複'].items():
                        print(f"    3連複 {trio_combo}: {payout}円")

print("\n" + "=" * 80)
print("テスト完了！")
print("=" * 80)
print("\nGUIツールを使えばもっと簡単に予測できます！")
print("→ python keiba_analysis_tool.py")
