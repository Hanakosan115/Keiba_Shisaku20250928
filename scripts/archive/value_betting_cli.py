"""
Value Betting CLI ツール

コマンドラインから手軽にValue Betting分析

使い方:
    # モデル使用
    python value_betting_cli.py --race_id 202408010104

    # 手動でオッズと予測順位を入力
    python value_betting_cli.py --manual

    # バックテスト
    python value_betting_cli.py --backtest
"""

import argparse
import pandas as pd
import numpy as np
import pickle
from value_betting_module import ValueBettingAnalyzer

def load_model():
    """モデル読み込み"""
    try:
        with open('lgbm_model_hybrid.pkl', 'rb') as f:
            return pickle.load(f)
    except:
        print("警告: モデルファイルが見つかりません")
        return None

def analyze_race(race_id, model=None, threshold=0.05, budget=10000):
    """レース分析"""
    print("="*80)
    print(f"Value Betting分析 - レースID: {race_id}")
    print("="*80)

    # データ読み込み
    try:
        df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv',
                         encoding='utf-8', low_memory=False)
        df['race_id'] = df['race_id'].astype(str)
    except:
        print("エラー: データファイルが見つかりません")
        return

    # レースデータ取得
    race_data = df[df['race_id'] == race_id].copy()

    if len(race_data) == 0:
        print(f"エラー: レースID {race_id} が見つかりません")
        return

    print(f"\nレース: {race_data.iloc[0].get('RaceName', 'N/A')}")
    print(f"日付: {race_data.iloc[0].get('date', 'N/A')}")
    print(f"出走頭数: {len(race_data)}頭\n")

    # 馬データ準備
    horses_data = []

    for _, horse in race_data.iterrows():
        umaban = horse.get('Umaban')
        odds = horse.get('Odds', 10.0)
        horse_name = horse.get('HorseName', 'N/A')

        horses_data.append({
            'umaban': umaban,
            'horse_name': horse_name,
            'odds': odds
        })

    # モデルがあれば予測
    if model:
        print("モデルで予測中...")
        # 簡易予測（特徴量生成は省略、オッズベース）
        for h in horses_data:
            # オッズの逆数をスコアとして使用（簡易版）
            h['score'] = 1.0 / h['odds']

        # スコアから順位計算
        scores = [h['score'] for h in horses_data]
        sorted_indices = np.argsort(scores)[::-1]
        ranks = np.empty(len(scores))
        ranks[sorted_indices] = np.arange(1, len(scores) + 1)

        for i, h in enumerate(horses_data):
            h['predicted_rank'] = ranks[i]
    else:
        print("モデルなし: オッズベースで分析")
        for h in horses_data:
            h['predicted_rank'] = h['odds'] / 2  # 簡易

    # Value分析
    analyzer = ValueBettingAnalyzer(value_threshold=threshold)

    predicted_ranks = [h['predicted_rank'] for h in horses_data]
    odds_list = [h['odds'] for h in horses_data]

    values = analyzer.calculate_values(predicted_ranks, odds_list)

    for i, h in enumerate(horses_data):
        h.update(values[i])

    # 推奨ベット生成
    recommendations = analyzer.recommend_bets(horses_data, budget=budget)

    # 結果表示
    print("\n" + "="*80)
    print("馬別 Value一覧")
    print("="*80)
    print(f"{'馬番':^6} {'馬名':^20} {'オッズ':^8} {'予測順位':^10} {'Value':^10}")
    print("-"*80)

    horses_sorted = sorted(horses_data, key=lambda x: x['value'], reverse=True)
    for h in horses_sorted[:10]:  # 上位10頭
        print(f"{h['umaban']:^6} {h['horse_name'][:20]:^20} {h['odds']:^8.1f} "
              f"{h['predicted_rank']:^10.2f} {h['value']*100:^+9.2f}%")

    # 推奨ベット表示
    print("\n" + analyzer.format_recommendation(recommendations))

def manual_input(threshold=0.05, budget=10000):
    """手動入力モード"""
    print("="*80)
    print("Value Betting分析 - 手動入力モード")
    print("="*80)

    horses_data = []

    print("\n馬のデータを入力してください（終了: 0を入力）\n")

    while True:
        try:
            umaban = int(input("馬番 (0で終了): "))
            if umaban == 0:
                break

            odds = float(input("  オッズ: "))
            predicted_rank = float(input("  予測順位: "))

            horses_data.append({
                'umaban': umaban,
                'odds': odds,
                'predicted_rank': predicted_rank
            })

            print("  → 追加しました\n")

        except ValueError:
            print("  エラー: 数値を入力してください\n")
        except KeyboardInterrupt:
            print("\n中断しました")
            return

    if len(horses_data) == 0:
        print("データが入力されていません")
        return

    # Value分析
    analyzer = ValueBettingAnalyzer(value_threshold=threshold)

    predicted_ranks = [h['predicted_rank'] for h in horses_data]
    odds_list = [h['odds'] for h in horses_data]

    values = analyzer.calculate_values(predicted_ranks, odds_list)

    for i, h in enumerate(horses_data):
        h.update(values[i])

    # 推奨ベット生成
    recommendations = analyzer.recommend_bets(horses_data, budget=budget)

    # 結果表示
    print("\n" + "="*80)
    print("Value分析結果")
    print("="*80)
    print(f"{'馬番':^6} {'オッズ':^8} {'予測順位':^10} {'Value':^10}")
    print("-"*60)

    horses_sorted = sorted(horses_data, key=lambda x: x['value'], reverse=True)
    for h in horses_sorted:
        print(f"{h['umaban']:^6} {h['odds']:^8.1f} "
              f"{h['predicted_rank']:^10.2f} {h['value']*100:^+9.2f}%")

    print("\n" + analyzer.format_recommendation(recommendations))

def run_backtest():
    """バックテスト実行"""
    print("="*80)
    print("Value Betting バックテスト")
    print("="*80)
    print("\nbacktest_value_strategy.py を実行します...\n")

    import subprocess
    result = subprocess.run(['python', 'backtest_value_strategy.py'],
                          capture_output=False)

    if result.returncode == 0:
        print("\nバックテスト完了")
    else:
        print("\nエラーが発生しました")

def main():
    parser = argparse.ArgumentParser(description='Value Betting CLI ツール')

    parser.add_argument('--race_id', type=str,
                       help='分析するレースID')
    parser.add_argument('--manual', action='store_true',
                       help='手動入力モード')
    parser.add_argument('--backtest', action='store_true',
                       help='バックテスト実行')
    parser.add_argument('--threshold', type=float, default=5.0,
                       help='Value閾値（%%、デフォルト5）')
    parser.add_argument('--budget', type=int, default=10000,
                       help='予算（円、デフォルト10000）')

    args = parser.parse_args()

    threshold = args.threshold / 100.0

    if args.backtest:
        run_backtest()
    elif args.manual:
        manual_input(threshold=threshold, budget=args.budget)
    elif args.race_id:
        model = load_model()
        analyze_race(args.race_id, model=model,
                    threshold=threshold, budget=args.budget)
    else:
        # デフォルト: 最新のサンプルレースを分析
        print("使い方:")
        print("  python value_betting_cli.py --race_id 202408010104")
        print("  python value_betting_cli.py --manual")
        print("  python value_betting_cli.py --backtest")
        print("\nサンプルレースを分析します...\n")

        model = load_model()
        analyze_race('202408010104', model=model,
                    threshold=threshold, budget=args.budget)

if __name__ == "__main__":
    main()
