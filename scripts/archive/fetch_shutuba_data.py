"""
出馬表データ取得ツール
netkeibaから未来レースの出馬表を取得

必要なライブラリ:
pip install requests beautifulsoup4 lxml
"""
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
from datetime import datetime

def fetch_shutuba(race_id):
    """
    netkeibaから出馬表データを取得

    Args:
        race_id: レースID（例: 202506030811）

    Returns:
        DataFrame: 出馬表データ
    """
    url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"

    print(f"出馬表を取得中: {url}")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        print(f"ステータス: {response.status_code}")

        # HTMLをパース
        soup = BeautifulSoup(response.content, 'lxml')

        # レース情報を取得
        race_info = {}

        # レース名
        race_title = soup.find('div', class_='RaceName')
        if race_title:
            race_info['race_name'] = race_title.get_text(strip=True)

        # 開催情報
        race_data = soup.find('div', class_='RaceData01')
        if race_data:
            race_info['race_details'] = race_data.get_text(strip=True)

        print(f"\nレース名: {race_info.get('race_name', 'N/A')}")
        print(f"詳細: {race_info.get('race_details', 'N/A')}")

        # 出走馬テーブルを取得
        table = soup.find('table', class_='Shutuba_Table')

        if not table:
            print("エラー: 出馬表が見つかりません")
            print("可能性:")
            print("  - race_idが間違っている")
            print("  - レースがまだ確定していない")
            print("  - ページ構造が変更された")
            return None

        # テーブルをパース
        horses = []

        rows = table.find_all('tr')

        for row in rows[1:]:  # ヘッダーをスキップ
            cols = row.find_all('td')

            if len(cols) < 10:
                continue

            try:
                # 馬番
                umaban_tag = cols[0].find('div', class_='Umaban')
                umaban = int(umaban_tag.get_text(strip=True)) if umaban_tag else 0

                # 馬名
                horse_name_tag = cols[3].find('a')
                horse_name = horse_name_tag.get_text(strip=True) if horse_name_tag else 'N/A'

                # 性齢
                sex_age_tag = cols[4]
                sex_age = sex_age_tag.get_text(strip=True) if sex_age_tag else 'N/A'

                # 斤量
                weight_tag = cols[5]
                weight = weight_tag.get_text(strip=True) if weight_tag else '0'

                # 騎手
                jockey_tag = cols[6].find('a')
                jockey = jockey_tag.get_text(strip=True) if jockey_tag else 'N/A'

                # オッズ（存在する場合）
                odds_tag = cols[9] if len(cols) > 9 else None
                odds_text = odds_tag.get_text(strip=True) if odds_tag else ''

                try:
                    odds = float(odds_text) if odds_text else None
                except:
                    odds = None

                # 馬体重（発表後のみ）
                horse_weight_tag = cols[8] if len(cols) > 8 else None
                horse_weight = horse_weight_tag.get_text(strip=True) if horse_weight_tag else 'N/A'

                horses.append({
                    'race_id': race_id,
                    'Umaban': umaban,
                    'HorseName': horse_name,
                    'SexAge': sex_age,
                    'Load': weight,
                    'JockeyName': jockey,
                    'Odds': odds,
                    'WeightInfo': horse_weight,
                })

            except Exception as e:
                print(f"行のパースエラー: {e}")
                continue

        if len(horses) == 0:
            print("エラー: 馬データを抽出できませんでした")
            return None

        print(f"\n{len(horses)}頭の出走馬データを取得しました")

        # DataFrameに変換
        df = pd.DataFrame(horses)

        # レース情報を追加
        for key, value in race_info.items():
            df[key] = value

        return df

    except requests.exceptions.RequestException as e:
        print(f"エラー: {e}")
        return None

def save_shutuba_data(df, race_id):
    """
    出馬表データをCSV保存
    """
    if df is None or len(df) == 0:
        print("保存するデータがありません")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"shutuba_{race_id}_{timestamp}.csv"

    df.to_csv(filename, index=False, encoding='utf-8-sig')
    print(f"\n保存完了: {filename}")

    return filename

# ============================================================================
# メイン処理
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("出馬表データ取得ツール")
    print("=" * 80)

    print("\n取得したいレースのrace_idを入力してください")
    print("（例: 202506030811 = 2025年11月23日 京都11R マイルCS）")
    print()

    race_id_input = input("race_id: ").strip()

    if not race_id_input:
        print("終了します")
        exit(0)

    try:
        race_id = int(race_id_input)
    except:
        print("エラー: race_idは数字で入力してください")
        exit(1)

    # 出馬表を取得
    df = fetch_shutuba(race_id)

    if df is not None:
        # プレビュー表示
        print("\n" + "=" * 80)
        print("取得データプレビュー")
        print("=" * 80)
        print(df[['Umaban', 'HorseName', 'JockeyName', 'Odds']].to_string())

        # 保存
        save_shutuba_data(df, race_id)

        print("\n" + "=" * 80)
        print("次のステップ")
        print("=" * 80)
        print("""
このデータを使って予測を実行:
1. predict_with_shutuba.py を実行
2. 保存したCSVファイルを読み込み
3. モデルで予測
""")
    else:
        print("\nデータ取得に失敗しました")
        print("\n手動入力で予測する場合:")
        print("  python predict_future_race.py")
