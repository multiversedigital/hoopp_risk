import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

# 输出目录：与 app.py 一致，写入 data/ 便于应用加载
_SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = _SCRIPT_DIR / "data"

# ==========================================
# 1. 配置参数 (Configuration)
# ==========================================
np.random.seed(42)
NUM_DAYS = 10
ROWS_PER_DAY = 200
TOTAL_ASSETS_CAD = 124000       # 124 Billion CAD — 基准总额，每日实际值围绕此波动
TOTAL_LIABILITY_CAD = 110800    # 110.8 Billion CAD — 固定负债总额（精算负债不随市场每日波动）
DAILY_DRIFT_SIGMA = 0.00316     # 每日资产漂移标准差；累积10天后 ±1%~±2% 范围波动

# --- 事件注入: FX 敞口突破 ---
# 模拟某天 FX Forward 对冲仓部分平仓（流动性约束），导致净 FX 敞口突破 15% 上限。
# 注入逻辑: 在指定日期，将 FX Forward 的 fx_exposure_cad 缩减至原值的 FX_BREACH_RETAIN 倍。
# 正常净敞口 ~12.5%，对冲仓缩减到 40% 后净敞口跳到 ~15.7%，越过 15% limit。
FX_BREACH_DATE = '2026-01-27'   # 注入日期（选中间某天，前后都有对比）
FX_BREACH_RETAIN = 0.86         # 该天 FX Forward 对冲仓保留比例（缩减到原来的 86%，净敞口从 ~12.5% 突破到 ~15.8%）

# 定义资产配置特征 (基于 HOOPP 2026 SIPP & 2024 Annual Report)
# Weight: 目标权重
# Lev: 杠杆率 (Exposure / MTM)，用于模拟衍生品
# FX_Ratio: 未对冲比例 (1.0 = 完全暴露, 0.0 = 完全对冲)
ASSET_PROFILES = [
    # --- Fixed Income (Liability Hedging) ---
    {'class': 'Fixed Income', 'sub': 'Nominal Bonds',     'sec': 'Government', 'w': 0.30, 'dur': 8.0,  'inf': 0.0, 'beta': 0.0, 'lev': 1.0,  'fx': 0.1,  'geo': 'North America', 'ctry': 'Canada',  'curr': 'CAD'},
    {'class': 'Fixed Income', 'sub': 'Real Return Bonds', 'sec': 'Government', 'w': 0.12, 'dur': 14.0, 'inf': 1.0, 'beta': 0.0, 'lev': 1.0,  'fx': 0.0,  'geo': 'North America', 'ctry': 'Canada',  'curr': 'CAD'},

    # --- Public Equities (Return Seeking) ---
    {'class': 'Public Equities', 'sub': 'Developed Markets',      'sec': 'Info Tech',   'w': 0.15, 'dur': 0.0, 'inf': 0.1, 'beta': 1.2, 'lev': 1.0,  'fx': 1.0,  'geo': 'North America', 'ctry': 'USA',     'curr': 'USD'},
    {'class': 'Public Equities', 'sub': 'Developed Markets',      'sec': 'Financials',  'w': 0.10, 'dur': 0.0, 'inf': 0.1, 'beta': 1.0, 'lev': 1.0,  'fx': 0.5,  'geo': 'Europe',        'ctry': 'UK',      'curr': 'GBP'},
    {'class': 'Public Equities', 'sub': 'Emerging Markets',       'sec': 'Consumer',    'w': 0.08, 'dur': 0.0, 'inf': 0.3, 'beta': 1.1, 'lev': 1.0,  'fx': 1.0,  'geo': 'APAC',          'ctry': 'S.Korea', 'curr': 'KRW'},
    {'class': 'Public Equities', 'sub': 'Derivatives (Futures)',  'sec': 'Multi',       'w': 0.05, 'dur': 0.0, 'inf': 0.0, 'beta': 1.0, 'lev': 20.0, 'fx': 0.0,  'geo': 'North America', 'ctry': 'USA',     'curr': 'USD'},  # fx=0: 期货 FX 风险独立对冲，不按杠杆放大

    # --- Private Markets (Inflation Sensitive) ---
    {'class': 'Private Real Estate',    'sub': 'Global RE',   'sec': 'Real Estate', 'w': 0.18, 'dur': 0.0, 'inf': 0.6, 'beta': 0.4, 'lev': 1.0, 'fx': 0.2, 'geo': 'North America', 'ctry': 'Canada',  'curr': 'CAD'},
    {'class': 'Private Infrastructure', 'sub': 'Renewables',  'sec': 'Utilities',   'w': 0.07, 'dur': 0.0, 'inf': 0.5, 'beta': 0.3, 'lev': 1.0, 'fx': 0.3, 'geo': 'Europe',        'ctry': 'Germany', 'curr': 'EUR'},

    # --- Credit & Funding ---
    {'class': 'Private Credit',  'sub': 'Direct Lending', 'sec': 'Financials', 'w': 0.07,  'dur': 4.0, 'inf': 0.0, 'beta': 0.2, 'lev': 1.0, 'fx': 0.0,  'geo': 'North America', 'ctry': 'USA', 'curr': 'USD'},
    {'class': 'Cash & Funding',  'sub': 'FX Forwards',    'sec': 'Multi',      'w': -0.12, 'dur': 0.0, 'inf': 0.0, 'beta': 0.0, 'lev': 2.0, 'fx': 1.0, 'geo': 'North America', 'ctry': 'USA', 'curr': 'USD'},  # lev=2.0: 对冲仓规模约 24%，配合正敞口 ~37% 得到净敞口 ~13%
]

# ==========================================
# 2. 生成核心函数
# ==========================================
def _generate_business_dates(base_date, n_days):
    """从 base_date 往回数 n_days 个工作日（跳过周六周日），返回逆序列表（最新在前）。"""
    dates = []
    current = base_date
    while len(dates) < n_days:
        if current.weekday() < 5:  # 0=Mon ~ 4=Fri
            dates.append(current)
        current -= timedelta(days=1)
    return dates  # 已经是最新在前的顺序


def generate_positions():
    data = []
    base_date = datetime(2026, 1, 30)  # 周五，确保最新日恰好是一个工作日

    # 生成 10 个工作日日期（最新在前）
    business_dates = _generate_business_dates(base_date, NUM_DAYS)

    # 预生成 10 天的资产漂移路径（随机游走）
    # cumsum 保证相邻两天之间是连续漂移，不是独立跳跃
    daily_epsilons = np.random.normal(0, DAILY_DRIFT_SIGMA, NUM_DAYS)
    drift_path = np.cumsum(daily_epsilons)
    drift_path -= drift_path.mean()  # 居中：路径围绕 0 上下波动，避免单向漂移
    # drift_path[0] 对应最早的那天，反转后和 business_dates（最新在前）对齐
    drift_path = drift_path[::-1]

    for day_idx, current_date in enumerate(business_dates):
        # 当日资产总额 = 基准 × (1 + 累积漂移)
        daily_total = TOTAL_ASSETS_CAD * (1 + drift_path[day_idx])

        # --- A. 生成资产端 (Assets) ---
        for profile in ASSET_PROFILES:
            # 用当日波动后的总额分配到该类别
            target_amt = daily_total * profile['w']
            n_rows = max(2, int(ROWS_PER_DAY * abs(profile['w'])))

            for _ in range(n_rows):
                # 位置级别噪声（用于模拟持仓内部的正常波动，不影响总额趋势）
                mtm = (target_amt / n_rows) * np.random.normal(1.0, 0.05)

                esg_base  = 85 if profile['class'] in ['Private Infrastructure', 'Private Real Estate'] else 75
                carb_base = 5  if profile['class'] in ['Private Infrastructure'] else 20

                mkt_exp = mtm * profile['lev']
                fx_exp  = mkt_exp * profile['fx']

                # 事件注入: breach 日期的 FX Forward 对冲仓部分平仓
                if (current_date.strftime('%Y-%m-%d') == FX_BREACH_DATE
                        and profile['sub'] == 'FX Forwards'):
                    fx_exp *= FX_BREACH_RETAIN

                row = {
                    'timestamp':              current_date.strftime('%Y-%m-%d'),
                    'asset_name':             f"{profile['sub']}_{np.random.randint(1000, 9999)}",
                    'plan_category':          'Asset',
                    'asset_class':            profile['class'],
                    'sub_asset_class':        profile['sub'],
                    'sector':                 profile['sec'],
                    'geography':              profile['geo'],
                    'country':                profile['ctry'],
                    'currency':               profile['curr'],
                    'mtm_cad':                round(mtm, 2),
                    'market_exposure_cad':    round(mkt_exp, 2),
                    'fx_exposure_cad':        round(fx_exp, 2),
                    'duration':               round(profile['dur'] + np.random.normal(0, 0.5), 1),
                    'equity_beta':            round(profile['beta'] + np.random.normal(0, 0.1), 2),
                    'inflation_beta':         profile['inf'],
                    'fx_delta':               1.0 if profile['curr'] != 'CAD' else 0.0,
                    'carbon_intensity':       max(0, round(np.random.normal(carb_base, 5), 1)),
                    'esg_score':              min(100, round(np.random.normal(esg_base, 8), 1))
                }
                data.append(row)

        # --- B. 生成负债端 (Liabilities) ---
        # 负债固定，不随资产波动。精算负债基于长期假设，不会日日变化。
        for liab_type in ['Active_Members', 'Retired_Members']:
            amt = -(TOTAL_LIABILITY_CAD * 0.5)  # 负号表示负债，Active 和 Retired 各占一半
            row = {
                'timestamp':              current_date.strftime('%Y-%m-%d'),
                'asset_name':             f"Pension_Obligation_{liab_type}",
                'plan_category':          'Liability',
                'asset_class':            'Obligations',
                'sub_asset_class':        'Actuarial',
                'sector':                 'Social Security',
                'geography':              'North America',
                'country':                'Canada',
                'currency':               'CAD',
                'mtm_cad':                round(amt, 2),
                'market_exposure_cad':    round(amt, 2),
                'fx_exposure_cad':        0.0,
                'duration':               14.5 if liab_type == 'Active_Members' else 11.2,
                'equity_beta':            0.0,
                'inflation_beta':         0.8 if liab_type == 'Active_Members' else 0.5,  # COLA 条款：Active 成员未来 COLA 调整期更长，通胀敏感度更高
                'fx_delta':               0.0,
                'carbon_intensity':       0.0,
                'esg_score':              0.0
            }
            data.append(row)

    return pd.DataFrame(data)

# ==========================================
# 3. 生成政策限额表
# ==========================================
def generate_policies():
    policies = [
        ['Asset_Mix', 'Fixed Income',            0.42, 0.20, 0.75, 0.05, 0.40, 0.30, 'Government and Corporate Bonds'],
        ['Asset_Mix', 'Public Equities',         0.38, 0.20, 0.50, 0.05, 0.25, 0.30, 'Global Developed and EM Stocks'],
        ['Asset_Mix', 'Private Real Estate',     0.18, 0.00, 0.25, 0.10, 0.30, 0.30, 'Global Real Estate Portfolio'],
        ['Asset_Mix', 'Private Infrastructure',  0.07, 0.00, 0.25, 0.10, 0.25, 0.30, 'Infrastructure and Essential Services'],
        ['Asset_Mix', 'Private Credit',          0.07, 0.00, 0.25, 0.05, 0.20, 0.30, 'Corporate and Private Debt'],
        ['Asset_Mix', 'Cash & Funding',         -0.12,-0.50, 0.00, 0.00, 0.00, 0.00, 'Repo and Leverage Funding'],
        ['Global_Limit', 'FX_Net_Exposure',      0.00, 0.00, 0.15, 0.00, 0.00, 0.00, 'Total Non-CAD Net Exposure'],
        ['Global_Limit', 'Funded_Status',        1.11, 1.00, 1.50, 0.00, 0.00, 0.00, 'Assets over Actuarial Liabilities'],
    ]
    cols = ['category_type', 'asset_class', 'policy_target', 'range_min', 'range_max',
            'issuer_limit', 'sector_limit', 'target_waci_reduction', 'description']
    return pd.DataFrame(policies, columns=cols)

# ==========================================
# 4. 执行输出
# ==========================================
if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)

    df_pos = generate_positions()
    pos_path = DATA_DIR / 'hoopp_positions_sample.csv'
    df_pos.to_csv(pos_path, index=False)

    # --- 验证输出 ---
    dates = sorted(df_pos['timestamp'].unique())
    print(f"✅ 生成成功: {pos_path}  ({len(df_pos)} 行，{len(dates)} 天)")
    print(f"   日期范围: {dates[0]} ~ {dates[-1]}")
    print()
    print(f"{'日期':<12} {'资产总额':>12} {'负债总额':>12} {'Funded Status':>14}")
    print("-" * 54)
    for d in dates:
        day_df = df_pos[df_pos['timestamp'] == d]
        a = day_df[day_df['plan_category'] == 'Asset']['mtm_cad'].sum()
        l = abs(day_df[day_df['plan_category'] == 'Liability']['mtm_cad'].sum())
        fs = a / l
        print(f"{d:<12} {a:>12,.0f} {l:>12,.0f} {fs:>13.1%}")

    df_pol = generate_policies()
    pol_path = DATA_DIR / 'policy_limit_management.csv'
    df_pol.to_csv(pol_path, index=False)
    print(f"\n✅ 生成成功: {pol_path}")