"""
skills.py — Risk Engine Skills for AI Agent

职责:
    将 engine.py 的计算函数封装为 LangChain Tools，
    供 AI Agent 调用进行风险计算和分析。

设计理念:
    不修改现有 engine.py，只是在外面套一层"技能包"
"""

from typing import Optional
from dataclasses import dataclass


@dataclass
class RiskMetrics:
    """风险指标数据结构"""
    funded_status: float
    total_assets: float
    total_liabilities: float
    surplus: float
    asset_duration: float
    liability_duration: float
    duration_gap: float
    fx_exposure: float


@dataclass
class StressResult:
    """压力测试结果"""
    scenario_name: str
    rate_shock_bp: int
    equity_shock_pct: float
    inflation_shock_pct: float
    stressed_funded: float
    delta_funded: float
    stressed_assets: float
    stressed_liabilities: float
    stressed_surplus: float
    delta_surplus: float


def get_current_risk_metrics(ctx: dict) -> RiskMetrics:
    """
    获取当前风险指标
    
    Args:
        ctx: 从 engine.build_context() 获取的上下文
        
    Returns:
        RiskMetrics: 当前风险指标
    """
    return RiskMetrics(
        funded_status=ctx['funded_status'],
        total_assets=ctx['total_assets'],
        total_liabilities=ctx['total_liabilities'],
        surplus=ctx['surplus'],
        asset_duration=ctx['asset_dur'],
        liability_duration=ctx['liability_dur'],
        duration_gap=ctx['asset_dur'] - ctx['liability_dur'],
        fx_exposure=ctx['fx_pct'],
    )


def calculate_stress_scenario(
    ctx: dict,
    rate_shock_bp: int = 0,
    equity_shock_pct: float = 0.0,
    inflation_shock_pct: float = 0.0,
    scenario_name: str = "Custom"
) -> StressResult:
    """
    计算压力测试场景
    
    Args:
        ctx: 上下文
        rate_shock_bp: 利率冲击 (基点)
        equity_shock_pct: 股票冲击 (%)
        inflation_shock_pct: 通胀冲击 (%)
        scenario_name: 场景名称
        
    Returns:
        StressResult: 压力测试结果
    """
    # 基线数据
    base_assets = ctx['total_assets']
    base_liabilities = ctx['total_liabilities']
    base_funded = ctx['funded_status']
    asset_dur = ctx['asset_dur']
    liability_dur = ctx['liability_dur']
    
    # 资产配置 (简化假设)
    equity_weight = 0.35  # 假设 35% 股票
    fi_weight = 0.40      # 假设 40% 固定收益
    real_asset_weight = 0.25  # 假设 25% 实物资产
    
    # === 计算冲击 ===
    
    # 利率冲击对资产的影响 (Duration × Rate Change)
    rate_change = rate_shock_bp / 10000  # bp to decimal
    asset_rate_impact = -asset_dur * rate_change * fi_weight
    liability_rate_impact = -liability_dur * rate_change
    
    # 股票冲击
    equity_impact = equity_shock_pct * equity_weight
    
    # 通胀冲击 (简化: 假设实物资产与通胀正相关)
    inflation_impact = inflation_shock_pct * real_asset_weight * 0.5
    
    # === 计算压力后数值 ===
    total_asset_impact = asset_rate_impact + equity_impact + inflation_impact
    stressed_assets = base_assets * (1 + total_asset_impact)
    stressed_liabilities = base_liabilities * (1 + liability_rate_impact)
    stressed_surplus = stressed_assets - stressed_liabilities
    stressed_funded = stressed_assets / stressed_liabilities if stressed_liabilities > 0 else 0
    
    return StressResult(
        scenario_name=scenario_name,
        rate_shock_bp=rate_shock_bp,
        equity_shock_pct=equity_shock_pct,
        inflation_shock_pct=inflation_shock_pct,
        stressed_funded=stressed_funded,
        delta_funded=stressed_funded - base_funded,
        stressed_assets=stressed_assets,
        stressed_liabilities=stressed_liabilities,
        stressed_surplus=stressed_surplus,
        delta_surplus=stressed_surplus - (base_assets - base_liabilities),
    )


def check_hedge_compliance(
    ctx: dict,
    proposed_hedge_ratio: float,
    hedge_type: str = "duration"
) -> dict:
    """
    检查对冲方案是否合规
    
    Args:
        ctx: 上下文
        proposed_hedge_ratio: 建议的对冲比例 (0-1)
        hedge_type: 对冲类型 ("duration", "fx", "equity")
        
    Returns:
        dict: 合规检查结果
    """
    # === 限额定义 ===
    LIMITS = {
        "duration": {
            "max_hedge_ratio": 0.80,    # 最大对冲比例 80%
            "min_duration_gap": -15.0,  # 最小 duration gap
            "max_duration_gap": 5.0,    # 最大 duration gap
        },
        "fx": {
            "max_hedge_ratio": 0.90,
            "max_exposure": 0.15,       # FX exposure 不超过 15%
        },
        "equity": {
            "max_hedge_ratio": 0.50,    # 股票最多对冲 50%
            "min_equity_exposure": 0.20, # 至少保留 20% 股票敞口
        },
    }
    
    limit_config = LIMITS.get(hedge_type, LIMITS["duration"])
    max_ratio = limit_config.get("max_hedge_ratio", 1.0)
    
    # === 合规检查 ===
    is_compliant = proposed_hedge_ratio <= max_ratio
    
    if is_compliant:
        return {
            "status": "PASS",
            "proposed_ratio": proposed_hedge_ratio,
            "max_allowed": max_ratio,
            "message": f"✅ Hedge ratio {proposed_hedge_ratio:.0%} is within limit ({max_ratio:.0%})",
            "recommendation": None,
        }
    else:
        # 计算合规的替代方案
        compliant_ratio = max_ratio * 0.95  # 留 5% buffer
        return {
            "status": "FAIL",
            "proposed_ratio": proposed_hedge_ratio,
            "max_allowed": max_ratio,
            "message": f"❌ Hedge ratio {proposed_hedge_ratio:.0%} exceeds limit ({max_ratio:.0%})",
            "recommendation": compliant_ratio,
            "recommendation_message": f"💡 Suggested compliant ratio: {compliant_ratio:.0%}",
        }


def get_limit_status(ctx: dict) -> dict:
    """
    获取当前限额状态
    
    Returns:
        dict: 限额状态摘要
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
    }


# ============================================================
# 预设场景
# ============================================================
PRESET_SCENARIOS = {
    "rate_up_100": {
        "name": "Rate +100bp",
        "rate_shock_bp": 100,
        "equity_shock_pct": 0.0,
        "inflation_shock_pct": 0.0,
    },
    "rate_down_100": {
        "name": "Rate -100bp", 
        "rate_shock_bp": -100,
        "equity_shock_pct": 0.0,
        "inflation_shock_pct": 0.0,
    },
    "equity_crash": {
        "name": "Equity -20%",
        "rate_shock_bp": 0,
        "equity_shock_pct": -0.20,
        "inflation_shock_pct": 0.0,
    },
    "stagflation": {
        "name": "Stagflation",
        "rate_shock_bp": 200,
        "equity_shock_pct": -0.15,
        "inflation_shock_pct": 0.03,
    },
    "2008_crisis": {
        "name": "2008 Crisis",
        "rate_shock_bp": -150,
        "equity_shock_pct": -0.40,
        "inflation_shock_pct": -0.01,
    },
}