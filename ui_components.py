"""
ui_components.py — HOOPP Risk Navigator 机构级 UI 组件库

设计理念:
    - BlackRock Aladdin 的 "Invisible UI" — 数据优先
    - MSCI RiskMetrics 的专业仪表盘风格

对外暴露:
    - GLOBAL_CSS: 全局样式字符串
    - render_kpi_card(): KPI 卡片组件
    - render_status_badge(): 状态徽章
    - render_section_header(): 区块标题
    - get_chart_layout(): Plotly 图表通用布局
    - COLORS: 颜色常量字典
"""

import streamlit as st

# ============================================================
# 颜色系统
# ============================================================
COLORS = {
    # 背景层级
    'bg_page': '#0a0e14',
    'bg_card': '#12171f',
    'bg_hover': '#1a2332',
    'bg_border': '#262f3d',
    
    # 文字层级
    'text_primary': '#f0f4f8',
    'text_secondary': '#94a3b8',
    'text_tertiary': '#64748b',
    
    # 语义色
    'positive': '#10b981',
    'negative': '#ef4444',
    'warning': '#f59e0b',
    'info': '#3b82f6',
    
    # 强调色
    'accent': '#6366f1',
    'accent_secondary': '#8b5cf6',
    
    # 图表色板
    'chart_primary': '#6366f1',
    'chart_secondary': '#8b5cf6',
    'chart_tertiary': '#3b82f6',
}

# 图表色板
CHART_COLORS = ['#6366f1', '#818cf8', '#a5b4fc', '#c7d2fe', '#e0e7ff']
ASSET_COLORS = {
    'Fixed Income': '#3b82f6',
    'Public Equities': '#10b981',
    'Private Real Estate': '#f59e0b',
    'Private Infrastructure': '#8b5cf6',
    'Private Credit': '#ec4899',
    'Cash & Funding': '#64748b',
}

# ============================================================
# 全局 CSS
# ============================================================
GLOBAL_CSS = """
<style>
/* ============================================================
   HOOPP Risk Navigator - Institutional Grade UI
   Inspired by BlackRock Aladdin & MSCI RiskMetrics
   ============================================================ */

/* ── CSS Variables ── */
:root {
    --bg-page: #0a0e14;
    --bg-card: #12171f;
    --bg-hover: #1a2332;
    --bg-border: #262f3d;
    
    --text-primary: #f0f4f8;
    --text-secondary: #94a3b8;
    --text-tertiary: #64748b;
    
    --positive: #10b981;
    --negative: #ef4444;
    --warning: #f59e0b;
    --info: #3b82f6;
    
    --accent: #6366f1;
    --accent-secondary: #8b5cf6;
    
    --radius-sm: 4px;
    --radius-md: 8px;
    --radius-lg: 12px;
    
    --transition: 0.15s ease;
}

/* ── Global Reset ── */
.stApp {
    background-color: var(--bg-page);
    color: var(--text-primary);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* ── 去掉顶部留白 ── */
.block-container {
    padding-top: 1rem !important;
    padding-bottom: 1rem !important;
}

header[data-testid="stHeader"] {
    background-color: transparent;
    height: 0;
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background-color: #080b10;
    border-right: 1px solid var(--bg-border);
}

[data-testid="stSidebar"] [data-testid="stMarkdown"] {
    color: var(--text-secondary);
}

/* ── Tab Bar ── */
.stTabs [data-baseweb="tab-list"] {
    background-color: transparent;
    border-bottom: 1px solid var(--bg-border);
    gap: 0;
}

.stTabs [data-baseweb="tab"] {
    color: var(--text-secondary);
    background-color: transparent;
    border: none;
    padding: 16px 24px;
    font-size: 0.95rem;
    font-weight: 500;
    transition: var(--transition);
    cursor: pointer;
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-primary);
    background-color: var(--bg-hover);
}

.stTabs [aria-selected="true"] {
    color: var(--accent) !important;
    background-color: transparent !important;
    border-bottom: 2px solid var(--accent) !important;
}

/* ── Metric Cards (st.metric) ── */
[data-testid="stMetric"] {
    background-color: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-md);
    padding: 16px 20px;
    transition: var(--transition);
}

[data-testid="stMetric"]:hover {
    background-color: var(--bg-hover);
    border-color: var(--accent);
}

[data-testid="stMetric"] label {
    color: var(--text-tertiary) !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
}

[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: var(--text-primary) !important;
    font-size: 1.75rem !important;
    font-weight: 600 !important;
    font-variant-numeric: tabular-nums !important;
}

[data-testid="stMetric"] [data-testid="stMetricDelta"] {
    font-size: 0.8rem !important;
    font-weight: 500 !important;
}

[data-testid="stMetric"] [data-testid="stMetricDelta"][data-testid-delta-type="positive"] {
    color: var(--positive) !important;
}

[data-testid="stMetric"] [data-testid="stMetricDelta"][data-testid-delta-type="negative"] {
    color: var(--negative) !important;
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
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.3px !important;
    padding: 12px 16px !important;
    border-bottom: 1px solid var(--bg-border) !important;
}

.stDataFrame tbody tr td {
    background-color: var(--bg-card) !important;
    color: var(--text-primary) !important;
    font-size: 0.875rem !important;
    padding: 10px 16px !important;
    border-bottom: 1px solid var(--bg-border) !important;
    font-variant-numeric: tabular-nums !important;
}

.stDataFrame tbody tr:hover td {
    background-color: var(--bg-hover) !important;
}

/* ── Buttons ── */
.stButton button {
    background-color: var(--accent);
    color: white;
    border: none;
    border-radius: var(--radius-sm);
    padding: 8px 16px;
    font-size: 0.875rem;
    font-weight: 500;
    transition: var(--transition);
    cursor: pointer;
}

.stButton button:hover {
    background-color: var(--accent-secondary);
    transform: translateY(-1px);
}

.stButton button:active {
    transform: translateY(0);
}

/* Secondary Button Style */
.stButton button[kind="secondary"] {
    background-color: transparent;
    border: 1px solid var(--bg-border);
    color: var(--text-secondary);
}

.stButton button[kind="secondary"]:hover {
    background-color: var(--bg-hover);
    border-color: var(--accent);
    color: var(--text-primary);
}

/* ── Sliders ── */
.stSlider [data-baseweb="slider"] {
    margin-top: 8px;
}

.stSlider [data-testid="stTickBar"] {
    background-color: var(--bg-border);
}

.stSlider [data-testid="stThumbValue"] {
    color: var(--text-primary);
    font-weight: 500;
}

/* Slider track and thumb colors */
.stSlider [data-baseweb="slider"] [role="slider"] {
    background-color: var(--accent) !important;
}

.stSlider [data-baseweb="slider"] div[data-testid="stTickBar"] > div {
    background-color: var(--accent) !important;
}

.stSlider label {
    color: var(--text-secondary) !important;
}

.stSlider [data-baseweb="slider"] div:first-child {
    background-color: var(--bg-border) !important;
}

/* ── Select Box ── */
.stSelectbox [data-baseweb="select"] {
    background-color: var(--bg-card);
    border-color: var(--bg-border);
}

.stSelectbox [data-baseweb="select"]:hover {
    border-color: var(--accent);
}

/* ── Text Input ── */
.stTextInput input {
    background-color: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-sm);
    color: var(--text-primary);
    padding: 10px 14px;
}

.stTextInput input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
}

/* ── Chat Input ── */
.stChatInput {
    background-color: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-md);
}

/* ── Plotly Charts ── */
.stPlotlyChart {
    background-color: transparent !important;
}

/* ── Section Headers ── */
.section-header {
    color: var(--text-primary);
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--bg-border);
    display: flex;
    align-items: center;
    gap: 8px;
}

.section-header .icon {
    font-size: 1.1rem;
}

/* ── Status Badges ── */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 4px 10px;
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
}

.status-badge.ok {
    background-color: rgba(16, 185, 129, 0.15);
    color: var(--positive);
}

.status-badge.warn {
    background-color: rgba(245, 158, 11, 0.15);
    color: var(--warning);
}

.status-badge.breach {
    background-color: rgba(239, 68, 68, 0.15);
    color: var(--negative);
}

/* ── Info Cards ── */
.info-card {
    background-color: var(--bg-card);
    border: 1px solid var(--bg-border);
    border-radius: var(--radius-md);
    padding: 20px;
    transition: var(--transition);
}

.info-card:hover {
    border-color: var(--accent);
}

.info-card .title {
    color: var(--text-tertiary);
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 8px;
}

.info-card .value {
    color: var(--text-primary);
    font-size: 1.5rem;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
}

.info-card .delta {
    font-size: 0.8rem;
    font-weight: 500;
    margin-top: 4px;
}

.info-card .delta.positive {
    color: var(--positive);
}

.info-card .delta.negative {
    color: var(--negative);
}

/* ── Dividers ── */
.divider {
    height: 1px;
    background-color: var(--bg-border);
    margin: 24px 0;
}

/* ── Scrollbar ── */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-page);
}

::-webkit-scrollbar-thumb {
    background: var(--bg-border);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--text-tertiary);
}

/* ── Responsive Adjustments ── */
@media (max-width: 768px) {
    [data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.25rem !important;
    }
    
    .stDataFrame thead tr th,
    .stDataFrame tbody tr td {
        padding: 8px 12px !important;
        font-size: 0.8rem !important;
    }
}

/* ── Animation ── */
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
    animation: fadeIn 0.3s ease-out;
}
</style>
"""


# ============================================================
# 组件函数
# ============================================================

def render_section_header(title: str, icon: str = ""):
    """渲染区块标题"""
    st.markdown(
        f'<div class="section-header">'
        f'<span class="icon">{icon}</span>'
        f'{title}'
        f'</div>',
        unsafe_allow_html=True
    )


def render_status_badge(status: str) -> str:
    """
    返回状态徽章的 HTML。
    status: 'ok', 'warn', 'breach'
    """
    labels = {
        'ok': '🟢 OK',
        'warn': '🟡 WARN', 
        'breach': '🔴 BREACH'
    }
    return f'<span class="status-badge {status}">{labels.get(status, status)}</span>'


def render_info_card(title: str, value: str, delta: str = None, delta_type: str = "neutral"):
    """
    渲染自定义 KPI 卡片 (用于需要更多控制的场景)
    """
    delta_html = ""
    if delta:
        delta_class = "positive" if delta_type == "positive" else "negative" if delta_type == "negative" else ""
        delta_html = f'<div class="delta {delta_class}">{delta}</div>'
    
    st.markdown(
        f'''
        <div class="info-card">
            <div class="title">{title}</div>
            <div class="value">{value}</div>
            {delta_html}
        </div>
        ''',
        unsafe_allow_html=True
    )


def render_divider():
    """渲染分隔线"""
    st.markdown('<div class="divider"></div>', unsafe_allow_html=True)


def get_chart_layout(height: int = 300) -> dict:
    """
    返回 Plotly 图表的通用布局配置。
    保持所有图表风格一致。
    注意：不包含 legend，让每个图表自定义。
    """
    return {
        'height': height,
        'margin': dict(l=20, r=20, t=40, b=40),
        'paper_bgcolor': 'rgba(0,0,0,0)',
        'plot_bgcolor': 'rgba(0,0,0,0)',
        'font': {
            'family': 'Inter, sans-serif',
            'color': COLORS['text_secondary'],
            'size': 12,
        },
        'title': None,
        'showlegend': True,
        'xaxis': {
            'gridcolor': COLORS['bg_border'],
            'linecolor': COLORS['bg_border'],
            'tickfont': {'size': 10, 'color': COLORS['text_tertiary']},
            'zeroline': False,
        },
        'yaxis': {
            'gridcolor': COLORS['bg_border'],
            'linecolor': COLORS['bg_border'],
            'tickfont': {'size': 10, 'color': COLORS['text_tertiary']},
            'zeroline': False,
        },
        'hovermode': 'x unified',
        'hoverlabel': {
            'bgcolor': COLORS['bg_hover'],
            'bordercolor': COLORS['bg_border'],
            'font': {'color': COLORS['text_primary'], 'size': 12},
        },
    }


def format_number(value: float, prefix: str = "", suffix: str = "", decimals: int = 1) -> str:
    """
    格式化数字显示。
    支持自动缩写 (B, M, K) 和千分符。
    """
    if abs(value) >= 1e9:
        return f"{prefix}{value/1e9:,.{decimals}f}B{suffix}"
    elif abs(value) >= 1e6:
        return f"{prefix}{value/1e6:,.{decimals}f}M{suffix}"
    elif abs(value) >= 1e3:
        return f"{prefix}{value/1e3:,.{decimals}f}K{suffix}"
    else:
        return f"{prefix}{value:,.{decimals}f}{suffix}"


def format_percent(value: float, decimals: int = 1) -> str:
    """格式化百分比显示"""
    return f"{value * 100:,.{decimals}f}%"


def format_delta(value: float, prefix: str = "", suffix: str = "", decimals: int = 2) -> str:
    """格式化变化值 (带正负号)"""
    sign = "+" if value >= 0 else ""
    return f"{sign}{format_number(value, prefix, suffix, decimals)}"
