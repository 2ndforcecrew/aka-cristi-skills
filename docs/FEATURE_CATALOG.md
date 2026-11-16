# AKA.CRISTI Skills · 完整功能目录

> 本文以仓库 `main` 的实际代码为准，不把规划、静态配置、CI 模拟测试与真实 Agent 联动混为一谈。主页入口：[README](../README.md)。公开稳定版本仍未发布；当前公开测试版是 [v1.0.0-beta.2](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.2)。

## 如何理解功能状态

- **已实现（本地/工程验证）**：对应代码已存在，具备单元、隔离或 CI 测试；不自动意味着真实用户环境已通过验收。
- **实验性（真实宿主尚需验收）**：具有可运行入口或有限真实运行证据，但没有完成全场景或外部用户验收。
- **部分实现（适配/检测）**：有发现、预览、文件安装等局部能力，没有完整任务运行能力。
- **规划中**：已有设计、接口或路线图，但相关端到端产品功能尚未交付。

## 01｜CHEF Orchestrator：总指挥与工作规则

**状态：本地安装已实现；自动跨 Agent 调度尚未完全实现。**

- 核心：将任务按 `Inspect → Plan → Build → Test → Review → Deliver` 处理，先检查环境和已有工作，再决定工具、执行和验收。
- 规则：安装受管理的 `AGENTS.md` 区块。保留已有自定义内容，检测冲突并提供受控操作、备份和验证。
- 技能：`chef-orchestrator` 负责目标拆解、工具分工、证据交接、错误恢复以及可复用经验总结。
- 限制：`AGENTS.md` 是工作指引，不是后台持续运行的 Agent 进程；只有宿主真的调用工具或角色时才会执行。

源码：[规则安装器](../tools/chef_global_rules.py) · [模板](../templates/AGENTS.global.md) · [CHEF Skill](../skills/chef-orchestrator/SKILL.md)

## 02｜Dual-Engine V0.3：Factory × Studio 双引擎

**状态：实验性 Python 运行时已实现，具有隔离与离线测试；真实 Codex 端到端交付未通过。**

这是项目重要的高级模块，**不是只有 PDF 思路**。它允许针对任务选择三种执行模式：

| 模式 | 重点 | 实际行为 |
| --- | --- | --- |
| `factory` | 工程执行 | 针对指定工作区生成实现/测试候选，由独立 QA 复核 |
| `studio` | 创意与用户体验 | 对用户旅程、视觉质量、产品意图作审阅，结果交给 QA |
| `hybrid` | 先工程、再创意体验 | Factory → Studio → 独立 QA 的顺序交接 |

### 已写入运行时的机制

1. **任务路由**：根据 `--kind` 选择 Factory、Studio 或 Hybrid；并非同一任务中无限并行启动 Agent。
2. **隔离执行**：从干净的、已提交的 Git 仓库建立独立本地快照/克隆，避免多个角色争抢原始文件；要求用户先保存未提交修改。
3. **Codex 运行适配**：通过本机已授权的 `codex exec` 调用真实 CLI。Factory 的有条件修改与 Studio/QA 的只读检查严格区分。
4. **结构化交接**：为角色规定任务目标、输入输出、权限、超时、重试和禁止操作，保留实际结果而非口头声称。
5. **持久化记录**：使用 SQLite `tasks`、`events`、`attempts` 记录任务、状态、调用结果；独立文件锁限制重复执行。
6. **错误恢复**：记录中断、限制尝试次数；`--resume` 仅在来源版本和快照一致时恢复，不无条件重复执行。
7. **独立 QA**：最后再调用单独 QA 检查候选成果；流程返回 `REVIEW_REQUIRED`，**不会自称 QA 已通过或自动合并 PR**。
8. **安全边界**：私有日志、独立工作目录、有限超时、受控进程终止；不会自动发布或替用户更改生产仓库。

### 使用示例（实验性；会调用实际 Codex 和消耗额度）

~~~bash
python3 -m tools.chef_dual_engine --kind hybrid \
  --prompt "分析并修复一个小问题，随后检查用户体验" \
  --workspace /absolute/project --db /absolute/private-state/chef.sqlite3 --timeout 300
~~~

`--workspace` 必须是可信且干净的 Git 仓库，`--db` 放在源码目录之外。该运行时**不是 `tools.full_setup` 安装后自动启动的后台服务**。代码中有本地脚本宿主 E2E、隔离、恢复、SQLite 与回归测试，但此前真实 Codex 云端尝试遇到 HTTP451 / WebSocket / Token 刷新故障，未拿到完整 Factory→Studio→QA 交付证据；因此不能称为生产级自治引擎。

源码：[Dual-Engine](../tools/chef_dual_engine.py) · [架构路线图](CHEF_DUAL_ENGINE_V03_ROADMAP.md) · [运行机制与测试记录](CHEF_DUAL_ENGINE_V03_RUNTIME.md) · [真实尝试记录](evidence/chef-dual-engine-v03-live-attempt.json)

## 03｜四个原生 Codex Agent 角色

**状态：原生 TOML 配置与受控安装已实现；部分真实只读联动有证据，外部环境需要复验。**

| 角色名称 | 配置名 | 使用场景 |
| --- | --- | --- |
| Research | `aka_research` | 阅读代码/资料、查证信息、说明不确定性 |
| Coding | `aka_coding` | 在明确授权范围内修复、开发、运行测试 |
| QA | `aka_qa` | 独立复核功能、回归、质量和证据 |
| Automation | `aka_automation` | 设计 API/MCP 自动化、超时、重试和恢复 |

安装位置：`$CODEX_HOME/agents/` 或 `~/.codex/agents/`。这些配置由 Codex 宿主读取，不是四个独立付费 AI 服务。真正调用需要正确的 Codex CLI、登录、可用模型、权限、Host Subagents 能力及新会话。

### 真实调用验收

- 文件安装可返回 `FILES_VERIFIED`；这只是文件一致性。
- `tools.verify_four_agents` 会尝试真实 `codex exec --json` 并核对父子线程、角色和回复，可能消耗额度。
- 仓库记录过 Codex CLI 0.169.0 的限定只读四角色协作，旧自动解析器对此返回了 `INCONCLUSIVE`，经独立跨源证据复核为限定案例通过；不等于任意用户机器都能复现。

源码：[四角色 TOML](../agents) · [安装器](../tools/codex_subagents.py) · [四 Agent 验收](FOUR_AGENT_RUNTIME_ACCEPTANCE.md) · [现有证据](UNIVERSAL_VERIFICATION_2026-11-16.md)

## 04｜四个方法论 Skills

**状态：`SKILL.md` 与本地安装工具已实现。**

| 模块 | 核心流程 | 典型用途 |
| --- | --- | --- |
| [CHEF Orchestrator](../skills/chef-orchestrator/SKILL.md) | 明确目标、拆解、分工、验收 | 复杂任务总协调 |
| [Verified Change Loop](../skills/verified-change-loop/SKILL.md) | 复现 → 最小修复 → 重测 → 独立验证 | Bug、CI、环境故障 |
| [Feature Journey Map](../skills/feature-journey-map/SKILL.md) | 从入口到结果检查用户旅程与异常流程 | 产品、网站和工具体验 |
| [Skill Evaluation Gate](../skills/skill-evaluation-gate/SKILL.md) | 用行为、质量、安全和性能证据评估 | Skill 发布与升级评审 |

这些是四种可复用的工作方法，**不是自动运行的后台流程**。它们能否被 Agent 正确发现、读取并使用，还需由相应宿主进行真实测试。

## 05｜统一安装入口与 Windows GUI

**状态：已实现并有 Windows/macOS/Linux CI。**

- **`tools.full_setup`（`main` 新入口）**：环境与冲突预览、明确同意后安装 CHEF 规则、4 Skills、4 Codex 角色；检查 Codex 登录；可选启用 Workspace 设置和真实四 Agent 验收，额外授权另询问。
- **`tools.quick_install`（`v1.0.0-beta.2` 已包含）**：核心配置统一预览、交互同意和文件校验，不调用真实模型。
- **Windows GUI**：Tk 桌面窗口和冻结 EXE，支持预览、同意、进度、取消、文件验证和受保护回滚；二进制附有 GitHub 来源证明，**无 Authenticode 证书签名**。
- **受保护事务安装**：`tools.install_transaction` 保存快照/日志，按受管理文件归属检查回滚，不允许盲目覆盖私人规则。
- **Windows 引导程序**：`install.ps1` 对可信本地来源、Pinned ZIP 与来源信息进行严谨检查，不是无需验证的远程 `curl | bash`。

**注意：** 用户需要预先有 Git、Python 3.11+；没有 Codex CLI/登录或必要授权时，统一入口不能凭空补齐账户访问；跨厂商自动授权未实现。

源码：[一条命令完整向导](../tools/full_setup.py) · [核心安装](../tools/quick_install.py) · [Windows GUI](../tools/gui_installer.py) · [安装事务](../tools/install_transaction.py) · [图形说明](WINDOWS_GUI.md)

## 06｜Personal AI Workspace：私人规则与 Skills 工作区

**状态：CLI/GUI、Device Flow、同步与隔离测试已实现；真实 OAuth/外部账号建仓未验收。**

- **首次启动引导**：GitHub Setup Wizard / Sync Center，用户可跳过，之后重新设置。
- **GitHub Device Flow**：使用官方浏览器与一次性 User Code；凭据预期保存在 OS 原生安全存储（Windows Credential Manager / macOS Keychain / Linux Secret Service），不写到普通设置文件。
- **私人仓库**：支持用户自行授权创建/复用默认名 `my-agent-workspace`，必须明确确认，拒绝不匹配的账号或公开仓库。
- **公开白名单初始化**：拟写入公开版 CHEF 规则、4 角色、4 Skills 与元数据，不自动上传用户私人 `AGENTS.md` 或客户数据。
- **版本检查与手动拉取**：按远端固定 revision 预览差异，SHA-256/manifest 校验，手动 `Sync Now`，不是自动 push 或实时双向同步。
- **备份、恢复与审计**：同步前创建本地备份，冲突停止，受控 Restore，锁避免不同进程同时改写，简化审计日志。
- **ChatGPT 连接指导**：提供独立官方授权指引，**不能替用户验证 ChatGPT 账户已经 Connected**。

### 使用前仍缺什么

发布者需要注册并提供 GitHub OAuth App 的公共 Client ID，用户需要自己的授权和可用系统凭据库。当前未取得真实 OAuth、独立用户创建私人仓库及跨机器同步的完整验收证据；因此只将它列为**实验功能**。

源码：[Workspace 控制器](../tools/personal_workspace.py) · [一键编排](../tools/workspace_oneclick.py) · [差异/备份/同步](../tools/workspace_sync.py) · [GUI](../tools/workspace_gui.py) · [详细说明](PERSONAL_AI_WORKSPACE.md)

## 07｜Universal Skills：创建、验证、生命周期和维护

**状态：本地辅助工具已实现；自动晋升/淘汰发布尚未实现。**

- **Skill Validator** `tools.skill_validator`：检查 `SKILL.md` 结构、frontmatter、名称、文件类型、危险链接/路径等；只读，不执行脚本。
- **Skill Builder** `tools.skill_builder`：生成最小标准 Skill 模板；先预览、`--apply` 才创建目录；拒绝覆盖已有 Skill。
- **Skill Lifecycle** `tools.skill_lifecycle`：生成确定性的 SHA-256 清单、结构检查、版本/维护/退休建议；**不会自动更新、卸载或宣布某 Skill 淘汰**。
- **Skill Evidence** `tools.skill_evidence`：校验测试/评估账本结构与证据引用；验证记录格式不等于真的执行了对应测试。
- **安全安装器** `tools.skill_installer`：预览、安装、校验、卸载、已管理状态及冲突保护。

**Skill Evolution 的完整闭环仍在开发**：自动识别重复成功→生成候选→独立评估→发布/退役，不会因为这些辅助模块存在就自动运行。

源码：[Validator](../tools/skill_validator.py) · [Builder](../tools/skill_builder.py) · [Lifecycle](../tools/skill_lifecycle.py) · [Evidence](../tools/skill_evidence.py) · [设计说明](UNIVERSAL_SKILL_ARCHITECTURE.md)

## 08｜跨厂商 Agent 适配器

**状态：发现/检测和有限文件适配已实现；真实跨厂商编排未实现。**

- **Agent Registry/Discovery** `tools.agent_adapters`：只读发现 Codex、Claude Code、Gemini CLI、OpenCode、Hermes 或自定义 Agent 的候选能力，不能仅因检测到安装文件就判定可调度。
- **Host Adapter** `tools.host_adapters`：统一 inspect、preview、install、verify、uninstall 的契约。Codex 使用用户级 Skills，Claude Code 的**项目级 Skills 文件**可受控安装；Hermes/ChatGPT 当前不执行安装或真实调用。
- **模型/API/MCP**：不自动生成密钥，不继承独立第三方账号权限；各宿主需要单独完成连接与验收。

源码：[Agent Discovery](../tools/agent_adapters.py) · [Host Adapters](../tools/host_adapters.py) · [能力矩阵](HOST_CAPABILITY_MATRIX.md) · [适配契约](UNIVERSAL_AGENT_ADAPTERS.md)

## 09｜真实调用验证与诊断

**状态：验证程序与离线回归已实现；实际验证需要登录宿主和模型额度。**

- **Skill 激活验证** `tools.verify_codex_activation`：用临时只读案例检查 Codex 是否实际读取指定 Skill、观察案例、正确报告未知状态。
- **四角色验收** `tools.verify_four_agents`：核对真实调用、独立子线程、准确角色和完成结果，避免只靠 Agent 自称。
- **调用异常诊断** `tools.diagnose_four_agents`：针对运行输出/元数据提供诊断，不将不完整或模拟记录冒充真实通过。
- **受限探针隔离** `tools.codex_probe_isolation`：为真实测试建立更窄的本地临时环境和证据；不能替代操作系统级安全边界。

源码：[Skill 激活验收](../tools/verify_codex_activation.py) · [四 Agent 验收](../tools/verify_four_agents.py) · [调用诊断](../tools/diagnose_four_agents.py) · [验收标准](AGENT_ACTIVATION_VERIFICATION.md)

## 10｜测试、候选包来源证明和风险控制

**状态：具备测试与候选发布流程；不是商业代码签名或全生态安全认证。**

- **跨平台 CI**：Windows、macOS、Linux 执行单元/回归、安装器、工作空间及打包检查；Mock 和合成数据明确标记。
- **GitHub Release**：`v1.0.0-beta.2` 已公开附带源码 ZIP、Windows EXE、SHA-256 manifest、GitHub OIDC / Sigstore 来源证明；可验证精确发布来源。
- **Windows Job Object** `tools.aka_windows_job_runner`：控制超时或取消后的进程树生命周期，**不是沙盒或权限隔离**。
- **Release verifier** `tools.verify_release`：检查来源包结构与固定 SHA/来源信息。
- **Acceptance Gate** `tools.acceptance_gate`：审查证据记录是否齐全，永远不自动宣布真实独立验收 PASS。
- **Scan Report Gate** `tools.scan_report_gate`：可选静态扫描报告预检。旧 SkillSpector `DO_NOT_INSTALL` 记录属于历史基线，不是当前 Beta 的实时风险判定；但也不能未经核查就宣称所有发现皆为误报。

源码：[验证器](../tools/verify_release.py) · [签发流程](../.github/workflows/beta-release.yml) · [安全说明](SECURITY_REVIEW_2026-11-15.md) · [Beta 验收](CODEX_V1_RELEASE_ACCEPTANCE.md)

## 11｜成长日志、路线图和项目管理

**状态：已有 Markdown 成长记录、开发路线及证据文件；独立公网项目仪表盘不包含在此仓库内。**

- [成长日志](GROWTH_JOURNAL_2026-11-16.md) · [私人工作区成长记录](GROWTH_PERSONAL_WORKSPACE_2026-11-16.md)
- [ROADMAP](../ROADMAP.md) · [Dual-Engine 路线](CHEF_DUAL_ENGINE_V03_ROADMAP.md)
- [外部用户测试说明](EXTERNAL_UAT.md) · [正式证据记录](SIX_GATE_STATUS.md)

计划中的 Factory/Studio 实时看板、Agent Collaboration OS 全生态跨宿主调度、自维护自淘汰 Skill、稳定版多设备同步等功能，**不能仅因被列在路线图就算已部署**。

---

## 新增｜Universal CHEF 跨 Agent 平台安装（Beta.3）

**状态：原生配置转换、预览、文件校验与受管理撤销已实现；各厂商真实 Agent 线程联动仍需独立实测。**

- WorkBuddy / CodeBuddy：项目 `.codebuddy/rules`、`agents`、`skills`；或用户全局 `~/.codebuddy/`，不覆盖内置 WorkBuddy 规则。
- Claude Code：项目/用户级 `.claude/rules`、`agents`、`skills`。
- Gemini CLI：`GEMINI.md` / `~/.gemini/GEMINI.md`、`.gemini/agents`、`.gemini/skills`。
- OpenCode：`AGENTS.md` / `~/.config/opencode/AGENTS.md`、`.opencode/agents`、`.opencode/skills`。
- Hermes：项目 `AGENTS.md`，可选实际用户 `~/.hermes/skills`；四角色模板仅供交接，尚不是 Hermes 原生子 Agent。
- 通用 Agent：`AGENTS.md` 与 `.agents/skills`，是否真实加载由具体宿主决定。

项目级、用户级需要用户显式选择 `--scope`；保护既有规则和角色，不在未经确认时修改权限/账号。Dual-Engine 的通用 Factory/Studio/QA 交接 JSON 可以安全生成和检查，但非 Codex 宿主的自动 CLI Runner **未实现**。原有 Codex 运行时保留不变。

[跨宿主安装/验收手册](UNIVERSAL_CHEF_SETUP.md) · [安装源码](../tools/universal_chef.py) · [交接源码](../tools/chef_handoff.py)


## 研发中｜CHEF Runtime V0.4 真正的跨宿主执行入口

**状态：已实现并正在审查的代码候选，不属于已发布的 beta.3。** `tools.host_runtime` 为 CodeBuddy/WorkBuddy CLI、Claude、Gemini、OpenCode、Hermes 提供需要明确授权的 CLI 调用探针，要求独立会话标识、结构化结束证据与清楚的权限界限。Dual-Engine 的 Studio 和 QA 可在不同 Git 克隆内通过这些 CLI 工作；Factory 仍沿用 Codex 实验性隔离执行。**没有实际用户宿主账号的 Live E2E，CI 的 Mock 结果不计入真实激活验证。**

[Runtime V0.4 完整说明](HOST_RUNTIME_V04.md) · [运行时代码](../tools/host_runtime.py) · [回归测试](../tests/test_chef_cross_host.py)

## 当前安装究竟会部署哪些模块？

| 模块 | 运行 `tools.full_setup` 后的行为 |
| --- | --- |
| CHEF `AGENTS.md` | 用户确认后安装，检查完整性 |
| 四个 Skills | 用户确认后安装，检查完整性 |
| 四个 Codex TOML 角色 | 用户确认后安装，检查完整性 |
| Codex 登录检查 | 可用时执行不消耗模型的登录状态检查 |
| Personal AI Workspace | 可选且单独授权，缺 OAuth Client ID/Keyring 会报告缺项 |
| 真实四角色验证 | 可选且单独授权消耗额度，结果以真实测试报告为准 |
| Dual-Engine Factory / Studio | **源码随仓库一起下载，不会被安装为常驻服务，也不会自动执行** |
| Skill Builder / Validator / Lifecycle | **源码随仓库一起下载，按需单独运行，不会默认创建或修改 Skills** |
| Claude、Hermes、ChatGPT 适配 | 不会自动连接、不设置凭据，不声称已经运行 |

**最终判断：** 当前交付的是「可安装的 Codex-first 协作基础 + 多个独立开发工具」，不是「装完就能无条件管理所有 AI 的全自动 OS」。每个模块的状态与源代码都可以逐项核查。

