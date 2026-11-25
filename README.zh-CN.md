<div align="center">

# AKA.CRISTI / SKILLS

**把人与 AI 的成功协作，转化为可安装、可验证、可持续进化的工作能力。**

*DESIGN × CODE × AI × AUTOMATION*

**UNIVERSAL HOST FILES** &nbsp; | &nbsp; **CHEF ORCHESTRATOR** &nbsp; | &nbsp; **DUAL-ENGINE** &nbsp; | &nbsp; **AGENT COLLABORATION**

[一键安装](#quick-start) · [项目理念](#vision) · [全部功能](#features) · [双引擎架构](#dual-engine) · [当前状态](#status) · [功能手册](docs/FEATURE_CATALOG.md) · [GitHub Release](https://github.com/2ndforcecrew/aka-cristi-skills/releases)

</div>

---

> ### FROM EXPERIENCE TO CAPABILITY
>
> **让 AI 不止于回答，而是真正参与工作的全过程。**
>
> AKA.CRISTI Skills 是一个以 **CHEF 主厨模式** 为核心的 AI Agent 协作项目。它将统一工作规则、专业 Agent 角色、可复用 Skills、双引擎任务执行、独立验收、错误恢复以及个人配置管理逐步组合成一个系统。
>
> 我们关注的不只是「AI 能完成一次任务」，更是「它能否安全地重复完成、用证据证明结果，并把经验转化为下一次可直接复用的能力」。

### 解决什么问题？

| 普通 Agent 使用体验 | AKA.CRISTI 希望建立的工作方式 |
| :--- | :--- |
| 每个任务都要重新交代工作要求 | `AGENTS.md` 统一执行原则与交付标准 |
| 一个 Agent 又开发又自己宣布通过 | CHEF 分工 + 独立 QA + 可追踪的结果 |
| 出错后靠用户反复手动修复 | 有边界的诊断、重试、恢复和验证闭环 |
| 好的工作方法只留在聊天记录中 | 用 Skills、结构化证据和版本信息保留经验 |
| 换电脑或换 Agent 就重新配置 | 个人 Workspace 与跨宿主适配逐步实现 |
| AI 说「完成了」，却没有可核查结果 | 记录实际变更、测试、线程和验收状态 |

**项目定位：** CHEF Core 已可安装到多个宿主的原生规则 / Skills / 角色目录；真实自动执行运行时目前仍以 Codex 为先。部分能力已经有本地实现与跨平台 CI；完整的跨厂商、全自动、长期运行 Agent OS 仍在发展中。**不把规划写成已完成，也不把安装成功写成真实 Agent 已激活。**

<a id="quick-start"></a>

## UNIVERSAL CHEF / 不再只支持 Codex

**同一套 CHEF Core 规则、四个 Skills、四个专业角色，根据宿主转换为原生配置。**

现在除了 Codex，还可为 **WorkBuddy / CodeBuddy、Claude Code、Gemini CLI、OpenCode、Hermes** 及支持 `AGENTS.md` 的其他 Agent 安装项目级能力。WorkBuddy、Claude、Gemini、OpenCode 还支持**明确选择用户全局范围**。安装器默认只预览；安装前会检查已有文件，避免破坏原来的工作规则。

| 目标 Agent | 可安装的内容 | 真实 Agent 调用 |
| --- | --- | --- |
| **Codex** | 全局 `AGENTS.md` + 四 Skills + 四原生 TOML 角色 | 有 Codex CLI 验证器；具体用户环境需实测 |
| **WorkBuddy** | `.codebuddy/rules` + Skills + 四原生 Markdown 角色 | 需要 WorkBuddy 实际会话验收 |
| **Claude Code** | `.claude/rules` + Skills + 四原生 Markdown 角色 | 需要 Claude Code 实际会话验收 |
| **Gemini CLI** | `GEMINI.md` + Skills + 四原生 Markdown 角色 | 需要 Gemini CLI 实际会话验收 |
| **OpenCode** | `AGENTS.md` + Skills + 四原生 Markdown 角色 | 需要 OpenCode 实际会话验收 |
| **Hermes** | 项目 `AGENTS.md`、可选用户 Skills、角色交接模板 | 尚无四角色原生调度适配 |
| **其他 Agent** | 通用 `AGENTS.md` / Skills / 手动交接模板 | 依各宿主实际兼容性 |

### 一条命令安装到 WorkBuddy（Windows / PowerShell）

~~~powershell
git clone --depth 1 https://github.com/2ndforcecrew/aka-cristi-skills.git; if ($LASTEXITCODE -ne 0) { throw "Git clone failed" }; Set-Location aka-cristi-skills; py -3 -m tools.full_setup --host workbuddy --scope user --interactive
~~~

### macOS / Ubuntu / Linux · WorkBuddy 全局规则示例

~~~bash
git clone --depth 1 https://github.com/2ndforcecrew/aka-cristi-skills.git && cd aka-cristi-skills && python3 -m tools.full_setup --host workbuddy --scope user --interactive
~~~

**只改当前项目**可使用 `--scope project --project /path/to/your-project`；换成其他宿主则将 `--host workbuddy` 改成 `--host claude`、`gemini`、`opencode` 等。Hermes 的用户级身份文件 `SOUL.md` 不会被覆盖。安装成功后要**新开宿主会话**，再验证角色是否真正被加载。

> **哪些没有自动完成？** Dual-Engine 有通用 Factory/Studio/QA JSON Handoff 生成器，但目前能自动执行的实验性引擎仍使用 Codex CLI；不同厂商的真实子 Agent 调度需要经过单独适配和验收，不能因文件安装成功而宣传已全平台打通。

**[完整跨宿主安装与验收说明](docs/UNIVERSAL_CHEF_SETUP.md)** · [宿主适配安装器源码](tools/universal_chef.py) · [双引擎通用任务交接](tools/chef_handoff.py)

---

## CHEF RUNTIME V0.4 / 从文件配置到真实宿主会话

**新开发：Claude Code、Gemini CLI、OpenCode 的受控 Headless CLI 调用和 Dual-Engine 独立宿主会话交接。** 不再只有文件安装；在用户同意模型调用、完成宿主登录之后，CHEF 可以运行 Factory → Studio → 独立 QA 的任务序列，复用隔离 Git 快照、SQLite 日志、有限重试和恢复框架。

**这里执行的是独立宿主会话，并非已经验证的原生子 Agent Spawn。** WorkBuddy / Hermes 的安全非交互任务接口尚未验收，因此仍不会冒险调用它们；不覆盖原项目，不自动发布或消耗模型额度。

~~~bash
# 先预检查；不会调用模型
python3 -m tools.host_runtime --host claude --role qa \
  --prompt "检查测试项目" --workspace /absolute/trusted/project

# 明确授权后，实验性运行三阶段 Dual-Engine
python3 -m tools.chef_dual_engine --host claude --kind hybrid \
  --prompt "提出修复建议并审查用户体验" \
  --workspace /absolute/trusted/clean-git-project \
  --db /absolute/private-state/chef.sqlite3 \
  --authorize-inference
~~~

详细说明：[跨宿主 Runtime V0.4](docs/HOST_RUNTIME_V04.md) · [真实宿主执行源码](tools/host_runtime.py) · [开发任务 #44](https://github.com/2ndforcecrew/aka-cristi-skills/issues/44)

---

## 01 / QUICK START — 一条命令，启动完整安装向导

用户打开 GitHub `main` 首页，复制对应操作系统的整行命令即可进入引导。它先检查环境、已有配置和冲突，再由用户授权安装。

### Windows 11 — PowerShell

~~~powershell
git clone --depth 1 https://github.com/2ndforcecrew/aka-cristi-skills.git; if ($LASTEXITCODE -ne 0) { throw "Git clone failed" }; Set-Location aka-cristi-skills; py -3 -m tools.full_setup --interactive --workspace --test-agents
~~~

### macOS — Apple Silicon / Intel

~~~bash
git clone --depth 1 https://github.com/2ndforcecrew/aka-cristi-skills.git && cd aka-cristi-skills && python3 -m tools.full_setup --interactive --workspace --test-agents
~~~

### Ubuntu / Debian / Linux

使用与 macOS 相同的 Bash 命令。请使用普通用户账户，不需要 `sudo`。

**前提：** Git、Python 3.11+。如果需要真实调用 Agent，还必须安装、登录受支持的 Codex CLI，并具有可用额度和权限。此命令针对持续更新的 `main`，运行前应审查来源；已有 `aka-cristi-skills` 文件夹时，应先检查现有代码，避免覆盖。

| 阶段 | 自动处理的内容 | 授权与验收 |
| --- | --- | --- |
| **01 · Inspect** | 检查 Python、Git、Codex 和现有本地配置 | 默认无写入 |
| **02 · Preview** | 展示 CHEF 规则、四个 Skills、四个角色的变更计划 | 冲突则停止 |
| **03 · Install** | 安装并验证受管理的配置与 Skill 文件 | 本地写入前输入 `YES` |
| **04 · Connect** | 检查 Codex CLI 登录状态 | 未登录则提示用户 |
| **05 · Workspace** | 可选进入 GitHub 私人工作空间向导 | OAuth、依赖和云端操作需另行授权 |
| **06 · Agent Verify** | 可选执行四个真实 Codex 角色验收测试 | 单独同意使用 Codex 额度 |

**重要：** 安装验证状态 `FILES_VERIFIED` = 文件已正确放置；不表示已自动完成 GitHub OAuth、跨电脑同步或真实多 Agent 调用。

### 给 Codex Agent 的安装指令

把这段文字粘贴到具有本地终端权限的 Codex，让它协助完成安装：

> 请读取 `https://github.com/2ndforcecrew/aka-cristi-skills` 当前 `main` 和完整功能目录。检查操作系统、Git、Python 3.11+、Codex CLI 以及现有配置；执行对应系统的 `tools.full_setup --interactive --workspace --test-agents` 安装引导。先展示修改计划，获得我明确批准后才安装。GitHub OAuth、额外依赖及消耗额度的真实 Agent 测试必须各自单独确认。完成后报告实际安装文件、`FILES_VERIFIED`、登录情况、Workspace 状态、真实 Agent 运行证据与未解决问题。禁止覆盖私人配置、提交凭据、模拟验收通过。

没有终端访问权限的 Agent 只能指导安装，不能直接操作你的电脑。

**更保守的安装方式：** 仅安装 Codex 核心配置，可运行 `python3 -m tools.quick_install --interactive`（Windows 用 `py -3`）。`v1.0.0-beta.2` 是历史 Codex-first Beta；新版 `v1.0.0-beta.3` 已把通用宿主源码安装器一起打包并公开发布。

<a id="vision"></a>
## 02 / CORE CONCEPT — CHEF、Skills、Agents 与双引擎

这四种能力构成项目的核心：

- **CHEF（主厨）**：理解用户意图、安排执行顺序、分配角色、管理风险、验证交付。
- **AGENTS.md（工作规则）**：约束 Agent 如何检查环境、保护已有工作、修复错误和报告证据。
- **Skills（工作方法）**：把实践中可复用的流程写成结构化的专业能力。
- **Agent Roles（执行角色）**：Research、Coding、QA、Automation 各司其职，减少自查自批。
- **Dual-Engine（任务运行引擎）**：根据任务属性在 Factory（工程）与 Studio（体验/创意）之间选择执行路径。

~~~text
                         USER INTENT
                        用户目标 / 需求
                              │
                              ▼
                       CHEF ORCHESTRATOR
                   理解目标 · 策略 · 风险 · 验收
                              │
             ┌────────────────┼────────────────┐
             ▼                ▼                ▼
           AGENTS.md         SKILLS         AGENT ROLES
          统一工作规范       可复用流程       专业执行角色
             └────────────────┼────────────────┘
                              ▼
                 DUAL-ENGINE TASK RUNTIME
                  ┌──────────┴──────────┐
                  ▼                     ▼
              FACTORY                STUDIO
           代码 / 测试 / 修复       设计 / 体验 / 审阅
                  └──────────┬──────────┘
                             ▼
                        INDEPENDENT QA
                        证据 · 风险 · 验收
                             ▼
                    REVIEW → DELIVER
                      修复与经验沉淀
~~~

**这是整体架构方向，不是已完成的自动在线编排全景图。** 当前四个原生 Codex 角色与 Dual-Engine CLI 是两条不同的实现路径：角色由 Codex 宿主发现与调用，Dual-Engine 目前使用独立 Python/CLI 子进程执行，默认不会被 `full_setup` 自动启动。

<a id="features"></a>
## 03 / FEATURE SYSTEM — 功能全景

> **以下全部来源于仓库实际文件。** 每个模块可以点进源码或文档，详细的适用范围、使用命令、验证状态和限制均整理在 [《完整功能目录》](docs/FEATURE_CATALOG.md)。

### 01. CHEF Orchestrator — 主厨总指挥

**本地规则与 Skill 已实现。** 通过项目底座、环境检查、任务目标拆解、分工、可控修改、测试、独立复核与经验沉淀，统一 AI 的工作方式。`AGENTS.md` 以受管理区块追加，不应盲目覆盖个人规则。

[CHEF 规则](docs/CHEF_GLOBAL_AND_MULTIAGENT.md) · [CHEF Skill](skills/chef-orchestrator/SKILL.md)

### 02. Dual-Engine V0.3 — Factory × Studio 双引擎 <a id="dual-engine"></a>

**实验性运行时已实现，真实 Codex 端到端交付尚未验收。**

这是项目的核心创新之一，不只是说明文档，实际运行代码位于 [`tools/chef_dual_engine.py`](tools/chef_dual_engine.py)。

| 引擎 | 关注重点 | 工作内容 |
| --- | --- | --- |
| **FACTORY** | 可运行、可测试、可维护 | 在独立 Git 快照中提出代码变更候选，运行有限测试，交给 QA |
| **STUDIO** | 用户体验、视觉审美、产品目标 | 审视实际方案的用户旅程、设计质量、可用性和创意意图 |
| **HYBRID** | 工程质量 × 体验质量 | Factory → Studio → 独立 QA，顺序交接与审查 |

**当前已写入的机制：** 本地 Git 隔离克隆、结构化角色交接、SQLite 任务与事件日志、失败/中断状态、有限超时与重试、显式 `--resume` 恢复、私有产物目录、来源快照检查、独立 QA 与人工审查边界。

**和一般多 Agent 聊天有什么不同？** 双引擎处理的是一个具体任务从工程实施到体验审阅、证据记录和恢复的生命周期，不靠多个 Agent 在同一个工作目录里同时修改文件。

**当前限制：** 运行时有离线回归和脚本宿主 E2E；此前真实 Codex 执行遇到连接与授权错误，没有获得完整 Factory→Studio→QA 交付记录。它也不会自动发布 PR、合并代码或启动为长期后台进程。

**实验性独立调用：**

~~~bash
python3 -m tools.chef_dual_engine --kind hybrid --prompt "修复一个小问题并评估用户旅程" --workspace /absolute/project --db /absolute/private-state/chef.sqlite3 --timeout 300
~~~

该命令需要可信的、干净且已提交的 Git 项目，以及已经登录可用的 Codex CLI；可能消耗额度。日志和运行数据应放在原项目目录之外。

[双引擎架构与阶段路线](docs/CHEF_DUAL_ENGINE_V03_ROADMAP.md) · [运行机制、限制与真实测试记录](docs/CHEF_DUAL_ENGINE_V03_RUNTIME.md)

### 03. Four Native Codex Agents — 四个专业角色

**原生 TOML 角色定义与安装器已实现；真实调用依赖用户 Codex 宿主。**

| Agent | 配置名 | 负责什么 |
| --- | --- | --- |
| **Research** | `aka_research` | 查阅文档、源码、来源、证据与不确定性 |
| **Coding** | `aka_coding` | 根据明确授权范围写代码、修复、运行测试 |
| **QA** | `aka_qa` | 独立复核代码、回归、可访问性、可靠性及证据 |
| **Automation** | `aka_automation` | 设计 API / MCP 流程、重试、超时、日志和恢复 |

这些角色是 **Codex 内的自定义子 Agent 配置**，不是四个自动购买或登录的第三方 AI。安装 `agents/*.toml` 文件不等于成功创建四个线程；[真实四角色验证器](tools/verify_four_agents.py) 能在授权环境中检测线程与执行结果。

[角色配置与激活流程](docs/CODEX_NATIVE_SUBAGENTS_V02.md) · [真实验收要求](docs/FOUR_AGENT_RUNTIME_ACCEPTANCE.md)

### 04. Four Reusable Skills — 四个方法论 Skill

| Skill | 帮用户完成什么 |
| --- | --- |
| [**CHEF Orchestrator**](skills/chef-orchestrator/SKILL.md) | 规划、委派、监督、交接、验收 |
| [**Verified Change Loop**](skills/verified-change-loop/SKILL.md) | 复现 Bug → 最小修复 → 回归与复核 |
| [**Feature Journey Map**](skills/feature-journey-map/SKILL.md) | 检查从用户入口到最终结果的真实使用路径 |
| [**Skill Evaluation Gate**](skills/skill-evaluation-gate/SKILL.md) | 评估 Skill 的行为、质量、风险和升级证据 |

**已实现安装与文件验证。** Skill 是工作流程和说明，不是自己运行的后台程序；需要真实 Agent 读取和执行才能发挥作用。

### 05. Personal AI Workspace — 私人配置与同步

**实验性 CLI/GUI 已实现；真实 GitHub OAuth / 外部用户端到端验收尚未完成。**

规划让每位用户使用自己的 GitHub 账号管理私有 `my-agent-workspace`：Device Flow 授权、私人仓库创建/复用、公开配置白名单初始化、固定版本拉取、差异预览、冲突检测、本地备份、恢复、日志和 Sync Center。

默认是**用户确认后的手动 Pull**，不是自动 Push，更不是已完成的跨设备实时双向同步。OAuth 还需要发布者提供 GitHub OAuth App 公共 Client ID、系统原生安全凭据库与用户授权；不会假装 ChatGPT 已 Connected。

[Personal AI Workspace](docs/PERSONAL_AI_WORKSPACE.md) · [一键初始化编排](tools/workspace_oneclick.py) · [同步与备份引擎](tools/workspace_sync.py)

### 06. Universal Skill Toolkit — Skill 创建、验证与生命周期

**本地工具已实现；完整自动进化尚未实现。**

- [Skill Validator](tools/skill_validator.py)：只读检查 Skill 结构、元数据和危险路径。
- [Skill Builder](tools/skill_builder.py)：生成标准 Skill 目录与模板；预览优先，不覆盖已有作品。
- [Skill Lifecycle](tools/skill_lifecycle.py)：生成 SHA-256 清单、结构检查与维护/退役建议。
- [Skill Evidence](tools/skill_evidence.py)：核对验证账本与证据引用的格式，等待真实审核。
- [Skill Installer](tools/skill_installer.py)：受管理的预览、安装、校验与卸载。

**未来目标：** 自动识别反复成功的流程 → 形成 Skill 候选 → 独立复测 → 版本评估 → 更新或淘汰。当前并没有不经确认就自动改写、发布或淘汰用户 Skills 的自进化服务。

[Universal Skill Architecture](docs/UNIVERSAL_SKILL_ARCHITECTURE.md)

### 07. Multi-Host Agent Adapters — 跨厂商适配

**只读发现与部分文件适配已实现，真实跨厂商调度尚未实现。**

- [Agent Discovery](tools/agent_adapters.py)：探测 Codex、Claude Code、Gemini CLI、OpenCode、Hermes 和自定义 Agent 的本地候选能力。
- [Host Adapters](tools/host_adapters.py)：提供 inspect、preview、install、verify、uninstall 的统一契约。Codex 用户级 Skills 和 Claude Code 项目级 Skill 文件有受控适配；Hermes、ChatGPT 不会被假装连接成功。
- **不自动生成凭据或第三方访问权限。** 不支持的宿主、缺少真实调用证据的功能明确报告未验证。

[当前宿主能力矩阵](docs/HOST_CAPABILITY_MATRIX.md) · [适配器契约](docs/UNIVERSAL_AGENT_ADAPTERS.md)

### 08. Activation & Diagnostics — 真实 Agent 调用验收

**调用验证程序和离线回归已实现。**

- [Skill Activation](tools/verify_codex_activation.py)：真实 `codex exec` 只读探针，检查是否确实读取 Skill 和测试案例。
- [Four-Agent Runtime](tools/verify_four_agents.py)：核对真实父子线程、准确角色、完成回复，而非仅听 AI 自称。
- [Diagnostics](tools/diagnose_four_agents.py)：对格式变化、不完整调用和异常提供诊断。
- [Probe Isolation](tools/codex_probe_isolation.py)：控制测试工作区与配置边界。

曾取得 **Codex CLI 0.169.0 限定只读协作案例**的外部跨源证据；旧自动解析器对此标记 `INCONCLUSIVE`，与完整的独立用户验收是不同层级。

[真实调用验收标准](docs/AGENT_ACTIVATION_VERIFICATION.md) · [已记录证据](docs/UNIVERSAL_VERIFICATION_2026-11-16.md)

### 09. Install, Protection & Recovery — 安装、来源与恢复

**已有可用的本地安装工程与跨平台测试。**

- [`tools.full_setup`](tools/full_setup.py)：`main` 的统一安装引导，连接核心配置、可选 Workspace、可选真实 Agent 测试。
- [`tools.quick_install`](tools/quick_install.py)：早期 `beta.2` 已包含的 Codex 核心配置快速安装。
- [Windows GUI](tools/gui_installer.py)：预览、确认、进度、取消、验证、受保护恢复。
- [Install Transaction](tools/install_transaction.py)：记录受管理的文件变化、检查冲突与回滚条件。
- [Windows Job Object](tools/aka_windows_job_runner.py)：管理超时子进程的生命周期；**不是权限沙盒**。
- [Release Verification](tools/verify_release.py)：源码版本、摘要与 GitHub 来源证明验证。

**发布机制：** Windows EXE 和源码 ZIP 由 GitHub Actions 构建，配 SHA-256 与 GitHub OIDC / Sigstore provenance；Windows EXE 尚无 Authenticode 证书签名。

[Windows GUI 使用与恢复](docs/WINDOWS_GUI.md) · [候选包与来源验证](docs/RELEASE_VERIFICATION.md)

### 10. Testing, Evidence & Release Quality — 质量与持续交付

**CI、离线测试、验收文档均已建立。**

- Windows、macOS、Ubuntu 运行多组单元、安装、GUI、同步与安全检查。
- [Acceptance Gate](tools/acceptance_gate.py) 管理证据资料预检，不会代替独立审核。
- [Scan Report Gate](tools/scan_report_gate.py) 可选整理静态扫描记录，不代表完整软件已获安全认证。
- [成长记录](docs/GROWTH_JOURNAL_2026-11-16.md)、[路线图](ROADMAP.md) 和 [外部 UAT 指引](docs/EXTERNAL_UAT.md) 保留开发过程和未完成事项。

历史 SkillSpector 标记不能直接拿来断言当前 Beta 有多少实际漏洞，也不能因为发布 Beta 就声称所有历史发现都是误报。[查看历史审计范围](docs/SECURITY_REVIEW_2026-11-15.md)。

### 11. Agent Collaboration OS — 长期演进方向

**这是以上模块组合的产品目标，还不是所有部分都已交付。**

将来希望把任务状态、Agent Registry、跨厂商调度、Factory/Studio 执行、质量复核、自动恢复、Skill Evolution、持续维护/淘汰和个人 Workspace 串成统一系统。当前仓库已有其中多个可独立使用的模块，**尚未具备完整的后台自动调度、自动发布和全部宿主的真实端到端连通能力**。

[双引擎研发阶段](docs/CHEF_DUAL_ENGINE_V03_ROADMAP.md) · [全部功能与源码明细](docs/FEATURE_CATALOG.md)

<a id="status"></a>
## 04 / RELEASE & REALITY — 当前版本状态

| 类别 | 状态 | 说明 |
| --- | --- | --- |
| **公开发布** | **已完成 Beta** | [`v1.0.0-beta.3`](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.3) 已提供 Windows EXE、源码 ZIP、SHA-256、GitHub provenance |
| **CHEF + 5 Skills + 4 角色配置** | **已实现** | 可本地预览、安装、校验；不是自动启动所有 Agent |
| **跨平台 CI** | **已通过相应测试** | Windows、macOS、Ubuntu；不代表所有外部用户环境 |
| **Dual-Engine Factory / Studio** | **实验性运行时** | 隔离执行、SQLite、恢复、QA；尚无完整真实 Codex E2E |
| **Personal AI Workspace** | **实验性** | GUI/CLI/Mock 已实现，真实 OAuth 与私人仓库流程需验收 |
| **Skill Builder / Validator / Lifecycle** | **本地工具已实现** | 自动进化、安装和退役流程尚未闭环 |
| **跨厂商 Adapter** | **部分实现** | Claude 项目级文件适配；Hermes/ChatGPT 完整调用未实现 |
| **四 Agent 真实协作** | **有范围限定的实测证据** | 普通用户安装后的完整激活仍需单独验证 |
| **Windows Authenticode 签名** | **尚未签署** | GitHub OIDC 来源证明不能代替代码签名证书 |
| **外部用户验收 / Stable** | **未完成** | Beta 可供独立用户测试，不等于稳定版 |

**版本区别：** `v1.0.0-beta.2` 只包含 Codex 核心 `quick_install`；`v1.0.0-beta.3` 新增 `full_setup` 的跨宿主适配、全局/项目级安装、受管理卸载和 Dual-Engine 通用交接协议。安装一次仍不会自动启动任何宿主的真实 Agent 或 Dual-Engine 后台进程。

<a id="verify"></a>
## 05 / VERIFY — 如何验证安装与真实 Agent 调用？

进入已经下载并审查过的仓库目录：

~~~bash
python3 -m tools.chef_global_rules verify
python3 -m tools.codex_subagents verify
python3 -m tools.skill_installer verify chef-orchestrator --target codex
~~~

Windows 可以用 `py -3` 替换 `python3`。完整四角色真实调用需要用户已登录 Codex CLI，且**另外授权使用模型额度**：

~~~bash
codex login status
python3 -m tools.verify_four_agents --timeout 600 --out four-agent-report.json
~~~

`PASS` 表示在该次验收范围内得到完整证据；`INCONCLUSIVE` 表示证据不足；`FAIL` 表示执行失败；`NOT_RUN` 表示未执行或缺少运行条件。不要把 `FILES_VERIFIED` 与真实 Agent 激活混为一谈。

### 常见问题

**Q：安装后能自动调用 Hermes、Claude 和 ChatGPT 吗？**  
不能。目前它是 Codex-first 项目，跨厂商完整调度仍需独立实现与用户授权。

**Q：Dual-Engine 不是已经开发了吗？为什么安装后没有界面？**  
已存在独立 `tools.chef_dual_engine` CLI 运行时，但还未集成进统一安装器的自动启动或后台服务。请查看 [双引擎文档](docs/CHEF_DUAL_ENGINE_V03_RUNTIME.md)。

**Q：为什么安装成功后仍可能无法启动四个 Agent？**  
因为文件校验不等于宿主加载；还需支持 Subagents 的 Codex、登录、额度、实际权限及真实父子线程验证。

**Q：是否会覆盖我的个人 AGENTS.md？**  
安装器以受管理区块/文件所有权进行预览与保护，发现不受管理或用户改动冲突时拒绝直接覆盖。请先审查预览及备份。

**Q：可以直接用于正式生产或真实客户数据吗？**  
这是 Beta，推荐先在独立测试环境验证；缺失的真实 OAuth、外部 UAT、签名和宿主兼容验收必须如实考虑。

<a id="resources"></a>
## 06 / DOCUMENTATION — 完整文档与参与开发

| 文档 | 适合了解什么 |
| --- | --- |
| [**完整功能目录 · Feature Catalog**](docs/FEATURE_CATALOG.md) | **全部模块、实际能力、状态、源码与使用边界** |
| [Dual-Engine 架构路线](docs/CHEF_DUAL_ENGINE_V03_ROADMAP.md) | Factory / Studio / Hybrid 与未来扩展 |
| [Dual-Engine 运行实录](docs/CHEF_DUAL_ENGINE_V03_RUNTIME.md) | 隔离 Git、SQLite、恢复、QA、实测限制 |
| [Codex 四 Agent 配置](docs/CODEX_NATIVE_SUBAGENTS_V02.md) | 四角色职责、安装、加载、测试 |
| [Personal AI Workspace](docs/PERSONAL_AI_WORKSPACE.md) | GitHub Device Flow、私人仓库、备份与同步 |
| [Universal Skill Architecture](docs/UNIVERSAL_SKILL_ARCHITECTURE.md) | Skill Validator、Builder、Lifecycle |
| [Agent Host 能力矩阵](docs/HOST_CAPABILITY_MATRIX.md) | Codex、Claude、Hermes、ChatGPT 的适配范围 |
| [版本验收标准](docs/CODEX_V1_RELEASE_ACCEPTANCE.md) | 工程验证、Beta、稳定版的区别 |
| [外部测试计划](docs/EXTERNAL_UAT.md) | Windows/macOS/Linux 的真实安装记录要求 |
| [GitHub Issues](https://github.com/2ndforcecrew/aka-cristi-skills/issues) | Bug、兼容性反馈与建议 |

帮助项目改进时，欢迎提交可复现的操作步骤、系统版本和**脱敏**测试证据；请勿上传 Token、密钥、客户隐私或完整私人会话日志。

### Developer Checks

~~~bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s tests -p 'test_full_setup.py' -v
python3 -m unittest discover -s tests -p 'test_chef_dual_engine.py' -v
~~~

测试与真实付费模型调用不是一回事。CI 通过可以证明特定代码路径工作，并不证明所有 Agent 已经在用户电脑上成功协作。

---

<div align="center">

**AKA.CRISTI**

*CREATE BEAUTIFULLY. BUILD INTELLIGENTLY. AUTOMATE EVERYTHING REASONABLE.*

[返回一键安装](#quick-start) · [完整功能手册](docs/FEATURE_CATALOG.md) · [查看发布版本](https://github.com/2ndforcecrew/aka-cristi-skills/releases) · [反馈问题](https://github.com/2ndforcecrew/aka-cristi-skills/issues)

</div>
