"""
EDA Dashboard - インタラクティブデータ探索
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(page_title="競馬データEDA", layout="wide")

# タイトル
st.title("競馬データ探索ダッシュボード")
st.markdown("---")

# データ読み込み
@st.cache_data
def load_data():
    """データ読み込みとキャッシュ"""
    df = pd.read_csv('netkeiba_data_2020_2024_enhanced.csv', low_memory=False)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')

    # 数値変換
    df['着順_num'] = pd.to_numeric(df['着順'], errors='coerce')
    df['単勝_num'] = pd.to_numeric(df['単勝'], errors='coerce')
    df['人気_num'] = pd.to_numeric(df['人気'], errors='coerce')
    df['distance_num'] = pd.to_numeric(df['distance'], errors='coerce')
    df['total_win_rate_num'] = pd.to_numeric(df['total_win_rate'], errors='coerce')

    return df

try:
    df = load_data()
    st.success(f"データ読み込み完了: {len(df):,}行、{df['race_id'].nunique():,}レース")
except Exception as e:
    st.error(f"データ読み込みエラー: {e}")
    st.stop()

# サイドバー - フィルター
st.sidebar.header("フィルター設定")

# 年フィルター
years = sorted(df['date'].dt.year.dropna().unique())
selected_years = st.sidebar.multiselect(
    "年を選択",
    years,
    default=years
)

# コース種別フィルター
if 'course_type' in df.columns:
    course_types = df['course_type'].dropna().unique()
    selected_courses = st.sidebar.multiselect(
        "コース種別",
        course_types,
        default=course_types
    )
else:
    selected_courses = []

# 馬場状態フィルター
if 'track_condition' in df.columns:
    conditions = df['track_condition'].dropna().unique()
    selected_conditions = st.sidebar.multiselect(
        "馬場状態",
        conditions,
        default=conditions
    )
else:
    selected_conditions = []

# データフィルタリング
filtered_df = df.copy()
if selected_years:
    filtered_df = filtered_df[filtered_df['date'].dt.year.isin(selected_years)]
if selected_courses and 'course_type' in df.columns:
    filtered_df = filtered_df[filtered_df['course_type'].isin(selected_courses)]
if selected_conditions and 'track_condition' in df.columns:
    filtered_df = filtered_df[filtered_df['track_condition'].isin(selected_conditions)]

st.sidebar.markdown(f"**フィルター後: {len(filtered_df):,}行**")

# タブ構成
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "データ概要",
    "勝率分析",
    "オッズ分析",
    "距離・コース分析",
    "騎手・調教師分析",
    "時系列分析"
])

# ===== タブ1: データ概要 =====
with tab1:
    st.header("データ概要")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("総レース数", f"{filtered_df['race_id'].nunique():,}")
    with col2:
        st.metric("総出走数", f"{len(filtered_df):,}")
    with col3:
        avg_horses = len(filtered_df) / filtered_df['race_id'].nunique()
        st.metric("平均出走頭数", f"{avg_horses:.1f}")
    with col4:
        if 'total_starts' in filtered_df.columns:
            stats_cov = filtered_df['total_starts'].notna().sum() / len(filtered_df) * 100
            st.metric("統計カバー率", f"{stats_cov:.1f}%")

    st.subheader("年別統計")
    yearly_stats = []
    for year in sorted(filtered_df['date'].dt.year.dropna().unique()):
        year_df = filtered_df[filtered_df['date'].dt.year == year]
        yearly_stats.append({
            '年': int(year),
            'レース数': year_df['race_id'].nunique(),
            '出走数': len(year_df),
            '平均出走頭数': len(year_df) / year_df['race_id'].nunique()
        })

    yearly_df = pd.DataFrame(yearly_stats)
    st.dataframe(yearly_df, use_container_width=True)

    # 年別レース数推移
    fig = px.bar(yearly_df, x='年', y='レース数', title='年別レース数推移')
    st.plotly_chart(fig, use_container_width=True)

# ===== タブ2: 勝率分析 =====
with tab2:
    st.header("勝率分析")

    # 人気別勝率
    st.subheader("人気別勝率")
    if '人気_num' in filtered_df.columns and '着順_num' in filtered_df.columns:
        popularity_stats = []
        for pop in sorted(filtered_df['人気_num'].dropna().unique()):
            if pop <= 18:  # 人気18番以内
                pop_df = filtered_df[filtered_df['人気_num'] == pop]
                win_rate = (pop_df['着順_num'] == 1).sum() / len(pop_df) * 100
                top3_rate = (pop_df['着順_num'] <= 3).sum() / len(pop_df) * 100
                popularity_stats.append({
                    '人気': int(pop),
                    '出走数': len(pop_df),
                    '勝率(%)': win_rate,
                    '複勝率(%)': top3_rate
                })

        pop_df_stats = pd.DataFrame(popularity_stats)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(pop_df_stats, x='人気', y='勝率(%)',
                        title='人気別勝率',
                        color='勝率(%)',
                        color_continuous_scale='Blues')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.line(pop_df_stats, x='人気', y=['勝率(%)', '複勝率(%)'],
                         title='人気別勝率・複勝率',
                         markers=True)
            st.plotly_chart(fig, use_container_width=True)

    # 馬場状態別勝率
    if 'track_condition' in filtered_df.columns and '着順_num' in filtered_df.columns:
        st.subheader("馬場状態別勝率")
        condition_stats = []
        for condition in filtered_df['track_condition'].dropna().unique():
            cond_df = filtered_df[filtered_df['track_condition'] == condition]
            win_rate = (cond_df['着順_num'] == 1).sum() / len(cond_df) * 100
            condition_stats.append({
                '馬場状態': condition,
                '出走数': len(cond_df),
                '勝率(%)': win_rate
            })

        cond_df_stats = pd.DataFrame(condition_stats)
        fig = px.bar(cond_df_stats, x='馬場状態', y='勝率(%)',
                    title='馬場状態別勝率',
                    color='勝率(%)',
                    text='出走数')
        st.plotly_chart(fig, use_container_width=True)

# ===== タブ3: オッズ分析 =====
with tab3:
    st.header("オッズ分析")

    if '単勝_num' in filtered_df.columns:
        # オッズ分布
        st.subheader("オッズ分布")
        odds_data = filtered_df['単勝_num'].dropna()
        odds_data = odds_data[odds_data <= 100]  # 100倍以下に限定

        col1, col2 = st.columns(2)
        with col1:
            fig = px.histogram(odds_data, nbins=50,
                             title='オッズ分布（100倍以下）',
                             labels={'value': 'オッズ', 'count': '頻度'})
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            stats = odds_data.describe()
            st.write("**オッズ統計**")
            st.write(f"- 平均: {stats['mean']:.2f}倍")
            st.write(f"- 中央値: {stats['50%']:.2f}倍")
            st.write(f"- 最小: {stats['min']:.2f}倍")
            st.write(f"- 最大: {odds_data.max():.2f}倍")

        # オッズ帯別勝率
        if '着順_num' in filtered_df.columns:
            st.subheader("オッズ帯別勝率")
            odds_ranges = [
                (0, 3, '1.0-2.9倍'),
                (3, 5, '3.0-4.9倍'),
                (5, 10, '5.0-9.9倍'),
                (10, 20, '10-19.9倍'),
                (20, 50, '20-49.9倍'),
                (50, 100, '50-99.9倍'),
                (100, 1000, '100倍以上')
            ]

            odds_stats = []
            for min_odds, max_odds, label in odds_ranges:
                range_df = filtered_df[
                    (filtered_df['単勝_num'] >= min_odds) &
                    (filtered_df['単勝_num'] < max_odds)
                ]
                if len(range_df) > 0:
                    win_rate = (range_df['着順_num'] == 1).sum() / len(range_df) * 100
                    odds_stats.append({
                        'オッズ帯': label,
                        '出走数': len(range_df),
                        '勝率(%)': win_rate
                    })

            odds_stats_df = pd.DataFrame(odds_stats)
            fig = px.bar(odds_stats_df, x='オッズ帯', y='勝率(%)',
                        title='オッズ帯別勝率',
                        color='勝率(%)',
                        text='出走数')
            st.plotly_chart(fig, use_container_width=True)

# ===== タブ4: 距離・コース分析 =====
with tab4:
    st.header("距離・コース分析")

    if 'distance_num' in filtered_df.columns and '着順_num' in filtered_df.columns:
        # 距離帯別分析
        st.subheader("距離帯別勝率")
        distance_ranges = [
            (1000, 1400, '短距離(1000-1399m)'),
            (1400, 1800, 'マイル(1400-1799m)'),
            (1800, 2200, '中距離(1800-2199m)'),
            (2200, 3000, '長距離(2200m以上)')
        ]

        dist_stats = []
        for min_dist, max_dist, label in distance_ranges:
            dist_df = filtered_df[
                (filtered_df['distance_num'] >= min_dist) &
                (filtered_df['distance_num'] < max_dist)
            ]
            if len(dist_df) > 0:
                win_rate = (dist_df['着順_num'] == 1).sum() / len(dist_df) * 100
                avg_odds = dist_df['単勝_num'].mean()
                dist_stats.append({
                    '距離帯': label,
                    'レース数': dist_df['race_id'].nunique(),
                    '出走数': len(dist_df),
                    '勝率(%)': win_rate,
                    '平均オッズ': avg_odds
                })

        dist_stats_df = pd.DataFrame(dist_stats)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.bar(dist_stats_df, x='距離帯', y='出走数',
                        title='距離帯別出走数')
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(dist_stats_df, x='距離帯', y='勝率(%)',
                        title='距離帯別勝率',
                        color='勝率(%)')
            st.plotly_chart(fig, use_container_width=True)

    # コース種別分析
    if 'course_type' in filtered_df.columns:
        st.subheader("コース種別統計")
        course_stats = []
        for course in filtered_df['course_type'].dropna().unique():
            course_df = filtered_df[filtered_df['course_type'] == course]
            course_stats.append({
                'コース': course,
                'レース数': course_df['race_id'].nunique(),
                '出走数': len(course_df),
                '平均距離': course_df['distance_num'].mean()
            })

        course_stats_df = pd.DataFrame(course_stats)
        st.dataframe(course_stats_df, use_container_width=True)

# ===== タブ5: 騎手・調教師分析 =====
with tab5:
    st.header("騎手・調教師分析")

    if '騎手' in filtered_df.columns and '着順_num' in filtered_df.columns:
        st.subheader("騎手TOP20")

        jockey_stats = []
        for jockey in filtered_df['騎手'].dropna().unique():
            jockey_df = filtered_df[filtered_df['騎手'] == jockey]
            if len(jockey_df) >= 50:  # 50レース以上のみ
                wins = (jockey_df['着順_num'] == 1).sum()
                win_rate = wins / len(jockey_df) * 100
                jockey_stats.append({
                    '騎手': jockey,
                    '騎乗数': len(jockey_df),
                    '勝利数': wins,
                    '勝率(%)': win_rate
                })

        jockey_df_stats = pd.DataFrame(jockey_stats)
        jockey_df_stats = jockey_df_stats.sort_values('勝率(%)', ascending=False).head(20)

        fig = px.bar(jockey_df_stats, x='騎手', y='勝率(%)',
                    title='騎手別勝率TOP20（50レース以上）',
                    color='勝率(%)',
                    hover_data=['騎乗数', '勝利数'])
        fig.update_xaxis(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

    if '調教師' in filtered_df.columns and '着順_num' in filtered_df.columns:
        st.subheader("調教師TOP20")

        trainer_stats = []
        for trainer in filtered_df['調教師'].dropna().unique():
            trainer_df = filtered_df[filtered_df['調教師'] == trainer]
            if len(trainer_df) >= 50:
                wins = (trainer_df['着順_num'] == 1).sum()
                win_rate = wins / len(trainer_df) * 100
                trainer_stats.append({
                    '調教師': trainer,
                    '管理頭数': len(trainer_df),
                    '勝利数': wins,
                    '勝率(%)': win_rate
                })

        trainer_df_stats = pd.DataFrame(trainer_stats)
        trainer_df_stats = trainer_df_stats.sort_values('勝率(%)', ascending=False).head(20)

        fig = px.bar(trainer_df_stats, x='調教師', y='勝率(%)',
                    title='調教師別勝率TOP20（50レース以上）',
                    color='勝率(%)',
                    hover_data=['管理頭数', '勝利数'])
        fig.update_xaxis(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

# ===== タブ6: 時系列分析 =====
with tab6:
    st.header("時系列分析")

    # 月別レース数推移
    st.subheader("月別レース数推移")
    filtered_df['年月'] = filtered_df['date'].dt.to_period('M').astype(str)
    monthly_races = filtered_df.groupby('年月')['race_id'].nunique().reset_index()
    monthly_races.columns = ['年月', 'レース数']

    fig = px.line(monthly_races, x='年月', y='レース数',
                 title='月別レース数推移',
                 markers=True)
    fig.update_xaxis(tickangle=45)
    st.plotly_chart(fig, use_container_width=True)

    # 月別平均オッズ推移
    if '単勝_num' in filtered_df.columns:
        st.subheader("月別平均オッズ推移")
        monthly_odds = filtered_df.groupby('年月')['単勝_num'].mean().reset_index()
        monthly_odds.columns = ['年月', '平均オッズ']

        fig = px.line(monthly_odds, x='年月', y='平均オッズ',
                     title='月別平均オッズ推移',
                     markers=True)
        fig.update_xaxis(tickangle=45)
        st.plotly_chart(fig, use_container_width=True)

# フッター
st.markdown("---")
st.markdown(f"最終更新: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
