"""
race_idの実際のフォーマットを解析
"""
import pandas as pd

df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv", encoding='utf-8', low_memory=False)

print("=" * 80)
print("race_idフォーマット解析")
print("=" * 80)

# サンプルを抽出
sample = df.head(20)[['race_id', 'date', 'track_name', 'race_name']].drop_duplicates('race_id')

print("\n【サンプル20件】")
print("-" * 80)
for _, row in sample.iterrows():
    race_id = str(row['race_id'])
    actual_date = str(row['date'])[:10]
    print(f"race_id: {race_id:12} | date: {actual_date} | {row['track_name']} | {row['race_name']}")

# race_idの桁数分布
df['race_id_str'] = df['race_id'].astype(str)
df['race_id_len'] = df['race_id_str'].str.len()

print("\n" + "=" * 80)
print("race_idの桁数分布:")
print("=" * 80)
print(df.groupby('race_id_len')['race_id'].nunique())

# netkeibaのrace_idフォーマット推測
print("\n" + "=" * 80)
print("【重要】race_idの正しいフォーマット")
print("=" * 80)
print("""
netkeibaのrace_idは以下のフォーマットと推測されます:
- YYYY: 開催年
- PP: 競馬場コード(01=札幌, 02=函館, 03=福島, 04=新潟, 05=東京, 06=中山, 07=中京, 08=京都, 09=阪神, 10=小倉)
- KK: 開催回次(01=1回, 02=2回...)
- DD: 開催日目(01=1日目, 02=2日目...)
- RR: レース番号(01-12)

例: 202506010101
- 2025: 2025年
- 06: 中山競馬場
- 01: 1回開催
- 01: 1日目
- 01: 1レース

→ 実際の日付は別途date列で管理されている
→ race_idから日付を推定することは**不可能**
""")

print("=" * 80)
print("【結論】")
print("=" * 80)
print("バックテストでrace_idから日付を推定していたのが間違い。")
print("必ずdate列を使用する必要がある。")
print("=" * 80)
