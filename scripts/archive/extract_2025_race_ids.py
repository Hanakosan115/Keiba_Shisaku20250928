"""
2025年のレースIDを抽出してファイルに保存
馬統計データ収集用
"""

import pandas as pd

def main():
    print("="*60)
    print(" 2025年レースID抽出")
    print("="*60)
    print()

    try:
        # CSVを読み込み
        print("CSVを読み込み中...")
        df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

        # 2025年のレースを抽出
        df_2025 = df[df['race_id'].astype(str).str.startswith('2025')].copy()

        print(f"2025年のレース: {len(df_2025)}件")

        # レースIDを取得
        race_ids = df_2025['race_id'].unique()

        print(f"ユニークなレースID: {len(race_ids)}件")
        print()

        # 出力オプション
        print("出力オプションを選択してください:")
        print()
        print(f"  [1] 全件出力 ({len(race_ids)}件)")
        print("  [2] サンプル出力（最初の100件）")
        print("  [3] サンプル出力（最初の500件）")
        print("  [4] カスタム件数指定")
        print()

        choice = input("選択 [1-4]: ").strip()

        if choice == '1':
            output_ids = race_ids
            filename = 'race_ids_2025_all.txt'
        elif choice == '2':
            output_ids = race_ids[:100]
            filename = 'race_ids_2025_sample_100.txt'
        elif choice == '3':
            output_ids = race_ids[:500]
            filename = 'race_ids_2025_sample_500.txt'
        elif choice == '4':
            count = int(input("件数を入力: ").strip())
            output_ids = race_ids[:count]
            filename = f'race_ids_2025_sample_{count}.txt'
        else:
            print("無効な選択です")
            return

        # ファイルに保存
        with open(filename, 'w', encoding='utf-8') as f:
            for race_id in output_ids:
                f.write(f"{race_id}\n")

        print()
        print(f"ファイルに保存しました: {filename}")
        print(f"件数: {len(output_ids)}件")
        print()
        print("使い方:")
        print(f"  1. py update_from_list.py を実行")
        print(f"  2. オプション [1] を選択（A案: レースIDリスト）")
        print(f"  3. ファイル名に「{filename}」を入力")
        print(f"  4. 馬統計情報収集で「y」を選択")
        print()

        print("推定処理時間:")
        min_time = len(output_ids) * 2.2  # 分
        max_time = len(output_ids) * 4.7  # 分

        if min_time < 60:
            print(f"  最小: 約{min_time:.0f}分")
        else:
            print(f"  最小: 約{min_time/60:.1f}時間")

        if max_time < 60:
            print(f"  最大: 約{max_time:.0f}分")
        else:
            print(f"  最大: 約{max_time/60:.1f}時間")

    except FileNotFoundError:
        print("エラー: netkeiba_data_2020_2024_enhanced.csv が見つかりません")
    except Exception as e:
        print(f"エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
