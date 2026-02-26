import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_clean.csv', low_memory=False)

# Find races from 2024 that are not maiden races
df_2024 = df[df['race_id'].str.startswith('20240', na=False)]

# Count horses per race
race_counts = df_2024.groupby(['race_id', 'race_name', 'date']).size().reset_index(name='horse_count')

# Filter out maiden races
non_maiden = race_counts[~race_counts['race_name'].str.contains('新馬', na=False)]

# Get races with reasonable horse count (10-18 horses)
good_races = non_maiden[(non_maiden['horse_count'] >= 10) & (non_maiden['horse_count'] <= 18)]

print("Sample non-maiden races for testing:")
print(good_races.head(10))
