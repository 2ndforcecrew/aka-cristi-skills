# 成长记录同步 · 2026-11-16

[查看成长记录网站](https://aka-cristi-growth-journal-f6dh09.v2.appdeploy.ai/#latest)

本次用户授权同步 GitHub 与现有成长网站；保留 CASE 001–016，新增 CASE 017–022，沿用原网址。网站部署版本 `1794768218664` 已返回 READY，桌面/手机 QA 未报告前端、网络或后端错误。这是进展记录更新，不是六项全部通过通知。

## 核查基准

- PR [#14](https://github.com/2ndforcecrew/aka-cristi-skills/pull/14) 已合并，merge commit `8e2b5c5`。
- 本次核查 main：`573fae8d67bcb45e46ab7a426b4ef268f41dade4`；[最新 main CI 成功](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43726640530)。
- [124 项测试所在开发版本三平台 CI](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43721892705)成功；本地该轮 124 tests、3 platform/display skips，不把跨平台次数相加作为新测试数量。
- English、简体中文、繁體中文、日本語、한국어、Français README 已进入 main，保留后续翻译提交。
- Issues #8–#13 当前均开放；没有将 CI 或文件安装成功当作全部发布验收通过。

## CASE 017 · 六项开发合并：从候选分支进入 main

**状态：MERGED / MAIN CI PASS**

PR #14 已合并，安全安装、Windows GUI、来源验签、适配与线程证据工具已进入主分支；六份语言说明也已更新。

截至 2026.11.16 核查，main 为 573fae8，最新 main CI 成功。本地上一轮运行 124 项测试，3 项因平台/显示条件跳过。代码合并与持续集成通过是工程里程碑，六项发布验收仍需各自证据。

- [PR #14 · 已合并](https://github.com/2ndforcecrew/aka-cristi-skills/pull/14)
- [最新 main CI](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43726640530)

## CASE 018 · Windows GUI：独立 EXE 与真实窗口启动通过

**状态：EXE BUILD / SMOKE PASS**

从命令行安装升级为独立图形程序：规则差异预览、明确同意、进度、取消、文件校验和受保护撤销已实现。

Windows 云端真实构建 EXE，在空用户目录启动窗口并确认不写用户配置；仅打包九个公开数据文件。来源签名验证通过；尚无 Authenticode 证书。干净 Windows 11 标准用户、朋友首次安装与缺 Codex 的依赖安装仍待独立验收。

- [Windows GUI 验证](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43721887589)
- [下载 EXE 开发候选](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43721887589/artifacts/14164932492)
- [界面与验收边界](https://github.com/2ndforcecrew/aka-cristi-skills/blob/main/docs/WINDOWS_GUI.md)

## CASE 019 · 来源签名：先证明是谁构建，再运行安装包

**状态：OIDC PROVENANCE VERIFIED**

确定性 ZIP、SHA-256 清单、固定仓库与工作流身份的 GitHub OIDC 来源验签已在云端实际通过。

归档和 EXE 候选分别构建、签名并验证 source commit/ref 与 publisher workflow。未验签远程 bootstrap 默认阻塞，不再自动执行未验证的 Codex 下载脚本。产物是开发候选，不是已通过所有安全与用户验收的正式版本；下载可能要求 GitHub 登录，当前产物保留至 2026.12.15。

- [来源包签名与验签](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43721887652)
- [验签方法](https://github.com/2ndforcecrew/aka-cristi-skills/blob/main/docs/RELEASE_VERIFICATION.md)

## CASE 020 · 安全复核：修复真实问题，也保留不通过结果

**状态：FIXES VERIFIED / SECURITY BLOCKED**

修复符号链接与 Windows reparse 路径重定向、备份路径、枚举摘要不稳定，以及规则 CRLF/尾部空行保留问题。安全扫描结果未被包装成通过。

SkillSpector 2.12.0 无 LLM 基线扫描为 56 分、23 项、DO_NOT_INSTALL，并完成逐条独立复核；修正快照全仓扫描为 100 分、160 项且覆盖不完整，其中 115 项来自之前的报告与复核文档。该扫描自包含问题需定义范围后再验证。原先外部 67 分、24 项原始报告仍缺失，不能宣称全部误报。

- [安全复核与剩余风险](https://github.com/2ndforcecrew/aka-cristi-skills/blob/main/docs/SECURITY_REVIEW_2026-11-15.md)
- [实际扫描记录](https://github.com/2ndforcecrew/aka-cristi-skills/blob/main/docs/evidence/skillspector-runs.json)

## CASE 021 · 适配与外部验收：安装、加载、调用分开记录

**状态：CLAUDE FILE ADAPTER / LIVE NOT_RUN**

新增 Claude 项目级 Skill 文件适配：检查、预览、安装、校验与卸载；保留已有文件与冲突保护。

Claude 隔离目录文件生命周期测试通过，真实 Claude 加载/调用尚未验证。Hermes 与 ChatGPT 适配继续标为 BLOCKED。已建立 Windows/macOS/Linux 首次安装计划和匿名证据门禁；没有独立外部测试者时，不用模拟测试冒充用户验收。

- [各宿主能力矩阵](https://github.com/2ndforcecrew/aka-cristi-skills/blob/main/docs/HOST_CAPABILITY_MATRIX.md)
- [外部验收计划](https://github.com/2ndforcecrew/aka-cristi-skills/blob/main/docs/EXTERNAL_UAT.md)

## CASE 022 · 四个真实 Subagents：严格关联，保留云端失败

**状态：RUNTIME BLOCKED / NO FALSE PASS**

验证器现在要求 call → result → child ID → parent_thread_id → 精确角色 → 完成回复的完整证据链，拒绝角色标签、自述与历史无关线程。

已在云端使用 Codex CLI 0.167.0-alpha.4 实际尝试一次，只使用临时公开角色配置、不修改全局账号配置。该次退出码为 1，没有可归属的根/子线程及完成事件；未保留 stderr，因此不臆测根因。四角色验收仍为 BLOCKED，与历史 CASE 013 的四次 spawn 观察分开记录。

- [实际云端尝试证据](https://github.com/2ndforcecrew/aka-cristi-skills/blob/main/docs/evidence/codex-cloud-attempt.json)
- [严格线程关联规则](https://github.com/2ndforcecrew/aka-cristi-skills/blob/main/docs/FOUR_AGENT_EVIDENCE_V03.md)

## 同步范围与后续

本次仅更新成长记录和 GitHub 文档，不修改运行代码、不修改账号/权限或密钥，不访问关机电脑。原有网站历史和代码提交保留。来源签名为 GitHub OIDC provenance，不能标为 Authenticode 或正式发布许可。

仍需：原始安全扫描报告脱敏复核、干净 Windows 11 标准用户与首次安装、真实 Claude/其他宿主调用、三平台独立用户验收、可归属的四个 Codex 子线程完成证据。完整状态见 [六项验收状态](SIX_GATE_STATUS.md)。

