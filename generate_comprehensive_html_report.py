"""
包括的HTMLレポート生成
"""
import json
from datetime import datetime

# JSONデータ読み込み
with open(r'C:\Users\bu158\Keiba_Shisaku20250928\comprehensive_backtest_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

total = data['total']
by_year = data['by_year']

# HTML生成
html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>競馬予測システム - 包括的バックテストレポート</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', 'Yu Gothic', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        .header {{
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            margin-bottom: 30px;
            text-align: center;
        }}
        .header h1 {{
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 20px;
        }}
        .header .period {{
            font-size: 1.3em;
            color: #666;
            margin-bottom: 10px;
        }}
        .header .total-races {{
            font-size: 2em;
            color: #764ba2;
            font-weight: bold;
        }}

        .mega-summary {{
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            margin-bottom: 30px;
            text-align: center;
        }}
        .mega-summary h2 {{
            font-size: 2em;
            margin-bottom: 30px;
        }}
        .mega-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}
        .mega-stat {{
            background: rgba(255,255,255,0.2);
            padding: 20px;
            border-radius: 10px;
        }}
        .mega-stat .label {{
            font-size: 0.9em;
            margin-bottom: 10px;
            opacity: 0.9;
        }}
        .mega-stat .value {{
            font-size: 2.5em;
            font-weight: bold;
        }}

        .ticket-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .ticket-card {{
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
        }}
        .ticket-card h3 {{
            color: #667eea;
            font-size: 1.8em;
            margin-bottom: 20px;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        .ticket-stat {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        .ticket-stat .label {{
            color: #666;
            font-weight: 500;
        }}
        .ticket-stat .value {{
            font-weight: bold;
            color: #333;
        }}
        .ticket-stat.highlight {{
            background: #f0f7ff;
            padding: 15px;
            border-radius: 5px;
            border: none;
        }}
        .ticket-stat.highlight .value {{
            font-size: 1.3em;
            color: #667eea;
        }}

        .recovery-high {{
            color: #10b981 !important;
        }}
        .recovery-medium {{
            color: #f59e0b !important;
        }}
        .recovery-low {{
            color: #ef4444 !important;
        }}

        .yearly-section {{
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 5px 20px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }}
        .yearly-section h2 {{
            color: #667eea;
            font-size: 2em;
            margin-bottom: 30px;
            text-align: center;
        }}

        .year-card {{
            background: linear-gradient(135deg, #f6f8fb 0%, #e9ecef 100%);
            padding: 25px;
            border-radius: 10px;
            margin-bottom: 20px;
            border-left: 5px solid #667eea;
        }}
        .year-card h3 {{
            color: #764ba2;
            font-size: 1.5em;
            margin-bottom: 15px;
        }}
        .year-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 15px;
        }}
        .year-stat {{
            background: white;
            padding: 15px;
            border-radius: 8px;
        }}
        .year-stat .ticket-name {{
            color: #666;
            font-size: 0.9em;
            margin-bottom: 5px;
        }}
        .year-stat .stats {{
            font-size: 0.95em;
            color: #333;
        }}

        .year-summary {{
            background: #667eea;
            color: white;
            padding: 20px;
            border-radius: 8px;
            margin-top: 15px;
            text-align: center;
        }}
        .year-summary .combined {{
            font-size: 1.5em;
            font-weight: bold;
        }}

        .footer {{
            text-align: center;
            color: white;
            margin-top: 30px;
            padding: 20px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏇 競馬予測システム 包括的バックテストレポート</h1>
            <p class="period">2020年1月 ～ 2025年8月</p>
            <p class="total-races">{total['total']:,} レース</p>
            <p style="color: #999; margin-top: 10px;">生成日時: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>

        <div class="mega-summary">
            <h2>📈 全期間合計（全券種合算）</h2>
            <div class="mega-stats">
                <div class="mega-stat">
                    <div class="label">総投資額</div>
                    <div class="value">{(total['umaren_cost'] + total['umatan_cost'] + total['wide_cost'] + total['sanrenpuku_cost'] + total['sanrentan_cost']):,}円</div>
                </div>
                <div class="mega-stat">
                    <div class="label">総払戻額</div>
                    <div class="value">{(total['umaren_return'] + total['umatan_return'] + total['wide_return'] + total['sanrenpuku_return'] + total['sanrentan_return']):,}円</div>
                </div>
                <div class="mega-stat">
                    <div class="label">合算回収率</div>
                    <div class="value">{((total['umaren_return'] + total['umatan_return'] + total['wide_return'] + total['sanrenpuku_return'] + total['sanrentan_return']) / (total['umaren_cost'] + total['umatan_cost'] + total['wide_cost'] + total['sanrenpuku_cost'] + total['sanrentan_cost']) * 100):.1f}%</div>
                </div>
                <div class="mega-stat">
                    <div class="label">総損益</div>
                    <div class="value">{((total['umaren_return'] + total['umatan_return'] + total['wide_return'] + total['sanrenpuku_return'] + total['sanrentan_return']) - (total['umaren_cost'] + total['umatan_cost'] + total['wide_cost'] + total['sanrenpuku_cost'] + total['sanrentan_cost'])):+,}円</div>
                </div>
            </div>
        </div>

        <div class="ticket-grid">
"""

# 馬連
if total['umaren_cost'] > 0:
    recovery = (total['umaren_return'] / total['umaren_cost']) * 100
    recovery_class = 'recovery-high' if recovery >= 100 else 'recovery-medium' if recovery >= 80 else 'recovery-low'
    html += f"""
            <div class="ticket-card">
                <h3>🎯 馬連（3頭BOX）</h3>
                <div class="ticket-stat">
                    <span class="label">的中回数</span>
                    <span class="value">{total['umaren_hit']:,}回 / {total['total']:,}レース</span>
                </div>
                <div class="ticket-stat">
                    <span class="label">的中率</span>
                    <span class="value">{total['umaren_hit']/total['total']*100:.2f}%</span>
                </div>
                <div class="ticket-stat">
                    <span class="label">投資額</span>
                    <span class="value">{total['umaren_cost']:,}円</span>
                </div>
                <div class="ticket-stat">
                    <span class="label">払戻額</span>
                    <span class="value">{total['umaren_return']:,}円</span>
                </div>
                <div class="ticket-stat highlight">
                    <span class="label">回収率</span>
                    <span class="value {recovery_class}">{recovery:.2f}%</span>
                </div>
                <div class="ticket-stat highlight">
                    <span class="label">損益</span>
                    <span class="value">{total['umaren_return'] - total['umaren_cost']:+,}円</span>
                </div>
            </div>
"""

# 馬単
if total['umatan_cost'] > 0:
    recovery = (total['umatan_return'] / total['umatan_cost']) * 100
    recovery_class = 'recovery-high' if recovery >= 100 else 'recovery-medium' if recovery >= 80 else 'recovery-low'
    html += f"""
            <div class="ticket-card">
                <h3>🎯 馬単（3頭BOX）</h3>
                <div class="ticket-stat">
                    <span class="label">的中回数</span>
                    <span class="value">{total['umatan_hit']:,}回 / {total['total']:,}レース</span>
                </div>
                <div class="ticket-stat">
                    <span class="label">的中率</span>
                    <span class="value">{total['umatan_hit']/total['total']*100:.2f}%</span>
                </div>
                <div class="ticket-stat">
                    <span class="label">投資額</span>
                    <span class="value">{total['umatan_cost']:,}円</span>
                </div>
                <div class="ticket-stat">
                    <span class="label">払戻額</span>
                    <span class="value">{total['umatan_return']:,}円</span>
                </div>
                <div class="ticket-stat highlight">
                    <span class="label">回収率</span>
                    <span class="value {recovery_class}">{recovery:.2f}%</span>
                </div>
                <div class="ticket-stat highlight">
                    <span class="label">損益</span>
                    <span class="value">{total['umatan_return'] - total['umatan_cost']:+,}円</span>
                </div>
            </div>
"""

# 3連複
if total['sanrenpuku_cost'] > 0:
    recovery = (total['sanrenpuku_return'] / total['sanrenpuku_cost']) * 100
    recovery_class = 'recovery-high' if recovery >= 100 else 'recovery-medium' if recovery >= 80 else 'recovery-low'
    html += f"""
            <div class="ticket-card">
                <h3>🎯 3連複（3頭BOX）</h3>
                <div class="ticket-stat">
                    <span class="label">的中回数</span>
                    <span class="value">{total['sanrenpuku_hit']:,}回 / {total['total']:,}レース</span>
                </div>
                <div class="ticket-stat">
                    <span class="label">的中率</span>
                    <span class="value">{total['sanrenpuku_hit']/total['total']*100:.2f}%</span>
                </div>
                <div class="ticket-stat">
                    <span class="label">投資額</span>
                    <span class="value">{total['sanrenpuku_cost']:,}円</span>
                </div>
                <div class="ticket-stat">
                    <span class="label">払戻額</span>
                    <span class="value">{total['sanrenpuku_return']:,}円</span>
                </div>
                <div class="ticket-stat highlight">
                    <span class="label">回収率</span>
                    <span class="value {recovery_class}">{recovery:.2f}%</span>
                </div>
                <div class="ticket-stat highlight">
                    <span class="label">損益</span>
                    <span class="value">{total['sanrenpuku_return'] - total['sanrenpuku_cost']:+,}円</span>
                </div>
            </div>
"""

# 3連単
if total['sanrentan_cost'] > 0:
    recovery = (total['sanrentan_return'] / total['sanrentan_cost']) * 100
    recovery_class = 'recovery-high' if recovery >= 100 else 'recovery-medium' if recovery >= 80 else 'recovery-low'
    html += f"""
            <div class="ticket-card">
                <h3>🎯 3連単（3頭BOX）</h3>
                <div class="ticket-stat">
                    <span class="label">的中回数</span>
                    <span class="value">{total['sanrentan_hit']:,}回 / {total['total']:,}レース</span>
                </div>
                <div class="ticket-stat">
                    <span class="label">的中率</span>
                    <span class="value">{total['sanrentan_hit']/total['total']*100:.2f}%</span>
                </div>
                <div class="ticket-stat">
                    <span class="label">投資額</span>
                    <span class="value">{total['sanrentan_cost']:,}円</span>
                </div>
                <div class="ticket-stat">
                    <span class="label">払戻額</span>
                    <span class="value">{total['sanrentan_return']:,}円</span>
                </div>
                <div class="ticket-stat highlight">
                    <span class="label">回収率</span>
                    <span class="value {recovery_class}">{recovery:.2f}%</span>
                </div>
                <div class="ticket-stat highlight">
                    <span class="label">損益</span>
                    <span class="value">{total['sanrentan_return'] - total['sanrentan_cost']:+,}円</span>
                </div>
            </div>
"""

html += """
        </div>

        <div class="yearly-section">
            <h2>📅 年ごとの詳細結果</h2>
"""

# 年ごとの結果
for year_name, year_data in by_year.items():
    r = year_data['3box']
    if r['total'] == 0:
        continue

    year_total_investment = r['umaren_cost'] + r['umatan_cost'] + r['wide_cost'] + r['sanrenpuku_cost'] + r['sanrentan_cost']
    year_total_payout = r['umaren_return'] + r['umatan_return'] + r['wide_return'] + r['sanrenpuku_return'] + r['sanrentan_return']
    year_combined_recovery = (year_total_payout / year_total_investment * 100) if year_total_investment > 0 else 0

    html += f"""
            <div class="year-card">
                <h3>📆 {year_name}</h3>
                <p style="color: #666; margin-bottom: 10px;">対象レース: {r['total']:,}レース</p>

                <div class="year-stats">
"""

    # 馬連
    if r['umaren_cost'] > 0:
        recovery = (r['umaren_return'] / r['umaren_cost']) * 100
        html += f"""
                    <div class="year-stat">
                        <div class="ticket-name">馬連</div>
                        <div class="stats">的中率: {r['umaren_hit']/r['total']*100:.1f}%</div>
                        <div class="stats">回収率: {recovery:.1f}%</div>
                    </div>
"""

    # 馬単
    if r['umatan_cost'] > 0:
        recovery = (r['umatan_return'] / r['umatan_cost']) * 100
        html += f"""
                    <div class="year-stat">
                        <div class="ticket-name">馬単</div>
                        <div class="stats">的中率: {r['umatan_hit']/r['total']*100:.1f}%</div>
                        <div class="stats">回収率: {recovery:.1f}%</div>
                    </div>
"""

    # 3連複
    if r['sanrenpuku_cost'] > 0:
        recovery = (r['sanrenpuku_return'] / r['sanrenpuku_cost']) * 100
        html += f"""
                    <div class="year-stat">
                        <div class="ticket-name">3連複</div>
                        <div class="stats">的中率: {r['sanrenpuku_hit']/r['total']*100:.1f}%</div>
                        <div class="stats">回収率: {recovery:.1f}%</div>
                    </div>
"""

    # 3連単
    if r['sanrentan_cost'] > 0:
        recovery = (r['sanrentan_return'] / r['sanrentan_cost']) * 100
        html += f"""
                    <div class="year-stat">
                        <div class="ticket-name">3連単</div>
                        <div class="stats">的中率: {r['sanrentan_hit']/r['total']*100:.1f}%</div>
                        <div class="stats">回収率: {recovery:.1f}%</div>
                    </div>
"""

    html += f"""
                </div>

                <div class="year-summary">
                    <div>合算回収率: <span class="combined">{year_combined_recovery:.1f}%</span></div>
                    <div>損益: {year_total_payout - year_total_investment:+,}円</div>
                </div>
            </div>
"""

html += """
        </div>

        <div class="footer">
            <p>🤖 Generated by Claude Code - 競馬予測システム</p>
            <p style="margin-top: 10px; font-size: 0.9em;">過去の成績は将来の結果を保証するものではありません。馬券購入は自己責任で行ってください。</p>
        </div>
    </div>
</body>
</html>
"""

# HTMLファイル保存
output_path = r"C:\Users\bu158\Keiba_Shisaku20250928\comprehensive_backtest_report.html"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("\n" + "=" * 80)
print("包括的HTMLレポートを生成しました！")
print("=" * 80)
print(f"\n出力先: {output_path}")
print("\nブラウザで開いて確認してください。")
print("\n【ハイライト】")
print(f"  - 総レース数: {total['total']:,}レース")
print(f"  - 合算回収率: {((total['umaren_return'] + total['umatan_return'] + total['wide_return'] + total['sanrenpuku_return'] + total['sanrentan_return']) / (total['umaren_cost'] + total['umatan_cost'] + total['wide_cost'] + total['sanrenpuku_cost'] + total['sanrentan_cost']) * 100):.1f}%")
print(f"  - 総損益: {((total['umaren_return'] + total['umatan_return'] + total['wide_return'] + total['sanrenpuku_return'] + total['sanrentan_return']) - (total['umaren_cost'] + total['umatan_cost'] + total['wide_cost'] + total['sanrenpuku_cost'] + total['sanrentan_cost'])):+,}円")
print("=" * 80)
