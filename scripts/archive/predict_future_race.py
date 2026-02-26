"""
未来レース予測ツール
出馬表データから明日以降のレースを予測

使い方:
1. netkeibaで予測したいレースのrace_idを確認
2. このスクリプトを実行
3. race_idを入力
4. 出馬表データを自動取得（または手動入力）
5. 予測結果を表示
"""
import pandas as pd
import numpy as np
import pickle
import json
from datetime import datetime
from data_config import MAIN_CSV, MAIN_JSON

print("=" * 80)
print("未来レース予測ツール")
print("=" * 80)

# ============================================================================
# Step 1: race_id入力
# ============================================================================

print("\n予測したいレースのrace_idを入力してください")
print("（例: 202506030811 = 2025年11月23日 京都11R マイルCS）")
print()

race_id_input = input("race_id: ").strip()

if not race_id_input:
    print("エラー: race_idが入力されていません")
    exit(1)

try:
    race_id = int(race_id_input)
except:
    print("エラー: race_idは数字で入力してください")
    exit(1)

print(f"\nrace_id: {race_id}")

# ============================================================================
# Step 2: データ確認
# ============================================================================

print("\n" + "=" * 80)
print("Step 2: データ確認")
print("=" * 80)

# 既存データにあるか確認
df = pd.read_csv(MAIN_CSV, low_memory=False)
existing_race = df[df['race_id'] == race_id]

if len(existing_race) > 0:
    print(f"\n✓ このrace_idは既存データにあります（過去レース）")
    race_date = existing_race.iloc[0]['date']
    race_name = existing_race.iloc[0]['race_name']
    track_name = existing_race.iloc[0]['track_name']

    print(f"  レース名: {race_name}")
    print(f"  日付: {race_date}")
    print(f"  場所: {track_name}")

    print("\n既存データで予測します...")

    # 通常の予測処理（既存データ使用）
    # （keiba_analysis_tool.pyのロジックを流用）

else:
    print(f"\n⚠ このrace_idは既存データにありません（未来レース）")
    print("\n出馬表データが必要です")

    print("\n" + "=" * 80)
    print("未来レース予測の準備")
    print("=" * 80)

    print("""
未来レースを予測するには、以下の手順が必要です:

【方法A: 自動取得（推奨）】
1. netkeibaから出馬表データを自動スクレイピング
2. 特徴量を抽出
3. モデルで予測

【方法B: 手動入力】
1. netkeibaの出馬表ページを開く
2. 馬番、馬名、騎手、オッズなどを手動入力
3. モデルで予測

どちらの方法を使いますか？
A: 自動取得（実装必要）
B: 手動入力
Q: 終了
""")

    choice = input("選択 (A/B/Q): ").strip().upper()

    if choice == 'Q':
        print("終了します")
        exit(0)

    elif choice == 'A':
        print("\n【方法A: 自動取得】")
        print("=" * 80)
        print("""
出馬表データの自動取得機能を実装します。

必要な処理:
1. netkeibaの出馬表ページにアクセス
   URL: https://race.netkeiba.com/race/shutuba.html?race_id={race_id}

2. スクレイピングで以下を取得:
   - 馬番
   - 馬名
   - 性齢
   - 斤量
   - 騎手名
   - オッズ（前日オッズまたは当日オッズ）
   - 馬体重（発表後）

3. 過去レースデータから特徴量を補完:
   - 馬の過去成績
   - 騎手の勝率
   - 血統情報

4. 特徴量ベクトルを作成してモデルで予測

この機能を実装しますか？ (y/n): """)

        implement = input().strip().lower()

        if implement == 'y':
            print("\n出馬表スクレイピング機能を作成中...")
            print("→ fetch_shutuba_data.py を作成します")

            # 別スクリプトとして実装を提案
            print("""
次のステップ:
1. fetch_shutuba_data.py を実装
2. predict_future_race.py と統合
3. テスト実行

実装内容は以下を参照:
- 元のスクレイピングツールのロジック
- requests + BeautifulSoup
- selenium（動的コンテンツの場合）
""")

    elif choice == 'B':
        print("\n【方法B: 手動入力】")
        print("=" * 80)
        print("""
netkeibaの出馬表ページを開いてください:
https://race.netkeiba.com/race/shutuba.html?race_id={race_id}

以下の情報を入力してください:
""".format(race_id=race_id))

        horses = []

        print("\n出走馬の情報を入力（終了したら空欄でEnter）")

        while True:
            print(f"\n--- 馬 #{len(horses) + 1} ---")

            umaban = input("馬番: ").strip()
            if umaban == '':
                break

            horse_name = input("馬名: ").strip()
            jockey = input("騎手: ").strip()
            odds = input("オッズ: ").strip()
            ninki = input("人気（予想）: ").strip()
            age = input("年齢: ").strip()

            horses.append({
                'umaban': int(umaban) if umaban else 0,
                'horse_name': horse_name,
                'jockey': jockey,
                'odds': float(odds) if odds else 5.0,
                'ninki': int(ninki) if ninki else 5,
                'age': int(age) if age else 4,
            })

        if len(horses) == 0:
            print("\nエラー: 馬の情報が入力されていません")
            exit(1)

        print(f"\n{len(horses)}頭のデータを入力しました")

        # ============================================================================
        # Step 3: 予測実行
        # ============================================================================

        print("\n" + "=" * 80)
        print("Step 3: 予測実行")
        print("=" * 80)

        # 簡易予測（オッズベース）
        print("\n予測中...")

        for horse in horses:
            # オッズベーススコア
            horse['score'] = 1.0 / horse['odds'] if horse['odds'] > 0 else 0

        # スコア順にソート
        horses.sort(key=lambda x: x['score'], reverse=True)

        # 結果表示
        print("\n予測結果:")
        print(f"{'順位':<6} | {'馬番':<6} | {'馬名':<20} | {'騎手':<15} | {'人気':<6} | {'オッズ':<8}")
        print("-" * 80)

        for i, horse in enumerate(horses[:10], 1):
            print(f"{i:<6} | {horse['umaban']:<6} | {horse['horse_name']:<20} | {horse['jockey']:<15} | {horse['ninki']:<6} | {horse['odds']:<8.1f}")

        # 推奨馬券
        top3 = [h['umaban'] for h in horses[:3]]
        top5 = [h['umaban'] for h in horses[:5]]

        print("\n推奨馬券:")
        print(f"  ワイド: {top3[0]}-{top3[2]} (100円)")
        print(f"  3連複: BOX5頭 ({'-'.join(map(str, top5))}) (1,000円)")
        print(f"  馬連: {top3[0]}-{top3[1]} (100円)")

        # CSV保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_csv = f"future_prediction_{race_id}_{timestamp}.csv"

        df_result = pd.DataFrame(horses)
        df_result.to_csv(output_csv, index=False, encoding='utf-8-sig')

        print(f"\n結果を保存しました: {output_csv}")

print("\n" + "=" * 80)
print("完了")
print("=" * 80)
