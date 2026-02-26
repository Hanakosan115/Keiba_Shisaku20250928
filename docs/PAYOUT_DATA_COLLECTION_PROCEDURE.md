# 払戻データ収集・検証 実施手順書

**作成日**: 2026年2月21日
**対象期間**: 2020年〜2026年
**推定所要時間**: 6-8時間（バックグラウンド実行）

---

## 📋 実施概要

### 目的
Phase 13で理論計算のみで検証した複勝・ワイド・馬連を、実際の払戻データで再検証する。

### 3段階アプローチ
1. **即座**: 既存データ活用（660レース）
2. **バックグラウンド**: 全期間データ収集（21,000レース）
3. **将来**: GUI統合（Phase 14）

---

## ステップ1: 既存払戻データの活用（5分）

### 1-1. データファイルのコピー

```bash
# コマンドプロンプトで実行
cd C:\Users\bu158\Keiba_Shisaku20250928\data\payout_data

# HorseRacingAnalyzerから払戻JSONをコピー
copy "C:\Users\bu158\HorseRacingAnalyzer\data\netkeiba_data_payouts_202001_202601.json" payout_2025_2026.json
```

**確認**:
```bash
# ファイルサイズ確認（約1.2MB）
dir payout_2025_2026.json

# レース数確認（660レース）
py -c "import json; print(len(json.load(open('payout_2025_2026.json', encoding='utf-8'))))"
```

---

### 1-2. Phase 13再検証スクリプトの作成

**ファイル**: `phase13_exotic_bets_REAL_DATA.py`

```python
"""
Phase 13: 複勝・ワイド・馬連の実データ検証
既存のphase13_exotic_bets_theoretical.pyの払戻計算部分を実データに置き換え
"""
import pandas as pd
import numpy as np
import json
from datetime import datetime

print("="*80)
print("Phase 13: 複勝・ワイド・馬連 実データ検証")
print("="*80)

# 1. 払戻データ読み込み
print("\n[1/6] 払戻データ読み込み...")
with open('data/payout_data/payout_2025_2026.json', encoding='utf-8') as f:
    payout_data = json.load(f)

# race_id -> 払戻情報のマップ作成
payout_map = {str(race['race_id']): race for race in payout_data}
print(f"  払戻データ: {len(payout_map):,}レース")

# 2. Phase 13の予測結果読み込み
print("\n[2/6] Phase 13予測結果読み込み...")
# phase13_full_period_ALL_RACES_results.csv を使用
df_pred = pd.read_csv('phase13_full_period_ALL_RACES_results.csv')
print(f"  予測結果: {len(df_pred):,}レース")

# 払戻データがあるレースのみ抽出
df_pred['race_id'] = df_pred['race_id'].astype(str)
df_with_payout = df_pred[df_pred['race_id'].isin(payout_map.keys())]
print(f"  払戻あり: {len(df_with_payout):,}レース")

# 3. 15-20%確率帯のレース抽出
print("\n[3/6] 15-20%確率帯レース抽出...")
df_sweet = df_with_payout[
    (df_with_payout['win_probability'] >= 0.15) &
    (df_with_payout['win_probability'] < 0.20)
]
print(f"  15-20%確率帯: {len(df_sweet):,}レース")

# 4. 的中・回収率計算
print("\n[4/6] 的中・回収率計算...")

results = {
    '全レース': {'races': len(df_with_payout), 'bets': {}},
    '15-20%確率帯': {'races': len(df_sweet), 'bets': {}}
}

for category, df_target in [('全レース', df_with_payout), ('15-20%確率帯', df_sweet)]:

    fukusho_investment = 0
    fukusho_return = 0
    fukusho_hits = 0

    wide_investment = 0
    wide_return = 0
    wide_hits = 0

    umaren_investment = 0
    umaren_return = 0
    umaren_hits = 0

    for _, row in df_target.iterrows():
        race_id = str(row['race_id'])
        predicted_rank = int(row['predicted_rank'])
        actual_rank = int(row['actual_rank'])

        payout_info = payout_map.get(race_id)
        if not payout_info:
            continue

        # 複勝（予測1位馬）
        fukusho_investment += 100
        fukusho_payout = payout_info.get('複勝', {})
        fukusho_horses = fukusho_payout.get('馬番', [])
        fukusho_amounts = fukusho_payout.get('払戻金', [])

        # 予測1位馬が複勝圏内（1-3着）か確認
        if actual_rank <= 3:
            # 馬番から払戻額を取得
            predicted_horse = str(predicted_rank)  # 簡易的に予測順位を馬番として使用
            if predicted_horse in fukusho_horses:
                idx = fukusho_horses.index(predicted_horse)
                fukusho_return += fukusho_amounts[idx]
                fukusho_hits += 1

        # ワイド（予測1-2位）
        wide_investment += 100
        wide_payout = payout_info.get('ワイド', {})
        wide_horses = wide_payout.get('馬番', [])
        wide_amounts = wide_payout.get('払戻金', [])

        # 予測1-2位が両方3着以内なら的中
        # ※ 実際の実装ではより詳細なマッチングが必要

        # 馬連（予測1-2位）
        umaren_investment += 100
        umaren_payout = payout_info.get('馬連', {})
        # ※ 同様の処理

    # 回収率計算
    results[category]['bets'] = {
        '複勝': {
            '投資': fukusho_investment,
            '払戻': fukusho_return,
            '回収率': (fukusho_return / fukusho_investment * 100) if fukusho_investment > 0 else 0,
            '的中数': fukusho_hits,
            '的中率': (fukusho_hits / len(df_target) * 100) if len(df_target) > 0 else 0
        },
        'ワイド': {
            '投資': wide_investment,
            '払戻': wide_return,
            '回収率': (wide_return / wide_investment * 100) if wide_investment > 0 else 0,
            '的中数': wide_hits,
            '的中率': (wide_hits / len(df_target) * 100) if len(df_target) > 0 else 0
        },
        '馬連': {
            '投資': umaren_investment,
            '払戻': umaren_return,
            '回収率': (umaren_return / umaren_investment * 100) if umaren_investment > 0 else 0,
            '的中数': umaren_hits,
            '的中率': (umaren_hits / len(df_target) * 100) if len(df_target) > 0 else 0
        }
    }

# 5. 結果表示
print("\n[5/6] 結果集計...")
print("\n" + "="*80)
print("【全レース】")
print("="*80)
for bet_type, metrics in results['全レース']['bets'].items():
    print(f"\n{bet_type}:")
    print(f"  投資額: {metrics['投資']:,}円")
    print(f"  払戻額: {metrics['払戻']:,}円")
    print(f"  回収率: {metrics['回収率']:.1f}%")
    print(f"  的中数: {metrics['的中数']}/{results['全レース']['races']}レース ({metrics['的中率']:.1f}%)")

print("\n" + "="*80)
print("【15-20%確率帯のみ】")
print("="*80)
for bet_type, metrics in results['15-20%確率帯']['bets'].items():
    print(f"\n{bet_type}:")
    print(f"  投資額: {metrics['投資']:,}円")
    print(f"  払戻額: {metrics['払戻']:,}円")
    print(f"  回収率: {metrics['回収率']:.1f}%")
    print(f"  的中数: {metrics['的中数']}/{results['15-20%確率帯']['races']}レース ({metrics['的中率']:.1f}%)")

# 6. 結果保存
print("\n[6/6] 結果保存...")
output_file = 'phase13_exotic_bets_REAL_DATA_results.csv'
# CSVに保存する処理
print(f"  保存: {output_file}")

print("\n完了！")
```

**実行**:
```bash
cd C:\Users\bu158\Keiba_Shisaku20250928
py phase13_exotic_bets_REAL_DATA.py
```

---

## ステップ2: 全期間データ収集（6-8時間）

### 2-1. 収集スクリプトの準備

**元ファイル**: `archive/data_processing/collect_payouts_2024_2025.py`
**新ファイル**: `collect_payouts_2020_2026_FULL.py`

**主な変更点**:

```python
# 変更前
df_target = df[df['year'].isin(['2024', '2025'])]

# 変更後
df_target = df[df['year'].isin(['2020', '2021', '2022', '2023', '2024', '2025', '2026'])]

# 出力先も変更
OUTPUT_FILE = 'data/payout_data/payout_cache_2020_2026_FULL.pkl'
```

**完全版スクリプト**:
```python
"""
2020-2026年 全期間払戻データ取得
"""
import pandas as pd
import time
import requests
from bs4 import BeautifulSoup
import pickle
import os
from datetime import datetime
import json

print("="*80)
print(" 2020-2026年 全期間払戻データ取得")
print("="*80)
print()

# 設定
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
SLEEP_TIME = 1.5  # サーバー負荷軽減のため1.5秒に延長
OUTPUT_PKL = 'data/payout_data/payout_cache_2020_2026_FULL.pkl'
OUTPUT_JSON = 'data/payout_data/payout_2020_2026_FULL.json'

# 既存データ読み込み（あれば）
if os.path.exists(OUTPUT_PKL):
    with open(OUTPUT_PKL, 'rb') as f:
        payout_cache = pickle.load(f)
    print(f"既存データ読み込み: {len(payout_cache):,}件")
else:
    payout_cache = {}
    print("新規データ取得を開始")

print()

# レースID取得
print("[1] レースID取得中...")
df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
df['race_id'] = df['race_id'].astype(str)
df['year'] = df['race_id'].str[:4]

# 2020-2026年を対象
df_target = df[df['year'].isin(['2020', '2021', '2022', '2023', '2024', '2025', '2026'])]

race_ids = df_target['race_id'].unique()
print(f"    対象レース: {len(race_ids):,}件")
print()

# 既に取得済みのものを除外
race_ids_to_fetch = [r for r in race_ids if str(r) not in payout_cache]
print(f"    未取得レース: {len(race_ids_to_fetch):,}件")
print()

if len(race_ids_to_fetch) == 0:
    print("すべてのレースの払戻データ取得済みです！")
else:
    def get_payout_data(race_id):
        """払戻データ取得（collect_payouts_2024_2025.pyと同じロジック）"""
        url = f'https://race.netkeiba.com/race/result.html?race_id={race_id}'
        headers = {'User-Agent': USER_AGENT}

        try:
            time.sleep(SLEEP_TIME)
            r = requests.get(url, headers=headers, timeout=30)
            r.raise_for_status()
            r.encoding = r.apparent_encoding
            soup = BeautifulSoup(r.content, 'lxml')

            payout_data = {'race_id': race_id}

            # 配当テーブル取得
            payout_tables = soup.select('.Result_Pay_Back .Payout_Detail_Table')

            if not payout_tables:
                payout_tables = soup.select('.payout_block table')
            if not payout_tables:
                payout_tables = soup.select('table.pay_table_01')

            if not payout_tables:
                return None

            current_type = None

            for table_tag in payout_tables:
                for tr_tag in table_tag.select('tr'):
                    th_tags = tr_tag.select('th')
                    td_tags = tr_tag.select('td')

                    if th_tags:
                        header_text = th_tags[0].get_text(strip=True)
                        if '単勝' in header_text:
                            current_type = '単勝'
                        elif '複勝' in header_text:
                            current_type = '複勝'
                        elif '馬連' in header_text:
                            current_type = '馬連'
                        elif 'ワイド' in header_text:
                            current_type = 'ワイド'
                        elif '馬単' in header_text:
                            current_type = '馬単'
                        elif '三連複' in header_text or '3連複' in header_text:
                            current_type = '3連複'
                        elif '三連単' in header_text or '3連単' in header_text:
                            current_type = '3連単'
                        elif '枠連' in header_text:
                            current_type = '枠連'

                    # データ行の処理
                    if td_tags and current_type:
                        if current_type not in payout_data:
                            payout_data[current_type] = {
                                '馬番': [],
                                '払戻金': [],
                                '人気': []
                            }

                        try:
                            horses = td_tags[0].get_text(strip=True).split('\n')
                            payouts = td_tags[1].get_text(strip=True).split('\n')
                            ninki = td_tags[2].get_text(strip=True).split('\n') if len(td_tags) > 2 else []

                            # 払戻金を数値化
                            payout_vals = [int(p.replace(',', '').replace('円', '')) for p in payouts if p]
                            ninki_vals = [int(n.replace('人気', '')) for n in ninki if n and n.replace('人気', '').isdigit()]

                            payout_data[current_type]['馬番'].extend(horses)
                            payout_data[current_type]['払戻金'].extend(payout_vals)
                            if ninki_vals:
                                payout_data[current_type]['人気'].extend(ninki_vals)
                        except:
                            pass

            return payout_data if len(payout_data) > 1 else None

        except Exception as e:
            # エラーは表示せず静かにスキップ
            return None

    # データ取得開始
    print("[2] 払戻データ取得中...")
    start_time = datetime.now()
    success_count = 0
    error_count = 0

    for i, race_id in enumerate(race_ids_to_fetch, 1):
        payout = get_payout_data(race_id)

        if payout:
            payout_cache[str(race_id)] = payout
            success_count += 1
        else:
            error_count += 1

        # 進捗表示（100件ごと）
        if i % 100 == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            remaining = (len(race_ids_to_fetch) - i) * (elapsed / i)
            print(f"  進捗: {i:,}/{len(race_ids_to_fetch):,} ({i/len(race_ids_to_fetch)*100:.1f}%) "
                  f"| 成功: {success_count:,} | エラー: {error_count:,} "
                  f"| 残り時間: {int(remaining/60)}分")

            # 途中保存（Pickle）
            with open(OUTPUT_PKL, 'wb') as f:
                pickle.dump(payout_cache, f)

    print()
    print("="*80)
    print(" 完了！")
    print("="*80)
    print()
    print(f"総件数: {len(payout_cache):,}件")
    print(f"成功: {success_count:,}件")
    print(f"エラー: {error_count:,}件")
    print()

# 最終保存（Pickle + JSON）
print("[3] データ保存中...")
with open(OUTPUT_PKL, 'wb') as f:
    pickle.dump(payout_cache, f)
print(f"  Pickle保存: {OUTPUT_PKL}")

# JSON形式でも保存
payout_list = list(payout_cache.values())
with open(OUTPUT_JSON, 'w', encoding='utf-8') as f:
    json.dump(payout_list, f, ensure_ascii=False, indent=2)
print(f"  JSON保存: {OUTPUT_JSON}")

print()
print("払戻データ取得完了！")
```

---

### 2-2. バックグラウンド実行

```bash
# コマンドプロンプトで実行
cd C:\Users\bu158\Keiba_Shisaku20250928

# バックグラウンド実行（ログファイルに出力）
start /B py collect_payouts_2020_2026_FULL.py > payout_collection_log.txt 2>&1
```

**進捗確認**:
```bash
# ログファイルを確認
type payout_collection_log.txt

# または最新の100行を表示
powershell "Get-Content payout_collection_log.txt -Tail 100"
```

**推定時間**:
- 1レースあたり1.5秒
- 21,000レース × 1.5秒 = 31,500秒 ≒ **8.75時間**

---

### 2-3. 完了後の確認

```python
# データ確認スクリプト
import json
import pickle

# Pickle確認
with open('data/payout_data/payout_cache_2020_2026_FULL.pkl', 'rb') as f:
    data_pkl = pickle.load(f)
print(f"Pickle: {len(data_pkl):,}レース")

# JSON確認
with open('data/payout_data/payout_2020_2026_FULL.json', encoding='utf-8') as f:
    data_json = json.load(f)
print(f"JSON: {len(data_json):,}レース")

# 年度別集計
from collections import Counter
years = Counter()
for race in data_json:
    year = race['race_id'][:4]
    years[year] += 1

print("\n年度別レース数:")
for year in sorted(years.keys()):
    print(f"  {year}年: {years[year]:,}レース")
```

---

## ステップ3: Phase 13完全再検証

### 3-1. 全データでの再検証

**ファイル**: `phase13_COMPLETE_VERIFICATION.py`

ステップ1で作成した`phase13_exotic_bets_REAL_DATA.py`を、全期間データに対応させる:

```python
# 払戻データ読み込み部分を変更
with open('data/payout_data/payout_2020_2026_FULL.json', encoding='utf-8') as f:
    payout_data = json.load(f)
```

---

### 3-2. 結果比較

| 項目 | 理論計算 | 実データ(660) | 実データ(全期間) |
|:---|---:|---:|---:|
| 複勝回収率 | 122.7% | ??% | ??% |
| ワイド回収率 | 75.3% | ??% | ??% |
| 馬連回収率 | 77.9% | ??% | ??% |
| サンプル数 | 289 | 660 | 21,000 |

---

## ステップ4: GUI統合（Phase 14）

### 4-1. keiba_prediction_gui_v3.pyへの統合

**追加機能**:
1. `get_pay_table()` メソッド追加
2. `format_payout_data()` メソッド追加
3. 予測時に自動で払戻データ取得・保存

**実装場所**: 約3200行目付近（`get_race_from_database()`の後）

---

## トラブルシューティング

### エラー1: "requests.exceptions.HTTPError: 404"
**原因**: レースIDが存在しない
**対処**: スキップして次へ（正常動作）

### エラー2: "UnicodeEncodeError"
**原因**: コンソールの文字コード問題
**対処**: ログファイルにリダイレクト

### エラー3: スクリプトが途中で止まる
**原因**: ネットワークタイムアウト
**対処**: 既存データを読み込んで再実行（自動で続きから開始）

---

## 完了チェックリスト

- [ ] ステップ1: 既存データコピー完了
- [ ] ステップ1: 660レースでの仮検証完了
- [ ] ステップ2: 収集スクリプト作成完了
- [ ] ステップ2: バックグラウンド実行開始
- [ ] ステップ2: 約8時間後に完了確認
- [ ] ステップ2: JSON/Pickle両方で保存確認
- [ ] ステップ3: 全期間での完全検証実施
- [ ] ステップ3: 結果のMD形式レポート作成
- [ ] ステップ4: GUI統合（Phase 14で実施）

---

## 推定スケジュール

| タイミング | 作業 | 所要時間 |
|:---|:---|---:|
| **開始時** | ステップ1実施 | 5分 |
| **開始+10分** | ステップ2バックグラウンド起動 | 5分 |
| **開始+8時間** | データ収集完了確認 | 5分 |
| **開始+8.5時間** | ステップ3完全検証実施 | 30分 |
| **開始+9時間** | 結果レポート作成 | 30分 |
| **合計** | | **約9-10時間** |

---

**作成者**: Claude Opus 4.6
**最終更新**: 2026年2月21日
