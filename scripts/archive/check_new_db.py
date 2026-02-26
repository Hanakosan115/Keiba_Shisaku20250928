import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', nrows=10, low_memory=False)

print(f"Total rows in sample: {len(df)}")
print(f"Total columns: {len(df.columns)}")
print()
print("First 30 columns:")
for i, col in enumerate(df.columns[:30], 1):
    print(f"  {i:2d}. {col!r}")

print()
print("Checking key columns:")
for col in ['馬名', '馬番', 'HorseName', 'Umaban', 'Rank', '着順']:
    exists = col in df.columns
    print(f"  {col!r}: {exists}")

print()
print("Sample data (first 5 rows, first 10 cols):")
print(df.iloc[:5, :10])
