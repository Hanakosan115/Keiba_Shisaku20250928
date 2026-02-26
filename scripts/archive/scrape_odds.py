"""
オッズデータ取得スクリプト

netkeibaから単勝オッズを取得してCSVに追加
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from typing import Dict, Optional

class OddsScraper:
    """オッズ取得クラス"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def scrape_race_odds(self, race_id: str) -> Optional[Dict]:
        """
        レースIDから確定オッズを取得

        Args:
            race_id: レースID（例: "202406010101"）

        Returns:
            馬番とオッズの辞書、または取得失敗時はNone
        """
        # DBページから取得
        url = f"https://db.netkeiba.com/race/{race_id}/"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding

            soup = BeautifulSoup(response.text, 'html.parser')

            # レース結果テーブルから単勝オッズを抽出
            odds_dict = self._extract_odds_from_results(soup)

            if odds_dict:
                return {'race_id': race_id, 'odds_data': odds_dict}
            else:
                return None

        except Exception as e:
            print(f"Error scraping odds for race {race_id}: {e}")
            return None

    def _extract_odds_from_results(self, soup: BeautifulSoup) -> Optional[Dict]:
        """
        レース結果テーブルから単勝オッズを抽出

        Returns:
            {馬番: オッズ} の辞書
        """
        odds_dict = {}

        # レース結果テーブルを探す
        result_table = soup.find('table', class_='race_table_01')
        if not result_table:
            # 別のクラス名を試す
            result_table = soup.find('table', summary='レース結果')

        if not result_table:
            return None

        # テーブルの行を解析
        rows = result_table.find_all('tr')

        for row in rows[1:]:  # ヘッダー行をスキップ
            cells = row.find_all('td')

            if len(cells) < 13:  # 単勝オッズ列（12列目）がない場合
                continue

            try:
                # 馬番を取得（2列目 = インデックス2）
                umaban_cell = cells[2]
                umaban = umaban_cell.get_text(strip=True)
                umaban_num = int(umaban)

                # 単勝オッズを取得（12列目 = インデックス12）
                odds_cell = cells[12]
                odds_text = odds_cell.get_text(strip=True)

                # オッズをfloatに変換
                odds_value = float(odds_text)

                # 妥当な範囲チェック
                if 1.0 <= odds_value <= 999.9:
                    odds_dict[umaban_num] = odds_value

            except (ValueError, AttributeError, IndexError):
                continue

        return odds_dict if odds_dict else None


def test_scraper():
    """スクレイパーのテスト"""
    print("=" * 80)
    print("オッズ取得テスト")
    print("=" * 80)

    scraper = OddsScraper()

    # テスト用レースID
    test_race_ids = [
        "202006010101",  # 2020年6月 札幌
        "202008010105",  # 2020年8月
    ]

    for race_id in test_race_ids:
        print(f"\nレースID: {race_id}")
        print("-" * 80)

        odds_data = scraper.scrape_race_odds(race_id)

        if odds_data and odds_data['odds_data']:
            print(f"OK オッズ取得成功")
            print(f"  取得馬数: {len(odds_data['odds_data'])}頭")
            print(f"  サンプル:")
            for umaban, odds in list(odds_data['odds_data'].items())[:5]:
                print(f"    馬番{umaban}: {odds}倍")
        else:
            print(f"NG オッズ取得失敗")

        time.sleep(2)

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


def add_odds_to_csv(input_csv: str, output_csv: str = None):
    """
    CSVにオッズ情報を追加

    Args:
        input_csv: 入力CSVファイル
        output_csv: 出力CSVファイル（Noneの場合は元ファイルを上書き）
    """
    print("=" * 80)
    print("CSVへのオッズ追加")
    print("=" * 80)

    # CSV読み込み
    print("\nCSV読み込み中...")
    df = pd.read_csv(input_csv, encoding='utf-8', low_memory=False)
    print(f"総レコード数: {len(df)}")

    # オッズ列を初期化（既存の列を保持）
    if 'odds_scraped' not in df.columns:
        df['odds_scraped'] = None

    # スクレイパー初期化
    scraper = OddsScraper()

    # レースごとに処理
    unique_races = df['race_id'].unique()
    print(f"ユニークなレース数: {len(unique_races)}")

    success_count = 0
    fail_count = 0

    for i, race_id in enumerate(unique_races, 1):
        if i % 100 == 0:
            print(f"  進捗: {i}/{len(unique_races)} ({100*i/len(unique_races):.1f}%)")
            print(f"    成功: {success_count}, 失敗: {fail_count}")

        # オッズ取得
        odds_data = scraper.scrape_race_odds(race_id)

        if odds_data and odds_data['odds_data']:
            success_count += 1

            # 同一レースの各馬にオッズを設定
            race_mask = df['race_id'] == race_id

            for idx in df[race_mask].index:
                umaban = df.loc[idx, 'Umaban']
                if pd.notna(umaban):
                    umaban_int = int(umaban)
                    if umaban_int in odds_data['odds_data']:
                        df.loc[idx, 'odds_scraped'] = odds_data['odds_data'][umaban_int]
        else:
            fail_count += 1

        # サーバー負荷軽減
        time.sleep(2)

    # CSV保存
    if output_csv is None:
        output_csv = input_csv

    print(f"\nCSV保存中: {output_csv}")
    df.to_csv(output_csv, index=False, encoding='utf-8')
    print("完了！")

    # 統計情報
    print("\n" + "=" * 80)
    print("オッズ取得統計")
    print("=" * 80)
    print(f"処理レース数: {len(unique_races)}")
    print(f"成功: {success_count} ({100*success_count/len(unique_races):.1f}%)")
    print(f"失敗: {fail_count} ({100*fail_count/len(unique_races):.1f}%)")

    odds_count = df['odds_scraped'].notna().sum()
    print(f"\nオッズが取得できた馬: {odds_count}/{len(df)} ({100*odds_count/len(df):.1f}%)")

    if odds_count > 0:
        print(f"\nオッズ統計:")
        print(f"  平均: {df['odds_scraped'].mean():.2f}倍")
        print(f"  中央値: {df['odds_scraped'].median():.2f}倍")
        print(f"  最小: {df['odds_scraped'].min():.2f}倍")
        print(f"  最大: {df['odds_scraped'].max():.2f}倍")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_scraper()
    elif len(sys.argv) > 1 and sys.argv[1] == 'add':
        input_file = "netkeiba_data_2020_2024_enhanced.csv"
        output_file = "netkeiba_data_2020_2024_enhanced_with_odds.csv"
        add_odds_to_csv(input_file, output_file)
    else:
        print("使用方法:")
        print("  テスト: py scrape_odds.py test")
        print("  CSV追加: py scrape_odds.py add")
