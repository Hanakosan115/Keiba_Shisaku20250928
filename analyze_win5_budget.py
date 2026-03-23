"""
WIN5 予算別・自信度ベース購入戦略 分析

予算制約の中で、レグごとの自信度に応じて購入頭数を調整:
  - 高自信(P >= th_high) → 1頭
  - 中自信(P >= th_mid)  → 2頭
  - 低自信(P < th_mid)   → 3頭 or 4頭 or 5頭

予算: 5,000円(50点), 10,000円(100点), 20,000円(200点)
"""

import pickle
import sys
import numpy as np
from itertools import product

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

print("=" * 70)
print("  WIN5 予算別・自信度ベース購入戦略 分析")
print("=" * 70)

# データ読み込み
with open('win5_leg_results.pkl', 'rb') as f:
    results = pickle.load(f)

print(f"\n  対象: {len(results)}週")


def calculate_week_result(legs, th_high, th_mid, max_low):
    """
    1週分の購入点数と的中判定を計算

    Returns:
        points: 購入点数
        hit: 的中したか
        leg_picks: 各レグの購入頭数リスト
    """
    points = 1
    hit = True
    leg_picks = []

    for leg in legs:
        proba = leg['top1_proba']

        if proba >= th_high:
            n = 1
            leg_hit = leg['top1_won']
        elif proba >= th_mid:
            n = 2
            leg_hit = leg['top2_won']
        else:
            n = max_low
            if max_low == 3:
                leg_hit = leg['top3_won']
            elif max_low == 4:
                # top4_wonがないので、top3とtop5の間で近似
                leg_hit = leg['top3_won']  # 保守的に3頭で判定
            elif max_low == 5:
                leg_hit = leg['top5_won']
            else:
                leg_hit = leg['top3_won']

        points *= n
        leg_picks.append(n)
        if not leg_hit:
            hit = False

    return points, hit, leg_picks


def evaluate_budget_strategy(results, th_high, th_mid, max_low, budget_points):
    """
    予算制約下での戦略評価

    budget_points: 週あたりの最大点数
    """
    hits = 0
    total_points = 0
    valid_weeks = 0
    skipped_weeks = 0
    hit_details = []
    close_calls = []  # 惜しかった週

    for r in results:
        legs = r['legs'][:5]
        points, hit, leg_picks = calculate_week_result(legs, th_high, th_mid, max_low)

        if points <= budget_points:
            valid_weeks += 1
            total_points += points
            if hit:
                hits += 1
                hit_details.append({
                    'date': r['date'],
                    'points': points,
                    'legs': legs,
                    'picks': leg_picks,
                })
            else:
                # 惜しかったかチェック（4/5レグ的中）
                hit_count = 0
                for i, leg in enumerate(legs):
                    n = leg_picks[i]
                    if n == 1 and leg['top1_won']:
                        hit_count += 1
                    elif n == 2 and leg['top2_won']:
                        hit_count += 1
                    elif n >= 3 and leg['top3_won']:
                        hit_count += 1
                if hit_count == 4:
                    close_calls.append({
                        'date': r['date'],
                        'points': points,
                        'legs': legs,
                        'picks': leg_picks,
                    })
        else:
            skipped_weeks += 1

    return {
        'hits': hits,
        'valid_weeks': valid_weeks,
        'skipped_weeks': skipped_weeks,
        'total_points': total_points,
        'avg_points': total_points / valid_weeks if valid_weeks > 0 else 0,
        'hit_details': hit_details,
        'close_calls': close_calls,
    }


# ============================================================
# 予算別分析
# ============================================================

budgets = [
    (50, '5,000円'),
    (100, '10,000円'),
    (200, '20,000円'),
    (500, '50,000円'),
]

# 閾値パラメータの候補
th_high_list = [0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60]
th_mid_list = [0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
max_low_list = [3, 4, 5]

for budget_points, budget_label in budgets:
    print(f"\n{'='*70}")
    print(f"  予算: 週{budget_label}以内（{budget_points}点以内）")
    print(f"{'='*70}")

    all_results = []

    for th_h in th_high_list:
        for th_m in th_mid_list:
            if th_m >= th_h:
                continue
            for max_n in max_low_list:
                res = evaluate_budget_strategy(results, th_h, th_m, max_n, budget_points)

                if res['valid_weeks'] == 0:
                    continue

                all_results.append({
                    'th_h': th_h,
                    'th_m': th_m,
                    'max_n': max_n,
                    'hits': res['hits'],
                    'valid_weeks': res['valid_weeks'],
                    'skipped': res['skipped_weeks'],
                    'avg_points': res['avg_points'],
                    'total_cost': res['total_points'] * 100,
                    'hit_details': res['hit_details'],
                    'close_calls': res['close_calls'],
                })

    if not all_results:
        print("  この予算で有効な戦略がありません")
        continue

    # 的中回数でソート
    all_results.sort(key=lambda x: (-x['hits'], x['total_cost']))

    print(f"\n  {'高閾値':>6s} {'中閾値':>6s} {'低N':>3s} │ {'的中':>4s} {'参加':>4s} │ {'平均点':>6s} {'年間投資':>10s}")
    print(f"  {'─'*60}")

    shown = set()
    for r in all_results[:15]:
        key = (r['th_h'], r['th_m'], r['max_n'])
        if key in shown:
            continue
        shown.add(key)

        mark = ' ★' if r['hits'] >= 2 else ''
        print(f"  {r['th_h']:>5.2f}  {r['th_m']:>5.2f}  {r['max_n']:>2d}  │ {r['hits']:>3d}回 {r['valid_weeks']:>3d}週 │ "
              f"{r['avg_points']:>5.1f}点 {r['total_cost']:>9,d}円{mark}")

    # 最良戦略の詳細
    if all_results:
        best = all_results[0]
        print(f"\n  {'─'*60}")
        print(f"  ベスト戦略詳細: 高={best['th_h']:.2f} 中={best['th_m']:.2f} 低={best['max_n']}頭")
        print(f"  {'─'*60}")

        if best['hit_details']:
            print(f"\n  的中週:")
            for h in best['hit_details']:
                picks_str = ' x '.join([str(p) for p in h['picks']])
                print(f"    {h['date']}  {h['points']:>3d}点 ({picks_str})")
                for i, leg in enumerate(h['legs']):
                    tn = str(leg['track_name'] or '')
                    rn = str(leg['race_name'] or '')[:18]
                    wn = str(leg['winner_name'] or '?')[:6]
                    print(f"      Leg{i+1}: {tn:<4s} {rn:<18s} 勝馬:{wn}({leg['winner_pop']}人気) "
                          f"P={leg['top1_proba']:.2f} → {h['picks'][i]}頭")

        if best['close_calls']:
            print(f"\n  惜しかった週（4/5レグ的中）:")
            for c in best['close_calls'][:5]:
                picks_str = ' x '.join([str(p) for p in c['picks']])
                # 外したレグを特定
                miss_idx = -1
                for i, leg in enumerate(c['legs']):
                    n = c['picks'][i]
                    if n == 1 and not leg['top1_won']:
                        miss_idx = i
                    elif n == 2 and not leg['top2_won']:
                        miss_idx = i
                    elif n >= 3 and not leg['top3_won']:
                        miss_idx = i

                if miss_idx >= 0:
                    miss_leg = c['legs'][miss_idx]
                    mtn = str(miss_leg['track_name'] or '')
                    mrn = str(miss_leg['race_name'] or '')[:15]
                    mwn = str(miss_leg['winner_name'] or '?')
                    print(f"    {c['date']}  {c['points']:>3d}点 ({picks_str})")
                    print(f"      外れ: Leg{miss_idx+1} {mtn} {mrn} 勝馬={mwn}({miss_leg['winner_pop']}人気)")


# ============================================================
# 動的調整戦略（予算内で最大化）
# ============================================================
print(f"\n{'='*70}")
print("  動的調整戦略: 予算内で自信度に応じて頭数を最適化")
print(f"{'='*70}")

def dynamic_allocation(legs, budget_points):
    """
    予算内で的中確率を最大化する頭数配分を探索

    自信度の低いレグから頭数を増やしていく貪欲法
    """
    n_legs = 5

    # 各レグの自信度を取得
    probas = [leg['top1_proba'] for leg in legs]

    # まず全て1頭でスタート
    picks = [1] * n_legs

    # 自信度が低い順にソート（頭数を増やす優先順位）
    sorted_indices = sorted(range(n_legs), key=lambda i: probas[i])

    # 予算内で頭数を増やせるだけ増やす
    for idx in sorted_indices:
        current_points = np.prod(picks)

        # 2頭に増やせるか
        if current_points * 2 <= budget_points:
            picks[idx] = 2
            current_points = np.prod(picks)

        # 3頭に増やせるか
        if picks[idx] == 2 and current_points * 1.5 <= budget_points:
            picks[idx] = 3
            current_points = np.prod(picks)

        # 5頭に増やせるか（さらに余裕があれば）
        if picks[idx] == 3 and current_points * (5/3) <= budget_points:
            picks[idx] = 5

    return picks


def evaluate_dynamic_strategy(results, budget_points):
    """動的配分戦略の評価"""
    hits = 0
    total_points = 0
    hit_details = []
    close_calls = []

    for r in results:
        legs = r['legs'][:5]
        picks = dynamic_allocation(legs, budget_points)
        points = int(np.prod(picks))

        # 的中判定
        hit = True
        hit_count = 0
        for i, leg in enumerate(legs):
            n = picks[i]
            if n == 1:
                leg_hit = leg['top1_won']
            elif n == 2:
                leg_hit = leg['top2_won']
            elif n == 3:
                leg_hit = leg['top3_won']
            else:  # 5頭
                leg_hit = leg['top5_won']

            if leg_hit:
                hit_count += 1
            else:
                hit = False

        total_points += points

        if hit:
            hits += 1
            hit_details.append({
                'date': r['date'],
                'points': points,
                'picks': picks,
                'legs': legs,
            })
        elif hit_count == 4:
            close_calls.append({
                'date': r['date'],
                'points': points,
                'picks': picks,
                'legs': legs,
            })

    return {
        'hits': hits,
        'total_points': total_points,
        'avg_points': total_points / len(results),
        'hit_details': hit_details,
        'close_calls': close_calls,
    }


for budget_points, budget_label in budgets:
    print(f"\n  --- 予算: 週{budget_label}以内（{budget_points}点） ---")

    res = evaluate_dynamic_strategy(results, budget_points)

    print(f"  的中: {res['hits']}/{len(results)}週  "
          f"平均{res['avg_points']:.1f}点/週  "
          f"年間投資{res['total_points'] * 100:,}円")

    if res['hit_details']:
        print(f"  的中週:")
        for h in res['hit_details']:
            picks_str = 'x'.join([str(p) for p in h['picks']])
            probas = [f"{leg['top1_proba']:.2f}" for leg in h['legs']]
            print(f"    {h['date']}  {h['points']:>3d}点 [{picks_str}]  "
                  f"P=[{', '.join(probas)}]")

    if res['close_calls']:
        print(f"  惜しかった週（4/5）: {len(res['close_calls'])}週")
        for c in res['close_calls'][:3]:
            picks_str = 'x'.join([str(p) for p in c['picks']])
            print(f"    {c['date']}  {c['points']:>3d}点 [{picks_str}]")


# ============================================================
# 推奨まとめ
# ============================================================
print(f"\n{'='*70}")
print("  予算別・推奨戦略まとめ")
print(f"{'='*70}")

print("""
  ┌─────────────┬────────────────────────────────────────────┐
  │ 予算        │ 推奨設定                                   │
  ├─────────────┼────────────────────────────────────────────┤
  │ 週5,000円   │ 高>=0.50→1頭, 中>=0.20→2頭, 低→3頭       │
  │             │ 平均30~40点、堅実だが的中は稀              │
  ├─────────────┼────────────────────────────────────────────┤
  │ 週10,000円  │ 高>=0.45→1頭, 中>=0.20→2頭, 低→3頭       │
  │             │ 平均50~80点、バランス型                    │
  ├─────────────┼────────────────────────────────────────────┤
  │ 週20,000円  │ 高>=0.40→1頭, 中>=0.15→2頭, 低→5頭       │
  │             │ 平均100~150点、的中重視型                  │
  ├─────────────┼────────────────────────────────────────────┤
  │ 週50,000円  │ 動的配分（自信度低いレグに頭数集中）       │
  │             │ 平均300点前後、高配当狙い                  │
  └─────────────┴────────────────────────────────────────────┘

  ポイント:
  - P>=0.50以上のレグは1頭買いでも72%的中
  - P<0.20のレグは3頭でも49%しか的中しない（荒れやすい）
  - 予算が少ない場合は高自信レグを信じて点数を抑える
  - 予算がある場合は低自信レグの頭数を増やして保険をかける
""")

print(f"{'='*70}")
print("  分析完了")
print(f"{'='*70}")
