"""
スマート自動更新システム v2
動作確認済みのスクレイピングロジックを使用
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime, timedelta
import re

class SmartUpdaterV2:
    """スマート更新システム v2"""

    def __init__(self, db_path='netkeiba_data_2020_2024_enhanced.csv'):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def get_last_update_date(self):
        """データベースの最終更新日を取得"""
        try:
            df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
            if 'date' in df.columns:
                df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
                last_date = df['date_parsed'].max()
                if pd.notna(last_date):
                    print(f"✓ データベース最終更新: {last_date.strftime('%Y-%m-%d')}")
                    return last_date
            return datetime.now() - timedelta(days=30)
        except:
            print("! 既存データベースなし")
            return datetime.now() - timedelta(days=30)

    def get_existing_race_ids(self):
        """既存のレースIDセットを取得"""
        try:
            df = pd.read_csv(self.db_path, encoding='utf-8', low_memory=False)
            df['race_id'] = df['race_id'].astype(str)
            existing_ids = set(df['race_id'].unique())
            print(f"✓ 既存レース数: {len(existing_ids)}件")
            return existing_ids
        except:
            return set()

    def get_race_ids_in_period(self, start_date, end_date):
        """
        指定期間のレースIDを取得（カレンダーページから）

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
            # 土日のみ（平日開催もあるが主に土日）
            if current_date.weekday() in [5, 6]:  # 土=5, 日=6
                date_str = current_date.strftime('%Y%m%d')
                day_name = '土曜' if current_date.weekday() == 5 else '日曜'

                print(f"\n{current_date.strftime('%Y-%m-%d')} ({day_name})")

                # カレンダーページから取得
                calendar_url = f"https://race.netkeiba.com/top/race_list.html?date={date_str}"

                try:
                    response = self.session.get(calendar_url, timeout=10)
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
                        print(f"  レースなし（休催）")

                    time.sleep(1)  # レート制限

                except Exception as e:
                    print(f"  エラー: {e}")

            current_date += timedelta(days=1)

        print(f"\n合計取得レース: {len(race_ids)}件")
        return race_ids

    def scrape_race_result(self, race_id):
        """レース結果をスクレイピング（動作確認済み版）"""
        url = f'https://db.netkeiba.com/race/{race_id}/'

        try:
            response = self.session.get(url, timeout=10)

            # 404やエラーの場合はスキップ
            if response.status_code != 200:
                return None

            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')

            # テーブル取得
            result_table = soup.find('table', class_='race_table_01')
            if not result_table:
                return None

            # レース名（h1タグの2番目、classなし）
            h1_tags = soup.find_all('h1')
            race_name = h1_tags[1].text.strip() if len(h1_tags) > 1 else 'N/A'

            # レースデータ（p.smalltxt または div.data_intro）
            race_data_elem = soup.find('p', class_='smalltxt')
            race_data_text = race_data_elem.text.strip() if race_data_elem else ''

            # 距離は data_intro からも取得を試みる
            if not race_data_text:
                data_intro = soup.find('div', class_='data_intro')
                race_data_text = data_intro.text.strip() if data_intro else ''

            # 距離
            distance_match = re.search(r'(\d+)m', race_data_text)
            distance = int(distance_match.group(1)) if distance_match else None

            # 馬場状態
            track_match = re.search(r'馬場:(\S+)', race_data_text)
            track_condition = track_match.group(1) if track_match else None

            # 日付
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', race_data_text)
            if date_match:
                year, month, day = date_match.groups()
                race_date = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            else:
                race_date = None

            # データ抽出
            rows = result_table.find_all('tr')[1:]  # ヘッダー除く
            horses = []

            for row in rows:
                cols = row.find_all('td')

                if len(cols) < 13:
                    continue

                try:
                    # 新しい列構造に対応（21列）
                    # [0]着順 [1]枠番 [2]馬番 [3]馬名 [4]性齢 [5]斤量 [6]騎手 [7]タイム
                    # [8]着差 [9]タイム指数 [10]通過 [11]上り [12]単勝 [13]人気 [14]馬体重
                    # [15]調教タイム [16]厩舎コメント [17]備考 [18]調教師 [19]馬主 [20]賞金

                    rank = int(cols[0].text.strip())
                    waku = int(cols[1].text.strip())
                    umaban = int(cols[2].text.strip())

                    # 馬名（3列目）
                    horse_elem = cols[3].find('a')
                    horse_name = horse_elem.text.strip() if horse_elem else cols[3].text.strip()
                    horse_url = horse_elem.get('href', '') if horse_elem else ''
                    horse_id = horse_url.split('/')[-2] if '/horse/' in horse_url else None

                    # 性齢（4列目）
                    sex_age = cols[4].text.strip()

                    # 斤量（5列目）
                    kinryo = float(cols[5].text.strip())

                    # 騎手（6列目）
                    jockey_elem = cols[6].find('a')
                    jockey_name = jockey_elem.text.strip() if jockey_elem else cols[6].text.strip()

                    # タイム（7列目）
                    race_time = cols[7].text.strip()

                    # 着差（8列目）
                    diff = cols[8].text.strip()

                    # 通過順（10列目）
                    passage = cols[10].text.strip() if len(cols) > 10 else ''

                    # 上がり（11列目）
                    agari = cols[11].text.strip() if len(cols) > 11 else ''

                    # オッズ（12列目）
                    try:
                        odds = float(cols[12].text.strip())
                    except:
                        odds = None

                    # 人気（13列目）
                    try:
                        ninki = int(cols[13].text.strip())
                    except:
                        ninki = None

                    # 馬体重（14列目）
                    weight_info = cols[14].text.strip() if len(cols) > 14 else ''

                    # 調教師（18列目）
                    trainer_elem = cols[18].find('a') if len(cols) > 18 else None
                    trainer_name = trainer_elem.text.strip() if trainer_elem else 'N/A'

                    horses.append({
                        'race_id': race_id,
                        'race_name': race_name,
                        'date': race_date,
                        'distance': distance,
                        'track_condition': track_condition,
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

                except (ValueError, IndexError):
                    continue

            return pd.DataFrame(horses) if horses else None

        except Exception as e:
            return None

    def scrape_horse_past_ranks(self, horse_id, num_races=5):
        """馬の過去着順を取得"""
        url = f"https://db.netkeiba.com/horse/{horse_id}"

        try:
            response = self.session.get(url, timeout=10)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.text, 'html.parser')

            result_table = soup.find('table', class_='db_h_race_results')
            if not result_table:
                return []

            rows = result_table.find_all('tr')[1:]
            past_ranks = []

            for row in rows[:num_races]:
                cols = row.find_all('td')
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

    def update_database(self, target_race_ids=None, max_races=50):
        """
        データベースを更新

        Args:
            target_race_ids: 更新対象のレースIDリスト（Noneの場合は自動検出）
            max_races: 最大取得レース数（デフォルト50）
        """
        print("="*80)
        print("スマートデータ更新システム v2")
        print("="*80)

        # 既存レースID取得
        existing_race_ids = self.get_existing_race_ids()

        if target_race_ids is None:
            # 最終更新日から期間を計算
            last_date = self.get_last_update_date()
            start_date = last_date + timedelta(days=1)
            end_date = datetime.now()

            print(f"\n更新期間: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}")

            # レースID候補を生成
            candidate_race_ids = self.get_race_ids_in_period(start_date, end_date)
        else:
            candidate_race_ids = target_race_ids

        # 重複を除外
        new_race_ids = [rid for rid in candidate_race_ids if rid not in existing_race_ids]

        print(f"\n候補レース: {len(candidate_race_ids)}件")
        print(f"既存レース: {len(candidate_race_ids) - len(new_race_ids)}件（スキップ）")
        print(f"新規レース: {len(new_race_ids)}件")

        if len(new_race_ids) == 0:
            print("\n✓ 新規レースはありません")
            return

        # 最大件数制限
        if len(new_race_ids) > max_races:
            print(f"\n! {len(new_race_ids)}件は多すぎるため、最新{max_races}件のみ取得します")
            new_race_ids = new_race_ids[-max_races:]

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
        print(f"スクレイピング開始（最大{len(new_race_ids)}レース）")
        print("="*80)

        all_new_data = []
        success_count = 0
        fail_count = 0

        for i, race_id in enumerate(new_race_ids, 1):
            print(f"\n[{i}/{len(new_race_ids)}] レースID: {race_id}", end=' ')

            # レース結果取得
            race_df = self.scrape_race_result(race_id)

            if race_df is None or len(race_df) == 0:
                print("✗")
                fail_count += 1
                continue

            print(f"✓ {race_df.iloc[0]['race_name']} ({len(race_df)}頭)")

            # 過去着順を追加
            for idx, row in race_df.iterrows():
                horse_id = row['horse_id']
                if horse_id:
                    past_ranks = self.scrape_horse_past_ranks(horse_id, num_races=5)

                    for j in range(5):
                        if j < len(past_ranks):
                            race_df.at[idx, f'past_rank_{j+1}'] = past_ranks[j]

                    time.sleep(0.2)  # 負荷軽減

            all_new_data.append(race_df)
            success_count += 1
            time.sleep(1)

            # 進捗保存（10レースごと）
            if success_count % 10 == 0:
                print(f"\n  中間保存... ({success_count}レース)")

        # 結果サマリー
        print(f"\n" + "="*80)
        print("スクレイピング完了")
        print("="*80)
        print(f"成功: {success_count}レース")
        print(f"失敗: {fail_count}レース")

        if len(all_new_data) == 0:
            print("\n新しいデータが取得できませんでした")
            return

        # 新データを結合
        new_df = pd.concat(all_new_data, ignore_index=True)
        new_df['race_id'] = new_df['race_id'].astype(str)

        print(f"\n新規レコード: {len(new_df):,}件")

        # 結合
        if len(main_df) > 0:
            main_df = main_df[~main_df['race_id'].isin(new_df['race_id'].unique())]
            updated_df = pd.concat([main_df, new_df], ignore_index=True)
        else:
            updated_df = new_df

        # 重複削除
        before = len(updated_df)
        updated_df = updated_df.drop_duplicates(subset=['race_id', 'Umaban'], keep='last')
        after = len(updated_df)

        if before != after:
            print(f"重複削除: {before - after}件")

        # 保存
        updated_df.to_csv(self.db_path, index=False, encoding='utf-8')

        print(f"\n" + "="*80)
        print("✓ 更新完了！")
        print("="*80)
        print(f"総レコード数: {len(updated_df):,}件")
        print(f"追加レース: {success_count}件")
        print(f"保存先: {self.db_path}")

        return updated_df

def main():
    """メイン処理"""
    updater = SmartUpdaterV2()

    print("\n更新モードを選択してください:")
    print("  1. 自動更新（推奨）- 最近のレースを最大50件取得")
    print("  2. 手動指定 - 特定のレースIDを指定")
    print("  3. テスト - サンプルレース1件のみ")

    choice = input("> ").strip()

    if choice == '2':
        race_ids_input = input("\nレースIDをカンマ区切りで入力: ").strip()
        race_ids = [rid.strip() for rid in race_ids_input.split(',')]
        updater.update_database(target_race_ids=race_ids)

    elif choice == '3':
        # テスト用
        test_race_id = '202408010104'
        print(f"\nテストレースID: {test_race_id}")
        updater.update_database(target_race_ids=[test_race_id], max_races=1)

    else:
        # 自動更新
        updater.update_database(max_races=50)

if __name__ == "__main__":
    main()
