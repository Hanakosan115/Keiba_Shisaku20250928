import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
df_2025 = df[df['race_id'].astype(str).str.startswith('2025')]

stat_cols = ['horse_avg_prize', 'horse_win_rate', 'horse_place_rate', 'horse_avg_odds']
available_cols = [c for c in stat_cols if c in df.columns]

print(f'Total 2025 races: {len(df_2025)}')
print(f'Available stat columns: {available_cols}')

if available_cols:
    for col in available_cols:
        count = df_2025[col].notna().sum()
        print(f'  {col}: {count} / {len(df_2025)} ({count/len(df_2025)*100:.1f}%)')
else:
    print('\nNo statistics columns found - races collected without horse stats')
