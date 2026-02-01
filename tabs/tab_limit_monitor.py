"""
tab_limit_monitor.py — Tab 2: Limit Monitor

职责:
    展示基金合规限额监控状态
    - KPI 卡片: Total Limits / Breaches / Warnings / FX Exposure
    - 红绿灯表: 各限额状态
    - FX Gauge: 外汇敞口仪表盘
    - Top 5 Issuers: 集中度监控
    - 时间序列: Funded Status + FX % 双轴图

对外暴露: render(ctx)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ============================================================
# 颜色常量 (与 app.py GLOBAL_CSS 保持一致)
# ============================================================
COLOR_BG = "#0f1923"
COLOR_CARD = "#162232"
COLOR_BORDER = "#1e3a5f"
COLOR_PRIMARY = "#00b4d8"      # 冰蓝
COLOR_SECONDARY = "#8a9bb0"    # 灰蓝
COLOR_OK = "#00c9a7"           # 绿
COLOR_WARN = "#f9a825"         # 橙
COLOR_BREACH = "#e74c3c"       # 红


def render(ctx: dict):
    """
    Tab 2 主入口。从 ctx 取数据，渲染所有组件。
    """
    # ─────────────────────────────────────────────────────────
    # 数据准备
    # ─────────────────────────────────────────────────────────
    limits_df = ctx['limits_df']
    issuer_df = ctx['issuer_df']
    fx_pct = ctx['fx_pct']
    ts_df = ctx['time_series_df']

    # 统计 breach / warn 数量
    n_total = len(limits_df)
    n_breach = len(limits_df[limits_df['Status'].str.contains('BREACH')])
    n_warn = len(limits_df[limits_df['Status'].str.contains('WARN')])

    # ─────────────────────────────────────────────────────────
    # Row 1: KPI 卡片
    # ─────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(label="Total Limits", value=n_total)
    with c2:
        st.metric(label="🔴 Breaches", value=n_breach)
    with c3:
        st.metric(label="🟡 Warnings", value=n_warn)
    with c4:
        st.metric(label="FX Exposure", value=f"{fx_pct:.1%}")

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # Row 2: 左边红绿灯表 + 右边 FX Gauge & Issuer 表
    # ─────────────────────────────────────────────────────────
    col_left, col_right = st.columns([6, 4])

    with col_left:
        st.markdown("#### 📊 Limits Status")
        _render_limits_table(limits_df)

    with col_right:
        st.markdown("#### 🎯 FX Exposure")
        _render_fx_gauge(fx_pct)

        st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)

        st.markdown("#### 📋 Top 5 Issuers")
        _render_issuer_table(issuer_df)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # Row 3: 时间序列图 (双Y轴)
    # ─────────────────────────────────────────────────────────
    st.markdown("#### 📈 Trend: Funded Status & FX Exposure")
    _render_time_series(ts_df)


# ============================================================
# 私有渲染函数
# ============================================================

def _render_limits_table(limits_df: pd.DataFrame):
    """
    渲染红绿灯表，显示各限额状态。
    """
    # 准备显示用的 DataFrame
    display_df = limits_df[['asset_class', 'current_weight', 'policy_target', 
                            'range_min', 'range_max', 'Status']].copy()

    # 重命名列
    display_df.columns = ['Limit', 'Actual', 'Target', 'Min', 'Max', 'Status']

    # 格式化百分比
    for col in ['Actual', 'Target', 'Min', 'Max']:
        display_df[col] = display_df[col].apply(lambda x: f"{x:.1%}" if abs(x) < 10 else f"{x:.1%}")

    # 用 Streamlit dataframe 显示，带颜色
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Limit": st.column_config.TextColumn("Limit", width="medium"),
            "Actual": st.column_config.TextColumn("Actual", width="small"),
            "Target": st.column_config.TextColumn("Target", width="small"),
            "Min": st.column_config.TextColumn("Min", width="small"),
            "Max": st.column_config.TextColumn("Max", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
        height=320,
    )


def _render_fx_gauge(fx_pct: float):
    """
    渲染 FX 敞口仪表盘。
    阈值: 15%
    颜色区间: 绿(0-12%), 黄(12-15%), 红(>15%)
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=fx_pct * 100,  # 转换为百分比数值
        number={'suffix': '%', 'font': {'size': 36, 'color': COLOR_PRIMARY}},
        gauge={
            'axis': {
                'range': [0, 25],
                'tickwidth': 1,
                'tickcolor': COLOR_SECONDARY,
                'tickfont': {'color': COLOR_SECONDARY},
            },
            'bar': {'color': COLOR_PRIMARY, 'thickness': 0.7},
            'bgcolor': COLOR_CARD,
            'borderwidth': 1,
            'bordercolor': COLOR_BORDER,
            'steps': [
                {'range': [0, 12], 'color': 'rgba(0, 201, 167, 0.3)'},   # 绿区
                {'range': [12, 15], 'color': 'rgba(249, 168, 37, 0.3)'}, # 黄区
                {'range': [15, 25], 'color': 'rgba(231, 76, 60, 0.3)'},  # 红区
            ],
            'threshold': {
                'line': {'color': COLOR_BREACH, 'width': 3},
                'thickness': 0.8,
                'value': 15,  # 15% 阈值
            },
        },
    ))

    fig.update_layout(
        height=180,
        margin=dict(l=20, r=20, t=30, b=10),
        paper_bgcolor=COLOR_BG,
        font={'color': COLOR_SECONDARY},
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_issuer_table(issuer_df: pd.DataFrame):
    """
    渲染 Top 5 发行人集中度表。
    """
    display_df = issuer_df[['Issuer', 'Weight', 'Status']].copy()

    # 格式化 Weight 为百分比
    display_df['Weight'] = display_df['Weight'].apply(lambda x: f"{x:.2%}")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=200,
    )


def _render_time_series(ts_df: pd.DataFrame):
    """
    渲染双 Y 轴时间序列图:
    - 左轴: Funded Status (%)
    - 右轴: FX Exposure (%)
    - 阈值线: 111% (Funded Status), 15% (FX)
    """
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # ── Funded Status (左轴) ──
    fig.add_trace(
        go.Scatter(
            x=ts_df['date'],
            y=ts_df['funded_status'] * 100,
            name='Funded Status',
            line=dict(color=COLOR_PRIMARY, width=2.5),
            mode='lines+markers',
            marker=dict(size=6),
        ),
        secondary_y=False,
    )

    # ── FX Exposure (右轴) ──
    fig.add_trace(
        go.Scatter(
            x=ts_df['date'],
            y=ts_df['fx_pct'] * 100,
            name='FX Exposure',
            line=dict(color=COLOR_SECONDARY, width=2),
            mode='lines+markers',
            marker=dict(size=5),
        ),
        secondary_y=True,
    )

    # ── 阈值线: Funded Status 111% ──
    fig.add_hline(
        y=111,
        line_dash="dash",
        line_color=COLOR_OK,
        line_width=1.5,
        annotation_text="111% Target",
        annotation_position="right",
        annotation_font_color=COLOR_OK,
        secondary_y=False,
    )

    # ── 阈值线: FX 15% ──
    fig.add_hline(
        y=15,
        line_dash="dash",
        line_color=COLOR_BREACH,
        line_width=1.5,
        annotation_text="15% FX Limit",
        annotation_position="right",
        annotation_font_color=COLOR_BREACH,
        secondary_y=True,
    )

    # ── 布局设置 ──
    fig.update_layout(
        height=350,
        margin=dict(l=10, r=10, t=40, b=40),
        paper_bgcolor=COLOR_BG,
        plot_bgcolor=COLOR_BG,
        font={'color': COLOR_SECONDARY},
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=12),
        ),
        hovermode='x unified',
    )

    # 左 Y 轴
    fig.update_yaxes(
        title_text="Funded Status (%)",
        secondary_y=False,
        range=[105, 115],
        gridcolor=COLOR_BORDER,
        ticksuffix="%",
    )

    # 右 Y 轴
    fig.update_yaxes(
        title_text="FX Exposure (%)",
        secondary_y=True,
        range=[0, 25],
        gridcolor=COLOR_BORDER,
        ticksuffix="%",
    )

    # X 轴
    fig.update_xaxes(
        gridcolor=COLOR_BORDER,
        tickformat="%m/%d",
    )

    st.plotly_chart(fig, use_container_width=True)