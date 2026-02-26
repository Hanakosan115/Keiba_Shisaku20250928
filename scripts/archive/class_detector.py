"""
レースクラス判定ロジック - 特別戦対応版

特別戦（○○賞、○○ステークス、○○杯など）は
レース名だけでなく、括弧内の条件文も解析する必要がある

例:
  - "シリウスステークス(3勝クラス)" → 3勝
  - "京都新聞杯(オープン)" → オープン
  - "アハルテケステークス(1000万下)" → 2勝クラス
  - "エルフィンステークス(500万下)" → 1勝クラス
"""

import re
from typing import Optional, Dict

class RaceClassDetector:
    """
    レースクラス判定クラス

    優先順位:
    1. 括弧内の明示的なクラス表記
    2. 賞金額での判定（500万、1000万、1600万）
    3. レース名での判定
    4. 特別戦の既知マッピング
    """

    def __init__(self):
        # クラスのランク（数値が大きいほど上位）
        self.class_ranks = {
            '新馬': 0,
            '未勝利': 0,
            '1勝': 1,
            '2勝': 2,
            '3勝': 3,
            'オープン': 4,
            'リステッド': 4.5,
            'G3': 5,
            'G2': 6,
            'G1': 7,
            '障害': -1  # 特殊
        }

        # 既知の特別戦マッピング（主要なものだけ）
        # 実際の運用ではもっと多くのレースを登録
        self.special_race_mapping = {
            # G1
            '天皇賞': 'G1',
            '宝塚記念': 'G1',
            '有馬記念': 'G1',
            '日本ダービー': 'G1',
            '桜花賞': 'G1',
            'オークス': 'G1',
            '菊花賞': 'G1',
            '皐月賞': 'G1',
            'フェブラリーS': 'G1',
            '高松宮記念': 'G1',
            '安田記念': 'G1',
            'スプリンターズS': 'G1',
            '秋華賞': 'G1',
            'マイルCS': 'G1',
            'ジャパンC': 'G1',
            'チャンピオンズC': 'G1',

            # G2
            '京都記念': 'G2',
            '中山記念': 'G2',
            '阪神大賞典': 'G2',
            '日経賞': 'G2',
            '京都新聞杯': 'G2',
            '青葉賞': 'G2',

            # G3
            'ラジオNIKKEI賞': 'G3',
            '函館記念': 'G3',
            '小倉記念': 'G3',

            # オープン
            'シリウスS': 'オープン',
            'カペラS': 'オープン',
        }

    def detect_class(self, race_name: str, race_subtitle: str = '') -> Dict[str, any]:
        """
        レース名からクラスを判定

        Args:
            race_name: レース名（例: "1回東京1日11R シリウスステークス(3勝クラス)"）
            race_subtitle: 副題・条件文（例: "(3勝クラス)(定量)"）

        Returns:
            dict: {
                'class': クラス名,
                'class_rank': クラスランク,
                'confidence': 確信度 (0-1),
                'method': 判定方法,
                'is_special': 特別戦かどうか
            }
        """

        # 全体を結合
        full_text = race_name + ' ' + race_subtitle

        # 1. 括弧内の明示的なクラス表記をチェック
        result = self._check_explicit_class(full_text)
        if result:
            return result

        # 2. 賞金額での判定
        result = self._check_prize_money(full_text)
        if result:
            return result

        # 3. レース名での直接判定（未勝利、新馬など）
        result = self._check_direct_class_name(full_text)
        if result:
            return result

        # 4. 特別戦の既知マッピング
        result = self._check_special_race_mapping(race_name)
        if result:
            return result

        # 5. G1/G2/G3の判定
        result = self._check_grade_race(full_text)
        if result:
            return result

        # 判定できない場合
        return {
            'class': '不明',
            'class_rank': -999,
            'confidence': 0.0,
            'method': 'unknown',
            'is_special': self._is_special_race_name(race_name)
        }

    def _check_explicit_class(self, text: str) -> Optional[Dict]:
        """
        括弧内の明示的なクラス表記をチェック

        例:
          "(3勝クラス)" → 3勝
          "(1勝クラス)" → 1勝
          "(オープン)" → オープン
        """
        # パターン1: (N勝クラス)
        match = re.search(r'\(([123])勝クラス\)', text)
        if match:
            class_num = match.group(1)
            class_name = f'{class_num}勝'
            return {
                'class': class_name,
                'class_rank': self.class_ranks[class_name],
                'confidence': 1.0,
                'method': 'explicit_bracket',
                'is_special': True
            }

        # パターン2: (オープン)
        if '(オープン)' in text or '（オープン）' in text:
            return {
                'class': 'オープン',
                'class_rank': self.class_ranks['オープン'],
                'confidence': 1.0,
                'method': 'explicit_bracket',
                'is_special': True
            }

        # パターン3: (リステッド)
        if '(リステッド)' in text or '（リステッド）' in text:
            return {
                'class': 'リステッド',
                'class_rank': self.class_ranks['リステッド'],
                'confidence': 1.0,
                'method': 'explicit_bracket',
                'is_special': True
            }

        return None

    def _check_prize_money(self, text: str) -> Optional[Dict]:
        """
        賞金額での判定

        例:
          "(500万下)" → 1勝クラス
          "(1000万下)" → 2勝クラス
          "(1600万下)" → 3勝クラス
        """
        # パターン: (NNN万下) または (N,NNN万下)
        match = re.search(r'\((\d{3,4})万下?\)', text) or \
                re.search(r'\((\d),(\d{3})万下?\)', text)

        if match:
            if len(match.groups()) == 2:
                # 1,000の形式
                prize = int(match.group(1)) * 1000 + int(match.group(2))
            else:
                # 1000の形式
                prize = int(match.group(1))

            # 賞金額からクラスを判定
            if prize <= 500:
                class_name = '1勝'
            elif prize <= 1000:
                class_name = '2勝'
            elif prize <= 1600:
                class_name = '3勝'
            else:
                class_name = 'オープン'

            return {
                'class': class_name,
                'class_rank': self.class_ranks[class_name],
                'confidence': 0.95,
                'method': 'prize_money',
                'is_special': True,
                'prize': prize
            }

        return None

    def _check_direct_class_name(self, text: str) -> Optional[Dict]:
        """
        レース名に直接書かれているクラス名をチェック

        例:
          "未勝利" → 未勝利
          "新馬" → 新馬
          "1勝クラス" → 1勝
        """
        # 新馬
        if '新馬' in text:
            return {
                'class': '新馬',
                'class_rank': self.class_ranks['新馬'],
                'confidence': 1.0,
                'method': 'direct_name',
                'is_special': False
            }

        # 未勝利
        if '未勝利' in text:
            return {
                'class': '未勝利',
                'class_rank': self.class_ranks['未勝利'],
                'confidence': 1.0,
                'method': 'direct_name',
                'is_special': False
            }

        # N勝クラス（括弧外）
        match = re.search(r'([123])勝クラス', text)
        if match:
            class_num = match.group(1)
            class_name = f'{class_num}勝'
            return {
                'class': class_name,
                'class_rank': self.class_ranks[class_name],
                'confidence': 1.0,
                'method': 'direct_name',
                'is_special': False
            }

        return None

    def _check_special_race_mapping(self, race_name: str) -> Optional[Dict]:
        """
        既知の特別戦マッピングから判定

        例:
          "シリウスステークス" → オープン（マッピングによる）
        """
        # レース名から不要な部分を削除
        clean_name = self._clean_race_name(race_name)

        # マッピングテーブルをチェック
        for key, class_name in self.special_race_mapping.items():
            if key in clean_name:
                return {
                    'class': class_name,
                    'class_rank': self.class_ranks[class_name],
                    'confidence': 0.9,
                    'method': 'special_mapping',
                    'is_special': True,
                    'race_key': key
                }

        return None

    def _check_grade_race(self, text: str) -> Optional[Dict]:
        """
        G1/G2/G3の判定
        """
        # G1
        if re.search(r'G[IⅠ1]|GI|G1', text):
            return {
                'class': 'G1',
                'class_rank': self.class_ranks['G1'],
                'confidence': 1.0,
                'method': 'grade',
                'is_special': True
            }

        # G2
        if re.search(r'G[IIⅡ2]|GII|G2', text):
            return {
                'class': 'G2',
                'class_rank': self.class_ranks['G2'],
                'confidence': 1.0,
                'method': 'grade',
                'is_special': True
            }

        # G3
        if re.search(r'G[IIIⅢ3]|GIII|G3', text):
            return {
                'class': 'G3',
                'class_rank': self.class_ranks['G3'],
                'confidence': 1.0,
                'method': 'grade',
                'is_special': True
            }

        return None

    def _is_special_race_name(self, race_name: str) -> bool:
        """
        特別戦かどうかを判定（名前から）

        特別戦の特徴:
          - ○○賞
          - ○○ステークス / ○○S
          - ○○杯
          - ○○記念
          - ○○カップ / ○○C
        """
        indicators = ['賞', 'ステークス', '杯', '記念', 'カップ', 'Ｓ', 'Ｃ']

        clean_name = self._clean_race_name(race_name)

        return any(ind in clean_name for ind in indicators)

    def _clean_race_name(self, race_name: str) -> str:
        """
        レース名から不要な部分を削除

        例:
          "1回東京1日11R シリウスステークス(3勝クラス)"
          → "シリウスステークス"
        """
        # 開催情報（1回東京1日11R など）を削除
        name = re.sub(r'\d+回[^日]+\d+日\d+R\s*', '', race_name)

        # 括弧内を削除
        name = re.sub(r'\([^)]*\)', '', name)
        name = re.sub(r'（[^）]*）', '', name)

        # 前後の空白削除
        name = name.strip()

        return name

    def detect_class_change(self, prev_class: str, current_class: str) -> Dict:
        """
        クラス変動を検出

        Args:
            prev_class: 前回のクラス
            current_class: 今回のクラス

        Returns:
            dict: {
                'changed': クラス変動があったか,
                'type': 'promotion' / 'demotion' / 'same',
                'rank_diff': ランク差分
            }
        """
        prev_rank = self.class_ranks.get(prev_class, -999)
        current_rank = self.class_ranks.get(current_class, -999)

        if prev_rank == -999 or current_rank == -999:
            return {
                'changed': False,
                'type': 'unknown',
                'rank_diff': 0
            }

        rank_diff = current_rank - prev_rank

        if rank_diff > 0:
            return {
                'changed': True,
                'type': 'promotion',  # 昇級
                'rank_diff': rank_diff,
                'message': f'{prev_class} → {current_class} (昇級)'
            }
        elif rank_diff < 0:
            return {
                'changed': True,
                'type': 'demotion',  # 降級
                'rank_diff': rank_diff,
                'message': f'{prev_class} → {current_class} (降級)'
            }
        else:
            return {
                'changed': False,
                'type': 'same',
                'rank_diff': 0,
                'message': f'{prev_class} (同クラス)'
            }


# ============================================================================
# テストケース
# ============================================================================
def test_class_detector():
    """
    クラス判定のテスト
    """
    detector = RaceClassDetector()

    test_cases = [
        # 一般戦
        ("未勝利", ""),
        ("新馬", ""),
        ("1勝クラス", ""),
        ("2勝クラス", ""),
        ("3勝クラス", ""),

        # 特別戦（括弧あり）
        ("シリウスステークス", "(3勝クラス)(定量)"),
        ("アハルテケステークス", "(1000万下)(定量)"),
        ("エルフィンステークス", "(500万下)(定量)"),
        ("ダリア賞", "(オープン)"),

        # 特別戦（括弧なし）
        ("京都新聞杯", ""),
        ("青葉賞", ""),

        # G1レース
        ("天皇賞(春)", "(G1)"),
        ("日本ダービー", ""),
        ("有馬記念", ""),

        # 実際のフォーマット
        ("1回東京1日11R シリウスステークス(3勝クラス)(定量)", ""),
        ("2回阪神3日10R アハルテケステークス(1000万下)(定量)", ""),
    ]

    print("="*80)
    print("クラス判定テスト")
    print("="*80)

    for race_name, subtitle in test_cases:
        result = detector.detect_class(race_name, subtitle)

        print(f"\n【レース名】: {race_name}")
        if subtitle:
            print(f"【条件】: {subtitle}")
        print(f"  クラス: {result['class']}")
        print(f"  ランク: {result['class_rank']}")
        print(f"  確信度: {result['confidence']:.0%}")
        print(f"  判定方法: {result['method']}")
        print(f"  特別戦: {'はい' if result['is_special'] else 'いいえ'}")

    # クラス変動テスト
    print("\n" + "="*80)
    print("クラス変動テスト")
    print("="*80)

    change_cases = [
        ('1勝', '2勝'),
        ('未勝利', '1勝'),
        ('3勝', 'オープン'),
        ('オープン', 'G3'),
        ('2勝', '2勝'),
        ('オープン', '3勝'),  # 降級
    ]

    for prev, current in change_cases:
        result = detector.detect_class_change(prev, current)
        print(f"\n{result['message']}")
        print(f"  変動: {result['type']}")
        print(f"  ランク差: {result['rank_diff']}")


if __name__ == '__main__':
    test_class_detector()
