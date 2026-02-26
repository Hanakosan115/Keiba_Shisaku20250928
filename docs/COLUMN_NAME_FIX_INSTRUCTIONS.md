# カラム名不一致問題 解決指示書

**作成日**: 2026年2月21日
**目的**: Phase 2/3のブロッカーとなっているカラム名不一致を解決する
**推定所要時間**: 1-2時間（準備） + 4-8時間（バックグラウンド実行）

---

## 📋 問題の概要

### 現状

**Phase 13特徴量計算モジュール**は以下の英語カラム名を期待:
```python
'rank', 'father', 'mother_father', 'trainer', 'jockey',
'weather', 'track_condition', 'course_type', 'horse_weight', etc.
```

**完全データベース**は日本語カラム名を使用:
```python
'着順', '父', '母父', '調教師', '騎手',
'天気', '馬場状態', 'コースタイプ', '馬体重', etc.
```

### 影響

- ❌ 特徴量計算が `KeyError: 'rank'` で停止
- ❌ Phase 2（Phase 13再検証）が実行不可
- ❌ Phase 3（Phase 14開発）が実行不可

---

## 🎯 解決方針

### Option A: データベースのカラム名を英語に統一（推奨）

**メリット**:
- 一度実施すれば今後の開発がスムーズ
- Phase 13モジュールをそのまま使用可能
- 可読性向上

**デメリット**:
- 初回の変換作業が必要
- 既存スクリプトの一部修正が必要

**推定時間**: 1-2時間

### Option B: Phase 13モジュールを日本語カラム対応に修正

**メリット**:
- データベースを変更しない

**デメリット**:
- Phase 13モジュールの複数ファイルを修正が必要
- 今後も同じ問題が発生する可能性
- メンテナンス性が低下

**推定時間**: 2-4時間

### 推奨: Option A

---

## 📝 実施手順（Option A）

### ステップ1: カラム名マッピングの作成

**ファイル**: `create_column_mapping.py`

```python
"""
完全データベースのカラム名を分析し、英語マッピングを作成
"""
import pandas as pd
import json

# 完全データベース読み込み（1行のみ）
df = pd.read_csv('data/main/netkeiba_data_2020_2025_complete.csv', nrows=1)

# Phase 13が期待するカラム名
EXPECTED_COLUMNS = {
    # 基本情報
    'race_id': 'race_id',
    'horse_id': 'horse_id',
    'date': 'date',

    # レース情報
    'race_name': 'race_name',
    'race_num': 'race_num',
    'distance': 'distance',
    'course_type': 'course_type',  # 芝/ダ
    'turn': 'turn',
    'weather': 'weather',
    'track_condition': 'track_condition',

    # 馬情報
    'HorseName_url': 'HorseName_url',
    'father': 'father',
    'mother_father': 'mother_father',

    # レース結果
    'rank': '着順',  # ★ 重要
    'odds': '単勝',
    'popularity': '人気',
    'jockey': '騎手',
    'trainer': '調教師',
    'horse_weight': '馬体重',
    'bracket': '枠番',

    # 統計情報（既に英語の場合が多い）
    'total_starts': 'total_starts',
    'total_win_rate': 'total_win_rate',
    'total_earnings': 'total_earnings',
    'turf_win_rate': 'turf_win_rate',
    'dirt_win_rate': 'dirt_win_rate',
    'distance_similar_win_rate': 'distance_similar_win_rate',
    'prev_race_rank': 'prev_race_rank',
    'days_since_last_race': 'days_since_last_race',
    'avg_passage_position': 'avg_passage_position',
    'avg_last_3f': 'avg_last_3f',
    'grade_race_starts': 'grade_race_starts',
}

# 現在のカラム名を確認
print("完全データベースの現在のカラム名:")
print(f"総数: {len(df.columns)}")
print()

# マッピングが必要なカラムを特定
mapping = {}
reverse_mapping = {v: k for k, v in EXPECTED_COLUMNS.items()}

for col in df.columns:
    if col in reverse_mapping:
        # 日本語カラムが見つかった
        english_name = reverse_mapping[col]
        mapping[col] = english_name
        print(f"  {col} → {english_name}")
    elif col in EXPECTED_COLUMNS:
        # 既に英語
        mapping[col] = col
    else:
        # マッピング不明（そのまま維持）
        mapping[col] = col

# マッピングをJSON保存
with open('column_name_mapping.json', 'w', encoding='utf-8') as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)

print()
print(f"マッピングを保存: column_name_mapping.json")
print(f"総マッピング数: {len(mapping)}")
```

**実行**:
```bash
python create_column_mapping.py
```

**出力**: `column_name_mapping.json`

---

### ステップ2: データベース前処理スクリプトの作成

**ファイル**: `preprocess_database.py`

```python
"""
完全データベースのカラム名を英語に統一
"""
import pandas as pd
import json
from datetime import datetime

print("="*80)
print("  完全データベース カラム名標準化")
print("="*80)
print()

# マッピング読み込み
print("[1/4] カラム名マッピング読み込み...")
with open('column_name_mapping.json', 'r', encoding='utf-8') as f:
    mapping = json.load(f)
print(f"  マッピング数: {len(mapping)}")
print()

# データベース読み込み
print("[2/4] 完全データベース読み込み...")
df = pd.read_csv('data/main/netkeiba_data_2020_2025_complete.csv', low_memory=False)
print(f"  レコード数: {len(df):,}")
print(f"  カラム数: {len(df.columns)}")
print()

# バックアップ
print("[3/4] バックアップ作成...")
backup_file = f'data/main/netkeiba_data_2020_2025_complete_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
df.to_csv(backup_file, index=False, encoding='utf-8-sig')
print(f"  {backup_file}")
print()

# カラム名変更
print("[4/4] カラム名変更中...")
df_renamed = df.rename(columns=mapping)

# 変更されたカラムをレポート
changed = []
for old, new in mapping.items():
    if old != new:
        changed.append((old, new))

print(f"  変更されたカラム数: {len(changed)}")
if changed:
    print("\n  主な変更:")
    for old, new in changed[:10]:
        print(f"    {old} → {new}")
print()

# 保存
output_file = 'data/main/netkeiba_data_2020_2025_standardized.csv'
df_renamed.to_csv(output_file, index=False, encoding='utf-8-sig')
print(f"  保存完了: {output_file}")
print()

# 検証
print("="*80)
print("  検証")
print("="*80)

# Phase 13が期待する重要カラムの存在確認
critical_columns = ['rank', 'father', 'mother_father', 'trainer', 'jockey']
missing = []
for col in critical_columns:
    if col not in df_renamed.columns:
        missing.append(col)

if missing:
    print(f"  ❌ 警告: {len(missing)}個の重要カラムが不足")
    for col in missing:
        print(f"    - {col}")
else:
    print(f"  ✅ 全ての重要カラムが存在")

print()
print("="*80)
print("  完了")
print("="*80)
```

**実行**:
```bash
python preprocess_database.py
```

**出力**:
- `data/main/netkeiba_data_2020_2025_standardized.csv` - 標準化版DB
- `data/main/netkeiba_data_2020_2025_complete_backup_*.csv` - バックアップ

---

### ステップ3: 特徴量計算スクリプトの修正

**ファイル**: `calculate_features_standardized.py`

`calculate_features_complete_db.py`をコピーして、以下を修正:

```python
# 変更前
df_all = pd.read_csv('data/main/netkeiba_data_2020_2025_complete.csv', low_memory=False)

# 変更後
df_all = pd.read_csv('data/main/netkeiba_data_2020_2025_standardized.csv', low_memory=False)
```

**実行**:
```bash
python calculate_features_standardized.py
```

**推定時間**: 4-8時間（バックグラウンド実行）

---

### ステップ4: 特徴量計算の実行と監視

**バックグラウンド実行**:
```bash
nohup python calculate_features_standardized.py > feature_calc_standardized.log 2>&1 &
```

**進捗確認**:
```bash
# ログの最新20行を表示
tail -20 calculate_features_standardized.log

# 10秒ごとに自動更新
watch -n 10 tail -20 calculate_features_standardized.log
```

**チェックポイントファイル確認**:
```bash
# 10,000レースごとに保存される
ls -lh calculate_features_checkpoint.csv
```

**完了確認**:
- `data/phase14/train_features.csv` が作成されたら完了
- ログファイルに "完了" の表示

---

## ⏰ 時間見積もり

### 各ステップの所要時間

| ステップ | 作業内容 | 所要時間 | 備考 |
|:---:|:---|---:|:---|
| 1 | マッピング作成 | 10分 | スクリプト実行 |
| 2 | DB前処理 | 10-15分 | 28万レコード処理 |
| 3 | スクリプト修正 | 5分 | 1行変更 |
| 4 | 特徴量計算 | **4-8時間** | バックグラウンド |

**合計**: 約30分（準備） + 4-8時間（計算）

### バックグラウンド実行中にできること

特徴量計算は完全にバックグラウンドで実行されるため、
その間に以下の作業が可能:

1. Phase 2スクリプトの準備
2. Phase 14訓練スクリプトの最終確認
3. ドキュメントの更新
4. または離席可能

---

## 🚀 大規模な時間を要する作業の提案

### 提案1: 完全なPhase 14開発（推奨）★★★★★

**内容**:
1. カラム名問題解決（上記）
2. 特徴量計算（4-8時間）
3. Phase 14モデル訓練（2-3時間）
4. 2024年全レースでバックテスト（1-2時間）
5. Phase 13との性能比較

**総所要時間**: **8-14時間**

**期待される成果**:
- ✅ Phase 14複勝モデル完成
- ✅ Phase 13の真の性能評価
- ✅ 単勝 vs 複勝の比較
- ✅ 実運用可能なモデル

**価値**: ★★★★★（最高）

---

### 提案2: Phase 13の全確率帯クリーン検証 ★★★★☆

**内容**:
1. カラム名問題解決
2. Phase 13モデルで2024年全レースを再検証
3. 全10確率帯の真の回収率を算出
4. 219%との比較レポート

**総所要時間**: **2-3時間**

**期待される成果**:
- ✅ Phase 13の真の性能判明
- ✅ 実用可能性の判定
- ✅ 最適確率帯の特定

**価値**: ★★★★☆（高い）

---

### 提案3: GUIの特徴量計算修正 ★★★☆☆

**内容**:
1. `keiba_prediction_gui_v3.py`の`predict_core()`を修正
2. 79特徴量 → 39特徴量に変更
3. Phase 13モデルとの整合性確保

**総所要時間**: **2-4時間**

**期待される成果**:
- ✅ GUIで予測が実行可能に
- ✅ Phase 13モデルが使用可能に

**価値**: ★★★☆☆（中程度）

**注意**: Phase 14開発とは独立。両方実施も可能。

---

### 提案4: 2020-2025年の完全バックテスト ★★★★☆

**内容**:
1. Phase 13モデルで2020-2025年全レースをバックテスト
2. 年別・確率帯別の詳細分析
3. 経年変化の把握

**総所要時間**: **3-5時間**

**期待される成果**:
- ✅ 6年分の性能データ
- ✅ モデルの安定性評価
- ✅ 年による性能変動の分析

**価値**: ★★★★☆（高い）

---

### 提案5: WIN5予測システムの完成 ★★☆☆☆

**内容**:
1. WIN5専用モデルの開発
2. 5レース組み合わせ最適化
3. バックテスト検証

**総所要時間**: **6-10時間**

**期待される成果**:
- ✅ WIN5予測機能
- ⚠️ ただし収益性は不明

**価値**: ★★☆☆☆（低い - 優先度低）

**理由**: Phase 13/14が優先

---

## 🎯 推奨する実施順序

### 最優先（必須）

1. **カラム名問題の解決**（30分）
   - ステップ1-3を実施

2. **特徴量計算の開始**（4-8時間、バックグラウンド）
   - ステップ4を実施
   - 他の作業と並行可能

### 特徴量計算完了後（優先度順）

3. **Phase 2: Phase 13再検証**（1-2時間）
   - 真の性能評価
   - 実用可能性判定

4. **Phase 3: Phase 14モデル訓練**（2-3時間）
   - 複勝モデル開発
   - バックテスト検証

5. **Phase 13 vs Phase 14 比較レポート**（1時間）
   - 性能比較
   - 推奨戦略

### 余力があれば

6. **GUIの修正**（2-4時間）
   - 39特徴量対応
   - Phase 13モデル使用可能化

7. **2020-2025完全バックテスト**（3-5時間）
   - 長期性能分析

---

## 📋 チェックリスト

### 準備段階
- [ ] `create_column_mapping.py` 作成
- [ ] `preprocess_database.py` 作成
- [ ] `calculate_features_standardized.py` 作成

### 実行段階
- [ ] カラム名マッピング作成
- [ ] データベース前処理実行
- [ ] バックアップ確認
- [ ] 標準化DB作成確認

### 特徴量計算
- [ ] バックグラウンド実行開始
- [ ] ログファイル確認
- [ ] チェックポイント保存確認（10,000レースごと）
- [ ] 完了確認（data/phase14/train_features.csv）

### Phase 2/3実行
- [ ] Phase 2スクリプト実行
- [ ] Phase 13真の性能確認
- [ ] Phase 3モデル訓練実行
- [ ] Phase 14バックテスト実行

### 最終確認
- [ ] 性能比較レポート作成
- [ ] 実運用マニュアル更新
- [ ] 全ドキュメント最終化

---

## ⚠️ 注意事項

### データバックアップ

前処理実行前に必ずバックアップを作成:
```bash
cp data/main/netkeiba_data_2020_2025_complete.csv \
   data/main/netkeiba_data_2020_2025_complete_backup_manual.csv
```

### ディスク容量

必要な容量:
- 元DB: 約200MB
- 標準化DB: 約200MB
- 特徴量計算結果: 約100-150MB
- **合計: 約500-600MB**

### 中断・再開

特徴量計算は10,000レースごとにチェックポイント保存。
Ctrl+Cで中断しても、次回実行時に自動的に続きから再開。

---

## 📞 問題が発生した場合

### エラー: KeyError

```python
KeyError: 'rank'
```

**原因**: マッピングが不完全
**解決**: `create_column_mapping.py`を再実行し、マッピングを確認

### エラー: FileNotFoundError

```python
FileNotFoundError: 'data/main/netkeiba_data_2020_2025_standardized.csv'
```

**原因**: 前処理が未実行
**解決**: `preprocess_database.py`を実行

### 特徴量計算が進まない

**確認**:
```bash
tail -f calculate_features_standardized.log
```

**対処**:
1. エラーメッセージを確認
2. チェックポイントファイルの存在確認
3. 必要なら中断して再実行

---

## 📊 期待される最終成果

### Phase 14開発完了時

1. **モデルファイル**:
   - `phase14_model_win.pkl` - 単勝予測
   - `phase14_model_place.pkl` - 複勝予測
   - `phase14_feature_list.pkl` - 特徴量リスト
   - `phase14_model_metadata.json` - メタデータ

2. **バックテスト結果**:
   - `phase14_backtest_results.csv` - 詳細結果
   - `phase2_phase13_clean_results.csv` - Phase 13真の性能

3. **ドキュメント**:
   - `docs/PHASE2_VERIFICATION_REPORT.md` - Phase 13再検証
   - `docs/PHASE3_DEVELOPMENT_REPORT.md` - Phase 14開発
   - `docs/PHASE13_VS_PHASE14_COMPARISON.md` - 性能比較

### 実用化への道筋

**Phase 13の真の性能が判明**:
- 80-100%なら実用可能
- GUIを修正して使用開始

**Phase 14が完成**:
- 複勝モデルとして運用
- Phase 13（単勝）と併用可能

---

**作成者**: Claude Opus 4.6
**作成日**: 2026年2月21日
**推定総所要時間**: 8-14時間（大部分はバックグラウンド実行）
**次のアクション**: ステップ1から順次実施
