# データ収集ガイド

## 🖥️ GUI（Streamlitダッシュボード）

### 起動方法
```bash
cd Keiba_Shisaku20250928
py -m streamlit run dashboard.py
```

ブラウザで http://localhost:8501 にアクセス

### 機能
1. **データ収集** - 年月指定で収集設定・コマンド生成
2. **進捗モニター** - リアルタイム進捗確認
3. **データ概要** - データベース統計・カバー率
4. **統計表示** - 期間別フィルター・分析
5. **ログビューア** - 処理履歴確認
6. **設定** - ファイル確認・自動更新

## 🎯 期間指定データ収集

### 基本コマンド

```bash
# 2025年2月のデータ収集
py collect_by_period.py --year 2025 --month 2

# 2025年全月のデータ収集
py collect_by_period.py --year 2025 --month all

# 2024年1月～6月のデータ収集
py collect_by_period.py --year 2024 --month 1-6

# 強制更新モード（既存データも再収集）
py collect_by_period.py --year 2025 --month 2 --force
```

### オプション

| オプション | 説明 | 例 |
|-----------|------|-----|
| `--year` | 収集年（必須） | `--year 2025` |
| `--month` | 収集月 | `--month 2`<br>`--month all`<br>`--month 1-6` |
| `--force` | 強制更新 | `--force` |
| `--stats-only` | 統計のみ | `--stats-only` |

## 📅 推奨収集順序

### 2025年データ（優先度：高）

```bash
# 2月（統計データ追加）
py collect_by_period.py --year 2025 --month 2

# 3月
py collect_by_period.py --year 2025 --month 3

# 4月
py collect_by_period.py --year 2025 --month 4

# 5月～8月
py collect_by_period.py --year 2025 --month 5-8
```

### 2024年以前のデータ

```bash
# 2024年全年
py collect_by_period.py --year 2024 --month all

# 2023年全年
py collect_by_period.py --year 2023 --month all

# 2022年全年
py collect_by_period.py --year 2022 --month all
```

## ⏱️ 推定所要時間

| 期間 | レース数（推定） | 所要時間 |
|------|----------------|----------|
| 1ヶ月 | 240レース | 8-15時間 |
| 1年 | 3,000レース | 100-180時間 |

## 📊 収集状況の確認

### GUIで確認
1. Streamlitダッシュボード起動
2. 「データ概要」メニュー
3. 年別・月別カバー率を確認

### コマンドで確認
```bash
py -c "import pandas as pd; df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv'); df['date'] = pd.to_datetime(df['date'], errors='coerce'); print(df.groupby([df['date'].dt.year, df['date'].dt.month])['race_id'].nunique())"
```

## 🔄 中断・再開

### 中断方法
- `Ctrl + C` でプロセスを中断
- 進捗は10レースごとに自動保存

### 再開方法
- 同じコマンドを再実行
- 進捗ファイル（`collection_progress.json`）から自動再開
- 続きから処理が開始されます

## ⚠️ 注意事項

1. **レート制限**
   - 自動でランダム遅延（2-5秒/馬）
   - バッチクールダウン（30-60秒/10馬）
   - サーバー負荷軽減のため必須

2. **バックアップ**
   - 10レースごとに自動バックアップ生成
   - `netkeiba_data_2020_2024_enhanced_backup_YYYYMMDD_HHMMSS.csv`

3. **ディスク容量**
   - 1年分約500MB～1GB必要
   - 十分な空き容量を確保

4. **実行環境**
   - 安定したネットワーク環境推奨
   - 長時間実行のため、PCをスリープさせない設定に

## 🎉 収集完了後

1. **データ確認**
   - GUIの「データ概要」で統計確認
   - カバー率95%以上が目標

2. **機械学習モデル訓練**
   - 十分なデータが揃ったら予測モデル構築開始
   - `train_advanced_model.py` など使用

3. **次の期間へ**
   - 収集完了した期間から次へ進む
   - 優先度: 2025年 > 2024年 > 2023年以前

---

**作成日**: 2025-12-11
**バージョン**: 1.0
