"""
app.py — HOOPP Risk Navigator 入口

职责:
    1. page config + 全局样式注入
    2. sidebar: 日期选择器 + HOOPP Logo
    3. 调用 engine.build_context() 拿到 ctx
    4. 依次 render 5 个 Tab

设计: 方案 C 混合主题 (深色侧边栏 + 浅色内容区)
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
    page_icon="🌳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# 2. 全局 CSS (从 ui_components 导入)
# ============================================================

from ui_components import GLOBAL_CSS, COLORS, get_chart_layout
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

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
# 4. Sidebar (方案 C: 深色侧边栏 + 文字 Logo)
# ============================================================

with st.sidebar:
    # ── 文字 Logo (避免版权问题) ──
    st.markdown(
        """
        <div style="text-align: center; padding: 20px 0 10px 0;">
            <span style="font-size: 2.5rem;">🌳</span>
            <br>
            <span style="font-size: 1.5rem; font-weight: 700; color: #00843D; letter-spacing: 2px;">HOOPP</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # ── 副标题 ──
    st.markdown(
        """
        <div style="text-align: center; margin-top: 4px; margin-bottom: 20px;">
            <span style="color: #94a3b8; font-size: 0.75rem; font-weight: 500; letter-spacing: 1px; text-transform: uppercase;">
                AI Powered Risk Reporting & Monitoring
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("<hr style='border-color: #1e293b; margin: 10px 0 20px 0;'>", unsafe_allow_html=True)

    # ── 日期选择器 ──
    st.markdown(
        '<div style="color: #e2e8f0; font-size: 0.9rem; font-weight: 600; margin-bottom: 8px;">📅 Report Date</div>',
        unsafe_allow_html=True,
    )

    available_dates = sorted(df_all['timestamp'].unique())
    selected_date = st.selectbox(
        label="Select Date",
        options=available_dates,
        index=len(available_dates) - 1,
        format_func=lambda d: pd.Timestamp(d).strftime("%Y-%m-%d (%a)"),
        label_visibility="collapsed",
    )
    
    st.markdown("<hr style='border-color: #1e293b; margin: 20px 0 16px 0;'>", unsafe_allow_html=True)
    
    # ── System Configuration (机构风格) ──
    num_positions = len(df_all[df_all["timestamp"] == selected_date])
    
    st.markdown(
        f"""
        <div style="font-size: 0.8rem; color: #94a3b8;">
            <strong style="color: #e2e8f0; letter-spacing: 0.5px;">⚙️ SYSTEM CONFIGURATION</strong>
            <ul style="padding-left: 0; margin-top: 10px; line-height: 1.9; list-style-type: none;">
                <li style="margin-bottom: 6px;">
                    <span style="color: #64748b;">Data Source:</span><br>
                    <span style="color: #e2e8f0; padding-left: 8px;">Synthetic HOOPP Portfolio</span>
                </li>
                <li style="margin-bottom: 6px;">
                    <span style="color: #64748b;">Data Coverage:</span><br>
                    <span style="color: #e2e8f0; padding-left: 8px;">{len(available_dates)} days · {num_positions} positions</span>
                </li>
                <li style="margin-bottom: 6px;">
                    <span style="color: #64748b;">Valuation Model:</span><br>
                    <span style="color: #e2e8f0; padding-left: 8px;">Linear Sensitivity (Delta-Normal)</span>
                </li>
                <li style="margin-bottom: 6px;">
                    <span style="color: #64748b;">AI Engine:</span><br>
                    <span style="color: #e2e8f0; padding-left: 8px;">GPT-4o （OpenAI API）</span>
                </li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("<hr style='border-color: #1e293b; margin: 16px 0;'>", unsafe_allow_html=True)
    
    # ── 底部品牌 ──
    st.markdown(
        """
        <div style="text-align: center; padding: 8px 0;">
            <span style="color: #94a3b8; font-size: 0.85rem; font-weight: 500;">Risk Navigator</span>
            <span style="color: #64748b; font-size: 0.75rem;"> · v1.0 Preview</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================
# 5. 调用 engine，拿到 ctx
# ============================================================

ctx = engine.build_context(df_all, df_policy, selected_date)

# ============================================================
# 6. Tab 渲染
# ============================================================

from tabs.tab_funding_status import render as render_funding_status
from tabs.tab_limit_monitor import render as render_limit_monitor
from tabs.tab_stress import render as render_stress
from tabs.tab_ai_copilot import render as render_ai_copilot
from tabs.tab_data_governance import render as render_data_governance


tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Funding Status",
    "🚦 Limit Monitor",
    "🎚️ Stress Testing",
    "🤖 AI Copilot",
    "🛡️ Data Governance (in pipeline)",
])

with tab1:
    render_funding_status(ctx)

with tab2:
    render_limit_monitor(ctx)

with tab3:
    render_stress(ctx)

with tab4:
    render_ai_copilot(ctx)

with tab5:
    render_data_governance(ctx)














