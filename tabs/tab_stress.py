"""
tab_stress.py — Tab 3: Stress Testing

职责:
    展示基金在宏观冲击场景下的表现
    - 预设场景 Dropdown (2008 危机、滞胀、加息等)
    - 3 个 Slider: Rate / Equity / Inflation
    - KPI 卡片: Stressed Funded Status / Asset Δ / Liability Δ / Surplus Δ
    - Waterfall 瀑布图: P&L 按因子分解
    - Top Movers 表: 涨跌最大的资产

对外暴露: render(ctx)
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# 需要调用 engine 的 calculate_metrics
import engine

# ============================================================
# 颜色常量
# ============================================================
COLOR_BG = "#0f1923"
COLOR_CARD = "#162232"
COLOR_BORDER = "#1e3a5f"
COLOR_PRIMARY = "#00b4d8"
COLOR_SECONDARY = "#8a9bb0"
COLOR_OK = "#00c9a7"
COLOR_BREACH = "#e74c3c"

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
    """
    Tab 3 主入口。
    """
    # ─────────────────────────────────────────────────────────
    # 从 ctx 取 baseline 数据
    # ─────────────────────────────────────────────────────────
    df_day = ctx['df_day']
    baseline_assets = ctx['total_assets']
    baseline_liabilities = ctx['total_liabilities']
    baseline_funded = ctx['funded_status']
    baseline_surplus = ctx['surplus']

    # ─────────────────────────────────────────────────────────
    # Row 2 左: Scenario Controls
    # ─────────────────────────────────────────────────────────
    col_left, col_right = st.columns([0.35, 0.65])

    with col_left:
        st.markdown("#### 🎚️ Scenario Controls")

        # ── 预设场景 Dropdown ──
        preset_name = st.selectbox(
            "Preset Scenario",
            options=list(PRESET_SCENARIOS.keys()),
            index=0,
            help="选择预设场景快速填充参数，或选 Custom 手动调节",
        )

        preset = PRESET_SCENARIOS[preset_name]

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # ── Sliders ──
        # 如果选了预设场景，slider 默认值跟着变
        s_rate = st.slider(
            "Interest Rate Shock (bp)",
            min_value=-200,
            max_value=200,
            value=preset["rate"],
            step=5,
            help="+100bp 表示利率上升 1%",
        )

        s_equity = st.slider(
            "Equity Shock (%)",
            min_value=-50,
            max_value=50,
            value=preset["equity"],
            step=1,
            help="-20% 表示股市下跌 20%",
        )

        s_inflation = st.slider(
            "Inflation Shock (%)",
            min_value=-3.0,
            max_value=3.0,
            value=preset["inflation"],
            step=0.1,
            format="%.1f",
            help="+1% 表示通胀预期上升 1%",
        )

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # ── Reset Button ──
        if st.button("🔄 Reset to Baseline", use_container_width=True):
            # Streamlit 的 slider 没法直接 reset，但选 Custom 会让 value=0
            st.rerun()

        # ── 当前场景说明 ──
        st.markdown(
            f"""
            <div style="background-color:{COLOR_CARD}; border:1px solid {COLOR_BORDER}; 
                        border-radius:8px; padding:12px; margin-top:15px; font-size:0.85rem;">
            <b style="color:{COLOR_PRIMARY};">Current Scenario:</b><br>
            Rate: <span style="color:{COLOR_PRIMARY};">{s_rate:+d} bp</span><br>
            Equity: <span style="color:{COLOR_PRIMARY};">{s_equity:+d}%</span><br>
            Inflation: <span style="color:{COLOR_PRIMARY};">{s_inflation:+.1f}%</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ─────────────────────────────────────────────────────────
    # 执行压力计算
    # ─────────────────────────────────────────────────────────
    df_stressed = engine.calculate_metrics(df_day, s_rate, s_equity, s_inflation)

    # 分离资产和负债
    assets_stressed = df_stressed[df_stressed['plan_category'] == 'Asset']
    liabs_stressed = df_stressed[df_stressed['plan_category'] == 'Liability']

    stressed_assets = assets_stressed['mtm_stressed'].sum()
    stressed_liabilities = abs(liabs_stressed['mtm_stressed'].sum())
    stressed_funded = stressed_assets / stressed_liabilities if stressed_liabilities != 0 else 0
    stressed_surplus = stressed_assets - stressed_liabilities

    # 计算 Delta
    delta_assets = stressed_assets - baseline_assets
    delta_liabilities = stressed_liabilities - baseline_liabilities
    delta_surplus = stressed_surplus - baseline_surplus

    # ─────────────────────────────────────────────────────────
    # Row 1: KPI 卡片 (放在最上面，但代码在这里因为需要计算结果)
    # ─────────────────────────────────────────────────────────
    # 用 placeholder 在页面顶部插入
    kpi_placeholder = st.container()

    with kpi_placeholder:
        k1, k2, k3, k4 = st.columns(4)

        with k1:
            st.metric(
                label="Stressed Funded Status",
                value=f"{stressed_funded:.1%}",
                delta=f"{(stressed_funded - baseline_funded):.2%}",
                delta_color="normal",  # 正=绿，负=红
            )
        with k2:
            st.metric(
                label="Asset Δ",
                value=f"${stressed_assets/1000:.1f}B",
                delta=f"${delta_assets/1000:+.2f}B",
                delta_color="normal",
            )
        with k3:
            st.metric(
                label="Liability Δ",
                value=f"${stressed_liabilities/1000:.1f}B",
                delta=f"${delta_liabilities/1000:+.2f}B",
                delta_color="inverse",  # 负债涨是坏事，所以反转颜色
            )
        with k4:
            st.metric(
                label="Surplus Δ",
                value=f"${stressed_surplus/1000:.1f}B",
                delta=f"${delta_surplus/1000:+.2f}B",
                delta_color="normal",
            )

    # ─────────────────────────────────────────────────────────
    # Row 2 右: Waterfall + Top Movers
    # ─────────────────────────────────────────────────────────
    with col_right:
        st.markdown("#### 📊 P&L Waterfall (Assets)")
        _render_waterfall(df_day, assets_stressed, baseline_assets, s_rate, s_equity, s_inflation)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        st.markdown("#### 📋 Top Movers")
        _render_top_movers(df_day, assets_stressed)


# ============================================================
# 私有渲染函数
# ============================================================

def _render_waterfall(df_day: pd.DataFrame, 
                      assets_stressed: pd.DataFrame,
                      baseline_assets: float,
                      s_rate: int, s_equity: int, s_inflation: float):
    """
    渲染 P&L 瀑布图，按因子分解。
    """
    # 只取资产部分计算
    assets_baseline = df_day[df_day['plan_category'] == 'Asset']

    # 分别计算每个因子的独立 P&L 贡献
    rate_pnl = (assets_baseline['market_exposure_cad'] * 
                (-assets_baseline['duration'] * s_rate / 10000)).sum()

    equity_pnl = (assets_baseline['market_exposure_cad'] * 
                  (assets_baseline['equity_beta'] * s_equity / 100)).sum()

    inflation_pnl = (assets_baseline['market_exposure_cad'] * 
                     (assets_baseline['inflation_beta'] * s_inflation / 100)).sum()

    final_assets = assets_stressed['mtm_stressed'].sum()

    # 构建瀑布图数据
    stages = ['Baseline', 'Rate Impact', 'Equity Impact', 'Inflation Impact', 'Final']
    values = [baseline_assets, rate_pnl, equity_pnl, inflation_pnl, final_assets]

    # 确定颜色
    colors = []
    for i, v in enumerate(values):
        if i == 0:
            colors.append(COLOR_SECONDARY)  # Baseline: 灰
        elif i == len(values) - 1:
            colors.append(COLOR_PRIMARY)    # Final: 冰蓝
        elif v >= 0:
            colors.append(COLOR_OK)         # Positive: 绿
        else:
            colors.append(COLOR_BREACH)     # Negative: 红

    # Plotly Waterfall
    fig = go.Figure(go.Waterfall(
        name="P&L",
        orientation="v",
        measure=["absolute", "relative", "relative", "relative", "total"],
        x=stages,
        y=values,
        connector={"line": {"color": COLOR_BORDER}},
        decreasing={"marker": {"color": COLOR_BREACH}},
        increasing={"marker": {"color": COLOR_OK}},
        totals={"marker": {"color": COLOR_PRIMARY}},
        textposition="outside",
        text=[f"${v/1000:.1f}B" if abs(v) > 500 else f"${v:.0f}M" for v in values],
        textfont={"color": COLOR_SECONDARY, "size": 11},
    ))

    fig.update_layout(
        height=280,
        margin=dict(l=10, r=10, t=30, b=40),
        paper_bgcolor=COLOR_BG,
        plot_bgcolor=COLOR_BG,
        font={'color': COLOR_SECONDARY},
        showlegend=False,
        waterfallgap=0.3,
    )

    fig.update_xaxes(
        tickfont=dict(size=11),
        gridcolor=COLOR_BORDER,
    )

    fig.update_yaxes(
        tickformat="$,.0f",
        ticksuffix="M",
        gridcolor=COLOR_BORDER,
    )

    st.plotly_chart(fig, use_container_width=True)


def _render_top_movers(df_day: pd.DataFrame, assets_stressed: pd.DataFrame):
    """
    渲染 Top Movers 表：5 biggest gains + 5 biggest losses。
    """
    # 合并 baseline 和 stressed 数据
    baseline_assets = df_day[df_day['plan_category'] == 'Asset'][['asset_name', 'asset_class', 'mtm_cad']].copy()
    stressed_mtm = assets_stressed[['asset_name', 'mtm_stressed']].copy()

    merged = pd.merge(baseline_assets, stressed_mtm, on='asset_name')
    merged['pnl'] = merged['mtm_stressed'] - merged['mtm_cad']
    merged['pnl_pct'] = merged['pnl'] / merged['mtm_cad'].abs() * 100

    # 排序找 top 5 gains 和 top 5 losses
    top_gains = merged.nlargest(5, 'pnl')
    top_losses = merged.nsmallest(5, 'pnl')

    # 合并并排序
    top_movers = pd.concat([top_gains, top_losses]).sort_values('pnl', ascending=False)

    # 准备显示 DataFrame
    display_df = top_movers[['asset_name', 'asset_class', 'mtm_cad', 'mtm_stressed', 'pnl', 'pnl_pct']].copy()
    display_df.columns = ['Asset', 'Class', 'Baseline ($M)', 'Stressed ($M)', 'P&L ($M)', 'P&L %']

    # 格式化
    display_df['Baseline ($M)'] = display_df['Baseline ($M)'].apply(lambda x: f"{x:,.0f}")
    display_df['Stressed ($M)'] = display_df['Stressed ($M)'].apply(lambda x: f"{x:,.0f}")
    display_df['P&L ($M)'] = display_df['P&L ($M)'].apply(lambda x: f"{x:+,.0f}")
    display_df['P&L %'] = display_df['P&L %'].apply(lambda x: f"{x:+.1f}%")

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=320,
        column_config={
            "Asset": st.column_config.TextColumn("Asset", width="large"),
            "Class": st.column_config.TextColumn("Class", width="medium"),
            "Baseline ($M)": st.column_config.TextColumn("Baseline", width="small"),
            "Stressed ($M)": st.column_config.TextColumn("Stressed", width="small"),
            "P&L ($M)": st.column_config.TextColumn("P&L", width="small"),
            "P&L %": st.column_config.TextColumn("P&L %", width="small"),
        },
    )
