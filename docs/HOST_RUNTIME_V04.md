# CHEF Runtime V0.4 · 真实跨宿主调用（开发候选）

> **状态：已实现实验性 CLI 运行适配器与隔离式 Dual-Engine 接线；CI 仅使用虚构 JSON 事件和 Git 沙盒，不等于在 WorkBuddy / Claude / Gemini / OpenCode / Hermes 的真实账号上通过验证。** 目前不作为稳定版功能宣传，也不自动升级已发布的 `v1.0.0-beta.3`。

## 从文件安装走向真实执行

之前 `tools.universal_chef` 安装 CHEF 规则、四角色和四 Skills，但并不运行模型。V0.4 增加 `tools.host_runtime`：基于宿主公开 CLI，以独立进程提交**真实的、需要用户明确授权**的只读研究/审阅任务，并严格解析结构化会话结果。

| 宿主 | 调用方式 | 默认安全行为 | 证据 |
| --- | --- | --- | --- |
| **WorkBuddy / CodeBuddy CLI** | `codebuddy --print ... --output-format json` | 默认拒绝启动：官方 Headless 对受权限控制的工具操作要求 `-y`；须额外显式 `--allow-host-permissions` | JSON 结果须含独立 `session_id` |
| **Claude Code** | `claude --print ... --output-format json --permission-mode plan` | 使用宿主 Plan 模式 | JSON 结果含 `session_id` 与最终响应 |
| **Gemini CLI** | `gemini --prompt ... --output-format stream-json --approval-mode plan` | 使用宿主实验性 Plan 模式；仍需隔离和实机验证 | JSONL `init.session_id` + 完成事件 |
| **OpenCode** | `opencode run --agent plan --format json --archived ...` | 使用宿主 Plan 角色；不保证本项目四角色都作为原生子 Agent 加载 | JSONL 结果与会话 ID |
| **Hermes Agent** | `hermes chat --oneshot --query-file - --format stream-json` | 默认拒绝：可能继承用户配置的 terminal/web 工具和 Gateway 会话，须额外显式 `--allow-host-permissions` | JSONL `result.session_id`、`exit_code=0` 与非空结果 |

**任何 `COMPLETED` 仅代表该次有结构化结果、可归属到一个宿主会话，不代表创建了原生父子 Agent 线程。** 程序永远输出 `native_subagent: NOT_VERIFIED`，不会把 JSON 模拟数据或 Agent 口头陈述当作真实验收。

### 1. 无费用只预览

先从已经审查的仓库进入一个**干净、独立的测试项目**：

~~~bash
python3 -m tools.host_runtime --host claude --role qa --workspace /absolute/test-project --prompt "只读审查 README 的错误处理"
~~~

这会返回命令预览并将 Prompt 隐去，**不启动 CLI、不消耗额度、不要求登录**。

### 2. 经明确授权后进行真实 CLI 调用

~~~bash
python3 -m tools.host_runtime --host claude --role qa --workspace /absolute/test-project --prompt "只读审查 README 的错误处理" --allow-live
~~~

仅在具备宿主有效账户、权限和额度后执行。脚本可能实际产生模型计费。对 WorkBuddy 和 Hermes，还须另加 `--allow-host-permissions`，该参数意味着**用户明确接受宿主配置可能授予的更大工具权限**；本项目无法确保它等价于操作系统只读沙盒，正式仓库和私人数据环境**不要启用**。

### 3. 用两个不同的宿主完成 Factory → Studio → QA

可以继续复用原有 `tools.chef_dual_engine` 的 **Git 隔离克隆 + SQLite 事件与尝试记录 + 显式恢复 + 独立 QA**。Factory 仍使用 Codex 授权的隔离工作区；Studio 和 QA 可用指定的不同 CLI：

~~~bash
python3 -m tools.chef_dual_engine \
  --kind hybrid \
  --prompt "在测试项目修复小问题，然后审查用户体验" \
  --workspace /absolute/clean-committed-test-project \
  --db /absolute/private-state/chef.sqlite3 \
  --studio-host claude \
  --qa-host gemini \
  --allow-live \
  --timeout 180
~~~

**注意：** 这是需要真实 Codex + Claude + Gemini 授权及额度的实验命令。`--allow-live` 是明确的调用许可，**不代表对修改、付费、发布和高风险工具行为的一揽子许可**。既有 Codex Factory 负责修改 *隔离快照*，Studio/QA 使用宿主只读/Plan 配置审阅；实际工具权限边界依赖宿主，并非本项目提供的安全沙盒。若某个阶段的输出不可归属、没有唯一会话 ID、修改了只读工作区、格式不符或超时，整个任务将 `BLOCKED`，不会继续发版或自动合并。

不同宿主的 session ID 不证明 native parent/child 关系，所以报告中特别标注 `independent_sequential_host_sessions_NOT_native_subagents`。原有全 Codex 默认行为与断点续跑指纹保持兼容。输出的 SQLite、日志、补丁和私有工作区可能包含项目内容，请存放在原项目之外，保护好文件访问权限。

### 4. 测试范围

- `tests/test_host_runtime.py`：真实宿主 JSON/JSONL 格式的**合成 fixture**，验证异常处理、独立 ID、预览脱敏、缺少 CLI、显式额度/权限授权。
- `tests/test_chef_cross_host.py`：真实本地 Git 创建/克隆/SQLite 记录，宿主执行部分用 Mock 代替，验证两个不同的后端、拒绝重复身份及失败时停止。
- GitHub Actions Windows/macOS/Ubuntu：运行以上单元和本地 Git 流程，不使用私人 Codex/WorkBuddy 等账户，也不执行付费模型。

### 仍未完成（Issue #44）

- WorkBuddy/CodeBuddy、Claude、Gemini、OpenCode、Hermes 的**真实账号端到端** CLI 执行样本、版本矩阵与 native Subagent 父子事件审核。
- 更强的真正 OS 沙盒和最小权限 Profile；Plan、allowedTools 与 Prompt 不等于完整文件系统安全隔离。
- 跨平台完整 Agent Orchestration：登录诊断、动态任务分发、UI 状态、自动授权/权限管理和真正的并行执行。
- Hermes/WorkBuddy 非交互式调用需要的高风险权限方案的独立安全审查。

## 官方 CLI 文档

- [CodeBuddy / WorkBuddy Headless](https://www.workbuddy.ai/docs/cli/headless)
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code/cli-usage)
- [Gemini CLI Headless](https://geminicli.com/docs/cli/headless/)
- [OpenCode CLI](https://opencode.ai/docs/cli/commands)
- [Hermes CLI](https://hermes-agent.nousresearch.com/docs/reference/cli-commands/)

