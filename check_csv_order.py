"""
CSVのデータ順序を確認
"""
import pandas as pd

df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2020年1月の最初のレースを取得
jan_2020_races = df[
    (df['date_parsed'] >= '2020-01-01') &
    (df['date_parsed'] <= '2020-01-31')
]

race_ids = jan_2020_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

first_race_id = race_ids[0]
first_race_horses = df[df['race_id'] == first_race_id].copy()

print("=" * 80)
print("CSVのデータ順序を確認")
print("=" * 80)

print(f"\nレースID: {first_race_id}")
print(f"レース日付: {first_race_horses.iloc[0]['date']}")
print(f"レース名: {first_race_horses.iloc[0].get('race_name')}")

print(f"\n【CSVの元の順序】")
print("馬番 | 馬名 | 実際の着順 | 人気")
print("-" * 80)

for _, horse in first_race_horses.iterrows():
    umaban = int(horse.get('Umaban', 0))
    name = horse.get('HorseName', '')
    rank = horse.get('Rank')
    ninki = horse.get('Ninki')
    print(f"{umaban:>2}番 | {name:<20} | {rank:>2}着 | {ninki:>2}番人気")

print("\n" + "=" * 80)
print("【重要】CSVはどの順序で並んでいるか？")
print("=" * 80)

# 馬番順かチェック
umaban_list = first_race_horses['Umaban'].tolist()
is_umaban_order = umaban_list == sorted(umaban_list)

# 人気順かチェック
ninki_list = first_race_horses['Ninki'].tolist()
is_ninki_order = ninki_list == sorted(ninki_list, key=lambda x: float(x) if pd.notna(x) else 999)

# 着順かチェック
rank_list = first_race_horses['Rank'].tolist()
is_rank_order = rank_list == sorted(rank_list, key=lambda x: float(x) if pd.notna(x) else 999)

print(f"\n馬番順: {'YES' if is_umaban_order else 'NO'}")
print(f"人気順: {'YES' if is_ninki_order else 'NO'}")
print(f"着順: {'YES' if is_rank_order else 'NO'}")

# もう一つのレースも確認
if len(race_ids) > 1:
    second_race_id = race_ids[1]
    second_race_horses = df[df['race_id'] == second_race_id].copy()

    print(f"\n【2つ目のレース】レースID: {second_race_id}")

    umaban_list2 = second_race_horses['Umaban'].tolist()
    is_umaban_order2 = umaban_list2 == sorted(umaban_list2)

    ninki_list2 = second_race_horses['Ninki'].tolist()
    is_ninki_order2 = ninki_list2 == sorted(ninki_list2, key=lambda x: float(x) if pd.notna(x) else 999)

    rank_list2 = second_race_horses['Rank'].tolist()
    is_rank_order2 = rank_list2 == sorted(rank_list2, key=lambda x: float(x) if pd.notna(x) else 999)

    print(f"馬番順: {'YES' if is_umaban_order2 else 'NO'}")
    print(f"人気順: {'YES' if is_ninki_order2 else 'NO'}")
    print(f"着順: {'YES' if is_rank_order2 else 'NO'}")

print("\n" + "=" * 80)
print("【結論】")
print("=" * 80)

if is_rank_order:
    print("""
!!! 重大な発見 !!!

CSVのデータが **着順** で並んでいます！

つまり：
1. 2020年1月のレースは過去データなし
2. 全馬がデフォルトスコア30点になる
3. ソートしても同じスコアなので元の順序が保たれる
4. 元の順序 = 着順
5. TOP3を選ぶと = 1着, 2着, 3着の馬になる
6. 的中率100%になる！

これが71.6%的中率の原因です。
データが着順で並んでいるという、データリーケージの一種です。

正しいバックテストには、ランダムに並べ替えるか、
馬番順に並べ替える必要があります。
""")
elif is_ninki_order:
    print("""
CSVのデータが **人気順** で並んでいます。

過去データなし = 全馬同じスコア
→ 人気順の上位3頭が選ばれる
→ 人気順予測と同じ結果になる
""")
elif is_umaban_order:
    print("""
CSVのデータが **馬番順** で並んでいます。

過去データなし = 全馬同じスコア
→ 馬番の若い順に選ばれる
→ ランダムな予測と同じ結果になる（馬番は本来ランダム）
""")
else:
    print("データの順序が不明です。さらに調査が必要です。")

print("=" * 80)
