import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

# Check race 202506010101
test_race = df[df['race_id'] == '202506010101']
print(f"Race 202506010101: {len(test_race)} rows\n")

# Show all data for this race
print("All rows for this race:")
print(test_race[['Umaban', 'HorseName', 'father', 'mother_father', 'total_starts', 'total_win_rate']].to_string())

print("\n" + "="*60)

# Count non-null values
print(f"\nNon-null values:")
print(f"  Umaban: {test_race['Umaban'].notna().sum()}")
print(f"  HorseName: {test_race['HorseName'].notna().sum()}")
print(f"  father: {test_race['father'].notna().sum()}")
print(f"  mother_father: {test_race['mother_father'].notna().sum()}")
print(f"  total_starts: {test_race['total_starts'].notna().sum()}")
print(f"  total_win_rate: {test_race['total_win_rate'].notna().sum()}")
print(f"  total_earnings: {test_race['total_earnings'].notna().sum()}")

# Now check all January 2025 races
df['date'] = pd.to_datetime(df['date'], errors='coerce')
df_jan = df[(df['date'] >= '2025-01-01') & (df['date'] < '2025-02-01')]

print(f"\n\nJanuary 2025 overview:")
print(f"  Total rows: {len(df_jan):,}")
print(f"  Unique races: {df_jan['race_id'].nunique()}")
print(f"  Rows with HorseName: {df_jan['HorseName'].notna().sum():,}")
print(f"  Rows with father: {df_jan['father'].notna().sum():,}")
print(f"  Rows with total_starts: {df_jan['total_starts'].notna().sum():,}")
print(f"  Rows with total_win_rate: {df_jan['total_win_rate'].notna().sum():,}")
