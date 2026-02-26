"""
競馬予想ツール - シンプル版

目的: 明日のレースを予想してプラス収支を作る

使い方:
  python yosou.py 202506030811

たったこれだけ！
"""
import sys
import pandas as pd
import numpy as np
import pickle
import os
from datetime import datetime
from data_config import MAIN_CSV

def load_model():
    """モデルを読み込む（なければオッズベース）"""
    model_files = [f for f in os.listdir('.') if f.startswith('race_prediction_model_') and f.endswith('.pkl')]

    if len(model_files) == 0:
        print("⚠ モデル未訓練 → オッズベース予測を使用")
        return None

    model_files.sort(reverse=True)
    model_file = model_files[0]

    try:
        with open(model_file, 'rb') as f:
            model_data = pickle.load(f)
            return model_data.get('model')
    except:
        return None

def get_race_data(race_id):
    """レースデータを取得（既存データまたは出馬表）"""
    # 既存データから探す
    df = pd.read_csv(MAIN_CSV, low_memory=False)
    race_data = df[df['race_id'] == race_id]

    if len(race_data) > 0:
        return race_data, 'past'

    # 未来レース → 出馬表を取得
    print(f"\n未来レースです。出馬表を取得します...")

    try:
        import requests
        from bs4 import BeautifulSoup

        url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.content, 'lxml')

        # レース名
        race_title = soup.find('div', class_='RaceName')
        race_name = race_title.get_text(strip=True) if race_title else 'N/A'

        # 出走馬テーブル
        table = soup.find('table', class_='Shutuba_Table')

        if not table:
            print("❌ 出馬表が見つかりません")
            print("   手動入力モードに切り替えます")
            return manual_input_mode(), 'manual'

        horses = []
        rows = table.find_all('tr')

        for row in rows[1:]:
            cols = row.find_all('td')
            if len(cols) < 10:
                continue

            try:
                umaban = int(cols[0].get_text(strip=True))
                horse_name = cols[3].get_text(strip=True)
                jockey = cols[6].get_text(strip=True)
                odds_text = cols[9].get_text(strip=True) if len(cols) > 9 else ''

                try:
                    odds = float(odds_text)
                except:
                    odds = 5.0 + (umaban % 5)  # デフォルト

                horses.append({
                    'race_id': race_id,
                    'Umaban': umaban,
                    'HorseName': horse_name,
                    'JockeyName': jockey,
                    'Odds': odds,
                    'race_name': race_name,
                })
            except:
                continue

        if len(horses) == 0:
            print("❌ データ抽出失敗")
            return manual_input_mode(), 'manual'

        print(f"✓ 出馬表取得成功: {len(horses)}頭")
        return pd.DataFrame(horses), 'future'

    except ImportError:
        print("⚠ requests/beautifulsoup4 が必要です")
        print("  pip install requests beautifulsoup4 lxml")
        print("\n手動入力モードに切り替えます")
        return manual_input_mode(), 'manual'
    except Exception as e:
        print(f"❌ エラー: {e}")
        print("手動入力モードに切り替えます")
        return manual_input_mode(), 'manual'

def manual_input_mode():
    """手動入力モード"""
    print("\n=== 手動入力モード ===")
    print("出走馬の情報を入力してください（終了: 空欄でEnter）\n")

    horses = []

    while True:
        print(f"--- 馬 #{len(horses) + 1} ---")
        umaban = input("馬番: ").strip()
        if umaban == '':
            break

        horse_name = input("馬名: ").strip()
        jockey = input("騎手: ").strip()
        odds = input("オッズ: ").strip()

        horses.append({
            'Umaban': int(umaban),
            'HorseName': horse_name,
            'JockeyName': jockey,
            'Odds': float(odds) if odds else 5.0,
        })

    return pd.DataFrame(horses)

def predict(race_data, model=None):
    """予測を実行"""
    predictions = []

    for _, horse in race_data.iterrows():
        umaban = horse.get('Umaban', 0)
        horse_name = horse.get('HorseName', 'N/A')
        jockey = horse.get('JockeyName', 'N/A')
        odds = horse.get('Odds', 5.0)

        # スコア計算（オッズベース）
        score = 1.0 / odds if odds > 0 else 0

        predictions.append({
            'umaban': umaban,
            'horse_name': horse_name,
            'jockey': jockey,
            'odds': odds,
            'score': score,
        })

    # ソート
    predictions.sort(key=lambda x: x['score'], reverse=True)

    return predictions

def display_results(predictions, race_name='N/A'):
    """結果を表示"""
    print("\n" + "=" * 80)
    print(f"予想結果: {race_name}")
    print("=" * 80)

    print(f"\n{'順位':<6} | {'馬番':<6} | {'馬名':<25} | {'騎手':<15} | {'オッズ':<8}")
    print("-" * 80)

    for i, pred in enumerate(predictions[:10], 1):
        print(f"{i:<6} | {pred['umaban']:<6} | {pred['horse_name']:<25} | {pred['jockey']:<15} | {pred['odds']:<8.1f}")

    # 推奨馬券
    top3 = [p['umaban'] for p in predictions[:3]]
    top5 = [p['umaban'] for p in predictions[:5]]

    print("\n" + "=" * 80)
    print("推奨馬券")
    print("=" * 80)

    print(f"\n1. ワイド: {top3[0]}-{top3[2]} (100円)")
    print(f"2. 3連複 BOX5: {'-'.join(map(str, top5))} (1,000円)")
    print(f"3. 馬連: {top3[0]}-{top3[1]} (100円)")

    total_cost = 100 + 1000 + 100
    print(f"\n合計購入額: {total_cost:,}円")

    print("\n" + "=" * 80)

def main():
    """メイン処理"""
    print("=" * 80)
    print("競馬予想ツール")
    print("=" * 80)

    # race_id取得
    if len(sys.argv) > 1:
        race_id_input = sys.argv[1]
    else:
        print("\n予想したいレースのrace_idを入力:")
        print("（例: 202506030811 = 明日のマイルCS）")
        race_id_input = input("\nrace_id: ").strip()

    if not race_id_input:
        print("終了します")
        return

    try:
        race_id = int(race_id_input)
    except:
        print("エラー: race_idは数字で入力してください")
        return

    print(f"\nrace_id: {race_id}")

    # モデル読み込み
    model = load_model()

    # レースデータ取得
    race_data, data_type = get_race_data(race_id)

    if race_data is None or len(race_data) == 0:
        print("エラー: データが取得できませんでした")
        return

    race_name = race_data.iloc[0].get('race_name', 'N/A') if 'race_name' in race_data.columns else 'N/A'

    if data_type == 'past':
        print(f"✓ 過去レースです: {race_name}")
        race_date = race_data.iloc[0].get('date', 'N/A')
        print(f"  日付: {race_date}")

    # 予測
    print("\n予測中...")
    predictions = predict(race_data, model)

    # 結果表示
    display_results(predictions, race_name)

    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"yosou_{race_id}_{timestamp}.txt"

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"レース予想結果\n")
        f.write(f"race_id: {race_id}\n")
        f.write(f"レース名: {race_name}\n\n")
        f.write(f"予想着順:\n")
        for i, pred in enumerate(predictions[:5], 1):
            f.write(f"{i}. {pred['umaban']}番 {pred['horse_name']} ({pred['jockey']})\n")

        top3 = [p['umaban'] for p in predictions[:3]]
        top5 = [p['umaban'] for p in predictions[:5]]

        f.write(f"\n推奨馬券:\n")
        f.write(f"ワイド: {top3[0]}-{top3[2]} (100円)\n")
        f.write(f"3連複 BOX5: {'-'.join(map(str, top5))} (1,000円)\n")
        f.write(f"馬連: {top3[0]}-{top3[1]} (100円)\n")

    print(f"\n結果保存: {output_file}")
    print("\n的中を祈ります！ 🏇")

if __name__ == "__main__":
    main()
