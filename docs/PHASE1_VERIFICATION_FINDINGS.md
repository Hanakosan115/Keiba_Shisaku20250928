# Phase 1: 検証基盤構築 - 発見事項

**作成日**: 2026年2月21日
**フェーズ**: Phase 1 / 4
**ステータス**: 進行中

---

## 実施内容

### 1. 検証システム構築

以下の2つの検証ツールを開発:

1. **verify_gui_backtest_match.py**
   - GUI予測とバックテスト予測の完全一致を検証
   - 10レースでパイロット検証

2. **check_leakage.py**
   - データリーク検出システム
   - datetime.now()の不正使用を検出
   - predict_core()のcurrent_date未指定を検出

---

## データリーク検出結果

### 検出サマリー

**総検出数**: 8件
- **CRITICAL**: 1件
- **HIGH**: 7件

### 検出詳細

#### 1. backtest_gui_logic.py (4件)

| 行番号 | 重要度 | 内容 |
|:---:|:---:|:---|
| 164 | CRITICAL | MODE Bでdatetime.now()使用を許可 |
| 8, 58 | HIGH | コメント内のdatetime.now()記載 |
| 4 | HIGH | predict_core()説明内 |

**最重要問題**: MODE B設定

```python
if MODE == 'A':
    # モードA: リーケージ防止（レース日付でフィルタ）
    current_date_param = race_date
else:
    # モードB: GUI一致（datetime.now()使用 = 未来データも含む）
    current_date_param = None  # ← これが問題
```

**影響**:
- MODE Bを使用すると、predict_core()内でdatetime.now()が呼ばれる
- バックテスト時に「現在時刻」を基準にするため、レース時点では存在しなかった未来の馬データまでアクセス可能
- これがPhase 13の219%という非現実的な回収率の原因

#### 2. keiba_prediction_gui_v3.py (4件)

| 行番号 | 重要度 | 内容 | コンテキスト |
|:---:|:---:|:---|:---|
| 1656 | HIGH | `current_date = datetime.now().strftime('%Y-%m-%d')` | predict_core()内のデフォルト値設定 |
| 2388 | HIGH | `current_date = datetime.now().strftime('%Y-%m-%d')` | WIN5予測関数内 |
| 1647 | HIGH | docstring内の説明 | predict_core()のコメント |
| 2773 | LOW | `now = datetime.now()` | UI日付ピッカーの初期値（問題なし） |

**predict_core()のデフォルト動作**:

```python
def predict_core(self, race_id, horses, race_info, has_odds, current_date=None):
    if current_date is None:
        current_date = datetime.now().strftime('%Y-%m-%d')  # ← GUI用は問題ないが、バックテスト用は危険
```

- **GUI使用時**: current_date=Noneで呼ぶのは正常（実際に今日のレースを予測）
- **バックテスト時**: 必ずcurrent_date=race_dateを渡す必要あり

**WIN5予測の問題**:

```python
# WIN5予測関数（2388行目）
current_date = datetime.now().strftime('%Y-%m-%d')  # ← predict_core()を使っていない
```

- predict_core()メソッドを使わず独自実装
- datetime.now()を直接使用
- WIN5バックテスト時にもリーク発生

---

## 問題の根本原因

### Phase 13の219%回収率が非現実的な理由

1. **MODE B使用による未来データアクセス**
   ```
   バックテスト実行日: 2026年2月21日
   対象レース: 2024年1月1日

   MODE B使用時:
   - current_date = None
   - predict_core()内で datetime.now() = 2026-02-21
   - 2024年1月1日のレースなのに、2026年2月21日までの全データにアクセス
   - レース後2年分の未来データで予測 → 当然的中率が高い
   ```

2. **データリークの影響範囲**
   - 馬の2024-2026年の成績データ
   - 種牡馬の評価データ
   - コース適性データ
   - 全ての計算済み特徴量

3. **結果への影響**
   ```
   Phase 13 全確率帯バックテスト結果:
   - 40-50%確率帯: 219.1% (← 非現実的)
   - 35-40%確率帯: 166.2%
   - 全10確率帯: 100%超

   現実的な結果（予想）:
   - 優秀なモデル: 80-100%
   - 極めて優秀: 100-120%
   - 150%超: ほぼ確実にリークあり
   ```

---

## 修正方針

### 即座の修正（Phase 1完了に必要）

#### 1. backtest_gui_logic.py の修正

```python
# 修正前
if MODE == 'A':
    current_date_param = race_date
else:
    current_date_param = None

# 修正後
# MODE Bは削除。常にリーク防止モードを使用
current_date_param = race_date
```

#### 2. 検証の再実行

- MODE A固定でGUI/バックテスト一致検証
- 10レース全てで完全一致を確認
- 一致しない場合は差分を分析

### Phase 2での対応（Phase 13 再検証）

1. **クリーンバックテストの実行**
   - MODE A（リーク防止）で2024年全レース再検証
   - 真の回収率を算出
   - 現実的な結果（80-120%想定）を確認

2. **確率帯別の真の性能評価**
   - 各確率帯の本当の回収率
   - 219%が実際は何%だったのか
   - 実用可能な確率帯の特定

### Phase 3での対応（Phase 14 開発）

1. **WIN5予測の修正**
   - predict_core()を使用するようリファクタ
   - または current_dateパラメータを追加

2. **強制的なリークチェック**
   - 全バックテストスクリプトで check_leakage() 実行を必須化
   - CI/CDパイプラインに組み込み

---

## Phase 1 の成果物

### 作成したツール

1. **verify_gui_backtest_match.py** (357行)
   - GUI/バックテスト予測の完全一致検証
   - 10レースパイロット検証機能
   - JSON形式の詳細レポート出力

2. **check_leakage.py** (310行)
   - データリーク自動検出
   - datetime.now()使用箇所の特定
   - predict_core()のcurrent_date未指定検出
   - 重要度別レポート（CRITICAL/HIGH/MEDIUM/LOW）

### 生成されたレポート

1. **leakage_report_specific.txt**
   - 4ファイル、8件のリークポイント
   - ファイル別・重要度別の詳細

2. **phase1_pilot_verification.json** (実行中)
   - 10レースの検証結果
   - 一致/不一致の詳細

---

## 次のステップ（Phase 1完了後）

### 即座のアクション

1. ✅ リーク検出完了
2. 🔄 GUI/バックテスト一致検証実行中
3. ⏳ 検証結果の確認待ち
4. ⏳ backtest_gui_logic.py 修正（MODE B削除）
5. ⏳ 修正後の再検証

### Phase 2 準備

- Phase 13 クリーンバックテスト計画
- 2024年全レース（約3,200レース）の処理
- 確率帯別分析スクリプト

---

## 重要な教訓

### データリークの深刻性

```
リークなし（正しい）:
  2024年1月1日レース予測時
  → 2023年12月31日までのデータのみ使用
  → 現実的な回収率: 80-100%

リークあり（間違い）:
  2024年1月1日レース予測時
  → 2026年2月21日までのデータ使用
  → 非現実的な回収率: 150-250%
```

### MODE Bの危険性

- **設計意図**: GUIとの完全一致確認用
- **実際の影響**: 未来データアクセスを許可
- **結論**: 検証目的でも使用すべきでない

### 検証の重要性

- Phase 13の結果は2週間以上信じられていた
- 実運用していたら大きな損失の可能性
- 早期発見により被害を回避

---

**作成者**: Claude Opus 4.6
**最終更新**: 2026年2月21日
**次のアクション**: GUI/バックテスト検証結果の確認
