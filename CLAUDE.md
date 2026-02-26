# 競馬予想AIプロジェクト — Claude Code プロジェクトメモリ

> このファイルは Claude Code が毎回自動で読み込む。
> 作業の継続性・背景共有のために更新し続ける。←Claude Code側で随時実行すること。

---

## このプロジェクトは何か

**競馬の単勝・複勝を機械学習で予測し、バックテストで有効性を確認したベットルールを実際に運用するシステム。**

- 2020〜2025年の netkeiba レースデータ（約290,000件）を学習
- LightGBM モデルで「この馬が1着になる確率」「3着以内に入る確率」を予測
- Rule4 複合ベットルールで回収率159%・年間+225,360円をバックテストで確認済み
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

## 現在のステータス（2026年2月25日時点）

```
Phase 14 ✅ → Phase A/B/C ✅ → GUI統合 ✅ → NaT修正 ✅
→ 運用ツール整備 ✅ → タスクスケジューラ設定 ✅ → SHAP実装 ✅
                                                      ↓
                                            今週末: ペーパートレード開始
```

**次のアクション**: `競馬予想ツール.bat` 起動 → SHAP表示確認 → 今週末からペーパートレード開始

---

## 推奨ベットルール（Rule4）

| 条件                             |   件数/年 |    的中率 |   回収率 |         純損益 |
| -------------------------------- | --------: | --------: | -------: | -------------: |
| pred_win > 10% かつ odds ≥ 10.0x |     2,439 |      8.0% |     172% |     +175,640円 |
| pred_win > 20% かつ odds ≥ 5.0x  |       914 |     18.9% |     223% |     +112,210円 |
| **Rule4（上2つの和集合）**       | **3,833** | **17.5%** | **159%** | **+225,360円** |

_(初期資金50,000円、1点100円固定)_

---

## 主要ファイル

| ファイル                            | 役割                                     |
| ----------------------------------- | ---------------------------------------- |
| `keiba_prediction_gui_v3.py`        | GUI本体（予測・推奨買い目・SHAP表示）    |
| `phase14_model_win.txt`             | 単勝予測モデル（LightGBM、AUC 0.7988）   |
| `phase14_model_place.txt`           | 複勝予測モデル（LightGBM、AUC 0.7558）   |
| `phase14_feature_list.pkl`          | 39特徴量リスト                           |
| `paper_trade_add.py`                | ペーパートレード記録CLI（Kelly計算付き） |
| `paper_trade_log.csv`               | ペーパートレード記録CSV                  |
| `paper_trade_review.py`             | 月次レビュー（PSI・GO/NO-GO・Kelly比較） |
| `odds_collector/schedule_fetch.py`  | レーススケジュール取得（土日07:00自動）  |
| `odds_collector/odds_snapshot.py`   | オッズスナップショット取得               |
| `odds_collector/odds_timeseries.db` | オッズ時系列SQLiteデータベース           |
| `競馬予想ツール.bat`                | GUI起動バッチ                            |

---

## 週末の運用フロー

```
土日 07:00  py odds_collector/schedule_fetch.py      # 自動実行（タスクスケジューラ）
各レース30分前  py odds_collector/odds_snapshot.py --timing 30min_before  # 自動実行
GUIで予測  競馬予想ツール.bat
Rule4条件の馬を確認してペーパートレード記録  py paper_trade_add.py
```

---

## 技術スタック

- **言語**: Python 3.13
- **ML**: LightGBM 4.6.0（Booster形式）
- **GUI**: Tkinter (keiba_prediction_gui_v3.py, 4,257行+)
- **予測根拠**: shap 0.48.0（TreeExplainer）
- **データ**: netkeiba スクレイピング（2020〜2025年）
- **DB**: SQLite（オッズ時系列）
- **自動化**: Windowsタスクスケジューラ

---

## これまでの主な修正履歴

| 日付       | 内容                                                        |
| ---------- | ----------------------------------------------------------- |
| 2026/02/23 | Phase C-2 GUI統合（Phase 14モデルをGUIに組み込み）          |
| 2026/02/24 | Phase C-3 NaT修正（日本語日付 `2024年01月06日` → ISO形式）  |
| 2026/02/24 | pandas FutureWarning修正（fillna inplace廃止対応）          |
| 2026/02/24 | paper_trade_add.py リライト（Kelly計算・bankroll基準）      |
| 2026/02/24 | odds_collector/ 一式作成（SQLite・スクレイパー・README）    |
| 2026/02/24 | paper_trade_review.py 作成（PSI・GO/NO-GO・Kelly比較）      |
| 2026/02/25 | Windowsタスクスケジューラ設定（3タスク・WakeToRun設定済み） |
| 2026/02/25 | SHAP予測根拠表示をGUIに実装（recommend_text末尾にTOP5表示） |

---

## 今後のロードマップ

| 時期         | タスク                                                  |
| ------------ | ------------------------------------------------------- |
| **今週末〜** | **ペーパートレード開始**                                |
| 1〜2ヶ月後   | `py paper_trade_review.py` で GO/NO-GO 判定             |
| 3〜6ヶ月後   | Phase D-1: オッズドリフト特徴量（odds_collector蓄積後） |
| 3〜6ヶ月後   | Isotonic Regression キャリブレーション                  |
| 3〜6ヶ月後   | SHAP をさらに拡充（place モデルへの対応等）             |
| 長期         | Phase D-2: 月次モデル再訓練サイクル                     |

---

## よくあるトラブル

| 症状                         | 対処                                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| `SHAP explainer 初期化失敗`  | `py -m pip install shap`                                                                    |
| `モデル読み込み失敗`         | `phase14_model_win.txt` / `phase14_model_place.txt` / `phase14_feature_list.pkl` の存在確認 |
| GUI予測でエラー              | `keiba_prediction_gui_v3.py` L1777 の `float(self.model_win.predict(feat_df)[0])` を確認    |
| タスクスケジューラが動かない | PCスリープ中 → WakeToRun設定確認 or 手動実行                                                |

---

_最終更新: 2026年2月25日_
