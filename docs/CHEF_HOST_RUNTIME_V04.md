# CHEF Host Runtime v0.4 — 第一阶段真实执行接口

## 已实现

新增 `tools.chef_host_runtime`。它把安装配置与真正执行分开：

- `probe`：只检查本机 CLI 是否存在，最多运行 5 秒的 `--version`。不会登录、读 Token、调用模型或花费额度。
- `invoke`：仅在明确传入 `--allow-paid-inference` 后，允许**一次**只读 CLI 调用。当前支持 Codex 原有受控 `codex exec`，以及 Claude Code 的 `claude -p --output-format json --permission-mode plan`。所有请求均禁止编辑、发布、安装依赖和访问密钥。
- Claude 必须返回具有 `type=result`、`is_error=false`、非空 `session_id` 与 `result` 的结构，才标记 `HOST_COMPLETED`。**这只证明父会话有结果，不证明四个原生子 Agent 已启动**。
- Codex 使用现有 JSON 事件解析器及 `read-only` 沙箱；即使有线程 ID，也不能将父会话算作真实子 Agent 验收。
- WorkBuddy / Gemini / OpenCode / Hermes / Generic 目前**没有在本仓库验证过的安全 CLI 调度命令**，因此返回 `UNSUPPORTED`，不会猜测 CLI 参数或执行任意命令。
- 超时、非零退出、无效 JSON、缺失会话证据均返回 `BLOCKED` 或 `FAILED`；输出不回显模型正文、凭证、路径等敏感信息。

## 安全预检（零模型调用）

```bash
python3 -m tools.chef_host_runtime probe --host claude
python3 -m tools.chef_host_runtime probe --host workbuddy
python3 -m tools.chef_host_runtime probe --host codex
```

## 明确授权后，进行一次只读真实调用

```bash
python3 -m tools.chef_host_runtime invoke --host claude --role qa --objective "只读审查当前项目并报告测试证据" --project /path/to/project --allow-paid-inference
```

此命令可能使用 Claude 账户额度，必须由本机用户自主执行。默认不执行，也不在 CI 中使用。Windows 使用 `py -3` 代替 `python3`。

## 尚未通过的门禁

1. WorkBuddy 原生四角色调度：**NOT_VERIFIED**，不能宣传完成。
2. Claude / Gemini / OpenCode 的真实子 Agent：**NOT_VERIFIED**。Claude 当前只实现父 CLI 会话执行，不是原生四角色调度。
3. Hermes 原生 Worker 与规则优先级：**NOT_VERIFIED**。
4. Factory → Studio → QA 的跨宿主持久化任务队列、隔离快照、重试与恢复：**尚未接入**。现有隔离编排器仍由 Codex 执行。
5. Windows / macOS / Linux 外部真实宿主 UAT：**NOT_RUN**。

本阶段不能合并测试模拟结果到真实 Agent 验收证据。后续以 Issue #44 为唯一验收记录，必须拿到真实独立线程/任务 ID、可复核输出及人工批准，才开放通用调度。

[Issue #44](https://github.com/2ndforcecrew/aka-cristi-skills/issues/44) · [安装手册](UNIVERSAL_CHEF_SETUP.md)
