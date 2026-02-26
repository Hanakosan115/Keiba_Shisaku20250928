"""
全モデル性能比較スクリプト

全ての利用可能なモデルを最新データでテストし、
どれが最も優れているかを明確に示します。
"""

import pickle
import pandas as pd
import numpy as np
from pathlib import Path
import warnings
from data_config import MAIN_CSV
warnings.filterwarnings('ignore')

# テスト対象モデル（優先順位順）
MODELS_TO_TEST = [
    'lightgbm_model_trifecta_optimized_fixed.pkl',
    'lightgbm_model_trifecta_optimized.pkl',
    'lightgbm_model_advanced.pkl',
    'lightgbm_model_with_running_style.pkl',
    'lightgbm_model_tuned.pkl',
    'lightgbm_model.pkl',
]

def load_model(model_path):
    """モデルを読み込み"""
    try:
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
            # モデルだけ、または{model, features}の辞書形式
            if isinstance(model_data, dict) and 'model' in model_data:
                return model_data['model']
            return model_data
    except Exception as e:
        print(f"  [エラー] {model_path}: {e}")
        return None

def get_validation_races(df, year=2024, limit=500):
    """検証用レースデータを取得（最新レース）"""
    df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')

    # 指定年のレース
    target_races = df[
        (df['date_parsed'] >= f'{year}-01-01') &
        (df['date_parsed'] <= f'{year}-12-31')
    ]

    # 8頭以上のレースのみ
    race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

    # 最新から指定数取得
    race_ids = sorted(race_ids, reverse=True)[:limit]

    print(f"検証用レース: {len(race_ids)}レース（{year}年）")
    return race_ids

def get_race_data(df, race_id):
    """レースデータを取得"""
    race_horses = df[df['race_id'] == race_id].copy()
    race_horses = race_horses.sort_values('Umaban')
    return race_horses

def prepare_basic_features(race_horses):
    """基本的な特徴量を準備（簡易版）"""
    # 数値列のみ抽出
    exclude_cols = [
        'race_id', 'date', 'Umaban', 'Rank', 'Horse', 'Jockey', 'Trainer',
        'horse_id', 'jockey_id', 'trainer_id', 'date_parsed', 'Passage',
        'Race', 'Weather', 'RaceGround', 'RaceGroundCondition'
    ]

    feature_cols = []
    for col in race_horses.columns:
        if col in exclude_cols:
            continue
        # 数値型またはbool型
        if race_horses[col].dtype in ['int64', 'float64', 'bool']:
            feature_cols.append(col)

    X = race_horses[feature_cols].copy()

    # 欠損値を0埋め
    X = X.fillna(0)

    # 無限大を0に
    X = X.replace([np.inf, -np.inf], 0)

    return X

def predict_with_model(model, race_horses):
    """モデルで予測"""
    try:
        X = prepare_basic_features(race_horses)
        if X is None or len(X) == 0:
            return None

        # 予測
        predictions = model.predict(X)

        # 予測値を馬番と紐付け
        df_pred = race_horses[['Umaban', 'Rank']].copy()
        df_pred['score'] = predictions
        df_pred = df_pred.sort_values('score', ascending=False)

        return df_pred
    except Exception as e:
        # print(f"    [予測エラー] {e}")
        return None

def predict_by_odds(race_horses):
    """オッズベースの予測（ベースライン）"""
    if 'Odds' not in race_horses.columns:
        return None

    df_pred = race_horses[['Umaban', 'Rank', 'Odds']].copy()
    df_pred['score'] = 1.0 / (pd.to_numeric(df_pred['Odds'], errors='coerce') + 0.1)
    df_pred = df_pred.sort_values('score', ascending=False)

    return df_pred

def evaluate_predictions(df_pred, race_horses):
    """予測を評価"""
    if df_pred is None or len(df_pred) == 0:
        return None

    # 上位3頭を予測
    top3_pred = df_pred.head(3)['Umaban'].tolist()

    # 実際の結果（上位3着）
    actual_ranks = race_horses.copy()
    actual_ranks['Rank_num'] = pd.to_numeric(actual_ranks['Rank'], errors='coerce')
    actual_ranks = actual_ranks.dropna(subset=['Rank_num'])
    actual_ranks = actual_ranks.sort_values('Rank_num')

    if len(actual_ranks) < 3:
        return None

    top3_actual = actual_ranks.head(3)['Umaban'].tolist()

    # 的中判定
    hit_any = len(set(top3_pred) & set(top3_actual)) > 0  # 1頭でも当たり
    hit_2 = len(set(top3_pred) & set(top3_actual)) >= 2   # 2頭当たり
    hit_all = set(top3_pred) == set(top3_actual)          # 3頭完全的中

    return {
        'top3_pred': top3_pred,
        'top3_actual': top3_actual,
        'hit_any': hit_any,
        'hit_2': hit_2,
        'hit_all': hit_all
    }

def test_model(model_name, model, df_all, race_ids):
    """モデルをテスト"""
    print(f"\n{'='*60}")
    print(f"テスト中: {model_name}")
    print('='*60)

    results = []
    hit_any_count = 0
    hit_2_count = 0
    hit_all_count = 0
    valid_races = 0
    prediction_errors = 0

    for i, race_id in enumerate(race_ids):
        if (i + 1) % 100 == 0:
            print(f"  進捗: {i+1}/{len(race_ids)} レース")

        # レースデータ取得
        race_horses = get_race_data(df_all, race_id)
        if race_horses is None or len(race_horses) == 0:
            continue

        # 結果がないレースはスキップ
        race_horses['Rank_num'] = pd.to_numeric(race_horses['Rank'], errors='coerce')
        if race_horses['Rank_num'].isna().all():
            continue

        valid_races += 1

        # 予測
        if model == 'odds_only':
            df_pred = predict_by_odds(race_horses)
        else:
            df_pred = predict_with_model(model, race_horses)

        if df_pred is None:
            prediction_errors += 1
            continue

        # 評価
        eval_result = evaluate_predictions(df_pred, race_horses)
        if eval_result:
            results.append(eval_result)
            if eval_result['hit_any']:
                hit_any_count += 1
            if eval_result['hit_2']:
                hit_2_count += 1
            if eval_result['hit_all']:
                hit_all_count += 1

    # 結果集計
    print(f"\n[結果]")
    print(f"  有効レース数: {valid_races}")
    print(f"  予測成功: {valid_races - prediction_errors}")
    print(f"  予測エラー: {prediction_errors}")
    print(f"  1頭以上的中率: {hit_any_count}/{valid_races} ({100*hit_any_count/max(valid_races,1):.1f}%)")
    print(f"  2頭以上的中率: {hit_2_count}/{valid_races} ({100*hit_2_count/max(valid_races,1):.1f}%)")
    print(f"  3頭完全的中率: {hit_all_count}/{valid_races} ({100*hit_all_count/max(valid_races,1):.1f}%)")

    return {
        'model_name': model_name,
        'valid_races': valid_races,
        'prediction_success': valid_races - prediction_errors,
        'hit_any': hit_any_count,
        'hit_any_rate': 100 * hit_any_count / max(valid_races, 1),
        'hit_2': hit_2_count,
        'hit_2_rate': 100 * hit_2_count / max(valid_races, 1),
        'hit_all': hit_all_count,
        'hit_all_rate': 100 * hit_all_count / max(valid_races, 1),
    }

def main():
    print("="*60)
    print("全モデル性能比較")
    print("="*60)

    # データ読み込み
    print("\nデータ読み込み中...")
    df_all = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
    print(f"  総データ数: {len(df_all):,}行")

    # 検証用レース取得
    race_ids = get_validation_races(df_all, year=2024, limit=500)

    if len(race_ids) == 0:
        print("[エラー] 検証用レースが見つかりません")
        return

    # 全結果を保存
    all_results = []

    # 各モデルをテスト
    for model_path in MODELS_TO_TEST:
        if not Path(model_path).exists():
            print(f"\n[スキップ] {model_path} は存在しません")
            continue

        model = load_model(model_path)
        if model is None:
            continue

        result = test_model(model_path, model, df_all, race_ids)
        all_results.append(result)

    # オッズベースライン
    print(f"\n{'='*60}")
    print("テスト中: オッズベースライン（比較用）")
    print('='*60)
    result = test_model('odds_only', 'odds_only', df_all, race_ids)
    all_results.append(result)

    # 結果比較
    print("\n" + "="*60)
    print("総合比較")
    print("="*60)

    df_results = pd.DataFrame(all_results)
    df_results = df_results.sort_values('hit_2_rate', ascending=False)

    print("\n【2頭以上的中率でランキング】")
    for i, row in df_results.iterrows():
        print(f"\n{row['model_name']}")
        print(f"  予測成功率: {100*row['prediction_success']/max(row['valid_races'],1):.1f}%")
        print(f"  1頭以上的中: {row['hit_any_rate']:.1f}%")
        print(f"  2頭以上的中: {row['hit_2_rate']:.1f}%")
        print(f"  3頭完全的中: {row['hit_all_rate']:.1f}%")

    # 推奨モデル
    best_model = df_results.iloc[0]
    print("\n" + "="*60)
    print("【推奨モデル】")
    print("="*60)
    print(f"モデル: {best_model['model_name']}")
    print(f"2頭以上的中率: {best_model['hit_2_rate']:.1f}%")
    print(f"\n→ このモデルをkeiba_yosou_tool.pyで使用することを推奨")

    # CSV保存
    df_results.to_csv('model_comparison_results.csv', index=False, encoding='utf-8-sig')
    print("\n詳細結果を model_comparison_results.csv に保存しました")

if __name__ == '__main__':
    main()
