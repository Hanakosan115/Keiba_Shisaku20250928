"""
NetKeiba 競馬データ収集・分析ダッシュボード
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import os
import json

# ページ設定
st.set_page_config(
    page_title="NetKeiba データ収集ツール",
    page_icon="🏇",
    layout="wide",
    initial_sidebar_state="expanded"
)

# タイトル
st.title("🏇 NetKeiba データ収集・分析ダッシュボード")

# サイドバー
st.sidebar.title("📊 メニュー")
menu = st.sidebar.radio(
    "選択",
    ["データ収集", "進捗モニター", "データ概要", "統計表示", "ログビューア", "設定"]
)

# ===================================================================
# データ収集コントロール
# ===================================================================
if menu == "データ収集":
    st.header("🎯 データ収集コントロール")

    # 現在のデータ状況を確認
    if os.path.exists('netkeiba_data_2020_2024_enhanced.csv'):
        df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

        st.subheader("📊 現在のデータベース状況")

        col1, col2, col3 = st.columns(3)

        with col1:
            total_races = df['race_id'].nunique()
            st.metric("総レース数", f"{total_races:,}")

        with col2:
            df_2025 = df[df['race_id'].astype(str).str.startswith('2025')]
            races_2025 = df_2025['race_id'].nunique()
            st.metric("2025年レース", f"{races_2025:,}")

        with col3:
            # 統計データあり
            stats_filled = df['total_starts'].notna().sum()
            stats_pct = (stats_filled / len(df) * 100) if len(df) > 0 else 0
            st.metric("統計データ率", f"{stats_pct:.1f}%")

        st.divider()

        # 年別・月別データ状況
        st.subheader("📅 年別・月別データ状況")

        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df['year'] = df['date'].dt.year
        df['month'] = df['date'].dt.month

        # 2025年の月別カバー率
        df_2025_detail = df[df['year'] == 2025].copy()
        if len(df_2025_detail) > 0:
            monthly_stats = []
            for month in range(1, 13):
                df_month = df_2025_detail[df_2025_detail['month'] == month]
                if len(df_month) > 0:
                    races = df_month['race_id'].nunique()
                    with_stats = df_month['total_starts'].notna().sum()
                    stats_rate = (with_stats / len(df_month) * 100) if len(df_month) > 0 else 0
                    monthly_stats.append({
                        '月': f"{month}月",
                        'レース数': races,
                        '統計データ率': f"{stats_rate:.1f}%"
                    })

            if monthly_stats:
                st.dataframe(pd.DataFrame(monthly_stats), use_container_width=True)

        st.divider()

        # 収集コントロール
        st.subheader("🚀 新規データ収集")

        col1, col2 = st.columns(2)

        with col1:
            year = st.selectbox(
                "収集年",
                [2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015],
                key="collect_year"
            )

        with col2:
            month = st.selectbox(
                "収集月",
                ["全月"] + [f"{m}月" for m in range(1, 13)],
                key="collect_month"
            )

        collect_type = st.radio(
            "収集タイプ",
            ["統計データ追加（既存レースに馬統計を追加）", "新規レース収集（Selenium使用）"],
            key="collect_type"
        )

        force_update = st.checkbox(
            "強制更新（既存データも再収集）",
            value=False,
            key="force_update"
        )

        st.info(f"""
        **選択内容:**
        - 対象: {year}年 {month}
        - タイプ: {collect_type}
        - 強制更新: {'ON' if force_update else 'OFF'}
        """)

        # 実行ボタン
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("🚀 収集開始", type="primary", use_container_width=True):
                st.warning("⚠️ この機能は現在開発中です。コマンドラインからの実行をお願いします。")

                # 実行コマンドを生成
                if month == "全月":
                    month_str = "all"
                else:
                    month_str = month.replace("月", "")

                st.code(f"""
# コマンドライン実行例：
cd Keiba_Shisaku20250928

# {year}年{month}の統計データ追加
py -c "from update_from_list import ListBasedUpdater; import pandas as pd; df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv'); df['date'] = pd.to_datetime(df['date'], errors='coerce'); race_ids = df[(df['date'].dt.year == {year}) {'& (df[\"date\"].dt.month == ' + month_str + ')' if month_str != 'all' else ''}]['race_id'].unique().tolist(); updater = ListBasedUpdater('netkeiba_data_2020_2024_enhanced.csv', 'horse_past_results.csv'); updater._collect_races(race_ids, collect_horse_details=True, force_update={str(force_update)})"
                """, language="bash")

        with col2:
            if st.button("⏸️ 停止", use_container_width=True):
                st.info("収集プロセスを停止する場合は、実行中のPythonプロセスを終了してください。")
    else:
        st.warning("データベースファイルが見つかりません。")

# ===================================================================
# 進捗モニター
# ===================================================================
elif menu == "進捗モニター":
    st.header("📈 データ収集進捗モニター")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 進捗ファイル読み込み
        progress_file = 'collection_progress.json'
        if os.path.exists(progress_file):
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)

            processed_count = len(progress_data.get('processed_race_ids', []))
            horses_count = progress_data.get('horses_processed_count', 0)
            timestamp = progress_data.get('timestamp', '不明')

            # 総レース数を進捗ファイルから取得、なければ処理済み数を使用
            total_races = max(processed_count, 240)
            progress_pct = (processed_count / total_races) * 100 if total_races > 0 else 0

            # 進捗バーの値を0.0-1.0に制限
            progress_value = min(progress_pct / 100, 1.0)

            st.metric("処理済みレース", f"{processed_count}/{total_races}", f"{progress_pct:.1f}%")
            st.progress(progress_value)

            st.metric("処理済み馬数", horses_count)
            st.info(f"最終更新: {timestamp}")

            # 残り時間推定
            if processed_count > 0:
                avg_time_per_race = 3.5  # 分（推定）
                remaining_races = total_races - processed_count
                remaining_minutes = remaining_races * avg_time_per_race
                remaining_hours = remaining_minutes / 60

                st.metric("残り推定時間", f"約{remaining_hours:.1f}時間")

        else:
            st.warning("進捗ファイルが見つかりません。収集が開始されていないか、完了しています。")

    with col2:
        # ステータス表示
        st.subheader("📊 ステータス")

        if os.path.exists(progress_file):
            st.success("🔄 収集実行中")
        else:
            st.info("⏸️ 待機中")

        # リフレッシュボタン
        if st.button("🔄 更新", key="refresh_progress"):
            st.rerun()

    # データベース統計
    st.subheader("📁 データベース統計")

    if os.path.exists('netkeiba_data_2020_2024_enhanced.csv'):
        try:
            df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_rows = len(df)
                st.metric("総レコード数", f"{total_rows:,}")

            with col2:
                unique_races = df['race_id'].nunique() if 'race_id' in df.columns else 0
                st.metric("ユニークレース数", f"{unique_races:,}")

            with col3:
                # 2025年データ
                df_2025 = df[df['race_id'].astype(str).str.startswith('2025')]
                st.metric("2025年レース", f"{len(df_2025['race_id'].unique()):,}")

            with col4:
                # 統計列カバー率
                stat_cols = ['total_starts', 'total_win_rate', 'total_earnings']
                has_stats = sum([col in df.columns for col in stat_cols])
                st.metric("統計列", f"{has_stats}/{len(stat_cols)}")

        except Exception as e:
            st.error(f"データベース読み込みエラー: {e}")
    else:
        st.warning("データベースファイルが見つかりません")

# ===================================================================
# データ概要
# ===================================================================
elif menu == "データ概要":
    st.header("📊 データ概要")

    if os.path.exists('netkeiba_data_2020_2024_enhanced.csv'):
        try:
            df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

            # 基本情報
            st.subheader("📈 基本統計")
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("総レコード数", f"{len(df):,}")
                st.metric("総列数", f"{len(df.columns)}")

            with col2:
                if 'race_id' in df.columns:
                    st.metric("ユニークレース", f"{df['race_id'].nunique():,}")
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'], errors='coerce')
                    st.metric("期間", f"{df['date'].min().year} - {df['date'].max().year}")

            with col3:
                # 統計列の確認
                stat_cols = ['father', 'mother_father', 'total_starts', 'total_win_rate',
                            'turf_win_rate', 'dirt_win_rate', 'total_earnings']
                existing_stat_cols = [col for col in stat_cols if col in df.columns]
                st.metric("統計列数", f"{len(existing_stat_cols)}/{len(stat_cols)}")

            # 年別レース数
            st.subheader("📅 年別レース数")
            if 'date' in df.columns:
                df['year'] = df['date'].dt.year
                year_counts = df.groupby('year')['race_id'].nunique().reset_index()
                year_counts.columns = ['年', 'レース数']

                fig = px.bar(year_counts, x='年', y='レース数',
                           title="年別ユニークレース数")
                st.plotly_chart(fig, use_container_width=True)

            # 統計列カバー率
            if existing_stat_cols:
                st.subheader("📊 統計列カバー率")

                coverage_data = []
                for col in existing_stat_cols:
                    total = len(df)
                    filled = df[col].notna().sum()
                    pct = (filled / total * 100) if total > 0 else 0
                    coverage_data.append({'列名': col, 'カバー率(%)': pct, '件数': filled})

                coverage_df = pd.DataFrame(coverage_data)

                fig = px.bar(coverage_df, x='列名', y='カバー率(%)',
                           title="統計列データカバー率",
                           text='カバー率(%)')
                fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                st.plotly_chart(fig, use_container_width=True)

                st.dataframe(coverage_df, use_container_width=True)

        except Exception as e:
            st.error(f"エラー: {e}")
    else:
        st.warning("データベースファイルが見つかりません")

# ===================================================================
# 統計表示
# ===================================================================
elif menu == "統計表示":
    st.header("📈 統計分析")

    if os.path.exists('netkeiba_data_2020_2024_enhanced.csv'):
        try:
            df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)

            # 月別フィルター
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df['year_month'] = df['date'].dt.to_period('M').astype(str)

                selected_period = st.selectbox(
                    "期間選択",
                    ["全期間"] + sorted(df['year_month'].dropna().unique().tolist(), reverse=True)
                )

                if selected_period != "全期間":
                    df_filtered = df[df['year_month'] == selected_period]
                else:
                    df_filtered = df

                st.info(f"選択期間のレコード数: {len(df_filtered):,}件")
            else:
                df_filtered = df

            # 統計列がある場合
            stat_cols = ['total_starts', 'total_win_rate', 'turf_win_rate',
                        'dirt_win_rate', 'total_earnings']
            existing_stat_cols = [col for col in stat_cols if col in df_filtered.columns]

            if existing_stat_cols:
                st.subheader("🔢 統計サマリー")

                summary_data = df_filtered[existing_stat_cols].describe().T
                st.dataframe(summary_data, use_container_width=True)

                # ヒストグラム
                selected_col = st.selectbox("表示する統計", existing_stat_cols)

                if selected_col:
                    fig = px.histogram(df_filtered, x=selected_col,
                                     title=f"{selected_col} の分布",
                                     nbins=50)
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("統計列がまだ収集されていません")

        except Exception as e:
            st.error(f"エラー: {e}")
    else:
        st.warning("データベースファイルが見つかりません")

# ===================================================================
# ログビューア
# ===================================================================
elif menu == "ログビューア":
    st.header("📋 ログビューア")

    # 進捗ファイルの内容
    progress_file = 'collection_progress.json'
    if os.path.exists(progress_file):
        st.subheader("📄 進捗ファイル")

        with open(progress_file, 'r', encoding='utf-8') as f:
            progress_data = json.load(f)

        st.json(progress_data)

        # 処理済みレースID一覧
        if 'processed_race_ids' in progress_data:
            processed_ids = progress_data['processed_race_ids']
            st.subheader(f"処理済みレースID ({len(processed_ids)}件)")

            # 最新10件を表示
            st.text("最新10件:")
            for rid in processed_ids[-10:]:
                st.code(rid)
    else:
        st.info("進捗ファイルがありません")

# ===================================================================
# 設定
# ===================================================================
elif menu == "設定":
    st.header("⚙️ 設定")

    st.subheader("📁 ファイルパス")

    files = {
        "メインDB": "netkeiba_data_2020_2024_enhanced.csv",
        "過去戦績": "horse_past_results.csv",
        "進捗ファイル": "collection_progress.json",
        "レースIDリスト": "race_ids_2025_january_by_date.txt"
    }

    for name, path in files.items():
        if os.path.exists(path):
            size = os.path.getsize(path) / (1024 * 1024)  # MB
            st.success(f"✅ {name}: {path} ({size:.2f} MB)")
        else:
            st.error(f"❌ {name}: {path} (見つかりません)")

    st.subheader("🔄 リフレッシュ設定")

    auto_refresh = st.checkbox("自動更新を有効にする", value=False)

    if auto_refresh:
        refresh_interval = st.slider("更新間隔（秒）", 5, 60, 10)
        st.info(f"{refresh_interval}秒ごとに自動更新されます")

        # 自動リフレッシュ
        import time
        time.sleep(refresh_interval)
        st.rerun()

# フッター
st.sidebar.markdown("---")
st.sidebar.info(f"更新時刻: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
