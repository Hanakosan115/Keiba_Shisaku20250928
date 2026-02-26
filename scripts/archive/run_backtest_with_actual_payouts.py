"""
実際の配当データを使った正確なバックテスト
"""
import pandas as pd
import numpy as np
import pickle
import os
import sys
from improved_analyzer import ImprovedHorseAnalyzer

# prediction_integration.pyから過去成績取得関数をインポート
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')
from prediction_integration import get_horse_past_results_from_csv

def load_payout_cache(cache_file='payout_cache.pkl'):
    """配当キャッシュを読み込む"""
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return {}


def extract_umaban_from_payout(uma_str):
    """配当の馬番文字列から番号を抽出（例: '12' → 12, '3-5' → [3, 5]）"""
    uma_str = uma_str.strip()

    if '-' in uma_str:
        # 馬連・ワイドなど
        parts = uma_str.split('-')
        return [int(p.strip()) for p in parts if p.strip().isdigit()]
    else:
        # 単勝・複勝
        if uma_str.isdigit():
            return int(uma_str)
    return None


def check_tansho_hit(honmei_umaban, payout_data):
    """単勝的中チェック"""
    if '単勝' not in payout_data:
        return 0

    for item in payout_data['単勝']:
        uma = extract_umaban_from_payout(item['馬番'])
        if uma == honmei_umaban:
            return item['払戻']

    return 0


def check_fukusho_hit(honmei_umaban, payout_data):
    """複勝的中チェック"""
    if '複勝' not in payout_data:
        return 0

    for item in payout_data['複勝']:
        uma = extract_umaban_from_payout(item['馬番'])
        if uma == honmei_umaban:
            return item['払戻']

    return 0


def check_umaren_hit(honmei_umaban, taikou_umaban, payout_data):
    """馬連的中チェック"""
    if '馬連' not in payout_data:
        return 0

    target_set = {honmei_umaban, taikou_umaban}

    for item in payout_data['馬連']:
        uma_list = extract_umaban_from_payout(item['馬番'])
        # uma_listがintの場合はスキップ
        if isinstance(uma_list, list) and len(uma_list) == 2:
            if set(uma_list) == target_set:
                return item['払戻']

    return 0


def check_sanrenpuku_hit(honmei_umaban, taikou_umaban, ana_umaban, payout_data):
    """3連複的中チェック"""
    if '3連複' not in payout_data:
        return 0

    target_set = {honmei_umaban, taikou_umaban, ana_umaban}

    for item in payout_data['3連複']:
        uma_str = item['馬番']
        # 3連複は "1-2-3" 形式
        if isinstance(uma_str, str) and '-' in uma_str:
            parts = uma_str.split('-')
            uma_list = [int(p.strip()) for p in parts if p.strip().isdigit()]
            if len(uma_list) == 3 and set(uma_list) == target_set:
                return item['払戻']

    return 0


def check_sanrentan_hit(honmei_umaban, taikou_umaban, ana_umaban, honmei_rank, taikou_rank, ana_rank, payout_data):
    """3連単的中チェック（着順も確認）"""
    if '3連単' not in payout_data:
        return 0

    # ◎が1着、○が2着、▲が3着の場合のみ的中
    if not (honmei_rank == 1 and taikou_rank == 2 and ana_rank == 3):
        return 0

    target_order = f"{honmei_umaban}-{taikou_umaban}-{ana_umaban}"

    for item in payout_data['3連単']:
        uma_str = item['馬番'].replace(' ', '').replace('→', '-')
        if uma_str == target_order or uma_str == f"{honmei_umaban}{taikou_umaban}{ana_umaban}":
            return item['払戻']

    return 0


def run_backtest_with_actual_payouts(df, payout_cache, analyzer, test_races=500):
    """実際の配当データを使ったバックテスト"""
    print("\n" + "=" * 60)
    print(f"実配当データ使用バックテスト開始（{test_races}レース）")
    print("=" * 60)

    race_ids = df['race_id'].unique()[:test_races]
    print(f"テスト対象: {len(race_ids)}レース")
    print(f"配当データ保有: {len(payout_cache)}レース\n")

    results = {
        'tansho': {'bets': 0, 'hits': 0, 'investment': 0, 'return': 0, 'hit_details': []},
        'fukusho': {'bets': 0, 'hits': 0, 'investment': 0, 'return': 0, 'hit_details': []},
        'umaren': {'bets': 0, 'hits': 0, 'investment': 0, 'return': 0, 'hit_details': []},
        'sanrenpuku': {'bets': 0, 'hits': 0, 'investment': 0, 'return': 0, 'hit_details': []},
        'sanrentan': {'bets': 0, 'hits': 0, 'investment': 0, 'return': 0, 'hit_details': []}
    }

    processed = 0

    for idx, race_id in enumerate(race_ids):
        if (idx + 1) % 50 == 0:
            print(f"処理中: {idx + 1}/{len(race_ids)} レース")

        race_horses = df[df['race_id'] == race_id].copy()

        if len(race_horses) < 5:
            continue

        # 配当データがない場合はスキップ
        if race_id not in payout_cache:
            continue

        payout_data = payout_cache[race_id]

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
            # レースIDから日付を抽出（YYYYMMDDCCR形式）
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

            # 簡易AI予測モデルを使用
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

        # ◎○▲を取得
        honmei = next((h for h in horses_with_marks if h.get('mark') == '◎'), None)
        taikou = next((h for h in horses_with_marks if h.get('mark') == '○'), None)
        ana = next((h for h in horses_with_marks if h.get('mark') == '▲'), None)

        if not honmei:
            continue

        processed += 1

        # 単勝
        tansho_payout = check_tansho_hit(honmei['umaban'], payout_data)
        results['tansho']['bets'] += 1
        results['tansho']['investment'] += 100
        if tansho_payout > 0:
            results['tansho']['hits'] += 1
            results['tansho']['return'] += tansho_payout

        # 複勝
        fukusho_payout = check_fukusho_hit(honmei['umaban'], payout_data)
        results['fukusho']['bets'] += 1
        results['fukusho']['investment'] += 100
        if fukusho_payout > 0:
            results['fukusho']['hits'] += 1
            results['fukusho']['return'] += fukusho_payout

        # 馬連
        if taikou:
            umaren_payout = check_umaren_hit(honmei['umaban'], taikou['umaban'], payout_data)
            results['umaren']['bets'] += 1
            results['umaren']['investment'] += 100
            if umaren_payout > 0:
                results['umaren']['hits'] += 1
                results['umaren']['return'] += umaren_payout

        # 3連複
        if taikou and ana:
            sanrenpuku_payout = check_sanrenpuku_hit(honmei['umaban'], taikou['umaban'], ana['umaban'], payout_data)
            results['sanrenpuku']['bets'] += 1
            results['sanrenpuku']['investment'] += 100
            if sanrenpuku_payout > 0:
                results['sanrenpuku']['hits'] += 1
                results['sanrenpuku']['return'] += sanrenpuku_payout

        # 3連単
        if taikou and ana:
            sanrentan_payout = check_sanrentan_hit(
                honmei['umaban'], taikou['umaban'], ana['umaban'],
                honmei['actual_rank'], taikou['actual_rank'], ana['actual_rank'],
                payout_data
            )
            results['sanrentan']['bets'] += 1
            results['sanrentan']['investment'] += 100
            if sanrentan_payout > 0:
                results['sanrentan']['hits'] += 1
                results['sanrentan']['return'] += sanrentan_payout
                # 的中レース詳細を記録
                results['sanrentan']['hit_details'].append({
                    'race_id': race_id,
                    'honmei': f"{honmei['umaban']}番 {honmei['horse_name']} ({honmei['actual_rank']}着)",
                    'taikou': f"{taikou['umaban']}番 {taikou['horse_name']} ({taikou['actual_rank']}着)",
                    'ana': f"{ana['umaban']}番 {ana['horse_name']} ({ana['actual_rank']}着)",
                    'payout': sanrentan_payout
                })

    print(f"\n処理完了: {processed}レース")
    return results


def print_results(results):
    """結果表示"""
    print("\n" + "=" * 60)
    print("【実配当データを使った回収率】")
    print("=" * 60)

    bet_types = {
        'tansho': '本命（◎）単勝',
        'fukusho': '本命（◎）複勝',
        'umaren': '馬連（◎-○）',
        'sanrenpuku': '3連複（◎-○-▲）',
        'sanrentan': '3連単（◎→○→▲）'
    }

    for key, name in bet_types.items():
        data = results[key]

        if data['bets'] == 0:
            continue

        hit_rate = (data['hits'] / data['bets'] * 100) if data['bets'] > 0 else 0
        recovery_rate = (data['return'] / data['investment'] * 100) if data['investment'] > 0 else 0
        avg_payout = (data['return'] / data['hits']) if data['hits'] > 0 else 0

        print(f"\n[{name}]")
        print(f"  購入数: {data['bets']}回")
        print(f"  的中数: {data['hits']}回")
        print(f"  的中率: {hit_rate:.1f}%")
        print(f"  投資額: {data['investment']:,}円")
        print(f"  払戻額: {data['return']:,}円")
        print(f"  回収率: {recovery_rate:.1f}%")
        print(f"  平均配当: {avg_payout:.0f}円")

        if recovery_rate >= 100:
            print(f"  ★ プラス収支！")
        elif recovery_rate >= 90:
            print(f"  → 優秀（90%以上）")
        elif recovery_rate >= 80:
            print(f"  → 良好（80%以上）")

        # 3連単の的中レース詳細を表示
        if key == 'sanrentan' and data['hit_details']:
            print(f"\n  【的中レース詳細】")
            for i, detail in enumerate(data['hit_details'], 1):
                print(f"  {i}. レースID: {detail['race_id']}")
                print(f"     ◎ {detail['honmei']}")
                print(f"     ○ {detail['taikou']}")
                print(f"     ▲ {detail['ana']}")
                print(f"     配当: {detail['payout']:,}円")

    print("\n" + "=" * 60)


def main():
    """メイン処理"""
    print("=" * 60)
    print("実配当データ使用バックテスト")
    print("=" * 60)

    # データ読み込み
    data_dir = r"C:\Users\bu158\HorseRacingAnalyzer\data"
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and 'combined' in f]

    if not csv_files:
        print("エラー: CSVファイルが見つかりません")
        return

    csv_path = os.path.join(data_dir, csv_files[0])
    print(f"CSV読み込み: {csv_files[0]}")
    df = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)

    # 配当キャッシュ読み込み
    cache_file = r'C:\Users\bu158\Keiba_Shisaku20250928\payout_cache.pkl'
    payout_cache = load_payout_cache(cache_file)
    print(f"配当データ読み込み: {len(payout_cache)}レース\n")

    # アナライザー初期化
    analyzer = ImprovedHorseAnalyzer()

    # バックテスト実行（500レース）
    results = run_backtest_with_actual_payouts(df, payout_cache, analyzer, test_races=500)

    # 結果表示
    print_results(results)

    print("\n[完了] 実配当データ使用バックテスト完了")


if __name__ == "__main__":
    main()
