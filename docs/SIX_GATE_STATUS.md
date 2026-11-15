# CHEF 六项验收状态

2026.11.16 已核查：PR [#14](https://github.com/2ndforcecrew/aka-cristi-skills/pull/14) 已合并到 main；main `573fae8` 的 [CI 成功](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43726640530)。Windows GUI EXE、空用户目录启动与来源验签均已通过云端验证。六项发布验收仍分别保留阻塞，不把工程里程碑等同全部完成。原文件与历史提交均保留。

[成长记录 · 2026.11.16](GROWTH_JOURNAL_2026-11-16.md) · [公开成长网站最新进展](https://aka-cristi-growth-journal-f6dh09.v2.appdeploy.ai/#latest)

以下保留前一轮各项实现与验收限制；最新进展以上述核查及同步记录为准。

| Issue | 本次实际开发 | 实际证据与剩余阻塞 |
|---|---|---|
| #8 安全复核 | 修复路径重定向、Windows reparse 检查与非确定摘要；原始大文件/链接读取前检查；独立逐项复核新扫描的 23 条 | 两次实际扫描均 DO_NOT_INSTALL，第二次因历史报告自包含而覆盖不完整；原外部 24 项/版本/模式/commit 缺失，BLOCKED |
| #9 软件包签名 | 确定性 ZIP、SHA256/source commit、GitHub OIDC provenance、固定身份验签、拒绝未验签远程执行 | [候选签名与验签成功](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43720719566)，源 bd1edff；正式版本、安全依赖与跨平台 installer 下载/回滚完整验收未完成，Issue 保持开放 |
| #10 Windows GUI | Tk 实际窗口、预览差异、明确同意、后台进度、取消、文件验证、受保护恢复与冲突处理 | Linux 虚拟显示和 Windows CI 的真实 Tk 控件 smoke 已运行；不是干净 Windows 11 的独立用户验收；已增加独立 EXE 构建/来源签名/云端 smoke 流程，实际产物见 PR Checks；缺 Codex 自动安装/远程 GUI 获取未完成，BLOCKED |
| #11 多宿主适配 | Codex / Claude 项目级文件生命周期；安装、加载、调用、完成分开；Hermes/ChatGPT 明确阻塞 | Claude 隔离文件测试通过，真实 Claude 调用 NOT_RUN；Hermes/ChatGPT 未实现，BLOCKED |
| #12 外部用户验收 | 三平台首次安装计划、匿名证据模板、附件摘要检查与禁止自报 PASS 的文档预检 | 没有独立 Windows/macOS/Linux 测试者和真实宿主完成证据，BLOCKED |
| #13 四个真实 Codex Subagents | 严格 call→result→child ID→parent→exact role→completion/reply；拒绝旧格式、不相关线程、伪标签等 | [实际云端尝试](evidence/codex-cloud-attempt.json)退出 1，无根/子线程证据，BLOCKED；synthetic fixtures 不充当真实验收 |

## 可复核证据

- 基线 main `63c4339`：[三平台 CI 成功](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43711869961)。
- 开发初轮：[CI 43720722718](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43720722718)。117 项测试在 Windows 全部通过，Linux 跳过 Windows/显示限定项；Linux Xvfb Tk 控件 smoke 通过。macOS 的测试临时目录经过 `/var` 系统 symlink 被安全拒绝，改成显式 canonical 测试路径；不放宽生产的 symlink 拒绝。Windows 预期拒绝远程来源后 LASTEXITCODE=1 被 pwsh 传播，已重置预期失败状态，避免错误的 CI 失败。[修正后的三平台复验已通过](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43721083323)。后续 GUI 打包提交的最终复验见 PR Checks。
- 已实际签名的 bd1edff 候选：[artifact](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43720719566/artifacts/14163962744)，保留到 2026-12-15；下载可能要求 GitHub 登录。内部 ZIP SHA256 `e85cfe019b7aa8618b9c8adc9038271235e3c6024c31caa6b707640449b412a1`。artifact 外层 ZIP 摘要与内部安装包摘要不同。后续提交有独立候选，不可混用上述 pin。
- [完整扫描元数据](evidence/skillspector-runs.json)、[基线 JSON](evidence/skillspector-baseline-report.json)、[独立逐条复核](evidence/skillspector-baseline-triage.json)、[安全面与剩余限制](SECURITY_REVIEW_2026-11-15.md)。
- 本地复验：`python -m unittest discover -s tests -v`（最新本地 124 tests, 3 skips；追加 CRLF/空行原字节保留与冻结数据打包测试）、`python -m compileall -q tools tests`、`git diff --check`。这些结果不证明外部用户成功安装。

## 成长记录网站

2026.11.16 用户另行授权更新成长记录网站，现已保留 CASE 001–016 并追加 CASE 017–022，加入 GUI、来源签名、CI 与 main 合并证据，公开显示真实失败和剩余阻塞。该网站进度同步不属于“六项全部完成”通知；完整发布验收当前仍为 **BLOCKED**。

下一步真实证据：原扫描材料脱敏复核；标准用户 Windows 11 GUI/依赖/卸载；非 Codex 实际调用；三平台独立用户；经过诊断的 Codex 四角色 live run。只在可用且授权的环境进行，不要求启动已关机电脑。

追加：全局 AGENTS.md 安装现在按原始 newline 读取并只在原文后追加，保留 CRLF 与尾部空行；GUI 预览/事务校验使用同一个 append_block 计算，已有规则的原始字节不再被隐藏归一化。回归先失败复现、修正后通过。

GUI 构建首轮 [43721677476](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43721677476)：独立 EXE 构建、空 profile 的实际窗口 smoke 和 OIDC attestation 成功，但 Windows gh 版本探测步骤失败，未上传候选。已改为完整收集原生 stdout 再判断退出码，最终构建及精确身份验签需看后续 PR Checks；不能将这次失败称为验签 PASS。另补测 CRLF managed block 的兼容判断，保持原字节不变。

## 最终云端验证链接补充

- [三平台 CI / 124 项测试版本](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43721892705)：success。
- [确定性 ZIP 签名及来源验签](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43721887652)：success。
- [独立 Windows GUI EXE 构建、空 profile 启动、来源验签](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43721887589)：success。
- [下载 GUI 开发候选](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43721887589/artifacts/14164932492)：可能要求 GitHub 登录，产物保留至 2026-12-15；不是 Authenticode 或完整用户验收。
