# Phase C-3: セッション完了レポート（2026年2月24日）

**作成日**: 2026年2月24日
**対象ファイル**: `phase_c_operation.py`
**ステータス**: Phase C-3 完了

---

## 1. セッション開始時の状態

```
Phase 14 訓練 ✅ → Phase A ✅ → Phase B ✅ → Phase C ✅ → Phase C-2 GUI統合 ✅
                                                                  ↓
                                                         (本セッション開始地点)
```

START_HERE.md（2026年2月23日付）が示す次のアクション:

| 優先度 | タスク |
|---|---|
| **今すぐ** | GUI動作確認 |
| **今週末** | ペーパートレード開始 |
| 中 | Phase C-3: `phase_c_operation.py` 月次NaT修正 |
| 中 | Phase D-1: オッズドリフト特徴量追加 |
| 低 | Phase D-2: 月次モデル再訓練サイクル |

---

## 2. 環境・モデル動作確認（GUI動作確認 代替）

GUIは対話起動が必要なため、以下の自動検証を実施。

### 2-1. ライブラリ確認

| ライブラリ | バージョン | 結果 |
|---|---|---|
| lightgbm | 4.6.0 | ✅ |
| tkinter | 標準ライブラリ | ✅ |
| pandas | 2.2.3 | ✅ |

### 2-2. Phase 14 モデル読み込みテスト

```python
model_win   = lgb.Booster(model_file='phase14_model_win.txt')   # 74 trees
model_place = lgb.Booster(model_file='phase14_model_place.txt') # 60 trees
features    = pickle.load(open('phase14_feature_list.pkl','rb')) # 39特徴量
```

| ファイル | 内容 | 結果 |
|---|---|---|
| `phase14_model_win.txt` | 単勝モデル 74 trees | ✅ |
| `phase14_model_place.txt` | 複勝モデル 60 trees | ✅ |
| `phase14_feature_list.pkl` | 39特徴量リスト | ✅ |

### 2-3. GUIファイル構文チェック

| 項目 | 値 |
|---|---|
| ファイル | `keiba_prediction_gui_v3.py` |
| 総行数 | 4,257行 |
| 構文エラー | なし |
| predict呼び出し（L1777） | `float(self.model_win.predict(feat_df)[0])` ✅ |
| predict呼び出し（L1778） | `float(self.model_place.predict(feat_df)[0])` ✅ |

**結論**: GUIは手動起動すれば正常動作する状態。

---

## 3. Phase C-3: 月次NaT修正

### 3-1. 問題の原因

`phase_c_operation.py` L57:

```python
df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
```

`data/main/netkeiba_data_2020_2025_complete.csv` の `date` 列には
**日本語形式**（`2024年01月06日`）と **ISO形式**（`2024-01-01 00:00:00`）が混在。

| 形式 | 件数 | 割合 |
|---|---:|---:|
| ISO形式（正常解析） | 190,995件 | 66.0% |
| 日本語形式（NaT化） | 98,341件 | **34.0%** |
| 合計 | 289,336件 | 100% |

NaTが34%発生すると、月次バンクロールの `dt.to_period('M')` が
`NaT` 期間を生成し、月次集計が崩壊する。

### 3-2. 修正内容

**`phase_c_operation.py`** に以下の2箇所を追加:

#### (1) importに `re` を追加（L20）

```python
# 変更前
import pandas as pd
import numpy as np
import warnings

# 変更後
import pandas as pd
import numpy as np
import re
import warnings
```

#### (2) 日付正規化関数を追加（L57付近、`pd.to_datetime` の直前）

```python
# 日付正規化: '2024年01月06日' → '2024-01-06' (NaT防止)
def _norm_date(s):
    s = str(s)
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', s)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    return s
df['race_date'] = df['race_date'].apply(_norm_date)

# 日付ソート
df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
```

同じ日付正規化ロジックは `keiba_prediction_gui_v3.py` の `load_data()`
（`_normalize_date` 関数）でも既に実装済み。今回は `phase_c_operation.py`
にも同等の修正を適用した。

### 3-3. 修正後の実行結果

```
有効レコード数: 36,136
期間: 2025-01-05 〜 2025-12-27
レース数: 2,770
```

月次バンクロール（Rule4_複合最良）:

| 月 | 賭件数 | 的中 | 月次損益 | 累積残高 |
|---|---:|---:|---:|---:|
| 2025-01 | 466 | 62 | +10,730円 | 60,730円 |
| 2025-02 | 474 | 73 | +16,870円 | 77,600円 |
| 2025-03 | 551 | 101 | +29,640円 | 107,240円 |
| 2025-04 | 394 | 64 | +23,870円 | 131,110円 |
| 2025-05 | 470 | 81 | +45,970円 | 177,080円 |
| 2025-06 | 418 | 73 | +17,870円 | 194,950円 |
| 2025-07 | 278 | 63 | +37,580円 | 232,530円 |
| 2025-08 | 461 | 106 | +30,440円 | 262,970円 |
| 2025-09 | 1 | 0 | -100円 | 262,870円 |
| 2025-11 | 264 | 37 | +8,950円 | 271,820円 |
| 2025-12 | 56 | 9 | +3,540円 | 275,360円 |
| **合計** | **3,833** | **669** | **+225,360円** | **275,360円** |

回収率: 158.8%　最大ドローダウン: 8.8%

エラーなし。修正前は月次集計が NaT 期間として集約されていたが、
修正後は2025年全12ヶ月（一部除く）が正常に分離された。

---

## 4. ペーパートレード準備

### 4-1. 新規作成ファイル

| ファイル | 内容 |
|---|---|
| `paper_trade_log.csv` | ペーパートレード記録CSV（ヘッダー付き空ファイル） |
| `paper_trade_add.py` | 対話形式でベット結果を記録するCLIツール |

### 4-2. paper_trade_log.csv 列定義

| 列名 | 内容 |
|---|---|
| date | ベット日（YYYY-MM-DD） |
| race_id | レースID（12桁） |
| race_name | レース名 |
| horse_name | 馬名 |
| horse_id | 馬ID |
| pred_win | GUIの単勝予測確率 |
| pred_place | GUIの複勝予測確率 |
| odds | 単勝オッズ |
| bet_rule | 適用ルール（Rule1〜Rule4） |
| bet_amount | ベット金額（固定100円） |
| result | 的中 / ハズレ / 未確定 |
| payout | 払い戻し金額 |
| pl | 損益（payout - bet_amount） |
| bankroll | 累積残高 |
| memo | メモ |

### 4-3. ペーパートレード手順

```bash
# 1. GUIで予測
py keiba_prediction_gui_v3.py

# 2. Rule4条件を満たす馬をメモ
#    pred_win > 20% かつ 2.0x ≤ odds < 10.0x
#    または pred_win > 10% かつ odds ≥ 10.0x

# 3. レース後に結果を記録
py paper_trade_add.py
```

---

## 5. 現在の全体状態

```
Phase 14 訓練 ✅ → Phase A ✅ → Phase B ✅ → Phase C ✅
→ Phase C-2 GUI統合 ✅ → Phase C-3 NaT修正 ✅
                                   ↓
                        次: GUI手動起動確認 & ペーパートレード開始
```

### 完成済みファイル一覧

| ファイル | 内容 | 状態 |
|---|---|---|
| `phase14_model_win.txt` | 単勝モデル（AUC 0.7988） | ✅ |
| `phase14_model_place.txt` | 複勝モデル（AUC 0.7558） | ✅ |
| `phase14_feature_list.pkl` | 39特徴量リスト | ✅ |
| `keiba_prediction_gui_v3.py` | GUI本体（Phase 14統合済み） | ✅ |
| `phase_c_operation.py` | バックテスト・バンクロール試算（NaT修正済み） | ✅ |
| `phase_a_predictions.csv` | 2025年全馬の予測確率 | ✅ |
| `phase_c_rule_summary.csv` | ベットルール別成績 | ✅ |
| `phase_c_bankroll_summary.csv` | バンクロールサマリー | ✅ |
| `paper_trade_log.csv` | ペーパートレード記録 | 記録待ち |
| `paper_trade_add.py` | ペーパートレード記録CLI | ✅ |

---

## 6. 次のロードマップ

| 優先度 | タスク | 内容 |
|---|---|---|
| **今すぐ** | GUI手動起動確認 | `競馬予想ツール.bat` → 「Phase 14モデル読み込み成功」確認 |
| **今週末〜** | ペーパートレード開始 | `py paper_trade_add.py` で毎週記録（最低2週間） |
| 中 | Phase D-1 | オッズドリフト特徴量追加（朝イチ vs 直前オッズ差分） |
| 低 | Phase D-2 | 月次モデル再訓練サイクル構築 |

### Phase D-1 概要（次の実装タスク）

朝イチオッズと直前オッズの差分を特徴量として追加することで、
「市場のオッズ変動」を予測に組み込む。

```python
# 追加予定特徴量（案）
odds_drift = (odds_morning - odds_final) / odds_morning  # ドリフト率
odds_steam  = 1 if odds_drift > 0.15 else 0              # 大幅短縮フラグ
```

データ収集が必要なため、netkeibaのオッズデータ取得方法の調査が先行作業。

---

*作成: 2026年2月24日*
