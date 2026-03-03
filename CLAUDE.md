# 競馬予想AIプロジェクト — Claude Code プロジェクトメモリ

> このファイルは Claude Code が毎回自動で読み込む。
> 作業の継続性・背景共有のために更新し続ける。←Claude Code側で随時実行すること。

---

## このプロジェクトは何か

**競馬の単勝・複勝を機械学習で予測し、バックテストで有効性を確認したベットルールを実際に運用するシステム。**

- 2020〜2025年の netkeiba レースデータ（約290,000件）を学習
- LightGBM モデルで「この馬が1着になる確率」「3着以内に入る確率」を予測
- Rule4 複合ベットルールで **GUI完全一致バックテスト（2024 out-of-sample）ROI 139.1%・年間+247,939円** を確認済み
- GUI（Tkinter）から未来のレースURLを入力 → 予測確率 + 推奨買い目 + SHAP予測根拠を表示

---

## 最終ゴール

```
ペーパートレード（紙上取引）で1〜2ヶ月実績を積む
        ↓
GO/NO-GO 5基準をすべてクリア
        ↓
ライブトレード（実際の馬券購入）へ移行
```

**GO/NO-GO 5基準**（`paper_trade_review.py` で自動判定）:

1. ペーパートレード期間 8週間以上
2. ベット件数 200件以上
3. 実績回収率 100%以上
4. 最大ドローダウン 15%以内
5. 95% CI下限 > 損益分岐勝率（統計的有意性）

---

## 現在のステータス（2026年3月1日時点）

```
Phase 14 ✅ → Phase A/B/C ✅ → GUI統合 ✅ → SHAP実装 ✅
→ GUI完全一致バックテスト完了 ✅ → 券種別分析完了 ✅
→ odds_snapshot GUI統合 ✅ → タスクスケジューラ設定 ✅
                  ↓
         ペーパートレード開始（随時）
```

**次のアクション**: 今週末（3/7土曜）タスクスケジューラ自動起動を確認 → `競馬予想ツール.bat` でGUI → Rule4 条件B 中心にペーパー記録

---

## 推奨ベットルール（Rule4）— GUI完全一致バックテスト済み

| 条件 | 年間件数 | 的中率 | ROI（2024 OOS） | ROI（2025 OOS） |
|------|---------|--------|----------------|----------------|
| **条件B: pred_win ≥ 10% & odds ≥ 10x** | ~5,500件 | 8〜18% | **154-172%** | **154-172%** |
| **条件A: pred_win ≥ 20% & odds 2〜10x** | ~2,400件 | 32% | 125.9% | — |
| **Rule4（A ∪ B）** | **6,349件** | **16.3%** | **139.1%** | **154.8%** |

_(1点100円固定。2024・2025はモデル訓練外の out-of-sample)_

### バックテスト確定数値（GUI完全一致・`run_gui_backtest.py`）

| 年 | レース数 | Rule4件数 | ROI | 純損益 | 区分 |
|----|---------|----------|-----|--------|------|
| 2020 | 3,456 | 4,404件 | 142.8% | +188,679円 | in-sample |
| 2021 | 3,456 | 5,111件 | 144.1% | +225,515円 | in-sample |
| 2022 | 3,456 | 5,658件 | 138.1% | +215,843円 | in-sample |
| 2023 | 3,456 | 6,013件 | 142.3% | +254,053円 | in-sample |
| **2024** | **3,454** | **6,349件** | **139.1%** | **+247,939円** | **out-of-sample ✓** |
| **2025** | **2,867** | **5,495件** | **154.8%** | **+300,870円** | **out-of-sample ✓** |

---

## 券種別分析結果（2024年 out-of-sample）

| 券種 | ヒット率 | ROI | 推奨 |
|------|---------|-----|------|
| **単勝 Rule4 条件B（odds≥10x）** | 8.7% | **151.7%** | ★最推奨 |
| 単勝 Rule4 条件A（odds 2-10x） | 36.7% | 140.9% | ★推奨 |
| 単勝◎ 全買い | 32.1% | 129.4% | 参考 |
| 複勝◎ 全買い | 58.1% | ~80-90%（推定） | 非推奨（配当圧縮） |
| ワイド（複勝率1-2位） | 22.9% | ~114%（推定） | 要実データ確認 |
| 馬連◎-○ | 11.6% | 不明 | 当面見送り |
| 3連複（複勝率1-3位） | 6.1% | 高分散 | 非推奨 |

詳細: `docs/PHASE14_BET_TYPE_ANALYSIS.md`

---

## 主要ファイル

| ファイル | 役割 |
|----------|------|
| `keiba_prediction_gui_v3.py` | GUI本体（予測・推奨買い目・SHAP・DBオッズ補完） |
| `phase14_model_win.txt` | 単勝予測モデル（LightGBM、AUC 0.7988） |
| `phase14_model_place.txt` | 複勝予測モデル（LightGBM、AUC 0.7558） |
| `phase14_feature_list.pkl` | 39特徴量リスト |
| `run_gui_backtest.py` | GUI完全一致バックテスト（`predict_core()`直接呼び出し） |
| `paper_trade_log.csv` | ペーパートレード記録CSV |
| `paper_trade_review.py` | 月次レビュー（PSI・GO/NO-GO・Kelly比較） |
| `odds_collector/schedule_fetch.py` | レーススケジュール取得（土日07:00自動） |
| `odds_collector/odds_snapshot.py` | オッズスナップショット取得（単勝+馬連+ワイド） |
| `odds_collector/odds_timeseries.db` | オッズ時系列SQLiteデータベース（race_schedule + odds_snapshots + combo_odds_snapshots） |
| `analyze_bet_types_phase14.py` | 券種別ヒット率・ROI分析スクリプト |
| `check_calibration.py` | 予測確率キャリブレーション確認（`py check_calibration.py`） |
| `setup_tasks.bat` | Windowsタスクスケジューラ登録バッチ（管理者権限で実行） |
| `setup_odds_task.ps1` | KeibaOddsSnapshot タスク再作成用 PowerShell スクリプト |
| `setup_note_task.ps1` | KeibaNotePoster タスク登録用 PowerShell スクリプト |
| `note_publisher/run_auto_post.py` | note.com 自動投稿オーケストレーター（--dry/--test/--date 対応） |
| `note_publisher/post_to_note.py` | Playwright で note.com に有料記事を投稿 |
| `note_publisher/format_article.py` | predict_core() 結果 → note記事テキスト生成 |
| `note_publisher/.env` | note.com 認証情報（gitignore済み） |
| `競馬予想ツール.bat` | GUI起動バッチ（土日は schedule_fetch.py を自動実行） |

### run_gui_backtest.py 出力ファイル

| ファイル | 内容 |
|----------|------|
| `backtest_gui_{label}_races.csv` | レース単位結果（年・月・競馬場・◎的中・Rule4集計） |
| `backtest_gui_{label}_bets.csv` | Rule4ベット単位詳細（馬番・予測値・オッズ・的中・配当） |

> label = 年指定時は "2024"、全期間は "all"。Excel で開いて月次・場別分析が可能。

### バックテスト結果ドキュメント（`docs/`）

| ファイル | 内容 |
|----------|------|
| `docs/PHASE14_GUI_BACKTEST_2024.md` | 2024年 GUI完全一致バックテスト詳細 |
| `docs/PHASE14_GUI_BACKTEST_2020_2025.md` | 2020-2025年 全期間バックテスト詳細 |
| `docs/PHASE14_BET_TYPE_ANALYSIS.md` | 券種別パフォーマンス分析（2024年） |

---

## 週末の運用フロー（統合済み・自動実行）

```
【自動】土日 07:00  KeibaScheduleFetch  →  race_schedule テーブル更新
【自動】土日 08:30  KeibaNotePoster     →  note.com 全レース自動投稿（有料300円/レース）
【自動】土日 09:00〜17:30（30分毎）  KeibaOddsSnapshot  →  odds_snapshots + combo_odds_snapshots 更新

【手動】競馬予想ツール.bat 起動
  → GUI で出馬表URLを入力
  → スクレイプ失敗時は odds_timeseries.db から自動補完
  → SHAP予測根拠 + Rule4 推奨買い目を表示

【手動】月次レビュー  py paper_trade_review.py
```

### タスクスケジューラ登録状況

| タスク名 | 次回実行 | 説明 |
|---------|---------|------|
| `KeibaScheduleFetch` | 2026/03/07 07:00 | 土日朝: レーススケジュール取得 |
| `KeibaOddsSnapshot` | 2026/03/07 09:00 | 土日 09:00〜17:30（30分毎）: 単勝+馬連+ワイド取得 |
| `KeibaNotePoster` | 2026/03/07 08:30 | 土日 08:30: note.com 全レース自動投稿（headless） |

> 旧タスク (`keiba_schedule_fetch`, `keiba_odds_morning`, `keiba_odds_afternoon`) も残存しているが無害。削除には管理者権限が必要。

---

## 技術スタック

- **言語**: Python 3.13
- **ML**: LightGBM 4.6.0（Booster形式）
- **GUI**: Tkinter (`keiba_prediction_gui_v3.py`, 4,257行+)
- **予測根拠**: shap 0.48.0（TreeExplainer）
- **データ**: netkeiba スクレイピング（2020〜2025年）
- **DB**: SQLite（オッズ時系列）
- **自動化**: Windowsタスクスケジューラ
- **note.com自動投稿**: Playwright + python-dotenv（note_publisher/）

---

## これまでの主な修正履歴

| 日付 | 内容 |
|------|------|
| 2026/02/23 | Phase C-2 GUI統合（Phase 14モデルをGUIに組み込み） |
| 2026/02/24 | Phase C-3 NaT修正（日本語日付 `2024年01月06日` → ISO形式） |
| 2026/02/24 | pandas FutureWarning修正（fillna inplace廃止対応） |
| 2026/02/24 | paper_trade_add.py リライト（Kelly計算・bankroll基準） |
| 2026/02/24 | odds_collector/ 一式作成（SQLite・スクレイパー・README） |
| 2026/02/24 | paper_trade_review.py 作成（PSI・GO/NO-GO・Kelly比較） |
| 2026/02/25 | Windowsタスクスケジューラ設定（3タスク・WakeToRun設定済み） |
| 2026/02/25 | SHAP予測根拠表示をGUIに実装（recommend_text末尾にTOP5表示） |
| 2026/03/01 | odds_snapshot.py APIバグ修正（`odds.netkeiba.com` DNS不存在 → `race.netkeiba.com/api/api_get_jra_odds.html?type=1` + EUC-JP対応） |
| 2026/03/01 | `run_gui_backtest.py` 作成（`predict_core()`直接呼び出しによるGUI完全一致バックテスト） |
| 2026/03/01 | 2024年 GUI完全一致バックテスト完了（3,454レース・Rule4 ROI 139.1%） |
| 2026/03/01 | 2020-2025年 全期間バックテスト完了（20,145レース・155.2分） |
| 2026/03/01 | 券種別分析完了（単勝Rule4条件Bが最良・ワイドは要実データ確認） |
| 2026/03/01 | paper_trade_add.py 削除（使用しないため） |
| 2026/03/01 | run_gui_backtest.py 改善（CSV出力・月次集計・競馬場別集計追加） |
| 2026/03/01 | odds_snapshot.py 改善（馬連・ワイドオッズ収集追加・combo_odds_snapshotsテーブル追加） |
| 2026/03/01 | check_calibration.py 作成（予測確率 vs 実際的中率の検証ツール） |
| 2026/03/01 | odds_snapshot.py GUI統合: umaban列追加 + combo_odds_snapshotsテーブル追加 + 馬連/ワイド収集 |
| 2026/03/01 | GUI(_get_odds_from_snapshot_db)追加: スクレイプ失敗時にDBからオッズ自動補完 |
| 2026/03/01 | 競馬予想ツール.bat 更新: 土日はschedule_fetch.py自動実行 |
| 2026/03/01 | setup_tasks.bat / setup_odds_task.ps1 作成: Windowsタスクスケジューラ登録 |
| 2026/03/01 | KeibaOddsSnapshot タスク修正: schtasks /ri 制限回避のためXML方式で30分間隔を正確に設定 |
| 2026/03/01 | note.com 自動投稿システム完成（note_publisher/ 一式）: Playwright でログイン→記事作成→有料300円設定→投稿まで完全自動化 |
| 2026/03/01 | KeibaNotePoster タスク登録（土日 08:30 自動実行） |

---

## 重要な技術メモ

### odds_snapshot.py の正しいAPIエンドポイント

```python
# ✗ 旧（DNS不存在）
https://odds.netkeiba.com/?type=b1&race_id={race_id}

# ✓ 正（JSON API）
https://race.netkeiba.com/api/api_get_jra_odds.html?race_id={race_id}&type=1
# レスポンス: {"status":"result","data":{"odds":{"1":{"01":["4.9","","4"],...}}}}
# "1" = 単勝, 配列 = [オッズ, "", 人気順]

# shutuba.html は EUC-JP エンコーディング
resp.encoding = 'euc-jp'
```

### GUI完全一致バックテストの核心

```python
# current_date = レース日付 が未来データリーク防止の核心
df_pred = gui.predict_core(race_id, horses, race_info, has_odds,
                           current_date=race_date)
```

### Phase 12 vs Phase 14 比較

| 指標 | Phase 12（問題あり） | Phase 14（正確） |
|------|---------------------|----------------|
| ◎的中率（2024） | 58.8%（リーケージ） | **35.0%** |
| Rule4 ROI（2024） | 354.7%（リーケージ） | **139.1%** |
| 原因 | `datetime.now()`・累積統計漏れ・79特徴量 | `current_date=race_date`・39特徴量 |

---

## 今後のロードマップ

| 時期 | タスク |
|------|--------|
| **随時** | **ペーパートレード継続（Rule4 条件B 優先）** |
| 1〜2ヶ月後 | `py paper_trade_review.py` で GO/NO-GO 判定 |
| 3〜6ヶ月後 | ワイドの実配当データ検証（odds_collector 蓄積後） |
| 3〜6ヶ月後 | Phase D-1: オッズドリフト特徴量 |
| 3〜6ヶ月後 | Isotonic Regression キャリブレーション |
| 長期 | Phase D-2: 月次モデル再訓練サイクル |

---

## よくあるトラブル

| 症状 | 対処 |
|------|------|
| `SHAP explainer 初期化失敗` | `py -m pip install shap` |
| `モデル読み込み失敗` | `phase14_model_win.txt` / `phase14_model_place.txt` / `phase14_feature_list.pkl` の存在確認 |
| GUI予測でエラー | `keiba_prediction_gui_v3.py` L1777 の `float(self.model_win.predict(feat_df)[0])` を確認 |
| タスクスケジューラが動かない | PCスリープ中 → WakeToRun設定確認 or 手動実行 |
| odds_snapshot.py でオッズ取得失敗 | レース発売前 or API仕様変更 → `race.netkeiba.com/api/api_get_jra_odds.html?race_id=...&type=1` を確認 |
| KeibaOddsSnapshot が N/A になる | `powershell -ExecutionPolicy Bypass -File setup_odds_task.ps1` で再作成（XML方式で30分間隔設定） |
| 旧タスクを削除したい | タスクスケジューラGUIを管理者として開いて手動削除 |
| note投稿が失敗する | `py note_publisher/run_auto_post.py --test` でブラウザ表示テスト → スクリーンショット確認 |
| note「有料エリア設定」ボタンが出る | 正常動作（境界線なし記事の場合、ボタンクリックで自動挿入） |
| note価格入力フィールドが出ない | note.com 本人情報登録（氏名・住所）未完了の可能性 |

---

---

## odds_snapshot.py × GUI 統合フロー（詳細）

```
odds_timeseries.db
├── race_schedule       （schedule_fetch.py が土日07:00に更新）
├── odds_snapshots      （odds_snapshot.py が単勝オッズ+umaban列を保存）
└── combo_odds_snapshots（odds_snapshot.py が馬連+ワイドオッズを保存）

GUI predict_race()
  1. scrape_shutuba() でオッズ取得試みる
  2. has_odds=False なら _get_odds_from_snapshot_db(race_id) で補完
     → SELECT umaban, odds_win FROM odds_snapshots WHERE race_id=? ORDER BY recorded_at DESC
  3. odds があれば predict_core() で予測続行
```

GUI補完の表示メッセージ:
```
✓ オッズをローカルDB（odds_timeseries.db）から補完しました（16頭分）
```

### note.com 自動投稿 確認済みセレクタ

| 要素 | セレクタ |
|------|---------|
| ログインemail | `#email` |
| ログインpassword | `#password` |
| ログインボタン | `button:has-text("ログイン")` |
| エディタURL | `https://editor.note.com/new` (domcontentloaded) |
| タイトル | `textarea[placeholder="記事タイトル"]` |
| 本文 | `.ProseMirror` (contenteditable) |
| 公開に進む | `button:has-text("公開に進む")` |
| 有料ラジオlabel | `label[for="paid"]` |
| 価格入力 | `input#price` (type=text, デフォルト300) |
| 有料エリア設定 | `button:has-text("有料エリア設定")` |
| 投稿ボタン | `button:has-text("投稿する")` |

**ログイン完了待機**: `wait_for_url` は `/login` 自体にもマッチするため
`wait_for_function("() => !window.location.href.includes('/login')")` を使用

_最終更新: 2026年3月1日_
