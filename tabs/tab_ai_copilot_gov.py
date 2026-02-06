"""
tab_ai_copilot_gov.py — Tab: AI Copilot (Governance Version)

核心特性:
    1. Tool Calling 透明化: 展示 AI 自主选择的工具
    2. Human-in-the-loop: 审批卡片 UI
    3. 实时节点追踪: st.status 动态更新

与其他版本的区别:
    - tab_ai_copilot.py: 基础版
    - tab_ai_copilot_lg.py: LangGraph 版
    - tab_ai_copilot_gov.py: 治理版 (本文件)

对外暴露: render(ctx)
"""

import streamlit as st
import time
from ui_components import COLORS, render_section_header

from agent_logic_gov import (
    run_agent,
    run_agent_stream,
    process_approval,
    ThinkingStep,
    TOOL_DESCRIPTIONS,
)


# ============================================================
# 节点状态消息映射
# ============================================================
NODE_STATUS_MESSAGES = {
    "analyze": ("🤖", "AI 正在分析意图并选择工具...", "Tool Selection"),
    "execute": ("⚙️", "正在执行风险计算工具...", "Tool Execution"),
    "audit": ("🛡️", "正在进行合规审计...", "Compliance Audit"),
    "respond": ("💬", "正在生成响应...", "Response Generation"),
    "handle_approval": ("✅", "正在处理审批结果...", "Approval Processing"),
}


# ============================================================
# 预设问题
# ============================================================
QUICK_QUESTIONS = {
    "📊 Metrics": "What are our current risk metrics?",
    "⚠️ Limits": "Check limit breaches and warnings",
    "🎚️ Stress": "Run stress test: rates +100bp, equity -15%",
    "🛡️ Hedge 85%": "I want to increase hedge ratio to 85%",
    "📈 Allocation": "Show current asset allocation",
}


# ============================================================
# 主渲染函数
# ============================================================

def render(ctx: dict):
    """Tab 主入口 - 治理版"""
    
    # ── Governance 标签 ──
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(90deg, #6c5ce720, transparent);
            border-left: 3px solid #6c5ce7;
            padding: 12px 16px;
            border-radius: 0 8px 8px 0;
            margin-bottom: 16px;
            display: flex;
            align-items: center;
            gap: 12px;
        ">
            <span style="
                background: linear-gradient(135deg, #6c5ce7, #a29bfe);
                color: white;
                padding: 2px 10px;
                border-radius: 4px;
                font-size: 0.7rem;
                font-weight: 700;
            ">GOVERNANCE</span>
            <span style="color: {COLORS['text_secondary']}; font-size: 0.85rem;">
                <strong>AI-First + Human-in-the-loop</strong> — Tool Calling with approval workflow
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # ── 初始化 Session State ──
    if 'gov_chat_history' not in st.session_state:
        st.session_state.gov_chat_history = []
    if 'gov_thinking_steps' not in st.session_state:
        st.session_state.gov_thinking_steps = []
    if 'gov_pending_approval' not in st.session_state:
        st.session_state.gov_pending_approval = None

    # ── 检查 API Key ──
    api_key = _get_api_key()

    # ── 布局 ──
    col_main, col_thinking = st.columns([2, 1])
    
    with col_main:
        _render_status_summary(ctx)
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        _render_quick_questions(api_key, ctx)
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        _render_chat_section(api_key, ctx)
    
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

def _render_quick_questions(api_key: str, ctx: dict):
    """渲染快速问题按钮"""
    render_section_header("Quick Actions", "⚡")
    
    cols = st.columns(5)
    
    for i, (label, question) in enumerate(QUICK_QUESTIONS.items()):
        with cols[i]:
            # 如果有待审批任务，禁用按钮
            disabled = not api_key or st.session_state.gov_pending_approval is not None
            if st.button(label, use_container_width=True, disabled=disabled, key=f"gov_quick_{i}"):
                _process_user_input_with_status(question, ctx, api_key)


# ============================================================
# UI 组件: 聊天区域
# ============================================================

def _render_chat_section(api_key: str, ctx: dict):
    """渲染聊天区域"""
    render_section_header("Conversation", "💬")
    
    chat_container = st.container(height=320)
    with chat_container:
        if not st.session_state.gov_chat_history:
            st.markdown(
                f"""
                <div style="color: {COLORS['text_tertiary']}; text-align: center; padding: 30px 20px;">
                    <p style="font-size: 1rem; margin-bottom: 8px;">🛡️ Governance AI Copilot</p>
                    <p style="font-size: 0.85rem;">AI-powered tool selection with human approval workflow</p>
                    <p style="font-size: 0.8rem; color: #6c5ce7; margin-top: 12px;">
                        💡 Try "Hedge 85%" to trigger the approval workflow!
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            for message in st.session_state.gov_chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # 审批卡片 (如果有待审批任务)
        if st.session_state.gov_pending_approval:
            _render_approval_card(ctx, api_key)
    
    if not api_key:
        st.warning("⚠️ OpenAI API key not configured.")
        st.chat_input("Type your question...", disabled=True)
        return

    # 如果有待审批任务，禁用输入
    if st.session_state.gov_pending_approval:
        st.info("⏳ 请先处理待审批任务")
        st.chat_input("Waiting for approval...", disabled=True)
        return

    col_input, col_clear = st.columns([6, 1])
    
    with col_clear:
        if st.button("🗑️", use_container_width=True, help="Clear", key="gov_clear"):
            st.session_state.gov_chat_history = []
            st.session_state.gov_thinking_steps = []
            st.session_state.gov_pending_approval = None
            st.rerun()

    user_input = st.chat_input("Ask about risk metrics, stress tests, or hedging...", key="gov_input")

    if user_input:
        _process_user_input_with_status(user_input, ctx, api_key)


# ============================================================
# UI 组件: 审批卡片
# ============================================================

def _render_approval_card(ctx: dict, api_key: str):
    """渲染审批卡片"""
    pending = st.session_state.gov_pending_approval
    
    st.markdown(
        f"""
        <div style="
            border: 2px solid #ff6b6b;
            background: linear-gradient(135deg, #ff6b6b10, #ff6b6b05);
            border-radius: 12px;
            padding: 20px;
            margin: 16px 0;
        ">
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
                <span style="font-size: 1.5rem;">🚨</span>
                <span style="font-size: 1.1rem; font-weight: 700; color: #ff6b6b;">需要人工审批</span>
            </div>
            <div style="
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 16px;
            ">
                <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; text-align: center;">
                    <div>
                        <div style="color: {COLORS['text_tertiary']}; font-size: 0.75rem;">建议比例</div>
                        <div style="color: #ff6b6b; font-size: 1.3rem; font-weight: 700;">{pending['proposed_ratio']:.0%}</div>
                    </div>
                    <div>
                        <div style="color: {COLORS['text_tertiary']}; font-size: 0.75rem;">合规限额</div>
                        <div style="color: {COLORS['text_primary']}; font-size: 1.3rem; font-weight: 700;">{pending['max_allowed']:.0%}</div>
                    </div>
                    <div>
                        <div style="color: {COLORS['text_tertiary']}; font-size: 0.75rem;">系统建议</div>
                        <div style="color: {COLORS['positive']}; font-size: 1.3rem; font-weight: 700;">{pending['recommendation']:.0%}</div>
                    </div>
                </div>
            </div>
            <div style="color: {COLORS['text_secondary']}; font-size: 0.85rem; margin-bottom: 12px;">
                {pending.get('reason', '建议的对冲比例超出合规限额，需要人工决策。')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # 审批按钮
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        if st.button(
            f"✅ 批准调整至 {pending['recommendation']:.0%}",
            type="primary",
            use_container_width=True,
            key="gov_approve",
        ):
            _handle_approval("approved", ctx, api_key)
    
    with col2:
        if st.button(
            "❌ 驳回此操作",
            type="secondary",
            use_container_width=True,
            key="gov_reject",
        ):
            _handle_approval("rejected", ctx, api_key)
    
    with col3:
        st.markdown(
            f"<div style='text-align: center; padding-top: 8px; color: {COLORS['text_tertiary']}; font-size: 0.75rem;'>操作将记录至审计日志</div>",
            unsafe_allow_html=True,
        )


def _handle_approval(status: str, ctx: dict, api_key: str):
    """处理审批结果"""
    pending = st.session_state.gov_pending_approval
    
    # 调用处理函数
    response, steps = process_approval(
        approval_status=status,
        ctx=ctx,
        api_key=api_key,
        pending_state=pending.get("state", {}),
    )
    
    # 更新聊天历史
    st.session_state.gov_chat_history.append({
        "role": "assistant",
        "content": response,
    })
    
    # 更新思考步骤
    st.session_state.gov_thinking_steps.extend(steps)
    
    # 清除待审批状态
    st.session_state.gov_pending_approval = None
    
    st.rerun()


# ============================================================
# UI 组件: 思考面板
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
            min-height: 480px;
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
                    🧠 Governance Engine
                </span>
                <span style="
                    font-size: 0.7rem;
                    color: #6c5ce7;
                    background-color: #6c5ce715;
                    padding: 2px 8px;
                    border-radius: 4px;
                ">Tool Calling</span>
            </div>
        """,
        unsafe_allow_html=True,
    )
    
    if not st.session_state.gov_thinking_steps:
        st.markdown(
            f"""
            <div style="color: {COLORS['text_tertiary']}; font-size: 0.85rem; padding: 20px;">
                <p style="margin-bottom: 16px; text-align: center;">Waiting for query...</p>
                <div style="font-size: 0.75rem; line-height: 2;">
                    <p><strong>Workflow:</strong></p>
                    <p>🤖 <code>Tool Selection</code> → AI chooses tool</p>
                    <p>⚙️ <code>Execute</code> → Run risk engine</p>
                    <p>🛡️ <code>Audit</code> → Compliance check</p>
                    <p>✅ <code>Approval</code> → Human decision</p>
                    <p>💬 <code>Respond</code> → Final response</p>
                </div>
                <div style="margin-top: 16px; padding-top: 12px; border-top: 1px solid {COLORS['bg_border']};">
                    <p style="font-size: 0.7rem; color: #6c5ce7;">
                        High-risk ops require human approval
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for step in st.session_state.gov_thinking_steps:
            _render_thinking_step_enhanced(step)
    
    st.markdown("</div>", unsafe_allow_html=True)


def _render_thinking_step_enhanced(step: ThinkingStep):
    """渲染单个思考步骤"""
    
    status_config = {
        "running": {"icon": "⏳", "color": COLORS['warning'], "bg": f"{COLORS['warning']}10", "border": COLORS['warning']},
        "success": {"icon": "✅", "color": COLORS['positive'], "bg": f"{COLORS['positive']}10", "border": COLORS['positive']},
        "warning": {"icon": "⚠️", "color": "#ff6b6b", "bg": "#ff6b6b15", "border": "#ff6b6b"},
        "error": {"icon": "❌", "color": COLORS['negative'], "bg": f"{COLORS['negative']}10", "border": COLORS['negative']},
        "pending": {"icon": "⏸️", "color": "#6c5ce7", "bg": "#6c5ce715", "border": "#6c5ce7"},
    }
    
    config = status_config.get(step.status, status_config["running"])
    
    # 特殊处理
    if step.is_warning:
        config = {"icon": "🚨", "color": "#ff4757", "bg": "#ff475720", "border": "#ff4757"}
    if step.requires_approval:
        config = {"icon": "⏸️", "color": "#6c5ce7", "bg": "#6c5ce720", "border": "#6c5ce7"}
    
    # 工具信息
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
            <div style="color: #6c5ce7;">📦 {step.tool_call}</div>
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
# 核心处理函数
# ============================================================

def _process_user_input_with_status(user_input: str, ctx: dict, api_key: str):
    """处理用户输入 - 使用 st.status 实时追踪"""
    
    st.session_state.gov_chat_history.append({"role": "user", "content": user_input})
    st.session_state.gov_thinking_steps = []
    
    status_placeholder = st.empty()
    
    try:
        with status_placeholder.status("🛡️ Governance Engine 启动中...", expanded=True) as status:
            final_response = ""
            requires_approval = False
            approval_context = {}
            final_state = {}
            
            for node_name, state, is_final in run_agent_stream(
                user_query=user_input,
                ctx=ctx,
                api_key=api_key,
            ):
                icon, message, label = NODE_STATUS_MESSAGES.get(
                    node_name, 
                    ("🔄", "Processing...", node_name)
                )
                
                status.update(label=f"{icon} {message}")
                st.write(f"**Node:** `{node_name}` — {label}")
                
                # 检查是否选择了工具
                if node_name == "analyze" and state.get("selected_tool"):
                    tool_name = state.get("selected_tool", "")
                    tool_desc = TOOL_DESCRIPTIONS.get(tool_name, tool_name)
                    st.success(f"🤖 AI 选择工具: **{tool_desc}**")
                
                # 检查是否需要审批
                if state.get("requires_approval"):
                    requires_approval = True
                    st.warning("🚨 **触发合规拦截** — 需要人工审批")
                
                # 收集结果
                if "thinking_steps" in state:
                    st.session_state.gov_thinking_steps = state["thinking_steps"]
                
                if is_final:
                    final_response = state.get("final_response", "")
                    final_state = state
                
                time.sleep(0.1)
            
            status.update(label="✅ 执行完成", state="complete", expanded=False)
        
        # 添加响应到聊天
        st.session_state.gov_chat_history.append({
            "role": "assistant",
            "content": final_response,
        })
        
        # 如果需要审批，保存待审批状态
        if requires_approval:
            st.session_state.gov_pending_approval = {
                "proposed_ratio": final_state.get("tool_output", {}).get("proposed_ratio", 0),
                "max_allowed": final_state.get("tool_output", {}).get("max_allowed", 0),
                "recommendation": final_state.get("tool_output", {}).get("recommendation", 0),
                "reason": final_state.get("approval_reason", ""),
                "state": final_state,
            }
        
        st.rerun()

    except Exception as e:
        status_placeholder.empty()
        st.session_state.gov_thinking_steps.append(ThinkingStep(
            node="❌ Error",
            status="error",
            message=str(e),
        ))
        st.session_state.gov_chat_history.append({
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
