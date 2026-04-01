[English](README.md)

# harness-orchestrator

> Cursor 原生多智能体开发框架 — 在 Cursor 内一条命令完成 计划-构建-评审-发布 全流程。

[![Python](https://img.shields.io/badge/python-%3E%3D3.9-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

AI 编程工具擅长单次任务，但持续开发需要更多：目标跟踪、质量门禁、对抗评审、审计轨迹。Harness 将这些组织成契约驱动的工程闭环，**直接运行在 Cursor IDE 内** — 无需独立编排进程，无需复杂配置。

## 从 3.x 升级

4.0.0 版本完全移除了编排器模式。如果你使用过 `harness run`、`harness auto`、`harness stop` 或 `harness vision`，这些 CLI 命令已不再存在。

**迁移路径：**
- `harness run <需求>` → 在 Cursor IDE 中使用 `/harness-plan <需求>`
- `harness auto` → 在 Cursor IDE 中使用 `/harness-vision`
- `harness vision` → 在 Cursor IDE 中使用 `/harness-vision`
- `harness stop` → 不再需要（Cursor IDE 管理任务生命周期）
- `[drivers]` 配置段 → 被忽略（可安全保留在配置中）
- `workflow.mode` → 已移除（始终为 cursor-native）

你的 `.agents/config.toml` 将继续正常加载 — 未知配置段会被静默忽略。

---

## 快速开始（3 分钟上手）

### 1. 安装 harness

```bash
pip install harness-orchestrator
harness --version
```

<details>
<summary>备选：从源码安装（面向贡献者）</summary>

```bash
git clone https://github.com/arthaszeng/harness-orchestrator.git
cd harness-orchestrator
pip install -e ".[dev]"
```

</details>

### 2. 初始化你的项目

```bash
cd /path/to/your/project
harness init
```

向导会引导你完成配置：项目信息、主干分支、CI 命令和可选的 Memverse 集成。它会将 skills、subagents 和 rules 直接生成到你的 `.cursor/` 目录。

### 3. 在 Cursor 中使用

在 Cursor 中打开项目。你现在拥有 **三个主要入口**，覆盖所有任务体量：

| 技能 | 何时用 | 功能 |
|-------|-------------|------|
| `/harness-brainstorm` | "我有个想法" | 发散探索 → vision → 计划 → 审阅门控 → 自动构建/评审/发布/回顾 |
| `/harness-vision` | "我有个方向" | 澄清 vision → 计划 → 审阅门控 → 自动构建/评审/发布/回顾 |
| `/harness-plan` | "我有个需求" | 细化计划 + 5 角色审查 → 审阅门控 → 自动构建/评审/发布/回顾 |

三个入口采用递归组合（brainstorm ⊃ vision ⊃ plan），共享同一计划审查 → ship 管线。

**工具类技能：**

| 技能 | 功能 |
|-------|-------------|
| `/harness-investigate` | 系统化 bug 调查：复现 → 假设 → 验证 → 最小修复 |
| `/harness-learn` | Memverse 知识管理：存储、检索、更新项目经验 |
| `/harness-retro` | 工程回顾：提交分析、热点检测、趋势追踪 |

**高级技能**（细粒度控制）：

| 技能 | 功能 |
|-------|-------------|
| `/harness-build` | 按契约实现，运行 CI，分流失败，输出结构化构建日志 |
| `/harness-eval` | 5 角色代码评审（架构师 + 产品负责人 + 工程师 + QA + 项目经理） |
| `/harness-ship` | 全自动流水线：测试 → 评审 → 修复 → 提交 → push → PR |
| `/harness-doc-release` | 文档同步：检测代码变更导致的文档过时 |

**现在就试试** — 打开 Cursor 聊天窗口，输入：

```
/harness-plan 给用户注册接口添加输入校验
```

### 更新

```bash
harness update          # 升级到最新版，重装产物，检查配置
harness update --check  # 仅检查是否有新版本
```

---

## 背后发生了什么

```
你输入 /harness-ship "添加功能 X"
  → Rebase 到 main，运行测试
  → 5 角色代码评审（全部并行调度）：
      架构师：      设计 + 安全评审
      产品负责人：  完整性 + 行为正确性
      工程师：      质量 + 性能
      QA：          回归 + 测试（唯一运行 CI 的角色）
      项目经理：    scope + 交付
  → Fix-First：自动修复琐碎问题，重要问题询问你
  → 可二分提交 + push + PR
```

### 统一 5 角色评审系统

同一组 5 个专业角色同时审查**计划**和**代码**，全部并行调度：

| 角色 | 计划审查关注点 | 代码评审关注点 |
|------|---------------|---------------|
| **架构师** | 可行性、模块影响、依赖变更 | 架构合规性、分层、耦合、安全 |
| **产品负责人** | vision 对齐、用户价值、验收标准 | 需求覆盖、行为正确性 |
| **工程师** | 实现可行性、代码复用、技术债 | 代码质量、DRY、模式一致、性能 |
| **QA** | 测试策略、边界值、回归风险 | 测试覆盖、边界场景、CI 健康度 |
| **项目经理** | 任务分解、并行度、scope | scope 漂移、计划完成度、交付风险 |

被 2+ 角色发现的问题标注为**高置信度**。每个角色可通过 `[native.role_models]` 使用不同模型。

### Fix-First 自动修复

评审发现在呈现前先分类：

- **AUTO-FIX** — 高确定性、影响面小、可逆。立即修复并提交。
- **ASK** — 安全发现、行为变更或低置信度。交由你决策。

---

## 配置

项目设置位于 `.agents/config.toml`：

| 键 | 默认值 | 说明 |
|-----|---------|-------------|
| `workflow.max_iterations` | 3 | 每任务最大迭代次数 |
| `workflow.pass_threshold` | 7.0 | 评审通过阈值（满分 10） |
| `workflow.auto_merge` | true | 通过后自动合并分支 |
| `workflow.branch_prefix` | "agent" | 任务分支前缀 |
| `native.gate_full_review_min` | 5 | 完整人工审查的升级分数阈值 |
| `native.gate_summary_confirm_min` | 3 | 摘要确认的升级分数阈值 |
| `native.adversarial_model` | "gpt-4.1" | 跨模型审查器模型 |
| `native.review_gate` | "eng" | 评审门禁严格度（`eng` = 硬门禁，`advisory` = 仅记录） |
| `native.plan_review_gate` | "auto" | 计划审阅门控模式（`human` / `ai` / `auto`） |
| `native.role_models.*` | `{}` | 每角色模型覆盖 |

---

## 命令参考

| 命令 | 说明 |
|---------|-------------|
| `harness init [--name] [--ci] [-y]` | 初始化项目配置（交互式向导） |
| `harness install [--force] [--lang]` | 生成 native 产物（.cursor/ skills、agents、rules） |
| `harness status` | 显示当前进度 |
| `harness update [--check] [--force]` | 自更新，重装产物，检查配置 |
| `harness --version` | 显示版本 |

---

## 仓库布局

```
harness-orchestrator/
├── src/harness/
│   ├── cli.py              # CLI 入口（Typer）
│   ├── commands/            # init、install、update、status
│   ├── core/                # 配置、状态、UI、事件
│   ├── native/              # Cursor 原生模式生成器
│   ├── templates/           # Jinja2 模板（配置 + 原生）
│   └── integrations/        # Git、Memverse
├── tests/                   # 测试套件
└── pyproject.toml
```

---

## 国际化

```bash
harness init --lang zh    # 中文
harness init --lang en    # 英文（默认）
```

---

## 开发

```bash
pip install -e ".[dev]"
pytest
ruff check src/ tests/
ruff format src/ tests/
```

---

## 许可

[MIT](LICENSE)
