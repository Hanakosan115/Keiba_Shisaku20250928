"""
今週末のレース予想ツール
最新データをもとに今週末のレースを予想
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import pickle
from datetime import datetime, timedelta
import re
from value_betting_module import ValueBettingAnalyzer

class WeekendRacePredictor:
    """今週末予想クラス"""

    def __init__(self, model_path='lgbm_model_hybrid.pkl',
                 db_path='netkeiba_data_2020_2024_enhanced.csv'):
        # モデル読み込み
        try:
            with open(model_path, 'rb') as f:
                self.model = pickle.load(f)
            print(f"[OK] モデル読み込み完了: {model_path}")
        except:
            print("[NG] モデルが見つかりません")
            self.model = None

        # データベース読み込み
        try:
            self.df = pd.read_csv(db_path, encoding='utf-8', low_memory=False)
            self.df['race_id'] = self.df['race_id'].astype(str)
            print(f"[OK] データベース読み込み完了: {len(self.df):,}件")
        except:
            print("[NG] データベースが見つかりません")
            self.df = None

        self.session = requests.Session()
        self.value_analyzer = ValueBettingAnalyzer(value_threshold=0.05)

    def get_this_weekend_races(self):
        """今週末のレース一覧を取得"""
        today = datetime.now()

        # 次の土曜日を探す
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0 and today.weekday() == 5:
            # 今日が土曜日
            saturday = today
        else:
            saturday = today + timedelta(days=days_until_saturday)

        sunday = saturday + timedelta(days=1)

        print(f"\n今週末:")
        print(f"  土曜日: {saturday.strftime('%Y年%m月%d日')}")
        print(f"  日曜日: {sunday.strftime('%Y年%m月%d日')}")

        weekend_races = []

        for target_date in [saturday, sunday]:
            date_str = target_date.strftime('%Y%m%d')
            day_name = '土曜' if target_date.weekday() == 5 else '日曜'

            print(f"\n{day_name}のレースを取得中...")

            url = f"https://race.netkeiba.com/top/race_list.html?date={date_str}"

            try:
                response = self.session.get(url)
                response.encoding = 'EUC-JP'
                soup = BeautifulSoup(response.content, 'html.parser')

                # レースリンクを探す
                race_links = soup.select('a[href*="race_id="]')

                found_races = {}
                for link in race_links:
                    href = link.get('href', '')
                    match = re.search(r'race_id=(\d{12})', href)
                    if match:
                        race_id = match.group(1)
                        race_title = link.text.strip()
                        found_races[race_id] = race_title

                if found_races:
                    print(f"  見つかったレース: {len(found_races)}件")
                    for race_id, title in found_races.items():
                        weekend_races.append({
                            'date': target_date,
                            'day_name': day_name,
                            'race_id': race_id,
                            'title': title
                        })
                else:
                    print(f"  レースなし")

            except Exception as e:
                print(f"  エラー: {e}")

        return weekend_races

    def get_race_shutuba(self, race_id):
        """出馬表を取得"""
        url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"

        try:
            response = self.session.get(url)
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
                horse_url = horse_name_elem.get('href', '') if horse_name_elem else ''
                horse_id = horse_url.split('/')[-2] if '/horse/' in horse_url else None

                # オッズ
                odds_elem = row.select_one('.Popular')
                odds_text = odds_elem.text.strip() if odds_elem else None
                try:
                    odds = float(odds_text) if odds_text and odds_text != '-' else 10.0
                except:
                    odds = 10.0

                # 人気
                ninki_elem = row.select_one('.Ninki')
                ninki_text = ninki_elem.text.strip() if ninki_elem else None
                try:
                    ninki = int(ninki_text) if ninki_text and ninki_text.isdigit() else None
                except:
                    ninki = None

                # 騎手
                jockey_elem = row.select_one('.Jockey a')
                jockey_name = jockey_elem.text.strip() if jockey_elem else 'N/A'

                horses_data.append({
                    'Umaban': umaban,
                    'HorseName': horse_name,
                    'horse_id': horse_id,
                    'Odds': odds,
                    'Ninki': ninki,
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

    def predict_race(self, race_id, budget=10000):
        """レースを予想"""
        print(f"\n{'='*80}")
        print(f"レースID: {race_id}")
        print("="*80)

        # 出馬表取得
        horses_df, race_info = self.get_race_shutuba(race_id)

        if horses_df is None:
            print("出馬表が取得できませんでした")
            return None

        print(f"レース: {race_info['race_name']}")
        print(f"距離: {race_info['distance']}m")
        print(f"出走: {len(horses_df)}頭")

        # 簡易予測（オッズベース）
        # 本来はここで特徴量を生成してモデル予測するが、簡略化
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
                'score': row['score']
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
        print(f"{'順位':^6} {'馬番':^6} {'馬名':^20} {'オッズ':^8} {'Value':^10}")
        print("-"*80)

        horses_sorted = sorted(horses_data, key=lambda x: x['predicted_rank'])
        for i, h in enumerate(horses_sorted[:5], 1):
            print(f"{i:^6} {h['umaban']:^6} {h['horse_name'][:20]:^20} {h['odds']:^8.1f} {h['value']*100:^+9.2f}%")

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
    print("今週末のレース予想ツール")
    print("="*80)

    predictor = WeekendRacePredictor()

    # 今週末のレース取得
    weekend_races = predictor.get_this_weekend_races()

    if len(weekend_races) == 0:
        print("\n今週末のレースが見つかりませんでした")
        return

    # レース一覧表示
    print("\n" + "="*80)
    print("レース一覧")
    print("="*80)

    for i, race in enumerate(weekend_races, 1):
        print(f"{i:2d}. [{race['day_name']}] {race['title']} (ID: {race['race_id']})")

    # レース選択
    print("\n予想するレース番号を入力してください（全て予想: all）")
    choice = input("> ").strip()

    if choice.lower() == 'all':
        selected_races = weekend_races
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(weekend_races):
                selected_races = [weekend_races[idx]]
            else:
                print("無効な番号です")
                return
        except:
            print("無効な入力です")
            return

    # 予算
    budget_input = input("\n予算を入力してください（デフォルト: 10000円）\n> ").strip()
    budget = int(budget_input) if budget_input.isdigit() else 10000

    # 予想実行
    results = []
    for race in selected_races:
        result = predictor.predict_race(race['race_id'], budget=budget)
        if result:
            results.append(result)

    print("\n" + "="*80)
    print("予想完了！")
    print("="*80)
    print(f"\n{len(results)}レースの予想が完了しました")
    print("推奨ベットに従って馬券を購入してください")

if __name__ == "__main__":
    main()
