# Gemini Q&A 回答まとめ・対応方針

**作成日**: 2026年2月24日
**前提資料**: `GEMINI_EVAL_RESPONSE_20260224.md` の相談1〜4 + 逆提言（SHAP）への回答

---

## 1. 相談1への回答：キャリブレーション手法の選択

### Geminiの回答要点

> 競馬（予測確率が0〜0.3に密集、サンプル数十万件）には
> **Isotonic Regression が圧倒的に適している**。
> Platt ScalingはS字カーブを強制するため競馬特有の分布歪みを吸収しきれない。

> 高確率帯（データが疎な50%+等）の対策として：
> 1. `scipy.ndimage.gaussian_filter1d` でスムージング後に適用
> 2. **「30%超はキャリブレーションしない（生の値を使う）ハイブリッド方式」** が実務的

### 採用する設計方針

```python
# 実装方針（Phase D-1 以降）
from sklearn.isotonic import IsotonicRegression

# 2024年検証データで学習（30%未満の帯のみ）
mask = (raw_proba_val < 0.30)
iso = IsotonicRegression(out_of_bounds='clip')
iso.fit(raw_proba_val[mask], target_val[mask])

# 予測時
def calibrate(p):
    if p >= 0.30:
        return p  # 高確率帯はそのまま（安全装置）
    return float(iso.predict([p])[0])
```

### ペーパートレード期間中の並行記録

- `pred_win` 列：生の確率（現在使用中・Rule4 判定に使用）
- `pred_win_calibrated` 列：補正後の確率（参考値として記録、**Rule4 判定には使わない**）
- 2〜3ヶ月後に「rawとcalibrated、どちらが的中馬をより正確に絞れたか」を比較検証

---

## 2. 相談2への回答：ライブトレード移行GO/NO-GO基準

### Geminiの回答要点

> 提示した4基準は「クオンツ運用の教科書に載せたいほど完璧」。
> 1点だけ追加したい：**「勝率の信頼区間の下限 > 損益分岐勝率」**

> 例：複勝平均オッズ2.5倍の場合、損益分岐勝率 = 40%
> 200件中88勝（44%）でも95%CI下限は37% → 損益分岐点40%を割る → まだ危険

### 更新後のGO/NO-GO基準

| 基準 | 条件 | 計算方法 |
|---|---|---|
| 1. 期間 | 2ヶ月（8週間）以上 | 暦日で計測 |
| 2. サンプル | 200件以上の確定ベット | `len(df[df.result != '未確定'])` |
| 3. 回収率 | 実績回収率 ≥ 100% | `(払戻合計) / (ベット合計)` |
| 4. ドローダウン | 最大DD < 15% | バックテスト基準4.2%の約3倍を上限に |
| 5. **統計的有意性（追加）** | 信頼区間下限 > 損益分岐勝率 | 下記参照 |

```python
# 基準5の計算例
import scipy.stats as stats

n_bets = 200          # ベット件数
n_hits = 88           # 的中件数
avg_odds = 2.5        # 平均オッズ
break_even_rate = 1 / avg_odds  # 損益分岐勝率 = 40%

# Clopper-Pearson信頼区間（95%）
ci_low, ci_high = stats.binom.ppf([0.025, 0.975], n_bets, n_hits/n_bets) / n_bets
# ci_low が break_even_rate を上回ればGO
go = ci_low > break_even_rate
print(f"95%CI下限: {ci_low:.1%}  損益分岐: {break_even_rate:.1%}  GO判定: {go}")
```

---

## 3. 相談3への回答：コンセプトドリフト検出

### Geminiの回答要点

> 月300件では的中率のKS検定はノイズだらけ。
> **PSI（Population Stability Index）が最も実用的で感度が高い。**
>
> バックテスト時の予測確率分布と直近1ヶ月の予測確率分布を比較。
> PSI > 0.2 でドリフトの疑いアラートを出す。

### PSI実装方針

```python
# PSI計算（月次モニタリング用）
import numpy as np

def calc_psi(expected, actual, bins=10):
    """
    expected: バックテスト時の予測確率分布（配列）
    actual:   直近1ヶ月の予測確率分布（配列）
    """
    breakpoints = np.linspace(0, 1, bins + 1)
    e_pct = np.histogram(expected, bins=breakpoints)[0] / len(expected)
    a_pct = np.histogram(actual,   bins=breakpoints)[0] / len(actual)
    e_pct = np.where(e_pct == 0, 1e-6, e_pct)  # ゼロ除算防止
    a_pct = np.where(a_pct == 0, 1e-6, a_pct)
    psi = np.sum((a_pct - e_pct) * np.log(a_pct / e_pct))
    return psi

# 判定基準
# PSI < 0.1  : 分布変化なし（正常）
# 0.1 ≤ PSI < 0.2 : 小さな変化（注意）
# PSI ≥ 0.2  : 大きな変化（ドリフトの疑い → モデル見直し検討）
```

月次モニタリングスクリプト（`paper_trade_review.py`）にPSI計算を組み込む予定。

---

## 4. 相談4への回答：オッズ収集スクリプトの設計

### Geminiの回答要点

| 項目 | 推奨 |
|---|---|
| レート制限 | **1リクエスト2〜3秒のsleep**（厳守） |
| スケジュール取得 | 朝7:00に「本日のレース一覧」を1回スクレイピング → レースID + 発走時刻を保存 |
| データ保存形式 | **SQLite（またはDuckDB）**。CSVは追記時破損リスクと集計クエリ速度が問題 |

### 設計方針（今週中に着手予定）

```
odds_collector/
  ├── schedule_fetch.py   # 朝7:00実行: 本日のレース一覧取得 → SQLiteに保存
  ├── odds_snapshot.py    # 発走30分前/5分前: 各レースのオッズを取得
  └── odds_timeseries.db  # SQLiteデータベース
      └── テーブル: odds_snapshots
          (race_id, horse_id, timing, odds_win, recorded_at)
```

タスクスケジューラ設定（土日のみ）:
```
07:00 → schedule_fetch.py  (レース一覧取得)
30分前 × 各レース → odds_snapshot.py  (オッズ取得)
```

---

## 5. 逆提言（SHAP GUI統合）への評価

### Geminiの評価

> **大賛成。神の一手。XAI（説明可能なAI）として馬券購入の納得感を劇的に高める。**
>
> - 速度：LightGBM TreeExplainer はC++最適化済み → 18頭×39特徴量で数十〜数百ms。問題なし
> - 表示方法：上位3〜5特徴量を「+要因/−要因」で表示するのが最も効果的
> - 推奨：「フェーズC-2の仕上げ」として組み込むべき

### GUI実装方針

```python
import shap

# GUIの予測処理に追加（predict_core 内）
explainer = shap.TreeExplainer(self.model_win)
shap_values = explainer.shap_values(feat_df)

# 上位3特徴量の寄与を取得
contributions = sorted(
    zip(model_features, shap_values[0]),
    key=lambda x: abs(x[1]), reverse=True
)[:3]

# 表示例: 「↑通算勝率 ↑芝勝率 ↓前走着順」
reason_parts = []
for feat, val in contributions:
    arrow = '↑' if val > 0 else '↓'
    # 特徴量名を日本語化するマッピングが必要
    reason_parts.append(f"{arrow}{feat_ja.get(feat, feat)}")
reason_str = ' '.join(reason_parts)
```

**実装タイミング**: Phase D-1（オッズドリフト特徴量追加）と同時に実施。
ペーパートレード期間中は現状のGUIで運用し、モデル再訓練のタイミングで統合する。

---

## 6. 本セッションで完了したコード修正

### 提言F — pandas FutureWarning 修正

| ファイル | 修正箇所 | 変更内容 |
|---|---|---|
| `keiba_prediction_gui_v3.py` | L152 | `fillna(3, inplace=True)` → `= .fillna(3)` |
| `backtest_full_2020_2025.py` | L65 | 同上 |

### 提言C + B — paper_trade_log.csv / paper_trade_add.py 更新

| 追加列 | 内容 |
|---|---|
| `bet_type` | `win` / `place` / `both` |
| `pred_win_calibrated` | キャリブレーション後の確率（参考値） |
| `kelly_theoretical` | フラクショナルKelly理論値（バンクロール基準、上限500円、記録専用） |

Kelly計算仕様：`bankroll × Kelly比率 × 0.25`（フラクショナルKelly）、100円単位切上げ。

---

## 7. 更新後の優先ロードマップ

### 今すぐ（本セッション完了済み）

- [x] 提言F: FutureWarning 修正（`keiba_prediction_gui_v3.py` / `backtest_full_2020_2025.py`）
- [x] 提言C: 複勝並行記録（`bet_type` 列追加）
- [x] 提言B: Kelly理論値列追加（バンクロール基準・記録専用）
- [x] 相談1〜4・SHAP提言の回答まとめドキュメント化

### 今週中

- [ ] **提言D**: バックアップファイル削除（本人確認後。推奨: 最新3件+月次版を残して削除）
- [ ] **提言E 着手**: `schedule_fetch.py` + `odds_snapshot.py` のシンプル版を作成
  （今週は「HTMLを保存するだけ」のバッチで十分）

### 今週末〜

- [ ] ペーパートレード開始（`paper_trade_add.py`）
  - `pred_win_calibrated` はしばらく空欄でOK
  - `kelly_theoretical` は毎回記録して推移を観察

### 1〜2ヶ月後

- [ ] **基準5（信頼区間）の計算実装**: `paper_trade_review.py` に組み込み
- [ ] **PSI計算実装**: バックテスト時の pred_win 分布を baseline として保存し、月次比較

### 3〜6ヶ月後

- [ ] **提言A 本実装**: Isotonic Regression キャリブレーション（ハイブリッド方式）
- [ ] **Phase D-1 + SHAP GUI統合**: オッズドリフト特徴量追加 + GUI予測根拠表示

### GO/NO-GO 判断（ライブトレード移行）

```
以下の全条件を満たした場合のみライブトレード移行を検討:
  1. 期間      2ヶ月以上
  2. サンプル  200件以上
  3. 回収率    100%以上
  4. 最大DD    15%未満
  5. 統計的有意 CI下限 > 損益分岐勝率
```

---

*作成: 2026年2月24日*
