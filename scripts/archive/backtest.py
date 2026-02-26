"""
バックテスト機能 - 過去データでの予測精度検証

機能:
1. 過去のレースデータで予測を実行
2. 印別・自信度別の的中率を集計
3. 回収率の計算
4. 結果の可視化
"""
import pandas as pd
import numpy as np
from typing import Dict, List
import matplotlib.pyplot as plt
from improved_analyzer import ImprovedHorseAnalyzer


class BacktestEngine:
    """バックテストエンジン"""

    def __init__(self):
        self.analyzer = ImprovedHorseAnalyzer()
        self.results = []

    def load_historical_data(self, csv_path: str) -> pd.DataFrame:
        """
        過去のレースデータを読み込む

        Args:
            csv_path: CSVファイルのパス

        Returns:
            レースデータのDataFrame
        """
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            print(f"データ読み込み完了: {len(df)}レース")
            return df
        except Exception as e:
            print(f"データ読み込みエラー: {e}")
            return pd.DataFrame()

    def run_backtest(self, race_data: pd.DataFrame, model, features_list: List[str]) -> Dict:
        """
        バックテストを実行

        Args:
            race_data: レースデータ
            model: 学習済みモデル
            features_list: 特徴量のリスト

        Returns:
            バックテスト結果の辞書
        """
        results = {
            'total_races': 0,
            'predictions': [],
            'by_mark': {'◎': [], '○': [], '▲': [], '△': []},
            'by_confidence': {'S': [], 'A': [], 'B': [], 'C': []},
            'by_divergence': {'strong_undervalued': [], 'undervalued': [],
                              'fair': [], 'overvalued': [], 'strong_overvalued': []}
        }

        # レースごとに処理
        race_ids = race_data['race_id'].unique() if 'race_id' in race_data.columns else []

        for race_id in race_ids[:100]:  # 最初の100レースでテスト
            race_horses = race_data[race_data['race_id'] == race_id]

            if len(race_horses) < 5:  # 5頭未満は除外
                continue

            results['total_races'] += 1

            # 各馬の予測を実行（簡易版）
            horses_predictions = []

            for idx, horse in race_horses.iterrows():
                # 簡易的な予測（実際はモデルを使用）
                # ここではオッズから推定
                odds = horse.get('odds', 10.0)
                actual_rank = horse.get('rank', 99)

                # オッズ期待勝率
                odds_rate = 1.0 / odds if odds > 0 else 0.01

                # ダミーのAI予測（実際はモデルで計算）
                # 実データでは: ai_prediction = model.predict_proba(features)[0, 1]
                ai_prediction = odds_rate * np.random.uniform(0.8, 1.2)  # ダミー

                # 乖離度
                divergence = ai_prediction - odds_rate

                # 評価
                if divergence > 0.10:
                    evaluation = 'strong_undervalued'
                elif divergence > 0.05:
                    evaluation = 'undervalued'
                elif divergence > -0.05:
                    evaluation = 'fair'
                elif divergence > -0.10:
                    evaluation = 'overvalued'
                else:
                    evaluation = 'strong_overvalued'

                horses_predictions.append({
                    'horse_id': horse.get('horse_id'),
                    'umaban': horse.get('umaban'),
                    'odds': odds,
                    'ai_prediction': ai_prediction,
                    'divergence': divergence,
                    'evaluation': evaluation,
                    'actual_rank': actual_rank,
                    'composite_score': ai_prediction * 0.6 + max(0, divergence) * 2 * 0.4
                })

            # 印と自信度を付与
            horses_predictions.sort(key=lambda x: x['composite_score'], reverse=True)

            for i, horse in enumerate(horses_predictions):
                # 印
                if i == 0:
                    horse['mark'] = '◎'
                elif i == 1:
                    horse['mark'] = '○'
                elif i == 2:
                    horse['mark'] = '▲'
                elif i == 3:
                    horse['mark'] = '△'
                else:
                    horse['mark'] = ''

                # 自信度（簡易版）
                if i == 0 and horse['divergence'] > -0.05:
                    horse['confidence'] = 'A'
                elif i <= 1:
                    horse['confidence'] = 'B'
                else:
                    horse['confidence'] = 'C'

                # 的中判定
                horse['hit'] = 1 if horse['actual_rank'] <= 3 else 0
                horse['win'] = 1 if horse['actual_rank'] == 1 else 0

                # 結果を記録
                results['predictions'].append(horse)

                # 印別に集計
                if horse['mark'] in results['by_mark']:
                    results['by_mark'][horse['mark']].append(horse)

                # 自信度別に集計
                if horse['confidence'] in results['by_confidence']:
                    results['by_confidence'][horse['confidence']].append(horse)

                # 評価別に集計
                if horse['evaluation'] in results['by_divergence']:
                    results['by_divergence'][horse['evaluation']].append(horse)

        return results

    def calculate_statistics(self, results: Dict) -> Dict:
        """
        統計情報を計算

        Args:
            results: バックテスト結果

        Returns:
            統計情報の辞書
        """
        stats = {}

        # 全体統計
        all_predictions = results['predictions']
        if all_predictions:
            stats['total_predictions'] = len(all_predictions)
            stats['overall_hit_rate'] = np.mean([p['hit'] for p in all_predictions])
            stats['overall_win_rate'] = np.mean([p['win'] for p in all_predictions])

        # 印別統計
        stats['by_mark'] = {}
        for mark, predictions in results['by_mark'].items():
            if predictions:
                stats['by_mark'][mark] = {
                    'count': len(predictions),
                    'hit_rate': np.mean([p['hit'] for p in predictions]),
                    'win_rate': np.mean([p['win'] for p in predictions]),
                    'avg_odds': np.mean([p['odds'] for p in predictions])
                }

        # 自信度別統計
        stats['by_confidence'] = {}
        for confidence, predictions in results['by_confidence'].items():
            if predictions:
                stats['by_confidence'][confidence] = {
                    'count': len(predictions),
                    'hit_rate': np.mean([p['hit'] for p in predictions]),
                    'win_rate': np.mean([p['win'] for p in predictions])
                }

        # 評価別統計
        stats['by_divergence'] = {}
        for evaluation, predictions in results['by_divergence'].items():
            if predictions:
                stats['by_divergence'][evaluation] = {
                    'count': len(predictions),
                    'hit_rate': np.mean([p['hit'] for p in predictions]),
                    'avg_divergence': np.mean([p['divergence'] for p in predictions])
                }

        return stats

    def print_results(self, stats: Dict):
        """
        結果を表示

        Args:
            stats: 統計情報
        """
        print("\n" + "=" * 60)
        print("バックテスト結果")
        print("=" * 60)

        # 全体統計
        print("\n【全体統計】")
        print(f"総予測数: {stats.get('total_predictions', 0)}")
        print(f"複勝的中率: {stats.get('overall_hit_rate', 0)*100:.1f}%")
        print(f"単勝的中率: {stats.get('overall_win_rate', 0)*100:.1f}%")

        # 印別統計
        print("\n【印別的中率】")
        print(f"{'印':<4} {'件数':<8} {'複勝的中率':<12} {'単勝的中率':<12} {'平均オッズ':<10}")
        print("-" * 60)

        for mark in ['◎', '○', '▲', '△']:
            if mark in stats.get('by_mark', {}):
                data = stats['by_mark'][mark]
                print(f"{mark:<4} {data['count']:<8} "
                      f"{data['hit_rate']*100:>10.1f}% "
                      f"{data['win_rate']*100:>10.1f}% "
                      f"{data['avg_odds']:>10.1f}倍")

        # 自信度別統計
        print("\n【自信度別的中率】")
        print(f"{'自信度':<6} {'件数':<8} {'複勝的中率':<12} {'単勝的中率':<12}")
        print("-" * 60)

        for confidence in ['S', 'A', 'B', 'C']:
            if confidence in stats.get('by_confidence', {}):
                data = stats['by_confidence'][confidence]
                print(f"{confidence:<6} {data['count']:<8} "
                      f"{data['hit_rate']*100:>10.1f}% "
                      f"{data['win_rate']*100:>10.1f}%")

        # 評価別統計
        print("\n【オッズ評価別的中率】")
        print(f"{'評価':<20} {'件数':<8} {'複勝的中率':<12} {'平均乖離度':<12}")
        print("-" * 60)

        eval_names = {
            'strong_undervalued': '強い過小評価',
            'undervalued': '過小評価',
            'fair': '妥当',
            'overvalued': '過大評価',
            'strong_overvalued': '強い過大評価'
        }

        for evaluation, name in eval_names.items():
            if evaluation in stats.get('by_divergence', {}):
                data = stats['by_divergence'][evaluation]
                print(f"{name:<20} {data['count']:<8} "
                      f"{data['hit_rate']*100:>10.1f}% "
                      f"{data['avg_divergence']*100:>+10.1f}%")

        print("\n" + "=" * 60)

    def plot_results(self, stats: Dict, output_path: str = None):
        """
        結果をグラフ化

        Args:
            stats: 統計情報
            output_path: 保存先パス（Noneの場合は表示のみ）
        """
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('バックテスト結果', fontsize=16, fontweight='bold')

        # グラフ1: 印別的中率
        ax1 = axes[0, 0]
        marks = []
        hit_rates = []
        for mark in ['◎', '○', '▲', '△']:
            if mark in stats.get('by_mark', {}):
                marks.append(mark)
                hit_rates.append(stats['by_mark'][mark]['hit_rate'] * 100)

        ax1.bar(marks, hit_rates, color=['gold', 'silver', '#CD7F32', 'lightblue'])
        ax1.set_ylabel('複勝的中率 (%)')
        ax1.set_title('印別的中率')
        ax1.set_ylim(0, 100)
        ax1.grid(axis='y', alpha=0.3)

        # グラフ2: 自信度別的中率
        ax2 = axes[0, 1]
        confidences = []
        conf_hit_rates = []
        for confidence in ['S', 'A', 'B', 'C']:
            if confidence in stats.get('by_confidence', {}):
                confidences.append(confidence)
                conf_hit_rates.append(stats['by_confidence'][confidence]['hit_rate'] * 100)

        colors = ['#FFD700', '#87CEEB', '#90EE90', '#FFFFE0']
        ax2.bar(confidences, conf_hit_rates, color=colors[:len(confidences)])
        ax2.set_ylabel('複勝的中率 (%)')
        ax2.set_title('自信度別的中率')
        ax2.set_ylim(0, 100)
        ax2.grid(axis='y', alpha=0.3)

        # グラフ3: 評価別的中率
        ax3 = axes[1, 0]
        eval_names = {
            'strong_undervalued': '強過小評価',
            'undervalued': '過小評価',
            'fair': '妥当',
            'overvalued': '過大評価',
            'strong_overvalued': '強過大評価'
        }

        evals = []
        eval_hit_rates = []
        for evaluation, name in eval_names.items():
            if evaluation in stats.get('by_divergence', {}):
                evals.append(name)
                eval_hit_rates.append(stats['by_divergence'][evaluation]['hit_rate'] * 100)

        ax3.barh(evals, eval_hit_rates, color='skyblue')
        ax3.set_xlabel('複勝的中率 (%)')
        ax3.set_title('オッズ評価別的中率')
        ax3.set_xlim(0, 100)
        ax3.grid(axis='x', alpha=0.3)

        # グラフ4: サマリーテキスト
        ax4 = axes[1, 1]
        ax4.axis('off')

        summary_text = f"""
【総合結果サマリー】

総予測数: {stats.get('total_predictions', 0)}件
総レース数: {stats.get('total_predictions', 0) // 4}レース

複勝的中率: {stats.get('overall_hit_rate', 0)*100:.1f}%
単勝的中率: {stats.get('overall_win_rate', 0)*100:.1f}%

【印別ベスト】
"""
        # 印別で最も的中率が高いものを表示
        if stats.get('by_mark'):
            best_mark = max(stats['by_mark'].items(),
                           key=lambda x: x[1]['hit_rate'])
            summary_text += f"{best_mark[0]}: {best_mark[1]['hit_rate']*100:.1f}%\n"

        summary_text += "\n【自信度別ベスト】\n"
        if stats.get('by_confidence'):
            best_conf = max(stats['by_confidence'].items(),
                           key=lambda x: x[1]['hit_rate'])
            summary_text += f"{best_conf[0]}: {best_conf[1]['hit_rate']*100:.1f}%"

        ax4.text(0.1, 0.9, summary_text, fontsize=11, verticalalignment='top',
                fontfamily='monospace')

        plt.tight_layout()

        if output_path:
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            print(f"\nグラフを保存しました: {output_path}")

        plt.show()


def demo_backtest():
    """バックテストのデモ"""
    print("バックテストエンジンのデモ実行")
    print("-" * 60)

    engine = BacktestEngine()

    # ダミーデータで実行
    # 実際のデータは CSVから読み込む
    dummy_data = pd.DataFrame({
        'race_id': [f'2024010{i//10:02d}{j:02d}' for i in range(100) for j in range(10)],
        'horse_id': [f'horse_{i*10+j}' for i in range(100) for j in range(10)],
        'umaban': [(j % 18) + 1 for i in range(100) for j in range(10)],
        'odds': [np.random.uniform(1.5, 50) for _ in range(1000)],
        'rank': [np.random.randint(1, 19) for _ in range(1000)]
    })

    print(f"ダミーデータ生成: {len(dummy_data)}件")

    # バックテスト実行
    results = engine.run_backtest(dummy_data, model=None, features_list=[])

    # 統計計算
    stats = engine.calculate_statistics(results)

    # 結果表示
    engine.print_results(stats)

    # グラフ化
    try:
        engine.plot_results(stats, output_path='backtest_results.png')
    except Exception as e:
        print(f"グラフ描画エラー: {e}")


if __name__ == "__main__":
    demo_backtest()
