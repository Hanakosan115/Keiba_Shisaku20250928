"""
データ更新スクリプト
新しくスクレイピングしたデータを既存のクリーンデータとマージ
"""
import pandas as pd
import json
from datetime import datetime
import os
from data_config import MAIN_CSV, MAIN_JSON

print("=" * 80)
print("データ更新ツール")
print("=" * 80)

# ============================================================================
# 設定（新データの場所を指定）
# ============================================================================

NEW_CSV = input("\n新しいCSVファイルのパス: ").strip().strip('"')
NEW_JSON = input("新しいJSONファイルのパス: ").strip().strip('"')

if not os.path.exists(NEW_CSV):
    print(f"\nエラー: {NEW_CSV} が見つかりません")
    exit(1)

if not os.path.exists(NEW_JSON):
    print(f"\nエラー: {NEW_JSON} が見つかりません")
    exit(1)

# ============================================================================
# Step 1: CSVのマージ
# ============================================================================

print("\n" + "=" * 80)
print("Step 1: CSVデータのマージ")
print("=" * 80)

print(f"\n既存データ読み込み: {MAIN_CSV}")
df_existing = pd.read_csv(MAIN_CSV, low_memory=False)
print(f"  既存行数: {len(df_existing):,}")

print(f"\n新データ読み込み: {NEW_CSV}")
df_new = pd.read_csv(NEW_CSV, low_memory=False)
print(f"  新規行数: {len(df_new):,}")

# 日付をパース
df_existing['date_parsed'] = pd.to_datetime(df_existing['date'], errors='coerce')
df_new['date_parsed'] = pd.to_datetime(df_new['date'], errors='coerce')

# 新データの日付範囲を確認
print(f"\n新データの日付範囲:")
print(f"  最小: {df_new['date_parsed'].min()}")
print(f"  最大: {df_new['date_parsed'].max()}")

# 未来データチェック
today = datetime.now()
future_data = df_new[df_new['date_parsed'] > today]
if len(future_data) > 0:
    print(f"\n警告: 新データに未来データが{len(future_data):,}行あります！")
    print(f"  最新の未来日付: {future_data['date_parsed'].max()}")

    response = input("\n未来データを除外してマージしますか？ (y/n): ")
    if response.lower() != 'y':
        print("中止しました")
        exit(0)

    df_new = df_new[df_new['date_parsed'] <= today].copy()
    print(f"  未来データ除外後: {len(df_new):,}行")

# マージ
print("\nデータをマージ中...")
df_merged = pd.concat([df_existing, df_new], ignore_index=True)
print(f"  マージ後: {len(df_merged):,}行")

# 重複除去
print("\n重複を除去中...")
before_dup = len(df_merged)
df_merged = df_merged.drop_duplicates(subset=['race_id', 'horse_id'], keep='last')
duplicates_removed = before_dup - len(df_merged)
print(f"  除去した重複: {duplicates_removed:,}行")
print(f"  最終行数: {len(df_merged):,}行")

# date_parsedカラムを削除（一時的に使用しただけ）
df_merged = df_merged.drop(columns=['date_parsed'])

# ============================================================================
# Step 2: JSONのマージ
# ============================================================================

print("\n" + "=" * 80)
print("Step 2: JSONデータのマージ")
print("=" * 80)

print(f"\n既存データ読み込み: {MAIN_JSON}")
with open(MAIN_JSON, 'r', encoding='utf-8') as f:
    json_existing = json.load(f)
print(f"  既存レース数: {len(json_existing):,}")

print(f"\n新データ読み込み: {NEW_JSON}")
with open(NEW_JSON, 'r', encoding='utf-8') as f:
    json_new = json.load(f)
print(f"  新規レース数: {len(json_new):,}")

# マージ（新データで上書き）
print("\nJSONデータをマージ中...")
json_merged = {**json_existing, **json_new}
print(f"  マージ後レース数: {len(json_merged):,}")

# ============================================================================
# Step 3: バックアップと保存
# ============================================================================

print("\n" + "=" * 80)
print("Step 3: バックアップと保存")
print("=" * 80)

# バックアップ作成
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_csv = MAIN_CSV.replace('.csv', f'_backup_{timestamp}.csv')
backup_json = MAIN_JSON.replace('.json', f'_backup_{timestamp}.json')

print(f"\nバックアップ作成中...")
print(f"  CSV: {backup_csv}")
df_existing_backup = pd.read_csv(MAIN_CSV, low_memory=False)
df_existing_backup.to_csv(backup_csv, index=False, encoding='utf-8')

print(f"  JSON: {backup_json}")
with open(MAIN_JSON, 'r', encoding='utf-8') as f:
    json_backup = json.load(f)
with open(backup_json, 'w', encoding='utf-8') as f:
    json.dump(json_backup, f, ensure_ascii=False, indent=2)

print("✓ バックアップ完了")

# 新しいデータを保存
print(f"\n新しいデータを保存中...")
print(f"  CSV: {MAIN_CSV}")
df_merged.to_csv(MAIN_CSV, index=False, encoding='utf-8')

print(f"  JSON: {MAIN_JSON}")
with open(MAIN_JSON, 'w', encoding='utf-8') as f:
    json.dump(json_merged, f, ensure_ascii=False, indent=2)

print("✓ 保存完了")

# ============================================================================
# Step 4: サマリー
# ============================================================================

print("\n" + "=" * 80)
print("更新完了サマリー")
print("=" * 80)

# 最終データの統計
df_final = pd.read_csv(MAIN_CSV, low_memory=False)
df_final['date_parsed'] = pd.to_datetime(df_final['date'], errors='coerce')

print(f"\n最終データ統計:")
print(f"  総行数: {len(df_final):,}")
print(f"  ユニークレース数: {df_final['race_id'].nunique():,}")
print(f"  ユニーク馬数: {df_final['horse_id'].nunique():,}")
print(f"  日付範囲: {df_final['date_parsed'].min()} ～ {df_final['date_parsed'].max()}")

print(f"\n追加されたデータ:")
print(f"  新規行数: {len(df_final) - len(df_existing):,}")
print(f"  新規レース数: {len(json_merged) - len(json_existing):,}")

print(f"\nバックアップファイル:")
print(f"  {backup_csv}")
print(f"  {backup_json}")

print("\n" + "=" * 80)
print("次のステップ")
print("=" * 80)
print("""
1. GUIツールでデータ検証
   → keiba_analysis_tool.py を起動
   → データ管理タブで「データ統計を更新」

2. モデル再訓練
   → モデル訓練タブで再訓練を実行

3. バックテストで精度確認
   → バックテストタブで最新年をテスト

4. 次週のレースを予測
   → レース予測タブで予測実行
""")

print("=" * 80)
print("完了！")
print("=" * 80)
