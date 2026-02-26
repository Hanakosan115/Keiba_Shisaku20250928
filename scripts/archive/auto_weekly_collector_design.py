"""
週次自動データ収集システム - 設計書・サンプル実装

目的:
  毎週自動で最新レース結果を収集し、データの鮮度を保つ
  ユーザー指摘の「先週勝ってクラスが上がった馬」問題を解決
"""

import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from bs4 import BeautifulSoup
import time
import json
import os

class WeeklyDataCollector:
    """
    週次データ収集クラス

    実行タイミング: 毎週月曜 朝7:00
    収集対象: 先週土日のレース結果
    """

    def __init__(self, csv_path='netkeiba_data_2020_2024_clean.csv'):
        self.csv_path = csv_path
        self.log_path = 'data_collection_log.json'

    def get_last_week_dates(self):
        """
        先週の土日の日付を取得

        Returns:
            list: [(2024, 11, 16), (2024, 11, 17)]
        """
        today = datetime.now()

        # 先週の日曜日を計算
        days_since_sunday = (today.weekday() + 1) % 7
        last_sunday = today - timedelta(days=days_since_sunday)

        # 先週の土曜日
        last_saturday = last_sunday - timedelta(days=1)

        return [
            (last_saturday.year, last_saturday.month, last_saturday.day),
            (last_sunday.year, last_sunday.month, last_sunday.day)
        ]

    def get_race_list_for_date(self, year, month, day):
        """
        指定日の全レース一覧を取得

        Args:
            year, month, day: 日付

        Returns:
            list: [race_id1, race_id2, ...]

        実装:
            netkeibaのカレンダーページから
            https://race.netkeiba.com/top/calendar.html?year=2024&month=11
        """
        url = f"https://race.netkeiba.com/top/calendar.html?year={year}&month={month}"

        # Selenium で取得（動的コンテンツ対応）
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'lxml')
        driver.quit()

        # カレンダーから指定日のリンクを抽出
        # （実際の実装はHTMLの構造に依存）
        race_ids = []

        # 例: <a href="/race/list/20241117/">みたいなリンクを探す
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/race/list/' in href:
                date_str = href.split('/')[-2]
                if date_str.startswith(f"{year:04d}{month:02d}{day:02d}"):
                    # その日のレース一覧ページへ
                    race_list_url = f"https://race.netkeiba.com{href}"
                    race_ids.extend(self._get_races_from_list_page(race_list_url))

        return race_ids

    def _get_races_from_list_page(self, list_url):
        """
        レース一覧ページから各race_idを取得
        """
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')

        driver = webdriver.Chrome(options=options)
        driver.get(list_url)
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'lxml')
        driver.quit()

        race_ids = []

        # レース結果へのリンクを探す
        # 例: /race/result.html?race_id=202411170101
        for link in soup.find_all('a', href=True):
            if 'race_id=' in link['href']:
                race_id = link['href'].split('race_id=')[1].split('&')[0]
                race_ids.append(race_id)

        return list(set(race_ids))  # 重複除去

    def collect_race_result(self, race_id):
        """
        指定race_idのレース結果を収集

        Args:
            race_id: レースID（例: 202411170101）

        Returns:
            dict: {
                'race_info': {...},
                'horses': [{...}, {...}, ...]
            }
        """
        url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')

        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(3)

        soup = BeautifulSoup(driver.page_source, 'lxml')
        driver.quit()

        # レース情報抽出
        race_info = self._extract_race_info(soup, race_id)

        # 各馬の情報抽出
        horses = self._extract_horses_info(soup, race_id, race_info)

        return {
            'race_info': race_info,
            'horses': horses
        }

    def _extract_race_info(self, soup, race_id):
        """
        レース情報を抽出

        重要: クラス情報を取得！
        """
        # レース名から「1勝クラス」「未勝利」などを抽出
        race_name_tag = soup.find('h1', class_='RaceName')
        race_name = race_name_tag.text.strip() if race_name_tag else ''

        # クラス判定
        race_class = self._detect_class(race_name)

        # その他の情報
        # （距離、馬場状態、天気など）

        return {
            'race_id': race_id,
            'race_name': race_name,
            'race_class': race_class,
            # ... 他の情報
        }

    def _detect_class(self, race_name):
        """
        レース名からクラスを判定

        これが鍵！
        """
        if '未勝利' in race_name:
            return '未勝利'
        elif '新馬' in race_name:
            return '新馬'
        elif '1勝クラス' in race_name or '500万' in race_name:
            return '1勝'
        elif '2勝クラス' in race_name or '1000万' in race_name:
            return '2勝'
        elif '3勝クラス' in race_name or '1600万' in race_name:
            return '3勝'
        elif 'オープン' in race_name:
            return 'オープン'
        elif 'G1' in race_name or 'GI' in race_name:
            return 'G1'
        elif 'G2' in race_name or 'GII' in race_name:
            return 'G2'
        elif 'G3' in race_name or 'GIII' in race_name:
            return 'G3'
        else:
            return '不明'

    def _extract_horses_info(self, soup, race_id, race_info):
        """
        各馬の情報を抽出
        """
        horses = []

        table = soup.find('table', class_='Result_Table')
        if not table:
            return horses

        for row in table.find_all('tr')[1:]:  # ヘッダーをスキップ
            cols = row.find_all('td')
            if len(cols) < 10:
                continue

            # 着順
            rank = cols[0].text.strip()

            # 馬番
            umaban = cols[1].text.strip()

            # 馬名とhorse_id
            horse_link = cols[3].find('a')
            horse_name = horse_link.text.strip() if horse_link else ''
            horse_url = horse_link['href'] if horse_link else ''
            horse_id = horse_url.split('/')[-2] if '/' in horse_url else ''

            # 性齢
            sex_age = cols[4].text.strip()

            # 斤量
            load = cols[5].text.strip()

            # 騎手
            jockey = cols[6].text.strip()

            # タイム
            time_str = cols[7].text.strip()

            # 着差
            diff = cols[8].text.strip()

            # 通過順位
            passage = cols[11].text.strip() if len(cols) > 11 else ''

            # 上がり
            agari = cols[12].text.strip() if len(cols) > 12 else ''

            # オッズ
            odds = cols[13].text.strip() if len(cols) > 13 else ''

            # 人気
            ninki = cols[14].text.strip() if len(cols) > 14 else ''

            # 馬体重
            weight_info = cols[15].text.strip() if len(cols) > 15 else ''

            horses.append({
                'race_id': race_id,
                'date': race_info.get('date'),
                'race_class': race_info.get('race_class'),
                'rank': rank,
                'umaban': umaban,
                'horse_id': horse_id,
                'horse_name': horse_name,
                'sex_age': sex_age,
                'load': load,
                'jockey': jockey,
                'time': time_str,
                'diff': diff,
                'passage': passage,
                'agari': agari,
                'odds': odds,
                'ninki': ninki,
                'weight_info': weight_info,
                # ... 他の列
            })

        return horses

    def update_database(self, new_data):
        """
        収集したデータをCSVに追加

        重要:
          - 重複チェック（race_id + horse_idで判定）
          - 既存馬のクラス変動を検出
        """
        # 既存データ読み込み
        if os.path.exists(self.csv_path):
            df_existing = pd.read_csv(self.csv_path, low_memory=False)
        else:
            df_existing = pd.DataFrame()

        # 新データをDataFrameに
        new_records = []
        for race in new_data:
            for horse in race['horses']:
                new_records.append(horse)

        df_new = pd.DataFrame(new_records)

        # 重複チェック
        if not df_existing.empty:
            # race_id + horse_id で重複判定
            df_existing['key'] = df_existing['race_id'].astype(str) + '_' + df_existing['horse_id'].astype(str)
            df_new['key'] = df_new['race_id'].astype(str) + '_' + df_new['horse_id'].astype(str)

            # 新規レコードのみ
            df_new = df_new[~df_new['key'].isin(df_existing['key'])]
            df_new = df_new.drop('key', axis=1)
            df_existing = df_existing.drop('key', axis=1)

        # 結合
        df_updated = pd.concat([df_existing, df_new], ignore_index=True)

        # 保存
        df_updated.to_csv(self.csv_path, index=False, encoding='utf-8-sig')

        return len(df_new)

    def detect_class_changes(self, horse_id):
        """
        指定馬のクラス変動を検出

        例:
          前回: 1勝クラス
          今回: 2勝クラス
          → 昇級！
        """
        df = pd.read_csv(self.csv_path, low_memory=False)
        horse_races = df[df['horse_id'] == horse_id].copy()
        horse_races = horse_races.sort_values('date')

        if len(horse_races) < 2:
            return None

        last_class = horse_races.iloc[-2]['race_class']
        current_class = horse_races.iloc[-1]['race_class']

        if last_class != current_class:
            return {
                'horse_id': horse_id,
                'from_class': last_class,
                'to_class': current_class,
                'type': 'promotion' if self._class_rank(current_class) > self._class_rank(last_class) else 'demotion'
            }

        return None

    def _class_rank(self, class_name):
        """クラスのランク数値"""
        ranks = {
            '新馬': 0,
            '未勝利': 0,
            '1勝': 1,
            '2勝': 2,
            '3勝': 3,
            'オープン': 4,
            'G3': 5,
            'G2': 6,
            'G1': 7
        }
        return ranks.get(class_name, 0)

    def run_weekly_collection(self):
        """
        週次収集のメイン処理

        これをWindows Task Schedulerで実行
        """
        print("="*80)
        print("週次データ収集開始")
        print(f"実行時刻: {datetime.now()}")
        print("="*80)

        # 先週の日付
        dates = self.get_last_week_dates()
        print(f"\n収集対象: {dates}")

        all_data = []
        total_races = 0

        for year, month, day in dates:
            print(f"\n{year}/{month}/{day} のレースを収集中...")

            # その日のレース一覧
            race_ids = self.get_race_list_for_date(year, month, day)
            print(f"  {len(race_ids)}レース発見")

            for race_id in race_ids:
                try:
                    race_data = self.collect_race_result(race_id)
                    all_data.append(race_data)
                    total_races += 1

                    print(f"    {race_id}: {race_data['race_info']['race_name'][:20]}... OK")

                    time.sleep(2)  # サーバー負荷軽減

                except Exception as e:
                    print(f"    {race_id}: エラー - {e}")

        # データベース更新
        print(f"\nデータベース更新中...")
        new_records = self.update_database(all_data)
        print(f"  新規レコード: {new_records}件追加")

        # ログ記録
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'dates_collected': dates,
            'total_races': total_races,
            'new_records': new_records,
            'status': 'success'
        }

        self._save_log(log_entry)

        print("\n収集完了！")
        print("="*80)

        return log_entry

    def _save_log(self, log_entry):
        """ログをJSONファイルに追記"""
        if os.path.exists(self.log_path):
            with open(self.log_path, 'r', encoding='utf-8') as f:
                logs = json.load(f)
        else:
            logs = []

        logs.append(log_entry)

        with open(self.log_path, 'w', encoding='utf-8') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)


# ============================================================================
# Windows Task Scheduler 設定方法
# ============================================================================
"""
1. タスクスケジューラを開く
   - Windowsキー → "タスクスケジューラ" で検索

2. 「基本タスクの作成」をクリック

3. 設定:
   名前: 週次競馬データ収集
   説明: 毎週月曜朝に先週のレース結果を収集

   トリガー: 毎週
   開始: 月曜日 07:00
   間隔: 1週間

   操作: プログラムの開始
   プログラム: C:\Users\bu158\AppData\Local\Programs\Python\Python313\python.exe
   引数: C:\Users\bu158\Keiba_Shisaku20250928\auto_weekly_collector.py
   開始: C:\Users\bu158\Keiba_Shisaku20250928

4. 「完了」をクリック

5. 手動テスト:
   - タスクを右クリック → "実行"
"""


# ============================================================================
# 使用例
# ============================================================================
if __name__ == '__main__':
    collector = WeeklyDataCollector()

    # 週次収集実行
    result = collector.run_weekly_collection()

    print(f"\n結果: {result}")
