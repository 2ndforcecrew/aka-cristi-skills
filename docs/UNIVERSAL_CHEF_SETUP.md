# Universal CHEF · 跨宿主 Agent 适配与安装说明

**目标：让 CHEF Core 不依赖 Codex 专属 TOML，在不同 Agent 宿主上安装符合其规范的规则、31 个 Skills（6 原生 + 25 vendored）和执行角色。**

这份说明依据真实源代码与各平台公开文档。**“文件可安装”不代表“已经真实启动四个 Agent”；跨平台配置与运行时接入分开验收。**

## 分层架构

| 层级 | 当前实现 | 能力限制 |
| --- | --- | --- |
| CHEF Core Rules | 共用 `templates/AGENTS.global.md` | 尊重平台内置和用户既有规则，不能取代系统指令 |
| Skills | 同一套 31 个 Skills（6 原生 + 25 vendored），经目标平台原生 Skills 路径安装 | 是否被加载、触发由宿主控制 |
| Role Profiles | 从 `agents/*.toml` 的职责语义生成各宿主原生 Markdown | WorkBuddy、Claude、Gemini、OpenCode 可发现配置，但运行时需单独验证 |
| Agent Coordination | 原生角色说明写明 CHEF 分工与交接，提供通用 Handoff 任务契约 | 不能凭文件定义保证宿主实际派发 |
| Dual-Engine | Factory/Studio/QA 通用 JSON 交接计划 + 现有 Codex CLI 隔离运行时 | 自动执行的跨厂商 Host Runner **尚未实现** |
| Runtime Acceptance | Codex 已有真实 Skill / 四角色验收器 | 非 Codex 宿主真实线程验收仍需开发 |

## 官方支持的配置映射

| 宿主 | 项目规则 | 四角色定义 | 31 Skills |
| --- | --- | --- | --- |
| **Codex** | 原有 Codex 用户 `AGENTS.md` | `~/.codex/agents/*.toml` | `~/.agents/skills` |
| **WorkBuddy / CodeBuddy** | `.codebuddy/rules/aka-chef.md` | `.codebuddy/agents/aka_*.md` | `.codebuddy/skills/*/SKILL.md` |
| **Claude Code** | `.claude/rules/aka-chef.md` | `.claude/agents/aka_*.md` | `.claude/skills/*/SKILL.md` |
| **Gemini CLI** | `GEMINI.md` 的 CHEF 受管理区块 | `.gemini/agents/aka_*.md` | `.gemini/skills/*/SKILL.md` |
| **OpenCode** | `AGENTS.md` 的 CHEF 受管理区块 | `.opencode/agents/aka_*.md` | `.opencode/skills/*/SKILL.md` |
| **Hermes Agent** | 项目 `AGENTS.md` 受管理区块 | `.aka-chef/role-templates/`（只是交接说明；**不是 Hermes 原生子 Agent**） | 需要额外指定用户 `~/.hermes/skills` 目标 |
| **通用 Agent** | 项目 `AGENTS.md` CHEF 受管理区块 | `.aka-chef/role-templates/`（手动使用） | `.agents/skills/*/SKILL.md`（兼容性依宿主而定） |

**Hermes 注意：** 它的项目上下文文件存在优先级。如果项目已有优先级更高的 `.hermes.md`，`AGENTS.md` 可能不会成为实际加载的项目指令。安装器不会修改 `SOUL.md`，因为它是 Hermes 的身份配置，而非普通项目规则。

### 复制一条命令安装（仓库内）

**默认只预览。** 参数 `--interactive` 会展示计划，输入 `INSTALL` 后才写入。现有不受管理的同名规则或角色、被用户修改的受管理文件会导致 `CONFLICT`，拒绝覆盖。

~~~bash
# WorkBuddy · 用户全局规则 + Roles + Skills（所有项目可用）
python3 -m tools.full_setup --host workbuddy --scope user --interactive

# WorkBuddy · 仅一个项目
python3 -m tools.full_setup --host workbuddy --scope project --project /path/to/project --interactive

# Claude / Gemini / OpenCode · 用户全局配置
python3 -m tools.full_setup --host claude --scope user --interactive
python3 -m tools.full_setup --host gemini --scope user --interactive
python3 -m tools.full_setup --host opencode --scope user --interactive

# Gemini / OpenCode 等 · 只对指定项目生效
python3 -m tools.full_setup --host gemini --project /path/to/project --interactive

# Hermes · 项目规则及角色交接模板（不假装是原生角色）
python3 -m tools.universal_chef install --host hermes --project /path/to/project --interactive

# Hermes · 另行授权安装到真实用户 Skills 目录
python3 -m tools.universal_chef install --host hermes --project /path/to/project --hermes-skills-root ~/.hermes/skills --interactive
~~~

Windows PowerShell 使用 `py -3` 代替 `python3`，将项目路径替换为本地真实路径。`--scope user` 只在 WorkBuddy、Claude、Gemini、OpenCode 等具有核实过用户规则/Skills 目录的平台实现；**不会强行在 Hermes 或未知平台的全局身份配置里写规则**。

### 校验与撤销

~~~bash
python3 -m tools.universal_chef verify --host workbuddy --scope user
python3 -m tools.universal_chef uninstall --host workbuddy --scope user --interactive
~~~

撤销先检查本项目管理的配置内容是否仍与记录一致：受管理规则区块只移除该区块，其他用户规则保留；已管理 Skills 由原 Skill 安装器归档。若出现冲突则拒绝删除。某些意外文件系统异常可能需要根据现场备份恢复；不称整体操作已实现数据库式原子事务。

### 为什么没有全自动调用所有厂商？

不同平台的 **规则文件 ≠ 原生 Agent 任务调度 API**。我们只能直接保证将允许安装的文件放到正确位置、校验 SHA-256 并保存状态：

- WorkBuddy：官方支持项目 `.codebuddy/rules`、`agents`、`skills`；最终的 Expert/Agent 真正启动需要在 WorkBuddy 会话里进行独立测试。
- Claude / Gemini / OpenCode：提供自定义 Agent 和 Skills 的公开格式，但仍需要宿主用户权限、登录以及真正的任务委派。
- Hermes：公开技能路径与项目规则可用，**没有经过验证的本项目四角色原生 Host Adapter**。
- Codex：已有原生 TOML + CLI 实验与四角色测试脚本，但非所有机器都经过真实验收。
- ChatGPT：无法通过本地 Markdown 直接修改 ChatGPT 的系统规则或 Skills；需要独立用户授权的官方集成。

## Dual-Engine · 通用任务契约

即使宿主不支持 Codex CLI，也可以生成不执行模型的 Factory / Studio / QA 交接计划：

~~~bash
python3 -m tools.chef_handoff --host workbuddy --kind hybrid --objective "修复前端功能并审查用户体验" --project /path/to/project
~~~

以上命令只展示 JSON，不写文件。要保存交接合同，需要**单独选一个安全私有目录**：

~~~bash
python3 -m tools.chef_handoff --host workbuddy --kind hybrid --objective "修复前端功能并审查用户体验" --project /path/to/project --out /path/to/private-state --apply
~~~

保存的 `chef-handoff-<task-id>.json` 说明角色顺序、期望职责、输入/输出和验收边界，并且所有执行状态初始均为 `NOT_RUN`。它**不启动模型**。需要在真实宿主会话内读取此任务文件、委派实际 Agent，并取得可验证的角色/线程证据。

既有 `tools.chef_dual_engine` 包含独立 Git 克隆、SQLite、有限重试、恢复和独立 QA，但其 **自动执行器仍使用 Codex CLI**；需要下一阶段逐厂商实现和验证 Runner。

## 完整状态

- **已实现 / 经过工程测试：** 各宿主原生规则/角色/Skills 文件生成、冲突预检、确认安装、状态记录、文件完整性验证、受管理文件撤销；通用 Dual-Engine Handoff 生成器。
- **需用户实机测试：** WorkBuddy 等宿主是否自动加载规则/Skills/四角色，及真实子 Agent 是否响应。
- **尚未实现：** 一套无需用户登录或授权、可以自动控制任何厂商 Agent 的统一后台调度、跨厂商模型账户与实时协作。
- **原有功能继续保留：** Codex CHEF 安装器、Dual-Engine Codex CLI 运行时、Personal AI Workspace、GUI、Skill 进化辅助工具等，均不被此变更替换。

### 参考文档

- [WorkBuddy 项目配置](https://www.codebuddy.cn/docs/workbuddy/From-Beginner-to-Expert-Guide/Function-Description/Project)
- [Claude Code 子 Agent](https://claude.com/blog/subagents-in-claude-code)
- [Gemini CLI Skills](https://geminicli.com/docs/cli/skills/) · [Gemini 子 Agent](https://github.com/google-gemini/gemini-cli/blob/main/docs/core/subagents.md)
- [OpenCode Agents](https://opencode.ai/docs/agents) · [Skills](https://opencode.ai/docs/skills/)
- [Hermes 配置](https://hermes-agent.nousresearch.com/docs/user-guide/configuration/) · [Skills](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills/)

