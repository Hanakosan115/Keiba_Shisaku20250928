"""
スマート自動更新システム v3
実用的アプローチ: 最近の期間だけ効率的にスキャン
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime, timedelta
import re

class SmartUpdaterV3:
    """スマート更新システム v3 - 実用的アプローチ"""

    def __init__(self, db_path='netkeiba_data_2020_2024_enhanced.csv'):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def get_race_ids_smart_scan(self, start_date, end_date):
        """
        スマートスキャン方式

        実在するレースIDのみを効率的に取得:
        - 各日付・競馬場・レース番号の組み合わせをチェック
        - 存在しないものは404エラーですぐわかる
        - 存在率を計測しながら効率的にスキャン

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            list: 実在するレースIDのリスト
        """
        race_ids = []
        current_date = start_date

        # 競馬場コード（JRA10場）
        places = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10']

        # 開催回・日・レース数の最大値
        max_kai = 6   # 最大6回開催
        max_day = 12  # 最大12日間開催
        max_race = 12 # 最大12レース

        print(f"\n{start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")
        print(f"レースIDスキャン開始...\n")

        total_checked = 0
        total_found = 0

        while current_date <= end_date:
            year = current_date.strftime('%Y')
            month = current_date.strftime('%m')
            day = current_date.strftime('%d')

            date_races = []

            # この日付の全パターンをチェック
            for place in places:
                for kai in range(1, max_kai + 1):
                    for day_num in range(1, max_day + 1):
                        for race_num in range(1, max_race + 1):
                            race_id = f"{year}{place}{kai:02d}{day_num:02d}{race_num:02d}"

                            # レース結果ページで存在確認（軽量）
                            if self.check_race_exists(race_id):
                                date_races.append(race_id)
                                total_found += 1

                            total_checked += 1

                            # 進捗表示（100件ごと）
                            if total_checked % 100 == 0:
                                exist_rate = (total_found / total_checked) * 100
                                print(f"  チェック済: {total_checked}件 | 発見: {total_found}件 ({exist_rate:.1f}%)")

            if date_races:
                print(f"{current_date.strftime('%Y-%m-%d')}: {len(date_races)}レース")
                race_ids.extend(date_races)

            current_date += timedelta(days=1)
            time.sleep(0.5)  # レート制限

        print(f"\n完了: {total_found}レース発見 / {total_checked}件チェック")
        print(f"存在率: {(total_found/total_checked*100):.1f}%")

        return race_ids

    def check_race_exists(self, race_id):
        """
        レースが存在するか軽量チェック

        Args:
            race_id: レースID

        Returns:
            bool: 存在すればTrue
        """
        # 結果ページで確認（出馬表より軽量）
        url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

        try:
            response = self.session.get(url, timeout=5)

            # 200 OK で、かつエラーページでなければ存在
            if response.status_code == 200:
                # "該当するデータがありません" などのエラーメッセージがなければOK
                if 'データがありません' not in response.text and '存在しません' not in response.text:
                    return True

            return False

        except:
            return False

    def get_race_ids_focused_scan(self, target_weeks):
        """
        重点スキャン方式（推奨）

        特定の週末（土日）のみスキャンして効率化

        Args:
            target_weeks: [(year, month, week_number), ...]
                         例: [(2024, 11, 1), (2024, 11, 2)] = 11月第1・第2週

        Returns:
            list: 実在するレースIDのリスト
        """
        race_ids = []

        for year, month, week in target_weeks:
            # その月の第N週の土日を計算
            first_day = datetime(year, month, 1)

            # 第N週の土曜日を見つける
            days_to_first_saturday = (5 - first_day.weekday()) % 7
            first_saturday = first_day + timedelta(days=days_to_first_saturday)

            target_saturday = first_saturday + timedelta(weeks=week-1)
            target_sunday = target_saturday + timedelta(days=1)

            print(f"\n{year}年{month}月第{week}週:")
            print(f"  土曜: {target_saturday.strftime('%Y-%m-%d')}")
            print(f"  日曜: {target_sunday.strftime('%Y-%m-%d')}")

            # 土日のレースをスキャン
            weekend_races = self._scan_single_day(target_saturday)
            weekend_races.extend(self._scan_single_day(target_sunday))

            race_ids.extend(weekend_races)

        return race_ids

    def _scan_single_day(self, target_date):
        """1日分のレースをスキャン"""
        year = target_date.strftime('%Y')
        date_races = []

        # 土日なので主要3場くらいで開催されることが多い
        places = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10']

        print(f"\n  スキャン中: {target_date.strftime('%Y-%m-%d')}")

        checked = 0
        found = 0

        # 効率化: 開催回は1-5、日は1-12、レースは1-12で十分
        for place in places:
            for kai in range(1, 6):  # 通常は1-5回
                for day in range(1, 13):  # 通常は1-12日
                    for race_num in range(1, 13):  # 通常は1-12R
                        race_id = f"{year}{place}{kai:02d}{day:02d}{race_num:02d}"

                        if self.check_race_exists(race_id):
                            date_races.append(race_id)
                            found += 1

                        checked += 1

                        # 最初のレースが見つからなかったら、その開催はスキップ
                        if race_num == 1 and checked > 0 and found == 0:
                            break

        print(f"    発見: {found}レース ({checked}件チェック)")

        return date_races

    def scrape_race_result(self, race_id):
        """
        レース結果をスクレイピング（v2の修正版）
        """
        url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

        try:
            response = self.session.get(url, timeout=10)
            response.encoding = 'EUC-JP'
            soup = BeautifulSoup(response.content, 'html.parser')

            # レース名取得（修正済み）
            h1_tags = soup.find_all('h1')
            race_name = h1_tags[1].text.strip() if len(h1_tags) > 1 else 'N/A'

            # レース情報取得
            race_data_elements = soup.select('div.data_intro p')
            date_text = ''
            distance = ''

            if race_data_elements:
                for elem in race_data_elements:
                    text = elem.get_text(strip=True)
                    if '年' in text or '月' in text:
                        date_text = text.split()[0] if text else ''
                    elif 'm' in text or 'ダ' in text or '芝' in text:
                        distance = text

            # 結果テーブル取得
            result_table = soup.find('table', class_='race_table_01')

            if not result_table:
                return None

            rows = result_table.find_all('tr')[1:]  # ヘッダー除く

            results = []
            for row in rows:
                cols = row.find_all('td')

                if len(cols) < 19:
                    continue

                # 21カラム構造に対応
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

            if results:
                return pd.DataFrame(results)
            else:
                return None

        except Exception as e:
            print(f"エラー [{race_id}]: {e}")
            return None


def main():
    """使用例"""
    updater = SmartUpdaterV3()

    # 2024年11月のレースを取得
    print("="*60)
    print("2024年11月のレースをスキャン")
    print("="*60)

    start_date = datetime(2024, 11, 1)
    end_date = datetime(2024, 11, 30)

    # 注意: 全期間スキャンは時間がかかります
    # 実際には週末だけスキャンする方が効率的

    # 重点スキャン（推奨）
    target_weeks = [
        (2024, 11, 1),  # 11月第1週
        (2024, 11, 2),  # 11月第2週
        (2024, 11, 3),  # 11月第3週
        (2024, 11, 4),  # 11月第4週
    ]

    race_ids = updater.get_race_ids_focused_scan(target_weeks)

    print(f"\n合計: {len(race_ids)}レース発見")

    if race_ids:
        print(f"\nサンプル: {race_ids[:5]}")


if __name__ == '__main__':
    main()
