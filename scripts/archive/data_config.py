"""
データファイルパスの一元管理
全スクリプトでこのファイルをインポートして使用

使い方:
    from data_config import MAIN_CSV, MAIN_JSON
    df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
"""

# メインデータファイル（クリーン版: 2020-2024年、未来データ除外済み）
MAIN_CSV = r"C:\Users\bu158\Keiba_Shisaku20250928\netkeiba_data_2020_2024_clean.csv"
MAIN_JSON = r"C:\Users\bu158\Keiba_Shisaku20250928\netkeiba_data_payouts_2020_2024_clean.json"

# 旧データファイル（未来データ含む、参考用）
# MAIN_CSV = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_combined_202001_202511_merged.csv"
# MAIN_JSON = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_payouts_202001_202511_merged.json"

# データディレクトリ
DATA_DIR = r"C:\Users\bu158\HorseRacingAnalyzer\data"
BACKUP_DIR = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\backups"

# 古いファイル（参考用）
OLD_CSV_202508 = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_combined_202001_202508.csv"
OLD_JSON_202508 = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_payouts_202001_202508.json"
