# -*- coding: utf-8 -*-
"""
ペーパートレード記録ツール（v2 - 複勝並行・Kelly理論値・キャリブレーション対応）

使い方:
  py paper_trade_add.py

列定義:
  bet_type            : win / place / both
  pred_win            : GUIの単勝予測確率（生のまま）
  pred_place          : GUIの複勝予測確率
  pred_win_calibrated : キャリブレーション後の単勝確率（参考値・未確定時は空欄可）
  odds_recorded_time  : オッズ取得時刻（例: 発走5分前 / 09:50）
  kelly_theoretical   : フラクショナルKelly×0.25での理論ベット額（記録のみ、実際は100円固定）
"""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
from datetime import date

LOG_CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paper_trade_log.csv')
INITIAL_BANKROLL = 50_000
BET_UNIT = 100
KELLY_FRACTION = 0.25
KELLY_MAX = 500


def kelly_bet(p, odds, bankroll=INITIAL_BANKROLL, fraction=KELLY_FRACTION, max_bet=KELLY_MAX):
    """フラクショナルKelly計算（記録用・実際のベットには使わない）
    基準: バンクロール全体に対するKelly比率を算出"""
    b = odds - 1
    if b <= 0 or p <= 0:
        return 0
    f = (p * b - (1 - p)) / b  # Kelly比率
    if f <= 0:
        return 0
    raw = bankroll * f * fraction  # バンクロール基準で計算
    # 100円単位で丸め（記録専用参考値）
    return min(max_bet, max(100, round(raw / 100) * 100))


def load_log():
    df = pd.read_csv(LOG_CSV, encoding='utf-8-sig')
    if len(df) == 0:
        return df, INITIAL_BANKROLL
    df['bankroll'] = pd.to_numeric(df['bankroll'], errors='coerce')
    last_bankroll = df['bankroll'].dropna().iloc[-1] if not df['bankroll'].dropna().empty else INITIAL_BANKROLL
    return df, last_bankroll


def show_summary(df):
    if len(df) == 0:
        print("まだ記録がありません。")
        return
    confirmed = df[df['result'].isin(['的中', 'ハズレ'])]
    if len(confirmed) == 0:
        print("確定ベットがまだありません。")
        return
    n = len(confirmed)
    hits = (confirmed['result'] == '的中').sum()
    total_pl = confirmed['pl'].astype(float).sum()
    last_bank = df['bankroll'].iloc[-1]
    total_kelly = df['kelly_theoretical'].astype(float).sum() if 'kelly_theoretical' in df.columns else 0

    print(f"\n--- ペーパートレード集計 ---")
    print(f"  ベット数（確定）: {n}件  (未確定: {len(df)-n}件)")
    print(f"  的中数          : {hits}件 ({hits/n:.1%})")
    print(f"  純損益          : {total_pl:+,.0f}円")
    print(f"  現在残高        : {last_bank:,.0f}円")
    print(f"  回収率          : {(last_bank - INITIAL_BANKROLL + n*BET_UNIT)/(n*BET_UNIT)*100:.1f}%")
    print(f"  Kelly理論値合計 : {total_kelly:,.0f}円（参考）")

    # 馬券種別集計
    if 'bet_type' in df.columns:
        for bt in ['win', 'place', 'both']:
            sub = confirmed[confirmed['bet_type'] == bt]
            if len(sub) > 0:
                h = (sub['result'] == '的中').sum()
                print(f"  [{bt}] {len(sub)}件 的中{h}件 ({h/len(sub):.1%})")
    print()


def add_entry(df, bankroll):
    print("\n=== 新規ベット追加 ===")
    today = date.today().isoformat()
    d = input(f"  日付 [{today}]: ").strip() or today
    race_id   = input("  レースID (例: 202601020510): ").strip()
    race_name = input("  レース名 (例: 2月28日 中山1R): ").strip()
    horse     = input("  馬名: ").strip()
    horse_id  = input("  馬ID: ").strip()

    print("  馬券種別: 1=単勝(win) 2=複勝(place) 3=両方(both)")
    bt_num   = input("  選択 [1]: ").strip() or "1"
    bet_type = {'1': 'win', '2': 'place', '3': 'both'}.get(bt_num, 'win')

    pred_win  = float(input("  pred_win  (例: 0.23): ").strip())
    pred_pl   = float(input("  pred_place (例: 0.55): ").strip())
    pred_cal  = input("  pred_win_calibrated (未確定なら空Enter): ").strip()
    pred_win_cal = float(pred_cal) if pred_cal else ''

    odds      = float(input("  単勝オッズ (例: 12.3): ").strip())
    odds_time = input("  オッズ取得時刻 (例: 発走5分前 / 09:50): ").strip()

    print("  ベットルール: 1=Rule1 2=Rule2 3=Rule3 4=Rule4(推奨)")
    rule_num  = input("  選択 [4]: ").strip() or "4"
    rule_map  = {'1': 'Rule1_保守高頻度', '2': 'Rule2_中庸',
                 '3': 'Rule3_積極', '4': 'Rule4_複合最良'}
    bet_rule  = rule_map.get(rule_num, 'Rule4_複合最良')

    # Kelly理論値（記録のみ・バンクロール基準）
    k = kelly_bet(pred_win, odds, bankroll=bankroll)
    print(f"  Kelly理論値(×{KELLY_FRACTION}, 残高{bankroll:,.0f}円基準): {k}円  ※実際のベットは{BET_UNIT}円固定")
    bet_amount = BET_UNIT

    result_str = input("  結果 (1=的中 / 0=ハズレ / -=未確定) [-]: ").strip() or "-"
    if result_str == "1":
        result = "的中"
        payout = odds * bet_amount
        pl     = payout - bet_amount
    elif result_str == "0":
        result = "ハズレ"
        payout = 0.0
        pl     = -bet_amount
    else:
        result = "未確定"
        payout = 0.0
        pl     = 0.0

    bankroll += pl
    memo = input("  メモ: ").strip()

    new_row = {
        'date': d, 'race_id': race_id, 'race_name': race_name,
        'horse_name': horse, 'horse_id': horse_id,
        'bet_type': bet_type,
        'pred_win': pred_win, 'pred_place': pred_pl,
        'pred_win_calibrated': pred_win_cal,
        'odds': odds, 'odds_recorded_time': odds_time,
        'bet_rule': bet_rule, 'bet_amount': bet_amount,
        'kelly_theoretical': k,
        'result': result, 'payout': payout, 'pl': pl,
        'bankroll': bankroll, 'memo': memo,
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    df.to_csv(LOG_CSV, index=False, encoding='utf-8-sig')
    print(f"\n  → 記録しました。現在残高: {bankroll:,.0f}円")
    return df, bankroll


if __name__ == '__main__':
    df, bankroll = load_log()
    show_summary(df)

    while True:
        print("1: ベット追加  2: 集計表示  3: 終了")
        choice = input("選択: ").strip()
        if choice == '1':
            df, bankroll = add_entry(df, bankroll)
        elif choice == '2':
            df, _ = load_log()
            show_summary(df)
        elif choice == '3':
            break
        else:
            print("1, 2, 3 で選択してください")
