# UI 升级指南 - 如何集成机构级样式

## 快速开始

### 1. 添加文件

把以下文件放到项目根目录：
```
HOOPP_Risk_Demo/
├── ui_components.py      ← 新增：组件库
├── STYLE_GUIDE.md        ← 新增：设计规范文档
├── app.py
├── engine.py
└── tabs/
    └── ...
```

### 2. 修改 app.py

替换原来的 `GLOBAL_CSS`：

```python
# 旧代码
# GLOBAL_CSS = """..."""

# 新代码
from ui_components import GLOBAL_CSS, COLORS, get_chart_layout

# 在 st.set_page_config() 之后立即注入
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
```

### 3. 更新 Tab 文件中的图表

在每个 Tab 文件中导入组件库：

```python
from ui_components import (
    COLORS, 
    CHART_COLORS,
    get_chart_layout,
    render_section_header,
    format_number,
    format_percent,
)
```

更新 Plotly 图表布局：

```python
# 旧代码
fig.update_layout(
    height=300,
    paper_bgcolor='#0f1923',
    ...
)

# 新代码
fig.update_layout(**get_chart_layout(height=300))
```

---

## 组件使用示例

### Section Header

```python
from ui_components import render_section_header

render_section_header("Asset Allocation", "📊")
```

输出：
```
📊 Asset Allocation
────────────────────
```

### 数字格式化

```python
from ui_components import format_number, format_percent

format_number(123700000000, prefix="$")  # → "$123.7B"
format_percent(0.1123)                   # → "11.2%"
```

### 图表颜色

```python
from ui_components import COLORS, CHART_COLORS, ASSET_COLORS

# 单色系渐变 (饼图)
fig = go.Figure(go.Pie(
    values=[...],
    marker_colors=CHART_COLORS,
))

# 资产类别专用色
color = ASSET_COLORS.get('Fixed Income', COLORS['chart_primary'])
```

### 统一图表布局

```python
from ui_components import get_chart_layout

fig = go.Figure(...)
fig.update_layout(**get_chart_layout(height=350, show_legend=True))
st.plotly_chart(fig, use_container_width=True)
```

---

## 颜色快速参考

```python
COLORS = {
    # 背景
    'bg_page': '#0a0e14',      # 页面背景
    'bg_card': '#12171f',      # 卡片背景
    'bg_hover': '#1a2332',     # 悬停背景
    'bg_border': '#262f3d',    # 边框色
    
    # 文字
    'text_primary': '#f0f4f8',   # 主文字 (近白)
    'text_secondary': '#94a3b8', # 副文字 (灰蓝)
    'text_tertiary': '#64748b',  # 三级文字 (暗灰)
    
    # 状态
    'positive': '#10b981',  # 正向 (翠绿)
    'negative': '#ef4444',  # 负向 (亮红)
    'warning': '#f59e0b',   # 警告 (琥珀)
    
    # 强调
    'accent': '#6366f1',           # 主强调 (靛蓝)
    'accent_secondary': '#8b5cf6', # 次强调 (紫)
}
```

---

## 前后对比

### KPI 卡片

| Before | After |
|--------|-------|
| 冰蓝强调色 | 更柔和的靛蓝 |
| 圆角 10px | 圆角 8px (更专业) |
| 单一悬停效果 | 悬停时边框变色 |

### 表格

| Before | After |
|--------|-------|
| 默认样式 | 自定义表头 (大写、小字) |
| 无悬停 | 行悬停高亮 |
| 默认颜色 | 统一的状态色 |

### 图表

| Before | After |
|--------|-------|
| template="plotly_dark" | 自定义透明背景 |
| 默认网格 | 淡化网格线 |
| 随意的图例位置 | 统一的图例样式 |

---

## 逐 Tab 检查清单

### Tab 1: Fund Health
- [ ] 导入 `ui_components`
- [ ] 替换饼图颜色为 `CHART_COLORS`
- [ ] 替换柱状图颜色为 `COLORS['accent']` / `COLORS['warning']`
- [ ] 使用 `get_chart_layout()` 更新图表

### Tab 2: Limit Monitor
- [ ] 替换 `COLOR_OK/WARN/BREACH` 为 `COLORS['positive/warning/negative']`
- [ ] 更新 Gauge 颜色
- [ ] 更新时间序列图布局

### Tab 3: Stress Testing
- [ ] 替换瀑布图颜色
- [ ] 更新 Top Movers 表格样式

### Tab 4: Data Pipeline
- [ ] 替换柱状图颜色
- [ ] 更新质量表状态色

### Tab 5: AI Copilot
- [ ] 更新 Smart Summary 卡片样式
- [ ] 统一按钮颜色

---

## 高级：添加自定义组件

如果需要更多组件，在 `ui_components.py` 中添加：

```python
def render_metric_row(metrics: list):
    """
    渲染一行 KPI 卡片
    metrics: [{'label': 'xxx', 'value': 'xxx', 'delta': 'xxx'}, ...]
    """
    cols = st.columns(len(metrics))
    for col, m in zip(cols, metrics):
        with col:
            st.metric(
                label=m['label'],
                value=m['value'],
                delta=m.get('delta'),
            )
```

使用：
```python
render_metric_row([
    {'label': 'Funded Status', 'value': '111.2%', 'delta': '+0.3%'},
    {'label': 'Surplus', 'value': '$13.2B', 'delta': '+$0.5B'},
])
```

---

## 常见问题

### Q: 样式没生效？
确保 `st.markdown(GLOBAL_CSS, ...)` 在 `st.set_page_config()` 之后立即调用。

### Q: 图表背景不透明？
检查是否使用了 `get_chart_layout()`，它会设置 `paper_bgcolor='rgba(0,0,0,0)'`。

### Q: 数字没有对齐？
CSS 已设置 `font-variant-numeric: tabular-nums`，如果还不对齐，检查是否有内联样式覆盖。

---

## 下一步

1. **先跑起来** — 确保新样式正常加载
2. **逐 Tab 更新** — 按上面的检查清单逐个改
3. **微调** — 根据实际效果调整间距、颜色
4. **截图对比** — 保存前后对比图，面试时展示改进过程
