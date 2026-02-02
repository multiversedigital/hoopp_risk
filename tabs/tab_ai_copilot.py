"""
tab_ai_copilot.py — Tab 5: AI Copilot

职责:
    智能风险顾问，基于 OpenAI GPT-4 提供自然语言交互

布局:
    1. Daily Analysis (模板 或 AI 生成)
    2. 输入框 (居中)
    3. Quick Questions
    4. Conversation (页面底部)

对外暴露: render(ctx)
"""

import streamlit as st
from openai import OpenAI
from datetime import datetime

# ============================================================
# 导入统一 UI 组件库
# ============================================================
from ui_components import (
    COLORS,
    render_section_header,
)

# ============================================================
# 预设问题
# ============================================================
QUICK_QUESTIONS = {
    "📊 Rate": "Which assets are most sensitive to interest rate changes? List the top 5 by duration.",
    "⚠️ Risks": "What are the top 3 risks in today's portfolio that I should focus on?",
    "🚦 Limits": "Summarize today's limit breaches and warnings. Which ones need immediate attention?",
    "🥧 Alloc": "How does our current asset allocation compare to policy targets?",
}


def render(ctx: dict):
    """Tab 5 主入口。"""
    
    # ─────────────────────────────────────────────────────────
    # 自定义样式
    # ─────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <style>
        /* Daily Analysis 卡片 */
        .analysis-card {{
            background-color: {COLORS['bg_card']};
            border: 1px solid {COLORS['bg_border']};
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
        }}
        .analysis-card.ai-generated {{
            border-left: 3px solid {COLORS['accent']};
        }}
        .ai-badge {{
            display: inline-block;
            background-color: rgba(99, 102, 241, 0.15);
            color: {COLORS['accent']};
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            margin-bottom: 12px;
        }}
        .analysis-content {{
            color: {COLORS['text_secondary']};
            font-size: 0.9rem;
            line-height: 1.7;
        }}
        .analysis-timestamp {{
            color: {COLORS['text_tertiary']};
            font-size: 0.75rem;
            text-align: right;
            margin-top: 12px;
        }}
        /* Chat 样式 */
        .stChatMessage {{
            background-color: {COLORS['bg_card']} !important;
            border: 1px solid {COLORS['bg_border']} !important;
            border-radius: 8px !important;
        }}
        /* 空状态 */
        .empty-state {{
            color: {COLORS['text_tertiary']};
            text-align: center;
            padding: 40px 20px;
        }}
        .empty-state p {{
            margin: 8px 0;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ─────────────────────────────────────────────────────────
    # 初始化 Session State
    # ─────────────────────────────────────────────────────────
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'ai_analysis' not in st.session_state:
        st.session_state.ai_analysis = None
    if 'ai_analysis_time' not in st.session_state:
        st.session_state.ai_analysis_time = None

    # ─────────────────────────────────────────────────────────
    # 检查 API Key
    # ─────────────────────────────────────────────────────────
    api_key_available = _check_api_key()

    # ─────────────────────────────────────────────────────────
    # 构建 System Prompt
    # ─────────────────────────────────────────────────────────
    system_prompt = _build_system_prompt(ctx)

    # ─────────────────────────────────────────────────────────
    # Section 1: Daily Analysis
    # ─────────────────────────────────────────────────────────
    _render_daily_analysis(ctx, api_key_available, system_prompt)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # Section 2: Input Box (居中)
    # ─────────────────────────────────────────────────────────
    _render_chat_input(api_key_available, system_prompt)

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # Section 3: Quick Questions
    # ─────────────────────────────────────────────────────────
    _render_quick_questions(api_key_available, system_prompt)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # Section 4: Conversation (底部)
    # ─────────────────────────────────────────────────────────
    _render_conversation()


# ============================================================
# Daily Analysis
# ============================================================

def _render_daily_analysis(ctx: dict, api_key_available: bool, system_prompt: str):
    """渲染 Daily Analysis 区域"""
    
    # 标题行：标题 + 按钮
    col_title, col_btn = st.columns([8, 2])
    
    with col_title:
        render_section_header("Daily Analysis", "📋")
    
    with col_btn:
        if st.session_state.ai_analysis:
            # 已有 AI 分析，显示 Refresh 按钮
            if st.button("🔄 Refresh", use_container_width=True, disabled=not api_key_available):
                _generate_ai_analysis(ctx, system_prompt)
                st.rerun()
        else:
            # 还没有 AI 分析，显示生成按钮
            if st.button("✨ AI Insights", use_container_width=True, disabled=not api_key_available):
                _generate_ai_analysis(ctx, system_prompt)
                st.rerun()

    # 内容区域
    if st.session_state.ai_analysis:
        # 显示 AI 生成的分析
        st.markdown(
            f"""
            <div class="analysis-card ai-generated">
                <span class="ai-badge">✨ AI Generated</span>
                <div class="analysis-content">
                    {st.session_state.ai_analysis}
                </div>
                <div class="analysis-timestamp">
                    Generated: {st.session_state.ai_analysis_time}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        # 显示模板生成的摘要
        summary = _generate_template_summary(ctx)
        st.markdown(
            f"""
            <div class="analysis-card">
                <div class="analysis-content">
                    {summary}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _generate_template_summary(ctx: dict) -> str:
    """生成模板摘要 (不调用 API)"""
    limits_df = ctx['limits_df']
    n_breach = len(limits_df[limits_df['Status'].str.contains('BREACH')])
    n_warn = len(limits_df[limits_df['Status'].str.contains('WARN')])

    # 欢迎语
    welcome_text = "Hello Team, this is your AI Copilot. Click <b>[✨ AI Insights]</b> above to generate today's portfolio analysis."
    
    # Alerts
    if n_breach > 0:
        alert_text = f"⚠️ <b>{n_breach} limit breach(es)</b> require attention."
    elif n_warn > 0:
        alert_text = f"🟡 <b>{n_warn} warning(s)</b> to monitor."
    else:
        alert_text = "✅ No limit breaches or warnings today."

    return f"{welcome_text}<br><br>{alert_text}"


def _generate_ai_analysis(ctx: dict, system_prompt: str):
    """调用 GPT 生成深度分析"""
    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        
        prompt = """Based on the portfolio data provided, give a concise daily risk briefing for a pension fund risk manager.

Structure your response as:
1. **Overall Status** - One sentence on fund health
2. **Key Observations** - 2-3 bullet points on the most important things to note today
3. **Watch Items** - Any metrics approaching limits or concerns

Keep it under 150 words. Be specific with numbers. Professional tone."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            temperature=0.3,
        )
        
        # 存储结果
        st.session_state.ai_analysis = response.choices[0].message.content
        st.session_state.ai_analysis_time = datetime.now().strftime("%b %d, %I:%M %p")
        
    except Exception as e:
        st.session_state.ai_analysis = f"❌ Error generating analysis: {str(e)}"
        st.session_state.ai_analysis_time = datetime.now().strftime("%b %d, %I:%M %p")


# ============================================================
# Chat Input
# ============================================================

def _render_chat_input(api_key_available: bool, system_prompt: str):
    """渲染输入框"""
    if not api_key_available:
        st.warning("⚠️ OpenAI API key not configured. Add `OPENAI_API_KEY` to `.streamlit/secrets.toml`")
        st.chat_input("Ask about risks, limits, duration...", disabled=True)
        return

    user_input = st.chat_input("Ask about risks, limits, duration, allocation...")

    if user_input:
        _handle_user_input(user_input, system_prompt)
        st.rerun()


# ============================================================
# Quick Questions
# ============================================================

def _render_quick_questions(api_key_available: bool, system_prompt: str):
    """渲染 Quick Questions + Clear 按钮"""
    
    st.markdown(
        f"<p style='color:{COLORS['text_tertiary']}; font-size:0.85rem; margin-bottom:8px;'>Try asking:</p>",
        unsafe_allow_html=True,
    )
    
    cols = st.columns([1, 1, 1, 1, 1.2])
    
    questions = list(QUICK_QUESTIONS.items())
    for i, (label, question) in enumerate(questions):
        with cols[i]:
            if st.button(label, use_container_width=True, disabled=not api_key_available):
                _handle_user_input(question, system_prompt)
                st.rerun()
    
    # Clear 按钮
    with cols[4]:
        if st.button("🗑️ Clear Chat", help="Clear chat history", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()


# ============================================================
# Conversation
# ============================================================

def _render_conversation():
    """渲染对话历史 (最新在上)"""
    render_section_header("Conversation", "🗨️")
    
    chat_container = st.container(height=300)

    with chat_container:
        if not st.session_state.chat_history:
            st.markdown(
                """
                <div class="empty-state">
                    <p style="font-size:1rem;">💬 No conversation yet</p>
                    <p style="font-size:0.85rem;">Ask a question above to start chatting</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            # 倒序显示，最新的在上面
            for message in reversed(st.session_state.chat_history):
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])


# ============================================================
# 辅助函数
# ============================================================

def _check_api_key() -> bool:
    """检查 OpenAI API Key 是否配置"""
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
        return api_key is not None and len(api_key) > 10
    except Exception:
        return False


def _build_system_prompt(ctx: dict) -> str:
    """构建 System Prompt"""
    funded_status = ctx['funded_status']
    total_assets = ctx['total_assets']
    total_liabilities = ctx['total_liabilities']
    surplus = ctx['surplus']
    asset_dur = ctx['asset_dur']
    liability_dur = ctx['liability_dur']
    duration_gap = asset_dur - liability_dur
    fx_pct = ctx['fx_pct']

    comp_df = ctx['comp_df']
    allocation_str = comp_df[['asset_class', 'current_weight', 'policy_target']].to_string(index=False)

    limits_df = ctx['limits_df']
    limits_str = limits_df[['asset_class', 'current_weight', 'range_min', 'range_max', 'Status']].to_string(index=False)

    issuer_df = ctx['issuer_df']
    issuer_str = issuer_df.to_string(index=False)

    return f"""You are a Risk Advisor for HOOPP (Healthcare of Ontario Pension Plan), a $124B Canadian defined benefit pension fund.

=== CURRENT PORTFOLIO SNAPSHOT ===

Key Metrics:
- Funded Status: {funded_status:.1%} (Target: 111%)
- Total Assets: ${total_assets/1000:.1f}B
- Total Liabilities: ${total_liabilities/1000:.1f}B
- Surplus: ${surplus/1000:.1f}B
- Asset Duration: {asset_dur:.1f} years
- Liability Duration: {liability_dur:.1f} years
- Duration Gap: {duration_gap:.1f} years
- FX Exposure: {fx_pct:.1%} (Limit: 15%)

Asset Allocation:
{allocation_str}

Limit Status:
{limits_str}

Top 5 Issuers:
{issuer_str}

=== INSTRUCTIONS ===
1. Answer based ONLY on the data above
2. Be concise and professional
3. Use bullet points for lists
4. Include units ($B, %, years, bp)
5. Highlight risks and actionable insights
Keep responses under 200 words unless more detail requested."""


def _handle_user_input(user_input: str, system_prompt: str):
    """处理用户输入"""
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input,
    })

    try:
        client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(st.session_state.chat_history[-20:])

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=500,
            temperature=0.3,
        )

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response.choices[0].message.content,
        })

    except Exception as e:
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": f"❌ Error: {str(e)}",
        })