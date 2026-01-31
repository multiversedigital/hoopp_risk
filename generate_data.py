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
np.random.seed(42)  # 锁定随机种子，保证每次生成结果一致（方便调试）
NUM_DAYS = 5
ROWS_PER_DAY = 200
TOTAL_ASSETS_CAD = 124000  # 124 Billion CAD (Total Fund Scale)
TARGET_FUNDED_STATUS = 1.11  # 目标充足率 111%

# 定义资产配置特征 (基于 HOOPP 2026 SIPP & 2024 Annual Report)
# Weight: 目标权重
# Lev: 杠杆率 (Exposure / MTM)，用于模拟衍生品
# FX_Ratio: 未对冲比例 (1.0 = 完全暴露, 0.0 = 完全对冲)
ASSET_PROFILES = [
    # --- Fixed Income (Liability Hedging) ---
    {'class': 'Fixed Income', 'sub': 'Nominal Bonds', 'sec': 'Government', 'w': 0.30, 'dur': 8.0, 'inf': 0.0, 'beta': 0.0, 'lev': 1.0, 'fx': 0.1, 'geo': 'North America', 'ctry': 'Canada', 'curr': 'CAD'},
    {'class': 'Fixed Income', 'sub': 'Real Return Bonds', 'sec': 'Government', 'w': 0.12, 'dur': 14.0, 'inf': 1.0, 'beta': 0.0, 'lev': 1.0, 'fx': 0.0, 'geo': 'North America', 'ctry': 'Canada', 'curr': 'CAD'},
    
    # --- Public Equities (Return Seeking) ---
    {'class': 'Public Equities', 'sub': 'Developed Markets', 'sec': 'Info Tech', 'w': 0.15, 'dur': 0.0, 'inf': 0.1, 'beta': 1.2, 'lev': 1.0, 'fx': 1.0, 'geo': 'North America', 'ctry': 'USA', 'curr': 'USD'},
    {'class': 'Public Equities', 'sub': 'Developed Markets', 'sec': 'Financials', 'w': 0.10, 'dur': 0.0, 'inf': 0.1, 'beta': 1.0, 'lev': 1.0, 'fx': 0.5, 'geo': 'Europe', 'ctry': 'UK', 'curr': 'GBP'},
    {'class': 'Public Equities', 'sub': 'Emerging Markets', 'sec': 'Consumer', 'w': 0.08, 'dur': 0.0, 'inf': 0.3, 'beta': 1.1, 'lev': 1.0, 'fx': 1.0, 'geo': 'APAC', 'ctry': 'S.Korea', 'curr': 'KRW'},
    {'class': 'Public Equities', 'sub': 'Derivatives (Futures)', 'sec': 'Multi', 'w': 0.05, 'dur': 0.0, 'inf': 0.0, 'beta': 1.0, 'lev': 20.0, 'fx': 1.0, 'geo': 'North America', 'ctry': 'USA', 'curr': 'USD'}, # 高杠杆
    
    # --- Private Markets (Inflation Sensitive) ---
    {'class': 'Private Real Estate', 'sub': 'Global RE', 'sec': 'Real Estate', 'w': 0.18, 'dur': 0.0, 'inf': 0.6, 'beta': 0.4, 'lev': 1.0, 'fx': 0.2, 'geo': 'North America', 'ctry': 'Canada', 'curr': 'CAD'},
    {'class': 'Private Infrastructure', 'sub': 'Renewables', 'sec': 'Utilities', 'w': 0.07, 'dur': 0.0, 'inf': 0.5, 'beta': 0.3, 'lev': 1.0, 'fx': 0.3, 'geo': 'Europe', 'ctry': 'Germany', 'curr': 'EUR'},
    
    # --- Credit & Funding ---
    {'class': 'Private Credit', 'sub': 'Direct Lending', 'sec': 'Financials', 'w': 0.07, 'dur': 4.0, 'inf': 0.0, 'beta': 0.2, 'lev': 1.0, 'fx': 0.0, 'geo': 'North America', 'ctry': 'USA', 'curr': 'USD'},
    {'class': 'Cash & Funding', 'sub': 'FX Forwards', 'sec': 'Multi', 'w': -0.12, 'dur': 0.0, 'inf': 0.0, 'beta': 0.0, 'lev': 5.0, 'fx': -1.0, 'geo': 'North America', 'ctry': 'USA', 'curr': 'USD'}, # 负 FX 用于对冲
]

# ==========================================
# 2. 生成核心函数
# ==========================================
def generate_positions():
    data = []
    base_date = datetime(2026, 1, 31)
    
    for day_offset in range(NUM_DAYS):
        current_date = (base_date - timedelta(days=day_offset)).strftime('%Y-%m-%d')
        
        # --- A. 生成资产端 (Assets) ---
        daily_assets_mtm = 0
        
        # 为每个 Profile 生成若干行
        for profile in ASSET_PROFILES:
            # 计算该类别的目标总金额
            target_amt = TOTAL_ASSETS_CAD * profile['w']
            # 分配给多少行 (加权分配行数)
            n_rows = max(2, int(ROWS_PER_DAY * abs(profile['w']))) 
            
            for _ in range(n_rows):
                # 随机波动金额
                mtm = (target_amt / n_rows) * np.random.normal(1.0, 0.1)
                
                # ESG 数据模拟 (Infra/RE 评分通常较高)
                esg_base = 85 if profile['class'] in ['Private Infrastructure', 'Private Real Estate'] else 75
                carb_base = 5 if profile['class'] in ['Private Infrastructure'] else 20
                
                # 衍生品逻辑: Exposure = MTM * Leverage
                mkt_exp = mtm * profile['lev']
                
                # 外汇逻辑: FX Exposure = Mkt Exposure * FX Ratio
                # 如果是 FX Forward (Cash & Funding), 这里的 FX Exposure 会是负数，起到对冲作用
                fx_exp = mkt_exp * profile['fx']
                
                row = {
                    'timestamp': current_date,
                    'asset_name': f"{profile['sub']}_{np.random.randint(1000,9999)}",
                    'plan_category': 'Asset',
                    'asset_class': profile['class'],
                    'sub_asset_class': profile['sub'],
                    'sector': profile['sec'],
                    'geography': profile['geo'],
                    'country': profile['ctry'],
                    'currency': profile['curr'],
                    'mtm_cad': round(mtm, 2),
                    'market_exposure_cad': round(mkt_exp, 2),
                    'fx_exposure_cad': round(fx_exp, 2),
                    'duration': round(profile['dur'] + np.random.normal(0, 0.5), 1),
                    'equity_beta': round(profile['beta'] + np.random.normal(0, 0.1), 2),
                    'inflation_beta': profile['inf'],
                    'fx_delta': 1.0 if profile['curr'] != 'CAD' else 0.0,
                    'carbon_intensity': max(0, round(np.random.normal(carb_base, 5), 1)),
                    'esg_score': min(100, round(np.random.normal(esg_base, 8), 1))
                }
                data.append(row)
                daily_assets_mtm += mtm

        # --- B. 生成负债端 (Liabilities) ---
        # 核心逻辑: Liabilities = Assets / 1.11
        # 这保证了 Funded Status 恒定在目标附近
        target_liability_total = -(daily_assets_mtm / TARGET_FUNDED_STATUS)
        
        # 将负债拆分为 Active 和 Retired 两部分
        for i, liab_type in enumerate(['Active_Members', 'Retired_Members']):
            amt = target_liability_total * 0.5
            row = {
                'timestamp': current_date,
                'asset_name': f"Pension_Obligation_{liab_type}",
                'plan_category': 'Liability',
                'asset_class': 'Obligations',
                'sub_asset_class': 'Actuarial',
                'sector': 'Social Security',
                'geography': 'North America',
                'country': 'Canada',
                'currency': 'CAD',
                'mtm_cad': round(amt, 2),
                'market_exposure_cad': round(amt, 2), # 负债的敞口等于现值
                'fx_exposure_cad': 0.0,
                'duration': 14.5 if liab_type == 'Active_Members' else 11.2, # 退休人员久期较短
                'equity_beta': 0.0,
                'inflation_beta': 0.0, # 简化处理，精算模型中其实有隐含通胀
                'fx_delta': 0.0,
                'carbon_intensity': 0.0,
                'esg_score': 0.0
            }
            data.append(row)

    return pd.DataFrame(data)

# ==========================================
# 3. 生成政策限额表
# ==========================================
def generate_policies():
    policies = [
        ['Asset_Mix', 'Fixed Income', 0.42, 0.20, 0.75, 0.05, 0.40, 0.30, 'Government and Corporate Bonds'],
        ['Asset_Mix', 'Public Equities', 0.38, 0.20, 0.50, 0.05, 0.25, 0.30, 'Global Developed and EM Stocks'],
        ['Asset_Mix', 'Private Real Estate', 0.18, 0.00, 0.25, 0.10, 0.30, 0.30, 'Global Real Estate Portfolio'],
        ['Asset_Mix', 'Private Infrastructure', 0.07, 0.00, 0.25, 0.10, 0.25, 0.30, 'Infrastructure and Essential Services'],
        ['Asset_Mix', 'Private Credit', 0.07, 0.00, 0.25, 0.05, 0.20, 0.30, 'Corporate and Private Debt'],
        ['Asset_Mix', 'Cash & Funding', -0.12, -0.50, 0.00, 0.00, 0.00, 0.00, 'Repo and Leverage Funding'],
        ['Global_Limit', 'FX_Net_Exposure', 0.00, 0.00, 0.15, 0.00, 0.00, 0.00, 'Total Non-CAD Net Exposure'],
        ['Global_Limit', 'Funded_Status', 1.11, 1.00, 1.50, 0.00, 0.00, 0.00, 'Assets over Actuarial Liabilities']
    ]
    cols = ['category_type','asset_class','policy_target','range_min','range_max','issuer_limit','sector_limit','target_waci_reduction','description']
    return pd.DataFrame(policies, columns=cols)

# ==========================================
# 4. 执行输出
# ==========================================
if __name__ == "__main__":
    DATA_DIR.mkdir(exist_ok=True)
    # 1. Generate Positions
    df_pos = generate_positions()
    pos_path = DATA_DIR / 'hoopp_positions_sample.csv'
    df_pos.to_csv(pos_path, index=False)
    print(f"✅ 生成成功: {pos_path} ({len(df_pos)} 行)")
    print(f"   - 样本数据日期: {df_pos['timestamp'].unique()}")
    print(f"   - 资产端总额 (最新日): {df_pos[df_pos['timestamp']==df_pos['timestamp'].max()][df_pos['plan_category']=='Asset']['mtm_cad'].sum():,.0f} M")
    print(f"   - 负债端总额 (最新日): {df_pos[df_pos['timestamp']==df_pos['timestamp'].max()][df_pos['plan_category']=='Liability']['mtm_cad'].sum():,.0f} M")

    # 2. Generate Policies
    df_pol = generate_policies()
    pol_path = DATA_DIR / 'policy_limit_management.csv'
    df_pol.to_csv(pol_path, index=False)
    print(f"✅ 生成成功: {pol_path}")