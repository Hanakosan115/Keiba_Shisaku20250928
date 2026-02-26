"""
最新レースのスクレイピング
指定したレースIDのデータを取得して既存データに追加
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_race_shutuba(race_id):
    """
    レースの出馬表をスクレイピング

    Args:
        race_id: レースID (例: 202505050812)

    Returns:
        DataFrame: 出馬表データ
    """
    url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"

    print(f"スクレイピング中: {url}")

    try:
        response = requests.get(url)
        response.encoding = 'EUC-JP'
        soup = BeautifulSoup(response.content, 'html.parser')

        # レース名取得
        race_name_elem = soup.select_one('.RaceName')
        race_name = race_name_elem.text.strip() if race_name_elem else 'N/A'

        print(f"レース名: {race_name}")

        # 出馬表テーブル
        horse_table = soup.select_one('.Shutuba_Table')

        if not horse_table:
            print("出馬表が見つかりません")
            return None

        horses_data = []

        rows = horse_table.select('tr.HorseList')

        for row in rows:
            # 馬番
            umaban_elem = row.select_one('.Umaban')
            umaban = int(umaban_elem.text.strip()) if umaban_elem else None

            # 馬名
            horse_name_elem = row.select_one('.Horse_Name a')
            horse_name = horse_name_elem.text.strip() if horse_name_elem else 'N/A'
            horse_id = horse_name_elem['href'].split('/')[-2] if horse_name_elem else None

            # オッズ
            odds_elem = row.select_one('.Popular')
            odds = float(odds_elem.text.strip()) if odds_elem and odds_elem.text.strip() != '-' else None

            # 人気
            ninki_elem = row.select_one('.Ninki')
            ninki = int(ninki_elem.text.strip()) if ninki_elem and ninki_elem.text.strip().isdigit() else None

            # 騎手
            jockey_elem = row.select_one('.Jockey a')
            jockey = jockey_elem.text.strip() if jockey_elem else 'N/A'

            # 斤量
            weight_elem = row.select_one('.Weight')
            weight = float(weight_elem.text.strip()) if weight_elem else None

            horses_data.append({
                'race_id': race_id,
                'race_name': race_name,
                'Umaban': umaban,
                'HorseName': horse_name,
                'horse_id': horse_id,
                'Odds': odds,
                'Ninki': ninki,
                'JockeyName': jockey,
                'Kinryo': weight
            })

        df = pd.DataFrame(horses_data)
        print(f"取得完了: {len(df)}頭")

        return df

    except Exception as e:
        print(f"エラー: {e}")
        return None

def scrape_horse_past_races(horse_id, num_races=5):
    """
    馬の過去成績をスクレイピング

    Args:
        horse_id: 馬ID
        num_races: 取得する過去レース数

    Returns:
        list: 過去着順のリスト
    """
    url = f"https://db.netkeiba.com/horse/{horse_id}"

    try:
        response = requests.get(url)
        response.encoding = 'EUC-JP'
        soup = BeautifulSoup(response.content, 'html.parser')

        # 成績テーブル
        result_table = soup.select_one('.db_h_race_results')

        if not result_table:
            return []

        rows = result_table.select('tr')[1:]  # ヘッダー除く

        past_ranks = []

        for row in rows[:num_races]:
            rank_elem = row.select_one('td:nth-child(12)')  # 着順カラム
            if rank_elem:
                rank_text = rank_elem.text.strip()
                try:
                    rank = int(rank_text)
                    past_ranks.append(rank)
                except:
                    pass

        return past_ranks

    except Exception as e:
        print(f"  エラー (馬ID {horse_id}): {e}")
        return []

if __name__ == "__main__":
    race_id = "202505050812"

    print("="*80)
    print(f"レースID {race_id} をスクレイピング")
    print("="*80)

    # 出馬表取得
    df = scrape_race_shutuba(race_id)

    if df is None or len(df) == 0:
        print("データ取得失敗")
        exit(1)

    # 各馬の過去成績を取得
    print("\n過去成績を取得中...")

    for idx, row in df.iterrows():
        horse_id = row['horse_id']
        horse_name = row['HorseName']

        if horse_id:
            print(f"  {horse_name} (ID: {horse_id})")
            past_ranks = scrape_horse_past_races(horse_id, num_races=5)

            # 過去5走の着順を追加
            for i in range(5):
                if i < len(past_ranks):
                    df.at[idx, f'past_rank_{i+1}'] = past_ranks[i]
                else:
                    df.at[idx, f'past_rank_{i+1}'] = None

            print(f"    過去着順: {'-'.join(map(str, past_ranks)) if past_ranks else 'データなし'}")

            time.sleep(1)  # 負荷軽減

    # 保存
    output_file = f"race_{race_id}_data.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    print(f"\n保存完了: {output_file}")
    print("\n" + "="*80)
    print("取得データサマリー")
    print("="*80)
    print(df[['Umaban', 'HorseName', 'Odds', 'past_rank_1', 'past_rank_2', 'past_rank_3']].to_string())
