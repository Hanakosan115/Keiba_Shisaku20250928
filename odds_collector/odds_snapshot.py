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
    conn = sqlite3.connect(DB_PATH)
    # umaban 列を追加（既存DBには ALTER TABLE で追加）
    try:
        conn.execute('ALTER TABLE odds_snapshots ADD COLUMN umaban TEXT')
        conn.commit()
    except Exception:
        pass  # 既にカラムが存在する場合は無視
    # 馬連・ワイドのオッズを保存するテーブル（初回のみ作成）
    conn.execute('''
        CREATE TABLE IF NOT EXISTS combo_odds_snapshots (
            race_id      TEXT NOT NULL,
            combo_key    TEXT NOT NULL,
            ticket_type  TEXT NOT NULL,
            odds_min     REAL,
            odds_max     REAL,
            timing       TEXT NOT NULL,
            recorded_at  TEXT NOT NULL,
            PRIMARY KEY (race_id, combo_key, ticket_type, timing, recorded_at)
        )
    ''')
    conn.commit()
    return conn


def _fetch_horse_info(race_id: str) -> dict:
    """
    shutuba.html（EUC-JP）から馬番→{horse_id, horse_name}マッピングを取得。
    戻り値: {'01': {'id': '2023103588', 'name': 'バハルブルー'}, ...}
    失敗時は空dict。
    """
    url = f'https://race.netkeiba.com/race/shutuba.html?race_id={race_id}'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = 'euc-jp'   # netkeiba shutuba.html は EUC-JP
        soup = BeautifulSoup(resp.text, 'html.parser')
    except Exception:
        return {}

    info = {}
    table = soup.find('table', class_='Shutuba_Table')
    if not table:
        return {}

    for row in table.find_all('tr'):
        tds = row.find_all('td')
        if len(tds) < 4:
            continue
        umaban = tds[1].get_text(strip=True).zfill(2)
        horse_link = tds[3].find('a', href=re.compile(r'/horse/(\d+)'))
        if horse_link:
            m = re.search(r'/horse/(\d+)', horse_link['href'])
            horse_id   = m.group(1) if m else ''
            horse_name = horse_link.get_text(strip=True)
            info[umaban] = {'id': horse_id, 'name': horse_name}

    return info


def fetch_win_odds(race_id: str) -> list[dict]:
    """
    netkeiba の単勝オッズJSON APIからオッズを取得する。
    正しいエンドポイント: race.netkeiba.com/api/api_get_jra_odds.html?race_id=...&type=1
    （旧 odds.netkeiba.com は存在しない → DNS エラーのため使用不可）
    returns: [{'horse_id': ..., 'horse_name': ..., 'odds_win': ...}, ...]
    """
    api_url = (f'https://race.netkeiba.com/api/api_get_jra_odds.html'
               f'?race_id={race_id}&type=1')
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f'    [ERROR] {race_id}: {e}')
        return []

    if data.get('status') != 'result':
        return []

    odds_dict = data.get('data', {}).get('odds', {}).get('1', {})
    if not odds_dict:
        return []

    # 馬名を取得（shutuba.html より、失敗しても処理続行）
    horse_info = _fetch_horse_info(race_id)

    results = []
    for umaban_padded, vals in odds_dict.items():
        # vals = ["4.9", "", "4"]  → [オッズ, "", 人気]
        try:
            odds_win = float(vals[0]) if vals[0] not in ('', '---') else None
        except (ValueError, IndexError):
            odds_win = None
        if not odds_win or odds_win <= 0:
            continue

        info    = horse_info.get(umaban_padded, {})
        horse_id   = info.get('id', umaban_padded)   # 取得できなければ馬番で代替
        horse_name = info.get('name', f'馬{umaban_padded}')

        results.append({
            'horse_id':   horse_id,
            'horse_name': horse_name,
            'odds_win':   odds_win,
            'umaban':     umaban_padded,
        })

    return results


def fetch_combo_odds(race_id: str, ticket_type: str) -> list[dict]:
    """
    馬連(umaren=type4) or ワイド(wide=type5) のオッズを取得する。
    returns: [{'combo_key': '01-02', 'odds_min': 3.5, 'odds_max': 5.2 or None}, ...]
    ワイドは "3.5-5.2" 形式の範囲オッズが返る場合がある。
    """
    type_num = {'umaren': '4', 'wide': '5'}.get(ticket_type)
    if type_num is None:
        return []

    api_url = (f'https://race.netkeiba.com/api/api_get_jra_odds.html'
               f'?race_id={race_id}&type={type_num}')
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f'      [{ticket_type} ERROR] {e}')
        return []

    if data.get('status') != 'result':
        return []

    odds_dict = data.get('data', {}).get('odds', {}).get(type_num, {})
    if not odds_dict:
        return []

    results = []
    for combo_key, vals in odds_dict.items():
        odds_str = vals[0] if vals else ''
        if not odds_str or odds_str == '---':
            continue
        # ワイドは "3.5-5.2" 形式、馬連は単一値
        # combo_key は "01-02" 形式（整数-整数）なので混同なし
        parts = odds_str.split('-')
        if len(parts) == 2:
            try:
                odds_min, odds_max = float(parts[0]), float(parts[1])
            except ValueError:
                continue
        else:
            try:
                odds_min, odds_max = float(odds_str), None
            except ValueError:
                continue
        if odds_min <= 0:
            continue
        results.append({
            'combo_key': combo_key,
            'odds_min':  odds_min,
            'odds_max':  odds_max,
        })
    return results


def save_combo_snapshot(conn, race_id: str, combos: list[dict],
                        ticket_type: str, timing: str):
    now = datetime.now().isoformat(timespec='seconds')
    conn.executemany('''
        INSERT OR REPLACE INTO combo_odds_snapshots
            (race_id, combo_key, ticket_type, odds_min, odds_max, timing, recorded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', [(race_id, c['combo_key'], ticket_type,
           c['odds_min'], c.get('odds_max'), timing, now) for c in combos])
    conn.commit()


def save_snapshot(conn, race_id: str, horses: list[dict], timing: str):
    now = datetime.now().isoformat(timespec='seconds')
    conn.executemany('''
        INSERT OR REPLACE INTO odds_snapshots
            (race_id, horse_id, horse_name, timing, odds_win, recorded_at, umaban)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', [(race_id, h['horse_id'], h['horse_name'],
           timing, h['odds_win'], now, h.get('umaban', '')) for h in horses])
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
            print('→ 単勝取得失敗 or 発売前')
            continue

        save_snapshot(conn, race_id, horses, timing)
        odds_range = f"{min(h['odds_win'] for h in horses):.1f}x〜{max(h['odds_win'] for h in horses):.1f}x"
        print(f'→ 単勝{len(horses)}頭 {odds_range}', end='')

        # 馬連・ワイドも取得
        for ttype in ('umaren', 'wide'):
            time.sleep(1.0)
            combos = fetch_combo_odds(race_id, ttype)
            if combos:
                save_combo_snapshot(conn, race_id, combos, ttype, timing)
                print(f'  {ttype}:{len(combos)}組', end='')
        print(' 保存')
        ok_count += 1

    conn.close()
    print(f'=== 完了: {ok_count}/{len(races)}レース ===')


if __name__ == '__main__':
    main()
