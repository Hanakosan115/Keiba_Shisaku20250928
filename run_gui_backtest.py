# -*- coding: utf-8 -*-
"""
run_gui_backtest.py — GUI完全一致バックテスト（Phase 14対応・依存ファイル修正版）

backtest_gui_logic_clean.py の正当後継版。
外部JSONファイル依存を排除し、ローカルデータのみで動作する。

【GUIとの同一性】
  gui.get_race_from_database(race_id)  ← GUIと同じデータ取得
  gui.predict_core(...)               ← GUIと同じ予測ロジック
  current_date = レース日付            ← 未来データリーク防止

【払戻データ】
  data/main/netkeiba_data_2020_2025_enriched.csv（着順・オッズ）
  ※ GUIがネットから取る値と同等のものをローカルで代用

使い方:
  py run_gui_backtest.py                     # 全期間
  py run_gui_backtest.py --year 2024         # 2024年のみ
  py run_gui_backtest.py --year 2023 2024    # 複数年
  py run_gui_backtest.py --sample 200        # 最初の200レースのみ（動作確認用）
  py run_gui_backtest.py --year 2024 --sample 50
"""
import sys
import os
import re
import time
import argparse
import tkinter as tk
import warnings

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENRICHED_PATH = os.path.join(BASE_DIR, 'data', 'main',
                              'netkeiba_data_2020_2025_enriched.csv')
BET_UNIT = 100  # 1点100円固定

VENUE_MAP = {
    '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
    '05': '東京', '06': '中山', '07': '中京', '08': '京都',
    '09': '阪神', '10': '小倉',
}


def normalize_date_str(date_str):
    """日付文字列を'YYYY-MM-DD'に正規化"""
    s = str(date_str)
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', s)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    m = re.search(r'(\d{4}-\d{2}-\d{2})', s)
    if m:
        return m.group(1)
    return s


def build_payout_table():
    """
    払戻テーブルをローカルデータから構築。
    戻り値: {race_id_str: {umaban_str: {'rank': int, 'odds': float}}}
    """
    print("着順・オッズデータ読み込み中...")
    df = pd.read_csv(ENRICHED_PATH,
                     usecols=['race_id', 'Umaban', 'Rank', 'Odds_x'],
                     low_memory=False)
    # 有効なrace_id（12桁数字）のみ
    df = df[df['race_id'].astype(str).str.match(r'^\d{12}$')].copy()
    df['race_id'] = df['race_id'].astype(str)
    df['Umaban'] = df['Umaban'].apply(
        lambda x: str(int(float(x))) if pd.notna(x) else ''
    )
    df['rank'] = pd.to_numeric(df['Rank'], errors='coerce')
    df['odds'] = pd.to_numeric(df['Odds_x'], errors='coerce')

    payout = {}
    for _, row in df.iterrows():
        rid = row['race_id']
        if rid not in payout:
            payout[rid] = {}
        payout[rid][row['Umaban']] = {
            'rank': row['rank'],
            'odds': row['odds'],
        }

    print(f"  払戻テーブル: {len(payout):,}レース")
    return payout


def main():
    parser = argparse.ArgumentParser(description='GUI完全一致バックテスト（Phase 14）')
    parser.add_argument('--year', type=int, nargs='+',
                        help='対象年（例: 2024 or 2023 2024）')
    parser.add_argument('--sample', type=int, default=0,
                        help='先頭Nレースのみ（動作確認用）')
    args = parser.parse_args()

    print("=" * 70)
    print("  GUI完全一致バックテスト（Phase 14）")
    print("  KeibaGUIv3.predict_core() を直接呼び出し")
    print("  current_date = レース日付（リーケージ防止）")
    print("=" * 70)

    # ── GUI インスタンス作成 ──────────────────────────────
    print("\nGUI初期化中（ダミーウィンドウ）...")
    root = tk.Tk()
    root.withdraw()

    from keiba_prediction_gui_v3 import KeibaGUIv3
    gui = KeibaGUIv3(root)

    if gui.df is None:
        print("[ERROR] GUIのデータ読み込みに失敗しました。")
        return

    print(f"  データ: {len(gui.df):,}行")

    # ── 払戻テーブル構築 ──────────────────────────────────
    payout_table = build_payout_table()

    # ── 対象レース ID リスト ──────────────────────────────
    all_race_ids = sorted(gui.df['race_id'].dropna().unique().tolist())

    # 年フィルタ
    if args.year:
        target_years = set(str(y) for y in args.year)
        all_race_ids = [r for r in all_race_ids
                        if str(int(r))[:4] in target_years]

    # サンプル
    if args.sample > 0:
        all_race_ids = all_race_ids[:args.sample]

    print(f"\n対象レース: {len(all_race_ids):,}件")

    # ── バックテスト本体 ──────────────────────────────────
    results = []
    errors = 0
    start_ts = time.time()

    for i, race_id_raw in enumerate(all_race_ids, 1):
        race_id_str = str(int(race_id_raw))

        # 進捗表示
        if i % 200 == 0 or i == 1:
            elapsed = time.time() - start_ts
            pace = elapsed / i
            remain = pace * (len(all_race_ids) - i)
            print(f"  [{i:>5}/{len(all_race_ids)}] "
                  f"残 {remain/60:.0f}分{remain%60:.0f}秒 "
                  f"({errors}エラー)")

        # 払戻データがないレースはスキップ
        if race_id_str not in payout_table:
            errors += 1
            continue

        # ── GUIと同一: データ取得 ───────────────────────
        horses, race_info = gui.get_race_from_database(race_id_str)
        if not horses or not race_info:
            errors += 1
            continue

        # ── オッズを払戻テーブルから注入 ────────────────
        # GUI内部では単勝オッズがある/ないで予測が変わるため補完
        pay_data = payout_table[race_id_str]
        for h in horses:
            umaban = str(h.get('馬番', ''))
            if umaban in pay_data and pay_data[umaban]['odds'] > 0:
                h['単勝オッズ'] = pay_data[umaban]['odds']

        has_odds = any(h.get('単勝オッズ', 0) > 0 for h in horses)

        # ── レース日付（リーケージ防止用）────────────────
        race_date = normalize_date_str(race_info.get('date', ''))
        if not race_date or race_date == 'nan':
            y = race_id_str[:4]
            m = race_id_str[4:6]
            d = race_id_str[6:8]
            race_date = f"{y}-{m}-{d}"

        # ── GUIと同一: 予測コア ──────────────────────────
        try:
            df_pred = gui.predict_core(
                race_id_str, horses, race_info, has_odds,
                current_date=race_date    # ← リーケージ防止の核心
            )
        except Exception as e:
            errors += 1
            continue

        if df_pred is None or len(df_pred) == 0:
            errors += 1
            continue

        # ── GUIと同一: 馬券推奨 ─────────────────────────
        try:
            targets = KeibaGUIv3.get_recommended_bet_targets(df_pred, has_odds)
        except Exception as e:
            errors += 1
            continue

        if targets is None:
            errors += 1
            continue

        # ── 的中判定 ─────────────────────────────────────
        year = int(race_id_str[:4])

        # ◎ 本命 (targets['honmei'] は 馬番の整数)
        honmei_umaban = str(targets.get('honmei', '')) if targets.get('honmei') is not None else ''
        honmei_proba  = float(targets.get('win_proba', 0))

        # 実際の1着馬（着順==1の馬番）
        winner_umaban = ''
        winner_odds   = 0.0
        tan_payout    = 0  # 単勝配当（100円あたり）
        for umaban, d in pay_data.items():
            if d.get('rank') == 1:
                winner_umaban = umaban
                winner_odds   = d.get('odds', 0)
                # 払戻 = オッズ × 100円
                tan_payout = int(winner_odds * 100) if winner_odds > 0 else 0
                break

        honmei_hit = (honmei_umaban == winner_umaban) and (honmei_umaban != '')

        # 月・競馬場
        venue_code = race_id_str[4:6]
        venue_name = VENUE_MAP.get(venue_code, f'場{venue_code}')
        month_str  = race_date[5:7] if len(race_date) >= 7 else '00'

        # Rule4 対象馬（バリューベース or 条件A/B）
        # df_pred の列名は日本語: '馬番', '勝率予測', 'オッズ'
        rule4_bets = []
        for _, row in df_pred.iterrows():
            try:
                umaban = str(int(row['馬番']))
            except Exception:
                continue
            try:
                pw = float(row['勝率予測'])
            except Exception:
                pw = 0.0
            try:
                odds = float(row['オッズ'])
            except Exception:
                odds = 0.0
            if odds <= 0:
                continue
            # 条件A: pred_win>20% AND 2.0≤odds<10
            cond_a = (pw >= 0.20) and (2.0 <= odds < 10.0)
            # 条件B: pred_win>10% AND odds≥10
            cond_b = (pw >= 0.10) and (odds >= 10.0)
            if cond_a or cond_b:
                hit = (umaban == winner_umaban)
                rule4_bets.append({
                    'umaban': umaban,
                    'pred_win': pw,
                    'odds': odds,
                    'hit': hit,
                    'payout': tan_payout if hit else 0,
                    'cond_a': cond_a,
                    'cond_b': cond_b,
                })

        results.append({
            'race_id': race_id_str,
            'date': race_date,
            'year': year,
            'month': month_str,
            'venue_code': venue_code,
            'venue_name': venue_name,
            'honmei_umaban': honmei_umaban,
            'honmei_proba': honmei_proba,
            'honmei_hit': honmei_hit,
            'winner_umaban': winner_umaban,
            'winner_odds': winner_odds,
            'tan_payout': tan_payout,
            'rule4_bets': rule4_bets,
            'has_odds': has_odds,
        })

    elapsed_total = time.time() - start_ts
    print(f"\n完了: {len(results):,}レース処理 / {errors:,}エラー "
          f"({elapsed_total/60:.1f}分)")

    # ─────────────────────────────────────────────────────
    #  集計・レポート
    # ─────────────────────────────────────────────────────
    if not results:
        print("結果なし。終了。")
        return

    print("\n" + "=" * 70)
    print("  【バックテスト結果】GUIと完全一致ロジック（Phase 14）")
    print("=" * 70)

    # ◎ 本命 的中率
    total_races = len(results)
    honmei_hits = sum(1 for r in results if r['honmei_hit'])
    print(f"\n▼ 対象レース: {total_races:,}  (has_odds: {sum(1 for r in results if r['has_odds']):,})")
    print(f"\n【◎ 本命 単勝的中率】")
    print(f"  全体: {honmei_hits:,}/{total_races:,} = {honmei_hits/total_races*100:.1f}%")

    # ◎単勝を全レース買った場合のROI
    honmei_invest = total_races * BET_UNIT
    honmei_payout = sum(r['tan_payout'] for r in results if r['honmei_hit'])
    print(f"  ◎単勝全買い: 投資{honmei_invest:,}円 / 回収{honmei_payout:,}円 / "
          f"ROI {honmei_payout/honmei_invest*100:.1f}%")

    # 年別 ◎本命
    print(f"\n  年別:")
    years = sorted(set(r['year'] for r in results))
    for y in years:
        ry = [r for r in results if r['year'] == y]
        hits = sum(1 for r in ry if r['honmei_hit'])
        inv  = len(ry) * BET_UNIT
        pay  = sum(r['tan_payout'] for r in ry if r['honmei_hit'])
        print(f"  {y}年: {len(ry):,}レース  的中{hits:,}件({hits/len(ry)*100:.1f}%)  "
              f"ROI {pay/inv*100:.1f}%  純損益{pay-inv:+,}円")

    # Rule4
    print(f"\n【Rule4 バックテスト（1点100円 単勝）】")
    print(f"  条件A: pred_win≥20% AND 2.0≤odds<10.0x")
    print(f"  条件B: pred_win≥10% AND odds≥10.0x")

    all_bets = [b for r in results for b in r['rule4_bets']]
    if all_bets:
        total_b = len(all_bets)
        hits_b  = sum(1 for b in all_bets if b['hit'])
        invest_b = total_b * BET_UNIT
        payout_b = sum(b['payout'] for b in all_bets)
        roi_b    = payout_b / invest_b * 100
        print(f"\n  Rule4合計: {total_b:,}件  的中{hits_b:,}件({hits_b/total_b*100:.1f}%)  "
              f"投資{invest_b:,}円  回収{payout_b:,}円  ROI {roi_b:.1f}%  "
              f"純損益{payout_b-invest_b:+,}円")

        # 年別
        print(f"\n  {'年':>4} {'件数':>6} {'的中':>5} {'的中率':>7} {'ROI':>8} {'純損益':>12}")
        print("  " + "-" * 50)
        for y in years:
            yb = [b for r in results if r['year'] == y for b in r['rule4_bets']]
            if not yb:
                continue
            h = sum(1 for b in yb if b['hit'])
            inv = len(yb) * BET_UNIT
            pay = sum(b['payout'] for b in yb)
            print(f"  {y}年 {len(yb):>6} {h:>5} {h/len(yb)*100:>6.1f}% "
                  f"{pay/inv*100:>7.1f}% {pay-inv:>+12,}円")

        # 条件A / B 別
        bets_a = [b for b in all_bets if b['cond_a'] and not b['cond_b']]
        bets_b = [b for b in all_bets if b['cond_b'] and not b['cond_a']]
        bets_ab = [b for b in all_bets if b['cond_a'] and b['cond_b']]
        def _stat(blist, label):
            if not blist: return
            h = sum(1 for b in blist if b['hit'])
            inv = len(blist) * BET_UNIT
            pay = sum(b['payout'] for b in blist)
            print(f"  {label}: {len(blist):,}件  {h/len(blist)*100:.1f}%  ROI {pay/inv*100:.1f}%")
        print()
        _stat(bets_a,  "条件Aのみ(pred>20% odds 2-10x)")
        _stat(bets_b,  "条件Bのみ(pred>10% odds≥10x) ")
        _stat(bets_ab, "条件A∩B  (両条件とも満たす)  ")

        # オッズ帯別
        print(f"\n  【オッズ帯別】")
        bands = [(2,5),(5,10),(10,20),(20,50),(50,999)]
        for lo, hi in bands:
            blist = [b for b in all_bets if lo <= b['odds'] < hi]
            if not blist: continue
            h = sum(1 for b in blist if b['hit'])
            inv = len(blist) * BET_UNIT
            pay = sum(b['payout'] for b in blist)
            hilab = f"{hi}x" if hi < 999 else "∞"
            print(f"  {lo:>3}x〜{hilab:>4}: {len(blist):>5}件  "
                  f"{h/len(blist)*100:.1f}%  ROI {pay/inv*100:.1f}%  "
                  f"純損益{pay-inv:>+10,}円")
    else:
        print("  Rule4ベット対象なし（オッズデータ不足の可能性）")

    # ── 月次集計（Rule4）────────────────────────────────────
    if all_bets:
        print(f"\n【月次集計（Rule4）】")
        print(f"  {'年月':>7} {'件数':>6} {'的中':>5} {'的中率':>7} {'ROI':>8} {'純損益':>12}")
        print("  " + "-" * 55)
        ym_keys = sorted(set((r['year'], r['month']) for r in results))
        for y, m in ym_keys:
            ymbets = [b for r in results if r['year'] == y and r['month'] == m
                      for b in r['rule4_bets']]
            if not ymbets:
                continue
            h = sum(1 for b in ymbets if b['hit'])
            inv = len(ymbets) * BET_UNIT
            pay = sum(b['payout'] for b in ymbets)
            print(f"  {y}-{m} {len(ymbets):>6} {h:>5} {h/len(ymbets)*100:>6.1f}% "
                  f"{pay/inv*100:>7.1f}% {pay-inv:>+12,}円")

    # ── 競馬場別集計（Rule4）────────────────────────────────
    if all_bets:
        print(f"\n【競馬場別集計（Rule4）】")
        print(f"  {'競馬場':>6} {'件数':>6} {'的中':>5} {'的中率':>7} {'ROI':>8} {'純損益':>12}")
        print("  " + "-" * 55)
        venues = sorted(set(r['venue_name'] for r in results))
        venue_stats = []
        for v in venues:
            vbets = [b for r in results if r['venue_name'] == v
                     for b in r['rule4_bets']]
            if not vbets:
                continue
            h = sum(1 for b in vbets if b['hit'])
            inv = len(vbets) * BET_UNIT
            pay = sum(b['payout'] for b in vbets)
            venue_stats.append((v, len(vbets), h, pay/inv*100, pay-inv))
        # ROI降順で表示
        for v, cnt, h, roi_v, profit in sorted(venue_stats, key=lambda x: -x[3]):
            print(f"  {v:>6} {cnt:>6} {h:>5} {h/cnt*100:>6.1f}% "
                  f"{roi_v:>7.1f}% {profit:>+12,}円")

    print("\n" + "=" * 70)

    # ── CSV出力 ────────────────────────────────────────────
    # 出力ファイル名（年指定があれば年付き）
    if args.year and len(args.year) == 1:
        label = str(args.year[0])
    elif args.year:
        label = f"{min(args.year)}-{max(args.year)}"
    else:
        label = "all"

    # レース単位CSV
    race_csv_path = os.path.join(BASE_DIR, f'backtest_gui_{label}_races.csv')
    race_rows = []
    for r in results:
        r4 = r['rule4_bets']
        race_rows.append({
            'race_id':       r['race_id'],
            'date':          r['date'],
            'year':          r['year'],
            'month':         r['month'],
            'venue':         r['venue_name'],
            'honmei_umaban': r['honmei_umaban'],
            'honmei_proba':  round(r['honmei_proba'], 4),
            'honmei_hit':    int(r['honmei_hit']),
            'winner_odds':   r['winner_odds'],
            'tan_payout':    r['tan_payout'],
            'has_odds':      int(r['has_odds']),
            'rule4_count':   len(r4),
            'rule4_hits':    sum(1 for b in r4 if b['hit']),
            'rule4_invest':  len(r4) * BET_UNIT,
            'rule4_payout':  sum(b['payout'] for b in r4),
        })
    pd.DataFrame(race_rows).to_csv(race_csv_path, index=False, encoding='utf-8-sig')
    print(f"\n  レース単位CSV保存: {race_csv_path}")

    # Rule4ベット単位CSV
    bet_csv_path = os.path.join(BASE_DIR, f'backtest_gui_{label}_bets.csv')
    bet_rows = []
    for r in results:
        for b in r['rule4_bets']:
            bet_rows.append({
                'race_id':   r['race_id'],
                'date':      r['date'],
                'year':      r['year'],
                'month':     r['month'],
                'venue':     r['venue_name'],
                'umaban':    b['umaban'],
                'pred_win':  round(b['pred_win'], 4),
                'odds':      b['odds'],
                'cond_a':    int(b['cond_a']),
                'cond_b':    int(b['cond_b']),
                'hit':       int(b['hit']),
                'payout':    b['payout'],
            })
    if bet_rows:
        pd.DataFrame(bet_rows).to_csv(bet_csv_path, index=False, encoding='utf-8-sig')
        print(f"  Rule4ベットCSV保存: {bet_csv_path}")

    print(f"\n  ※ CSVをExcel等で開いて月次・場所別の詳細分析が可能です。")
    print("=" * 70)


if __name__ == '__main__':
    main()
