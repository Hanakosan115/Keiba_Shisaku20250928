# 3連単改善プラン

## 現状の問題

### 現在の的中率
- 3連単: **1.9-2.0%** ← 低すぎる
- 3連複: 7.4-9.0%

### 推定される問題点
1. **全馬を同じモデルで評価** → 1着馬と3着馬の違いを学習できていない
2. **絶対評価のみ** → 馬同士の相対的な力関係を考慮していない
3. **2着・3着の特徴が弱い** → 1着予測に特化してしまっている

---

## 改善戦略（3段階アプローチ）

### 【戦略1】位置別モデルの構築（短期・実装優先度: 高）

#### コンセプト
各着順に特化したモデルを個別に訓練

#### 実装
```python
# 3つの独立したモデル
model_1st = train_for_1st_place(df)  # 1着予測専用
model_2nd = train_for_2nd_place(df)  # 2着予測専用
model_3rd = train_for_3rd_place(df)  # 3着予測専用

# 予測時
prob_1st = model_1st.predict(X)
prob_2nd = model_2nd.predict(X)
prob_3rd = model_3rd.predict(X)

# 組み合わせて最適な3頭を選択
```

#### 期待効果
- 1着馬: 逃げ切り力・スピード重視
- 2着馬: 位置取りの良さ・安定性重視
- 3着馬: 追い込み力・粘り強さ重視

**期待的中率**: 2.0% → **3.5-4.0%**

---

### 【戦略2】ペアワイズ比較モデル（中期・実装優先度: 中）

#### コンセプト
「AとBならどちらが上位に来るか」を学習

#### 実装
```python
# 馬のペアごとに比較
def compare_horses(horse_A, horse_B):
    """horse_A > horse_B の確率を返す"""
    features = combine_features(horse_A, horse_B)
    return model_pairwise.predict(features)

# 全ペアで比較してランキング作成
ranking = create_ranking_from_pairwise_comparisons(horses)
```

#### 必要なデータ
- 同一レースでの相対的な着順
- 馬同士の過去の対戦成績（あれば）

**期待的中率**: 2.0% → **4.0-5.0%**

---

### 【戦略3】2着・3着特化特徴量の追加（短期・実装優先度: 高）

#### 新特徴量
1. **差し脚の強さ**
   - 最後の200mでの追い込み成功率
   - 後方から3着以内に入った割合

2. **位置取りの安定性**
   - コーナーでの位置変化の少なさ
   - 好位キープ率

3. **接戦での粘り強さ**
   - ハナ差・クビ差での勝率
   - 同タイム着での成績

4. **レースペースとの相性**
   - スローペース時の2-3着率
   - ハイペース時の差し成功率

#### 実装例
```python
def extract_position_specific_features(horse_past_races):
    """2着・3着に必要な特徴を抽出"""

    # 差し脚評価
    closing_success = 0
    for race in horse_past_races:
        if race['early_position'] > 8 and race['final_rank'] <= 3:
            closing_success += 1

    # 好位キープ率
    stable_position = 0
    for race in horse_past_races:
        position_change = abs(race['corner2_pos'] - race['corner3_pos'])
        if position_change <= 2:
            stable_position += 1

    return {
        'closing_success_rate': closing_success / len(horse_past_races),
        'stable_position_rate': stable_position / len(horse_past_races),
        # ... その他
    }
```

**期待的中率**: 2.0% → **3.0-3.5%**

---

### 【戦略4】アンサンブル予測（長期・実装優先度: 中）

#### 複数モデルの組み合わせ
```python
# 異なるアプローチのモデル
predictions_A = model_position_specific.predict(X)  # 位置別モデル
predictions_B = model_pairwise.predict(X)          # ペアワイズ
predictions_C = model_baseline.predict(X)          # ベースライン

# 加重平均またはVoting
final_prediction = weighted_average([predictions_A, predictions_B, predictions_C],
                                   weights=[0.5, 0.3, 0.2])
```

**期待的中率**: 2.0% → **5.0-6.0%**

---

## 実装ロードマップ

### Phase 1: クイックウィン（1-2週間）
1. ✅ 失敗パターン分析スクリプトの実行
2. ⏳ 2着・3着特化特徴量の追加（戦略3）
3. ⏳ データ確認と特徴量抽出ロジック実装
4. ⏳ モデル再訓練とバックテスト

**目標**: 3連単的中率 2.0% → 3.0%

### Phase 2: 位置別モデル（2-3週間）
1. ⏳ 1着・2着・3着それぞれの訓練データ作成
2. ⏳ 位置別モデルの訓練（戦略1）
3. ⏳ 組み合わせロジックの最適化
4. ⏳ バックテストと検証

**目標**: 3連単的中率 3.0% → 4.0%

### Phase 3: 高度な手法（1-2ヶ月）
1. ⏳ ペアワイズ比較モデルの実装（戦略2）
2. ⏳ アンサンブル学習（戦略4）
3. ⏳ ハイパーパラメータ最適化
4. ⏳ 最終検証

**目標**: 3連単的中率 4.0% → 5.0%+

---

## 必要なデータの優先度

### 既存データで実装可能（優先度: 高）
- ✅ Passage（位置取り）
- ✅ Agari（上がり3F）
- ✅ 過去着順
- ✅ 脚質分類

### 追加取得で大幅改善（優先度: 中）
- ⚠️ セクショナルタイム → Webスクレイピング必要
- ⚠️ ラップタイム → 有料データまたはスクレイピング
- ⚠️ 調教タイム → スクレイピング可能

### 長期的に検討（優先度: 低）
- ❌ パドック評価 → 画像解析必要
- ❌ 騎手コメント → NLP必要

---

## 期待される最終成果

### 保守的な目標
- 3連単的中率: 2.0% → **4.0%** (2倍)
- 3連複的中率: 7.4% → **12.0%** (1.6倍)

### 楽観的な目標（全戦略実装後）
- 3連単的中率: 2.0% → **6.0%** (3倍)
- 3連複的中率: 7.4% → **15.0%** (2倍)

### 回収率への影響
現在の脚質モデル（ワイド特化）:
- ワイド_1-2: 173.7%
- 3連単: （買わない方が良い）

改善後:
- ワイド_1-2: 170%前後（若干下がる可能性）
- **3連単**: **120-140%**（実用レベルに）
- **3連複BOX**: **130-150%**（実用レベルに）

---

## 次のアクション

1. **今すぐ実行**: 失敗パターン分析
   ```bash
   python analyze_trifecta_failures.py
   ```

2. **今週中**: 2着・3着特化特徴量の実装
   - 差し脚評価
   - 位置取り安定性
   - 接戦での粘り

3. **来週**: 位置別モデルのプロトタイプ作成

---

**作成日**: 2025-11-18
**目標**: 3連単的中率を2倍以上に改善
