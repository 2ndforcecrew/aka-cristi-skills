# 可验证候选包（Issue #9）

本分支实现候选打包与验签工具；**没有发布正式版本，没有声称已经生成真实签名**。GitHub Actions 普通 CI 的成功不代表签名验收通过。候选签名工作流仅在本次独立开发分支 push 或维护者手动运行时触发；本次不自动合并或发布。

## 信任与产物

`tools.release_package` 只打包指定的 40 位 Git commit 中已提交的普通文件，不读取未提交内容、Git 内部文件或用户家目录。固定文件顺序、1980 ZIP 时间戳、Unix 模式与 ZIP_STORED 字节格式，使相同提交与版本的输出可重复。清单记录版本、源提交、SHA-256、Python 要求与目标平台；平台字段表示源码工具的目标范围，不表示真实用户验收通过。

`.github/workflows/release-candidate.yml` 仅允许本仓库 `feat/chef-six-gates-20261115` 的 push，以及 `main` 或该分支上的手动运行。固定 SHA 的官方 Actions 对 ZIP 和清单生成 GitHub OIDC / Sigstore SLSA provenance，并保存为 30 天有效的 Actions 候选产物。签名只证明来源，不能替代代码审查、恶意代码扫描或独立验收。签名权限仅存在于此候选 job；无 PR 签名、无 `contents: write`、无发布 Release 或部署步骤。

## 打包与核验

从已经审查的 checkout 运行；不要先执行 ZIP 内的 verifier 来验证该 ZIP 自己。

```sh
python -m tools.release_package --commit <40位已审查提交> --version 0.3.0-rc.1 --out ./candidate
python -m tools.verify_release ./candidate/aka-cristi-skills-0.3.0-rc.1.zip --expected-commit <40位已审查提交> --expected-sha256 <已核实的64位SHA256> --source-ref refs/heads/main --bundle ./candidate/provenance.sigstore.json --extract-to ./verified-source
```

核验需要官方 GitHub CLI **2.102.0+**。`gh attestation verify` 必须同时验证仓库 `2ndforcecrew/aka-cristi-skills`、完整工作流 `.github/workflows/release-candidate.yml`、signer digest、source digest 及精确 source ref。工具检查 `gh` 的退出状态与非空 JSON 验证结果，并再次核对 archive digest；不复制原始签名输出或凭据到报告。包被篡改、旧提交、缺失/错误签名、未知输出格式、旧版/缺失 `gh`、工具超时都会关闭安装路径。

开发分支候选的 `--source-ref` 应明确改为 `refs/heads/feat/chef-six-gates-20261115`。

SHA-256 与提交 pin 必须来自审查决定或已经验证的候选信息。与 ZIP 一起下载的任意清单本身不构成信任；该工作流也对清单生成 attestation。缺省省略 `--bundle` 时由官方 `gh` 查询该制品的 attestation；不自行接受下载重定向或执行网络内容。

Python 3.11+。ZIP 解包限制总大小/条目数，拒绝路径穿越、符号链接、重复与大小写冲突名称、Windows 保留名或非法路径，并仅创建新目录。先验证完整 ZIP，再解包同一 SHA-256 字节快照；失败不替换原始目录。

## Windows 引导

现有 `install.ps1` 保留。提供经审查的本地 `-SourceDirectory` 明确表示信任本地源码，不称为签名发布。原先从 `main` 下载 ZIP 后直接运行 Python 的默认路径现在 **BLOCKED**，直到有通过验签的候选。

```powershell
# 现有本地源码预览；无文件修改
.\install.ps1 -SourceDirectory .

# 使用经审查的 install.ps1 + 同目录 tools/verify_release.py
# 所有 pin 都应替换成已核实值；不要直接复制占位符运行
.\install.ps1 -ArchivePath C:\Downloads\aka-cristi-skills-0.3.0-rc.1.zip -ExpectedCommit <COMMIT> -ExpectedSha256 <SHA256> -ProvenanceBundle C:\Downloads\provenance.sigstore.json
```

验签通过后才执行解包源码与配置预览；`-Apply` 仍独立授权写入。缺少 Python 时，archive 路径要求先独立安装 Python。经审查的本地 source 路径保留明确授权的 winget Python 安装，不使用 hash bypass。未经校验的 Codex 网络安装脚本执行已经禁用，即使存在 `-InstallDependencies` 也会提示独立安装后重试。

隔离测试可同时指定 `-CodexHome <临时目录> -SkillsRoot <临时目录>`。不指定 `-SkillsRoot` 才使用当前用户 `.agents/skills`；`-CodexHome` 本身从不代表 Skills 目录也被隔离。

## 测试与仍待验证

`tests/test_release.py` 验证真实本地 Git 快照、重复构建、篡改/旧提交、缺失 bundle、解包越界与不覆盖；外部 `gh` 过程契约测试明确为 synthetic，不代表真实加密签名验证。`tests/test_release_bootstrap.py` 只检查脚本安全约束，Windows CI 另做 PowerShell 解析与隔离运行。

仍待：真实候选 attestation 生成及核验、标准用户 Windows 11 验签安装、坏签名与中断下载真实流程、外部用户验收。不存在正式版本或可信签名时保持 BLOCKED，不回退至未经校验的网络执行。

## 官方依据（2026-11-15 核对）

- [GitHub CLI attestation verify 手册](https://cli.github.com/manual/gh_attestation_verify)
- [GitHub 官方 actions/attest](https://github.com/actions/attest)
- [GitHub CLI 工作流身份前缀匹配安全公告：2.102.0 修复](https://github.com/cli/cli/security/advisories/GHSA-wjmr-j3rp-mh2g)

本工具要求修复后的 `gh`，避免旧版把其他同前缀工作流误认为指定的签名者。独立 pin 的 source 与 signer digest 同时约束源提交及签名工作流提交。
