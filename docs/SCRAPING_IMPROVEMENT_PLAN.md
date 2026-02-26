# スクレイピング改善・検証プラン

## 現状確認

### 1. 既存スクレイピングの検証

**チェック項目:**
```python
□ ラップタイム取得できているか
□ コーナー毎の位置取り
□ 調教タイム
□ 馬具変更情報
□ 血統情報の完全性
□ 前走からの日数（休養期間）
```

**検証スクリプト作成:**
```python
# verify_scraping.py
- 最近のレースを1つ取得
- 全項目を表示
- 欠損をチェック
```

---

## Phase 1: ラップタイム取得（最優先）

### なぜ重要か
- ペース予想の基礎
- 前半3Fと後半3Fの比較でペース判定
- 馬の脚質をより正確に判定

### 取得元
**netkeibaのレース結果ページ:**
```
https://race.netkeiba.com/race/result.html?race_id=202411090411

ページ内の「ラップ」セクション:
  200m: 12.1 - 11.8 - 11.5 - ...
  400m: 23.9 - 23.3 - ...
  800m: 47.2 - 46.8 - ...
```

### 実装
```python
def scrape_lap_times(race_id):
    """ラップタイムを取得"""
    url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

    # HTMLから抽出
    lap_section = soup.find('div', class_='RaceData01')
    # ラップタイムをパース

    return {
        '200m_laps': [12.1, 11.8, 11.5, ...],
        '400m_laps': [23.9, 23.3, ...],
        'pace': 'slow' | 'medium' | 'fast'
    }
```

---

## Phase 2: 調教情報取得

### 重要性
- 馬の仕上がり状態
- 本気度（強めか軽めか）
- 調教師の意図

### 取得元
**馬の調教タブ:**
```
https://race.netkeiba.com/horse/training/調教タブ

取得項目:
  - 最終追い切り日
  - タイム
  - 調教評価（A, B, C等）
  - 併せ馬か単走か
```

---

## Phase 3: 位置取り詳細

### 現状
```python
現在: Passage = "5-5-4-3"
  → 序盤-中盤-終盤-最後の位置
```

### 改善
```python
詳細な位置取り:
  - 1コーナー
  - 2コーナー
  - 3コーナー
  - 4コーナー
  - 直線入口

→ より正確な脚質判定が可能
```

---

## Phase 4: 馬場差・バイアス情報

### 新規スクレイピング

**JRA公式の馬場情報:**
```
https://www.jra.go.jp/datafile/seiseki/...

取得項目:
  - 馬場含水率
  - 馬場状態（良/稍重/重/不良）の詳細
  - 開催週（何週目か）
```

**netkeiba馬場コメント:**
```
各レース後のコメント:
  "内有利"
  "外伸びる"
  "時計かかる"
  "高速馬場"
```

---

## Phase 5: 馬具変更

### 取得項目
```
- ブリンカー初装着
- メンコ使用
- シャドーロール
- チークピーシーズ

→ 気性面の変化を示唆
```

---

## 実装スケジュール

### Week 1: 検証
```
□ 現状のスクレイピング結果を確認
□ 欠損項目をリストアップ
□ 優先順位付け
```

### Week 2-3: ラップタイム実装
```
□ スクレイピングスクリプト作成
□ 過去データへの遡及適用
□ ペース判定ロジック実装
```

### Week 4: 展開予想実装
```
□ 脚質分布からペース予想
□ コース特性データベース作成
□ 開幕週判定ロジック
```

### Week 5-6: 追加データ
```
□ 調教情報
□ 馬場バイアス
□ 馬具変更
```

---

## データベース設計

### 新テーブル: race_pace
```sql
race_id         | レースID
lap_200m        | 200mラップタイム配列
lap_400m        | 400mラップタイム配列
first_3f        | 前半3F平均
last_3f         | 後半3F平均
pace_category   | slow/medium/fast
pace_index      | ペース指数
```

### 新テーブル: track_bias
```sql
date            | 日付
track_name      | 競馬場
course          | コース（芝1600mなど）
week_number     | 開催何週目
bias_type       | inner/outer/front/closer
bias_strength   | バイアスの強さ (1-5)
comment         | コメント
```

### 新テーブル: horse_training
```sql
horse_id        | 馬ID
date            | 調教日
time            | タイム
evaluation      | 評価 (A/B/C)
course_type     | 芝/ダート/坂路
horse_gear      | 馬具（ブリンカー等）
```

---

## 特徴量の追加

### 展開予想関連（+10次元）
```python
# レース全体の特徴
escape_horse_count      # 逃げ馬の数
leading_horse_count     # 先行馬の数
expected_pace           # 予想ペース (0-1)
pace_match_score        # 馬の脚質とペースの相性

# コース特性
course_bias_front       # 前有利度
course_bias_inner       # 内有利度
track_week_number       # 開催何週目
track_condition_trend   # 馬場状態トレンド

# 相対的位置
expected_position       # 予想位置取り
position_advantage      # 位置取り有利度
```

### 馬場関連（+5次元）
```python
track_moisture          # 馬場含水率
track_speed_index       # 馬場スピード指数
prev_day_condition      # 前日の馬場状態
condition_change        # 馬場状態変化
track_bias_match        # 馬場バイアスとの相性
```

### 調教関連（+3次元）
```python
training_evaluation     # 調教評価
days_since_training     # 調教からの日数
gear_change             # 馬具変更フラグ
```

---

## 期待される効果

### ペース・展開予想の追加
```
推定的中率向上: +8-12%
理由: プロ予想家も最重視する要素
```

### 馬場バイアスの考慮
```
推定的中率向上: +3-5%
理由: 開幕週と最終週で大きく変わる
```

### 調教情報の活用
```
推定的中率向上: +2-3%
理由: 仕上がり状態の把握
```

**総合推定:**
```
現在: 24.2%（ワイド1-3）
改善後: 35-45%を目標
回収率: 95-105%
```

---

## リスクと対策

### リスク1: スクレイピング負荷
**対策:**
- 適切な間隔（2-3秒）
- User-Agent設定
- エラーハンドリング

### リスク2: データ量増加
**対策:**
- 重要な項目から段階的に
- 古いデータは省略

### リスク3: 複雑化
**対策:**
- シンプルなロジックから
- 効果測定しながら追加

---

## まとめ

**最優先:**
1. ラップタイム取得
2. ペース予想実装
3. コース特性データベース

**これらが最も効果が高い！**
