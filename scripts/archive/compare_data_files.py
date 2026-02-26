"""
データファイルの比較と正しいファイルの特定
"""
import pandas as pd
import os

files_to_check = [
    (r'C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202510.csv', '202510'),
    (r'C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202511.csv', '202511'),
    (r'C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_combined_202001_202511_merged.csv', '避難用_202511_merged'),
]

print("=" * 80)
print("データファイル比較")
print("=" * 80)

results = []

for filepath, label in files_to_check:
    if not os.path.exists(filepath):
        print(f"\n[{label}] ファイルが存在しません")
        continue

    print(f"\n[{label}]")
    print(f"パス: {filepath}")

    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"サイズ: {size_mb:.2f} MB")

    try:
        df = pd.read_csv(filepath, low_memory=False)
        print(f"行数: {len(df):,}")
        print(f"カラム数: {len(df.columns)}")

        if 'date' in df.columns:
            # 日付の最小・最大（文字列として）
            dates = df['date'].astype(str)
            dates_clean = dates[dates.str.len() >= 10]  # 最低10文字以上
            if len(dates_clean) > 0:
                min_date = dates_clean.min()[:10]
                max_date = dates_clean.max()[:10]
                print(f"日付範囲: {min_date} ～ {max_date}")

            # 2024年のデータ数
            dates_2024 = dates[dates.str.startswith('2024', na=False)]
            print(f"2024年データ: {len(dates_2024):,}行")

            # 10月、11月のデータ
            dates_oct = dates[dates.str.startswith('2024-10', na=False)]
            dates_nov = dates[dates.str.startswith('2024-11', na=False)]
            print(f"  10月: {len(dates_oct):,}行")
            print(f"  11月: {len(dates_nov):,}行")

        if 'race_id' in df.columns:
            print(f"ユニークレース数: {df['race_id'].nunique():,}")

        results.append({
            'label': label,
            'path': filepath,
            'size_mb': size_mb,
            'rows': len(df),
            'has_data': True
        })

    except Exception as e:
        print(f"エラー: {e}")
        results.append({
            'label': label,
            'path': filepath,
            'size_mb': size_mb,
            'rows': 0,
            'has_data': False
        })

# 推奨ファイルの決定
print("\n" + "=" * 80)
print("推奨アクション")
print("=" * 80)

# 最大の行数を持つファイル
valid_results = [r for r in results if r['has_data']]
if valid_results:
    best = max(valid_results, key=lambda x: x['rows'])
    print(f"\n最も完全なデータファイル: [{best['label']}]")
    print(f"  行数: {best['rows']:,}")
    print(f"  サイズ: {best['size_mb']:.2f} MB")
    print(f"\n推奨: このファイルをベースに使用してください")
    print(f"パス: {best['path']}")

print("\n" + "=" * 80)
print("次のステップ")
print("=" * 80)
print("\n1. 202510ファイル（最も完全）をベースにする")
print("2. 202511（11月のみ）の新データをマージ")
print("3. data_config.pyを更新")
