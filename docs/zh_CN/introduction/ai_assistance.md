# AI 辅助开发

`rhosocial-activerecord` 设计为 **AI-Native**（AI 原生）—— 从底层架构开始就是为 AI 代码智能体和编辑器无缝协作而构建的。

## 为什么是 AI-Native？

以下几项设计决策使这个项目特别适合 AI 辅助：

- **显式类型注解** —— 完整的 Pydantic v2 集成帮助 AI 理解模型结构
- **透明化 SQL** —— 每个查询都有 `.to_sql()` 方法，AI 可以在执行前验证生成的 SQL
- **清晰架构** —— Expression-Dialect 分离使代码库易于 AI 理解
- **内置上下文** —— 项目自带 AI 专用配置

## 内置 AI 配置

当你克隆本仓库时，以下 AI 配置会自动可用：

```
python-activerecord/
├── CLAUDE.md                    # Claude Code: 项目级指令
├── AGENTS.md                    # Codex / 通用智能体: 项目上下文
├── .claude/
│   ├── skills/                  # Claude Code: 12 个专业技能文件
│   │   ├── user-activerecord-pattern/SKILL.md
│   │   ├── user-backend-development/SKILL.md
│   │   ├── user-enterprise-features/SKILL.md
│   │   ├── user-getting-started/SKILL.md
│   │   ├── user-modeling-guide/SKILL.md
│   │   ├── user-performance-tuning/SKILL.md
│   │   ├── user-query-advanced/SKILL.md
│   │   ├── user-relationships/SKILL.md
│   │   ├── user-testing-guide/SKILL.md
│   │   ├── user-troubleshooting/SKILL.md
│   │   ├── dev-sync-async-parity/SKILL.md
│   │   ├── dev-expression-dialect/SKILL.md
│   │   ├── dev-protocol-design/SKILL.md
│   │   └── dev-testing-contributor/SKILL.md
│   └── commands/                # Claude Code: 13 个斜杠命令
├── .opencode/
│   ├── commands/                # OpenCode: 13 个斜杠命令
│   └── hints.yml               # OpenCode: 关键字触发的建议
└── docs/
    └── LLM_CONTEXT.md          # 任何 LLM 的结构化参考
```

### 支持的工具

| 工具 | 启动方式 | 配置文件 |
|------|----------|----------|
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | `claude` | `CLAUDE.md`, `.claude/skills/`, `.claude/commands/` |
| [OpenCode](https://github.com/opencode-ai/opencode) | `opencode` | `.opencode/commands/`, `.opencode/hints.yml` |
| [Codex](https://github.com/openai/codex) | `codex` | `AGENTS.md` |
| [Cursor](https://cursor.com) | 打开文件夹 | `CLAUDE.md`, `AGENTS.md` 通过上下文 |
| [Windsurf](https://windsurf.com) | 打开文件夹 | `CLAUDE.md`, `AGENTS.md` 通过上下文 |

## 与 AI 快速开始

### 1. 生成模型

描述你的业务领域，让 AI 生成模型：

> 💡 **试试这个提示词：**
> ```
> 创建一个博客系统，包含 User、Post 和 Comment 模型。
> 用户可以有多篇文章，文章可以有多条评论。
> 所有模型使用时间戳和软删除功能。
> ```

### 2. 构建复杂查询

> 💡 **试试这个提示词：**
> ```
> 写一个查询，找出文章数量最多的前 5 位作者，
> 排除已软删除的文章，然后展示生成的 SQL。
> ```

### 3. 解释错误

> 💡 **试试这个提示词：**
> ```
> 我遇到 "No backend configured" 错误。出了什么问题，如何修复？
> ```

## 常见的 AI 任务

### 应用开发者

| 任务 | 示例提示词 |
|------|-----------|
| **生成模型** | "创建一个包含客户信息、订单行和时间戳的 Order 模型" |
| **构建查询** | "找出最近 30 天注册且至少有 3 个订单的所有用户" |
| **添加关系** | "在 Post 和 Tag 之间建立多对多关系" |
| **编写测试** | "为 User 模型编写测试：保存、查询过滤和软删除" |
| **调试问题** | "解释这个错误：FieldProxy not found on User.c" |
| **检查 SQL** | "展示这个查询生成的 SQL" |

### 贡献者

| 任务 | 示例提示词 |
|------|-----------|
| **新后端** | "@backend-development 参考 SQLite 实现创建一个 PostgreSQL 后端" |
| **添加表达式** | "@expression-dialect 添加 JSON 路径表达式支持" |
| **检查对等** | "@sync-async-parity 检查是否所有方法都有异步对应版本" |
| **运行测试** | "@testing-guide 运行查询测试并解释失败原因" |

## 工具专属技巧

### Claude Code

显式引用技能以获取项目特定知识：

```
@user-getting-started       # 快速开始指导
@user-modeling-guide        # 模型定义模式
@user-query-advanced        # 复杂查询构建
@dev-sync-async-parity      # API 一致性规则
@dev-expression-dialect     # 表达式系统内部实现
```

使用斜杠命令执行常见任务：

```
/gen:model User             # 生成 User 模型
/test-feature query         # 运行查询测试
/check-sync-async           # 验证 API 对等
```

### OpenCode

使用命名空间命令：

**开发命令：**
- `/test` — 运行所有测试
- `/test:feature query` — 运行特定功能测试
- `/lint` / `/lint:fix` — 代码风格检查
- `/type-check` — 使用 mypy 进行类型检查

**代码生成：**
- `/gen:model` — 生成 ActiveRecord 模型
- `/gen:query` — 生成预设查询方法
- `/gen:relation` — 生成模型关系
- `/validate:model` — 验证模型配置

**框架开发：**
- `/new-feature` — 搭建新功能
- `/new-backend` — 创建新数据库后端
- `/check-sync-async` — 验证同步异步对等

### Cursor 和 Windsurf

这些编辑器受益于项目的类型注解和文档字符串。要获得更深入的上下文：

1. 将 `docs/LLM_CONTEXT.md` 或 `AGENTS.md` 添加到编辑器的上下文/规则中
2. 向 AI 寻求帮助时引用这些文件以获得项目特定模式

## 最佳实践

**具体明确。** "创建一个带邮箱验证、可选年龄、时间戳和软删除的 User 模型" 比 "创建一个 User 模型" 更好。

**要求查看 `.to_sql()`。** 始终请求生成的 SQL 以验证正确性：
> "编写这个查询，然后展示它为 SQLite 和 PostgreSQL 生成的 SQL。"

**引用上下文。** 如果 AI 生成了不正确的代码，请指向正确的技能：
> "检查 @sync-async-parity — 这个方法需要一个异步对应版本。"

**用于审计。** AI 智能体可以审查代码：
- 类型注解完整性
- 同步异步对等违规
- 缺失的测试
- `ToSQLProtocol` 合规性

## 下一步

- **项目新手？** 查看 [快速入门](../getting_started/README.md)
- **想要详细示例？** 查看 [快速开始指南](../getting_started/quick_start.md)
- **需要 LLM 上下文？** 将 [`../LLM_CONTEXT.md`](../LLM_CONTEXT.md) 提供给你的 AI 助手

---

> 🤖 **在本文档中，你会看到 💡 AI 提示词标记出现在复杂概念旁边。遇到不理解的概念时，随时可以向你的 AI 助手提问。**
