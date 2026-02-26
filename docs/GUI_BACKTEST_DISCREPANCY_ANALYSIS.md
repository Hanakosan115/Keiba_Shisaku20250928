# GUIロジック完全一致バックテスト - 不一致原因分析と修正計画

## 1. 現状の結論

`backtest_gui_logic.py` は「GUIロジック完全一致」と謳っているが、**実際にはGUIの予測開始ボタンの動作を正確に再現していない**。以下に全ての不一致箇所とその影響を示す。

---

## 2. 不一致箇所の一覧

| # | 項目 | 深刻度 | GUI (`keiba_prediction_gui_v3.py`) | バックテスト (`backtest_gui_logic.py`) |
|---|------|--------|-----------------------------------|-----------------------------------------|
| 1 | current_date | **致命的** | `datetime.now()` (実行時点の日付) | `datetime.now()` (2026年2月の日付を全レースに使用) |
| 2 | モデル使用 | **重大** | `model_win` + `model_top3` 両方 | `model_win` のみ |
| 3 | 印割り当て | **重大** | `_assign_marks()` で ◎○▲☆△注 を計算 | 実装なし (勝率上位3頭をそのまま使用) |
| 4 | 推奨馬券の決定 | **重大** | 印ベースで○▲△から紐馬選定、勝率別買い目パターン | 勝率Top3の馬番をそのまま使用 |
| 5 | バリュー計算 | **中** | `期待値 = 勝率 * オッズ`、`バリュー = 勝率 - 1/オッズ` | 計算なし |
| 6 | ☆マーク | **中** | バリュー>0 かつ オッズ>=10.0 の穴馬に割り当て | 実装なし |
| 7 | △マーク | **中** | `複勝予測`上位2頭 (>=0.20) に割り当て | 実装なし (`model_top3`未使用のため不可能) |
| 8 | horse_dataのソート | **軽微** | `date_normalized`で昇順ソート後に特徴量計算へ渡す | ソートなし |
| 9 | 特徴量信頼度 | **軽微** | 計算して`?`マーク付与に使用 | 計算なし |

---

## 3. 各不一致の詳細分析

### 3.1 [致命的] current_date の誤り

**GUIでの動作** (`keiba_prediction_gui_v3.py:1485`)
```python
current_date = datetime.now().strftime('%Y-%m-%d')
```
GUIでは、ユーザーがレースの発走前〜当日にボタンを押す。よって `datetime.now()` = レース日付近辺となり正しい。

**バックテストでの動作** (`backtest_gui_logic.py:113`)
```python
current_date = datetime.now().strftime('%Y-%m-%d')  # 常に2026-02-13
```
2020年のレースをバックテストする際も `current_date = '2026-02-13'` が使われる。

**影響**:
- `_add_phase10_features()` 内で `df_dates < current_date_dt` のフィルタが効かず、未来データ（そのレース以降のデータ）が全て特徴量計算に含まれる
- 2020年のレースの特徴量に2021〜2025年のデータが混入 = **未来データリーケージ**
- **年が新しいほど的中率が上がる**という結果ログの挙動と完全に一致:
  - 2020年: 29.4% → 2024年: 52.2% → 2025年: 43.8%
  - 新しい年ほどリーケージ量が少ないため「正しい」結果に近づき、それでも高すぎる
- GUIで実際に当日押した場合の成績とは異なる数字になる

**あるべき姿**: レース日付を `current_date` として渡す。

---

### 3.2 [重大] model_top3 を使っていない

**GUI** (`keiba_prediction_gui_v3.py:1627-1628`)
```python
pred_win_proba = self.model_win.predict_proba(feat_df)[0, 1]
pred_top3_proba = self.model_top3.predict_proba(feat_df)[0, 1]
```

**バックテスト** (`backtest_gui_logic.py:204`)
```python
pred_win = gui.model_win.predict_proba(feat_df)[0, 1]
# model_top3 を一切使っていない
```

**影響**:
- `複勝予測` が存在しないため、GUIの `_assign_marks()` で使われる `△` マーク (複勝予測上位)、`注` マーク (複勝予測一定以上) の判定が不可能
- GUIの推奨馬券は印ベースで決まるため、推奨馬番が異なる可能性がある

---

### 3.3 [重大] 印割り当てロジック未実装

**GUI** (`keiba_prediction_gui_v3.py:1766-1824`)
```
◎: 勝率1位
○: 勝率2位
▲: 勝率3位
☆: バリュー>0 かつ オッズ>=10.0 (◎○▲以外で最もバリューが高い馬)
△: ◎○▲☆以外で複勝予測上位2頭 (>=0.20)
注: 残りで複勝予測が閾値以上の最大2頭
```
→ その後 `update_recommended_bets()` で**印ベース**で馬券を組み立てる。

**バックテスト** (`backtest_gui_logic.py:252-254`)
```python
uma1 = predictions[0]['umaban']  # 勝率1位
uma2 = predictions[1]['umaban']  # 勝率2位
uma3 = predictions[2]['umaban']  # 勝率3位
```
→ 単純に勝率上位3頭。

**影響**:
- GUIが `☆` 付き穴馬を3着候補に含めるケースで、バックテストは勝率3位を使い続ける
- GUIの `update_recommended_bets()` は紐馬（○▲△）を使ってワイド流し・3連複ボックスを組むが、バックテストはその概念がない

---

### 3.4 [重大] 推奨馬券の組み立て方が異なる

**GUI** (`keiba_prediction_gui_v3.py:3636-3750`)

GUIの推奨買い目は**印の役割ベース**で決まる:
```
紐馬 = [○, ▲, △(最大2頭)] から重複除去、最大3頭
3着候補 = ▲（▲がなければ勝率3位で◎○以外）
単勝: ◎
馬連: ◎-○
3連複: ◎-○-▲
ワイド流し: ◎→紐馬
3連複BOX: ◎+紐馬
```
さらに勝率別に購入金額パターンまで変わる。

**バックテスト** (`backtest_gui_logic.py:252-267`)
```
単勝: 勝率1位
馬連: 勝率1位-勝率2位
ワイド: 勝率1位-勝率2位
3連複: 勝率1位-2位-3位
3連単BOX: 勝率1位-2位-3位
```
印の概念がないため、GUIとは異なる馬番の組み合わせになりうる。

---

### 3.5 [中] バリュー・期待値計算なし

**GUI** (`keiba_prediction_gui_v3.py:1630-1634`)
```python
expected_value = pred_win_proba * odds if odds > 0 else 0
value = pred_win_proba - (1.0 / odds) if odds > 0 else 0
```

**バックテスト**: 計算なし。

**影響**: `☆` マークが付く穴馬の特定が不可能。GUIではオッズ10倍以上のバリュー馬が `☆` となり、推奨買い目に影響する。

---

### 3.6 [軽微] horse_data のソート漏れ

**GUI** (`keiba_prediction_gui_v3.py:1544-1546`)
```python
horse_data['date_normalized'] = horse_data['date'].apply(normalize_date)
horse_data = horse_data.sort_values('date_normalized', ascending=True)
```

**バックテスト** (`backtest_gui_logic.py:155-157`)
```python
horse_data['date_normalized'] = horse_data['date'].apply(normalize_date)
horse_data = horse_data.sort_values('date_normalized', ascending=True)
```

→ **コード上はソートしている** (一見同じ)。ただしバックテスト側はtry/exceptの中でソートしており、`gui.df['horse_id'] == horse_id_num` のフィルタが失敗した場合のフォールバック (`gui.df[gui.df['horse_id'] == horse_id_num]`) ではソートが適用されない。

---

## 4. 結果の信頼性への影響

現在のバックテスト結果:
```
単勝的中率: 37.4%  ROI: 237.5%
2024年: 52.2%  ROI: 339%
```

これらの数字は**未来データリーケージ (3.1) のため実際より大幅に高い**。
実際にGUIで当日ボタンを押した場合の成績とは一致しない。

---

## 5. 修正作業計画

### Phase 1: current_date の修正 (最優先)

**目的**: 未来データリーケージを排除する

```
修正内容:
- レースのdate列からレース日付を取得
- current_date にそのレース日付を設定
- これにより、そのレース時点で入手可能だったデータのみで特徴量が計算される
```

**修正箇所**: `backtest_gui_logic.py` の `predict_race_gui_logic()` 関数
- `current_date = datetime.now()` → レースの`date`列から取得

### Phase 2: model_top3 の追加

**目的**: GUIと同じ2モデル予測を行う

```
修正内容:
- gui.model_top3.predict_proba() を追加
- predictions辞書に 'top3_proba' を追加
```

**修正箇所**: `backtest_gui_logic.py:204` 付近

### Phase 3: _assign_marks() の呼び出し

**目的**: GUIと完全に同じ印割り当てを行う

```
修正内容:
- predictionsをDataFrame化
- gui._assign_marks(df_pred, has_odds) を呼び出す
- 印に基づいて推奨馬番を決定
```

**修正箇所**: `backtest_gui_logic.py` の `run_backtest()` 関数内

### Phase 4: 推奨馬券のGUI完全再現

**目的**: GUIの `update_recommended_bets()` と同じ紐馬選定・馬券組み立てを行う

```
修正内容:
- 印から◎○▲☆△注を取得
- 紐馬リスト構築 (○, ▲, △から重複除去、最大3頭)
- 3着候補 = ▲ (▲なしなら勝率3位で◎○以外)
- 馬券組み立て: 単勝=◎、馬連=◎-○、3連複=◎-○-▲、ワイド流し=◎→紐馬
```

**修正箇所**: `backtest_gui_logic.py` の `run_backtest()` 関数内

### Phase 5: バリュー・オッズ計算の追加

**目的**: ☆マーク判定と期待値ベース推奨の再現

```
修正内容:
- 各馬の期待値とバリューを計算
- has_odds判定 (DBレースの場合はwin_odds列の有無で判定)
```

**修正箇所**: `backtest_gui_logic.py` の `predict_race_gui_logic()` 関数内

### Phase 6: 結果検証

```
検証方法:
1. 特定の1レースをGUIで予測し、結果をCSVエクスポート
2. 同じレースを修正後バックテストで予測
3. 馬番順位・印・推奨馬券が完全一致することを確認
4. 全レースバックテストを再実行し、年別成績の変化を確認
   - 特にリーケージ修正により2020-2023年の成績が大幅に下がるはず
```

---

## 6. 修正の優先順位まとめ

| 優先度 | Phase | 内容 | 影響度 |
|--------|-------|------|--------|
| 1 | Phase 1 | current_date修正 (リーケージ排除) | 全数字が変わる |
| 2 | Phase 2 | model_top3追加 | 印割り当てに必要 |
| 3 | Phase 3 | _assign_marks()呼び出し | 推奨馬番が変わる |
| 4 | Phase 4 | 推奨馬券の完全再現 | 最終的な馬券が変わる |
| 5 | Phase 5 | バリュー計算 | ☆マーク・追加推奨に必要 |
| 6 | Phase 6 | 検証 | 一致の証明 |

**全Phase完了後に初めて「GUIロジック完全一致」と呼べるバックテストになる。**
