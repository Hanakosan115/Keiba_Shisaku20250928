# -*- coding: utf-8 -*-
"""
run_auto_post.py — 競馬予想 → note.com 自動投稿 メインスクリプト

使い方:
  py note_publisher/run_auto_post.py --auto           # 発走30分前のレースを自動投稿（タスクスケジューラ用）
  py note_publisher/run_auto_post.py --dry            # 未投稿レースの記事テキストを表示（投稿しない）
  py note_publisher/run_auto_post.py --test           # 最初の1レースのみ（ブラウザ表示）
  py note_publisher/run_auto_post.py --date 20260308  # 日付指定で全レース一括投稿（手動用）
"""
import sys
import os
import asyncio
import sqlite3
import argparse
import csv
import tkinter as tk
import warnings
from datetime import date, datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from note_publisher.format_article import format_article
from note_publisher.format_win5    import format_win5
from note_publisher.post_to_note   import post_article, post_articles_batch

DB_PATH       = os.path.join(BASE_DIR, 'odds_collector', 'odds_timeseries.db')
LOG_CSV        = os.path.join(BASE_DIR, 'paper_trade_log.csv')
INITIAL_BANKROLL = 50_000
BET_UNIT         = 100

# ── ベットサイジング設定 ──────────────────────────────────────
# 条件A（pred>=20% & odds 2-10倍）にフラクショナルKellyを使う
# False にすると全条件 BET_UNIT 固定に戻る
USE_KELLY_FOR_COND_A  = True
KELLY_FRACTION        = 0.5    # 1/2 Kelly
KELLY_MAX_BET         = 1_000  # 1回あたり上限（円）
KELLY_MIN_BET         = 100    # 下限（円、JRA最小単位）

LOG_COLUMNS = [
    'date', 'race_id', 'race_name', 'horse_name', 'horse_id',
    'bet_type', 'pred_win', 'pred_place', 'pred_win_calibrated',
    'odds', 'odds_recorded_time', 'bet_rule', 'bet_amount',
    'kelly_theoretical', 'result', 'payout', 'pl', 'bankroll', 'memo',
]

# 発走の何分前に投稿するか
POST_BEFORE_MINUTES = 30
# 5分おきに起動するため、±の許容幅（この範囲内の発走時刻を対象にする）
WINDOW_EARLY = 25  # 25分後〜
WINDOW_LATE  = 40  # 〜40分後


def _ensure_note_posts_table(conn):
    """投稿済み管理テーブルを作成（なければ）。"""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS note_posts (
            race_id   TEXT PRIMARY KEY,
            posted_at TEXT
        )
    ''')
    conn.commit()


def get_upcoming_races(target_date: str) -> list[dict]:
    """
    --auto モード用:
    発走 WINDOW_EARLY〜WINDOW_LATE 分後 かつ 未投稿 のレースを返す。
    """
    if not os.path.exists(DB_PATH):
        print(f'[ERROR] DBが見つかりません: {DB_PATH}')
        return []

    now = datetime.now()
    from_time = (now + timedelta(minutes=WINDOW_EARLY)).strftime('%H:%M')
    to_time   = (now + timedelta(minutes=WINDOW_LATE  )).strftime('%H:%M')

    conn = sqlite3.connect(DB_PATH)
    _ensure_note_posts_table(conn)
    rows = conn.execute(
        '''
        SELECT rs.race_id, rs.race_name, rs.start_time, rs.venue
        FROM race_schedule rs
        LEFT JOIN note_posts np ON rs.race_id = np.race_id
        WHERE rs.race_date = ?
          AND rs.start_time >= ?
          AND rs.start_time <= ?
          AND np.race_id IS NULL
        ORDER BY rs.start_time
        ''',
        (target_date, from_time, to_time)
    ).fetchall()
    conn.close()

    return [{'race_id': r[0], 'race_name': r[1],
             'start_time': r[2], 'venue': r[3]} for r in rows]


def get_today_races(target_date: str) -> list[dict]:
    """--date / デフォルトモード用: 当日の全レース一覧を取得。"""
    if not os.path.exists(DB_PATH):
        print(f'[ERROR] DBが見つかりません: {DB_PATH}')
        print('       先に py odds_collector/schedule_fetch.py を実行してください。')
        return []
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        'SELECT race_id, race_name, start_time, venue '
        'FROM race_schedule WHERE race_date=? ORDER BY start_time',
        (target_date,)
    ).fetchall()
    conn.close()
    return [{'race_id': r[0], 'race_name': r[1],
             'start_time': r[2], 'venue': r[3]} for r in rows]


def save_race_predictions(race_id: str, df_pred):
    """予測結果（印・勝率・オッズ）をDBに保存。成績レポート用。"""
    if df_pred is None or len(df_pred) == 0:
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS race_predictions (
            race_id    TEXT,
            umaban     TEXT,
            horse_name TEXT,
            mark       TEXT,
            pred_win   REAL,
            pred_place REAL,
            odds       REAL,
            created_at TEXT,
            PRIMARY KEY (race_id, umaban)
        )
    ''')
    now = datetime.now().isoformat()
    for _, row in df_pred.iterrows():
        conn.execute('''
            INSERT OR REPLACE INTO race_predictions
            (race_id, umaban, horse_name, mark, pred_win, pred_place, odds, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            race_id,
            str(row.get('馬番', '')),
            str(row.get('馬名', '')),
            str(row.get('印', '')),
            float(row.get('勝率予測', 0)),
            float(row.get('複勝予測', 0)),
            float(row.get('オッズ', 0)),
            now,
        ))
    conn.commit()
    conn.close()


def mark_as_posted(race_ids: list[str]):
    """投稿済みとして note_posts テーブルに記録する。"""
    if not race_ids:
        return
    conn = sqlite3.connect(DB_PATH)
    _ensure_note_posts_table(conn)
    posted_at = datetime.now().isoformat()
    conn.executemany(
        'INSERT OR IGNORE INTO note_posts (race_id, posted_at) VALUES (?, ?)',
        [(rid, posted_at) for rid in race_ids]
    )
    conn.commit()
    conn.close()


def build_gui():
    """GUI インスタンスを headless（非表示）で初期化。"""
    from keiba_prediction_gui_v3 import KeibaGUIv3
    root = tk.Tk()
    root.withdraw()
    gui = KeibaGUIv3(root)
    return gui


def predict_one_race(gui, race_id: str, today_str: str):
    """
    1レースの予測を実行して df_pred と race_info を返す。
    ① scrape_shutuba()（netkeiba から出馬表取得・当日レース用）
    ② get_race_from_database()（ローカルDB・過去レース用）
    の順に試みる。失敗時は (None, None) を返す。
    """
    try:
        horses, race_info = None, {}

        scraped, r_info = gui.scrape_shutuba(race_id)
        if scraped:
            horses    = scraped
            race_info = r_info or {}
            print(f'  [{race_id}] 出馬表スクレイプ成功（{len(horses)}頭）')
        else:
            horses, race_info = gui.get_race_from_database(race_id)
            if horses:
                print(f'  [{race_id}] DB取得（{len(horses)}頭）')

        if not horses:
            print(f'  [{race_id}] データなし → スキップ')
            return None, None

        has_odds = any(h.get('単勝オッズ', 0) > 0 for h in horses)

        if not has_odds:
            db_odds = gui._get_odds_from_snapshot_db(race_id)
            if db_odds:
                for h in horses:
                    uma = str(h.get('馬番', ''))
                    if uma in db_odds and db_odds[uma] > 0:
                        h['単勝オッズ'] = db_odds[uma]
                has_odds = any(h.get('単勝オッズ', 0) > 0 for h in horses)
                if has_odds:
                    print(f'  [{race_id}] DBスナップショットでオッズ補完')

        df_pred = gui.predict_core(
            race_id, horses, race_info, has_odds,
            current_date=today_str
        )
        return df_pred, race_info

    except Exception as e:
        print(f'  [{race_id}] 予測エラー: {e}')
        return None, None


def _load_paper_log() -> list[dict]:
    if not os.path.exists(LOG_CSV):
        return []
    with open(LOG_CSV, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def _save_paper_log(rows: list[dict]):
    with open(LOG_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def _calc_kelly(pred_win: float, odds: float, bankroll: float) -> int:
    if odds <= 1:
        return 0
    k = (pred_win * odds - 1.0) / (odds - 1.0)
    k = max(0.0, min(k, 0.5))
    return int(round(k * bankroll))


def _calc_bet_amount(pred_win: float, odds: float, bankroll: float, cond_a: bool) -> int:
    """
    ベット額を決定する。
    - 条件A & USE_KELLY_FOR_COND_A=True: フラクショナルKelly（100円単位に丸め、上下限あり）
    - それ以外: BET_UNIT固定
    """
    if cond_a and USE_KELLY_FOR_COND_A:
        full_kelly = _calc_kelly(pred_win, odds, bankroll)
        amount = full_kelly * KELLY_FRACTION
        amount = max(KELLY_MIN_BET, min(KELLY_MAX_BET, amount))
        return int(round(amount / 100) * 100)  # 100円単位
    return BET_UNIT


def _last_bankroll(rows: list[dict]) -> float:
    confirmed = [r for r in rows if r.get('result') in ('的中', 'ハズレ')]
    if not confirmed:
        return float(INITIAL_BANKROLL)
    try:
        return float(confirmed[-1]['bankroll'])
    except (ValueError, KeyError):
        return float(INITIAL_BANKROLL)


def record_paper_trades(df_pred, race_id: str, race_info: dict, today_iso: str):
    """
    df_pred から Rule4 対象馬を抽出して paper_trade_log.csv に追記する。
    重複（同 race_id + horse_name）はスキップ。
    """
    import pandas as pd

    if df_pred is None or len(df_pred) == 0:
        return 0

    rows = _load_paper_log()

    # 既存の (race_id, horse_name, bet_type) セットを作成して重複チェック
    existing = {(r['race_id'], r['horse_name'], r.get('bet_type', '単勝')) for r in rows}

    race_name = race_info.get('race_name', '') or ''
    now_str   = datetime.now().strftime('%Y-%m-%d %H:%M')
    bankroll  = _last_bankroll(rows)

    added = 0
    for _, row in df_pred.iterrows():
        pred_win = float(row.get('勝率予測', 0))
        odds     = float(row.get('オッズ', 0))
        horse    = str(row.get('馬名', ''))

        # Rule4 条件判定
        cond_a = pred_win >= 0.20 and 2.0 <= odds < 10.0
        cond_b = pred_win >= 0.10 and odds >= 10.0
        if not (cond_a or cond_b):
            continue

        bet_rule = '条件A' if cond_a else '条件B'

        if (race_id, horse, '単勝') in existing:
            continue

        kelly      = _calc_kelly(pred_win, odds, bankroll)
        bet_amount = _calc_bet_amount(pred_win, odds, bankroll, cond_a)
        pred_place = float(row.get('複勝予測', 0))

        new_row = {
            'date':                today_iso,
            'race_id':             race_id,
            'race_name':           race_name,
            'horse_name':          horse,
            'horse_id':            str(row.get('horse_id', '')),
            'bet_type':            '単勝',
            'pred_win':            f'{pred_win:.4f}',
            'pred_place':          f'{pred_place:.4f}',
            'pred_win_calibrated': f'{pred_win:.4f}',
            'odds':                f'{odds:.1f}',
            'odds_recorded_time':  now_str,
            'bet_rule':            bet_rule,
            'bet_amount':          str(bet_amount),
            'kelly_theoretical':   str(kelly),
            'result':              '未確定',
            'payout':              '0',
            'pl':                  '0',
            'bankroll':            '0',
            'memo':                '',
        }
        rows.append(new_row)
        existing.add((race_id, horse, '単勝'))
        added += 1

    # ── ワイド・馬連: 複勝予測上位3頭ボックス ──────────────────
    from itertools import combinations as _combinations
    top3_df = df_pred.nlargest(3, '複勝予測')
    if len(top3_df) >= 2:
        top3_horses = []
        for _, row in top3_df.iterrows():
            uma = str(row.get('馬番', ''))
            top3_horses.append({
                'horse':       str(row.get('馬名', '')),
                'uma':         uma,
                'pred_place':  float(row.get('複勝予測', 0)),
            })

        for bet_type in ('ワイド', '馬連'):
            for h1, h2 in _combinations(top3_horses, 2):
                horse_name = f"{h1['horse']}×{h2['horse']}"
                if h1['uma'] and h2['uma']:
                    a, b = sorted([int(h1['uma']), int(h2['uma'])])
                    uma_pair = f'{a}-{b}'
                else:
                    uma_pair = ''

                if (race_id, horse_name, bet_type) in existing:
                    continue

                avg_place = (h1['pred_place'] + h2['pred_place']) / 2
                new_row = {
                    'date':                today_iso,
                    'race_id':             race_id,
                    'race_name':           race_name,
                    'horse_name':          horse_name,
                    'horse_id':            '',
                    'bet_type':            bet_type,
                    'pred_win':            '',
                    'pred_place':          f'{avg_place:.4f}',
                    'pred_win_calibrated': '',
                    'odds':                '0.0',
                    'odds_recorded_time':  now_str,
                    'bet_rule':            '複勝上位3頭ボックス',
                    'bet_amount':          str(BET_UNIT),
                    'kelly_theoretical':   '0',
                    'result':              '未確定',
                    'payout':              '0',
                    'pl':                  '0',
                    'bankroll':            '0',
                    'memo':                uma_pair,
                }
                rows.append(new_row)
                existing.add((race_id, horse_name, bet_type))
                added += 1

    if added > 0:
        _save_paper_log(rows)

    return added


def print_dry_run(article: dict):
    """--dry モード: 記事内容をコンソールに表示。"""
    print('\n' + '=' * 60)
    print(f'TITLE: {article["title"]}')
    print(f'PRICE: {article["price"]}円')
    print('\n--- 無料プレビュー ---')
    print(article['free_body'])
    print('\n--- 有料部分 ---')
    print(article['paid_body'])
    print('=' * 60)


def _fetch_win5_race_names(today_str: str, race_ids: list[str]) -> dict[str, str]:
    """
    netkeibaスケジュールページからWIN5対象レースのレース名を取得する。
    {race_id: race_name} を返す。取得失敗時は空dict。
    """
    import re, requests
    from bs4 import BeautifulSoup
    url = f'https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={today_str}'
    try:
        resp = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        resp.encoding = resp.apparent_encoding
        soup = BeautifulSoup(resp.text, 'html.parser')
        race_names = {}
        seen = set()
        for a in soup.find_all('a', href=True):
            m = re.search(r'race_id=(\d{12})', a['href'])
            if not m:
                continue
            rid = m.group(1)
            if rid in seen or rid not in race_ids:
                continue
            seen.add(rid)
            text = a.get_text(strip=True)
            # "10R甲南S14:50ダ1800m14頭" → "甲南S"
            s = re.sub(r'^\d+R', '', text)
            s = re.sub(r'\d+:\d+', '', s)
            s = re.sub(r'[芝ダ障]\d+m\d*頭?', '', s)
            name = s.strip()
            if name:
                race_names[rid] = name
        return race_names
    except Exception as e:
        print(f'  [WIN5] レース名取得失敗: {e}')
        return {}


def run_win5(gui, today_str: str, today_iso: str, dry: bool, headless: bool,
             budget: int = 10000, preview: bool = False):
    """
    WIN5専用記事を生成して投稿する。

    GUI の以下のメソッドをそのまま利用:
      gui._scrape_win5_race_ids(today_str)   → 5レースID自動取得
      gui._predict_race_for_win5(race_id)    → 各レグ予測
      gui._calculate_win5_strategy(leg_results, budget_points)  → 戦略計算
    """
    print(f'\n=== WIN5記事生成  {today_str} ===')

    # ── Step1: WIN5対象レースIDを自動取得 ───────────────────────
    print('  [1/3] WIN5対象レースID取得中...')
    race_ids = gui._scrape_win5_race_ids(today_str)
    if len(race_ids) != 5:
        print(f'  [WIN5] エラー: 対象レースが5つ取得できませんでした（{len(race_ids)}件）')
        print('  netkeiba のスケジュールページを確認するか、日付を確認してください。')
        return

    print(f'  対象レース: {" / ".join(race_ids)}')

    # ── レース名を取得（スケジュールページから）──────────────────
    race_names = _fetch_win5_race_names(today_str, race_ids)
    print(f'  レース名取得: {race_names}')

    # ── Step2: 各レグを予測 ──────────────────────────────────────
    print('  [2/3] 各レグ予測中...')
    leg_results = []
    for i, race_id in enumerate(race_ids, 1):
        print(f'    第{i}レグ: {race_id}')
        df_pred, race_info = gui._predict_race_for_win5(race_id)
        if df_pred is None:
            print(f'    → データ取得失敗（全頭流しとして続行）')
            df_pred   = None
            race_info = {}
        if not race_info:
            race_info = {}
        if not race_info.get('date'):
            race_info['date'] = today_iso
        # スケジュールページから取得したレース名を注入
        if not race_info.get('race_name') and race_id in race_names:
            race_info['race_name'] = race_names[race_id]
        leg_results.append({
            'race_id':   race_id,
            'df_pred':   df_pred,
            'race_info': race_info,
        })
        if df_pred is not None and not df_pred.empty:
            top_name = str(df_pred.iloc[0].get('馬名', ''))
            top_prob = float(df_pred.iloc[0].get('勝率予測', 0))
            print(f'    → 完了: top1={top_name} P={top_prob:.3f}')

    # ── Step3: 購入戦略を計算 ────────────────────────────────────
    print('  [3/3] 購入戦略計算中...')
    budget_points = budget // 100  # 円 → 点数
    strategies = gui._calculate_win5_strategy(leg_results, budget_points)
    rec = strategies.get('recommended', 'dynamic')
    rec_st = strategies.get(rec, {})
    print(f'  推奨戦略: {rec}  {rec_st.get("total", 0)}点  {rec_st.get("cost", 0):,}円')

    # ── 記事生成 ─────────────────────────────────────────────────
    article = format_win5(leg_results, strategies,
                          date_str=today_iso, budget=budget)
    if not article:
        print('[WIN5] 記事生成失敗')
        return

    # ── 出力 / 投稿 ──────────────────────────────────────────────
    if dry:
        # 推奨馬サマリー（レグ×推奨馬一覧）
        rec_key   = strategies.get('recommended', 'dynamic')
        rec_picks = strategies.get(rec_key, {}).get('picks', [3, 3, 3, 3, 3])
        probas    = strategies.get('probas', [0.0] * 5)
        MARKS     = ['◎', '○', '▲', '△', '☆']
        VENUE_MAP = {
            '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
            '05': '東京', '06': '中山', '07': '中京', '08': '京都',
            '09': '阪神', '10': '小倉',
        }
        print('\n' + '─' * 60)
        print('  推奨馬サマリー')
        print('─' * 60)
        for i, ld in enumerate(leg_results):
            rid   = ld.get('race_id', '')
            ri    = ld.get('race_info') or {}
            df    = ld.get('df_pred')
            n     = rec_picks[i] if i < len(rec_picks) else 3
            prob  = probas[i] * 100 if i < len(probas) else 0
            venue = ri.get('track_name') or VENUE_MAP.get(str(rid)[4:6], f'会場{str(rid)[4:6]}')
            rnum  = ri.get('race_num') or str(int(str(rid)[10:12]))
            horses_str = '（データなし）'
            if df is not None and not df.empty:
                import pandas as pd
                d = df.copy()
                d['_win'] = pd.to_numeric(d.get('勝率予測', 0), errors='coerce').fillna(0)
                d = d.sort_values('_win', ascending=False).reset_index(drop=True)
                parts = []
                for j in range(min(n, len(d))):
                    row  = d.iloc[j]
                    mark = MARKS[j] if j < len(MARKS) else f'{j+1}位'
                    name = str(row.get('馬名', ''))
                    uma  = str(row.get('馬番', ''))
                    parts.append(f'{mark}{uma}番{name}')
                horses_str = '  '.join(parts)
            print(f'  Leg{i+1} {venue}{rnum}R (確信度{prob:.0f}%/{n}頭): {horses_str}')
        print('─' * 60)

        print('\n' + '=' * 60)
        print('[WIN5 DRY RUN]')
        print(f'TITLE: {article["title"]}')
        print(f'PRICE: {article["price"]}円')
        print('\n--- 無料プレビュー ---')
        print(article['free_body'])
        print('\n--- 有料部分 ---')
        print(article['paid_body'])
        print('=' * 60)
    elif preview:
        print('\n[WIN5 PREVIEW] ブラウザを起動して投稿直前で停止します...')
        asyncio.run(post_articles_batch([article], headless=False, stop_before_post=True))
        print('[WIN5 PREVIEW] 確認完了。投稿する場合は --preview なしで実行してください。')
    else:
        ok, _ = asyncio.run(post_articles_batch([article], headless=headless))
        print(f'\n[WIN5] 投稿{"成功" if ok > 0 else "失敗"}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--auto', action='store_true',
                        help=f'発走{POST_BEFORE_MINUTES}分前のレースを自動投稿（タスクスケジューラ用）')
    parser.add_argument('--dry',      action='store_true', help='投稿せずに記事テキストを表示')
    parser.add_argument('--test',     action='store_true', help='最初の1レースのみ・ブラウザ表示')
    parser.add_argument('--date',     default=None,        help='対象日付 YYYYMMDD（省略で今日）')
    parser.add_argument('--no-paper', action='store_true', help='ペーパートレード自動記録を無効化')
    parser.add_argument('--win5',     action='store_true',
                        help='WIN5専用記事を投稿（日付は --date で指定、省略で今日）')
    parser.add_argument('--win5-budget', type=int, default=10000,
                        help='WIN5購入予算（円）。デフォルト10000円。例: --win5-budget 20000')
    parser.add_argument('--preview',  action='store_true',
                        help='--win5 と併用: 投稿直前でブラウザを60秒停止して確認')
    args = parser.parse_args()

    today_str  = args.date or date.today().strftime('%Y%m%d')
    today_iso  = f'{today_str[:4]}-{today_str[4:6]}-{today_str[6:]}'
    headless   = False  # note.com がヘッドレスをブロックするため常にブラウザ表示
    do_paper   = not args.no_paper

    print(f'=== note.com 自動投稿  {today_str}  {datetime.now().strftime("%H:%M:%S")} ===')

    # ── WIN5専用モード ────────────────────────────────────────────
    if args.win5:
        print('  モデル読み込み中...')
        gui = build_gui()
        run_win5(gui, today_str, today_iso,
                 dry=args.dry, headless=headless,
                 budget=args.win5_budget, preview=args.preview)
        return

    # ── レース対象の決定 ──────────────────────────────────────
    if args.auto:
        races = get_upcoming_races(today_str)
        now = datetime.now()
        from_t = (now + timedelta(minutes=WINDOW_EARLY)).strftime('%H:%M')
        to_t   = (now + timedelta(minutes=WINDOW_LATE  )).strftime('%H:%M')
        print(f'  モード: AUTO（発走 {from_t}〜{to_t} の未投稿レース）')
        if not races:
            print('  対象レースなし → 終了')
            return
    else:
        races = get_today_races(today_str)
        mode_label = 'DRY RUN（投稿なし）' if args.dry else \
                     'TEST（1レース・ブラウザ表示）' if args.test else \
                     'LIVE（全レース一括投稿）'
        print(f'  モード: {mode_label}')
        if not races:
            print(f'  {today_str} のレーススケジュールが見つかりません。')
            return

    print(f'  対象: {len(races)}レース')

    # ── GUI 初期化 ────────────────────────────────────────────
    print('  モデル読み込み中...')
    gui = build_gui()

    # ── 予測 & 記事生成 ──────────────────────────────────────
    articles    = []
    skip_count  = 0
    paper_count = 0

    for i, race in enumerate(races):
        race_id    = race['race_id']
        venue      = race.get('venue', '')
        start_time = race.get('start_time', '')
        print(f'\n  [{i+1}/{len(races)}] {venue} {start_time} {race_id}')

        df_pred, race_info = predict_one_race(gui, race_id, today_iso)
        if df_pred is None:
            skip_count += 1
            if args.test:
                break
            continue

        if not race_info.get('date'):
            race_info['date'] = today_iso
        if not race_info.get('race_name') and race.get('race_name'):
            race_info['race_name'] = race['race_name']
        if not race_info.get('start_time') and race.get('start_time'):
            race_info['start_time'] = race['start_time']

        # ── 予測をDBに保存（成績レポート用） ────────────────────
        save_race_predictions(race_id, df_pred)

        # ── ペーパートレード自動記録 ────────────────────────────
        if do_paper:
            n = record_paper_trades(df_pred, race_id, race_info, today_iso)
            paper_count += n
            if n > 0:
                print(f'  [{race_id}] ペーパートレード記録: {n}件')

        article = format_article(race_id, df_pred, race_info)
        if not article:
            print(f'  [{race_id}] 記事生成失敗 → スキップ')
            skip_count += 1
            if args.test:
                break
            continue

        if args.dry:
            print_dry_run(article)
        else:
            articles.append(article)

        if args.test:
            print('\n  [TEST] 1レースで終了します。')
            break

    # ── 投稿（1ブラウザで連続投稿） ──────────────────────────
    ok_count = 0
    posted_ids = []
    if not args.dry and articles:
        ok_count, batch_skip = asyncio.run(
            post_articles_batch(articles, headless=headless)
        )
        skip_count += batch_skip
        # 成功した記事を投稿済みとして記録
        if args.auto and ok_count > 0:
            posted_ids = [a['race_id'] for a in articles[:ok_count]]
            mark_as_posted(posted_ids)

    paper_msg = f' / ペーパートレード記録 {paper_count}件' if do_paper else ''
    print(f'\n=== 完了: 投稿 {ok_count}件 / スキップ {skip_count}件{paper_msg} ===')


if __name__ == '__main__':
    main()
