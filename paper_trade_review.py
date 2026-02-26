# -*- coding: utf-8 -*-
"""
paper_trade_review.py — ペーパートレード月次レビュースクリプト

【実行方法】
  py paper_trade_review.py            # 全期間集計
  py paper_trade_review.py --month 202603  # 月次指定

【出力】
  1. 月次損益サマリー
  2. ルール別・馬券種別集計
  3. GO/NO-GO 判定（5基準）
  4. PSI（Population Stability Index）ドリフト判定
  5. Kelly理論値 vs 実固定ベット 比較
"""
import sys, os, argparse
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pandas as pd
import numpy as np
from datetime import date

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
LOG_CSV    = os.path.join(BASE_DIR, 'paper_trade_log.csv')
PRED_A_CSV = os.path.join(BASE_DIR, 'phase_a_predictions.csv')

INITIAL_BANKROLL = 50_000
BET_UNIT         = 100

# ── GO/NO-GO 基準 ──────────────────────────────────
GO_MIN_WEEKS     = 8      # 最低8週間（2ヶ月）
GO_MIN_BETS      = 200    # 最低200件
GO_MIN_ROI       = 1.00   # 実績回収率 100% 以上
GO_MAX_DD        = 0.15   # 最大ドローダウン 15% 以内
GO_CI_ALPHA      = 0.05   # 信頼区間 95%

# PSI 閾値
PSI_WARN         = 0.10   # 注意
PSI_ALERT        = 0.20   # ドリフト疑い

SEP = '─' * 55


def load_log(month: str = None) -> pd.DataFrame:
    df = pd.read_csv(LOG_CSV, encoding='utf-8-sig')
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['pl']   = pd.to_numeric(df['pl'],   errors='coerce').fillna(0)
    df['payout'] = pd.to_numeric(df['payout'], errors='coerce').fillna(0)
    df['bet_amount'] = pd.to_numeric(df['bet_amount'], errors='coerce').fillna(BET_UNIT)
    df['kelly_theoretical'] = pd.to_numeric(df['kelly_theoretical'], errors='coerce').fillna(0)
    df['pred_win'] = pd.to_numeric(df['pred_win'], errors='coerce')
    df['odds']     = pd.to_numeric(df['odds'], errors='coerce')
    if month:
        df = df[df['date'].dt.strftime('%Y%m') == month]
    return df


def print_monthly_summary(df: pd.DataFrame):
    confirmed = df[df['result'].isin(['的中', 'ハズレ'])]
    if len(confirmed) == 0:
        print('  確定ベットなし')
        return

    print(f'\n{SEP}')
    print(' 月次損益サマリー')
    print(SEP)

    monthly = confirmed.copy()
    monthly['month'] = monthly['date'].dt.to_period('M')
    for m, g in monthly.groupby('month'):
        n     = len(g)
        hits  = (g['result'] == '的中').sum()
        pl    = g['pl'].sum()
        bank  = g['bankroll'].iloc[-1] if 'bankroll' in g.columns else 0
        roi   = (g['payout'].sum() / (n * BET_UNIT) * 100) if n > 0 else 0
        print(f'  {m}  {n:>4}件  的中{hits:>3}件({hits/n:.0%})  '
              f'損益{pl:>+7,.0f}円  回収{roi:>5.1f}%  残高{bank:>8,.0f}円')


def print_rule_breakdown(df: pd.DataFrame):
    confirmed = df[df['result'].isin(['的中', 'ハズレ'])]
    if len(confirmed) == 0:
        return

    print(f'\n{SEP}')
    print(' ルール別・馬券種別集計')
    print(SEP)

    for col, label in [('bet_rule', 'ルール'), ('bet_type', '馬券種別')]:
        if col not in confirmed.columns:
            continue
        print(f'\n  [{label}]')
        for val, g in confirmed.groupby(col):
            n    = len(g)
            hits = (g['result'] == '的中').sum()
            pl   = g['pl'].sum()
            roi  = g['payout'].sum() / (n * BET_UNIT) * 100
            print(f'    {str(val):<22} {n:>4}件  {hits/n:>5.1%}  '
                  f'ROI{roi:>6.1f}%  損益{pl:>+8,.0f}円')


def go_nogo_check(df: pd.DataFrame):
    confirmed = df[df['result'].isin(['的中', 'ハズレ'])]

    print(f'\n{SEP}')
    print(' GO/NO-GO 判定（ライブトレード移行基準）')
    print(SEP)

    results = {}

    # 基準1: 期間
    if len(confirmed) > 0 and confirmed['date'].notna().any():
        days  = (confirmed['date'].max() - confirmed['date'].min()).days
        weeks = days / 7
    else:
        weeks = 0
    ok1 = weeks >= GO_MIN_WEEKS
    results['基準1 期間'] = (ok1, f'{weeks:.1f}週間 (必要: {GO_MIN_WEEKS}週間以上)')

    # 基準2: サンプル数
    n = len(confirmed)
    ok2 = n >= GO_MIN_BETS
    results['基準2 件数'] = (ok2, f'{n}件 (必要: {GO_MIN_BETS}件以上)')

    # 基準3: 回収率
    if n > 0:
        roi = confirmed['payout'].sum() / (n * BET_UNIT)
    else:
        roi = 0
    ok3 = roi >= GO_MIN_ROI
    results['基準3 回収率'] = (ok3, f'{roi:.1%} (必要: {GO_MIN_ROI:.0%}以上)')

    # 基準4: 最大ドローダウン
    if 'bankroll' in confirmed.columns and len(confirmed) > 0:
        bank = confirmed['bankroll'].values
        peak = np.maximum.accumulate(np.where(np.isnan(bank), INITIAL_BANKROLL, bank))
        dd   = np.max((peak - bank) / peak)
    else:
        dd = 0
    ok4 = dd <= GO_MAX_DD
    results['基準4 最大DD'] = (ok4, f'{dd:.1%} (上限: {GO_MAX_DD:.0%})')

    # 基準5: 統計的有意性（Clopper-Pearson 95%CI下限 > 損益分岐勝率）
    if n > 0 and confirmed['odds'].notna().any():
        hits     = int((confirmed['result'] == '的中').sum())
        avg_odds = confirmed['odds'].mean()
        breakeven = 1.0 / avg_odds

        # Clopper-Pearson 95% CI 下限（正規近似）
        p_hat = hits / n
        se    = np.sqrt(p_hat * (1 - p_hat) / n)
        ci_low = max(0, p_hat - 1.96 * se)

        ok5 = ci_low > breakeven
        results['基準5 統計的有意性'] = (
            ok5,
            f'CI下限{ci_low:.1%} vs 損益分岐{breakeven:.1%} '
            f'(平均オッズ{avg_odds:.1f}x, 的中{hits}/{n}件)'
        )
    else:
        ok5 = False
        results['基準5 統計的有意性'] = (False, 'データ不足')

    all_ok = all(v[0] for v in results.values())
    for label, (ok, detail) in results.items():
        mark = '✅' if ok else '❌'
        print(f'  {mark} {label:<22} {detail}')

    print()
    if all_ok:
        print('  ★ 全基準クリア → ライブトレード移行を検討してください')
    else:
        ng = [k for k, (ok, _) in results.items() if not ok]
        print(f'  → NO-GO  未達成: {", ".join(ng)}')


def psi_check(df: pd.DataFrame):
    """
    PSI: バックテスト時のpred_win分布 vs 現在のpred_win分布を比較
    """
    print(f'\n{SEP}')
    print(' PSI（Population Stability Index）ドリフト判定')
    print(SEP)

    if not os.path.exists(PRED_A_CSV):
        print('  phase_a_predictions.csv が見つかりません。スキップ。')
        return

    current = df['pred_win'].dropna()
    if len(current) < 30:
        print(f'  サンプル不足（{len(current)}件）。30件以上で実施可能。')
        return

    baseline = pd.read_csv(PRED_A_CSV, encoding='utf-8-sig')['pred_win'].dropna()

    bins = np.linspace(0, 1, 11)  # 0〜100%を10等分
    e_cnt, _ = np.histogram(baseline, bins=bins)
    a_cnt, _ = np.histogram(current,  bins=bins)

    e_pct = e_cnt / e_cnt.sum()
    a_pct = a_cnt / a_cnt.sum()
    e_pct = np.where(e_pct == 0, 1e-6, e_pct)
    a_pct = np.where(a_pct == 0, 1e-6, a_pct)

    psi = float(np.sum((a_pct - e_pct) * np.log(a_pct / e_pct)))

    print(f'  PSI = {psi:.4f}')
    print(f'  判定: ', end='')
    if psi < PSI_WARN:
        print(f'✅ 正常（分布変化なし）')
    elif psi < PSI_ALERT:
        print(f'⚠️  注意（小さな変化あり）')
    else:
        print(f'🚨 要注意（ドリフトの疑い → モデル再訓練を検討）')

    print(f'\n  確率帯別分布比較（バックテスト vs ペーパートレード）:')
    print(f'  {"帯":<12} {"baseline":>10} {"current":>10} {"差分":>8}')
    print(f'  {"-"*44}')
    labels = [f'{int(bins[i]*100)}-{int(bins[i+1]*100)}%' for i in range(len(bins)-1)]
    for label, e, a in zip(labels, e_pct, a_pct):
        diff = a - e
        bar  = '▲' if diff > 0.02 else ('▼' if diff < -0.02 else ' ')
        print(f'  {label:<12} {e:>9.1%} {a:>10.1%} {diff:>+7.1%} {bar}')


def kelly_comparison(df: pd.DataFrame):
    confirmed = df[df['result'].isin(['的中', 'ハズレ'])]
    if len(confirmed) == 0 or 'kelly_theoretical' not in confirmed.columns:
        return

    print(f'\n{SEP}')
    print(' Kelly理論値 vs 固定100円 比較（シミュレーション）')
    print(SEP)

    n          = len(confirmed)
    fixed_pl   = confirmed['pl'].sum()
    fixed_roi  = confirmed['payout'].sum() / (n * BET_UNIT) * 100

    # Kelly仮想損益: 的中なら kelly × odds、ハズレなら -kelly
    kelly_col = confirmed['kelly_theoretical'].fillna(0)
    kelly_pl_sim = (
        confirmed.apply(
            lambda r: r['kelly_theoretical'] * (r['odds'] - 1)
                      if r['result'] == '的中'
                      else -r['kelly_theoretical'],
            axis=1
        )
    )
    kelly_total_bet = kelly_col.sum()
    kelly_total_pl  = kelly_pl_sim.sum()
    kelly_roi = (kelly_total_pl + kelly_total_bet) / kelly_total_bet * 100 if kelly_total_bet > 0 else 0

    print(f'  ベット件数: {n}件')
    print(f'\n  固定100円ベット:')
    print(f'    総ベット額: {n * BET_UNIT:>8,.0f}円')
    print(f'    純損益:     {fixed_pl:>+8,.0f}円')
    print(f'    回収率:     {fixed_roi:>8.1f}%')
    print(f'\n  Kelly理論値ベット（仮想・参考）:')
    print(f'    総ベット額: {kelly_total_bet:>8,.0f}円')
    print(f'    純損益:     {kelly_total_pl:>+8,.0f}円')
    print(f'    回収率:     {kelly_roi:>8.1f}%')
    note = 'Kelly有利' if kelly_total_pl > fixed_pl else '固定有利'
    print(f'\n  → 今のところ【{note}】（最低200件で判断してください）')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--month', default=None,
                        help='対象月 YYYYMM（例: 202603）。省略で全期間')
    args = parser.parse_args()

    if not os.path.exists(LOG_CSV):
        print('paper_trade_log.csv が見つかりません。')
        return

    df = load_log(args.month)
    label = f'{args.month}月' if args.month else '全期間'

    print(f'\n{"="*55}')
    print(f' ペーパートレード月次レビュー  [{label}]')
    print(f'{"="*55}')
    print(f'  読込件数: {len(df)}件  '
          f'確定: {len(df[df["result"].isin(["的中","ハズレ"])])}件  '
          f'未確定: {len(df[df["result"]=="未確定"])}件')

    print_monthly_summary(df)
    print_rule_breakdown(df)
    go_nogo_check(df)
    psi_check(df)
    kelly_comparison(df)

    print(f'\n{"="*55}')
    print(f' レビュー完了')
    print(f'{"="*55}\n')


if __name__ == '__main__':
    main()
