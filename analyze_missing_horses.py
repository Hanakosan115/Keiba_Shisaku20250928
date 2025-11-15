"""
◎○▲以外の馬を分析して、改善のヒントを得る
"""
import pandas as pd
import sys
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from improved_analyzer import ImprovedHorseAnalyzer
from prediction_integration import get_horse_past_results_from_csv

def analyze_missing_predictions(csv_path, num_races=50):
    """予測に含まれなかった馬を分析"""
    print("=" * 60)
    print("予測外の馬分析 - 改善のヒント")
    print("=" * 60)

    df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
    august_races = df[df['date'].str.contains('2025-08', na=False)]
    race_ids = august_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()

    print(f"\n対象レース: {min(num_races, len(race_ids))}レース\n")

    analyzer = ImprovedHorseAnalyzer()

    # 分析データ
    missing_horses = []  # 予測外だが3着以内に入った馬
    predicted_horses = []  # 予測に含まれた馬

    for idx, race_id in enumerate(race_ids[:num_races]):
        if (idx + 1) % 10 == 0:
            print(f"処理中: {idx + 1}/{min(num_races, len(race_ids))} レース")

        race_horses = df[df['race_id'] == race_id].copy()
        if len(race_horses) < 5:
            continue

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
                'ninki': int(horse.get('Ninki', 0)) if pd.notna(horse.get('Ninki')) else 0,
                'odds': odds,
                'ai_prediction': ai_prediction,
                'divergence': divergence_info['divergence'],
                'actual_rank': actual_rank,
                'composite_score': ai_prediction * 0.6 + max(0, divergence_info['divergence']) * 2 * 0.4
            })

        if len(horses_predictions) < 5:
            continue

        horses_with_marks = analyzer.assign_marks_and_confidence(horses_predictions)

        # ◎○▲を取得
        honmei = next((h for h in horses_with_marks if h.get('mark') == '◎'), None)
        taikou = next((h for h in horses_with_marks if h.get('mark') == '○'), None)
        ana = next((h for h in horses_with_marks if h.get('mark') == '▲'), None)

        if not honmei:
            continue

        predicted_umabans = {honmei['umaban']}
        if taikou:
            predicted_umabans.add(taikou['umaban'])
        if ana:
            predicted_umabans.add(ana['umaban'])

        # 実際の1-3着
        actual_top3 = [h for h in horses_predictions if h['actual_rank'] <= 3]

        for horse in actual_top3:
            if horse['umaban'] in predicted_umabans:
                predicted_horses.append(horse)
            else:
                missing_horses.append(horse)

    # 分析結果
    print("\n" + "=" * 60)
    print("【分析結果】")
    print("=" * 60)

    total_top3 = len(missing_horses) + len(predicted_horses)
    print(f"\n3着以内の馬 総数: {total_top3}頭")
    print(f"  予測的中: {len(predicted_horses)}頭 ({len(predicted_horses)/total_top3*100:.1f}%)")
    print(f"  予測漏れ: {len(missing_horses)}頭 ({len(missing_horses)/total_top3*100:.1f}%)")

    # 予測漏れ馬の特徴分析
    if missing_horses:
        print("\n【予測漏れ馬の特徴】")

        # 人気別分布
        ninki_dist = {}
        for h in missing_horses:
            ninki = h['ninki']
            if ninki <= 3:
                key = "1-3番人気"
            elif ninki <= 6:
                key = "4-6番人気"
            elif ninki <= 9:
                key = "7-9番人気"
            else:
                key = "10番人気以下"
            ninki_dist[key] = ninki_dist.get(key, 0) + 1

        print("\n人気別分布:")
        for key in ["1-3番人気", "4-6番人気", "7-9番人気", "10番人気以下"]:
            count = ninki_dist.get(key, 0)
            if count > 0:
                print(f"  {key}: {count}頭 ({count/len(missing_horses)*100:.1f}%)")

        # AI予測値の分布
        ai_scores = [h['ai_prediction'] for h in missing_horses]
        comp_scores = [h['composite_score'] for h in missing_horses]

        print(f"\nAI予測値:")
        print(f"  平均: {sum(ai_scores)/len(ai_scores):.1f}%")
        print(f"  最小: {min(ai_scores):.1f}%")
        print(f"  最大: {max(ai_scores):.1f}%")

        print(f"\n総合スコア:")
        print(f"  平均: {sum(comp_scores)/len(comp_scores):.1f}")
        print(f"  最小: {min(comp_scores):.1f}")
        print(f"  最大: {max(comp_scores):.1f}")

    # 改善提案
    print("\n" + "=" * 60)
    print("【改善提案】")
    print("=" * 60)

    miss_rate = len(missing_horses) / total_top3 * 100

    if miss_rate > 50:
        print("\n1. 印の数を増やす (◎○▲ → ◎○▲☆△)")
        print("   → 現在3頭のみ予測、5頭に拡張することを推奨")

    if ninki_dist.get("4-6番人気", 0) > len(missing_horses) * 0.3:
        print("\n2. 中穴馬の評価を改善")
        print("   → 4-6番人気の馬が多く漏れています")
        print("   → composite_scoreの計算式を調整")

    if ninki_dist.get("1-3番人気", 0) > len(missing_horses) * 0.2:
        print("\n3. 人気馬の評価を見直し")
        print("   → 上位人気馬を見逃しているケースがあります")

    print("\n4. フォーメーション買いの推奨")
    print("   → 1着軸: ◎○")
    print("   → 2-3着: ◎○▲☆△")
    print("   → この組み合わせで的中率向上が期待できます")

    return missing_horses, predicted_horses


if __name__ == "__main__":
    csv_path = r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv"
    analyze_missing_predictions(csv_path, num_races=50)
