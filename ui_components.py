"""
ui_components.py — HOOPP Risk Navigator UI 组件库

设计理念:
    - 方案 C: 混合主题 (深色侧边栏 + 浅色内容区)
    - HOOPP 品牌绿色 #00843D
    - 机构级风险系统风格

对外暴露:
    - GLOBAL_CSS: 全局样式字符串
    - COLORS: 颜色常量字典
    - render_section_header(): 区块标题
    - get_chart_layout(): Plotly 图表通用布局
    - format_number(), format_percent(): 格式化函数
"""

import streamlit as st

# ============================================================
# 颜色系统 - 方案 C 混合主题
# ============================================================
COLORS = {
    # 侧边栏 (深色)
    'sidebar_bg': '#0f172a',
    'sidebar_text': '#e2e8f0',
    'sidebar_text_muted': '#94a3b8',
    'sidebar_border': '#1e293b',
    
    # 主内容区 (浅色)
    'bg_page': '#f8fafc',
    'bg_card': '#ffffff',
    'bg_hover': '#f1f5f9',
    'bg_border': '#e2e8f0',
    
    # 文字 (深色文字用于浅色背景)
    'text_primary': '#1e293b',
    'text_secondary': '#475569',
    'text_tertiary': '#64748b',
    
    # 语义色
    'positive': '#00843D',      # HOOPP 绿
    'negative': '#dc2626',
    'warning': '#f59e0b',
    'info': '#0284c7',
    
    # 强调色 - HOOPP 绿
    'accent': '#00843D',
    'accent_light': '#00a34a',
    'accent_bg': 'rgba(0, 132, 61, 0.1)',
    
    # 图表色板
    'chart_primary': '#00843D',
    'chart_secondary': '#0284c7',
    'chart_tertiary': '#7c3aed',
}

# 资产类别颜色
ASSET_COLORS = {
    'Fixed Income': '#0284c7',
    'Public Equities': '#00843D',
    'Private Real Estate': '#f59e0b',
    'Private Infrastructure': '#7c3aed',
    'Private Credit': '#db2777',
    'Cash & Funding': '#64748b',
}

# 图表色板
CHART_COLORS = ['#00843D', '#0284c7', '#7c3aed', '#f59e0b', '#db2777', '#64748b']

# ============================================================
# 全局 CSS - 方案 C 混合主题
# ============================================================
GLOBAL_CSS = """
<style>
/* ============================================================
   HOOPP Risk Navigator - Hybrid Theme
   深色侧边栏 + 浅色内容区
   ============================================================ */

/* ── CSS Variables ── */
:root {
    /* 侧边栏 */
    --sidebar-bg: #0f172a;
    --sidebar-text: #e2e8f0;
    --sidebar-text-muted: #94a3b8;
    --sidebar-border: #1e293b;
    
    /* 主内容区 */
    --bg-page: #f8fafc;
    --bg-card: #ffffff;
    --bg-hover: #f1f5f9;
    --bg-border: #e2e8f0;
    
    /* 文字 */
    --text-primary: #1e293b;
    --text-secondary: #475569;
    --text-tertiary: #64748b;
    
    /* 语义色 */
    --positive: #00843D;
    --negative: #dc2626;
    --warning: #f59e0b;
    --info: #0284c7;
    
    /* 强调色 */
    --accent: #00843D;
    --accent-light: #00a34a;
    
    /* 圆角 */
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    
    --transition: 0.15s ease;
}

/* ── 主内容区背景 ── */
.stApp {
    background-color: var(--bg-page) !important;
    font-size: 16px !important;
}

.stApp > header {
    background-color: transparent !important;
}

.main .block-container {
    background-color: var(--bg-page);
    padding-top: 1.5rem !important;
    padding-bottom: 1rem !important;
    max-width: 1400px;
    font-size: 1rem !important;
}

/* 全局字体增大 */
.stMarkdown, .stMarkdown p, .stMarkdown span {
    font-size: 1.05rem !important;
    line-height: 1.6 !important;
}

/* ── 侧边栏样式 ── */
[data-testid="stSidebar"] {
    background-color: var(--sidebar-bg) !important;
    border-right: 1px solid var(--sidebar-border);
}

[data-testid="stSidebar"] * {
    color: var(--sidebar-text) !important;
}

[data-testid="stSidebar"] .stMarkdown p {
    color: var(--sidebar-text-muted) !important;
}

[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
    color: var(--sidebar-text-muted) !important;
}

/* 侧边栏下拉框 */
[data-testid="stSidebar"] [data-baseweb="select"] {
    background-color: var(--sidebar-border) !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: var(--sidebar-border) !important;
    border-color: var(--sidebar-border) !important;
    color: var(--sidebar-text) !important;
}

/* 侧边栏折叠按钮 */
[data-testid="stSidebar"] button[kind="header"] {
    color: var(--sidebar-text) !important;
}

[data-testid="collapsedControl"] {
    color: var(--text-primary) !important;
    background-color: var(--bg-card) !important;
}

/* ── Tab Bar ── */
.stTabs [data-baseweb="tab-list"] {
    background-color: var(--bg-card) !important;
    border-bottom: 2px solid var(--bg-border) !important;
    gap: 0 !important;
    border-radius: var(--radius-md) var(--radius-md) 0 0 !important;
    padding: 0 8px !important;
}

.stTabs [data-baseweb="tab"] {
    color: var(--text-primary) !important;
    background-color: transparent !important;
    border: none !important;
    padding: 20px 32px !important;
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    transition: var(--transition) !important;
    cursor: pointer !important;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-primary) !important;
    background-color: var(--bg-hover) !important;
}

.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    background-color: transparent !important;
    border-bottom: 3px solid var(--accent) !important;
    font-weight: 700 !important;
}

/* Tab 内容区 */
.stTabs [data-baseweb="tab-panel"] {
    background-color: var(--bg-card);
    border-radius: 0 0 var(--radius-md) var(--radius-md);
    padding: 24px;
    border: 1px solid var(--bg-border);
    border-top: none;
}

/* ── Metric Cards ── */
[data-testid="stMetric"] {
    background-color: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-md);
    padding: 20px;
    transition: var(--transition);
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

[data-testid="stMetric"]:hover {
    border-color: var(--accent);
    box-shadow: 0 4px 12px rgba(0, 132, 61, 0.1);
}

[data-testid="stMetric"] [data-testid="stMetricLabel"] {
    color: var(--text-tertiary) !important;
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-size: 2.4rem !important;
    font-weight: 700 !important;
    font-variant-numeric: tabular-nums !important;
}

[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-size: 1rem !important;
    font-weight: 500 !important;
}

[data-testid="stMetricDelta"] svg {
    display: none;
}

/* ── Data Tables ── */
.stDataFrame {
    border-radius: var(--radius-md);
    overflow: hidden;
}

.stDataFrame [data-testid="stDataFrameResizable"] {
    background-color: var(--bg-card);
    border: 1px solid var(--bg-border);
}

.stDataFrame thead tr th {
    background-color: var(--bg-hover) !important;
    color: var(--text-tertiary) !important;
    font-size: 0.95rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.3px !important;
    padding: 16px 18px !important;
    border-bottom: 2px solid var(--bg-border) !important;
}

.stDataFrame tbody tr td {
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
    font-size: 1.1rem !important;
    padding: 16px 18px !important;
    border-bottom: 1px solid var(--bg-border) !important;
    font-variant-numeric: tabular-nums !important;
}

.stDataFrame tbody tr:hover td {
    background-color: var(--bg-hover) !important;
}

/* ── Buttons ── */
.stButton button {
    background-color: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: var(--radius-md) !important;
    padding: 16px 32px !important;
    font-weight: 600 !important;
    font-size: 1.05rem !important;
    transition: var(--transition) !important;
}
    transition: var(--transition) !important;
}

.stButton button:hover {
    background-color: var(--accent-light) !important;
    box-shadow: 0 4px 12px rgba(0, 132, 61, 0.3) !important;
}

.stButton button:disabled {
    background-color: var(--bg-border) !important;
    color: var(--text-tertiary) !important;
}

/* Secondary Buttons */
.stButton button[kind="secondary"] {
    background-color: transparent !important;
    color: var(--accent) !important;
    border: 2px solid var(--accent) !important;
}

.stButton button[kind="secondary"]:hover {
    background-color: var(--accent) !important;
    color: white !important;
}

/* ── Selectbox ── */
[data-baseweb="select"] > div {
    background-color: var(--bg-card) !important;
    border-color: var(--bg-border) !important;
    border-radius: var(--radius-md) !important;
    color: var(--text-primary) !important;
    font-size: 1rem !important;
}

[data-baseweb="select"] > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 2px rgba(0, 132, 61, 0.2) !important;
}

/* Dropdown menu */
[data-baseweb="popover"] {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--bg-border) !important;
    border-radius: var(--radius-md) !important;
}

[data-baseweb="menu"] {
    background-color: var(--bg-card) !important;
}

[data-baseweb="menu"] li {
    color: var(--text-primary) !important;
    font-size: 1rem !important;
}

[data-baseweb="menu"] li:hover {
    background-color: var(--bg-hover) !important;
}

/* ── Sliders ── */
.stSlider label p {
    color: var(--text-secondary) !important;
    font-size: 0.95rem !important;
    font-weight: 500 !important;
}

.stSlider [data-testid="stThumbValue"] {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
    background: var(--bg-card) !important;
    padding: 2px 8px;
    border-radius: 4px;
}

.stSlider [data-baseweb="slider"] > div > div {
    background-color: var(--bg-border) !important;
}

.stSlider [data-baseweb="slider"] > div > div > div {
    background-color: var(--accent) !important;
}

.stSlider [role="slider"] {
    background-color: var(--accent) !important;
    border-color: var(--accent) !important;
}

/* ── Chat Input ── */
.stChatInput {
    border-color: var(--bg-border) !important;
}

.stChatInput > div {
    border: 2px solid var(--bg-border) !important;
    border-radius: var(--radius-md) !important;
    background-color: var(--bg-card) !important;
}

.stChatInput > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(0, 132, 61, 0.15) !important;
}

.stChatInput textarea {
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
    font-size: 1.1rem !important;
    border-radius: var(--radius-md) !important;
    min-height: 70px !important;
    padding: 18px !important;
}

.stChatInput textarea::placeholder {
    color: var(--text-tertiary) !important;
    font-size: 1.05rem !important;
}

/* ── Chat Messages ── */
.stChatMessage {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--bg-border) !important;
    border-radius: var(--radius-md) !important;
    padding: 16px !important;
    margin-bottom: 12px !important;
}

[data-testid="stChatMessageContent"] {
    color: var(--text-primary) !important;
    font-size: 1rem !important;
    line-height: 1.6 !important;
}

/* ── Expander ── */
.streamlit-expanderHeader {
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
    font-size: 1rem !important;
    font-weight: 600 !important;
    border-radius: var(--radius-md) !important;
}

.streamlit-expanderContent {
    background-color: var(--bg-card) !important;
    border: 1px solid var(--bg-border) !important;
}

/* ── Warning/Info boxes ── */
.stAlert {
    border-radius: var(--radius-md) !important;
    font-size: 1rem !important;
}

/* ── Divider ── */
hr {
    border-color: var(--bg-border) !important;
}

/* ── Section Header ── */
.section-header {
    display: flex !important;
    align-items: center !important;
    gap: 12px !important;
    margin-bottom: 20px !important;
    padding-bottom: 14px !important;
    border-bottom: 2px solid var(--bg-border) !important;
}

.section-header .icon {
    font-size: 1.5rem !important;
}

.section-header .title {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    margin: 0 !important;
}

/* ── Plotly Charts ── */
.js-plotly-plot {
    border-radius: var(--radius-md);
}

/* 隐藏 Plotly 图表的 undefined title */
.js-plotly-plot .gtitle {
    display: none !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-hover);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb {
    background: var(--bg-border);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--text-tertiary);
}

/* ── Hide Streamlit Defaults ── */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {
    background-color: transparent;
}

/* ── Animation ── */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(8px); }
    to { opacity: 1; transform: translateY(0); }
}

.stTabs [data-baseweb="tab-panel"] > div {
    animation: fadeIn 0.2s ease-out;
}
</style>
"""

# ============================================================
# 辅助函数
# ============================================================

def render_section_header(title: str, icon: str = "📊"):
    """渲染区块标题"""
    st.markdown(
        f"""
        <div class="section-header">
            <span class="icon">{icon}</span>
            <h3 class="title">{title}</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )


def get_chart_layout(height: int = 300) -> dict:
    """
    返回 Plotly 图表的通用布局配置 (浅色主题)。
    """
    return {
        'height': height,
        'margin': dict(l=20, r=20, t=40, b=40),
        'paper_bgcolor': 'rgba(255,255,255,0)',
        'plot_bgcolor': 'rgba(255,255,255,0)',
        'font': {
            'family': 'Inter, -apple-system, sans-serif',
            'color': COLORS['text_secondary'],
            'size': 13,
        },
        'title': None,
        'showlegend': True,
        'xaxis': {
            'gridcolor': COLORS['bg_border'],
            'linecolor': COLORS['bg_border'],
            'tickfont': {'size': 12, 'color': COLORS['text_tertiary']},
            'zeroline': False,
        },
        'yaxis': {
            'gridcolor': COLORS['bg_border'],
            'linecolor': COLORS['bg_border'],
            'tickfont': {'size': 12, 'color': COLORS['text_tertiary']},
            'zeroline': False,
        },
        'hovermode': 'x unified',
        'hoverlabel': {
            'bgcolor': COLORS['bg_card'],
            'bordercolor': COLORS['bg_border'],
            'font': {'color': COLORS['text_primary'], 'size': 13},
        },
    }


def format_number(value: float, prefix: str = "", suffix: str = "", decimals: int = 1) -> str:
    """
    格式化数字，自动选择 B/M/K 单位。
    """
    abs_val = abs(value)
    sign = "-" if value < 0 else ""
    
    if abs_val >= 1_000_000_000:
        formatted = f"{abs_val / 1_000_000_000:.{decimals}f}B"
    elif abs_val >= 1_000_000:
        formatted = f"{abs_val / 1_000_000:.{decimals}f}M"
    elif abs_val >= 1_000:
        formatted = f"{abs_val / 1_000:.{decimals}f}K"
    else:
        formatted = f"{abs_val:.{decimals}f}"
    
    return f"{prefix}{sign}{formatted}{suffix}"


def format_percent(value: float, decimals: int = 1) -> str:
    """格式化为百分比"""
    return f"{value * 100:.{decimals}f}%"


def format_delta(value: float, prefix: str = "", suffix: str = "", decimals: int = 2) -> str:
    """格式化变化值，带正负号"""
    sign = "+" if value >= 0 else ""
    return f"{sign}{format_number(value, prefix, suffix, decimals)}"


def render_status_badge(status: str) -> str:
    """返回状态徽章的 HTML"""
    status_lower = status.lower()
    
    if 'breach' in status_lower:
        bg_color = 'rgba(220, 38, 38, 0.1)'
        text_color = COLORS['negative']
        icon = '🔴'
    elif 'warn' in status_lower:
        bg_color = 'rgba(245, 158, 11, 0.1)'
        text_color = COLORS['warning']
        icon = '🟡'
    else:
        bg_color = 'rgba(0, 132, 61, 0.1)'
        text_color = COLORS['positive']
        icon = '🟢'
    
    return f"""
    <span style="
        background-color: {bg_color};
        color: {text_color};
        padding: 4px 10px;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
    ">{icon} {status}</span>
    """