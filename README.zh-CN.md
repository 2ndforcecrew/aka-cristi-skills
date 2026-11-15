# AKA.CRISTI Skills — 中文功能说明

🌐 **Language / 语言：** [English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Français](README.fr.md)

**FROM EXPERIENCE TO CAPABILITY｜将协作经验变成可复用能力**

## 项目是什么

AKA.CRISTI Skills 是一套公开、可审查、可在本地安装的 **AI Agent 工作流程技能包**，配套安全安装器和 Codex 的 CHEF 协作配置。目标是让 AI 在执行复杂任务时，不只输出建议，而是遵循「明确目标 → 检查环境 → 分工执行 → 验证结果 → 错误恢复 → 记录可复用经验」的工作方法。

**需要区分：** Skill 是指导 Agent 如何工作的说明与流程，**不是**独立运行的 AI 大脑，也不会自动获得 GitHub、Codex、Hermes、Claude 或其他服务的登录权限。是否能真正调用某个 Agent，取决于本机宿主版本、工具连接和授权。

本仓库是公开发行版，与 AKA.CRISTI 的私有开发仓库分离；不会发布私有工作规则、账号信息、客户数据、私有历史记录。

## 六项发布门禁：整体仍未通过

Issues #8–#13 的六项工作已通过 PR #14 合入 main，但整体状态仍为 **BLOCKED**，**不是已批准的正式版本，也不是安全安装建议**。详见[六项验收状态](docs/SIX_GATE_STATUS.md)。原始“67 分、24 项”扫描报告缺失；本次固定基线重新执行 SkillSpector 2.12.0 `--no-llm`，得到 **56 分、23 项、DO_NOT_INSTALL**，两者不能混为一次扫描。详见[安全复核](docs/SECURITY_REVIEW_2026-11-15.md)。

旧版自动获取 main ZIP 的 bootstrap 已改为默认阻塞。固定 commit 的下载不等于验签；远程来源必须先用独立确认的 commit、SHA256、工作流身份与 provenance 验证。不会自动执行未验签的 Codex 安装脚本。前置依赖和来源审查仍需完成。

已有 Python 3.11+、审查过完整本地源码后，可在 main 上测试真实图形窗口：

```powershell
python -m tools.gui_installer
```

本地源码可双击 `start-gui.cmd`。另新增 [Windows 独立 EXE 候选构建](.github/workflows/windows-gui-candidate.yml)，仅打包 9 个公开数据文件，并进行真实控件/EXE 启动测试及 GitHub 来源验签；不包含 Authenticode 证书。界面提供差异预览、同意勾选、进度、文件校验及受保护撤销；缺依赖自动安装、干净 Windows 11 与朋友首次安装验收仍为 BLOCKED。安装文件成功始终与真实 Agent 激活分开。

- [Windows GUI 与恢复](docs/WINDOWS_GUI.md)
- [签名候选、身份固定与验签](docs/RELEASE_VERIFICATION.md)
- [Codex / Claude / Hermes / ChatGPT 能力矩阵](docs/HOST_CAPABILITY_MATRIX.md)
- [独立外部用户验收计划](docs/EXTERNAL_UAT.md)
- [严格四角色线程关联](docs/FOUR_AGENT_EVIDENCE_V03.md)

Claude 目前只实现项目级 Skill 文件适配，真实调用 NOT_RUN；Hermes/ChatGPT BLOCKED。云端实际尝试过一次 Codex 调用，退出码 1，未取得可归属线程，不能宣布四角色通过。

## 一、核心功能

### 1. CHEF Orchestrator：AI 任务总指挥

文件：[chef-orchestrator/SKILL.md](skills/chef-orchestrator/SKILL.md)

- **目标与验收：** 将用户需求转成可观察的完成条件、授权边界与停止条件。
- **Inspect：** 先读取项目规则、现有配置、Git 状态及可用工具，避免直接覆盖工作成果。
- **任务分工：** 按需规划 Research、Creative、Coding、QA、Automation、Knowledge 等职责。
- **可追踪交接：** 明确任务 ID、使用的实际工具、文件范围、输入输出、超时、重试次数和验收标准。
- **实际执行：** 有真实连接才调用其他 Agent；不可用时明确记录 `BLOCKED` 或 `NOT_RUN`，不伪造委派结果。
- **独立验证：** 检查代码、测试、日志和实际用户路径，区分「已完成」与「已验证」。
- **自动恢复方法：** 对失败进行有边界的诊断、最小修复和重复测试；涉及不可逆操作仍需授权。
- **经验沉淀：** 仅将真实验证过的重复流程提炼成待审核 Skill，不自动公开或安装。

### 2. Verified Change Loop：问题诊断与修复闭环

文件：[verified-change-loop/SKILL.md](skills/verified-change-loop/SKILL.md)

复现问题 → 检查证据 → 最小可逆修改 → 重跑相同场景 → 对比结果 → 回归测试 → 交付验收。适合代码 Bug、CI 故障、网页功能异常及复杂流程修复。

### 3. Feature Journey Map：真实用户操作路径

文件：[feature-journey-map/SKILL.md](skills/feature-journey-map/SKILL.md)

记录用户从入口、初始化、操作到可见结果的完整流程，并覆盖空状态、权限不足、错误输入、慢网络等异常路径。避免只凭单元测试通过就宣称产品可用。

### 4. Skill Evaluation Gate：技能质量审核

文件：[skill-evaluation-gate/SKILL.md](skills/skill-evaluation-gate/SKILL.md)

通过实际场景、测试证据、独立复核和发布授权判断 Skill 是否可进入下一个阶段；区分 Candidate、Tested、Reviewed、Approved / Released，不将安装成功等同于运行成功。

### 5. CHEF Global Rules：跨项目工作规则

- 将**经过公开脱敏的** CHEF 规则写入 `~/.codex/AGENTS.md` 或 `$CODEX_HOME/AGENTS.md`。
- 安装前支持 `preview`；通过 `--apply` 才实际写入。
- 采用受管理标记区块追加规则，尽量保留用户现有内容，已有文件会备份。
- 支持校验和卸载受管理区块；不等于自动同步所有电脑的私有规则。

技术说明：[CHEF Global Rules + Multi-Agent Starter](docs/CHEF_GLOBAL_AND_MULTIAGENT.md)。

### 6. Codex Native Subagents：四个角色

| 角色 | 名称 | 主要职责 |
| --- | --- | --- |
| Research | `aka_research` | 搜索事实、整理来源和证据 |
| Coding | `aka_coding` | 在授权范围内编程、修复和测试 |
| QA | `aka_qa` | 对最终版本进行独立审查和验证 |
| Automation | `aka_automation` | 设计安全、有边界的自动化流程 |

仓库提供四个原生 Codex 自定义 Agent 的 TOML 配置及安装、校验脚本。**安装配置不代表四个 Agent 已实际启动**，更不代表能够调用其他厂商的账户。正式判断需要真实 Codex 子线程和执行记录。

详细说明：[Codex Native Subagents V0.2](docs/CODEX_NATIVE_SUBAGENTS_V02.md)。

### 7. 本地安全 Skill 安装器

- 支持本地预览、安装、文件完整性校验、升级、回滚、卸载。
- 拒绝覆盖不归安装器管理或已被外部改动的 Skill。
- 不从网络自行下载代码、不执行 Skill 内部脚本、不主动上传密钥。
- 卸载时保留归档；回滚依赖此前确实存在的备份。
- 这不是病毒扫描器或数字签名校验，现有 CLI 不等于一键 GUI；候选图形界面仍需真实环境验收。

## 二、朋友如何安装（Windows 11 / macOS / Linux）

前置条件：安装 [Git](https://git-scm.com/downloads) 与 Python 3.11 或更新版本；使用有权限的本机终端。先自行阅读仓库内容，安装操作会修改当前用户的本地 Codex 文件。

### 第一步：下载公开仓库

```powershell
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git
cd aka-cristi-skills
```

### 第二步：预览 CHEF 全局规则和主 Skill

```powershell
python -m tools.chef_global_rules preview
python -m tools.skill_installer preview skills/chef-orchestrator --target codex
```

### 第三步：明确授权本地安装

```powershell
python -m tools.chef_global_rules install --apply
python -m tools.skill_installer install skills/chef-orchestrator --target codex --apply
python -m tools.skill_installer install skills/verified-change-loop --target codex --apply
python -m tools.skill_installer install skills/feature-journey-map --target codex --apply
python -m tools.skill_installer install skills/skill-evaluation-gate --target codex --apply
```

### 第四步：可选安装四个原生 Codex 角色

```powershell
python -m tools.codex_subagents preview
python -m tools.codex_subagents install --apply
python -m tools.codex_subagents verify
```

### 第五步：检查安装文件

```powershell
python -m tools.chef_global_rules verify
python -m tools.skill_installer verify chef-orchestrator --target codex
python -m tools.skill_installer verify verified-change-loop --target codex
```

这些命令检查**配置与文件**，并不证明 Codex 已调用 Skill 或启动四个 Agent。请重新开启 Codex 会话，测试真实委派，并保存实际执行证据。

若本机已安装并登录 Codex CLI，可以执行严格的四角色运行验收（可能消耗 Codex 使用额度）：

```powershell
codex login status
python -m tools.verify_four_agents --timeout 600 --out four-agent-report.json
```

验收结果应区分 `PASS`、`FAIL`、`INCONCLUSIVE`、`NOT_RUN`。没有真实线程证据就不能声称通过。详见：[四 Agent 真实运行验收](docs/FOUR_AGENT_RUNTIME_ACCEPTANCE.md)。

## 三、真实能力与限制

| 项目 | 当前边界 |
| --- | --- |
| 公开 Skill 文件与 CLI 安装器 | 仓库已提供；可阅读、下载与本地运行 |
| CHEF 全局规则安装 | 提供安全预览、受管理区块安装与校验 |
| 四个原生 Codex 角色配置 | 提供 TOML 与安装/校验工具 |
| 自动检测并修复所有真实项目错误 | **不能保证**；仍依赖工具、权限、项目情况与实际测试 |
| 自动连接 Hermes、Claude、其他品牌 Agent | **未实现通用连接**；需要单独的 API / MCP / CLI 适配 |
| 四 Agent 在用户真实 Codex 环境运行通过 | **须在已登录的真实 Codex 设备上单独验证** |
| 自动把成功经验发布为 Skill | 有评估流程，**不是无需审核的自动发布系统** |
| 全设备自动同步与一键图形安装 | 尚非此公开发行版的已验证功能 |

## 四、安全原则

- 不覆盖现有私人规则或未托管 Skill；先预览，再明确执行。
- 不上传密码、API Key、私人对话和客户数据。
- 不将本地测试、模拟输出或 Agent 自述误判为真实运行结果。
- 不自动进行付费操作、权限变更、生产发布、删除数据等高风险操作。
- 所有跨平台 Agent 连接都需要独立授权和真实验收。

## 五、项目方向

以 **DESIGN × CODE × AI × AUTOMATION × BUSINESS** 为方向，逐步完善更友好的安装体验、跨 Agent 适配、可审计任务日志、技能评估与持续维护。未完成的能力只列为规划，不宣称已交付。

---

**AKA.CRISTI · CREATE BEAUTIFULLY. BUILD INTELLIGENTLY. AUTOMATE EVERYTHING REASONABLE.**
