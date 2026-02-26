# Phase 13 D: predict_core()抽出とGUI/バックテスト統合計画

## 背景

現在、GUIの予測ロジックとバックテストの予測ロジックが分離しており、以下の問題があります:
- GUIを改善してもバックテストに自動反映されない
- コードの重複によるメンテナンス性の低下
- バックテストがGUIの動作を正しく再現できない可能性

## 目標

GUIとバックテストで完全に同一の予測ロジックを使用できるようにする。

## 実装手順

### D1: predict_core()メソッドの抽出

#### 現在の構造

`keiba_prediction_gui_v3.py` の `predict_race()` メソッド（1357-1846行）:
- レースデータ取得
- 各馬の特徴量計算
- モデルで予測
- 印の割り当て
- GUI表示処理

#### 新しい構造

`predict_core()`メソッドを追加:
```python
def predict_core(self, race_id, horses, race_info, has_odds, current_date=None):
    """
    UI非依存の予測コアロジック。GUIとバックテストの両方から呼ばれる。

    Args:
        race_id: レースID文字列
        horses: get_race_from_database()等が返す馬リスト
        race_info: レース情報dict
        has_odds: オッズ有無
        current_date: 'YYYY-MM-DD'文字列。Noneならdatetime.now()を使用。
                      バックテスト時はレース日付を渡してリーケージ防止。
    Returns:
        pd.DataFrame: 印付きdf_pred（'馬番','馬名','勝率予測','複勝予測','印','回収率優秀' 等全カラム）
    """
    # 1. current_date処理
    if current_date is None:
        current_date = datetime.now().strftime('%Y-%m-%d')

    # 2. 各馬の特徴量計算
    predictions = []
    for horse in horses:
        horse_id = horse.get('horse_id')
        if not horse_id:
            continue

        # 馬データ取得（race_id除外＋日付フィルタ）
        horse_data = self.df[self.df['horse_id'] == horse_id]
        horse_data = horse_data[horse_data['race_id'] != int(race_id)]

        # 日付フィルタ（リーケージ防止）
        horse_data['date_normalized'] = horse_data['date'].apply(normalize_date)
        horse_data_dates = pd.to_datetime(horse_data['date_normalized'], errors='coerce')
        cutoff = pd.to_datetime(current_date)
        horse_data = horse_data[horse_data_dates <= cutoff]

        # 特徴量計算
        features = calculate_horse_features_dynamic(...)

        # 予測
        pred_win = self.model_win.predict_proba(feat_df)[0, 1]
        pred_top3 = self.model_top3.predict_proba(feat_df)[0, 1]

        # 15-20%確率帯判定
        is_sweet_spot = (0.15 <= pred_win < 0.20)

        predictions.append({
            '馬番': horse['馬番'],
            '馬名': horse['馬名'],
            '勝率予測': pred_win,
            '複勝予測': pred_top3,
            '回収率優秀': is_sweet_spot,
            ...
        })

    # 3. DataFrame化
    df_pred = pd.DataFrame(predictions)
    df_pred = df_pred.sort_values('勝率予測', ascending=False)

    # 4. 印の割り当て
    df_pred = self._assign_marks(df_pred, has_odds)

    return df_pred
```

#### predict_race()のリファクタ

```python
def predict_race(self):
    # ... レースデータ取得部分は同じ ...

    # 予測実行（current_date=Noneで現在時刻を使用）
    df_pred = self.predict_core(race_id, horses, race_info, has_odds, current_date=None)

    # ... GUI表示処理は同じ ...
```

### D2: backtest_gui_logic.pyの全面書き換え

#### 現在の問題

- 独自の予測ロジックを実装しているため、GUIと乖離
- model_top3未使用
- 印の割り当てなし
- datetime.now()によるリーケージ

#### 新しい構造

```python
def run_backtest(start_ym, end_ym, max_races=None):
    # GUI準備
    root = tk.Tk()
    root.withdraw()
    gui = KeibaGUIv3(root)

    # レースID取得
    race_ids = get_race_ids_in_range(start_ym, end_ym)

    results = []
    for race_id in race_ids:
        # レースデータ取得
        horses, race_info = gui.get_race_from_database(str(int(race_id)))

        # レース日付取得（リーケージ防止）
        race_date = normalize_date(race_info.get('date', ''))

        has_odds = any(h.get('単勝オッズ', 0) > 0 for h in horses)

        # GUIと完全に同じ予測コアを呼ぶ
        df_pred = gui.predict_core(race_id, horses, race_info, has_odds,
                                    current_date=race_date)  # <- リーケージ防止

        # GUIと完全に同じ馬券推奨ロジック
        targets = KeibaGUIv3.get_recommended_bet_targets(df_pred, has_odds)

        # 払戻との照合
        # ... (既存のロジック) ...

    return results
```

## 検証方法

1. **GUI動作確認**:
   - レースID 202509050612 を予測
   - 修正前と同じ結果が出ることを確認

2. **単体レース照合**:
   - 同じレースIDで、バックテスト側の `predict_core()` 出力とGUI出力を比較
   - current_dateの差による微差は許容

3. **バックテスト実行**:
   - 100レースでバックテスト
   - 以下を確認:
     - `複勝予測` 列が存在（model_top3使用の証拠）
     - `印` 列が ◎○▲☆△注 を含む
     - `回収率優秀` 列が存在
     - 年による的中率の極端な偏りが解消

## 期待される効果

1. **コード品質向上**
   - 単一責任の原則: predict_core()は予測のみ
   - DRY原則: 予測ロジックの重複排除

2. **メンテナンス性向上**
   - GUIの改善が自動的にバックテストに反映
   - バグ修正が一箇所で済む

3. **信頼性向上**
   - バックテストがGUIの実際の動作を正確に再現
   - リーケージの完全防止

## 実装優先度

- 優先度: 中
- 理由: 現在のシステムは動作しているが、長期的なメンテナンス性のため重要
- 推奨タイミング: Phase 14で実装

## 関連ファイル

- `keiba_prediction_gui_v3.py` (約4000行)
- `backtest_gui_logic.py` (約300行)
- `.claude/plans/agile-wondering-wigderson.md` (元の計画)
