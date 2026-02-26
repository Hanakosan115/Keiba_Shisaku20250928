import pandas as pd
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False, nrows=5)
print("Column count:", len(df.columns))
print("\nColumns:")
for i, col in enumerate(df.columns, 1):
    print(f"{i:2d}. {col}")
