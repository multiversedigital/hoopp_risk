"""
app.py — HOOPP Risk Navigator 入口

职责:
    1. page config + 全局样式注入
    2. sidebar: 日期选择器
    3. 调用 engine.build_context() 拿到 ctx
    4. 依次 render 5 个 Tab

不放任何计算逻辑。所有数据都从 ctx 取。
"""

import streamlit as st
import pandas as pd
from pathlib import Path

import engine

# ============================================================
# 1. Page Config（必须是文件里第一个 Streamlit 调用）
# ============================================================

st.set_page_config(
    page_title="HOOPP Risk Navigator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


from ui_components import GLOBAL_CSS, COLORS, get_chart_layout
st.markdown(GLOBAL_CSS, unsafe_allow_html=True) 

# ============================================================
# 2. 全局 CSS
# ============================================================

GLOBAL_CSS = """
<style>
/* ── 全局背景 + 字体 ── */
.stApp {
    background-color: #0f1923;
    color: #e8edf2;
    font-family: 'Segoe UI', 'Roboto', sans-serif;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #0a1420;
    border-right: 1px solid #1e3a5f;
}
[data-testid="stSidebar"] .stMarkdown h2 {
    color: #00b4d8;
}

/* ── Tab 条 ── */
.stTabs [data-baseweb="tab-list"] {
    background-color: #0f1923;
    border-bottom: 1px solid #1e3a5f;
    gap: 8px;
}
/* 激活 tab */
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
    color: #00b4d8 !important;
    border-bottom: 2px solid #00b4d8 !important;
    background-color: transparent !important;
}
/* 未激活 tab */
.stTabs [data-baseweb="tab-list"] button {
    color: #8a9bb0;
    background-color: transparent;
}

/* ── Metric 卡片 (st.metric) ── */
[data-testid="stMetric"] {
    background-color: #162232;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
    padding: 12px 16px;
}
[data-testid="stMetricLabel"] {
    color: #8a9bb0 !important;
    font-size: 0.85rem;
}
[data-testid="stMetricValue"] {
    color: #00b4d8 !important;
    font-size: 1.5rem;
    font-weight: 600;
}
[data-testid="stMetricDelta"] {
    color: #8a9bb0 !important;
    font-size: 0.75rem;
}

/* ── 表格样式 ── */
.stDataFrame {
    background-color: #162232;
    border: 1px solid #1e3a5f;
    border-radius: 8px;
}

/* ── 自定义 section title ── */
.section-title {
    color: #00b4d8;
    font-size: 0.9rem;
    font-weight: 600;
    margin-bottom: 8px;
    letter-spacing: 0.5px;
}

/* ── 隐藏 Streamlit 默认的 hamburger menu 和 footer ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* ── 小标题样式 ── */
h4 {
    color: #e8edf2 !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    margin-bottom: 12px !important;
}
</style>
"""

# ============================================================
# 3. 数据加载（缓存）
# ============================================================

@st.cache_data
def load_data():
    """读 CSV，返回原始 DataFrame。只在启动时跑一次。"""
    base = Path(__file__).resolve().parent / "data"
    df_all    = pd.read_csv(base / "hoopp_positions_sample.csv", parse_dates=["timestamp"])
    df_policy = pd.read_csv(base / "policy_limit_management.csv")
    return df_all, df_policy

df_all, df_policy = load_data()

# ============================================================
# 4. Sidebar
# ============================================================

with st.sidebar:
    # Logo 区域
    st.markdown("""
        <div style="text-align:center; padding: 20px 0 10px 0;">
            <span style="font-size: 1.8rem; font-weight: 700; color: #00b4d8;">📊</span>
            <br>
            <span style="font-size: 1.1rem; font-weight: 600; color: #e8edf2;">HOOPP</span>
            <br>
            <span style="font-size: 0.75rem; color: #8a9bb0; letter-spacing: 1.5px; text-transform: uppercase;">Risk Navigator</span>
        </div>
        <hr style="border-color: #1e3a5f; margin: 10px 0;">
    """, unsafe_allow_html=True)

    # 日期选择器
    st.markdown('<div class="section-title">📅 Report Date</div>', unsafe_allow_html=True)

    available_dates = sorted(df_all['timestamp'].unique())
    selected_date = st.selectbox(
        label="Select Date",
        options=available_dates,
        index=len(available_dates) - 1,
        format_func=lambda d: pd.Timestamp(d).strftime("%Y-%m-%d (%a)"),
        label_visibility="collapsed",
    )

    # 简短说明
    st.markdown(
        f'<div style="color:#8a9bb0; font-size:0.78rem; margin-top:6px;">'
        f'Data: {len(available_dates)} trading days<br>'
        f'Positions: {len(df_all[df_all["timestamp"] == selected_date])} records'
        f'</div>',
        unsafe_allow_html=True,
    )
    
    st.markdown("<hr style='border-color: #1e3a5f; margin: 20px 0;'>", unsafe_allow_html=True)
    
    # 版本信息
    st.markdown(
        '<div style="color:#8a9bb0; font-size:0.7rem; text-align:center;">'
        'v1.0 · Tab 1 Preview<br>'
        '© 2026 Risk Analytics'
        '</div>',
        unsafe_allow_html=True,
    )

# ============================================================
# 5. 调用 engine，拿到 ctx
# ============================================================

ctx = engine.build_context(df_all, df_policy, selected_date)

# ============================================================
# 6. Tab 渲染
# ============================================================

from tabs.tab_fund_health import render as render_fund_health
from tabs.tab_limit_monitor import render as render_limit_monitor
from tabs.tab_stress import render as render_stress
from tabs.tab_ai_copilot import render as render_ai_copilot
from tabs.tab_pipeline import render as render_data_pipeline
   

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Fund Health",
    "🚦 Limit Monitor",
    "🌪️ Stress Testing",
    "🤖 AI Copilot",
    "🔧 Data Control(Pipeline)",
])

with tab1:
    render_fund_health(ctx)
with tab2:
    render_limit_monitor(ctx)
with tab3:
    render_stress(ctx)
with tab4:
    render_ai_copilot(ctx)

