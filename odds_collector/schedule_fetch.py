# -*- coding: utf-8 -*-
"""
schedule_fetch.py — 当日レーススケジュール取得バッチ

【実行タイミング】 毎週土日 07:00（タスクスケジューラ）
【処理内容】
  1. netkeibaの「本日のレース」ページからレースID・発走時刻を取得
  2. SQLiteに保存（今日分を上書き）

【実行方法】
  py odds_collector/schedule_fetch.py
  py odds_collector/schedule_fetch.py --date 20260301  # 日付指定

【タスクスケジューラ設定（土日のみ）】
  トリガー: 毎週土曜 07:00 / 毎週日曜 07:00
  操作: py C:/Users/bu158/Keiba_Shisaku20250928/odds_collector/schedule_fetch.py
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import re, time, sqlite3, argparse
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup

# ── 設定 ────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH   = os.path.join(BASE_DIR, 'odds_collector', 'odds_timeseries.db')
SLEEP_SEC = 2.5   # リクエスト間隔（Gemini推奨: 2〜3秒）
HEADERS   = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}


# ── DB初期化 ─────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS race_schedule (
            race_date    TEXT NOT NULL,
            race_id      TEXT NOT NULL,
            race_name    TEXT,
            start_time   TEXT,
            venue        TEXT,
            fetched_at   TEXT NOT NULL,
            PRIMARY KEY (race_date, race_id)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS odds_snapshots (
            race_id       TEXT NOT NULL,
            horse_id      TEXT NOT NULL,
            horse_name    TEXT,
            timing        TEXT NOT NULL,
            odds_win      REAL,
            recorded_at   TEXT NOT NULL,
            PRIMARY KEY (race_id, horse_id, timing, recorded_at)
        )
    ''')
    conn.commit()
    return conn


def fetch_today_schedule(target_date: str) -> list[dict]:
    """
    netkeibaの当日レース一覧ページからスケジュールを取得する。
    target_date: 'YYYYMMDD'
    returns: [{'race_id': ..., 'race_name': ..., 'start_time': ..., 'venue': ...}, ...]
    """
    # race_list.html はJavaScript動的読み込みのため0件になる。
    # 静的HTMLを返す race_list_sub.html を使用する。
    url = f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={target_date}'
    print(f'  取得中: {url}')

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f'  [ERROR] 取得失敗: {e}')
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    races = []

    # レースリンク: /race/result.html?race_id=XXXXXXXXXXXX 形式
    for a in soup.find_all('a', href=True):
        href = a['href']
        m = re.search(r'race_id=(\d{12})', href)
        if not m:
            continue
        race_id = m.group(1)

        # 発走時刻（親要素のテキストから探す）
        parent_text = a.get_text(separator=' ', strip=True)
        time_m = re.search(r'(\d{1,2}:\d{2})', parent_text)
        start_time = time_m.group(1) if time_m else ''

        # レース名
        race_name = a.get_text(strip=True)[:30]

        # 会場（race_idの5〜6桁目: 01=札幌 02=函館 03=福島 04=新潟 05=東京
        #        06=中山 07=中京 08=京都 09=阪神 10=小倉）
        venue_code = race_id[4:6]
        venue_map  = {'01':'札幌','02':'函館','03':'福島','04':'新潟','05':'東京',
                      '06':'中山','07':'中京','08':'京都','09':'阪神','10':'小倉'}
        venue = venue_map.get(venue_code, venue_code)

        races.append({
            'race_id': race_id, 'race_name': race_name,
            'start_time': start_time, 'venue': venue,
        })

    # 重複除去
    seen = set()
    unique = []
    for r in races:
        if r['race_id'] not in seen:
            seen.add(r['race_id'])
            unique.append(r)

    return unique


def save_schedule(conn, target_date: str, races: list[dict]):
    now = datetime.now().isoformat(timespec='seconds')
    conn.executemany('''
        INSERT OR REPLACE INTO race_schedule
            (race_date, race_id, race_name, start_time, venue, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', [(target_date, r['race_id'], r['race_name'],
           r['start_time'], r['venue'], now) for r in races])
    conn.commit()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default=date.today().strftime('%Y%m%d'),
                        help='対象日 YYYYMMDD（デフォルト: 今日）')
    args = parser.parse_args()
    target_date = args.date

    print(f'=== schedule_fetch.py  対象日: {target_date} ===')
    conn = init_db()

    time.sleep(SLEEP_SEC)
    races = fetch_today_schedule(target_date)

    if not races:
        print('  レース情報を取得できませんでした。')
        conn.close()
        return

    save_schedule(conn, target_date, races)
    print(f'  保存完了: {len(races)}レース')
    for r in races[:5]:
        print(f'    {r["venue"]} {r["start_time"]} {r["race_id"]} {r["race_name"][:20]}')
    if len(races) > 5:
        print(f'    ...（他{len(races)-5}レース）')

    conn.close()
    print('=== 完了 ===')


if __name__ == '__main__':
    main()
