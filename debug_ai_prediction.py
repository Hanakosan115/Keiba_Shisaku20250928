"""AI予測のデバッグスクリプト"""
import pandas as pd
import sys
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')
from improved_analyzer import ImprovedHorseAnalyzer
from prediction_integration import get_horse_past_results_from_csv

# CSVからテストデータを読み込み
data_dir = r"C:\Users\bu158\HorseRacingAnalyzer\data"
csv_path = data_dir + "\\netkeiba_data_combined_202001_202508.csv"
df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)

# 最初のレースを取得
race_id = df['race_id'].iloc[0]
race_horses = df[df['race_id'] == race_id].head(5)

analyzer = ImprovedHorseAnalyzer()

print("=" * 60)
print(f"レース: {race_id}")
print("=" * 60)

for _, horse in race_horses.iterrows():
    print(f"\n馬名: {horse.get('HorseName')}")
    print(f"オッズ: {horse.get('Odds')}")

    # 過去成績を取得
    horse_id = horse.get('horse_id')
    # レースIDから日付を抽出
    race_id_str = str(race_id)
    if len(race_id_str) >= 8:
        year = race_id_str[0:4]
        month = race_id_str[4:6]
        day = race_id_str[6:8]
        race_date = f"{year}-{month}-{day}"
    else:
        race_date = horse.get('date')
    print(f"horse_id: {horse_id}, race_date: {race_date} (from race_id: {race_id})")
    past_results = get_horse_past_results_from_csv(horse_id, race_date, max_results=5)

    print(f"過去成績件数: {len(past_results)}")
    if len(past_results) > 0:
        print(f"  最新の過去成績: 着順{past_results[0].get('rank')} ({past_results[0].get('date')})")

    # 特徴量計算
    horse_basic_info = {
        'Odds': horse.get('Odds'),
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

    # 重要な特徴量を表示
    print(f"  直近平均着順: {features.get('recent_rank_avg')}")
    print(f"  直近成績SD: {features.get('recent_rank_std')}")
    print(f"  距離適性: {features.get('distance_fitness')}")
    print(f"  馬場適性: {features.get('track_fitness')}")
    print(f"  騎手勝率: {features.get('jockey_win_rate')}")

    # AI予測
    ai_pred = analyzer.calculate_simple_ai_prediction(features)
    odds_rate = features.get('odds_win_rate', 0)

    print(f"  AI予測: {ai_pred:.4f} ({ai_pred*100:.2f}%)")
    print(f"  オッズ期待値: {odds_rate:.4f} ({odds_rate*100:.2f}%)")
    print(f"  乖離度: {(ai_pred - odds_rate):.4f}")
