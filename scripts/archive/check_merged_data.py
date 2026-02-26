"""
マージ済みデータの内容確認
- 新しく追加されたレース数
- 日付範囲
- データの整合性チェック
"""
import pandas as pd

print("=" * 80)
print("マージ済みデータの確認")
print("=" * 80)

# 旧データ
OLD_CSV = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_combined_202001_202508.csv"
print("\n旧データ読み込み中...")
df_old = pd.read_csv(OLD_CSV, encoding='utf-8', low_memory=False)
print(f"旧データ: {len(df_old):,}件")

df_old['date_parsed'] = pd.to_datetime(df_old['date'], errors='coerce')
print(f"日付範囲: {df_old['date_parsed'].min()} ～ {df_old['date_parsed'].max()}")
old_races = df_old['race_id'].nunique()
print(f"レース数: {old_races:,}レース")

# 新マージ済みデータ
NEW_CSV = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_combined_202001_202511_merged.csv"
print("\n新マージ済みデータ読み込み中...")
df_new = pd.read_csv(NEW_CSV, encoding='utf-8', low_memory=False)
print(f"新データ: {len(df_new):,}件")

df_new['date_parsed'] = pd.to_datetime(df_new['date'], errors='coerce')
print(f"日付範囲: {df_new['date_parsed'].min()} ～ {df_new['date_parsed'].max()}")
new_races = df_new['race_id'].nunique()
print(f"レース数: {new_races:,}レース")

# 差分
print("\n" + "=" * 80)
print("【追加されたデータ】")
print("=" * 80)
print(f"追加レコード数: {len(df_new) - len(df_old):,}件")
print(f"追加レース数: {new_races - old_races:,}レース")

# 2024年9月以降のデータ
new_data = df_new[df_new['date_parsed'] >= '2024-09-01']
print(f"\n2024年9月以降のデータ: {len(new_data):,}件")
print(f"2024年9月以降のレース数: {new_data['race_id'].nunique():,}レース")

if len(new_data) > 0:
    print(f"月別内訳:")
    new_data['month'] = new_data['date_parsed'].dt.to_period('M')
    for month, count in new_data.groupby('month').size().items():
        print(f"  {month}: {count:,}件")

# データ品質チェック
print("\n" + "=" * 80)
print("【データ品質チェック】")
print("=" * 80)

# 必須カラムの確認
required_cols = ['race_id', 'Umaban', 'HorseName', 'Rank', 'Odds_x', 'date']
missing_cols = [col for col in required_cols if col not in df_new.columns]
if missing_cols:
    print(f"⚠️ 不足カラム: {missing_cols}")
else:
    print("✅ 必須カラムすべて存在")

# NULL値チェック
print("\n主要カラムのNULL率:")
for col in ['race_id', 'horse_id', 'Rank', 'Odds_x', 'date']:
    if col in df_new.columns:
        null_rate = df_new[col].isna().sum() / len(df_new) * 100
        print(f"  {col}: {null_rate:.2f}%")

print("\n" + "=" * 80)
print("確認完了")
print("=" * 80)
