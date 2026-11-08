"""
プール間の歪み検証 (ロジック1) の第一段階: 単勝オッズ → 理論確率 → 実績との校正

必要な列: race_id, Rank, Umaban, Odds(単勝確定オッズ, 小数)
使い方:  python pool_calibration.py <netkeiba_data.csv> [--min-horses 6]

出力:
  A. 単勝: オッズ帯別の実回収率 (人気薄バイアスの確認)
  B. 暗黙確率の補正 (比例正規化 vs べき乗法) の log-loss
  C. Harville を一般化した 2着/3着の補正指数 (gamma, lambda) の最尤推定
  D. 馬連・三連複: 理論確率 (Harville / 補正後) の帯別 予測 vs 実績

重要: 配当(馬連・ワイド等の組合せオッズ)が無いため、ここで測れるのは
「理論確率が実績と合っているか」まで。ROI の検証には組合せの確定オッズが必要。
"""
import argparse
import sys
from itertools import combinations, permutations

import numpy as np
import pandas as pd


def load(path, min_horses):
    df = pd.read_csv(path, encoding="utf-8-sig")
    df = df.rename(columns={df.columns[0]: df.columns[0].lstrip("﻿")})
    df["Rank"] = pd.to_numeric(df["Rank"], errors="coerce")
    df["Odds"] = pd.to_numeric(df["Odds"], errors="coerce")
    df = df.dropna(subset=["Odds"])
    df = df[df["Odds"] > 0]
    races = []
    for rid, g in df.groupby("race_id"):
        if len(g) < min_horses:
            continue
        g = g.reset_index(drop=True)
        # 着順が 1,2,3 で一意に決まるレースのみ (同着・全馬失格等は除外)
        top = {r: g.index[g["Rank"] == r].tolist() for r in (1, 2, 3)}
        if any(len(v) != 1 for v in top.values()):
            continue
        races.append(
            dict(
                race_id=rid,
                odds=g["Odds"].to_numpy(float),
                rank=g["Rank"].to_numpy(float),
                w=top[1][0],
                s=top[2][0],
                t=top[3][0],
            )
        )
    return races


def implied_proportional(odds):
    inv = 1.0 / odds
    return inv / inv.sum()


def implied_power(odds, iters=60):
    """(1/o)^k の合計が1になる k を二分法で求める (人気薄の過大評価を圧縮)"""
    inv = 1.0 / odds
    lo, hi = 0.5, 3.0
    for _ in range(iters):
        k = (lo + hi) / 2
        if (inv**k).sum() > 1:
            lo = k
        else:
            hi = k
    p = inv**k
    return p / p.sum()


def win_table(races):
    rows = []
    for r in races:
        for o, rk in zip(r["odds"], r["rank"]):
            rows.append((o, rk == 1))
    d = pd.DataFrame(rows, columns=["odds", "hit"])
    bins = [0, 2, 3, 5, 8, 12, 20, 40, 80, 1e9]
    d["bin"] = pd.cut(d["odds"], bins)
    d["ret"] = d["hit"] * d["odds"]
    t = d.groupby("bin", observed=True).agg(
        n=("hit", "size"), hit_rate=("hit", "mean"), roi=("ret", "mean")
    )
    t["roi"] = t["roi"].round(3)
    t["hit_rate"] = t["hit_rate"].round(4)
    total_roi = d["ret"].mean()
    return t, total_roi, len(d)


def winner_logloss(races, fn):
    ll = [np.log(fn(r["odds"])[r["w"]]) for r in races]
    return -float(np.mean(ll))


def fit_gamma(races, p_fn, stage):
    """stage=2: P(2着=s | 1着=w) ∝ p_s^g  /  stage=3: P(3着=t | w,s) ∝ p_t^g"""
    grid = np.arange(0.5, 1.5001, 0.05)
    best = None
    out = []
    for g in grid:
        ll = 0.0
        for r in races:
            p = p_fn(r["odds"]) ** g
            if stage == 2:
                mask = np.ones(len(p), bool)
                mask[r["w"]] = False
                ll += np.log(p[r["s"]] / p[mask].sum())
            else:
                mask = np.ones(len(p), bool)
                mask[[r["w"], r["s"]]] = False
                ll += np.log(p[r["t"]] / p[mask].sum())
        out.append((g, ll))
        if best is None or ll > best[1]:
            best = (g, ll)
    return best[0], out


def stage_probs(p, g2, g3):
    """1着は p、2着以降は p^g で再正規化 (g=1 なら Harville)"""
    q2, q3 = p**g2, p**g3
    return p, q2, q3


def pair_prob(p, q2, i, j):
    # 馬連: i→j と j→i
    a = p[i] * q2[j] / (q2.sum() - q2[i])
    b = p[j] * q2[i] / (q2.sum() - q2[j])
    return a + b


def trio_prob(p, q2, q3, trio):
    tot = 0.0
    for a, b, c in permutations(trio):
        pa = p[a]
        pb = q2[b] / (q2.sum() - q2[a])
        pc = q3[c] / (q3.sum() - q3[a] - q3[b])
        tot += pa * pb * pc
    return tot


def combo_calibration(races, p_fn, g2, g3, kind):
    rows = []
    for r in races:
        p = p_fn(r["odds"])
        q2, q3 = p**g2, p**g3
        n = len(p)
        if kind == "umaren":
            actual = frozenset((r["w"], r["s"]))
            for c in combinations(range(n), 2):
                rows.append((pair_prob(p, q2, *c), frozenset(c) == actual))
        else:
            actual = frozenset((r["w"], r["s"], r["t"]))
            for c in combinations(range(n), 3):
                rows.append((trio_prob(p, q2, q3, c), frozenset(c) == actual))
    d = pd.DataFrame(rows, columns=["pred", "hit"])
    qs = [0, 0.002, 0.005, 0.01, 0.02, 0.04, 0.08, 1.0]
    d["bin"] = pd.cut(d["pred"], qs)
    t = d.groupby("bin", observed=True).agg(
        n=("hit", "size"), pred=("pred", "mean"), obs=("hit", "mean"), hits=("hit", "sum")
    )
    t["obs/pred"] = (t["obs"] / t["pred"]).round(2)
    t["pred"] = t["pred"].round(4)
    t["obs"] = t["obs"].round(4)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--min-horses", type=int, default=6)
    a = ap.parse_args()

    races = load(a.csv, a.min_horses)
    print(f"対象レース数: {len(races)}")
    if len(races) < 30:
        sys.exit("レース数が少なすぎます")

    print("\n=== A. 単勝: オッズ帯別の実回収率 (ROI=1.0 で損益ゼロ) ===")
    t, roi, n = win_table(races)
    print(t.to_string())
    print(f"全買いROI: {roi:.3f}  (n={n}) / JRA単勝の理論値は控除率20%で約0.80")

    print("\n=== B. 勝ち馬の log-loss (小さいほど良い) ===")
    for name, fn in (("比例正規化", implied_proportional), ("べき乗法", implied_power)):
        print(f"{name}: {winner_logloss(races, fn):.4f}")

    p_fn = implied_power if winner_logloss(races, implied_power) < winner_logloss(
        races, implied_proportional
    ) else implied_proportional
    print(f"→ 以降は {p_fn.__name__} を使用")

    print("\n=== C. 2着/3着の補正指数 (1.0 = Harville) ===")
    g2, ll2 = fit_gamma(races, p_fn, 2)
    g3, ll3 = fit_gamma(races, p_fn, 3)
    ll2_h = dict(ll2)[min(dict(ll2), key=lambda x: abs(x - 1.0))]
    ll3_h = dict(ll3)[min(dict(ll3), key=lambda x: abs(x - 1.0))]
    print(f"gamma2={g2:.2f} (対数尤度改善 {max(v for _, v in ll2) - ll2_h:+.2f})")
    print(f"gamma3={g3:.2f} (対数尤度改善 {max(v for _, v in ll3) - ll3_h:+.2f})")
    print("gamma<1: 人気薄の2・3着を Harville は過小評価 / gamma>1: 過大評価")

    for kind, label in (("umaren", "馬連"), ("sanrenpuku", "三連複")):
        for tag, (x2, x3) in (("Harville(g=1)", (1.0, 1.0)), ("補正後", (g2, g3))):
            print(f"\n=== D. {label} 理論確率の校正: {tag} ===")
            print(combo_calibration(races, p_fn, x2, x3, kind).to_string())


if __name__ == "__main__":
    main()
