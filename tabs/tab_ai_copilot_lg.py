"""
tab_ai_copilot_lg.py — Tab: AI Copilot (LangGraph Version) - Enhanced UI

增强特性:
    1. 实时节点追踪: st.status 动态显示当前执行节点
    2. 审计失败高亮: 红色/黄色警示 + 自动修正提示
    3. 工具调用透明化: 显示函数名、参数、返回值

对外暴露: render(ctx)
"""

import streamlit as st
import time
from ui_components import COLORS, render_section_header

from agent_logic_lg import (
    run_agent_stream,
    build_system_prompt,
    ThinkingStep,
    COMPLIANCE_LIMITS,
)


# ============================================================
# 节点状态消息映射
# ============================================================
NODE_STATUS_MESSAGES = {
    "analyze": ("🔍", "Analyzing risk intent...", "Intent Analysis"),
    "calculate": ("⚙️", "Calling Risk Engine...", "Risk Calculation"),
    "audit": ("🛡️", "Running compliance audit...", "Compliance Audit"),
    "refine": ("🔄", "Compliance risk detected! Auto-correcting...", "Auto Refinement"),
    "respond": ("💬", "Generating response...", "Response Generation"),
}


# ============================================================
# 预设问题
# ============================================================
QUICK_QUESTIONS = {
    "📊 Summary": "Give me a summary of our current risk position.",
    "⚠️ Limits": "Check all risk limits and highlight any breaches.",
    "🎚️ Stress": "Run a stress test with rates up 100bp and equity down 15%.",
    "🛡️ Hedge 85%": "I want to increase our duration hedge ratio to 85%.",
    "📈 Rates": "Which assets are most sensitive to interest rate changes?",
}


# ============================================================
# 主渲染函数
# ============================================================

def render(ctx: dict):
    """Tab 主入口 - LangGraph 增强版"""
    
    # ── Beta 标签 ──
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(90deg, {COLORS['accent']}20, transparent);
            border-left: 3px solid {COLORS['accent']};
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
        ">
            <span style="
                background-color: {COLORS['accent']};
                color: white;
                padding: 2px 8px;
                border-radius: 4px;
                font-size: 0.7rem;
                font-weight: 700;
            ">BETA</span>
            <span style="color: {COLORS['text_secondary']}; font-size: 0.85rem;">
                <strong>LangGraph Engine</strong> — Real-time node tracking with tool-use transparency
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # ── 初始化 Session State ──
    if 'lg_chat_history' not in st.session_state:
        st.session_state.lg_chat_history = []
    if 'lg_thinking_steps' not in st.session_state:
        st.session_state.lg_thinking_steps = []

    # ── 检查 API Key ──
    api_key = _get_api_key()
    system_prompt = build_system_prompt(ctx)

    # ── 布局 ──
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
            if st.button(label, use_container_width=True, disabled=not api_key, key=f"lg_quick_{i}"):
                _process_user_input_with_status(question, system_prompt, ctx, api_key)


# ============================================================
# UI 组件: 聊天区域
# ============================================================

def _render_chat_section(api_key: str, system_prompt: str, ctx: dict):
    """渲染聊天区域"""
    render_section_header("Conversation", "💬")
    
    chat_container = st.container(height=280)
    with chat_container:
        if not st.session_state.lg_chat_history:
            st.markdown(
                f"""
                <div style="color: {COLORS['text_tertiary']}; text-align: center; padding: 30px 20px;">
                    <p style="font-size: 1rem; margin-bottom: 8px;">🧪 LangGraph AI Risk Advisor</p>
                    <p style="font-size: 0.85rem;">Watch real-time node execution in the Thinking Panel →</p>
                    <p style="font-size: 0.8rem; color: {COLORS['accent']}; margin-top: 12px;">
                        💡 Try "Hedge 85%" to see the Audit Loop in action!
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for message in st.session_state.lg_chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
    
    if not api_key:
        st.warning("⚠️ OpenAI API key not configured.")
        st.chat_input("Type your question...", disabled=True)
        return

    col_input, col_clear = st.columns([6, 1])
    
    with col_clear:
        if st.button("🗑️", use_container_width=True, help="Clear", key="lg_clear"):
            st.session_state.lg_chat_history = []
            st.session_state.lg_thinking_steps = []
            st.rerun()

    user_input = st.chat_input("Ask about risk, stress tests, or hedging...", key="lg_input")

    if user_input:
        _process_user_input_with_status(user_input, system_prompt, ctx, api_key)


# ============================================================
# UI 组件: 思考面板 (增强版)
# ============================================================

def _render_thinking_panel():
    """渲染思考过程面板 - 增强版"""
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
                    🧠 LangGraph Execution
                </span>
                <span style="
                    font-size: 0.7rem;
                    color: {COLORS['accent']};
                    background-color: {COLORS['accent']}15;
                    padding: 2px 8px;
                    border-radius: 4px;
                ">StateGraph</span>
            </div>
        """,
        unsafe_allow_html=True,
    )
    
    if not st.session_state.lg_thinking_steps:
        st.markdown(
            f"""
            <div style="color: {COLORS['text_tertiary']}; font-size: 0.85rem; padding: 20px;">
                <p style="margin-bottom: 16px; text-align: center;">Waiting for execution...</p>
                <div style="font-size: 0.75rem; line-height: 2;">
                    <p>🔍 <code>analyze</code> → Intent detection</p>
                    <p>⚙️ <code>calculate</code> → Risk engine</p>
                    <p>🛡️ <code>audit</code> → Compliance check</p>
                    <p>🔄 <code>refine</code> → Auto-correction</p>
                    <p>💬 <code>respond</code> → LLM response</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for step in st.session_state.lg_thinking_steps:
            _render_thinking_step_enhanced(step)
    
    st.markdown("</div>", unsafe_allow_html=True)


def _render_thinking_step_enhanced(step: ThinkingStep):
    """渲染单个思考步骤 - 增强版 (含工具调用信息)"""
    
    # 状态配置
    status_config = {
        "running": {"icon": "⏳", "color": COLORS['warning'], "bg": f"{COLORS['warning']}10", "border": COLORS['warning']},
        "success": {"icon": "✅", "color": COLORS['positive'], "bg": f"{COLORS['positive']}10", "border": COLORS['positive']},
        "warning": {"icon": "⚠️", "color": "#ff6b6b", "bg": "#ff6b6b15", "border": "#ff6b6b"},
        "error": {"icon": "❌", "color": COLORS['negative'], "bg": f"{COLORS['negative']}10", "border": COLORS['negative']},
    }
    
    config = status_config.get(step.status, status_config["running"])
    
    # 特殊处理: 审计失败高亮
    if step.is_warning:
        config = {
            "icon": "🚨",
            "color": "#ff4757",
            "bg": "#ff475720",
            "border": "#ff4757",
        }
    
    # 构建 HTML
    tool_info_html = ""
    if step.tool_call:
        tool_info_html += f"""
        <div style="
            margin-top: 8px;
            padding: 8px;
            background-color: {COLORS['bg_hover']};
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', monospace;
            font-size: 0.7rem;
        ">
            <div style="color: {COLORS['accent']};">📦 {step.tool_call}</div>
        """
        if step.tool_params:
            tool_info_html += f"""<div style="color: {COLORS['text_tertiary']}; margin-top: 2px;">├─ params: {step.tool_params}</div>"""
        if step.tool_result:
            tool_info_html += f"""<div style="color: {COLORS['positive']}; margin-top: 2px;">└─ result: {step.tool_result}</div>"""
        tool_info_html += "</div>"
    
    detail_html = ""
    if step.detail:
        detail_html = f"<div style='font-size: 0.75rem; color: {COLORS['text_tertiary']}; margin-top: 4px;'>{step.detail}</div>"
    
    st.markdown(
        f"""
        <div style="
            background-color: {config['bg']};
            border-left: 3px solid {config['border']};
            border-radius: 4px;
            padding: 12px;
            margin-bottom: 10px;
        ">
            <div style="display: flex; align-items: center; gap: 8px;">
                <span style="font-size: 1rem;">{config['icon']}</span>
                <span style="font-size: 0.85rem; font-weight: 600; color: {COLORS['text_primary']};">{step.node}</span>
            </div>
            <div style="font-size: 0.8rem; color: {config['color']}; margin-top: 4px; font-weight: 500;">
                {step.message}
            </div>
            {detail_html}
            {tool_info_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# 核心处理函数 - 实时状态追踪版
# ============================================================

def _process_user_input_with_status(user_input: str, system_prompt: str, ctx: dict, api_key: str):
    """
    处理用户输入 - 使用 st.status 实时追踪
    
    关键特性:
    - st.status 显示当前节点
    - 流式更新思考步骤
    - 审计失败特殊处理
    """
    # 添加用户消息
    st.session_state.lg_chat_history.append({"role": "user", "content": user_input})
    st.session_state.lg_thinking_steps = []
    
    # 创建状态容器
    status_placeholder = st.empty()
    
    try:
        with status_placeholder.status("🧠 LangGraph Engine running...", expanded=True) as status:
            final_response = ""
            
            for node_name, state, is_final in run_agent_stream(
                user_query=user_input,
                ctx=ctx,
                system_prompt=system_prompt,
                api_key=api_key,
            ):
                # 获取节点信息
                icon, message, label = NODE_STATUS_MESSAGES.get(
                    node_name, 
                    ("🔄", "Processing...", node_name)
                )
                
                # 更新状态显示
                status.update(label=f"{icon} {message}")
                
                # 写入当前节点执行信息
                st.write(f"**Node:** `{node_name}` — {label}")
                
                # 检查是否审计失败
                audit_result = state.get("audit_result", {})
                if node_name == "audit" and audit_result.get("status") == "FAIL":
                    st.warning("🚨 **Compliance Failed!** Auto-correcting...")
                
                # 收集思考步骤
                if "thinking_steps" in state:
                    st.session_state.lg_thinking_steps = state["thinking_steps"]
                
                # 收集最终响应
                if is_final and state.get("final_response"):
                    final_response = state["final_response"]
                
                # 短暂延迟让用户能看到状态变化
                time.sleep(0.1)
            
            # 完成状态
            status.update(label="✅ Complete", state="complete", expanded=False)
        
        # 添加助手响应
        st.session_state.lg_chat_history.append({
            "role": "assistant",
            "content": final_response or "Unable to generate response",
        })
        
        # 刷新页面显示结果
        st.rerun()

    except Exception as e:
        status_placeholder.empty()
        st.session_state.lg_thinking_steps.append(ThinkingStep(
            node="❌ Error",
            status="error",
            message=str(e),
        ))
        st.session_state.lg_chat_history.append({
            "role": "assistant",
            "content": f"Error: {str(e)}",
        })
        st.rerun()


# ============================================================
# 辅助函数
# ============================================================

def _get_api_key() -> str:
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except:
        return ""