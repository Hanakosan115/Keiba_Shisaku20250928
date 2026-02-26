"""
日付形式を修正してサマリーを出力
"""
import pandas as pd
import re

print("データベース読み込み中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

print(f"総行数: {len(df):,}\n")

# 日付の変換関数
def convert_japanese_date(date_str):
    """日本語形式の日付を標準形式に変換"""
    if pd.isna(date_str):
        return None

    date_str = str(date_str)

    # 既に標準形式の場合
    if '-' in date_str:
        return date_str

    # 日本語形式 "2025年01月05日" -> "2025-01-05"
    match = re.match(r'(\d{4})年(\d{2})月(\d{2})日', date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"

    return date_str

# 日付列を修正
print("日付形式を修正中...")
df['date'] = df['date'].apply(convert_japanese_date)
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# 保存
print("データベースに保存中...")
df.to_csv('netkeiba_data_2020_2024_enhanced.csv', index=False, encoding='utf-8')

print("完了！\n")
print("="*60)

# サマリー
df_jan = df[(df['date'] >= '2025-01-01') & (df['date'] < '2025-02-01')]

print(f"\n1月データサマリー:")
print(f"  レース数: {df_jan['race_id'].nunique()}件")
print(f"  馬データ行数: {len(df_jan):,}行")
print(f"  平均馬数/レース: {len(df_jan) / df_jan['race_id'].nunique():.1f}頭")

stat_cols = ['father', 'mother_father', 'total_starts', 'total_win_rate',
             'turf_win_rate', 'dirt_win_rate', 'total_earnings']

print(f"\n統計列カバー率:")
for col in stat_cols:
    if col in df_jan.columns:
        count = df_jan[col].notna().sum()
        pct = count / len(df_jan) * 100 if len(df_jan) > 0 else 0
        print(f"  {col}: {count}/{len(df_jan)} ({pct:.1f}%)")
    else:
        print(f"  {col}: 列なし")

print("\n" + "="*60)
