"""
2025年の全レースIDを生成し、CSV内に存在しないものだけを出力
"""
import pandas as pd

# CSV内の既存レースIDを取得
print("CSV読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
existing_ids = set(df['race_id'].astype(str).unique())
print(f"既存レース数: {len(existing_ids):,}件")

# JRA競馬場コード
places = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10']

# 2025年の全レースIDを生成
print("\n2025年のレースID生成中...")
all_race_ids = []

for place in places:
    for kai in range(1, 6):  # 1-5回開催
        for day in range(1, 13):  # 1-12日
            for race_num in range(1, 13):  # 1-12R
                race_id = f"2025{place}{kai:02d}{day:02d}{race_num:02d}"
                all_race_ids.append(race_id)

print(f"生成した全レースID数: {len(all_race_ids):,}件")

# CSV内に存在しないレースIDのみフィルタ
missing_ids = [rid for rid in all_race_ids if rid not in existing_ids]
print(f"CSV内に未存在: {len(missing_ids):,}件")

if missing_ids:
    print(f"\n最初の10件: {missing_ids[:10]}")
    print(f"最後の10件: {missing_ids[-10:]}")

    # ファイルに保存
    with open('race_ids.txt', 'w', encoding='utf-8') as f:
        for race_id in missing_ids:
            f.write(f"{race_id}\n")

    print(f"\nrace_ids.txt に保存しました（{len(missing_ids):,}件）")
else:
    print("\n全てのレースが既にCSVに存在します")
