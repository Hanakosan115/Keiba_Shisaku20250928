# Value Betting機能 統合完了

## 📦 新規追加ファイル

### 1. コアモジュール
**`value_betting_module.py`**
- Value Betting分析のコアロジック
- 各券種の配当推定関数
- 推奨ベット生成機能
- 他のツールから再利用可能

### 2. GUI統合版
**`keiba_yosou_tool_value_betting.py`**
- 既存のGUIツールにValue Betting機能を追加
- リアルタイムでValue分析表示
- 閾値・予算の調整可能
- 視覚的に推奨ベットを確認

### 3. CLI版
**`value_betting_cli.py`**
- コマンドラインから手軽に分析
- レースID指定で自動分析
- 手動入力モードあり
- バックテスト実行機能

### 4. バックテストスクリプト
- **`backtest_value_strategy.py`** - 単勝Value戦略
- **`backtest_place_value.py`** - 複勝Value戦略（★450%回収）
- **`backtest_exotic_bets.py`** - 馬連・3連単等
- **`verify_place_odds.py`** - 複勝オッズ推定検証

### 5. ドキュメント
- **`BACKTEST_SUMMARY.md`** - 全券種バックテスト結果サマリー
- **`VALUE_BETTING_README.md`** - このファイル

## 🚀 使い方

### GUI版（推奨）

```bash
# Value Betting対応GUIツール起動
python keiba_yosou_tool_value_betting.py
```

**機能:**
- レース選択 → 予測実行
- Value分析結果を自動表示
- 推奨ベット（複勝 + 3連単）を提示
- Value閾値・予算を調整可能

### CLI版

```bash
# レースID指定で分析
python value_betting_cli.py --race_id 202408010104

# 手動入力モード（オッズと予測順位を入力）
python value_betting_cli.py --manual

# バックテスト実行
python value_betting_cli.py --backtest

# 閾値・予算を指定
python value_betting_cli.py --race_id 202408010104 --threshold 5 --budget 10000
```

### バックテスト実行

```bash
# 単勝Value戦略
python backtest_value_strategy.py

# 複勝Value戦略（★450%回収）
python backtest_place_value.py

# 馬連・3連単等
python backtest_exotic_bets.py

# 複勝オッズ推定の検証
python verify_place_odds.py
```

## 📊 主要機能

### 1. Value計算
```python
from value_betting_module import ValueBettingAnalyzer

analyzer = ValueBettingAnalyzer(value_threshold=0.05)

# 予測順位とオッズからValue計算
values = analyzer.calculate_values(predicted_ranks, odds_list)
```

### 2. 推奨ベット生成
```python
# 馬データを準備
horses_data = [
    {'umaban': 1, 'odds': 45.4, 'predicted_rank': 1.2, ...},
    {'umaban': 2, 'odds': 8.5, 'predicted_rank': 3.5, ...},
    ...
]

# 推奨ベット生成
recommendations = analyzer.recommend_bets(horses_data, budget=10000)

# フォーマット表示
print(analyzer.format_recommendation(recommendations))
```

### 3. 配当推定
```python
# 複勝オッズ推定
place_odds = analyzer.estimate_place_odds(win_odds=45.4, num_horses=16)

# ワイド配当推定
wide_payout = analyzer.estimate_wide_payout(odds1=45.4, odds2=8.5)

# 3連単配当推定
sanrentan = analyzer.estimate_sanrentan_payout(odds1=45.4, odds2=8.5, odds3=12.3)
```

## 🎯 推奨戦略

### ポートフォリオ型アプローチ

**資金配分:**
- 複勝: 70% → 回収率450%、的中率18.9%
- 3連単: 30% → 回収率353%、的中率2.9%

**期待回収率: 421%**

### Value閾値設定

| 閾値 | ベット数 | 的中率 | 回収率 | 推奨 |
|------|----------|--------|--------|------|
| 0% | 488 | 12.1% | 278% | × (ベット多すぎ) |
| **5%** | **159** | **18.9%** | **450%** | ★★★★★ |
| 10% | 1 | 0% | 0% | × (ベット少なすぎ) |

**→ 閾値5%が最適**

## 📈 バックテスト結果（500レース）

| 券種 | 的中率 | 回収率 | 損益 | 評価 |
|------|--------|--------|------|------|
| **複勝** | **18.9%** | **450%** | **+55,644円** | ★★★★★ |
| **3連単** | 2.9% | 353% | +123,486円 | ★★★☆☆ |
| 単勝 | 1.9% | 113% | +2,030円 | ★★★☆☆ |
| 3連複 | 9.8% | 121% | +9,982円 | ★★☆☆☆ |
| 馬単 | 11.1% | 97% | -1,380円 | ★☆☆☆☆ |
| 馬連 | 19.3% | 84% | -7,740円 | ☆☆☆☆☆ |

## 🔧 既存ツールへの統合方法

### 方法1: モジュールとしてインポート

```python
from value_betting_module import ValueBettingAnalyzer

# 既存の予測コードの後に追加
analyzer = ValueBettingAnalyzer(value_threshold=0.05)

# Value計算
predicted_ranks = [...]  # モデルの予測結果
odds_list = [...]  # オッズリスト
values = analyzer.calculate_values(predicted_ranks, odds_list)

# 推奨ベット生成
recommendations = analyzer.recommend_bets(horses_data, budget=10000)
```

### 方法2: GUI版を直接使用

既存の`keiba_yosou_tool.py`の代わりに:

```bash
python keiba_yosou_tool_value_betting.py
```

### 方法3: CLI版をスクリプトから呼び出し

```python
import subprocess

result = subprocess.run([
    'python', 'value_betting_cli.py',
    '--race_id', race_id,
    '--threshold', '5',
    '--budget', '10000'
])
```

## 💡 カスタマイズ

### Value閾値の調整

```python
# 保守的（ベット数少ない、高Value馬のみ）
analyzer = ValueBettingAnalyzer(value_threshold=0.10)  # 10%

# 標準（推奨）
analyzer = ValueBettingAnalyzer(value_threshold=0.05)  # 5%

# アグレッシブ（ベット数多い）
analyzer = ValueBettingAnalyzer(value_threshold=0.00)  # 0%
```

### 資金配分の調整

```python
# 複勝のみ（安定重視）
recommendations = analyzer.recommend_bets(horses_data, budget=10000)
# → 複勝70%, 3連単30%で自動配分

# カスタム配分
fukusho_budget = 8000  # 80%
sanrentan_budget = 2000  # 20%
```

### 配当推定式の調整

`value_betting_module.py`の各`estimate_*_payout()`メソッドを編集:

```python
def estimate_place_odds(self, win_odds, num_horses=16):
    # オッズレンジごとの比率を調整
    if win_odds < 2.0:
        ratio = 0.15  # ← ここを調整
    # ...
```

## 🚨 注意事項

1. **複勝オッズは推定値**
   - 実際の複勝オッズデータがないため、単勝オッズから推定
   - 実運用時は実オッズを確認推奨

2. **過去データによる検証**
   - バックテストは500レースのみ
   - さらなるデータ蓄積が望ましい

3. **市場効率性の変化**
   - モデルが広く使われると効果が薄れる可能性
   - 定期的な再学習が必要

4. **資金管理の徹底**
   - 高回収率でも連敗はあり得る
   - 推奨予算内での運用

## 📁 ファイル一覧

```
Keiba_Shisaku20250928/
├── value_betting_module.py          # コアモジュール
├── keiba_yosou_tool_value_betting.py  # GUI版
├── value_betting_cli.py             # CLI版
├── backtest_value_strategy.py       # 単勝バックテスト
├── backtest_place_value.py          # 複勝バックテスト★
├── backtest_exotic_bets.py          # 馬連・3連単等
├── verify_place_odds.py             # オッズ推定検証
├── BACKTEST_SUMMARY.md              # 結果サマリー
└── VALUE_BETTING_README.md          # このファイル
```

## 🎓 次のステップ

1. **実オッズの取得**
   - 複勝・ワイドの実オッズをスクレイピング
   - 推定精度の向上

2. **データ拡充**
   - 500レース → 全2024年データ
   - 2025年データの追加

3. **リアルタイム化**
   - オッズAPI連携
   - 自動ベッティングシステム

4. **機械学習の改善**
   - Value予測モデルの構築
   - アンサンブル学習

---

**生成日:** 2024-12-02
**バージョン:** 1.0
**モデル:** lgbm_model_hybrid.pkl
