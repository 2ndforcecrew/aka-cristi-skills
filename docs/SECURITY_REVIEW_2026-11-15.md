> **历史审计快照（2026-11-15），非当前版本安装结论。** 本文中的第三方扫描标记和发现数量对应旧提交、旧扫描模式，**不适用于直接判断已发布的 [v1.0.0-beta.2](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.2)**。当前 Beta 已完成 Windows/macOS/Ubuntu CI、EXE 构建和 GitHub 来源证明；仍需外部用户与真实 Agent 验收。历史扫描数据保留供追溯；不能把所有 finding 直接认定为漏洞，也不能无证据称全部误报。SkillSpector 为自愿第三方审计，不是安装或发布强制依赖。

# 安全复核：进行中，禁止当作安装许可

基线：`63c4339d462136d746e06121f50acf884c4b1e3c`。本次仅检查公开仓库；没有读取用户私有扫描材料、密钥或个人电脑。

## Issue #8 外部报告

状态 **BLOCKED**。Issue 与评论没有原始 JSON/SARIF，没有 scanner 版本、flags、LLM provider/mode、扫描源 commit 或 24 条 finding 的原文。因此无法复现“67 / DO_NOT_INSTALL”，也无法确认“24 项全部误报”。不得创建虚构 finding、整体 suppress 或用本次静态检查覆盖该结论。

需要的脱敏复核字段：原报告 hash、scanner version/source commit、完整命令及模式、公开仓库 commit、覆盖文件/遗漏范围；逐条 rule ID、文件/行号、公开代码片段、fingerprint、confirmed/disputed/false-positive/needs-fix、独立 reviewer、证据 URL。私人报告先留在私人审核位置，禁止直接发布私人上下文。

## 已复现的代码问题（与缺失的 24 条报告无对应关系）

| 编号 | 基线行为 | 修正与回归证据 |
|---|---|---|
| LOCAL-01 | global AGENTS.md 只检查文件本身；父目录 symlink 可重定向写入 | `checked_path` 拒绝祖先 symlink/reparse；`test_global_rules_refuse_symlink_ancestor_without_writing` |
| LOCAL-02 | `.aka-chef-backups` 可为 symlink，备份写向外部目录 | 在创建和复制前验证备份路径；`test_global_rules_refuse_symlink_backup_folder` |
| LOCAL-03 | Codex role 安装只检查部分路径；更高祖先可为 symlink | 角色 source/destination/state 全路径验证；`test_roles_refuse_symlink_ancestor_without_writing` |
| LOCAL-04 | Skill SHA256 依赖 os.walk 的文件枚举顺序；跨文件系统复制可产生错误冲突 | 排序子目录和文件；`test_skill_digest_independent_of_directory_enumeration` |
| LOCAL-05 | 旧 bootstrap 会执行缺少独立完整性/来源验签的下载与 Codex prerequisite 脚本 | 默认远程安装阻塞；签名档案需固定 commit/digest/source ref 并先验签；依赖脚本不再自动执行 |

LOCAL-01–04 的四个测试在修复前全部 FAIL，修复后全部 PASS。Windows junction 的真实测试由云 CI 另行记录；没有以 Linux symlink 测试冒充 Windows 桌面验收。

摘要兼容性：早期安装 receipt 使用未排序枚举时可能与新的稳定摘要不同。现有文件保留；发现 mismatch 时显示冲突，不能静默重新标记或覆盖。用旧版本工具在确认没有用户修改后归档卸载，再预览新版本；保留备份供人工比较。尚未自动迁移旧摘要。

## 攻击面与剩余限制

| 面 | 处理 | 限制 |
|---|---|---|
| 网络与执行 | 本地安装器不执行 Skill 脚本；release verifier 在执行/解压前检查固定身份与摘要 | 初次获取 bootstrap/verifier 本身仍需可信分发；本地 reviewed source 是明确的信任边界 |
| 依赖 | 缺失依赖需独立授权；禁止无验签 PowerShell prerequisite 下载执行 | Windows clean-machine dependency UX 尚未验收 |
| 配置写入 | preview、managed ownership、冲突拒绝、保留备份；新增事务后端 | 不构成对恶意同用户进程并发替换路径的内核级防护 |
| 文件路径 | 拒绝已有 symlink / Windows reparse 路径 | 不改变 ACL、不提权；网络盘和竞争条件还需专项审计 |
| 回滚 | 修改后的文件拒绝静默移除；发生错误保留恢复信息 | 断电/磁盘损坏不保证自动恢复；备份也可能包含私人规则，禁止上传 |
| 日志与外发 | 不上传本机 raw Codex 会话、账号文件或用户配置；公开测试使用 synthetic case | 扫描器完整 LLM 模式未获原始配置，不能重现同一判定 |
| CI | PR 测试只读；签名 candidate 作业单独限定权限；无 production deploy | 云 CI 不等于外部用户验收，也不能推翻缺失的安全报告 |

## 复验

```sh
python -m unittest tests.test_filesystem_security -v
python -m unittest discover -s tests -v
```

额外静态扫描的实际命令、固定版本、范围与结果另存 evidence；若依赖安装或扫描失败，应记录失败，不能报告扫描 PASS。Issue #8 的原始报告复核完成前六项总门禁仍为 BLOCKED。

## 本次实际扫描（不覆盖外部 24 项报告）

固定 NVIDIA scanner commit `c81615007d40e86051a302a3cf897f8a05264928` / version 2.12.0，隔离虚拟环境，`--no-llm --format json --fail-on-incomplete`。扫描进程清空 API key/追踪环境设置，不读取私人配置。

- 基线 `63c4339`：34 个文件，56 分，23 项，DO_NOT_INSTALL；静态模式覆盖完整，退出 1。逐项独立复核见 [triage](evidence/skillspector-baseline-triage.json)，无 suppression。
- 修正快照 `bd1edff`：62 个组件，100 分，160 项，DO_NOT_INSTALL，覆盖不完整，退出 1。该完整仓库扫描包含前一轮 report/triage，115 项来自这两个证据文档；scanner 对之前 JSON 报告标记 obfuscated_instruction_text，造成静态分析降级。不能将这个结果改写成安全通过，也不能拿两个不同文件集合的总分证明风险升降。
- [运行元数据与原始报告摘要](evidence/skillspector-runs.json)；第二轮原报告以 gzip 原样保存（无内容改写），解压后 SHA256 可复核。原 24 项报告、LLM 模式和独立来源仍缺失。

后续应分别定义可执行安装包扫描范围与历史报告数据范围，并保留全量扫描失败证据；不得为了得分删改安全告警。
