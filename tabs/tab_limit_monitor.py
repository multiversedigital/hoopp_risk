"""
tab_limit_monitor.py — Tab 2: Limit Monitor

职责:
    展示基金合规限额监控状态
    - KPI 卡片: Total Limits / Breaches / Warnings / FX Exposure
    - 红绿灯表 + Top 5 Issuers 并排
    - FX Gauge + 时间序列并排

布局:
    Row 1: 4 个 KPI 卡片
    Row 2: [Limit Status Table] | [Top 5 Issuers Table]  (5:5)
    Row 3: [FX Gauge] | [Trend Chart]  (4:6)

对外暴露: render(ctx)

更新: 使用 ui_components 统一样式
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# ============================================================
# 导入统一 UI 组件库
# ============================================================
from ui_components import (
    COLORS,
    get_chart_layout,
    render_section_header,
    format_percent,
)


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
        st.metric(
            label="No. Limits",
            value=n_total,
            delta="—",
            delta_color="off"
        )
    with c2:
        st.metric(
            label="Breaches",
            value=n_breach,
            delta="🔴" if n_breach > 0 else "✓",
            delta_color="inverse" if n_breach > 0 else "off"
        )
    with c3:
        st.metric(
            label="Warnings",
            value=n_warn,
            delta="🟡" if n_warn > 0 else "✓",
            delta_color="off"
        )
    with c4:
        fx_status = "🔴 Over limit" if fx_pct > 0.15 else "✓ OK"
        st.metric(
            label="FX Exposure",
            value=format_percent(fx_pct),
            delta=fx_status,
            delta_color="inverse" if fx_pct > 0.15 else "off"
        )

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # Row 2: Limit Status Table | Top 5 Issuers Table (并排)
    # ─────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)

    with col_left:
        render_section_header("Limit Status", "📊")
        _render_limits_table(limits_df)

    with col_right:
        render_section_header("Top 5 Issuers", "📋")
        _render_issuer_table(issuer_df)

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # Row 3: FX Gauge | Trend Chart (并排)
    # ─────────────────────────────────────────────────────────
    col_gauge, col_trend = st.columns([4, 6])

    with col_gauge:
        render_section_header("FX Exposure Gauge", "🎯")
        _render_fx_gauge(fx_pct)

    with col_trend:
        render_section_header("Trend: FX", "📈")
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
        height=300,
    )


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
        column_config={
            "Issuer": st.column_config.TextColumn("Issuer", width="large"),
            "Weight": st.column_config.TextColumn("Weight", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
        },
        height=300,
    )


def _render_fx_gauge(fx_pct: float):
    """
    渲染 FX 敞口仪表盘。
    阈值: 15%
    颜色区间: 绿(0-12%), 黄(12-15%), 红(>15%)
    """
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=fx_pct * 100,
        number={
            'suffix': '%',
            'font': {'size': 42, 'color': COLORS['text_primary'], 'family': 'Inter'}
        },
        gauge={
            'axis': {
                'range': [0, 25],
                'tickwidth': 1,
                'tickcolor': COLORS['text_tertiary'],
                'tickfont': {'color': COLORS['text_tertiary'], 'size': 10},
            },
            'bar': {'color': COLORS['accent'], 'thickness': 0.75},
            'bgcolor': COLORS['bg_card'],
            'borderwidth': 1,
            'bordercolor': COLORS['bg_border'],
            'steps': [
                {'range': [0, 12], 'color': f"rgba(16, 185, 129, 0.2)"},    # 绿区
                {'range': [12, 15], 'color': f"rgba(245, 158, 11, 0.2)"},   # 黄区
                {'range': [15, 25], 'color': f"rgba(239, 68, 68, 0.2)"},    # 红区
            ],
            'threshold': {
                'line': {'color': COLORS['negative'], 'width': 3},
                'thickness': 0.85,
                'value': 15,
            },
        },
    ))

    fig.update_layout(
        height=250,
        margin=dict(l=30, r=30, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': COLORS['text_secondary']},
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_time_series(ts_df: pd.DataFrame):
    """
    渲染 FX 时间序列图:
    - 单轴: FX Exposure (%)
    - 阈值线: 15% (FX)
    """
    fig = go.Figure()

    # 格式化日期
    ts_df = ts_df.copy()
    ts_df['date_str'] = pd.to_datetime(ts_df['date']).dt.strftime('%b %d')

    # ── FX Exposure ──
    fig.add_trace(
        go.Scatter(
            x=ts_df['date_str'],
            y=ts_df['fx_pct'] * 100,
            name='FX Exposure',
            line=dict(color=COLORS['warning'], width=2),
            mode='lines+markers',
            marker=dict(size=5),
            hovertemplate='FX: %{y:.1f}%<extra></extra>'
        ),
    )

    # ── 阈值线: FX 15% ──
    fig.add_hline(
        y=15,
        line_dash="dash",
        line_color=COLORS['negative'],
        line_width=1.5,
        annotation_text="15% Limit",
        annotation_position="right",
        annotation_font_color=COLORS['negative'],
        annotation_font_size=10,
    )

    # ── 应用统一布局 ──
    base_layout = get_chart_layout(height=250)
    fig.update_layout(
        **base_layout,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
            font=dict(size=11, color=COLORS['text_secondary']),
        ),
    )

    # Y 轴
    fig.update_yaxes(
        title_text="FX Exposure (%)",
        title_font=dict(size=10, color=COLORS['text_tertiary']),
        range=[0, 25],
        gridcolor=COLORS['bg_border'],
        ticksuffix="%",
        tickfont=dict(size=9, color=COLORS['text_tertiary']),
    )

    # X 轴
    fig.update_xaxes(
        gridcolor=COLORS['bg_border'],
        tickfont=dict(size=9, color=COLORS['text_tertiary']),
        tickangle=-45,
    )

    st.plotly_chart(fig, use_container_width=True)