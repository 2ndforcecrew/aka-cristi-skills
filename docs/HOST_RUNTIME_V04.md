# CHEF Host Runtime V0.4 — 宿主会话执行（实验性）

> **区别于 `Universal CHEF Beta.3`：** Beta.3 安装规则、Skills 与角色定义；V0.4 增加真正启动已登录宿主 CLI 的能力，按 Factory → Studio → QA 顺序交接。**独立 CLI 会话不等于原生父子 Agent 派发。**

## 官方 Headless CLI 对照

| 宿主 | 最小权限调用 | 可观测结果 | 子 Agent 调用 |
| --- | --- | --- | --- |
| Claude Code | `claude -p ... --permission-mode plan --output-format json` | 返回 `result/session_id` | NOT_VERIFIED |
| Gemini CLI | `gemini -p ... --approval-mode plan --output-format stream-json` | `init.session_id` 与最终 `result` | NOT_VERIFIED |
| OpenCode | `opencode run --agent plan --format json ...` | JSONL `sessionID/step_finish` | NOT_VERIFIED |
| WorkBuddy | 目前没有经过本项目验证的非交互 CLI 调用协议 | NOT_RUN | NOT_RUN |
| Hermes | 官方有 `hermes chat --oneshot`，但还没证明安全限制及会话身份关联 | NOT_RUN | NOT_RUN |

启动任何模型请求之前，用户必须在自己电脑完成目标宿主安装与登录、确认其权限及额度。Plan 模式只是在宿主内部限制写入，不是操作系统级沙盒；宿主自带 MCP 或其他插件权限必须另外审查。禁止将本模块直接用在含私人客户资料的生产项目。

来源：[Claude CLI](https://docs.anthropic.com/en/docs/claude-code/cli-usage) · [Gemini Headless](https://geminicli.com/docs/cli/headless/) · [Gemini Plan](https://geminicli.com/docs/cli/plan-mode/) · [OpenCode CLI](https://opencode.ai/docs/cli/commands)

## 01 / 单次宿主调用

使用不带授权参数的命令只报告缺少调用同意，并**不会使用推理额度**：

~~~bash
python3 -m tools.host_runtime --host claude --role qa \
  --prompt "检查这个测试项目" --workspace /absolute/trusted/project
~~~

明确授权以后，增加 `--authorize-inference`：

~~~bash
python3 -m tools.host_runtime --host claude --role qa \
  --prompt "审查测试项目并说明风险" \
  --workspace /absolute/trusted/project --timeout 300 \
  --authorize-inference
~~~

Windows 使用 `py -3` 替换 `python3`。适用于已安装并登录 Claude CLI 的电脑；其他宿主可用 `--host gemini` 或 `--host opencode`。

返回 `COMPLETED` 要求**退出码正常、明确完成事件、非空输出、真实宿主 session ID**。仅文字声称「已经派发 Agent」绝不被视为有原生子 Agent 的证据。

## 02 / Dual-Engine Factory / Studio / QA 真正会话

~~~bash
python3 -m tools.chef_dual_engine \
  --host claude --kind hybrid \
  --prompt "提出修复建议并审查用户体验" \
  --workspace /absolute/trusted/clean-git-project \
  --db /absolute/private-state/chef.sqlite3 \
  --timeout 300 --authorize-inference
~~~

**代码现已接入原有 Git 隔离、SQLite、超时、显式恢复框架。**

- 每阶段在独立 Git 克隆运行，并记录来源 SHA、任务 ID、宿主 session ID、执行结果及验收证据。
- Factory 在非 Codex 宿主仅能提供**只读补丁建议**，不能自动对源码应用修复。
- 任何非 Codex 阶段出现文件修改，均视为失败并停止执行；原始项目保持不变。
- 缺少宿主 session ID、任务结束事件或有效回复时，状态保持 `BLOCKED`，不能伪造成协作成功。
- 使用 `--resume <task-id>` 仅能在版本、宿主、目标和来源提交都一致时恢复；每个角色最多三次记录的尝试。
- 最终返回 `REVIEW_REQUIRED` 仍需要独立人工审查；并不代表真实四子 Agent 激活或生产上线许可。

## 03 / 验收边界

| 已开发 | 仍需真实环境验收 |
| --- | --- |
| 三个受支持宿主的官方 CLI 参数与事件解析 | 在用户自己的已登录宿主中真实付费调用 |
| 默认拒绝未授权模型请求 | 宿主额外 MCP/工具权限核对 |
| 超时终止、限量的可验证结果 | 原生父子 Agent 线程映射 |
| Git 隔离、SQLite 事件记录、失败后重试与 QA | WorkBuddy 和 Hermes 的安全无界面适配 |
| Windows / macOS / Ubuntu 的模拟协议和离线回归 | 多宿主外部用户实机 E2E |

有关完整真实调用验收继续跟踪 [Issue #44](https://github.com/2ndforcecrew/aka-cristi-skills/issues/44)。本版本为开发中的 V0.4；**不代表已经发布下一版 Beta 或拥有真实宿主测试 PASS**。
