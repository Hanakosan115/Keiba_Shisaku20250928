"""
最新データ更新ツール
指定したレースの最新データをnetkeibaから取得してデータベースに追加
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re

def scrape_race_result(race_id):
    """レース結果をスクレイピング"""
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

    print(f"取得中: {url}")

    try:
        response = requests.get(url)
        response.encoding = 'EUC-JP'
        soup = BeautifulSoup(response.content, 'html.parser')

        # レース名
        race_title = soup.select_one('.RaceName')
        race_name = race_title.text.strip() if race_title else 'N/A'

        print(f"レース名: {race_name}")

        # 結果テーブル
        result_table = soup.select_one('.Race_Result_Table')

        if not result_table:
            print("結果テーブルが見つかりません（まだ開催されていない可能性）")
            return None

        horses_data = []
        rows = result_table.select('tr')[1:]  # ヘッダー除く

        for row in rows:
            cols = row.select('td')
            if len(cols) < 10:
                continue

            # 着順
            rank_elem = cols[0]
            rank_text = rank_elem.text.strip()
            try:
                rank = int(rank_text)
            except:
                rank = None

            # 馬番
            umaban = int(cols[2].text.strip())

            # 馬名
            horse_name_elem = cols[3].select_one('a')
            horse_name = horse_name_elem.text.strip() if horse_name_elem else 'N/A'
            horse_url = horse_name_elem['href'] if horse_name_elem else None
            horse_id = horse_url.split('/')[-2] if horse_url else None

            # オッズ
            odds_text = cols[12].text.strip()
            try:
                odds = float(odds_text)
            except:
                odds = None

            # 人気
            ninki = int(cols[13].text.strip())

            horses_data.append({
                'race_id': race_id,
                'race_name': race_name,
                'Rank': rank,
                'Umaban': umaban,
                'HorseName': horse_name,
                'horse_id': horse_id,
                'Odds': odds,
                'Ninki': ninki
            })

        return pd.DataFrame(horses_data)

    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

def scrape_horse_latest_races(horse_id, num_races=5):
    """馬の最新成績を取得"""
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
            cols = row.select('td')
            if len(cols) < 12:
                continue

            # 着順（11番目のカラム）
            rank_elem = cols[11]
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

def main():
    race_id = input("レースID を入力してください (例: 202505050812): ").strip()

    if not race_id:
        race_id = "202505050812"

    print("="*80)
    print(f"レースID {race_id} の最新データを取得")
    print("="*80)

    # レース結果を取得
    df = scrape_race_result(race_id)

    if df is None or len(df) == 0:
        print("\n結果が見つかりません。出馬表から取得します...")

        # 出馬表を取得（レース前の場合）
        url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"
        print(f"取得中: {url}")

        try:
            response = requests.get(url)
            response.encoding = 'EUC-JP'
            soup = BeautifulSoup(response.content, 'html.parser')

            # レース名
            race_title = soup.select_one('.RaceName')
            race_name = race_title.text.strip() if race_title else 'N/A'

            print(f"レース名: {race_name}")

            # 出馬表テーブル
            shutuba_table = soup.select_one('.Shutuba_Table')

            if not shutuba_table:
                print("出馬表が見つかりません")
                return

            horses_data = []
            rows = shutuba_table.select('tr.HorseList')

            for row in rows:
                # 馬番
                umaban_elem = row.select_one('.Umaban')
                umaban = int(umaban_elem.text.strip()) if umaban_elem else None

                # 馬名
                horse_name_elem = row.select_one('.Horse_Name a')
                horse_name = horse_name_elem.text.strip() if horse_name_elem else 'N/A'
                horse_url = horse_name_elem['href'] if horse_name_elem else None
                horse_id = horse_url.split('/')[-2] if horse_url else None

                # オッズ
                odds_elem = row.select_one('.Popular')
                odds_text = odds_elem.text.strip() if odds_elem else None
                try:
                    odds = float(odds_text) if odds_text and odds_text != '-' else None
                except:
                    odds = None

                # 人気
                ninki_elem = row.select_one('.Ninki')
                ninki_text = ninki_elem.text.strip() if ninki_elem else None
                try:
                    ninki = int(ninki_text) if ninki_text and ninki_text.isdigit() else None
                except:
                    ninki = None

                horses_data.append({
                    'race_id': race_id,
                    'race_name': race_name,
                    'Rank': None,  # まだレース前
                    'Umaban': umaban,
                    'HorseName': horse_name,
                    'horse_id': horse_id,
                    'Odds': odds,
                    'Ninki': ninki
                })

            df = pd.DataFrame(horses_data)
            print(f"取得完了: {len(df)}頭")

        except Exception as e:
            print(f"エラー: {e}")
            import traceback
            traceback.print_exc()
            return

    # 各馬の過去成績を取得
    print("\n各馬の過去成績を取得中...")
    print("-"*80)

    for idx, row in df.iterrows():
        horse_id = row['horse_id']
        horse_name = row['HorseName']

        if horse_id:
            print(f"{horse_name} (ID: {horse_id})")

            past_ranks = scrape_horse_latest_races(horse_id, num_races=5)

            # 過去5走を追加
            for i in range(5):
                if i < len(past_ranks):
                    df.at[idx, f'past_rank_{i+1}'] = past_ranks[i]
                else:
                    df.at[idx, f'past_rank_{i+1}'] = None

            past_str = '-'.join(map(str, past_ranks[:3])) if len(past_ranks) >= 3 else 'データ不足'
            print(f"  近3走: {past_str}")

            time.sleep(1)  # 負荷軽減

    # 保存
    output_file = f"race_{race_id}_latest.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    print("\n" + "="*80)
    print(f"保存完了: {output_file}")
    print("="*80)

    # サマリー表示
    print("\n取得データサマリー:")
    print("-"*80)
    display_cols = ['Umaban', 'HorseName', 'Odds', 'Ninki', 'past_rank_1', 'past_rank_2', 'past_rank_3']
    available_cols = [col for col in display_cols if col in df.columns]
    print(df[available_cols].to_string(index=False))

    # 既存データベースへの統合オプション
    print("\n" + "="*80)
    print("既存データベースに追加しますか？")
    print("  y: 追加する")
    print("  n: 追加しない（CSVファイルのみ保存）")
    choice = input("選択 [y/n]: ").strip().lower()

    if choice == 'y':
        try:
            main_df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv',
                                  encoding='utf-8', low_memory=False)

            # 重複削除（同じrace_id + Umabanは上書き）
            main_df['race_id'] = main_df['race_id'].astype(str)
            df['race_id'] = df['race_id'].astype(str)

            # 既存データから該当レースを削除
            main_df = main_df[main_df['race_id'] != race_id]

            # 新データを追加
            updated_df = pd.concat([main_df, df], ignore_index=True)

            # 保存
            updated_df.to_csv('netkeiba_data_2020_2024_enhanced.csv',
                            index=False, encoding='utf-8')

            print(f"✓ データベースに追加しました（総レコード数: {len(updated_df):,}件）")

        except Exception as e:
            print(f"エラー: データベースへの追加に失敗しました - {e}")
    else:
        print("CSVファイルのみ保存しました")

    print("\n完了！")

if __name__ == "__main__":
    main()
