"""
全スクリプトを一括更新してdata_config.pyを使用するように変更
"""
import os
import re

# 更新対象スクリプト
scripts = [
    "train_with_best_params.py",
    "train_with_running_style_optimized.py",
    "train_advanced_model.py",
    "backtest_tuned_model.py",
    "backtest_running_style_optimized.py",
    "backtest_advanced_model_optimized.py",
]

# 古いパス
OLD_CSV_PATTERN = r'r"C:\\Users\\bu158\\HorseRacingAnalyzer\\data\\一旦避難用\\netkeiba_data_combined_202001_202508\.csv"'
OLD_JSON_PATTERN = r'r"C:\\Users\\bu158\\HorseRacingAnalyzer\\data\\一旦避難用\\netkeiba_data_payouts_202001_202508\.json"'

print("=" * 80)
print("スクリプト一括更新ツール")
print("=" * 80)

for script_name in scripts:
    script_path = os.path.join(os.path.dirname(__file__), script_name)

    if not os.path.exists(script_path):
        print(f"\n[SKIP] {script_name}: ファイルが見つかりません")
        continue

    print(f"\n[UPDATE] {script_name}")

    # ファイル読み込み
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # data_config のインポートを追加（まだなければ）
    if 'from data_config import' not in content:
        # import文を探して直後に追加
        import_section = []
        lines = content.split('\n')
        insert_index = 0

        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                insert_index = i + 1

        if insert_index > 0:
            lines.insert(insert_index, 'from data_config import MAIN_CSV, MAIN_JSON')
            content = '\n'.join(lines)
            print("  - data_config インポートを追加")

    # CSVパスを置換
    csv_matches = len(re.findall(OLD_CSV_PATTERN, content))
    if csv_matches > 0:
        content = re.sub(OLD_CSV_PATTERN, 'MAIN_CSV', content)
        print(f"  - CSV パスを置換 ({csv_matches}箇所)")

    # JSONパスを置換
    json_matches = len(re.findall(OLD_JSON_PATTERN, content))
    if json_matches > 0:
        content = re.sub(OLD_JSON_PATTERN, 'MAIN_JSON', content)
        print(f"  - JSON パスを置換 ({json_matches}箇所)")

    # 変更があれば保存
    if content != original_content:
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  → 更新完了")
    else:
        print("  → 変更なし（既に最新）")

print("\n" + "=" * 80)
print("全スクリプトの更新完了")
print("=" * 80)

print("\n【更新内容】")
print("1. data_config のインポートを追加")
print("2. 古いCSV/JSONパスを MAIN_CSV, MAIN_JSON に置換")
print("\n【次のステップ】")
print("1. 任意の訓練スクリプトを実行して動作確認")
print("2. 新しいデータが追加されたら auto_merge_system.py を実行")
print("3. data_config.py のパスを更新すれば全スクリプトが新データを使用")
