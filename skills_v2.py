"""
skills_v2.py — Risk Toolkit with Tool Calling Support

升级特性:
    1. @tool 装饰器: 让 LLM 能自主选择工具
    2. Pydantic 校验: 严格的参数类型和范围检查
    3. 详细 Docstring: AI 的"工具说明书"

架构定位:
    领域层 (Domain Layer) — 封装所有风险计算的业务逻辑

使用方式:
    from skills_v2 import get_all_tools
    tools = get_all_tools()
    llm_with_tools = llm.bind_tools(tools)
"""

from typing import Optional, List, Literal
from pydantic import BaseModel, Field, field_validator
from langchain_core.tools import tool


# ============================================================
# Pydantic 参数模型 (Input Schemas)
# ============================================================

class HedgeComplianceInput(BaseModel):
    """对冲合规检查的输入参数"""
    ratio: float = Field(
        ...,
        description="建议的对冲比例，范围 0.0-1.0（例如 0.85 表示 85%）",
        ge=0.0,
        le=1.0,
    )
    hedge_type: Literal["duration", "fx", "equity"] = Field(
        default="duration",
        description="对冲类型：duration(久期对冲)、fx(外汇对冲)、equity(权益对冲)",
    )
    
    @field_validator('ratio')
    @classmethod
    def validate_ratio(cls, v):
        if v < 0 or v > 1:
            raise ValueError('对冲比例必须在 0-1 之间')
        return v


class StressTestInput(BaseModel):
    """压力测试的输入参数"""
    rate_shock_bp: int = Field(
        default=100,
        description="利率冲击幅度（基点），正数表示加息，负数表示降息",
        ge=-500,
        le=500,
    )
    equity_shock_pct: float = Field(
        default=-0.15,
        description="股票冲击幅度（百分比），例如 -0.15 表示下跌 15%",
        ge=-0.50,
        le=0.50,
    )
    inflation_shock_pct: float = Field(
        default=0.0,
        description="通胀冲击幅度（百分比）",
        ge=-0.10,
        le=0.10,
    )
    scenario_name: str = Field(
        default="Custom Scenario",
        description="场景名称，用于报告标识",
    )


# ============================================================
# 合规限额定义
# ============================================================

COMPLIANCE_LIMITS = {
    "duration": {
        "max_hedge_ratio": 0.80,
        "min_duration_gap": -15.0,
        "max_duration_gap": 5.0,
    },
    "fx": {
        "max_hedge_ratio": 0.90,
        "max_exposure": 0.15,
    },
    "equity": {
        "max_hedge_ratio": 0.50,
        "min_equity_exposure": 0.20,
    },
}


# ============================================================
# Tool 1: 获取当前风险指标
# ============================================================

@tool
def get_risk_metrics(ctx: dict) -> dict:
    """
    获取当前投资组合的核心风险指标。
    
    使用场景:
        - 用户询问"当前风险状况如何"
        - 用户想了解 funded status、surplus、duration gap
        - 用户请求 portfolio snapshot 或 risk dashboard
    
    Args:
        ctx: 风险上下文（从 engine.build_context() 获取）
    
    Returns:
        包含以下指标的字典:
        - funded_status: 资金充足率
        - total_assets: 总资产
        - total_liabilities: 总负债
        - surplus: 盈余
        - duration_gap: 久期缺口
        - fx_exposure: 外汇敞口
    """
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


# ============================================================
# Tool 2: 压力测试计算
# ============================================================

@tool(args_schema=StressTestInput)
def run_stress_test(
    ctx: dict,
    rate_shock_bp: int = 100,
    equity_shock_pct: float = -0.15,
    inflation_shock_pct: float = 0.0,
    scenario_name: str = "Custom Scenario",
) -> dict:
    """
    执行压力测试，计算极端市场条件下的投资组合影响。
    
    使用场景:
        - 用户询问"如果利率上升 100bp 会怎样"
        - 用户想测试"股市下跌 20% 的影响"
        - 用户请求 stress test、scenario analysis、what-if analysis
        - 用户提到 2008 危机、滞胀等历史场景
    
    Args:
        ctx: 风险上下文
        rate_shock_bp: 利率冲击（基点），例如 100 表示加息 1%
        equity_shock_pct: 股票冲击（百分比），例如 -0.15 表示下跌 15%
        inflation_shock_pct: 通胀冲击（百分比）
        scenario_name: 场景名称
    
    Returns:
        压力测试结果，包含压力后的 funded status、资产、负债、surplus
    """
    # 基线数据
    base_assets = ctx['total_assets']
    base_liabilities = ctx['total_liabilities']
    base_funded = ctx['funded_status']
    asset_dur = ctx['asset_dur']
    liability_dur = ctx['liability_dur']
    
    # 资产配置假设
    equity_weight = 0.35
    fi_weight = 0.40
    real_asset_weight = 0.25
    
    # 计算冲击
    rate_change = rate_shock_bp / 10000
    asset_rate_impact = -asset_dur * rate_change * fi_weight
    liability_rate_impact = -liability_dur * rate_change
    equity_impact = equity_shock_pct * equity_weight
    inflation_impact = inflation_shock_pct * real_asset_weight * 0.5
    
    # 压力后数值
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


# ============================================================
# Tool 3: 对冲合规检查
# ============================================================

@tool(args_schema=HedgeComplianceInput)
def check_hedge_compliance(
    ctx: dict,
    ratio: float,
    hedge_type: str = "duration",
) -> dict:
    """
    检查对冲方案是否符合 HOOPP 的合规限额要求。
    
    使用场景:
        - 用户想"把对冲比例提高到 85%"
        - 用户询问"我能对冲多少"
        - 用户请求调整 hedge ratio、duration hedge、FX hedge
        - 任何涉及对冲策略调整的请求
    
    重要: 这是一个需要合规审核的操作。如果建议的比例超出限额，
    系统会返回 FAIL 状态和建议的合规替代方案。
    
    Args:
        ctx: 风险上下文
        ratio: 建议的对冲比例（0.0-1.0）
        hedge_type: 对冲类型（duration/fx/equity）
    
    Returns:
        合规检查结果:
        - status: PASS 或 FAIL
        - proposed_ratio: 建议的比例
        - max_allowed: 允许的最大比例
        - recommendation: 如果 FAIL，建议的合规替代方案
        - requires_approval: 是否需要人工审批
    """
    limit_config = COMPLIANCE_LIMITS.get(hedge_type, COMPLIANCE_LIMITS["duration"])
    max_ratio = limit_config.get("max_hedge_ratio", 1.0)
    
    is_compliant = ratio <= max_ratio
    
    if is_compliant:
        return {
            "status": "PASS",
            "proposed_ratio": ratio,
            "max_allowed": max_ratio,
            "hedge_type": hedge_type,
            "message": f"对冲比例 {ratio:.0%} 在限额 {max_ratio:.0%} 内，合规通过",
            "recommendation": None,
            "requires_approval": False,
        }
    else:
        compliant_ratio = max_ratio * 0.95  # 留 5% buffer
        return {
            "status": "FAIL",
            "proposed_ratio": ratio,
            "max_allowed": max_ratio,
            "hedge_type": hedge_type,
            "message": f"对冲比例 {ratio:.0%} 超出限额 {max_ratio:.0%}，需要人工审批",
            "recommendation": compliant_ratio,
            "recommendation_message": f"建议调整至 {compliant_ratio:.0%}（限额的 95%）",
            "requires_approval": True,
        }


# ============================================================
# Tool 4: 限额状态查询
# ============================================================

@tool
def get_limit_status(ctx: dict) -> dict:
    """
    获取所有风险限额的当前状态，识别 breaches 和 warnings。
    
    使用场景:
        - 用户询问"有没有超限"
        - 用户想了解 limit breaches、compliance status
        - 用户请求 risk limit report、warning check
    
    Args:
        ctx: 风险上下文
    
    Returns:
        限额状态摘要:
        - total_limits: 总限额数量
        - breaches: 超限数量
        - warnings: 警告数量
        - breach_details: 超限详情
        - warning_details: 警告详情
    """
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


# ============================================================
# Tool 5: 资产配置查询
# ============================================================

@tool
def get_asset_allocation(ctx: dict) -> dict:
    """
    获取当前资产配置与政策目标的对比。
    
    使用场景:
        - 用户询问"当前资产配置是什么"
        - 用户想了解 allocation、portfolio composition
        - 用户请求与 policy target 的偏离分析
    
    Args:
        ctx: 风险上下文
    
    Returns:
        资产配置详情，包含各资产类别的当前权重和目标权重
    """
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
        "as_of_date": "2024-12-31",  # 可以从 ctx 中获取
    }


# ============================================================
# 工具注册表
# ============================================================

def get_all_tools() -> List:
    """
    获取所有可用工具的列表
    
    用于绑定到 LLM:
        tools = get_all_tools()
        llm_with_tools = llm.bind_tools(tools)
    """
    return [
        get_risk_metrics,
        run_stress_test,
        check_hedge_compliance,
        get_limit_status,
        get_asset_allocation,
    ]


def get_tool_descriptions() -> dict:
    """
    获取所有工具的描述（用于 UI 展示）
    """
    return {
        "get_risk_metrics": "📊 获取核心风险指标",
        "run_stress_test": "🎚️ 执行压力测试",
        "check_hedge_compliance": "🛡️ 检查对冲合规",
        "get_limit_status": "⚠️ 查询限额状态",
        "get_asset_allocation": "📈 获取资产配置",
    }


# ============================================================
# 预设压力场景
# ============================================================

PRESET_SCENARIOS = {
    "rate_up_100": StressTestInput(
        rate_shock_bp=100,
        equity_shock_pct=0.0,
        scenario_name="Rate +100bp",
    ),
    "rate_down_100": StressTestInput(
        rate_shock_bp=-100,
        equity_shock_pct=0.0,
        scenario_name="Rate -100bp",
    ),
    "equity_crash": StressTestInput(
        rate_shock_bp=0,
        equity_shock_pct=-0.20,
        scenario_name="Equity -20%",
    ),
    "stagflation": StressTestInput(
        rate_shock_bp=200,
        equity_shock_pct=-0.15,
        inflation_shock_pct=0.03,
        scenario_name="Stagflation",
    ),
    "crisis_2008": StressTestInput(
        rate_shock_bp=-150,
        equity_shock_pct=-0.40,
        inflation_shock_pct=-0.01,
        scenario_name="2008 Crisis",
    ),
}
