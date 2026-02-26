"""
2024年8月-12月の欠損データ収集スクリプト

CSVに存在しない2024年後半のレースデータを効率的に収集
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime, timedelta
import os

class MissingDataCollector:
    """2024年欠損データ収集"""

    def __init__(self, db_path='netkeiba_data_2020_2024_enhanced.csv'):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })

    def get_existing_race_ids(self):
        """既存レースID取得"""
        try:
            if os.path.exists(self.db_path):
                df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
                existing_ids = set(df['race_id'].astype(str).unique())
                print(f"[CSV] 既存レース: {len(existing_ids):,}件")
                return existing_ids
        except Exception as e:
            print(f"[警告] CSV読み込みエラー: {e}")
        return set()

    def scan_2024_races(self, start_month=8, end_month=12):
        """
        2024年の指定月範囲のレースを体系的にスキャン

        Args:
            start_month: 開始月 (デフォルト8月)
            end_month: 終了月 (デフォルト12月)

        Returns:
            list: 発見したレースIDのリスト
        """
        print("\n" + "="*60)
        print(f"2024年 {start_month}月-{end_month}月 レーススキャン")
        print("="*60)

        # JRA競馬場コード（10場）
        jra_places = {
            '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
            '05': '東京', '06': '中山', '07': '中京', '08': '京都',
            '09': '阪神', '10': '小倉'
        }

        race_ids = []

        # 月ごとにスキャン
        for month in range(start_month, end_month + 1):
            print(f"\n--- 2024年{month}月 ---")

            month_races = []

            # 各競馬場をスキャン
            for place_code, place_name in jra_places.items():
                place_races = self._scan_place_month(2024, month, place_code, place_name)
                month_races.extend(place_races)

            print(f"  → {month}月合計: {len(month_races)}レース")
            race_ids.extend(month_races)

        print("\n" + "="*60)
        print(f"スキャン完了: {len(race_ids)}レース発見")
        print("="*60)

        return race_ids

    def _scan_place_month(self, year, month, place_code, place_name):
        """
        特定月・特定競馬場のレースをスキャン

        効率化:
        - 開催回は通常1-5回程度
        - 各開催は通常1-12日
        - 1R目が見つからなければその日はスキップ
        """
        found_races = []

        # 開催回・日・レース数の範囲
        for kai in range(1, 6):  # 1-5回開催
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
                        # 1R目が見つからなければその日は開催なし
                        if race_num == 1:
                            break

                # その日にレースがなければ次の開催回へ
                if not day_found:
                    break

            # その開催回にレースがなければ終了
            if not kai_found:
                break

        if found_races:
            print(f"  {place_name}: {len(found_races)}R", end="  ")

        return found_races

    def _quick_check_race(self, race_id):
        """
        レースの存在を高速チェック

        db.netkeiba.comで200 OKならレース存在
        """
        url = f"https://db.netkeiba.com/race/{race_id}/"

        try:
            response = self.session.get(url, timeout=5)

            # 200 OKで、かつエラーメッセージがなければ存在
            if response.status_code == 200:
                # 簡易チェック: レース結果テーブルが存在するか
                if 'race_table_01' in response.text or 'RaceList' in response.text:
                    return True

            return False

        except:
            return False

    def scrape_race_result(self, race_id):
        """レース結果をスクレイピング"""
        url = f"https://db.netkeiba.com/race/{race_id}/"

        try:
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None

            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')

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

        except Exception as e:
            print(f"    エラー: {e}")
            return None

    def update_database(self):
        """
        データベースを更新（2024年8-12月）
        """
        print("\n" + "="*60)
        print("2024年8-12月データ収集開始")
        print("="*60)

        # 既存データ確認
        existing_ids = self.get_existing_race_ids()

        # 2024年8-12月をスキャン
        race_ids = self.scan_2024_races(start_month=8, end_month=12)

        # 新規レースのみフィルタ
        new_race_ids = [rid for rid in race_ids if rid not in existing_ids]

        print(f"\n発見: {len(race_ids)}レース")
        print(f"既存: {len(race_ids) - len(new_race_ids)}レース")
        print(f"新規: {len(new_race_ids)}レース")

        if not new_race_ids:
            print("\n更新不要です。データベースは最新です。")
            return

        # スクレイピング実行
        print("\nレース結果を取得中...")
        print("（10件ごとに自動保存します）\n")

        all_new_data = []
        success = 0
        fail = 0

        for i, race_id in enumerate(new_race_ids, 1):
            print(f"[{i}/{len(new_race_ids)}] {race_id}...", end=" ")

            df = self.scrape_race_result(race_id)

            if df is not None and len(df) > 0:
                all_new_data.append(df)
                success += 1
                print(f"OK ({len(df)}頭)")
            else:
                fail += 1
                print("NG")

            # 10件ごとに保存
            if len(all_new_data) >= 10:
                self._save_batch(all_new_data)
                print(f"  → {len(all_new_data)}件をDBに追加\n")
                all_new_data = []

            time.sleep(1)  # レート制限（1秒待機）

        # 残りを保存
        if all_new_data:
            self._save_batch(all_new_data)
            print(f"\n  → {len(all_new_data)}件をDBに追加")

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


def main():
    """メイン実行"""
    print("\n" + "="*60)
    print("2024年8-12月 欠損データ収集")
    print("="*60)
    print("\n注意: VPN接続を確認してください！")
    print("      NetKeibaのアクセス制限を回避するため、VPN接続が必要です。")
    print("\n収集を開始します...\n")

    collector = MissingDataCollector()
    collector.update_database()

    print("\n処理完了！")


if __name__ == '__main__':
    main()
