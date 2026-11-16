# CHEF Runtime v0.4 — 真实 CLI 调用与安全验收

> **阶段：CLI 只读运行时已实现，非 Codex 平台的原生子 Agent 验收仍为 NOT_VERIFIED。** WorkBuddy 桌面端与 **CodeBuddy Code CLI** 是不同宿主：下面的 `codebuddy -p` 适配只代表 CodeBuddy Code CLI 的无头模式，不代表已控制 WorkBuddy 桌面应用。

## 本轮补齐的关键差距

上一版本 v1.0.0-beta.3 能把 CHEF Rules、Skills 和四个角色文件装进多个 Agent 的目录，但**不能实际派发任务**。

现在增加 `tools.chef_runtime_dispatch`：支持 `--kind hybrid` 的 Factory → Studio → QA 三阶段只读会话，及 `--kind four-roles` 的 Research → Coding → QA → Automation 四角色只读会话。当系统中存在 **CodeBuddy Code CLI** 或 **Claude Code CLI**，且用户单独确认使用模型额度时，CHEF 会创建三或四个独立的模型会话并分别调用：

```text
用户明确授权调用 / 同意使用模型额度
        │
        ▼
CHEF Runtime Dispatcher
        │
        ▼
Factory ──真实只读 CLI 调用──► 结果摘要
        │
        ▼
Studio  ──全新 CLI 会话────────► 独立评审
        │
        ▼
QA      ──全新 CLI 会话────────► 独立复核
        │
        ▼
记录：host / role / session_id / reply SHA256 / status
        │
        ▼
REVIEW_REQUIRED（由人独立验收，不自动发布）
```

它运行的是**分开的 CLI 主会话**，不是宿主原生子 Agent 父子线程。各平台真正的原生 Role Delegation / WorkBuddy Expert Team / Factory 写代码仍需要专用 Host Runner 和实机证据。

### 安全默认值

- **默认只读预览：** 无 `--allow-quota` 就不会调用任何模型，也不会尝试登录或更新账号。
- **工具权限最小化：** CodeBuddy 使用 `--tools "" --strict-mcp-config`，Claude 使用 `--tools "" --permission-mode plan`。不调用命令执行工具，不绕过宿主授权，不写入生产代码。
- **真实会话识别：** 必须在真实 CLI JSON 中见到有效 `session_id`、非空回复与正常退出；各角色的会话 ID 不得重复。文本里自称“Agent 已完成”不足以通过。
- **错误停止：** 任一角色失败、退出码异常、JSON 不完整、缺失会话 ID、超时或重复线程 ID，流程即停止并报告 `BLOCKED`，不会继续执行后续 QA。
- **证据脱敏：** 仅保留角色、会话 ID、模型回复字节数和 SHA-256 摘要；不向报告写入模型原始回复、私人路径或 Token。
- **限时与终止：** 每个调用 1–600 秒，超时终止进程树；Windows 与 POSIX 使用不同终止策略。
- **模型与会话成本：** 此流程启动真实、可能收费或消耗额度的模型会话，用户必须主动授权；工具测试并不自动消费额度。
- **真实产品边界：** 模型或宿主本身可能保存会话、访问云端；禁用工具不等于模型未接触用户提供的提示词。不要把隐私资料作为目标文本。

## 开始使用

在已检出的仓库目录，先做**只读环境检测**：

```bash
python3 -m tools.chef_runtime_dispatch inspect --host codebuddy
python3 -m tools.chef_runtime_dispatch inspect --host claude
```

仅看任务计划（**不会调用模型**）：

```bash
python3 -m tools.chef_runtime_dispatch run --host codebuddy --kind hybrid --project . --objective "评估用户旅程与修复方案"
```

**在专门的测试目录中，并明确同意消耗模型额度**时才能启动真实 CLI：

```bash
python3 -m tools.chef_runtime_dispatch run --host codebuddy --kind hybrid --project . --objective "对 CHEF 的工程与用户体验协作方法进行只读评审" --allow-quota
```

Claude Code 换成 `--host claude`。Windows PowerShell 把 `python3` 换为 `py -3`。

**四角色独立会话验证（不是原生子 Agent）：**

```bash
python3 -m tools.chef_runtime_dispatch run --host codebuddy --kind four-roles --project . --objective "核查 Research/Coding/QA/Automation 的只读分工" --allow-quota
```


**从通用 CHEF 一键安装后自动引导验收：**

```bash
python3 -m tools.full_setup --host workbuddy --scope user --interactive --test-agents
```

本命令先让用户批准配置写入，然后再次单独询问是否使用额度测试四段真实 CLI 会话；`--test-agents` 不会默认自动调用或绕过额度确认。

## 验收范围及状态

| 验收内容 | 当前证据/状态 |
| --- | --- |
| CLI 命令生成、授权门禁、会话 ID 校验、异常停止、敏感信息脱敏 | 离线/CI 测试 |
| CLI 已安装、登录可用、响应非空并能提供真实 Session ID | 需要用户环境实际运行 |
| CodeBuddy Code CLI → Factory / Studio / QA 连续只读主会话 | 代码路径已实现，实机仍待验收 |
| WorkBuddy Desktop Expert Team 子 Agent / 子线程 | **NOT_VERIFIED** |
| Claude Code 原生子 Agent 父子线程 | **NOT_VERIFIED** |
| Gemini / OpenCode / Hermes 独立真实运行时 | **NOT_IMPLEMENTED（本轮）** |
| 有权限进行真实代码修改的 Factory + 独立 QA | **NOT_IMPLEMENTED（本轮）** |
| Dual-Engine Codex V0.3 隔离 Git + SQLite 的原有运行时 | 完整保留，无覆盖、未改动 |

**为什么不是直接打开 WorkBuddy 全权限运行？** CodeBuddy Code 官方 Headless 文档指出，要让无头模式调用需要权限的工具，常须使用 `-y / --dangerously-skip-permissions`；我们不会为追求一键自动化而默认启用这种高风险配置。等实际隔离执行、权限审查与端到端验收完成后，才能开放写入式 Factory。参见[官方 Headless 文档](https://www.codebuddy.cn/docs/cli/headless)、[CLI Reference](https://www.codebuddy.cn/docs/cli/cli-reference) 与 [Claude Code CLI 参考](https://docs.anthropic.com/en/docs/claude-code/cli-usage)。

## 与路线图的关系

[Issue #44](https://github.com/2ndforcecrew/aka-cristi-skills/issues/44) 中的完整跨宿主 Runtime 还没有全部实现。本版本只是把**真正的代码执行接口与安全验收数据层**建立起来。

接下来应优先验证真实 WorkBuddy/CodeBuddy 与 Claude 环境、优化输出格式兼容、接入原生角色委派证据和受控 Factory 隔离写入。不能用 CI Mock 输出冒充这些验收通过。
