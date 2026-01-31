import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from pathlib import Path

# 数据文件路径：相对于本脚本所在目录，这样无论从哪启动 Streamlit 都能找到
_APP_DIR = Path(__file__).resolve().parent
_DATA_DIR = _APP_DIR / "data"
POSITIONS_CSV = _DATA_DIR / "hoopp_positions_sample.csv"
POLICY_CSV = _DATA_DIR / "policy_limit_management.csv"

# ==========================================
# 1. 页面配置 (Page Configuration)
# ==========================================
st.set_page_config(
    page_title="HOOPP Risk Navigator",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义 CSS 让界面更像金融终端
st.markdown("""
<style>
    .metric-card {background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #004E7C;}
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 4px 4px 0px 0px; gap: 1px; padding-top: 10px; padding-bottom: 10px; }
    .stTabs [data-baseweb="tab"][aria-selected="true"] { background-color: #FFFFFF; border-top: 2px solid #004E7C; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 数据加载与预处理 (Data Loader)
# ==========================================
@st.cache_data
def load_data():
    # 读取我们在 generate_data.py 中生成的两个文件（路径相对于 app.py 所在目录）
    try:
        df_pos = pd.read_csv(POSITIONS_CSV)
        df_pol = pd.read_csv(POLICY_CSV)
        
        # 确保日期格式正确
        df_pos['timestamp'] = pd.to_datetime(df_pos['timestamp'])
        return df_pos, df_pol
    except FileNotFoundError:
        st.error("❌ 未找到数据文件！请先运行 'generate_data.py' 生成 CSV。")
        st.stop()

df, df_policy = load_data()

# ==========================================
# 3. 侧边栏：情景模拟 (Scenario Control)
# ==========================================
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/Healthcare_of_Ontario_Pension_Plan_logo.svg/1200px-Healthcare_of_Ontario_Pension_Plan_logo.svg.png", width=200)
    st.header("⚙️ Risk Scenarios (Scheme A)")
    st.markdown("---")
    
    # 日期选择 (Time Travel)
    available_dates = df['timestamp'].dt.strftime('%Y-%m-%d').unique()
    selected_date = st.selectbox("📅 Valuation Date", sorted(available_dates, reverse=True))
    
    st.markdown("### 🌪️ Stress Factors")
    # 压力测试滑块
    shock_rate = st.slider("📈 Interest Rate (bps)", -100, 100, 0, step=10, help="Shift in Yield Curve")
    shock_equity = st.slider("📉 Public Equity (%)", -30, 30, 0, step=1, help="Global Equity Market Shock")
    shock_inf = st.slider("🎈 Inflation Expectation (%)", -2.0, 2.0, 0.0, step=0.1, help="Impact on Real Return Bonds & Liabilities")
    
    st.markdown("---")
    if st.button("🔄 Reset Scenarios"):
        st.rerun()

# 过滤当前日期数据
df_day = df[df['timestamp'] == selected_date].copy()

# ==========================================
# 4. 核心计算引擎 (ALM Calculation Engine)
# ==========================================
def calculate_metrics(df_in, s_rate, s_eq, s_inf):
    """
    执行 Scheme A 实时计算：
    基于 Duration, Beta, Inflation Beta 计算新的 MTM
    """
    # 1. 利率冲击 (Price Change ~= -Duration * Shock)
    # 注意: s_rate 是 bps，所以要除以 10000
    rate_impact = -1 * df_in['duration'] * (s_rate / 10000)
    
    # 2. 权益冲击 (Price Change = Beta * Shock)
    # s_eq 是百分比，所以要除以 100
    equity_impact = df_in['equity_beta'] * (s_eq / 100)
    
    # 3. 通胀冲击 (Price Change = Inf_Beta * Shock)
    inf_impact = df_in['inflation_beta'] * (s_inf / 100)
    
    # 4. 综合总冲击 (Total P&L %)
    total_shock_pct = rate_impact + equity_impact + inf_impact
    
    # 5. 应用冲击到 Market Exposure (这是风险计算的基数)
    # 对于衍生品，冲击作用于 Exposure；对于实物，MTM ~= Exposure
    # 简化的 P&L = Exposure * Shock%
    pnl = df_in['market_exposure_cad'] * total_shock_pct
    
    # 6. 计算新的 MTM
    # New MTM = Old MTM + PnL
    df_in['mtm_stressed'] = df_in['mtm_cad'] + pnl
    
    return df_in

# 运行计算
df_stressed = calculate_metrics(df_day, shock_rate, shock_equity, shock_inf)

# 分离资产与负债
assets = df_stressed[df_stressed['plan_category'] == 'Asset']
liabilities = df_stressed[df_stressed['plan_category'] == 'Liability']

# 计算关键指标 (KPIs)
total_assets = assets['mtm_stressed'].sum()
total_liabilities = abs(liabilities['mtm_stressed'].sum()) # 取绝对值作为分母
funded_status = total_assets / total_liabilities
surplus = total_assets - total_liabilities

# ==========================================
# 5. 顶部 KPI 看板 (Executive Dashboard)
# ==========================================
st.title("🛡️ HOOPP Risk Navigator")
st.markdown(f"**Data Snapshot:** {selected_date} | **View:** Total Fund Management (TFM)")

c1, c2, c3, c4 = st.columns(4)
with c1:
    delta_fs = funded_status - 1.11 # 假设基准是 1.11
    st.metric("Funded Status", f"{funded_status:.1%}", f"{delta_fs:.2%}")
with c2:
    st.metric("Net Surplus (CAD)", f"${surplus/1000:.1f} B", f"{(surplus - (124000/1.11*0.11))/1000:.1f} B")
with c3:
    st.metric("Total Assets", f"${total_assets/1000:.1f} B", help="Includes Leverage")
with c4:
    # 计算当前加权久期 (Asset Duration)
    asset_dur = (assets['duration'] * assets['mtm_stressed']).sum() / total_assets
    st.metric("Asset Duration", f"{asset_dur:.1f} yrs", "vs Liab ~12.5 yrs")

st.markdown("---")

# ==========================================
# 6. 多标签页视图 (Tabs View)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Asset Mix & ALM", 
    "🌪️ Stress Testing", 
    "🚦 Compliance Monitor", 
    "🌍 TFM Deep Dive"
])

# --- TAB 1: 资产配置与概览 ---
with tab1:
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Current Asset Mix (Actual)")
        # 按 Asset Class 汇总
        mix_df = assets.groupby('asset_class')['mtm_stressed'].sum().reset_index()
        # 处理负值（Cash & Funding），饼图通常不显示负值，这里做绝对值处理或过滤
        fig_pie = px.pie(
            mix_df[mix_df['mtm_stressed'] > 0], 
            values='mtm_stressed', 
            names='asset_class',
            title='Long Term Asset Mix (Excl. Leverage)',
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Prism
        )
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col2:
        st.subheader("Actual vs Policy Target")
        # 合并 Policy 数据
        policy_view = df_policy[df_policy['category_type'] == 'Asset_Mix'].copy()
        
        # 计算当前权重
        current_w = assets.groupby('asset_class')['mtm_stressed'].sum() / total_assets
        current_w = current_w.reset_index(name='current_weight')
        
        # Merge
        comp_df = pd.merge(policy_view, current_w, on='asset_class', how='left').fillna(0)
        
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=comp_df['asset_class'], y=comp_df['current_weight'],
            name='Actual', marker_color='#004E7C'
        ))
        fig_bar.add_trace(go.Bar(
            x=comp_df['asset_class'], y=comp_df['policy_target'],
            name='Policy Target', marker_color='#A0C4FF'
        ))
        # 添加 Range 区间线
        fig_bar.add_trace(go.Scatter(
            x=comp_df['asset_class'], y=comp_df['range_max'],
            mode='markers', marker=dict(symbol='line-ew', color='red', size=20, line=dict(width=2)),
            name='Max Limit'
        ))
        
        fig_bar.update_layout(title="Policy Compliance Check", barmode='group', yaxis_tickformat='.0%')
        st.plotly_chart(fig_bar, use_container_width=True)

# --- TAB 2: 压力测试详情 ---
with tab2:
    st.subheader("Scheme A: ALM Sensitivity Analysis")
    st.markdown("""
    > **HOOPP Insight:** 注意观察当你**提高利率**时，Funded Status 如何变化。
    > 由于负债久期 (Duration ~12-14) 大于资产久期 (Duration ~8)，**加息实际上会改善 Funded Status** (负债价值下降得更快)。
    """)
    
    # 展示 Top 10 盈亏贡献者
    df_stressed['PnL'] = df_stressed['mtm_stressed'] - df_stressed['mtm_cad']
    top_movers = df_stressed.sort_values(by='PnL', ascending=True).head(5)
    bottom_movers = df_stressed.sort_values(by='PnL', ascending=False).head(5)
    
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        st.markdown("#### 📉 Top Losers (Under Scenario)")
        st.dataframe(top_movers[['asset_name', 'asset_class', 'duration', 'equity_beta', 'PnL']].style.format({'PnL': "{:,.1f}"}))
    with c_s2:
        st.markdown("#### 📈 Top Gainers (Under Scenario)")
        st.dataframe(bottom_movers[['asset_name', 'asset_class', 'duration', 'equity_beta', 'PnL']].style.format({'PnL': "{:,.1f}"}))

    # 瀑布图：解释 Funded Status 的变化来源
    st.markdown("#### Scenario Attribution")
    fig_waterfall = go.Figure(go.Waterfall(
        name = "20", orientation = "v",
        measure = ["relative", "relative", "relative", "total"],
        x = ["Rate Impact", "Equity Impact", "Inflation Impact", "Total Change"],
        textposition = "outside",
        # 这里的计算是近似值，仅作演示
        y = [
            -1 * (df_day['market_exposure_cad'] * df_day['duration'] * (shock_rate/10000)).sum(),
            (df_day['market_exposure_cad'] * df_day['equity_beta'] * (shock_equity/100)).sum(),
            (df_day['market_exposure_cad'] * df_day['inflation_beta'] * (shock_inf/100)).sum(),
            0 # Total 会自动计算
        ],
        connector = {"line":{"color":"rgb(63, 63, 63)"}},
    ))
    fig_waterfall.update_layout(title = "P&L Attribution by Risk Factor (CAD)")
    st.plotly_chart(fig_waterfall, use_container_width=True)

# --- TAB 3: 合规监控 (红绿灯) ---
with tab3:
    st.subheader("Compliance & Limits Monitor")
    
    # 1. 资产配置合规 (从 Tab 1 借用的数据)
    limits_df = comp_df.copy()
    limits_df['Status'] = limits_df.apply(
        lambda x: '🔴 BREACH' if (x['current_weight'] > x['range_max'] or x['current_weight'] < x['range_min']) 
        else ('🟡 WARN' if x['current_weight'] > x['range_max']*0.9 else '🟢 OK'), axis=1
    )
    
    st.markdown("#### 1. Asset Mix Limits (SIPP)")
    st.dataframe(
        limits_df[['asset_class', 'current_weight', 'policy_target', 'range_min', 'range_max', 'Status']]
        .style.applymap(lambda v: 'color: red; font-weight: bold' if 'BREACH' in str(v) else ('color: orange' if 'WARN' in str(v) else 'color: green'), subset=['Status'])
        .format({'current_weight': '{:.1%}', 'policy_target': '{:.1%}', 'range_min': '{:.1%}', 'range_max': '{:.1%}'})
    )
    
    st.markdown("---")
    
    col_lim1, col_lim2 = st.columns(2)
    
    # 2. 外汇限额监控 (FX Limit)
    with col_lim1:
        st.markdown("#### 2. FX Exposure Limit (Max 15%)")
        # 计算净外汇敞口 (Net FX Exposure)
        net_fx_exposure = assets['fx_exposure_cad'].sum()
        fx_pct = net_fx_exposure / total_assets
        
        limit_val = 0.15
        delta_fx = limit_val - fx_pct
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number+delta",
            value = fx_pct * 100,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Net FX Exposure (%)"},
            delta = {'reference': 15.0, 'increasing': {'color': "red"}},
            gauge = {
                'axis': {'range': [0, 25], 'tickwidth': 1},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [0, 12], 'color': "lightgreen"},
                    {'range': [12, 15], 'color': "yellow"},
                    {'range': [15, 25], 'color': "red"}],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 15.0}
            }
        ))
        st.plotly_chart(fig_gauge, use_container_width=True)
        st.caption(f"Net FX Exposure: ${net_fx_exposure/1000:.1f} B. Includes Derivatives hedging.")

    # 3. 单一发行人限额 (Issuer Limit)
    with col_lim2:
        st.markdown("#### 3. Top 5 Issuer Concentration (Max 5%)")
        # 按 Asset Name 聚合 (模拟 Issuer)
        issuer_conc = assets.groupby('asset_name')['mtm_stressed'].sum().sort_values(ascending=False).head(5)
        issuer_pct = issuer_conc / total_assets
        
        iss_df = pd.DataFrame({'Issuer': issuer_conc.index, 'Weight': issuer_pct.values})
        iss_df['Status'] = iss_df['Weight'].apply(lambda x: '🔴' if x > 0.05 else '🟢')
        
        st.dataframe(iss_df.style.format({'Weight': '{:.2%}'}))

# --- TAB 4: 穿透式分析 (TFM Deep Dive) ---
with tab4:
    st.subheader("Total Fund Look-through Analysis")
    
    t1, t2 = st.columns(2)
    with t1:
        # Sunburst Chart: Asset Class -> Sector -> Geography
        st.markdown("##### Portfolio Composition (Drill-down)")
        # 过滤掉负值的行以防 Sunburst 报错
        pos_assets = assets[assets['mtm_stressed'] > 0]
        fig_sun = px.sunburst(
            pos_assets, 
            path=['asset_class', 'sector', 'geography'], 
            values='mtm_stressed',
            color='sector',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_sun, use_container_width=True)
        
    with t2:
        # ESG vs Returns Scatter
        st.markdown("##### ESG Score vs. Risk (Duration)")
        fig_esg = px.scatter(
            assets[assets['asset_class'].isin(['Public Equities', 'Private Infrastructure', 'Private Real Estate'])],
            x='esg_score', y='carbon_intensity',
            size='mtm_stressed', color='asset_class',
            hover_name='asset_name',
            title="Carbon Intensity vs ESG Score (Bubble Size = MTM)",
            labels={'carbon_intensity': 'Carbon Intensity (tCO2e/$M)', 'esg_score': 'ESG Score (0-100)'}
        )
        # 添加 2030 目标线
        fig_esg.add_vline(x=0, line_dash="dash", annotation_text="Ideal State")
        st.plotly_chart(fig_esg, use_container_width=True)

    st.markdown("---")
    st.info("💡 **TFM Insight:** This view aggregates exposures across both Public and Private markets, allowing the Risk Committee to see total 'Technology' or 'Real Estate' exposure regardless of the investment vehicle.")