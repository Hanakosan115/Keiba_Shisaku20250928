#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
collect_race_ids_2020_2025.py
2020〜2025年のJRA全レースIDをnetkeibaカレンダーから取得

使い方:
  py collect_race_ids_2020_2025.py              # 全期間（2020-2025）
  py collect_race_ids_2020_2025.py --year 2023  # 指定年のみ
  py collect_race_ids_2020_2025.py --resume     # 中断した続きから再開

出力:
  race_ids_2020_2025.json         {日付(YYYYMMDD): [race_id, ...]}
  race_ids_2020_2025.csv          date, race_id の2列フラット
  race_ids_checkpoint.json        進捗保存（自動更新）
"""

import requests
from bs4 import BeautifulSoup
import re
import json
import csv
import time
import argparse
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHECKPOINT_FILE = os.path.join(BASE_DIR, 'race_ids_checkpoint.json')
OUTPUT_JSON     = os.path.join(BASE_DIR, 'race_ids_2020_2025.json')
OUTPUT_CSV      = os.path.join(BASE_DIR, 'race_ids_2020_2025.csv')

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    )
}

SLEEP_SEC = 1.5   # リクエスト間隔（秒）
TIMEOUT   = 15    # タイムアウト（秒）
RETRIES   = 2     # リトライ回数


# ─────────────────────────────────────────
#  スクレイピング関数
# ─────────────────────────────────────────

def get_kaisai_dates(year, month):
    """カレンダーページから指定年月の開催日リストを取得"""
    url = f'https://race.netkeiba.com/top/calendar.html?year={year}&month={month}'
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        soup = BeautifulSoup(r.content, 'html.parser')

        dates = set()
        for a in soup.find_all('a', href=True):
            m = re.search(r'kaisai_date=(\d{8})', a['href'])
            if m:
                dates.add(m.group(1))

        return sorted(dates)

    except Exception as e:
        print(f'  [ERR] カレンダー {year}/{month:02d}: {e}')
        return []


def get_race_ids_from_date(kaisai_date):
    """開催日ページからレースIDリストを取得（最大RETRIESリトライ）

    race_list.html はJavaScript動的読み込みのため、
    静的HTMLを返す race_list_sub.html を使用する。
    """
    # _sub.html エンドポイントは静的HTMLでレースIDを含む
    url = f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={kaisai_date}'

    for attempt in range(RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, 'html.parser')

            race_ids = set()
            for a in soup.find_all('a', href=True):
                href = a['href']
                # パターンA: ?race_id=XXXXXXXXXXXX
                m = re.search(r'race_id=(\d{12})', href)
                if m:
                    race_ids.add(m.group(1))
                    continue
                # パターンB: /race/result/XXXXXXXXXXXX/ または /race/shutuba/
                m = re.search(r'/race/(?:result|shutuba)/(\d{12})/', href)
                if m:
                    race_ids.add(m.group(1))

            return sorted(race_ids)

        except Exception as e:
            if attempt < RETRIES:
                print(f'    リトライ {attempt+1}/{RETRIES} ({kaisai_date}): {e}')
                time.sleep(3)
            else:
                print(f'  [ERR] レースID取得失敗 {kaisai_date}: {e}')
                return []


# ─────────────────────────────────────────
#  チェックポイント管理
# ─────────────────────────────────────────

def load_checkpoint():
    """チェックポイント読み込み → (dates_dict, completed_months_set)"""
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, encoding='utf-8') as f:
            data = json.load(f)
        return data.get('dates', {}), set(data.get('completed_months', []))
    return {}, set()


def save_checkpoint(dates, completed_months):
    """チェックポイント保存"""
    with open(CHECKPOINT_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'updated': datetime.now().isoformat(),
            'completed_months': sorted(completed_months),
            'dates': dates,
        }, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────
#  出力保存
# ─────────────────────────────────────────

def save_outputs(dates):
    """JSON と CSV を保存"""
    sorted_dates = dict(sorted(dates.items()))

    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(sorted_dates, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'race_id'])
        for d, ids in sorted_dates.items():
            for rid in ids:
                writer.writerow([d, rid])

    total = sum(len(v) for v in dates.values())
    print(f'\n保存完了: {len(dates)}開催日 / {total}レース')
    print(f'  → {OUTPUT_JSON}')
    print(f'  → {OUTPUT_CSV}')


# ─────────────────────────────────────────
#  メイン
# ─────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='2020〜2025年のJRAレースIDをnetkeibaから取得'
    )
    parser.add_argument('--year',   type=int, help='特定の年だけ取得（例: 2022）')
    parser.add_argument('--resume', action='store_true', help='チェックポイントから再開')
    args = parser.parse_args()

    # 対象年月リスト
    if args.year:
        year_months = [(args.year, m) for m in range(1, 13)]
    else:
        year_months = [(y, m) for y in range(2020, 2026) for m in range(1, 13)]

    # チェックポイント読み込み
    if args.resume:
        dates, completed = load_checkpoint()
        print(f'チェックポイント読み込み: {len(completed)}ヶ月完了済み / {len(dates)}開催日取得済み')
    else:
        dates, completed = {}, set()

    total = len(year_months)
    start_ts = time.time()

    for idx, (year, month) in enumerate(year_months):
        ym_key = f'{year}{month:02d}'
        done_count = idx + 1

        # 完了済み月はスキップ
        if ym_key in completed:
            print(f'[{done_count:>3}/{total}] {year}/{month:02d} スキップ（取得済み）')
            continue

        # 経過時間・残時間の推計
        elapsed = time.time() - start_ts
        if idx > 0:
            pace = elapsed / idx
            remaining = pace * (total - idx)
            eta = f'残 {int(remaining//60)}分{int(remaining%60)}秒'
        else:
            eta = ''

        print(f'[{done_count:>3}/{total}] {year}/{month:02d} カレンダー取得中... {eta}')

        kaisai_dates = get_kaisai_dates(year, month)
        time.sleep(SLEEP_SEC)

        if not kaisai_dates:
            print(f'  → 開催なし（または取得失敗）')
            completed.add(ym_key)
            save_checkpoint(dates, completed)
            continue

        print(f'  → {len(kaisai_dates)}開催日: {" ".join(kaisai_dates)}')

        for d in kaisai_dates:
            ids = get_race_ids_from_date(d)
            dates[d] = ids
            print(f'     {d}: {len(ids)}レース'
                  + (f'  {ids[0]}〜{ids[-1]}' if ids else ''))
            time.sleep(SLEEP_SEC)

        # 月完了 → チェックポイント保存
        completed.add(ym_key)
        save_checkpoint(dates, completed)

    # 最終出力
    save_outputs(dates)

    # サマリー
    total_races = sum(len(v) for v in dates.values())
    total_sec = time.time() - start_ts
    print(f'\n=== 完了 ({int(total_sec//60)}分{int(total_sec%60)}秒) ===')
    if dates:
        print(f'期間  : {min(dates.keys())} 〜 {max(dates.keys())}')
    print(f'開催日: {len(dates)}日')
    print(f'レース: {total_races}件')

    # 年別サマリー
    by_year = {}
    for d, ids in dates.items():
        y = d[:4]
        by_year[y] = by_year.get(y, 0) + len(ids)
    for y, cnt in sorted(by_year.items()):
        print(f'  {y}年: {cnt}レース')


if __name__ == '__main__':
    main()
