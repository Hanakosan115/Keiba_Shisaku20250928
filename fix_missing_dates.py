"""
日付欠損レースの修正スクリプト

date=NaNの1,320レースを再スクレイピングして日付を取得
"""
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import time
from datetime import datetime

CSV_PATH = 'data/main/netkeiba_data_2020_2025_complete.csv'

def scrape_race_date(race_id):
    """
    レースページから日付を取得

    Returns:
        str: 日付（YYYY年MM月DD日形式）、取得失敗時はNone
    """
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'EUC-JP'

        soup = BeautifulSoup(response.text, 'html.parser')

        # タイトルから日付を抽出
        title_tag = soup.find('title')
        if title_tag:
            title_text = title_tag.get_text()
            # 例: "２歳未勝利 結果・払戻 | 2025年12月28日 中山1R レース情報(JRA)"
            date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', title_text)
            if date_match:
                year = date_match.group(1)
                month = date_match.group(2).zfill(2)
                day = date_match.group(3).zfill(2)
                return f"{year}年{month}月{day}日"

        return None

    except Exception as e:
        print(f"    Error scraping race {race_id}: {e}")
        return None

def main():
    print("="*80)
    print(" 日付欠損レースの修正")
    print("="*80)
    print()

    # CSVを読み込み
    print(f"CSVを読み込み中: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH, low_memory=False)
    print(f"総レコード数: {len(df):,}")

    # date欠損のレコードを特定
    missing_date = df[df['date'].isna()]
    print(f"\ndate欠損レコード: {len(missing_date):,}件")

    if len(missing_date) == 0:
        print("修正の必要なレコードはありません")
        return

    # ユニークなrace_idを取得
    unique_race_ids = missing_date['race_id'].unique()
    print(f"ユニークなrace_id: {len(unique_race_ids):,}レース")

    # レースごとに日付を取得
    print(f"\n日付を再取得中...")
    race_date_map = {}

    for i, race_id in enumerate(unique_race_ids, 1):
        race_id_str = str(int(race_id))
        print(f"\r[{i}/{len(unique_race_ids)}] race_id: {race_id_str} を処理中...", end='', flush=True)

        date_str = scrape_race_date(race_id_str)
        if date_str:
            race_date_map[race_id] = date_str

        time.sleep(1.0)  # レート制限対策

        # 10レースごとに改行して進捗表示
        if i % 10 == 0:
            success_count = len(race_date_map)
            print(f"\r[{i}/{len(unique_race_ids)}] 完了 ({success_count}件成功)", flush=True)

    print(f"\n\n日付取得完了: {len(race_date_map)}/{len(unique_race_ids)}レース")

    # DataFrameを更新
    print("\nDataFrameを更新中...")
    updated_count = 0

    for race_id, date_str in race_date_map.items():
        mask = df['race_id'] == race_id
        df.loc[mask, 'date'] = date_str
        updated_count += mask.sum()

    print(f"更新レコード数: {updated_count:,}件")

    # バックアップを作成
    backup_path = CSV_PATH.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    print(f"\nバックアップを作成中: {backup_path}")
    import shutil
    shutil.copy(CSV_PATH, backup_path)

    # 保存
    print(f"\n保存中: {CSV_PATH}")
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')

    # 結果確認
    remaining_missing = df['date'].isna().sum()
    print(f"\n修正後のdate欠損: {remaining_missing:,}件")

    if remaining_missing == 0:
        print("\n✓ すべての日付欠損を修正しました！")
    else:
        print(f"\n⚠ {remaining_missing:,}件の日付が取得できませんでした")

    print("\n完了！")

if __name__ == "__main__":
    main()
