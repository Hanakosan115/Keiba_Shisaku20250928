# -*- coding: utf-8 -*-
"""
odds_snapshot.py — オッズスナップショット取得バッチ

【実行タイミング】 各レースの発走30分前・5分前に手動実行（または自動実行）
【処理内容】
  1. DBに保存されている当日のレーススケジュールを読み込む
  2. 発走まで X分以内のレースのオッズを取得
  3. timing（'30min_before' / '5min_before' / 'manual'）付きでDBに保存

【実行方法（手動）】
  # 全レースの現在オッズを一括取得
  py odds_collector/odds_snapshot.py

  # 特定レースIDのみ
  py odds_collector/odds_snapshot.py --race_id 202601050801

  # タイミングラベルを指定
  py odds_collector/odds_snapshot.py --timing 30min_before
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
SLEEP_SEC = 2.5
HEADERS   = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}


def get_conn():
    return sqlite3.connect(DB_PATH)


def fetch_win_odds(race_id: str) -> list[dict]:
    """
    netkeibaの単勝オッズページからオッズを取得する。
    returns: [{'horse_id': ..., 'horse_name': ..., 'odds_win': ...}, ...]
    """
    url = f'https://odds.netkeiba.com/?type=b1&race_id={race_id}'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f'    [ERROR] {race_id}: {e}')
        return []

    soup = BeautifulSoup(resp.text, 'html.parser')
    results = []

    # 馬ごとの行を探す（tbody > tr）
    for tr in soup.select('table tr'):
        tds = tr.find_all('td')
        if len(tds) < 3:
            continue

        # 馬IDリンクを探す
        horse_link = tr.find('a', href=re.compile(r'/horse/(\d+)'))
        if not horse_link:
            continue
        horse_id_m = re.search(r'/horse/(\d+)', horse_link['href'])
        if not horse_id_m:
            continue
        horse_id   = horse_id_m.group(1)
        horse_name = horse_link.get_text(strip=True)

        # オッズ値（数値セルを探す）
        odds_win = None
        for td in tds:
            text = td.get_text(strip=True).replace(',', '')
            try:
                v = float(text)
                if 1.0 <= v <= 9999.9:
                    odds_win = v
                    break
            except ValueError:
                continue

        if odds_win:
            results.append({
                'horse_id': horse_id,
                'horse_name': horse_name,
                'odds_win': odds_win,
            })

    return results


def save_snapshot(conn, race_id: str, horses: list[dict], timing: str):
    now = datetime.now().isoformat(timespec='seconds')
    conn.executemany('''
        INSERT OR REPLACE INTO odds_snapshots
            (race_id, horse_id, horse_name, timing, odds_win, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', [(race_id, h['horse_id'], h['horse_name'],
           timing, h['odds_win'], now) for h in horses])
    conn.commit()


def load_today_races(conn, target_date: str) -> list[dict]:
    cur = conn.execute(
        'SELECT race_id, race_name, start_time, venue FROM race_schedule WHERE race_date=? ORDER BY start_time',
        (target_date,)
    )
    return [{'race_id': r[0], 'race_name': r[1],
              'start_time': r[2], 'venue': r[3]} for r in cur.fetchall()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default=date.today().strftime('%Y%m%d'))
    parser.add_argument('--race_id', default=None, help='特定のrace_idのみ取得')
    parser.add_argument('--timing', default='manual',
                        choices=['30min_before', '5min_before', 'manual'],
                        help='取得タイミングのラベル')
    args = parser.parse_args()

    target_date = args.date
    timing      = args.timing
    now_str     = datetime.now().strftime('%H:%M')

    print(f'=== odds_snapshot.py  {target_date} {now_str}  timing={timing} ===')

    conn = get_conn()

    if args.race_id:
        races = [{'race_id': args.race_id, 'race_name': '', 'start_time': '', 'venue': ''}]
    else:
        races = load_today_races(conn, target_date)
        if not races:
            print('  スケジュールが見つかりません。先に schedule_fetch.py を実行してください。')
            conn.close()
            return

    print(f'  対象: {len(races)}レース')

    ok_count = 0
    for race in races:
        race_id = race['race_id']
        label   = f"{race.get('venue','')} {race.get('start_time','')} {race_id}"
        print(f'  [{ok_count+1}/{len(races)}] {label}', end=' ', flush=True)

        time.sleep(SLEEP_SEC)  # レート制限
        horses = fetch_win_odds(race_id)

        if not horses:
            print('→ 取得失敗 or 発売前')
            continue

        save_snapshot(conn, race_id, horses, timing)
        odds_range = f"{min(h['odds_win'] for h in horses):.1f}x〜{max(h['odds_win'] for h in horses):.1f}x"
        print(f'→ {len(horses)}頭 {odds_range} 保存')
        ok_count += 1

    conn.close()
    print(f'=== 完了: {ok_count}/{len(races)}レース ===')


if __name__ == '__main__':
    main()
