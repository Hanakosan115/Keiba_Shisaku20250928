"""
collect_training_history.py — 調教データ過去分一括収集（type=2: タイムラップ付き）

complete.csv の全 race_id に対して oikiri.html?type=2 をスクレイプし、
training_evaluations_v2.csv に保存する。

type=2 テーブル列構成（12列）:
  cols[1]=馬番, cols[4]=日付, cols[5]=コース, cols[6]=馬場, cols[7]=乗り役
  cols[8]=タイムラップ文字列, cols[9]=位置, cols[10]=脚色, cols[11]=評価テキスト, cols[12]=ランク

初回のみ手動実行（全期間で ~8〜18時間かかる）。
すでに取得済みの race_id はスキップするので、中断・再開が可能。

使い方:
    py collect_training_history.py              # 全期間（2020〜）
    py collect_training_history.py --year 2024  # 指定年のみ
"""

import sys
import re
import time
import argparse
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR     = Path(__file__).parent
COMPLETE_CSV = BASE_DIR / 'data' / 'main' / 'netkeiba_data_2020_2025_complete.csv'
TRAINING_CSV = BASE_DIR / 'data' / 'main' / 'training_evaluations_v2.csv'

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
}
SLEEP_SEC = 1.5  # リクエスト間隔


def scrape_training(race_id: str) -> list[dict]:
    """oikiri.html?type=2 からタイムラップ付き調教データを取得して dict のリストを返す"""
    url = f'https://race.netkeiba.com/race/oikiri.html?race_id={race_id}&type=2'
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        if r.status_code != 200:
            return []
        r.encoding = 'euc-jp'
        soup = BeautifulSoup(r.text, 'html.parser')
        table = soup.find('table')
        if not table:
            return []
        rows = table.find_all('tr')[1:]
        data = []
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all('td')]
            if len(cols) < 13:
                continue
            data.append({
                'race_id':          int(race_id),
                'umaban':           cols[1],
                'training_date':    cols[4],
                'training_course':  cols[5],
                'training_baba':    cols[6],
                'training_rider':   cols[7],
                'training_laps':    cols[8],
                'training_pos':     cols[9],
                'training_finish':  cols[10],
                'training_critic':  cols[11],
                'training_rank':    cols[12],
            })
        return data
    except Exception:
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--year', type=int, help='対象年（例: 2024）')
    args = parser.parse_args()

    print('=' * 60)
    print('  調教データ過去分一括収集（type=2: タイムラップ付き）')
    print('=' * 60)

    # complete.csv から race_id リストを取得
    df_main = pd.read_csv(COMPLETE_CSV, usecols=['race_id'], low_memory=False)
    df_main['race_id'] = df_main['race_id'].astype(str).str.strip()
    df_main = df_main[df_main['race_id'].str.match(r'^\d{12}$')]
    all_race_ids = sorted(df_main['race_id'].unique().tolist())

    if args.year:
        all_race_ids = [r for r in all_race_ids if r[:4] == str(args.year)]
        print(f'対象: {args.year}年 {len(all_race_ids):,}レース')
    else:
        print(f'対象: 全期間 {len(all_race_ids):,}レース')

    # 取得済み race_id をスキップ
    done_ids: set[str] = set()
    if TRAINING_CSV.exists():
        df_done = pd.read_csv(TRAINING_CSV, usecols=['race_id'], low_memory=False)
        done_ids = set(df_done['race_id'].astype(str))
        print(f'取得済み: {len(done_ids):,}レース → スキップ')

    target_ids = [r for r in all_race_ids if r not in done_ids]
    print(f'収集対象: {len(target_ids):,}レース')

    if not target_ids:
        print('すべて取得済みです')
        return

    # 収集ループ（100レースごとに保存）
    buffer: list[dict] = []
    ok = skip_empty = err = 0
    SAVE_INTERVAL = 100

    for i, race_id in enumerate(target_ids, 1):
        data = scrape_training(race_id)

        if data:
            buffer.extend(data)
            ok += 1
        else:
            skip_empty += 1

        # 進捗表示
        if i % 50 == 0 or i == len(target_ids):
            pct = i / len(target_ids) * 100
            print(f'  [{i:>6}/{len(target_ids)}] {pct:5.1f}%  OK={ok} 空={skip_empty}')

        # 定期保存
        if len(buffer) >= SAVE_INTERVAL * 15 or i == len(target_ids):
            if buffer:
                new_df = pd.DataFrame(buffer)
                if TRAINING_CSV.exists():
                    old = pd.read_csv(TRAINING_CSV, low_memory=False)
                    combined = pd.concat([old, new_df], ignore_index=True)
                else:
                    combined = new_df
                combined.to_csv(TRAINING_CSV, index=False, encoding='utf-8-sig')
                buffer = []

        time.sleep(SLEEP_SEC)

    print(f'\n完了: OK={ok} / 空={skip_empty}')
    if TRAINING_CSV.exists():
        total = len(pd.read_csv(TRAINING_CSV))
        print(f'training_evaluations_v2.csv: {total:,}件')
    print('次: py calculate_features_r10.py')
    print('=' * 60)


if __name__ == '__main__':
    main()
