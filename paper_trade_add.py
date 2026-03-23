# -*- coding: utf-8 -*-
"""
paper_trade_add.py — ペーパートレード記録CLI

【使い方】
  py paper_trade_add.py           # 新規ベット追加（対話式）
  py paper_trade_add.py --result  # 結果更新モード
  py paper_trade_add.py --list    # 未確定ベット一覧
  py paper_trade_add.py --summary # 簡易集計表示

【ワークフロー】
  1. レース前: py paper_trade_add.py         → GUIの予測結果を入力（result=未確定）
  2. レース後: py paper_trade_add.py --result → 的中/ハズレと払戻し金額を入力
  3. 月末:     py paper_trade_review.py        → GO/NO-GO 判定
"""
import sys, os, argparse, csv
from datetime import date, datetime

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stdin.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR        = os.path.dirname(os.path.abspath(__file__))
LOG_CSV         = os.path.join(BASE_DIR, 'paper_trade_log.csv')
INITIAL_BANKROLL = 50_000
BET_UNIT         = 100

COLUMNS = [
    'date', 'race_id', 'race_name', 'horse_name', 'horse_id',
    'bet_type', 'pred_win', 'pred_place', 'pred_win_calibrated',
    'odds', 'odds_recorded_time', 'bet_rule', 'bet_amount',
    'kelly_theoretical', 'result', 'payout', 'pl', 'bankroll', 'memo',
]

SEP = '─' * 60


def load_rows() -> list[dict]:
    if not os.path.exists(LOG_CSV):
        return []
    rows = []
    with open(LOG_CSV, encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def save_rows(rows: list[dict]):
    with open(LOG_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def get_last_bankroll(rows: list[dict]) -> float:
    confirmed = [r for r in rows if r.get('result') in ('的中', 'ハズレ')]
    if not confirmed:
        return float(INITIAL_BANKROLL)
    try:
        return float(confirmed[-1]['bankroll'])
    except (ValueError, KeyError):
        return float(INITIAL_BANKROLL)


def calc_kelly(pred_win: float, odds: float, bankroll: float) -> float:
    """Kelly基準ベット額（円）を計算"""
    if odds <= 1:
        return 0.0
    k = (pred_win * odds - 1.0) / (odds - 1.0)
    k = max(0.0, min(k, 0.5))  # 上限50%（過剰ベット防止）
    return round(k * bankroll)


def prompt(label: str, default=None, choices=None) -> str:
    """対話入力ヘルパー"""
    hint = f' ({"/".join(choices)})' if choices else ''
    def_hint = f' [デフォルト: {default}]' if default is not None else ''
    while True:
        val = input(f'  {label}{hint}{def_hint}: ').strip()
        if val == '' and default is not None:
            return str(default)
        if choices and val not in choices:
            print(f'    ※ {"/".join(choices)} のいずれかを入力してください')
            continue
        if val:
            return val
        print('    ※ 必須項目です')


def prompt_float(label: str, default=None) -> float:
    while True:
        raw = prompt(label, default=default)
        try:
            return float(raw)
        except ValueError:
            print('    ※ 数値を入力してください')


def cmd_add(rows: list[dict]):
    """新規ベット追加"""
    print(f'\n{SEP}')
    print(' 新規ベット追加')
    print(f'{SEP}')
    print('  ※ Enter でデフォルト値を使用\n')

    today = date.today().strftime('%Y-%m-%d')
    row = {}

    row['date']      = prompt('日付 (YYYY-MM-DD)', default=today)
    row['race_id']   = prompt('race_id (例: 202606010311)')
    row['race_name'] = prompt('レース名 (例: 東京11R)', default='')
    row['horse_name']= prompt('馬名')
    row['horse_id']  = prompt('horse_id (不明なら空)', default='')
    row['bet_type']  = prompt('馬券種別', default='単勝', choices=['単勝', '複勝', 'ワイド', '馬連'])
    row['pred_win']  = prompt('予測単勝確率 (例: 0.25)', default='')
    row['pred_place']= prompt('予測複勝確率 (例: 0.55)', default='')
    row['pred_win_calibrated'] = row['pred_win']

    odds_str = prompt('オッズ (例: 8.5)')
    try:
        odds = float(odds_str)
    except ValueError:
        odds = 0.0
    row['odds'] = odds_str
    row['odds_recorded_time'] = datetime.now().strftime('%Y-%m-%d %H:%M')

    row['bet_rule']   = prompt('ベットルール', default='Rule4',
                                choices=['Rule4', '条件A', '条件B', '手動'])
    row['bet_amount'] = prompt('ベット額（円）', default=str(BET_UNIT))

    # Kelly理論値を自動計算
    try:
        pw   = float(row['pred_win']) if row['pred_win'] else 0.0
        bk   = get_last_bankroll(rows)
        kelly = calc_kelly(pw, odds, bk)
    except (ValueError, ZeroDivisionError):
        kelly = 0
    row['kelly_theoretical'] = str(kelly)

    row['result']  = '未確定'
    row['payout']  = '0'
    row['pl']      = '0'
    row['bankroll'] = '0'  # 確定時に更新
    row['memo']    = prompt('メモ（任意）', default='')

    rows.append(row)
    save_rows(rows)

    print(f'\n  ✅ 追加しました: {row["date"]} {row["horse_name"]} '
          f'@{row["odds"]}x  Kelly推奨: {kelly:.0f}円')


def cmd_result(rows: list[dict]):
    """結果更新"""
    pending = [(i, r) for i, r in enumerate(rows) if r.get('result') == '未確定']

    if not pending:
        print('\n  未確定のベットはありません。')
        return

    print(f'\n{SEP}')
    print(' 結果更新（未確定ベット一覧）')
    print(SEP)
    print(f'  {"#":<3} {"日付":<12} {"race_id":<16} {"馬名":<16} {"オッズ":>6} {"ルール":<8}')
    print(f'  {"-"*65}')
    for no, (i, r) in enumerate(pending, 1):
        print(f'  {no:<3} {r.get("date",""):<12} {r.get("race_id",""):<16} '
              f'{r.get("horse_name",""):<16} {r.get("odds",""):>6}x  {r.get("bet_rule",""):<8}')

    print()
    no_str = prompt(f'更新する番号 (1-{len(pending)}、全て=all)')

    if no_str.lower() == 'all':
        targets = list(range(len(pending)))
    else:
        try:
            targets = [int(no_str) - 1]
        except ValueError:
            print('  ※ 無効な番号です')
            return

    for t in targets:
        if t < 0 or t >= len(pending):
            continue
        idx, row = pending[t]
        print(f'\n  --- {row.get("horse_name")} ({row.get("date")}) ---')
        result = prompt('結果', choices=['的中', 'ハズレ'])
        if result == '的中':
            payout_str = prompt('払戻し額（円）')
            try:
                payout = int(payout_str)
            except ValueError:
                payout = 0
        else:
            payout = 0

        bet_amount = int(row.get('bet_amount', BET_UNIT))
        pl         = payout - bet_amount
        last_bank  = get_last_bankroll(rows)
        bankroll   = last_bank - bet_amount + payout

        rows[idx]['result']   = result
        rows[idx]['payout']   = str(payout)
        rows[idx]['pl']       = str(pl)
        rows[idx]['bankroll'] = str(bankroll)

        mark = '✅' if result == '的中' else '❌'
        print(f'  {mark} 確定: {result}  払戻し={payout}円  損益={pl:+,.0f}円  残高={bankroll:,.0f}円')

    save_rows(rows)
    print(f'\n  保存しました。')


def cmd_list(rows: list[dict]):
    """未確定ベット一覧"""
    pending = [r for r in rows if r.get('result') == '未確定']
    confirmed = [r for r in rows if r.get('result') in ('的中', 'ハズレ')]

    print(f'\n{SEP}')
    print(f' ペーパートレード状況  （確定: {len(confirmed)}件 / 未確定: {len(pending)}件）')
    print(SEP)

    if pending:
        print(f'\n  【未確定】')
        print(f'  {"日付":<12} {"race_id":<16} {"馬名":<16} {"オッズ":>6} {"予測":>6} {"ルール":<8}')
        print(f'  {"-"*70}')
        for r in pending:
            pw = r.get('pred_win', '')
            try:
                pw_str = f'{float(pw):.0%}'
            except (ValueError, TypeError):
                pw_str = pw
            print(f'  {r.get("date",""):<12} {r.get("race_id",""):<16} '
                  f'{r.get("horse_name",""):<16} {r.get("odds",""):>6}x '
                  f'{pw_str:>6}  {r.get("bet_rule",""):<8}')
    else:
        print('\n  未確定ベットはありません。')


def cmd_summary(rows: list[dict]):
    """簡易集計"""
    confirmed = [r for r in rows if r.get('result') in ('的中', 'ハズレ')]

    print(f'\n{SEP}')
    print(' 簡易集計')
    print(SEP)

    if not confirmed:
        print('  確定ベットなし')
        return

    n     = len(confirmed)
    hits  = sum(1 for r in confirmed if r.get('result') == '的中')
    total_bet    = sum(int(r.get('bet_amount', BET_UNIT)) for r in confirmed)
    total_payout = sum(int(r.get('payout', 0)) for r in confirmed)
    total_pl     = total_payout - total_bet
    roi          = total_payout / total_bet * 100 if total_bet > 0 else 0
    last_bank    = get_last_bankroll(rows)

    print(f'\n  ベット件数:  {n}件（的中 {hits}件 / {hits/n:.1%}）')
    print(f'  総ベット額: {total_bet:>10,.0f}円')
    print(f'  総払戻し:   {total_payout:>10,.0f}円')
    print(f'  純損益:     {total_pl:>+10,.0f}円')
    print(f'  回収率:     {roi:>10.1f}%')
    print(f'  現在残高:   {last_bank:>10,.0f}円（初期: {INITIAL_BANKROLL:,.0f}円）')


def main():
    parser = argparse.ArgumentParser(
        description='ペーパートレード記録CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--result',  action='store_true', help='結果更新モード')
    parser.add_argument('--list',    action='store_true', help='未確定一覧表示')
    parser.add_argument('--summary', action='store_true', help='簡易集計表示')
    args = parser.parse_args()

    rows = load_rows()

    if args.result:
        cmd_result(rows)
    elif args.list:
        cmd_list(rows)
    elif args.summary:
        cmd_summary(rows)
    else:
        cmd_add(rows)

    print()


if __name__ == '__main__':
    main()
