"""
2024年の500レースサンプルのオッズを取得してCSVに保存
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
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
            race_id: レースID

        Returns:
            馬番とオッズの辞書、または取得失敗時はNone
        """
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
            print(f"Error scraping race {race_id}: {e}")
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


print("="*80)
print("2024年レースのオッズ取得（500レースサンプル）")
print("="*80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv',
                 encoding='utf-8', low_memory=False)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2024年データ
df_2024 = df[df['date_parsed'] >= '2024-01-01'].copy()
print(f"2024年データ: {len(df_2024):,}件")

# ユニークなレース
unique_races = df_2024['race_id'].unique()
print(f"2024年レース数: {len(unique_races):,}レース")

# 500レースサンプル（均等に分散）
sample_size = 500
step = len(unique_races) // sample_size
sample_races = unique_races[::step][:sample_size]

print(f"サンプルレース数: {len(sample_races)}レース")
print(f"推定時間: {len(sample_races) * 2 / 60:.1f}分")

# スクレイパー初期化
scraper = OddsScraper()

# オッズ取得
success_count = 0
fail_count = 0

odds_results = []

print("\nオッズ取得中...")

for i, race_id in enumerate(sample_races, 1):
    if i % 50 == 0:
        print(f"  進捗: {i}/{len(sample_races)} ({100*i/len(sample_races):.1f}%)")
        print(f"    成功: {success_count}, 失敗: {fail_count}")

    # オッズ取得
    odds_data = scraper.scrape_race_odds(race_id)

    if odds_data and odds_data['odds_data']:
        success_count += 1

        # 各馬のオッズを記録
        for umaban, odds in odds_data['odds_data'].items():
            odds_results.append({
                'race_id': race_id,
                'Umaban': umaban,
                'odds_real': odds
            })
    else:
        fail_count += 1

    # サーバー負荷軽減
    time.sleep(2)

# 結果をDataFrameに変換
odds_df = pd.DataFrame(odds_results)

print(f"\n取得完了")
print(f"成功: {success_count}/{len(sample_races)} ({100*success_count/len(sample_races):.1f}%)")
print(f"取得オッズ数: {len(odds_df):,}件")

# CSVに保存
output_file = 'odds_2024_sample_500.csv'
odds_df.to_csv(output_file, index=False, encoding='utf-8')
print(f"\n保存: {output_file}")

# 統計情報
if len(odds_df) > 0:
    print("\nオッズ統計:")
    print(f"  平均: {odds_df['odds_real'].mean():.2f}倍")
    print(f"  中央値: {odds_df['odds_real'].median():.2f}倍")
    print(f"  最小: {odds_df['odds_real'].min():.2f}倍")
    print(f"  最大: {odds_df['odds_real'].max():.2f}倍")

print("\n" + "="*80)
print("完了")
print("="*80)
