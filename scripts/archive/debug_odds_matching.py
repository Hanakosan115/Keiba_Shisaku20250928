"""
オッズデータのマッチング確認
"""

import pandas as pd

print("="*80)
print("オッズデータマッチングのデバッグ")
print("="*80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv',
                 encoding='utf-8', low_memory=False)

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 実オッズデータ読み込み
odds_df = pd.read_csv('odds_2024_sample_500.csv', encoding='utf-8')

print(f"\n元データ: {len(df):,}件")
print(f"オッズデータ: {len(odds_df):,}件")

# オッズデータのrace_id一覧
odds_race_ids = odds_df['race_id'].unique()
print(f"\nオッズあるレース数: {len(odds_race_ids)}レース")

# 最初の3レースを詳しく見る
print("\n" + "="*80)
print("サンプル分析（最初の3レース）")
print("="*80)

for i, race_id in enumerate(odds_race_ids[:3]):
    print(f"\n【レース{i+1}: {race_id}】")

    # 元データでこのレースを検索
    race_horses = df[df['race_id'] == race_id]
    print(f"  元データの馬数: {len(race_horses)}頭")

    if len(race_horses) > 0:
        print(f"  日付: {race_horses.iloc[0]['date']}")
        print(f"  Umaban例: {race_horses['Umaban'].head(5).tolist()}")
    else:
        print(f"  元データに該当レースなし")

    # オッズデータでこのレースの馬を検索
    race_odds = odds_df[odds_df['race_id'] == race_id]
    print(f"  オッズデータの馬数: {len(race_odds)}頭")
    print(f"  Umaban例: {race_odds['Umaban'].head(5).tolist()}")
    print(f"  オッズ例: {race_odds['odds_real'].head(5).tolist()}")

    # マッチングテスト
    if len(race_horses) > 0:
        matched_count = 0
        for _, horse in race_horses.iterrows():
            umaban = horse.get('Umaban')
            matched = odds_df[
                (odds_df['race_id'] == race_id) &
                (odds_df['Umaban'] == umaban)
            ]
            if len(matched) > 0:
                matched_count += 1

        print(f"  マッチング成功: {matched_count}頭/{len(race_horses)}頭")

# race_idとUmabanの型をチェック
print("\n" + "="*80)
print("データ型チェック")
print("="*80)

print(f"\n元データ:")
print(f"  race_id型: {df['race_id'].dtype}")
print(f"  Umaban型: {df['Umaban'].dtype}")
print(f"  race_idサンプル: {df['race_id'].head(3).tolist()}")
print(f"  Umabanサンプル: {df['Umaban'].head(3).tolist()}")

print(f"\nオッズデータ:")
print(f"  race_id型: {odds_df['race_id'].dtype}")
print(f"  Umaban型: {odds_df['Umaban'].dtype}")
print(f"  race_idサンプル: {odds_df['race_id'].head(3).tolist()}")
print(f"  Umabanサンプル: {odds_df['Umaban'].head(3).tolist()}")

# 2024年データの確認
df_2024 = df[df['date_parsed'] >= '2024-01-01']
print(f"\n元データの2024年レース数: {df_2024['race_id'].nunique()}レース")

# オッズあるレースが元データにあるか確認
odds_races_in_df = df[df['race_id'].isin(odds_race_ids)]
print(f"オッズあるレースが元データに存在: {odds_races_in_df['race_id'].nunique()}レース")

if len(odds_races_in_df) == 0:
    print("\n重大な問題: オッズデータのレースIDが元データに1つも見つかりません")
    print("\nrace_idの比較:")
    print(f"  元データの最初のrace_id: {df['race_id'].iloc[0]}")
    print(f"  オッズの最初のrace_id: {odds_df['race_id'].iloc[0]}")

print("\n" + "="*80)
print("完了")
print("="*80)
