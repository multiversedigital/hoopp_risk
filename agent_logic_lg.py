"""
agent_logic_lg.py — Agentic Audit Loop (LangGraph Version)

增强特性:
    - 工具调用透明化: 显示函数名、参数、返回值
    - 审计状态详细化: PASS/FAIL 明确标识
    - 支持流式执行: run_agent_stream()

架构:
    agent_logic_lg.py (Orchestrator) → skills.py (Calculator)
"""

import re
from typing import Optional, List, Tuple, TypedDict, Literal
from dataclasses import dataclass
from openai import OpenAI

# LangGraph imports
from langgraph.graph import StateGraph, END

# 从 skills.py 导入业务计算函数
from skills import (
    get_current_risk_metrics,
    calculate_stress_scenario,
    check_hedge_compliance,
    get_limit_status,
    RiskMetrics,
    StressResult,
)


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class ThinkingStep:
    """
    思考步骤 - 增强版
    
    新增字段:
        tool_call: 调用的工具函数名
        tool_params: 传入的参数
        tool_result: 返回的核心数据
        is_warning: 是否为警告状态 (用于审计失败高亮)
    """
    node: str
    status: str  # "running", "success", "warning", "error"
    message: str
    detail: Optional[str] = None
    tool_call: Optional[str] = None      # 新增: 工具函数名
    tool_params: Optional[str] = None    # 新增: 参数
    tool_result: Optional[str] = None    # 新增: 返回值
    is_warning: bool = False             # 新增: 警告标识


class AgentState(TypedDict):
    """LangGraph 状态定义"""
    user_query: str
    ctx: dict
    system_prompt: str
    api_key: str
    thinking_steps: List[ThinkingStep]
    intent: str
    params: dict
    calculation_result: dict
    audit_result: dict
    final_response: str
    iteration: int


# ============================================================
# 合规限额
# ============================================================

COMPLIANCE_LIMITS = {
    "max_hedge_ratio": 0.80,
    "max_fx_exposure": 0.15,
    "min_equity_exposure": 0.20,
    "max_single_issuer": 0.05,
}


# ============================================================
# 节点函数 (Nodes) - 增强版
# ============================================================

def node_analyze(state: AgentState) -> AgentState:
    """节点 1: 分析用户意图"""
    steps = list(state.get("thinking_steps", []))
    
    query_lower = state["user_query"].lower()
    
    # 意图识别
    if any(kw in query_lower for kw in ["hedge", "hedging", "adjust hedge", "hedge ratio"]):
        intent = "hedge"
        ratio = _extract_percentage(query_lower)
        params = {"hedge_ratio": ratio if ratio else 0.70}
        detail = f"检测到对冲请求 → 目标比例: {params['hedge_ratio']:.0%}"
    elif any(kw in query_lower for kw in ["stress", "scenario", "shock", "crisis", "what if"]):
        intent = "stress"
        rate_bp = _extract_bp(query_lower) or 100
        equity_pct = _extract_equity_shock(query_lower) or -0.15
        params = {"rate_bp": rate_bp, "equity_pct": equity_pct}
        detail = f"检测到压力测试 → 利率: {rate_bp}bp, 权益: {equity_pct:.0%}"
    elif any(kw in query_lower for kw in ["limit", "breach", "warning", "compliance"]):
        intent = "limits"
        params = {}
        detail = "检测到限额查询请求"
    else:
        intent = "query"
        params = {}
        detail = "通用信息查询"
    
    steps.append(ThinkingStep(
        node="🔍 Analyze",
        status="success",
        message=f"意图识别: {intent.upper()}",
        detail=detail,
    ))
    
    return {
        **state,
        "thinking_steps": steps,
        "intent": intent,
        "params": params,
    }


def node_calculate(state: AgentState) -> AgentState:
    """节点 2: 执行计算 - 显示工具调用"""
    steps = list(state.get("thinking_steps", []))
    
    intent = state.get("intent", "query")
    params = state.get("params", {})
    ctx = state["ctx"]
    
    try:
        if intent == "stress":
            # 工具调用: calculate_stress_scenario
            rate_bp = params.get("rate_bp", 100)
            equity_pct = params.get("equity_pct", -0.15)
            
            result: StressResult = calculate_stress_scenario(
                ctx=ctx,
                rate_shock_bp=rate_bp,
                equity_shock_pct=equity_pct,
                scenario_name="AI Requested",
            )
            
            calculation_result = {
                "type": "stress",
                "stressed_funded": result.stressed_funded,
                "delta_funded": result.delta_funded,
                "stressed_assets": result.stressed_assets,
                "stressed_liabilities": result.stressed_liabilities,
                "stressed_surplus": result.stressed_surplus,
            }
            
            steps.append(ThinkingStep(
                node="⚙️ Calculate",
                status="success",
                message="压力测试计算完成",
                tool_call="calculate_stress_scenario()",
                tool_params=f"rate_shock_bp={rate_bp}, equity_shock_pct={equity_pct:.0%}",
                tool_result=f"Stressed Funded: {result.stressed_funded:.1%} (Δ{result.delta_funded*100:+.1f}%)",
            ))
            
        elif intent == "hedge":
            # 记录参数，稍后审计
            calculation_result = {
                "type": "hedge",
                "proposed_ratio": params.get("hedge_ratio", 0.70),
            }
            
            steps.append(ThinkingStep(
                node="⚙️ Calculate",
                status="success",
                message="对冲方案准备完成",
                detail=f"建议对冲比例: {params.get('hedge_ratio', 0.70):.0%}",
                tool_call="准备调用 check_hedge_compliance()",
            ))
            
        elif intent == "limits":
            # 工具调用: get_limit_status
            limit_status = get_limit_status(ctx)
            calculation_result = {"type": "limits", **limit_status}
            
            steps.append(ThinkingStep(
                node="⚙️ Calculate",
                status="success",
                message="限额状态查询完成",
                tool_call="get_limit_status()",
                tool_result=f"Breaches: {limit_status['breaches']}, Warnings: {limit_status['warnings']}",
            ))
            
        else:
            # 工具调用: get_current_risk_metrics
            metrics: RiskMetrics = get_current_risk_metrics(ctx)
            calculation_result = {
                "type": "query",
                "funded_status": metrics.funded_status,
                "surplus": metrics.surplus,
                "duration_gap": metrics.duration_gap,
            }
            
            steps.append(ThinkingStep(
                node="⚙️ Calculate",
                status="success",
                message="风险指标获取完成",
                tool_call="get_current_risk_metrics()",
                tool_result=f"Funded: {metrics.funded_status:.1%}, Surplus: ${metrics.surplus/1000:.1f}B",
            ))
        
    except Exception as e:
        calculation_result = {"type": "error", "error": str(e)}
        steps.append(ThinkingStep(
            node="⚙️ Calculate",
            status="error",
            message=f"计算失败: {str(e)}",
        ))
    
    return {
        **state,
        "thinking_steps": steps,
        "calculation_result": calculation_result,
    }


def node_audit(state: AgentState) -> AgentState:
    """节点 3: 合规审计 - 高亮显示 PASS/FAIL"""
    steps = list(state.get("thinking_steps", []))
    
    params = state.get("params", {})
    proposed_ratio = params.get("hedge_ratio", 0)
    is_refined = params.get("refined", False)
    
    # 工具调用: check_hedge_compliance
    audit_result = check_hedge_compliance(
        ctx=state["ctx"],
        proposed_hedge_ratio=proposed_ratio,
        hedge_type="duration",
    )
    
    if audit_result["status"] == "PASS":
        steps.append(ThinkingStep(
            node="🛡️ Audit",
            status="success",
            message="✅ 合规检查通过",
            tool_call="check_hedge_compliance()",
            tool_params=f"proposed_ratio={proposed_ratio:.0%}, hedge_type='duration'",
            tool_result=f"PASS - 在限额 {audit_result['max_allowed']:.0%} 内",
            is_warning=False,
        ))
    else:
        # 审计失败 - 高亮警告
        steps.append(ThinkingStep(
            node="🛡️ Audit",
            status="warning",
            message="⚠️ 合规检查失败 - 需要强制修正",
            detail=f"建议比例 {proposed_ratio:.0%} 超出限额 {audit_result['max_allowed']:.0%}",
            tool_call="check_hedge_compliance()",
            tool_params=f"proposed_ratio={proposed_ratio:.0%}",
            tool_result=f"FAIL - 超出限额! 推荐: {audit_result.get('recommendation', 0):.0%}",
            is_warning=True,
        ))
    
    return {
        **state,
        "thinking_steps": steps,
        "audit_result": audit_result,
    }


def node_refine(state: AgentState) -> AgentState:
    """节点 4: 优化方案 - 自动修正"""
    steps = list(state.get("thinking_steps", []))
    
    audit_result = state.get("audit_result", {})
    params = dict(state.get("params", {}))
    iteration = state.get("iteration", 0) + 1
    
    if audit_result.get("recommendation"):
        new_ratio = audit_result["recommendation"]
        old_ratio = params.get("hedge_ratio", 0)
        params["hedge_ratio"] = new_ratio
        params["refined"] = True
        
        steps.append(ThinkingStep(
            node="🔄 Refine",
            status="success",
            message="系统自动修正完成",
            detail=f"对冲比例: {old_ratio:.0%} → {new_ratio:.0%}",
            tool_result=f"已调整至合规范围内 (限额 {audit_result['max_allowed']:.0%} 的 95%)",
        ))
    else:
        steps.append(ThinkingStep(
            node="🔄 Refine",
            status="error",
            message="无法找到合规替代方案",
        ))
    
    return {
        **state,
        "thinking_steps": steps,
        "params": params,
        "iteration": iteration,
    }


def node_respond(state: AgentState) -> AgentState:
    """节点 5: 生成最终回复"""
    steps = list(state.get("thinking_steps", []))
    
    # 构建增强上下文
    context_parts = [f"User Intent: {state.get('intent', 'unknown')}"]
    
    calc_result = state.get("calculation_result", {})
    if calc_result:
        context_parts.append(f"Calculation Result: {calc_result}")
    
    audit_result = state.get("audit_result", {})
    if audit_result:
        context_parts.append(f"Audit Result: {audit_result.get('status', 'N/A')} - {audit_result.get('message', '')}")
        params = state.get("params", {})
        if audit_result.get("status") == "FAIL" and params.get("refined"):
            context_parts.append(f"Auto-Refined to: {params.get('hedge_ratio', 0):.0%}")
    
    enhanced_context = "\n".join(context_parts)
    
    full_prompt = f"""{state['system_prompt']}

=== AGENT EXECUTION CONTEXT ===
{enhanced_context}

=== RESPONSE GUIDELINES ===
1. If audit failed and was refined, explain what happened clearly
2. Always mention compliance status when discussing hedging
3. Be concise (< 150 words) unless more detail requested
4. Use professional risk management terminology
"""
    
    try:
        response = _call_llm(state["api_key"], full_prompt, state["user_query"])
        steps.append(ThinkingStep(
            node="💬 Respond",
            status="success",
            message="响应生成完成",
            tool_call="_call_llm()",
            tool_result="GPT-4o-mini 响应就绪",
        ))
    except Exception as e:
        response = f"I apologize, but I encountered an error: {str(e)}"
        steps.append(ThinkingStep(
            node="💬 Respond",
            status="error",
            message=f"生成失败: {str(e)}",
        ))
    
    return {
        **state,
        "thinking_steps": steps,
        "final_response": response,
    }


# ============================================================
# 路由函数 (Conditional Edges)
# ============================================================

def route_after_analyze(state: AgentState) -> Literal["calculate", "respond"]:
    intent = state.get("intent", "query")
    if intent in ["hedge", "stress", "limits"]:
        return "calculate"
    return "respond"


def route_after_calculate(state: AgentState) -> Literal["audit", "respond"]:
    intent = state.get("intent", "query")
    if intent == "hedge":
        return "audit"
    return "respond"


def route_after_audit(state: AgentState) -> Literal["refine", "respond"]:
    audit_result = state.get("audit_result", {})
    iteration = state.get("iteration", 0)
    
    if audit_result.get("status") == "FAIL" and iteration < 3:
        return "refine"
    return "respond"


# ============================================================
# 构建 StateGraph
# ============================================================

def build_graph() -> StateGraph:
    """
    构建 LangGraph StateGraph
    
    图结构:
        analyze → calculate → audit ←→ refine
                     ↓          ↓
                  respond ← ─ ─ ┘
    """
    graph = StateGraph(AgentState)
    
    # 添加节点
    graph.add_node("analyze", node_analyze)
    graph.add_node("calculate", node_calculate)
    graph.add_node("audit", node_audit)
    graph.add_node("refine", node_refine)
    graph.add_node("respond", node_respond)
    
    # 入口点
    graph.set_entry_point("analyze")
    
    # 条件边
    graph.add_conditional_edges("analyze", route_after_analyze, {"calculate": "calculate", "respond": "respond"})
    graph.add_conditional_edges("calculate", route_after_calculate, {"audit": "audit", "respond": "respond"})
    graph.add_conditional_edges("audit", route_after_audit, {"refine": "refine", "respond": "respond"})
    
    # Refine 后重新 Audit
    graph.add_edge("refine", "audit")
    
    # Respond 是终点
    graph.add_edge("respond", END)
    
    return graph


# 编译图 (全局单例)
_compiled_graph = None

def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph().compile()
    return _compiled_graph


# ============================================================
# 主运行函数
# ============================================================

def run_agent(
    user_query: str,
    ctx: dict,
    system_prompt: str,
    api_key: str,
) -> Tuple[str, List[ThinkingStep]]:
    """运行 Agent (非流式版本)"""
    graph = get_compiled_graph()
    
    initial_state: AgentState = {
        "user_query": user_query,
        "ctx": ctx,
        "system_prompt": system_prompt,
        "api_key": api_key,
        "thinking_steps": [],
        "intent": "",
        "params": {},
        "calculation_result": {},
        "audit_result": {},
        "final_response": "",
        "iteration": 0,
    }
    
    final_state = graph.invoke(initial_state)
    return final_state["final_response"], final_state["thinking_steps"]


def run_agent_stream(
    user_query: str,
    ctx: dict,
    system_prompt: str,
    api_key: str,
):
    """
    运行 Agent (流式版本)
    
    Yields: (node_name, state, is_final)
    """
    graph = get_compiled_graph()
    
    initial_state: AgentState = {
        "user_query": user_query,
        "ctx": ctx,
        "system_prompt": system_prompt,
        "api_key": api_key,
        "thinking_steps": [],
        "intent": "",
        "params": {},
        "calculation_result": {},
        "audit_result": {},
        "final_response": "",
        "iteration": 0,
    }
    
    for event in graph.stream(initial_state):
        for node_name, state in event.items():
            is_final = (node_name == "respond" and state.get("final_response"))
            yield node_name, state, is_final


# ============================================================
# 辅助函数
# ============================================================

def _extract_percentage(text: str) -> Optional[float]:
    match = re.search(r'(\d+)\s*%', text)
    if match:
        return int(match.group(1)) / 100
    return None


def _extract_bp(text: str) -> Optional[int]:
    match = re.search(r'(\d+)\s*bp', text.lower())
    if match:
        return int(match.group(1))
    return None


def _extract_equity_shock(text: str) -> Optional[float]:
    match = re.search(r'equity.*?(\-?\d+)\s*%', text.lower())
    if match:
        val = int(match.group(1))
        return val / 100 if val < 0 else -val / 100
    return None


def _call_llm(api_key: str, system_prompt: str, user_query: str) -> str:
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ],
        max_tokens=400,
        temperature=0.3,
    )
    return response.choices[0].message.content


# ============================================================
# 便捷函数
# ============================================================

def build_system_prompt(ctx: dict) -> str:
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

    return f"""You are a Risk Advisor for HOOPP (Healthcare of Ontario Pension Plan), a $125B Canadian defined benefit pension fund.

IMPORTANT: You are part of an Agentic System powered by LangGraph with AUDIT capabilities. 
- Any hedging/rebalancing suggestions are automatically checked against compliance limits
- If a suggestion exceeds limits, the system auto-adjusts to a compliant alternative

=== PORTFOLIO SNAPSHOT ===

Key Metrics:
- Funded Status: {funded_status:.1%} (Target: 111%)
- Total Assets: ${total_assets/1000:.1f}B | Liabilities: ${total_liabilities/1000:.1f}B
- Surplus: ${surplus/1000:.1f}B
- Duration Gap: {duration_gap:.1f} years
- FX Exposure: {fx_pct:.1%} (Limit: 15%)

=== COMPLIANCE LIMITS ===
- Max Hedge Ratio: {COMPLIANCE_LIMITS['max_hedge_ratio']:.0%}
- Max FX Exposure: {COMPLIANCE_LIMITS['max_fx_exposure']:.0%}

Asset Allocation:
{allocation_str}

Limit Status:
{limits_str}
"""