"""
tab_ai_copilot.py — Tab 4: AI Copilot (Decoupled UI Layer)

设计理念:
    - UI 与逻辑完全分离
    - 本文件只负责渲染，不包含业务逻辑
    - 核心 Agent 逻辑在 agent_logic.py (可独立测试)

对外暴露: render(ctx)
"""

import streamlit as st
from ui_components import COLORS, render_section_header

# ============================================================
# 从 agent_logic 导入核心功能 (解耦的关键)
# ============================================================
from agent_logic import (
    run_agent,
    build_system_prompt,
    ThinkingStep,
    COMPLIANCE_LIMITS,
)


# ============================================================
# 预设问题
# ============================================================
QUICK_QUESTIONS = {
    "📊 Snapshot": "Give me a quick snapshot of our current risk metrics - funded status, duration gap, and any concerns.",
    "⚠️ Limits": "Check all risk limits and highlight any breaches or warnings that need immediate attention.",
    "🎚️ Stress": "Run a stress test with rates up 100bp and equity down 15%. What's the impact?",
    "🛡️ Hedge 85%": "I want to increase our duration hedge ratio to 85%. Check if this is compliant.",
    "📈 Rates": "Which assets are most sensitive to interest rate changes?",
}


# ============================================================
# 主渲染函数
# ============================================================

def render(ctx: dict):
    """Tab 4 主入口 - 纯 UI 渲染"""
    
    # ── 初始化 Session State ──
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'thinking_steps' not in st.session_state:
        st.session_state.thinking_steps = []

    # ── 检查 API Key ──
    api_key = _get_api_key()

    # ── 构建 System Prompt (调用 agent_logic) ──
    system_prompt = build_system_prompt(ctx)

    # ── 布局: 左侧聊天 (2/3) + 右侧思考面板 (1/3) ──
    col_main, col_thinking = st.columns([2, 1])
    
    with col_main:
        _render_status_summary(ctx)
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        _render_quick_questions(api_key, system_prompt, ctx)
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        _render_chat_section(api_key, system_prompt, ctx)
    
    with col_thinking:
        _render_thinking_panel()


# ============================================================
# UI 组件: 状态摘要
# ============================================================

def _render_status_summary(ctx: dict):
    """渲染风险状态摘要"""
    render_section_header("Portfolio Status", "📋")
    
    funded_status = ctx['funded_status']
    surplus = ctx['surplus']
    fx_pct = ctx['fx_pct']
    duration_gap = ctx['asset_dur'] - ctx['liability_dur']
    
    limits_df = ctx['limits_df']
    breaches = len(limits_df[limits_df['Status'].str.contains('BREACH', na=False)])
    warnings = len(limits_df[limits_df['Status'].str.contains('WARN', na=False)])

    # 状态判断
    if breaches > 0:
        status_icon, status_text, status_color = "🔴", f"{breaches} BREACH", COLORS['negative']
    elif warnings > 0:
        status_icon, status_text, status_color = "🟡", f"{warnings} WARNING", COLORS['warning']
    else:
        status_icon, status_text, status_color = "🟢", "ALL OK", COLORS['positive']

    st.markdown(
        f"""
        <div style="
            background-color: {COLORS['bg_card']};
            border: 1px solid {COLORS['bg_border']};
            border-radius: 8px;
            padding: 16px;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                <span style="font-weight: 600; color: {COLORS['text_primary']};">Risk Dashboard</span>
                <span style="
                    background-color: {status_color}20;
                    color: {status_color};
                    padding: 4px 12px;
                    border-radius: 16px;
                    font-size: 0.8rem;
                    font-weight: 600;
                ">{status_icon} {status_text}</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;">
                <div style="text-align: center;">
                    <div style="color: {COLORS['text_tertiary']}; font-size: 0.75rem;">Funded</div>
                    <div style="color: {COLORS['positive']}; font-size: 1.1rem; font-weight: 600;">{funded_status:.1%}</div>
                </div>
                <div style="text-align: center;">
                    <div style="color: {COLORS['text_tertiary']}; font-size: 0.75rem;">Surplus</div>
                    <div style="color: {COLORS['text_primary']}; font-size: 1.1rem; font-weight: 600;">${surplus/1000:.1f}B</div>
                </div>
                <div style="text-align: center;">
                    <div style="color: {COLORS['text_tertiary']}; font-size: 0.75rem;">Duration Gap</div>
                    <div style="color: {COLORS['text_primary']}; font-size: 1.1rem; font-weight: 600;">{duration_gap:.1f} yrs</div>
                </div>
                <div style="text-align: center;">
                    <div style="color: {COLORS['text_tertiary']}; font-size: 0.75rem;">FX Exp</div>
                    <div style="color: {COLORS['warning'] if fx_pct > 0.12 else COLORS['text_primary']}; font-size: 1.1rem; font-weight: 600;">{fx_pct:.1%}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# UI 组件: 快速问题
# ============================================================

def _render_quick_questions(api_key: str, system_prompt: str, ctx: dict):
    """渲染快速问题按钮"""
    render_section_header("Quick Actions", "⚡")
    
    cols = st.columns(5)
    
    for i, (label, question) in enumerate(QUICK_QUESTIONS.items()):
        with cols[i]:
            disabled = not api_key
            if st.button(label, use_container_width=True, disabled=disabled, key=f"quick_{i}"):
                _process_user_input(question, system_prompt, ctx, api_key)
                st.rerun()


# ============================================================
# UI 组件: 聊天区域
# ============================================================

def _render_chat_section(api_key: str, system_prompt: str, ctx: dict):
    """渲染聊天区域"""
    render_section_header("Conversation", "💬")
    
    # 聊天历史
    chat_container = st.container(height=280)
    with chat_container:
        if not st.session_state.chat_history:
            st.markdown(
                f"""
                <div style="color: {COLORS['text_tertiary']}; text-align: center; padding: 30px 20px;">
                    <p style="font-size: 1rem; margin-bottom: 8px;">👋 Welcome to AI Risk Advisor</p>
                    <p style="font-size: 0.85rem;">Ask about risk metrics, run stress tests, or propose hedging strategies.</p>
                    <p style="font-size: 0.8rem; color: {COLORS['accent']}; margin-top: 12px;">
                        💡 Try "Hedge 85%" to see the Audit Loop in action!
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
    
    # 输入区域
    if not api_key:
        st.warning("⚠️ OpenAI API key not configured. Add `OPENAI_API_KEY` to `.streamlit/secrets.toml`")
        st.chat_input("Type your question...", disabled=True)
        return

    col_input, col_clear = st.columns([6, 1])
    
    with col_clear:
        if st.button("🗑️", use_container_width=True, help="Clear conversation"):
            st.session_state.chat_history = []
            st.session_state.thinking_steps = []
            st.rerun()

    user_input = st.chat_input("Ask about risk, stress tests, or hedging strategies...")

    if user_input:
        _process_user_input(user_input, system_prompt, ctx, api_key)
        st.rerun()


# ============================================================
# UI 组件: 思考面板 (Thinking Panel)
# ============================================================

def _render_thinking_panel():
    """渲染思考过程面板"""
    st.markdown(
        f"""
        <div style="
            background-color: {COLORS['bg_card']};
            border: 1px solid {COLORS['bg_border']};
            border-radius: 8px;
            padding: 16px;
            min-height: 450px;
        ">
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
                padding-bottom: 12px;
                border-bottom: 1px solid {COLORS['bg_border']};
            ">
                <span style="font-size: 0.95rem; font-weight: 600; color: {COLORS['text_primary']};">
                    🧠 Agent Thinking
                </span>
                <span style="
                    font-size: 0.7rem;
                    color: {COLORS['accent']};
                    background-color: {COLORS['accent']}15;
                    padding: 2px 8px;
                    border-radius: 4px;
                ">Audit Loop</span>
            </div>
        """,
        unsafe_allow_html=True,
    )
    
    if not st.session_state.thinking_steps:
        st.markdown(
            f"""
            <div style="color: {COLORS['text_tertiary']}; font-size: 0.85rem; padding: 20px; text-align: center;">
                <p style="margin-bottom: 12px;">Agent workflow will appear here.</p>
                <div style="font-size: 0.75rem; line-height: 1.8; text-align: left; padding: 0 10px;">
                    <p>🔍 <strong>Analyze</strong> → Understand intent</p>
                    <p>⚙️ <strong>Calculate</strong> → Run risk engine</p>
                    <p>🛡️ <strong>Audit</strong> → Check compliance</p>
                    <p>🔄 <strong>Refine</strong> → Auto-correct if needed</p>
                    <p>💬 <strong>Respond</strong> → Generate answer</p>
                </div>
                <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid {COLORS['bg_border']};">
                    <p style="font-size: 0.7rem; color: {COLORS['text_tertiary']};">
                        Max Hedge: {COMPLIANCE_LIMITS['max_hedge_ratio']:.0%} | 
                        Max FX: {COMPLIANCE_LIMITS['max_fx_exposure']:.0%}
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for step in st.session_state.thinking_steps:
            _render_thinking_step(step)
    
    st.markdown("</div>", unsafe_allow_html=True)


def _render_thinking_step(step: ThinkingStep):
    """渲染单个思考步骤"""
    status_config = {
        "running": {"icon": "⏳", "color": COLORS['warning'], "bg": f"{COLORS['warning']}15"},
        "success": {"icon": "✅", "color": COLORS['positive'], "bg": f"{COLORS['positive']}15"},
        "warning": {"icon": "⚠️", "color": COLORS['warning'], "bg": f"{COLORS['warning']}15"},
        "error": {"icon": "❌", "color": COLORS['negative'], "bg": f"{COLORS['negative']}15"},
    }
    
    config = status_config.get(step.status, status_config["running"])
    
    detail_html = ""
    if step.detail:
        detail_html = f"<div style='font-size: 0.75rem; color: {COLORS['text_tertiary']}; margin-top: 4px; font-style: italic;'>{step.detail}</div>"
    
    st.markdown(
        f"""
        <div style="
            background-color: {config['bg']};
            border-left: 3px solid {config['color']};
            border-radius: 4px;
            padding: 10px 12px;
            margin-bottom: 8px;
        ">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>{config['icon']}</span>
                <span style="font-size: 0.85rem; font-weight: 600; color: {COLORS['text_primary']};">{step.node}</span>
            </div>
            <div style="font-size: 0.8rem; color: {COLORS['text_secondary']}; margin-top: 4px;">
                {step.message}
            </div>
            {detail_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 核心处理函数 (调用 agent_logic)
# ============================================================

def _process_user_input(user_input: str, system_prompt: str, ctx: dict, api_key: str):
    """
    处理用户输入 - 调用解耦的 agent_logic
    
    这里只做:
    1. 更新 session state
    2. 调用 run_agent()
    3. 保存结果
    """
    # 添加用户消息
    st.session_state.chat_history.append({"role": "user", "content": user_input})
    
    # 清空之前的思考步骤
    st.session_state.thinking_steps = []
    
    try:
        # ========================================
        # 核心调用 - agent_logic.run_agent()
        # ========================================
        response, thinking_steps = run_agent(
            user_query=user_input,
            ctx=ctx,
            system_prompt=system_prompt,
            api_key=api_key,
        )
        
        # 保存思考步骤
        st.session_state.thinking_steps = thinking_steps
        
        # 添加助手响应
        st.session_state.chat_history.append({"role": "assistant", "content": response})

    except Exception as e:
        st.session_state.thinking_steps.append(ThinkingStep(
            node="❌ Error",
            status="error",
            message=str(e),
        ))
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": f"I apologize, but I encountered an error: {str(e)}",
        })


# ============================================================
# 辅助函数
# ============================================================

def _get_api_key() -> str:
    """获取 API Key"""
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except:
        return ""