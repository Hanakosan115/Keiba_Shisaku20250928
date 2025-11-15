"""
2025年8月のレースで予測精度を検証し、回収率を計算するスクリプト
"""
import pandas as pd
import json
import sys
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from improved_analyzer import ImprovedHorseAnalyzer
from prediction_integration import get_horse_past_results_from_csv

def load_payout_data(json_path):
    """配当データを読み込み、race_idでマッピング"""
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)

    payout_dict = {}
    for item in payout_list:
        race_id = str(item.get('race_id', ''))
        payout_dict[race_id] = item

    return payout_dict

def check_umaren_box_hit(horses_list, payout_data):
    """馬連BOX的中チェックと配当計算"""
    if '馬連' not in payout_data:
        return False, 0

    umaren_data = payout_data['馬連']
    winning_pairs = umaren_data.get('馬番', [])
    payouts = umaren_data.get('払戻金', [])

    if not winning_pairs or not payouts:
        return False, 0

    # 的中組み合わせをチェック
    # 馬番データの形式確認
    if not isinstance(winning_pairs, list):
        return False, 0

    # 1つの組み合わせが ['6', '10'] のような形式の場合
    if len(winning_pairs) > 0 and isinstance(winning_pairs[0], str):
        try:
            pair_nums = [int(p) for p in winning_pairs]
            if len(pair_nums) >= 2:
                if all(num in horses_list for num in pair_nums[:2]):
                    return True, payouts[0] if payouts else 0
        except:
            pass

    return False, 0

def check_sanrenpuku_box_hit(horses_list, payout_data):
    """3連複BOX的中チェックと配当計算"""
    if '3連複' not in payout_data:
        return False, 0

    sanrenpuku_data = payout_data['3連複']
    winning_sets = sanrenpuku_data.get('馬番', [])
    payouts = sanrenpuku_data.get('払戻金', [])

    if not winning_sets or not payouts:
        return False, 0

    # 馬番が ['3', '6', '10'] のようなリスト形式の場合
    if len(winning_sets) > 0 and isinstance(winning_sets[0], str):
        try:
            trio_nums = [int(p) for p in winning_sets]
            if len(trio_nums) >= 3:
                if all(num in horses_list for num in trio_nums[:3]):
                    return True, payouts[0] if payouts else 0
        except:
            pass

    return False, 0

def check_sanrentan_box_hit(horses_list, payout_data):
    """3連単BOX的中チェックと配当計算"""
    if '3連単' not in payout_data:
        return False, 0

    sanrentan_data = payout_data['3連単']
    winning_trios = sanrentan_data.get('馬番', [])
    payouts = sanrentan_data.get('払戻金', [])

    if not winning_trios or not payouts:
        return False, 0

    # 馬番が ['10', '6', '3'] のようなリスト形式の場合
    if len(winning_trios) > 0 and isinstance(winning_trios[0], str):
        try:
            trio_nums = [int(p) for p in winning_trios]
            if len(trio_nums) >= 3:
                if all(num in horses_list for num in trio_nums[:3]):
                    return True, payouts[0] if payouts else 0
        except:
            pass

    return False, 0

def validate_august_races_with_payout(csv_path, payout_json_path, num_races=None):
    """指定期間のレースで予測精度と回収率を検証"""
    print("=" * 60)
    print("2025年6-8月 予測精度・回収率検証（5頭体制）")
    print("=" * 60)

    # データ読み込み
    df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
    payout_dict = load_payout_data(payout_json_path)

    print(f"配当データ読み込み: {len(payout_dict)}レース")

    # 2025年6-8月のレースを抽出（race_idから判定）
    df['race_id_str'] = df['race_id'].astype(str)
    target_races = df[
        df['race_id_str'].str.startswith('202506') |
        df['race_id_str'].str.startswith('202507') |
        df['race_id_str'].str.startswith('202508')
    ]
    race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

    # num_racesがNoneの場合は全レース検証
    if num_races is None:
        num_races = len(race_ids)

    print(f"\n対象レース: {len(race_ids)}レース")
    print(f"検証レース数: {min(num_races, len(race_ids))}レース\n")

    # アナライザー初期化
    analyzer = ImprovedHorseAnalyzer()

    # 結果集計用
    results = {
        'total_races': 0,
        'total_investment': 0,
        'total_return': 0,
        'umaren_investment': 0,
        'umaren_return': 0,
        'umaren_hit_count': 0,
        'sanrenpuku_investment': 0,
        'sanrenpuku_return': 0,
        'sanrenpuku_hit_count': 0,
        'sanrentan_investment': 0,
        'sanrentan_return': 0,
        'sanrentan_hit_count': 0,
    }

    # レースごとに検証
    for idx, race_id in enumerate(race_ids[:num_races]):
        if (idx + 1) % 10 == 0:
            print(f"処理中: {idx + 1}/{min(num_races, len(race_ids))} レース")

        race_horses = df[df['race_id'] == race_id].copy()

        if len(race_horses) < 5:
            continue

        # 馬の予測
        horses_predictions = []

        for _, horse in race_horses.iterrows():
            odds = horse.get('Odds', 1.0)
            if pd.isna(odds) or odds <= 0:
                odds = horse.get('Odds_x', horse.get('Odds_y', 1.0))
            if pd.isna(odds) or odds <= 0:
                odds = 10.0

            # 過去成績を取得
            horse_id = horse.get('horse_id')
            race_id_str = str(race_id)
            if len(race_id_str) >= 8:
                year = race_id_str[0:4]
                month = race_id_str[4:6]
                day = race_id_str[6:8]
                race_date = f"{year}-{month}-{day}"
            else:
                race_date = horse.get('date')

            past_results = get_horse_past_results_from_csv(horse_id, race_date, max_results=5)

            horse_basic_info = {
                'Odds': odds,
                'Ninki': horse.get('Ninki'),
                'Age': horse.get('Age'),
                'Sex': horse.get('Sex'),
                'Load': horse.get('Load'),
                'Waku': horse.get('Waku'),
                'HorseName': horse.get('HorseName'),
                'race_results': past_results
            }

            race_conditions = {
                'Distance': horse.get('distance'),
                'CourseType': horse.get('course_type'),
                'TrackCondition': horse.get('track_condition')
            }

            features = analyzer.calculate_simplified_features(horse_basic_info, race_conditions)
            ai_prediction = analyzer.calculate_simple_ai_prediction(features)
            divergence_info = analyzer.calculate_divergence_score(features, ai_prediction)

            horses_predictions.append({
                'umaban': int(horse.get('Umaban', 0)),
                'horse_name': horse.get('HorseName', ''),
                'odds': odds,
                'ai_prediction': ai_prediction,
                'divergence': divergence_info['divergence'],
                'composite_score': ai_prediction * 0.6 + max(0, divergence_info['divergence']) * 2 * 0.4
            })

        if len(horses_predictions) < 5:
            continue

        # 印と自信度を付与
        horses_with_marks = analyzer.assign_marks_and_confidence(horses_predictions)

        # ◎○▲△☆を取得
        honmei = next((h for h in horses_with_marks if h.get('mark') == '◎'), None)
        taikou = next((h for h in horses_with_marks if h.get('mark') == '○'), None)
        ana = next((h for h in horses_with_marks if h.get('mark') == '▲'), None)
        renge = next((h for h in horses_with_marks if h.get('mark') == '△'), None)
        hoshi = next((h for h in horses_with_marks if h.get('mark') == '☆'), None)

        if not honmei:
            continue

        results['total_races'] += 1

        # 配当データを取得
        race_id_str = str(race_id)
        payout_data = payout_dict.get(race_id_str, {})

        if not payout_data:
            continue

        # 馬連BOX（◎○▲△☆の全組み合わせ）
        all_horses = [honmei['umaban']]
        if taikou:
            all_horses.append(taikou['umaban'])
        if ana:
            all_horses.append(ana['umaban'])
        if renge:
            all_horses.append(renge['umaban'])
        if hoshi:
            all_horses.append(hoshi['umaban'])

        # BOX買い: n頭 → n*(n-1)/2 点
        umaren_tickets = len(all_horses) * (len(all_horses) - 1) // 2
        results['umaren_investment'] += umaren_tickets * 100

        hit, payout = check_umaren_box_hit(all_horses, payout_data)

        if hit:
            results['umaren_return'] += payout
            results['umaren_hit_count'] += 1

        # 3連複BOX
        if len(all_horses) >= 3:
            # BOX買い: n頭 → n*(n-1)*(n-2)/6 点
            sanrenpuku_tickets = len(all_horses) * (len(all_horses) - 1) * (len(all_horses) - 2) // 6
            results['sanrenpuku_investment'] += sanrenpuku_tickets * 100

            hit, payout = check_sanrenpuku_box_hit(all_horses, payout_data)

            if hit:
                results['sanrenpuku_return'] += payout
                results['sanrenpuku_hit_count'] += 1

        # 3連単BOX
        if len(all_horses) >= 3:
            # BOX買い: n頭 → n*(n-1)*(n-2) 点
            sanrentan_tickets = len(all_horses) * (len(all_horses) - 1) * (len(all_horses) - 2)
            results['sanrentan_investment'] += sanrentan_tickets * 100

            hit, payout = check_sanrentan_box_hit(all_horses, payout_data)

            if hit:
                results['sanrentan_return'] += payout
                results['sanrentan_hit_count'] += 1

    # 総投資額と総払戻額
    results['total_investment'] = results['umaren_investment'] + results['sanrenpuku_investment'] + results['sanrentan_investment']
    results['total_return'] = results['umaren_return'] + results['sanrenpuku_return'] + results['sanrentan_return']

    # 結果表示
    print("\n" + "=" * 60)
    print("【回収率検証結果】")
    print("=" * 60)

    total = results['total_races']
    if total == 0:
        print("検証対象レースがありません")
        return

    print(f"\n検証レース数: {total}レース\n")

    print("【馬連BOX（◎○▲△☆の全組み合わせ）】")
    print(f"  投資額: {results['umaren_investment']:,}円")
    print(f"  払戻額: {results['umaren_return']:,}円")
    print(f"  的中回数: {results['umaren_hit_count']}回 ({results['umaren_hit_count']/total*100:.1f}%)")
    umaren_recovery = results['umaren_return'] / results['umaren_investment'] * 100 if results['umaren_investment'] > 0 else 0
    print(f"  回収率: {umaren_recovery:.1f}%")
    print(f"  損益: {results['umaren_return'] - results['umaren_investment']:+,}円")

    print("\n【3連複BOX（◎○▲△☆の全組み合わせ）】")
    print(f"  投資額: {results['sanrenpuku_investment']:,}円")
    print(f"  払戻額: {results['sanrenpuku_return']:,}円")
    print(f"  的中回数: {results['sanrenpuku_hit_count']}回 ({results['sanrenpuku_hit_count']/total*100:.1f}%)")
    sanrenpuku_recovery = results['sanrenpuku_return'] / results['sanrenpuku_investment'] * 100 if results['sanrenpuku_investment'] > 0 else 0
    print(f"  回収率: {sanrenpuku_recovery:.1f}%")
    print(f"  損益: {results['sanrenpuku_return'] - results['sanrenpuku_investment']:+,}円")

    print("\n【3連単BOX（◎○▲△☆の全組み合わせ）】")
    print(f"  投資額: {results['sanrentan_investment']:,}円")
    print(f"  払戻額: {results['sanrentan_return']:,}円")
    print(f"  的中回数: {results['sanrentan_hit_count']}回 ({results['sanrentan_hit_count']/total*100:.1f}%)")
    sanrentan_recovery = results['sanrentan_return'] / results['sanrentan_investment'] * 100 if results['sanrentan_investment'] > 0 else 0
    print(f"  回収率: {sanrentan_recovery:.1f}%")
    print(f"  損益: {results['sanrentan_return'] - results['sanrentan_investment']:+,}円")

    print("\n【総合】")
    print(f"  総投資額: {results['total_investment']:,}円")
    print(f"  総払戻額: {results['total_return']:,}円")
    total_recovery = results['total_return'] / results['total_investment'] * 100 if results['total_investment'] > 0 else 0
    print(f"  総回収率: {total_recovery:.1f}%")
    total_profit = results['total_return'] - results['total_investment']
    print(f"  総損益: {total_profit:+,}円")

    print("\n" + "=" * 60)

    # 評価
    print("\n【評価】")
    if total_recovery >= 100:
        print(f"[黒字達成！] 回収率{total_recovery:.1f}%で利益が出ています。")
    elif total_recovery >= 80:
        print(f"[優秀] 回収率{total_recovery:.1f}%は実用的なレベルです。")
    elif total_recovery >= 60:
        print(f"[良好] 回収率{total_recovery:.1f}%。改善の余地があります。")
    else:
        print(f"[要改善] 回収率{total_recovery:.1f}%。戦略の見直しが必要です。")

    if umaren_recovery > total_recovery:
        print("[推奨] 馬連フォーメーションが最も効率的です。")
    elif sanrenpuku_recovery > total_recovery:
        print("[推奨] 3連複フォーメーションが最も効率的です。")
    elif sanrentan_recovery > total_recovery:
        print("[推奨] 3連単フォーメーションが最も効率的です。")

    return results


if __name__ == "__main__":
    csv_path = r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv"
    payout_json_path = r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json"

    # 全レース検証（num_races=Noneで全レース）
    validate_august_races_with_payout(csv_path, payout_json_path, num_races=None)
