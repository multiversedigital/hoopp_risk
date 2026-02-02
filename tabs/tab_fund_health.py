"""
tab_fund_health.py — Tab 1: Fund Health (全基金监控)

职责:
    展示基金整体健康状况，核心指标是 Funded Status (资金充足率)

布局:
    Row 1: 5 个 KPI 卡片
    Row 2: 组合时间序列图（Asset/Liability 柱状 + Funded Status 线）
    Row 3: 左(饼图) + 右(Actual vs Policy 柱状图)

数据源: 全部从 ctx dict 获取

更新: 使用 ui_components 统一样式
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# ============================================================
# 导入统一 UI 组件库
# ============================================================
from ui_components import (
    COLORS,
    CHART_COLORS,
    ASSET_COLORS,
    get_chart_layout,
    render_section_header,
    format_number,
    format_percent,
)


# ============================================================
# PUBLIC: render(ctx)
# ============================================================

def render(ctx: dict):
    """Tab 1 主入口，由 app.py 调用"""
    
    # ─────────────────────────────────────────────────────────
    # Row 1: KPI 卡片
    # ─────────────────────────────────────────────────────────
    _render_kpi_cards(ctx)
    
    st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────
    # Row 2: 组合时间序列图
    # ─────────────────────────────────────────────────────────
    render_section_header("Assets vs Liabilities Trend", "📈")
    fig_ts = _build_combo_time_series(ctx)
    st.plotly_chart(fig_ts, use_container_width=True)
    
    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────
    # Row 3: 饼图 + 柱状图
    # ─────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)
    
    with col_left:
        render_section_header("Asset Allocation", "🥧")
        fig_pie = _build_pie_chart(ctx)
        st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
    
    with col_right:
        render_section_header("Actual vs Policy Target", "📊")
        fig_bar = _build_comparison_bar(ctx)
        st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})


# ============================================================
# PRIVATE: KPI 卡片
# ============================================================

def _render_kpi_cards(ctx: dict):
    """渲染 5 个 KPI 卡片"""
    
    funded_status = ctx['funded_status']
    surplus       = ctx['surplus']
    total_assets  = ctx['total_assets']
    asset_dur     = ctx['asset_dur']
    liability_dur = ctx['liability_dur']
    duration_gap  = asset_dur - liability_dur
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="Funded Status",
            value=format_percent(funded_status),
            delta="Target: 111%",
            delta_color="off"
        )
    
    with col2:
        st.metric(
            label="Surplus",
            value=format_number(surplus, prefix="$"),
            delta="Assets − Liabilities",
            delta_color="off"
        )
    
    with col3:
        st.metric(
            label="Total Assets",
            value=format_number(total_assets, prefix="$"),
            delta="CAD",
            delta_color="off"
        )
    
    with col4:
        st.metric(
            label="Asset Duration",
            value=f"{asset_dur:.1f} yrs",
            delta=f"Liab: {liability_dur:.1f} yrs",
            delta_color="off"
        )
    
    with col5:
        gap_prefix = "+" if duration_gap > 0 else ""
        st.metric(
            label="Duration Gap",
            value=f"{gap_prefix}{duration_gap:.1f} yrs",
            delta="Asset − Liability",
            delta_color="off"
        )


# ============================================================
# PRIVATE: 组合时间序列图 (柱状 + 线)
# ============================================================

def _build_combo_time_series(ctx: dict) -> go.Figure:
    """
    组合图表:
    - 柱状图: Asset (靛蓝) + Liability (灰) 并排
    - 线图: Funded Status (绿色) 叠加在右 Y 轴
    - 基准线: 111% target (虚线)
    """
    ts_df = ctx['time_series_df'].copy()
    
    # 转换日期格式用于显示
    ts_df['date_str'] = pd.to_datetime(ts_df['date']).dt.strftime('%b %d')
    
    # 创建双 Y 轴图表
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # ── 柱状图: Assets ──
    fig.add_trace(
        go.Bar(
            name='Assets',
            x=ts_df['date_str'],
            y=ts_df['total_assets'] / 1000,
            marker_color=COLORS['accent'],
            opacity=0.9,
            hovertemplate='Assets: $%{y:.1f}B<extra></extra>'
        ),
        secondary_y=False
    )
    
    # ── 柱状图: Liabilities ──
    fig.add_trace(
        go.Bar(
            name='Liabilities',
            x=ts_df['date_str'],
            y=ts_df['total_liabilities'] / 1000,
            marker_color=COLORS['text_tertiary'],
            opacity=0.7,
            hovertemplate='Liabilities: $%{y:.1f}B<extra></extra>'
        ),
        secondary_y=False
    )
    
    # ── 线图: Funded Status ──
    fig.add_trace(
        go.Scatter(
            name='Funded Status',
            x=ts_df['date_str'],
            y=ts_df['funded_status'] * 100,
            mode='lines+markers',
            line=dict(color=COLORS['positive'], width=3),
            marker=dict(size=8, color=COLORS['positive']),
            hovertemplate='Funded Status: %{y:.1f}%<extra></extra>'
        ),
        secondary_y=True
    )
    
    # ── 基准线: 111% Target ──
    fig.add_hline(
        y=111,
        line_dash="dash",
        line_color=COLORS['warning'],
        line_width=2,
        annotation_text="111% Target",
        annotation_position="right",
        annotation_font_color=COLORS['warning'],
        secondary_y=True
    )
    
    # ── 应用统一布局 ──
    base_layout = get_chart_layout(height=350)
    fig.update_layout(
        **base_layout,
        barmode='group',
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=11, color=COLORS['text_secondary'])
        ),
    )
    
    # 左 Y 轴 (金额)
    fig.update_yaxes(
        title_text="Amount ($B CAD)",
        title_font=dict(size=11, color=COLORS['text_tertiary']),
        secondary_y=False,
        gridcolor=COLORS['bg_border'],
        tickformat=".0f",
        range=[100, 130],
        tickfont=dict(size=10, color=COLORS['text_tertiary'])
    )
    
    # 右 Y 轴 (百分比)
    fig.update_yaxes(
        title_text="Funded Status (%)",
        title_font=dict(size=11, color=COLORS['text_tertiary']),
        secondary_y=True,
        gridcolor='rgba(0,0,0,0)',
        ticksuffix="%",
        range=[105, 115],
        tickfont=dict(size=10, color=COLORS['text_tertiary'])
    )
    
    # X 轴
    fig.update_xaxes(
        gridcolor=COLORS['bg_border'],
        tickangle=-45,
        tickfont=dict(size=10, color=COLORS['text_tertiary'])
    )
    
    return fig


# ============================================================
# PRIVATE: 饼图 (Asset Allocation)
# ============================================================

def _build_pie_chart(ctx: dict) -> go.Figure:
    """
    资产配置饼图
    - 过滤掉负值 (Cash & Funding 是负的)
    - 使用统一色阶
    """
    mix_df = ctx['mix_df'].copy()
    
    # 过滤掉负值
    mix_df = mix_df[mix_df['total_mtm'] > 0].copy()
    
    # 计算百分比
    total = mix_df['total_mtm'].sum()
    mix_df['pct'] = mix_df['total_mtm'] / total * 100
    
    # 排序，让最大的在前面
    mix_df = mix_df.sort_values('total_mtm', ascending=False)
    
    # 为每个资产类别分配颜色
    colors = [ASSET_COLORS.get(ac, COLORS['accent']) for ac in mix_df['asset_class']]
    
    fig = go.Figure(data=[
        go.Pie(
            labels=mix_df['asset_class'],
            values=mix_df['total_mtm'],
            marker=dict(
                colors=colors,
                line=dict(color=COLORS['bg_page'], width=2)  # 分隔线
            ),
            textinfo='label+percent',
            textposition='outside',
            textfont=dict(size=11, color=COLORS['text_primary']),
            hovertemplate='%{label}<br>$%{value:,.0f}M<br>%{percent}<extra></extra>',
            hole=0.45,  # 甜甜圈效果
            pull=[0.02] * len(mix_df)
        )
    ])
    
    # 应用统一布局（合并 base 与覆盖项，避免 showlegend 重复）
    base_layout = get_chart_layout(height=320)
    layout = {
        **base_layout,
        'showlegend': False,
        'margin': dict(l=20, r=20, t=20, b=20),
        'annotations': [
            dict(
                text=f"<b>${total/1000:.0f}B</b>",
                x=0.5, y=0.5,
                font_size=20,
                font_color=COLORS['text_primary'],
                showarrow=False
            )
        ]
    }
    fig.update_layout(**layout)
    
    return fig


# ============================================================
# PRIVATE: 柱状图 (Actual vs Policy)
# ============================================================

def _build_comparison_bar(ctx: dict) -> go.Figure:
    """
    Actual vs Policy Target 对比柱状图
    - 每个 asset_class 有两根柱子: Actual + Target
    - 背景带: range_min ~ range_max
    """
    comp_df = ctx['comp_df'].copy()
    
    # 过滤掉 Cash & Funding (负权重)
    comp_df = comp_df[comp_df['current_weight'] >= 0].copy()
    
    # 简化 asset_class 名称
    comp_df['short_name'] = comp_df['asset_class'].apply(
        lambda x: x.replace('Private ', 'Priv ').replace('Public ', '')
    )
    
    fig = go.Figure()
    
    # ── Range Band (背景色带) ──
    for i, row in comp_df.iterrows():
        fig.add_shape(
            type="rect",
            x0=i - 0.4,
            x1=i + 0.4,
            y0=row['range_min'] * 100,
            y1=row['range_max'] * 100,
            xref="x",
            yref="y",
            fillcolor=f"rgba({int(COLORS['accent'][1:3], 16)}, {int(COLORS['accent'][3:5], 16)}, {int(COLORS['accent'][5:7], 16)}, 0.1)",
            line=dict(width=0),
            layer="below"
        )
    
    # ── Actual 柱 ──
    fig.add_trace(
        go.Bar(
            name='Actual',
            x=comp_df['short_name'],
            y=comp_df['current_weight'] * 100,
            marker_color=COLORS['accent'],
            text=[f"{v*100:.1f}%" for v in comp_df['current_weight']],
            textposition='outside',
            textfont=dict(size=10, color=COLORS['text_secondary']),
            hovertemplate='Actual: %{y:.1f}%<extra></extra>'
        )
    )
    
    # ── Target 柱 ──
    fig.add_trace(
        go.Bar(
            name='Target',
            x=comp_df['short_name'],
            y=comp_df['policy_target'] * 100,
            marker_color=COLORS['warning'],
            opacity=0.7,
            hovertemplate='Target: %{y:.1f}%<extra></extra>'
        )
    )
    
    # 应用统一布局（合并 base 与覆盖项，避免 margin/legend 重复）
    base_layout = get_chart_layout(height=320)
    layout = {
        **base_layout,
        'barmode': 'group',
        'bargap': 0.3,
        'bargroupgap': 0.1,
        'legend': dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=11, color=COLORS['text_secondary'])
        ),
        'margin': dict(l=50, r=20, t=40, b=80),
    }
    fig.update_layout(**layout)
    
    # Y 轴
    fig.update_yaxes(
        title_text="Weight (%)",
        title_font=dict(size=11, color=COLORS['text_tertiary']),
        gridcolor=COLORS['bg_border'],
        ticksuffix="%",
        range=[0, 55],
        tickfont=dict(size=10, color=COLORS['text_tertiary'])
    )
    
    # X 轴
    fig.update_xaxes(
        tickangle=-30,
        tickfont=dict(size=10, color=COLORS['text_tertiary'])
    )
    
    return fig
