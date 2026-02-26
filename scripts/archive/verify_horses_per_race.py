import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

print(f"Total: {len(df)} rows")
print()
print("Horses per race:")
for rid in sorted(df['race_id'].unique()):
    count = len(df[df['race_id'] == rid])
    print(f"  {rid}: {count} horses")

print()
print("SUCCESS: All races have multiple horses!" if all(len(df[df['race_id'] == rid]) > 1 for rid in df['race_id'].unique()) else "FAIL: Some races have only 1 horse")
