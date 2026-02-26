# odds_collector — オッズ時系列収集システム

**作成日**: 2026年2月24日
**目的**: Phase D-1（オッズドリフト特徴量）の事前データ収集

---

## ファイル構成

```
odds_collector/
  ├── schedule_fetch.py    # 当日レーススケジュール取得（07:00実行）
  ├── odds_snapshot.py     # オッズスナップショット取得
  ├── odds_timeseries.db   # SQLiteデータベース（自動生成）
  └── README.md            # 本ファイル
```

## データベース構造

### race_schedule テーブル

| 列 | 型 | 内容 |
|---|---|---|
| race_date | TEXT | 開催日（YYYYMMDD） |
| race_id | TEXT | レースID（12桁） |
| race_name | TEXT | レース名 |
| start_time | TEXT | 発走時刻（HH:MM） |
| venue | TEXT | 開催場（中山・東京など） |
| fetched_at | TEXT | 取得日時 |

### odds_snapshots テーブル

| 列 | 型 | 内容 |
|---|---|---|
| race_id | TEXT | レースID |
| horse_id | TEXT | 馬ID |
| horse_name | TEXT | 馬名 |
| timing | TEXT | 取得タイミング（30min_before / 5min_before / manual） |
| odds_win | REAL | 単勝オッズ |
| recorded_at | TEXT | 記録日時 |

---

## 毎週末の運用手順

### 当日朝（07:00）

```bash
py odds_collector/schedule_fetch.py
```

→ 当日のレース一覧をDBに保存

### 各レース発走30分前

```bash
py odds_collector/odds_snapshot.py --timing 30min_before
```

### 各レース発走5分前

```bash
py odds_collector/odds_snapshot.py --timing 5min_before
```

### 特定レースのみ取得する場合

```bash
py odds_collector/odds_snapshot.py --race_id 202601050801 --timing manual
```

---

## Windowsタスクスケジューラ設定（土日自動実行）

以下の設定で `schedule_fetch.py` を自動実行できる：

1. タスクスケジューラを開く（`taskschd.msc`）
2. 「タスクの作成」→「トリガー」→「毎週：土曜・日曜 07:00」
3. 「操作」→「プログラムの開始」
   - プログラム: `py`
   - 引数: `C:\Users\bu158\Keiba_Shisaku20250928\odds_collector\schedule_fetch.py`
   - 開始: `C:\Users\bu158\Keiba_Shisaku20250928`

---

## データ活用方法（Phase D-1）

3〜6ヶ月蓄積後に以下の特徴量を計算してモデル再訓練に使用：

```python
import sqlite3, pandas as pd

conn = sqlite3.connect('odds_collector/odds_timeseries.db')

# 30分前と確定オッズの差分を計算
df = pd.read_sql('''
    SELECT a.race_id, a.horse_id, a.horse_name,
           a.odds_win AS odds_30min,
           b.odds_win AS odds_final
    FROM odds_snapshots a
    JOIN odds_snapshots b
      ON a.race_id = b.race_id AND a.horse_id = b.horse_id
    WHERE a.timing = '30min_before'
      AND b.timing = '5min_before'
''', conn)

df['odds_drift']  = (df['odds_30min'] - df['odds_final']) / df['odds_30min']
df['odds_steam']  = (df['odds_drift'] > 0.15).astype(int)  # 15%以上短縮
df['odds_drifted'] = (df['odds_drift'] < -0.10).astype(int)  # 10%以上流れた
```

---

## 注意事項

- **レート制限**: 1リクエストごとに 2.5秒 sleep（Gemini推奨 2〜3秒）
- **利用規約**: netkeibaの利用規約を遵守すること
- **HTMLの変更**: netkeiba のDOM構造が変わった場合はパーサーの修正が必要
- **バックアップ不要**: `odds_timeseries.db` は再取得可能なため、主データCSVのようなバックアップ増殖は不要
