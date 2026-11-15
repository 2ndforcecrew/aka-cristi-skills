# CHEF 六项验收状态

这是开发交付记录，不是“六项完成通知”。工作分支 `feat/chef-six-gates-20261115`，PR [#14](https://github.com/2ndforcecrew/aka-cristi-skills/pull/14)。原文件全部保留，没有合并 main、发布 GitHub Release、部署生产网站或访问已关闭的电脑。

| Issue | 本次实际开发 | 实际证据与剩余阻塞 |
|---|---|---|
| #8 安全复核 | 修复路径重定向、Windows reparse 检查与非确定摘要；原始大文件/链接读取前检查；独立逐项复核新扫描的 23 条 | 两次实际扫描均 DO_NOT_INSTALL，第二次因历史报告自包含而覆盖不完整；原外部 24 项/版本/模式/commit 缺失，BLOCKED |
| #9 软件包签名 | 确定性 ZIP、SHA256/source commit、GitHub OIDC provenance、固定身份验签、拒绝未验签远程执行 | [候选签名与验签成功](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43720719566)，源 bd1edff；正式版本、安全依赖与跨平台 installer 下载/回滚完整验收未完成，Issue 保持开放 |
| #10 Windows GUI | Tk 实际窗口、预览差异、明确同意、后台进度、取消、文件验证、受保护恢复与冲突处理 | Linux 虚拟显示和 Windows CI 的真实 Tk 控件 smoke 已运行；不是干净 Windows 11 的独立用户验收；独立 EXE/缺依赖自动安装/远程 GUI 获取未完成，BLOCKED |
| #11 多宿主适配 | Codex / Claude 项目级文件生命周期；安装、加载、调用、完成分开；Hermes/ChatGPT 明确阻塞 | Claude 隔离文件测试通过，真实 Claude 调用 NOT_RUN；Hermes/ChatGPT 未实现，BLOCKED |
| #12 外部用户验收 | 三平台首次安装计划、匿名证据模板、附件摘要检查与禁止自报 PASS 的文档预检 | 没有独立 Windows/macOS/Linux 测试者和真实宿主完成证据，BLOCKED |
| #13 四个真实 Codex Subagents | 严格 call→result→child ID→parent→exact role→completion/reply；拒绝旧格式、不相关线程、伪标签等 | [实际云端尝试](evidence/codex-cloud-attempt.json)退出 1，无根/子线程证据，BLOCKED；synthetic fixtures 不充当真实验收 |

## 可复核证据

- 基线 main `63c4339`：[三平台 CI 成功](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43711869961)。
- 开发初轮：[CI 43720722718](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43720722718)。117 项测试在 Windows 全部通过，Linux 跳过 Windows/显示限定项；Linux Xvfb Tk 控件 smoke 通过。macOS 的测试临时目录经过 `/var` 系统 symlink 被安全拒绝，改成显式 canonical 测试路径；不放宽生产的 symlink 拒绝。Windows 预期拒绝远程来源后 LASTEXITCODE=1 被 pwsh 传播，已重置预期失败状态，避免错误的 CI 失败。最终复验见 PR Checks。
- 已实际签名的 bd1edff 候选：[artifact](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43720719566/artifacts/14163962744)，保留到 2026-12-15；下载可能要求 GitHub 登录。内部 ZIP SHA256 `e85cfe019b7aa8618b9c8adc9038271235e3c6024c31caa6b707640449b412a1`。artifact 外层 ZIP 摘要与内部安装包摘要不同。后续提交有独立候选，不可混用上述 pin。
- [完整扫描元数据](evidence/skillspector-runs.json)、[基线 JSON](evidence/skillspector-baseline-report.json)、[独立逐条复核](evidence/skillspector-baseline-triage.json)、[安全面与剩余限制](SECURITY_REVIEW_2026-11-15.md)。
- 本地复验：`python -m unittest discover -s tests -v`（117 tests, 3 skips）、`python -m compileall -q tools tests`、`git diff --check`。这些结果不证明外部用户成功安装。

## 成长记录网站

待发布条目：新增六项验收门禁、四类安全修复、候选包真实签名证据、GUI/Claude 文件适配和严格线程检查；保留真实失败与阻塞。六项全部独立验证前不发布完成通知，也不将草稿部署到成长网站。当前总状态 **BLOCKED**。

下一步真实证据：原扫描材料脱敏复核；标准用户 Windows 11 GUI/依赖/卸载；非 Codex 实际调用；三平台独立用户；经过诊断的 Codex 四角色 live run。只在可用且授权的环境进行，不要求启动已关机电脑。
