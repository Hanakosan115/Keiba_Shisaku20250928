"""
既存データにクラス情報を追加

実行内容:
1. netkeiba_data_2020_2024_clean.csv を読み込み
2. 各レースのrace_nameからクラスを判定
3. race_class, race_class_rank 列を追加
4. 各馬の前走クラスと比較して昇級/降級フラグを追加
5. 新しいCSVとして保存
"""

import pandas as pd
import numpy as np
from class_detector import RaceClassDetector
from data_config import MAIN_CSV
from tqdm import tqdm

def add_class_info_to_data():
    """
    既存データにクラス情報を追加
    """
    print("="*80)
    print("既存データへのクラス情報追加")
    print("="*80)

    # データ読み込み
    print("\nデータ読み込み中...")
    df = pd.read_csv(MAIN_CSV, encoding='utf-8', low_memory=False)
    print(f"  総レコード数: {len(df):,}件")
    print(f"  総レース数: {df['race_id'].nunique():,}レース")

    # クラス判定器
    detector = RaceClassDetector()

    # レース情報を取得（race_idごとに1回だけ処理）
    print("\nレース情報からクラスを判定中...")
    race_classes = {}

    unique_races = df[['race_id', 'race_name']].drop_duplicates()

    for _, row in tqdm(unique_races.iterrows(), total=len(unique_races)):
        race_id = row['race_id']
        race_name = row['race_name']

        if pd.isna(race_name):
            race_name = ''

        # クラス判定
        result = detector.detect_class(str(race_name))

        race_classes[race_id] = {
            'race_class': result['class'],
            'race_class_rank': result['class_rank'],
            'race_is_special': result['is_special'],
            'race_class_confidence': result['confidence']
        }

    # データフレームに追加
    print("\nクラス情報をデータに追加中...")
    df['race_class'] = df['race_id'].map(lambda x: race_classes.get(x, {}).get('race_class', '不明'))
    df['race_class_rank'] = df['race_id'].map(lambda x: race_classes.get(x, {}).get('race_class_rank', -999))
    df['race_is_special'] = df['race_id'].map(lambda x: race_classes.get(x, {}).get('race_is_special', False))
    df['race_class_confidence'] = df['race_id'].map(lambda x: race_classes.get(x, {}).get('race_class_confidence', 0.0))

    # クラス分布を表示
    print("\n【クラス分布】")
    class_counts = df.groupby('race_class')['race_id'].nunique().sort_values(ascending=False)
    for class_name, count in class_counts.items():
        print(f"  {class_name:12s}: {count:5d}レース")

    # 各馬のクラス変動を計算
    print("\nクラス変動を計算中...")
    df['date_parsed'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.sort_values(['horse_id', 'date_parsed'])

    # 前走のクラスを取得
    df['prev_race_class'] = df.groupby('horse_id')['race_class'].shift(1)
    df['prev_race_class_rank'] = df.groupby('horse_id')['race_class_rank'].shift(1)

    # クラス変動フラグ
    df['class_change'] = 'same'  # デフォルト

    # 昇級
    mask_promotion = (
        df['prev_race_class_rank'].notna() &
        (df['race_class_rank'] > df['prev_race_class_rank'])
    )
    df.loc[mask_promotion, 'class_change'] = 'promotion'

    # 降級
    mask_demotion = (
        df['prev_race_class_rank'].notna() &
        (df['race_class_rank'] < df['prev_race_class_rank'])
    )
    df.loc[mask_demotion, 'class_change'] = 'demotion'

    # 初出走
    df.loc[df['prev_race_class'].isna(), 'class_change'] = 'debut'

    # クラス変動統計
    print("\n【クラス変動統計】")
    change_counts = df['class_change'].value_counts()
    for change_type, count in change_counts.items():
        pct = 100 * count / len(df)
        print(f"  {change_type:12s}: {count:7,}件 ({pct:5.1f}%)")

    # 昇級馬の成績を分析
    print("\n【昇級初戦の成績】")
    promotion_horses = df[df['class_change'] == 'promotion'].copy()
    promotion_horses['Rank_num'] = pd.to_numeric(promotion_horses['Rank'], errors='coerce')
    promotion_horses = promotion_horses.dropna(subset=['Rank_num'])

    if len(promotion_horses) > 0:
        avg_rank = promotion_horses['Rank_num'].mean()
        win_rate = (promotion_horses['Rank_num'] == 1).sum() / len(promotion_horses) * 100
        top3_rate = (promotion_horses['Rank_num'] <= 3).sum() / len(promotion_horses) * 100

        print(f"  対象数: {len(promotion_horses):,}レース")
        print(f"  平均着順: {avg_rank:.2f}着")
        print(f"  勝率: {win_rate:.1f}%")
        print(f"  3着内率: {top3_rate:.1f}%")

        # 比較：同クラス
        same_class = df[df['class_change'] == 'same'].copy()
        same_class['Rank_num'] = pd.to_numeric(same_class['Rank'], errors='coerce')
        same_class = same_class.dropna(subset=['Rank_num'])

        if len(same_class) > 0:
            same_avg_rank = same_class['Rank_num'].mean()
            same_win_rate = (same_class['Rank_num'] == 1).sum() / len(same_class) * 100
            same_top3_rate = (same_class['Rank_num'] <= 3).sum() / len(same_class) * 100

            print(f"\n【参考：同クラス連続出走の成績】")
            print(f"  対象数: {len(same_class):,}レース")
            print(f"  平均着順: {same_avg_rank:.2f}着")
            print(f"  勝率: {same_win_rate:.1f}%")
            print(f"  3着内率: {same_top3_rate:.1f}%")

            print(f"\n【差分】")
            print(f"  平均着順: {avg_rank - same_avg_rank:+.2f}着")
            print(f"  勝率: {win_rate - same_win_rate:+.1f}%")
            print(f"  3着内率: {top3_rate - same_top3_rate:+.1f}%")

    # 保存
    output_path = MAIN_CSV.replace('.csv', '_with_class.csv')
    print(f"\n保存中: {output_path}")
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print("完了！")

    # サンプル表示
    print("\n【サンプルデータ】")
    sample = df[df['class_change'] == 'promotion'].head(10)
    for _, row in sample.iterrows():
        print(f"\n  馬ID: {row['horse_id']}")
        print(f"    日付: {row['date']}")
        print(f"    {row['prev_race_class']} → {row['race_class']} (昇級)")
        print(f"    レース: {str(row['race_name'])[:40]}...")
        print(f"    着順: {row['Rank']}着")

    return output_path


if __name__ == '__main__':
    output_path = add_class_info_to_data()
    print(f"\n新しいデータファイル: {output_path}")
    print("このファイルを使って再訓練・再評価してください！")
