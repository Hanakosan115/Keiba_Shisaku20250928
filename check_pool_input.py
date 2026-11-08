"""pool_calibration.py / pool_roi.py に渡すCSVの診断。 使い方: python check_pool_input.py <csv>"""
import sys

import pandas as pd

df = pd.read_csv(sys.argv[1], encoding="utf-8-sig", low_memory=False)
df = df.rename(columns={df.columns[0]: df.columns[0].lstrip("﻿")})
print(f"行数 {len(df)} / 列数 {len(df.columns)}")
print("列名:", list(df.columns))

need = ["race_id", "Rank", "Umaban", "Odds"]
print("\n必須列:", {c: (c in df.columns) for c in need})
if not all(c in df.columns for c in need):
    sys.exit("必須列が足りません。列名の対応を教えてください")

print(f"\nrace_id: ユニーク {df['race_id'].nunique()} / 欠損 {df['race_id'].isna().sum()}")
print("race_id 先頭5:", df["race_id"].head().tolist())

for c in ("Rank", "Odds", "Umaban"):
    num = pd.to_numeric(df[c], errors="coerce")
    bad = df[c][num.isna() & df[c].notna()]
    print(f"\n[{c}] 数値化できた {num.notna().sum()} / 欠損 {df[c].isna().sum()} / 数値化できない値 {len(bad)}")
    print("  例:", bad.astype(str).value_counts().head(8).to_dict())

df["Rank_n"] = pd.to_numeric(df["Rank"], errors="coerce")
df["Odds_n"] = pd.to_numeric(df["Odds"], errors="coerce")
df["year"] = df["race_id"].astype(str).str[:4]
print("\n年別: 行数 / Oddsあり / Rank=1の数 / レース数")
print(
    df.groupby("year").agg(
        rows=("race_id", "size"),
        odds_ok=("Odds_n", lambda s: int(s.notna().sum())),
        wins=("Rank_n", lambda s: int((s == 1).sum())),
        races=("race_id", "nunique"),
    ).to_string()
)

g = df.groupby("race_id")
print("\nレースごとの Rank==1 の頭数 (1 が理想):")
print(g["Rank_n"].apply(lambda s: int((s == 1).sum())).value_counts().head(6).to_dict())
print("レースごとの Odds がある頭数 / 全頭数 の分布:")
frac = g["Odds_n"].apply(lambda s: s.notna().mean())
print(frac.describe().round(2).to_dict())
dup = df.duplicated(["race_id", "Umaban"]).sum()
print(f"\n(race_id, Umaban) の重複行: {dup}")
