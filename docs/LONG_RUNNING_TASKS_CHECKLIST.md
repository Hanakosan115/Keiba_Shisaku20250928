# 長時間作業チェックリスト

**作成日**: 2026年2月21日
**対象**: 24時間以上不在時に実行可能な作業
**優先順位**: 高 → 中 → 低

---

## 🔴 優先度: 高（必須）

### タスク1: 払戻データ収集・検証 ⭐⭐⭐
**所要時間**: 9-10時間
**詳細**: `PAYOUT_DATA_COLLECTION_PROCEDURE.md` 参照

**実施内容**:
1. 既存660レースで仮検証（5分）
2. 2020-2026年全期間データ収集（8時間）
3. 全期間での完全検証（30分）
4. 結果レポート作成（30分）

**成果物**:
- `payout_2020_2026_FULL.json` (約15-20MB)
- `phase13_COMPLETE_VERIFICATION_RESULTS.md`
- 複勝・ワイド・馬連の実データ回収率

**状態**: ✅ 手順書作成済み

---

### タスク2: 欠損馬データの補完
**所要時間**: 1-2時間
**優先度**: 🔴 高

**現状**:
```
father: 75件欠損 (0.2%)
mother_father: 75件欠損 (0.2%)
```

**実施内容**:
```python
# 欠損馬データを特定
import pandas as pd

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv')
missing_horses = df[df['father'].isna() | df['mother_father'].isna()]

print(f"欠損レコード数: {len(missing_horses)}")
print(f"ユニーク馬ID数: {missing_horses['horse_id'].nunique()}")

# horse_idのリスト
horse_ids_to_fetch = missing_horses['horse_id'].unique().tolist()
print(f"\n取得対象: {len(horse_ids_to_fetch)}頭")

# スクレイピングで補完
from scrape_horse_selenium import scrape_horse_data

for horse_id in horse_ids_to_fetch:
    horse_data = scrape_horse_data(horse_id)
    # データベース更新
    # ...
```

**スクリプト作成**:
```bash
# ファイル: fix_missing_horse_data.py
```

**成果物**:
- 欠損データ0件達成
- 予測精度向上（わずかながら）

---

### タスク3: データベース整合性チェック
**所要時間**: 30分-1時間
**優先度**: 🔴 高

**実施内容**:
```python
"""
netkeiba_data_2020_2024_enhanced.csv の健全性チェック
"""
import pandas as pd
import numpy as np

print("データベース整合性チェック")
print("="*80)

df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

# 1. 基本統計
print(f"\n総レコード数: {len(df):,}")
print(f"総カラム数: {len(df.columns)}")
print(f"期間: {df['date'].min()} 〜 {df['date'].max()}")

# 2. 重複チェック
duplicates = df.duplicated(subset=['race_id', 'horse_id'], keep=False)
if duplicates.sum() > 0:
    print(f"\n⚠️ 重複レコード検出: {duplicates.sum():,}件")
    df_dup = df[duplicates]
    print(df_dup[['race_id', 'horse_id', 'date', '馬名']].head(20))
else:
    print("\n✅ 重複レコードなし")

# 3. race_id形式チェック
df['race_id_str'] = df['race_id'].astype(str)
invalid_ids = df[df['race_id_str'].str.len() != 12]
if len(invalid_ids) > 0:
    print(f"\n⚠️ 不正なrace_id: {len(invalid_ids):,}件")
else:
    print("\n✅ race_id形式正常")

# 4. 着順の整合性
df['着順'] = pd.to_numeric(df['着順'], errors='coerce')
invalid_rank = df[(df['着順'] < 1) | (df['着順'] > 18)]
if len(invalid_rank) > 0:
    print(f"\n⚠️ 不正な着順: {len(invalid_rank):,}件")
else:
    print("\n✅ 着順データ正常")

# 5. オッズの整合性
df['単勝'] = pd.to_numeric(df['単勝'], errors='coerce')
invalid_odds = df[(df['単勝'] < 1.0) | (df['単勝'] > 1000)]
if len(invalid_odds) > 0:
    print(f"\n⚠️ 不正なオッズ: {len(invalid_odds):,}件")
else:
    print("\n✅ オッズデータ正常")

# 6. 日付の整合性
df['date_normalized'] = pd.to_datetime(df['date'], format='%Y年%m月%d日', errors='coerce')
invalid_dates = df[df['date_normalized'].isna()]
if len(invalid_dates) > 0:
    print(f"\n⚠️ 不正な日付: {len(invalid_dates):,}件")
else:
    print("\n✅ 日付データ正常")

# 7. 結果サマリー
print("\n" + "="*80)
print("チェック完了")
print("="*80)
```

**スクリプト**: `check_database_integrity.py`

**成果物**:
- 整合性レポート
- 問題があれば修正スクリプトも作成

---

## 🟡 優先度: 中（推奨）

### タスク4: 古いバックアップファイルの削除
**所要時間**: 10分
**優先度**: 🟡 中
**削減容量**: 3-4GB

**現状**:
```bash
# 26個のバックアップファイルが存在
netkeiba_data_2020_2024_enhanced_backup_20251220_*.csv
```

**実施内容**:
```bash
# 最新5個のみ保持、残りを削除
cd C:\Users\bu158\Keiba_Shisaku20250928

# PowerShellで実行
powershell "Get-ChildItem -Filter 'netkeiba_data_*_backup_*.csv' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 5 | Remove-Item -Verbose"
```

**確認**:
```bash
# 削除前のファイル数とサイズ
dir netkeiba_data_*_backup_*.csv

# 削除後
dir netkeiba_data_*_backup_*.csv
```

**成果物**:
- ディスク容量3-4GB削減

---

### タスク5: 古いモデルファイルの削除
**所要時間**: 5分
**優先度**: 🟡 中
**削減容量**: 500MB

**削除対象**:
```
model_phase10_win.pkl
model_phase10_top3.pkl
model_phase10_hybrid_win.pkl
model_phase10_hybrid_top3.pkl
model_phase11_win.pkl
model_phase11_top3.pkl
model_phase12_win.pkl
model_phase12_top3.pkl
model_phase12_analyzers.pkl
model_win_prediction.pkl
model_top3_prediction.pkl
```

**実施前確認**:
```python
# Phase 13モデルが存在することを確認
import os

phase13_models = [
    'phase13_model_win.pkl',
    'phase13_calibrators.pkl',
    'phase13_feature_list.pkl'
]

all_exist = all(os.path.exists(m) for m in phase13_models)
if all_exist:
    print("✅ Phase 13モデル確認完了 - 旧モデル削除可能")
else:
    print("⚠️ Phase 13モデルが見つかりません - 削除保留")
```

**実施**:
```bash
# 削除実行
del model_phase10_*.pkl
del model_phase11_*.pkl
del model_phase12_*.pkl
del model_win_prediction.pkl
del model_top3_prediction.pkl
```

---

### タスク6: アーカイブフォルダの圧縮
**所要時間**: 30分
**優先度**: 🟡 中
**削減容量**: 200-300MB

**実施内容**:
```bash
# PowerShellで圧縮
cd C:\Users\bu158\Keiba_Shisaku20250928

# 日付付きで圧縮
$date = Get-Date -Format "yyyyMMdd"
Compress-Archive -Path "archive" -DestinationPath "archive_backup_$date.zip" -CompressionLevel Optimal

# 確認
dir archive_backup_*.zip
```

**成果物**:
- `archive_backup_20260221.zip` (約200-300MB)
- 必要に応じて元のarchive/フォルダは削除可能

---

## 🟢 優先度: 低（任意）

### タスク7: 馬キャッシュの更新
**所要時間**: 2-3時間
**優先度**: 🟢 低

**実施内容**:
```python
# 最近のレース（2025-2026年）の馬データを再取得
# 統計情報が最新になる
```

**効果**: 微小（予測精度0.1%程度の改善可能性）

---

### タスク8: 特徴量の再計算
**所要時間**: 1-2時間
**優先度**: 🟢 低

**実施内容**:
```python
# feature_engineering.pyを使って全レコードの特徴量を再計算
# 欠損値の補完や計算ミスの修正
```

**効果**: データの一貫性向上

---

### タスク9: __pycache__のクリア
**所要時間**: 1分
**優先度**: 🟢 低
**削減容量**: 50-100MB

**実施内容**:
```bash
# 全ての__pycache__フォルダを削除
cd C:\Users\bu158\Keiba_Shisaku20250928
powershell "Get-ChildItem -Path . -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force -Verbose"
```

---

## 📊 推奨実施順序（24時間不在時）

### フェーズ1: 即座実行（開始〜15分）
1. ✅ タスク1開始: 払戻データ収集スクリプト起動（バックグラウンド）
2. ✅ タスク3実行: データベース整合性チェック（10分）
3. ✅ タスク9実行: __pycache__クリア（1分）

### フェーズ2: 並行実行（15分〜2時間）
4. ✅ タスク2実行: 欠損馬データ補完（1-2時間）
5. ✅ タスク4実行: 古いバックアップ削除（5分）
6. ✅ タスク5実行: 古いモデル削除（5分）
7. ✅ タスク6実行: アーカイブ圧縮（30分）

### フェーズ3: 待機（2時間〜8時間）
- タスク1のバックグラウンド処理を待つ
- （この間は他の作業不要）

### フェーズ4: 最終処理（8時間〜10時間）
8. ✅ タスク1完了確認: 払戻データ収集完了
9. ✅ タスク1検証: Phase 13完全再検証実施（30分）
10. ✅ レポート作成: 結果のMD化（30分）

---

## 📋 実行チェックリスト

### 必須タスク（優先度: 高）
- [ ] タスク1: 払戻データ収集・検証（9-10時間）
- [ ] タスク2: 欠損馬データ補完（1-2時間）
- [ ] タスク3: データベース整合性チェック（30分）

### 推奨タスク（優先度: 中）
- [ ] タスク4: 古いバックアップ削除（10分）
- [ ] タスク5: 古いモデル削除（5分）
- [ ] タスク6: アーカイブ圧縮（30分）

### 任意タスク（優先度: 低）
- [ ] タスク7: 馬キャッシュ更新（2-3時間）
- [ ] タスク8: 特徴量再計算（1-2時間）
- [ ] タスク9: __pycache__クリア（1分）

---

## 🎯 推定合計時間

**最小構成**（必須タスクのみ）:
- タスク1: 9-10時間
- タスク2: 1-2時間
- タスク3: 30分
- **合計**: **約11-13時間**

**推奨構成**（必須+推奨）:
- 上記 + タスク4-6
- **合計**: **約12-14時間**

**完全実施**（全タスク）:
- **合計**: **約15-18時間**

---

## 📝 実行前の準備

### 1. 必要なスクリプトの作成
```bash
# まだ作成していないスクリプト
- collect_payouts_2020_2026_FULL.py
- phase13_exotic_bets_REAL_DATA.py
- phase13_COMPLETE_VERIFICATION.py
- fix_missing_horse_data.py
- check_database_integrity.py
```

### 2. バックアップの作成
```bash
# 作業開始前にメインDBのバックアップ
copy netkeiba_data_2020_2024_enhanced.csv netkeiba_data_BACKUP_BEFORE_TASKS.csv
```

### 3. ログファイルの準備
```bash
# 各タスクのログファイル
task1_payout_collection.log
task2_horse_data_fix.log
task3_integrity_check.log
```

---

## ⚠️ 注意事項

1. **ネットワーク接続**: 払戻データ収集中は安定した接続が必要
2. **ディスク容量**: 最低10GB以上の空き容量を確保
3. **PC稼働**: スリープモード無効化を推奨
4. **バックアップ**: 作業前に必ずバックアップ作成

---

**作成者**: Claude Opus 4.6
**最終更新**: 2026年2月21日
