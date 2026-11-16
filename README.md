# AKA.CRISTI Skills

**让 AI 协作经验变成可安装、可验证、可复用的工作能力。**

> **当前公开版本：[v1.0.0-beta.2（Beta 测试版）](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.2)** · [反馈问题](https://github.com/2ndforcecrew/aka-cristi-skills/issues) · [开发与验收记录](docs/CODEX_V1_RELEASE_ACCEPTANCE.md)
>
> 面向 Codex 的 CHEF 主厨工作规则、4 个 Skills、4 个原生 Codex 角色和安全安装器。**Beta 可以下载测试，但不是已完成外部验收的稳定版本。** Windows EXE 具有 GitHub 来源证明，但**没有 Authenticode 签名**。

## 01 · 选择安装方式

| 系统 / 使用方式 | 推荐方法 | 需要什么 |
| --- | --- | --- |
| **Windows 11** | [下载图形安装器](https://github.com/2ndforcecrew/aka-cristi-skills/releases/download/v1.0.0-beta.2/AKA-CRISTI-CHEF-Setup.exe) | 独立测试环境、Codex CLI |
| **Windows 11 命令行** | 下方 PowerShell 命令 | Git、Python 3.11+ |
| **macOS（Apple Silicon / Intel）** | 下方 Terminal 命令 | Git、Python 3.11+ |
| **Ubuntu / Debian / 其他 Linux** | 下方 Bash 命令 | Git、Python 3.11+ |
| **让 Codex / 其他 Agent 协助安装** | 下方 Agent 安装指令 | Agent 有终端权限，用户批准本地写入 |

**当前版本声明：** 本仓库已正式公开发布 **Codex 优先的 `v1.0.0-beta.2` Beta**。网上引用的 `DO_NOT_INSTALL / 23 findings / BLOCKED` 是**旧版第三方扫描或历史发布门禁记录**，并非本版本作者发出的禁止安装通知，也不能直接证明当前版存在 23 个漏洞。已通过跨平台 CI、Windows EXE 构建及 GitHub 来源证明；外部用户安装和真实四 Agent 联动仍需单独验收。可查看[历史扫描说明](docs/SECURITY_REVIEW_2026-11-15.md)与[当前 Beta 发布页](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.2)。

**v1.0.0-beta.2 已包含跨平台一键命令安装器 `tools/quick_install.py`。** Windows EXE 是另一个图形入口；命令安装器适用于 Windows、Mac 和 Ubuntu/Linux。

统一安装入口：`python -m tools.quick_install --interactive`。**先展示全部变更，用户输入 `INSTALL` 后才安装并验证** CHEF 全局规则、4 个角色和 4 个 Skills。默认不带参数时仅预览；也支持手动使用 `--apply`。这个安装器不会启动模型或消耗 Codex 推理额度。

### Windows 11 · 图形安装（最适合朋友）

1. 从 [GitHub Release](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.2) 下载 `AKA-CRISTI-CHEF-Setup.exe`。
2. 在独立的 Windows 11 测试账户或虚拟机中，先核验来源和 SHA-256，再打开 EXE。
3. 点击 **检查与预览**，确认现有 `AGENTS.md` 不会被覆盖。
4. 阅读差异后明确同意，再点击 **安装并校验文件**；需要撤销时使用内置受保护恢复功能。

**Beta EXE 的 SHA-256：**

```powershell
Get-FileHash "$env:USERPROFILE\Downloads\AKA-CRISTI-CHEF-Setup.exe" -Algorithm SHA256
```

预期 SHA-256 应与 **本次 `v1.0.0-beta.2` 的 `gui-candidate-manifest.json`** 对应。不要沿用上一版 Hash；必须先验证清单的 GitHub 来源证明。

核对 Hash 不能代替验证发布者身份。可从 [Release](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.2) 下载 `gui-provenance.sigstore.json`，在两个文件所在目录使用 **GitHub CLI 2.102.0+** 进行来源验证：

```powershell
$commit = (gh api repos/2ndforcecrew/aka-cristi-skills/git/ref/tags/v1.0.0-beta.2 --jq '.object.sha').Trim()
gh attestation verify .\AKA-CRISTI-CHEF-Setup.exe --bundle .\gui-provenance.sigstore.json --repo 2ndforcecrew/aka-cristi-skills --signer-workflow 2ndforcecrew/aka-cristi-skills/.github/workflows/beta-release.yml --signer-digest $commit --source-digest $commit --source-ref refs/heads/main --predicate-type https://slsa.dev/provenance/v1
```

验证失败或遇到系统安全策略限制时**停止安装**；不要为了运行 Beta 关闭系统保护。

### Windows 11 · PowerShell 一条命令

先安装 Git、Python 3.11+；把下面**整行**复制到 PowerShell。命令将下载固定的 Beta Tag 并展示全部安装预览；只有输入 `INSTALL` 才会实际写入：

```powershell
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git; if ($LASTEXITCODE -ne 0) { throw "下载失败" }; cd aka-cristi-skills; git checkout v1.0.0-beta.2; if ($LASTEXITCODE -ne 0) { throw "版本校验失败" }; py -3 -m tools.quick_install --interactive
```

如果希望分开进行预览和安装，可以在确认预览后执行：

```powershell
py -3 -m tools.quick_install --apply
```

**说明：** 命令检出固定的 `beta.2` Tag，请审查源码和来源。如果目录已经存在，不要重新 clone；进入原目录检查当前修改后再操作。

### Mac · Terminal 安装（M 系列 / Intel 都适用）

需要 Git 和 Python **3.11 或更新版本**。打开「终端 Terminal」，复制以下命令：

**① 下载并预览：**

```bash
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git && cd aka-cristi-skills && git checkout v1.0.0-beta.2 && python3 -m tools.quick_install --interactive
```

**② 如想分开执行，先预览，再明确授权安装：**

```bash
python3 -m tools.quick_install --apply
```

**③ 检查版本：**

```bash
python3 --version && git describe --tags --exact-match
```

Mac 安装的是 **Codex Skills + AGENTS.md + 自定义角色配置**；Windows `.exe` **不能在 macOS 使用**。这里不会安装 Codex 本体，也不保证 Codex 已登录或真的生成四个子 Agent。

### Ubuntu / Debian / Linux · Bash 一条命令

确保已安装 Git 与 Python 3.11+；Ubuntu 默认 Python 可能比 3.11 旧，需先使用系统认可的软件源安装适用版本，**不要擅自替换系统 Python**。

**① 下载并预览：**

```bash
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git && cd aka-cristi-skills && git checkout v1.0.0-beta.2 && python3 -m tools.quick_install --interactive
```

**② 也可以分开执行明确授权安装：**

```bash
python3 -m tools.quick_install --apply
```

**③ 不修改用户现有配置的隔离测试：**

```bash
python3 -m tools.quick_install --codex-home /tmp/aka-chef-test-codex --skills-root /tmp/aka-chef-test-skills
```

建议使用本机普通用户账号运行，**不需要 `sudo`，也不应写进 root 的 Codex 配置**。Linux/macOS 还需要自行安装和授权 Codex CLI 才能实际调用模型。

### 给 Agent 的安装指令（可复制到 Codex）

> 请检查本机是否安装 Git、Python 3.11+ 及 Codex CLI；确认操作系统。阅读 https://github.com/2ndforcecrew/aka-cristi-skills 的 README，检出固定测试版 `v1.0.0-beta.2`（包含统一安装器），执行 `python3 -m tools.quick_install --interactive`（Windows 使用 `py -3`），展示完整预览；**我输入 `INSTALL` 同意后**再自动安装和验证，并检查 `FILES_VERIFIED`。若有冲突或来源异常，停止，不覆盖我的现有 `AGENTS.md`、Skills、凭据或 Agent 文件。记录版本、修改和校验结果，不把文件安装成功冒充真实 Agent 调用。

**不支持的安装捷径：** 目前尚未验证 `npx skills add 2ndforcecrew/aka-cristi-skills` 是可用的官方入口。**粘贴仓库链接给 Agent 不等于自动安装成功**，必须验证真实文件与运行环境。

## 02 · 项目提供什么？

| 模块 | 作用 |
| --- | --- |
| [CHEF Orchestrator](skills/chef-orchestrator/SKILL.md) | 按 Inspect → Plan → Build → Test → Review → Deliver 统筹任务和 Agent |
| [Verified Change Loop](skills/verified-change-loop/SKILL.md) | 复现、最小修复、重跑测试、独立验收 |
| [Feature Journey Map](skills/feature-journey-map/SKILL.md) | 检查真实用户操作路径与异常恢复 |
| [Skill Evaluation Gate](skills/skill-evaluation-gate/SKILL.md) | 使用实际证据决定是否升级或发布 Skill |
| [CHEF 全局规则](docs/CHEF_GLOBAL_AND_MULTIAGENT.md) | 追加受管理区块到 Codex `AGENTS.md`，保留原始内容及备份 |
| [四角色配置](docs/CODEX_NATIVE_SUBAGENTS_V02.md) | `aka_research`、`aka_coding`、`aka_qa`、`aka_automation` |
| [安全安装器](tools/quick_install.py) | 默认预览；授权后安装及文件校验；冲突阻止写入 |

这是一套 **Agent 工作规则与 Skill 工具**，不是自动拥有所有 Agent 权限的独立大脑。是否可以调用其他服务，取决于真实连接、凭据、用户权限与宿主支持程度。

## 03 · 验证、卸载与常见问题

**本地安装验证：**

```bash
python3 -m tools.chef_global_rules verify
python3 -m tools.codex_subagents verify
python3 -m tools.skill_installer verify chef-orchestrator --target codex
```

**删除自己安装的受管理配置（不会强行删除用户原有文件）：**

```bash
python3 -m tools.chef_global_rules uninstall --apply
python3 -m tools.codex_subagents uninstall --apply
python3 -m tools.skill_installer uninstall chef-orchestrator --target codex --apply
```

其余三个 Skills 也分别通过 `tools.skill_installer uninstall 技能名称 --target codex --apply` 卸载；安装器对未受管理或已经修改的文件会拒绝覆盖/删除。旧版本的受管理文件可按实际备份执行 `rollback`。

**常见问题：**

- **安装命令提示 Git / Python 不存在：** 先独立安装对应依赖，再检查 `git --version` 与 `python3 --version`（Windows 可用 `py -3 --version`）。
- **预览或安装出现 CONFLICT：** 现有自定义规则或配置与目标相冲突；检查差异，不要删除私人数据来强制通过。
- **显示 FILES_VERIFIED，但 Codex 没调用 Skill：** 文件校验与 Agent 运行是两回事。重启 Codex，使用已授权的真实环境单独验收。
- **能否一键连接 Hermes、Claude 或 ChatGPT？** 不能承诺。这些宿主仍需要独立适配与真实授权验收。
- **能否在正式工作电脑直接安装 Beta？** 建议先在独立测试环境使用，核实备份和撤销流程后再决定。
- **SkillSpector 是否必须安装？** 不需要。它是可选第三方审计工具，不是本仓库运行依赖或强制发布步骤。

## 04 · 真实状态与版本限制

- **已公开：** [v1.0.0-beta.2 GitHub Release](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.2)，含 Windows EXE、源码 ZIP、SHA-256 与 GitHub 来源证明。
- **已完成工程 CI：** Windows/macOS/Ubuntu 回归、Windows EXE 构建和来源证明。测试通过不等于每台电脑都能安装。
- **未完成：** 外部 Windows 11 首次安装 UAT、当前发布版本四个真实子 Agent 的完整验收、独立 MCP 权限隔离验证、Windows Authenticode 证书签名。
- **实验功能：** Personal AI Workspace 的真实 OAuth、用户私人仓库创建及多设备同步；不能以模拟测试声称已在真实账户通过。
- **跨宿主：** Claude 项目级文件适配范围有限；Hermes 和 ChatGPT 的完整集成尚未验证。

[发布验收标准](docs/CODEX_V1_RELEASE_ACCEPTANCE.md) · [Windows GUI 说明](docs/WINDOWS_GUI.md) · [宿主兼容情况](docs/HOST_CAPABILITY_MATRIX.md) · [四 Agent 验收方法](docs/FOUR_AGENT_EVIDENCE_V03.md) · [外部用户测试计划](docs/EXTERNAL_UAT.md)

## 05 · 开发验证

在已信任且审查过的仓库中：

```bash
python3 -m unittest discover -s tests -v
python3 -m unittest discover -s tests -p 'test_quick_install.py' -v
```

测试只验证本地流程，不调用真实 Codex 模型。任何需要网络访问、付费或外部发布的动作均需单独授权。

---

**AKA.CRISTI · CREATE BEAUTIFULLY. BUILD INTELLIGENTLY. AUTOMATE EVERYTHING REASONABLE.**
