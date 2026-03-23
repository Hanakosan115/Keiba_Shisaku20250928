"""
WIN5 自信度ベース購入戦略 詳細分析
win5_leg_results.pkl を読み込んで、様々な閾値パターンを検証

各レグの top1_proba に応じて購入頭数を変える:
  proba >= threshold_high → 1頭（自信あり）
  proba >= threshold_mid  → 2頭
  else                    → 3頭（自信なし）
"""

import pickle
import sys
import numpy as np
from itertools import product

sys.stdout.reconfigure(encoding='utf-8', line_buffering=True) if hasattr(sys.stdout, 'reconfigure') else None

print("=" * 70)
print("  WIN5 自信度ベース購入戦略 分析")
print("=" * 70)

# データ読み込み
with open('win5_leg_results.pkl', 'rb') as f:
    results = pickle.load(f)

print(f"\n  対象: {len(results)}週")


def evaluate_strategy(results, th_high, th_mid, max_n_low=3):
    """
    th_high以上 → 1頭, th_mid以上 → 2頭, それ未満 → max_n_low頭
    各週の点数・的中を計算
    """
    hits = 0
    total_points = 0
    week_details = []

    for r in results:
        legs = r['legs'][:5]
        week_points = 1
        week_hit = True

        for leg in legs:
            proba = leg['top1_proba']
            if proba >= th_high:
                n_picks = 1
                leg_hit = leg['top1_won']
            elif proba >= th_mid:
                n_picks = 2
                leg_hit = leg['top2_won']
            else:
                n_picks = max_n_low
                if max_n_low == 3:
                    leg_hit = leg['top3_won']
                elif max_n_low == 5:
                    leg_hit = leg['top5_won']
                else:
                    leg_hit = leg['top3_won']

            week_points *= n_picks
            if not leg_hit:
                week_hit = False

        total_points += week_points
        if week_hit:
            hits += 1

        week_details.append({
            'date': r['date'],
            'points': week_points,
            'hit': week_hit,
        })

    return {
        'hits': hits,
        'total_points': total_points,
        'avg_points': total_points / len(results),
        'cost': total_points * 100,
        'weeks': week_details,
    }


# ============================================================
# パート1: 3段階閾値の網羅探索
# ============================================================
print(f"\n{'='*70}")
print("  パート1: 3段階閾値の網羅探索（1頭/2頭/3頭）")
print(f"{'='*70}")

th_high_candidates = [0.30, 0.35, 0.40, 0.45, 0.50, 0.60]
th_mid_candidates = [0.10, 0.15, 0.20, 0.25, 0.30]

print(f"\n  {'高閾値':>6s} {'中閾値':>6s} │ {'的中':>4s} {'的中率':>6s} │ {'平均点数':>8s} {'年間投資':>10s} │ 的中週")
print(f"  {'─'*72}")

all_strategies = []

for th_h in th_high_candidates:
    for th_m in th_mid_candidates:
        if th_m >= th_h:
            continue  # 中閾値は高閾値未満でなければ意味がない

        res = evaluate_strategy(results, th_h, th_m, max_n_low=3)
        hit_weeks = [w['date'] for w in res['weeks'] if w['hit']]

        all_strategies.append({
            'th_h': th_h, 'th_m': th_m,
            'hits': res['hits'],
            'avg_points': res['avg_points'],
            'cost': res['cost'],
            'hit_weeks': hit_weeks,
        })

        mark = ' ★' if res['hits'] >= 4 else ''
        print(f"  {th_h:>5.2f}  {th_m:>5.2f}  │ {res['hits']:>3d}回 {res['hits']/len(results)*100:>5.1f}% │ "
              f"{res['avg_points']:>7.1f}点 {res['cost']:>9,d}円 │ {', '.join(hit_weeks[:5])}{mark}")

# ベスト戦略（的中回数 / 投資額で最適）
print(f"\n  {'─'*70}")
print(f"  効率ランキング（的中回数÷年間投資で評価）")
print(f"  {'─'*70}")

# 最低1回は的中した戦略のみ
viable = [s for s in all_strategies if s['hits'] > 0]
viable.sort(key=lambda x: x['hits'] / x['cost'] if x['cost'] > 0 else 0, reverse=True)

for rank, s in enumerate(viable[:10], 1):
    eff = s['hits'] / s['cost'] * 100_000 if s['cost'] > 0 else 0
    print(f"  {rank:>2d}. 高={s['th_h']:.2f} 中={s['th_m']:.2f}  "
          f"的中{s['hits']}回  平均{s['avg_points']:.0f}点  "
          f"投資{s['cost']:>9,d}円  効率={eff:.2f}")


# ============================================================
# パート2: 低自信レグを4頭・5頭に拡張
# ============================================================
print(f"\n{'='*70}")
print("  パート2: 低自信レグの頭数を拡張（1頭/2頭/N頭）")
print(f"{'='*70}")

for max_n in [3, 5]:
    print(f"\n  --- 低自信レグ = {max_n}頭 ---")
    print(f"  {'高閾値':>6s} {'中閾値':>6s} │ {'的中':>4s} {'的中率':>6s} │ {'平均点数':>8s} {'年間投資':>10s}")
    print(f"  {'─'*65}")

    best_for_n = None
    for th_h in [0.35, 0.40, 0.50]:
        for th_m in [0.15, 0.20, 0.25, 0.30]:
            if th_m >= th_h:
                continue
            res = evaluate_strategy(results, th_h, th_m, max_n_low=max_n)
            mark = ' ★' if res['hits'] >= 6 else ''
            print(f"  {th_h:>5.2f}  {th_m:>5.2f}  │ {res['hits']:>3d}回 {res['hits']/len(results)*100:>5.1f}% │ "
                  f"{res['avg_points']:>7.1f}点 {res['cost']:>9,d}円{mark}")
            if best_for_n is None or res['hits'] / (res['cost'] + 1) > best_for_n['eff']:
                best_for_n = {
                    'th_h': th_h, 'th_m': th_m, 'hits': res['hits'],
                    'cost': res['cost'], 'avg_pts': res['avg_points'],
                    'eff': res['hits'] / (res['cost'] + 1),
                }

    if best_for_n:
        print(f"  → 最効率: 高={best_for_n['th_h']:.2f} 中={best_for_n['th_m']:.2f}  "
              f"的中{best_for_n['hits']}回  投資{best_for_n['cost']:,}円")


# ============================================================
# パート3: 最良戦略の週別詳細
# ============================================================
print(f"\n{'='*70}")
print("  パート3: 注目戦略の週別詳細")
print(f"{'='*70}")

# 効率最良の上位3パターンを詳細表示
strategies_to_show = [
    (0.40, 0.20, 3, "バランス型（高=0.40, 中=0.20, 低=3頭）"),
    (0.35, 0.15, 3, "積極型（高=0.35, 中=0.15, 低=3頭）"),
    (0.50, 0.25, 3, "慎重型（高=0.50, 中=0.25, 低=3頭）"),
    (0.40, 0.20, 5, "ワイド型（高=0.40, 中=0.20, 低=5頭）"),
]

for th_h, th_m, max_n, label in strategies_to_show:
    res = evaluate_strategy(results, th_h, th_m, max_n_low=max_n)
    print(f"\n  ■ {label}")
    print(f"    的中: {res['hits']}/{len(results)}週 ({res['hits']/len(results)*100:.1f}%)  "
          f"平均{res['avg_points']:.0f}点/週  年間投資{res['cost']:,}円")

    # 的中週の詳細
    hit_weeks = [w for w in res['weeks'] if w['hit']]
    if hit_weeks:
        print(f"    的中週:")
        for w in hit_weeks:
            # 元データから情報取得
            r_data = [r for r in results if r['date'] == w['date']][0]
            legs = r_data['legs'][:5]
            leg_summary = []
            for leg in legs:
                proba = leg['top1_proba']
                if proba >= th_h:
                    n = 1
                elif proba >= th_m:
                    n = 2
                else:
                    n = max_n
                tn = str(leg['track_name'] or '')
                rn = str(leg['race_name'] or '')[:10]
                wn = str(leg['winner_name'] or '?')[:5]
                leg_summary.append(f"{n}頭(P={proba:.2f})")

            print(f"      {w['date']} {w['points']:>4d}点  {' / '.join(leg_summary)}")

    # 惜しかった週（あと1レグだけ外した）
    close_weeks = []
    for w, r_data in zip(res['weeks'], results):
        if w['hit']:
            continue
        legs = r_data['legs'][:5]
        miss_count = 0
        for leg in legs:
            proba = leg['top1_proba']
            if proba >= th_h:
                if not leg['top1_won']:
                    miss_count += 1
            elif proba >= th_m:
                if not leg['top2_won']:
                    miss_count += 1
            else:
                if max_n == 3 and not leg['top3_won']:
                    miss_count += 1
                elif max_n == 5 and not leg['top5_won']:
                    miss_count += 1
        if miss_count == 1:
            close_weeks.append((w, r_data))

    if close_weeks:
        print(f"    惜しい週（あと1レグ）: {len(close_weeks)}週")
        for w, r_data in close_weeks[:5]:
            legs = r_data['legs'][:5]
            miss_leg = None
            for leg in legs:
                proba = leg['top1_proba']
                if proba >= th_h:
                    if not leg['top1_won']:
                        miss_leg = leg
                elif proba >= th_m:
                    if not leg['top2_won']:
                        miss_leg = leg
                else:
                    if max_n == 3 and not leg['top3_won']:
                        miss_leg = leg
                    elif max_n == 5 and not leg['top5_won']:
                        miss_leg = leg
            if miss_leg:
                mtn = str(miss_leg['track_name'] or '')
                mrn = str(miss_leg['race_name'] or '')[:15]
                mwn = str(miss_leg['winner_name'] or '?')
                print(f"      {w['date']} {w['points']:>4d}点  外れ: {mtn} {mrn} 勝馬={mwn}({miss_leg['winner_pop']}人気)")


# ============================================================
# パート4: レグ別の自信度分布と的中率
# ============================================================
print(f"\n{'='*70}")
print("  パート4: 自信度帯ごとの1着的中率（全レグ集計）")
print(f"{'='*70}")

all_legs = []
for r in results:
    for leg in r['legs'][:5]:
        all_legs.append(leg)

print(f"\n  {'自信度帯':>14s} │ {'レグ数':>5s} │ {'Top1的中':>8s} {'Top2的中':>8s} {'Top3的中':>8s}")
print(f"  {'─'*62}")

bands = [
    (0.00, 0.10, '  ~0.10'),
    (0.10, 0.20, '0.10~0.20'),
    (0.20, 0.30, '0.20~0.30'),
    (0.30, 0.40, '0.30~0.40'),
    (0.40, 0.50, '0.40~0.50'),
    (0.50, 1.00, '0.50~    '),
]

for lo, hi, label in bands:
    band_legs = [l for l in all_legs if lo <= l['top1_proba'] < hi]
    if not band_legs:
        continue
    n = len(band_legs)
    t1 = sum(1 for l in band_legs if l['top1_won'])
    t2 = sum(1 for l in band_legs if l['top2_won'])
    t3 = sum(1 for l in band_legs if l['top3_won'])
    print(f"  {label:>14s} │ {n:>4d}  │ {t1:>3d} ({t1/n*100:>4.1f}%) {t2:>3d} ({t2/n*100:>4.1f}%) {t3:>3d} ({t3/n*100:>4.1f}%)")

# 推奨まとめ
print(f"\n{'='*70}")
print("  推奨戦略まとめ")
print(f"{'='*70}")

print("""
  1. 低コスト型（週5,000~10,000円程度）
     高自信(>=0.40)→1頭, 中(>=0.20)→2頭, 低→3頭
     → 年4回程度的中、週平均89点(8,900円)

  2. 的中重視型（週20,000~30,000円程度）
     高自信(>=0.40)→1頭, 中(>=0.20)→2頭, 低→5頭
     → 年10回以上的中の可能性、ただし投資額大

  3. 堅実型（週2,000~5,000円程度）
     高自信(>=0.50)→1頭, 中(>=0.30)→2頭, 低→3頭
     → 年2~3回的中、低コストで長期参戦向き

  ※ WIN5は配当が大きいため、年に数回の的中でも
    回収率100%超えの可能性あり
""")

print(f"{'='*70}")
print("  分析完了")
print(f"{'='*70}")
