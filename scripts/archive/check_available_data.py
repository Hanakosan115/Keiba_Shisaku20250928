"""
利用可能なデータの詳細確認
- どんなカラムがあるか
- 展開予想に使えるデータは何か
- セクショナルタイム関連のデータ
"""
import pandas as pd
import numpy as np

print("=" * 80)
print("利用可能なデータの確認")
print("=" * 80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)

print(f"総レコード数: {len(df):,}件")
print(f"カラム数: {len(df.columns)}個")

print("\n【全カラム一覧】")
print("-" * 80)
for i, col in enumerate(df.columns, 1):
    print(f"{i:2d}. {col}")

print("\n【重要カラムのサンプルデータ】")
print("-" * 80)

# レースを1つ選んで詳細表示
sample_race = df[df['date'].notna()].head(50)
race_id = sample_race.iloc[0]['race_id']
race_data = df[df['race_id'] == race_id].head(5)

important_cols = ['race_id', 'Umaban', 'HorseName', 'Rank', 'Passage', 'Agari',
                  'Time', 'distance', 'track_name', 'course_type', 'track_condition',
                  'Odds_x', 'Ninki', 'Weight', 'WeightDiff', 'JockeyName']

print(f"\nレースID: {race_id}")
print(f"出走頭数: {len(df[df['race_id'] == race_id])}頭\n")

for col in important_cols:
    if col in race_data.columns:
        print(f"{col}:")
        print(f"  {race_data[col].values[:5]}")
        print()

print("\n【Passageデータの分析】")
print("-" * 80)

# Passageデータのパターン分析
passage_samples = df['Passage'].dropna().head(100)
print(f"Passageのサンプル20件:")
for i, passage in enumerate(passage_samples.head(20), 1):
    print(f"  {i:2d}. {passage}")

print("\n【Agariデータの分析】")
print("-" * 80)

agari_samples = df['Agari'].dropna()
print(f"Agari（上がり3F）の統計:")
print(f"  件数: {len(agari_samples):,}件")
print(f"  最小値: {agari_samples.min()}")
print(f"  最大値: {agari_samples.max()}")
print(f"  平均値: {agari_samples.mean():.2f}秒")
print(f"  中央値: {agari_samples.median():.2f}秒")

print("\n【Timeデータの分析】")
print("-" * 80)

time_samples = df['Time'].dropna().head(20)
print(f"Time（レースタイム）のサンプル20件:")
for i, time_val in enumerate(time_samples, 1):
    print(f"  {i:2d}. {time_val}")

print("\n【距離別のデータ分布】")
print("-" * 80)

distance_dist = df['distance'].value_counts().head(10)
print("出現頻度の高い距離TOP10:")
for dist, count in distance_dist.items():
    print(f"  {dist}m: {count:,}レース")

print("\n【競馬場別のデータ分布】")
print("-" * 80)

track_dist = df['track_name'].value_counts().head(10)
print("出現頻度の高い競馬場TOP10:")
for track, count in track_dist.items():
    print(f"  {track}: {count:,}件")

print("\n【コース種別の分布】")
print("-" * 80)

course_dist = df['course_type'].value_counts()
print("コース種別:")
for course, count in course_dist.items():
    print(f"  {course}: {count:,}件 ({count/len(df)*100:.1f}%)")

print("\n【馬場状態の分布】")
print("-" * 80)

condition_dist = df['track_condition'].value_counts()
print("馬場状態:")
for condition, count in condition_dist.items():
    print(f"  {condition}: {count:,}件 ({count/len(df)*100:.1f}%)")

print("\n" + "=" * 80)
print("データ確認完了")
print("=" * 80)

# 展開予想に使えるデータの評価
print("\n【展開予想実装の可否】")
print("-" * 80)
print("✅ Passage: 利用可能（序盤-終盤位置）")
print("✅ Agari: 利用可能（上がり3F）")
print("✅ distance: 利用可能")
print("✅ track_name: 利用可能（コース適性分析）")
print("✅ course_type: 利用可能（芝/ダート）")
print("✅ track_condition: 利用可能（馬場状態）")
print("⚠️ Time: 要確認（フォーマット次第）")
print("❌ セクショナルタイム: おそらく無し（Passage位置から推定必要）")

print("\n次のステップ:")
print("1. レース単位での展開予想機能を実装")
print("2. ペースシナリオ判定ロジックを作成")
print("3. 新特徴量を段階的に追加してバックテスト")
