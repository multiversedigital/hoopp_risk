
# 🛡️ HOOPP Risk Navigator 1.0 - 需求规格说明书 (Consolidated)

## 1. 项目愿景 (Vision)

将 HOOPP 静态的《2024 年度报告》转化为一个交互式的、基于 Python 的决策支持系统。通过 **负债感知投资 (LAI)** 框架，实时监控 111% 资金充足率，展现从数据链路自动化到 AI 风险洞察的全栈能力。

## 2. 核心业务逻辑 (Core Business Logic)

* **北极星指标**：资金充足率 (Funded Status)。
* **计算模型**：

* **风险哲学**：不仅仅关注资产波动，更关注资产与负债的**匹配偏差**（Mismatch Risk）。

---

## 3. 功能模块详细设计 (Functional Specs)

### Tab 1: Total Fund Health (全基金监控)

* **业务指标**：
* Net Assets: **$123.7 Billion** (2024 Actual).
* Funded Status: **111%**.
* Policy Asset Mix: 对比实际配置与政策基准（Public vs Private）。


* **UI 组件**：KPI 卡片 + 交互式饼图。

### Tab 2: Liability-Driven Scenarios (负债驱动压力测试)

* **业务指标**：利率 (Interest Rate) 与 通胀 (Inflation) 的敏感性。
* **交互逻辑**：
* 用户通过滑动条调节宏观因子。
* 系统调用 `src/risk_analysis.py` 实时重新计算资产与负债的现值，展示充足率的动态漂移。


* **公式参考**：展示资产与负债的久期对冲效果（Duration Matching）。

### Tab 3: IP&G Compliance (合规与限额监控)

* **监控项 (Detailed Limits)**：
* **单一发行人限制**：任何单一头寸 。
* **外汇风险限制**：未对冲敞口 。
* **信用等级监控**：投资级以下资产的比例。


* **UI 组件**：自动化扫描状态栏（✅ Pass / 🚩 Breach）。

### Tab 4: Automation Pipeline (自动化流水线)

* **解决痛点**：通过技术手段终结琐碎的 Excel 对账工作。
* **功能点**：
* **Data Integrity Check**：自动检测数据源中的空值或异常。
* **One-click Reconciliation**：一键执行跨系统（如 SimCorp 到 SQL）的数据一致性校验。



### Tab 5: AI-First Risk Advisor (AI 风险顾问)

* **愿景**：Genesis Alpha 的 AI 化重构展示。
* **功能点**：
* **Smart Summary**：利用 LLM 自动生成针对本周风险波动的文字解读。
* **Natural Language Query**：支持通过对话框提问（例如：“哪项资产对 VaR 的贡献最大？”）。



---

## 4. 技术栈与实施 (Technical Implementation)

* **前端**：Streamlit (部署于 Streamlit Community Cloud)。
* **后端**：Python (利用 `Multi_Instruments_Portfolio/src/` 核心算法)。
* **数据**：初期使用 `hoopp_data_generator.py` 生成模拟数据，后期对接 SQL/API。
* **安全性**：使用 Streamlit Secrets 管理 API 凭证。

---

### 💡 建议的操作步骤：

1. **保存文件**：在你本地项目根目录下新建 `REQUIREMENTS.md`，把上面的内容贴进去。
2. **在 UI 中展示**：在你的 `hoopp_demo.py` 里，你可以加一个侧边栏选项叫做 "Documentation"，代码只需要两行：
```python
with open("REQUIREMENTS.md", "r", encoding="utf-8") as f:
    st.markdown(f.read())

```


这样 Navid 看到这个 Tab 时，会觉得你的项目管理极其规范。

**如果你对这个文档满意，下一步我们可以开始编写 `Hoopp_dashboard/summary_tab.py` 的第一个原型代码了，需要我开始吗？**