# 馬の統計値の提案

## 📊 メインCSVに追加する統計列（案）

### コース適性
- `turf_starts` - 芝出走回数
- `turf_wins` - 芝勝利数
- `turf_win_rate` - 芝勝率
- `dirt_starts` - ダート出走回数
- `dirt_wins` - ダート勝利数
- `dirt_win_rate` - ダート勝率

### 距離適性
- `distance_1600_starts` - 1600m出走回数
- `distance_1600_win_rate` - 1600m勝率
- `distance_1800_starts` - 1800m出走回数
- `distance_1800_win_rate` - 1800m勝率
- `distance_2000_starts` - 2000m出走回数
- `distance_2000_win_rate` - 2000m勝率
- `distance_2400_starts` - 2400m出走回数
- `distance_2400_win_rate` - 2400m勝率

### レースレベル・経験
- `grade_race_starts` - 重賞（G1/G2/G3）出走回数
- `g1_starts` - G1出走回数
- `g1_wins` - G1勝利数
- `listed_race_starts` - オープン・リステッド戦出走回数
- `is_local_transfer` - 地方転入馬フラグ (0/1)
- `local_race_starts` - 地方競馬出走回数

### 走法・ペース適性
- `avg_passage_position` - 平均通過順位（小さいほど逃げ・先行）
- `running_style_category` - 走法カテゴリ（逃げ/先行/差し/追込）
- `avg_last_3f` - 平均上がり3F

### 馬場適性
- `heavy_track_starts` - 重・不良馬場出走回数
- `heavy_track_win_rate` - 重・不良馬場勝率

### 前走情報
- `prev_race_rank` - 前走着順
- `prev_race_date` - 前走日付
- `prev_race_name` - 前走レース名
- `prev_race_distance` - 前走距離
- `prev_race_course` - 前走コース種別
- `prev_race_place` - 前走競馬場
- `days_since_last_race` - 前走からの間隔（日数）

### 基本実績
- `total_starts` - 総出走回数
- `total_wins` - 総勝利数
- `total_win_rate` - 総合勝率
- `total_place_rate` - 連対率
- `total_show_rate` - 複勝率
- `total_earnings` - 獲得賞金（万円）

---

## ✅ 推奨する最小セット（20列程度）

まず以下を実装して、後で追加する方式はどうでしょうか？

### 必須統計値:
1. `total_starts` - 総出走回数
2. `total_win_rate` - 総合勝率
3. `turf_win_rate` - 芝勝率
4. `dirt_win_rate` - ダート勝率
5. `distance_similar_win_rate` - 同距離帯（±200m）勝率
6. `grade_race_starts` - 重賞出走回数
7. `is_local_transfer` - 地方転入フラグ
8. `avg_passage_position` - 平均通過順位
9. `running_style_category` - 走法カテゴリ
10. `prev_race_rank` - 前走着順
11. `prev_race_distance` - 前走距離
12. `days_since_last_race` - 前走からの間隔
13. `heavy_track_win_rate` - 重馬場勝率
14. `avg_last_3f` - 平均上がり3F
15. `total_earnings` - 獲得賞金

---

## 🤔 質問
1. 上記の推奨セットでOKですか？追加/削除したいものは？
2. 距離帯の区切り方は？（1600m, 1800m, 2000m, 2400m でOK？）
3. 走法カテゴリの判定基準は？（平均通過順位で自動判定？）
