# 競馬予想AIプロジェクト — Claude Code プロジェクトメモリ

> このファイルは Claude Code が毎回自動で読み込む。
> 作業の継続性・背景共有のために更新し続ける。←Claude Code側で随時実行すること。

---

## このプロジェクトは何か

**競馬の単勝・複勝を機械学習で予測し、バックテストで有効性を確認したベットルールを実際に運用するシステム。**

- 2020〜2025年の netkeiba レースデータ（約290,000件）を学習
- LightGBM モデルで「この馬が1着になる確率」「3着以内に入る確率」を予測
- Rule4 複合ベットルールで **GUI完全一致バックテスト（2024 out-of-sample）ROI 148.0%・年間+274,879円** を確認済み（Phase R2-Optunaモデル）
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

## 現在のステータス（2026年3月23日時点）

```
Phase 14 ✅ → Phase A/B/C ✅ → GUI統合 ✅ → SHAP実装 ✅
→ GUI完全一致バックテスト完了 ✅ → 券種別分析完了 ✅
→ odds_snapshot GUI統合 ✅ → タスクスケジューラ設定 ✅
→ Phase R1〜R8+Optuna ✅ → 2024 ROI 179.8% / 2025 ROI 178.1% ★現在の有効モデル★
→ phase13_feature_engineering.py に R8特徴量計算追加 ✅
→ note.com 自動投稿: 各レース有料記事（300円）✅ + Win5有料記事（300円）✅
→ 成績レポート無料投稿 ✅ / 結果未取得バグ修正 ✅
→ KeibaWin5Poster タスク登録済み（日曜09:15）✅
→ backtest_analysis.py 作成（競馬場・月・オッズ帯・確率帯の多角分析）✅
→ ワイド・馬連 複勝上位3頭BOX をペーパートレードに追加 ✅
→ 条件A に 1/2 Kelly ベットサイジング導入 ✅
→ GUI に Rule4買い目・Kelly額・ワイド馬連BOX表示を追加 ✅
→ データ自動収集: collect_weekly_races.py（月曜06:00自動）✅
→ 調教データ収集完了: training_evaluations.csv（296,801件・2020-2026全レース）✅
→ Phase R9（調教ランク特徴量）実装・検証完了 ✅ → R8+Optuna 維持を選択
→ oikiri.html?type=2 で実タイムデータ取得可能と判明 ✅（Phase R10 候補）
                  ↓
         ペーパートレード継続中（R8+Optunaモデルで運用）
         開始: 2026/03/08  初期バンクロール: 50,000円
         2週間実績（確定分310件）: ROI -27%（条件A -21% / 条件B -32%）
         ※ サンプル少（2週間）。Phase R9検証などモデル改善を並行調査中。
```

**次のアクション**: ペーパートレード継続 / Phase R10（調教タイム特徴量）検討 / 月次レビュー `py paper_trade_review.py`

---

## 推奨ベットルール（Rule4）— GUI完全一致バックテスト済み

| 条件 | 年間件数 | 的中率 | ROI（2024 OOS） |
|------|---------|--------|----------------|
| **条件B: pred_win ≥ 10% & odds ≥ 10x** | ~3,343件 | 7.1% | **163.2%** |
| **条件A: pred_win ≥ 20% & odds 2〜10x** | ~2,387件 | 32.6% | 126.7% |
| **Rule4（A ∪ B）** | **5,730件** | **17.7%** | **148.0%** |

_(1点100円固定。Phase R2-Optunaモデル（60特徴量）。2024はout-of-sample)_

### バックテスト確定数値（GUI完全一致・`run_gui_backtest.py`）

**Phase 14 ベースライン（39特徴量・AUC 0.7988）**:

| 年 | レース数 | Rule4件数 | ROI | 純損益 | 区分 |
|----|---------|----------|-----|--------|------|
| 2020 | 3,456 | 4,404件 | 142.8% | +188,679円 | in-sample |
| 2021 | 3,456 | 5,111件 | 144.1% | +225,515円 | in-sample |
| 2022 | 3,456 | 5,658件 | 138.1% | +215,843円 | in-sample |
| 2023 | 3,456 | 6,013件 | 142.3% | +254,053円 | in-sample |
| **2024** | **3,454** | **6,349件** | **139.1%** | **+247,939円** | **out-of-sample ✓** |
| **2025** | **2,867** | **5,495件** | **154.8%** | **+300,870円** | **out-of-sample ✓** |

**Phase R1（46特徴量・AUC 0.7997）**:

| 年 | Rule4件数 | ROI | 純損益 | 区分 |
|----|----------|-----|--------|------|
| **2024** | **6,122件** | **142.1%** | **+257,480円** | **out-of-sample ✓** |

**Phase R2-Optuna（60特徴量・Val AUC 0.7656）**:

| 年 | Rule4件数 | ROI | 純損益 | 区分 |
|----|----------|-----|--------|------|
| **2024** | **5,730件** | **148.0%** | **+274,879円** | **out-of-sample ✓** |
| **2025** | **5,372件** | **174.7%** | **+401,142円** | **out-of-sample ✓** |

**Phase R4（67特徴量・Val AUC 0.7858）**:
_R2-Optunaパラメータ流用（lr 0.0086、num_leaves 43）+ レース内相対特徴量7個_

| 年 | Rule4件数 | ROI | 純損益 | 区分 |
|----|----------|-----|--------|------|
| **2024** | **4,384件** | **157.3%** | **+251,393円** | **out-of-sample ✓** |
| **2025** | **3,729件** | **197.9%** | **+365,046円** | **out-of-sample ✓** |

**Phase R7（71特徴量・Val AUC 0.7854）**:
_R4パラメータ流用 + 枠番バイアス（waku_win_rate/field_waku_rank）+ 騎手交代（jockey_changed/jockey_change_quality）_

| 年 | Rule4件数 | ROI | 純損益 | 区分 |
|----|----------|-----|--------|------|
| **2024** | **4,359件** | **157.4%** | **+250,246円** | **out-of-sample ✓** |
| **2025** | **3,860件** | **184.5%** | **+326,047円** | **out-of-sample ✓** |

**Phase R7+Optuna（71特徴量・Val AUC 0.7875）**:
_Optuna 100試行（lr=0.01112, num_leaves=37）_

| 年 | Rule4件数 | ROI | 純損益 | 区分 |
|----|----------|-----|--------|------|
| **2024** | **4,500件** | **161.1%** | **+275,150円** | **out-of-sample ✓** |
| **2025** | **4,000件** | **186.4%** | **+345,430円** | **out-of-sample ✓** |

**Phase R8（78特徴量・Val AUC 0.8245）**:
_R7+Optunaパラメータ流用 + 血統×競馬場/近況/馬個体×条件 7特徴量_

| 年 | Rule4件数 | ROI | 純損益 | 区分 |
|----|----------|-----|--------|------|
| **2024** | **5,314件** | **176.1%** | **+404,263円** | **out-of-sample ✓** |
| **2025** | **5,522件** | **180.4%** | **+443,984円** | **out-of-sample ✓** |

**Phase R8+Optuna（78特徴量・Val AUC 0.8256）— 現在の有効モデル ★最高純損益★**:
_Optuna 100試行（lr=0.0369, num_leaves=30）/ Best CV AUC=0.8683_

| 年 | Rule4件数 | 的中率 | ROI | 純損益 | 区分 |
|----|----------|------|-----|--------|------|
| **2024** | **5,272件** | **24.4%** | **181.3%** | **+428,552円** | **out-of-sample ✓** |
| **2025** | **5,581件** | — | **178.1%** | **+435,715円** | **out-of-sample ✓** |

2024詳細: 条件A 2,860件 的中率36.3% ROI 143.5% / 条件B 2,412件 的中率10.3% ROI 226.1%
restore: `py restore_model.py phase_r8_base` でpre-Optuna R8に戻せる

**Phase R9（79特徴量・Val AUC 0.8283）— 調教ランク追加・検証済み・不採用**:
_R8パラメータ流用（Optuna再最適化より高ROI）/ `training_rank_num`（A=4,B=3,C=2,D=1）_

| 年 | Rule4件数 | 的中率 | ROI | 純損益 | 区分 |
|----|----------|------|-----|--------|------|
| 2022 | 4,362件 | 26.6% | 223.0% | +536,741円 | in-sample |
| 2023 | 4,464件 | 26.7% | 224.3% | +554,730円 | in-sample |
| **2024** | **3,121件** | **29.1%** | **211.9%** | **+346,931円** | **out-of-sample ✓** |
| **2025** | **4,093件** | **26.7%** | **201.5%** | **+415,412円** | **out-of-sample ✓** |

R9不採用理由: ROI効率は+26pt向上だが件数▼41%減で純損益はR8に劣る。
`training_rank_num` はオッズ代理変数の疑いあり（A評価の中央値オッズ3.9倍=人気馬偏り）。
調教ランクA実勝率22.6% < 理論勝率~26%（市場がA評価を折り込み済み）。
将来: タイムデータ（客観指標）で再挑戦予定（Phase R10）

---

## 券種別分析結果（2024年 out-of-sample）

| 券種 | ヒット率 | ROI | 推奨 |
|------|---------|-----|------|
| **単勝 Rule4 条件B（odds≥10x）** | 7.2% | **154.1%** | ★最推奨 |
| 単勝 Rule4 条件A（odds 2-10x） | 31.9% | 125.3% | ★推奨 |
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
| `keiba_prediction_gui_v3.py` | GUI本体（予測・推奨買い目・SHAP・DBオッズ補完・Win5予測） |
| `phase14_model_win.txt` | 単勝予測モデル（LightGBM、Val AUC 0.8256・Phase R8+Optuna） |
| `phase14_model_place.txt` | 複勝予測モデル（LightGBM、Phase R8+Optuna） |
| `phase14_feature_list.pkl` | 78特徴量リスト（Phase R8+Optuna） |
| `models/phase_r8/` | R8+Optunaモデル（現行）+ sire_track_stats.json |
| `models/phase_r8_base/` | R8（Optuna前）バックアップ |
| `models/phase_r9/` | R9モデル（不採用・保存のみ）|
| `restore_model.py` | モデルバージョン切り替えスクリプト |
| `collect_weekly_races.py` | 週次データ自動収集（complete.csv + training_evaluations.csv 更新）|
| `collect_training_history.py` | 調教データ過去分一括収集（oikiri.html スクレイプ）|
| `calculate_features_r9.py` | Phase R9 特徴量計算（training_rank_num 追加）|
| `train_phase_r9.py` | Phase R9 モデル訓練（--optuna N 対応）|
| `data/main/training_evaluations.csv` | 調教評価データ（296,801件・2020-2026全レース）race_id/umaban/training_critic/training_rank |
| `run_gui_backtest.py` | GUI完全一致バックテスト（`predict_core()`直接呼び出し） |
| `paper_trade_log.csv` | ペーパートレード記録CSV |
| `paper_trade_review.py` | 月次レビュー（PSI・GO/NO-GO・Kelly比較） |
| `paper_trade_result_auto.py` | netkeiba結果自動取得・paper_trade_log.csv更新（--backfill/--date 対応） |
| `odds_collector/schedule_fetch.py` | レーススケジュール取得（土日07:00自動） |
| `odds_collector/odds_snapshot.py` | オッズスナップショット取得（単勝+馬連+ワイド） |
| `odds_collector/odds_timeseries.db` | オッズ時系列SQLiteDB（race_schedule/odds_snapshots/combo_odds_snapshots/race_predictions/race_results） |
| `note_publisher/run_auto_post.py` | note自動投稿メイン（--auto/--win5/--preview/--dry/--win5-budget） |
| `note_publisher/format_article.py` | 通常レース記事テキスト生成 |
| `note_publisher/format_win5.py` | Win5記事テキスト生成（無料+有料300円） |
| `note_publisher/post_to_note.py` | Playwright投稿エンジン（sep_label/stop_before_post対応） |
| `note_publisher/post_result_report.py` | AI予想成績レポートを無料記事で投稿（--dry/--preview/--date 対応） |
| `note_publisher/.env` | note.com 認証情報（gitignore済み） |
| `setup_note_task.ps1` | KeibaNotePoster タスク登録（土日08:30） |
| `setup_win5_task.ps1` | KeibaWin5Poster タスク登録（日曜09:15）★NEW |
| `setup_result_task.bat` | KeibaResultFetch タスク登録（土日 18:00） |
| `setup_report_task.bat` | KeibaReportPost タスク登録（土日 18:30） |
| `setup_odds_task.ps1` | KeibaOddsSnapshot タスク再作成用 |
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
【自動】日曜 09:15  KeibaWin5Poster     →  note.com WIN5予想記事投稿（有料300円）★NEW
【自動】土日 09:00〜17:30（30分毎）  KeibaOddsSnapshot  →  odds_snapshots + combo_odds_snapshots 更新
【自動】土日 18:00  KeibaResultFetch    →  netkeiba結果取得・paper_trade_log更新
【自動】土日 18:30  KeibaReportPost     →  AI予想成績レポート無料記事投稿

【手動】競馬予想ツール.bat 起動
  → GUI で出馬表URLを入力
  → スクレイプ失敗時は odds_timeseries.db から自動補完
  → SHAP予測根拠 + Rule4 推奨買い目を表示

【手動】月次レビュー  py paper_trade_review.py
```

### note.com 投稿コマンド早見表

```bash
# Win5 DRY RUN（記事テキスト + 推奨馬サマリー確認）
py note_publisher/run_auto_post.py --win5 --dry

# Win5 プレビュー（ブラウザで投稿直前まで確認・5分停止）
py note_publisher/run_auto_post.py --win5 --preview

# Win5 実投稿
py note_publisher/run_auto_post.py --win5

# 成績レポート確認 / 投稿
py note_publisher/post_result_report.py --dry
py note_publisher/post_result_report.py
```

### タスクスケジューラ登録状況

| タスク名 | 次回実行 | 説明 |
|---------|---------|------|
| `KeibaScheduleFetch` | 土日 07:00 | 土日朝: レーススケジュール取得 |
| `KeibaOddsSnapshot` | 土日 09:00〜17:30（30分毎） | 単勝+馬連+ワイド取得 |
| `KeibaNotePoster` | 土日 08:30 | 全レース有料記事（300円）自動投稿 |
| `KeibaWin5Poster` | 日曜 09:15（次回: 2026/03/22） | WIN5予想有料記事（300円）自動投稿 ★NEW |
| `KeibaResultFetch` | 土日 18:00 | netkeiba結果取得・paper_trade_log更新 |
| `KeibaReportPost` | 土日 18:30 | AI予想成績レポート無料記事投稿 |

> 旧タスク (`keiba_schedule_fetch`, `keiba_odds_morning`, `keiba_odds_afternoon`) も残存しているが無害。削除には管理者権限が必要。

---

## 技術スタック

- **言語**: Python 3.13
- **ML**: LightGBM 4.6.0（Booster形式）+ Optuna ハイパーパラメータ最適化
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
| 2026/03/04 | Phase R1: 特徴量7個追加（heavy_track_win_rate・distance_change・kiryou・is_female・horse_age・horse_weight・weight_change） |
| 2026/03/04 | Phase R1: 訓練データ再計算（46特徴量・2時間）→ モデル再訓練（Win AUC: 0.7997 ← 0.7988） |
| 2026/03/04 | Phase R1: get_race_from_database()バグ修正（斤量・性齢・馬体重をDBから取得するよう修正） |
| 2026/03/04 | Phase R1: 2024 OOS バックテスト完了（Rule4 ROI 142.1%・純損益+257,480円 ← 139.1%・+247,939円） |
| 2026/03/05 | Phase R2: 64特徴量 CSV 再生成・モデル再訓練完了（Win Val AUC: 0.7596←0.7997 / CV AUC: 0.8234）|
| 2026/03/05 | Phase R2: 2024 OOS バックテスト完了（Rule4 ROI 144.3%・純損益+275,049円 ← 142.1%・+257,480円）★ ROI は Phase R1 超え ★ |
| 2026/03/05 | Phase R2-Clean: 重複/定数特徴量4個削除（pace_preference・class_adjusted_diff・class_change・current_class）→ 60特徴量 ROI 134.9% |
| 2026/03/05 | Phase R2-Optuna: Optuna 80トライアル最適化（learning_rate 0.05→0.0086、Best Iter 38→338）|
| 2026/03/05 | Phase R2-Optuna: 2024 OOS バックテスト完了（Val AUC 0.7656・Rule4 ROI **148.0%**・純損益+274,879円）★ 全フェーズ最高記録 ★ |
| 2026/03/07 | Phase R3: avg_last_3f（Agariから計算）・running_style（running_style_categoryから計算）修正 → Val AUC 0.7660・ROI 138.1%（▼9.9pt）→ R2-Optuna維持 |
| 2026/03/08 | Phase R4: レース内相対特徴量7個追加（67特徴量）→ Win Val AUC 0.7858 / 2024 ROI 157.3% / 2025 ROI 197.9% ★最高記録★ |
| 2026/03/08 | Phase R4: predict_core() を2パス構造に変更（_add_relative_features_for_race() 追加） |
| 2026/03/08 | note.com ヘッダー画像アップロード修正: button[aria-label="画像を追加"] → JS textContent検索 → クロップ保存 → 30秒待機 |
| 2026/03/08 | paper_trade_result_auto.py 作成: netkeiba結果自動取得・paper_trade_log.csv更新・同着対応（PRIMARY KEY: race_id+umaban） |
| 2026/03/08 | post_result_report.py 作成: AI予想 vs 実結果レポートを無料note記事で投稿（土日18:30自動化） |
| 2026/03/08 | note.com ログイン修正: #email/#password が機能しない場合、wait_for_timeout(2000) + wait_for(visible) 後に fill() + dispatch_event('input') |
| 2026/03/08 | race_predictions / race_results テーブル追加: 予測印・上位3着結果をDBに保存（created_atで日付絞り込み） |
| 2026/03/09 | Phase R5: ペース・脚質特徴量7個追加（calculate_features_r5.py）・Optuna 150試行完了（Val AUC 0.7911） |
| 2026/03/09 | Phase R5: 2024 ROI 147.3% / 2025 ROI 183.3% → R4（157.3%/197.9%）より低ROI → R4維持確定 |
| 2026/03/09 | phase13_feature_engineering.py: R5特徴量計算追加（avg_first_corner_fixed/running_style_v2/slightly_heavy_win_rate等） |
| 2026/03/09 | keiba_prediction_gui_v3.py: _add_relative_features_for_race()にfield_escape_count/field_pace_advantage追加 |
| 2026/03/10 | Phase R6: 日次バイアス/天候/prev_agari_relative 6特徴量追加・Optuna 100試行（Val AUC 0.7907） |
| 2026/03/10 | Phase R6: 2024 ROI 146.1% / 2025 ROI 169.1% → R4（157.3%/197.9%）より低ROI → R4維持確定 |
| 2026/03/10 | Phase R6分析: prev_agari_relative(11位)・daily_prior_races(12位)は有効。daily_front_biasは弱信号（gain=30） |
| 2026/03/10 | GUI: predict_core()にR6特徴量計算追加（daily_front_bias・prev_agari_relative等） |
| 2026/03/11 | Phase R7: 枠番バイアス（waku_win_rate/field_waku_rank）+ 騎手交代（jockey_changed/jockey_change_quality）4特徴量追加 |
| 2026/03/11 | Phase R7: field_waku_rank 12位（gain=15,286）・waku_win_rate 18位（gain=8,980）→ 高インパクト |
| 2026/03/11 | Phase R7: 2024 ROI 157.4% / 2025 ROI 184.5%（R4パラメータ流用） |
| 2026/03/11 | Phase R7+Optuna: 2024 ROI **161.1%** / 2025 ROI **186.4%** |
| 2026/03/11 | Phase R8: 血統×競馬場/近況/馬個体特徴量7個追加（78特徴量・Val AUC 0.8245） |
| 2026/03/11 | Phase R8: 2024 ROI 176.1% / 2025 ROI 180.4%（純損益: +404,263/+443,984円） |
| 2026/03/12 | Phase R8+Optuna: Optuna 100試行完了（Best CV AUC=0.8683・Val AUC 0.8256） |
| 2026/03/12 | Phase R8+Optuna: 2024 ROI **179.8%** / 2025 ROI **178.1%**（純損益: +420,812/+435,715円）★最高記録★ |
| 2026/03/11 | phase13_feature_engineering.py: R7特徴量計算追加（waku_stats.json ロード + jockey_changed計算） |
| 2026/03/11 | keiba_prediction_gui_v3.py: _add_relative_features_for_race()にfield_waku_rank追加 |
| 2026/03/15 | post_result_report.py: load_results()をrace_id直接ルックアップに変更（結果未取得バグ修正） |
| 2026/03/15 | paper_trade_result_auto.py: 通常モードにrace_predictions全レース補完パス追加 |
| 2026/03/15 | note_publisher/format_win5.py 新規作成: Win5記事テキスト生成（無料/有料300円） |
| 2026/03/15 | note_publisher/run_auto_post.py: --win5/--preview/--win5-budget オプション追加・run_win5()/_fetch_win5_race_names()追加 |
| 2026/03/15 | note_publisher/post_to_note.py: sep_label/stop_before_post対応・プレビュー5分停止 |
| 2026/03/15 | setup_win5_task.ps1 新規作成: KeibaWin5Posterタスク登録（日曜09:15）登録済み |
| 2026/03/22 | backtest_analysis.py 作成: 2024+2025 OOSデータを競馬場・月・オッズ帯・予測確率帯で多角分析 |
| 2026/03/22 | キャリブレーション確認: 条件A（pred>=20%）は精度良好。条件B（pred 10-20%）は系統的過大評価（実際は約半分） |
| 2026/03/22 | ワイド・馬連追加: paper_trade_result_auto.py に parse_combo_payout() 追加・複勝上位3頭BOX記録対応 |
| 2026/03/22 | ワイド・馬連追加: note_publisher/run_auto_post.py の record_paper_trades() に複勝上位3頭BOX自動記録追加 |
| 2026/03/22 | Kelly ベットサイジング: 条件A → 1/2 Kelly（上限1,000円・下限100円・100円単位）、条件B → 100円固定 |
| 2026/03/22 | Kelly 設定フラグ: USE_KELLY_FOR_COND_A=True/False で即座に ON/OFF 切り替え可能 |
| 2026/03/22 | GUI更新: update_recommended_bets() に「Rule4単勝買い目＋Kelly額」「ワイド・馬連複勝上位3頭BOX」セクション追加 |
| 2026/03/23 | run_gui_backtest.py: enriched.csv+complete.csv の両方でバックテスト可能に修正（2025-09以降のレース対応）|
| 2026/03/23 | collect_weekly_races.py 新規作成: netkeiba週次スクレイプ（complete.csv + training_evaluations.csv 更新）|
| 2026/03/23 | collect_training_history.py 新規作成: 過去全レース調教データ一括収集（oikiri.html type=1）|
| 2026/03/23 | 調教データ収集完了: training_evaluations.csv 296,801件（2020-2026全年・空レースゼロ）|
| 2026/03/23 | Phase R9 実装: calculate_features_r9.py + train_phase_r9.py 作成 |
| 2026/03/23 | Phase R9 検証: training_rank_numは特徴量重要度6位（gain=18,174）・Val AUC 0.8302（R8比+0.005）|
| 2026/03/23 | Phase R9 検証: OOS ROI 205.9%/201.5%（R8の179.8%/178.1%より高い）、ただし件数▼41%で純損益は下回る |
| 2026/03/23 | Phase R9 不採用決定: training_rank A = 人気馬代理変数（中央値オッズ3.9倍・実勝率22.6%<理論値26%）|
| 2026/03/23 | 調教タイム発見: oikiri.html?type=2 で3Fタイム・コース・脚色取得可能と確認（Phase R10 候補）|
| 2026/03/23 | KeibaWeeklyCollect タスク登録: 毎週月曜 06:00 自動実行 |

---

## バックテスト深掘り分析サマリー（2024+2025 OOS）

`py backtest_analysis.py` で再現可能。

### 収益構造
- 条件A ROI 145% / 条件B ROI **217%** → 条件Bが稼ぎ頭
- 条件B オッズ高いほど強い: 10-20倍 182% / 20-30倍 210% / 30-50倍 246% / 50倍超 **285%**

### 強い競馬場（条件B）
福島 350% / 中京 308% / 函館 307% / 小倉 294%

### 弱い帯（足を引っ張っている）
- 条件A 2〜4倍: ROI 124%（件数多く効率低）
- 条件B pred10-13% × odds10-20倍: ROI 127%（件数843件と最多）
- 条件B pred13-16% × odds50倍超: ROI 92%（唯一の赤字帯）

### キャリブレーション
- **条件A（pred>=20%）**: 精度良好（誤差±2pt以内）→ Kelly適用可
- **条件B（pred10-20%）**: 系統的過大評価（予測15%→実際9%）→ Kelly不適・固定100円維持

### ベットサイジング設定（note_publisher/run_auto_post.py）
```python
USE_KELLY_FOR_COND_A = True   # False で全条件100円固定に戻す
KELLY_FRACTION       = 0.5    # 1/2 Kelly
KELLY_MAX_BET        = 1_000  # 上限円
KELLY_MIN_BET        = 100    # 下限円
```

---

## 調教データ分析サマリー（2026年3月23日）

### 調教ランク分布（training_evaluations.csv・全296,801件）
| ランク | 件数 | 割合 |
|--------|------|------|
| B | 167,757 | 56.5% |
| C | 112,976 | 38.0% |
| D | 11,101 | 3.7% |
| A | 4,043 | 1.4% |（少ない）

### 調教ランクとオッズ・勝率の関係（重要）
| ランク | オッズ中央値 | 実勝率 | 理論勝率（中央値ベース） | 判定 |
|--------|------------|------|----------------------|------|
| **A** | **3.9倍** | 22.6% | ~26% | **過大評価（市場に折り込み済み）** |
| B | 14.0倍 | 9.9% | ~7% | **過小評価（穴）** |
| C | 59.6倍 | 3.6% | ~1.7% | 過小評価 |
| D | 150.1倍 | 1.6% | ~0.7% | ほぼ理論値 |

**結論**: A評価は人気馬シグナル（中央値3.9倍）。市場がA評価を折り込んでおりプレミアムなし。
B評価の高オッズ馬が最も割安（理論値の1.4倍の実勝率）。

### Phase R9 vs R8+Optuna 比較（OOS 2024）
| | R8+Optuna | R9+Optuna |
|--|-----------|-----------|
| 件数 | 5,272件 | 3,121件（▼41%）|
| 的中率 | 24.4% | 29.1%（+4.7pt）|
| 条件A的中率 | 36.3% | 40.6%（+4.3pt）|
| 条件B的中率 | 10.3% | 13.2%（+2.9pt）|
| ROI | 181.3% | 205.9%（+24.6pt）|
| 純損益 | **+428,552円** | +330,580円（▼9.8万）|

的中率↑の主因：A評価=人気馬選択により条件Aで当たりやすい馬を優先した結果。
件数▼41%の主因：調教ランクがフィルタとして働き高オッズ穴馬の多くが除外された。

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

| 優先度 | タスク | 概要 |
|------|--------|------|
| **随時** | **ペーパートレード継続** | Rule4 条件B優先。毎週末自動実行 |
| **高・次期** | **Phase R10: 調教タイム特徴量** | oikiri.html?type=2 で3Fタイム・コース・脚色取得 → 相対タイム偏差値特徴量化。R9の「ランク=人気馬代理」問題を解決できる可能性 |
| 中 | GO/NO-GO 判定 | 8週間・200件以上になったら `py paper_trade_review.py` で判定 |
| 中 | オッズドリフト特徴量 | odds_timeseries.db 蓄積が2ヶ月分たまったら検討（直前オッズ変動率）|
| 中 | ワイド実配当データ検証 | odds_collector 蓄積後に実ROI確認 |
| 低 | Isotonic Regression キャリブレーション | 条件B の系統的過大評価を補正 |
| 低 | 月次モデル再訓練サイクル | 年1〜2回、データ追加後に再訓練 |
| GO/NO-GO後 | ライブトレード移行 | 5基準クリア後 |

### Phase R10（調教タイム）実装方針メモ

```
oikiri.html?race_id=XXXX&type=2 → 12列テーブル
  cols[4]=日付, cols[5]=コース（美Ｗ/美坂/栗Ｗ等）, cols[6]=馬場, cols[7]=乗り役
  cols[8]=タイムラップ文字列（例: "85.2(16.6)68.6(14.9)53.7(14.5)39.2(26.3)12.9(12.9)"）
  cols[10]=脚色（一杯/強め/馬也/末強め等）, cols[11]=評価テキスト, cols[12]=ランク

タイム抽出方法:
  re.findall(r'\d+\.\d+', "85.2(16.6)...12.9(12.9)") → [85.2, 16.6, 68.6, 14.9, 53.7, ...]
  3F時計 = 3番目の数値（53.7）, 上がり1F = 最後から2番目（12.9）

特徴量案:
  training_3f_raw        : 3Fタイム生値
  training_3f_relative   : 同日・同コース・同馬場での偏差値（重要）
  training_last1f        : 上がり1Fタイム
  training_course_type   : コース種別（坂路/W/芝/ダート）
  training_finish_type   : 脚色（一杯=0 / 強め=1 / 馬也=2 / 末強め=3）

注意:
  - コース別の正規化必須（坂路40秒 ≠ W38秒）
  - タイム欠損（-始まり = 計測なし）は中央値補完
  - 再スクレイプ: 既存 type=1 データを type=2 で再取得（約18時間）
  - collect_training_history.py の URL を type=2 に変更してバックグラウンド実行
```

---

## よくあるトラブル

| 症状 | 対処 |
|------|------|
| `SHAP explainer 初期化失敗` | `py -m pip install shap` |
| `モデル読み込み失敗` | `phase14_model_win.txt` / `phase14_model_place.txt` / `phase14_feature_list.pkl` の存在確認（`py restore_model.py` でバージョン確認） |
| GUI予測でエラー | `keiba_prediction_gui_v3.py` L1777 の `float(self.model_win.predict(feat_df)[0])` を確認 |
| タスクスケジューラが動かない | PCスリープ中 → WakeToRun設定確認 or 手動実行 |
| odds_snapshot.py でオッズ取得失敗 | レース発売前 or API仕様変更 → `race.netkeiba.com/api/api_get_jra_odds.html?race_id=...&type=1` を確認 |
| KeibaOddsSnapshot が N/A になる | `powershell -ExecutionPolicy Bypass -File setup_odds_task.ps1` で再作成（XML方式で30分間隔設定） |
| 旧タスクを削除したい | タスクスケジューラGUIを管理者として開いて手動削除 |
| note投稿が失敗する | `py note_publisher/run_auto_post.py --test` でブラウザ表示テスト → スクリーンショット確認 |
| note「有料エリア設定」ボタンが出る | 正常動作（境界線なし記事の場合、ボタンクリックで自動挿入） |
| note価格入力フィールドが出ない | note.com 本人情報登録（氏名・住所）未完了の可能性 |
| noteヘッダー画像が反映されない | クロップ保存後30秒待機が必要。`_upload_header_image()` 内 `await page.wait_for_timeout(30000)` を確認 |
| noteヘッダーのクロップ保存ボタン未検出 | JS で `data-testid="cropper"` 親を遡って `btn.textContent.trim()==="保存"` を検索（`ReactModalPortal` 直接検索は非推奨） |
| Win5記事の有料エリア境界がずれる | `sep_label='WIN5 推奨馬（各レグ詳細）'` が article dict に設定されているか確認 |
| Win5のレース名が空欄になる | `_fetch_win5_race_names()` はスケジュールページを再スクレイプ。ネット接続確認 |
| Win5 --preview でブラウザが見えない | 予測処理2〜3分後に起動。タスクバーを確認（5分間停止） |

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
| **ヘッダー画像ボタン** | **`button[aria-label="画像を追加"]`** |
| **ヘッダーアップロード** | **JS: `btn.textContent.includes("画像をアップロード")`** |
| **クロップ保存** | **JS: `data-testid="cropper"` 親→ `btn.textContent.trim()==="保存"`** |
| 有料ラジオlabel | `label[for="paid"]` |
| 価格入力 | `input#price` (type=text, デフォルト300) |
| 有料エリア設定 | `button:has-text("有料エリア設定")` |
| 投稿ボタン | `button:has-text("投稿する")` |

**ログイン完了待機**: `wait_for_url` は `/login` 自体にもマッチするため
`wait_for_function("() => !window.location.href.includes('/login')")` を使用

**ヘッダー画像反映待機**: クロップ保存後 `await page.wait_for_timeout(30000)` が必要（画像反映に10〜30秒かかる）

_最終更新: 2026年3月23日_
