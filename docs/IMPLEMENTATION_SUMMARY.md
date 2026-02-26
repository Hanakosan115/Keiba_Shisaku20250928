# ハイブリッド方式実装完了レポート

## 🎉 実装完了内容

### 1. ランダムUser-Agent選択機能 ✅

**実装箇所**: `update_from_list.py` 38-56行目

**機能**:
- 5種類のUser-Agent（Chrome 119/120、Firefox 121、Safari 17）
- リクエストごとにランダム選択
- ブロック回避・自然なアクセスパターン

**コード例**:
```python
self.USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15',
]
```

---

### 2. カレンダーベース収集機能（B案） ✅

**実装箇所**: `update_from_list.py` 676-905行目

**新メソッド**:

#### `get_kaisai_dates(year, month)`
- カレンダーページから開催日リストを取得
- URL: `https://race.netkeiba.com/top/calendar.html?year={year}&month={month}`
- セレクタ: `.Calendar_Table .Week td > a[href*="kaisai_date="]`
- 戻り値: `['20250601', '20250602', ...]`

#### `get_race_ids_for_date(date_str)`
- 指定日のレースIDリストを取得
- URL: `https://race.netkeiba.com/top/race_list.html?kaisai_date={date_str}`
- セレクタ: `.RaceList_DataItem > a:first-of-type`
- 戻り値: `['202506010101', '202506010102', ...]`

#### `collect_from_calendar(start_year, start_month, end_year, end_month, collect_horse_details=True)`
- 期間指定でカレンダーから自動収集
- 開催日取得 → レースID取得 → データ収集の3段階
- 馬統計情報の収集可否を選択可能

#### `_collect_races(race_ids, collect_horse_details=True)`
- 内部用共通収集メソッド
- A案・B案の両方から呼び出される
- 重複チェック、100件ごと保存、進捗表示

---

### 3. ハイブリッドmain()関数 ✅

**実装箇所**: `update_from_list.py` 1077-1175行目

**メニュー構成**:

```
============================================================
 NetKeibaデータ収集ツール（ハイブリッド版）
============================================================

収集方式を選択してください：

  [1] A案: レースIDリストから収集（高速・安定）
      → race_ids.txt から読み込み

  [2] B案: カレンダーから期間指定で収集（自動・柔軟）
      → 年月を指定して自動取得

  [3] 11-12月の新規レースを自動収集（2025年）
      → カレンダー方式で最新データ取得

  [0] 終了
```

**各オプション詳細**:

- **オプション1（A案）**:
  - ファイル名指定（デフォルト: race_ids.txt）
  - 馬統計収集の可否選択
  - 高速・安定した収集

- **オプション2（B案）**:
  - 開始年月・終了年月を入力
  - 自動的にレースIDを取得
  - 完全自動化

- **オプション3（専用）**:
  - 2025年11-12月固定
  - ワンクリックで最新データ取得
  - 今回の目的に最適

---

## 📊 比較表（再掲）

| 項目 | A案（リスト方式） | B案（カレンダー方式） |
|------|------------------|---------------------|
| **処理速度** | ⭐⭐⭐⭐⭐ 速い | ⭐⭐⭐ やや遅い |
| **自動化** | ⭐⭐ 手動リスト必要 | ⭐⭐⭐⭐⭐ 完全自動 |
| **正確性** | ⭐⭐⭐⭐ 高い | ⭐⭐⭐⭐⭐ 最高 |
| **保守性** | ⭐⭐⭐ 普通 | ⭐⭐⭐⭐⭐ 優秀 |
| **新規レース対応** | ⭐ 不可 | ⭐⭐⭐⭐⭐ 完全対応 |

---

## 🚀 使用方法

### ケース1: 既存2025年データに統計追加（A案）

```bash
cd Keiba_Shisaku20250928
py update_from_list.py
```

1. メニューで `1` を選択
2. ファイル名: `existing_2025_race_ids.txt` と入力
3. 馬統計収集: `y` を選択
4. 3,263レースの統計情報が追加される

**メリット**: 高速（数時間）、安定

---

### ケース2: 11-12月の新規レース収集（B案）

```bash
cd Keiba_Shisaku20250928
py update_from_list.py
```

1. メニューで `3` を選択
2. 実行確認: `y` を選択
3. 馬統計収集: `y` を選択
4. 自動的にカレンダーから収集

**メリット**: 完全自動、存在しないレースIDへのアクセス回避

---

### ケース3: カスタム期間収集（B案）

```bash
cd Keiba_Shisaku20250928
py update_from_list.py
```

1. メニューで `2` を選択
2. 開始年: `2025`
3. 開始月: `6`
4. 終了年: `2025`
5. 終了月: `10`
6. 馬統計収集: `y` を選択

**メリット**: 柔軟な期間指定、過去データ補完にも対応

---

## 📁 ファイル構成

```
Keiba_Shisaku20250928/
├── update_from_list.py              ← 拡張版（ハイブリッド方式）
├── netkeiba_data_2020_2024_enhanced.csv  ← メインDB（統計追加）
├── horse_past_results.csv           ← 馬過去戦績詳細
├── existing_2025_race_ids.txt       ← 既存2025年レースID（3,263件）
├── race_ids.txt                     ← 旧リスト（使用しない）
├── approach_comparison.md           ← 詳細比較分析
└── IMPLEMENTATION_SUMMARY.md        ← 本ドキュメント
```

---

## 🔧 技術詳細

### User-Agent管理

- **切り替えタイミング**: 各HTTPリクエスト前
- **メソッド**: `_update_user_agent()`
- **効果**: ブロックリスク低減、サーバー負荷分散模倣

### データフロー（B案）

```
カレンダーページ
    ↓ get_kaisai_dates()
開催日リスト ['20251101', '20251102', ...]
    ↓ get_race_ids_for_date()
レースIDリスト ['202511010101', '202511010102', ...]
    ↓ _collect_races()
レース詳細スクレイピング
    ↓ scrape_race_result()
馬詳細・統計計算
    ↓ _save_data()
CSV保存（100件ごと）
```

### エラーハンドリング

- タイムアウト処理
- HTTPエラー処理
- 空レース（開催なし）の検出
- セレクタ変更への対応

---

## ⚠️ 重要な変更点

### 1. `update_from_file()` は従来通り動作

- 既存のA案コードも保持
- 後方互換性あり
- メニューから選択可能

### 2. `_collect_races()` の共通化

- A案・B案の両方から呼び出される内部メソッド
- 重複処理ロジックを統一
- 保守性向上

### 3. 統計収集の可否選択

- 全てのメソッドで `collect_horse_details` パラメータ対応
- `y`/`n` で選択可能
- デフォルト: `y`（収集する）

---

## 📈 推定処理時間

### A案（既存2025年データ、3,263レース）
- 馬統計あり: **4-6時間**
- 馬統計なし: **1-2時間**

### B案（11-12月の新規レース、推定200-300レース）
- 馬統計あり: **1-2時間**
- 馬統計なし: **30-60分**

**注**: 1レースあたり約30-60秒（馬詳細16頭×アクセス時間）

---

## 🎯 今後の運用推奨

### 定期実行（毎週月曜）
```python
updater = ListBasedUpdater()
# 直近1週間分を自動収集
updater.collect_from_calendar(2025, 12, 2025, 12, collect_horse_details=True)
```

### 年次更新（1月）
```python
# 前年全体を再収集して統計更新
updater.collect_from_calendar(2024, 1, 2024, 12, collect_horse_details=True)
```

### 過去データ補完
```python
# 空白期間を埋める
updater.collect_from_calendar(2020, 6, 2020, 8, collect_horse_details=True)
```

---

## 🔍 テスト方法

### 小規模テスト（推奨）

```bash
cd Keiba_Shisaku20250928
py update_from_list.py
```

1. メニューで `2` を選択
2. 開始年: `2025`
3. 開始月: `11`
4. 終了年: `2025`
5. 終了月: `11`（11月のみ）
6. 馬統計収集: `y`

**期待結果**:
- 開催日が表示される
- 各日のレース数が表示される
- 重複チェックが動作
- データが正常に保存される

---

## 🐛 トラブルシューティング

### 問題1: カレンダーページが取得できない

**原因**: セレクタ変更、ネットワークエラー

**対処**:
```python
# update_from_list.py の 704行目付近
selector = '.Calendar_Table .Week td > a[href*="kaisai_date="]'
# ↑ NetKeiba側の変更に応じて調整
```

### 問題2: レースIDが取得できない

**原因**: レース一覧ページのセレクタ変更

**対処**:
```python
# update_from_list.py の 748行目付近
selector = '.RaceList_DataItem > a:first-of-type'
# ↑ 変更された場合は調整
```

### 問題3: User-Agentでブロックされる

**対処**:
- `USER_AGENTS` リストに最新ブラウザを追加
- `time.sleep()` の値を増やす（1.0 → 2.0秒など）

---

## ✨ まとめ

### 達成したこと

1. ✅ ランダムUser-Agent選択（ブロック回避）
2. ✅ カレンダーベース自動収集（B案）
3. ✅ リストベース高速収集（A案）の維持
4. ✅ ハイブリッド方式の統合
5. ✅ 柔軟なメニューシステム
6. ✅ 今後10年使える設計

### 次のステップ

1. **小規模テスト**: 11月のみで動作確認
2. **本番実行**: 11-12月の全データ収集
3. **既存データ更新**: existing_2025_race_ids.txt で統計追加
4. **定期実行**: 週次スケジュール化

---

**実装日**: 2025-12-10
**バージョン**: v2.0 (Hybrid)
**ファイル**: update_from_list.py (1,176行)
