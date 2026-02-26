"""
スマートデータ更新システム - 3層アプローチ

レベル1: 予測時クイックチェック（警告のみ、高速）
レベル2: レース単位の一括更新（効率的、必要な馬だけ）
レベル3: 定期自動メンテナンス（完全、週次or月次）
"""
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime, timedelta
import time
import os

# Selenium版スクレイピングをインポート
try:
    from scrape_horse_selenium import scrape_horse_races_selenium
    SELENIUM_AVAILABLE = True
    print("[INFO] Selenium版スクレイピング: 利用可能")
except ImportError:
    SELENIUM_AVAILABLE = False
    print("[WARNING] Selenium版スクレイピング: 利用不可（BeautifulSoupを使用）")

# ===============================================================================
# レベル1: クイックチェック（予測時）
# ===============================================================================

def quick_check_horses(horses, df, warn_days=30):
    """
    予測時のクイックチェック - 警告のみ、更新はしない

    Args:
        horses: レースの出走馬リスト
        df: データベース
        warn_days: この日数より古ければ警告

    Returns:
        dict: {
            'warnings': [...],
            'needs_update': [...],
            'ok': [...]
        }
    """
    result = {
        'warnings': [],
        'needs_update': [],
        'ok': []
    }

    current_date = datetime.now()

    for horse in horses:
        horse_id = horse.get('horse_id')
        horse_name = horse.get('馬名')

        if not horse_id:
            continue

        try:
            horse_id_num = float(horse_id)
            horse_data = df[df['horse_id'] == horse_id_num]
        except:
            horse_data = pd.DataFrame()

        if len(horse_data) == 0:
            result['warnings'].append({
                'horse_name': horse_name,
                'horse_id': horse_id,
                'type': 'no_data',
                'message': 'データなし（新馬または未収集）'
            })
            result['needs_update'].append(horse_id)
        else:
            latest = horse_data.sort_values('date', ascending=False).iloc[0]
            latest_date_str = latest.get('date')

            try:
                # ISO形式('2025-01-05')と日本語形式('2025年01月05日')の両方に対応
                try:
                    latest_date = datetime.strptime(latest_date_str, '%Y-%m-%d')
                except ValueError:
                    latest_date = datetime.strptime(latest_date_str, '%Y年%m月%d日')
                days_old = (current_date - latest_date).days

                if days_old > 180:
                    result['warnings'].append({
                        'horse_name': horse_name,
                        'horse_id': horse_id,
                        'type': 'very_old',
                        'message': f'最終出走: {latest_date_str} ({days_old}日前) - データ更新が必要',
                        'days_old': days_old
                    })
                    result['needs_update'].append(horse_id)
                elif days_old > warn_days:
                    result['warnings'].append({
                        'horse_name': horse_name,
                        'horse_id': horse_id,
                        'type': 'old',
                        'message': f'最終出走: {latest_date_str} ({days_old}日前) - 更新推奨',
                        'days_old': days_old
                    })
                    result['needs_update'].append(horse_id)
                else:
                    result['ok'].append({
                        'horse_name': horse_name,
                        'horse_id': horse_id,
                        'latest_date': latest_date_str
                    })
            except:
                result['warnings'].append({
                    'horse_name': horse_name,
                    'horse_id': horse_id,
                    'type': 'error',
                    'message': '日付解析エラー'
                })

    return result


# ===============================================================================
# レベル2: レース単位の一括更新
# ===============================================================================

def scrape_horse_recent_races(horse_id, since_date=None):
    """
    馬の最新レース結果を取得（Selenium版優先）

    Args:
        horse_id: 馬ID
        since_date: この日付以降のレースを取得（datetime）

    Returns:
        list: 新規レースのリスト
    """
    # Selenium版が利用可能な場合は使用
    if SELENIUM_AVAILABLE:
        try:
            # since_dateを文字列形式に変換
            since_date_str = None
            if since_date:
                since_date_str = since_date.strftime('%Y年%m月%d日')

            # Selenium版でスクレイピング
            races = scrape_horse_races_selenium(horse_id, since_date_str)

            # フォーマットを統一
            new_races = []
            for race in races:
                new_races.append({
                    'date': race['date'].replace('/', '年', 1).replace('/', '月', 1) + '日',
                    'horse_id': horse_id,
                    'race_data': race  # 詳細データ
                })

            return new_races
        except Exception as e:
            print(f"  Selenium版エラー (馬ID {horse_id}): {e}")
            print(f"  BeautifulSoup版にフォールバック...")

    # BeautifulSoup版（フォールバック）
    url = f"https://db.netkeiba.com/horse/{horse_id}"

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = response.apparent_encoding

        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', class_='db_h_race_results')

        if not table:
            return []

        rows = table.find_all('tr')[1:]
        new_races = []

        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 14:
                continue

            # 日付
            date_text = cols[0].get_text(strip=True)
            try:
                race_date = datetime.strptime(date_text, '%Y/%m/%d')

                # since_date以降のデータのみ
                if since_date and race_date <= since_date:
                    break  # 古いデータに到達したので終了

            except:
                continue

            # レース情報を抽出（簡易版）
            new_races.append({
                'date': race_date.strftime('%Y年%m月%d日'),
                'horse_id': horse_id,
                'raw_data': [col.get_text(strip=True) for col in cols]
            })

        return new_races

    except Exception as e:
        print(f"  エラー: 馬ID {horse_id}: {e}")
        return []


def batch_update_race_horses(horses, df, csv_path='data/main/netkeiba_data_2020_2025_complete.csv'):
    """
    レース単位での一括更新 - 必要な馬だけ効率的に更新

    Args:
        horses: レースの出走馬リスト
        df: データベース
        csv_path: CSVファイルパス

    Returns:
        dict: 更新結果
    """
    print("\n" + "="*80)
    print(" レベル2: レース単位の一括更新")
    print("="*80)

    # クイックチェックで更新が必要な馬を特定
    check_result = quick_check_horses(horses, df, warn_days=30)

    if len(check_result['needs_update']) == 0:
        print("  全ての馬のデータは最新です！")
        return {'updated': 0, 'failed': 0}

    print(f"\n  更新が必要な馬: {len(check_result['needs_update'])}頭")

    updated_count = 0
    failed_count = 0
    new_rows = []

    for i, horse_id in enumerate(check_result['needs_update'], 1):
        # 馬名を取得
        horse_name = next((h['馬名'] for h in horses if h.get('horse_id') == horse_id), horse_id)

        print(f"\n  [{i}/{len(check_result['needs_update'])}] {horse_name} (ID: {horse_id})")

        # データベースから最終出走日を取得
        try:
            horse_id_num = float(horse_id)
            horse_data = df[df['horse_id'] == horse_id_num]

            if len(horse_data) > 0:
                latest = horse_data.sort_values('date', ascending=False).iloc[0]
                latest_date_str = latest.get('date')
                since_date = datetime.strptime(latest_date_str, '%Y年%m月%d日')
                print(f"    最終DB日付: {latest_date_str}")
            else:
                since_date = None
                print(f"    DB: データなし")
        except:
            since_date = None

        # 新規レースを取得
        new_races = scrape_horse_recent_races(horse_id, since_date)

        if len(new_races) > 0:
            print(f"    → {len(new_races)}件の新規レースを発見")
            new_rows.extend(new_races)
            updated_count += 1
        else:
            print(f"    → 新規レースなし")
            failed_count += 1

        # レート制限（1秒待機）
        time.sleep(1)

    print(f"\n  更新完了: {updated_count}頭成功, {failed_count}頭は新規なし")

    # TODO: new_rowsをCSVに追記する処理（将来実装）
    # 現在は取得のみ、実際の更新は手動で

    return {
        'updated': updated_count,
        'failed': failed_count,
        'new_races': new_rows
    }


# ===============================================================================
# レベル3: 定期自動メンテナンス
# ===============================================================================

def periodic_database_maintenance(csv_path='data/main/netkeiba_data_2020_2025_complete.csv',
                                  max_age_days=30,
                                  max_horses_per_run=50):
    """
    定期的なデータベースメンテナンス

    Args:
        csv_path: CSVファイルパス
        max_age_days: この日数より古いデータを更新対象とする
        max_horses_per_run: 1回の実行で更新する最大馬数

    Returns:
        dict: メンテナンス結果
    """
    print("\n" + "="*80)
    print(" レベル3: 定期データベースメンテナンス")
    print("="*80)
    print(f"\n  対象: {max_age_days}日以上前のデータ")
    print(f"  更新上限: {max_horses_per_run}頭/回")
    print()

    # データベース読み込み
    df = pd.read_csv(csv_path, low_memory=False)

    # 各馬の最終出走日を集計
    horse_latest = df.groupby('horse_id').agg({
        'date': 'max',
        'horse_id': 'count'  # 出走回数
    }).rename(columns={'horse_id': 'race_count'})

    current_date = datetime.now()
    cutoff_date = current_date - timedelta(days=max_age_days)

    # 更新が必要な馬を特定
    needs_update = []

    for horse_id, row in horse_latest.iterrows():
        latest_date_str = row['date']

        try:
            latest_date = datetime.strptime(latest_date_str, '%Y年%m月%d日')

            if latest_date < cutoff_date:
                days_old = (current_date - latest_date).days
                needs_update.append({
                    'horse_id': int(horse_id),
                    'latest_date': latest_date_str,
                    'days_old': days_old,
                    'race_count': int(row['race_count'])
                })
        except:
            continue

    # 古い順にソート
    needs_update.sort(key=lambda x: x['days_old'], reverse=True)

    print(f"  更新対象馬: {len(needs_update)}頭")

    if len(needs_update) == 0:
        print("  データベースは最新です！")
        return {'updated': 0, 'total_candidates': 0}

    # 上限まで更新
    to_update = needs_update[:max_horses_per_run]

    print(f"  今回の更新: {len(to_update)}頭")
    print()

    updated_count = 0

    for i, horse_info in enumerate(to_update, 1):
        horse_id = str(horse_info['horse_id'])

        print(f"  [{i}/{len(to_update)}] 馬ID {horse_id}")
        print(f"    最終: {horse_info['latest_date']} ({horse_info['days_old']}日前)")

        # 最新データを取得
        since_date = datetime.strptime(horse_info['latest_date'], '%Y年%m月%d日')
        new_races = scrape_horse_recent_races(horse_id, since_date)

        if len(new_races) > 0:
            print(f"    → {len(new_races)}件の新規レース")
            updated_count += 1
        else:
            print(f"    → 新規なし")

        # レート制限
        time.sleep(1)

    print(f"\n  完了: {updated_count}/{len(to_update)}頭更新")
    print(f"  残り: {len(needs_update) - len(to_update)}頭")

    return {
        'updated': updated_count,
        'total_candidates': len(needs_update),
        'remaining': len(needs_update) - len(to_update)
    }


# ===============================================================================
# メイン実行
# ===============================================================================

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("使用法:")
        print("  py smart_update_system.py quick     # クイックチェック")
        print("  py smart_update_system.py batch     # レース単位更新")
        print("  py smart_update_system.py periodic  # 定期メンテナンス")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "periodic":
        # 定期メンテナンス
        result = periodic_database_maintenance(
            max_age_days=30,
            max_horses_per_run=50
        )
        print(f"\n結果: {result}")

    else:
        print(f"モード '{mode}' は未実装です")
