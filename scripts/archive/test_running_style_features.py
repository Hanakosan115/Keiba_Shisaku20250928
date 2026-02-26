"""
脚質特徴量のテスト（少数レースで動作確認）
"""
import pandas as pd
import sys
import numpy as np
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv

def parse_passage(passage_str):
    """Passage文字列から序盤の位置を抽出"""
    if pd.isna(passage_str) or passage_str == '':
        return None

    try:
        parts = str(passage_str).split('-')
        if len(parts) >= 1:
            return int(parts[0])
    except:
        pass

    return None

def classify_running_style(early_position):
    """序盤位置から脚質を分類"""
    if early_position is None:
        return None

    if early_position <= 2:
        return 'escape'
    elif early_position <= 5:
        return 'leading'
    elif early_position <= 10:
        return 'closing'
    else:
        return 'pursuing'

def calculate_running_style_distribution(past_results):
    """過去成績から脚質分布を計算"""
    style_counts = {'escape': 0, 'leading': 0, 'closing': 0, 'pursuing': 0, 'unknown': 0}
    agari_times = []

    for race in past_results:
        if isinstance(race, dict):
            # Passage解析
            passage = race.get('passage')
            early_pos = parse_passage(passage)
            style = classify_running_style(early_pos)

            if style:
                style_counts[style] += 1
            else:
                style_counts['unknown'] += 1

            # 上がり3F
            agari = pd.to_numeric(race.get('agari'), errors='coerce')
            if pd.notna(agari) and agari > 0:
                agari_times.append(agari)

    total = sum(style_counts.values())

    if total == 0:
        return {
            'escape_rate': 0,
            'leading_rate': 0,
            'closing_rate': 0,
            'pursuing_rate': 0,
            'avg_agari': 0
        }

    return {
        'escape_rate': style_counts['escape'] / total,
        'leading_rate': style_counts['leading'] / total,
        'closing_rate': style_counts['closing'] / total,
        'pursuing_rate': style_counts['pursuing'] / total,
        'avg_agari': np.mean(agari_times) if agari_times else 0
    }

print("=" * 80)
print("脚質特徴量抽出テスト")
print("=" * 80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2023年のレースでテスト（過去成績が確実にある）
target_races = df[
    (df['date_parsed'] >= '2023-06-01') &
    (df['date_parsed'] <= '2023-06-30')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()[:10]

print(f"テスト対象: {len(race_ids)}レース")

for idx, race_id in enumerate(race_ids):
    print(f"\n{'='*60}")
    print(f"レース {idx+1}/{len(race_ids)}: {race_id}")
    print('='*60)

    race_horses = df[df['race_id'] == race_id].copy()
    race_date = race_horses.iloc[0]['date']
    race_date_str = str(race_date)[:10]

    print(f"日付: {race_date_str}")
    print(f"出走頭数: {len(race_horses)}頭\n")

    for _, horse in race_horses.head(3).iterrows():  # 最初の3頭のみ
        horse_id = horse.get('horse_id')
        horse_name = horse.get('HorseName', 'Unknown')
        umaban = horse.get('Umaban')

        print(f"  馬番{umaban}: {horse_name}")

        past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=10)

        if past_results and len(past_results) > 0:
            print(f"    過去成績数: {len(past_results)}レース")

            # 脚質分布を計算
            style_dist = calculate_running_style_distribution(past_results)

            print(f"    脚質分布:")
            print(f"      逃げ率: {style_dist['escape_rate']*100:.1f}%")
            print(f"      先行率: {style_dist['leading_rate']*100:.1f}%")
            print(f"      差し率: {style_dist['closing_rate']*100:.1f}%")
            print(f"      追込率: {style_dist['pursuing_rate']*100:.1f}%")
            print(f"      平均上がり3F: {style_dist['avg_agari']:.1f}秒")

            # サンプルデータ表示
            print(f"    過去3走のPassageデータ:")
            for i, race in enumerate(past_results[:3]):
                passage = race.get('passage', 'N/A')
                early_pos = parse_passage(passage)
                style = classify_running_style(early_pos) if early_pos else 'unknown'
                agari = race.get('agari', 'N/A')
                print(f"      {i+1}走前: Passage={passage}, 脚質={style}, 上がり={agari}")
        else:
            print(f"    過去成績なし")

print("\n" + "=" * 80)
print("テスト完了")
print("=" * 80)
