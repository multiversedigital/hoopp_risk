"""
engine.py — HOOPP Risk Navigator 核心计算引擎

对外暴露两个入口：
    calculate_metrics(df_in, s_rate, s_eq, s_inf) → df_stressed
        Tab4 Stress Testing 用，slider 变化时实时调用

    build_context(df_all, df_policy, selected_date) → ctx (dict)
        app.py 调用一次，返回所有 Tab 需要的数据

内部按 Layer 分层计算，不跳层：
    Layer 0  原始数据
    Layer 1  日期过滤
    Layer 2  Baseline stress（shock 全 0）
    Layer 3  KPI 标量
    Layer 4  派生表（comp_df, limits_df, issuer_df, fx）
    Layer 5  时间序列 + AI summary
"""

import pandas as pd
import numpy as np


# ============================================================
# PUBLIC: calculate_metrics
# ============================================================

def calculate_metrics(df_in: pd.DataFrame,
                      s_rate: float,
                      s_eq: float,
                      s_inf: float) -> pd.DataFrame:
    """
    对一天的仓位数据执行 Scheme A stress 计算。

    参数:
        df_in   : 单日仓位 DataFrame（Asset + Liability 行都在里面）
        s_rate  : 利率冲击 (bps)，如 +50 表示利率上升 50bp
        s_eq    : 权益冲击 (%)，如 -10 表示股市跌 10%
        s_inf   : 通胀冲击 (%)，如 +1 表示通胀预期上升 1%

    返回:
        带新列 'mtm_stressed' 的 DataFrame
        mtm_stressed = mtm_cad + PnL
        PnL = market_exposure_cad × (rate_impact + equity_impact + inf_impact)
    """
    df = df_in.copy()

    # 三个独立风险因子的 P&L%
    rate_impact   = -1.0 * df['duration']        * (s_rate / 10_000)  # bps → 小数
    equity_impact =        df['equity_beta']     * (s_eq   / 100)     # % → 小数
    inf_impact    =        df['inflation_beta']  * (s_inf  / 100)     # % → 小数

    total_shock_pct = rate_impact + equity_impact + inf_impact

    # PnL 作用在 market_exposure 上（衍生品按 notional exposure 算）
    pnl = df['market_exposure_cad'] * total_shock_pct

    df['mtm_stressed'] = df['mtm_cad'] + pnl
    return df


# ============================================================
# PUBLIC: build_context
# ============================================================

def build_context(df_all: pd.DataFrame,
                  df_policy: pd.DataFrame,
                  selected_date: str) -> dict:
    """
    app.py 的唯一入口。返回 ctx dict，所有 Tab 从这里取数据。
    """
    ctx = {}

    # ─── Layer 0: 原始数据 passthrough（Tab5 Pipeline 用） ───
    ctx['df_all']     = df_all
    ctx['df_policy']  = df_policy

    # ─── Layer 1: 日期过滤 ───
    df_day = df_all[df_all['timestamp'] == selected_date].copy()
    ctx['df_day'] = df_day          # Tab4 Stress 用（未 stress 的原始数据）

    # ─── Layer 2: Baseline（shock 全 0，算出 mtm_stressed = mtm_cad） ───
    df_baseline = calculate_metrics(df_day, 0, 0, 0)
    assets      = df_baseline[df_baseline['plan_category'] == 'Asset']
    liabilities = df_baseline[df_baseline['plan_category'] == 'Liability']

    # 暴露给 Tab（Sunburst / ESG scatter 需要行级别数据）
    ctx['assets']      = assets
    ctx['liabilities'] = liabilities

    # ─── Layer 3: KPI 标量 ───
    kpis = _build_kpis(assets, liabilities)
    ctx.update(kpis)
    # kpis keys: total_assets, total_liabilities,
    #            funded_status, surplus, asset_dur, liability_dur

    # ─── Layer 4: 派生表 ───
    comp_df = _build_comp_df(assets, kpis['total_assets'], df_policy)
    ctx['comp_df'] = comp_df                          # Tab1 柱状图

    ctx['mix_df'] = _build_mix_df(assets)             # Tab1 饼图

    fx_pct, net_fx_exposure = _build_fx(assets, kpis['total_assets'])
    ctx['fx_pct']           = fx_pct                  # Tab2 仪表盘
    ctx['net_fx_exposure']  = net_fx_exposure         # Tab2 caption

    limits_df = _build_limits_df(comp_df, fx_pct, kpis['funded_status'])
    ctx['limits_df'] = limits_df                      # Tab2 红绿灯表

    issuer_df = _build_issuer_df(assets, kpis['total_assets'])
    ctx['issuer_df'] = issuer_df                      # Tab2 Top5 表

    # ─── sidebar（放在 ai_summary 之前，因为 summary 要用 available_dates） ───
    ctx['available_dates'] = sorted(df_all['timestamp'].unique())

    # ─── Layer 5: 时间序列 + AI summary ───
    ctx['time_series_df']     = _build_time_series(df_all)
    ctx['ai_context_summary'] = _build_ai_summary(ctx)

    return ctx


# ============================================================
# PRIVATE helpers — 按依赖顺序排列
# ============================================================

def _build_kpis(assets: pd.DataFrame,
                liabilities: pd.DataFrame) -> dict:
    """
    Layer 3: 从 assets / liabilities 算出所有 scalar KPI。
    多个 Tab 共用，抽成一个函数避免重复。
    """
    total_assets      = assets['mtm_stressed'].sum()
    total_liabilities = abs(liabilities['mtm_stressed'].sum())  # 负债 mtm 是负数

    funded_status = total_assets / total_liabilities if total_liabilities != 0 else 0
    surplus       = total_assets - total_liabilities

    # 加权资产久期: Σ(duration_i × mtm_i) / total_assets
    asset_dur = (assets['duration'] * assets['mtm_stressed']).sum() / total_assets \
                if total_assets != 0 else 0

    # 负债久期（负债固定，但算一次放在 ctx 里，AI summary 用）
    liab_mtm_abs      = abs(liabilities['mtm_stressed'])
    liability_dur = (liabilities['duration'] * liab_mtm_abs).sum() / total_liabilities \
                    if total_liabilities != 0 else 0

    return {
        'total_assets':      total_assets,
        'total_liabilities': total_liabilities,
        'funded_status':     funded_status,
        'surplus':           surplus,
        'asset_dur':         asset_dur,
        'liability_dur':     liability_dur,
    }


def _build_mix_df(assets: pd.DataFrame) -> pd.DataFrame:
    """
    Tab1 饼图数据：按 asset_class 汇总 mtm_stressed。
    饼图本身会过滤掉负值（Cash & Funding），但这里保留完整数据，
    过滤逻辑放在 Tab 渲染层。
    """
    return (assets
            .groupby('asset_class')['mtm_stressed']
            .sum()
            .reset_index()
            .rename(columns={'mtm_stressed': 'total_mtm'}))


def _build_comp_df(assets: pd.DataFrame,
                   total_assets: float,
                   df_policy: pd.DataFrame) -> pd.DataFrame:
    """
    Tab1 柱状图 / Tab2 limits_df 的基础：
        asset_class | current_weight | policy_target | range_min | range_max

    3 步依赖链:
        ① groupby asset_class → sum
        ② 除以 total_assets → current_weight
        ③ merge policy 表 → 加上 target / range
    """
    # ① + ②
    current_w = (assets
                 .groupby('asset_class')['mtm_stressed']
                 .sum()
                 .div(total_assets)
                 .reset_index()
                 .rename(columns={'mtm_stressed': 'current_weight'}))

    # ③ merge policy（只取 Asset_Mix 行）
    policy_mix = df_policy[df_policy['category_type'] == 'Asset_Mix'].copy()

    comp = pd.merge(policy_mix, current_w, on='asset_class', how='left').fillna(0)

    # 保留需要的列，按固定顺序
    return comp[['asset_class', 'current_weight',
                 'policy_target', 'range_min', 'range_max',
                 'issuer_limit', 'sector_limit']]


def _build_fx(assets: pd.DataFrame, total_assets: float) -> tuple:
    """
    FX 敞口: net_fx_exposure (绝对值 M CAD) 和 fx_pct (占比)。
    """
    net_fx = assets['fx_exposure_cad'].sum()
    fx_pct = net_fx / total_assets if total_assets != 0 else 0
    return fx_pct, net_fx


def _build_limits_df(comp_df: pd.DataFrame,
                     fx_pct: float,
                     funded_status: float) -> pd.DataFrame:
    """
    Tab2 红绿灯表。在 comp_df 基础上:
        ① 对每个 asset_class 判断 Status（BREACH / WARN / OK）
        ② 把 FX 和 Funded Status 的 global limit 也合并进来

    判断规则:
        current < range_min 或 current > range_max  →  🔴 BREACH
        current > range_max × 0.9                   →  🟡 WARN
        否则                                        →  🟢 OK
    """
    df = comp_df.copy()

    def _status(row):
        c = row['current_weight']
        lo, hi = row['range_min'], row['range_max']
        if c > hi or c < lo:
            return '🔴 BREACH'
        if hi > 0 and c > hi * 0.9:
            return '🟡 WARN'
        return '🟢 OK'

    df['Status'] = df.apply(_status, axis=1)

    # ── 把 FX 和 Funded Status 的 global limit 行追加进来 ──
    fx_row = pd.DataFrame([{
        'asset_class':     'FX Net Exposure',
        'current_weight':  fx_pct,
        'policy_target':   0.0,
        'range_min':       0.0,
        'range_max':       0.15,           # 15% limit
        'issuer_limit':    0.0,
        'sector_limit':    0.0,
        'Status':          '🔴 BREACH' if fx_pct > 0.15 else
                           ('🟡 WARN'  if fx_pct > 0.135 else '🟢 OK'),
    }])

    fs_row = pd.DataFrame([{
        'asset_class':     'Funded Status',
        'current_weight':  funded_status,
        'policy_target':   1.11,
        'range_min':       1.00,
        'range_max':       1.50,
        'issuer_limit':    0.0,
        'sector_limit':    0.0,
        'Status':          '🔴 BREACH' if (funded_status > 1.50 or funded_status < 1.00) else
                           ('🟡 WARN'  if funded_status < 1.05 else '🟢 OK'),
    }])

    return pd.concat([df, fx_row, fs_row], ignore_index=True)


def _build_issuer_df(assets: pd.DataFrame, total_assets: float) -> pd.DataFrame:
    """
    Tab2 Top5 单一发行人集中度表:
        Issuer | Weight | Status

    issuer_limit 从 policy 里取，但当前所有 asset_class 的 issuer_limit
    都是 5% 或 10%，这里用保守值 5% 作为通用阈值。
    """
    ISSUER_LIMIT = 0.05  # 5%

    top5 = (assets
            .groupby('asset_name')['mtm_stressed']
            .sum()
            .nlargest(5))

    issuer_df = pd.DataFrame({
        'Issuer': top5.index,
        'Weight': top5.values / total_assets,
    })
    issuer_df['Status'] = issuer_df['Weight'].apply(
        lambda w: '🔴 BREACH' if w > ISSUER_LIMIT else '🟢 OK'
    )
    return issuer_df


def _build_time_series(df_all: pd.DataFrame) -> pd.DataFrame:
    """
    对所有日期循环执行 baseline 计算，输出 5 列时间序列:
        date | funded_status | fx_pct | w_fi | w_eq | w_re

    列选择依据（见 engine_design.md 附录 A）:
        强信号（CV高 + 跨越 threshold，默认画图用）:
            funded_status  CV=0.8%   跨越 111% target ✓
            fx_pct         CV=9.1%   跨越 15% limit   ✓  (1/27 breach event)
        弱信号（波动极小但有 threshold crossing，备用数据）:
            w_fi           CV=0.3%   在 42% target 附近穿越
            w_eq           CV=0.5%   在 38% target 附近穿越
            w_re           CV=0.9%   在 18% target 附近穿越

    淘汰的候选 metric（CV<1% 且无 threshold crossing，10天内几乎不动）:
        total_assets, asset_dur, liability_dur, duration_gap,
        w_gov, w_tech, w_na, top_issuer_w

    使用方式: Tab 层面按需取列。默认只画 funded_status + fx_pct，
    如果将来需要 asset_class 权重趋势，数据已在此，无需修改 engine。
    """
    # 预计算 asset_class 权重所需的 class 名
    FI  = 'Fixed Income'
    EQ  = 'Public Equities'
    RE  = 'Private Real Estate'

    rows = []
    for date in sorted(df_all['timestamp'].unique()):
        day = df_all[df_all['timestamp'] == date]
        day_b  = calculate_metrics(day, 0, 0, 0)   # baseline, no stress
        assets = day_b[day_b['plan_category'] == 'Asset']
        liabs  = day_b[day_b['plan_category'] == 'Liability']

        ta = assets['mtm_stressed'].sum()
        tl = abs(liabs['mtm_stressed'].sum())

        # 按 asset_class 分组一次，避免重复 filter
        class_sums = assets.groupby('asset_class')['mtm_stressed'].sum()

        rows.append({
            'date':           date,
            'funded_status':  ta / tl if tl != 0 else 0,
            'fx_pct':         assets['fx_exposure_cad'].sum() / ta if ta != 0 else 0,
            'w_fi':           class_sums.get(FI, 0) / ta if ta != 0 else 0,
            'w_eq':           class_sums.get(EQ, 0) / ta if ta != 0 else 0,
            'w_re':           class_sums.get(RE, 0) / ta if ta != 0 else 0,
        })

    return pd.DataFrame(rows)


def _build_ai_summary(ctx: dict) -> str:
    """
    把当前快照序列化为 AI prompt 用的字符串。
    Tab3 AI Advisor 直接把这个 string 塞进 system prompt，不需要自己序列化。

    格式设计目标: 让 LLM 能一次性理解整个基金状态。
    """
    fs   = ctx['funded_status']
    sur  = ctx['surplus']
    ta   = ctx['total_assets']
    tl   = ctx['total_liabilities']
    adur = ctx['asset_dur']
    ldur = ctx['liability_dur']
    fx   = ctx['fx_pct']
    nfx  = ctx['net_fx_exposure']

    # ── Asset Mix vs Policy ──
    mix_lines = []
    for _, row in ctx['comp_df'].iterrows():
        ac     = row['asset_class']
        actual = row['current_weight']
        target = row['policy_target']
        lo     = row['range_min']
        hi     = row['range_max']
        ok     = '✓ OK' if lo <= actual <= hi else '⚠ BREACH'
        mix_lines.append(
            f"  {ac:<28} actual {actual:>6.1%} | target {target:>5.0%} | "
            f"range [{lo:.0%}, {hi:.0%}] → {ok}"
        )

    # ── Limit Status ──
    fx_status  = '⚠ BREACH' if fx > 0.15 else ('~ WARN' if fx > 0.135 else '✓ OK')
    top_issuer = ctx['issuer_df']['Weight'].max() if len(ctx['issuer_df']) > 0 else 0
    iss_status = '⚠ BREACH' if top_issuer > 0.05 else '✓ OK'

    # ── N-Day Trend ──
    ts = ctx['time_series_df']
    fs_trend  = ' → '.join(f"{v:.1%}" for v in ts['funded_status'])
    fx_trend  = ' → '.join(f"{v:.1%}" for v in ts['fx_pct'])
    fi_trend  = ' → '.join(f"{v:.1%}" for v in ts['w_fi'])
    eq_trend  = ' → '.join(f"{v:.1%}" for v in ts['w_eq'])
    re_trend  = ' → '.join(f"{v:.1%}" for v in ts['w_re'])

    # ── 拼接 ──
    summary = (
        f"--- HOOPP Fund Snapshot ({ctx['available_dates'][-1]}) ---\n"
        f"Funded Status: {fs:.1%} (target: 111%, range: 100%-150%)\n"
        f"Net Surplus: ${sur/1000:.1f}B\n"
        f"Total Assets: ${ta/1000:.1f}B | Total Liabilities: ${tl/1000:.1f}B\n"
        f"Asset Duration: {adur:.1f} yrs | Liability Duration: {ldur:.1f} yrs | "
        f"Gap: {ldur - adur:.1f} yrs\n"
        f"\n"
        f"Asset Mix vs Policy:\n"
        + '\n'.join(mix_lines) + '\n'
        f"\n"
        f"Limit Status:\n"
        f"  FX Net Exposure: {fx:.1%} (limit: 15%) → {fx_status}\n"
        f"  Top Issuer Concentration: {top_issuer:.2%} (limit: 5%) → {iss_status}\n"
        f"\n"
        f"{len(ts)}-Day Trend:\n"
        f"  Funded Status:      {fs_trend}\n"
        f"  FX Exposure:        {fx_trend}\n"
        f"  Fixed Income w:     {fi_trend}\n"
        f"  Public Equities w:  {eq_trend}\n"
        f"  Private RE w:       {re_trend}\n"
    )
    return summary
