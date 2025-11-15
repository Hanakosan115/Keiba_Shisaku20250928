"""
人気順での的中率を確認（ベンチマーク）
AI予測と人気順を比較して、データセットの特性を確認
"""
import pandas as pd
import json
import sys
from itertools import combinations
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

# データ読み込み
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv", encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

# 6-8月のレースを抽出
df['race_id_str'] = df['race_id'].astype(str)
target_races = df[
    df['race_id_str'].str.startswith('202506') |
    df['race_id_str'].str.startswith('202507') |
    df['race_id_str'].str.startswith('202508')
]
race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

print("=" * 80)
print("人気順予測の的中率検証（ベンチマーク）")
print("=" * 80)
print(f"\n対象レース: {len(race_ids)}レース\n")

umaren_hits = 0
umaren_total = 0

for idx, race_id in enumerate(race_ids[:100]):  # 最初の100レースで検証
    if (idx + 1) % 20 == 0:
        print(f"処理中: {idx + 1}/100 レース")

    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 5:
        continue

    # 人気順でソート（1-3番人気を予測とする）
    race_horses['Ninki_num'] = pd.to_numeric(race_horses['Ninki'], errors='coerce')
    race_horses_sorted = race_horses.sort_values('Ninki_num')

    # 1-3番人気の馬番を取得
    top3_popular = race_horses_sorted.head(3)['Umaban'].tolist()

    if len(top3_popular) < 3:
        continue

    # 配当データ取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    if not payout_data or '馬連' not in payout_data:
        continue

    umaren_data = payout_data['馬連']
    winning_pairs = umaren_data.get('馬番', [])

    if not winning_pairs:
        continue

    try:
        winning_pair = set([int(x) for x in winning_pairs[:2]])

        # 1-3番人気の馬連BOXを生成
        umaren_pairs = list(combinations(top3_popular, 2))

        # 的中判定
        hit_found = False
        for pair in umaren_pairs:
            if set(pair) == winning_pair:
                hit_found = True
                break

        umaren_total += 1
        if hit_found:
            umaren_hits += 1

    except Exception as e:
        print(f"Error in race {race_id}: {e}")
        continue

print("\n" + "=" * 80)
print("【人気順予測の結果】")
print("=" * 80)
print(f"\n馬連BOX（1-3番人気）:")
print(f"  検証レース: {umaren_total}レース")
print(f"  的中: {umaren_hits}回")
print(f"  的中率: {umaren_hits/umaren_total*100:.1f}%")
print("\n")
print("=" * 80)
print("考察:")
print("=" * 80)
print("・人気順での的中率が高ければ、データセット自体が「人気通りの結果」が多い")
print("・AI予測が人気順とほぼ同じなら、AI予測の付加価値が低い可能性")
print("・逆に人気順の的中率が低ければ、AI予測の99.9%は疑わしい")
print("=" * 80)
