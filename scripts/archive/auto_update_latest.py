"""
自動データ更新システム - 最新データを効率的に取得

戦略:
1. JRA公式開催スケジュールは土日が中心
2. 主要競馬場（10場）のみチェック
3. 効率化: 1レース目が見つからない開催はスキップ
4. 昨日までのデータを自動取得
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime, timedelta
import os

class AutoLatestUpdater:
    """最新データ自動更新システム"""

    def __init__(self, db_path='netkeiba_data_2020_2024_enhanced.csv'):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def get_latest_db_date(self):
        """データベースの最新日付を取得"""
        try:
            if os.path.exists(self.db_path):
                df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
                if 'date' in df.columns and len(df) > 0:
                    # 日付を解析
                    df['date_parsed'] = pd.to_datetime(df['date'], format='%Y年%m月%d日', errors='coerce')
                    max_date = df['date_parsed'].max()
                    if pd.notna(max_date):
                        print(f"[DB] 現在の最新日付: {max_date.strftime('%Y年%m月%d日')}")
                        return max_date
        except Exception as e:
            print(f"[警告] DB読み込みエラー: {e}")

        # デフォルト: 30日前から
        return datetime.now() - timedelta(days=30)

    def get_existing_race_ids(self):
        """既存のレースIDセットを取得"""
        try:
            if os.path.exists(self.db_path):
                df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
                existing_ids = set(df['race_id'].astype(str).unique())
                print(f"[DB] 既存レース数: {len(existing_ids):,}件")
                return existing_ids
        except:
            pass
        return set()

    def scan_recent_races(self, days_back=7):
        """
        最近N日間のレースを効率的にスキャン

        Args:
            days_back: 何日前まで遡るか（デフォルト7日=1週間）

        Returns:
            list: 発見したレースIDのリスト
        """
        print("\n" + "="*60)
        print(f"最近{days_back}日間のレーススキャン")
        print("="*60)

        end_date = datetime.now() - timedelta(days=1)  # 昨日まで
        start_date = end_date - timedelta(days=days_back)

        print(f"期間: {start_date.strftime('%Y-%m-%d')} ～ {end_date.strftime('%Y-%m-%d')}")

        # JRA競馬場コード（10場）
        jra_places = {
            '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
            '05': '東京', '06': '中山', '07': '中京', '08': '京都',
            '09': '阪神', '10': '小倉'
        }

        race_ids = []
        current_date = start_date

        while current_date <= end_date:
            year = current_date.year
            date_str = current_date.strftime('%Y-%m-%d (%a)')

            print(f"\n{date_str}")

            day_races = []

            # 各競馬場をチェック
            for place_code, place_name in jra_places.items():
                found_races = self._scan_place_on_date(year, place_code, place_name)
                day_races.extend(found_races)

            if day_races:
                print(f"  合計: {len(day_races)}レース")
                race_ids.extend(day_races)
            else:
                print(f"  開催なし")

            current_date += timedelta(days=1)

        print("\n" + "="*60)
        print(f"スキャン完了: {len(race_ids)}レース発見")
        print("="*60)

        return race_ids

    def _scan_place_on_date(self, year, place_code, place_name):
        """
        特定日・特定競馬場のレースをスキャン

        効率化ポイント:
        - 開催回は通常1-6回程度
        - 日数は通常1-12日程度
        - レース数は1-12R
        - 1R目が見つからなければその開催は存在しない
        """
        found_races = []

        # 開催回・日・レース数の範囲
        for kai in range(1, 7):  # 1-6回開催
            kai_found = False

            for day in range(1, 13):  # 1-12日
                day_found = False

                for race_num in range(1, 13):  # 1-12R
                    race_id = f"{year}{place_code}{kai:02d}{day:02d}{race_num:02d}"

                    if self._quick_check_race(race_id):
                        found_races.append(race_id)
                        kai_found = True
                        day_found = True
                    else:
                        # 1R目が見つからなければ、その日は開催なし
                        if race_num == 1:
                            break

                # その日にレースがなければ次の開催回へ
                if not day_found:
                    break

            # その開催回にレースがなければ終了
            if not kai_found:
                break

        if found_races:
            print(f"  {place_name}: {len(found_races)}R", end="")

        return found_races

    def _quick_check_race(self, race_id):
        """
        レースの存在を高速チェック（HEAD リクエスト）
        """
        url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

        try:
            # HEAD リクエストで存在確認（軽量）
            response = self.session.head(url, timeout=3, allow_redirects=True)

            # 200 OK なら存在する可能性が高い
            if response.status_code == 200:
                return True

            return False

        except:
            return False

    def scrape_race_result(self, race_id):
        """
        レース結果をスクレイピング（修正版）
        """
        url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

        try:
            response = self.session.get(url, timeout=10)
            response.encoding = 'EUC-JP'
            soup = BeautifulSoup(response.content, 'html.parser')

            # レース名取得
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
            return None

    def update_database(self, days_back=7, batch_size=50):
        """
        データベースを最新に更新

        Args:
            days_back: 何日前まで遡るか
            batch_size: 何レースごとに保存するか
        """
        print("\n" + "="*60)
        print("データベース自動更新")
        print("="*60)

        # 既存データ確認
        existing_ids = self.get_existing_race_ids()

        # 最近のレースをスキャン
        race_ids = self.scan_recent_races(days_back=days_back)

        # 新規レースのみフィルタ
        new_race_ids = [rid for rid in race_ids if rid not in existing_ids]

        print(f"\n新規レース: {len(new_race_ids)}件")

        if not new_race_ids:
            print("更新不要です。データベースは最新です。")
            return

        # スクレイピング実行
        print("\nレース結果を取得中...")

        all_new_data = []
        success = 0
        fail = 0

        for i, race_id in enumerate(new_race_ids, 1):
            print(f"[{i}/{len(new_race_ids)}] {race_id}...", end="")

            df = self.scrape_race_result(race_id)

            if df is not None and len(df) > 0:
                all_new_data.append(df)
                success += 1
                print(f" OK ({len(df)}頭)")
            else:
                fail += 1
                print(" NG")

            # バッチ保存
            if len(all_new_data) >= batch_size:
                self._save_batch(all_new_data)
                all_new_data = []

            time.sleep(0.5)  # レート制限

        # 残りを保存
        if all_new_data:
            self._save_batch(all_new_data)

        print("\n" + "="*60)
        print(f"更新完了: 成功 {success}件 / 失敗 {fail}件")
        print("="*60)

    def _save_batch(self, data_list):
        """バッチデータを保存"""
        if not data_list:
            return

        new_df = pd.concat(data_list, ignore_index=True)

        if os.path.exists(self.db_path):
            existing_df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df

        # 重複削除
        combined_df = combined_df.drop_duplicates(subset=['race_id', '馬番'], keep='last')

        # 保存
        combined_df.to_csv(self.db_path, index=False, encoding='utf-8')
        print(f"\n  → {len(new_df)}件をDBに追加")


def main():
    """メイン実行"""
    updater = AutoLatestUpdater()

    # 最近7日間（1週間）を更新
    updater.update_database(days_back=7)


if __name__ == '__main__':
    main()
