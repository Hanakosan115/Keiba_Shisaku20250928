"""
既存データベースの列名を確認
"""
import pandas as pd
import warnings
warnings.filterwarnings('ignore')

print("Checking existing database columns...")
print()

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', nrows=10, low_memory=False)

print(f"Total columns: {len(df.columns)}")
print()
print("First 30 columns:")
for i, col in enumerate(df.columns[:30], 1):
    print(f"  {i:2d}. {col!r}")

print()
print("Checking key columns:")
for col in ['馬番', 'Umaban', 'HorseName', '馬名']:
    print(f"  {col!r}: {col in df.columns}")

print()
print("Columns containing '馬' or 'uma':")
for col in df.columns:
    if '馬' in col or 'uma' in col.lower():
        print(f"  - {col!r}")
