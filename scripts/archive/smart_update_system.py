"""
スマート自動更新システム
- データベース最終更新日を自動検出
- 欠損期間を自動補完
- 重複を完全排除
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime, timedelta
import re

class SmartUpdater:
    """スマート更新システム"""

    def __init__(self, db_path='netkeiba_data_2020_2024_enhanced.csv'):
        self.db_path = db_path
        self.session = requests.Session()
        # User-Agentヘッダーを追加
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_last_update_date(self):
        """
        データベースの最終更新日を取得

        Returns:
            datetime: 最終更新日（データがない場合は30日前）
        """
        try:
            df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)

            # date カラムから最新日付を取得
            if 'date' in df.columns:
                df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
                last_date = df['date_parsed'].max()

                if pd.notna(last_date):
                    print(f"✓ データベース最終更新: {last_date.strftime('%Y-%m-%d')}")
                    return last_date

            print("! 日付情報が見つかりません")
            return datetime.now() - timedelta(days=30)

        except FileNotFoundError:
            print("! データベースが存在しません（新規作成）")
            return datetime.now() - timedelta(days=30)

        except Exception as e:
            print(f"! エラー: {e}")
            return datetime.now() - timedelta(days=30)

    def get_existing_race_ids(self):
        """
        既存のレースIDセットを取得（重複チェック用）

        Returns:
            set: 既存レースIDのセット
        """
        try:
            df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
            df['race_id'] = df['race_id'].astype(str)

            existing_ids = set(df['race_id'].unique())
            print(f"✓ 既存レース数: {len(existing_ids)}件")

            return existing_ids

        except:
            print("! 既存データなし")
            return set()

    def calculate_update_period(self, last_date=None):
        """
        更新期間を自動計算

        Args:
            last_date: 最終更新日（Noneの場合は自動検出）

        Returns:
            tuple: (開始日, 終了日, 更新日数)
        """
        if last_date is None:
            last_date = self.get_last_update_date()

        today = datetime.now()

        # 最終更新日の翌日から今日まで
        start_date = last_date + timedelta(days=1)
        end_date = today

        days = (end_date - start_date).days

        print(f"\n更新期間:")
        print(f"  開始: {start_date.strftime('%Y-%m-%d')}")
        print(f"  終了: {end_date.strftime('%Y-%m-%d')}")
        print(f"  日数: {days}日間")

        return start_date, end_date, days

    def get_race_ids_in_period(self, start_date, end_date):
        """
        指定期間のレースIDを取得（土日のみ）

        Args:
            start_date: 開始日
            end_date: 終了日

        Returns:
            list: レースIDのリスト
        """
        race_ids = []
        current_date = start_date

        print(f"\n期間内の開催日を検索中...")

        while current_date <= end_date:
            # 土日のみ
            if current_date.weekday() in [5, 6]:  # 土=5, 日=6
                date_str = current_date.strftime('%Y%m%d')
                day_name = '土曜' if current_date.weekday() == 5 else '日曜'

                print(f"\n{current_date.strftime('%Y-%m-%d')} ({day_name})")

                # カレンダーページから取得
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
                        print(f"  レース: {len(found_races)}件")
                        race_ids.extend(sorted(found_races))
                    else:
                        print(f"  レースなし（平日開催なしor休催）")

                    time.sleep(1)

                except Exception as e:
                    print(f"  エラー: {e}")

            current_date += timedelta(days=1)

        return race_ids

    def scrape_race_result(self, race_id):
        """レース結果をスクレイピング"""
        # DBページから取得（こちらの方が安定）
        url = f"https://db.netkeiba.com/race/{race_id}/"

        try:
            response = self.session.get(url, timeout=10)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')

            # レース名
            race_name_elem = soup.find('h1', class_='raceTitle')
            if not race_name_elem:
                race_name_elem = soup.find('div', class_='mainrace_data').find('h1') if soup.find('div', class_='mainrace_data') else None
            race_name = race_name_elem.text.strip() if race_name_elem else 'N/A'

            # レースデータ（距離、馬場など）
            race_data_elem = soup.find('div', class_='racedata')
            if not race_data_elem:
                race_data_elem = soup.find('p', class_='smalltxt')

            race_data_text = race_data_elem.text.strip() if race_data_elem else ''

            # 距離
            distance_match = re.search(r'(\d+)m', race_data_text)
            distance = int(distance_match.group(1)) if distance_match else None

            # 馬場状態
            track_match = re.search(r'馬場:(\S+)', race_data_text)
            track_condition = track_match.group(1) if track_match else None

            # 天気
            weather_match = re.search(r'天候:(\S+)', race_data_text)
            weather = weather_match.group(1) if weather_match else None

            # 日付
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', race_data_text)
            if date_match:
                year, month, day = date_match.groups()
                race_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            else:
                race_date = None

            # 結果テーブル
            result_table = soup.find('table', class_='race_table_01')
            if not result_table:
                result_table = soup.find('table', summary='レース結果')

            if not result_table:
                return None

            horses_data = []
            rows = result_table.find_all('tr')[1:]  # ヘッダー除く

            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 13:  # 最低限必要な列数
                    continue

                try:
                    # 着順（0列目）
                    rank_text = cols[0].text.strip()
                    rank = int(rank_text)

                    # 枠番（1列目）
                    waku = int(cols[1].text.strip())

                    # 馬番（2列目）
                    umaban = int(cols[2].text.strip())

                    # 馬名（4列目）- 3列目は印
                    horse_elem = cols[4].find('a')
                    horse_name = horse_elem.text.strip() if horse_elem else cols[4].text.strip()
                    horse_url = horse_elem.get('href', '') if horse_elem else ''
                    horse_id = horse_url.split('/')[-2] if '/horse/' in horse_url else None

                    # 性齢（5列目）
                    sex_age = cols[5].text.strip()

                    # 斤量（6列目）
                    kinryo = float(cols[6].text.strip())

                    # 騎手（7列目）
                    jockey_elem = cols[7].find('a')
                    jockey_name = jockey_elem.text.strip() if jockey_elem else cols[7].text.strip()

                    # タイム（8列目）
                    race_time = cols[8].text.strip()

                    # 着差（9列目）
                    diff = cols[9].text.strip()

                    # 通過順（10列目）
                    passage = cols[10].text.strip() if len(cols) > 10 else ''

                    # 上がり（11列目）
                    agari = cols[11].text.strip() if len(cols) > 11 else ''

                    # オッズ（12列目）
                    try:
                        odds = float(cols[12].text.strip()) if len(cols) > 12 else None
                    except:
                        odds = None

                    # 人気（13列目）
                    try:
                        ninki = int(cols[13].text.strip()) if len(cols) > 13 else None
                    except:
                        ninki = None

                    # 馬体重（14列目）
                    weight_info = cols[14].text.strip() if len(cols) > 14 else ''

                    # 調教師（最終列付近）
                    trainer_elem = cols[-1].find('a') if len(cols) > 16 else None
                    trainer_name = trainer_elem.text.strip() if trainer_elem else 'N/A'

                except (ValueError, IndexError, AttributeError):
                    continue

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

            return pd.DataFrame(horses_data) if horses_data else None

        except Exception as e:
            print(f"    エラー: {e}")
            import traceback
            traceback.print_exc()
            return None

    def scrape_horse_past_ranks(self, horse_id, num_races=5):
        """馬の過去着順を取得"""
        url = f"https://db.netkeiba.com/horse/{horse_id}"

        try:
            response = self.session.get(url, timeout=10)
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

    def update_database(self, force_days=None):
        """
        データベースをスマート更新

        Args:
            force_days: 強制的に指定日数分を更新（Noneの場合は自動検出）

        Returns:
            DataFrame: 更新後のデータフレーム
        """
        print("="*80)
        print("スマートデータ更新システム")
        print("="*80)

        # 既存レースID取得（重複チェック用）
        existing_race_ids = self.get_existing_race_ids()

        # 更新期間を計算
        if force_days:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=force_days)
            print(f"\n強制更新モード: 過去{force_days}日間")
        else:
            last_date = self.get_last_update_date()
            start_date, end_date, days = self.calculate_update_period(last_date)

            if days <= 0:
                print("\n✓ データベースは最新です")
                return

            if days > 90:
                print(f"\n警告: {days}日間のデータが不足しています")
                confirm = input("続行しますか？ (y/n): ").strip().lower()
                if confirm != 'y':
                    return

        # 期間内のレースID取得
        all_race_ids = self.get_race_ids_in_period(start_date, end_date)

        if len(all_race_ids) == 0:
            print("\n更新するレースが見つかりませんでした")
            return

        # 重複を除外
        new_race_ids = [rid for rid in all_race_ids if rid not in existing_race_ids]
        duplicate_count = len(all_race_ids) - len(new_race_ids)

        print(f"\n" + "="*80)
        print(f"更新サマリー")
        print("="*80)
        print(f"発見レース: {len(all_race_ids)}件")
        print(f"既存レース: {duplicate_count}件（スキップ）")
        print(f"新規レース: {len(new_race_ids)}件")

        if len(new_race_ids) == 0:
            print("\n✓ 新規レースはありません")
            return

        # 既存データベース読み込み
        try:
            main_df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
            main_df['race_id'] = main_df['race_id'].astype(str)
            print(f"\n既存データ: {len(main_df):,}件")
        except:
            print("\n新規データベースを作成します")
            main_df = pd.DataFrame()

        # スクレイピング実行
        print(f"\n" + "="*80)
        print(f"スクレイピング開始（{len(new_race_ids)}レース）")
        print("="*80)

        all_new_data = []
        success_count = 0
        fail_count = 0

        for i, race_id in enumerate(new_race_ids, 1):
            print(f"\n[{i}/{len(new_race_ids)}] レースID: {race_id}")

            # レース結果取得
            race_df = self.scrape_race_result(race_id)

            if race_df is None or len(race_df) == 0:
                print("  ✗ スキップ（データなし）")
                fail_count += 1
                continue

            print(f"  ✓ {race_df.iloc[0]['race_name']} - {len(race_df)}頭")

            # 過去着順を追加
            for idx, row in race_df.iterrows():
                horse_id = row['horse_id']
                if horse_id:
                    past_ranks = self.scrape_horse_past_ranks(horse_id, num_races=5)

                    for j in range(5):
                        if j < len(past_ranks):
                            race_df.at[idx, f'past_rank_{j+1}'] = past_ranks[j]

                    time.sleep(0.3)  # 負荷軽減

            all_new_data.append(race_df)
            success_count += 1
            time.sleep(1)

        # 結果サマリー
        print(f"\n" + "="*80)
        print("スクレイピング完了")
        print("="*80)
        print(f"成功: {success_count}件")
        print(f"失敗: {fail_count}件")

        if len(all_new_data) == 0:
            print("\n新しいデータが取得できませんでした")
            return

        # 新データを結合
        new_df = pd.concat(all_new_data, ignore_index=True)
        new_df['race_id'] = new_df['race_id'].astype(str)

        print(f"\n新規レコード: {len(new_df):,}件")

        # 念のため重複削除（race_id + Umaban でユニーク）
        if len(main_df) > 0:
            # 既存データから今回取得したrace_idを削除
            main_df = main_df[~main_df['race_id'].isin(new_df['race_id'].unique())]

        # 結合
        updated_df = pd.concat([main_df, new_df], ignore_index=True)

        # 重複チェック（念のため）
        before_dedup = len(updated_df)
        updated_df = updated_df.drop_duplicates(subset=['race_id', 'Umaban'], keep='last')
        after_dedup = len(updated_df)

        if before_dedup != after_dedup:
            print(f"\n重複削除: {before_dedup - after_dedup}件")

        # 保存
        updated_df.to_csv(self.db_path, index=False, encoding='utf-8')

        print(f"\n" + "="*80)
        print("✓ 更新完了！")
        print("="*80)
        print(f"総レコード数: {len(updated_df):,}件")
        print(f"追加: {len(new_df):,}件")
        print(f"保存先: {self.db_path}")

        return updated_df

def main():
    """メイン処理"""
    updater = SmartUpdater()

    print("\n更新モードを選択してください:")
    print("  1. 自動検出（推奨）- 最終更新日から今日まで")
    print("  2. 手動指定 - 過去N日間を強制更新")

    choice = input("> ").strip()

    if choice == '2':
        days_input = input("\n何日前まで遡りますか？: ").strip()
        if days_input.isdigit():
            updater.update_database(force_days=int(days_input))
        else:
            print("無効な入力です")
    else:
        updater.update_database()

if __name__ == "__main__":
    main()
