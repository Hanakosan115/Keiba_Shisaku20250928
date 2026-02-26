import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

# Check the newly added rows (should be 25749+)
print(f"Total rows in database: {len(df):,}")
print(f"First row index: {df.index[0]}")
print(f"Last row index: {df.index[-1]}")

# Check race 202506010101 again
test_race = df[df['race_id'] == '202506010101']
print(f"\nRace 202506010101: {len(test_race)} rows")
print(f"Row indices: {test_race.index.tolist()}")

# Check if new rows have date
print("\nDate values for this race:")
print(test_race[['race_id', 'date', 'HorseName', 'father']].to_string())

# Count rows by date presence
print(f"\n\nRows with date filled: {df['date'].notna().sum():,}")
print(f"Rows with date NaN: {df['date'].isna().sum():,}")

# Check all 2025 race IDs
df_2025 = df[df['race_id'].astype(str).str.startswith('2025')]
print(f"\n\n2025 race IDs:")
print(f"  Total rows: {len(df_2025):,}")
print(f"  With HorseName: {df_2025['HorseName'].notna().sum():,}")
print(f"  With father: {df_2025['father'].notna().sum():,}")
print(f"  With total_starts: {df_2025['total_starts'].notna().sum():,}")
print(f"  With date filled: {df_2025['date'].notna().sum():,}")
print(f"  With date NaN: {df_2025['date'].isna().sum():,}")
