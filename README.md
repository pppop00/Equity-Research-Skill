# Equity Research Skill（权益研究 / 研报生成）

面向 **ChatGPT、Claude、Cursor** 等 AI 助手的「权益研究」技能包：在给出**公司名称**或上传**财报 PDF**（如美股 10-K/10-Q、港股 A 股年报/中报等）后，按固定流程收集数据、做财务与行业分析，并生成 **一份可交互的中文 HTML 研报**（内含 **Sankey 收入流向**、**宏观因子瀑布图**、**波特五力雷达**）。

本仓库与公开地址：**[github.com/pppop00/Equity-Research-Skill](https://github.com/pppop00/Equity-Research-Skill)**

---

## 你能得到什么

- **单一终稿**：`{公司}_Research_CN.html`，可本地用浏览器打开，支持深/浅主题切换。
- **中间产物（JSON）**：财务、宏观、新闻情报、预测瀑布、波特五力等，便于复查或再接其他工具。
- **流程可追溯**：主文档为根目录 **`SKILL.md`**，子任务说明在 **`agents/`**，公式与 β 表在 **`references/`**。

---

## 仓库结构（上传 / 克隆后应看到）

```
Equity-Research-Skill/
├── SKILL.md                 # ★ 主流程：先读这个（Orchestrator）
├── README.md                # 本说明
├── agents/
│   ├── report_writer_cn.md  # ★ 锁定中文 HTML 模板（仅填充 {{占位符}}）
│   ├── report_validator.md # HTML 结构/数据校验清单
│   ├── financial_data_collector.md
│   ├── macro_scanner.md
│   └── news_researcher.md
└── references/
    ├── prediction_factors.md   # 宏观预测：φ、β、公式
    ├── porter_framework.md     # 波特五力写作指引
    ├── financial_metrics.md    # 财务指标定义
    └── report_style_guide_cn.md
```

> **注意**：请不要修改 `agents/report_writer_cn.md` 中的 HTML/CSS/JS 骨架；动态内容只通过占位符填入，详见该文件开头的规则说明。

---

## 使用方式（按你用的产品）

### 通用步骤

1. **克隆本仓库**到本地（或下载 ZIP 解压）：
   ```bash
   git clone https://github.com/pppop00/Equity-Research-Skill.git
   cd Equity-Research-Skill
   ```
2. 在 AI 对话中 **把本仓库加入上下文**（文件夹上传、@ 工作区、或打开本地项目）。
3. 对 AI 说清：请 **严格遵循 `SKILL.md`**，并按照 Phase 5 使用 **`agents/report_writer_cn.md` 的锁定模板** 生成 HTML。
4. 提供 **公司名** 和/或 **财报 PDF**；输出目录建议为 `workspace/{Company}_{Date}/`。

### Cursor

- 将 **`SKILL.md`** 所在目录作为工作区打开，或把本仓库复制到你的项目下。
- 在 **Rules / Skills** 中引用本 skill：让用户规则或项目规则写明「做研报时读取并执行 `SKILL.md`」；需要时也可将 `SKILL.md` 要点复制进 `.cursor/rules`。
- 任务示例：`@SKILL.md 根据我上传的 XXX 公司 2025 中报 PDF 生成中文 HTML 研报`。

### Claude（网页 / Claude Code）

- **Claude Code**：把仓库当作项目打开，可按 `SKILL.md` 描述并行调用多个 agent 文档。
- **Claude.ai**：把 `SKILL.md` + 相关 `agents/`、`references/` 分批贴入或上传为项目知识，再要求按 Phase 顺序执行（无子 agent 时由单次对话顺序完成）。

### ChatGPT（网页 / 桌面）

- 使用 **Advanced Data Analysis（代码解释器）** 或 **附件上传**：打包 `SKILL.md`、`agents/`、`references/` 为 ZIP 上传，或分文件粘贴关键章节。
- 明确指令：**执行 `SKILL.md` 全流程**，最后一步 **只能用 `report_writer_cn.md` 里的 HTML 模板** 填数，不要重写页面结构。

---

## 输入模式（摘自 `SKILL.md`）

| 模式 | 输入 | 说明 |
|------|------|------|
| A | 仅公司名 | 偏网络检索，部分数据为估算，需标注置信度 |
| B | 公司名 + 年报类 PDF | 以文件中的历史期实际值为主，预测结合宏观与公司事件 |
| C | 公司名 + 多期财报 PDF | 数据最完整 |

港股/ A 股 **中报、年报** 同样可作为「文件模式」输入；模板与校验以锁定 HTML 为准。

---

## 许可证与免责

- 本仓库代码与文档以 **[Apache License 2.0](https://github.com/pppop00/Equity-Research-Skill/blob/main/LICENSE)** 授权（与 GitHub 上 `LICENSE` 文件一致）。
- 研报内容为 **模型生成的研究辅助材料**，不构成投资建议；预测模块为 **概率性示意**，使用前请自行核对原始财报与监管披露。

---

## 贡献与反馈

- **Issue**：模板错误、`SKILL.md` 与 agent 描述不一致、或某类产品无法按流程执行，欢迎到 **[Issues](https://github.com/pppop00/Equity-Research-Skill/issues)** 反馈。
- **Pull Request**：改进中文表述、β 表校准说明、或补充「非美股」财报模式的最佳实践，可附简短动机与测试方式。

---

祝使用愉快。若你希望把「锁定模板」单独打成 `.skill` 单文件分发，可在本地将本目录打包为 zip 并按所用客户端的 skill 安装指引命名即可。
