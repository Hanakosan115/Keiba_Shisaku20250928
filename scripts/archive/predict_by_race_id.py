"""
レースID直接指定予想ツール
週末レース一覧が取得できない場合の代替手段
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import pickle
from value_betting_module import ValueBettingAnalyzer
import re

class DirectRacePredictor:
    """レースID直接指定の予想クラス"""

    def __init__(self, model_path='lgbm_model_hybrid.pkl'):
        # モデル読み込み
        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            print(f"[OK] モデル読み込み完了")
        except:
            print("[NG] モデルが見つかりません（オッズベース予想を使用します）")
            self.model = None

        self.session = requests.Session()
        self.value_analyzer = ValueBettingAnalyzer(value_threshold=0.05)

    def get_race_shutuba(self, race_id):
        """出馬表を取得"""
        url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"

        try:
            response = self.session.get(url, timeout=10)
            response.encoding = 'EUC-JP'
            soup = BeautifulSoup(response.content, 'html.parser')

            # レース情報
            race_name_elem = soup.select_one('.RaceName')
            race_name = race_name_elem.text.strip() if race_name_elem else 'N/A'

            race_data_elem = soup.select_one('.RaceData01')
            race_data_text = race_data_elem.text.strip() if race_data_elem else ''

            # 距離
            distance_match = re.search(r'(\d+)m', race_data_text)
            distance = int(distance_match.group(1)) if distance_match else 1600

            # 出馬表テーブル
            shutuba_table = soup.select_one('.Shutuba_Table')

            if not shutuba_table:
                return None, None

            horses_data = []
            rows = shutuba_table.select('tr.HorseList')

            for row in rows:
                # 馬番
                umaban_elem = row.select_one('.Umaban')
                umaban = int(umaban_elem.text.strip()) if umaban_elem else None

                # 馬名
                horse_name_elem = row.select_one('.Horse_Name a')
                horse_name = horse_name_elem.text.strip() if horse_name_elem else 'N/A'

                # オッズ
                odds_elem = row.select_one('.Popular')
                odds_text = odds_elem.text.strip() if odds_elem else None
                try:
                    odds = float(odds_text) if odds_text and odds_text != '-' else 10.0
                except:
                    odds = 10.0

                # 騎手
                jockey_elem = row.select_one('.Jockey a')
                jockey_name = jockey_elem.text.strip() if jockey_elem else 'N/A'

                horses_data.append({
                    'Umaban': umaban,
                    'HorseName': horse_name,
                    'Odds': odds,
                    'JockeyName': jockey_name
                })

            race_info = {
                'race_name': race_name,
                'distance': distance
            }

            return pd.DataFrame(horses_data), race_info

        except Exception as e:
            print(f"エラー: {e}")
            return None, None

    def get_race_result(self, race_id):
        """レース結果から取得（過去レース用）"""
        url = f"https://db.netkeiba.com/race/{race_id}/"

        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None, None

            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.content, 'html.parser')

            # レース名
            race_name_elem = soup.find('h1', class_='raceTitle')
            race_name = race_name_elem.text.strip() if race_name_elem else 'N/A'

            # レースデータ
            race_data_elem = soup.find('div', class_='racedata')
            if not race_data_elem:
                race_data_elem = soup.find('p', class_='smalltxt')
            race_data_text = race_data_elem.text.strip() if race_data_elem else ''

            # 距離
            distance_match = re.search(r'(\d+)m', race_data_text)
            distance = int(distance_match.group(1)) if distance_match else 1600

            # 結果テーブル
            result_table = soup.find('table', class_='race_table_01')
            if not result_table:
                return None, None

            horses_data = []
            rows = result_table.find_all('tr')[1:]  # ヘッダー除く

            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 13:
                    continue

                try:
                    # 馬番
                    umaban = int(cols[2].text.strip())

                    # 馬名
                    horse_elem = cols[4].find('a')
                    horse_name = horse_elem.text.strip() if horse_elem else cols[4].text.strip()

                    # 騎手
                    jockey_elem = cols[7].find('a')
                    jockey_name = jockey_elem.text.strip() if jockey_elem else cols[7].text.strip()

                    # オッズ
                    try:
                        odds = float(cols[12].text.strip())
                    except:
                        odds = 5.0

                    horses_data.append({
                        'Umaban': umaban,
                        'HorseName': horse_name,
                        'Odds': odds,
                        'JockeyName': jockey_name
                    })

                except (ValueError, IndexError):
                    continue

            race_info = {
                'race_name': race_name,
                'distance': distance
            }

            return pd.DataFrame(horses_data), race_info

        except Exception as e:
            return None, None

    def predict_race(self, race_id, budget=10000):
        """レースを予想"""
        print(f"\n{'='*80}")
        print(f"レースID: {race_id}")
        print("="*80)

        # まず出馬表を試す
        horses_df, race_info = self.get_race_shutuba(race_id)

        # 出馬表が取得できなければ結果ページを試す（過去レース）
        if horses_df is None:
            print("出馬表が見つかりません... 過去レース結果を確認中...")
            horses_df, race_info = self.get_race_result(race_id)

            if horses_df is None:
                print("\n[エラー] レース情報が取得できませんでした")
                print("\n考えられる原因:")
                print("  1. レースIDが間違っている")
                print("  2. まだ出馬表が公開されていない（未来のレース）")
                print("  3. レースが存在しない")
                print("\nヒント:")
                print("  - 出馬表: レース当日の朝9時頃公開")
                print("  - 過去レース: 結果が公開されているはず")
                return None
            else:
                print("[OK] 過去レース結果から取得しました")

        print(f"レース: {race_info['race_name']}")
        print(f"距離: {race_info['distance']}m")
        print(f"出走: {len(horses_df)}頭")

        # 簡易予測（オッズベース）
        for idx, row in horses_df.iterrows():
            horses_df.at[idx, 'score'] = 1.0 / row['Odds']

        scores = horses_df['score'].values
        sorted_indices = np.argsort(scores)[::-1]
        ranks = np.empty(len(scores))
        ranks[sorted_indices] = np.arange(1, len(scores) + 1)

        horses_df['predicted_rank'] = ranks

        # Value分析
        horses_data = []
        for idx, row in horses_df.iterrows():
            horses_data.append({
                'umaban': row['Umaban'],
                'horse_name': row['HorseName'],
                'odds': row['Odds'],
                'predicted_rank': row['predicted_rank'],
                'score': row['score'],
                'jockey': row['JockeyName']
            })

        predicted_ranks = [h['predicted_rank'] for h in horses_data]
        odds_list = [h['odds'] for h in horses_data]

        values = self.value_analyzer.calculate_values(predicted_ranks, odds_list)

        for i, h in enumerate(horses_data):
            h.update(values[i])

        # 推奨ベット
        recommendations = self.value_analyzer.recommend_bets(horses_data, budget=budget)

        # 結果表示
        print("\n" + "-"*80)
        print("予想結果（上位5頭）")
        print("-"*80)
        print(f"{'順位':^6} {'馬番':^6} {'馬名':^20} {'騎手':^12} {'オッズ':^8} {'Value':^10}")
        print("-"*80)

        horses_sorted = sorted(horses_data, key=lambda x: x['predicted_rank'])
        for i, h in enumerate(horses_sorted[:5], 1):
            print(f"{i:^6} {h['umaban']:^6} {h['horse_name'][:20]:^20} {h['jockey'][:12]:^12} {h['odds']:^8.1f} {h['value']*100:^+9.2f}%")

        # 推奨ベット
        print("\n" + self.value_analyzer.format_recommendation(recommendations))

        return {
            'race_id': race_id,
            'race_info': race_info,
            'horses': horses_data,
            'recommendations': recommendations
        }

def main():
    """メイン処理"""
    print("="*80)
    print("レースID直接指定予想ツール")
    print("="*80)

    predictor = DirectRacePredictor()

    print("\n使い方:")
    print("  1. netkeibaで今週末のレースを探す")
    print("  2. レースページのURLから12桁のrace_idをコピー")
    print("     例: https://race.netkeiba.com/race/shutuba.html?race_id=202412010811")
    print("         → race_id = 202412010811")
    print()

    print("【参考】よく使われる競馬場コード:")
    print("  05: 東京  06: 中山  07: 中京")
    print("  09: 阪神  10: 福島  01: 札幌")
    print()

    race_id_input = input("レースIDを入力（12桁、複数の場合はカンマ区切り）: ").strip()

    if not race_id_input:
        print("\n入力がありません")
        return

    # 複数レース対応
    race_ids = [rid.strip() for rid in race_id_input.split(',')]

    # 予算
    budget_input = input("\n予算を入力してください（デフォルト: 10000円）: ").strip()
    budget = int(budget_input) if budget_input.isdigit() else 10000

    # 予想実行
    results = []
    for race_id in race_ids:
        if len(race_id) != 12 or not race_id.isdigit():
            print(f"\n[スキップ] 無効なレースID: {race_id}")
            continue

        result = predictor.predict_race(race_id, budget=budget)
        if result:
            results.append(result)

    print("\n" + "="*80)
    print("予想完了！")
    print("="*80)
    print(f"\n{len(results)}レースの予想が完了しました")

if __name__ == "__main__":
    main()
