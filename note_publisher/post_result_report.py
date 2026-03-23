# -*- coding: utf-8 -*-
"""
post_result_report.py — AI予想成績レポートを無料note記事として投稿

【フォーマット】
  中山
   01R  ◎ ○ △  (2人気, 1人気, 5人気)
   11R  ◎ － ▲  (1人気, 7人気, 3人気)  ◎1着@3.5x  ▲3着

  ■ 印別3着内率
  ◎ 8/12 (67%)  ○ 5/9 (56%)  ...

【使い方】
  py note_publisher/post_result_report.py              # 今日の成績を投稿
  py note_publisher/post_result_report.py --dry        # 記事テキスト確認のみ
  py note_publisher/post_result_report.py --date 20260308
"""
import sys, os, asyncio, sqlite3, argparse, re
from datetime import date, datetime
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH  = os.path.join(BASE_DIR, 'odds_collector', 'odds_timeseries.db')

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / '.env')
except ImportError:
    pass

from playwright.async_api import async_playwright

NOTE_EMAIL    = os.getenv('NOTE_EMAIL', '')
NOTE_PASSWORD = os.getenv('NOTE_PASSWORD', '')

VENUE_MAP = {
    '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
    '05': '東京', '06': '中山', '07': '中京', '08': '京都',
    '09': '阪神', '10': '小倉',
}

ALL_MARKS = ['◎', '○', '▲', '△', '☆', '注']
DOW_JA    = ['月', '火', '水', '木', '金', '土', '日']


# ── DB 読み込み ────────────────────────────────────────────────

def load_predictions(target_date: str) -> dict[str, dict[str, str]]:
    """race_predictions から {race_id: {umaban: mark}} を返す。"""
    if not os.path.exists(DB_PATH):
        return {}
    conn = sqlite3.connect(DB_PATH)
    # race_id の日付部分で絞り込み（race_id: YYYYVVRRNN 形式、先頭8桁が日付）
    try:
        rows = conn.execute('''
            SELECT race_id, umaban, mark
            FROM race_predictions
            WHERE created_at LIKE ?
        ''', (f'{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}%',)).fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    result = defaultdict(dict)
    for race_id, umaban, mark in rows:
        if mark:
            result[race_id][umaban] = mark
    return dict(result)


def load_results(race_ids: list[str]) -> dict[str, list[dict]]:
    """
    race_results から {race_id: [top3]} を返す。
    created_at ではなく race_id で直接ルックアップするため、
    結果取得が日付をまたいでも正しく引ける。
    """
    if not os.path.exists(DB_PATH) or not race_ids:
        return {}
    conn = sqlite3.connect(DB_PATH)
    try:
        placeholders = ','.join('?' * len(race_ids))
        rows = conn.execute(f'''
            SELECT race_id, rank, umaban, ninki
            FROM race_results
            WHERE race_id IN ({placeholders})
            ORDER BY race_id, rank
        ''', race_ids).fetchall()
    except sqlite3.OperationalError:
        rows = []
    conn.close()
    result = defaultdict(list)
    for race_id, rank, umaban, ninki in rows:
        result[race_id].append({'rank': rank, 'umaban': umaban, 'ninki': ninki})
    return dict(result)


def load_payout(target_date: str) -> dict[str, float]:
    """単勝払戻し {race_id: payout_yen} を paper_trade_log から取得。"""
    import csv
    log_csv = os.path.join(BASE_DIR, 'paper_trade_log.csv')
    payouts = {}
    if not os.path.exists(log_csv):
        return payouts
    with open(log_csv, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            if row.get('date', '').replace('-', '') != target_date:
                continue
            if row.get('result') == '的中':
                rid = row['race_id']
                try:
                    payouts[rid] = float(row['payout'])
                except (ValueError, KeyError):
                    pass
    return payouts


# ── 記事テキスト生成 ──────────────────────────────────────────

def format_report(target_date: str) -> tuple[str, str]:
    """
    (title, body) を返す。
    """
    predictions = load_predictions(target_date)
    results     = load_results(list(predictions.keys()))
    payouts     = load_payout(target_date)

    if not predictions:
        return None, None

    dt  = datetime.strptime(target_date, '%Y%m%d')
    dow = DOW_JA[dt.weekday()]
    title = f'【{dt.month}/{dt.day}（{dow}）】競馬成績振り返り'

    # 全race_idをvenueごとにグループ化
    venue_races: dict[str, list[str]] = defaultdict(list)
    all_race_ids = sorted(set(predictions.keys()) | set(results.keys()))
    for rid in all_race_ids:
        venue_code = rid[4:6]
        venue = VENUE_MAP.get(venue_code, f'会場{venue_code}')
        venue_races[venue].append(rid)

    # 印別カウント
    mark_hits  = defaultdict(int)  # 3着以内の的中数
    mark_total = defaultdict(int)  # 印をつけた総レース数

    lines = []

    for venue, race_ids in sorted(venue_races.items()):
        lines.append(f'\n{venue}')
        for rid in sorted(race_ids):
            race_no = int(rid[10:12])
            pred = predictions.get(rid, {})   # {umaban: mark}
            top3 = results.get(rid, [])        # [{rank, umaban, ninki}]

            # 印のカウント（このレースでどの印をつけたか）
            for mark in ALL_MARKS:
                if mark in pred.values():
                    mark_total[mark] += 1

            if not top3:
                # 結果未取得
                lines.append(f'  {race_no:02d}R  （結果未取得）')
                continue

            # 1着/2着/3着それぞれの印と人気
            col_marks = []
            col_ninkis = []
            hit_details = []

            for r in top3:
                uma   = r['umaban']
                ninki = r['ninki']
                mark  = pred.get(uma, '－')
                col_marks.append(mark)
                col_ninkis.append(f'{ninki}人気' if ninki else '－')

                if mark != '－':
                    mark_hits[mark] += 1
                    rank = r['rank']
                    if rank == 1 and rid in payouts:
                        odds_x = payouts[rid] / 100
                        hit_details.append(f'{mark}1着@{odds_x:.1f}x')
                    else:
                        hit_details.append(f'{mark}{rank}着')

            # 3着分揃っていない場合は－で埋める
            while len(col_marks) < 3:
                col_marks.append('－')
                col_ninkis.append('－')

            main = f'  {race_no:02d}R  {col_marks[0]} {col_marks[1]} {col_marks[2]}  ({", ".join(col_ninkis[:3])})'
            if hit_details:
                main += '  ' + '  '.join(hit_details)
            lines.append(main)

    # 印別3着内率サマリー
    lines.append('\n\n■ 印別3着内率')
    summary_parts = []
    for mark in ALL_MARKS:
        total = mark_total[mark]
        hits  = mark_hits[mark]
        if total > 0:
            pct = hits / total * 100
            summary_parts.append(f'{mark} {hits}/{total} ({pct:.0f}%)')
    lines.append('  '.join(summary_parts))



    body = '\n'.join(lines)
    return title, body


# ── note.com 無料記事投稿 ─────────────────────────────────────

async def post_free_article(title: str, body: str, stop_before_post: bool = False) -> bool:
    """無料記事としてnote.comに投稿する。stop_before_post=True なら投稿直前で60秒待機して終了。"""
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        page    = await browser.new_page()
        try:
            # ログイン
            await page.goto('https://note.com/login', wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)
            email_sel = 'input[type="email"], #email, input[name="email"]'
            pw_sel    = 'input[type="password"], #password, input[name="password"]'
            await page.locator(email_sel).first.wait_for(state='visible', timeout=10_000)
            await page.locator(email_sel).first.fill(NOTE_EMAIL)
            await page.locator(email_sel).first.dispatch_event('input')
            await page.locator(pw_sel).first.fill(NOTE_PASSWORD)
            await page.locator(pw_sel).first.dispatch_event('input')
            await page.wait_for_timeout(1000)
            await page.locator('button:has-text("ログイン")').last.click()
            await page.wait_for_function(
                "() => !window.location.href.includes('/login')", timeout=30_000
            )
            print('  [note] ログイン完了')

            # エディタ
            await page.goto('https://editor.note.com/new', wait_until='domcontentloaded')
            await page.wait_for_timeout(2000)

            # タイトル
            await page.fill('textarea[placeholder="記事タイトル"]', title)
            await page.wait_for_timeout(500)

            # 本文
            editor = page.locator('.ProseMirror').first
            await editor.click()
            await page.keyboard.type(body, delay=5)
            await page.wait_for_timeout(1000)
            print('  [note] 本文入力完了')

            # 公開に進む
            await page.click('button:has-text("公開に進む")')
            await page.wait_for_timeout(3000)

            if stop_before_post:
                print('\n=== 投稿直前で停止 ===')
                print('ブラウザを確認してください（60秒後に自動終了）')
                await page.wait_for_timeout(60_000)
                return False

            # 無料記事 → 価格設定不要、そのまま投稿
            for btn_text in ['投稿する', '公開する']:
                btn = page.locator(f'button:has-text("{btn_text}")').first
                if await btn.count() > 0:
                    await btn.scroll_into_view_if_needed()
                    await btn.click(timeout=10_000)
                    print(f'  [note] 投稿ボタン: 「{btn_text}」')
                    break

            await page.wait_for_timeout(5000)
            # 公開成功 = 「記事が公開されました」ダイアログ or URLがnote.comへリダイレクト
            success_dialog = await page.locator('text=記事が公開されました').count()
            if success_dialog > 0 or 'editor.note.com' not in page.url:
                print(f'  [note] 投稿完了: {page.url}')
                return True
            raise Exception(f'投稿未完了（URL: {page.url}）')

        except Exception as e:
            print(f'  [ERROR] {e}')
            return False
        finally:
            await browser.close()


# ── main ──────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='AI予想成績レポートをnoteに無料投稿')
    parser.add_argument('--dry',     action='store_true', help='記事テキストを表示するだけ（投稿しない）')
    parser.add_argument('--preview', action='store_true', help='ブラウザで確認（投稿直前で60秒停止）')
    parser.add_argument('--date',    default=None,        help='対象日付 YYYYMMDD（省略で今日）')
    args = parser.parse_args()

    target_date = args.date or date.today().strftime('%Y%m%d')

    print(f'\n=== AI予想成績レポート  {target_date} ===')

    title, body = format_report(target_date)
    if not title:
        print('  予測データが見つかりません。')
        print('  → run_auto_post.py が今日実行されているか確認してください。')
        return

    print(f'\nタイトル: {title}')
    print('─' * 60)
    print(body)
    print('─' * 60)

    if args.dry:
        print('\n[DRY RUN] 投稿をスキップしました。')
        return

    print('\nブラウザを起動中...')
    ok = asyncio.run(post_free_article(title, body, stop_before_post=args.preview))
    if args.preview:
        print('確認完了。投稿する場合は --preview なしで実行してください。')
    elif ok:
        print('投稿完了')
    else:
        print('投稿失敗。--dry で内容を確認してください。')


if __name__ == '__main__':
    main()
