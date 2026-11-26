<div align="center">

# AKA.CRISTI / SKILLS

**FROM EXPERIENCE TO CAPABILITY.**

把人与 AI 的成功协作，变成一个可以安装、可以运行、可以调用的工具。

`DESIGN` × `CODE` × `AI` × `AUTOMATION` × `BUSINESS`

[![Public Skill Installer Tests](https://github.com/2ndforcecrew/aka-cristi-skills/actions/workflows/tests.yml/badge.svg)](https://github.com/2ndforcecrew/aka-cristi-skills/actions/workflows/tests.yml)

[安装](#install) · [Visual Design](#visual-design) · [全部功能](#features) · [兼容平台](#hosts) · [真实状态](#status)

---

| SHARED TRAINING | GLOBAL RULES | SKILLS | AGENT ROLES |
| :---: | :---: | :---: | :---: |
| **22** | **12** | **32** | **04** |
| 共享训练规则 | 全局工作规范 | 工作方法：6 原生 + 26 vendored，31 可安装 + 1 参考 | 专业角色配置 |

| CLI 命令 | MCP 工具 |
| :---: | :---: |
| **06** | **07** |
| 安装、验证、状态、调用 | 列出、读取、预览、验证 |

**NEW — 2026-11-26 · PR #66 已合併**：Addy Osmani agent-skills 全量引入，32 个能力走同一安装器、同一路由、同一载入索引。

</div>

> **THINK. ACT. SOLVE. VERIFY. LEARN.**
>
> 不只是让 AI 回答问题，而是让它理解目标、主动解决问题、验证结果，并将成功经验沉淀为下一次可以复用的能力。
>
> **现在它是一个工具**：装一条命令就能用，任何支持 MCP 的 AI 都能直接调用。

<a id="install"></a>
<a id="one-command-install"></a>
<a id="quick-start"></a>

## 01 / INSTALL — 安装方法（写明每一步）

### MCP Server 一行装（想让 AI 直接调用，先装这个）

~~~bash
git clone --depth 1 https://github.com/2ndforcecrew/aka-cristi-skills.git && cd aka-cristi-skills && pip install '.[mcp]' && aka-skills serve
~~~

客户端配置（Claude、Cursor、Muse 等支持 MCP 的宿主通用）：

~~~json
{"mcpServers": {"aka-skills": {"command": "aka-skills", "args": ["serve"]}}}
~~~

**注意**：MCP 已合入 main（PR #62，2026-11-25），按上面命令装即可。`serve` 报错说缺 MCP SDK，就是你只装了 `pip install .`、没装 `.[mcp]`，跑 `pip install '.[mcp]'` 就好。`serve` 是 stdio 服务，没有网络端口、不设认证，跑起来不打印东西是正常的，要透过 MCP 客户端调用才看到回应。

### A. 命令行工具 `aka-skills`（推荐，最安全）

**第 1 步：拿到源码**

~~~bash
git clone --depth 1 https://github.com/2ndforcecrew/aka-cristi-skills.git && cd aka-cristi-skills
~~~

**第 2 步：安装**

~~~bash
pip install .           # 只装命令行工具
pip install '.[mcp]'    # 再加 MCP Server（想让别的 AI 调用才需要）
~~~

**第 3 步：先预览，再安装**

~~~bash
aka-skills --help                 # 看全部 6 个子命令
aka-skills status                 # 环境预检 + 安装预览，不写文件
aka-skills install                # 只预览，不写文件
aka-skills install --interactive  # 预览后输入 YES 才真正安装
~~~

**安全规则（写死在工具里，不是口头承诺）**：默认只预览、不写文件；输入 `YES` 才写；有冲突的个人配置不会被覆盖；装完会校验文件完整性。`--workspace` 云端配置不在 CLI 中提供，仍需 `python3 -m tools.full_setup --workspace`。

**第 4 步：看看装了什么**

~~~bash
aka-skills list-skills             # 列出全部 31 个可安装 Skills
aka-skills validate visual-design  # 只读预检单个 Skill，不写文件
aka-skills verify                  # 校验已安装的文件
~~~

### B. MCP Server：让任何支持 MCP 的 AI 都能调用

~~~bash
pip install '.[mcp]'   # 只装 MCP 依赖
aka-skills serve        # stdio 方式运行，没有网络监听、不设认证
~~~

客户端配置示例（Claude、Cursor、Muse 等支持 MCP 的宿主通用）：

~~~json
{"mcpServers": {"aka-skills": {"command": "aka-skills", "args": ["serve"]}}}
~~~

| 工具 | 作用 |
| :--- | :--- |
| `list_skills` | 列出全部 Skills |
| `read_skill` | 读取单个 Skill |
| `list_design_cases` | 列出设计案例 |
| `read_design_case` | 读取单个设计案例 |
| `install_preview` | 安装预览（纯 dry-run，不写文件、不提问） |
| `validate_skill` | 验证单个 Skill |
| `check_status` | 环境与安装状态 |

没有装 MCP 依赖时，`serve` 会以非零退出码退出，并明确提示需要安装 `.[mcp]`；其他子命令不需要 MCP 依赖。

### C. 经典安装：`full_setup`（Codex）

~~~bash
# macOS / Linux
git clone --depth 1 https://github.com/2ndforcecrew/aka-cristi-skills.git && cd aka-cristi-skills && python3 -m tools.full_setup --interactive
~~~

~~~powershell
# Windows · PowerShell
git clone --depth 1 https://github.com/2ndforcecrew/aka-cristi-skills.git; if ($LASTEXITCODE -ne 0) { throw "Git clone failed" }; Set-Location aka-cristi-skills; py -3 -m tools.full_setup --interactive
~~~

两种安装结果相同。`pip install .` 只从本地源码安装，尚未发布到 PyPI（`pip install aka-cristi-skills` 目前不可用）。

### 安装前提与装完之后

- **前提**：Git、Python 3.11+、新目录，以及与目标宿主匹配的运行环境。先审查源码；安装器预览变更并要求同意，不覆盖有冲突的个人配置。已有仓库请先检查 Git 状态及更新内容，再从干净的可信版本运行安装器。
- **装完之后**：新开一个 Agent 会话，验证规则和 Skill 是不是真的加载了。可选私人 Workspace、真实模型测试分别授权；基础安装不需要额外 GitHub 账号授权。
- **不熟悉终端？** 将本仓库链接发给具备终端权限的 Agent，请它检查环境、预览安装并在获批后执行对应宿主命令。没有终端权限的 Agent 只能提供指导。

[完整安装说明](PRODUCT_REFERENCE.md#quick-start) · [安装器源码](tools/full_setup.py) · [CLI 源码](aka_skills/cli.py) · [MCP Server 源码](aka_skills/mcp_server.py) · [历史 Beta 下载](https://github.com/2ndforcecrew/aka-cristi-skills/releases)

---

<a id="visual-design"></a>

## 02 / VISUAL DESIGN — 视觉设计 Skill（重点）

**一句话：把一句 brief，变成一件可以交付的作品。** 设计决定有据可查，QA 证据老实写，不把没做过的事写成做过。

这个 Skill 是 **brand-neutral**：不把 AKA.CRISTI 的颜色、Logo 或审美强加给别人的品牌。用客户自己的参考图先行，从参考里提炼原则，不照抄别人的版式和图片。

### 工作流程：Brief → Perceive → Reason → Execute → Verify

| 步骤 | 做什么 |
| :--- | :--- |
| **Brief** | 定清楚：做什么、给谁看、在哪个平台、传达什么、品牌是什么、有哪些素材和限制、怎样算成功。只问真正缺的信息。 |
| **Perceive** | 看已有的成品和参考图，记录观察到的东西，不猜。看构图、字阶、颜色、间距、图片、对比度、交互、响应式。看不到的就写「未验证」。 |
| **Reason** | 最多提三个方向，选一个：比清晰度、原创性、品牌契合度、可行性、无障碍。写一份 Design Decision Record（目标 → 证据 → 选择 → 代价）。 |
| **Execute** | 在原生媒介里做出来。写代码就改最少的文件，照顾 reduced-motion、键盘操作、响应式断点和性能。做静态图就写清尺寸、字体、颜色、导出标准。概念稿不能代替能用的成品。 |
| **Verify** | 先跑硬检查，再做美学点评。严重问题修好再验，最多两轮自动改。主观的最终决定一定要人来拍板。 |

### 八种交付物，八套做法

| 交付物 | 关键决定 | 验什么 |
| :--- | :--- | :--- |
| 叙事、时装、编辑插画 | 故事瞬间、视角、剪影、姿态、笔触、颜色 | 缩略图里剪影清不清楚、手的细节、焦点对不对 |
| 角色、IP 与场景 | 比例、面孔、服装、道具定型；地平线、比例、光线 | 不同角度身份一不一致、透视和接触阴影 |
| 品牌识别与视觉系统 | 标志几何、字标间距、字阶、色彩分工 | 小尺寸和单色下清不清楚、标志间距一不一致 |
| 包装与周边 | 按刀模和印刷区排版，先排正面、侧面、接缝和折线 | 实物尺寸、折线、文案可读性、出血 |
| 编辑、 campaign、电商 | 阅读顺序、网格、字体、产品突出程度；按比例重排 | 最终裁切、最小文字、关键文案、产品比例 |
| 时装摄影与图片指导 | 取景、镜头、主光补光、造型、调色 | 皮肤和面料细节、光的方向、整组颜色一不一致 |
| 网站、UI 与交互 | 视觉层级变成组件、响应式、状态、键盘路径 | 窄屏、可视焦点、真实交互、reduced motion |
| 动态图形与分镜 | 关键姿势、图层、时间、缓动、镜头、循环接缝 | 按目标速度播放、首尾帧、遮挡、身份连续性 |

### QA：硬检查 + 美学点评 + 证据合同

**硬检查（过 / 不过 / 未跑）**：内容齐全、响应式无溢出、文字对比度（WCAG AA）、键盘导航、焦点可见、图片 alt 文字、reduced-motion、build / lint / typecheck、没有坏掉的图片和链接、身份和品牌资产无损。

**美学点评（每项 1–5 分，写理由）**：层级、一致性、编辑节奏、原创性、品牌契合度、构图、图片、工艺。分数是编辑判断，不是客观真理，不会平均成一个「美」的总分。

**证据合同**：每一项都记录状态、方法、证据、局限，分开写 `VERIFIED`、`FAILED`、`NOT_RUN`、`SUBJECTIVE_REVIEW`。没有工具就写未跑，不会把没验过的写成过了。

### 设计参考案例（真的在仓库里）

| 案例 | 内容 |
| :--- | :--- |
| [Glassmorphism](skills/visual-design/references/styles/glassmorphism.md) | 雾面玻璃 UI，四个子变体 |
| [Flat Information Graphics](skills/visual-design/references/styles/flat-information-graphics.md) | 扁平信息图、仪表板、HUD 单色 |
| [Giant-Type Posters](skills/visual-design/references/styles/giant-type-posters.md) | 巨字海报，时装 / 音乐活动 / 酸性科技 |
| [Experimental Posters](skills/visual-design/references/styles/experimental-posters.md) | 实验海报，六个子变体 |
| [Colorful Commercial Posters](skills/visual-design/references/styles/colorful-commercial-posters.md) | 彩色商业海报与广告 |
| [Giant-Type Web Design](skills/visual-design/references/styles/giant-type-web-design.md) | 巨字网页设计，六个子变体 |
| [Beauty Class 案例](skills/visual-design/references/cases/beauty-class-poster.md) | 美妆海报单案例 |

另外有 [Phase 1 视觉研究](skills/visual-design/references/phase-1-visual-research.md)、[视觉语言批次 01–02](skills/visual-design/references/visual-language-batches-01-02.md) 和 16 条用户自选网页研究链接。

### 诚实状态：V0.1，还没过实战验收

本地 Skill 校验只证明文件结构对。真正的验收要三个不同的 brief（网站、海报 / 编辑、品牌系统）＋ 有没有这个 Skill 的 side-by-side 对比 ＋ 可复现的证据 ＋ 独立审查员。**在那之前，V0.1 是已实现、未实战验证。**

目前进度 **1 / 3**：海报 brief 已做（AKA.CRISTI Skills 海报，硬检查过了，绿色细字对比度低于 WCAG AA，已记录为已知限制）。剩下网站和品牌系统两个 brief。

**Creative Web Toolkit 是路线图，还没建成**：滚动动画、爆炸视图、电影转场、Shader、动态字体；按需选用 GSAP、Three.js 等。不要把它当成已经交付的工具箱。

---

<a id="vision"></a>

## 03 / SYSTEM — 工作能力架构

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

这是产品架构方向。当前 CHEF 与六个 Skills 已有安装实现，双引擎为实验性运行时，不代表全部厂商 Agent 已自动在线协作。

<a id="shared-training"></a>

## 04 / SHARED TRAINING — 共享训练成果

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

## 05 / FEATURES — 全部功能

### 核心方法

| 功能 | 做什么 | 状态 |
| :--- | :--- | :--- |
| **CHEF Orchestrator** | 总指挥：理解目标、规划、调度、恢复、验证 | 已有规则及 Skill |
| **[Verified Change Loop](skills/verified-change-loop/SKILL.md)** | 复现 → 修复 → 回归 → 复核，改完一定要验 | 已有本地安装实现 |
| **[Feature Journey Map](skills/feature-journey-map/SKILL.md)** | 从用户入口验证完整实际路径 | 已有本地安装实现 |
| **[Skill Evaluation Gate](skills/skill-evaluation-gate/SKILL.md)** | 评估风险、质量、兼容性及发布证据 | 已有本地安装实现 |
| **[Visual Design](skills/visual-design/SKILL.md)** | 视觉设计全流程 + QA + 设计参考案例 | V0.1 已实现，未实战验证，见 [§02](#visual-design) |
| **[interview-me](skills/interview-me/SKILL.md)** | 一次一问、每问附推荐答案，榨需求到 ~95% 信心再开工 | 已实现（PR #63 新增） |
| **[Vendored skills × 25](vendor/addy-agent-skills/)** | Addy Osmani agent-skills v0.6.18（MIT）全树引入：spec、TDD、code-review、ship 等 25 个工程 skill，补齐原生 6 个之外的生命周期覆盖 | 已合併（PR #66，2026-11-26）；同一安装器、CHEF 路由 + 渐进式载入；真机加载 NOT_RUN，见下 |

### Hybrid Agent System（PR #66，已合併）

6 个原生 skill + 25 个 vendored skill 走同一安装器、同一 CHEF 路由表、同一渐进式载入索引（`docs/skill-index.json`，脚本生成）。vendored `interview-me` 是参考（原生优先），永不安装；hooks 默认不接线；上游 Node 校验脚本只作参考。文件级验证已过：测试 393 个全过、原生 evals 6/6 + 18/18、vendor evals 26/26 + 26/26、隔离安装演练 31 个 skill 落盘、wheel 1,122 KB。但**没有一个真机宿主加载过**——7 宿主加载 / 调用一律 NOT_RUN，六道门禁仍 BLOCKED。详见 [去重裁决](docs/dedup-decisions.md) · [载入索引](docs/skill-index.json) · [跨宿主适配](docs/host-adaptation.md) · [导入状态](vendor/addy-agent-skills/IMPORT_STATUS.md)。

### 训练、标准与验收框架

| 能力 | 做什么 | 状态 |
| :--- | :--- | :--- |
| **22 项共享训练规则** | CHEF 调度、审美、设计流程、交付验收 | 随 CHEF Skill 分发 |
| **12 章全局工作规范** | 沟通、工程、AI 自动化、摄影、电商、安全、测试 | 随 CHEF Skill 分发 |
| **[Evals 框架](evals/run_evals.py)** | 结构 + 路由 44 条（原生 18 + vendored 26），确定性检查、无 LLM、无联网 | 已实现，exit 0 |
| **[Skill 格式标准](docs/skill-format.md)** | 10 节固定顺序 + SKILL.md / references / scripts / assets 目录结构 | 已实现；evals 强制执行 6 个核心节标题 |

### 四个专业角色（Codex 原生 TOML）

| 角色 | 做什么 |
| :--- | :--- |
| Research | 研究、查资料、核对事实 |
| Coding | 写代码、改代码、修 bug |
| QA | 独立验证、跑测试、审结果 |
| Automation | 自动化流程、定时任务、批量操作 |

角色是配置文件；真实调用看宿主支不支持，四角色验收目前 BLOCKED。

### 工具：命令行、MCP、安装器

| 工具 | 做什么 | 状态 |
| :--- | :--- | :--- |
| **`aka-skills` CLI** | 安装、验证、状态、列出、预检、MCP 服务，6 个子命令 | 已实现；干净 venv 安装验证通过 |
| **MCP Server** | stdio 服务，7 个工具，任何支持 MCP 的 AI 都能调用 | 已实现；protocol smoke 通过 |
| **安装器 `full_setup`** | 交互安装向导：预览、YES 确认、写文件、校验 | 已实现；行为未变 |
| **快速安装 `quick_install`** | 不交互的安装路径 | 已实现 |
| **安装事务与回滚** | 安装失败回滚、文件安全检查 | 已实现 |
| **Skill 工具箱** | 创建、验证、安装、生命周期管理、证据记录 | 已实现 |
| **验收门禁** | 六道发布门禁、扫描报告门禁 | 已实现；历史门禁状态见 [SIX_GATE_STATUS](docs/SIX_GATE_STATUS.md) |

### 跨宿主与双引擎

| 工具 | 做什么 | 状态 |
| :--- | :--- | :--- |
| **Multi-Host Adapters** | 把规则和 Skill 文件适配到 Codex、Claude Code、Gemini CLI、OpenCode、WorkBuddy、Hermes | 部分实现；跨厂商运行时待验收 |
| **Dual-Engine** | Factory（工程、稳定性）× Studio（创意、体验），结构化交接 + 独立 QA | 实验性 Codex CLI 运行时 |
| **Agent 交接** | 结构化交接、子代理编排、探针隔离 | 已实现 |

### 私人工作空间与 Windows

| 工具 | 做什么 | 状态 |
| :--- | :--- | :--- |
| **Personal AI Workspace** | 一键初始化私人配置、差异检查、同步与恢复 | 实验性；OAuth 实测待完成 |
| **工作空间同步** | GitHub 同步、锁、GUI | 已实现 |
| **Windows 支持** | Job Object 运行器、GUI 安装器、安装包、EXE 构建 | 已实现；Windows 真机验收待完成 |

### 证据与恢复

| 工具 | 做什么 | 状态 |
| :--- | :--- | :--- |
| **Evidence & Recovery** | 安装校验、日志、超时、备份及回滚 | 按模块验证 |
| **发布验证** | 版本来源验证、发布包校验 | 已实现 |

<a id="dual-engine"></a>

### Dual-Engine / Factory × Studio

Factory 负责工程、稳定性、代码与测试；Studio 负责视觉语言、产品体验、用户旅程与创意判断。两者通过结构化交接与独立 QA 合作。现有实验性运行时不自动启动为后台服务。

[完整功能目录](docs/FEATURE_CATALOG.md) · [双引擎运行说明](docs/CHEF_DUAL_ENGINE_V03_RUNTIME.md) · [四角色配置](docs/CODEX_NATIVE_SUBAGENTS_V02.md) · [私人工作空间](docs/PERSONAL_AI_WORKSPACE.md)

---

<a id="hosts"></a>

## 06 / COMPATIBILITY — 不限定一个厂牌

**文件装到了，不等于 Agent 真的在用。** 下表按实测状态写，不把「装了文件」写成「已经激活」。

| Agent / Host | 安装范围 | 实测状态 |
| :--- | :--- | :--- |
| Codex | 用户级规则、Skills、四个原生 TOML 角色 | 真实安装；四角色验收 BLOCKED |
| Claude Code | 项目级 Skill 文件适配 | 仅文件适配；加载 / 调用 NOT_RUN |
| WorkBuddy / CodeBuddy | 项目级或用户级规则、Skills、Markdown 角色 | 仅文件适配；未验证 |
| Gemini CLI | 项目级规则、Skills、Markdown 角色 | 仅文件适配；未验证 |
| OpenCode | 项目级规则、Skills、Markdown 角色 | 仅文件适配；未验证 |
| Hermes | 项目规则、角色交接模板 | 不支持（BLOCKED） |
| ChatGPT | 无兼容本地宿主 | 不支持（BLOCKED） |

例如 WorkBuddy 全局安装：将对应系统的安装命令最后一段改为 `py -3 -m tools.full_setup --host workbuddy --scope user --interactive`，macOS / Linux 使用 `python3`。

Vendored skills（25 个）与原生 6 个走同一安装器，落盘路径与上表相同；加载 / 调用同样 NOT_RUN，见 [跨宿主适配](docs/host-adaptation.md)。

其他平台的参数、目录及加载方式参阅 [跨宿主安装指南](docs/UNIVERSAL_CHEF_SETUP.md)。**MCP 是另一条路**：任何支持 MCP 的宿主都可以用 `aka-skills serve` 直接调用，不用逐个平台适配，见 [MCP Server](#install)。

---

<a id="status"></a>
<a id="verify"></a>

## 07 / REALITY — 真实状态与验收

**不把愿景写成已实现，不把文件安装写成真实 Agent 已激活。**

| 项目 | 状态 |
| :--- | :--- |
| 共享训练规则公开至 Skills 源码 | 已完成，PR #55 已合并 |
| 训练 MD 随 CHEF Skill 分发 | 本次源码集成；安装回归见 PR #57 |
| 核心安装器、31 个可安装 Skills（6 原生 + 25 vendored）、角色文件、CLI、MCP server | 已有本地实现；干净 venv 安装验证通过；wheel 1,122 KB |
| PR #63：借鉴 agent-skills 的 4 项机制 | 已合并（Rationalizations + Red Flags、interview-me、evals 框架、comparison.md） |
| PR #64：Skill 格式统一 | 已合并（10 节固定顺序、字面标题、格式标准 docs/skill-format.md） |
| PR #66：Addy Osmani agent-skills 全量引入 + Hybrid Agent System | 已合并（merge 97e4a25，2026-11-26）；vendor 273 文件 + 1 symlink（上游 e997ac5，280 项，排除 6 个）；全树扫描 235 项（180 误报、55 真问题为未 pin 版本 npx，低风险）；六道门禁仍 BLOCKED；真机加载 NOT_RUN |
| 全量测试 | 393 个全过（31 跳过）；原生 evals：skills 6/6、路由 18/18；vendor evals：frontmatter 26/26、路由 26/26；0 软建议 |
| Visual Design Skill | V0.1 已实现；实战验收 1 / 3（海报已做，网站和品牌系统待做） |
| 真实跨宿主端到端验收 | 尚未全部完成 |
| Visual Design 完整技术 Toolkit | 开发中（路线图，未建成） |
| 后台自动更新与跨厂商自动调度 | 尚未完成 |
| 历史 Beta 安装包 | v1.0.0-beta.3；不含 CLI / MCP 及之后新增内容；main 已有这些内容，尚未切新 beta |
| 稳定版、独立用户 UAT、Windows 代码签名 | 尚未完成 |

验证报告应区分 `FILES_VERIFIED`、`PASS`、`FAIL`、`BLOCKED`、`NOT_RUN` 和 `INCONCLUSIVE`。真实模型调用需要宿主、登录、额度及另外授权。

[安装及验收完整说明](PRODUCT_REFERENCE.md#verify) · [真实 Agent 验证标准](docs/AGENT_ACTIVATION_VERIFICATION.md) · [版本来源验证](docs/RELEASE_VERIFICATION.md)

---

<a id="resources"></a>

## 08 / DOCUMENTATION — 深入了解

[完整产品参考](PRODUCT_REFERENCE.md) · [全部功能手册](docs/FEATURE_CATALOG.md) · [项目路线图](ROADMAP.md) · [外部用户验收](docs/EXTERNAL_UAT.md) · [反馈问题](https://github.com/2ndforcecrew/aka-cristi-skills/issues)

欢迎分享脱敏的复现步骤与验证证据。不要上传 API Key、Token、私人会话或客户数据。

<div align="center">

---

**AKA.CRISTI**

*CREATE BEAUTIFULLY. BUILD INTELLIGENTLY. AUTOMATE EVERYTHING REASONABLE.*

[返回安装](#install) · [Visual Design](#visual-design) · [GitHub Releases](https://github.com/2ndforcecrew/aka-cristi-skills/releases)

</div>
