"""
NetkeibaのURLからレースIDを抽出するツール
"""

import re

def extract_race_id(url_or_text):
    """
    URLまたはテキストからレースIDを抽出

    Args:
        url_or_text: netkeibaのURLまたはレースIDを含むテキスト

    Returns:
        str: レースID（12桁）
    """
    # レースIDパターン（12桁の数字）
    pattern = r'race_id=(\d{12})|/race/(\d{12})\.html|^(\d{12})$'

    match = re.search(pattern, url_or_text)

    if match:
        # いずれかのグループにマッチした値を返す
        race_id = match.group(1) or match.group(2) or match.group(3)
        return race_id

    return None

def decode_race_id(race_id):
    """
    レースIDをデコード

    レースID形式: YYYYPPRRDD##
    - YYYY: 年（2024, 2025など）
    - PP: 競馬場コード（01-10）
    - RR: レース回次（01-08）
    - DD: 日次（01-12）
    - ##: レース番号（01-12）
    """
    if len(race_id) != 12:
        return None

    year = race_id[0:4]
    place_code = race_id[4:6]
    kai = race_id[6:8]
    day = race_id[8:10]
    race_num = race_id[10:12]

    # 競馬場名マッピング
    place_names = {
        '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
        '05': '東京', '06': '中山', '07': '中京', '08': '京都',
        '09': '阪神', '10': '小倉'
    }

    place_name = place_names.get(place_code, f'不明({place_code})')

    return {
        'year': year,
        'place': place_name,
        'place_code': place_code,
        'kai': kai,
        'day': day,
        'race_num': race_num,
        'summary': f"{year}年 {place_name} {int(kai)}回{int(day)}日 第{int(race_num)}R"
    }

def main():
    print("="*80)
    print("Netkeiba レースID 抽出ツール")
    print("="*80)

    while True:
        print("\nURLまたはレースIDを入力してください（終了: q）")
        user_input = input("> ").strip()

        if user_input.lower() == 'q':
            break

        if not user_input:
            continue

        # レースID抽出
        race_id = extract_race_id(user_input)

        if race_id:
            print(f"\n✓ レースID: {race_id}")

            # デコード
            info = decode_race_id(race_id)

            if info:
                print(f"  {info['summary']}")
                print(f"\n  詳細:")
                print(f"    年: {info['year']}")
                print(f"    競馬場: {info['place']}")
                print(f"    開催: {int(info['kai'])}回")
                print(f"    日次: {int(info['day'])}日目")
                print(f"    レース番号: 第{int(info['race_num'])}R")

                # URL生成
                print(f"\n  URL:")
                print(f"    出馬表: https://race.netkeiba.com/race/shutuba.html?race_id={race_id}")
                print(f"    結果: https://race.netkeiba.com/race/result.html?race_id={race_id}")
        else:
            print("✗ レースIDが見つかりませんでした")

    print("\n終了")

if __name__ == "__main__":
    print("使用例:")
    print("  https://race.netkeiba.com/race/shutuba.html?race_id=202505050812")
    print("  202505050812")
    print("  /race/202505050812.html")
    print()

    # テスト
    test_id = "202505050812"
    info = decode_race_id(test_id)
    if info:
        print(f"サンプル ({test_id}): {info['summary']}")

    print()
    main()
