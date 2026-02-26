"""HTMLファイルからラップタイム情報を探す"""

import re

def find_lap_times_in_html(html_file):
    """HTMLファイル内のラップタイム関連情報を探す"""

    with open(html_file, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    print("=" * 80)
    print("ラップタイム情報の検索")
    print("=" * 80)

    # パターン1: "ラップ"という文字列
    if 'ラップ' in content:
        indices = [m.start() for m in re.finditer('ラップ', content)]
        print(f"\n'ラップ'が見つかりました: {len(indices)}箇所")
        for i, idx in enumerate(indices[:5]):  # 最初の5箇所
            context = content[max(0, idx-100):min(len(content), idx+200)]
            print(f"\n箇所 {i+1}:")
            print(context)
            print("-" * 80)
    else:
        print("\n'ラップ'は見つかりませんでした")

    # パターン2: JavaScript内のデータ
    js_data_patterns = [
        r'var\s+\w+\s*=\s*\[[\d\s,\.]+\]',  # var data = [12.1, 11.8, ...]
        r'data:\s*\[[\d\s,\.]+\]',          # data: [12.1, 11.8, ...]
        r'"lap":\s*\[[\d\s,\.]+\]',        # "lap": [12.1, 11.8, ...]
    ]

    print("\n" + "=" * 80)
    print("JavaScriptデータの検索")
    print("=" * 80)

    for pattern in js_data_patterns:
        matches = re.findall(pattern, content)
        if matches:
            print(f"\nパターン: {pattern}")
            for match in matches[:3]:  # 最初の3件
                print(f"  {match[:100]}")

    # パターン3: 数値の配列を探す（12.0前後の数値）
    print("\n" + "=" * 80)
    print("数値配列の検索（ラップタイムらしき数値）")
    print("=" * 80)

    # 10.0～20.0の範囲の数値が3つ以上連続するパターン
    num_array_pattern = r'(1[0-9]\.\d[\s,\-]+){3,}'
    matches = re.findall(num_array_pattern, content)
    if matches:
        print(f"\n見つかった数値配列: {len(matches)}個")
        for i, match in enumerate(matches[:5]):
            print(f"  {i+1}: {match[:100]}")

    # パターン4: d3やSVG関連のデータ
    print("\n" + "=" * 80)
    print("D3/SVG関連データ")
    print("=" * 80)

    if 'd3.rap_line' in content or 'drawsvg' in content:
        print("\nD3グラフ描画のライブラリが使用されています")
        # ラップタイムデータがJavaScript変数に格納されている可能性

        # JavaScriptのデータ変数を探す
        var_matches = re.findall(r'var\s+(\w+)\s*=\s*\{[^\}]*\}', content)
        if var_matches:
            print(f"\nJavaScript変数: {len(var_matches)}個見つかりました")
            print(f"変数名: {var_matches[:10]}")

    # パターン5: APIエンドポイントを探す
    print("\n" + "=" * 80)
    print("APIエンドポイント")
    print("=" * 80)

    api_patterns = [
        r'(https?://[^\s"\'>]+lap[^\s"\'>]*)',
        r'(https?://[^\s"\'>]+race[^\s"\'>]*)',
        r'(/api/[^\s"\'>]+)',
    ]

    for pattern in api_patterns:
        matches = re.findall(pattern, content)
        if matches:
            print(f"\nパターン: {pattern}")
            for match in set(matches):  # 重複を除去
                print(f"  {match}")

    # パターン6: テーブルデータを探す
    print("\n" + "=" * 80)
    print("テーブル内の数値")
    print("=" * 80)

    table_pattern = r'<table[^>]*>(.*?)</table>'
    tables = re.findall(table_pattern, content, re.DOTALL)
    print(f"\nテーブル要素: {len(tables)}個")

    for i, table in enumerate(tables[:3]):
        # テーブル内に10-20の範囲の数値があるか
        if re.search(r'1[0-9]\.\d', table):
            print(f"\nテーブル {i+1} にラップタイムらしき数値があります")
            print(table[:500])


if __name__ == '__main__':
    find_lap_times_in_html('debug_race_202411090411.html')
