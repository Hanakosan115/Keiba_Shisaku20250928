"""
利用可能な特徴量の分析
"""
import pandas as pd

df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv", encoding='utf-8', low_memory=False)

print("=" * 80)
print("CSVデータの列一覧")
print("=" * 80)

print("\n全列名:")
for i, col in enumerate(df.columns, 1):
    print(f"{i:2}. {col}")

print("\n" + "=" * 80)
print("サンプルデータ（最初の1レース）")
print("=" * 80)

# 最初のrace_idを取得
first_race_id = df['race_id'].iloc[0]
first_race = df[df['race_id'] == first_race_id].head(3)

print(f"\nレースID: {first_race_id}")
print(f"レコード数: {len(first_race)}")
print("\n各馬のデータ:")

for idx, (_, row) in enumerate(first_race.iterrows(), 1):
    print(f"\n--- 馬 #{idx} ---")
    for col in df.columns:
        value = row[col]
        if pd.notna(value):
            print(f"  {col}: {value}")

print("\n" + "=" * 80)
print("現在未使用で有用そうな特徴量")
print("=" * 80)

potentially_useful = [
    'Jockey',           # 騎手
    'Trainer',          # 調教師
    'Weight',           # 馬体重
    'WeightDiff',       # 馬体重変化
    'Sex',              # 性別
    'Age',              # 年齢
    'Handicap',         # 斤量
    'CornerPosition',   # コーナー順位
    'Last3F',           # 上がり3ハロン
    'Time',             # 走破タイム
    'Margin',           # 着差
    'HorseWeight',      # 馬体重（別名）
    'PrizeMoney',       # 賞金
    'track_condition',  # 馬場状態（使用中）
    'weather',          # 天候
    'course_type',      # コース種類（使用中）
]

print("\n検証:")
for feature in potentially_useful:
    if feature in df.columns:
        non_null_count = df[feature].notna().sum()
        total_count = len(df)
        availability = (non_null_count / total_count) * 100
        print(f"  {feature:20} | 利用可能率: {availability:5.1f}% | サンプル: {df[feature].dropna().iloc[0] if non_null_count > 0 else 'N/A'}")
    else:
        print(f"  {feature:20} | [列が存在しない]")

print("\n" + "=" * 80)
print("【重要】改善のための推奨事項")
print("=" * 80)
print("""
1. 騎手データの活用
   - 各騎手の勝率・連対率を計算
   - 騎手と競馬場の相性を分析

2. 調教師データの活用
   - 調教師の成績を特徴量として追加

3. 馬体重の活用
   - 適正体重との差
   - 体重の増減トレンド

4. 上がり3ハロンの活用
   - 末脚の速さを評価
   - コース形態との相性

5. オッズ情報の適切な活用（重要）
   - 事前予想オッズを別途取得
   - AIスコアとオッズの乖離度を計算
   - 過小評価されている馬を重視
""")
