"""
自動データ更新システム
毎週のレース結果を自動収集してデータベースを最新に保つ
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime, timedelta
import re

class NetkeibaAutoUpdater:
    """Netkeiba自動更新クラス"""

    def __init__(self, db_path='netkeiba_data_2020_2024_enhanced.csv'):
        self.db_path = db_path
        self.session = requests.Session()

    def get_recent_race_ids(self, days_back=7):
        """
        直近N日のレースIDを取得

        Args:
            days_back: 何日前まで遡るか

        Returns:
            list: レースIDのリスト
        """
        race_ids = []

        # 主要競馬場のコード
        place_codes = {
            '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
            '05': '東京', '06': '中山', '07': '中京', '08': '京都',
            '09': '阪神', '10': '小倉'
        }

        today = datetime.now()

        print(f"直近{days_back}日間のレース結果を検索中...")

        for days_ago in range(days_back):
            target_date = today - timedelta(days=days_ago)

            # 土日のみ（競馬開催日）
            if target_date.weekday() not in [5, 6]:  # 土=5, 日=6
                continue

            date_str = target_date.strftime('%Y%m%d')
            print(f"\n{target_date.strftime('%Y-%m-%d')} ({['月','火','水','木','金','土','日'][target_date.weekday()]})")

            # カレンダーページから開催情報を取得
            calendar_url = f"https://race.netkeiba.com/top/race_list.html?date={date_str}"

            try:
                response = self.session.get(calendar_url)
                response.encoding = 'EUC-JP'
                soup = BeautifulSoup(response.content, 'html.parser')

                # レースリンクを探す
                race_links = soup.select('a[href*="race_id="]')

                found_races = set()
                for link in race_links:
                    href = link.get('href', '')
                    match = re.search(r'race_id=(\d{12})', href)
                    if match:
                        race_id = match.group(1)
                        found_races.add(race_id)

                if found_races:
                    print(f"  見つかったレース: {len(found_races)}件")
                    race_ids.extend(sorted(found_races))
                else:
                    print(f"  レースなし")

                time.sleep(1)

            except Exception as e:
                print(f"  エラー: {e}")

        return race_ids

    def scrape_race_result(self, race_id):
        """レース結果をスクレイピング"""
        url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

        try:
            response = self.session.get(url)
            response.encoding = 'EUC-JP'
            soup = BeautifulSoup(response.content, 'html.parser')

            # レース情報
            race_data = soup.select_one('.RaceData01')
            if not race_data:
                return None

            race_data_text = race_data.text.strip()

            # 距離
            distance_match = re.search(r'(\d+)m', race_data_text)
            distance = int(distance_match.group(1)) if distance_match else None

            # 馬場状態
            track_match = re.search(r'馬場:(\S+)', race_data_text)
            track_condition = track_match.group(1) if track_match else None

            # 天気
            weather_match = re.search(r'天候:(\S+)', race_data_text)
            weather = weather_match.group(1) if weather_match else None

            # レース名
            race_name_elem = soup.select_one('.RaceName')
            race_name = race_name_elem.text.strip() if race_name_elem else 'N/A'

            # 日付
            race_date_elem = soup.select_one('.RaceData02')
            race_date = race_date_elem.text.strip() if race_date_elem else None

            # 結果テーブル
            result_table = soup.select_one('.Race_Result_Table')

            if not result_table:
                return None

            horses_data = []
            rows = result_table.select('tr')[1:]  # ヘッダー除く

            for row in rows:
                cols = row.select('td')
                if len(cols) < 18:
                    continue

                # 着順
                rank_text = cols[0].text.strip()
                try:
                    rank = int(rank_text)
                except:
                    continue

                # 枠番
                waku = int(cols[1].text.strip())

                # 馬番
                umaban = int(cols[2].text.strip())

                # 馬名
                horse_elem = cols[3].select_one('a')
                horse_name = horse_elem.text.strip() if horse_elem else 'N/A'
                horse_url = horse_elem.get('href', '') if horse_elem else ''
                horse_id = horse_url.split('/')[-2] if '/horse/' in horse_url else None

                # 性齢
                sex_age = cols[4].text.strip()

                # 斤量
                kinryo = float(cols[5].text.strip())

                # 騎手
                jockey_elem = cols[6].select_one('a')
                jockey_name = jockey_elem.text.strip() if jockey_elem else 'N/A'

                # タイム
                race_time = cols[7].text.strip()

                # 着差
                diff = cols[8].text.strip()

                # 通過順
                passage = cols[10].text.strip()

                # 上がり
                agari = cols[11].text.strip()

                # オッズ
                odds = float(cols[12].text.strip())

                # 人気
                ninki = int(cols[13].text.strip())

                # 馬体重
                weight_info = cols[14].text.strip()

                # 調教師
                trainer_elem = cols[18].select_one('a') if len(cols) > 18 else None
                trainer_name = trainer_elem.text.strip() if trainer_elem else 'N/A'

                horses_data.append({
                    'race_id': race_id,
                    'race_name': race_name,
                    'date': race_date,
                    'distance': distance,
                    'track_condition': track_condition,
                    'weather': weather,
                    'Rank': rank,
                    'Waku': waku,
                    'Umaban': umaban,
                    'HorseName': horse_name,
                    'horse_id': horse_id,
                    'SexAge': sex_age,
                    'Load': kinryo,
                    'JockeyName': jockey_name,
                    'Time': race_time,
                    'Diff': diff,
                    'Passage': passage,
                    'Agari': agari,
                    'Odds': odds,
                    'Ninki': ninki,
                    'WeightInfo': weight_info,
                    'TrainerName': trainer_name
                })

            return pd.DataFrame(horses_data)

        except Exception as e:
            print(f"    エラー: {e}")
            return None

    def scrape_horse_past_ranks(self, horse_id, num_races=5):
        """馬の過去着順を取得"""
        url = f"https://db.netkeiba.com/horse/{horse_id}"

        try:
            response = self.session.get(url)
            response.encoding = 'EUC-JP'
            soup = BeautifulSoup(response.content, 'html.parser')

            result_table = soup.select_one('.db_h_race_results')

            if not result_table:
                return []

            rows = result_table.select('tr')[1:]
            past_ranks = []

            for row in rows[:num_races]:
                cols = row.select('td')
                if len(cols) < 12:
                    continue

                rank_elem = cols[11]
                rank_text = rank_elem.text.strip()

                try:
                    rank = int(rank_text)
                    past_ranks.append(rank)
                except:
                    pass

            return past_ranks

        except:
            return []

    def update_database(self, days_back=7):
        """
        データベースを最新に更新

        Args:
            days_back: 何日前まで遡るか
        """
        print("="*80)
        print("自動データ更新システム")
        print("="*80)

        # 直近のレースID取得
        race_ids = self.get_recent_race_ids(days_back=days_back)

        if len(race_ids) == 0:
            print("\n更新するレースが見つかりませんでした")
            return

        print(f"\n合計 {len(race_ids)} レースを更新します")

        # 既存データベース読み込み
        try:
            main_df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
            main_df['race_id'] = main_df['race_id'].astype(str)
            print(f"既存データ: {len(main_df):,}件")
        except:
            print("既存データベースが見つかりません。新規作成します。")
            main_df = pd.DataFrame()

        # 各レースをスクレイピング
        all_new_data = []

        for i, race_id in enumerate(race_ids, 1):
            print(f"\n[{i}/{len(race_ids)}] レースID: {race_id}")

            # スクレイピング
            race_df = self.scrape_race_result(race_id)

            if race_df is None or len(race_df) == 0:
                print("  スキップ（データなし）")
                continue

            print(f"  {race_df.iloc[0]['race_name']} - {len(race_df)}頭")

            # 過去着順を追加
            for idx, row in race_df.iterrows():
                horse_id = row['horse_id']
                if horse_id:
                    past_ranks = self.scrape_horse_past_ranks(horse_id, num_races=5)

                    for j in range(5):
                        if j < len(past_ranks):
                            race_df.at[idx, f'past_rank_{j+1}'] = past_ranks[j]

                    time.sleep(0.5)  # 負荷軽減

            all_new_data.append(race_df)
            time.sleep(1)

        if len(all_new_data) == 0:
            print("\n新しいデータが取得できませんでした")
            return

        # 新データを結合
        new_df = pd.concat(all_new_data, ignore_index=True)
        print(f"\n新規データ: {len(new_df):,}件")

        # 既存データから重複を削除
        if len(main_df) > 0:
            main_df = main_df[~main_df['race_id'].isin(new_df['race_id'].unique())]

        # 結合
        updated_df = pd.concat([main_df, new_df], ignore_index=True)

        # 保存
        updated_df.to_csv(self.db_path, index=False, encoding='utf-8')

        print(f"\n✓ 更新完了！")
        print(f"  総レコード数: {len(updated_df):,}件")
        print(f"  追加: {len(new_df):,}件")

        return updated_df

def main():
    """メイン処理"""
    updater = NetkeibaAutoUpdater()

    print("何日前まで遡りますか？（デフォルト: 7日）")
    days_input = input("> ").strip()

    days_back = int(days_input) if days_input.isdigit() else 7

    updater.update_database(days_back=days_back)

if __name__ == "__main__":
    main()
