<div align="center">

# AKA.CRISTI / SKILLS

**FROM EXPERIENCE TO CAPABILITY.**

把人与 AI 的成功协作，转化为可安装、可复用、可验证的工作能力。

`DESIGN` × `CODE` × `AI` × `AUTOMATION` × `BUSINESS`

[一键安装](#one-command-install) · [产品架构](#vision) · [共享训练](#shared-training) · [全部能力](#features) · [兼容平台](#hosts) · [真实状态](#status)

---

| SHARED TRAINING | GLOBAL RULES | CORE SKILLS | AGENT ROLES |
| :---: | :---: | :---: | :---: |
| **22** | **12** | **04** | **04** |
| 共享训练规则 | 全局工作规范 | 核心工作方法 | 专业角色配置 |

</div>

> **THINK. ACT. SOLVE. VERIFY. LEARN.**
>
> 不只是让 AI 回答问题，而是让它理解目标、主动解决问题、验证结果，并将成功经验沉淀为下一次可以复用的能力。

<a id="one-command-install"></a>
<a id="quick-start"></a>

## 01 / INSTALL — 一条命令开始

一个公开仓库，一次安装向导。CHEF、核心 Skills、角色配置及共享训练 MD 在同一源码中提供。不需要额外访问私人规则仓库。

**Windows · PowerShell（Codex）**

~~~powershell
git clone --depth 1 https://github.com/2ndforcecrew/aka-cristi-skills.git; if ($LASTEXITCODE -ne 0) { throw "Git clone failed" }; Set-Location aka-cristi-skills; py -3 -m tools.full_setup --interactive
~~~

**macOS / Linux · Terminal（Codex）**

~~~bash
git clone --depth 1 https://github.com/2ndforcecrew/aka-cristi-skills.git && cd aka-cristi-skills && python3 -m tools.full_setup --interactive
~~~

前提：Git、Python 3.11+、新目录，以及与目标宿主匹配的运行环境。先审查源码；安装器预览变更并要求同意，不覆盖有冲突的个人配置。已有仓库请先检查 Git 状态及更新内容，再从干净的可信版本运行安装器。

**使用其他 Agent？** 见 [跨宿主安装](#hosts)。**不熟悉终端？** 将本仓库链接发给具备终端权限的 Agent，请它检查环境、预览安装并在获批后执行对应宿主命令。没有终端权限的 Agent 只能提供指导。

安装后新开 Agent 会话，验证实际规则和 Skill 加载情况。可选私人 Workspace、真实模型测试分别授权；基础安装不需要额外 GitHub 账号授权。

[完整安装说明](PRODUCT_REFERENCE.md#quick-start) · [安装器源码](tools/full_setup.py) · [历史 Beta 下载](https://github.com/2ndforcecrew/aka-cristi-skills/releases)

---

<a id="vision"></a>

## 02 / SYSTEM — 工作能力架构

~~~text
                        USER / 目标与创意
                                │
                                ▼
                        CHEF / 总指挥
                 理解 · 调度 · 恢复 · 验证
                                │
             ┌──────────────────┼──────────────────┐
             ▼                  ▼                  ▼
      SHARED TRAINING         SKILLS          AGENT ROLES
       训练方法与规则         工作流程          专业角色配置
             └──────────────────┼──────────────────┘
                                ▼
                    FACTORY  ×  STUDIO
                     工程质量 × 创意体验
                                │
                                ▼
                     VERIFY → DELIVER → LEARN
~~~

这是产品架构方向。当前 CHEF 与四个核心 Skills 已有安装实现，双引擎为实验性运行时，不代表全部厂商 Agent 已自动在线协作。

<a id="shared-training"></a>

## 03 / SHARED TRAINING — 共享训练成果

**学习的是工作方法，而不是私人记忆、固定模板或模型权重。**

| 训练体系 | 内容 |
| :--- | :--- |
| **22项共享训练规则** | CHEF 调度、独立审美、设计流程、创意技术、交付验收与经验积累 |
| **12章全局工作规范** | 沟通、工程、AI 自动化、摄影影像、电商营销、安全权限与测试标准 |
| **Visual Design** | BRIEF → PERCEIVE → REASON → EXECUTE → VERIFY → LEARN |
| **Continuous Learning** | 经过审核的经验沉淀为规则或 Skill 候选，按证据验证与维护 |

设计方法覆盖品牌视觉、平面海报、插画、包装、商业摄影、电影视觉、电商、网站 UI/UX、3D 与 Motion Design。独立选择字体、色彩、构图和视觉语言，不强制所有客户采用 AKA.CRISTI 品牌风格。

高级 Web 动效、Exploded View、Shader、Creative Web Toolkit 是训练规范和发展方向，不能视为完整交付的工具箱。

**[22项规则全文](shared-training/rules/TRAINING.md)** · **[12章全局规范](shared-training/rules/GLOBAL_WORK_RULES.md)** · [Agent 入口](shared-training/AGENTS.md) · [单向同步协议](shared-training/docs/SYNC_PROTOCOL.md)

两份核心训练 MD 随 CHEF Skill 的 references 目录分发；CHEF 被调用时读取适用章节。共享规则只向用户分发，不回传个人记忆；后台自动同步和跨宿主真实加载仍待验证。

---

<a id="features"></a>

## 04 / CAPABILITIES — 核心产品

| 模块 | 作用 | 当前边界 |
| :--- | :--- | :--- |
| **CHEF Orchestrator** | 自主规划、工具选择、任务委派、错误恢复 | 已有规则及 Skill |
| **Core Skills × 4** | 协作、修复、用户旅程、验收 | 已有本地安装实现 |
| **Agent Roles × 4** | Research / Coding / QA / Automation | 角色配置；真实调用依宿主 |
| **Dual-Engine** | Factory 工程 + Studio 创意体验 | 实验性 Codex CLI 运行时 |
| **Personal AI Workspace** | 私人配置、差异检查、同步与恢复 | 实验性；OAuth 实测待完成 |
| **Universal Skill Toolkit** | 创建、验证、安装及生命周期管理 | 已有本地工具 |
| **Multi-Host Adapters** | 原生规则及 Skill 文件适配 | 部分实现；跨厂商运行时待验收 |
| **Evidence & Recovery** | 安装校验、日志、超时、备份及回滚 | 按模块验证 |

### 四个核心 Skills

| Skill | 工作方法 |
| :--- | :--- |
| [CHEF Orchestrator](skills/chef-orchestrator/SKILL.md) | 统筹任务，协调执行与验收；含共享训练 MD |
| [Verified Change Loop](skills/verified-change-loop/SKILL.md) | 复现 → 修复 → 回归 → 复核 |
| [Feature Journey Map](skills/feature-journey-map/SKILL.md) | 从用户入口验证完整实际路径 |
| [Skill Evaluation Gate](skills/skill-evaluation-gate/SKILL.md) | 评估风险、质量、兼容性及发布证据 |

<a id="dual-engine"></a>

### Dual-Engine / Factory × Studio

Factory 负责工程、稳定性、代码与测试；Studio 负责视觉语言、产品体验、用户旅程与创意判断。两者通过结构化交接与独立 QA 合作。现有实验性运行时不自动启动为后台服务。

[完整功能目录](docs/FEATURE_CATALOG.md) · [双引擎运行说明](docs/CHEF_DUAL_ENGINE_V03_RUNTIME.md) · [四角色配置](docs/CODEX_NATIVE_SUBAGENTS_V02.md) · [私人工作空间](docs/PERSONAL_AI_WORKSPACE.md)

---

<a id="hosts"></a>

## 05 / COMPATIBILITY — 不限定一个厂牌

| Agent / Host | 现有安装范围 |
| :--- | :--- |
| Codex | 用户级规则、Skills、四个原生 TOML 角色 |
| WorkBuddy / CodeBuddy | 项目级或明确选择用户级规则、Skills、Markdown 角色 |
| Claude Code | 项目级或明确选择用户级规则、Skills、Markdown 角色 |
| Gemini CLI | 项目级或明确选择用户级规则、Skills、Markdown 角色 |
| OpenCode | 项目级或明确选择用户级规则、Skills、Markdown 角色 |
| Hermes | 项目规则、角色交接模板；Skills 目录需明确指定 |
| 其他兼容宿主 | 通用项目规则与文件适配，依实际支持 |

例如 WorkBuddy 全局安装：将对应系统的安装命令最后一段改为 `py -3 -m tools.full_setup --host workbuddy --scope user --interactive`，macOS / Linux 使用 `python3`。

其他平台的参数、目录及加载方式参阅 [跨宿主安装指南](docs/UNIVERSAL_CHEF_SETUP.md)。原生文件安装不等于完成真实跨厂商调度；ChatGPT 等无兼容本地宿主的场景不能假装已激活。

---

<a id="status"></a>
<a id="verify"></a>

## 06 / REALITY — 真实状态与验收

**不把愿景写成已实现，不把文件安装写成真实 Agent 已激活。**

| 项目 | 状态 |
| :--- | :--- |
| 共享训练规则公开至 Skills 源码 | 已完成，PR #55 已合并 |
| 训练 MD 随 CHEF Skill 分发 | 本次源码集成；安装回归见 PR #57 |
| 核心安装器、四 Skills、角色文件 | 已有本地实现 |
| 真实跨宿主端到端验收 | 尚未全部完成 |
| Visual Design 完整技术 Toolkit | 开发中 |
| 后台自动更新与跨厂商自动调度 | 尚未完成 |
| 历史 Beta 安装包 | v1.0.0-beta.3；不含本次新增源码 |
| 稳定版、独立用户 UAT、Windows 代码签名 | 尚未完成 |

验证报告应区分 `FILES_VERIFIED`、`PASS`、`FAIL`、`BLOCKED`、`NOT_RUN` 和 `INCONCLUSIVE`。真实模型调用需要宿主、登录、额度及另外授权。

[安装及验收完整说明](PRODUCT_REFERENCE.md#verify) · [真实 Agent 验证标准](docs/AGENT_ACTIVATION_VERIFICATION.md) · [版本来源验证](docs/RELEASE_VERIFICATION.md)

---

<a id="resources"></a>

## 07 / DOCUMENTATION — 深入了解

[完整产品参考](PRODUCT_REFERENCE.md) · [全部功能手册](docs/FEATURE_CATALOG.md) · [项目路线图](ROADMAP.md) · [外部用户验收](docs/EXTERNAL_UAT.md) · [反馈问题](https://github.com/2ndforcecrew/aka-cristi-skills/issues)

欢迎分享脱敏的复现步骤与验证证据。不要上传 API Key、Token、私人会话或客户数据。

<div align="center">

---

**AKA.CRISTI**

*CREATE BEAUTIFULLY. BUILD INTELLIGENTLY. AUTOMATE EVERYTHING REASONABLE.*

[返回一键安装](#one-command-install) · [共享训练](#shared-training) · [GitHub Releases](https://github.com/2ndforcecrew/aka-cristi-skills/releases)

</div>
