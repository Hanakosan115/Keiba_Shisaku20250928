"""
ラップタイム取得スクリプト

netkeibaのレース結果ページからラップタイムを取得し、
既存のCSVデータに追加する。

取得するデータ:
- 200mラップ
- 400mラップ
- ペース判定（slow/medium/fast）
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import time
import re
from typing import Dict, List, Optional, Tuple
import sys
from data_config import MAIN_CSV

class LapTimeScraper:
    """ラップタイム取得クラス"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def scrape_race_lap_times(self, race_id: str) -> Optional[Dict]:
        """
        レースIDからラップタイムを取得

        Args:
            race_id: レースID（例: "202411090411"）

        Returns:
            ラップタイム情報の辞書、または取得失敗時はNone
        """
        # DBページからラップタイムを取得
        url = f"https://db.netkeiba.com/race/{race_id}/"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding

            soup = BeautifulSoup(response.text, 'html.parser')

            # ラップタイム情報を取得
            lap_data = self._extract_lap_times_from_db(soup)

            if lap_data:
                # ペース判定を追加
                lap_data['pace_category'] = self._classify_pace(lap_data)
                lap_data['race_id'] = race_id
                return lap_data

            return None

        except Exception as e:
            print(f"Error scraping race {race_id}: {e}")
            return None

    def _extract_lap_times_from_db(self, soup: BeautifulSoup) -> Optional[Dict]:
        """
        DBページ（db.netkeiba.com）からラップタイムを抽出

        テーブル構造:
        <table summary="ラップタイム">
          <tr><th>ラップ</th><td>11.9 - 10.8 - 11.2 - 12.5...</td></tr>
          <tr><th>ペース</th><td>11.9 - 22.7 - 33.9...</td></tr>
        </table>
        """
        # ラップタイムテーブルを探す
        lap_table = soup.find('table', summary='ラップタイム')
        if not lap_table:
            # summaryがない場合、他の方法で探す
            lap_table = soup.find('table', class_='result_table_02')

        if not lap_table:
            return None

        # テーブルの行を取得
        rows = lap_table.find_all('tr')

        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                header = cells[0].get_text(strip=True)
                if header == 'ラップ' or 'ラップ' in header:
                    # ラップタイムの行を見つけた
                    lap_text = cells[1].get_text(strip=True)
                    # "11.9 - 10.8 - 11.2 - 12.5..." という形式をパース
                    lap_values = [part.strip() for part in lap_text.split('-')]

                    # 数値に変換
                    laps = []
                    for val in lap_values:
                        try:
                            lap_float = float(val)
                            # 妥当な範囲のラップタイム（10.0～20.0秒）
                            if 10.0 <= lap_float <= 20.0:
                                laps.append(lap_float)
                        except ValueError:
                            continue

                    if laps and len(laps) >= 3:
                        return {
                            'laps': laps,
                            'lap_count': len(laps)
                        }

        return None

    def _extract_lap_times(self, soup: BeautifulSoup) -> Optional[Dict]:
        """
        HTMLからラップタイムを抽出

        netkeibaのページ構造:
        - ラップタイムは通常「ラップ」というテキストの後に表示
        - "12.1 - 11.8 - 11.5 - ..." のような形式
        """
        lap_data = {}

        # パターン1: テーブル内のラップタイム
        tables = soup.find_all('table')
        for table in tables:
            # "ラップ"を含む行を探す
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                for i, cell in enumerate(cells):
                    cell_text = cell.get_text(strip=True)

                    # "ラップ"のキーワードを探す
                    if 'ラップ' in cell_text or 'LAP' in cell_text.upper():
                        # 次のセルにラップタイムがあるはず
                        if i + 1 < len(cells):
                            lap_text = cells[i + 1].get_text(strip=True)
                            laps = self._parse_lap_string(lap_text)
                            if laps:
                                lap_data['laps'] = laps
                                lap_data['lap_count'] = len(laps)
                                return lap_data

        # パターン2: div要素内のラップタイム
        race_data_divs = soup.find_all('div', class_=re.compile(r'RaceData|race_data|lap', re.I))
        for div in race_data_divs:
            text = div.get_text()
            if 'ラップ' in text or 'LAP' in text.upper():
                # ラップタイムのパターンを探す: "12.1-11.8-11.5" or "12.1 - 11.8 - 11.5"
                lap_pattern = r'(\d{1,2}\.\d)\s*-\s*(\d{1,2}\.\d)'
                matches = re.findall(lap_pattern, text)
                if matches:
                    # マッチした全ての数値を取得
                    laps = []
                    for match in matches:
                        laps.extend([float(x) for x in match])
                    # 重複を削除（最初の出現を保持）
                    seen = set()
                    unique_laps = []
                    for lap in laps:
                        if lap not in seen:
                            seen.add(lap)
                            unique_laps.append(lap)

                    if unique_laps:
                        lap_data['laps'] = unique_laps
                        lap_data['lap_count'] = len(unique_laps)
                        return lap_data

        # パターン3: スパン要素やテキストノードから直接
        all_text = soup.get_text()
        if 'ラップ' in all_text:
            # "ラップ"の後のテキストを抽出
            lap_section = all_text[all_text.find('ラップ'):]
            # 最初の500文字程度を対象
            lap_section = lap_section[:500]

            # 数値パターンを探す
            lap_pattern = r'(\d{1,2}\.\d)'
            matches = re.findall(lap_pattern, lap_section)
            if matches:
                laps = [float(x) for x in matches if 10.0 <= float(x) <= 20.0]  # 妥当な範囲
                if len(laps) >= 3:  # 最低3つのラップがあれば
                    lap_data['laps'] = laps
                    lap_data['lap_count'] = len(laps)
                    return lap_data

        return None

    def _parse_lap_string(self, lap_string: str) -> Optional[List[float]]:
        """
        ラップタイム文字列をパースして数値のリストに変換

        Args:
            lap_string: "12.1-11.8-11.5" or "12.1 - 11.8 - 11.5"

        Returns:
            ラップタイムのリスト
        """
        # ハイフンやスペースで区切る
        parts = re.split(r'[-\s]+', lap_string)

        laps = []
        for part in parts:
            part = part.strip()
            # 数値パターンにマッチするか確認
            if re.match(r'^\d{1,2}\.\d$', part):
                lap_time = float(part)
                # 妥当な範囲のラップタイムのみ（10.0秒～20.0秒）
                if 10.0 <= lap_time <= 20.0:
                    laps.append(lap_time)

        return laps if len(laps) >= 3 else None

    def _classify_pace(self, lap_data: Dict) -> str:
        """
        ラップタイムからペースを判定

        前半3F vs 後半3Fで判定:
        - slow: 前半が遅い（後半との差が大きい）
        - medium: 平均的
        - fast: 前半が速い
        """
        laps = lap_data.get('laps', [])
        if len(laps) < 6:
            return 'unknown'

        # 前半3F（最初の3つのハロン）の平均
        first_3f = np.mean(laps[:3])

        # 後半3F（最後の3つのハロン）の平均
        last_3f = np.mean(laps[-3:])

        # 差分で判定
        diff = first_3f - last_3f

        if diff > 0.5:
            return 'slow'  # 前半遅い→スローペース
        elif diff < -0.5:
            return 'fast'  # 前半速い→ハイペース
        else:
            return 'medium'  # 平均的

    def calculate_pace_features(self, laps: List[float]) -> Dict:
        """
        ラップタイムから詳細なペース特徴量を計算

        Returns:
            ペース関連の特徴量辞書
        """
        if not laps or len(laps) < 4:
            return {
                'first_3f_avg': None,
                'last_3f_avg': None,
                'pace_variance': None,
                'pace_acceleration': None
            }

        laps_array = np.array(laps)

        # 前半3Fの平均
        first_3f = np.mean(laps_array[:3]) if len(laps) >= 3 else None

        # 後半3Fの平均
        last_3f = np.mean(laps_array[-3:]) if len(laps) >= 3 else None

        # ペースの分散（安定性）
        pace_variance = np.var(laps_array)

        # ペースの加速度（後半にかけての変化）
        if len(laps) >= 4:
            pace_acceleration = np.mean(laps_array[-2:]) - np.mean(laps_array[:2])
        else:
            pace_acceleration = None

        return {
            'first_3f_avg': first_3f,
            'last_3f_avg': last_3f,
            'pace_variance': pace_variance,
            'pace_acceleration': pace_acceleration
        }


def test_scraper():
    """スクレイパーのテスト"""
    print("=" * 80)
    print("ラップタイム取得テスト")
    print("=" * 80)

    scraper = LapTimeScraper()

    # テスト用レースID（DBページに登録されているレース）
    test_race_ids = [
        "202006010101",  # 2020年6月1日
        "202008010105",  # 2020年8月1日
        "202308050811",  # 2023年8月5日
    ]

    for race_id in test_race_ids:
        print(f"\nレースID: {race_id}")
        print("-" * 80)

        lap_data = scraper.scrape_race_lap_times(race_id)

        if lap_data:
            print(f"OK ラップタイム取得成功")
            print(f"  ラップ数: {lap_data['lap_count']}")
            print(f"  ラップタイム: {lap_data['laps']}")
            print(f"  ペース判定: {lap_data['pace_category']}")

            # 詳細特徴量を計算
            features = scraper.calculate_pace_features(lap_data['laps'])
            print(f"  前半3F平均: {features['first_3f_avg']:.2f}秒" if features['first_3f_avg'] else "  前半3F平均: N/A")
            print(f"  後半3F平均: {features['last_3f_avg']:.2f}秒" if features['last_3f_avg'] else "  後半3F平均: N/A")
        else:
            print(f"NG ラップタイム取得失敗")

        # 次のリクエストまで待機（サーバー負荷軽減）
        time.sleep(2)

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


def add_lap_times_to_csv(csv_path: str, output_path: str = None, max_races: int = None):
    """
    既存CSVにラップタイム情報を追加

    Args:
        csv_path: 入力CSVパス
        output_path: 出力CSVパス（Noneの場合は元ファイルを上書き）
        max_races: 処理する最大レース数（テスト用）
    """
    print("=" * 80)
    print("CSVへのラップタイム追加")
    print("=" * 80)

    # CSV読み込み
    print("\nCSV読み込み中...")
    df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
    print(f"総レコード数: {len(df)}")

    # ユニークなレースIDを取得
    unique_race_ids = df['race_id'].unique()
    print(f"ユニークなレース数: {len(unique_race_ids)}")

    if max_races:
        unique_race_ids = unique_race_ids[:max_races]
        print(f"処理対象: {len(unique_race_ids)}レース（テストモード）")

    # 新しい列を初期化
    df['laps'] = None
    df['lap_count'] = 0
    df['pace_category'] = 'unknown'
    df['first_3f_avg'] = np.nan
    df['last_3f_avg'] = np.nan
    df['pace_variance'] = np.nan
    df['pace_acceleration'] = np.nan

    # スクレイパー初期化
    scraper = LapTimeScraper()

    # 各レースのラップタイムを取得
    success_count = 0
    fail_count = 0

    print("\nラップタイム取得中...")
    for i, race_id in enumerate(unique_race_ids, 1):
        if i % 10 == 0:
            print(f"  進捗: {i}/{len(unique_race_ids)} ({100*i/len(unique_race_ids):.1f}%)")
            print(f"    成功: {success_count}, 失敗: {fail_count}")

        lap_data = scraper.scrape_race_lap_times(race_id)

        if lap_data:
            success_count += 1

            # このレースIDの全行に情報を追加
            mask = df['race_id'] == race_id
            df.loc[mask, 'laps'] = str(lap_data['laps'])
            df.loc[mask, 'lap_count'] = lap_data['lap_count']
            df.loc[mask, 'pace_category'] = lap_data['pace_category']

            # 詳細特徴量を計算
            features = scraper.calculate_pace_features(lap_data['laps'])
            df.loc[mask, 'first_3f_avg'] = features['first_3f_avg']
            df.loc[mask, 'last_3f_avg'] = features['last_3f_avg']
            df.loc[mask, 'pace_variance'] = features['pace_variance']
            df.loc[mask, 'pace_acceleration'] = features['pace_acceleration']
        else:
            fail_count += 1

        # サーバー負荷軽減のため待機
        time.sleep(2)

    print("\n" + "=" * 80)
    print("結果サマリー")
    print("=" * 80)
    print(f"処理レース数: {len(unique_race_ids)}")
    print(f"成功: {success_count} ({100*success_count/len(unique_race_ids):.1f}%)")
    print(f"失敗: {fail_count} ({100*fail_count/len(unique_race_ids):.1f}%)")

    # CSV保存
    if output_path is None:
        output_path = csv_path

    print(f"\nCSV保存中: {output_path}")
    df.to_csv(output_path, index=False, encoding='utf-8')
    print("完了！")


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        # テストモード
        test_scraper()
    elif len(sys.argv) > 1 and sys.argv[1] == 'add':
        # CSV追加モード
        max_races = int(sys.argv[2]) if len(sys.argv) > 2 else None
        output_file = "netkeiba_data_2020_2024_clean_with_class_and_laps.csv"
        add_lap_times_to_csv(MAIN_CSV, output_file, max_races)
    else:
        print("使用方法:")
        print("  テスト: py scrape_lap_times.py test")
        print("  CSV追加: py scrape_lap_times.py add [最大レース数]")
        print("  例: py scrape_lap_times.py add 10  # 最初の10レースのみ")
