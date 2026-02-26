import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_clean.csv', low_memory=False)

race_id = 202508040611
race_data = df[df['race_id'] == race_id]

print(f'Race {race_id} in database: {len(race_data)} rows')

if len(race_data) > 0:
    print('\nHorses in this race from CSV:')
    print(race_data[['Umaban', 'HorseName', 'horse_id']].head(10))
else:
    print('\nRace NOT found in database!')
    print(f'\nSample race_ids from CSV:')
    print(df['race_id'].head(10).tolist())
