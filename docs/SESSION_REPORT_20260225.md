# セッションレポート — 2026年2月25日

**ステータス**: 実運用ツール全整備完了
**次のアクション**: 今週末からペーパートレード開始

---

## このセッションで実施したこと

### 1. Phase C-3 — NaT修正（`phase_c_operation.py`）

**問題**: `race_date` 列に日本語形式（`2024年01月06日`）の日付が34%混在しており、`pd.to_datetime()` がNaTを返してバンクロール月次集計が全て0になっていた。

**修正内容**:
```python
import re

def _norm_date(s):
    s = str(s)
    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', s)
    if m:
        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
    return s

df['race_date'] = df['race_date'].apply(_norm_date)
df['race_date'] = pd.to_datetime(df['race_date'], errors='coerce')
```

**結果**: 全12ヶ月のバンクロール推移が正常出力されるようになった。

---

### 2. GUIヘッドレス検証（`keiba_prediction_gui_v3.py`）

Tkウィンドウを使わずにGUI起動ステップをPython直接実行で再現し、全項目を確認。

| ステップ | 結果 |
|---|---|
| Phase 14モデル読込 | ✅ WIN(74本)/PLACE(60本)木、39特徴量 |
| データ読込 | ✅ 289,336件、NaT=0件 |
| 統計計算 | ✅ sire_stats/tj_stats正常 |
| サンプル予測 | ✅ 16頭の予測確率算出、1位が最高確率 |

- L1777–1778の `predict()` 呼び出しが正しいことも確認

---

### 3. pandas FutureWarning修正

**対象ファイル**:
- `keiba_prediction_gui_v3.py` L152
- `backtest_full_2020_2025.py` L65

**修正内容**:
```python
# Before（pandas 3.0で廃止予定）
df['training_rank_numeric'].fillna(3, inplace=True)

# After
df['training_rank_numeric'] = df['training_rank_numeric'].fillna(3)
```

---

### 4. paper_trade_log.csv — 列の整備

最終ヘッダー（確定版）:
```
date,race_id,race_name,horse_name,horse_id,bet_type,pred_win,pred_place,
pred_win_calibrated,odds,odds_recorded_time,bet_rule,bet_amount,
kelly_theoretical,result,payout,pl,bankroll,memo
```

追加した列:
- `bet_type` — win / place / both
- `pred_win_calibrated` — Isotonic Regression補正後確率（省略可）
- `kelly_theoretical` — Kelly理論値ベット額（参考値）
- `odds_recorded_time` — オッズ取得時刻（Geminiフィードバック対応）

---

### 5. paper_trade_add.py — 全面リライト（v2）

Kelly計算ロジック修正:
```python
def kelly_bet(p, odds, bankroll=INITIAL_BANKROLL, fraction=KELLY_FRACTION, max_bet=KELLY_MAX):
    b = odds - 1
    if b <= 0 or p <= 0: return 0
    f = (p * b - (1 - p)) / b      # フルKelly
    if f <= 0: return 0
    raw = bankroll * f * fraction   # バンクロール基準（50,000円 × f × 0.25）
    return min(max_bet, max(100, round(raw / 100) * 100))
```

- バンクロール基準に修正（旧: BET_UNIT=100円基準 → 7円になり0に丸められていたバグを修正）
- 上限500円、100円単位
- 入力項目: 日付 / レースID / 馬名 / bet_type / pred_win / pred_place / pred_win_calibrated / odds / odds_recorded_time / ルール / 結果

---

### 6. バックアップ削除（Task D）

| 項目 | 数値 |
|---|---|
| 削除前 | 114ファイル、13.52 GB |
| 削除後（残存） | 5ファイル、584 MB |
| 解放容量 | **109ファイル、12.95 GB** |

**残存5ファイルの選定基準**:
- 特別な名前のついたファイル（GUIリリース等）
- 各月の最後のバックアップ
- 最新のバックアップ

---

### 7. odds_collector/ — オッズ時系列収集システム（Task E）

**作成ファイル一覧**:

```
odds_collector/
  ├── schedule_fetch.py       # 当日レーススケジュール取得（07:00実行）
  ├── odds_snapshot.py        # オッズスナップショット取得
  ├── odds_timeseries.db      # SQLiteデータベース（初期化済み）
  ├── README.md               # システム概要・データ活用方法
  └── TASK_SCHEDULER_SETUP.md # Windowsタスクスケジューラ設定手順
```

**データベース構造**:
```sql
CREATE TABLE race_schedule (
    race_date TEXT, race_id TEXT, race_name TEXT,
    start_time TEXT, venue TEXT, fetched_at TEXT,
    PRIMARY KEY (race_date, race_id)
)
CREATE TABLE odds_snapshots (
    race_id TEXT, horse_id TEXT, horse_name TEXT,
    timing TEXT, odds_win REAL, recorded_at TEXT,
    PRIMARY KEY (race_id, horse_id, timing, recorded_at)
)
```

**設定タスク（土日自動実行）**:
| タスク名 | 時刻 | スクリプト |
|---|---|---|
| keiba_schedule_fetch | 土日 07:00 | `schedule_fetch.py` |
| keiba_odds_morning | 土日 09:00 | `odds_snapshot.py --timing 30min_before` |
| keiba_odds_afternoon | 土日 14:30 | `odds_snapshot.py --timing 30min_before` |

---

### 8. paper_trade_review.py — 月次レビュースクリプト（Task G）

**機能**:
1. **月次損益サマリー** — 月別件数・的中率・損益・残高・回収率
2. **ルール別・馬券種別集計** — bet_rule / bet_type ごとのROI・損益
3. **GO/NO-GO判定（5基準）**
4. **PSIドリフト判定** — `phase_a_predictions.csv` をベースライン
5. **Kelly理論値 vs 固定100円比較**

**GO/NO-GO 5基準**:
| 基準 | 閾値 | 内容 |
|---|---|---|
| 基準1 期間 | 8週間以上 | ペーパートレード継続期間 |
| 基準2 件数 | 200件以上 | 統計的に意味のあるサンプル数 |
| 基準3 回収率 | 100%以上 | 実績回収率 |
| 基準4 最大DD | 15%以内 | バンクロールの最大ドローダウン |
| 基準5 統計的有意性 | CI下限 > 損益分岐勝率 | Clopper-Pearson 95%CI（Gemini提案） |

**PSI判定基準**:
- `PSI < 0.10`: ✅ 正常（分布変化なし）
- `0.10 ≤ PSI < 0.20`: ⚠️ 注意（小さな変化）
- `PSI ≥ 0.20`: 🚨 要注意（ドリフトの疑い → モデル再訓練を検討）

---

### 9. Geminiフィードバック対応

**フィードバック1（odds_recorded_time追加）**:
- `paper_trade_log.csv` と `paper_trade_add.py` に列を追加
- 理由: 5分前オッズと30分前オッズを区別するため

**フィードバック2（Phase D-1データ取得方針変更）**:
- ~~過去データをnetkeibaからさかのぼる~~ → 不可能（確定オッズのみ保存）
- 今週末から `odds_collector/` でリアルタイム収集開始
- 3〜6ヶ月蓄積後にオッズドリフト特徴量エンジニアリング

**Q&Aサマリー（Gemini回答）**:
| テーマ | 採用方針 |
|---|---|
| キャリブレーション | Isotonic Regression、30%超は生値のまま（ハイブリッド） |
| GO/NO-GO基準5 | Clopper-Pearson 95%CI下限 > 損益分岐勝率を追加 |
| ドリフト検出 | PSI（300サンプル/月で実用的） |
| オッズ収集 | SQLite + 2.5秒sleep、morning schedule fetch |
| SHAP | 強く賛成、ms単位で動作、top3〜5特徴量 + 方向を表示 |

---

## 作成・修正したファイル一覧

| ファイル | 種別 | 内容 |
|---|---|---|
| `phase_c_operation.py` | 修正 | NaT修正（日本語日付正規化） |
| `keiba_prediction_gui_v3.py` | 修正 | pandas FutureWarning修正（L152） |
| `backtest_full_2020_2025.py` | 修正 | pandas FutureWarning修正（L65） |
| `paper_trade_log.csv` | 修正 | 列追加（bet_type / calibrated / kelly / odds_recorded_time） |
| `paper_trade_add.py` | 全面リライト | Kelly計算追加、バンクロール基準修正 |
| `paper_trade_review.py` | 新規作成 | 月次レビュースクリプト（298行） |
| `odds_collector/schedule_fetch.py` | 新規作成 | レーススケジュール取得バッチ |
| `odds_collector/odds_snapshot.py` | 新規作成 | オッズスナップショット取得 |
| `odds_collector/odds_timeseries.db` | 新規作成 | SQLiteデータベース（初期化済み） |
| `odds_collector/README.md` | 新規作成 | システム概要 |
| `odds_collector/TASK_SCHEDULER_SETUP.md` | 新規作成 | タスクスケジューラ設定手順 |
| `START_HERE.md` | 更新 | 最終ステータス・今週末の運用手順 |
| `docs/PHASE_C3_SESSION_REPORT_20260224.md` | 新規作成 | Phase C-3 NaT修正レポート |
| `docs/PROJECT_STATUS_20260224.md` | 新規作成 | プロジェクト総括・提言A〜G |
| `docs/GEMINI_FEEDBACK_20260224.md` | 新規作成 | Geminiフィードバック対応記録 |
| `docs/GEMINI_EVAL_RESPONSE_20260224.md` | 新規作成 | Gemini提言評価への相談・逆提言 |
| `docs/GEMINI_QA_RESPONSE_20260224.md` | 新規作成 | Gemini Q&A回答まとめ・実装方針 |

---

## 現在のバックテスト結果（参考）

**推奨ベットルール: Rule4 複合最良**

| 条件 | 件数/年 | 的中率 | 回収率 | 純損益 |
|---|---:|---:|---:|---:|
| pred_win > 10% かつ odds ≥ 10.0x | 2,439 | 8.0% | 172% | +175,640円 |
| pred_win > 20% かつ odds ≥ 5.0x | 914 | 18.9% | 223% | +112,210円 |
| **Rule4（上2つの和集合）** | **3,833** | **17.5%** | **159%** | **+225,360円** |

*(初期資金50,000円、1点100円固定。ペナルティ適用後は約130〜140%想定)*

---

## これからのロードマップ

| 時期 | タスク | 内容 |
|---|---|---|
| **今週末〜** | **ペーパートレード開始** | `START_HERE.md` の「今週末の運用手順」参照 |
| 今週末 | タスクスケジューラ設定 | `TASK_SCHEDULER_SETUP.md` 参照 |
| 1〜2ヶ月後 | GO/NO-GO判断 | `paper_trade_review.py` で5基準確認 |
| 3〜6ヶ月後 | Phase D-1 | オッズドリフト特徴量エンジニアリング |
| 3〜6ヶ月後 | SHAP GUI表示 | TreeExplainer でtop3〜5特徴量を表示 |
| 3〜6ヶ月後 | キャリブレーション | Isotonic Regression（30%超は生値） |
| 長期 | Phase D-2 | 月次モデル再訓練サイクル |

---

*作成: 2026年2月25日*
