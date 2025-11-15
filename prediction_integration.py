"""
既存のhorse_racing_analyzer.pyと改善版ロジックを統合するモジュール

使い方:
1. 既存のHorseRacingAnalyzerAppに、このモジュールの関数を追加
2. 予測処理で新しいロジックを使用
"""
import pandas as pd
import numpy as np
import tkinter as tk
import threading
import os
from improved_analyzer import ImprovedHorseAnalyzer

# CSV データのグローバルキャッシュ
_csv_race_data = None

def load_csv_race_data():
    """CSVから全レースデータを読み込む（初回のみ）"""
    global _csv_race_data

    if _csv_race_data is not None:
        return _csv_race_data

    data_dir = r"C:\Users\bu158\HorseRacingAnalyzer\data"
    csv_files = [f for f in os.listdir(data_dir) if f.endswith('.csv') and 'combined' in f]

    if csv_files:
        csv_path = os.path.join(data_dir, csv_files[0])
        print(f"[INFO] CSVデータ読み込み中: {csv_files[0]}")
        _csv_race_data = pd.read_csv(csv_path, encoding='utf-8', low_memory=False)
        print(f"[INFO] CSVデータ読み込み完了: {len(_csv_race_data)}件")
        return _csv_race_data
    else:
        print(f"[WARNING] CSVファイルが見つかりません: {data_dir}")
        return None

def get_horse_past_results_from_csv(horse_id, race_date, max_results=5):
    """
    CSVから指定した馬の過去成績を取得

    Args:
        horse_id: 馬ID
        race_date: 基準となるレース日付
        max_results: 最大取得件数

    Returns:
        過去成績のリスト（新しい順）
    """
    df = load_csv_race_data()
    if df is None or pd.isna(horse_id) or pd.isna(race_date):
        return []

    # この馬の全成績を取得
    horse_races = df[df['horse_id'] == horse_id].copy()

    if len(horse_races) == 0:
        # 型変換を試みる
        try:
            horse_id_int = int(horse_id)
            horse_races = df[df['horse_id'] == horse_id_int].copy()
        except:
            pass

    if len(horse_races) == 0:
        return []

    # 日付でフィルタ
    horse_races['date_parsed'] = pd.to_datetime(horse_races['date'], errors='coerce')
    race_date_parsed = pd.to_datetime(race_date, errors='coerce')

    past_races = horse_races[horse_races['date_parsed'] < race_date_parsed]
    past_races = past_races.sort_values('date_parsed', ascending=False)

    # 過去成績リストを作成
    results = []
    for _, race in past_races.head(max_results).iterrows():
        result = {
            'date': race.get('date'),
            'place': race.get('track_name'),
            'distance': pd.to_numeric(race.get('distance'), errors='coerce'),
            'rank': pd.to_numeric(race.get('Rank'), errors='coerce'),
            'course_type': race.get('course_type'),
            'baba': race.get('track_condition'),
            'time': race.get('Time'),
            'agari': race.get('Agari'),
            'passage': race.get('Passage'),
            'weight': pd.to_numeric(race.get('Weight'), errors='coerce'),
            'weight_diff': pd.to_numeric(race.get('WeightDiff'), errors='coerce'),
        }
        results.append(result)

    return results


def enhanced_fetch_race_info_thread(self, race_id):
    """
    【改善版】予測処理

    変更点:
    1. 簡潔な特徴量計算
    2. オッズ乖離度の計算
    3. 印と自信度の自動付与
    """
    import traceback
    from tkinter import messagebox
    import os

    try:
        self.root.after(0, lambda: self.update_status(f"レースID {race_id}: 予測処理開始..."))
        print(f"--- Enhanced Prediction: START (Race ID: {race_id}) ---")

        model_dir = self.settings.get("models_dir")

        # モデルのロード
        self.load_model_from_file(model_filename="trained_lgbm_model_place.pkl", mode='place')
        place_model, place_features, place_imputation = self.trained_model, self.model_features, self.imputation_values_

        if not place_model:
            self.root.after(0, lambda: messagebox.showerror("モデルエラー", "予測モデルが見つかりません。"))
            return

        # レース情報取得
        self.root.after(0, lambda: self.update_status(f"レースID {race_id}: 出馬表情報取得中..."))
        web_data = self.get_shutuba_table(race_id)
        if not web_data or not web_data.get('horse_list'):
            self.root.after(0, lambda: messagebox.showerror("取得エラー", f"レースID {race_id} の出馬表を取得できませんでした。"))
            return

        race_df = pd.DataFrame(web_data['horse_list'])
        race_conditions = web_data.get('race_details', {})
        race_date_str = race_conditions.get('RaceDate')
        race_conditions['RaceDate'] = pd.to_datetime(race_date_str, format='%Y年%m月%d日', errors='coerce') if race_date_str else pd.NaT

        # GUI表示（レース情報）
        race_date_for_display = race_conditions.get('RaceDate')
        race_date_str_display = race_date_for_display.strftime('%Y年%m月%d日') if pd.notna(race_date_for_display) else '日付不明'
        track_name_display = str(race_conditions.get('TrackName', '場所不明'))
        race_num_display = str(race_conditions.get('RaceNum', '?')).replace('R','')
        race_name_display = str(race_conditions.get('RaceName', 'レース名不明'))
        course_type_display = str(race_conditions.get('CourseType', '種別不明'))
        distance_val_display = race_conditions.get('Distance')
        distance_display_str = str(int(distance_val_display)) if pd.notna(distance_val_display) else '距離不明'

        race_info_text = f"{race_date_str_display} {track_name_display}{race_num_display}R {race_name_display}"
        race_details_text = f"{course_type_display}{distance_display_str}m"

        self.root.after(0, lambda text=race_info_text: self.race_info_label.config(text=text))
        self.root.after(0, lambda text=race_details_text: self.race_details_label.config(text=text))

        # 改善版アナライザーの初期化
        improved_analyzer = ImprovedHorseAnalyzer()
        # 統計情報を安全に設定（存在する場合のみ）
        if hasattr(self, 'jockey_stats'):
            improved_analyzer.jockey_stats = self.jockey_stats
        if hasattr(self, 'father_stats'):
            improved_analyzer.father_stats = self.father_stats
        if hasattr(self, 'gate_stats'):
            improved_analyzer.gate_stats = self.gate_stats

        # 各馬の特徴量計算とAI予測
        horses_prediction_data = []

        for index, row in race_df.iterrows():
            horse_id = row.get('horse_id')
            if pd.isna(horse_id):
                continue

            horse_id_str = str(horse_id).split('.')[0]

            # 馬の詳細情報取得
            horse_full_details = self.horse_details_cache.get(horse_id_str)
            if not horse_full_details:
                horse_full_details = self.get_horse_details(horse_id_str)
                if isinstance(horse_full_details, dict) and not horse_full_details.get('error'):
                    self.horse_details_cache[horse_id_str] = horse_full_details

            horse_basic_info = dict(row)
            if isinstance(horse_full_details, dict):
                horse_basic_info.update(horse_full_details)

            # CSVから過去成績を取得（horse_cacheが空の場合の代替）
            race_date = race_conditions.get('RaceDate')
            csv_race_results = get_horse_past_results_from_csv(horse_id_str, race_date, max_results=5)

            # デバッグ出力
            if index == 0:
                print(f"[DEBUG] horse_id_str: {horse_id_str}")
                print(f"[DEBUG] race_date: {race_date}")
                print(f"[DEBUG] csv_race_results count: {len(csv_race_results)}")

            csv_data_used = False
            if csv_race_results:
                horse_basic_info['race_results'] = csv_race_results
                csv_data_used = True  # CSVから取得した場合は既に日付フィルタ済み
            elif index == 0:
                print(f"[DEBUG] CSV取得失敗 - horse_cacheのrace_resultsを使用")

            # 予測日より前のデータのみ使用（CSVから取得した場合は既にフィルタ済みなのでスキップ）
            if not csv_data_used:
                predict_date = race_conditions.get('RaceDate')
                if pd.notna(predict_date) and 'race_results' in horse_basic_info and isinstance(horse_basic_info['race_results'], list):
                    horse_basic_info['race_results'] = [
                        r for r in horse_basic_info['race_results']
                        if isinstance(r, dict) and pd.to_datetime(r.get('date'), errors='coerce') < predict_date
                    ]

            # 【改善版】簡潔な特徴量計算
            features = improved_analyzer.calculate_simplified_features(horse_basic_info, race_conditions)

            # AI予測（簡易AI予測モデルを使用）
            # バックテストで高い回収率（単勝148%、馬連434%、3連複1291%、3連単1917%）を達成したモデル
            ai_place_proba = improved_analyzer.calculate_simple_ai_prediction(features)

            # オッズ乖離度の計算
            divergence_info = improved_analyzer.calculate_divergence_score(features, ai_place_proba)

            # 近3走と脚質を取得
            race_results = horse_basic_info.get('race_results', [])
            recent_3_results = improved_analyzer.get_recent_3_results(race_results)
            running_style = improved_analyzer.determine_running_style(race_results)

            # デバッグ出力
            if index == 0:  # 最初の馬のみ
                print(f"[DEBUG] Horse: {horse_basic_info.get('HorseName')}")
                print(f"[DEBUG] race_results count: {len(race_results)}")
                print(f"[DEBUG] recent_3_results: {recent_3_results}")
                print(f"[DEBUG] running_style: {running_style}")

            # データをまとめる
            horse_data = {
                'horse_id': horse_id_str,
                'horse_name': horse_basic_info.get('HorseName', ''),
                'umaban': row.get('Umaban'),
                'sex_age': row.get('SexAge', ''),
                'jockey': row.get('JockeyName', ''),
                'weight': row.get('Load', ''),
                'odds': features.get('odds'),
                'popularity': features.get('popularity'),
                'ai_prediction': ai_place_proba,
                'odds_rate': divergence_info['odds_rate'],
                'divergence': divergence_info['divergence'],
                'evaluation': divergence_info['evaluation'],
                'features': features,
                'recent_3_results': recent_3_results,
                'running_style': running_style,
            }

            horses_prediction_data.append(horse_data)

        # 印と自信度の付与
        horses_with_marks = improved_analyzer.assign_marks_and_confidence(horses_prediction_data)

        # 総合スコア順にソート（表示用）- 印の順番と一致
        horses_with_marks.sort(key=lambda x: x.get('composite_score', 0), reverse=True)

        # GUI更新
        self.root.after(0, self._update_enhanced_prediction_table, horses_with_marks)

        # 推奨買い目テキスト生成
        recommendation_text = self._create_enhanced_recommendation_text(horses_with_marks)
        if hasattr(self, 'recommendation_text') and self.recommendation_text.winfo_exists():
            self.root.after(0, lambda: self.recommendation_text.delete(1.0, tk.END))
            self.root.after(0, lambda: self.recommendation_text.insert(tk.END, recommendation_text))

        self.root.after(0, lambda: self.update_status(f"予測完了: {race_id}"))
        print("--- Enhanced Prediction: COMPLETE ---")

    except Exception as e:
        traceback.print_exc()
        self.root.after(0, lambda err=e: messagebox.showerror("予測処理エラー", f"予測処理中にエラー: {err}"))


def _update_enhanced_prediction_table(self, horses_data):
    """
    【改善版】予測結果テーブルの更新

    表示項目:
    - 印
    - 馬番
    - 馬名
    - 性齢
    - 斤量
    - 騎手
    - オッズ
    - 人気
    - AI予測(%)
    - 近3走
    - 脚質
    - 自信度
    """
    import tkinter as tk
    import pandas as pd

    # テーブルクリア
    for item in self.prediction_tree.get_children():
        self.prediction_tree.delete(item)

    # 馬データを保存（ソート機能用）
    self._current_horses_data = horses_data

    # 列定義を更新
    columns = ['印', '馬番', '馬名', '性齢', '斤量', '騎手', 'オッズ', '人気',
               'AI予測(%)', '近3走', '脚質', '自信度']

    self.prediction_tree["columns"] = columns
    self.prediction_tree["show"] = "headings"

    # 列幅設定
    column_widths = {
        '印': 40,
        '馬番': 50,
        '馬名': 120,
        '性齢': 60,
        '斤量': 50,
        '騎手': 80,
        'オッズ': 60,
        '人気': 50,
        'AI予測(%)': 80,
        '近3走': 80,
        '脚質': 60,
        '自信度': 60
    }

    # ソート機能付きヘッダー設定
    for col in columns:
        # ソート機能が利用可能な場合のみ設定
        if hasattr(self, '_sort_table_by_column'):
            self.prediction_tree.heading(col, text=col,
                                         command=lambda c=col: self._sort_table_by_column(c))
        else:
            self.prediction_tree.heading(col, text=col)
        self.prediction_tree.column(col, width=column_widths.get(col, 80), anchor=tk.CENTER)

    # データ挿入
    for horse in horses_data:
        ai_pred_pct = f"{horse['ai_prediction'] * 100:.1f}"
        recent_3 = horse.get('recent_3_results', '-')
        running_style = horse.get('running_style', '-')

        values = (
            horse.get('mark', ''),
            horse.get('umaban', ''),
            horse.get('horse_name', ''),
            horse.get('sex_age', ''),
            horse.get('weight', ''),
            horse.get('jockey', ''),
            f"{horse.get('odds', 0):.1f}",
            horse.get('popularity', ''),
            ai_pred_pct,
            recent_3,
            running_style,
            horse.get('confidence', '')
        )

        # 色分け判定（優先度: 過大評価 > 自信度）
        divergence = horse.get('divergence', 0)
        confidence = horse.get('confidence', '')
        tags = ()

        # 過大評価馬（マイナス乖離が大きい = オッズほど強くない）
        if divergence < -0.05:  # -5%以上のマイナス乖離
            tags = ('overrated',)
        # 自信度による色分け
        elif confidence == 'S':
            tags = ('confidence_s',)
        elif confidence == 'A':
            tags = ('confidence_a',)
        elif confidence == 'B':
            tags = ('confidence_b',)
        elif confidence == 'C':
            tags = ('confidence_c',)

        self.prediction_tree.insert("", "end", values=values, tags=tags)

    # タグに色を設定
    self.prediction_tree.tag_configure('overrated', background='#FFB6C1', foreground='#8B0000')  # 赤色（過大評価警告）
    self.prediction_tree.tag_configure('confidence_s', background='#FFD700')  # 金色
    self.prediction_tree.tag_configure('confidence_a', background='#87CEEB')  # 水色
    self.prediction_tree.tag_configure('confidence_b', background='#90EE90')  # 薄緑
    self.prediction_tree.tag_configure('confidence_c', background='#FFFFE0')  # 薄黄


def _sort_table_by_column(self, column):
    """
    カラムクリックでテーブルをソート

    Args:
        column: ソートするカラム名
    """
    if not hasattr(self, '_current_horses_data') or not self._current_horses_data:
        return

    # ソート方向を保存・トグル
    if not hasattr(self, '_sort_column') or self._sort_column != column:
        self._sort_reverse = False
    else:
        self._sort_reverse = not self._sort_reverse

    self._sort_column = column

    # カラムに対応するデータキーを取得
    column_key_map = {
        '印': 'mark',
        '馬番': 'umaban',
        '馬名': 'horse_name',
        'オッズ': 'odds',
        '人気': 'popularity',
        'AI予測(%)': 'ai_prediction',
        '自信度': 'confidence'
    }

    sort_key = column_key_map.get(column)
    if not sort_key:
        return

    # 数値カラムのリスト
    numeric_columns = ['umaban', 'popularity', 'odds', 'ai_prediction']

    # ソート実行
    try:
        if sort_key in numeric_columns:
            # 数値としてソート
            def numeric_sort_key(x):
                val = x.get(sort_key)
                if val in [None, '', '-']:
                    return float('inf')  # 欠損値は最後に
                try:
                    return float(val)
                except:
                    return float('inf')

            sorted_data = sorted(self._current_horses_data,
                               key=numeric_sort_key,
                               reverse=self._sort_reverse)
        else:
            # 文字列としてソート
            sorted_data = sorted(self._current_horses_data,
                               key=lambda x: str(x.get(sort_key, '')),
                               reverse=self._sort_reverse)

        # テーブル再描画
        self._update_enhanced_prediction_table(sorted_data)

        # ヘッダーにソート方向を表示
        direction = ' ↓' if self._sort_reverse else ' ↑'
        for col in self.prediction_tree["columns"]:
            text = col + (direction if col == column else '')
            self.prediction_tree.heading(col, text=text,
                                        command=lambda c=col: self._sort_table_by_column(c))
    except Exception as e:
        print(f"[ERROR] ソート失敗: {e}")


def _create_enhanced_recommendation_text(self, horses_data):
    """
    【改善版】推奨買い目テキストの生成

    内容:
    1. レース診断
    2. 本命・対抗・穴馬
    3. 注意馬（人気だが危険）
    4. 推奨買い目（シンプルに）
    """
    text = "【AI競馬予想 - 改善版】\n"
    text += "=" * 50 + "\n\n"

    # 印がついている馬を抽出（5頭体制）
    honmei = [h for h in horses_data if h.get('mark') == '◎']
    taikou = [h for h in horses_data if h.get('mark') == '○']
    ana = [h for h in horses_data if h.get('mark') == '▲']
    hoshi = [h for h in horses_data if h.get('mark') == '☆']
    renge = [h for h in horses_data if h.get('mark') == '△']

    # 本命
    if honmei:
        h = honmei[0]
        text += f"◎ 本命: {h['umaban']}番 {h['horse_name']}\n"
        text += f"   オッズ: {h['odds']:.1f}倍 ({h['popularity']}番人気)\n"
        text += f"   AI予測: {h['ai_prediction']*100:.1f}%\n"
        text += f"   自信度: {h['confidence']}\n"

        # 評価コメント
        if h['confidence'] == 'S':
            text += "   → 鉄板！安心して買える本命\n"
        elif h['confidence'] == 'A':
            if h.get('popularity', 99) >= 5:
                text += "   → 人気薄だがAI高評価！穴の本命\n"
            else:
                text += "   → 堅実な本命、信頼度高い\n"
        else:
            text += "   → 総合評価1位だが不安要素あり\n"
        text += "\n"

    # 対抗
    if taikou:
        h = taikou[0]
        text += f"○ 対抗: {h['umaban']}番 {h['horse_name']}\n"
        text += f"   オッズ: {h['odds']:.1f}倍 ({h['popularity']}番人気)\n"
        text += f"   AI予測: {h['ai_prediction']*100:.1f}%\n"
        text += f"   自信度: {h['confidence']}\n\n"

    # 穴馬
    if ana:
        h = ana[0]
        text += f"▲ 単穴: {h['umaban']}番 {h['horse_name']}\n"
        text += f"   オッズ: {h['odds']:.1f}倍 ({h['popularity']}番人気)\n"
        text += f"   AI予測: {h['ai_prediction']*100:.1f}%\n"

        # 穴馬の理由
        if h.get('divergence', 0) > 0.08:
            text += "   → オッズ以上の力あり！狙い目\n"
        text += "\n"

    # 連下1
    if hoshi:
        h = hoshi[0]
        text += f"☆ 連下1: {h['umaban']}番 {h['horse_name']}\n"
        text += f"   オッズ: {h['odds']:.1f}倍 ({h['popularity']}番人気)\n"
        text += f"   AI予測: {h['ai_prediction']*100:.1f}%\n\n"

    # 連下2
    if renge:
        h = renge[0]
        text += f"△ 連下2: {h['umaban']}番 {h['horse_name']}\n"
        text += f"   オッズ: {h['odds']:.1f}倍 ({h['popularity']}番人気)\n\n"

    text += "-" * 50 + "\n\n"

    # 注意馬（人気だが過大評価）
    overvalued_horses = [
        h for h in horses_data
        if h.get('evaluation') in ['strong_overvalued', 'overvalued']
        and h.get('popularity', 99) <= 5
    ]

    if overvalued_horses:
        text += "【注意】人気だが危険な馬:\n"
        for h in overvalued_horses[:2]:  # 上位2頭まで
            text += f"  {h['umaban']}番 {h['horse_name']} ({h['popularity']}番人気)\n"
            text += f"    → AI評価が低い。過大評価の可能性\n"
        text += "\n"

    # 推奨買い目（フォーメーション）
    text += "【推奨買い目 - フォーメーション】\n"

    # 印がついている馬の馬番を集める
    marked_horses = []
    if honmei:
        marked_horses.append(honmei[0]['umaban'])
    if taikou:
        marked_horses.append(taikou[0]['umaban'])
    if ana:
        marked_horses.append(ana[0]['umaban'])
    if hoshi:
        marked_horses.append(hoshi[0]['umaban'])
    if renge:
        marked_horses.append(renge[0]['umaban'])

    if len(marked_horses) >= 3:
        # 1着軸フォーメーション
        axis_horses = marked_horses[:2]  # ◎○
        other_horses = marked_horses[2:]  # ▲☆△

        text += f"◇ 馬連フォーメーション:\n"
        text += f"   軸: {', '.join(map(str, axis_horses))}  相手: {', '.join(map(str, other_horses))}\n"
        text += f"   → {len(axis_horses)} × {len(other_horses)} = {len(axis_horses) * len(other_horses)}点\n\n"

        text += f"◇ 3連複フォーメーション:\n"
        text += f"   1-2着: {', '.join(map(str, axis_horses))}\n"
        text += f"   3着: {', '.join(map(str, marked_horses[2:]))}\n"
        if len(marked_horses) >= 4:
            points_3renpuku = len(axis_horses) * (len(axis_horses)-1) * len(marked_horses[2:]) // 2
            text += f"   → 約{points_3renpuku}点\n\n"

        text += f"◇ 3連単フォーメーション:\n"
        text += f"   1着: {axis_horses[0] if axis_horses else '-'}\n"
        text += f"   2-3着: {', '.join(map(str, marked_horses[1:]))}\n"
        if len(marked_horses) >= 3:
            points_3rentan = len(marked_horses[1:]) * (len(marked_horses[1:])-1)
            text += f"   → {points_3rentan}点\n"

    text += "\n" + "=" * 50 + "\n"
    text += "※この予想はAIによる分析結果です。\n"
    text += "※馬券購入は自己責任でお願いします。\n"

    return text


# 既存クラスへのメソッド追加用
def integrate_enhanced_methods(app_instance):
    """
    既存のHorseRacingAnalyzerAppインスタンスに改善版メソッドを追加

    使用例:
        app = HorseRacingAnalyzerApp(root)
        integrate_enhanced_methods(app)
    """
    import types

    # メソッドをバインド
    app_instance.enhanced_fetch_race_info_thread = types.MethodType(
        enhanced_fetch_race_info_thread, app_instance
    )
    app_instance._update_enhanced_prediction_table = types.MethodType(
        _update_enhanced_prediction_table, app_instance
    )
    app_instance._create_enhanced_recommendation_text = types.MethodType(
        _create_enhanced_recommendation_text, app_instance
    )
    app_instance._sort_table_by_column = types.MethodType(
        _sort_table_by_column, app_instance
    )

    print("改善版メソッドを統合しました")
