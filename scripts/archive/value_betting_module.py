"""
Value Betting戦略モジュール

既存の競馬予想ツールに統合可能なモジュール
"""

import numpy as np
import pandas as pd

class ValueBettingAnalyzer:
    """Value Betting分析クラス"""

    def __init__(self, value_threshold=0.05):
        """
        Args:
            value_threshold: Value閾値（デフォルト5%）
        """
        self.value_threshold = value_threshold

    def calculate_values(self, predicted_ranks, odds_list):
        """
        予測順位とオッズからValue値を計算

        Args:
            predicted_ranks: 予測順位リスト
            odds_list: 単勝オッズリスト

        Returns:
            各馬のValue情報リスト
        """
        # 予測順位をスコアに変換（順位が良いほど高スコア）
        scores = np.array([1.0 / max(rank, 1.0) for rank in predicted_ranks])
        predicted_probs = scores / scores.sum()

        # 市場確率（オッズから逆算）
        market_probs = np.array([1.0 / odds for odds in odds_list])

        # Value = 予測確率 - 市場確率
        values = predicted_probs - market_probs

        return [{
            'predicted_prob': float(pred_prob),
            'market_prob': float(mkt_prob),
            'value': float(val),
            'value_pct': float(val * 100)
        } for pred_prob, mkt_prob, val in zip(predicted_probs, market_probs, values)]

    def get_value_bets(self, horses_data):
        """
        Value閾値を超える馬を抽出

        Args:
            horses_data: 馬のデータリスト（各要素にvalue情報含む）

        Returns:
            Value閾値を超える馬のリスト
        """
        return [h for h in horses_data if h.get('value', 0) >= self.value_threshold]

    def estimate_place_odds(self, win_odds, num_horses=16):
        """
        単勝オッズから複勝オッズを推定

        Args:
            win_odds: 単勝オッズ
            num_horses: 出走頭数

        Returns:
            推定複勝オッズ
        """
        # オッズレンジごとに異なる比率
        if win_odds < 2.0:
            ratio = 0.15  # 1番人気クラス
        elif win_odds < 5.0:
            ratio = 0.20  # 2-3番人気クラス
        elif win_odds < 10.0:
            ratio = 0.25  # 4-5番人気クラス
        elif win_odds < 20.0:
            ratio = 0.30  # 中穴クラス
        else:
            ratio = 0.35  # 大穴クラス

        place_odds = win_odds * ratio
        return max(place_odds, 1.1)

    def estimate_wide_payout(self, odds1, odds2):
        """
        ワイドの理論配当を推定

        Args:
            odds1, odds2: 2頭の単勝オッズ

        Returns:
            推定ワイド配当倍率
        """
        prob1 = 1.0 / odds1
        prob2 = 1.0 / odds2

        # 各馬の3着以内確率（簡易計算）
        place_prob1 = min(prob1 * 3, 0.5)
        place_prob2 = min(prob2 * 3, 0.3)

        combined_prob = place_prob1 * place_prob2 * 2

        payout = (0.75 / combined_prob) if combined_prob > 0 else 50

        return max(payout, 1.5)

    def estimate_umaren_payout(self, odds1, odds2):
        """馬連の理論配当を推定"""
        prob1 = 1.0 / odds1
        prob2 = 1.0 / odds2
        combined_prob = prob1 * prob2 * 2  # 順不同
        payout = (0.75 / combined_prob) if combined_prob > 0 else 100
        return max(payout, 1.5)

    def estimate_umatan_payout(self, odds1, odds2):
        """馬単の理論配当を推定"""
        prob1 = 1.0 / odds1
        prob2 = 1.0 / odds2
        combined_prob = prob1 * prob2
        payout = (0.75 / combined_prob) if combined_prob > 0 else 200
        return max(payout, 2.0)

    def estimate_sanrenpuku_payout(self, odds1, odds2, odds3):
        """3連複の理論配当を推定"""
        prob1 = 1.0 / odds1
        prob2 = 1.0 / odds2
        prob3 = 1.0 / odds3
        combined_prob = prob1 * prob2 * prob3 * 6  # 順不同
        payout = (0.75 / combined_prob) if combined_prob > 0 else 500
        return max(payout, 3.0)

    def estimate_sanrentan_payout(self, odds1, odds2, odds3):
        """3連単の理論配当を推定"""
        prob1 = 1.0 / odds1
        prob2 = 1.0 / odds2
        prob3 = 1.0 / odds3
        combined_prob = prob1 * prob2 * prob3
        payout = (0.75 / combined_prob) if combined_prob > 0 else 1000
        return max(payout, 5.0)

    def recommend_bets(self, horses_data, budget=10000):
        """
        推奨ベットを生成

        Args:
            horses_data: 馬のデータリスト（umaban, odds, predicted_rank, value含む）
            budget: 総予算

        Returns:
            推奨ベットのリスト
        """
        recommendations = []

        # Value馬を抽出
        value_horses = self.get_value_bets(horses_data)

        if len(value_horses) == 0:
            return [{
                'message': f'Value閾値{self.value_threshold*100:.0f}%を超える馬がありません',
                'recommendation': 'ベット見送り推奨'
            }]

        # 最もValueが高い馬
        best_horse = max(value_horses, key=lambda x: x.get('value', 0))

        # 予測順位でソート
        horses_sorted = sorted(horses_data, key=lambda x: x.get('predicted_rank', 99))

        # ポートフォリオ配分（複勝70% + 3連単30%）
        fukusho_budget = int(budget * 0.7)
        sanrentan_budget = int(budget * 0.3)

        # 複勝推奨
        place_odds = self.estimate_place_odds(best_horse['odds'], len(horses_data))
        recommendations.append({
            'type': '複勝',
            'horses': [best_horse['umaban']],
            'odds': best_horse['odds'],
            'estimated_payout': place_odds,
            'value': best_horse['value'],
            'value_pct': best_horse['value'] * 100,
            'budget': fukusho_budget,
            'expected_return': fukusho_budget * place_odds * 0.189,  # 的中率18.9%
            'confidence': '★★★★★'
        })

        # 3連単推奨（予測上位3頭）
        if len(horses_sorted) >= 3:
            top3 = horses_sorted[:3]
            sanrentan_odds = self.estimate_sanrentan_payout(
                top3[0]['odds'], top3[1]['odds'], top3[2]['odds']
            )
            recommendations.append({
                'type': '3連単',
                'horses': [h['umaban'] for h in top3],
                'odds': [h['odds'] for h in top3],
                'estimated_payout': sanrentan_odds,
                'budget': sanrentan_budget,
                'expected_return': sanrentan_budget * sanrentan_odds * 0.029,  # 的中率2.9%
                'confidence': '★★★☆☆'
            })

        # その他の券種情報
        if len(horses_sorted) >= 2:
            top2 = horses_sorted[:2]

            # ワイド
            wide_odds = self.estimate_wide_payout(top2[0]['odds'], top2[1]['odds'])
            recommendations.append({
                'type': 'ワイド（参考）',
                'horses': [h['umaban'] for h in top2],
                'estimated_payout': wide_odds,
                'budget': 0,
                'note': '的中率期待値高め'
            })

        return recommendations

    def format_recommendation(self, recommendations):
        """推奨ベットを見やすくフォーマット"""
        lines = []
        lines.append("=" * 60)
        lines.append("Value Betting 推奨ベット")
        lines.append("=" * 60)

        total_budget = 0
        total_expected = 0

        for rec in recommendations:
            if 'message' in rec:
                lines.append(f"\n{rec['message']}")
                lines.append(f"{rec['recommendation']}")
                continue

            lines.append(f"\n【{rec['type']}】")

            if rec['type'] == '複勝':
                lines.append(f"  馬番: {rec['horses'][0]}番")
                lines.append(f"  単勝オッズ: {rec['odds']:.1f}倍")
                lines.append(f"  推定複勝: {rec['estimated_payout']:.2f}倍")
                lines.append(f"  Value: +{rec['value_pct']:.2f}%")
                lines.append(f"  投資額: {rec['budget']:,}円")
                lines.append(f"  期待回収: {rec['expected_return']:.0f}円")
                lines.append(f"  信頼度: {rec['confidence']}")

            elif rec['type'] == '3連単':
                lines.append(f"  馬番: {rec['horses'][0]}-{rec['horses'][1]}-{rec['horses'][2]}")
                lines.append(f"  単勝オッズ: {rec['odds'][0]:.1f}-{rec['odds'][1]:.1f}-{rec['odds'][2]:.1f}倍")
                lines.append(f"  推定配当: {rec['estimated_payout']:.1f}倍")
                lines.append(f"  投資額: {rec['budget']:,}円")
                lines.append(f"  期待回収: {rec['expected_return']:.0f}円")
                lines.append(f"  信頼度: {rec['confidence']}")

            else:
                lines.append(f"  馬番: {'-'.join(map(str, rec['horses']))}")
                lines.append(f"  推定配当: {rec['estimated_payout']:.2f}倍")
                if 'note' in rec:
                    lines.append(f"  備考: {rec['note']}")

            total_budget += rec.get('budget', 0)
            total_expected += rec.get('expected_return', 0)

        if total_budget > 0:
            lines.append("\n" + "-" * 60)
            lines.append(f"総投資額: {total_budget:,}円")
            lines.append(f"期待回収額: {total_expected:.0f}円")
            lines.append(f"期待回収率: {total_expected/total_budget*100:.1f}%")

        lines.append("=" * 60)

        return "\n".join(lines)


# 使用例
if __name__ == "__main__":
    # テストデータ
    test_horses = [
        {'umaban': 1, 'odds': 45.4, 'predicted_rank': 1.2},
        {'umaban': 2, 'odds': 8.5, 'predicted_rank': 3.5},
        {'umaban': 3, 'odds': 3.2, 'predicted_rank': 5.1},
        {'umaban': 4, 'odds': 15.7, 'predicted_rank': 2.8},
    ]

    analyzer = ValueBettingAnalyzer(value_threshold=0.05)

    # Value計算
    predicted_ranks = [h['predicted_rank'] for h in test_horses]
    odds_list = [h['odds'] for h in test_horses]
    values = analyzer.calculate_values(predicted_ranks, odds_list)

    # Value情報を追加
    for i, h in enumerate(test_horses):
        h.update(values[i])

    # 推奨ベット生成
    recommendations = analyzer.recommend_bets(test_horses, budget=10000)

    # 表示
    print(analyzer.format_recommendation(recommendations))
