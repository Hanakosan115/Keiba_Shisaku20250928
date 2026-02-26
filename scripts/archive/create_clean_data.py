"""
2024年までのクリーンデータを作成
2025年の未来データを除外
"""
import pandas as pd
import json
from data_config import MAIN_CSV, MAIN_JSON

print("=" * 80)
print("クリーンデータ作成")
print("=" * 80)

# CSVデータのクリーニング
print("\n[1/2] CSVデータをクリーニング中...")
df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
print(f"  元データ: {len(df):,}行")

df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

# 2020-2024年のデータのみに絞る
df_clean = df[
    (df['date_parsed'] >= '2020-01-01') &
    (df['date_parsed'] <= '2024-12-31')
].copy()

print(f"  クリーン後: {len(df_clean):,}行")
print(f"  削除: {len(df) - len(df_clean):,}行 ({(len(df)-len(df_clean))/len(df)*100:.1f}%)")
print(f"  日付範囲: {df_clean['date_parsed'].min()} - {df_clean['date_parsed'].max()}")

# 不要なdate_parsedカラムを削除
df_clean = df_clean.drop(columns=['date_parsed'])

# 保存
clean_csv_path = r'C:\Users\bu158\Keiba_Shisaku20250928\netkeiba_data_2020_2024_clean.csv'
df_clean.to_csv(clean_csv_path, index=False, encoding='utf-8')
print(f"  保存: {clean_csv_path}")

# JSONデータのクリーニング
print("\n[2/2] JSONデータをクリーニング中...")
with open(MAIN_JSON, 'r', encoding='utf-8') as f:
    payout_list = json.load(f)

print(f"  元データ: {len(payout_list):,}レース")

# クリーンなrace_idのセットを取得
valid_race_ids = set(df_clean['race_id'].astype(str).unique())

# 有効なrace_idのみ保持
payout_list_clean = [p for p in payout_list if str(p.get('race_id')) in valid_race_ids]

print(f"  クリーン後: {len(payout_list_clean):,}レース")
print(f"  削除: {len(payout_list) - len(payout_list_clean):,}レース")

# 保存
clean_json_path = r'C:\Users\bu158\Keiba_Shisaku20250928\netkeiba_data_payouts_2020_2024_clean.json'
with open(clean_json_path, 'w', encoding='utf-8') as f:
    json.dump(payout_list_clean, f, indent=2, ensure_ascii=False)
print(f"  保存: {clean_json_path}")

# 統計サマリー
print("\n" + "=" * 80)
print("クリーンデータの統計")
print("=" * 80)
print(f"\n総出走数: {len(df_clean):,}頭")
print(f"レース数: {df_clean['race_id'].nunique():,}レース")
print(f"馬数: {df_clean['horse_id'].nunique():,}頭")
print(f"期間: {df_clean['date'].min()[:10]} ～ {df_clean['date'].max()[:10]}")

# 月別分布（2024年）
df_2024 = df_clean[df_clean['date'].str.startswith('2024', na=False)]
print(f"\n2024年データ:")
print(f"  出走数: {len(df_2024):,}頭")
print(f"  レース数: {df_2024['race_id'].nunique():,}レース")

# 保存したファイルパスを表示
print("\n" + "=" * 80)
print("次のステップ")
print("=" * 80)
print("\ndata_config.pyを更新してください:")
print(f'MAIN_CSV = r"{clean_csv_path}"')
print(f'MAIN_JSON = r"{clean_json_path}"')
