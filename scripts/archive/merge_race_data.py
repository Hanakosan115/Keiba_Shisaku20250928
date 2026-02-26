"""
新規レースデータを既存のメインCSVにマージする
- 重複を除去
- 日付順にソート
- メインCSVを更新
"""
import pandas as pd
import json
import os
from datetime import datetime

print("=" * 80)
print("レースデータマージツール")
print("=" * 80)

# ファイルパス
MAIN_CSV = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_combined_202001_202508.csv"
NEW_CSV = r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202511.csv"
OUTPUT_CSV = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_combined_202001_202511_merged.csv"

MAIN_JSON = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_payouts_202001_202508.json"
NEW_JSON = r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202511.json"
OUTPUT_JSON = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_payouts_202001_202511_merged.json"

print("\n【CSVデータのマージ】")
print("-" * 80)

# メインCSV読み込み
print(f"\nメインCSV読み込み中: {os.path.basename(MAIN_CSV)}")
if os.path.exists(MAIN_CSV):
    df_main = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
    print(f"  件数: {len(df_main):,}件")
else:
    print("  メインCSVが見つかりません")
    df_main = pd.DataFrame()

# 新規CSV読み込み
print(f"\n新規CSV読み込み中: {os.path.basename(NEW_CSV)}")
if os.path.exists(NEW_CSV):
    df_new = pd.read_csv(NEW_CSV, encoding='utf-8', low_memory=False)
    print(f"  件数: {len(df_new):,}件")

    # 日付列を確認
    if 'date' in df_new.columns:
        df_new['date_parsed'] = pd.to_datetime(df_new['date'], errors='coerce')
        valid_dates = df_new['date_parsed'].notna().sum()
        print(f"  有効な日付: {valid_dates}件")

        if valid_dates > 0:
            print(f"  日付範囲: {df_new['date_parsed'].min()} ～ {df_new['date_parsed'].max()}")
        else:
            print("  警告: 有効な日付データがありません")
    else:
        print("  警告: date列が見つかりません")
else:
    print("  新規CSVが見つかりません")
    df_new = pd.DataFrame()

# マージ処理
if not df_main.empty or not df_new.empty:
    print("\nマージ処理中...")

    if df_main.empty:
        df_merged = df_new.copy()
    elif df_new.empty:
        df_merged = df_main.copy()
    else:
        # 結合
        df_merged = pd.concat([df_main, df_new], ignore_index=True)

    # 重複除去（race_id + Umaban の組み合わせ）
    initial_count = len(df_merged)
    if 'race_id' in df_merged.columns and 'Umaban' in df_merged.columns:
        df_merged = df_merged.drop_duplicates(subset=['race_id', 'Umaban'], keep='first')
        duplicates_removed = initial_count - len(df_merged)
        print(f"  重複除去: {duplicates_removed:,}件")

    # 日付順にソート
    if 'date' in df_merged.columns:
        df_merged['date_parsed'] = pd.to_datetime(df_merged['date'], errors='coerce')
        df_merged = df_merged.sort_values('date_parsed')
        df_merged = df_merged.drop('date_parsed', axis=1)

    print(f"\nマージ後の件数: {len(df_merged):,}件")

    # 保存
    print(f"\n保存中: {os.path.basename(OUTPUT_CSV)}")
    df_merged.to_csv(OUTPUT_CSV, index=False, encoding='utf-8')
    print("  保存完了")
else:
    print("\nマージするデータがありません")

print("\n" + "=" * 80)
print("【配当データのマージ】")
print("-" * 80)

# メインJSON読み込み
print(f"\nメインJSON読み込み中: {os.path.basename(MAIN_JSON)}")
payouts_main = []
if os.path.exists(MAIN_JSON):
    with open(MAIN_JSON, 'r', encoding='utf-8') as f:
        payouts_main = json.load(f)
    print(f"  件数: {len(payouts_main):,}件")
else:
    print("  メインJSONが見つかりません")

# 新規JSON読み込み
print(f"\n新規JSON読み込み中: {os.path.basename(NEW_JSON)}")
payouts_new = []
if os.path.exists(NEW_JSON):
    with open(NEW_JSON, 'r', encoding='utf-8') as f:
        payouts_new = json.load(f)
    print(f"  件数: {len(payouts_new):,}件")
else:
    print("  新規JSONが見つかりません")

# マージ処理
if payouts_main or payouts_new:
    print("\nマージ処理中...")

    # race_idをキーにした辞書を作成（重複除去）
    payout_dict = {}

    for payout in payouts_main:
        race_id = str(payout.get('race_id', ''))
        if race_id:
            payout_dict[race_id] = payout

    for payout in payouts_new:
        race_id = str(payout.get('race_id', ''))
        if race_id:
            payout_dict[race_id] = payout  # 新しいデータで上書き

    payouts_merged = list(payout_dict.values())

    print(f"\nマージ後の件数: {len(payouts_merged):,}件")

    # 保存
    print(f"\n保存中: {os.path.basename(OUTPUT_JSON)}")
    with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(payouts_merged, f, ensure_ascii=False, indent=2)
    print("  保存完了")
else:
    print("\nマージするデータがありません")

print("\n" + "=" * 80)
print("マージ完了")
print("=" * 80)

print("\n【次のステップ】")
print("1. マージ済みデータの確認")
print(f"   CSV: {OUTPUT_CSV}")
print(f"   JSON: {OUTPUT_JSON}")
print("\n2. モデル訓練スクリプトのパスを更新")
print("   マージ済みCSVを使用するように変更してください")
