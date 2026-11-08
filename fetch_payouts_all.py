"""
全レースの確定払戻を取得して payout_cache.pkl 形式で保存する (再開可能)。

  py fetch_payouts_all.py <netkeiba_data.csv> --out payout_cache_all.pkl [--sample 3000] [--years 2021 2022]

- 出力形式: {race_id: {'race_id':..., 'v':2, '単勝':[{'馬番':'7','払戻':360}], '馬連':[...], 'ワイド':[...], ...}}
  (pool_roi.py がそのまま読める)
- 取得済み(v=2)のレースは飛ばすので、止めても続きから再開できる。
  旧キャッシュ (--out に旧 payout_cache.pkl を指定) もワイド欠損レースは取り直す。
- 7秒前後の間隔 (--sleep、±15%ゆらぐ)。403/429/連続エラーが続いたら自動で停止する。
- 取得はnetkeibaへのアクセスになる。負荷と利用規約に配慮し、必要な分だけ実行すること。
"""
import argparse
import os
import pickle
import random
import re
import sys
import time

import requests
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
URL = "https://race.netkeiba.com/race/result.html?race_id={}"
TYPES = {
    "Tansho": "単勝", "Fukusho": "複勝", "Wakuren": "枠連", "Umaren": "馬連",
    "Wide": "ワイド", "Umatan": "馬単", "Fuku3": "3連複", "Tan3": "3連単",
}
TH_TYPES = {"単勝": "単勝", "複勝": "複勝", "枠連": "枠連", "馬連": "馬連",
            "ワイド": "ワイド", "馬単": "馬単", "3連複": "3連複", "3連単": "3連単",
            "三連複": "3連複", "三連単": "3連単"}


def parse_payouts(html, race_id=None):
    """結果ページHTML → {'単勝':[{'馬番','払戻'}], ...}。取れなければ None"""
    soup = BeautifulSoup(html, "lxml")
    out = {"race_id": race_id, "v": 2}
    for tr in soup.select(".Payout_Detail_Table tr"):
        kind = None
        for cls in tr.get("class", []):
            if cls in TYPES:
                kind = TYPES[cls]
        if kind is None:
            th = tr.find("th")
            kind = TH_TYPES.get(th.get_text(strip=True)) if th else None
        if kind is None:
            continue
        result_td = tr.find("td", class_="Result")
        pay_td = tr.find("td", class_="Payout")
        if result_td is None or pay_td is None:
            continue
        # 組合せ: <ul> ごとに1組 (複勝などは <div> ごと)
        groups = result_td.find_all("ul") or result_td.find_all("div")
        combos = []
        for g in groups:
            nums = [s.get_text(strip=True) for s in g.find_all("span")]
            nums = [n for n in nums if n.isdigit()]
            if nums:
                combos.append("-".join(nums))
        # 払戻: <br> 区切り
        for br in pay_td.find_all("br"):
            br.replace_with("\n")
        pays = []
        for line in pay_td.get_text().split("\n"):
            m = re.sub(r"[^\d]", "", line)
            if m:
                pays.append(int(m))
        if combos and len(combos) == len(pays):
            out.setdefault(kind, []).extend(
                {"馬番": c, "払戻": p} for c, p in zip(combos, pays)
            )
    return out if len(out) > 2 else None


def fetch(race_id, sleep, session):
    time.sleep(max(0.0, random.uniform(sleep * 0.85, sleep * 1.15)))  # 間隔は±15%ゆらす
    r = session.get(URL.format(race_id), headers={"User-Agent": UA}, timeout=30)
    if r.status_code in (403, 429):
        raise PermissionError(f"HTTP {r.status_code} (アクセス制限の可能性)")
    r.raise_for_status()
    r.encoding = r.apparent_encoding
    return parse_payouts(r.text, race_id)


def save(cache, path):
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        pickle.dump(cache, f)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("--out", default="payout_cache_all.pkl")
    ap.add_argument("--years", type=int, nargs="*")
    ap.add_argument("--sample", type=int, help="ランダムにNレースだけ取得 (seed固定)")
    ap.add_argument("--sleep", type=float, default=7.0, help="リクエスト間隔の中心(秒)。実際は±15%でゆらぐ")
    ap.add_argument("--max-errors", type=int, default=5, help="連続エラーでこの回数に達したら停止")
    a = ap.parse_args()

    from pool_calibration import read_results

    df = read_results(a.csv)
    df = df.dropna(subset=["Odds"])
    ids = sorted(int(x) for x in df["race_id"].unique())
    if a.years:
        ids = [i for i in ids if int(str(i)[:4]) in a.years]
    if a.sample and a.sample < len(ids):
        rnd = random.Random(42)
        ids = sorted(rnd.sample(ids, a.sample))

    cache = {}
    if os.path.exists(a.out):
        with open(a.out, "rb") as f:
            cache = {int(k): v for k, v in pickle.load(f).items()}
    todo = [i for i in ids if cache.get(i, {}).get("v") != 2]
    print(f"対象 {len(ids)} レース / 取得済み(v2) {len(ids) - len(todo)} / これから {len(todo)}"
          f" (約 {len(todo) * a.sleep / 3600:.1f} 時間)")

    session = requests.Session()
    errors = 0
    done = 0
    try:
        for n, rid in enumerate(todo, 1):
            try:
                rec = fetch(rid, a.sleep, session)
                errors = 0
            except PermissionError as e:
                print(f"停止: {e}")
                break
            except Exception as e:  # noqa: BLE001
                errors += 1
                print(f"  [エラー] {rid}: {e}")
                if errors >= a.max_errors:
                    print("連続エラーのため停止します")
                    break
                time.sleep(5 * errors)
                continue
            if rec:
                cache[rid] = rec
                done += 1
            else:
                print(f"  [払戻なし] {rid}")
            if n % 50 == 0:
                save(cache, a.out)
                print(f"[{n}/{len(todo)}] 保存 (累計 {len(cache)})")
    except KeyboardInterrupt:
        print("中断")
    save(cache, a.out)
    print(f"完了: 今回 {done} 件取得 / 累計 {len(cache)} 件 → {a.out}")


if __name__ == "__main__":
    sys.exit(main())
