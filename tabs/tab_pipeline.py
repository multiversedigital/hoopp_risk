"""
tab_pipeline.py — Tab 4: Data Pipeline

职责:
    展示数据自动化与质量监控
    - KPI 卡片: Total Records / Missing Rate / Anomalies / Last Update
    - 列级数据质量表
    - 数据覆盖时间线
    - 异常值明细 + 数据源信息

对外暴露: render(ctx)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# ============================================================
# 颜色常量
# ============================================================
COLOR_BG = "#0f1923"
COLOR_CARD = "#162232"
COLOR_BORDER = "#1e3a5f"
COLOR_PRIMARY = "#00b4d8"
COLOR_SECONDARY = "#8a9bb0"
COLOR_OK = "#00c9a7"
COLOR_WARN = "#f9a825"
COLOR_ISSUE = "#e74c3c"

# ============================================================
# 异常值检测规则
# ============================================================
ANOMALY_RULES = {
    'mtm_cad': {'min': -50000, 'max': 50000, 'desc': 'MTM out of range'},
    'market_exposure_cad': {'min': -100000, 'max': 100000, 'desc': 'Exposure out of range'},
    'duration': {'min': -5, 'max': 30, 'desc': 'Duration out of range'},
    'equity_beta': {'min': -2, 'max': 3, 'desc': 'Beta out of range'},
    'inflation_beta': {'min': -2, 'max': 3, 'desc': 'Inflation beta out of range'},
}

# 要检查的数值列
NUMERIC_COLS = [
    'mtm_cad', 'market_exposure_cad', 'fx_exposure_cad',
    'duration', 'equity_beta', 'inflation_beta',
    'carbon_intensity', 'esg_score'
]


def render(ctx: dict):
    """
    Tab 4 主入口。
    """
    # ─────────────────────────────────────────────────────────
    # 获取数据
    # ─────────────────────────────────────────────────────────
    df_all = ctx['df_all']
    df_policy = ctx['df_policy']

    # ─────────────────────────────────────────────────────────
    # 数据质量分析
    # ─────────────────────────────────────────────────────────
    quality_df, anomalies_df, total_missing, total_anomalies = _analyze_data_quality(df_all)

    # ─────────────────────────────────────────────────────────
    # Row 1: KPI 卡片
    # ─────────────────────────────────────────────────────────
    total_records = len(df_all)
    missing_rate = total_missing / (total_records * len(df_all.columns)) * 100
    last_update = pd.Timestamp(df_all['timestamp'].max()).strftime('%Y-%m-%d')

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(label="Total Records", value=f"{total_records:,}")
    with c2:
        st.metric(label="Missing Rate", value=f"{missing_rate:.2f}%")
    with c3:
        st.metric(
            label="Anomalies",
            value=total_anomalies,
            delta="OK" if total_anomalies == 0 else f"{total_anomalies} found",
            delta_color="normal" if total_anomalies == 0 else "inverse",
        )
    with c4:
        st.metric(label="Last Update", value=last_update)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # Row 2: 列级数据质量表
    # ─────────────────────────────────────────────────────────
    st.markdown("#### 📊 Data Quality by Column")
    _render_quality_table(quality_df)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # Row 3: 数据覆盖时间线
    # ─────────────────────────────────────────────────────────
    st.markdown("#### 📈 Data Coverage Timeline")
    _render_coverage_chart(df_all)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # Row 4: 异常明细 + 数据源信息
    # ─────────────────────────────────────────────────────────
    col_left, col_right = st.columns([6, 4])

    with col_left:
        st.markdown("#### 🔍 Anomaly Details")
        _render_anomaly_details(anomalies_df)

    with col_right:
        st.markdown("#### 📋 Data Source Info")
        _render_source_info(df_all, df_policy)


# ============================================================
# 私有函数
# ============================================================

def _analyze_data_quality(df: pd.DataFrame) -> tuple:
    """
    分析数据质量，返回:
    - quality_df: 列级质量统计
    - anomalies_df: 异常值明细
    - total_missing: 总缺失数
    - total_anomalies: 总异常数
    """
    quality_rows = []
    anomalies_list = []
    total_missing = 0
    total_anomalies = 0

    for col in df.columns:
        # 缺失值统计
        missing = df[col].isnull().sum()
        missing_pct = missing / len(df) * 100
        total_missing += missing

        # 异常值检测 (仅数值列)
        anomaly_count = 0
        if col in NUMERIC_COLS and df[col].dtype in ['float64', 'int64']:
            if col in ANOMALY_RULES:
                rule = ANOMALY_RULES[col]
                mask = (df[col] < rule['min']) | (df[col] > rule['max'])
                anomaly_count = mask.sum()

                # 记录异常明细
                if anomaly_count > 0:
                    anomaly_rows = df[mask][['timestamp', col]].copy()
                    anomaly_rows['Column'] = col
                    anomaly_rows['Issue'] = rule['desc']
                    anomaly_rows = anomaly_rows.rename(columns={col: 'Value'})
                    anomalies_list.append(anomaly_rows)
            else:
                # 使用 3σ 规则
                mean = df[col].mean()
                std = df[col].std()
                if std > 0:
                    z_scores = np.abs((df[col] - mean) / std)
                    mask = z_scores > 3
                    anomaly_count = mask.sum()

                    if anomaly_count > 0:
                        anomaly_rows = df[mask][['timestamp', col]].copy()
                        anomaly_rows['Column'] = col
                        anomaly_rows['Issue'] = 'Z-score > 3'
                        anomaly_rows = anomaly_rows.rename(columns={col: 'Value'})
                        anomalies_list.append(anomaly_rows)

        total_anomalies += anomaly_count

        # 状态判断
        if missing > 0 or anomaly_count > 5:
            status = '🔴 ISSUE'
        elif anomaly_count > 0:
            status = '🟡 WARN'
        else:
            status = '🟢 OK'

        quality_rows.append({
            'Column': col,
            'Type': str(df[col].dtype),
            'Missing': missing,
            'Missing %': f"{missing_pct:.1f}%",
            'Anomalies': anomaly_count,
            'Status': status,
        })

    quality_df = pd.DataFrame(quality_rows)

    # 合并异常明细
    if anomalies_list:
        anomalies_df = pd.concat(anomalies_list, ignore_index=True)
        anomalies_df = anomalies_df[['timestamp', 'Column', 'Value', 'Issue']]
        anomalies_df = anomalies_df.head(20)  # 最多显示 20 条
    else:
        anomalies_df = pd.DataFrame(columns=['timestamp', 'Column', 'Value', 'Issue'])

    return quality_df, anomalies_df, total_missing, total_anomalies


def _render_quality_table(quality_df: pd.DataFrame):
    """
    渲染列级数据质量表。
    """
    # 只显示关键列
    key_cols = [
        'timestamp', 'asset_name', 'plan_category', 'asset_class',
        'mtm_cad', 'market_exposure_cad', 'fx_exposure_cad',
        'duration', 'equity_beta', 'inflation_beta'
    ]

    display_df = quality_df[quality_df['Column'].isin(key_cols)].copy()

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=300,
        column_config={
            "Column": st.column_config.TextColumn("Column", width="medium"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Missing": st.column_config.NumberColumn("Missing", width="small"),
            "Missing %": st.column_config.TextColumn("Miss %", width="small"),
            "Anomalies": st.column_config.NumberColumn("Anomalies", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
    )


def _render_coverage_chart(df: pd.DataFrame):
    """
    渲染数据覆盖时间线柱状图。
    """
    # 按日期统计记录数
    coverage = df.groupby('timestamp').size().reset_index(name='count')
    coverage['date'] = pd.to_datetime(coverage['timestamp']).dt.strftime('%m/%d')

    # 预期值 (假设每天 200 条)
    expected = 200

    fig = go.Figure()

    # 柱状图
    fig.add_trace(go.Bar(
        x=coverage['date'],
        y=coverage['count'],
        name='Records',
        marker_color=COLOR_PRIMARY,
        text=coverage['count'],
        textposition='outside',
        textfont=dict(color=COLOR_SECONDARY, size=11),
    ))

    # 预期线
    fig.add_hline(
        y=expected,
        line_dash="dash",
        line_color=COLOR_WARN,
        line_width=2,
        annotation_text=f"Expected: {expected}",
        annotation_position="right",
        annotation_font_color=COLOR_WARN,
    )

    fig.update_layout(
        height=250,
        margin=dict(l=10, r=10, t=30, b=40),
        paper_bgcolor=COLOR_BG,
        plot_bgcolor=COLOR_BG,
        font={'color': COLOR_SECONDARY},
        showlegend=False,
        bargap=0.3,
    )

    fig.update_xaxes(
        gridcolor=COLOR_BORDER,
        tickfont=dict(size=11),
    )

    fig.update_yaxes(
        gridcolor=COLOR_BORDER,
        title_text="Records",
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_anomaly_details(anomalies_df: pd.DataFrame):
    """
    渲染异常值明细表。
    """
    if len(anomalies_df) == 0:
        st.markdown(
            f"""
            <div style="background-color:{COLOR_CARD}; border:1px solid {COLOR_BORDER}; 
                        border-radius:8px; padding:20px; text-align:center;">
                <span style="color:{COLOR_OK}; font-size:1.2rem;">✅</span>
                <p style="color:{COLOR_SECONDARY}; margin-top:10px;">No anomalies detected</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        display_df = anomalies_df.copy()
        display_df['timestamp'] = pd.to_datetime(display_df['timestamp']).dt.strftime('%Y-%m-%d')
        display_df.columns = ['Date', 'Column', 'Value', 'Issue']

        # 格式化 Value
        display_df['Value'] = display_df['Value'].apply(
            lambda x: f"{x:,.2f}" if isinstance(x, (int, float)) else str(x)
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            height=200,
        )


def _render_source_info(df_all: pd.DataFrame, df_policy: pd.DataFrame):
    """
    渲染数据源信息。
    """
    # 统计
    n_positions = len(df_all)
    n_policies = len(df_policy)
    date_min = pd.Timestamp(df_all['timestamp'].min()).strftime('%Y-%m-%d')
    date_max = pd.Timestamp(df_all['timestamp'].max()).strftime('%Y-%m-%d')
    n_days = df_all['timestamp'].nunique()
    n_assets = df_all['asset_name'].nunique()

    info_html = f"""
    <div style="background-color:{COLOR_CARD}; border:1px solid {COLOR_BORDER}; 
                border-radius:10px; padding:16px; line-height:1.8;">
        
        <p style="color:{COLOR_PRIMARY}; font-weight:600; margin-bottom:8px;">📁 Source Files</p>
        <ul style="color:{COLOR_SECONDARY}; margin-left:20px; font-size:0.9rem;">
            <li>hoopp_positions_sample.csv ({n_positions:,} rows)</li>
            <li>policy_limit_management.csv ({n_policies} rows)</li>
        </ul>
        
        <p style="color:{COLOR_PRIMARY}; font-weight:600; margin-bottom:8px; margin-top:16px;">📅 Coverage</p>
        <ul style="color:{COLOR_SECONDARY}; margin-left:20px; font-size:0.9rem;">
            <li>Date Range: {date_min} to {date_max}</li>
            <li>Trading Days: {n_days}</li>
            <li>Unique Assets: {n_assets}</li>
        </ul>
        
        <p style="color:{COLOR_PRIMARY}; font-weight:600; margin-bottom:8px; margin-top:16px;">🔄 Refresh Mode</p>
        <ul style="color:{COLOR_SECONDARY}; margin-left:20px; font-size:0.9rem;">
            <li>Current: Manual (CSV)</li>
            <li style="color:{COLOR_WARN};">Future: SQL / API integration</li>
        </ul>
        
    </div>
    """

    st.markdown(info_html, unsafe_allow_html=True)
