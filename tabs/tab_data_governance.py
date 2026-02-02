"""
tab_data_governance.py — Data Quality & Governance Console

展示数据治理与质量监控的核心理念：
- Data Pipeline Status (Hop-by-Hop)
- CTA Framework: Completeness, Timeliness, Accuracy
- Day-over-Day Reconciliation

注：当前为静态展示版本，用于面试演示数据治理思维
"""

import streamlit as st
import pandas as pd
from ui_components import (
    COLORS,
    render_section_header,
)


def render(ctx: dict):
    """渲染 Data Governance Tab"""
    
    # ─────────────────────────────────────────────────────────
    # 顶部说明 Note
    # ─────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="
            background-color: {COLORS['bg_hover']};
            border: 1px solid {COLORS['bg_border']};
            border-left: 4px solid {COLORS['accent']};
            border-radius: 8px;
            padding: 16px 20px;
            margin-bottom: 24px;
        ">
            <div style="display: flex; align-items: flex-start; gap: 10px;">
                <span style="font-size: 1.1rem;">💡</span>
                <div style="font-size: 0.9rem; color: {COLORS['text_secondary']}; line-height: 1.6;">
                    <strong style="color: {COLORS['text_primary']};">Conceptual Design</strong><br>
                    This page demonstrates the <strong>data governance mindset</strong> and framework design — 
                    not a live implementation against the synthetic dataset. 
                    In production, each check would connect to actual pipeline metadata and quality rule engines.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # ─────────────────────────────────────────────────────────
    # Pipeline Status Banner
    # ─────────────────────────────────────────────────────────
    render_section_header("Data Pipeline Status", "🔄")
    
    # Pipeline 四个阶段
    col1, col2, col3, col4 = st.columns(4)
    
    pipeline_stages = [
        {"name": "Upstream Feeds", "icon": "📥", "status": "🟢", "time": "06:15 AM", "records": "1,250 rec", "desc": "Bloomberg, Custodian, Internal"},
        {"name": "Risk Lake", "icon": "🗄️", "status": "🟢", "time": "06:25 AM", "records": "1,250 rec", "desc": "Validation, Cleansing, Storage"},
        {"name": "Analysis Engine", "icon": "⚙️", "status": "🟢", "time": "06:40 AM", "records": "250 pos", "desc": "Aggregation, Risk Calculation"},
        {"name": "Risk Reporting", "icon": "📊", "status": "🟢", "time": "06:45 AM", "records": "250 pos", "desc": "Dashboards, Reports, Alerts"},
    ]
    
    for col, stage in zip([col1, col2, col3, col4], pipeline_stages):
        with col:
            st.markdown(
                f"""
                <div style="
                    background: linear-gradient(135deg, {COLORS['bg_card']} 0%, {COLORS['bg_hover']} 100%);
                    border: 2px solid {COLORS['positive']};
                    border-radius: 12px;
                    padding: 20px 16px;
                    text-align: center;
                    min-height: 200px;
                ">
                    <div style="font-size: 2rem; margin-bottom: 8px;">{stage['icon']}</div>
                    <div style="font-size: 1.1rem; font-weight: 700; color: {COLORS['text_primary']}; margin-bottom: 4px;">
                        {stage['name']}
                    </div>
                    <div style="font-size: 1.5rem; margin: 8px 0;">{stage['status']}</div>
                    <div style="font-size: 0.9rem; color: {COLORS['positive']}; font-weight: 600;">
                        {stage['time']}
                    </div>
                    <div style="font-size: 0.85rem; color: {COLORS['text_secondary']}; margin-top: 4px;">
                        {stage['records']}
                    </div>
                    <div style="font-size: 0.75rem; color: {COLORS['text_tertiary']}; margin-top: 8px; line-height: 1.4;">
                        {stage['desc']}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    
    # 箭头连接（用 CSS 或简单文字表示数据流）
    st.markdown(
        f"""
        <div style="text-align: center; margin: -10px 0 20px 0; color: {COLORS['text_tertiary']}; font-size: 0.85rem;">
            ━━━━━━━━━━━━━ Data flows left to right with Hop-by-Hop record reconciliation ━━━━━━━━━━━━━
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────
    # CTA Health Scorecard
    # ─────────────────────────────────────────────────────────
    render_section_header("CTA Health Scorecard", "🎯")
    
    col_c, col_t, col_a = st.columns(3)
    
    # Completeness
    with col_c:
        st.markdown(
            f"""
            <div style="
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['bg_border']};
                border-left: 4px solid {COLORS['positive']};
                border-radius: 8px;
                padding: 20px;
            ">
                <div style="color: {COLORS['text_tertiary']}; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                    Completeness
                </div>
                <div style="color: {COLORS['text_secondary']}; font-size: 0.8rem; margin-bottom: 12px;">
                    Record Integrity
                </div>
                <div style="font-size: 2.5rem; font-weight: 700; color: {COLORS['positive']};">
                    100%
                </div>
                <div style="
                    background-color: {COLORS['bg_hover']};
                    border-radius: 4px;
                    height: 8px;
                    margin: 12px 0;
                    overflow: hidden;
                ">
                    <div style="background-color: {COLORS['positive']}; height: 100%; width: 100%;"></div>
                </div>
                <div style="font-size: 0.85rem; color: {COLORS['text_secondary']}; line-height: 1.6;">
                    ✓ Feed → Lake: 1,250 rec<br>
                    ✓ Lake → Engine: 1,250 rec<br>
                    ✓ Engine → UI: 250 pos<br>
                    <span style="color: {COLORS['positive']}; font-weight: 600;">No record loss detected</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    # Timeliness
    with col_t:
        st.markdown(
            f"""
            <div style="
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['bg_border']};
                border-left: 4px solid {COLORS['positive']};
                border-radius: 8px;
                padding: 20px;
            ">
                <div style="color: {COLORS['text_tertiary']}; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                    Timeliness
                </div>
                <div style="color: {COLORS['text_secondary']}; font-size: 0.8rem; margin-bottom: 12px;">
                    SLA Compliance
                </div>
                <div style="font-size: 2.5rem; font-weight: 700; color: {COLORS['positive']};">
                    On-Time
                </div>
                <div style="
                    background-color: {COLORS['bg_hover']};
                    border-radius: 4px;
                    height: 8px;
                    margin: 12px 0;
                    overflow: hidden;
                ">
                    <div style="background-color: {COLORS['positive']}; height: 100%; width: 92%;"></div>
                </div>
                <div style="font-size: 0.85rem; color: {COLORS['text_secondary']}; line-height: 1.6;">
                    SLA Target: <strong>7:00 AM</strong><br>
                    Actual: <strong style="color: {COLORS['positive']};">6:45 AM</strong><br>
                    Buffer: 15 min<br>
                    <span style="color: {COLORS['positive']}; font-weight: 600;">Processing: 30 min total</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    # Accuracy
    with col_a:
        st.markdown(
            f"""
            <div style="
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['bg_border']};
                border-left: 4px solid {COLORS['positive']};
                border-radius: 8px;
                padding: 20px;
            ">
                <div style="color: {COLORS['text_tertiary']}; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">
                    Accuracy
                </div>
                <div style="color: {COLORS['text_secondary']}; font-size: 0.8rem; margin-bottom: 12px;">
                    Quality Rules
                </div>
                <div style="font-size: 2.5rem; font-weight: 700; color: {COLORS['positive']};">
                    5/5 Pass
                </div>
                <div style="
                    background-color: {COLORS['bg_hover']};
                    border-radius: 4px;
                    height: 8px;
                    margin: 12px 0;
                    overflow: hidden;
                ">
                    <div style="background-color: {COLORS['positive']}; height: 100%; width: 100%;"></div>
                </div>
                <div style="font-size: 0.85rem; color: {COLORS['text_secondary']}; line-height: 1.6;">
                    ✓ No missing MTM<br>
                    ✓ No missing Notional<br>
                    ✓ DoD variance in range<br>
                    <span style="color: {COLORS['positive']}; font-weight: 600;">0 anomalies detected</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    
    st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────
    # Detail Tables: Completeness + Accuracy Rules
    # ─────────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)
    
    with col_left:
        render_section_header("Completeness: Hop-by-Hop Recon", "📋")
        
        completeness_data = pd.DataFrame({
            "Hop": ["Upstream Feeds", "Risk Lake", "Analysis Engine", "UI Layer"],
            "Expected": ["1,250", "1,250", "250 (aggregated)", "250"],
            "Actual": ["1,250", "1,250", "250", "250"],
            "Delta": [0, 0, 0, 0],
            "Status": ["🟢 OK", "🟢 OK", "🟢 OK", "🟢 OK"],
        })
        
        st.dataframe(
            completeness_data,
            use_container_width=True,
            hide_index=True,
            height=200,
        )
    
    with col_right:
        render_section_header("Accuracy: Quality Rules", "🔍")
        
        accuracy_data = pd.DataFrame({
            "Rule": ["Missing MTM", "Missing Notional", "Missing Duration", "DoD Δ > 5% (AUM)", "DoD Δ > 2% (Funded)"],
            "Checked": [250, 250, 250, 1, 1],
            "Failed": [0, 0, 0, 0, 0],
            "Result": ["Pass (0 nulls)", "Pass (0 nulls)", "Pass (0 nulls)", "Pass (1.2%)", "Pass (0.3%)"],
            "Status": ["🟢", "🟢", "🟢", "🟢", "🟢"],
        })
        
        st.dataframe(
            accuracy_data,
            use_container_width=True,
            hide_index=True,
            height=200,
        )
    
    st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────
    # Day-over-Day Reconciliation
    # ─────────────────────────────────────────────────────────
    render_section_header("Day-over-Day Reconciliation", "📊")
    
    st.markdown(
        f"""
        <div style="font-size: 0.85rem; color: {COLORS['text_secondary']}; margin-bottom: 12px;">
            Threshold: <span style="color: #f59e0b;">🟡 Amber > 2%</span> · <span style="color: {COLORS['negative']};">🔴 Red > 5%</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    dod_data = pd.DataFrame({
        "Risk Metric": ["Total Assets", "Total Liabilities", "Surplus", "Funded Status", "Asset Duration", "Duration Gap", "FX Exposure"],
        "T-1 (Yesterday)": ["$124.2B", "$109.8B", "$14.4B", "113.1%", "4.3 yrs", "-8.4 yrs", "12.8%"],
        "T (Today)": ["$125.7B", "$110.8B", "$14.9B", "113.4%", "4.4 yrs", "-8.5 yrs", "13.0%"],
        "Delta": ["+$1.5B", "+$1.0B", "+$0.5B", "+0.3%", "+0.1 yrs", "-0.1 yrs", "+0.2%"],
        "Δ %": ["+1.21%", "+0.91%", "+3.47%", "+0.27%", "+2.33%", "-1.19%", "+1.56%"],
        "Status": ["🟢 OK", "🟢 OK", "🟡 Review", "🟢 OK", "🟡 Review", "🟢 OK", "🟢 OK"],
    })
    
    st.dataframe(
        dod_data,
        use_container_width=True,
        hide_index=True,
        height=300,
    )
    
    st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────
    # AI Variance Commentary
    # ─────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="
            background-color: {COLORS['bg_card']};
            border: 1px solid {COLORS['bg_border']};
            border-left: 4px solid {COLORS['accent']};
            border-radius: 8px;
            padding: 20px;
        ">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                <span style="font-size: 1.2rem;">🤖</span>
                <span style="font-size: 1rem; font-weight: 600; color: {COLORS['text_primary']};">
                    AI Variance Commentary
                </span>
            </div>
            <div style="font-size: 0.95rem; color: {COLORS['text_secondary']}; line-height: 1.8;">
                <p style="margin-bottom: 8px;">
                    <span style="color: {COLORS['positive']};">✓</span> 
                    <strong>Asset growth (+1.21%)</strong> aligns with market movement (S&P 500 +0.9%, TSX +1.1%).
                </p>
                <p style="margin-bottom: 8px;">
                    <span style="color: {COLORS['positive']};">✓</span> 
                    <strong>Liability increase (+0.91%)</strong> consistent with rate drop (-3bps in 10Y CAD).
                </p>
                <p style="margin-bottom: 8px;">
                    <span style="color: #f59e0b;">⚠️</span> 
                    <strong>Surplus Δ (+3.47%)</strong> flagged for review — driven by asset outperformance vs liabilities. Within acceptable range.
                </p>
                <p style="margin-bottom: 8px;">
                    <span style="color: {COLORS['positive']};">✓</span> 
                    <strong>Duration Gap</strong> stable at -8.5 yrs — no rebalancing activity detected.
                </p>
                <div style="
                    margin-top: 16px;
                    padding-top: 12px;
                    border-top: 1px solid {COLORS['bg_border']};
                    color: {COLORS['text_primary']};
                    font-weight: 600;
                ">
                    📋 Conclusion: All variances explainable by market movements. No data quality issues suspected.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    st.markdown("<div style='height: 24px'></div>", unsafe_allow_html=True)
    
    # ─────────────────────────────────────────────────────────
    # Footer: Methodology Note
    # ─────────────────────────────────────────────────────────
    st.markdown(
        f"""
        <div style="
            background-color: {COLORS['bg_hover']};
            border-radius: 8px;
            padding: 16px 20px;
            margin-top: 8px;
        ">
            <div style="display: flex; align-items: flex-start; gap: 10px;">
                <span style="font-size: 1rem;">ℹ️</span>
                <div style="font-size: 0.85rem; color: {COLORS['text_secondary']}; line-height: 1.6;">
                    <strong style="color: {COLORS['text_primary']};">CTA Framework</strong><br>
                    <strong>Completeness</strong>: Hop-by-hop record count reconciliation ensures no data loss during pipeline processing.<br>
                    <strong>Timeliness</strong>: SLA monitoring tracks data freshness and processing duration.<br>
                    <strong>Accuracy</strong>: Quality rules validate key attributes (MTM, Notional) and flag unexplained day-over-day variances.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )