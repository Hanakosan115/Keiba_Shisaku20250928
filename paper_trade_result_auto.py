# -*- coding: utf-8 -*-
"""
paper_trade_result_auto.py — ペーパートレード結果自動取得・更新スクリプト

netkeiba のレース結果ページから単勝払戻しを取得し、
paper_trade_log.csv の「未確定」ベットを自動的に確定する。

【使い方】
  py paper_trade_result_auto.py             # 今日の未確定分を全自動更新
  py paper_trade_result_auto.py --dry       # 確認のみ（CSVは更新しない）
  py paper_trade_result_auto.py --date 20260308  # 日付指定

【注意】
  レース終了後（最終レース発走から1時間以上後）に実行すること。
  発走前のレースはスキップされる。
"""
import sys, os, csv, time, re, argparse, sqlite3
import requests
from bs4 import BeautifulSoup
from datetime import date, datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
LOG_CSV   = os.path.join(BASE_DIR, 'paper_trade_log.csv')
DB_PATH   = os.path.join(BASE_DIR, 'odds_collector', 'odds_timeseries.db')

INITIAL_BANKROLL = 50_000
BET_UNIT         = 100
SLEEP_SEC        = 1.5   # netkeiba へのリクエスト間隔
HEADERS          = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

LOG_COLUMNS = [
    'date', 'race_id', 'race_name', 'horse_name', 'horse_id',
    'bet_type', 'pred_win', 'pred_place', 'pred_win_calibrated',
    'odds', 'odds_recorded_time', 'bet_rule', 'bet_amount',
    'kelly_theoretical', 'result', 'payout', 'pl', 'bankroll', 'memo',
]

SEP = '─' * 60


# ── CSV 読み書き ──────────────────────────────────────────────

def load_rows() -> list[dict]:
    if not os.path.exists(LOG_CSV):
        return []
    with open(LOG_CSV, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def save_rows(rows: list[dict]):
    with open(LOG_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLUMNS)
        w.writeheader()
        w.writerows(rows)


def last_confirmed_bankroll(rows: list[dict]) -> float:
    confirmed = [r for r in rows if r.get('result') in ('的中', 'ハズレ')]
    if not confirmed:
        return float(INITIAL_BANKROLL)
    try:
        return float(confirmed[-1]['bankroll'])
    except (ValueError, KeyError):
        return float(INITIAL_BANKROLL)


# ── netkeiba スクレイプ ──────────────────────────────────────

def fetch_result_page(race_id: str):
    """レース結果ページの BeautifulSoup を返す。失敗時は None。"""
    url = f'https://race.netkeiba.com/race/result.html?race_id={race_id}'
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20)
        resp.raise_for_status()
        resp.encoding = 'euc-jp'
        return BeautifulSoup(resp.text, 'lxml')
    except Exception as e:
        print(f'  [WARN] {race_id} ページ取得失敗: {e}')
        return None


def parse_tansho_payout(soup) -> dict[str, int]:
    """
    単勝払戻しを {馬番: 払戻し額} で返す。
    例: {'3': 2840}
    """
    result = {}
    tables = soup.select('.Result_Pay_Back .Payout_Detail_Table')
    if not tables:
        tables = soup.select('table.pay_table_01')

    current_type = None
    for table in tables:
        for tr in table.select('tr'):
            ths = tr.select('th')
            tds = tr.select('td')
            if ths:
                if '単勝' in ths[0].get_text():
                    current_type = '単勝'
                elif any(k in ths[0].get_text() for k in ('複勝','馬連','ワイド','馬単','三連','枠連')):
                    current_type = 'other'
            if current_type == '単勝' and len(tds) >= 2:
                # 馬番
                num_td = tds[0]
                pay_td = tds[1]
                for br in num_td.find_all('br'):
                    br.replace_with('\n')
                for br in pay_td.find_all('br'):
                    br.replace_with('\n')
                nums = [n.strip() for n in num_td.get_text().split('\n') if n.strip()]
                pays = [p.strip() for p in pay_td.get_text().split('\n') if p.strip()]
                for n, p in zip(nums, pays):
                    p_clean = re.sub(r'[^\d]', '', p)
                    if n and p_clean:
                        result[n] = int(p_clean)
    return result


def parse_combo_payout(soup, bet_type: str) -> dict[str, int]:
    """
    ワイドまたは馬連の払戻しを {"X-Y": 額} で返す（X < Y, 馬番の数値ソート済み）。
    例: {"1-3": 2340, "1-5": 1820}
    """
    result = {}
    tables = soup.select('.Result_Pay_Back .Payout_Detail_Table')
    if not tables:
        tables = soup.select('table.pay_table_01')

    current_type = None
    for table in tables:
        for tr in table.select('tr'):
            ths = tr.select('th')
            tds = tr.select('td')
            if ths:
                text = ths[0].get_text()
                if bet_type in text:
                    current_type = bet_type
                elif any(k in text for k in ('単勝', '複勝', '馬連', 'ワイド', '馬単', '三連', '枠連')):
                    current_type = 'other'
            if current_type == bet_type and len(tds) >= 2:
                num_td = tds[0]
                pay_td = tds[1]
                for br in num_td.find_all('br'):
                    br.replace_with('\n')
                for br in pay_td.find_all('br'):
                    br.replace_with('\n')
                nums = [n.strip() for n in num_td.get_text().split('\n') if n.strip()]
                pays = [p.strip() for p in pay_td.get_text().split('\n') if p.strip()]
                for n, p in zip(nums, pays):
                    parts = re.split(r'[\-\s－ー]+', n)
                    parts = [x.strip() for x in parts if x.strip().isdigit()]
                    p_clean = re.sub(r'[^\d]', '', p)
                    if len(parts) == 2 and p_clean:
                        a, b = sorted([int(parts[0]), int(parts[1])])
                        result[f'{a}-{b}'] = int(p_clean)
    return result


def parse_result_table(soup) -> dict[str, str]:
    """着順結果テーブルから {馬番: 馬名} を返す（単勝的中判定用）。"""
    return {r['umaban']: r['horse_name'] for r in parse_result_top3_full(soup)}


def parse_result_top3_full(soup) -> list[dict]:
    """
    結果テーブルから全着順を取得し、上位3着分の詳細を返す。
    Returns: [{'rank':1,'umaban':'3','horse_name':'テリオスララ','ninki':1}, ...]
    """
    selectors = [
        '#All_Result_Table tbody tr',
        '.race_table_01 tbody tr',
        'table.ResultCommon tbody tr',
        '.RaceResult_Table_Wrap table tbody tr',
    ]
    rows_found = []
    for sel in selectors:
        rows_found = soup.select(sel)
        if rows_found:
            break

    results = []
    for tr in rows_found:
        tds = tr.select('td')
        if len(tds) < 5:
            continue
        try:
            rank_text = tds[0].get_text(strip=True)
            rank_clean = re.sub(r'[^\d]', '', rank_text)
            if not rank_clean:
                continue
            rank = int(rank_clean)
            # 同着考慮: 先頭3行を取得（rank > 3 でも同着なら含む）
            if len(results) >= 3:
                break
            if rank > 3 and not results:
                continue  # 明らかに上位でない場合はスキップ
            umaban = tds[2].get_text(strip=True)
            horse_a = tds[3].find('a')
            horse_name = horse_a.get_text(strip=True) if horse_a else tds[3].get_text(strip=True)
            # 人気は末尾のtdにあることが多い
            ninki = 0
            for td in reversed(tds):
                t = td.get_text(strip=True)
                if re.fullmatch(r'\d{1,2}', t):
                    ninki = int(t)
                    break
            if umaban:
                results.append({'rank': rank, 'umaban': umaban,
                                 'horse_name': horse_name, 'ninki': ninki})
        except (ValueError, IndexError, AttributeError):
            continue

    return results  # テーブル順（着順）のまま返す


def save_race_results(race_id: str, top3: list[dict]):
    """結果（1〜3着・人気）をDBに保存。"""
    if not top3 or not os.path.exists(DB_PATH):
        return
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS race_results (
            race_id    TEXT,
            rank       INTEGER,
            umaban     TEXT,
            horse_name TEXT,
            ninki      INTEGER,
            created_at TEXT,
            PRIMARY KEY (race_id, umaban)
        )
    ''')
    now = datetime.now().isoformat()
    for r in top3:
        conn.execute('''
            INSERT OR REPLACE INTO race_results
            (race_id, rank, umaban, horse_name, ninki, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (race_id, r['rank'], r['umaban'], r['horse_name'], r['ninki'], now))
    conn.commit()
    conn.close()


def get_race_result(race_id: str) -> dict | None:
    """
    race_id の単勝結果を取得する。
    Returns: {'winner_umaban': '3', 'winner_name': '馬名', 'payout': 2840}
    レース未終了・取得失敗時は None。
    """
    soup = fetch_result_page(race_id)
    if soup is None:
        return None

    # 結果なし判定（まだ発走前など）
    no_result = soup.select_one('.No_Result') or soup.select_one('.result_none')
    if no_result:
        return None

    tansho = parse_tansho_payout(soup)
    if not tansho:
        return None

    top3 = parse_result_top3_full(soup)
    save_race_results(race_id, top3)

    horses = {r['umaban']: r['horse_name'] for r in top3}

    winner_uma, payout = next(iter(tansho.items()))
    winner_name = horses.get(winner_uma, '')

    return {
        'winner_umaban':  winner_uma,
        'winner_name':    winner_name,
        'payout':         payout,
        'top3':           top3,
        'wide_payouts':   parse_combo_payout(soup, 'ワイド'),
        'umaren_payouts': parse_combo_payout(soup, '馬連'),
    }


# ── メイン処理 ───────────────────────────────────────────────

def normalize(s: str) -> str:
    """比較用: 全角スペース・記号を除いた馬名正規化"""
    return re.sub(r'[\s　・]', '', str(s)).upper()


def main():
    parser = argparse.ArgumentParser(description='ペーパートレード結果自動更新')
    parser.add_argument('--dry',      action='store_true', help='確認のみ（CSV更新しない）')
    parser.add_argument('--date',     default=None,        help='対象日付 YYYYMMDD（省略で今日）')
    parser.add_argument('--backfill', action='store_true', help='確定済み含む全レースのrace_resultsをDBに保存')
    args = parser.parse_args()

    target_date = args.date or date.today().strftime('%Y%m%d')
    target_iso  = f'{target_date[:4]}-{target_date[4:6]}-{target_date[6:]}'

    print(f'\n{SEP}')
    print(f' ペーパートレード結果自動更新  {target_date}')
    if args.dry:
        print('  ※ DRY RUNモード（CSV更新なし）')
    print(SEP)

    rows = load_rows()

    # ── backfill モード: race_predictionsの全race_idの結果をDBに保存 ──
    if args.backfill:
        all_rids = []
        if os.path.exists(DB_PATH):
            import sqlite3 as _sq
            conn = _sq.connect(DB_PATH)
            try:
                rows_db = conn.execute(
                    "SELECT DISTINCT race_id FROM race_predictions WHERE created_at LIKE ?",
                    (f'{target_iso}%',)
                ).fetchall()
                all_rids = [r[0] for r in rows_db]
            except Exception:
                pass
            conn.close()
        if not all_rids:
            # フォールバック: paper_trade_log.csv から
            all_rids = list(dict.fromkeys(
                r['race_id'] for r in rows if r.get('date', '') == target_iso
            ))
        print(f'  バックフィル: {len(all_rids)}レース')
        for rid in sorted(all_rids):
            time.sleep(SLEEP_SEC)
            get_race_result(rid)
            print(f'    {rid} → 保存完了')
        print(f'  完了。')
        return

    # 対象日の未確定ベットを抽出
    pending = [(i, r) for i, r in enumerate(rows)
               if r.get('result') == '未確定' and r.get('date', '') == target_iso]

    if not pending:
        print(f'  {target_iso} の未確定ベットはありません。')
        return

    print(f'  未確定ベット: {len(pending)}件\n')

    # race_id ごとにグループ化
    race_groups: dict[str, list] = {}
    for i, r in pending:
        rid = r['race_id']
        race_groups.setdefault(rid, []).append((i, r))

    hit = 0
    miss = 0
    skip = 0

    for race_id, bets in race_groups.items():
        race_name = bets[0][1].get('race_name', '')
        print(f'  [{race_id}] {race_name}')

        time.sleep(SLEEP_SEC)
        result = get_race_result(race_id)

        if result is None:
            print(f'    → 結果未確定 or 取得失敗 → スキップ')
            skip += len(bets)
            continue

        winner_name = result['winner_name']
        winner_uma  = result['winner_umaban']
        payout_amt  = result['payout']
        print(f'    → 単勝: {winner_name}（{winner_uma}番）@ {payout_amt}円')

        # top3 の {馬名: 馬番} マップ（ワイド・馬連判定用）
        top3_list   = result.get('top3', [])
        top3_umas   = [r['umaban'] for r in top3_list]          # 1-3着の馬番リスト
        top2_umas   = top3_umas[:2]                              # 1-2着
        name_to_uma = {}
        for r in top3_list:
            name_to_uma[normalize(r['horse_name'])] = r['umaban']

        for i, row in bets:
            horse      = row['horse_name']
            bet_type   = row.get('bet_type', '単勝')
            bet_amount = int(row.get('bet_amount', BET_UNIT))
            bankroll   = last_confirmed_bankroll(rows)

            if bet_type == '単勝':
                # 既存ロジック: 馬名一致
                is_hit   = normalize(horse) == normalize(winner_name)
                if not is_hit and winner_name:
                    is_hit = normalize(winner_name) in normalize(horse) or \
                             normalize(horse) in normalize(winner_name)
                pay_result = payout_amt if is_hit else 0

            elif bet_type in ('ワイド', '馬連'):
                # horse = "馬名A×馬名B"
                parts = horse.split('×')
                if len(parts) != 2:
                    print(f'    [SKIP] 馬名形式エラー: {horse}')
                    skip += 1
                    continue
                ha, hb = normalize(parts[0].strip()), normalize(parts[1].strip())
                # 馬番を名前から逆引き
                uma_a = name_to_uma.get(ha)
                uma_b = name_to_uma.get(hb)
                # 部分一致フォールバック
                if uma_a is None:
                    for nm, uma in name_to_uma.items():
                        if ha in nm or nm in ha:
                            uma_a = uma; break
                if uma_b is None:
                    for nm, uma in name_to_uma.items():
                        if hb in nm or nm in hb:
                            uma_b = uma; break

                if bet_type == 'ワイド':
                    is_hit = uma_a in top3_umas and uma_b in top3_umas
                    if is_hit and uma_a and uma_b:
                        a, b = sorted([int(uma_a), int(uma_b)])
                        pay_result = result.get('wide_payouts', {}).get(f'{a}-{b}', 0)
                    else:
                        pay_result = 0
                else:  # 馬連
                    is_hit = uma_a in top2_umas and uma_b in top2_umas
                    if is_hit and uma_a and uma_b:
                        a, b = sorted([int(uma_a), int(uma_b)])
                        pay_result = result.get('umaren_payouts', {}).get(f'{a}-{b}', 0)
                    else:
                        pay_result = 0
            else:
                print(f'    [SKIP] 未対応bet_type: {bet_type}')
                skip += 1
                continue

            if is_hit:
                pl   = pay_result - bet_amount
                bank = bankroll - bet_amount + pay_result
                rows[i]['result']   = '的中'
                rows[i]['payout']   = str(pay_result)
                rows[i]['pl']       = str(pl)
                rows[i]['bankroll'] = str(bank)
                print(f'    [HIT] {bet_type}: {horse}  払戻={pay_result}円  損益={pl:+,}円  残高={bank:,}円')
                hit += 1
            else:
                pl   = -bet_amount
                bank = bankroll - bet_amount
                rows[i]['result']   = 'ハズレ'
                rows[i]['payout']   = '0'
                rows[i]['pl']       = str(pl)
                rows[i]['bankroll'] = str(bank)
                print(f'    [---] ハズレ: {bet_type} {horse}')
                miss += 1

    # 集計
    total = hit + miss
    roi   = 0.0
    confirmed = [r for r in rows if r.get('result') in ('的中', 'ハズレ')]
    if confirmed:
        total_bet    = sum(int(r.get('bet_amount', BET_UNIT)) for r in confirmed)
        total_payout = sum(int(r.get('payout', 0)) for r in confirmed)
        roi = total_payout / total_bet * 100 if total_bet > 0 else 0.0

    print(f'\n{SEP}')
    print(f'  本日確定: {total}件  的中{hit}件({hit/total:.0%})  ROI{roi:.1f}%' if total > 0 else '  本日確定: 0件')
    print(f'  スキップ: {skip}件（結果未発表 or 取得失敗）')
    print(f'  累計確定ベット: {len(confirmed)}件')

    if not args.dry:
        save_rows(rows)
        print(f'  → paper_trade_log.csv を更新しました。')

    # ── 補完: race_predictions にあるが race_results にないレースの結果を取得 ──
    # Rule4ベットなしのレースも成績レポートに反映するために必要
    extra_rids = []
    if os.path.exists(DB_PATH):
        import sqlite3 as _sq
        conn2 = _sq.connect(DB_PATH)
        try:
            pred_rows = conn2.execute(
                "SELECT DISTINCT race_id FROM race_predictions WHERE created_at LIKE ?",
                (f'{target_iso}%',)
            ).fetchall()
            all_pred_ids = [r[0] for r in pred_rows]
            if all_pred_ids:
                placeholders = ','.join('?' * len(all_pred_ids))
                done_rows = conn2.execute(
                    f"SELECT DISTINCT race_id FROM race_results WHERE race_id IN ({placeholders})",
                    all_pred_ids
                ).fetchall()
                done_ids = {r[0] for r in done_rows}
                extra_rids = [rid for rid in all_pred_ids if rid not in done_ids]
        except Exception:
            pass
        conn2.close()

    if extra_rids:
        print(f'\n  [補完] race_results 未保存レース: {len(extra_rids)}件 → 結果取得中...')
        for rid in sorted(extra_rids):
            time.sleep(SLEEP_SEC)
            get_race_result(rid)
            print(f'    {rid} → 保存完了')
        print(f'  補完完了。')
    else:
        print(f'  → DRY RUN: CSV は更新されていません。')

    print(SEP + '\n')


if __name__ == '__main__':
    main()
