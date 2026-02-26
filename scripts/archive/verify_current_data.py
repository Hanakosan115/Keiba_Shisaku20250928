"""
現状データの検証スクリプト

目的:
  既存のCSVデータに何が含まれていて、
  何が欠けているかを明確にする
"""

import pandas as pd
import numpy as np
from data_config import MAIN_CSV

print("="*80)
print("現状データ検証")
print("="*80)

# データ読み込み
print("\nデータ読み込み中...")
df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False, nrows=1000)
print(f"サンプル: {len(df)}件")

# 全列リスト
print("\n" + "="*80)
print("【利用可能な列一覧】")
print("="*80)
print(f"総列数: {len(df.columns)}")

# カテゴリ別に表示
categories = {
    '基本情報': ['race_id', 'date', 'Umaban', 'HorseName', 'horse_id', 'Rank',
                'SexAge', 'Sex', 'Age'],

    '人物': ['JockeyName', 'jockey_id', 'TrainerName', 'trainer_id'],

    'レース情報': ['race_name', 'race_num', 'track_name', 'course_type', 'distance',
                  'weather', 'track_condition', 'turn', 'turn_detail', 'start_time'],

    'パフォーマンス': ['Time', 'Diff', 'TimeIndex', 'Passage', 'Agari'],

    'オッズ・人気': ['Odds', 'Odds_x', 'Odds_y', 'Ninki'],

    '馬体': ['Weight', 'WeightDiff', 'WeightInfo', 'WeightInfoShutuba', 'Load'],

    '血統': ['father', 'mother_father'],

    '枠': ['Waku'],

    'その他': []
}

for category, cols in categories.items():
    print(f"\n【{category}】")
    available = [col for col in cols if col in df.columns]
    missing = [col for col in cols if col not in df.columns]

    if available:
        for col in available:
            # 欠損率を計算
            missing_rate = df[col].isna().sum() / len(df) * 100
            print(f"  OK {col:25s} (欠損: {missing_rate:5.1f}%)")

    if missing:
        for col in missing:
            print(f"  NG {col:25s} (列なし)")

# その他の列
other_cols = [col for col in df.columns if not any(col in cats for cats in categories.values())]
if other_cols:
    print(f"\n【その他】")
    for col in other_cols:
        missing_rate = df[col].isna().sum() / len(df) * 100
        print(f"  OK {col:25s} (欠損: {missing_rate:5.1f}%)")

# 重要データの詳細チェック
print("\n" + "="*80)
print("【重要項目の詳細チェック】")
print("="*80)

# 1. Passage（位置取り）
print("\n1. Passage（位置取り）")
if 'Passage' in df.columns:
    sample_passages = df['Passage'].dropna().head(10)
    print("  サンプル:")
    for p in sample_passages:
        print(f"    {p}")

    # フォーマット確認
    has_dash = sample_passages.str.contains('-').sum()
    print(f"  ダッシュ区切り: {has_dash}/{len(sample_passages)}")
else:
    print("  NG 列が存在しません")

# 2. Agari（上がり3F）
print("\n2. Agari（上がり3F）")
if 'Agari' in df.columns:
    agari_values = df['Agari'].dropna()
    print(f"  データ数: {len(agari_values)}/{len(df)} ({100*len(agari_values)/len(df):.1f}%)")
    print(f"  サンプル: {agari_values.head(5).tolist()}")

    # 数値化可能か
    agari_numeric = pd.to_numeric(agari_values, errors='coerce')
    print(f"  数値化可能: {agari_numeric.notna().sum()}/{len(agari_values)}")
else:
    print("  NG 列が存在しません")

# 3. 血統
print("\n3. 血統")
for col in ['father', 'mother_father']:
    if col in df.columns:
        available = df[col].notna().sum()
        print(f"  OK {col}: {available}/{len(df)} ({100*available/len(df):.1f}%)")
        print(f"    サンプル: {df[col].dropna().head(3).tolist()}")
    else:
        print(f"  NG {col}: 列が存在しません")

# 4. 調教情報
print("\n4. 調教情報")
training_cols = ['training_time', 'training_eval', 'training_date', 'training_comment']
training_found = False
for col in training_cols:
    if col in df.columns:
        print(f"  OK {col}: あり")
        training_found = True
    else:
        print(f"  NG {col}: なし")

if not training_found:
    print("  -> 調教情報は取得されていない")

# 5. ラップタイム
print("\n5. ラップタイム")
lap_cols = ['lap_200m', 'lap_400m', 'lap_time', 'lap', 'pace']
lap_found = False
for col in lap_cols:
    if col in df.columns:
        print(f"  OK {col}: あり")
        lap_found = True
    else:
        print(f"  NG {col}: なし")

if not lap_found:
    print("  -> ラップタイムは取得されていない")

# 6. 馬場情報
print("\n6. 馬場情報")
track_cols = ['track_moisture', 'track_bias', 'track_comment', 'week_number']
track_found = False
for col in track_cols:
    if col in df.columns:
        print(f"  OK {col}: あり")
        track_found = True
    else:
        print(f"  NG {col}: なし")

if not track_found:
    print("  -> 詳細な馬場情報は取得されていない")

# 7. 馬具
print("\n7. 馬具変更")
gear_cols = ['blinker', 'gear', 'equipment', 'horse_gear']
gear_found = False
for col in gear_cols:
    if col in df.columns:
        print(f"  OK {col}: あり")
        gear_found = True
    else:
        print(f"  NG {col}: なし")

if not gear_found:
    print("  -> 馬具情報は取得されていない")

# まとめ
print("\n" + "="*80)
print("【まとめ：欠けているデータ】")
print("="*80)

missing_important = []

if not lap_found:
    missing_important.append("NG ラップタイム（最重要！）")

if not training_found:
    missing_important.append("NG 調教情報")

if not track_found:
    missing_important.append("NG 馬場詳細情報")

if not gear_found:
    missing_important.append("NG 馬具変更情報")

# Passageの形式確認
if 'Passage' in df.columns:
    passage_ok = df['Passage'].dropna().str.contains('-').sum() > len(df) * 0.5
    if not passage_ok:
        missing_important.append("WARN Passage形式が不完全")

if missing_important:
    print("\n取得が必要なデータ:")
    for item in missing_important:
        print(f"  {item}")
else:
    print("\nOK 主要データは揃っています！")

# 次のアクション
print("\n" + "="*80)
print("【推奨される次のアクション】")
print("="*80)

print("""
優先度【高】:
1. ラップタイム取得スクリプトの作成
   → ペース予想の基礎となる最重要データ

2. 現状のPassageデータから脚質を正確に計算
   → 既存データの活用

3. コース特性データベースの構築
   → 外部データとして整備

優先度【中】:
4. 調教情報の取得
   → 馬の仕上がり状態

5. 馬場バイアス情報の収集
   → 開幕週判定など

優先度【低】:
6. 馬具変更情報
   → 影響は限定的
""")

print("\n検証完了！")
