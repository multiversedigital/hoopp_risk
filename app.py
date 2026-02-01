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
    layout="wide",                  # 桌面用宽布局，移动端 Streamlit 自动单列
    initial_sidebar_state="expanded",
)

# ============================================================
# 2. 全局 CSS
# ============================================================
# 颜色体系:
#   背景:   #0f1923 (深蓝黑)  — 金融终端感的核心
#   主色:   #00b4d8 (冰蓝)    — 主要 accent，按钮、标题高亮
#   辅色:   #48cae4 (浅蓝)    — 次级 accent
#   文字:   #e8edf2 (浅灰白)  — 正文
#   副文字: #8a9bb0 (灰蓝)    — label、caption
#   卡片:   #162232 (略浅深蓝)— 和背景有微小对比度差
#   边界:   #1e3a5f (深蓝)    — 卡片 border、分隔线
#
#   状态色 (保持通用, 不改):
#     绿: #00c9a7   橙: #f9a825   红: #e74c3c

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
[data-testid="stSidear"] .stMarkdown h2 {
    color: #00b4d8;
}

/* ── Tab 条 ── */
.stTabs [data-baseid="tab-bar"] {
    background-color: #0f1923;
    border-bottom: 1px solid #1e3a5f;
}
/* 激活 tab 下划线颜色 */
.stTabs [data-baseid="tab-bar"] button[aria-selected="true"] {
    color: #00b4d8 !important;
    border-bottom-color: #00b4d8 !important;
}
/* 未激活 tab 文字 */
.stTabs [data-baseid="tab-bar"] button {
    color: #8a9bb0;
}

/* ── Metric 卡片 (st.metric) ── */
[data-testid="stMetric"] {
    background-color: #162232;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 12px 16px;
}
[data-testid="stMetric"] [data-testid="metricValueDiv"] {
    color: #00b4d8;
    font-size: 1.6rem !important;
    font-weight: 700;
}
[data-testid="stMetric"] [data-testid="metricLabelDiv"] {
    color: #8a9bb0;
    font-size: 0.82rem !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Dataframe / 表格 ── */
.stDataframe {
    border-radius: 8px;
    overflow: hidden;
}
.stDataframe table {
    background-color: #162232;
    color: #e8edf2;
    border-collapse: collapse;
}
.stDataframe th {
    background-color: #1a2d42;
    color: #00b4d8;
    font-weight: 600;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    border-bottom: 1px solid #1e3a5f;
    padding: 10px 12px;
}
.stDataframe td {
    border-bottom: 1px solid #1e3a5f;
    padding: 8px 12px;
    font-size: 0.9rem;
}
.stDataframe tr:last-child td {
    border-bottom: none;
}

/* ── Plotly 图表背景透明 → 继承页面深色 ── */
.stPlotlyChart {
    background-color: transparent !important;
}

/* ── Slider ── */
.stSlider [data-testid="stSlider"] {
    color: #00b4d8;
}

/* ── Button ── */
.stButton button {
    background-color: #00b4d8;
    color: #0f1923;
    border: none;
    border-radius: 6px;
    font-weight: 600;
    font-size: 0.88rem;
    padding: 8px 20px;
    cursor: pointer;
    transition: background-color 0.2s;
}
.stButton button:hover {
    background-color: #48cae4;
}

/* ── Text Input (AI 对话框) ── */
.stTextInput input {
    background-color: #162232;
    color: #e8edf2;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
    padding: 10px 14px;
}
.stTextInput input:focus {
    border-color: #00b4d8;
    box-shadow: 0 0 0 2px rgba(0, 180, 216, 0.2);
    outline: none;
}

/* ── Selectbox / Dropdown ── */
.stSelectbox select {
    background-color: #162232;
    color: #e8edf2;
    border: 1px solid #1e3a5f;
    border-radius: 6px;
}

/* ── Section 标题 helper (.section-title) ── */
.section-title {
    color: #00b4d8;
    font-size: 1.05rem;
    font-weight: 600;
    margin-bottom: 8px;
    letter-spacing: 0.3px;
    border-bottom: 1px solid #1e3a5f;
    padding-bottom: 6px;
}

/* ── 卡片容器 helper (.card) ── */
.card {
    background-color: #162232;
    border: 1px solid #1e3a5f;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 12px;
}
</style>
"""

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ============================================================
# 3. 数据加载（缓存，避免每次 rerun 都读 CSV）
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
    # 默认选最新日期
    selected_date = st.selectbox(
        label="Select Date",               # label 显示在上面
        options=available_dates,
        index=len(available_dates) - 1,     # 默认最后一个（最新）
        format_func=lambda d: pd.Timestamp(d).strftime("%Y-%m-%d (%a)"),
        label_visibility="collapsed",       # label 用上面的 section-title 代替
    )

    # 简短说明
    st.markdown(
        f'<div style="color:#8a9bb0; font-size:0.78rem; margin-top:6px;">'
        f'Data: {len(available_dates)} trading days<br>'
        f'Positions: {len(df_all[df_all["timestamp"] == selected_date])} records'
        f'</div>',
        unsafe_allow_html=True,
    )

# ============================================================
# 5. 调用 engine，拿到 ctx
# ============================================================

ctx = engine.build_context(df_all, df_policy, selected_date)

# ============================================================
# 6. Tab 渲染
# ============================================================
# 每个 Tab 文件只暴露 render(ctx)，这里依次调用。
# import 放在这里（不放顶部）是为了让 Streamlit 先完成 page_config，
# 虽然实际上 import 顺序不影响 page_config，但习惯上保持入口文件的
# 阅读顺序和执行顺序一致。

"""
from tabs.tab_fund_health    import render as render_fund_health
from tabs.tab_limit_monitor  import render as render_limit_monitor
from tabs.tab_stress         import render as render_stress
from tabs.tab_pipeline       import render as render_pipeline
from tabs.tab_ai_advisor     import render as render_ai_advisor
"""

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Fund Health",
    "🚦 Compliance",
    "🌪️ Stress Testing",
    "🔧 Data Pipeline",
    "🤖 AI Advisor",
])

"""
with tab1:
    render_fund_health(ctx)

with tab2:
    render_limit_monitor(ctx)

with tab3:
    render_stress(ctx)

with tab4:
    render_pipeline(ctx)

with tab5:
    render_ai_advisor(ctx)
"""