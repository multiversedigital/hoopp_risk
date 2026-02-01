"""
tab_ai_copilot.py — Tab 5: AI Copilot

职责:
    智能风险顾问，基于 OpenAI GPT-4 提供自然语言交互
    - Smart Summary: 自动生成的当日风险摘要
    - Quick Questions: 预设问题快速入口
    - Chat: 多轮对话问答

对外暴露: render(ctx)
"""

import streamlit as st
from openai import OpenAI

# ============================================================
# 颜色常量
# ============================================================
COLOR_BG = "#0f1923"
COLOR_CARD = "#162232"
COLOR_BORDER = "#1e3a5f"
COLOR_PRIMARY = "#00b4d8"
COLOR_SECONDARY = "#8a9bb0"

# ============================================================
# 预设问题
# ============================================================
QUICK_QUESTIONS = {
    "📊 Rate Sensitivity": "Which assets in our portfolio are most sensitive to interest rate changes? List the top 5 by duration.",
    "⚠️ Top Risks": "What are the top 3 risks in today's portfolio that I should focus on?",
    "🚦 Limit Status": "Summarize today's limit breaches and warnings. Which ones need immediate attention?",
    "🥧 Allocation": "How does our current asset allocation compare to policy targets? Highlight any significant deviations.",
    "📈 Duration Gap": "Explain our current duration gap between assets and liabilities. What does this mean for our interest rate risk?",
}


def render(ctx: dict):
    """
    Tab 5 主入口。
    """
    # ─────────────────────────────────────────────────────────
    # 初始化 Session State
    # ─────────────────────────────────────────────────────────
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    # ─────────────────────────────────────────────────────────
    # 检查 API Key
    # ─────────────────────────────────────────────────────────
    api_key_available = _check_api_key()

    # ─────────────────────────────────────────────────────────
    # 构建 System Prompt
    # ─────────────────────────────────────────────────────────
    system_prompt = _build_system_prompt(ctx)

    # ─────────────────────────────────────────────────────────
    # 顶部: Smart Summary
    # ─────────────────────────────────────────────────────────
    st.markdown("#### 📋 Smart Summary")
    _render_smart_summary(ctx)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # 中部: Quick Questions
    # ─────────────────────────────────────────────────────────
    st.markdown("#### 💬 Quick Questions")
    _render_quick_questions(api_key_available, system_prompt)

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────
    # 主体: Chat History
    # ─────────────────────────────────────────────────────────
    st.markdown("#### 🗨️ Chat")
    _render_chat_history()

    # ─────────────────────────────────────────────────────────
    # 底部: Input Box
    # ─────────────────────────────────────────────────────────
    _render_chat_input(api_key_available, system_prompt)


# ============================================================
# 私有函数
# ============================================================

def _check_api_key() -> bool:
    """检查 OpenAI API Key 是否配置"""
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", None)
        return api_key is not None and len(api_key) > 10
    except Exception:
        return False


def _build_system_prompt(ctx: dict) -> str:
    """
    构建 System Prompt，包含完整的投资组合上下文。
    """
    # 基础 KPI
    funded_status = ctx['funded_status']
    total_assets = ctx['total_assets']
    total_liabilities = ctx['total_liabilities']
    surplus = ctx['surplus']
    asset_dur = ctx['asset_dur']
    liability_dur = ctx['liability_dur']
    duration_gap = asset_dur - liability_dur
    fx_pct = ctx['fx_pct']

    # 资产配置表
    comp_df = ctx['comp_df']
    allocation_str = comp_df[['asset_class', 'current_weight', 'policy_target']].to_string(index=False)

    # 限额状态表
    limits_df = ctx['limits_df']
    limits_str = limits_df[['asset_class', 'current_weight', 'range_min', 'range_max', 'Status']].to_string(index=False)

    # Top Issuers
    issuer_df = ctx['issuer_df']
    issuer_str = issuer_df.to_string(index=False)

    system_prompt = f"""You are a Risk Advisor for HOOPP (Healthcare of Ontario Pension Plan), a $124B Canadian defined benefit pension fund.
Your role is to analyze portfolio data and provide clear, actionable insights to risk managers.

=== CURRENT PORTFOLIO SNAPSHOT ===

Key Metrics:
- Funded Status: {funded_status:.1%} (Target: 111%)
- Total Assets: ${total_assets/1000:.1f}B
- Total Liabilities: ${total_liabilities/1000:.1f}B
- Surplus: ${surplus/1000:.1f}B
- Asset Duration: {asset_dur:.1f} years
- Liability Duration: {liability_dur:.1f} years
- Duration Gap: {duration_gap:.1f} years (negative means liabilities have longer duration)
- FX Exposure: {fx_pct:.1%} (Limit: 15%)

Asset Allocation (Current vs Policy Target):
{allocation_str}

Limit Status (🔴 BREACH / 🟡 WARN / 🟢 OK):
{limits_str}

Top 5 Issuers by Concentration:
{issuer_str}

=== INSTRUCTIONS ===

1. Answer questions based ONLY on the data provided above
2. Be concise and professional (risk manager tone)
3. Use bullet points for clarity when listing items
4. Always include units when discussing numbers ($B, %, years, bp)
5. Highlight risks and provide actionable insights
6. If the data is insufficient to answer a question, clearly say so
7. When discussing rate sensitivity, remember: Duration × Rate Change = Price Change
8. Positive duration gap means assets are less sensitive to rates than liabilities

Keep responses focused and under 200 words unless more detail is specifically requested.
"""
    return system_prompt


def _render_smart_summary(ctx: dict):
    """
    渲染自动生成的风险摘要。
    """
    # 从 ctx 获取预生成的摘要，如果没有则生成简单版本
    summary = ctx.get('ai_context_summary', None)

    if not summary:
        # Fallback: 生成简单摘要
        funded_status = ctx['funded_status']
        surplus = ctx['surplus']
        fx_pct = ctx['fx_pct']
        
        # 检查 breach
        limits_df = ctx['limits_df']
        breaches = limits_df[limits_df['Status'].str.contains('BREACH')]
        warnings = limits_df[limits_df['Status'].str.contains('WARN')]

        alerts = []
        if len(breaches) > 0:
            alerts.append(f"🔴 {len(breaches)} limit breach(es)")
        if len(warnings) > 0:
            alerts.append(f"🟡 {len(warnings)} warning(s)")

        alert_text = " | ".join(alerts) if alerts else "🟢 All limits OK"

        summary = f"""**Fund Status**: Funded ratio at **{funded_status:.1%}**, surplus **${surplus/1000:.1f}B**

**Alerts**: {alert_text}

**FX Exposure**: {fx_pct:.1%} {'(⚠️ Above 15% limit!)' if fx_pct > 0.15 else '(Within limit)'}
"""

    st.markdown(
        f"""
        <div style="background-color:{COLOR_CARD}; border:1px solid {COLOR_BORDER}; 
                    border-radius:10px; padding:16px; line-height:1.6;">
        {summary}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_quick_questions(api_key_available: bool, system_prompt: str):
    """
    渲染预设问题按钮。
    """
    cols = st.columns(len(QUICK_QUESTIONS))

    for i, (label, question) in enumerate(QUICK_QUESTIONS.items()):
        with cols[i]:
            if st.button(label, use_container_width=True, disabled=not api_key_available):
                _handle_user_input(question, system_prompt)
                st.rerun()


def _render_chat_history():
    """
    渲染对话历史。
    """
    chat_container = st.container(height=350)

    with chat_container:
        if not st.session_state.chat_history:
            st.markdown(
                f"""
                <div style="color:{COLOR_SECONDARY}; text-align:center; padding:50px 20px;">
                    <p style="font-size:1.1rem;">👋 Ask me anything about today's portfolio!</p>
                    <p style="font-size:0.85rem;">Try the Quick Questions above or type your own question below.</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])


def _render_chat_input(api_key_available: bool, system_prompt: str):
    """
    渲染输入框。
    """
    if not api_key_available:
        st.warning("⚠️ OpenAI API key not configured. Add `OPENAI_API_KEY` to `.streamlit/secrets.toml`")
        st.chat_input("Type your question...", disabled=True)
        return

    user_input = st.chat_input("Type your question about the portfolio...")

    if user_input:
        _handle_user_input(user_input, system_prompt)
        st.rerun()


def _handle_user_input(user_input: str, system_prompt: str):
    """
    处理用户输入，调用 OpenAI API 获取响应。
    """
    # 添加用户消息到历史
    st.session_state.chat_history.append({
        "role": "user",
        "content": user_input,
    })

    # 调用 API
    try:
        response = _call_openai_api(system_prompt, st.session_state.chat_history)

        # 添加助手响应到历史
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response,
        })

    except Exception as e:
        # 错误处理
        error_msg = f"❌ Error calling API: {str(e)}"
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": error_msg,
        })


def _call_openai_api(system_prompt: str, chat_history: list) -> str:
    """
    调用 OpenAI API。
    """
    client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

    # 构建消息列表
    messages = [{"role": "system", "content": system_prompt}]

    # 添加对话历史 (最近 10 轮)
    recent_history = chat_history[-20:]  # 最多 20 条消息 (10 轮对话)
    messages.extend(recent_history)

    # 调用 API
    response = client.chat.completions.create(
        model="gpt-4o-mini",  # 使用 gpt-4o-mini，性价比高
        messages=messages,
        max_tokens=500,
        temperature=0.3,  # 低温度，更确定性的回答
    )

    return response.choices[0].message.content


# ============================================================
# 清除对话历史 (可选功能)
# ============================================================
def _render_clear_button():
    """
    渲染清除对话按钮。
    """
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()
