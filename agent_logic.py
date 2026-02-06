"""
agent_logic.py — Agentic Audit Loop for Risk Copilot (Headless)

职责:
    实现 AI Copilot 的"审计闭环"逻辑：
    1. Analyze: 分析用户意图
    2. Calculate: 调用风险引擎计算
    3. Audit: 检查是否符合限额和合规要求
    4. Refine: 如果不合规，自动调整方案
    5. Respond: 生成最终回复
    
核心理念:
    "AI 可以犯错，但系统不能让错误的建议通过"

设计特点:
    - 完全无头化 (Headless)：不依赖 Streamlit，可独立测试
    - API Key 通过参数传入
    - 可被 UI 层、API 层、测试脚本复用
"""

import re
from typing import Optional, Callable, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from openai import OpenAI


# ============================================================
# 数据结构定义 (导出供 UI 层使用)
# ============================================================

@dataclass
class ThinkingStep:
    """思考步骤 - 用于展示 Agent 的推理过程"""
    node: str           # 节点名称，如 "🔍 Analyze"
    status: str         # "running", "success", "warning", "error"
    message: str        # 主要信息
    detail: Optional[str] = None  # 补充细节


class NodeType(Enum):
    """节点类型"""
    ANALYZE = "analyze"
    CALCULATE = "calculate"
    AUDIT = "audit"
    REFINE = "refine"
    RESPOND = "respond"


@dataclass
class AgentState:
    """Agent 运行状态"""
    user_query: str
    ctx: dict
    system_prompt: str
    api_key: str
    
    # 思考过程
    thinking_steps: List[ThinkingStep] = field(default_factory=list)
    
    # 中间结果
    intent: Optional[str] = None
    params: dict = field(default_factory=dict)
    calculation_result: Optional[dict] = None
    audit_result: Optional[dict] = None
    
    # 最终输出
    final_response: Optional[str] = None
    
    # 循环控制
    current_node: NodeType = NodeType.ANALYZE
    iteration: int = 0
    max_iterations: int = 3


# ============================================================
# 合规限额定义
# ============================================================

COMPLIANCE_LIMITS = {
    "max_hedge_ratio": 0.80,      # 最大对冲比例 80%
    "max_fx_exposure": 0.15,      # 最大 FX 敞口 15%
    "min_equity_exposure": 0.20,  # 最小权益敞口 20%
    "max_single_issuer": 0.05,    # 单一发行人限额 5%
}


# ============================================================
# 节点实现
# ============================================================

def _node_analyze(state: AgentState) -> AgentState:
    """节点 1: 分析用户意图"""
    state.thinking_steps.append(ThinkingStep(
        node="🔍 Analyze",
        status="running",
        message="Understanding user intent...",
    ))
    
    query_lower = state.user_query.lower()
    
    # 意图识别
    if any(kw in query_lower for kw in ["hedge", "hedging", "adjust hedge", "hedge ratio"]):
        state.intent = "hedge"
        ratio = _extract_percentage(query_lower)
        state.params = {"hedge_ratio": ratio if ratio else 0.70}
        detail = f"Hedge request detected: {state.params['hedge_ratio']:.0%}"
    elif any(kw in query_lower for kw in ["stress", "scenario", "shock", "crisis", "what if"]):
        state.intent = "stress"
        rate_bp = _extract_bp(query_lower) or 100
        equity_pct = _extract_equity_shock(query_lower) or -0.15
        state.params = {"rate_bp": rate_bp, "equity_pct": equity_pct}
        detail = f"Stress test: {rate_bp}bp rate, {equity_pct:.0%} equity"
    elif any(kw in query_lower for kw in ["limit", "breach", "warning", "compliance"]):
        state.intent = "limits"
        state.params = {}
        detail = "Limit status check"
    else:
        state.intent = "query"
        state.params = {}
        detail = "General information query"
    
    state.thinking_steps[-1].status = "success"
    state.thinking_steps[-1].message = f"Intent: {state.intent.upper()}"
    state.thinking_steps[-1].detail = detail
    
    # 决定下一步
    if state.intent in ["hedge", "stress"]:
        state.current_node = NodeType.CALCULATE
    else:
        state.current_node = NodeType.RESPOND
    
    return state


def _node_calculate(state: AgentState) -> AgentState:
    """节点 2: 执行计算"""
    state.thinking_steps.append(ThinkingStep(
        node="⚙️ Calculate",
        status="running",
        message="Running risk calculations...",
    ))
    
    try:
        if state.intent == "stress":
            result = _calculate_stress(state.ctx, state.params)
            state.calculation_result = result
            summary = f"Stressed Funded: {result['stressed_funded']:.1%} (Δ{result['delta_funded']*100:+.1f}%)"
        elif state.intent == "hedge":
            result = {
                "type": "hedge",
                "proposed_ratio": state.params.get("hedge_ratio", 0.70),
            }
            state.calculation_result = result
            summary = f"Proposed hedge ratio: {result['proposed_ratio']:.0%}"
        else:
            result = {"type": "query"}
            state.calculation_result = result
            summary = "No calculation needed"
        
        state.thinking_steps[-1].status = "success"
        state.thinking_steps[-1].message = "Calculation complete"
        state.thinking_steps[-1].detail = summary
        
        # 决定下一步
        if state.intent == "hedge":
            state.current_node = NodeType.AUDIT
        else:
            state.current_node = NodeType.RESPOND
            
    except Exception as e:
        state.thinking_steps[-1].status = "error"
        state.thinking_steps[-1].message = f"Calculation failed: {str(e)}"
        state.current_node = NodeType.RESPOND
    
    return state


def _node_audit(state: AgentState) -> AgentState:
    """节点 3: 合规审计"""
    state.thinking_steps.append(ThinkingStep(
        node="🛡️ Audit",
        status="running",
        message="Checking compliance limits...",
    ))
    
    proposed_ratio = state.params.get("hedge_ratio", 0)
    max_ratio = COMPLIANCE_LIMITS["max_hedge_ratio"]
    
    if proposed_ratio <= max_ratio:
        state.audit_result = {
            "status": "PASS",
            "message": f"Hedge ratio {proposed_ratio:.0%} is within limit ({max_ratio:.0%})",
            "proposed": proposed_ratio,
            "max_allowed": max_ratio,
        }
        state.thinking_steps[-1].status = "success"
        state.thinking_steps[-1].message = "✅ Compliance check passed"
        state.thinking_steps[-1].detail = state.audit_result["message"]
        state.current_node = NodeType.RESPOND
    else:
        state.audit_result = {
            "status": "FAIL",
            "message": f"Hedge ratio {proposed_ratio:.0%} exceeds limit ({max_ratio:.0%})",
            "proposed": proposed_ratio,
            "max_allowed": max_ratio,
            "recommendation": max_ratio * 0.95,  # 95% of limit
        }
        state.thinking_steps[-1].status = "warning"
        state.thinking_steps[-1].message = "⚠️ Compliance check failed"
        state.thinking_steps[-1].detail = state.audit_result["message"]
        
        # 需要优化
        if state.iteration < state.max_iterations:
            state.current_node = NodeType.REFINE
        else:
            state.current_node = NodeType.RESPOND
    
    return state


def _node_refine(state: AgentState) -> AgentState:
    """节点 4: 优化方案"""
    state.thinking_steps.append(ThinkingStep(
        node="🔄 Refine",
        status="running",
        message="Auto-adjusting to compliant parameters...",
    ))
    
    state.iteration += 1
    
    if state.audit_result and state.audit_result.get("recommendation"):
        new_ratio = state.audit_result["recommendation"]
        state.params["hedge_ratio"] = new_ratio
        state.params["refined"] = True
        
        state.thinking_steps[-1].status = "success"
        state.thinking_steps[-1].message = f"Adjusted to {new_ratio:.0%}"
        state.thinking_steps[-1].detail = "Re-running audit with compliant parameters"
        
        # 重新审计
        state.current_node = NodeType.AUDIT
    else:
        state.thinking_steps[-1].status = "error"
        state.thinking_steps[-1].message = "Unable to find compliant alternative"
        state.current_node = NodeType.RESPOND
    
    return state


def _node_respond(state: AgentState) -> AgentState:
    """节点 5: 生成最终回复"""
    state.thinking_steps.append(ThinkingStep(
        node="💬 Respond",
        status="running",
        message="Generating response...",
    ))
    
    # 构建增强上下文
    context_parts = [f"User Intent: {state.intent}"]
    
    if state.calculation_result:
        context_parts.append(f"Calculation: {state.calculation_result}")
    
    if state.audit_result:
        context_parts.append(f"Audit: {state.audit_result['status']} - {state.audit_result['message']}")
        if state.audit_result.get("status") == "FAIL" and state.params.get("refined"):
            context_parts.append(f"Refined to: {state.params.get('hedge_ratio', 0):.0%}")
    
    enhanced_context = "\n".join(context_parts)
    
    # 构建最终 prompt
    full_prompt = f"""{state.system_prompt}

=== AGENT EXECUTION CONTEXT ===
{enhanced_context}

=== RESPONSE GUIDELINES ===
1. If audit failed and was refined, explain what happened
2. Always mention compliance status when discussing hedging
3. Be concise (< 150 words) unless more detail requested
"""
    
    try:
        response = _call_llm(state.api_key, full_prompt, state.user_query)
        state.final_response = response
        state.thinking_steps[-1].status = "success"
        state.thinking_steps[-1].message = "Response ready"
    except Exception as e:
        state.final_response = f"I apologize, but I encountered an error: {str(e)}"
        state.thinking_steps[-1].status = "error"
        state.thinking_steps[-1].message = f"Error: {str(e)}"
    
    return state


# ============================================================
# 主运行函数 (公开接口)
# ============================================================

def run_agent(
    user_query: str,
    ctx: dict,
    system_prompt: str,
    api_key: str,
    on_step: Optional[Callable[[ThinkingStep], None]] = None
) -> Tuple[str, List[ThinkingStep]]:
    """
    运行 Agent 闭环
    
    Args:
        user_query: 用户问题
        ctx: 风险上下文 (来自 engine.build_context)
        system_prompt: 系统提示词
        api_key: OpenAI API Key
        on_step: 每步回调函数 (用于实时更新 UI)
        
    Returns:
        (final_response, thinking_steps)
    """
    state = AgentState(
        user_query=user_query,
        ctx=ctx,
        system_prompt=system_prompt,
        api_key=api_key,
    )
    
    # 节点映射
    node_handlers = {
        NodeType.ANALYZE: _node_analyze,
        NodeType.CALCULATE: _node_calculate,
        NodeType.AUDIT: _node_audit,
        NodeType.REFINE: _node_refine,
        NodeType.RESPOND: _node_respond,
    }
    
    # 执行循环
    max_steps = 10  # 防止无限循环
    step_count = 0
    
    while step_count < max_steps:
        handler = node_handlers.get(state.current_node)
        if handler:
            state = handler(state)
            
            # 回调通知 UI
            if on_step and state.thinking_steps:
                on_step(state.thinking_steps[-1])
        
        step_count += 1
        
        # 检查是否完成
        if state.current_node == NodeType.RESPOND and state.final_response:
            break
    
    return state.final_response or "Unable to generate response", state.thinking_steps


# ============================================================
# 辅助函数 (私有)
# ============================================================

def _extract_percentage(text: str) -> Optional[float]:
    """从文本中提取百分比"""
    match = re.search(r'(\d+)\s*%', text)
    if match:
        return int(match.group(1)) / 100
    return None


def _extract_bp(text: str) -> Optional[int]:
    """从文本中提取基点"""
    match = re.search(r'(\d+)\s*bp', text.lower())
    if match:
        return int(match.group(1))
    return None


def _extract_equity_shock(text: str) -> Optional[float]:
    """从文本中提取股票冲击"""
    # 匹配 "equity down 15%" 或 "equity -15%"
    match = re.search(r'equity.*?(\-?\d+)\s*%', text.lower())
    if match:
        val = int(match.group(1))
        return val / 100 if val < 0 else -val / 100
    return None


def _calculate_stress(ctx: dict, params: dict) -> dict:
    """执行压力测试计算"""
    rate_bp = params.get("rate_bp", 100)
    equity_pct = params.get("equity_pct", -0.15)
    
    base_assets = ctx['total_assets']
    base_liabilities = ctx['total_liabilities']
    base_funded = ctx['funded_status']
    asset_dur = ctx['asset_dur']
    liability_dur = ctx['liability_dur']
    
    # 利率冲击
    rate_impact_assets = -base_assets * asset_dur * (rate_bp / 10000) * 0.4  # 40% 固收
    rate_impact_liab = -base_liabilities * liability_dur * (rate_bp / 10000)
    
    # 权益冲击
    equity_impact = base_assets * 0.34 * equity_pct  # 34% 权益
    
    stressed_assets = base_assets + rate_impact_assets + equity_impact
    stressed_liab = base_liabilities + rate_impact_liab
    stressed_funded = stressed_assets / stressed_liab
    
    return {
        "type": "stress",
        "scenario": {"rate_bp": rate_bp, "equity_pct": equity_pct},
        "stressed_funded": stressed_funded,
        "delta_funded": stressed_funded - base_funded,
        "stressed_assets": stressed_assets,
        "stressed_liabilities": stressed_liab,
        "stressed_surplus": stressed_assets - stressed_liab,
    }


def _call_llm(api_key: str, system_prompt: str, user_query: str) -> str:
    """调用 LLM (无头版)"""
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
# 便捷函数：构建 System Prompt
# ============================================================

def build_system_prompt(ctx: dict) -> str:
    """
    构建标准的 System Prompt
    
    这个函数也可以被 UI 层调用，保持一致性
    """
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

IMPORTANT: You are part of an Agentic System with AUDIT capabilities. 
- Any hedging/rebalancing suggestions are automatically checked against compliance limits
- If a suggestion exceeds limits, the system auto-adjusts to a compliant alternative
- Always acknowledge when the system has auto-corrected your initial suggestion

=== PORTFOLIO SNAPSHOT ===

Key Metrics:
- Funded Status: {funded_status:.1%} (Target: 111%)
- Total Assets: ${total_assets/1000:.1f}B | Liabilities: ${total_liabilities/1000:.1f}B
- Surplus: ${surplus/1000:.1f}B
- Duration Gap: {duration_gap:.1f} years (Asset: {asset_dur:.1f} | Liab: {liability_dur:.1f})
- FX Exposure: {fx_pct:.1%} (Limit: 15%)

=== COMPLIANCE LIMITS ===
- Max Hedge Ratio: 80%
- Max FX Exposure: 15%
- Min Equity Exposure: 20%
- Single Issuer Limit: 5%

Asset Allocation:
{allocation_str}

Limit Status:
{limits_str}
"""