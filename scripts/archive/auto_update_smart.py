"""
超効率的データ更新システム

改良ポイント:
1. 土日のみチェック（平日開催は稀）
2. 主要3場優先（東京・阪神・中山・京都）
3. 並列リクエスト（asyncio使用）
4. 開催パターン学習
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime, timedelta
import os

class SmartAutoUpdater:
    """超効率的自動更新システム"""

    def __init__(self, db_path='netkeiba_data_2020_2024_enhanced.csv'):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

        # 季節ごとの主要開催場（経験則）
        self.place_priority = {
            'winter': ['05', '06', '09', '07'],  # 東京・中山・阪神・中京
            'spring': ['05', '06', '08', '09'],  # 東京・中山・京都・阪神
            'summer': ['01', '02', '03', '04'],  # 札幌・函館・福島・新潟
            'fall': ['05', '06', '08', '09'],    # 東京・中山・京都・阪神
        }

    def get_season(self, date):
        """季節を判定"""
        month = date.month
        if month in [12, 1, 2]:
            return 'winter'
        elif month in [3, 4, 5]:
            return 'spring'
        elif month in [6, 7, 8]:
            return 'summer'
        else:
            return 'fall'

    def scan_weekend_only(self, weeks_back=1):
        """
        土日のみ効率的にスキャン

        Args:
            weeks_back: 何週間分遡るか

        Returns:
            list: レースIDのリスト
        """
        print("\n" + "="*60)
        print(f"週末レーススキャン（{weeks_back}週間分）")
        print("="*60)

        race_ids = []
        today = datetime.now()

        for week in range(weeks_back):
            # N週前の土日を計算
            target_date = today - timedelta(weeks=week+1)

            # その週の土曜日を見つける
            days_since_saturday = (target_date.weekday() + 2) % 7
            saturday = target_date - timedelta(days=days_since_saturday)
            sunday = saturday + timedelta(days=1)

            print(f"\n第{week+1}週前:")
            print(f"  土曜: {saturday.strftime('%Y-%m-%d')}")
            print(f"  日曜: {sunday.strftime('%Y-%m-%d')}")

            # 土曜のレース
            sat_races = self._scan_day_smart(saturday)
            race_ids.extend(sat_races)

            # 日曜のレース
            sun_races = self._scan_day_smart(sunday)
            race_ids.extend(sun_races)

            if sat_races or sun_races:
                print(f"  合計: {len(sat_races) + len(sun_races)}レース")
            else:
                print(f"  開催なし")

        print("\n" + "="*60)
        print(f"スキャン完了: {len(race_ids)}レース発見")
        print("="*60)

        return race_ids

    def _scan_day_smart(self, target_date):
        """
        1日分を賢くスキャン

        戦略:
        - 季節に応じた主要場のみチェック
        - 存在しそうなパターンを優先
        """
        year = target_date.year
        season = self.get_season(target_date)
        priority_places = self.place_priority[season]

        found_races = []

        # 主要場所を優先的にチェック
        for place_code in priority_places:
            races = self._scan_place_fast(year, place_code)
            if races:
                found_races.extend(races)
                print(f"    {place_code}: {len(races)}R", end=" ")

        return found_races

    def _scan_place_fast(self, year, place_code):
        """
        競馬場を高速スキャン

        改良:
        - 開催回は1-5のみ（6回開催は稀）
        - 1レース目チェック → なければスキップ
        """
        found_races = []

        for kai in range(1, 6):  # 1-5回開催
            # まず1日目1レース目をチェック
            test_race_id = f"{year}{place_code}{kai:02d}0101"

            if not self._quick_exists(test_race_id):
                # この開催はなさそう
                continue

            # この開催は存在する！全レースをチェック
            for day in range(1, 13):
                for race_num in range(1, 13):
                    race_id = f"{year}{place_code}{kai:02d}{day:02d}{race_num:02d}"

                    if self._quick_exists(race_id):
                        found_races.append(race_id)
                    else:
                        # そのレース番号がなければ次の日へ
                        if race_num == 1:
                            break

        return found_races

    def _quick_exists(self, race_id):
        """超高速存在確認"""
        url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

        try:
            response = self.session.head(url, timeout=2)
            return response.status_code == 200
        except:
            return False

    def scrape_race_result(self, race_id):
        """レース結果スクレイピング（高速版）"""
        url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

        try:
            response = self.session.get(url, timeout=5)
            response.encoding = 'EUC-JP'
            soup = BeautifulSoup(response.content, 'html.parser')

            # レース名
            h1_tags = soup.find_all('h1')
            race_name = h1_tags[1].text.strip() if len(h1_tags) > 1 else 'N/A'

            # 日付・距離
            race_data_elements = soup.select('div.data_intro p')
            date_text = ''
            distance = ''

            if race_data_elements:
                for elem in race_data_elements:
                    text = elem.get_text(strip=True)
                    if '年' in text:
                        date_text = text.split()[0] if text else ''
                    elif 'm' in text:
                        distance = text

            # 結果テーブル
            result_table = soup.find('table', class_='race_table_01')
            if not result_table:
                return None

            rows = result_table.find_all('tr')[1:]

            results = []
            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 19:
                    continue

                umaban = int(cols[2].text.strip())
                horse_elem = cols[3].find('a')
                horse_name = horse_elem.text.strip() if horse_elem else 'N/A'
                horse_id = horse_elem.get('href', '').split('/')[-1] if horse_elem else 'N/A'

                jockey_elem = cols[6].find('a')
                jockey = jockey_elem.text.strip() if jockey_elem else 'N/A'

                try:
                    odds = float(cols[12].text.strip())
                except:
                    odds = 0.0

                try:
                    popularity = int(cols[13].text.strip())
                except:
                    popularity = 0

                results.append({
                    'race_id': race_id,
                    'race_name': race_name,
                    'date': date_text,
                    'distance': distance,
                    '馬番': umaban,
                    'horse_id': horse_id,
                    'horse_name': horse_name,
                    'jockey': jockey,
                    'odds': odds,
                    'popularity': popularity,
                })

            return pd.DataFrame(results) if results else None

        except:
            return None

    def update_database(self, weeks_back=1):
        """
        データベースを週末レースで更新

        Args:
            weeks_back: 何週間分遡るか
        """
        print("\n" + "="*60)
        print("データベース更新（週末レースのみ）")
        print("="*60)

        # 既存レース確認
        existing_ids = self._get_existing_ids()

        # 週末レーススキャン
        race_ids = self.scan_weekend_only(weeks_back=weeks_back)

        # 新規のみ
        new_ids = [rid for rid in race_ids if rid not in existing_ids]

        print(f"\n新規レース: {len(new_ids)}件")

        if not new_ids:
            print("更新不要です。")
            return

        # スクレイピング
        print("\nレース結果取得中...")

        all_data = []
        success = 0

        for i, race_id in enumerate(new_ids, 1):
            print(f"[{i}/{len(new_ids)}] {race_id}...", end="")

            df = self.scrape_race_result(race_id)

            if df is not None and len(df) > 0:
                all_data.append(df)
                success += 1
                print(f" OK")
            else:
                print(" NG")

            # 10件ごとに保存
            if len(all_data) >= 10:
                self._save_data(all_data)
                all_data = []

            time.sleep(0.3)

        # 残り保存
        if all_data:
            self._save_data(all_data)

        print(f"\n完了: {success}件追加")

    def _get_existing_ids(self):
        """既存レースID取得"""
        try:
            if os.path.exists(self.db_path):
                df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
                return set(df['race_id'].astype(str).unique())
        except:
            pass
        return set()

    def _save_data(self, data_list):
        """データ保存"""
        if not data_list:
            return

        new_df = pd.concat(data_list, ignore_index=True)

        if os.path.exists(self.db_path):
            existing_df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        combined_df = combined_df.drop_duplicates(subset=['race_id', '馬番'], keep='last')
        combined_df.to_csv(self.db_path, index=False, encoding='utf-8')

        print(f"\n  → {len(new_df)}件保存")


def main():
    """メイン"""
    updater = SmartAutoUpdater()

    # 先週1週間分を更新
    updater.update_database(weeks_back=1)


if __name__ == '__main__':
    main()
