"""
未来日付のデータを調査
"""
import pandas as pd
from data_config import MAIN_CSV

df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

print("=" * 80)
print("未来日付データの調査")
print("=" * 80)

future = df[df['date_parsed'] > '2024-12-31']
print(f"\n未来日付のレコード数: {len(future):,}行")

if len(future) > 0:
    print(f"日付範囲: {future['date_parsed'].min()} - {future['date_parsed'].max()}")

    # 月別集計
    print("\n未来データの月別分布:")
    monthly = future.groupby(future['date_parsed'].dt.to_period('M')).size()
    for month, count in monthly.items():
        print(f"  {month}: {count:,}行")

    # race_idのパターン確認
    print("\nrace_idサンプル (最初の10件):")
    for rid in future['race_id'].unique()[:10]:
        print(f"  {rid}")

    # 実際のレース名確認
    print("\nレース名サンプル:")
    for _, row in future.head(5).iterrows():
        race_name = row.get('RaceName', 'N/A')
        race_name = str(race_name)[:30] if race_name else 'N/A'
        print(f"  {row['date'][:10]}: {race_name} (race_id: {row['race_id']})")

    # この未来データを削除すべきか判断
    print("\n" + "=" * 80)
    print("推奨アクション")
    print("=" * 80)

    if len(future) / len(df) > 0.1:
        print(f"\n未来データが全体の{len(future)/len(df)*100:.1f}%を占めています")
        print("-> データ品質に重大な問題あり")
        print("-> クリーニングが必要")
    else:
        print(f"\n未来データは全体の{len(future)/len(df)*100:.1f}%のみ")
        print("-> 少数なのでフィルタリングで除外可能")

    print("\nオプション:")
    print("1. 未来データを除外してクリーン版CSVを作成")
    print("2. 元データを調査して原因特定")
else:
    print("\n[OK] 未来日付のデータはありません")

# 2024年データのみの統計
df_2024 = df[(df['date_parsed'] >= '2024-01-01') & (df['date_parsed'] <= '2024-12-31')]
print("\n" + "=" * 80)
print("2024年データ（正常範囲）の統計")
print("=" * 80)
print(f"総行数: {len(df_2024):,}行")
print(f"日付範囲: {df_2024['date_parsed'].min()} - {df_2024['date_parsed'].max()}")
print(f"ユニークレース数: {df_2024['race_id'].nunique():,}レース")
print(f"ユニーク馬数: {df_2024['horse_id'].nunique():,}頭")
