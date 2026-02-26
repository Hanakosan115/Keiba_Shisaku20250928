import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

# Check one race
test_race = df[df['race_id'] == '202506010101']
print(f"Race 202506010101: {len(test_race)} horses\n")

# All columns
print("All columns:")
for i, col in enumerate(df.columns):
    print(f"  {i+1}. {col}")

print(f"\nTotal columns: {len(df.columns)}")

# Check for statistics columns
stat_cols = ['father', 'mother_father', 'total_starts', 'total_win_rate',
             'turf_win_rate', 'dirt_win_rate', 'total_earnings']

print("\nStatistics columns existence:")
for col in stat_cols:
    exists = col in df.columns
    print(f"  {col}: {exists}")

# Sample data from test race
print("\nSample from race 202506010101:")
print(test_race[['race_id', 'Umaban', 'HorseName']].head())

# Check if statistics exist in this race
if 'father' in df.columns:
    print(f"\nfather column in this race:")
    print(test_race['father'].head())
