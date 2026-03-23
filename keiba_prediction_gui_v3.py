"""
競馬予想GUIツール - Phase 14
未来のレース（スクレイピング）と過去のレース（データベース）の両方に対応
Phase 14: 39特徴量 LightGBM + Rule4複合最良ベット戦略
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import pandas as pd
import numpy as np
import pickle
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, 'scripts'))

# Phase 14特徴量計算モジュール (phase13_feature_engineering.py)
import lightgbm as lgb
try:
    from phase13_feature_engineering import (
        calculate_sire_stats,
        calculate_trainer_jockey_stats,
        calculate_horse_features_safe
    )
    BACKTEST_AVAILABLE = True
except ImportError:
    print("Warning: phase13_feature_engineering not found. Prediction may not work.")
    BACKTEST_AVAILABLE = False

# Phase 10新規特徴量計算用
try:
    from feature_engineering_v2 import (
        parse_diff_to_seconds,
        parse_passage,
        extract_race_class
    )
    PHASE10_AVAILABLE = True
except ImportError:
    print("Warning: feature_engineering_v2 not found. Phase 10 features disabled.")
    PHASE10_AVAILABLE = False

# Phase 11 V3新規特徴量計算用
try:
    from feature_engineering_v3 import (
        PacePredictor,
        CourseBiasAnalyzer,
        FormCycleAnalyzer
    )
    PHASE11_V3_AVAILABLE = True
except ImportError:
    print("Warning: feature_engineering_v3 not found. V3 features disabled.")
    PHASE11_V3_AVAILABLE = False

# Phase 12 V4新規特徴量計算用
try:
    from feature_engineering_v4 import (
        TrackBiasAnalyzer,
        WeatherImpactAnalyzer,
        EnhancedPacePredictor,
        DistanceAptitudeAnalyzer
    )
    PHASE12_V4_AVAILABLE = True
except ImportError:
    print("Warning: feature_engineering_v4 not found. V4 features disabled.")
    PHASE12_V4_AVAILABLE = False

# SHAP (予測根拠表示)
try:
    import warnings
    import shap
    # LightGBM binary + SHAP 0.48.0 で出る既知の動作変更Warningを抑制
    warnings.filterwarnings('ignore',
        message='.*LightGBM binary classifier.*shap values output.*',
        category=UserWarning)
    SHAP_AVAILABLE = True
except ImportError:
    print("Warning: shap not found. SHAP explanation disabled.")
    SHAP_AVAILABLE = False

# 特徴量日本語名マッピング
FEATURE_NAMES_JP = {
    'total_starts':              '通算出走数',
    'total_win_rate':            '通算勝率',
    'total_earnings':            '通算獲得賞金',
    'turf_win_rate':             '芝勝率',
    'dirt_win_rate':             'ダート勝率',
    'distance_similar_win_rate': '同距離帯勝率',
    'prev_race_rank':            '前走着順',
    'days_since_last_race':      '前走からの日数',
    'avg_passage_position':      '平均道中通過順',
    'avg_last_3f':               '平均上がり3F',
    'grade_race_starts':         '重賞出走数',
    'father_win_rate':           '父馬勝率',
    'father_top3_rate':          '父馬複勝率',
    'mother_father_win_rate':    '母父勝率',
    'mother_father_top3_rate':   '母父複勝率',
    'avg_diff_seconds':          '平均着差(秒)',
    'min_diff_seconds':          '最小着差(秒)',
    'prev_diff_seconds':         '前走着差',
    'avg_first_corner':          '平均1角通過順',
    'avg_last_corner':           '平均最終角通過順',
    'avg_position_change':       '平均順位変化',
    'class_change':              'クラス変化',
    'current_class':             '現クラス',
    'trainer_win_rate':          '調教師勝率',
    'trainer_top3_rate':         '調教師複勝率',
    'trainer_starts':            '調教師出走数',
    'jockey_win_rate':           '騎手勝率',
    'jockey_top3_rate':          '騎手複勝率',
    'jockey_starts':             '騎手出走数',
    'track_win_rate':            'コース勝率',
    'track_top3_rate':           'コース複勝率',
    'race_distance':             'レース距離',
    'is_turf':                   '芝フラグ',
    'is_dirt':                   'ダートフラグ',
    'is_良':                     '良馬場',
    'is_稍重':                   '稍重馬場',
    'is_重':                     '重馬場',
    'is_不良':                   '不良馬場',
    'frame_number':              '枠番',
    # Phase R1 追加特徴量
    'heavy_track_win_rate':      '道悪勝率',
    'distance_change':           '前走距離差(m)',
    'kiryou':                    '斤量(kg)',
    'is_female':                 '牝馬フラグ',
    'horse_age':                 '馬齢',
    'horse_weight':              '馬体重(kg)',
    'weight_change':             '馬体重増減(kg)',
    # Phase R2 追加特徴量
    'father_turf_win_rate':         '父産駒芝勝率',
    'father_dirt_win_rate':         '父産駒ダート勝率',
    'father_heavy_win_rate':        '父産駒道悪勝率',
    'father_short_win_rate':        '父産駒短距離勝率',
    'father_long_win_rate':         '父産駒長距離勝率',
    'mother_father_turf_win_rate':  '母父産駒芝勝率',
    'mother_father_dirt_win_rate':  '母父産駒ダート勝率',
    'mother_father_heavy_win_rate': '母父産駒道悪勝率',
    'mother_father_short_win_rate': '母父産駒短距離勝率',
    'mother_father_long_win_rate':  '母父産駒長距離勝率',
    'running_style':                '脚質(1逃2先3差4追)',
    'recent_3race_improvement':     '直近3走着順改善',
    'jockey_track_win_rate':        '騎手×競馬場勝率',
    'jockey_track_top3_rate':       '騎手×競馬場複勝率',
    'good_track_win_rate':          '良馬場勝率',
    'finish_strength':              '末脚強度（3+前進率）',
    # Phase R5
    'avg_first_corner_fixed':       '平均1角通過順(修正)',
    'avg_last_corner_fixed':        '平均最終角通過順(修正)',
    'avg_position_change_v2':       '平均順位変化v2',
    'running_style_v2':             '脚質v2(修正版)',
    'slightly_heavy_win_rate':      '稍重馬場勝率',
    'field_escape_count':           '出走中逃先行頭数',
    'field_pace_advantage':         '展開有利度',
    # Phase R6
    'daily_front_bias':             '当日前有利/後有利バイアス',
    'daily_prior_races':            '当日前レース数(レース番号)',
    'horse_style_vs_bias':          '脚質×当日バイアス差',
    'is_rainy':                     '天候:雨フラグ',
    'is_sunny':                     '天候:晴フラグ',
    'prev_agari_relative':          '前走末脚相対指数',
    # Phase R7
    'waku_win_rate':                '枠番バイアス勝率',
    'field_waku_rank':              'レース内枠番有利度',
    'jockey_changed':               '騎手交代フラグ',
    'jockey_change_quality':        '騎手交代品質(昇格=正)',
    # Phase R10 調教タイム特徴量
    'training_3f_relative':         '調教3Fタイム偏差(同日同コース比)',
    'training_last1f_rel':          '調教上がり1Fタイム偏差',
    'training_finish_score':        '調教脚色スコア(0一杯〜3馬也)',
    'training_course_type':         '調教コース種別(0坂路1W2芝3ダ)',
}


class KeibaGUIv3:
    def __init__(self, root):
        self.root = root
        self.root.title("競馬予想AI - Phase 14")
        self.root.geometry("1200x900")

        # 予測結果を保存
        self.last_prediction = None
        self.last_race_id = None
        self.last_race_info = None
        self.last_has_odds = False

        # 自動データ更新フラグ
        self.auto_update = tk.BooleanVar(value=True)  # デフォルトON

        # データ範囲
        self.data_range_text = "未取得"

        # データ統計（デフォルト値）
        self.data_stats = {
            'total_records': 0,
            'total_races': 0,
            'total_horses': 0,
            'enhanced_completeness': 0.0,
            'latest_date': '不明',
            'father_missing': 0,
            'mother_father_missing': 0
        }

        # SHAP explainer（load_models()内で初期化）
        self.shap_explainer_win = None

        # モデル読み込み
        self.load_models()

        # データ読み込み
        self.load_data()

        # GUI作成
        self.create_widgets()

    def load_models(self):
        """モデル読み込み - Phase 14 (LightGBM Booster, 39特徴量)"""
        try:
            self.model_win = lgb.Booster(
                model_file=os.path.join(BASE_DIR, 'phase14_model_win.txt'))
            self.model_place = lgb.Booster(
                model_file=os.path.join(BASE_DIR, 'phase14_model_place.txt'))
            with open(os.path.join(BASE_DIR, 'phase14_feature_list.pkl'), 'rb') as f:
                self.model_features = pickle.load(f)
            self.log(f"Phase 14モデル読み込み成功 ({len(self.model_features)}特徴量)")
            if SHAP_AVAILABLE:
                try:
                    self.shap_explainer_win = shap.TreeExplainer(self.model_win)
                    self.log("SHAP explainer 初期化完了")
                except Exception as e:
                    self.log(f"SHAP explainer 初期化失敗（続行）: {e}")
                    self.shap_explainer_win = None
        except Exception as e:
            self.log(f"モデル読み込み失敗: {e}")
            self.model_win = None
            self.model_place = None
            self.model_features = None

    def load_data(self):
        """過去データ読み込み"""
        try:
            self.df = pd.read_csv(os.path.join(BASE_DIR, 'data/main/netkeiba_data_2020_2025_complete.csv'), low_memory=False)

            # 日付列をISO形式に正規化（'2025年01月05日' → '2025-01-05'）
            # ※ pd.to_datetime()が日本語形式を解釈できずNaTになる問題の根本対策
            if 'date' in self.df.columns:
                def _normalize_date(date_str):
                    s = str(date_str)
                    m = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', s)
                    if m:
                        return f"{m.group(1)}-{m.group(2).zfill(2)}-{m.group(3).zfill(2)}"
                    m2 = re.search(r'(\d{4}-\d{2}-\d{2})', s)
                    if m2:
                        return m2.group(1)
                    return s
                self.df['date'] = self.df['date'].apply(_normalize_date)

            # Agari（上がり3F実測値）を enriched CSV からマージ
            _enriched_path = os.path.join(BASE_DIR, 'data/main/netkeiba_data_2020_2025_enriched.csv')
            if os.path.exists(_enriched_path):
                try:
                    _agari_df = pd.read_csv(_enriched_path,
                                            usecols=['race_id', 'horse_id', 'Agari'],
                                            low_memory=False)
                    self.df = self.df.merge(_agari_df, on=['race_id', 'horse_id'], how='left')
                except Exception:
                    pass

            # 着順・オッズを数値化
            self.df['rank'] = pd.to_numeric(self.df['着順'], errors='coerce')
            self.df['win_odds'] = pd.to_numeric(self.df['単勝'], errors='coerce')

            # 調教ランク数値化
            training_rank_map = {'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1}
            self.df['training_rank_numeric'] = self.df['training_rank'].map(training_rank_map)
            self.df['training_rank_numeric'] = self.df['training_rank_numeric'].fillna(3)

            # ペースカテゴリ
            self.df['pace_fast'] = (self.df['pace_category'] == 'fast').astype(int)
            self.df['pace_medium'] = (self.df['pace_category'] == 'medium').astype(int)
            self.df['pace_slow'] = (self.df['pace_category'] == 'slow').astype(int)

            if BACKTEST_AVAILABLE:
                # 統計計算
                self.sire_stats = calculate_sire_stats(self.df)
                self.trainer_jockey_stats = calculate_trainer_jockey_stats(self.df)

            # V3分析器を初期化
            if PHASE11_V3_AVAILABLE:
                self.log("V3分析器を初期化中...")
                self.pace_predictor = PacePredictor(self.df)
                self.bias_analyzer = CourseBiasAnalyzer(self.df)
                self.form_analyzer = FormCycleAnalyzer(self.df)
                self.log("V3分析器初期化完了")
            else:
                self.pace_predictor = None
                self.bias_analyzer = None
                self.form_analyzer = None

            # V4分析器を初期化
            if PHASE12_V4_AVAILABLE:
                self.log("V4分析器を初期化中...")
                self.track_bias_analyzer = TrackBiasAnalyzer(self.df)
                self.weather_analyzer = WeatherImpactAnalyzer(self.df)
                self.enhanced_pace_predictor = EnhancedPacePredictor(self.df)
                self.distance_analyzer = DistanceAptitudeAnalyzer(self.df)
                self.log("V4分析器初期化完了")
            else:
                self.track_bias_analyzer = None
                self.weather_analyzer = None
                self.enhanced_pace_predictor = None
                self.distance_analyzer = None

            # データ範囲を計算
            self.data_range_text = self._calculate_data_range()

            # データステータスを計算
            self.data_stats = self._calculate_data_stats()

            self.log(f"データ読み込み成功: {len(self.df):,}件")
            self.log(f"データ範囲: {self.data_range_text}")
            self.log(f"拡張特徴量完全性: {self.data_stats['enhanced_completeness']:.1f}%")
        except Exception as e:
            self.log(f"データ読み込み失敗: {e}")
            self.df = None

        # Phase12バックテスト統計を読み込み
        self.phase12_stats = self._load_phase12_stats()

    def _load_phase12_stats(self):
        """phase12_backtest_results.csv を読み込み統計を算出"""
        csv_path = os.path.join(BASE_DIR, 'phase12_backtest_results.csv')
        try:
            bt = pd.read_csv(csv_path)
            total = len(bt)
            if total == 0:
                return None
            hit_rate = bt['honmei_won'].sum() / total
            top3_rate = bt['honmei_top3'].sum() / total

            # ROI: 的中時にオッズ倍率を回収、1レース100円換算
            roi = bt.loc[bt['honmei_won'], 'honmei_odds'].sum() / total if total > 0 else 0

            # 戦略別ROI
            strategy_rois = {}
            for threshold in [2.0, 1.5, 1.2]:
                mask = bt['value'] >= threshold
                n = mask.sum()
                if n > 0:
                    won_in = bt.loc[mask & bt['honmei_won'], 'honmei_odds'].sum()
                    strategy_rois[threshold] = won_in / n
                else:
                    strategy_rois[threshold] = 0

            return {
                'total': total,
                'hit_rate': hit_rate,
                'top3_rate': top3_rate,
                'roi': roi,
                'strategy_rois': strategy_rois,
            }
        except Exception as e:
            print(f"Phase12統計読み込み失敗: {e}")
            return None

    def log(self, message):
        """ログ出力（起動前）"""
        print(message)

    def _add_enhanced_features(self, df, log_widget, dialog):
        """
        収集したデータに拡張情報を追加
        - 父・母父（血統情報）
        - 勝率（芝・ダート・総合）
        - 脚質カテゴリ
        - 平均通過位置
        """
        import numpy as np

        # 新規データ（拡張情報が未追加）を特定
        # father, mother_fatherがNaNのデータを対象
        if 'father' not in df.columns:
            df['father'] = None
        if 'mother_father' not in df.columns:
            df['mother_father'] = None

        df_new = df[df['father'].isna()].copy()

        if len(df_new) == 0:
            log_widget.insert(tk.END, f"  拡張対象データなし\n")
            return df

        log_widget.insert(tk.END, f"  対象レコード: {len(df_new):,}件\n")
        dialog.update()

        # ユニークなhorse_idを取得
        unique_horses = df_new['horse_id'].dropna().unique()
        log_widget.insert(tk.END, f"  処理対象馬: {len(unique_horses):,}頭\n")
        dialog.update()

        # 馬ごとに詳細情報を取得
        horse_data_cache = {}

        for i, horse_id in enumerate(unique_horses, 1):
            horse_id_str = str(int(horse_id))

            if i % 10 == 0:
                log_widget.insert(tk.END, f"  [{i}/{len(unique_horses)}] 処理中...\n")
                dialog.update()

            details = self._scrape_horse_details(horse_id_str)
            if details:
                stats = self._calculate_horse_statistics(details)
                horse_data_cache[horse_id] = {
                    'father': details['father'],
                    'mother_father': details['mother_father'],
                    **stats
                }

            time.sleep(1.0)

        log_widget.insert(tk.END, f"  馬情報取得完了: {len(horse_data_cache)}頭\n")
        dialog.update()

        # DataFrameに情報を追加
        for col in ['total_starts', 'total_win_rate', 'turf_win_rate', 'dirt_win_rate',
                    'avg_passage_position', 'running_style_category']:
            if col not in df.columns:
                df[col] = None

        for idx in df.index:
            horse_id = df.at[idx, 'horse_id']

            if pd.notna(horse_id) and horse_id in horse_data_cache:
                data = horse_data_cache[horse_id]
                df.at[idx, 'father'] = data.get('father')
                df.at[idx, 'mother_father'] = data.get('mother_father')
                df.at[idx, 'total_starts'] = data.get('total_starts')
                df.at[idx, 'total_win_rate'] = data.get('total_win_rate')
                df.at[idx, 'turf_win_rate'] = data.get('turf_win_rate')
                df.at[idx, 'dirt_win_rate'] = data.get('dirt_win_rate')
                df.at[idx, 'avg_passage_position'] = data.get('avg_passage_position')
                df.at[idx, 'running_style_category'] = data.get('running_style_category')

        return df

    def _scrape_horse_details(self, horse_id):
        """馬の詳細ページから血統と過去成績を取得（Selenium使用）"""
        url = f"https://db.netkeiba.com/horse/{horse_id}/"

        driver = None
        try:
            # Seleniumでページ取得（動的コンテンツ対応）
            driver = get_driver()
            driver.get(url)
            time.sleep(2)  # ページ読み込み待機

            # BeautifulSoupで解析
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            result = {
                'father': None,
                'mother_father': None,
                'past_races': [],
                'turf_results': {'win': 0, 'total': 0},
                'dirt_results': {'win': 0, 'total': 0}
            }

            # 血統情報
            pedigree_table = soup.find('table', class_='blood_table')
            if pedigree_table:
                rows = pedigree_table.find_all('tr')
                # Row 0: 父（class='b_ml'の最初のtd）
                if len(rows) >= 1:
                    father_cell = rows[0].find('td', class_='b_ml')
                    if father_cell:
                        father_link = father_cell.find('a')
                        if father_link:
                            result['father'] = father_link.get_text(strip=True)
                # Row 2: 母父（class='b_ml'のtd）
                if len(rows) >= 3:
                    mf_cell = rows[2].find('td', class_='b_ml')
                    if mf_cell:
                        mf_link = mf_cell.find('a')
                        if mf_link:
                            result['mother_father'] = mf_link.get_text(strip=True)

            # 過去レース成績
            race_table = soup.find('table', class_='db_h_race_results')
            if race_table:
                rows = race_table.find_all('tr')[1:]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 14:
                        continue

                    try:
                        rank_text = cols[11].get_text(strip=True)
                        rank = None
                        try:
                            rank = int(rank_text)
                        except:
                            pass

                        distance_text = cols[14].get_text(strip=True) if len(cols) > 14 else ''
                        is_turf = '芝' in distance_text
                        is_dirt = 'ダ' in distance_text

                        passage_text = cols[10].get_text(strip=True) if len(cols) > 10 else ''

                        result['past_races'].append({
                            'rank': rank,
                            'is_turf': is_turf,
                            'is_dirt': is_dirt,
                            'passage': passage_text
                        })

                        if rank:
                            if is_turf:
                                result['turf_results']['total'] += 1
                                if rank == 1:
                                    result['turf_results']['win'] += 1
                            elif is_dirt:
                                result['dirt_results']['total'] += 1
                                if rank == 1:
                                    result['dirt_results']['win'] += 1
                    except:
                        continue

            return result

        except Exception as e:
            return None
        finally:
            if driver:
                driver.quit()

    def _calculate_horse_statistics(self, horse_details):
        """馬の統計情報を計算"""
        if not horse_details:
            return {}

        stats = {}
        import numpy as np

        turf = horse_details['turf_results']
        if turf['total'] > 0:
            stats['turf_win_rate'] = turf['win'] / turf['total']
        else:
            stats['turf_win_rate'] = 0.0

        dirt = horse_details['dirt_results']
        if dirt['total'] > 0:
            stats['dirt_win_rate'] = dirt['win'] / dirt['total']
        else:
            stats['dirt_win_rate'] = 0.0

        total_starts = turf['total'] + dirt['total']
        total_wins = turf['win'] + dirt['win']
        if total_starts > 0:
            stats['total_win_rate'] = total_wins / total_starts
            stats['total_starts'] = total_starts
        else:
            stats['total_win_rate'] = 0.0
            stats['total_starts'] = 0

        passages = []
        for race in horse_details['past_races']:
            passage = race.get('passage', '')
            if passage:
                parts = passage.split('-')
                if parts and parts[0]:
                    try:
                        passages.append(int(parts[0]))
                    except:
                        pass

        if passages:
            stats['avg_passage_position'] = np.mean(passages)
            if stats['avg_passage_position'] <= 3:
                stats['running_style_category'] = 'front_runner'
            elif stats['avg_passage_position'] <= 6:
                stats['running_style_category'] = 'stalker'
            elif stats['avg_passage_position'] <= 10:
                stats['running_style_category'] = 'midpack'
            else:
                stats['running_style_category'] = 'closer'
        else:
            stats['avg_passage_position'] = None
            stats['running_style_category'] = 'unknown'

        return stats

    def _add_phase10_features(self, features, horse_id, current_date, race_info):
        """Phase 10新規特徴量を追加（着差、脚質、クラス）"""
        try:
            # current_dateをdatetimeに変換
            if isinstance(current_date, str):
                current_date_dt = pd.to_datetime(current_date, errors='coerce')
            else:
                current_date_dt = pd.to_datetime(current_date, errors='coerce')

            # 馬の過去レース取得
            df_dates = pd.to_datetime(self.df['date'], errors='coerce')
            horse_races = self.df[
                (self.df['horse_id'] == horse_id) &
                (df_dates < current_date_dt)
            ].copy()

            # 1. 着差関連
            if len(horse_races) > 0 and '着差' in horse_races.columns:
                diffs = horse_races['着差'].apply(parse_diff_to_seconds)
                features['avg_diff_seconds'] = diffs.mean() if len(diffs) > 0 else 1.0
                features['min_diff_seconds'] = diffs.min() if len(diffs) > 0 else 1.0

                sorted_races = horse_races.sort_values('date', ascending=False)
                features['prev_diff_seconds'] = parse_diff_to_seconds(sorted_races.iloc[0].get('着差', ''))
            else:
                features['avg_diff_seconds'] = 1.0
                features['min_diff_seconds'] = 1.0
                features['prev_diff_seconds'] = 1.0

            # 2. 通過順関連（脚質）
            if len(horse_races) > 0 and '通過' in horse_races.columns:
                first_corners = []
                last_corners = []
                for _, row in horse_races.iterrows():
                    passage = parse_passage(row.get('通過', ''))
                    if len(passage) > 0:
                        first_corners.append(passage[0])
                        last_corners.append(passage[-1])

                if first_corners:
                    features['avg_first_corner'] = np.mean(first_corners)
                    features['avg_last_corner'] = np.mean(last_corners)
                    features['avg_position_change'] = np.mean([f - l for f, l in zip(first_corners, last_corners)])
                else:
                    features['avg_first_corner'] = 5.0
                    features['avg_last_corner'] = 5.0
                    features['avg_position_change'] = 0.0
            else:
                features['avg_first_corner'] = 5.0
                features['avg_last_corner'] = 5.0
                features['avg_position_change'] = 0.0

            # 3. クラス移動
            if race_info.get('race_name') and len(horse_races) > 0:
                current_class = extract_race_class(race_info['race_name'])
                sorted_races = horse_races.sort_values('date', ascending=False)
                last_class = extract_race_class(sorted_races.iloc[0].get('race_name', ''))
                features['class_change'] = current_class - last_class
                features['current_class'] = current_class
            else:
                features['class_change'] = 0
                features['current_class'] = 3

        except Exception as e:
            print(f"Phase 10特徴量計算エラー: {e}")
            # デフォルト値
            features['avg_diff_seconds'] = 1.0
            features['min_diff_seconds'] = 1.0
            features['prev_diff_seconds'] = 1.0
            features['avg_first_corner'] = 5.0
            features['avg_last_corner'] = 5.0
            features['avg_position_change'] = 0.0
            features['class_change'] = 0
            features['current_class'] = 3

        return features

    def _add_v3_features(self, features, horse_id, race_horses_ids, race_info):
        """V3新規特徴量を追加（ペース予測、コースバイアス、フォームサイクル）"""
        try:
            # 1. ペース予測
            predicted_pace = self.pace_predictor.predict_pace(race_horses_ids, len(race_horses_ids))
            pace_advantage = self.pace_predictor.calculate_pace_advantage(horse_id, predicted_pace)
            features['predicted_pace_high'] = 1 if predicted_pace == 'high' else 0
            features['predicted_pace_slow'] = 1 if predicted_pace == 'slow' else 0
            features['pace_advantage_v3'] = pace_advantage  # モデル特徴量名に合わせる

            # 2. コースバイアス（枠番有利不利）
            track = race_info.get('track_name', '')
            distance = race_info.get('distance', 1600)
            waku = race_info.get('waku', '')
            condition = race_info.get('track_condition', '')
            gate_advantage = self.bias_analyzer.get_gate_advantage(track, distance, waku, condition)
            features['gate_bias_advantage'] = gate_advantage

            # 3. フォームサイクル（休養明け適正）
            days_since_last = features.get('days_since_last_race', 30)
            interval_advantage = self.form_analyzer.get_interval_advantage(horse_id, days_since_last)
            features['interval_advantage'] = interval_advantage

        except Exception as e:
            print(f"V3特徴量計算エラー: {e}")
            # デフォルト値
            features['predicted_pace_high'] = 0
            features['predicted_pace_slow'] = 0
            features['pace_advantage_v3'] = 0.0  # モデル特徴量名に合わせる
            features['gate_bias_advantage'] = 0.0
            features['interval_advantage'] = 0.0

        return features

    def _add_v4_features(self, features, horse_info, horse_id, race_horses_ids, race_info):
        """V4新規特徴量を追加（馬場バイアス、天気×血統、展開予測、距離適性）"""
        try:
            waku = race_info.get('waku', 4)
            track = race_info.get('track_name', '')
            condition = race_info.get('track_condition', '良')
            weather = race_info.get('weather', '晴')
            course_type = race_info.get('course_type', '')
            distance = race_info.get('distance', 1600)

            # 血統情報を取得
            father = ''
            mother_father = ''
            if horse_id:
                horse_id_num = float(horse_id)
                horse_rows = self.df[self.df['horse_id'] == horse_id_num]
                if len(horse_rows) > 0:
                    latest = horse_rows.iloc[-1]
                    father = latest.get('father', '')
                    mother_father = latest.get('mother_father', '')

            # 1. 馬場バイアス
            bias_info = self.track_bias_analyzer.get_realtime_bias(track, condition, course_type)
            bias_advantage = self.track_bias_analyzer.calculate_bias_advantage(waku, bias_info)
            features['track_bias_advantage'] = bias_advantage
            features['track_bias_inner'] = 1 if bias_info['direction'] == 'inner' else 0
            features['track_bias_outer'] = 1 if bias_info['direction'] == 'outer' else 0
            features['track_bias_strength'] = bias_info['strength']

            # 2. 天気×血統
            weather_score = self.weather_analyzer.get_weather_condition_score(
                father, mother_father, condition, weather
            )
            features['weather_bloodline_score'] = weather_score
            features['is_heavy_track'] = 1 if condition in ['重', '不良'] else 0
            features['is_rainy'] = 1 if weather in ['雨', '小雨', '大雨'] else 0

            # 3. 展開予測強化
            race_horses = []
            for hid in race_horses_ids:
                race_horses.append({'horse_id': hid, 'waku': waku})
            pace_analysis = self.enhanced_pace_predictor.analyze_race_pace(race_horses)
            pace_advantage = self.enhanced_pace_predictor.calculate_pace_advantage(horse_id, pace_analysis)
            features['pace_advantage'] = pace_advantage
            features['escapers_count'] = pace_analysis['escapers_count']
            features['front_competition_intense'] = 1 if pace_analysis['front_competition'] == 'intense' else 0
            features['escape_success_prob'] = pace_analysis['escape_success_prob']

            # 4. 距離適性
            distance_score = self.distance_analyzer.get_distance_aptitude(horse_id, father, distance)
            features['distance_aptitude'] = distance_score

        except Exception as e:
            print(f"V4特徴量計算エラー: {e}")
            features.setdefault('track_bias_advantage', 0.0)
            features.setdefault('track_bias_inner', 0)
            features.setdefault('track_bias_outer', 0)
            features.setdefault('track_bias_strength', 0.0)
            features.setdefault('weather_bloodline_score', 0.0)
            features.setdefault('is_heavy_track', 0)
            features.setdefault('is_rainy', 0)
            features.setdefault('escapers_count', 0)
            features.setdefault('front_competition_intense', 0)
            features.setdefault('escape_success_prob', 0.0)
            features.setdefault('distance_aptitude', 0.0)

        return features

    def _calculate_data_range(self):
        """データベースの収録範囲を計算"""
        if self.df is None or len(self.df) == 0:
            return "データなし"

        try:
            # date列から最古と最新を取得
            dates = self.df['date'].dropna()
            if len(dates) == 0:
                return "日付データなし"

            # 日付フォーマットを統一して解析
            date_list = []
            for d in dates:
                d_str = str(d)
                try:
                    # "YYYY年MM月DD日" 形式
                    if '年' in d_str:
                        date_list.append(pd.to_datetime(d_str, format='%Y年%m月%d日'))
                    # "YYYY-MM-DD" 形式
                    elif '-' in d_str:
                        date_list.append(pd.to_datetime(d_str.split()[0]))  # タイムスタンプ除去
                    else:
                        date_list.append(pd.to_datetime(d_str))
                except:
                    continue

            if len(date_list) == 0:
                return "日付解析エラー"

            min_date = min(date_list)
            max_date = max(date_list)

            return f"{min_date.strftime('%Y年%m月')} ～ {max_date.strftime('%Y年%m月')}"
        except Exception as e:
            return f"計算エラー: {e}"

    def _calculate_data_stats(self):
        """データベースの詳細統計を計算"""
        if self.df is None or len(self.df) == 0:
            return {
                'total_records': 0,
                'total_races': 0,
                'total_horses': 0,
                'enhanced_completeness': 0.0,
                'latest_date': '不明',
                'father_missing': 0,
                'mother_father_missing': 0
            }

        try:
            # 基本統計
            total_records = len(self.df)
            total_races = self.df['race_id'].nunique() if 'race_id' in self.df.columns else 0
            total_horses = self.df['horse_id'].nunique() if 'horse_id' in self.df.columns else 0

            # 拡張特徴量の完全性
            father_missing = self.df['father'].isna().sum() if 'father' in self.df.columns else total_records
            mother_father_missing = self.df['mother_father'].isna().sum() if 'mother_father' in self.df.columns else total_records

            # 完全性スコア（father/mother_fatherの欠損率から計算）
            enhanced_completeness = 100.0 - (father_missing / total_records * 100) if total_records > 0 else 0.0

            # 最新データ日付
            latest_date = "不明"
            if 'date' in self.df.columns:
                dates = self.df['date'].dropna()
                if len(dates) > 0:
                    date_list = []
                    for d in dates:
                        d_str = str(d)
                        try:
                            if '年' in d_str:
                                date_list.append(pd.to_datetime(d_str, format='%Y年%m月%d日'))
                            elif '-' in d_str:
                                date_list.append(pd.to_datetime(d_str.split()[0]))
                            else:
                                date_list.append(pd.to_datetime(d_str))
                        except:
                            continue
                    if date_list:
                        max_date = max(date_list)
                        latest_date = max_date.strftime('%Y年%m月%d日')

            return {
                'total_records': total_records,
                'total_races': total_races,
                'total_horses': total_horses,
                'enhanced_completeness': enhanced_completeness,
                'latest_date': latest_date,
                'father_missing': father_missing,
                'mother_father_missing': mother_father_missing
            }
        except Exception as e:
            self.log(f"データ統計計算エラー: {e}")
            return {
                'total_records': 0,
                'total_races': 0,
                'total_horses': 0,
                'enhanced_completeness': 0.0,
                'latest_date': '不明',
                'father_missing': 0,
                'mother_father_missing': 0
            }

    def create_widgets(self):
        """GUI作成"""
        # タイトル
        title_frame = tk.Frame(self.root, bg="#2196F3", height=60)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        title = tk.Label(title_frame, text="🏇 競馬予想AI - Phase 14",
                        font=("Arial", 18, "bold"), bg="#2196F3", fg="white")
        title.pack(pady=15)

        # メインコンテナ（リサイズ可能なPanedWindow）
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左側: 入力エリア
        left_frame = tk.Frame(main_container)
        main_container.add(left_frame, weight=1)

        # レースID入力
        input_frame = tk.LabelFrame(left_frame, text="レース情報", font=("Arial", 11, "bold"))
        input_frame.pack(fill=tk.X, pady=5)

        tk.Label(input_frame, text="レースID:", font=("Arial", 10)).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.race_id_entry = tk.Entry(input_frame, width=25, font=("Arial", 10))
        self.race_id_entry.grid(row=0, column=1, padx=5, pady=5)
        self.race_id_entry.insert(0, "202510020812")  # データベース最新レース

        tk.Label(input_frame, text="例: 202510020812\n（年月日場所レース番号）\n\n未来のレース: netkeiba出馬表から取得\n過去のレース: データベース使用\n\nDB収録: 2025/01/01～2025/10/02",
                font=("Arial", 8), fg="gray").grid(row=1, column=1, padx=5, sticky=tk.W)

        # ボタン
        button_frame = tk.Frame(left_frame)
        button_frame.pack(pady=10)

        self.predict_button = tk.Button(button_frame, text="🔮 予想開始",
                                       command=self.predict_race,
                                       bg="#4CAF50", fg="white",
                                       font=("Arial", 12, "bold"),
                                       width=20, height=2)
        self.predict_button.pack(pady=5)

        self.export_button = tk.Button(button_frame, text="💾 結果をCSV保存",
                                       command=self.export_results,
                                       bg="#546E7A", fg="white",
                                       font=("Arial", 10, "bold"),
                                       width=20, height=1,
                                       state=tk.DISABLED)
        self.export_button.pack(pady=5)

        self.update_button = tk.Button(button_frame, text="🔄 このレースのデータ更新",
                                       command=self.update_race_data,
                                       bg="#546E7A", fg="white",
                                       font=("Arial", 10, "bold"),
                                       width=20, height=1)
        self.update_button.pack(pady=5)

        # 期間指定データ収集ボタン
        self.period_collect_button = tk.Button(button_frame, text="📅 期間データ収集",
                                               command=self.open_period_collection_dialog,
                                               bg="#546E7A", fg="white",
                                               font=("Arial", 10, "bold"),
                                               width=20, height=1)
        self.period_collect_button.pack(pady=5)

        # Win5予測ボタン
        self.win5_button = tk.Button(button_frame, text="🏆 Win5予測",
                                     command=self.predict_win5,
                                     bg="#546E7A", fg="white",
                                     font=("Arial", 10, "bold"),
                                     width=20, height=1)
        self.win5_button.pack(pady=5)

        # 自動更新チェックボックス
        auto_update_check = tk.Checkbutton(button_frame,
                                           text="予測前に自動データ更新",
                                           variable=self.auto_update,
                                           font=("Arial", 9))
        auto_update_check.pack(pady=5)

        # 進捗バー
        self.progress = ttk.Progressbar(left_frame, length=400, mode='determinate')
        self.progress.pack(pady=10)

        # 統計情報表示
        stats_frame = tk.LabelFrame(left_frame, text="Phase 14 統計", font=("Arial", 10, "bold"))
        stats_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        # データベース情報
        db_records = f"{len(self.df):,}" if self.df is not None else "0"

        # データ統計を取得
        stats = self.data_stats if hasattr(self, 'data_stats') else {}
        enhanced_complete = stats.get('enhanced_completeness', 0.0)
        latest_date = stats.get('latest_date', '不明')
        total_races = stats.get('total_races', 0)
        total_horses = stats.get('total_horses', 0)
        father_missing = stats.get('father_missing', 0)

        # Phase14モデル情報テキスト組み立て
        stats_text = (
            "Phase 14 モデル情報:\n\n"
            "  単勝モデル AUC: 0.7988\n"
            "  複勝モデル AUC: 0.7558\n"
            "  使用特徴量: 39個\n"
            "  訓練期間: 2020〜2022年\n"
            "  OOS検証: 2024・2025年\n\n"
            "GUI一致バックテスト (2024 OOS):\n"
            "  Rule4 ROI: 139.1%\n"
            "  Rule4 ROI (2025): 154.8%\n"
            "  年間件数: ~6,349件\n"
        )

        stats_text += (
            f"\n{'━'*28}\n"
            f"データベース状況:\n"
            f"{'━'*28}\n"
            f"  収録件数: {db_records}件\n"
            f"  レース数: {total_races:,}レース\n"
            f"  馬匹数: {total_horses:,}頭\n"
            f"  収録期間: {self.data_range_text}\n"
            f"  最新データ: {latest_date}\n\n"
            f"【拡張特徴量の充実度】\n"
            f"  完全性: {enhanced_complete:.1f}%\n"
            f"  欠損: {father_missing:,}件\n"
            f"    → 血統データの充実度を示します\n"
        )

        # スクロール可能な Text ウィジェットに変更
        stats_inner = tk.Frame(stats_frame)
        stats_inner.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        stats_scroll = tk.Scrollbar(stats_inner, orient=tk.VERTICAL)
        stats_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        stats_text_widget = tk.Text(stats_inner, wrap=tk.WORD, height=18,
                                    font=("Courier", 9), bg="lightyellow",
                                    yscrollcommand=stats_scroll.set,
                                    state=tk.NORMAL, relief=tk.FLAT)
        stats_text_widget.insert(tk.END, stats_text)
        stats_text_widget.config(state=tk.DISABLED)
        stats_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        stats_scroll.config(command=stats_text_widget.yview)

        # 右側: 結果表示エリア（リサイズ可能）
        right_frame = tk.Frame(main_container)
        main_container.add(right_frame, weight=3)  # 右側を広めに

        # レース情報表示エリア
        self.race_info_label = tk.Label(right_frame, text="レース情報: 未取得",
                                        font=("Arial", 10), anchor=tk.W, justify=tk.LEFT)
        self.race_info_label.pack(fill=tk.X, pady=(0, 5))

        # 予測結果テーブル
        table_frame = tk.Frame(right_frame)
        table_frame.pack(fill=tk.BOTH, expand=True)

        # スクロールバー
        scrollbar_y = tk.Scrollbar(table_frame, orient=tk.VERTICAL)
        scrollbar_x = tk.Scrollbar(table_frame, orient=tk.HORIZONTAL)

        # Treeview（表） - netkeiba風レイアウト
        columns = ('枠', '馬番', '印', '馬名', '性齢', '斤量', '騎手', '馬体重', 'オッズ', '人気', '勝率%', '複勝%', '期待値', '過去成績')
        self.result_tree = ttk.Treeview(table_frame, columns=columns, show='headings',
                                        yscrollcommand=scrollbar_y.set,
                                        xscrollcommand=scrollbar_x.set,
                                        height=18)

        scrollbar_y.config(command=self.result_tree.yview)
        scrollbar_x.config(command=self.result_tree.xview)
        scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 列の設定（netkeiba風）
        self.result_tree.column('枠', width=35, anchor=tk.CENTER)
        self.result_tree.column('馬番', width=35, anchor=tk.CENTER)
        self.result_tree.column('印', width=35, anchor=tk.CENTER)
        self.result_tree.column('馬名', width=140, anchor=tk.W)
        self.result_tree.column('性齢', width=45, anchor=tk.CENTER)
        self.result_tree.column('斤量', width=45, anchor=tk.CENTER)
        self.result_tree.column('騎手', width=70, anchor=tk.W)
        self.result_tree.column('馬体重', width=75, anchor=tk.CENTER)
        self.result_tree.column('オッズ', width=60, anchor=tk.E)
        self.result_tree.column('人気', width=40, anchor=tk.CENTER)
        self.result_tree.column('勝率%', width=60, anchor=tk.E)
        self.result_tree.column('複勝%', width=60, anchor=tk.E)
        self.result_tree.column('期待値', width=60, anchor=tk.E)
        self.result_tree.column('過去成績', width=200, anchor=tk.W)

        # ヘッダー設定（クリックでソート）
        for col in columns:
            self.result_tree.heading(col, text=col, command=lambda c=col: self.sort_tree_column(c))

        # 枠番色設定（薄い色で視認性向上）
        self.result_tree.tag_configure('waku1', background='#FFFFFF')  # 白
        self.result_tree.tag_configure('waku2', background='#E0E0E0')  # 薄い灰色（黒の代わり）
        self.result_tree.tag_configure('waku3', background='#FFE5E5')  # 薄い赤
        self.result_tree.tag_configure('waku4', background='#E5F0FF')  # 薄い青
        self.result_tree.tag_configure('waku5', background='#FFFACD')  # 薄い黄
        self.result_tree.tag_configure('waku6', background='#E8F5E9')  # 薄い緑
        self.result_tree.tag_configure('waku7', background='#FFE4CC')  # 薄い橙
        self.result_tree.tag_configure('waku8', background='#FFE4F0')  # 薄い桃

        # 信頼度低の行（グレー文字で表示）
        self.result_tree.tag_configure('low_reliability', foreground='#999999')

        # 推奨馬券表示エリア（予測結果の下に配置）- サイズ拡大
        recommend_frame = tk.LabelFrame(right_frame, text="📋 予測結果・推奨買い目", font=("Arial", 11, "bold"), fg="#37474F")
        recommend_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        # スクロール付きテキスト（高さ拡大: 8→15）
        recommend_scroll = tk.Scrollbar(recommend_frame)
        recommend_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.recommend_text = tk.Text(recommend_frame, height=15, font=("Consolas", 10),
                                      bg="#FFFFFF", state=tk.DISABLED, wrap=tk.WORD,
                                      yscrollcommand=recommend_scroll.set)
        self.recommend_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        recommend_scroll.config(command=self.recommend_text.yview)

        # 統計可視化・詳細分析ボタン
        analysis_button_frame = tk.Frame(right_frame)
        analysis_button_frame.pack(fill=tk.X, pady=5)

        self.stats_viz_button = tk.Button(analysis_button_frame, text="📊 統計情報グラフ",
                                          command=self.show_statistics_visualization,
                                          bg="#546E7A", fg="white",
                                          font=("Arial", 9, "bold"),
                                          width=18, height=1,
                                          state=tk.DISABLED)
        self.stats_viz_button.pack(side=tk.LEFT, padx=5)

        self.detail_analysis_button = tk.Button(analysis_button_frame, text="🔍 詳細分析",
                                               command=self.show_detailed_analysis,
                                               bg="#546E7A", fg="white",
                                               font=("Arial", 9, "bold"),
                                               width=18, height=1,
                                               state=tk.DISABLED)
        self.detail_analysis_button.pack(side=tk.LEFT, padx=5)

        # ステータスバー
        self.status_label = tk.Label(self.root, text="準備完了", bd=1, relief=tk.SUNKEN,
                                     anchor=tk.W, font=("Arial", 9))
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

    def _decode_race_id(self, race_id):
        """race_id (YYYYPPKKDDRR) をデコードして競馬場名・回・日・レース番号を返す"""
        TRACK_CODES = {
            '01': '札幌', '02': '函館', '03': '福島', '04': '新潟',
            '05': '東京', '06': '中山', '07': '中京', '08': '京都',
            '09': '阪神', '10': '小倉'
        }
        s = str(race_id).strip()
        if len(s) != 12 or not s.isdigit():
            return None
        year = s[0:4]
        place_code = s[4:6]
        kai = int(s[6:8])
        day = int(s[8:10])
        race_num = int(s[10:12])
        track_name = TRACK_CODES.get(place_code, f'場{place_code}')
        return {
            'year': year,
            'place_code': place_code,
            'track_name': track_name,
            'kai': kai,
            'day': day,
            'race_num': race_num,
        }

    def _get_odds_from_snapshot_db(self, race_id: str) -> dict:
        """
        odds_timeseries.db からこのレースの最新オッズを取得する。
        タスクスケジューラ or 手動実行で保存されたスナップショットを使用。
        returns: {'1': 4.5, '2': 12.3, ...}  馬番(文字列) → 単勝オッズ
                 データがなければ空dict
        """
        import sqlite3 as _sqlite3
        db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'odds_collector', 'odds_timeseries.db')
        if not os.path.exists(db_path):
            return {}
        try:
            conn = _sqlite3.connect(db_path)
            # umaban列でマッチング（最新タイミングのデータを優先）
            rows = conn.execute('''
                SELECT umaban, odds_win, recorded_at
                FROM odds_snapshots
                WHERE race_id = ? AND odds_win > 0 AND umaban != ''
                ORDER BY recorded_at DESC
            ''', (race_id,)).fetchall()
            conn.close()
        except Exception:
            return {}

        # 同一馬番の中で最新レコードのみ残す
        seen = {}
        for umaban, odds_win, rec_at in rows:
            uma = str(int(float(umaban))) if umaban else ''
            if uma and uma not in seen:
                seen[uma] = odds_win
        return seen

    def get_race_from_database(self, race_id):
        """データベースからレース情報を取得"""
        # race_idを整数に変換（データベースはint64型）
        try:
            race_id_int = int(race_id)
        except:
            return None, None

        race_data = self.df[self.df['race_id'] == race_id_int].copy()

        if len(race_data) == 0:
            return None, None

        # レース情報
        first_row = race_data.iloc[0]

        # race_idデコードで競馬場名・レース番号を補完
        decoded = self._decode_race_id(race_id)
        db_track = first_row.get('track_name', '')
        track_name = db_track if db_track else (decoded['track_name'] if decoded else '')
        race_num = decoded['race_num'] if decoded else None

        # race_name: DB列があればそちらを優先
        db_race_name = first_row.get('race_name', '') if 'race_name' in race_data.columns else ''
        if not db_race_name or pd.isna(db_race_name):
            db_race_name = ''
        race_name_display = db_race_name if db_race_name else f"{track_name} {first_row.get('distance', '')}m"

        # course_type補完: Noneの場合は空文字列（calculate_horse_features_dynamicでのエラー防止）
        course_type = first_row.get('course_type')
        if pd.isna(course_type) or course_type is None:
            course_type = ''  # 空文字列にすることでstr.contains()のエラーを回避

        race_info = {
            'race_name': race_name_display,
            'track_name': track_name,
            'distance': first_row.get('distance'),
            'course_type': course_type,
            'track_condition': first_row.get('track_condition'),
            'date': first_row.get('date'),
            'race_num': race_num,
            'from_database': True
        }
        if decoded:
            race_info['kai'] = decoded['kai']
            race_info['day'] = decoded['day']

        # 馬情報
        horses = []
        for idx, row in race_data.iterrows():
            horses.append({
                '枠番': str(int(row['枠番'])) if pd.notna(row.get('枠番')) else '1',
                '馬番': str(int(row['馬番'])) if pd.notna(row.get('馬番')) else '1',
                '馬名': row['馬名'],
                'horse_id': row['horse_id'],
                '騎手': row.get('騎手', ''),
                '調教師': row.get('調教師', ''),
                '斤量': row.get('斤量', ''),
                '性齢': row.get('性齢', ''),
                '馬体重': row.get('馬体重', ''),
                '単勝オッズ': row.get('win_odds', 0) if pd.notna(row.get('win_odds')) else 0,
                '実際の着順': row.get('rank')  # 答え合わせ用
            })

        return horses, race_info

    def scrape_race_result(self, race_id):
        """レース結果ページから馬の情報を取得"""
        url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.encoding = response.apparent_encoding

            if response.status_code != 200:
                return None, {'error': 'http_error', 'status_code': response.status_code}

            soup = BeautifulSoup(response.text, 'html.parser')

            race_info = {}
            race_title = soup.find('div', class_='RaceName')
            if race_title:
                race_info['race_name'] = race_title.get_text(strip=True)

            race_data01 = soup.find('div', class_='RaceData01')
            if race_data01:
                race_text = race_data01.get_text()
                distance_match = re.search(r'([芝ダ障])(\d+)m', race_text)
                if distance_match:
                    course_type = '芝' if distance_match.group(1) == '芝' else 'ダート'
                    distance = int(distance_match.group(2))
                    race_info['course_type'] = course_type
                    race_info['distance'] = distance

                condition_match = re.search(r'馬場[:：\s]*([良稍重不])', race_text)
                if condition_match:
                    race_info['track_condition'] = condition_match.group(1)

                # 発走時刻
                time_match = re.search(r'(\d{1,2}):(\d{2})発走', race_text)
                if time_match:
                    race_info['start_time'] = f"{time_match.group(1)}:{time_match.group(2)}"

            race_data02 = soup.find('div', class_='RaceData02')
            if race_data02:
                spans = race_data02.find_all('span')
                # spans[0]="1回", spans[1]="中山" なので spans[1] を使う
                if len(spans) > 1:
                    track_name = spans[1].get_text(strip=True)
                    race_info['track_name'] = track_name
                elif len(spans) > 0:
                    # フォールバック
                    track_name = spans[0].get_text(strip=True)
                    race_info['track_name'] = track_name

            table = soup.find('table', class_='RaceTable01')
            if not table:
                return None, race_info

            horses = []
            rows = table.find_all('tr')[1:]

            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 8:
                    continue

                rank = cols[0].get_text(strip=True)
                waku = cols[1].get_text(strip=True)
                umaban = cols[2].get_text(strip=True)

                horse_link = cols[3].find('a')
                if horse_link:
                    horse_name = horse_link.get_text(strip=True)
                    horse_url = horse_link.get('href', '')
                    horse_id_match = re.search(r'/horse/(\d+)', horse_url)
                    horse_id = horse_id_match.group(1) if horse_id_match else None
                else:
                    horse_name = cols[3].get_text(strip=True)
                    horse_id = None

                jockey_col = cols[6] if len(cols) > 6 else None
                if jockey_col:
                    jockey_link = jockey_col.find('a')
                    jockey = jockey_link.get_text(strip=True) if jockey_link else jockey_col.get_text(strip=True)
                else:
                    jockey = ''

                odds_col = cols[9] if len(cols) > 9 else None
                if odds_col:
                    odds_str = odds_col.get_text(strip=True)
                    try:
                        odds = float(odds_str)
                    except:
                        odds = 0
                else:
                    odds = 0

                horses.append({
                    '枠番': waku,
                    '馬番': umaban,
                    '馬名': horse_name,
                    'horse_id': horse_id,
                    '騎手': jockey,
                    '調教師': '',
                    '斤量': '',
                    '単勝オッズ': odds,
                    '実際の着順': rank
                })

            race_info['from_database'] = False
            race_info['from_result'] = True
            return horses, race_info

        except Exception as e:
            print(f"Result scraping error: {e}")
            return None, {'error': 'exception', 'message': str(e)}

    def scrape_shutuba(self, race_id):
        """出馬表をスクレイピング（Selenium版でオッズ取得）"""
        url = f"https://race.netkeiba.com/race/shutuba.html?race_id={race_id}"

        driver = None
        try:
            # Seleniumでページを取得（オッズは動的読み込みのため）
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            import time

            options = Options()
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            # GPU関連のエラーメッセージを抑制
            options.add_experimental_option('excludeSwitches', ['enable-logging'])

            driver = webdriver.Chrome(options=options)
            driver.get(url)

            # テーブルが読み込まれるまで待機
            wait = WebDriverWait(driver, 15)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.Shutuba_Table')))

            # さらに少し待機（オッズの動的読み込み対応）
            time.sleep(2)

            # ページソースを取得してBeautifulSoupで解析
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # レース情報取得
            race_info = {}
            race_title = soup.find('div', class_='RaceName')
            if race_title:
                race_info['race_name'] = race_title.get_text(strip=True)

            race_data = soup.find('div', class_='RaceData01')
            if race_data:
                race_text = race_data.get_text()
                distance_match = re.search(r'([芝ダ障])(\d+)m', race_text)
                if distance_match:
                    course_type = '芝' if distance_match.group(1) == '芝' else 'ダート'
                    distance = int(distance_match.group(2))
                    race_info['course_type'] = course_type
                    race_info['distance'] = distance

                condition_match = re.search(r'馬場[:：\s]*([良稍重不])', race_text)
                if condition_match:
                    race_info['track_condition'] = condition_match.group(1)

                # 発走時刻
                time_match = re.search(r'(\d{1,2}):(\d{2})発走', race_text)
                if time_match:
                    race_info['start_time'] = f"{time_match.group(1)}:{time_match.group(2)}"

            race_data02 = soup.find('div', class_='RaceData02')
            if race_data02:
                spans = race_data02.find_all('span')
                # spans[0]="1回", spans[1]="中山" なので spans[1] を使う
                if len(spans) > 1:
                    track_name = spans[1].get_text(strip=True)
                    race_info['track_name'] = track_name
                elif len(spans) > 0:
                    track_name = spans[0].get_text(strip=True)
                    race_info['track_name'] = track_name

            # 出馬表テーブル取得
            table = soup.find('table', class_='Shutuba_Table')
            if not table:
                if driver:
                    driver.quit()
                return None, race_info

            horses = []
            rows = table.find_all('tr')[1:]  # ヘッダー除く

            for row in rows:
                cols = row.find_all('td')
                if len(cols) < 10:
                    continue

                waku = cols[0].get_text(strip=True)
                umaban = cols[1].get_text(strip=True)

                # 馬名とhorse_id
                horse_link = cols[3].find('a')
                if horse_link:
                    horse_name = horse_link.get_text(strip=True)
                    horse_url = horse_link.get('href', '')
                    horse_id_match = re.search(r'/horse/(\d+)', horse_url)
                    horse_id = horse_id_match.group(1) if horse_id_match else None
                else:
                    horse_name = cols[3].get_text(strip=True)
                    horse_id = None

                sex_age = cols[4].get_text(strip=True)  # 性齢は4列目
                weight = cols[5].get_text(strip=True)   # 斤量は5列目
                jockey = cols[6].get_text(strip=True)   # 騎手は6列目
                trainer = cols[7].get_text(strip=True)  # 調教師は7列目
                horse_weight = cols[8].get_text(strip=True) if len(cols) > 8 else ''  # 馬体重は8列目

                # オッズ取得（複数の方法を試行）
                odds = 0

                # 方法1: spanタグのid="odds-{馬番}"を探す
                odds_span = row.select_one(f'span[id^="odds"]')
                if odds_span:
                    try:
                        odds = float(odds_span.get_text(strip=True))
                    except:
                        pass

                # 方法2: 列インデックス
                if odds == 0:
                    odds_str = cols[9].get_text(strip=True) if len(cols) > 9 else ''
                    try:
                        odds = float(odds_str) if odds_str else 0
                    except:
                        odds = 0

                horses.append({
                    '枠番': waku,
                    '馬番': umaban,
                    '馬名': horse_name,
                    'horse_id': horse_id,
                    '性齢': sex_age,
                    '斤量': weight,
                    '騎手': jockey,
                    '調教師': trainer,
                    '馬体重': horse_weight,
                    '単勝オッズ': odds  # 単勝オッズに統一
                })

            driver.quit()
            race_info['from_database'] = False
            return horses, race_info

        except Exception as e:
            print(f"Selenium scraping error: {e}")
            if driver:
                driver.quit()
            return None, {'error': 'exception', 'message': str(e)}

    def predict_race(self):
        """レース予想"""
        if not BACKTEST_AVAILABLE:
            messagebox.showerror("エラー", "バックテストモジュールが読み込まれていません")
            return

        race_id = self.race_id_entry.get().strip()

        if not race_id:
            messagebox.showerror("エラー", "レースIDを入力してください")
            return

        self.status_label.config(text=f"予想中... レースID: {race_id}")
        # テーブルとレース情報をクリア
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        self.race_info_label.config(text="レース情報取得中...")
        self.predict_button.config(state=tk.DISABLED)
        self.progress['value'] = 0
        self.root.update()

        try:
            # 出馬表取得
            self.insert_text(f"{'='*80}\n", "header")
            self.insert_text(f" レース予想 - {race_id}\n", "header")
            self.insert_text(f"{'='*80}\n\n", "header")

            self.insert_text("[1] レースデータ取得中...\n")
            self.progress['value'] = 10
            self.root.update()

            # まず出馬表ページを試行
            horses, race_info = self.scrape_shutuba(race_id)

            # オッズデータの有無を確認
            has_odds = False
            if horses:
                has_odds = any(h.get('単勝オッズ', 0) > 0 for h in horses)

            # 出馬表失敗時は結果ページを試行（オッズなしは許容）
            if not horses or (race_info and race_info.get('error')):
                self.insert_text("  出馬表なし → 結果ページを確認中...\n", "info")
                horses, race_info = self.scrape_race_result(race_id)
                # 結果ページでオッズを再確認
                if horses:
                    has_odds = any(h.get('単勝オッズ', 0) > 0 for h in horses)

            # それでも失敗時はデータベースを確認
            if not horses or (race_info and race_info.get('error')):
                self.insert_text("  結果ページなし → データベースを確認中...\n", "info")
                horses, race_info = self.get_race_from_database(race_id)

                if not horses:
                    self.insert_text("\nレースが見つかりませんでした。\n", "error")
                    self.insert_text("• 未来のレース: netkeibaで出馬表が公開されているか確認\n", "error")
                    self.insert_text("• 過去のレース: データベースに存在するレースIDを使用\n", "error")
                    self.insert_text("\nデータベース内のレース例:\n", "info")
                    sample_races = self.df.groupby('race_id').first().sample(5)
                    for rid in sample_races.index:
                        self.insert_text(f"  {rid}\n", "info")
                    self.status_label.config(text="エラー: レースが見つかりません")
                    return
                else:
                    self.insert_text("  データベースからレース情報を取得しました\n", "success")

            self.insert_text(f"  {len(horses)}頭の出馬を確認\n", "success")
            if race_info.get('race_name'):
                self.insert_text(f"  レース名: {race_info['race_name']}\n")
            if race_info.get('track_name'):
                self.insert_text(f"  競馬場: {race_info['track_name']}\n")
            if race_info.get('course_type') and race_info.get('distance'):
                self.insert_text(f"  コース: {race_info['course_type']}{race_info['distance']}m\n")
            if race_info.get('track_condition'):
                self.insert_text(f"  馬場状態: {race_info['track_condition']}\n")
            if race_info.get('date'):
                self.insert_text(f"  日付: {race_info['date']}\n")
            if race_info.get('from_database'):
                self.insert_text("  ソース: データベース（過去レース）\n", "info")
            elif race_info.get('from_result'):
                self.insert_text("  ソース: netkeiba結果ページ（過去レース・オッズあり）\n", "info")
            else:
                self.insert_text("  ソース: netkeiba出馬表（未来レース）\n", "info")

            # オッズが未取得の場合、ローカルDBから補完を試みる
            if not has_odds and horses:
                db_odds = self._get_odds_from_snapshot_db(race_id)
                if db_odds:
                    for h in horses:
                        uma = str(h.get('馬番', ''))
                        if uma in db_odds and db_odds[uma] > 0:
                            h['単勝オッズ'] = db_odds[uma]
                    has_odds = any(h.get('単勝オッズ', 0) > 0 for h in horses)
                    if has_odds:
                        self.insert_text(
                            f"  ✓ オッズをローカルDB（odds_timeseries.db）から補完しました"
                            f"（{len(db_odds)}頭分）\n", "success")

            # オッズの有無を表示
            if not has_odds:
                self.insert_text("  ⚠ オッズ未発表（予測は可能、期待値計算は不可）\n", "warning")

            self.insert_text("\n")

            self.progress['value'] = 20
            self.root.update()

            # 予測実行（ここから先は元のコードと同じ）
            if self.model_win is None or self.df is None:
                self.insert_text("モデルまたはデータが読み込まれていません\n", "error")
                self.status_label.config(text="エラー: モデル未読み込み")
                return

            # レベル1: クイックチェック（DB未登録馬のみ自動更新）
            # ※ warn_daysによる「データが古い」判定は誤検知が多い
            #   （単に出走間隔が空いているだけの馬を更新対象にしてしまう）
            #   → DB未登録馬(no_data)のみ自動更新対象とする
            try:
                from smart_update_system import quick_check_horses
                check_result = quick_check_horses(horses, self.df, warn_days=180)

                no_data = [w for w in check_result['warnings'] if w['type'] == 'no_data']
                if no_data:
                    self.insert_text("[2] データ状態チェック\n")
                    self.insert_text(f"  ℹ {len(no_data)}頭: DB未登録（予測精度低）\n", "info")

                    # DB未登録馬のみ自動更新
                    if self.auto_update.get():
                        no_data_ids = [w['horse_id'] for w in no_data]
                        no_data_horses = [h for h in horses if h.get('horse_id') in no_data_ids]
                        self.insert_text(f"  自動データ取得中... ({len(no_data_horses)}頭)\n", "info")
                        try:
                            from smart_update_system import batch_update_race_horses
                            update_result = batch_update_race_horses(no_data_horses, self.df)
                            if update_result['updated'] > 0:
                                self.insert_text(f"  {update_result['updated']}頭の新規データを取得\n", "success")
                            else:
                                self.insert_text(f"  新規レースなし\n", "info")
                        except Exception as e:
                            self.insert_text(f"  自動更新エラー: {e}\n", "warning")
                    self.insert_text("\n")
            except ImportError:
                pass  # スマート更新モジュールがない場合はスキップ

            self.insert_text("[3] AI予測中...\n")

            # predict_core()で予測実行（current_date=None → datetime.now()使用）
            df_pred = self.predict_core(race_id, horses, race_info, has_odds)

            self.progress['value'] = 80
            self.root.update()

            # 結果を保存（印カラム含む）
            self.last_prediction = df_pred.copy()
            self.last_race_id = race_id
            self.last_race_info = race_info
            self.last_has_odds = has_odds
            self.export_button.config(state=tk.NORMAL)

            # レース情報をラベルに表示
            # race_idデコードで補完（スクレイピング時もrace_numなどを補う）
            decoded = self._decode_race_id(race_id)
            disp_track = race_info.get('track_name', '')
            if not disp_track and decoded:
                disp_track = decoded['track_name']
            disp_race_num = race_info.get('race_num') or (decoded['race_num'] if decoded else None)

            info_text = f"【{race_id}】"
            if disp_track:
                info_text += f"{disp_track}"
            if disp_race_num:
                info_text += f" {disp_race_num}R"
            if race_info.get('race_name'):
                info_text += f" {race_info['race_name']}"
            info_text += " |"
            if decoded:
                info_text += f" {decoded['kai']}回{decoded['day']}日"
            if race_info.get('course_type') and race_info.get('distance'):
                info_text += f" {race_info['course_type']}{race_info['distance']}m"
            if race_info.get('track_condition'):
                info_text += f" 馬場:{race_info['track_condition']}"
            if race_info.get('start_time'):
                info_text += f" 発走{race_info['start_time']}"

            # 印割り当て結果から本命等を取得
            mark_labels = {'◎': '本命', '○': '対抗', '▲': '単穴', '☆': '星'}
            info_text += "\n\n"
            mark_parts = []
            for mark_char, label in mark_labels.items():
                matched = df_pred[df_pred['印'].str.startswith(mark_char, na=False)]
                if len(matched) > 0:
                    h = matched.iloc[0]
                    part = f"{mark_char}{label}: {h['馬番']}番 {h['馬名']}"
                    if mark_char == '◎':
                        part += f" (勝率{h['勝率予測']*100:.1f}%)"
                    mark_parts.append(part)
            info_text += "  ".join(mark_parts)

            if not has_odds:
                info_text += "\n⚠ オッズ未発表（期待値計算不可）"

            self.race_info_label.config(text=info_text)

            # テーブルに結果を表示
            self.last_sort_column = '勝率予測'
            self.update_result_tree(df_pred)

            # 推奨馬券を表示
            self.update_recommended_bets(df_pred, has_odds)

            # 統計・分析ボタンを有効化
            self.stats_viz_button.config(state=tk.NORMAL)
            self.detail_analysis_button.config(state=tk.NORMAL)

            # 完了
            self.progress['value'] = 100
            self.status_label.config(text=f"予想完了 - {race_id} (列ヘッダークリックでソート)")

        except Exception as e:
            # エラー発生時
            import traceback
            error_msg = f"予想処理中にエラーが発生しました:\n{str(e)}\n\n{traceback.format_exc()}"
            self.insert_text(f"\n{'='*80}\n", "error")
            self.insert_text("エラー発生\n", "error")
            self.insert_text(f"{'='*80}\n", "error")
            self.insert_text(f"{error_msg}\n", "error")
            self.status_label.config(text=f"エラー - {race_id}")
            messagebox.showerror("予想エラー", f"予想処理中にエラーが発生しました:\n\n{str(e)}")

        finally:
            # 必ず実行：ボタンを有効化
            self.predict_button.config(state=tk.NORMAL)
            # 進行バーが中途半端な場合は0にリセット
            if self.progress['value'] < 100 and self.progress['value'] > 0:
                self.progress['value'] = 0

    def _assign_marks(self, df_pred, has_odds):
        """役割別の印を割り当て、'印'カラムを追加して返す"""
        marks = {}  # 馬番 → 印文字列

        # 勝率予測順にソート済み前提
        sorted_by_win = df_pred.sort_values('勝率予測', ascending=False)

        # ◎: 勝率1位
        honmei = sorted_by_win.iloc[0]
        marks[honmei['馬番']] = '◎'

        # ○: 勝率2位
        if len(sorted_by_win) > 1:
            taikou = sorted_by_win.iloc[1]
            marks[taikou['馬番']] = '○'

        assigned = set(marks.keys())

        # ▲: 勝率予測3位（◎○に勝てる能力がある馬）
        if len(sorted_by_win) > 2:
            third = sorted_by_win.iloc[2]
            if third['馬番'] not in assigned:
                marks[third['馬番']] = '▲'
                assigned.add(third['馬番'])

        if has_odds and (df_pred['オッズ'] > 0).any():
            # ☆: バリュー > 0 かつ オッズ >= 10.0（大穴バリュー馬）
            remaining = df_pred[~df_pred['馬番'].isin(assigned)]
            star_cands = remaining[(remaining['バリュー'] > 0) & (remaining['オッズ'] >= 10.0)]
            if len(star_cands) > 0:
                star = star_cands.sort_values('バリュー', ascending=False).iloc[0]
                marks[star['馬番']] = '☆'
                assigned.add(star['馬番'])

        # △: ◎○▲☆以外で複勝予測上位（2・3着に来る可能性がある馬、最大2頭）
        remaining = df_pred[~df_pred['馬番'].isin(assigned)]
        renka_cands = remaining.sort_values('複勝予測', ascending=False)
        for _, r in renka_cands.head(2).iterrows():
            if r['複勝予測'] >= 0.20:
                marks[r['馬番']] = '△'
                assigned.add(r['馬番'])

        # 注: 残りで複勝予測が一定以上（最大2頭）
        remaining = df_pred[~df_pred['馬番'].isin(assigned)]
        note_threshold = 0.25 if has_odds else 0.20
        note_cands = remaining[remaining['複勝予測'] >= note_threshold].sort_values('複勝予測', ascending=False)
        for _, r in note_cands.head(2).iterrows():
            marks[r['馬番']] = '注'
            assigned.add(r['馬番'])

        # 信頼度チェック: 低信頼なら「?」付加
        def apply_mark(row):
            m = marks.get(row['馬番'], '')
            if m and row.get('特徴量信頼度', 1.0) < 0.25:
                m += '?'
            return m

        df_pred['印'] = df_pred.apply(apply_mark, axis=1)
        return df_pred

    # ── Phase R10: 調教タイム特徴量 ────────────────────────────────

    _TRAINING_FINISH_MAP = {
        '一杯': 0.0, '強め': 1.0, '末強め': 2.0, '馬也': 3.0,
        '直強め': 2.0, '外強め': 1.0, '内強め': 1.0,
    }
    _TRAINING_COURSE_MAP = {
        '坂路': 0.0, '美坂': 0.0, '栗坂': 0.0, '南坂': 0.0,
        'Ｗ': 1.0, '美Ｗ': 1.0, '栗Ｗ': 1.0, '南Ｗ': 1.0,
        '芝': 2.0, '美芝': 2.0, '栗芝': 2.0,
        'ダ': 3.0, '美ダ': 3.0, '栗ダ': 3.0,
    }

    @staticmethod
    def _parse_training_laps(laps_str: str):
        """
        タイムラップ文字列から 3Fタイム と 上がり1Fタイム を抽出。
        Returns (t3f, t1f) のタプル。取得不能時は (None, None)。
        """
        import re as _re
        if not isinstance(laps_str, str) or not laps_str.strip():
            return None, None
        nums = _re.findall(r'\d+\.\d+', laps_str.strip())
        if len(nums) < 4:
            return None, None
        try:
            all_vals = [float(x) for x in nums]
            cumulative = [all_vals[i] for i in range(0, len(all_vals), 2)]
            if len(cumulative) < 2:
                return None, None
            last1f = cumulative[-1]
            last3f = cumulative[-3] if len(cumulative) >= 3 else None
            if last1f < 10 or last1f > 20:
                last1f = None
            if last3f is not None and (last3f < 30 or last3f > 70):
                last3f = None
            return last3f, last1f
        except Exception:
            return None, None

    @classmethod
    def _classify_training_course(cls, course: str) -> float:
        if not isinstance(course, str):
            return 1.0  # 不明→W相当
        for key, val in cls._TRAINING_COURSE_MAP.items():
            if key in course:
                return val
        return 1.0

    @classmethod
    def _classify_training_finish(cls, finish: str) -> float:
        if not isinstance(finish, str):
            return 1.0  # 不明→強め相当
        for key, val in cls._TRAINING_FINISH_MAP.items():
            if key in finish:
                return val
        return 1.0

    def _add_training_features_for_race(
        self, race_id: str, all_feat_df, horses: list
    ):
        """
        oikiri.html?race_id=...&type=2 をスクレイプして
        調教タイム特徴量を all_feat_df に付与する（Phase R10対応）。
        失敗時はデフォルト値（0.0 / 1.0）のまま返す。
        """
        DEFAULT_3F_REL = 0.0
        DEFAULT_1F_REL = 0.0
        DEFAULT_FINISH = 1.0
        DEFAULT_COURSE = 1.0

        df = all_feat_df.copy()
        for col, default in [
            ('training_3f_relative',  DEFAULT_3F_REL),
            ('training_last1f_rel',   DEFAULT_1F_REL),
            ('training_finish_score', DEFAULT_FINISH),
            ('training_course_type',  DEFAULT_COURSE),
        ]:
            if col not in df.columns:
                df[col] = default

        try:
            import requests as _req
            from bs4 import BeautifulSoup as _BS

            url = (f'https://race.netkeiba.com/race/oikiri.html'
                   f'?race_id={race_id}&type=2')
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                )
            }
            resp = _req.get(url, headers=headers, timeout=10)
            if resp.status_code != 200:
                return df
            resp.encoding = 'euc-jp'
            soup = _BS(resp.text, 'html.parser')
            table = soup.find('table')
            if not table:
                return df

            rows_data = []
            for row in table.find_all('tr')[1:]:
                cols = [c.get_text(strip=True) for c in row.find_all('td')]
                if len(cols) < 13:
                    continue
                umaban = str(cols[1]).strip().replace('.0', '')
                t3f, t1f = self._parse_training_laps(cols[8])
                rows_data.append({
                    'umaban':        umaban,
                    'course_str':    cols[5],
                    'baba':          cols[6],
                    't3f':           t3f,
                    't1f':           t1f,
                    'course_type':   self._classify_training_course(cols[5]),
                    'finish_score':  self._classify_training_finish(cols[10]),
                })

            if not rows_data:
                return df

            import pandas as _pd
            tr = _pd.DataFrame(rows_data)

            # 同コース・同馬場グループ内での相対タイム偏差
            def _rel(series):
                med = series.median()
                return series - med if not _pd.isna(med) else series

            tr['t3f_rel'] = tr.groupby(['course_str', 'baba'])['t3f'].transform(_rel)
            tr['t1f_rel'] = tr.groupby(['course_str', 'baba'])['t1f'].transform(_rel)

            # 同一馬番の最初の行を使用
            tr_latest = tr.groupby('umaban').first().reset_index()

            for i, horse in enumerate(horses):
                umaban = str(horse.get('馬番', horse.get('umaban', ''))).strip()
                umaban = umaban.replace('.0', '').replace(' ', '')
                row = tr_latest[tr_latest['umaban'] == umaban]
                if row.empty:
                    continue
                r = row.iloc[0]
                if _pd.notna(r['t3f_rel']):
                    df.at[i, 'training_3f_relative'] = float(r['t3f_rel'])
                if _pd.notna(r['t1f_rel']):
                    df.at[i, 'training_last1f_rel'] = float(r['t1f_rel'])
                df.at[i, 'training_course_type']  = float(r['course_type'])
                df.at[i, 'training_finish_score'] = float(r['finish_score'])

            n_covered = (df['training_3f_relative'] != DEFAULT_3F_REL).sum()
            print(f"  調教データ取得: {n_covered}/{len(horses)}頭分")

        except Exception as e:
            print(f"  調教データ取得失敗（デフォルト使用）: {e}")

        return df

    # ────────────────────────────────────────────────────────────────

    @staticmethod
    def _add_relative_features_for_race(feat_df: pd.DataFrame) -> pd.DataFrame:
        """レース内相対特徴量を計算して追加（Phase R4対応）"""
        df = feat_df.copy()
        n = len(df)
        df['field_size'] = float(n)

        SPECS = [
            ('total_win_rate',   'field_win_rate_rank', False),
            ('jockey_win_rate',  'field_jockey_rank',   False),
            ('trainer_win_rate', 'field_trainer_rank',  False),
            ('total_earnings',   'field_earnings_rank', False),
            ('avg_last_3f',      'field_last3f_rank',   True),
            ('avg_diff_seconds', 'field_diff_rank',     True),
        ]

        for src_col, out_col, ascending in SPECS:
            if src_col not in df.columns:
                df[out_col] = 0.5
                continue
            filled = df[src_col].fillna(
                df[src_col].median() if not df[src_col].isna().all() else 0.0
            )
            raw_rank = filled.rank(method='min', ascending=ascending)
            df[out_col] = ((n - raw_rank) / max(n - 1, 1)).clip(0.0, 1.0).fillna(0.5)

        # Phase R5: field_escape_count, field_pace_advantage
        if 'running_style_v2' in df.columns:
            escape_count = int(df['running_style_v2'].isin([1, 2]).sum())
            df['field_escape_count'] = float(escape_count)

            def _pace_adv(style, ec):
                s = int(style) if not pd.isna(style) else 3
                if s in (1, 2):
                    return max(0.0, 1.0 - (ec - 1) * 0.15)
                if s in (3, 4):
                    return min(1.0, 0.3 + (ec - 2) * 0.1)
                return 0.5

            df['field_pace_advantage'] = [
                _pace_adv(s, escape_count) for s in df['running_style_v2']
            ]
        else:
            df['field_escape_count']   = 3.0
            df['field_pace_advantage'] = 0.5

        # Phase R7: field_waku_rank（枠番バイアスのレース内相対ランク）
        if 'waku_win_rate' in df.columns:
            filled_wwr = df['waku_win_rate'].fillna(0.065)
            raw_rank   = filled_wwr.rank(method='min', ascending=True)
            df['field_waku_rank'] = ((n - raw_rank) / max(n - 1, 1)).clip(0.0, 1.0).fillna(0.5)
        else:
            df['field_waku_rank'] = 0.5

        return df

    def predict_core(self, race_id, horses, race_info, has_odds, current_date=None):
        """
        UI非依存の予測コアロジック。GUIとバックテストの両方から呼ばれる。

        Args:
            race_id: レースID文字列
            horses: get_race_from_database()等が返す馬リスト
            race_info: レース情報dict
            has_odds: オッズ有無
            current_date: 'YYYY-MM-DD'文字列。Noneならdatetime.now()を使用。
                          バックテスト時はレース日付を渡してリーケージ防止。
        Returns:
            pd.DataFrame: 印付きdf_pred（'馬番','馬名','勝率予測','複勝予測','印' 等全カラム）
        """
        # pd.to_datetime互換のISO形式
        if current_date is None:
            current_date = datetime.now().strftime('%Y-%m-%d')

        # モデル特徴量リスト
        if self.model_features is None:
            raise ValueError("モデル特徴量リストが読み込まれていません")
        model_features = self.model_features

        # 出走馬のhorse_idリスト（V3ペース予測用）
        race_horses_ids = []
        for h in horses:
            hid = h.get('horse_id')
            if hid:
                try:
                    race_horses_ids.append(float(hid))
                except (ValueError, TypeError):
                    pass

        # ── Pass 1: 全馬の基本特徴量を収集 ─────────────────────────────
        all_feats = []   # features dict per horse
        all_meta  = []   # (horse, horse_data, horse_id) per horse

        for i, horse in enumerate(horses):
            horse_id  = horse['horse_id']
            horse_data = pd.DataFrame()

            if horse_id:
                try:
                    horse_id_num = float(horse_id)
                except Exception:
                    horse_id_num = None
                    print(f"  NG horse_id変換失敗 [{horse['馬名']}]: {horse_id}")

                if horse_id_num:
                    try:
                        race_id_int = int(race_id)
                        horse_data = self.df[(self.df['horse_id'] == horse_id_num) & (self.df['race_id'] != race_id_int)]
                    except Exception:
                        horse_data = self.df[self.df['horse_id'] == horse_id_num]

                    if len(horse_data) > 0 and 'date' in horse_data.columns:
                        def normalize_date(date_str):
                            """日付を比較可能な形式に正規化"""
                            import re
                            s = str(date_str)
                            match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', s)
                            if match:
                                return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
                            match = re.search(r'(\d{4}-\d{2}-\d{2})', s)
                            if match:
                                return match.group(1)
                            return s
                        horse_data = horse_data.copy()
                        horse_data['date_normalized'] = horse_data['date'].apply(normalize_date)

                        if current_date:
                            horse_data_dates = pd.to_datetime(horse_data['date_normalized'], errors='coerce')
                            cutoff = pd.to_datetime(current_date)
                            horse_data = horse_data[horse_data_dates <= cutoff]

                        horse_data = horse_data.sort_values('date_normalized', ascending=True)

                if len(horse_data) > 0:
                    try:
                        waku_num = int(horse['枠番'])
                    except Exception:
                        waku_num = None
                    race_info['waku'] = waku_num

                    try:
                        features = calculate_horse_features_safe(
                            horse_id, self.df, current_date, self.sire_stats,
                            self.trainer_jockey_stats,
                            horse.get('調教師'), horse.get('騎手'),
                            race_info.get('track_name'),
                            race_info.get('distance'),
                            race_info.get('course_type'),
                            race_info.get('track_condition'),
                            waku_num,
                            race_id=race_id,
                            horse_kiryou=horse.get('斤量'),
                            horse_seire=horse.get('性齢'),
                            horse_weight_str=horse.get('馬体重'),
                        )
                    except Exception as e:
                        print(f"特徴量計算エラー [{horse['馬名']}]: {e}")
                        import traceback
                        traceback.print_exc()
                        features = None

                    if features:
                        non_zero_count = sum(1 for v in features.values() if v != 0 and v != 0.0)
                        feature_reliability = non_zero_count / len(features)
                        print(f"  OK 特徴量計算成功 [{horse['馬名']}]: {len(features)}個 (有効: {non_zero_count}個, 信頼度: {feature_reliability*100:.0f}%)")
                    else:
                        print(f"  NG 特徴量がNone [{horse['馬名']}]")
                else:
                    print(f"  NG 馬データなし [{horse['馬名']}] (horse_id: {horse_id})")
                    features = None
            else:
                print(f"  NG horse_id取得失敗 [{horse['馬名']}]")
                features = None

            if features is None:
                print(f"  デフォルト値使用 [{horse['馬名']}]")
                features = {feat: 0 for feat in model_features}
                features['total_starts'] = 10
                features['total_win_rate'] = 0.1
            else:
                for feat in model_features:
                    if feat not in features:
                        features[feat] = 0

            all_feats.append(features)
            all_meta.append((horse, horse_data, horse_id))

        # ── Phase R6 レース単位特徴量を計算 ────────────────────────────
        r6_race_features = {}
        if any(f in model_features for f in ['daily_front_bias','daily_prior_races',
                                              'horse_style_vs_bias','is_rainy','is_sunny']):
            try:
                rid_str = str(race_id).strip()
                day_key  = rid_str[:10]
                race_no  = int(rid_str[10:12]) if len(rid_str) >= 12 else 0

                # 日次バイアス: 同日同コース前レースの勝ち馬1角通過順平均
                import re as _re
                def _parse_fc(s):
                    if pd.isna(s): return np.nan
                    nums = [int(p) for p in _re.split(r'[-\s]', str(s).strip()) if p.isdigit()]
                    return float(nums[0]) if nums else np.nan

                # self.df から同日前レースのデータを取得
                _prior_bias = np.nan
                _prior_cnt  = 0
                if hasattr(self, 'df') and self.df is not None and len(self.df) > 0:
                    _df = self.df
                    _rid_col = _df['race_id'].astype(str).str.strip()
                    _same_day = _rid_col.str[:10] == day_key
                    _prior    = _rid_col[_same_day].apply(lambda x: int(x[10:12]) if len(x) >= 12 else 99) < race_no
                    _prior_df = _df[_same_day & _prior.values]
                    if len(_prior_df) > 0 and 'rank' in _prior_df.columns and '通過' in _prior_df.columns:
                        _prior_df = _prior_df.copy()
                        _prior_df['_rank_n'] = pd.to_numeric(_prior_df['rank'], errors='coerce')
                        _winners = _prior_df[_prior_df['_rank_n'] == 1]
                        _fc_vals = [_parse_fc(s) for s in _winners['通過']]
                        _fc_vals = [v for v in _fc_vals if not np.isnan(v)]
                        if _fc_vals:
                            _prior_bias = float(np.mean(_fc_vals))
                            _prior_cnt  = len(_fc_vals)

                r6_race_features['daily_front_bias']  = _prior_bias if not np.isnan(_prior_bias) else 4.57
                r6_race_features['daily_prior_races'] = float(_prior_cnt)

                # 天候フラグ
                _weather = race_info.get('weather', '') if race_info else ''
                r6_race_features['is_rainy'] = 1 if _weather in ['雨', '小雨'] else 0
                r6_race_features['is_sunny'] = 1 if _weather == '晴'         else 0

            except Exception as _e:
                print(f'  [R6] race-level特徴量計算エラー: {_e}')
                r6_race_features = {
                    'daily_front_bias': 4.57, 'daily_prior_races': 0.0,
                    'is_rainy': 0, 'is_sunny': 0,
                }

        # R6 特徴量を各馬に付与 + horse_style_vs_bias を計算
        for feats in all_feats:
            for k, v in r6_race_features.items():
                feats[k] = v
            if 'horse_style_vs_bias' in model_features:
                _fc  = feats.get('avg_first_corner_fixed', 5.0)
                _db  = feats.get('daily_front_bias', 4.57)
                feats['horse_style_vs_bias'] = float(_fc) - float(_db)

        # ── レース内相対特徴量を付与（R4モデル対応） ──────────────────
        # model_features に field_* 列が含まれている場合のみ計算
        all_feat_df = pd.DataFrame(all_feats).reindex(columns=model_features).fillna(0)
        if any(f.startswith('field_') for f in model_features):
            all_feat_df = self._add_relative_features_for_race(all_feat_df)

        # ── 調教タイム特徴量を付与（R10モデル対応） ──────────────────
        _r10_feats = {'training_3f_relative', 'training_last1f_rel',
                      'training_finish_score', 'training_course_type'}
        if _r10_feats & set(model_features):
            all_feat_df = self._add_training_features_for_race(
                race_id, all_feat_df, horses)

        all_feat_df = all_feat_df.reindex(columns=model_features).fillna(0)

        # ── Pass 2: 予測 & 結果組み立て ────────────────────────────────
        predictions = []
        for i, (horse, horse_data, horse_id) in enumerate(all_meta):
            feat_row = all_feat_df.iloc[[i]]

            pred_win_proba  = float(self.model_win.predict(feat_row)[0])
            pred_top3_proba = float(self.model_place.predict(feat_row)[0])

            # SHAP値計算（予測根拠 TOP5）
            shap_top5 = []
            if SHAP_AVAILABLE and self.shap_explainer_win is not None:
                try:
                    sv = self.shap_explainer_win.shap_values(feat_row)[0]
                    pairs = sorted(zip(feat_row.columns.tolist(), sv),
                                   key=lambda x: abs(x[1]), reverse=True)[:5]
                    shap_top5 = pairs
                except Exception as e:
                    shap_top5 = []
                    print(f"SHAP計算エラー({horse.get('馬名','')}): {e}")

            odds = horse.get('単勝オッズ', 0)
            expected_value = pred_win_proba * odds if odds > 0 else 0
            value = pred_win_proba - (1.0 / odds) if odds > 0 else 0

            stats_summary = ""
            if horse_id and len(horse_data) > 0:
                total_races = len(horse_data)
                wins = (horse_data['rank'] == 1).sum()
                top3 = (horse_data['rank'] <= 3).sum()
                recent_5 = horse_data.tail(5)
                recent_ranks = [int(r) for r in recent_5['rank'].tolist() if pd.notna(r)]
                recent_ranks = recent_ranks[::-1]
                stats_summary = f"{total_races}戦{wins}勝{top3}着内 直近:{recent_ranks}"

            feat_non_zero  = (feat_row.iloc[0] != 0).sum()
            feat_reliability = feat_non_zero / len(model_features)
            is_sweet_spot  = (0.15 <= pred_win_proba < 0.20)

            predictions.append({
                '馬番': horse['馬番'],
                '枠番': horse.get('枠番', ''),
                '馬名': horse['馬名'],
                'horse_id': horse['horse_id'],
                '性齢': horse.get('性齢', ''),
                '斤量': horse.get('斤量', ''),
                '騎手': horse['騎手'],
                '馬体重': horse.get('馬体重', ''),
                'オッズ': horse.get('単勝オッズ', 0.0),
                '勝率予測': pred_win_proba,
                '複勝予測': pred_top3_proba,
                '期待値': expected_value,
                'バリュー': value,
                'データあり': horse_id is not None,
                '過去成績': stats_summary,
                '実際の着順': horse.get('実際の着順'),
                '特徴量信頼度': feat_reliability,
                '回収率優秀': is_sweet_spot,
                'shap_top5': shap_top5,
            })

        # 予測結果をDataFrameに
        df_pred = pd.DataFrame(predictions)
        df_pred = df_pred.sort_values('勝率予測', ascending=False)

        # 印の割り当て（役割別）
        df_pred = self._assign_marks(df_pred, has_odds)

        return df_pred

    @staticmethod
    def get_recommended_bet_targets(df_pred, has_odds):
        """
        印ベースの推奨馬券ターゲットを純粋関数として返す。
        GUIとバックテストの両方から呼ばれる。

        Returns:
            dict: 推奨馬券情報
        """
        if df_pred is None or len(df_pred) == 0:
            return None

        # 印から各役割の馬を取得
        def get_mark_horse(mark_char):
            matched = df_pred[df_pred['印'].str.startswith(mark_char, na=False)]
            return matched.iloc[0] if len(matched) > 0 else None

        def get_mark_horses(mark_char):
            return df_pred[df_pred['印'].str.startswith(mark_char, na=False)]

        honmei = get_mark_horse('◎')
        taikou = get_mark_horse('○')
        tanana = get_mark_horse('▲')
        star   = get_mark_horse('☆')
        renka  = get_mark_horses('△')

        if honmei is None:
            return None

        win_proba = honmei['勝率予測']

        # 紐馬候補を集める（○▲△から、最大3頭）
        himo_list = []
        if taikou is not None:
            himo_list.append(int(taikou['馬番']))
        if tanana is not None:
            himo_list.append(int(tanana['馬番']))
        for _, r in renka.head(2).iterrows():
            if int(r['馬番']) not in himo_list:
                himo_list.append(int(r['馬番']))
        himo_list = himo_list[:3]

        # 3連複/3連単用の3着候補
        uma1 = int(honmei['馬番'])
        uma2 = int(taikou['馬番']) if taikou is not None else None
        if tanana is not None:
            uma3 = int(tanana['馬番'])
        else:
            # ▲がない場合は勝率3位にフォールバック
            sorted_by_win = df_pred.sort_values('勝率予測', ascending=False)
            uma3 = None
            for _, r in sorted_by_win.iterrows():
                bn = int(r['馬番'])
                if bn != uma1 and (uma2 is None or bn != uma2):
                    uma3 = bn
                    break

        # 複勝率活用: ワイド・3連複用の馬番（複勝率上位を使用）
        # テスト結果: ワイド +4.8pt、3連複 +3.2pt の改善
        if '複勝予測' in df_pred.columns:
            sorted_by_place = df_pred.sort_values('複勝予測', ascending=False)

            # ワイド用: 複勝率上位2頭
            wide_horses = []
            for _, r in sorted_by_place.head(2).iterrows():
                wide_horses.append(int(r['馬番']))
            wide_uma1 = wide_horses[0] if len(wide_horses) > 0 else uma1
            wide_uma2 = wide_horses[1] if len(wide_horses) > 1 else uma2

            # 3連複用: 複勝率上位3頭
            sanren_horses = []
            for _, r in sorted_by_place.head(3).iterrows():
                sanren_horses.append(int(r['馬番']))
            sanren_uma1 = sanren_horses[0] if len(sanren_horses) > 0 else uma1
            sanren_uma2 = sanren_horses[1] if len(sanren_horses) > 1 else uma2
            sanren_uma3 = sanren_horses[2] if len(sanren_horses) > 2 else uma3
        else:
            # 複勝予測がない場合は従来通り（勝率ベース）
            wide_uma1, wide_uma2 = uma1, uma2
            sanren_uma1, sanren_uma2, sanren_uma3 = uma1, uma2, uma3

        # 勝率帯判定
        if win_proba >= 0.50:
            bet_pattern = '50+'
        elif win_proba >= 0.40:
            bet_pattern = '40-50'
        elif win_proba >= 0.30:
            bet_pattern = '30-40'
        elif win_proba >= 0.20:
            bet_pattern = '20-30'
        elif win_proba >= 0.10:
            bet_pattern = '10-20'
        else:
            bet_pattern = '<10'

        # 買い目構築
        bets = {
            'tansho': uma1,  # 単勝: 勝率1位（現行維持）
            'umaren': (uma1, uma2) if uma2 else None,  # 馬連: 勝率上位2頭
            'wide': (wide_uma1, wide_uma2) if wide_uma2 else None,  # ワイド: 複勝率上位2頭
            'sanrenpuku': (sanren_uma1, sanren_uma2, sanren_uma3) if sanren_uma2 and sanren_uma3 else None,  # 3連複: 複勝率上位3頭
            'sanrentan_box': (sanren_uma1, sanren_uma2, sanren_uma3) if sanren_uma2 and sanren_uma3 else None,  # 3連単BOX: 複勝率上位3頭
        }

        return {
            'honmei': uma1,
            'taikou': uma2,
            'tanana': uma3,
            'star': int(star['馬番']) if star is not None else None,
            'renka': [int(r['馬番']) for _, r in renka.iterrows()],
            'himo_list': himo_list,
            'win_proba': win_proba,
            'bet_pattern': bet_pattern,
            'bets': bets,
        }

    def _old_display_code_removed(self):
        """旧表示コード（削除済み）"""
        # 以下は旧コード（使用されていない）
        pass
        """
        for i, (idx, row) in enumerate(df_pred.iterrows(), 1):
            # 順位マーカー
            if i == 1:
                rank_mark = "◎"
                tag = "highlight"
            elif i == 2:
                rank_mark = "○"
                tag = "highlight"
            elif i == 3:
                rank_mark = "▲"
                tag = "highlight"
            elif i <= 5:
                rank_mark = "△"
                tag = None
            else:
                rank_mark = " "
                tag = None

            data_status = "✓" if row['データあり'] else "✗"

            # 過去レースの場合、実際の着順も表示
            answer_text = ""
            answer_tag = tag
            if show_answer and pd.notna(row['実際の着順']):
                actual_rank = int(row['実際の着順'])
                if actual_rank == 1:
                    answer_text = f" 【実際: 1着】"
                    answer_tag = "success"
                elif actual_rank <= 3:
                    answer_text = f" 【実際: {actual_rank}着】"
                    answer_tag = "success"
                elif actual_rank <= 5:
                    answer_text = f" 【実際: {actual_rank}着】"
                else:
                    answer_text = f" 【実際: {actual_rank}着】"

            # 馬番・馬名行
            self.result_text.insert(tk.END,
                f"{rank_mark} {i:2}位 ", answer_tag if answer_text else tag)
            self.result_text.insert(tk.END,
                f"{row['馬番']:>2}番 {row['馬名']:<18} 騎手:{row['騎手']:<10} {data_status}", answer_tag if answer_text else tag)
            if answer_text:
                self.result_text.insert(tk.END, answer_text, answer_tag)
            self.result_text.insert(tk.END, "\n", tag)

            # 予測データ行
            ev_marker = ""
            if row['期待値'] >= 2.0:
                ev_marker = " ★推奨★"
            elif row['期待値'] >= 1.5:
                ev_marker = " ☆注目☆"

            # オッズと期待値の表示（オッズがない場合は「未発表」）
            if row['オッズ'] > 0:
                odds_text = f"{row['オッズ']:6.1f}倍"
                ev_text = f"{row['期待値']:5.2f}"
            else:
                odds_text = "  未発表"
                ev_text = "  ---"

            self.result_text.insert(tk.END,
                f"      勝率: {row['勝率予測']*100:5.1f}%  複勝: {row['複勝予測']*100:5.1f}%  "
                f"オッズ: {odds_text}  期待値: {ev_text}{ev_marker}\n",
                "success" if ev_marker else tag)

            # 過去成績がある場合は表示
            if row['過去成績']:
                self.result_text.insert(tk.END, f"      過去: {row['過去成績']}\n", tag)

            self.result_text.insert(tk.END, "\n")

        # 推奨馬券
        self.insert_text(f"{'='*80}\n", "header")
        self.insert_text(" 推奨馬券\n", "header")
        self.insert_text(f"{'='*80}\n\n", "header")

        # 本命
        top1 = df_pred.iloc[0]
        self.insert_text(f"◎ 本命: {top1['馬番']}番 {top1['馬名']} "
                        f"(勝率予測: {top1['勝率予測']*100:.1f}%)\n", "success")

        # 対抗
        if len(df_pred) > 1:
            top2 = df_pred.iloc[1]
            self.insert_text(f"○ 対抗: {top2['馬番']}番 {top2['馬名']} "
                           f"(勝率予測: {top2['勝率予測']*100:.1f}%)\n", "success")

        # 単穴
        if len(df_pred) > 2:
            top3 = df_pred.iloc[2]
            self.insert_text(f"▲ 単穴: {top3['馬番']}番 {top3['馬名']} "
                           f"(勝率予測: {top3['勝率予測']*100:.1f}%)\n", "success")

        self.insert_text(f"\n推奨馬券:\n", "header")
        self.insert_text(f"  単勝: {top1['馬番']}番\n")

        if len(df_pred) >= 2:
            self.insert_text(f"  馬連: {top1['馬番']}-{top2['馬番']}\n")

        if len(df_pred) >= 3:
            self.insert_text(f"  3連複: {top1['馬番']}-{top2['馬番']}-{top3['馬番']}\n")

        # 期待値ベース推奨（オッズがある場合のみ）
        if has_odds:
            high_ev = df_pred[df_pred['期待値'] >= 1.2]
            if len(high_ev) > 0:
                self.insert_text(f"\n期待値1.2以上の馬:\n", "warning")
                for _, row in high_ev.iterrows():
                    self.insert_text(f"  {row['馬番']}番 {row['馬名']}: 期待値 {row['期待値']:.2f}\n", "warning")

            very_high_ev = df_pred[df_pred['期待値'] >= 2.0]
            if len(very_high_ev) > 0:
                self.insert_text(f"\n期待値2.0以上の馬（推奨！）:\n", "success")
                for _, row in very_high_ev.iterrows():
                    self.insert_text(f"  {row['馬番']}番 {row['馬名']}: 期待値 {row['期待値']:.2f} "
                                  f"(勝率予測: {row['勝率予測']*100:.1f}%)\n", "success")
        else:
            self.insert_text(f"\n⚠ オッズ未発表のため、期待値ベースの推奨はスキップされました\n", "info")
            self.insert_text(f"  オッズ発表後に再度予測を実行してください\n", "info")

        # データ不足の警告
        no_data_count = df_pred[~df_pred['データあり']].shape[0]
        if no_data_count > 0:
            self.insert_text(f"\n⚠ 注意事項:\n", "error")
            self.insert_text(f"  {no_data_count}頭の馬は過去データが不足しています\n", "error")
            self.insert_text(f"  これらの馬の予測精度は低い可能性があります\n", "error")
            no_data_horses = df_pred[~df_pred['データあり']]
            for _, row in no_data_horses.iterrows():
                self.insert_text(f"    - {row['馬番']}番 {row['馬名']}\n", "error")

        # 過去レースの場合は的中判定
        if show_answer:
            self.insert_text(f"\n{'='*80}\n", "header")
            self.insert_text(" 答え合わせ\n", "header")
            self.insert_text(f"{'='*80}\n\n", "header")

            # 実際の1着馬を取得
            winner = df_pred[df_pred['実際の着順'] == 1]
            if len(winner) > 0:
                winner_row = winner.iloc[0]

                # AI予測での順位を正しく取得（reset_indexして位置を確認）
                df_pred_reset = df_pred.reset_index(drop=True)
                predicted_rank = None
                for idx, row in df_pred_reset.iterrows():
                    if row['馬番'] == winner_row['馬番']:
                        predicted_rank = idx + 1
                        break

                self.insert_text(f"実際の勝ち馬: {winner_row['馬番']}番 {winner_row['馬名']} (オッズ: {winner_row['オッズ']:.1f}倍)\n")
                self.insert_text(f"AI予測順位: {predicted_rank}位 (勝率予測: {winner_row['勝率予測']*100:.1f}%)\n")

                if predicted_rank == 1:
                    self.insert_text("→ 的中！本命が勝ちました\n", "success")
                elif predicted_rank <= 3:
                    self.insert_text("→ 上位3頭に入っていました\n", "success")
                elif predicted_rank <= 5:
                    self.insert_text("→ 上位5頭に入っていました\n", "warning")
                else:
                    self.insert_text(f"→ 予想外の結果でした\n", "warning")

                # 期待値チェック
                if winner_row['期待値'] >= 2.0:
                    self.insert_text(f"\n期待値は {winner_row['期待値']:.2f} でした（2.0以上の推奨馬）\n", "success")
                elif winner_row['期待値'] >= 1.2:
                    self.insert_text(f"\n期待値は {winner_row['期待値']:.2f} でした（1.2以上）\n", "warning")

        """
        # コメント終了 - 旧コードここまで

    def insert_text(self, text, tag=None):
        """レース情報ラベルにテキストを追加"""
        # メッセージをrace_info_labelに追加
        current = self.race_info_label.cget("text")
        if current == "レース情報: 未取得":
            current = ""
        self.race_info_label.config(text=current + text)
        self.root.update()

    def update_race_data(self):
        """レベル2: このレースの出走馬のデータを一括更新"""
        race_id = self.race_id_entry.get().strip()

        if not race_id:
            messagebox.showwarning("警告", "レースIDを入力してください")
            return

        self.insert_text(f"\n{'='*80}\n", "header")
        self.insert_text(" レース単位データ更新\n", "header")
        self.insert_text(f"{'='*80}\n\n", "header")

        self.update_button.config(state=tk.DISABLED)
        self.status_label.config(text="データ更新中...")

        try:
            # レース情報を取得
            self.insert_text(f"[1] レース情報取得中... (ID: {race_id})\n")

            horses, race_info = self.scrape_shutuba(race_id)

            if not horses or (race_info and race_info.get('error')):
                horses, race_info = self.scrape_race_result(race_id)

            if not horses or (race_info and race_info.get('error')):
                horses, race_info = self.get_race_from_database(race_id)

            if not horses:
                self.insert_text("レースが見つかりませんでした\n", "error")
                self.update_button.config(state=tk.NORMAL)
                return

            self.insert_text(f"  {len(horses)}頭の出走馬を確認\n", "success")
            self.insert_text("\n")

            # レベル2更新を実行
            from smart_update_system import batch_update_race_horses

            self.insert_text("[2] 一括データ更新開始...\n")
            result = batch_update_race_horses(horses, self.df)

            self.insert_text(f"\n更新完了!\n", "success")
            self.insert_text(f"  成功: {result['updated']}頭\n", "success")
            self.insert_text(f"  新規なし: {result['failed']}頭\n", "info")

            if result['updated'] > 0:
                self.insert_text(f"\n💡 注意: データベースへの反映は手動で行ってください\n", "warning")

            messagebox.showinfo("完了", f"データ更新完了\n成功: {result['updated']}頭")

        except Exception as e:
            self.insert_text(f"\nエラー: {e}\n", "error")
            messagebox.showerror("エラー", f"データ更新に失敗しました:\n{e}")

        finally:
            self.update_button.config(state=tk.NORMAL)
            self.status_label.config(text="待機中")

    def export_results(self):
        """予測結果をCSVエクスポート"""
        if self.last_prediction is None:
            messagebox.showwarning("警告", "エクスポートする予測結果がありません")
            return

        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"prediction_{self.last_race_id}_{timestamp}.csv"

            self.last_prediction.to_csv(filename, index=False, encoding='utf-8-sig')

            messagebox.showinfo("成功", f"予測結果を保存しました:\n{filename}")
            self.status_label.config(text=f"CSV保存完了: {filename}")
        except Exception as e:
            messagebox.showerror("エラー", f"CSV保存に失敗しました:\n{e}")

    # ================================================================
    # WIN5 予測用メソッド群
    # ================================================================

    def _scrape_win5_race_ids(self, kaisai_date):
        """WIN5対象レースIDを自動取得

        WIN5ルール: 当日の最も発走時刻が遅い11Rを最終レグ(5レグ目)とし、
        それより前に発走する4レースを加えた計5レースが対象。
        発走時刻順に並べて返す。

        Args:
            kaisai_date: 'YYYYMMDD'形式の日付文字列

        Returns:
            list[str]: 5件のrace_id（発走時刻順）。取得失敗時は空リスト。
        """
        # race_list.html はJS動的読み込みのため、実データがある race_list_sub.html を使う
        url = f"https://race.netkeiba.com/top/race_list_sub.html?kaisai_date={kaisai_date}"
        print(f"[WIN5] レースリスト取得: {url}")

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            response.encoding = response.apparent_encoding

            if response.status_code != 200:
                print(f"[WIN5] HTTP error: {response.status_code}")
                return []

            soup = BeautifulSoup(response.text, 'html.parser')

            # 全レースのrace_id・発走時刻・レース番号を抽出
            all_races = []
            seen_ids = set()
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                m = re.search(r'race_id=(\d{12})', href)
                if not m:
                    continue
                rid = m.group(1)
                if rid in seen_ids:
                    continue
                seen_ids.add(rid)

                # aタグのテキストから発走時刻を抽出 (例: "11R AJCC 15:45 芝2200m")
                text = a_tag.get_text(strip=True)
                time_m = re.search(r'(\d{1,2}):(\d{2})', text)
                if not time_m:
                    continue
                hour = int(time_m.group(1))
                minute = int(time_m.group(2))
                start_time = hour * 60 + minute  # 分単位に変換

                race_num = int(rid[-2:])  # 末尾2桁 = レース番号

                all_races.append({
                    'race_id': rid,
                    'race_num': race_num,
                    'start_time': start_time,
                    'time_str': f"{hour:02d}:{minute:02d}",
                    'text': text,
                })

            print(f"[WIN5] 全レース: {len(all_races)}件")

            if not all_races:
                return []

            # 発走時刻順にソート
            all_races.sort(key=lambda r: r['start_time'])

            # 最も遅い11Rを探す（5レグ目）
            races_11r = [r for r in all_races if r['race_num'] == 11]
            if not races_11r:
                print("[WIN5] 11Rが見つかりません")
                return []

            leg5 = races_11r[-1]  # 最遅の11R
            print(f"[WIN5] Leg5（最遅11R）: {leg5['race_id']} {leg5['time_str']} {leg5['text']}")

            # Leg5より前のレースを時刻順で取得し、直前4レースを選ぶ
            before_leg5 = [r for r in all_races if r['start_time'] < leg5['start_time']]
            if len(before_leg5) < 4:
                print(f"[WIN5] Leg5より前のレースが4レース未満: {len(before_leg5)}件")
                return []

            # 直前4レース（時刻順で遅い方から4件）
            legs_1_to_4 = before_leg5[-4:]

            win5_races = legs_1_to_4 + [leg5]

            print(f"[WIN5] WIN5対象レース:")
            for i, r in enumerate(win5_races):
                print(f"  Leg{i+1}: {r['race_id']} {r['time_str']} {r['text']}")

            return [r['race_id'] for r in win5_races]

        except Exception as e:
            print(f"[WIN5] スクレイピングエラー: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _predict_race_for_win5(self, race_id):
        """WIN5用にレース予測を実行（predict_race()と同等の分析品質）

        predict_race()と同じスマートデータ更新 + 特徴量計算パイプラインを使用。
        GUI テーブル/テキストへの書き込みは行わないが、コンソールにログ出力する。

        Returns:
            (df_pred, race_info) or (None, None)
        """
        print(f"\n[WIN5] ========== 予測開始: {race_id} ==========")

        # 出馬表取得（フォールバック付き）
        horses, race_info = self.scrape_shutuba(race_id)

        if not horses or (race_info and race_info.get('error')):
            print(f"[WIN5] 出馬表なし -> 結果ページ試行: {race_id}")
            horses, race_info = self.scrape_race_result(race_id)

        if not horses or (race_info and race_info.get('error')):
            print(f"[WIN5] 結果ページなし -> DB試行: {race_id}")
            horses, race_info = self.get_race_from_database(race_id)

        if not horses:
            print(f"[WIN5] レース取得失敗: {race_id}")
            return None, None

        if race_info is None:
            race_info = {}

        print(f"[WIN5] {len(horses)}頭取得: {race_info.get('race_name', '?')}")

        # モデルチェック
        if self.model_win is None or self.df is None or self.model_features is None:
            print("[WIN5] モデルまたはデータ未読み込み")
            return None, race_info

        # ============================================================
        # データ状態チェック（警告ログのみ、更新はrun_win5側で一括実行済み）
        # ============================================================
        no_data_count = 0
        for horse in horses:
            horse_id = horse.get('horse_id')
            if horse_id:
                try:
                    horse_id_num = float(horse_id)
                    horse_data = self.df[self.df['horse_id'] == horse_id_num]
                    if len(horse_data) == 0:
                        no_data_count += 1
                        print(f"[WIN5]   データなし: {horse.get('馬名', '?')} (ID: {horse_id})")
                except (ValueError, TypeError):
                    pass
        if no_data_count > 0:
            print(f"[WIN5] {no_data_count}頭がDB未登録（デフォルト値で予測）")

        # ============================================================
        # AI予測（predict_race() 1366-1562行と同等）
        # ============================================================
        model_features = self.model_features
        # pd.to_datetime互換のISO形式（'2026年02月01日'形式はNaTになるため）
        current_date = datetime.now().strftime('%Y-%m-%d')
        race_horses_ids = [h.get('horse_id') for h in horses if h.get('horse_id')]

        predictions = []
        total_horses = len(horses)
        for i, horse in enumerate(horses):
            horse_id = horse.get('horse_id')
            features = None

            if horse_id:
                try:
                    horse_id_num = float(horse_id)
                except (ValueError, TypeError):
                    horse_id_num = None
                    print(f"[WIN5]   NG horse_id変換失敗 [{horse.get('馬名', '?')}]: {horse_id}")

                if horse_id_num is not None:
                    # 対象レース自体を除外（リーケージ防止）
                    try:
                        race_id_int = int(race_id)
                        horse_data = self.df[(self.df['horse_id'] == horse_id_num) & (self.df['race_id'] != race_id_int)]
                    except (ValueError, TypeError):
                        horse_data = self.df[self.df['horse_id'] == horse_id_num]

                    # 日付順にソート
                    if len(horse_data) > 0 and 'date' in horse_data.columns:
                        def normalize_date(date_str):
                            s = str(date_str)
                            match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', s)
                            if match:
                                return f"{match.group(1)}-{match.group(2).zfill(2)}-{match.group(3).zfill(2)}"
                            match = re.search(r'(\d{4}-\d{2}-\d{2})', s)
                            if match:
                                return match.group(1)
                            return s
                        horse_data = horse_data.copy()
                        horse_data['date_normalized'] = horse_data['date'].apply(normalize_date)
                        horse_data = horse_data.sort_values('date_normalized', ascending=True)
                    else:
                        horse_data = pd.DataFrame()

                    if len(horse_data) > 0:
                        try:
                            waku_num = int(horse.get('枠番', 0))
                        except (ValueError, TypeError):
                            waku_num = None
                        race_info['waku'] = waku_num

                        # 特徴量計算 (Phase R1: 46特徴量)
                        try:
                            features = calculate_horse_features_safe(
                                horse_id, self.df, current_date, self.sire_stats,
                                self.trainer_jockey_stats,
                                horse.get('調教師'), horse.get('騎手'),
                                race_info.get('track_name'),
                                race_info.get('distance'),
                                race_info.get('course_type'),
                                race_info.get('track_condition'),
                                waku_num,
                                race_id=race_id,
                                horse_kiryou=horse.get('斤量'),
                                horse_seire=horse.get('性齢'),
                                horse_weight_str=horse.get('馬体重'),
                            )
                        except Exception as e:
                            print(f"[WIN5]   特徴量計算エラー [{horse.get('馬名', '?')}]: {e}")
                            import traceback
                            traceback.print_exc()
                            features = None

                        if features:
                            # 特徴量の信頼性チェック
                            non_zero_count = sum(1 for v in features.values() if v != 0 and v != 0.0)
                            feature_reliability = non_zero_count / len(features) if features else 0
                            print(f"[WIN5]   OK [{horse.get('馬名', '?')}]: {len(features)}個 (有効: {non_zero_count}個, 信頼度: {feature_reliability*100:.0f}%)")
                        else:
                            print(f"[WIN5]   NG 特徴量がNone [{horse.get('馬名', '?')}]")
                    else:
                        print(f"[WIN5]   NG 馬データなし [{horse.get('馬名', '?')}] (horse_id: {horse_id})")
                        features = None
            else:
                print(f"[WIN5]   NG horse_id取得失敗 [{horse.get('馬名', '?')}]")
                features = None

            # 特徴量が取得できなかった場合はデフォルト値
            if features is None:
                print(f"[WIN5]   デフォルト値使用 [{horse.get('馬名', '?')}]")
                features = {feat: 0 for feat in model_features}
                features['total_starts'] = 10
                features['total_win_rate'] = 0.1
            else:
                for feat in model_features:
                    if feat not in features:
                        features[feat] = 0

            feat_df = pd.DataFrame([features])[model_features].fillna(0)

            # 予測 (Phase 14: lgb.Booster.predict() を使用)
            pred_win_proba = float(self.model_win.predict(feat_df)[0])
            pred_top3_proba = float(self.model_place.predict(feat_df)[0])

            odds = horse.get('単勝オッズ', 0)
            expected_value = pred_win_proba * odds if odds > 0 else 0

            predictions.append({
                '馬番': horse.get('馬番', ''),
                '枠番': horse.get('枠番', ''),
                '馬名': horse.get('馬名', ''),
                'horse_id': horse.get('horse_id'),
                '騎手': horse.get('騎手', ''),
                'オッズ': odds,
                '勝率予測': pred_win_proba,
                '複勝予測': pred_top3_proba,
                '期待値': expected_value,
            })

        if not predictions:
            return None, race_info

        df_pred = pd.DataFrame(predictions)
        df_pred = df_pred.sort_values('勝率予測', ascending=False).reset_index(drop=True)

        print(f"[WIN5] 予測完了: {race_id} top1={df_pred.iloc[0]['馬名']} P={df_pred.iloc[0]['勝率予測']:.3f}")
        return df_pred, race_info

    def _calculate_win5_strategy(self, leg_results, budget_points):
        """WIN5購入戦略を計算

        Args:
            leg_results: list of dict with 'df_pred', 'race_info', 'race_id'
            budget_points: 予算点数 (50/100/200/500)

        Returns:
            dict with 'dynamic' and 'fixed' strategies
        """
        # 各レグのtop1勝率を取得
        probas = []
        for leg in leg_results:
            if leg['df_pred'] is not None and len(leg['df_pred']) > 0:
                probas.append(leg['df_pred'].iloc[0]['勝率予測'])
            else:
                probas.append(0.0)

        n_legs = len(probas)

        # --- 動的配分（analyze_win5_budget.py の dynamic_allocation と同じロジック）---
        dynamic_picks = [1] * n_legs
        sorted_indices = sorted(range(n_legs), key=lambda i: probas[i])

        for idx in sorted_indices:
            current_points = 1
            for p in dynamic_picks:
                current_points *= p

            if current_points * 2 <= budget_points:
                dynamic_picks[idx] = 2
                current_points = 1
                for p in dynamic_picks:
                    current_points *= p

            if dynamic_picks[idx] == 2 and current_points * 1.5 <= budget_points:
                dynamic_picks[idx] = 3
                current_points = 1
                for p in dynamic_picks:
                    current_points *= p

            if dynamic_picks[idx] == 3 and current_points * (5/3) <= budget_points:
                dynamic_picks[idx] = 5

        dynamic_total = 1
        for p in dynamic_picks:
            dynamic_total *= p

        # --- 固定閾値パターン1: 高(≥0.40)→1頭, 中(≥0.20)→2頭, 低→3頭 ---
        fixed1_picks = []
        for p in probas:
            if p >= 0.40:
                fixed1_picks.append(1)
            elif p >= 0.20:
                fixed1_picks.append(2)
            else:
                fixed1_picks.append(3)

        fixed1_total = 1
        for p in fixed1_picks:
            fixed1_total *= p

        # --- 固定閾値パターン2: 高(≥0.40)→1頭, 中(≥0.20)→2頭, 低→5頭 ---
        fixed2_picks = []
        for p in probas:
            if p >= 0.40:
                fixed2_picks.append(1)
            elif p >= 0.20:
                fixed2_picks.append(2)
            else:
                fixed2_picks.append(5)

        fixed2_total = 1
        for p in fixed2_picks:
            fixed2_total *= p

        # 推奨: 予算内に収まるパターンの中で最も頭数が多いもの
        candidates = [
            ('dynamic', dynamic_picks, dynamic_total),
            ('fixed_3', fixed1_picks, fixed1_total),
            ('fixed_5', fixed2_picks, fixed2_total),
        ]
        # 予算内のもので点数が最も大きい戦略を推奨
        within_budget = [c for c in candidates if c[2] <= budget_points]
        if within_budget:
            recommended = max(within_budget, key=lambda c: c[2])
        else:
            recommended = candidates[0]  # 動的配分は常に予算内

        return {
            'probas': probas,
            'dynamic': {'picks': dynamic_picks, 'total': dynamic_total, 'cost': dynamic_total * 100},
            'fixed_3': {'picks': fixed1_picks, 'total': fixed1_total, 'cost': fixed1_total * 100},
            'fixed_5': {'picks': fixed2_picks, 'total': fixed2_total, 'cost': fixed2_total * 100},
            'recommended': recommended[0],
        }

    def _show_win5_result_dialog(self, date_str, leg_results, strategies, budget_points):
        """WIN5予測結果を専用ダイアログで表示"""
        win = tk.Toplevel(self.root)
        win.title(f"WIN5予測結果 - {date_str}")
        win.geometry("900x700")
        win.resizable(True, True)

        # タイトル
        title_frame = tk.Frame(win, bg="#E91E63", pady=8)
        title_frame.pack(fill=tk.X)
        tk.Label(title_frame, text=f"WIN5予測 - {date_str}",
                font=("Arial", 14, "bold"), bg="#E91E63", fg="white").pack()

        # ScrolledText
        text = scrolledtext.ScrolledText(win, font=("Consolas", 10), wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # テキスト構築
        lines = []
        probas = strategies['probas']
        rec_key = strategies['recommended']
        rec = strategies[rec_key]

        lines.append("=" * 60)
        lines.append(f"  WIN5予測 - {date_str}")
        lines.append("=" * 60)
        lines.append("")

        # 各レグの予測結果
        for i, leg in enumerate(leg_results):
            df_pred = leg['df_pred']
            race_info = leg.get('race_info') or {}
            race_id = leg['race_id']
            pick_n = rec['picks'][i]

            track = race_info.get('track_name', '')
            race_name = race_info.get('race_name', '')
            race_num = race_id[-2:] if len(race_id) >= 2 else '??'

            lines.append(f"--- Leg{i+1}: {track}{race_num}R {race_name} ---")

            if df_pred is None or len(df_pred) == 0:
                lines.append("  (予測失敗)")
                lines.append("")
                continue

            # 上位5頭を表示
            marks = ['◎', '○', '▲', '△', '☆']
            show_n = min(5, len(df_pred))
            for j in range(show_n):
                row = df_pred.iloc[j]
                mark = marks[j] if j < len(marks) else ' '
                umaban = str(row.get('馬番', ''))
                name = str(row.get('馬名', ''))
                wp = row.get('勝率予測', 0)
                jockey = str(row.get('騎手', ''))
                odds_val = row.get('オッズ', 0)

                buy_mark = ""
                if j < pick_n:
                    buy_mark = " << 購入"

                odds_str = f" odds={odds_val:.1f}" if odds_val > 0 else ""
                lines.append(f"  {mark} {umaban:>2s}番 {name:<8s} (P={wp:.3f}){odds_str} {jockey}{buy_mark}")

            lines.append("")

        # 購入戦略セクション
        lines.append("=" * 60)
        lines.append("  購入戦略")
        lines.append("=" * 60)
        lines.append("")

        budget_yen = budget_points * 100
        lines.append(f"  予算: {budget_yen:,}円（{budget_points}点以内）")
        lines.append("")

        # 動的配分
        d = strategies['dynamic']
        d_picks_str = ' x '.join(str(p) for p in d['picks'])
        d_mark = " ★推奨" if rec_key == 'dynamic' else ""
        lines.append(f"  [動的配分] {d_picks_str} = {d['total']}点 ({d['cost']:,}円){d_mark}")

        # 固定3段階(低→3頭)
        f3 = strategies['fixed_3']
        f3_picks_str = ' x '.join(str(p) for p in f3['picks'])
        f3_over = " ※予算超過" if f3['total'] > budget_points else ""
        f3_mark = " ★推奨" if rec_key == 'fixed_3' else ""
        lines.append(f"  [固定3段階] {f3_picks_str} = {f3['total']}点 ({f3['cost']:,}円){f3_over}{f3_mark}")

        # 固定5段階(低→5頭)
        f5 = strategies['fixed_5']
        f5_picks_str = ' x '.join(str(p) for p in f5['picks'])
        f5_over = " ※予算超過" if f5['total'] > budget_points else ""
        f5_mark = " ★推奨" if rec_key == 'fixed_5' else ""
        lines.append(f"  [固定5頭]   {f5_picks_str} = {f5['total']}点 ({f5['cost']:,}円){f5_over}{f5_mark}")

        lines.append("")
        lines.append("-" * 60)
        lines.append("  各レグ推奨（推奨戦略）")
        lines.append("-" * 60)

        for i, leg in enumerate(leg_results):
            df_pred = leg['df_pred']
            pick_n = rec['picks'][i]
            p = probas[i]

            conf = "★" if p >= 0.40 else " "

            if df_pred is not None and len(df_pred) > 0:
                pick_horses = []
                for j in range(min(pick_n, len(df_pred))):
                    row = df_pred.iloc[j]
                    pick_horses.append(f"{row.get('馬番', '?')}番")
                picks_str = ', '.join(pick_horses)
            else:
                picks_str = "(予測失敗)"

            lines.append(f"  Leg{i+1} (P={p:.2f}): {conf}{pick_n}頭 -> {picks_str}")

        # 合計
        lines.append("")
        lines.append(f"  合計: {rec['total']}点（{rec['cost']:,}円）")
        lines.append("")

        text.insert(tk.END, '\n'.join(lines))
        text.config(state=tk.DISABLED)

        # 閉じるボタン
        btn_frame = tk.Frame(win)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="閉じる", command=win.destroy,
                 width=10).pack()

    def predict_win5(self):
        """Win5予測 - 自信度ベース動的頭数配分"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Win5予測")
        dialog.geometry("420x300")
        dialog.resizable(False, False)

        tk.Label(dialog, text="WIN5予測", font=("Arial", 14, "bold"),
                bg="#E91E63", fg="white", pady=10).pack(fill=tk.X)

        tk.Label(dialog, text="対象日を指定してください:", font=("Arial", 10)).pack(pady=10)

        # 日付入力
        date_frame = tk.Frame(dialog)
        date_frame.pack(pady=5)

        now = datetime.now()
        tk.Label(date_frame, text="年:").grid(row=0, column=0, padx=5)
        year_var = tk.StringVar(value=str(now.year))
        tk.Entry(date_frame, textvariable=year_var, width=6).grid(row=0, column=1, padx=5)

        tk.Label(date_frame, text="月:").grid(row=0, column=2, padx=5)
        month_var = tk.StringVar(value=f"{now.month:02d}")
        tk.Entry(date_frame, textvariable=month_var, width=4).grid(row=0, column=3, padx=5)

        tk.Label(date_frame, text="日:").grid(row=0, column=4, padx=5)
        day_var = tk.StringVar(value=f"{now.day:02d}")
        tk.Entry(date_frame, textvariable=day_var, width=4).grid(row=0, column=5, padx=5)

        # 予算選択
        tk.Label(dialog, text="予算:", font=("Arial", 10)).pack(pady=(10, 5))
        budget_var = tk.IntVar(value=100)
        budget_frame = tk.Frame(dialog)
        budget_frame.pack()

        budgets = [("5,000円", 50), ("10,000円", 100), ("20,000円", 200), ("50,000円", 500)]
        for label, points in budgets:
            tk.Radiobutton(budget_frame, text=label, variable=budget_var,
                          value=points).pack(side=tk.LEFT, padx=5)

        # 実行ボタン
        def run_win5():
            try:
                target_date = f"{year_var.get()}{month_var.get().zfill(2)}{day_var.get().zfill(2)}"
                budget_points = budget_var.get()
                dialog.destroy()

                self.status_label.config(text=f"WIN5予測中... 対象日: {target_date}")
                self.progress['value'] = 0
                self.root.update()

                # 1. WIN5対象レースを自動取得
                self.progress['value'] = 5
                self.root.update()
                race_ids = self._scrape_win5_race_ids(target_date)

                if not race_ids or len(race_ids) < 5:
                    messagebox.showerror("エラー",
                        f"WIN5対象レースが5レース見つかりませんでした。\n"
                        f"取得数: {len(race_ids) if race_ids else 0}\n"
                        f"対象日: {target_date}\n\n"
                        f"開催日を確認してください。")
                    self.status_label.config(text="WIN5: レース取得失敗")
                    self.progress['value'] = 0
                    return

                # 2. DB未登録馬の事前チェック（5レース一括）
                self.status_label.config(text="WIN5: 出走馬データ確認中...")
                self.progress['value'] = 8
                self.root.update()

                all_no_data_horses = []
                for rid in race_ids:
                    horses_tmp, _ = self.scrape_shutuba(rid)
                    if not horses_tmp:
                        horses_tmp, _ = self.scrape_race_result(rid)
                    if horses_tmp:
                        for h in horses_tmp:
                            hid = h.get('horse_id')
                            if hid:
                                try:
                                    hid_num = float(hid)
                                    if len(self.df[self.df['horse_id'] == hid_num]) == 0:
                                        all_no_data_horses.append(h)
                                except (ValueError, TypeError):
                                    pass

                if all_no_data_horses and self.auto_update.get():
                    # DB未登録馬のみ一括更新（最終出走日が古いだけの馬はスキップ）
                    seen_ids = set()
                    unique_horses = []
                    for h in all_no_data_horses:
                        hid = h.get('horse_id')
                        if hid not in seen_ids:
                            seen_ids.add(hid)
                            unique_horses.append(h)

                    print(f"[WIN5] DB未登録馬: {len(unique_horses)}頭 → 自動データ取得")
                    self.status_label.config(text=f"WIN5: 未登録馬データ取得中... ({len(unique_horses)}頭)")
                    self.root.update()
                    try:
                        from smart_update_system import batch_update_race_horses
                        update_result = batch_update_race_horses(unique_horses, self.df)
                        if update_result.get('updated', 0) > 0:
                            new_races = update_result.get('new_races', [])
                            if new_races:
                                import pandas as _pd
                                new_df = _pd.DataFrame(new_races)
                                self.df = _pd.concat([self.df, new_df], ignore_index=True)
                                print(f"[WIN5] データ取得完了: +{len(new_races)}行")
                    except Exception as e:
                        print(f"[WIN5] データ取得エラー: {e}")
                elif all_no_data_horses:
                    print(f"[WIN5] DB未登録馬: {len(set(h.get('horse_id') for h in all_no_data_horses))}頭（自動更新OFF）")
                else:
                    print(f"[WIN5] 全出走馬のデータがDBに存在")

                # 3. 各レグの予測（通常予想と同等の分析を実行）
                leg_results = []
                for i, rid in enumerate(race_ids):
                    self.status_label.config(text=f"WIN5 Leg{i+1}/5 分析中... ({rid})")
                    self.progress['value'] = 10 + (i * 16)
                    self.root.update()

                    df_pred, race_info = self._predict_race_for_win5(rid)

                    race_name = race_info.get('race_name', '?') if race_info else '?'
                    if df_pred is not None and len(df_pred) > 0:
                        top_p = df_pred.iloc[0]['勝率予測']
                        self.status_label.config(text=f"WIN5 Leg{i+1}/5 完了: {race_name} (top P={top_p:.2f})")
                    else:
                        self.status_label.config(text=f"WIN5 Leg{i+1}/5 完了: {race_name} (予測失敗)")
                    self.root.update()

                    leg_results.append({
                        'race_id': rid,
                        'df_pred': df_pred,
                        'race_info': race_info,
                    })

                self.progress['value'] = 90
                self.root.update()

                # 4. 戦略計算
                strategies = self._calculate_win5_strategy(leg_results, budget_points)

                # 5. 結果表示
                self.progress['value'] = 95
                self.root.update()

                date_display = f"{year_var.get()}/{month_var.get().zfill(2)}/{day_var.get().zfill(2)}"
                self._show_win5_result_dialog(date_display, leg_results, strategies, budget_points)

                self.progress['value'] = 100
                self.status_label.config(text=f"WIN5予測完了 - {target_date}")

            except Exception as e:
                import traceback
                traceback.print_exc()
                messagebox.showerror("エラー", f"Win5予測エラー:\n{e}")
                self.status_label.config(text="WIN5予測エラー")
                self.progress['value'] = 0

        tk.Button(dialog, text="WIN5予測開始", command=run_win5,
                 bg="#4CAF50", fg="white", font=("Arial", 11, "bold"),
                 width=15).pack(pady=20)

    def open_period_collection_dialog(self):
        """期間指定データ収集ダイアログを開く"""
        dialog = tk.Toplevel(self.root)
        dialog.title("期間指定データ収集")
        dialog.geometry("600x550")
        dialog.resizable(True, True)

        # タイトル
        title_label = tk.Label(dialog, text="📅 期間を指定してデータ収集",
                              font=("Arial", 14, "bold"), bg="#9C27B0", fg="white", pady=10)
        title_label.pack(fill=tk.X)

        # 説明
        info_frame = tk.Frame(dialog, bg="#F5F5F5", pady=10)
        info_frame.pack(fill=tk.X, padx=10, pady=10)

        info_text = tk.Label(info_frame,
                            text="指定期間のレース結果を収集してデータベースに追加します\n"
                                 "※ 結果が公開されているレースのみ収集可能です",
                            bg="#F5F5F5", justify=tk.LEFT, font=("Arial", 9))
        info_text.pack()

        # 日付入力フレーム
        date_frame = tk.Frame(dialog)
        date_frame.pack(pady=20)

        # 開始日
        tk.Label(date_frame, text="開始日:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, pady=5)
        start_year = tk.StringVar(value="2025")
        start_month = tk.StringVar(value="10")
        start_day = tk.StringVar(value="03")

        tk.Label(date_frame, text="年:").grid(row=0, column=1, padx=5)
        tk.Entry(date_frame, textvariable=start_year, width=6).grid(row=0, column=2, padx=5)
        tk.Label(date_frame, text="月:").grid(row=0, column=3, padx=5)
        tk.Entry(date_frame, textvariable=start_month, width=4).grid(row=0, column=4, padx=5)
        tk.Label(date_frame, text="日:").grid(row=0, column=5, padx=5)
        tk.Entry(date_frame, textvariable=start_day, width=4).grid(row=0, column=6, padx=5)

        # 終了日
        tk.Label(date_frame, text="終了日:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, pady=5)
        end_year = tk.StringVar(value="2026")
        end_month = tk.StringVar(value="01")
        end_day = tk.StringVar(value="03")

        tk.Label(date_frame, text="年:").grid(row=1, column=1, padx=5)
        tk.Entry(date_frame, textvariable=end_year, width=6).grid(row=1, column=2, padx=5)
        tk.Label(date_frame, text="月:").grid(row=1, column=3, padx=5)
        tk.Entry(date_frame, textvariable=end_month, width=4).grid(row=1, column=4, padx=5)
        tk.Label(date_frame, text="日:").grid(row=1, column=5, padx=5)
        tk.Entry(date_frame, textvariable=end_day, width=4).grid(row=1, column=6, padx=5)

        # ログ表示エリア
        log_frame = tk.Frame(dialog)
        log_frame.pack(fill=tk.X, padx=10, pady=10)

        log_scroll = tk.Scrollbar(log_frame)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        log_text = tk.Text(log_frame, height=10, width=60, yscrollcommand=log_scroll.set,
                          font=("Courier", 9))
        log_text.pack(side=tk.LEFT, fill=tk.X, expand=False)
        log_scroll.config(command=log_text.yview)

        # 進捗バー
        progress_bar = ttk.Progressbar(dialog, length=480, mode='determinate')
        progress_bar.pack(padx=10, pady=5)

        # ボタンフレーム
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        def start_collection():
            """データ収集を開始"""
            try:
                # 日付を検証
                start_date_str = f"{start_year.get()}{start_month.get().zfill(2)}{start_day.get().zfill(2)}"
                end_date_str = f"{end_year.get()}{end_month.get().zfill(2)}{end_day.get().zfill(2)}"

                start_date = datetime.strptime(start_date_str, '%Y%m%d')
                end_date = datetime.strptime(end_date_str, '%Y%m%d')

                if start_date > end_date:
                    messagebox.showerror("エラー", "開始日は終了日より前である必要があります")
                    return

                # 確認
                days = (end_date - start_date).days + 1
                response = messagebox.askyesno("確認",
                    f"期間: {start_date.strftime('%Y年%m月%d日')} ～ {end_date.strftime('%Y年%m月%d日')}\n"
                    f"（{days}日間）\n\n"
                    f"データ収集を開始しますか？")

                if not response:
                    return

                # 収集開始
                collect_btn.config(state=tk.DISABLED)
                log_text.delete(1.0, tk.END)
                log_text.insert(tk.END, f"期間指定データ収集開始...\n")
                log_text.insert(tk.END, f"期間: {start_date.strftime('%Y/%m/%d')} ～ {end_date.strftime('%Y/%m/%d')}\n")
                log_text.insert(tk.END, f"{'-'*60}\n\n")
                dialog.update()

                # データ収集を実行
                self.collect_period_data(start_date, end_date, log_text, progress_bar, dialog)

                collect_btn.config(state=tk.NORMAL)
                messagebox.showinfo("完了", "データ収集が完了しました")

            except ValueError:
                messagebox.showerror("エラー", "無効な日付形式です")
            except Exception as e:
                messagebox.showerror("エラー", f"エラーが発生しました:\n{e}")
                collect_btn.config(state=tk.NORMAL)

        collect_btn = tk.Button(button_frame, text="▶ 収集開始", command=start_collection,
                               bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=15)
        collect_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="閉じる", command=dialog.destroy,
                 font=("Arial", 10), width=15).pack(side=tk.LEFT, padx=5)

    def collect_period_data(self, start_date, end_date, log_widget, progress_bar, dialog):
        """指定期間のデータを収集"""
        import requests
        from bs4 import BeautifulSoup
        import re
        import time
        import os
        import shutil

        # カレンダーから開催日を取得
        def get_race_dates_in_range(start, end):
            """期間内の開催日を取得"""
            dates = []
            current = start

            while current <= end:
                year = current.year
                month = current.month

                url = f"https://race.netkeiba.com/top/calendar.html?year={year}&month={month}"

                try:
                    headers = {'User-Agent': 'Mozilla/5.0'}
                    response = requests.get(url, headers=headers, timeout=10)
                    response.encoding = response.apparent_encoding
                    soup = BeautifulSoup(response.text, 'html.parser')

                    race_links = soup.find_all('a', href=re.compile(r'/top/race_list\.html\?kaisai_date='))

                    for link in race_links:
                        href = link.get('href')
                        date_match = re.search(r'kaisai_date=(\d{8})', href)
                        if date_match:
                            race_date_str = date_match.group(1)
                            race_date = datetime.strptime(race_date_str, '%Y%m%d')

                            if start <= race_date <= end:
                                dates.append(race_date_str)

                    # 重要: 待機時間（IPブロック防止）
                    time.sleep(1.5)

                except Exception as e:
                    log_widget.insert(tk.END, f"エラー ({year}/{month}): {e}\n")

                # 次の月へ
                if current.month == 12:
                    current = datetime(current.year + 1, 1, 1)
                else:
                    current = datetime(current.year, current.month + 1, 1)

            return sorted(list(set(dates)))

        # race_listページから実際のrace_idを取得（Selenium版）
        def get_race_ids_for_date(kaisai_date):
            """指定日のrace_listページから実際のrace_idを抽出（Selenium使用）"""
            race_ids = []
            url = f"https://race.netkeiba.com/top/race_list.html?kaisai_date={kaisai_date}"

            driver = None
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.options import Options

                options = Options()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--log-level=3')  # エラーログのみ表示
                options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
                options.add_experimental_option('excludeSwitches', ['enable-logging', 'enable-automation'])

                driver = webdriver.Chrome(options=options)
                driver.get(url)

                # ページ読み込み待機
                time.sleep(3)

                # ページソースを取得してBeautifulSoupで解析
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # href属性からrace_idを抽出
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    match = re.search(r'race_id=(\d{12})', href)
                    if match:
                        race_id = match.group(1)
                        if race_id not in race_ids:
                            race_ids.append(race_id)

                driver.quit()

                log_widget.insert(tk.END, f"  {kaisai_date}: {len(race_ids)}レース\n")
                log_widget.update()

                # 重要: 待機時間（IPブロック防止）
                time.sleep(1.5)

                return sorted(race_ids)

            except Exception as e:
                if driver:
                    driver.quit()
                log_widget.insert(tk.END, f"  エラー ({kaisai_date}): {e}\n")
                return []

        # レース結果を取得
        def scrape_race_result(race_id):
            """レース結果をスクレイピング (race.netkeiba.com対応)"""
            url = f"https://race.netkeiba.com/race/result.html?race_id={race_id}"

            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code != 200:
                    return None

                response.encoding = response.apparent_encoding
                soup = BeautifulSoup(response.text, 'html.parser')

                # レース情報を取得
                race_info = {}

                # タイトルから日付とレース名を取得
                title_tag = soup.find('title')
                if title_tag:
                    title_text = title_tag.get_text()
                    # 例: "２歳未勝利 結果・払戻 | 2025年12月28日 中山1R レース情報(JRA)"

                    # 日付を抽出
                    date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', title_text)
                    if date_match:
                        race_info['date'] = f"{date_match.group(1)}年{date_match.group(2).zfill(2)}月{date_match.group(3).zfill(2)}日"

                    # レース名を抽出（最初の部分）
                    race_name_match = re.search(r'^([^\|]+)', title_text)
                    if race_name_match:
                        race_name = race_name_match.group(1).strip()
                        # "結果・払戻"を削除
                        race_name = re.sub(r'\s*結果.*$', '', race_name)
                        race_info['race_name'] = race_name

                # レースデータ（距離、馬場状態など）を取得
                race_data01 = soup.find('div', class_='RaceData01')
                if race_data01:
                    data_text = race_data01.get_text()

                    # 距離とコース
                    distance_match = re.search(r'([芝ダ障])(\d+)m', data_text)
                    if distance_match:
                        race_info['course_type'] = '芝' if distance_match.group(1) == '芝' else 'ダート'
                        race_info['distance'] = int(distance_match.group(2))

                    # 馬場状態
                    condition_match = re.search(r'馬場[:：\s]*([良稍重不])', data_text)
                    if condition_match:
                        race_info['track_condition'] = condition_match.group(1)

                    # 天気
                    weather_match = re.search(r'天候[:：\s]*([晴曇雨雪])', data_text)
                    if weather_match:
                        race_info['weather'] = weather_match.group(1)

                # 競馬場名を取得（2番目のspanが競馬場名）
                race_data02 = soup.find('div', class_='RaceData02')
                if race_data02:
                    spans = race_data02.find_all('span')
                    if len(spans) > 1:
                        race_info['track_name'] = spans[1].get_text(strip=True)

                table = soup.find('table', class_='RaceTable01')
                if not table:
                    return None

                rows = table.find_all('tr')[1:]
                race_data = []

                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) < 15:
                        continue

                    try:
                        rank = cols[0].get_text(strip=True)
                        waku = cols[1].get_text(strip=True)
                        umaban = cols[2].get_text(strip=True)

                        horse_link = cols[3].find('a')
                        if horse_link:
                            horse_name = horse_link.get_text(strip=True)
                            horse_url = horse_link.get('href', '')
                            horse_id_match = re.search(r'/horse/(\d+)', horse_url)
                            horse_id = horse_id_match.group(1) if horse_id_match else None
                        else:
                            horse_name = cols[3].get_text(strip=True)
                            horse_id = None

                        sex_age = cols[4].get_text(strip=True)
                        weight_load = cols[5].get_text(strip=True)

                        jockey_link = cols[6].find('a')
                        jockey = jockey_link.get_text(strip=True) if jockey_link else cols[6].get_text(strip=True)

                        race_time = cols[7].get_text(strip=True)
                        margin = cols[8].get_text(strip=True)
                        passage = cols[10].get_text(strip=True)
                        last_3f = cols[11].get_text(strip=True)

                        odds_text = cols[12].get_text(strip=True)
                        try:
                            odds = float(odds_text)
                        except:
                            odds = None

                        popularity_text = cols[13].get_text(strip=True)
                        horse_weight = cols[14].get_text(strip=True)

                        race_data.append({
                            'race_id': int(race_id),
                            '着順': rank,
                            '枠番': waku,
                            '馬番': umaban,
                            '馬名': horse_name,
                            'horse_id': float(horse_id) if horse_id else None,
                            '性齢': sex_age,
                            '斤量': weight_load,
                            '騎手': jockey,
                            'タイム': race_time,
                            '着差': margin,
                            '通過': passage,
                            '上がり': last_3f,
                            '単勝': odds,
                            '人気': popularity_text,
                            '馬体重': horse_weight,
                            # レース情報を追加
                            'date': race_info.get('date'),
                            'track_name': race_info.get('track_name'),
                            'race_name': race_info.get('race_name'),
                            'distance': race_info.get('distance'),
                            'course_type': race_info.get('course_type'),
                            'track_condition': race_info.get('track_condition'),
                            'weather': race_info.get('weather')
                        })

                    except Exception as e:
                        continue

                if race_data:
                    return pd.DataFrame(race_data)
                else:
                    return None

            except Exception as e:
                return None

        # メイン処理
        log_widget.insert(tk.END, "[1] 開催日を取得中...\n")
        dialog.update()

        race_dates = get_race_dates_in_range(start_date, end_date)

        log_widget.insert(tk.END, f"  → {len(race_dates)}日の開催を検出\n\n")
        dialog.update()

        if not race_dates:
            log_widget.insert(tk.END, "開催日が見つかりませんでした\n")
            return

        # race_idを収集
        log_widget.insert(tk.END, "[2] レースID収集中...\n")
        dialog.update()

        all_race_ids = []
        for i, date in enumerate(race_dates):
            log_widget.insert(tk.END, f"  {date}: ")
            dialog.update()

            race_ids = get_race_ids_for_date(date)
            log_widget.insert(tk.END, f"{len(race_ids)}レース\n")
            dialog.update()

            all_race_ids.extend(race_ids)

            progress = int((i + 1) / len(race_dates) * 30)
            progress_bar['value'] = progress
            dialog.update()

            time.sleep(0.5)

        log_widget.insert(tk.END, f"\n  合計: {len(all_race_ids)}レース\n")
        dialog.update()

        if not all_race_ids:
            log_widget.insert(tk.END, "収集可能なレースが見つかりませんでした\n")
            log_widget.insert(tk.END, "※ まだ結果が公開されていない可能性があります\n")
            return

        # 既存データをチェックして重複を除外
        csv_path = os.path.join(BASE_DIR, 'data/main/netkeiba_data_2020_2025_complete.csv')
        existing_race_ids = set()

        if os.path.exists(csv_path):
            try:
                log_widget.insert(tk.END, "\n  既存データをチェック中...\n")
                dialog.update()

                existing_df = pd.read_csv(csv_path, low_memory=False)
                existing_race_ids = set(existing_df['race_id'].astype(str).unique())

                log_widget.insert(tk.END, f"  既存レース数: {len(existing_race_ids)}\n")
                dialog.update()
            except Exception as e:
                log_widget.insert(tk.END, f"  警告: 既存データの読み込みに失敗 ({e})\n")
                dialog.update()

        # 既に取得済みのrace_idを除外
        original_count = len(all_race_ids)
        all_race_ids = [rid for rid in all_race_ids if rid not in existing_race_ids]
        skipped_count = original_count - len(all_race_ids)

        if skipped_count > 0:
            log_widget.insert(tk.END, f"  スキップ: {skipped_count}レース（既に取得済み）\n")
            dialog.update()

        log_widget.insert(tk.END, f"  取得対象: {len(all_race_ids)}レース\n\n")
        dialog.update()

        if not all_race_ids:
            log_widget.insert(tk.END, "✓ 全てのレースが既に取得済みです\n")
            return

        # レースデータ収集
        log_widget.insert(tk.END, "[3] レースデータ収集中...\n")
        dialog.update()

        collected_data = []
        success = 0
        failed = 0

        for i, race_id in enumerate(all_race_ids):
            log_widget.insert(tk.END, f"  [{i+1}/{len(all_race_ids)}] {race_id}: ")
            dialog.update()

            df_race = scrape_race_result(race_id)

            if df_race is not None and len(df_race) > 0:
                collected_data.append(df_race)
                log_widget.insert(tk.END, f"OK ({len(df_race)}頭)\n")
                success += 1
            else:
                log_widget.insert(tk.END, "NG\n")
                failed += 1

            progress = 30 + int((i + 1) / len(all_race_ids) * 70)
            progress_bar['value'] = progress
            dialog.update()

            time.sleep(2)

        log_widget.insert(tk.END, f"\n[4] 収集完了: {success}レース成功, {failed}レース失敗\n")
        dialog.update()

        # データベースに追加
        if collected_data:
            log_widget.insert(tk.END, f"\n[5] データベース更新中...\n")
            dialog.update()

            new_df = pd.concat(collected_data, ignore_index=True)
            log_widget.insert(tk.END, f"  新規データ: {len(new_df)}件\n")

            csv_path = os.path.join(BASE_DIR, 'data/main/netkeiba_data_2020_2025_complete.csv')
            backup_path = os.path.join(BASE_DIR, 'data/main/netkeiba_data_2020_2025_complete_backup.csv')

            # バックアップ
            if os.path.exists(csv_path):
                import shutil
                shutil.copy2(csv_path, backup_path)
                log_widget.insert(tk.END, f"  バックアップ作成: 完了\n")

            # 既存データと結合
            if os.path.exists(csv_path):
                old_df = pd.read_csv(csv_path, low_memory=False)
                log_widget.insert(tk.END, f"  既存データ: {len(old_df)}件\n")

                combined_df = pd.concat([old_df, new_df], ignore_index=True)
                log_widget.insert(tk.END, f"  結合後: {len(combined_df)}件\n")

                # 重複を削除（race_idとhorse_idの組み合わせで判定）
                before_dedup = len(combined_df)
                combined_df = combined_df.drop_duplicates(subset=['race_id', 'horse_id'], keep='first')
                after_dedup = len(combined_df)

                if before_dedup > after_dedup:
                    log_widget.insert(tk.END, f"  重複削除: {before_dedup - after_dedup}件\n")

                log_widget.insert(tk.END, f"  最終データ: {len(combined_df)}件\n")

                combined_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                log_widget.insert(tk.END, f"\n✓ データベース更新完了!\n")
            else:
                new_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                log_widget.insert(tk.END, f"\n✓ 新規データベース作成完了!\n")

            # データベースを再読み込み
            self.df = pd.read_csv(csv_path, low_memory=False)
            log_widget.insert(tk.END, f"✓ メモリにリロード完了\n")

            # 拡張情報を追加（血統、勝率など）
            log_widget.insert(tk.END, f"\n[6] 拡張情報を追加中...\n")
            log_widget.insert(tk.END, f"  （血統・勝率・脚質などを取得します。時間がかかります）\n")
            dialog.update()

            try:
                self.df = self._add_enhanced_features(self.df, log_widget, dialog)
                log_widget.insert(tk.END, f"✓ 拡張情報追加完了\n")

                # 更新されたデータを保存
                self.df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                log_widget.insert(tk.END, f"✓ データベース更新完了\n")
            except Exception as e:
                log_widget.insert(tk.END, f"⚠ 拡張情報の追加でエラー: {e}\n")
                log_widget.insert(tk.END, f"  基本データは正常に保存されています\n")

            # 統計情報を更新
            self._calculate_data_range()

            dialog.update()
        else:
            log_widget.insert(tk.END, f"\n収集できたデータがありません\n")

        progress_bar['value'] = 100

    def sort_tree_column(self, col):
        """Treeviewの列をクリックしてソート"""
        if self.last_prediction is None:
            return

        # 列名からDataFrameのカラム名にマッピング
        col_map = {
            '順位': '勝率予測',  # デフォルトソート
            '印': '勝率予測',
            '枠': '枠番',
            '馬番': '馬番',
            '馬名': '馬名',
            '騎手': '騎手',
            'オッズ': 'オッズ',
            '人気': 'オッズ',  # オッズで人気も決まる
            '勝率%': '勝率予測',
            '複勝%': '複勝予測',
            '期待値': '期待値',
            '過去成績': '過去成績'
        }

        sort_col = col_map.get(col, '勝率予測')

        # 昇順/降順を切り替え
        if not hasattr(self, 'sort_reverse'):
            self.sort_reverse = {}

        if col not in self.sort_reverse:
            # 初回は降順（数値が大きい順）、馬番・枠番は昇順
            self.sort_reverse[col] = (col in ['枠', '馬番'])
        else:
            # 逆転
            self.sort_reverse[col] = not self.sort_reverse[col]

        ascending = self.sort_reverse[col]

        # DataFrameをソート
        df_sorted = self.last_prediction.copy()
        if sort_col in ['馬番', '枠番']:
            df_sorted[sort_col] = pd.to_numeric(df_sorted[sort_col], errors='coerce')

        df_sorted = df_sorted.sort_values(sort_col, ascending=ascending)

        # 現在のソート列を記録
        self.last_sort_column = sort_col

        # テーブル更新
        self.update_result_tree(df_sorted)

        # ステータス更新
        order_text = "昇順" if ascending else "降順"
        self.status_label.config(text=f"{col}で{order_text}ソート中")

    def update_result_tree(self, df_pred):
        """予測結果テーブルを更新"""
        # テーブルクリア
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

        if df_pred is None or len(df_pred) == 0:
            return

        # 人気順を計算（オッズが低い順）
        if 'オッズ' in df_pred.columns:
            df_with_popularity = df_pred.copy()
            # オッズ > 0 のものだけで人気順を計算
            valid_odds = df_with_popularity['オッズ'] > 0
            df_with_popularity.loc[valid_odds, '人気'] = df_with_popularity.loc[valid_odds, 'オッズ'].rank(method='min').astype(int)
            df_with_popularity.loc[~valid_odds, '人気'] = 0
        else:
            df_with_popularity = df_pred.copy()
            df_with_popularity['人気'] = 0

        # 行を挿入
        for i, (idx, row) in enumerate(df_with_popularity.iterrows(), 1):
            # 特徴量信頼度チェック（閾値25%: 79特徴量中20個未満でのみ低信頼）
            feat_rel = row.get('特徴量信頼度', 1.0)
            low_reliability = feat_rel < 0.25

            # 印: 事前計算済みの'印'カラムを使用（ソート変更しても維持）
            mark = row.get('印', '')

            # 回収率優秀マーク（15-20%確率帯: Phase 13で検証済み143.9%回収率）
            if row.get('回収率優秀', False):
                mark = mark + '*' if mark else '*'

            # 各列の値
            waku = row.get('枠番', '')
            umaban = row.get('馬番', '')
            name = row.get('馬名', '')
            jockey = row.get('騎手', '')

            # 性齢（例: 牡3）
            sex_age = row.get('性齢', '')

            # 斤量
            weight_load = row.get('斤量', '')

            # 馬体重（例: 468(+4)）
            horse_weight = row.get('馬体重', '')

            # オッズ
            odds_val = row.get('オッズ', 0)
            if odds_val > 0:
                odds_str = f"{odds_val:.1f}"
            else:
                odds_str = "---"

            # 人気
            popularity = int(row.get('人気', 0)) if row.get('人気', 0) > 0 else ""

            # 勝率・複勝率
            win_rate = f"{row.get('勝率予測', 0)*100:.1f}"
            place_rate = f"{row.get('複勝予測', 0)*100:.1f}"

            # 期待値
            ev_val = row.get('期待値', 0)
            if ev_val > 0:
                ev_str = f"{ev_val:.2f}"
            else:
                ev_str = "---"

            # タグ（枠番色 + 信頼度）
            tags = []
            try:
                waku_num = int(waku) if waku else 0
                if 1 <= waku_num <= 8:
                    tags.append(f'waku{waku_num}')
            except:
                pass

            # 信頼度低の場合はタグ追加
            if low_reliability:
                tags.append('low_reliability')

            # 過去成績
            past_record = row.get('過去成績', '')

            # 挿入（新しい列順）
            self.result_tree.insert('', 'end',
                                   values=(waku, umaban, mark, name, sex_age, weight_load,
                                          jockey, horse_weight, odds_str, popularity,
                                          win_rate, place_rate, ev_str, past_record),
                                   tags=tuple(tags))

    def resort_results(self, sort_by, ascending=False):
        """予測結果を再ソートして表示"""
        if self.last_prediction is None:
            messagebox.showwarning("警告", "表示する予測結果がありません")
            return

        # 現在のソート列を記録（印表示の制御に使用）
        self.last_sort_column = sort_by

        # ソート
        if sort_by in ['馬番', '枠番']:
            # 馬番・枠番は文字列なので数値に変換してソート
            df_sorted = self.last_prediction.copy()
            df_sorted[sort_by] = pd.to_numeric(df_sorted[sort_by], errors='coerce')
            df_sorted = df_sorted.sort_values(sort_by, ascending=ascending)
        else:
            df_sorted = self.last_prediction.sort_values(sort_by, ascending=ascending)

        # 新しいテーブル表示を使用
        self.update_result_tree(df_sorted)
        self.status_label.config(text=f"{sort_by}順で表示中")

    def update_recommended_bets(self, df_pred, has_odds):
        """推奨馬券を計算して表示（Feature A）- get_recommended_bet_targets()を内部使用"""
        self.recommend_text.config(state=tk.NORMAL)
        self.recommend_text.delete('1.0', tk.END)

        if df_pred is None or len(df_pred) == 0:
            self.recommend_text.insert(tk.END, "予測結果がありません\n")
            self.recommend_text.config(state=tk.DISABLED)
            return

        # 共通ロジックで馬券ターゲットを取得
        targets = self.get_recommended_bet_targets(df_pred, has_odds)
        if targets is None:
            self.recommend_text.insert(tk.END, "印割り当てがありません\n")
            self.recommend_text.config(state=tk.DISABLED)
            return

        # 印から各役割の馬を取得（表示用にdf_pred行が必要）
        def get_mark_horse(mark_char):
            matched = df_pred[df_pred['印'].str.startswith(mark_char, na=False)]
            return matched.iloc[0] if len(matched) > 0 else None

        def get_mark_horses(mark_char):
            return df_pred[df_pred['印'].str.startswith(mark_char, na=False)]

        honmei = get_mark_horse('◎')
        taikou = get_mark_horse('○')
        tanana = get_mark_horse('▲')
        star   = get_mark_horse('☆')
        renka  = get_mark_horses('△')
        chuui  = get_mark_horses('注')

        # 推奨馬券を構築
        recommend_lines = []

        win_proba = targets['win_proba']
        top1_value = honmei.get('バリュー', 0) if honmei is not None else 0

        # === 購入判定（バリューベット戦略） ===
        # Phase12実績ベース（2020-2025年, 20,365レース）
        if has_odds and 'バリュー' in df_pred.columns:
            if win_proba >= 0.50:
                signal = "【超高確信】単勝77.4%/複勝91.3%実績"
                action = "強気の単勝勝負（ROI 298%）"
            elif win_proba >= 0.35 and top1_value >= 0.10:
                signal = "【高確信+バリュー】単勝60%超/ROI270%超実績"
                action = "単勝購入推奨"
            elif win_proba >= 0.25 and top1_value >= 0.15:
                signal = "【バリュー】単勝50%超/ROI250%超実績"
                action = "単勝購入推奨（回収率重視）"
            elif win_proba >= 0.25:
                signal = "【中確信】"
                action = "複勝 or ワイドの軸に"
            elif top1_value >= 0.10:
                signal = "【穴バリュー】"
                action = "少額で単勝。穴狙い"
            else:
                signal = "【見送り推奨】"
                action = "このレースは見送り or 押さえ程度"
        else:
            if win_proba >= 0.50:
                signal = "【超高確信】単勝77.4%/複勝91.3%実績"
                action = "強気の単勝勝負（ROI 298%）"
            elif win_proba >= 0.35:
                signal = "【高確信】単勝60%超期待"
                action = "単勝軸。オッズ確認後バリュー判定を"
            elif win_proba >= 0.25:
                signal = "【中確信】単勝50%超期待"
                action = "オッズ次第。バリューがあれば購入"
            else:
                signal = "【見送り推奨】"
                action = "見送り or 押さえ程度"

        recommend_lines.append(f"{signal}")
        recommend_lines.append(f"  {action}")

        # 特徴量信頼度チェック
        if honmei is not None:
            top1_feat_rel = honmei.get('特徴量信頼度', 0)
            if top1_feat_rel < 0.5:
                recommend_lines.append(f"  WARNING: データ不足 (有効{top1_feat_rel*100:.0f}%) 精度低下の可能性")
        recommend_lines.append("")

        # === 予測印 ===
        recommend_lines.append("【予測印】")

        def format_horse_line(mark_char, label, horse):
            """印付き馬の表示行を生成"""
            odds_s = f" オッズ{horse['オッズ']:.1f}" if horse.get('オッズ', 0) > 0 else ""
            ev_s = f" EV={horse['期待値']:.2f}" if horse.get('期待値', 0) > 0 else ""
            val_s = f" V={horse['バリュー']:+.3f}" if has_odds and horse.get('オッズ', 0) > 0 else ""
            line = f"  {mark_char} {horse['馬番']}番 {horse['馬名']} 勝率{horse['勝率予測']*100:.1f}%{odds_s}"
            if mark_char == '▲' and ev_s:
                line += ev_s + "  <- 期待値最高"
            elif mark_char == '☆' and val_s:
                line += val_s + "  <- 大穴バリュー"
            elif ev_s:
                line += ev_s
            return line

        if honmei is not None:
            recommend_lines.append(format_horse_line('◎', '本命', honmei))
            past_record = honmei.get('過去成績', '')
            if past_record:
                recommend_lines.append(f"         {past_record}")
        if taikou is not None:
            recommend_lines.append(format_horse_line('○', '対抗', taikou))
        if tanana is not None:
            recommend_lines.append(format_horse_line('▲', '単穴', tanana))
        if star is not None:
            recommend_lines.append(format_horse_line('☆', '星', star))
        for _, r in renka.iterrows():
            recommend_lines.append(format_horse_line('△', '連下', r))
        for _, r in chuui.iterrows():
            recommend_lines.append(format_horse_line('注', '注意', r))

        # === Phase 13: 回収率優秀馬（15-20%確率帯）===
        sweet_spot_horses = df_pred[df_pred.get('回収率優秀', False) == True]
        if len(sweet_spot_horses) > 0:
            recommend_lines.append("")
            recommend_lines.append("【Phase 13: 回収率優秀馬】 (*印 = 143.9%回収率実績)")
            for _, row in sweet_spot_horses.iterrows():
                odds_info = f" オッズ{row['オッズ']:.1f}" if row.get('オッズ', 0) > 0 else ""

                # 推奨購入金額（オッズがある場合のみ）
                if row.get('オッズ', 0) > 0:
                    # 期待回収率143.9%をベースに、100円あたりの期待リターンを計算
                    expected_return = row['勝率予測'] * row['オッズ'] * 100
                    recommend_amount = "100円" if expected_return >= 100 else "見送り"
                    recommend_lines.append(
                        f"  * {row['馬番']}番 {row['馬名']} "
                        f"勝率{row['勝率予測']*100:.1f}%{odds_info} "
                        f"→ 推奨: {recommend_amount} (期待{expected_return:.0f}円)"
                    )
                else:
                    recommend_lines.append(
                        f"  * {row['馬番']}番 {row['馬名']} "
                        f"勝率{row['勝率予測']*100:.1f}% (オッズ未発表)"
                    )
            recommend_lines.append("  ※ 15-20%確率帯は907レースで検証済み（95%CI: 128.8%-160.1%）")

        # === バリューベット推奨（オッズあり時） ===
        if has_odds and 'バリュー' in df_pred.columns:
            recommend_lines.append("")
            recommend_lines.append("【バリューベット】(V=モデル確率-オッズ確率, 正=割安)")
            value_horses = df_pred[df_pred['バリュー'] >= 0.05].sort_values('バリュー', ascending=False)
            if len(value_horses) > 0:
                for _, row in value_horses.head(5).iterrows():
                    vm = "★" if row['バリュー'] >= 0.15 else "☆" if row['バリュー'] >= 0.10 else "△"
                    recommend_lines.append(
                        f"  {vm} {row['馬番']}番 {row['馬名']}: "
                        f"勝率{row['勝率予測']*100:.1f}% オッズ{row['オッズ']:.1f} "
                        f"V={row['バリュー']:+.2f} EV={row['期待値']:.2f}"
                    )
            else:
                recommend_lines.append("  バリューのある馬なし。見送り推奨。")
        elif not has_odds:
            recommend_lines.append("")
            recommend_lines.append("※ オッズ未発表: バリュー判定はオッズ確定後に")

        # === AI予測の仕組み説明 ===
        recommend_lines.append("")
        recommend_lines.append("【AI予測の仕組み】")
        recommend_lines.append("  ◎○▲印: 勝率ベースで選定（1着になる確率が高い馬）")
        recommend_lines.append("  ワイド・3連複: 複勝率ベースで選定（馬券圏内に入る組み合わせ）")
        recommend_lines.append("  → 検証結果: ワイド +4.8pt、3連複 +3.2pt 的中率改善")
        recommend_lines.append("  → 「勝てないが馬券圏内」の馬を正確に予測")

        # === 勝率に応じた最適買い目（targets dictから馬番を使用） ===
        uma1 = targets['honmei']
        uma2 = targets['taikou']
        uma3 = targets['tanana']
        himo_list = targets['himo_list']

        recommend_lines.append("")
        recommend_lines.append("【推奨買い目】勝率に応じた最適パターン")

        # 推奨買い目パターン（バックテスト検証済: 20,365レース, 2020-2025年）
        # BOX vs 流し比較で最適パターンを採用
        if uma1 is not None and uma2 is not None and uma3 is not None:
            if win_proba >= 0.50:
                recommend_lines.append("  ─ 本命レース（勝率50%以上）★最効率パターン ─")
                recommend_lines.append(f"  単勝: {uma1}番 400円 ← 77.4%的中/ROI 298%（メインベット）")
                recommend_lines.append(f"  3連複BOX: {uma1}-{uma2}-{uma3} 200円 ← 25.8%的中/ROI 911% ★超高効率")
                recommend_lines.append(f"             ↑複勝率上位3頭（1点買い・流しより高ROI）")
                if len(himo_list) >= 1:
                    himo_nums = [str(h) for h in himo_list[:1]]
                    recommend_lines.append(f"  ワイド流し: {uma1}→{uma2},{','.join(himo_nums)} 100円 ← 72.7%的中/ROI 337%（2点×50円）")
                recommend_lines.append(f"  → 合計700円 / 期待収支 +約250円")

            elif win_proba >= 0.40:
                recommend_lines.append("  ─ 準本命（勝率40-50%）─")
                recommend_lines.append(f"  単勝: {uma1}番 300円 ← 62.3%的中/ROI 273%")
                if len(himo_list) >= 2:
                    himo_nums = [str(h) for h in himo_list[:2]]
                    recommend_lines.append(f"  馬連流し: {uma1}→{uma2},{','.join(himo_nums)} 200円 ← 56.9%的中/ROI 301%（3点×66円）")
                else:
                    recommend_lines.append(f"  馬連: {uma1}-{uma2} 200円 ← 23.9%的中/ROI 307%")
                recommend_lines.append(f"  3連複BOX: {uma1}-{uma2}-{uma3} 100円 ← 20.1%的中/ROI 691%")
                recommend_lines.append(f"  → 合計600円 / 期待収支 +約120円")

            elif win_proba >= 0.30:
                recommend_lines.append("  ─ 中穴（勝率30-40%）─")
                recommend_lines.append(f"  単勝: {uma1}番 300円 ← 53.9%的中/ROI 279%")
                recommend_lines.append(f"  3連複BOX: {uma1}-{uma2}-{uma3} 200円 ← 15.3%的中/ROI 578%")
                recommend_lines.append(f"             ↑複勝率上位3頭（1点BOXが最効率）")
                if len(himo_list) >= 1:
                    himo_nums = [str(h) for h in himo_list[:1]]
                    recommend_lines.append(f"  ワイド流し: {uma1}→{uma2},{','.join(himo_nums)} 100円 ← 51.8%的中/ROI 250%（2点×50円）")
                recommend_lines.append(f"  → 合計600円 / 期待収支 +約100円")

            elif win_proba >= 0.20:
                recommend_lines.append("  ─ 穴狙い（勝率20-30%）─")
                recommend_lines.append(f"  単勝: {uma1}番 200円 ← 43.6%的中/ROI 248%")
                recommend_lines.append(f"  3連複BOX: {uma1}-{uma2}-{uma3} 300円 ← 11.7%的中/ROI 681% ★高配当")
                recommend_lines.append(f"             ↑複勝率上位3頭（1点BOXが最効率）")
                if len(himo_list) >= 1:
                    himo_nums = [str(h) for h in himo_list[:1]]
                    recommend_lines.append(f"  ワイド流し: {uma1}→{uma2},{','.join(himo_nums)} 100円 ← 44.0%的中/ROI 242%（2点×50円）")
                recommend_lines.append(f"  → 合計600円 / 期待収支 +約80円")

            elif win_proba >= 0.10:
                recommend_lines.append("  ─ 大穴ゾーン（勝率10-20%）─")
                recommend_lines.append(f"  単勝: {uma1}番 400円 ← 35.9%的中/ROI 272%")
                if len(himo_list) >= 2:
                    himo_nums = [str(h) for h in himo_list[:2]]
                    recommend_lines.append(f"  3連複2頭軸流し: {uma1}-{uma2}→{','.join(himo_nums)} 200円 ← 16.6%的中/ROI 450%（3点×66円）")
                    recommend_lines.append(f"                  ↑◎○軸で穴馬を拾う戦略")
                else:
                    recommend_lines.append(f"  3連複BOX: {uma1}-{uma2}-{uma3} 200円 ← 8.3%的中/ROI 519%")
                recommend_lines.append(f"  → 合計600円 / 期待収支 +約60円")

            else:
                recommend_lines.append("  ─ 超大穴（勝率10%未満）─")
                recommend_lines.append(f"  単勝: {uma1}番 100円のみ推奨 ← 11.5%的中/ROI 121%")
                recommend_lines.append(f"  ※ 期待値マイナス（-21%）のため基本的に見送り推奨")
                recommend_lines.append(f"  ※ 3連複も全パターンでROI 100%未満")

        # === バリュー馬がいる場合の追加推奨 ===
        if has_odds and '期待値' in df_pred.columns:
            ev_candidates = df_pred[df_pred['期待値'] >= 1.2].sort_values('期待値', ascending=False)
            if len(ev_candidates) > 0:
                best_ev = ev_candidates.iloc[0]
                if best_ev['馬番'] != str(uma1):
                    recommend_lines.append("")
                    recommend_lines.append("【バリュー追加】")
                    recommend_lines.append(f"  単勝: {int(best_ev['馬番'])}番 {best_ev['馬名']} (EV={best_ev['期待値']:.2f}) 100-200円")

        # === 参考: 流し・ボックス ===
        if uma1 is not None and len(himo_list) >= 2:
            recommend_lines.append("")
            recommend_lines.append("【参考: 流し・ボックス】")
            himo_nums = [str(h) for h in himo_list]
            recommend_lines.append(f"  ワイド流し: {uma1}→{','.join(himo_nums)} ({len(himo_list)}点/{len(himo_list)*100}円)")
            box_nums = [str(uma1)] + himo_nums
            # 重複除去
            seen = set()
            box_unique = []
            for bn in box_nums:
                if bn not in seen:
                    seen.add(bn)
                    box_unique.append(bn)
            box_nums = box_unique
            n_box = len(box_nums)
            if n_box >= 3:
                n_sanren = n_box * (n_box - 1) * (n_box - 2) // 6
                recommend_lines.append(f"  3連複BOX: {'-'.join(box_nums)} ({n_sanren}点/{n_sanren*100}円)")
            if n_box == 3:
                recommend_lines.append(f"  3連単BOX: {'-'.join(box_nums)} (6点/600円)")

        # === Rule4 単勝買い目（ペーパートレード準拠） ===
        rule4_horses = []
        for _, row in df_pred.iterrows():
            pred_w = float(row.get('勝率予測', 0))
            odds_v = float(row.get('オッズ', 0))
            if odds_v <= 0:
                continue
            cond_a = pred_w >= 0.20 and 2.0 <= odds_v < 10.0
            cond_b = pred_w >= 0.10 and odds_v >= 10.0
            if cond_a or cond_b:
                rule4_horses.append((row, cond_a, pred_w, odds_v))

        if rule4_horses:
            # 現在のバンクロールを paper_trade_log.csv から取得
            try:
                import csv as _csv
                _log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paper_trade_log.csv')
                _bankroll = 50000
                if os.path.exists(_log_path):
                    with open(_log_path, encoding='utf-8') as _f:
                        _rows = list(_csv.DictReader(_f))
                    _confirmed = [r for r in _rows if r.get('result') in ('的中', 'ハズレ')]
                    if _confirmed:
                        _bankroll = float(_confirmed[-1].get('bankroll', 50000) or 50000)
            except Exception:
                _bankroll = 50000

            def _kelly_bet(pred_w, odds_v, cond_a, bankroll):
                if odds_v <= 1:
                    return 100
                if cond_a:
                    k = (pred_w * odds_v - 1.0) / (odds_v - 1.0)
                    k = max(0.0, min(k, 0.5))
                    amt = k * bankroll * 0.5
                    amt = max(100, min(1000, amt))
                    return int(round(amt / 100) * 100)
                return 100

            recommend_lines.append("")
            recommend_lines.append("【Rule4 単勝買い目（ペーパートレード準拠）】")
            recommend_lines.append(f"  バンクロール: {int(_bankroll):,}円")
            for row, cond_a, pred_w, odds_v in rule4_horses:
                bet = _kelly_bet(pred_w, odds_v, cond_a, _bankroll)
                rule_label = "条件A(Kelly)" if cond_a else "条件B(固定)"
                recommend_lines.append(
                    f"  {rule_label}  {row['馬番']}番 {row['馬名']}"
                    f"  勝率{pred_w*100:.1f}%  オッズ{odds_v:.1f}倍  → {bet}円"
                )

        # === ワイド・馬連 複勝上位3頭BOX ===
        if '複勝予測' in df_pred.columns:
            from itertools import combinations as _comb
            top3 = df_pred.nlargest(3, '複勝予測')
            if len(top3) >= 2:
                top3_info = [(str(r['馬番']), r['馬名'], float(r['複勝予測'])*100)
                             for _, r in top3.iterrows()]
                recommend_lines.append("")
                recommend_lines.append("【ワイド・馬連 複勝上位3頭BOX】（各100円）")
                horses_str = "  / ".join(f"{u}番 {n}({p:.0f}%)" for u, n, p in top3_info)
                recommend_lines.append(f"  対象: {horses_str}")
                pairs = list(_comb(top3_info, 2))
                wide_str  = "  ".join(f"{a[0]}-{b[0]}" for a, b in pairs)
                umaren_str = "  ".join(f"{a[0]}-{b[0]}" for a, b in pairs)
                recommend_lines.append(f"  ワイド: {wide_str}  ({len(pairs)}点/{len(pairs)*100}円)")
                recommend_lines.append(f"  馬連:   {umaren_str}  ({len(pairs)}点/{len(pairs)*100}円)")

        # === SHAP 予測根拠（◎・○馬のみ） ===
        shap_targets = []
        if honmei is not None and len(honmei.get('shap_top5', [])) > 0:
            shap_targets.append(honmei)
        if taikou is not None and len(taikou.get('shap_top5', [])) > 0:
            shap_targets.append(taikou)

        if shap_targets:
            recommend_lines.append("")
            recommend_lines.append("【予測根拠（単勝モデル TOP5特徴量）】")
            for horse in shap_targets:
                name    = horse['馬名']
                win_pct = horse['勝率予測'] * 100
                recommend_lines.append(f"  ▶ {name} ({win_pct:.1f}%)")
                for feat, val in horse['shap_top5']:
                    jp    = FEATURE_NAMES_JP.get(feat, feat)
                    arrow = '↑' if val > 0 else '↓'
                    recommend_lines.append(f"      {arrow} {jp:<16} {val:+.3f}")

        # テキストを表示
        for line in recommend_lines:
            self.recommend_text.insert(tk.END, line + "\n")

        self.recommend_text.config(state=tk.DISABLED)

    def show_statistics_visualization(self):
        """統計情報グラフを表示（Feature B）"""
        if self.last_prediction is None:
            messagebox.showwarning("警告", "予測結果がありません")
            return

        try:
            import matplotlib.pyplot as plt
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import matplotlib
            matplotlib.use('TkAgg')
        except ImportError:
            messagebox.showerror("エラー", "matplotlibがインストールされていません\n\npip install matplotlib")
            return

        # 新しいウィンドウを作成
        viz_window = tk.Toplevel(self.root)
        viz_window.title("統計情報グラフ")
        viz_window.geometry("900x700")

        # タイトル
        title_label = tk.Label(viz_window, text="📊 統計情報の可視化", font=("Arial", 14, "bold"))
        title_label.pack(pady=10)

        # グラフ描画エリア
        fig, axes = plt.subplots(2, 2, figsize=(10, 8))
        fig.tight_layout(pad=4.0)

        df = self.last_prediction

        # グラフ1: 勝率予測の分布
        ax1 = axes[0, 0]
        win_rates = df['勝率予測'] * 100
        ax1.bar(range(len(win_rates)), win_rates.values, color='steelblue')
        ax1.set_xlabel('馬番順', fontproperties='MS Gothic')
        ax1.set_ylabel('勝率予測 (%)', fontproperties='MS Gothic')
        ax1.set_title('勝率予測分布', fontproperties='MS Gothic')
        ax1.grid(True, alpha=0.3)

        # グラフ2: 複勝率予測の分布
        ax2 = axes[0, 1]
        place_rates = df['複勝予測'] * 100
        ax2.bar(range(len(place_rates)), place_rates.values, color='orange')
        ax2.set_xlabel('馬番順', fontproperties='MS Gothic')
        ax2.set_ylabel('複勝率予測 (%)', fontproperties='MS Gothic')
        ax2.set_title('複勝率予測分布', fontproperties='MS Gothic')
        ax2.grid(True, alpha=0.3)

        # グラフ3: 期待値分布（オッズがある場合のみ）
        ax3 = axes[1, 0]
        if self.last_has_odds:
            evs = df['期待値']
            colors = ['red' if ev >= 2.0 else 'orange' if ev >= 1.5 else 'green' if ev >= 1.2 else 'gray' for ev in evs]
            ax3.bar(range(len(evs)), evs.values, color=colors)
            ax3.axhline(y=1.0, color='black', linestyle='--', alpha=0.5, label='損益分岐点')
            ax3.axhline(y=1.2, color='green', linestyle='--', alpha=0.5, label='注目ライン')
            ax3.axhline(y=1.5, color='orange', linestyle='--', alpha=0.5, label='推奨ライン')
            ax3.axhline(y=2.0, color='red', linestyle='--', alpha=0.5, label='超推奨ライン')
            ax3.legend(prop={'family': 'MS Gothic', 'size': 8})
        else:
            ax3.text(0.5, 0.5, 'オッズ未発表のため\n期待値計算不可', ha='center', va='center',
                    transform=ax3.transAxes, fontproperties='MS Gothic', fontsize=12)
        ax3.set_xlabel('馬番順', fontproperties='MS Gothic')
        ax3.set_ylabel('期待値', fontproperties='MS Gothic')
        ax3.set_title('期待値分布', fontproperties='MS Gothic')
        ax3.grid(True, alpha=0.3)

        # グラフ4: オッズと勝率予測の相関
        ax4 = axes[1, 1]
        if self.last_has_odds:
            odds_data = df[df['オッズ'] > 0]
            ax4.scatter(odds_data['オッズ'], odds_data['勝率予測'] * 100, color='purple', alpha=0.6, s=100)
            for _, row in odds_data.iterrows():
                ax4.annotate(f"{row['馬番']}", (row['オッズ'], row['勝率予測'] * 100),
                           fontproperties='MS Gothic', fontsize=8)
        else:
            ax4.text(0.5, 0.5, 'オッズ未発表のため\n相関分析不可', ha='center', va='center',
                    transform=ax4.transAxes, fontproperties='MS Gothic', fontsize=12)
        ax4.set_xlabel('オッズ (倍)', fontproperties='MS Gothic')
        ax4.set_ylabel('勝率予測 (%)', fontproperties='MS Gothic')
        ax4.set_title('オッズ vs 勝率予測', fontproperties='MS Gothic')
        ax4.grid(True, alpha=0.3)

        # Tkinterキャンバスに埋め込み
        canvas = FigureCanvasTkAgg(fig, master=viz_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # 閉じるボタン
        close_button = tk.Button(viz_window, text="閉じる", command=viz_window.destroy,
                                bg="#9E9E9E", fg="white", font=("Arial", 10, "bold"))
        close_button.pack(pady=10)

    def show_detailed_analysis(self):
        """詳細分析を表示（Feature C）"""
        if self.last_prediction is None:
            messagebox.showwarning("警告", "予測結果がありません")
            return

        # 新しいウィンドウを作成
        detail_window = tk.Toplevel(self.root)
        detail_window.title("詳細分析")
        detail_window.geometry("800x600")

        # タイトル
        title_label = tk.Label(detail_window, text="🔍 詳細分析", font=("Arial", 14, "bold"))
        title_label.pack(pady=10)

        # メインフレーム
        main_frame = tk.Frame(detail_window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 馬選択エリア
        select_frame = tk.LabelFrame(main_frame, text="分析対象馬選択", font=("Arial", 11, "bold"))
        select_frame.pack(fill=tk.X, pady=5)

        tk.Label(select_frame, text="馬番:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        horse_var = tk.StringVar()
        horse_numbers = [str(row['馬番']) for _, row in self.last_prediction.iterrows()]
        horse_combo = ttk.Combobox(select_frame, textvariable=horse_var, values=horse_numbers,
                                   state='readonly', width=10)
        horse_combo.pack(side=tk.LEFT, padx=5)
        if horse_numbers:
            horse_combo.current(0)

        # 分析結果表示エリア
        result_frame = tk.LabelFrame(main_frame, text="分析結果", font=("Arial", 11, "bold"))
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        result_text = scrolledtext.ScrolledText(result_frame, font=("Courier", 9), wrap=tk.WORD)
        result_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        def analyze_horse():
            """選択された馬を分析"""
            selected_umaban = horse_var.get()
            if not selected_umaban:
                return

            result_text.delete('1.0', tk.END)

            # 該当する馬を取得
            horse_row = self.last_prediction[self.last_prediction['馬番'] == selected_umaban]
            if len(horse_row) == 0:
                result_text.insert(tk.END, "馬が見つかりません\n")
                return

            horse_row = horse_row.iloc[0]

            # 基本情報
            result_text.insert(tk.END, "=" * 80 + "\n")
            result_text.insert(tk.END, f" 馬番: {horse_row['馬番']}番  馬名: {horse_row['馬名']}\n")
            result_text.insert(tk.END, "=" * 80 + "\n\n")

            # 予測情報
            result_text.insert(tk.END, "【予測情報】\n")
            result_text.insert(tk.END, f"  勝率予測: {horse_row['勝率予測']*100:.1f}%\n")
            result_text.insert(tk.END, f"  複勝率予測: {horse_row['複勝予測']*100:.1f}%\n")
            if horse_row.get('オッズ', 0) > 0:
                result_text.insert(tk.END, f"  単勝オッズ: {horse_row['オッズ']:.1f}倍\n")
                result_text.insert(tk.END, f"  期待値: {horse_row['期待値']:.2f}\n")
            else:
                result_text.insert(tk.END, f"  単勝オッズ: 未発表\n")
            result_text.insert(tk.END, "\n")

            # 騎手・調教師情報
            result_text.insert(tk.END, "【騎手・調教師】\n")
            result_text.insert(tk.END, f"  騎手: {horse_row.get('騎手', '不明')}\n")
            result_text.insert(tk.END, f"  調教師: {horse_row.get('調教師', '不明')}\n")
            result_text.insert(tk.END, "\n")

            # 過去成績（データベースから取得）
            horse_id = horse_row.get('horse_id')
            if horse_id and self.df is not None:
                result_text.insert(tk.END, "【過去成績（直近10レース）】\n")
                try:
                    horse_id_num = float(horse_id)
                    horse_history = self.df[self.df['horse_id'] == horse_id_num].sort_values('date', ascending=False).head(10)

                    if len(horse_history) > 0:
                        result_text.insert(tk.END, f"  総レース数: {len(self.df[self.df['horse_id'] == horse_id_num])}戦\n")
                        result_text.insert(tk.END, f"  直近10レース:\n")

                        for i, (_, row) in enumerate(horse_history.iterrows(), 1):
                            date = row.get('date', '不明')
                            rank = row.get('着順', '?')
                            track = row.get('track_name', '?')
                            distance = row.get('distance', '?')
                            result_text.insert(tk.END, f"    {i:2}. {date} {track} {distance}m → {rank}着\n")
                    else:
                        result_text.insert(tk.END, "  データなし\n")
                except Exception as e:
                    result_text.insert(tk.END, f"  取得エラー: {e}\n")
            else:
                result_text.insert(tk.END, "【過去成績】\n")
                result_text.insert(tk.END, "  データなし（horse_id不明）\n")

            result_text.insert(tk.END, "\n")

        # 分析ボタン
        analyze_button = tk.Button(select_frame, text="分析実行", command=analyze_horse,
                                  bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        analyze_button.pack(side=tk.LEFT, padx=10)

        # 初回自動分析
        analyze_horse()

        # 閉じるボタン
        close_button = tk.Button(detail_window, text="閉じる", command=detail_window.destroy,
                                bg="#9E9E9E", fg="white", font=("Arial", 10, "bold"))
        close_button.pack(pady=10)

    def open_period_collection_dialog(self):
        """期間指定データ収集ダイアログを開く"""
        dialog = tk.Toplevel(self.root)
        dialog.title("期間データ収集")
        dialog.geometry("550x600")
        dialog.transient(self.root)
        dialog.grab_set()

        # タイトル
        title_label = tk.Label(dialog, text="📅 期間指定データ収集",
                              font=("Arial", 14, "bold"), bg="#9C27B0", fg="white")
        title_label.pack(fill=tk.X, pady=(0, 10))

        # 説明
        desc_frame = tk.Frame(dialog, bg="lightyellow")
        desc_frame.pack(fill=tk.X, padx=10, pady=5)
        desc_text = """指定期間のレースデータを一括収集します
• 既存データは自動スキップ（重複なし）
• 馬情報（血統・統計）を自動収集
• 中断しても再開可能"""
        tk.Label(desc_frame, text=desc_text, bg="lightyellow", justify=tk.LEFT,
                font=("Arial", 9)).pack(padx=10, pady=5)

        # 入力フレーム
        input_frame = tk.Frame(dialog)
        input_frame.pack(pady=10)

        # 開始年月
        tk.Label(input_frame, text="開始:", font=("Arial", 10, "bold")).grid(row=0, column=0, sticky=tk.W, padx=5)
        start_year = tk.Spinbox(input_frame, from_=2020, to=2026, width=8, font=("Arial", 10))
        start_year.delete(0, tk.END)
        start_year.insert(0, "2020")
        start_year.grid(row=0, column=1, padx=5)
        tk.Label(input_frame, text="年").grid(row=0, column=2)

        start_month = tk.Spinbox(input_frame, from_=1, to=12, width=5, font=("Arial", 10))
        start_month.delete(0, tk.END)
        start_month.insert(0, "1")
        start_month.grid(row=0, column=3, padx=5)
        tk.Label(input_frame, text="月").grid(row=0, column=4)

        # 終了年月
        tk.Label(input_frame, text="終了:", font=("Arial", 10, "bold")).grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        end_year = tk.Spinbox(input_frame, from_=2020, to=2026, width=8, font=("Arial", 10))
        end_year.delete(0, tk.END)
        end_year.insert(0, "2026")
        end_year.grid(row=1, column=1, padx=5)
        tk.Label(input_frame, text="年").grid(row=1, column=2)

        end_month = tk.Spinbox(input_frame, from_=1, to=12, width=5, font=("Arial", 10))
        end_month.delete(0, tk.END)
        end_month.insert(0, "1")
        end_month.grid(row=1, column=3, padx=5)
        tk.Label(input_frame, text="月").grid(row=1, column=4)

        # オプション
        options_frame = tk.LabelFrame(dialog, text="オプション", font=("Arial", 10, "bold"))
        options_frame.pack(pady=10, padx=10, fill=tk.X)

        collect_horse_var = tk.BooleanVar(value=True)
        tk.Checkbutton(options_frame, text="馬情報も収集（血統・統計）",
                      variable=collect_horse_var, font=("Arial", 9)).pack(anchor=tk.W, padx=10, pady=2)

        force_update_var = tk.BooleanVar(value=False)
        tk.Checkbutton(options_frame, text="既存データも強制再収集",
                      variable=force_update_var, font=("Arial", 9)).pack(anchor=tk.W, padx=10, pady=2)

        # ログ表示
        log_frame = tk.LabelFrame(dialog, text="収集ログ", font=("Arial", 10, "bold"))
        log_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        log_widget = scrolledtext.ScrolledText(log_frame, height=12, font=("Courier", 8))
        log_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # プログレスバー
        progress_bar = ttk.Progressbar(dialog, mode='determinate')
        progress_bar.pack(fill=tk.X, padx=10, pady=5)

        def start_collection():
            """収集開始"""
            try:
                sy = int(start_year.get())
                sm = int(start_month.get())
                ey = int(end_year.get())
                em = int(end_month.get())
                collect_horse = collect_horse_var.get()
                force = force_update_var.get()

                log_widget.insert(tk.END, f"{'='*60}\n")
                log_widget.insert(tk.END, f" 期間データ収集: {sy}年{sm}月 ～ {ey}年{em}月\n")
                log_widget.insert(tk.END, f"{'='*60}\n\n")

                # ListBasedUpdaterをインポート
                import sys
                import os
                sys.path.insert(0, os.path.join(os.getcwd(), 'scripts', 'collection'))

                from update_from_list import ListBasedUpdater

                # CSVパスを修正
                db_path = os.path.join(BASE_DIR, 'data/main/netkeiba_data_2020_2025_complete.csv')

                log_widget.insert(tk.END, f"データベースパス: {db_path}\n")

                # Updaterを初期化
                updater = ListBasedUpdater(db_path=db_path)

                log_widget.insert(tk.END, "収集を開始します...\n\n")
                dialog.update()

                # カレンダーから収集
                collected_ids = updater.collect_from_calendar(
                    sy, sm, ey, em,
                    collect_horse_details=collect_horse
                )

                log_widget.insert(tk.END, f"\n{'='*60}\n")
                log_widget.insert(tk.END, f"収集完了: {len(collected_ids)}レース\n")
                log_widget.insert(tk.END, f"{'='*60}\n")

                # データベースを再読み込み
                log_widget.insert(tk.END, "\nデータベースを再読み込み中...\n")
                self.load_data()
                log_widget.insert(tk.END, "✓ 完了!\n")

                messagebox.showinfo("完了", f"データ収集が完了しました\n収集レース数: {len(collected_ids)}")

            except Exception as e:
                import traceback
                log_widget.insert(tk.END, f"\nエラー発生:\n{traceback.format_exc()}\n")
                messagebox.showerror("エラー", f"データ収集エラー:\n{str(e)}")

        # ボタンフレーム
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)

        start_button = tk.Button(button_frame, text="▶ 収集開始", command=start_collection,
                                bg="#4CAF50", fg="white", font=("Arial", 11, "bold"), width=15)
        start_button.pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="閉じる", command=dialog.destroy,
                 font=("Arial", 11), width=15).pack(side=tk.LEFT, padx=5)


def main():
    root = tk.Tk()
    app = KeibaGUIv3(root)
    root.mainloop()


if __name__ == "__main__":
    main()
