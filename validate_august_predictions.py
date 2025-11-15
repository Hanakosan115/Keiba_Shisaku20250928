"""
2025年8月のレースで予測精度を検証するスクリプト
"""
import pandas as pd
import sys
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from improved_analyzer import ImprovedHorseAnalyzer
from prediction_integration import get_horse_past_results_from_csv

def validate_august_races(csv_path, num_races=50):
    """8月のレースで予測精度を検証"""
    print("=" * 60)
    print("2025年8月 予測精度検証")
    print("=" * 60)

    # データ読み込み
    df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)

    # 2025年8月のレースを抽出
    august_races = df[df['date'].str.contains('2025-08', na=False)]

    # レースIDごとにグループ化
    race_ids = august_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

    print(f"\n対象レース: {len(race_ids)}レース")
    print(f"検証レース数: {min(num_races, len(race_ids))}レース\n")

    # アナライザー初期化
    analyzer = ImprovedHorseAnalyzer()

    # 結果集計用（5頭体制対応）
    results = {
        'total_races': 0,
        'honmei_win': 0,      # ◎が1着
        'honmei_place': 0,    # ◎が3着以内
        'taikou_win': 0,      # ○が1着
        'taikou_place': 0,    # ○が3着以内
        'ana_win': 0,         # ▲が1着
        'ana_place': 0,       # ▲が3着以内
        'renge_win': 0,       # △が1着
        'renge_place': 0,     # △が3着以内
        'hoshi_win': 0,       # ☆が1着
        'hoshi_place': 0,     # ☆が3着以内
        'wide_hit': 0,        # ワイド◎-○的中
        'umaren_hit': 0,      # 馬連◎-○的中
        'sanrenpuku_hit': 0,  # 3連複◎-○-▲的中
        'top3_coverage': 0,   # ◎○▲△☆のいずれかが1-3着
        'umaren_formation_hit': 0,    # 馬連フォーメーション的中（◎○×△▲☆）
        'sanrenpuku_formation_hit': 0, # 3連複フォーメーション的中
        'sanrentan_formation_hit': 0,  # 3連単フォーメーション的中
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

            actual_rank = horse.get('Rank')
            try:
                actual_rank = int(float(actual_rank)) if pd.notna(actual_rank) else 99
            except:
                actual_rank = 99

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
                'actual_rank': actual_rank,
                'composite_score': ai_prediction * 0.6 + max(0, divergence_info['divergence']) * 2 * 0.4
            })

        if len(horses_predictions) < 5:
            continue

        # 印と自信度を付与
        horses_with_marks = analyzer.assign_marks_and_confidence(horses_predictions)

        # ◎○▲△☆を取得（5頭体制）
        honmei = next((h for h in horses_with_marks if h.get('mark') == '◎'), None)
        taikou = next((h for h in horses_with_marks if h.get('mark') == '○'), None)
        ana = next((h for h in horses_with_marks if h.get('mark') == '▲'), None)
        renge = next((h for h in horses_with_marks if h.get('mark') == '△'), None)
        hoshi = next((h for h in horses_with_marks if h.get('mark') == '☆'), None)

        if not honmei:
            continue

        results['total_races'] += 1

        # 実際の1-3着を取得
        actual_top3 = sorted([h for h in horses_predictions if h['actual_rank'] <= 3],
                            key=lambda x: x['actual_rank'])
        if len(actual_top3) < 3:
            continue

        win_umaban = actual_top3[0]['umaban']
        place_umabans = {h['umaban'] for h in actual_top3}

        # ◎の成績
        if honmei['umaban'] == win_umaban:
            results['honmei_win'] += 1
        if honmei['umaban'] in place_umabans:
            results['honmei_place'] += 1

        # ○の成績
        if taikou:
            if taikou['umaban'] == win_umaban:
                results['taikou_win'] += 1
            if taikou['umaban'] in place_umabans:
                results['taikou_place'] += 1

        # ▲の成績
        if ana:
            if ana['umaban'] == win_umaban:
                results['ana_win'] += 1
            if ana['umaban'] in place_umabans:
                results['ana_place'] += 1

        # △の成績
        if renge:
            if renge['umaban'] == win_umaban:
                results['renge_win'] += 1
            if renge['umaban'] in place_umabans:
                results['renge_place'] += 1

        # ☆の成績
        if hoshi:
            if hoshi['umaban'] == win_umaban:
                results['hoshi_win'] += 1
            if hoshi['umaban'] in place_umabans:
                results['hoshi_place'] += 1

        # 馬券的中判定（5頭体制）
        predicted_umabans = {honmei['umaban']}
        if taikou:
            predicted_umabans.add(taikou['umaban'])
        if ana:
            predicted_umabans.add(ana['umaban'])
        if renge:
            predicted_umabans.add(renge['umaban'])
        if hoshi:
            predicted_umabans.add(hoshi['umaban'])

        # 3着以内カバー率
        if len(predicted_umabans & place_umabans) > 0:
            results['top3_coverage'] += 1

        # ワイド◎-○
        if taikou and honmei['umaban'] in place_umabans and taikou['umaban'] in place_umabans:
            results['wide_hit'] += 1

        # 馬連◎-○
        if taikou:
            if {honmei['umaban'], taikou['umaban']} == {actual_top3[0]['umaban'], actual_top3[1]['umaban']}:
                results['umaren_hit'] += 1

        # 3連複◎-○-▲（従来）
        if taikou and ana:
            if {honmei['umaban'], taikou['umaban'], ana['umaban']} == place_umabans:
                results['sanrenpuku_hit'] += 1

        # フォーメーション馬券の的中判定（5頭体制）
        axis_horses = {honmei['umaban']}
        if taikou:
            axis_horses.add(taikou['umaban'])

        other_horses = set()
        if ana:
            other_horses.add(ana['umaban'])
        if renge:
            other_horses.add(renge['umaban'])
        if hoshi:
            other_horses.add(hoshi['umaban'])

        # 馬連フォーメーション: 軸（◎○）×相手（▲△☆）が1-2着
        top2_umabans = {actual_top3[0]['umaban'], actual_top3[1]['umaban']}
        if len(axis_horses & top2_umabans) > 0 and len(other_horses & top2_umabans) > 0:
            results['umaren_formation_hit'] += 1

        # 3連複フォーメーション: ◎○から2頭+▲△☆から1頭が1-3着
        if len(axis_horses & place_umabans) >= 2 and len(other_horses & place_umabans) >= 1:
            results['sanrenpuku_formation_hit'] += 1

        # 3連単フォーメーション: ◎が1着+○▲△☆から2頭が2-3着
        if honmei['umaban'] == win_umaban:
            other_all = set()
            if taikou:
                other_all.add(taikou['umaban'])
            if ana:
                other_all.add(ana['umaban'])
            if renge:
                other_all.add(renge['umaban'])
            if hoshi:
                other_all.add(hoshi['umaban'])

            if len(other_all & {actual_top3[1]['umaban'], actual_top3[2]['umaban']}) == 2:
                results['sanrentan_formation_hit'] += 1

    # 結果表示
    print("\n" + "=" * 60)
    print("【検証結果】")
    print("=" * 60)

    total = results['total_races']
    if total == 0:
        print("検証対象レースがありません")
        return

    print(f"\n検証レース数: {total}レース\n")

    print("【本命（◎）の成績】")
    print(f"  1着的中: {results['honmei_win']}回 ({results['honmei_win']/total*100:.1f}%)")
    print(f"  複勝的中: {results['honmei_place']}回 ({results['honmei_place']/total*100:.1f}%)")

    print("\n【対抗（○）の成績】")
    print(f"  1着的中: {results['taikou_win']}回 ({results['taikou_win']/total*100:.1f}%)")
    print(f"  複勝的中: {results['taikou_place']}回 ({results['taikou_place']/total*100:.1f}%)")

    print("\n【単穴（▲）の成績】")
    print(f"  1着的中: {results['ana_win']}回 ({results['ana_win']/total*100:.1f}%)")
    print(f"  複勝的中: {results['ana_place']}回 ({results['ana_place']/total*100:.1f}%)")

    print("\n【連下（△）の成績】")
    print(f"  1着的中: {results['renge_win']}回 ({results['renge_win']/total*100:.1f}%)")
    print(f"  複勝的中: {results['renge_place']}回 ({results['renge_place']/total*100:.1f}%)")

    print("\n【穴馬（☆）の成績】")
    print(f"  1着的中: {results['hoshi_win']}回 ({results['hoshi_win']/total*100:.1f}%)")
    print(f"  複勝的中: {results['hoshi_place']}回 ({results['hoshi_place']/total*100:.1f}%)")

    print("\n【単式馬券的中率（従来）】")
    print(f"  ワイド◎-○: {results['wide_hit']}回 ({results['wide_hit']/total*100:.1f}%)")
    print(f"  馬連◎-○: {results['umaren_hit']}回 ({results['umaren_hit']/total*100:.1f}%)")
    print(f"  3連複◎-○-▲: {results['sanrenpuku_hit']}回 ({results['sanrenpuku_hit']/total*100:.1f}%)")

    print("\n【フォーメーション馬券的中率（5頭体制）】")
    print(f"  馬連フォーメーション（◎○×▲△☆）: {results['umaren_formation_hit']}回 ({results['umaren_formation_hit']/total*100:.1f}%)")
    print(f"  3連複フォーメーション: {results['sanrenpuku_formation_hit']}回 ({results['sanrenpuku_formation_hit']/total*100:.1f}%)")
    print(f"  3連単フォーメーション（◎→○▲△☆）: {results['sanrentan_formation_hit']}回 ({results['sanrentan_formation_hit']/total*100:.1f}%)")

    print("\n【総合評価】")
    coverage_rate = results['top3_coverage'] / total * 100
    print(f"  3着以内カバー率: {results['top3_coverage']}回 ({coverage_rate:.1f}%) ← 5頭で予測")

    # 複勝合計的中率（5頭）
    fukusho_total = results['honmei_place'] + results['taikou_place'] + results['ana_place'] + results['renge_place'] + results['hoshi_place']
    print(f"  複勝合計的中: {fukusho_total}回 (◎○▲△☆いずれか)")

    print("\n" + "=" * 60)

    # 評価コメント
    print("\n【評価】")
    if coverage_rate >= 80:
        print("[優秀] 3着以内のカバー率が高く、実用的な予測精度です。")
    elif coverage_rate >= 60:
        print("[良好] 予測精度は実用レベルです。")
    elif coverage_rate >= 40:
        print("[普通] 改善の余地があります。")
    else:
        print("[要改善] 予測精度の向上が必要です。")

    if results['honmei_place'] / total >= 0.3:
        print("[Good] 本命（◎）の複勝的中率が良好です。")

    if results['wide_hit'] / total >= 0.2:
        print("[Good] ワイド狙いが有効な予測傾向です。")

    # フォーメーション馬券の評価
    if results['umaren_formation_hit'] / total >= 0.15:
        print("[Good] 馬連フォーメーションが実用的な的中率です。")

    if results['sanrenpuku_formation_hit'] / total >= 0.10:
        print("[Excellent] 3連複フォーメーションの的中率が優秀です。")

    if results['sanrentan_formation_hit'] / total >= 0.08:
        print("[Excellent] 3連単フォーメーションの的中率が優秀です。")

    return results


if __name__ == "__main__":
    csv_path = r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv"

    # 50レースで検証
    validate_august_races(csv_path, num_races=50)
