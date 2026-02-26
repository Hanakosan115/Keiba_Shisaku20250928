# データマージシステム - 完全ガイド

## 解決した問題

✅ **新しいデータを分析してもマージされない問題を解決しました**

以前の問題:
- 新規データ（202511.csv）を取得しても、訓練スクリプトは古いデータ（202508.csv）を参照していた
- 手動でファイルパスを更新する必要があった
- どのファイルが最新か分からなくなっていた

新しいシステム:
- ✅ 全スクリプトが`data_config.py`を使用して**自動的に最新データを参照**
- ✅ 新規データ追加時は`data_config.py`を更新するだけで全スクリプトに反映
- ✅ バックアップ自動作成で安全性確保

---

## 現在のデータ状況

### マージ済み最新データ（使用中）

| ファイル | レコード数 | レース数 | 期間 |
|----------|-----------|---------|------|
| **netkeiba_data_combined_202001_202511_merged.csv** | **280,699件** | **20,337レース** | 2020-01 ～ 2025-08 |
| **netkeiba_data_payouts_202001_202511_merged.json** | **20,289レース** | - | 配当データ |

### 追加されたデータ

- **新規レコード**: 1,638件
- **新規レース**: 120レース
- **期間**: 2024年9月～11月

---

## ファイル構成

### 🔧 設定ファイル（重要！）

**`data_config.py`** - データパスの一元管理
```python
# メインデータファイル（常に最新）
MAIN_CSV = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_combined_202001_202511_merged.csv"
MAIN_JSON = r"C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\netkeiba_data_payouts_202001_202511_merged.json"
```

### 📊 更新済みスクリプト

以下のスクリプトは全て`data_config.py`を使用するように更新されました：

1. **訓練スクリプト**
   - `train_with_best_params.py` - ベースラインモデル（22次元）
   - `train_with_running_style_optimized.py` - 脚質モデル（28次元） ⭐最優秀
   - `train_advanced_model.py` - 次世代モデル（42次元）

2. **バックテストスクリプト**
   - `backtest_tuned_model.py` - ベースラインテスト
   - `backtest_running_style_optimized.py` - 脚質モデルテスト
   - `backtest_advanced_model_optimized.py` - 次世代モデルテスト

### 🛠️ ユーティリティ

- `auto_merge_system.py` - 自動マージツール（将来用）
- `update_all_scripts_to_use_config.py` - スクリプト一括更新ツール
- `check_merged_data.py` - データ内容確認ツール

---

## 使い方

### 日常的な使用（訓練・バックテスト）

**何も変更する必要はありません！**

いつも通りスクリプトを実行するだけで、自動的に最新データを使用します：

```bash
# 最優秀モデル（脚質モデル）の訓練
python train_with_running_style_optimized.py

# バックテスト
python backtest_running_style_optimized.py
```

### 新しいデータを追加する場合

#### ステップ1: 新規データファイルを配置

新しいデータを取得したら、以下のディレクトリに配置：
```
C:\Users\bu158\HorseRacingAnalyzer\data\
  ├── netkeiba_data_combined_202001_202512.csv  ← 新規
  └── netkeiba_data_payouts_202001_202512.json ← 新規
```

#### ステップ2: 既存の merge_race_data.py を実行

```bash
python merge_race_data.py
```

これで新しいマージ済みファイルが作成されます：
- `netkeiba_data_combined_202001_202512_merged.csv`
- `netkeiba_data_payouts_202001_202512_merged.json`

#### ステップ3: data_config.py を更新

`data_config.py`を開いて、パスを新しいファイルに変更：

```python
# 変更前
MAIN_CSV = r"...\netkeiba_data_combined_202001_202511_merged.csv"

# 変更後
MAIN_CSV = r"...\netkeiba_data_combined_202001_202512_merged.csv"
```

#### ステップ4: 完了！

これで全スクリプトが自動的に新しいデータを使用します。
スクリプト自体を変更する必要は**一切ありません**。

---

## システムの仕組み

### Before（旧システム）

```
train_with_running_style_optimized.py
  ↓ ハードコードされたパス
  "C:\...\netkeiba_data_combined_202001_202508.csv"  ← 古いデータ
```

**問題点:**
- 新データ（202511）があっても使われない
- 全スクリプトのパスを手動で変更する必要がある
- どれが最新か分からない

### After（新システム）

```
data_config.py
  └─ MAIN_CSV = "...\netkeiba_data_combined_202001_202511_merged.csv"
       ↑
       │ インポート
       │
  ┌────┴────┬────────┬───────────┐
  │         │        │           │
train_... backtest... train_... (全スクリプト)
```

**メリット:**
- ✅ 1ファイルの変更で全スクリプトに反映
- ✅ 最新データが明確
- ✅ 保守が簡単

---

## バックアップ

自動マージシステムは変更前にバックアップを作成します：

```
C:\Users\bu158\HorseRacingAnalyzer\data\一旦避難用\backups\
  ├── netkeiba_data_combined_latest_backup_20251118_002533.csv
  └── netkeiba_data_payouts_latest_backup_20251118_002533.json
```

---

## トラブルシューティング

### Q: スクリプト実行時に "ModuleNotFoundError: No module named 'data_config'" エラーが出る

**A:** `data_config.py`が存在することを確認してください。
```bash
dir C:\Users\bu158\Keiba_Shisaku20250928\data_config.py
```

### Q: 古いデータで訓練されてしまう

**A:** `data_config.py`のパスを確認してください。最新のマージ済みファイルを指していますか？

### Q: マージしたのに新しいデータが反映されない

**A:** 以下を確認：
1. マージは正常に完了しましたか？（ファイルサイズを確認）
2. `data_config.py`のパスを更新しましたか？
3. Python を再起動しましたか？（古い import がキャッシュされている可能性）

---

## 次のステップ

### 推奨アクション

1. **最優秀モデル（脚質モデル）を新データで再訓練**
   ```bash
   python train_with_running_style_optimized.py
   ```
   期待される効果：
   - 2024年9-11月の新データで精度向上
   - 回収率 173.7% → さらに向上の可能性

2. **新モデルでバックテスト**
   ```bash
   python backtest_running_style_optimized.py
   ```

3. **モデル比較レポートの更新**
   新データでの性能を `model_comparison_report.md` に追記

### 今後の拡張

- Webスクレイピングでリアルタイムデータ取得
- 調教タイム・馬場指数の追加
- 自動更新パイプラインの構築

---

## まとめ

✅ **問題解決**: 新データが自動的に全スクリプトで使われるようになりました

✅ **シンプル化**: `data_config.py` 1ファイルで全管理

✅ **将来対応**: 次回からは `merge_race_data.py` → `data_config.py` 更新だけでOK

---

**最終更新**: 2025-11-18
**システムステータス**: ✅ 運用可能
