"""
プール間の歪み検証 (ロジック1) の第二段階: 理論確率の帯別 実回収率 (ROI)

単勝確定オッズから作った理論確率 (Harville / 補正後) で組合せを分類し、
「その帯の組合せを全部100円ずつ買ったら回収率はいくつか」を測る。
選抜が単勝オッズ由来の確率だけで決まるので、的中組合せの払戻しか無くても
ROI を偏りなく計算できる (組合せオッズが無い場合の部分検証)。

  ROI(帯) = Σ(的中組合せの払戻/100) / 帯に入った組合せ数
  ROI が 1.0 を超える帯が「理論確率より払戻が厚い=歪み」の候補。

入力
  CSV: race_id, Umaban, Rank, Odds (単勝確定オッズ)
  払戻: payout_cache.pkl 形式 {race_id: {'馬連':[{'馬番':'1-7','払戻':2330}], ...}}
        または同形式のレコード配列の .json

使い方
  python pool_roi.py data.csv payout_cache.pkl --train-until 2023
    --train-until 年: その年以前でgamma推定、翌年以降で評価 (ウォークフォワード)
"""
import argparse
import json
import pickle
import sys
from itertools import combinations, permutations

import numpy as np
import pandas as pd

from pool_calibration import fit_gamma, implied_power, implied_proportional

_IDX_CACHE = {}


def _combos(n, k):
    key = (n, k)
    if key not in _IDX_CACHE:
        _IDX_CACHE[key] = np.array(list(combinations(range(n), k)), dtype=int)
    return _IDX_CACHE[key]


def load_races(csv_path, min_horses=6):
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df = df.rename(columns={df.columns[0]: df.columns[0].lstrip("﻿")})
    for c in ("Rank", "Odds", "Umaban"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Odds", "Umaban"])
    df = df[df["Odds"] > 0]
    races = []
    for rid, g in df.groupby("race_id"):
        if len(g) < min_horses:
            continue
        g = g.reset_index(drop=True)
        top = {r: g.index[g["Rank"] == r].tolist() for r in (1, 2, 3)}
        if any(len(v) != 1 for v in top.values()):
            continue
        races.append(
            dict(
                race_id=int(rid),
                year=int(str(int(rid))[:4]),
                odds=g["Odds"].to_numpy(float),
                umaban=g["Umaban"].to_numpy(int),
                w=top[1][0], s=top[2][0], t=top[3][0],
            )
        )
    return races


def load_payouts(path):
    if path.endswith(".json"):
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        raw = {int(r["race_id"]): r for r in raw}
    else:
        with open(path, "rb") as f:
            raw = pickle.load(f)
        raw = {int(k): v for k, v in raw.items()}
    out = {}
    for rid, rec in raw.items():
        d = {}
        for kind in ("馬連", "ワイド", "3連複"):
            items = rec.get(kind) or []
            d[kind] = {
                tuple(sorted(int(x) for x in it["馬番"].split("-"))): float(it["払戻"])
                for it in items
            }
        out[rid] = d
    return out


def trio_probs(p, q2, q3):
    """全3頭組の確率 (3頭組, 確率)"""
    idx = _combos(len(p), 3)
    s2, s3 = q2.sum(), q3.sum()
    tot = np.zeros(len(idx))
    for a, b, c in permutations(range(3)):
        ia, ib, ic = idx[:, a], idx[:, b], idx[:, c]
        tot += p[ia] * q2[ib] / (s2 - q2[ia]) * q3[ic] / (s3 - q3[ia] - q3[ib])
    return idx, tot


def pair_probs_umaren(p, q2):
    idx = _combos(len(p), 2)
    s2 = q2.sum()
    i, j = idx[:, 0], idx[:, 1]
    return idx, p[i] * q2[j] / (s2 - q2[i]) + p[j] * q2[i] / (s2 - q2[j])


def pair_probs_wide(tri_idx, tri_p, n):
    """ワイド = 2頭がともに3着以内。3頭組確率から集計"""
    pair_idx = _combos(n, 2)
    lookup = {tuple(pr): k for k, pr in enumerate(pair_idx)}
    out = np.zeros(len(pair_idx))
    for (a, b, c), pr in zip(tri_idx, tri_p):
        for x, y in ((a, b), (a, c), (b, c)):
            out[lookup[(x, y)]] += pr
    return pair_idx, out


BINS = [0, 0.002, 0.005, 0.01, 0.02, 0.04, 0.08, 1.0]
KINDS = {"馬連": 2, "ワイド": 2, "3連複": 3}


def evaluate(races, payouts, p_fn, g2, g3):
    acc = {k: [] for k in KINDS}  # (pred, ret) 行
    for r in races:
        pay = payouts.get(r["race_id"])
        if pay is None:
            continue
        p = p_fn(r["odds"])
        q2, q3 = p**g2, p**g3
        n = len(p)
        tri_idx, tri_p = trio_probs(p, q2, q3)
        sets = {
            "馬連": pair_probs_umaren(p, q2),
            "3連複": (tri_idx, tri_p),
        }
        if pay["ワイド"]:  # 取得できていないレースはワイドのみ除外
            sets["ワイド"] = pair_probs_wide(tri_idx, tri_p, n)
        for kind, (idx, pr) in sets.items():
            if not pay[kind]:
                continue
            um = r["umaban"]
            ret = np.zeros(len(idx))
            table = pay[kind]
            for k, c in enumerate(idx):
                key = tuple(sorted(um[c]))
                v = table.get(key)
                if v:
                    ret[k] = v / 100.0
            acc[kind].append(np.column_stack([pr, ret]))
    res = {}
    for kind, arrs in acc.items():
        if not arrs:
            continue
        a = np.vstack(arrs)
        d = pd.DataFrame(a, columns=["pred", "ret"])
        d["bin"] = pd.cut(d["pred"], BINS)
        g = d.groupby("bin", observed=True)
        t = g.agg(n=("ret", "size"), hits=("ret", lambda x: int((x > 0).sum())),
                  pred=("pred", "mean"), roi=("ret", "mean"), sd=("ret", "std"))
        t["se"] = t["sd"] / np.sqrt(t["n"])
        t["roi_lo"] = (t["roi"] - 2 * t["se"]).round(3)
        t["roi_hi"] = (t["roi"] + 2 * t["se"]).round(3)
        t["pred"] = t["pred"].round(4)
        t["roi"] = t["roi"].round(3)
        res[kind] = (t.drop(columns=["sd", "se"]), d["ret"].mean(), len(d))
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("payouts")
    ap.add_argument("--train-until", type=int, default=None)
    ap.add_argument("--min-horses", type=int, default=6)
    a = ap.parse_args()

    races = load_races(a.csv, a.min_horses)
    payouts = load_payouts(a.payouts)
    races = [r for r in races if r["race_id"] in payouts]
    print(f"配当と突合できたレース: {len(races)}")
    if len(races) < 30:
        sys.exit("突合できたレースが少なすぎます (race_id の型・範囲を確認)")

    if a.train_until:
        train = [r for r in races if r["year"] <= a.train_until]
        test = [r for r in races if r["year"] > a.train_until]
        if len(train) < 30 or len(test) < 30:
            sys.exit("train/test のレース数が不足")
    else:
        train = test = races
        print("※ --train-until 未指定: 同一データで推定・評価 (楽観的になる)")
    print(f"学習 {len(train)} レース / 評価 {len(test)} レース")

    p_fn = implied_power
    g2, _ = fit_gamma(train, p_fn, 2)
    g3, _ = fit_gamma(train, p_fn, 3)
    print(f"gamma2={g2:.2f} gamma3={g3:.2f} (学習期間で推定)")

    for tag, (x2, x3) in (("Harville(g=1)", (1.0, 1.0)), ("補正後", (g2, g3))):
        res = evaluate(test, payouts, p_fn, x2, x3)
        for kind, (t, total, n) in res.items():
            print(f"\n=== {kind} / {tag} / 全組合せ買いROI={total:.3f} (n={n}) ===")
            print(t.to_string())
    print("\nROI 1.0 超かつ信頼区間(±2SE)の下限も 1.0 超なら歪みの候補。"
          "控除率22.5〜25%のため、通常は全帯 0.75〜0.78 付近になる。")


if __name__ == "__main__":
    main()
