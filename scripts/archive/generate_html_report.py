"""
HTML形式のバックテストレポート生成
"""
import pandas as pd
import json
import sys
from itertools import combinations
from datetime import datetime
sys.path.insert(0, r'C:\Users\bu158\Keiba_Shisaku20250928')

from prediction_integration import get_horse_past_results_from_csv

def load_payout_data(json_path):
    with open(json_path, 'r', encoding='utf-8') as f:
        payout_list = json.load(f)
    return {str(item.get('race_id', '')): item for item in payout_list}

def calculate_horse_score(horse_basic_info, race_conditions):
    """過去成績のみで馬のスコアを計算"""
    score = 50.0

    race_results = horse_basic_info.get('race_results', [])

    if not race_results or len(race_results) == 0:
        return 30.0

    # 直近3走の平均着順
    recent_ranks = []
    for race in race_results[:3]:
        if isinstance(race, dict):
            rank = pd.to_numeric(race.get('rank'), errors='coerce')
            if pd.notna(rank):
                recent_ranks.append(rank)

    if recent_ranks:
        avg_rank = sum(recent_ranks) / len(recent_ranks)
        if avg_rank <= 2:
            score += 30
        elif avg_rank <= 3:
            score += 20
        elif avg_rank <= 5:
            score += 10
        elif avg_rank <= 8:
            score += 5
        else:
            score -= 10

        if len(recent_ranks) >= 2:
            import numpy as np
            std = np.std(recent_ranks)
            if std <= 1:
                score += 10
            elif std <= 2:
                score += 5
            elif std >= 5:
                score -= 5

    # 距離適性
    current_distance = pd.to_numeric(race_conditions.get('Distance'), errors='coerce')
    if pd.notna(current_distance):
        distance_fit_score = 0
        distance_count = 0

        for race in race_results[:5]:
            if isinstance(race, dict):
                past_distance = pd.to_numeric(race.get('distance'), errors='coerce')
                past_rank = pd.to_numeric(race.get('rank'), errors='coerce')

                if pd.notna(past_distance) and pd.notna(past_rank):
                    distance_diff = abs(current_distance - past_distance)

                    if distance_diff <= 200:
                        if past_rank <= 3:
                            distance_fit_score += 15
                        elif past_rank <= 5:
                            distance_fit_score += 5
                        distance_count += 1

        if distance_count > 0:
            score += distance_fit_score / distance_count

    return score

# データ読み込み
print("データ読み込み中...")
df = pd.read_csv(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_combined_202001_202508.csv",
                 encoding='utf-8', low_memory=False)
payout_dict = load_payout_data(r"C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202508.json")

# 2025年6-8月を正しく抽出
df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
target_races = df[
    (df['date_parsed'] >= '2025-06-01') &
    (df['date_parsed'] <= '2025-08-31')
]

race_ids = target_races.groupby('race_id').filter(lambda x: len(x) >= 8)['race_id'].unique()
print(f"対象レース: {len(race_ids)}レース")

# バックテスト実行（サンプル30レース）
sample_size = 30
race_details = []

print(f"\nサンプル{sample_size}レース処理中...")

for idx, race_id in enumerate(race_ids[:sample_size]):
    race_horses = df[df['race_id'] == race_id].copy()

    if len(race_horses) < 8:
        continue

    race_date = race_horses.iloc[0]['date']
    if pd.isna(race_date):
        continue

    race_date_str = str(race_date)[:10]

    # レース情報
    first_row = race_horses.iloc[0]
    race_info = {
        'race_id': race_id,
        'date': race_date_str,
        'track': first_row.get('track_name', ''),
        'name': first_row.get('race_name', ''),
        'distance': first_row.get('distance', ''),
        'course_type': first_row.get('course_type', '')
    }

    # 予測実行
    horses_scores = []

    for _, horse in race_horses.iterrows():
        horse_id = horse.get('horse_id')
        past_results = get_horse_past_results_from_csv(horse_id, race_date_str, max_results=5)

        horse_basic_info = {
            'HorseName': horse.get('HorseName'),
            'race_results': past_results
        }

        race_conditions = {
            'Distance': horse.get('distance'),
            'CourseType': horse.get('course_type'),
            'TrackCondition': horse.get('track_condition')
        }

        score = calculate_horse_score(horse_basic_info, race_conditions)

        horses_scores.append({
            'umaban': int(horse.get('Umaban', 0)),
            'name': horse.get('HorseName', ''),
            'score': score,
            'actual_rank': horse.get('Rank'),
            'actual_ninki': horse.get('Ninki')
        })

    # スコア順にソート
    horses_scores.sort(key=lambda x: x['score'], reverse=True)

    top3 = [h['umaban'] for h in horses_scores[:3]]
    top5 = [h['umaban'] for h in horses_scores[:5]]

    # 実際の結果
    actual_top3 = sorted(
        race_horses[['Umaban', 'HorseName', 'Rank']].values.tolist(),
        key=lambda x: x[2]
    )[:3]

    # 配当取得
    race_id_str = str(race_id)
    payout_data = payout_dict.get(race_id_str, {})

    # 的中判定
    umaren_hit = False
    umaren_payout = 0
    sanrenpuku_hit = False
    sanrenpuku_payout = 0

    if '馬連' in payout_data:
        umaren_data = payout_data['馬連']
        winning_pairs = umaren_data.get('馬番', [])
        payouts = umaren_data.get('払戻金', [])

        if winning_pairs and len(winning_pairs) >= 2:
            try:
                winning_pair = set([int(x) for x in winning_pairs[:2]])
                if all(num in top3 for num in winning_pair):
                    umaren_hit = True
                    umaren_payout = payouts[0] if payouts else 0
            except:
                pass

    if '3連複' in payout_data:
        sanrenpuku_data = payout_data['3連複']
        winning_trio = sanrenpuku_data.get('馬番', [])
        payouts = sanrenpuku_data.get('払戻金', [])

        if winning_trio and len(winning_trio) >= 3:
            try:
                winning_set = set([int(x) for x in winning_trio[:3]])
                if winning_set == set(top3):
                    sanrenpuku_hit = True
                    sanrenpuku_payout = payouts[0] if payouts else 0
            except:
                pass

    race_details.append({
        'info': race_info,
        'prediction': {'top3': top3, 'top5': top5},
        'actual': actual_top3,
        'horses': horses_scores[:5],
        'umaren': {'hit': umaren_hit, 'payout': umaren_payout},
        'sanrenpuku': {'hit': sanrenpuku_hit, 'payout': sanrenpuku_payout}
    })

# HTML生成
html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>競馬予測システム - バックテストレポート</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .summary-card h3 {{
            margin-top: 0;
            color: #667eea;
        }}
        .summary-card .value {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        .race-card {{
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .race-header {{
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }}
        .hit {{
            background: #d4edda;
            color: #155724;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }}
        .miss {{
            background: #f8d7da;
            color: #721c24;
            padding: 5px 10px;
            border-radius: 5px;
            font-weight: bold;
        }}
        .prediction {{
            display: flex;
            gap: 10px;
            margin: 10px 0;
        }}
        .horse {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
        }}
        th, td {{
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #667eea;
            color: white;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>競馬予測システム - バックテストレポート</h1>
        <p>生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        <p>対象期間: 2025年6月1日 ～ 2025年8月31日</p>
        <p>サンプルレース数: {len(race_details)}レース</p>
    </div>

    <div class="summary">
        <div class="summary-card">
            <h3>馬連（3頭BOX）</h3>
            <div class="value">{sum(1 for r in race_details if r['umaren']['hit'])}/{len(race_details)}</div>
            <p>的中率: {sum(1 for r in race_details if r['umaren']['hit'])/len(race_details)*100:.1f}%</p>
        </div>
        <div class="summary-card">
            <h3>3連複（3頭BOX）</h3>
            <div class="value">{sum(1 for r in race_details if r['sanrenpuku']['hit'])}/{len(race_details)}</div>
            <p>的中率: {sum(1 for r in race_details if r['sanrenpuku']['hit'])/len(race_details)*100:.1f}%</p>
        </div>
        <div class="summary-card">
            <h3>馬連回収率</h3>
            <div class="value">{sum(r['umaren']['payout'] for r in race_details)/(len(race_details)*300)*100:.1f}%</div>
            <p>投資: {len(race_details)*300:,}円 → 払戻: {sum(r['umaren']['payout'] for r in race_details):,}円</p>
        </div>
        <div class="summary-card">
            <h3>3連複回収率</h3>
            <div class="value">{sum(r['sanrenpuku']['payout'] for r in race_details)/(len(race_details)*100)*100:.1f}%</div>
            <p>投資: {len(race_details)*100:,}円 → 払戻: {sum(r['sanrenpuku']['payout'] for r in race_details):,}円</p>
        </div>
    </div>

    <h2>レース詳細</h2>
"""

for idx, race in enumerate(race_details, 1):
    info = race['info']
    pred = race['prediction']
    actual = race['actual']

    html += f"""
    <div class="race-card">
        <div class="race-header">
            <h3>#{idx}: {info['date']} {info['track']} - {info['name']}</h3>
            <p>距離: {info['distance']}m {info['course_type']}</p>
        </div>

        <div class="prediction">
            <div><strong>予測TOP3:</strong> {pred['top3']}</div>
            <div>
                馬連: <span class="{'hit' if race['umaren']['hit'] else 'miss'}">
                    {'的中' if race['umaren']['hit'] else '不的中'}
                </span>
                {f"({race['umaren']['payout']:,}円)" if race['umaren']['hit'] else ''}
            </div>
            <div>
                3連複: <span class="{'hit' if race['sanrenpuku']['hit'] else 'miss'}">
                    {'的中' if race['sanrenpuku']['hit'] else '不的中'}
                </span>
                {f"({race['sanrenpuku']['payout']:,}円)" if race['sanrenpuku']['hit'] else ''}
            </div>
        </div>

        <table>
            <tr>
                <th>順位</th>
                <th>馬番</th>
                <th>馬名</th>
                <th>AIスコア</th>
            </tr>
"""

    for i, horse in enumerate(race['horses'], 1):
        mark = ['◎', '○', '▲', '△', '☆'][i-1] if i <= 5 else ''
        html += f"""
            <tr>
                <td>{mark} {i}位</td>
                <td>{horse['umaban']}番</td>
                <td>{horse['name']}</td>
                <td>{horse['score']:.1f}</td>
            </tr>
"""

    html += """
        </table>

        <div><strong>実際の結果:</strong></div>
        <div class="prediction">
"""

    for rank, (umaban, name, _) in enumerate(actual, 1):
        html += f"<div class='horse'>{rank}着: {int(umaban)}番 {name}</div>"

    html += """
        </div>
    </div>
"""

html += """
</body>
</html>
"""

# HTMLファイル保存
output_path = r"C:\Users\bu158\Keiba_Shisaku20250928\backtest_report.html"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"\n完了！HTMLレポートを生成しました:")
print(f"→ {output_path}")
print(f"\nブラウザで開いて確認してください。")
