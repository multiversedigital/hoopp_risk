"""
tab_stress.py — Tab 3: Stress Testing

职责:
    展示基金在宏观冲击场景下的表现

布局:
    Row 1: Scenario Controls
           [Preset + Current + Reset] | [Sliders] | [KPIs 2x2]
    Row 2: [P&L Waterfall] | [Top Movers]

对外暴露: render(ctx)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import engine

# ============================================================
# 导入统一 UI 组件库
# ============================================================
from ui_components import (
    COLORS,
    get_chart_layout,
    render_section_header,
    format_number,
    format_percent,
)

# ============================================================
# 预设场景
# ============================================================
PRESET_SCENARIOS = {
    "Custom": {"rate": 0, "equity": 0, "inflation": 0.0},
    "2008 Financial Crisis": {"rate": 50, "equity": -40, "inflation": -1.0},
    "Stagflation": {"rate": 100, "equity": -15, "inflation": 3.0},
    "Rate Hike Shock": {"rate": 150, "equity": -10, "inflation": 0.5},
    "Market Rally": {"rate": -25, "equity": 20, "inflation": 0.5},
    "Deflation Scare": {"rate": -50, "equity": -10, "inflation": -2.0},
}


def render(ctx: dict):
    """Tab 3 主入口。"""
    
    # ─────────────────────────────────────────────────────────
    # 自定义 Slider 样式 (修复红色问题)
    # ─────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <style>
        /* Slider 标签 */
        .stSlider label p {{
            color: {COLORS['text_secondary']} !important;
            font-size: 0.85rem !important;
        }}
        /* Slider 数值 */
        .stSlider [data-testid="stThumbValue"] {{
            color: {COLORS['text_primary']} !important;
            font-weight: 500 !important;
            background: transparent !important;
        }}
        /* Slider track - 已填充部分 */
        .stSlider [data-testid="stSliderTrackValue"] {{
            background-color: {COLORS['accent']} !important;
        }}
        /* Slider thumb */
        .stSlider [role="slider"] {{
            background-color: {COLORS['accent']} !important;
            border-color: {COLORS['accent']} !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ─────────────────────────────────────────────────────────
    # 取 baseline 数据
    # ─────────────────────────────────────────────────────────
    df_day = ctx['df_day']
    baseline_assets = ctx['total_assets']
    baseline_liabilities = ctx['total_liabilities']
    baseline_funded = ctx['funded_status']
    baseline_surplus = ctx['surplus']

    # ─────────────────────────────────────────────────────────
    # 标题 + 说明
    # ─────────────────────────────────────────────────────────
    render_section_header("Scenario Controls", "🎚️")
    
    st.markdown(
        f"""
        <div style="color:{COLORS['text_secondary']}; font-size:1rem; line-height:1.5; margin-bottom:16px;">
            <strong>ℹ️ Methodology note</strong><br/>
            This demo uses <strong>simplified linear shocks</strong>: parallel moves in rate (bp), equity (%) and inflation (%), 
            with linear sensitivities (e.g. duration × rate, beta × equity). Suitable for illustration and quick what‑if.
            In <strong>production</strong>, institutions typically apply <strong>non‑linear factor models</strong> that capture 
            correlations, tail dependence, volatility regimes and scenario‑dependent behaviour (e.g. credit spread vs rates in stress).
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ─────────────────────────────────────────────────────────
    # 3 列布局: [左: Preset+Current+Reset] | [中: Sliders] | [右: KPIs 2x2]
    # 用单一 session_state["stress"] 存预设和三个值，Reset 只改这个 dict，不碰 widget key，避免报错和卡死
    # ─────────────────────────────────────────────────────────
    options = list(PRESET_SCENARIOS.keys())
    if "stress" not in st.session_state:
        st.session_state["stress"] = {"preset": "Custom", "rate": 0, "equity": 0, "inflation": 0.0}

    col_left, col_mid, col_right = st.columns([2.5, 3.5, 4])

    # ── 左列: Preset Dropdown ──
    with col_left:
        idx = options.index(st.session_state["stress"]["preset"]) if st.session_state["stress"]["preset"] in options else 0
        preset_name = st.selectbox(
            "Preset Scenario",
            options=options,
            index=idx,
        )
        preset = PRESET_SCENARIOS[preset_name]
        # 预设变了则同步三个值
        if preset_name != st.session_state["stress"]["preset"]:
            st.session_state["stress"] = {
                "preset": preset_name,
                "rate": preset["rate"],
                "equity": preset["equity"],
                "inflation": preset["inflation"],
            }

    # ── 中列: 3 Sliders（用 stress 里的值，不绑 key） ──
    with col_mid:
        s_rate = st.slider(
            "Rate (bp)",
            min_value=-200, max_value=200,
            value=st.session_state["stress"]["rate"], step=5,
        )
        s_equity = st.slider(
            "Equity (%)",
            min_value=-50, max_value=50,
            value=st.session_state["stress"]["equity"], step=1,
        )
        s_inflation = st.slider(
            "Inflation (%)",
            min_value=-3.0, max_value=3.0,
            value=st.session_state["stress"]["inflation"], step=0.1, format="%.1f",
        )
    # 用当前滑块值回写，保证下次 rerun 时保持
    st.session_state["stress"]["rate"] = s_rate
    st.session_state["stress"]["equity"] = s_equity
    st.session_state["stress"]["inflation"] = s_inflation
    st.session_state["stress"]["preset"] = preset_name

    # ─────────────────────────────────────────────────────────
    # 执行压力计算
    # ─────────────────────────────────────────────────────────
    df_stressed = engine.calculate_metrics(df_day, s_rate, s_equity, s_inflation)

    assets_stressed = df_stressed[df_stressed['plan_category'] == 'Asset']
    liabs_stressed = df_stressed[df_stressed['plan_category'] == 'Liability']

    stressed_assets = assets_stressed['mtm_stressed'].sum()
    stressed_liabilities = abs(liabs_stressed['mtm_stressed'].sum())
    stressed_funded = stressed_assets / stressed_liabilities if stressed_liabilities != 0 else 0
    stressed_surplus = stressed_assets - stressed_liabilities

    delta_assets = stressed_assets - baseline_assets
    delta_liabilities = stressed_liabilities - baseline_liabilities
    delta_surplus = stressed_surplus - baseline_surplus
    delta_funded = stressed_funded - baseline_funded

    # ── 右列: KPIs 2x2 ──
    with col_right:
        r1c1, r1c2 = st.columns(2)
        with r1c1:
            st.metric(
                label="Stressed Funded",
                value=format_percent(stressed_funded),
                delta=f"{delta_funded:+.2%}",
                delta_color="normal",
            )
        with r1c2:
            st.metric(
                label="Asset Δ",
                value=f"${stressed_assets/1000:.1f}B",
                delta=f"{'+' if delta_assets >= 0 else ''}{delta_assets/1000:.2f}B",
                delta_color="normal",
            )
        
        r2c1, r2c2 = st.columns(2)
        with r2c1:
            st.metric(
                label="Liability Δ",
                value=f"${stressed_liabilities/1000:.1f}B",
                delta=f"{'+' if delta_liabilities >= 0 else ''}{delta_liabilities/1000:.2f}B",
                delta_color="inverse",
            )
        with r2c2:
            st.metric(
                label="Surplus Δ",
                value=f"${stressed_surplus/1000:.1f}B",
                delta=f"{'+' if delta_surplus >= 0 else ''}{delta_surplus/1000:.2f}B",
                delta_color="normal",
            )

    # ── 左列续: Current Scenario + Reset ──
    with col_left:
        impact_color = COLORS['positive'] if delta_surplus >= 0 else COLORS['negative']
        impact_sign = "+" if delta_surplus >= 0 else ""
        
        st.markdown(
            f"""
            <div style="background-color:{COLORS['bg_card']}; border:1px solid {COLORS['bg_border']}; 
                        border-radius:8px; padding:14px; margin-top:12px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <span style="color:{COLORS['text_primary']}; font-weight:600; font-size:0.85rem;">Current Scenario</span>
                    <span style="background-color:{'rgba(16,185,129,0.15)' if delta_surplus >= 0 else 'rgba(239,68,68,0.15)'}; 
                                 color:{impact_color}; padding:3px 8px; border-radius:4px; font-size:0.7rem; font-weight:600;">
                        {impact_sign}${abs(delta_surplus)/1000:.2f}B
                    </span>
                </div>
                <div style="color:{COLORS['text_secondary']}; font-size:0.8rem; line-height:1.6;">
                    Rate: <span style="color:{COLORS['accent']}; font-weight:500;">{s_rate:+d} bp</span><br>
                    Equity: <span style="color:{COLORS['accent']}; font-weight:500;">{s_equity:+d}%</span><br>
                    Inflation: <span style="color:{COLORS['accent']}; font-weight:500;">{s_inflation:+.1f}%</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        if st.button("🔄 Reset to Baseline", use_container_width=True):
            st.session_state["stress"] = dict(PRESET_SCENARIOS["Custom"])
            st.session_state["stress"]["preset"] = "Custom"
            st.rerun()

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # Row 2: Waterfall + Top Movers 并排
    # ─────────────────────────────────────────────────────────
    col_waterfall, col_movers = st.columns(2)

    with col_waterfall:
        render_section_header("P&L Waterfall (Assets)", "📊")
        _render_waterfall(df_day, assets_stressed, baseline_assets, s_rate, s_equity, s_inflation)

    with col_movers:
        render_section_header("Top Movers", "📋")
        _render_top_movers(df_day, assets_stressed)


# ============================================================
# 私有渲染函数
# ============================================================

def _render_waterfall(df_day, assets_stressed, baseline_assets, s_rate, s_equity, s_inflation):
    """渲染 P&L 瀑布图"""
    assets_baseline = df_day[df_day['plan_category'] == 'Asset']

    rate_pnl = (assets_baseline['market_exposure_cad'] * 
                (-assets_baseline['duration'] * s_rate / 10000)).sum()
    equity_pnl = (assets_baseline['market_exposure_cad'] * 
                  (assets_baseline['equity_beta'] * s_equity / 100)).sum()
    inflation_pnl = (assets_baseline['market_exposure_cad'] * 
                     (assets_baseline['inflation_beta'] * s_inflation / 100)).sum()
    final_assets = assets_stressed['mtm_stressed'].sum()

    stages = ['Baseline', 'Rate', 'Equity', 'Inflation', 'Final']
    values = [baseline_assets, rate_pnl, equity_pnl, inflation_pnl, final_assets]

    fig = go.Figure(go.Waterfall(
        name="P&L",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=stages,
        y=values,
        connector={"line": {"color": COLORS['bg_border'], "width": 1}},
        decreasing={"marker": {"color": COLORS['negative']}},
        increasing={"marker": {"color": COLORS['positive']}},
        totals={"marker": {"color": COLORS['accent']}},
        textposition="outside",
        text=[f"${v/1000:.1f}B" if abs(v) > 500 else f"${v:.0f}M" for v in values],
        textfont={"color": COLORS['text_secondary'], "size": 10},
    ))

    base_layout = get_chart_layout(height=320)
    base_layout["showlegend"] = False
    base_layout["margin"] = dict(l=20, r=20, t=20, b=40)
    fig.update_layout(**base_layout, waterfallgap=0.4)
    fig.update_xaxes(tickfont=dict(size=10, color=COLORS['text_tertiary']), gridcolor=COLORS['bg_border'])
    fig.update_yaxes(tickformat="$,.0f", ticksuffix="M", gridcolor=COLORS['bg_border'],
                     tickfont=dict(size=9, color=COLORS['text_tertiary']))

    st.plotly_chart(fig, use_container_width=True)


def _render_top_movers(df_day, assets_stressed):
    """渲染 Top Movers 表"""
    baseline_assets = df_day[df_day['plan_category'] == 'Asset'][['asset_name', 'asset_class', 'mtm_cad']].copy()
    stressed_mtm = assets_stressed[['asset_name', 'mtm_stressed']].copy()

    merged = pd.merge(baseline_assets, stressed_mtm, on='asset_name')
    merged['pnl'] = merged['mtm_stressed'] - merged['mtm_cad']
    merged['pnl_pct'] = merged['pnl'] / merged['mtm_cad'].abs() * 100

    top_gains = merged.nlargest(5, 'pnl')
    top_losses = merged.nsmallest(5, 'pnl')
    top_movers = pd.concat([top_gains, top_losses]).sort_values('pnl', ascending=False)

    display_df = top_movers[['asset_name', 'asset_class', 'mtm_cad', 'mtm_stressed', 'pnl', 'pnl_pct']].copy()
    display_df.columns = ['Asset', 'Class', 'Baseline', 'Stressed', 'P&L', 'P&L %']

    display_df['Baseline'] = display_df['Baseline'].apply(lambda x: f"${x:,.0f}M")
    display_df['Stressed'] = display_df['Stressed'].apply(lambda x: f"${x:,.0f}M")
    display_df['P&L'] = display_df['P&L'].apply(lambda x: f"${x:+,.0f}M")
    display_df['P&L %'] = display_df['P&L %'].apply(lambda x: f"{x:+.1f}%")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=320,
        column_config={
            "Asset": st.column_config.TextColumn("Asset", width="medium"),
            "Class": st.column_config.TextColumn("Class", width="small"),
            "Baseline": st.column_config.TextColumn("Baseline", width="small"),
            "Stressed": st.column_config.TextColumn("Stressed", width="small"),
            "P&L": st.column_config.TextColumn("P&L", width="small"),
            "P&L %": st.column_config.TextColumn("P&L %", width="small"),
        },
    )