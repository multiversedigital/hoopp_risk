"""
agent_logic_gov.py — Governance Engine with Tool Calling & Human-in-the-loop

核心特性:
    1. Tool Calling: LLM 自主选择工具，废弃正则表达式
    2. Human-in-the-loop: 高风险操作需要人工审批
    3. 工具透明化: 完整展示 AI 的工具调用过程

架构定位:
    编排层 (Orchestration Layer) — 控制 AI 决策流程

与其他版本的区别:
    - agent_logic.py: 手动 while 循环
    - agent_logic_lg.py: LangGraph 基础版
    - agent_logic_gov.py: LangGraph + Tool Calling + Interrupt (本文件)
"""

import json
from typing import Optional, List, Tuple, TypedDict, Literal, Any
from dataclasses import dataclass
from openai import OpenAI

# LangGraph imports
from langgraph.graph import StateGraph, END

# 从 skills_v2.py 导入工具
from skills_v2 import (
    get_all_tools,
    get_tool_descriptions,
    get_risk_metrics,
    run_stress_test,
    check_hedge_compliance,
    get_limit_status,
    get_asset_allocation,
    COMPLIANCE_LIMITS,
)


# ============================================================
# 数据结构定义
# ============================================================

@dataclass
class ThinkingStep:
    """思考步骤 - 增强版"""
    node: str
    status: str  # "running", "success", "warning", "error", "pending"
    message: str
    detail: Optional[str] = None
    tool_call: Optional[str] = None
    tool_params: Optional[str] = None
    tool_result: Optional[str] = None
    is_warning: bool = False
    requires_approval: bool = False  # 新增: 是否需要审批


class AgentState(TypedDict):
    """LangGraph 状态定义"""
    user_query: str
    ctx: dict
    api_key: str
    
    # 思考过程
    thinking_steps: List[ThinkingStep]
    
    # Tool Calling 结果
    selected_tool: str
    tool_input: dict
    tool_output: dict
    
    # 审批状态
    requires_approval: bool
    approval_status: str  # "pending", "approved", "rejected", ""
    approval_reason: str
    
    # 最终输出
    final_response: str


# ============================================================
# 工具映射
# ============================================================

TOOL_MAP = {
    "get_risk_metrics": get_risk_metrics,
    "run_stress_test": run_stress_test,
    "check_hedge_compliance": check_hedge_compliance,
    "get_limit_status": get_limit_status,
    "get_asset_allocation": get_asset_allocation,
}

TOOL_DESCRIPTIONS = get_tool_descriptions()


# ============================================================
# 工具执行辅助函数 (绕过 @tool 装饰器直接执行)
# ============================================================

def _execute_get_risk_metrics(ctx: dict) -> dict:
    """执行 get_risk_metrics"""
    return {
        "funded_status": ctx['funded_status'],
        "total_assets": ctx['total_assets'],
        "total_liabilities": ctx['total_liabilities'],
        "surplus": ctx['surplus'],
        "asset_duration": ctx['asset_dur'],
        "liability_duration": ctx['liability_dur'],
        "duration_gap": ctx['asset_dur'] - ctx['liability_dur'],
        "fx_exposure": ctx['fx_pct'],
    }


def _execute_run_stress_test(
    ctx: dict,
    rate_shock_bp: int = 100,
    equity_shock_pct: float = -0.15,
    inflation_shock_pct: float = 0.0,
    scenario_name: str = "Custom",
) -> dict:
    """执行 run_stress_test"""
    base_assets = ctx['total_assets']
    base_liabilities = ctx['total_liabilities']
    base_funded = ctx['funded_status']
    asset_dur = ctx['asset_dur']
    liability_dur = ctx['liability_dur']
    
    equity_weight = 0.35
    fi_weight = 0.40
    real_asset_weight = 0.25
    
    rate_change = rate_shock_bp / 10000
    asset_rate_impact = -asset_dur * rate_change * fi_weight
    liability_rate_impact = -liability_dur * rate_change
    equity_impact = equity_shock_pct * equity_weight
    inflation_impact = inflation_shock_pct * real_asset_weight * 0.5
    
    total_asset_impact = asset_rate_impact + equity_impact + inflation_impact
    stressed_assets = base_assets * (1 + total_asset_impact)
    stressed_liabilities = base_liabilities * (1 + liability_rate_impact)
    stressed_surplus = stressed_assets - stressed_liabilities
    stressed_funded = stressed_assets / stressed_liabilities if stressed_liabilities > 0 else 0
    
    return {
        "scenario_name": scenario_name,
        "parameters": {
            "rate_shock_bp": rate_shock_bp,
            "equity_shock_pct": equity_shock_pct,
            "inflation_shock_pct": inflation_shock_pct,
        },
        "results": {
            "stressed_funded_status": stressed_funded,
            "delta_funded": stressed_funded - base_funded,
            "stressed_assets": stressed_assets,
            "stressed_liabilities": stressed_liabilities,
            "stressed_surplus": stressed_surplus,
            "delta_surplus": stressed_surplus - (base_assets - base_liabilities),
        },
    }


def _execute_check_hedge_compliance(
    ctx: dict,
    ratio: float,
    hedge_type: str = "duration",
) -> dict:
    """执行 check_hedge_compliance"""
    limit_config = COMPLIANCE_LIMITS.get(hedge_type, COMPLIANCE_LIMITS.get("duration", {}))
    max_ratio = limit_config.get("max_hedge_ratio", 0.80)
    
    is_compliant = ratio <= max_ratio
    
    if is_compliant:
        return {
            "status": "PASS",
            "proposed_ratio": ratio,
            "max_allowed": max_ratio,
            "hedge_type": hedge_type,
            "message": f"Hedge ratio {ratio:.0%} is within limit ({max_ratio:.0%})",
            "recommendation": None,
            "requires_approval": False,
        }
    else:
        compliant_ratio = max_ratio * 0.95
        return {
            "status": "FAIL",
            "proposed_ratio": ratio,
            "max_allowed": max_ratio,
            "hedge_type": hedge_type,
            "message": f"Hedge ratio {ratio:.0%} exceeds limit ({max_ratio:.0%}), approval required",
            "recommendation": compliant_ratio,
            "recommendation_message": f"Recommended adjustment: {compliant_ratio:.0%} (95% of limit)",
            "requires_approval": True,
        }


def _execute_get_limit_status(ctx: dict) -> dict:
    """执行 get_limit_status"""
    limits_df = ctx['limits_df']
    
    breaches = limits_df[limits_df['Status'].str.contains('BREACH', na=False)]
    warnings = limits_df[limits_df['Status'].str.contains('WARN', na=False)]
    
    return {
        "total_limits": len(limits_df),
        "breaches": len(breaches),
        "warnings": len(warnings),
        "ok": len(limits_df) - len(breaches) - len(warnings),
        "breach_details": breaches[['asset_class', 'current_weight', 'range_max']].to_dict('records') if len(breaches) > 0 else [],
        "warning_details": warnings[['asset_class', 'current_weight', 'range_max']].to_dict('records') if len(warnings) > 0 else [],
        "overall_status": "BREACH" if len(breaches) > 0 else ("WARNING" if len(warnings) > 0 else "OK"),
    }


def _execute_get_asset_allocation(ctx: dict) -> dict:
    """执行 get_asset_allocation"""
    comp_df = ctx['comp_df']
    
    allocation = []
    for _, row in comp_df.iterrows():
        allocation.append({
            "asset_class": row['asset_class'],
            "current_weight": row['current_weight'],
            "policy_target": row['policy_target'],
            "deviation": row['current_weight'] - row['policy_target'],
        })
    
    return {
        "allocation": allocation,
        "total_assets": ctx['total_assets'],
    }


# ============================================================
# 节点 1: 意图分析 + 工具选择 (Tool Calling)
# ============================================================

def node_analyze_with_tools(state: AgentState) -> AgentState:
    """
    使用 LLM Tool Calling 分析用户意图并选择工具
    
    这是核心升级点：废弃正则表达式，让 LLM 自主决策
    """
    steps = list(state.get("thinking_steps", []))
    
    # Build tool selection prompt
    tools_description = """
Available Tools:
1. get_risk_metrics - Get core risk metrics (funded status, surplus, duration gap)
2. run_stress_test - Run stress test (rate shock, equity shock)
3. check_hedge_compliance - Check hedge compliance (important: exceeding limit requires approval)
4. get_limit_status - Query limit status (breaches, warnings)
5. get_asset_allocation - Get asset allocation details

Rules:
- If user mentions hedge/hedging, use check_hedge_compliance
- If user mentions stress/scenario/shock/what-if, use run_stress_test
- If user mentions limit/breach/warning, use get_limit_status
- If user mentions allocation/portfolio, use get_asset_allocation
- For general risk questions, use get_risk_metrics
"""
    
    system_prompt = f"""You are a tool selector for a pension fund risk system.

{tools_description}

Analyze the user's query and respond with a JSON object:
{{
    "selected_tool": "tool_name",
    "tool_params": {{ ... }},
    "reasoning": "why this tool"
}}

For check_hedge_compliance, extract the ratio as a decimal (e.g., 85% -> 0.85).
For run_stress_test, extract rate_shock_bp and equity_shock_pct.

Respond ONLY with valid JSON, no other text."""

    try:
        client = OpenAI(api_key=state["api_key"])
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": state["user_query"]},
            ],
            max_tokens=300,
            temperature=0,
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # 清理可能的 markdown 包装
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
        result_text = result_text.strip()
        
        result = json.loads(result_text)
        
        selected_tool = result.get("selected_tool", "get_risk_metrics")
        tool_params = result.get("tool_params", {})
        reasoning = result.get("reasoning", "")
        
        steps.append(ThinkingStep(
            node="🤖 Tool Selection",
            status="success",
            message=f"AI selected tool: {selected_tool}",
            detail=reasoning,
            tool_call=f"{selected_tool}()",
            tool_params=json.dumps(tool_params, ensure_ascii=False) if tool_params else None,
        ))
        
        return {
            **state,
            "thinking_steps": steps,
            "selected_tool": selected_tool,
            "tool_input": tool_params,
        }
        
    except Exception as e:
        # Fallback: 使用简单规则
        steps.append(ThinkingStep(
            node="🤖 Tool Selection",
            status="warning",
            message=f"AI selection failed, using fallback: {str(e)}",
        ))
        
        # 简单 fallback 逻辑
        query_lower = state["user_query"].lower()
        if "hedge" in query_lower:
            selected_tool = "check_hedge_compliance"
            # 尝试提取比例
            import re
            match = re.search(r'(\d+)\s*%', query_lower)
            ratio = int(match.group(1)) / 100 if match else 0.70
            tool_params = {"ratio": ratio}
        elif "stress" in query_lower or "shock" in query_lower:
            selected_tool = "run_stress_test"
            tool_params = {"rate_shock_bp": 100, "equity_shock_pct": -0.15}
        elif "limit" in query_lower or "breach" in query_lower:
            selected_tool = "get_limit_status"
            tool_params = {}
        else:
            selected_tool = "get_risk_metrics"
            tool_params = {}
        
        return {
            **state,
            "thinking_steps": steps,
            "selected_tool": selected_tool,
            "tool_input": tool_params,
        }


# ============================================================
# 节点 2: 执行工具
# ============================================================

def node_execute_tool(state: AgentState) -> AgentState:
    """执行选中的工具"""
    steps = list(state.get("thinking_steps", []))
    
    selected_tool = state.get("selected_tool", "get_risk_metrics")
    tool_params = state.get("tool_input", {})
    ctx = state["ctx"]
    
    if selected_tool not in TOOL_MAP:
        steps.append(ThinkingStep(
            node="⚙️ Execute",
            status="error",
            message=f"Unknown tool: {selected_tool}",
        ))
        return {**state, "thinking_steps": steps, "tool_output": {}}
    
    try:
        # 直接调用底层函数（不使用 .invoke()，因为需要注入 ctx）
        if selected_tool == "check_hedge_compliance":
            # 支持两种参数名: ratio 或 hedge_ratio
            ratio = tool_params.get("ratio") or tool_params.get("hedge_ratio", 0.70)
            result = _execute_check_hedge_compliance(
                ctx=ctx,
                ratio=ratio,
                hedge_type=tool_params.get("hedge_type", "duration"),
            )
        elif selected_tool == "run_stress_test":
            result = _execute_run_stress_test(
                ctx=ctx,
                rate_shock_bp=tool_params.get("rate_shock_bp", 100),
                equity_shock_pct=tool_params.get("equity_shock_pct", -0.15),
                inflation_shock_pct=tool_params.get("inflation_shock_pct", 0.0),
                scenario_name=tool_params.get("scenario_name", "Custom"),
            )
        elif selected_tool == "get_limit_status":
            result = _execute_get_limit_status(ctx)
        elif selected_tool == "get_asset_allocation":
            result = _execute_get_asset_allocation(ctx)
        else:
            result = _execute_get_risk_metrics(ctx)
        
        # 格式化结果摘要
        result_summary = _format_tool_result(selected_tool, result)
        
        steps.append(ThinkingStep(
            node="⚙️ Execute",
            status="success",
            message=f"Tool executed: {TOOL_DESCRIPTIONS.get(selected_tool, selected_tool)}",
            tool_call=f"{selected_tool}()",
            tool_result=result_summary,
        ))
        
        return {
            **state,
            "thinking_steps": steps,
            "tool_output": result,
        }
        
    except Exception as e:
        steps.append(ThinkingStep(
            node="⚙️ Execute",
            status="error",
            message=f"Tool execution failed: {str(e)}",
        ))
        return {**state, "thinking_steps": steps, "tool_output": {}}


def _format_tool_result(tool_name: str, result: dict) -> str:
    """格式化工具结果为可读摘要"""
    if tool_name == "get_risk_metrics":
        return f"Funded: {result.get('funded_status', 0):.1%}, Surplus: ${result.get('surplus', 0)/1000:.1f}B"
    elif tool_name == "run_stress_test":
        res = result.get("results", {})
        return f"Stressed Funded: {res.get('stressed_funded_status', 0):.1%} (Δ{res.get('delta_funded', 0)*100:+.1f}%)"
    elif tool_name == "check_hedge_compliance":
        status = result.get("status", "UNKNOWN")
        ratio = result.get("proposed_ratio", 0)
        return f"{status} - Proposed ratio: {ratio:.0%}"
    elif tool_name == "get_limit_status":
        return f"Breaches: {result.get('breaches', 0)}, Warnings: {result.get('warnings', 0)}"
    elif tool_name == "get_asset_allocation":
        return f"Asset allocation retrieved"
    return str(result)[:100]


# ============================================================
# 节点 3: 合规审计 + 审批判断
# ============================================================

def node_audit(state: AgentState) -> AgentState:
    """
    审计节点 - 判断是否需要人工审批
    
    关键逻辑:
    - 如果是 check_hedge_compliance 且返回 FAIL，需要审批
    - 其他情况直接通过
    """
    steps = list(state.get("thinking_steps", []))
    
    selected_tool = state.get("selected_tool", "")
    tool_output = state.get("tool_output", {})
    
    requires_approval = False
    approval_reason = ""
    
    # 检查是否需要审批
    if selected_tool == "check_hedge_compliance":
        if tool_output.get("status") == "FAIL":
            requires_approval = True
            approval_reason = tool_output.get("message", "Exceeds compliance limit")
            
            steps.append(ThinkingStep(
                node="🛡️ Audit",
                status="warning",
                message="⚠️ Approval Required",
                detail=approval_reason,
                tool_result=f"Recommended: {tool_output.get('recommendation', 0):.0%}",
                is_warning=True,
                requires_approval=True,
            ))
        else:
            steps.append(ThinkingStep(
                node="🛡️ Audit",
                status="success",
                message="✅ Compliance Passed",
                detail=tool_output.get("message", ""),
            ))
    else:
        # Non-hedge operations pass directly
        steps.append(ThinkingStep(
            node="🛡️ Audit",
            status="success",
            message="✅ No Approval Required",
            detail="Low-risk operation",
        ))
    
    return {
        **state,
        "thinking_steps": steps,
        "requires_approval": requires_approval,
        "approval_reason": approval_reason,
        "approval_status": "pending" if requires_approval else "",
    }


# ============================================================
# 节点 4: 生成响应
# ============================================================

def node_respond(state: AgentState) -> AgentState:
    """生成最终响应"""
    steps = list(state.get("thinking_steps", []))
    
    # 如果需要审批，生成审批相关响应
    if state.get("requires_approval") and state.get("approval_status") == "pending":
        tool_output = state.get("tool_output", {})
        response = f"""⚠️ **Approval Required**

Your proposed hedge ratio **{tool_output.get('proposed_ratio', 0):.0%}** exceeds the compliance limit **{tool_output.get('max_allowed', 0):.0%}**.

**System Recommendation:** Adjust to **{tool_output.get('recommendation', 0):.0%}** (95% of limit)

Please select:
- ✅ **Approve** the recommended adjustment
- ❌ **Reject** this operation"""
        
        steps.append(ThinkingStep(
            node="💬 Respond",
            status="pending",
            message="Waiting for approval",
            requires_approval=True,
        ))
        
        return {
            **state,
            "thinking_steps": steps,
            "final_response": response,
        }
    
    # 正常响应生成
    tool_output = state.get("tool_output", {})
    selected_tool = state.get("selected_tool", "")
    
    # 构建 context for LLM
    context = f"""
Tool Used: {selected_tool}
Tool Output: {json.dumps(tool_output, ensure_ascii=False, indent=2)}
"""
    
    system_prompt = f"""You are a risk advisor for a large pension fund.

Based on the tool output below, provide a clear, professional response.

{context}

Guidelines:
- Be concise (under 150 words)
- Highlight key metrics
- If compliance passed, mention it
- Use professional terminology
- Respond in the same language as the user's query
"""
    
    try:
        client = OpenAI(api_key=state["api_key"])
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": state["user_query"]},
            ],
            max_tokens=400,
            temperature=0.3,
        )
        
        final_response = response.choices[0].message.content
        
        steps.append(ThinkingStep(
            node="💬 Respond",
            status="success",
            message="Response generated",
        ))
        
    except Exception as e:
        final_response = f"Error generating response: {str(e)}"
        steps.append(ThinkingStep(
            node="💬 Respond",
            status="error",
            message=str(e),
        ))
    
    return {
        **state,
        "thinking_steps": steps,
        "final_response": final_response,
    }


# ============================================================
# 节点 5: 处理审批结果 (简化版 - 由 UI 触发)
# ============================================================

def node_handle_approval(state: AgentState) -> AgentState:
    """
    处理审批结果
    
    这个节点由 UI 触发，用于处理用户的批准/驳回操作
    """
    steps = list(state.get("thinking_steps", []))
    approval_status = state.get("approval_status", "")
    tool_output = state.get("tool_output", {})
    
    if approval_status == "approved":
        # 用户批准了调整
        new_ratio = tool_output.get("recommendation", 0)
        
        steps.append(ThinkingStep(
            node="✅ Approved",
            status="success",
            message=f"Approved: adjusted to {new_ratio:.0%}",
            detail="Action logged to audit trail",
        ))
        
        response = f"""✅ **Operation Approved**

Hedge ratio adjusted to **{new_ratio:.0%}** (within {tool_output.get('max_allowed', 0):.0%} limit)

This action has been logged to the audit trail."""
        
    elif approval_status == "rejected":
        steps.append(ThinkingStep(
            node="❌ Rejected",
            status="error",
            message="Rejected: operation cancelled",
        ))
        
        response = """❌ **Operation Rejected**

The hedge adjustment request has been cancelled. Current configuration remains unchanged."""
        
    else:
        response = state.get("final_response", "")
    
    return {
        **state,
        "thinking_steps": steps,
        "final_response": response,
    }


# ============================================================
# 路由函数
# ============================================================

def route_after_audit(state: AgentState) -> Literal["respond", "wait_approval"]:
    """审计后路由：是否需要等待审批"""
    if state.get("requires_approval"):
        return "wait_approval"
    return "respond"


# ============================================================
# 构建 StateGraph
# ============================================================

def build_graph() -> StateGraph:
    """
    构建治理版 StateGraph
    
    流程:
        analyze → execute → audit → respond
                              ↓
                        wait_approval (如需审批)
    """
    graph = StateGraph(AgentState)
    
    # 添加节点
    graph.add_node("analyze", node_analyze_with_tools)
    graph.add_node("execute", node_execute_tool)
    graph.add_node("audit", node_audit)
    graph.add_node("respond", node_respond)
    graph.add_node("handle_approval", node_handle_approval)
    
    # 入口点
    graph.set_entry_point("analyze")
    
    # 边
    graph.add_edge("analyze", "execute")
    graph.add_edge("execute", "audit")
    
    # 审计后的条件路由
    graph.add_conditional_edges(
        "audit",
        route_after_audit,
        {
            "respond": "respond",
            "wait_approval": "respond",  # 简化版：仍然生成响应，但标记需要审批
        }
    )
    
    graph.add_edge("respond", END)
    graph.add_edge("handle_approval", END)
    
    return graph


# 编译图
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
    api_key: str,
) -> Tuple[str, List[ThinkingStep], bool, dict]:
    """
    运行治理版 Agent
    
    Returns:
        (final_response, thinking_steps, requires_approval, approval_context)
    """
    graph = get_compiled_graph()
    
    initial_state: AgentState = {
        "user_query": user_query,
        "ctx": ctx,
        "api_key": api_key,
        "thinking_steps": [],
        "selected_tool": "",
        "tool_input": {},
        "tool_output": {},
        "requires_approval": False,
        "approval_status": "",
        "approval_reason": "",
        "final_response": "",
    }
    
    final_state = graph.invoke(initial_state)
    
    # 提取审批上下文
    approval_context = {}
    if final_state.get("requires_approval"):
        approval_context = {
            "proposed_ratio": final_state["tool_output"].get("proposed_ratio", 0),
            "max_allowed": final_state["tool_output"].get("max_allowed", 0),
            "recommendation": final_state["tool_output"].get("recommendation", 0),
            "reason": final_state.get("approval_reason", ""),
        }
    
    return (
        final_state["final_response"],
        final_state["thinking_steps"],
        final_state.get("requires_approval", False),
        approval_context,
    )


def run_agent_stream(
    user_query: str,
    ctx: dict,
    api_key: str,
):
    """
    流式运行 Agent
    
    Yields: (node_name, state, is_final)
    """
    graph = get_compiled_graph()
    
    initial_state: AgentState = {
        "user_query": user_query,
        "ctx": ctx,
        "api_key": api_key,
        "thinking_steps": [],
        "selected_tool": "",
        "tool_input": {},
        "tool_output": {},
        "requires_approval": False,
        "approval_status": "",
        "approval_reason": "",
        "final_response": "",
    }
    
    for event in graph.stream(initial_state):
        for node_name, state in event.items():
            is_final = (node_name == "respond" and state.get("final_response"))
            yield node_name, state, is_final


def process_approval(
    approval_status: str,  # "approved" or "rejected"
    ctx: dict,
    api_key: str,
    pending_state: dict,
) -> Tuple[str, List[ThinkingStep]]:
    """
    处理审批结果 (由 UI 调用)
    
    Args:
        approval_status: "approved" 或 "rejected"
        ctx: 风险上下文
        api_key: API key
        pending_state: 之前保存的待审批状态
    
    Returns:
        (final_response, thinking_steps)
    """
    # 重建状态
    state = {
        **pending_state,
        "approval_status": approval_status,
    }
    
    # 执行审批处理
    result_state = node_handle_approval(state)
    
    return result_state["final_response"], result_state["thinking_steps"]