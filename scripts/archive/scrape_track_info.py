"""
馬場情報取得スクリプト

取得する情報:
1. 開催週数（開幕週判定）
2. 馬場状態（芝/ダート）
3. 天候
4. 競馬場名
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import time
import re
from typing import Dict, Optional

class TrackInfoScraper:
    """馬場情報取得クラス"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

        # 競馬場コードマッピング
        self.track_codes = {
            '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
            '05': '東京', '06': '中山', '07': '中京', '08': '京都',
            '09': '阪神', '10': '小倉'
        }

        # 馬場状態マッピング
        self.condition_map = {
            '良': 1, '稍': 2, '稍重': 2, '重': 3, '不': 4, '不良': 4
        }

    def scrape_track_info(self, race_id: str) -> Optional[Dict]:
        """
        レースIDから馬場情報を取得

        Args:
            race_id: レースID（例: "202006010101"）

        Returns:
            馬場情報の辞書、または取得失敗時はNone
        """
        # DBページから取得
        url = f"https://db.netkeiba.com/race/{race_id}/"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding

            soup = BeautifulSoup(response.text, 'html.parser')
            all_text = soup.get_text()

            # レースIDから基本情報を抽出
            track_info = self._parse_race_id(race_id)

            # 開催情報を抽出
            kaisai_info = self._extract_kaisai_info(all_text)
            if kaisai_info:
                track_info.update(kaisai_info)

            # 馬場状態を抽出
            condition_info = self._extract_track_condition(all_text)
            if condition_info:
                track_info.update(condition_info)

            # 天候を抽出
            weather = self._extract_weather(all_text)
            if weather:
                track_info['weather'] = weather

            track_info['race_id'] = race_id
            return track_info

        except Exception as e:
            print(f"Error scraping track info for race {race_id}: {e}")
            return None

    def _parse_race_id(self, race_id: str) -> Dict:
        """
        レースIDから基本情報を抽出

        race_id format: YYYYMMDDKKVV
        - YYYY: 年
        - MM: 月
        - DD: 日
        - KK: 競馬場コード
        - VV: レース番号
        """
        year = race_id[:4]
        month = race_id[4:6]
        day = race_id[6:8]
        track_code = race_id[8:10]
        race_num = race_id[10:12]

        track_name = self.track_codes.get(track_code, f'不明({track_code})')

        return {
            'year': int(year),
            'month': int(month),
            'day': int(day),
            'track_code': track_code,
            'track_name': track_name,
            'race_number': int(race_num)
        }

    def _extract_kaisai_info(self, text: str) -> Optional[Dict]:
        """
        開催情報を抽出

        例: "1回札幌1日" → 第1回開催の1日目 → 1週目
        """
        # パターン: ○回○○○日
        kaisai_pattern = r'(\d+)回.+?(\d+)日'
        match = re.search(kaisai_pattern, text)

        if match:
            kai_num = int(match.group(1))  # 第何回開催
            day_num = int(match.group(2))  # 何日目

            # 開催週数を計算（通常3日で1週）
            # 1-3日目 → 1週目、4-6日目 → 2週目、...
            week_num = (day_num - 1) // 3 + 1

            # 開幕週フラグ（1週目なら1、それ以外は0）
            is_opening_week = 1 if week_num == 1 else 0

            return {
                'kaisai_count': kai_num,
                'kaisai_day': day_num,
                'week_number': week_num,
                'is_opening_week': is_opening_week
            }

        return None

    def _extract_track_condition(self, text: str) -> Optional[Dict]:
        """
        馬場状態を抽出

        例: "芝:良", "ダート:稍重"
        """
        result = {}

        # 芝の馬場状態
        turf_pattern = r'芝\s*:\s*([良稍重不]{1,2})'
        turf_match = re.search(turf_pattern, text)
        if turf_match:
            condition = turf_match.group(1)
            result['turf_condition'] = condition
            result['turf_condition_code'] = self.condition_map.get(condition, 0)

        # ダートの馬場状態
        dirt_pattern = r'ダート\s*:\s*([良稍重不]{1,2})'
        dirt_match = re.search(dirt_pattern, text)
        if dirt_match:
            condition = dirt_match.group(1)
            result['dirt_condition'] = condition
            result['dirt_condition_code'] = self.condition_map.get(condition, 0)

        return result if result else None

    def _extract_weather(self, text: str) -> Optional[str]:
        """
        天候を抽出

        例: "天候:晴"
        """
        weather_pattern = r'天候\s*:\s*([晴曇雨雪]{1,2})'
        match = re.search(weather_pattern, text)
        if match:
            return match.group(1)
        return None


def test_scraper():
    """スクレイパーのテスト"""
    print("=" * 80)
    print("馬場情報取得テスト")
    print("=" * 80)

    scraper = TrackInfoScraper()

    # テスト用レースID
    test_race_ids = [
        "202006010101",  # 2020年6月 札幌
        "202008050811",  # 2020年8月 京都
    ]

    for race_id in test_race_ids:
        print(f"\nレースID: {race_id}")
        print("-" * 80)

        track_info = scraper.scrape_track_info(race_id)

        if track_info:
            print(f"OK 馬場情報取得成功")
            for key, value in track_info.items():
                print(f"  {key}: {value}")
        else:
            print(f"NG 馬場情報取得失敗")

        time.sleep(2)

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_scraper()
    else:
        print("使用方法:")
        print("  テスト: py scrape_track_info.py test")
