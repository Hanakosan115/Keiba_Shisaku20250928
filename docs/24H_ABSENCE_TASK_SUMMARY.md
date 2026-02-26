# 24時間不在時 実行タスク サマリー

**作成日**: 2026年2月21日
**想定不在時間**: 24時間以上
**推定実行時間**: 12-14時間

---

## 🎯 実行する作業（推奨構成）

### 1️⃣ 払戻データ収集・検証 ⭐最重要
- **時間**: 9-10時間
- **詳細**: `PAYOUT_DATA_COLLECTION_PROCEDURE.md`
- **成果**: 複勝・ワイド・馬連の実データ検証完了

### 2️⃣ 欠損馬データ補完
- **時間**: 1-2時間
- **対象**: 75件の欠損データ
- **成果**: データベース完全化

### 3️⃣ データベース整合性チェック
- **時間**: 30分
- **対象**: 800MB CSVファイル
- **成果**: 問題の早期発見

### 4️⃣ ディスククリーンアップ
- **時間**: 15分
- **削減**: 3-4GB
- **対象**: 古いバックアップ + モデルファイル

---

## 📁 作成済みドキュメント

| ファイル | 内容 | 用途 |
|:---|:---|:---|
| **PAYOUT_DATA_COLLECTION_PROCEDURE.md** | 払戻データ収集手順書 | タスク1の詳細マニュアル |
| **LONG_RUNNING_TASKS_CHECKLIST.md** | 全タスク詳細 | 全9タスクの完全リスト |
| **24H_ABSENCE_TASK_SUMMARY.md** | このファイル | クイックリファレンス |

---

## ⚡ クイックスタート

### 開始時に実行（コピペ可）

```bash
# 1. ディレクトリ移動
cd C:\Users\bu158\Keiba_Shisaku20250928

# 2. バックアップ作成
copy netkeiba_data_2020_2024_enhanced.csv netkeiba_data_BACKUP_BEFORE_TASKS.csv

# 3. 払戻データ収集開始（バックグラウンド）
start /B py collect_payouts_2020_2026_FULL.py > task1_payout_collection.log 2>&1

# 4. データベース整合性チェック
py check_database_integrity.py > task3_integrity_check.log 2>&1

# 5. 欠損馬データ補完
py fix_missing_horse_data.py > task2_horse_data_fix.log 2>&1

# 6. 古いバックアップ削除（最新5個のみ保持）
powershell "Get-ChildItem -Filter 'netkeiba_data_*_backup_*.csv' | Sort-Object LastWriteTime -Descending | Select-Object -Skip 5 | Remove-Item -Verbose"

# 7. 古いモデル削除
del model_phase10_*.pkl
del model_phase11_*.pkl
del model_phase12_*.pkl
del model_win_prediction.pkl
del model_top3_prediction.pkl

# 8. __pycache__クリア
powershell "Get-ChildItem -Path . -Recurse -Directory -Filter '__pycache__' | Remove-Item -Recurse -Force"
```

---

## 🔍 進捗確認方法

### 払戻データ収集の進捗
```bash
# ログファイルの最新100行を表示
powershell "Get-Content task1_payout_collection.log -Tail 100"

# または
type task1_payout_collection.log
```

### 完了確認
```bash
# 払戻データ件数確認
py -c "import json; print(len(json.load(open('data/payout_data/payout_2020_2026_FULL.json', encoding='utf-8'))))"

# 期待値: 約21,000レース
```

---

## 📊 予想される結果

### データ収集
- **払戻データ**: 約21,000レース分
- **ファイルサイズ**: 15-20MB（JSON）

### Phase 13再検証
| 券種 | 理論値 | 実データ予想 |
|:---|---:|---:|
| 複勝 | 122.7% | 100-120%？ |
| ワイド | 75.3% | 70-90%？ |
| 馬連 | 77.9% | 75-95%？ |

### ディスク容量
- **削減**: 3.5-4.5GB
- **追加**: 0.1GB（払戻データ）
- **正味**: **-3.4GB削減**

---

## ✅ 完了後の確認事項

### 1. ファイル存在確認
```bash
# 払戻データ
dir data\payout_data\payout_2020_2026_FULL.json
dir data\payout_data\payout_cache_2020_2026_FULL.pkl

# バックアップ
dir netkeiba_data_BACKUP_BEFORE_TASKS.csv

# ログファイル
dir task*.log
```

### 2. データ件数確認
```python
import json
import pandas as pd

# 払戻データ
with open('data/payout_data/payout_2020_2026_FULL.json', encoding='utf-8') as f:
    payout_data = json.load(f)
print(f"払戻: {len(payout_data):,}レース")

# メインDB
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv')
print(f"DB: {len(df):,}レコード")

# 欠損チェック
missing_father = df['father'].isna().sum()
missing_mother = df['mother_father'].isna().sum()
print(f"Father欠損: {missing_father}件")
print(f"Mother欠損: {missing_mother}件")
```

### 3. 結果レポート確認
```bash
# 生成されるべきファイル
dir phase13_COMPLETE_VERIFICATION_RESULTS.md
dir phase13_exotic_bets_REAL_DATA_results.csv
```

---

## ⚠️ トラブル時の対処

### エラー: "ModuleNotFoundError"
```bash
# 必要なパッケージをインストール
pip install pandas numpy requests beautifulsoup4 lxml
```

### エラー: "PermissionError"
```bash
# ファイルが開かれている可能性
# Excelやエディタを閉じてから再実行
```

### エラー: "MemoryError"
```bash
# メモリ不足の可能性
# 他のアプリケーションを閉じる
# PCを再起動してから実行
```

### 払戻データ収集が途中で止まった
```bash
# スクリプトを再実行（自動で続きから開始）
py collect_payouts_2020_2026_FULL.py
```

---

## 📞 完了報告フォーマット

作業完了後、以下の情報を確認:

```
【実行結果サマリー】

✅ タスク1: 払戻データ収集
  - 取得レース数: XXX,XXX件
  - ファイルサイズ: XX.X MB
  - 実行時間: XX時間XX分

✅ タスク2: 欠損馬データ補完
  - 補完件数: XX件
  - 残存欠損: XX件

✅ タスク3: データベース整合性チェック
  - 重複レコード: XX件
  - データ異常: XX件

✅ タスク4-6: クリーンアップ
  - ディスク削減: X.X GB

【Phase 13再検証結果】
  - 複勝回収率: XXX.X%
  - ワイド回収率: XXX.X%
  - 馬連回収率: XXX.X%
  - サンプル数: XX,XXX レース

【問題・エラー】
  - なし / 以下の通り
```

---

## 🚀 次のステップ（Phase 14）

完了後の次の作業:

1. **GUI統合**: 払戻データ自動取得機能の追加
2. **実運用開始**: 15-20%確率帯の単勝＋複勝・ワイド
3. **モデル改善**: 実データフィードバックに基づく調整

---

**重要**: 全ての作業は`推奨の通り`で進める

**作成者**: Claude Opus 4.6
**最終更新**: 2026年2月21日
