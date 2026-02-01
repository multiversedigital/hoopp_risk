"""
tab_fund_health.py — Tab 1: Fund Health (全基金监控)

职责:
    展示基金整体健康状况，核心指标是 Funded Status (资金充足率)

布局:
    Row 1: 5 个 KPI 卡片
    Row 2: 组合时间序列图（Asset/Liability 柱状 + Funded Status 线）
    Row 3: 左(饼图) + 右(Actual vs Policy 柱状图)

数据源: 全部从 ctx dict 获取
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

# ============================================================
# 颜色常量 (与 app.py GLOBAL_CSS 保持一致)
# ============================================================
COLOR_BG       = '#0f1923'      # 页面背景
COLOR_CARD     = '#162232'      # 卡片背景
COLOR_BORDER   = '#1e3a5f'      # 边框
COLOR_TEXT     = '#e8edf2'      # 主文字
COLOR_SUBTEXT  = '#8a9bb0'      # 副文字
COLOR_ACCENT   = '#00b4d8'      # 主 Accent (冰蓝)
COLOR_ACCENT2  = '#48cae4'      # 辅 Accent
COLOR_GREEN    = '#00c9a7'      # 状态绿
COLOR_ORANGE   = '#f9a825'      # 状态橙 / Target
COLOR_RED      = '#e74c3c'      # 状态红

# 饼图冰蓝色阶
PIE_COLORS = ['#00b4d8', '#48cae4', '#0891b2', '#06b6d4', '#22d3ee']


# ============================================================
# PUBLIC: render(ctx)
# ============================================================

def render(ctx: dict):
    """Tab 1 主入口，由 app.py 调用"""
    
    # ─────────────────────────────────────────────────────────
    # Row 1: KPI 卡片
    # ─────────────────────────────────────────────────────────
    _render_kpi_cards(ctx)
    
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)  # spacer
    
    # ─────────────────────────────────────────────────────────
    # Row 2: 组合时间序列图
    # ─────────────────────────────────────────────────────────
    st.markdown("#### 📈 Assets vs Liabilities Trend")
    fig_ts = _build_combo_time_series(ctx)
    st.plotly_chart(fig_ts, use_container_width=True)
    
    st.markdown("<div style='height: 10px'></div>", unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────
    # Row 3: 饼图 + 柱状图
    # ─────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.markdown("#### 🥧 Asset Allocation")
        fig_pie = _build_pie_chart(ctx)
        st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
    
    with col_right:
        st.markdown("#### 📊 Actual vs Policy Target")
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
        # Funded Status 用颜色指示健康度
        fs_color = COLOR_GREEN if funded_status >= 1.10 else (COLOR_ORANGE if funded_status >= 1.0 else COLOR_RED)
        st.metric(
            label="Funded Status",
            value=f"{funded_status:.1%}",
            delta="Target: 111%",
            delta_color="off"
        )
    
    with col2:
        st.metric(
            label="Surplus",
            value=f"${surplus/1000:.1f}B",
            delta=f"Assets - Liabilities",
            delta_color="off"
        )
    
    with col3:
        st.metric(
            label="Total Assets",
            value=f"${total_assets/1000:.1f}B",
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
        # Duration Gap 显示正负
        gap_prefix = "+" if duration_gap > 0 else ""
        st.metric(
            label="Duration Gap",
            value=f"{gap_prefix}{duration_gap:.1f} yrs",
            delta="Asset - Liability",
            delta_color="off"
        )


# ============================================================
# PRIVATE: 组合时间序列图 (柱状 + 线)
# ============================================================

def _build_combo_time_series(ctx: dict) -> go.Figure:
    """
    组合图表:
    - 柱状图: Asset (冰蓝) + Liability (灰蓝) 并排
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
            y=ts_df['total_assets'] / 1000,  # 转换为 Billion
            marker_color=COLOR_ACCENT,
            opacity=0.85,
            text=[f"${v/1000:.1f}B" for v in ts_df['total_assets']],
            textposition='none',
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
            marker_color=COLOR_SUBTEXT,
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
            y=ts_df['funded_status'] * 100,  # 转换为百分比数值
            mode='lines+markers',
            line=dict(color=COLOR_GREEN, width=3),
            marker=dict(size=8, color=COLOR_GREEN),
            hovertemplate='Funded Status: %{y:.1f}%<extra></extra>'
        ),
        secondary_y=True
    )
    
    # ── 基准线: 111% Target ──
    fig.add_hline(
        y=111,
        line_dash="dash",
        line_color=COLOR_ORANGE,
        line_width=2,
        annotation_text="111% Target",
        annotation_position="right",
        annotation_font_color=COLOR_ORANGE,
        secondary_y=True
    )
    
    # ── 布局设置 ──
    fig.update_layout(
        barmode='group',
        plot_bgcolor=COLOR_BG,
        paper_bgcolor=COLOR_BG,
        font=dict(color=COLOR_TEXT, size=12),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(size=11)
        ),
        margin=dict(l=60, r=60, t=40, b=40),
        height=350,
        hovermode='x unified'
    )
    
    # 左 Y 轴 (金额)
    fig.update_yaxes(
        title_text="Amount ($B CAD)",
        secondary_y=False,
        gridcolor=COLOR_BORDER,
        tickformat=".0f",
        range=[100, 130]  # 根据数据范围调整
    )
    
    # 右 Y 轴 (百分比)
    fig.update_yaxes(
        title_text="Funded Status (%)",
        secondary_y=True,
        gridcolor='rgba(0,0,0,0)',  # 右轴不画网格线
        ticksuffix="%",
        range=[105, 115]  # 留出空间显示 111% 线
    )
    
    # X 轴
    fig.update_xaxes(
        gridcolor=COLOR_BORDER,
        tickangle=-45
    )
    
    return fig


# ============================================================
# PRIVATE: 饼图 (Asset Allocation)
# ============================================================

def _build_pie_chart(ctx: dict) -> go.Figure:
    """
    资产配置饼图
    - 过滤掉负值 (Cash & Funding 是负的)
    - 使用冰蓝色阶
    """
    mix_df = ctx['mix_df'].copy()
    
    # 过滤掉负值
    mix_df = mix_df[mix_df['total_mtm'] > 0].copy()
    
    # 计算百分比
    total = mix_df['total_mtm'].sum()
    mix_df['pct'] = mix_df['total_mtm'] / total * 100
    
    # 排序，让最大的在前面
    mix_df = mix_df.sort_values('total_mtm', ascending=False)
    
    fig = go.Figure(data=[
        go.Pie(
            labels=mix_df['asset_class'],
            values=mix_df['total_mtm'],
            marker=dict(colors=PIE_COLORS[:len(mix_df)]),
            textinfo='label+percent',
            textposition='outside',
            textfont=dict(size=11, color=COLOR_TEXT),
            hovertemplate='%{label}<br>$%{value:,.0f}M<br>%{percent}<extra></extra>',
            hole=0.4,  # 甜甜圈效果
            pull=[0.02] * len(mix_df)  # 轻微分离效果
        )
    ])
    
    fig.update_layout(
        plot_bgcolor=COLOR_BG,
        paper_bgcolor=COLOR_BG,
        font=dict(color=COLOR_TEXT),
        showlegend=False,  # label 已经在外面显示了
        margin=dict(l=20, r=20, t=20, b=20),
        height=320,
        annotations=[
            dict(
                text=f"${total/1000:.0f}B",
                x=0.5, y=0.5,
                font_size=18,
                font_color=COLOR_ACCENT,
                showarrow=False
            )
        ]
    )
    
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
    comp_df['short_name'] = comp_df['asset_class'].apply(lambda x: x.replace('Private ', 'Priv ').replace('Public ', ''))
    
    fig = go.Figure()
    
    # ── Range Band (背景色带) ──
    for i, row in comp_df.iterrows():
        fig.add_shape(
            type="rect",
            x0=row['short_name'],
            x1=row['short_name'],
            y0=row['range_min'] * 100,
            y1=row['range_max'] * 100,
            xref="x",
            yref="y",
            fillcolor='rgba(30,58,95,0.3)',
            line=dict(width=0),
            layer="below"
        )
    
    # ── Actual 柱 ──
    fig.add_trace(
        go.Bar(
            name='Actual',
            x=comp_df['short_name'],
            y=comp_df['current_weight'] * 100,
            marker_color=COLOR_ACCENT,
            text=[f"{v*100:.1f}%" for v in comp_df['current_weight']],
            textposition='outside',
            textfont=dict(size=10),
            hovertemplate='Actual: %{y:.1f}%<extra></extra>'
        )
    )
    
    # ── Target 柱 ──
    fig.add_trace(
        go.Bar(
            name='Target',
            x=comp_df['short_name'],
            y=comp_df['policy_target'] * 100,
            marker_color=COLOR_ORANGE,
            opacity=0.7,
            hovertemplate='Target: %{y:.1f}%<extra></extra>'
        )
    )
    
    fig.update_layout(
        barmode='group',
        plot_bgcolor=COLOR_BG,
        paper_bgcolor=COLOR_BG,
        font=dict(color=COLOR_TEXT, size=11),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5
        ),
        margin=dict(l=40, r=20, t=40, b=60),
        height=320,
        yaxis=dict(
            title="Weight (%)",
            gridcolor=COLOR_BORDER,
            ticksuffix="%",
            range=[0, 55]
        ),
        xaxis=dict(
            tickangle=-30
        )
    )
    
    return fig
