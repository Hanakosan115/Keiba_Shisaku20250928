"""
自動データマージシステム
- 新規データを検出して自動的にマージ
- メインファイルを更新
- バックアップを作成
"""
import pandas as pd
import json
import os
import shutil
from datetime import datetime

print("=" * 80)
print("自動データマージシステム")
print("=" * 80)

# ファイルパス設定
DATA_DIR = r"C:\Users\bu158\HorseRacingAnalyzer\data"
BACKUP_DIR = os.path.join(DATA_DIR, "一旦避難用", "backups")
MAIN_DIR = os.path.join(DATA_DIR, "一旦避難用")

# メインファイル（これを常に最新に保つ）
MAIN_CSV = os.path.join(MAIN_DIR, "netkeiba_data_combined_latest.csv")
MAIN_JSON = os.path.join(MAIN_DIR, "netkeiba_data_payouts_latest.json")

# バックアップディレクトリ作成
os.makedirs(BACKUP_DIR, exist_ok=True)

def create_backup(file_path):
    """ファイルのバックアップを作成"""
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = os.path.basename(file_path).replace(".csv", f"_backup_{timestamp}.csv")
        backup_name = backup_name.replace(".json", f"_backup_{timestamp}.json")
        backup_path = os.path.join(BACKUP_DIR, backup_name)
        shutil.copy2(file_path, backup_path)
        print(f"  バックアップ作成: {os.path.basename(backup_path)}")
        return backup_path
    return None

def find_latest_data_file(pattern):
    """最新のデータファイルを検索"""
    import glob
    files = glob.glob(os.path.join(DATA_DIR, pattern))
    if files:
        # ファイル名から日付を抽出してソート
        files_sorted = sorted(files, reverse=True)
        return files_sorted[0] if files_sorted else None
    return None

def merge_csv_data():
    """CSVデータのマージ"""
    print("\n" + "=" * 80)
    print("【CSVデータのマージ】")
    print("=" * 80)

    # 現在のメインファイルを読み込む（存在する場合）
    df_main = pd.DataFrame()
    if os.path.exists(MAIN_CSV):
        print(f"\n現在のメインファイル読み込み中...")
        df_main = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
        print(f"  既存データ: {len(df_main):,}件")
        print(f"  既存レース: {df_main['race_id'].nunique():,}レース")

        # バックアップ作成
        create_backup(MAIN_CSV)
    else:
        # メインファイルが存在しない場合、既存の最新データから開始
        print(f"\nメインファイルが存在しないため、既存データから初期化します")
        old_csv = os.path.join(MAIN_DIR, "netkeiba_data_combined_202001_202508.csv")
        if os.path.exists(old_csv):
            print(f"  ベースファイル: {os.path.basename(old_csv)}")
            df_main = pd.read_csv(old_csv, encoding='utf-8', low_memory=False)
            print(f"  既存データ: {len(df_main):,}件")
            print(f"  既存レース: {df_main['race_id'].nunique():,}レース")
        else:
            print(f"  既存データなし、完全新規作成")

    # 最新の新規データを検索
    print(f"\n新規データファイルを検索中...")
    latest_csv = find_latest_data_file("netkeiba_data_combined_*.csv")

    if not latest_csv:
        print("  新規データが見つかりません")
        return False

    print(f"  検出: {os.path.basename(latest_csv)}")

    # 新規データ読み込み
    df_new = pd.read_csv(latest_csv, encoding='utf-8', low_memory=False)
    print(f"  新規データ: {len(df_new):,}件")

    # マージ処理
    if df_main.empty:
        df_merged = df_new.copy()
    else:
        # 結合
        df_merged = pd.concat([df_main, df_new], ignore_index=True)

        # 重複除去
        initial_count = len(df_merged)
        if 'race_id' in df_merged.columns and 'Umaban' in df_merged.columns:
            df_merged = df_merged.drop_duplicates(subset=['race_id', 'Umaban'], keep='last')
            duplicates_removed = initial_count - len(df_merged)
            print(f"  重複除去: {duplicates_removed:,}件")

    # 日付順にソート
    if 'date' in df_merged.columns:
        df_merged['date_parsed_temp'] = pd.to_datetime(df_merged['date'], errors='coerce')
        df_merged = df_merged.sort_values('date_parsed_temp')
        df_merged = df_merged.drop('date_parsed_temp', axis=1)

    print(f"\nマージ後: {len(df_merged):,}件")
    print(f"マージ後レース数: {df_merged['race_id'].nunique():,}レース")

    # 保存
    print(f"\n保存中: {os.path.basename(MAIN_CSV)}")
    df_merged.to_csv(MAIN_CSV, index=False, encoding='utf-8')
    print("  保存完了")

    return True

def merge_json_data():
    """配当データのマージ"""
    print("\n" + "=" * 80)
    print("【配当データのマージ】")
    print("=" * 80)

    # 現在のメインファイルを読み込む
    payouts_main = []
    if os.path.exists(MAIN_JSON):
        print(f"\n現在のメインファイル読み込み中...")
        with open(MAIN_JSON, 'r', encoding='utf-8') as f:
            payouts_main = json.load(f)
        print(f"  既存データ: {len(payouts_main):,}件")

        # バックアップ作成
        create_backup(MAIN_JSON)
    else:
        # メインファイルが存在しない場合、既存の最新データから開始
        print(f"\nメインファイルが存在しないため、既存データから初期化します")
        old_json = os.path.join(MAIN_DIR, "netkeiba_data_payouts_202001_202508.json")
        if os.path.exists(old_json):
            print(f"  ベースファイル: {os.path.basename(old_json)}")
            with open(old_json, 'r', encoding='utf-8') as f:
                payouts_main = json.load(f)
            print(f"  既存データ: {len(payouts_main):,}件")
        else:
            print(f"  既存データなし、完全新規作成")

    # 最新の新規データを検索
    print(f"\n新規データファイルを検索中...")
    latest_json = find_latest_data_file("netkeiba_data_payouts_*.json")

    if not latest_json:
        print("  新規データが見つかりません")
        return False

    print(f"  検出: {os.path.basename(latest_json)}")

    # 新規データ読み込み
    with open(latest_json, 'r', encoding='utf-8') as f:
        payouts_new = json.load(f)
    print(f"  新規データ: {len(payouts_new):,}件")

    # マージ処理（race_idをキーに重複除去）
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

    print(f"\nマージ後: {len(payouts_merged):,}件")

    # 保存
    print(f"\n保存中: {os.path.basename(MAIN_JSON)}")
    with open(MAIN_JSON, 'w', encoding='utf-8') as f:
        json.dump(payouts_merged, f, ensure_ascii=False, indent=2)
    print("  保存完了")

    return True

def update_config_file():
    """設定ファイルを作成（全スクリプトで共通利用）"""
    config_path = os.path.join(os.path.dirname(__file__), "data_config.py")

    config_content = f'''"""
データファイルパスの一元管理
全スクリプトでこのファイルをインポートして使用
"""

# メインデータファイル（常に最新）
MAIN_CSV = r"{MAIN_CSV}"
MAIN_JSON = r"{MAIN_JSON}"

# データディレクトリ
DATA_DIR = r"{DATA_DIR}"
BACKUP_DIR = r"{BACKUP_DIR}"
'''

    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(config_content)

    print(f"\n設定ファイル作成: {os.path.basename(config_path)}")

# メイン処理
try:
    # CSVマージ
    csv_updated = merge_csv_data()

    # JSONマージ
    json_updated = merge_json_data()

    # 設定ファイル更新
    update_config_file()

    print("\n" + "=" * 80)
    print("マージ完了")
    print("=" * 80)

    print("\n【次のステップ】")
    print("1. 訓練スクリプトを更新して data_config.py を使用するように変更")
    print("2. 新規データが追加されたら、このスクリプトを実行")
    print("3. バックアップは自動的に backups/ ディレクトリに保存されます")

    print(f"\n【メインファイル】")
    print(f"  CSV: {MAIN_CSV}")
    print(f"  JSON: {MAIN_JSON}")

except Exception as e:
    print(f"\nエラーが発生しました: {e}")
    import traceback
    traceback.print_exc()
