# Personal AI Workspace — development candidate

独立功能分支 `feat/personal-ai-workspace-20261116`。这是可运行 Python/Tk/CLI 实现；不是已通过真实 OAuth、独立 Windows 11 或 ChatGPT 连接验收的正式版本。现有六项发布门禁继续有效。

## 能力和默认值

- 默认仓库名 `my-agent-workspace`、可见性 `private`、同步 `manual`。
- 安装器的 Personal AI Workspace 入口打开 GitHub Setup Wizard 与 Sync Center。正常首次启动会显示设置；稍后设置会记住选择，仍可随时打开。安装和 smoke 不会自动授权/创建仓库。
- Connect GitHub 使用 GitHub Device Flow 在官方浏览器页面授权；界面/终端显示短期 user code，不要求密码或输入 Token。Disconnect 只清除本应用自己的系统凭据与选中仓库，不删除 GitHub 仓库或本机配置。
- 当前账号通过 `/user` 实际校验后才显示已授权用户名。创建、复用与初始化分别确认；拒绝其他账号、公有仓库、无写权限和私人中央仓库。
- 初始化只导出九份公开规则/Skills/Agent 资产与 `workspace.json`。不读取本机私人 AGENTS.md，不上传聊天、密钥、账号配置或日志。
- 检查更新、预览、手动同步、已安装 Skills、备份列表、恢复、错误日志均调用后端功能。同步只拉取，不 Push，也不运行仓库脚本。

## 来源安装与启动

Python 3.11+，在已经审查的开发分支源码中：

```sh
python -m pip install -r requirements-workspace.txt
python -m tools.gui_installer
# 或只启动 Sync Center
python -m tools.workspace_gui
```

现有 CLI 安装器功能保留。冻结 Windows EXE 构建加入系统 keyring backend；CI 仅生成未签名测试产物，不发布 Release。没有系统凭据库时拒绝授权，不回退到明文。Linux 需要可用的 Secret Service / 解锁密钥环；Windows 使用 Credential Manager；macOS 使用 Keychain。

## OAuth 应用前置条件

维护者需在 GitHub 注册并启用 Device Flow 的 OAuth App，分发其**公开 Client ID**。本次没有注册实际 OAuth App，也没有执行真实账号授权；不能编造一个可用 ID。

可在 GitHub 设置页的高级字段保存维护者提供的公开 ID，或由部署者设置 `AKA_WORKSPACE_OAUTH_CLIENT_ID`。此字段不是密码或 Token；不要粘贴凭据。没有 ID 时显示 `OAUTH_CLIENT_ID_REQUIRED`，没有可信系统存储时显示安全存储错误。

Device Flow 申请 classic OAuth `repo` 范围，用于私人仓库创建及读写。该范围在 GitHub OAuth 层比单仓库广；客户端额外限制当前个人账号、确认选中的私人仓库与公开初始化白名单，不能把这些客户端约束称为 GitHub 服务端单仓库权限。若需要服务端单仓库权限，应另行实现 GitHub App installation 授权，不能伪称已实现。

Token 只在 HTTPS 请求内存和本应用隔离的原生凭据库中使用；不会进入设置 JSON、命令行参数、审计或 Git。网络/取消/超时/拒绝授权可重新尝试；撤销凭据的 HTTP 401 可通过用户再次点击 Connect 重新授权。

## 使用流程

1. 运行 GUI，连接自己的 GitHub 账号；可先跳过。
2. 确认创建默认私人仓库，或显式选择复用已有仓库/修改名称。重复名字不会覆盖。
3. 单独确认初始化公开配置。已有不匹配内容拒绝初始化；中断后的公开 seed 可幂等重试。
4. 在每台电脑分别连接同一账号、复用同一个私人仓库；本机备份与状态分别保存。
5. Preview Changes 显示完整本机差异。Sync Now 需另行确认；预览后远程 revision、设置或本地文件变化会阻止应用。
6. 首次遇到不同的现有 AGENTS.md/同名文件会报告 CONFLICT，而非自动替换。先人工比较和整理自己的仓库规则，再重新预览；没有自动上传/合并私人规则。
7. 每次实际同步前备份。Restore 只在文件仍符合已记录状态时恢复；修改过的文件、篡改备份和未知并发写入会阻止覆盖。普通失败可回滚重试；无法确认的部分写入明确保留备份并阻塞。

文件格式、路径与跨 profile 锁见 [同步说明](PERSONAL_WORKSPACE_SYNC.md)。设置使用进程生命周期锁和变更检查，进程退出后不因残留锁文件永久阻塞；切换账号、仓库或 OAuth 设置后旧窗口必须重新打开/预览，不能用过期选择写入。

## CLI（写入必须 --apply）

```sh
python -m tools.personal_workspace status
python -m tools.personal_workspace configure-oauth --oauth-client-id PUBLIC_CLIENT_ID
python -m tools.personal_workspace connect
python -m tools.personal_workspace select --name my-agent-workspace
# 仅显示创建确认需求；不会创建。实际用户操作必须另加 --apply。
python -m tools.personal_workspace check
python -m tools.personal_workspace preview
python -m tools.personal_workspace sync
# 不加 --apply 仅预览；GUI预览与写入有独立同意。
python -m tools.personal_workspace backups
python -m tools.personal_workspace restore --backup-id BACKUP_ID
python -m tools.personal_workspace logs
```

`select --reuse --apply` 明确选择已有私人仓库；`initialize --apply` 才执行初始化写入；`sync --apply` 拉取固定 revision 并备份写入；`restore --apply` 才恢复；`disconnect --apply` 只清除自己的本应用授权。不要在未审查的源代码或未通过发布门禁的包上运行真实授权。

## ChatGPT 独立连接

页面提供[OpenAI 官方 GitHub 连接指南](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt-deep-resear)，要求用户在自己的 ChatGPT App/Plugin 中授权自己的 GitHub，并选中自己的私人仓库。在支持 GitHub 的 ChatGPT 会话中实际读取仓库，另存独立证据。

安装器没有可信的 ChatGPT 授权回调/验证 API，因此只有 `NOT_CONNECTED`、`PENDING_VERIFICATION` 或错误结果；不会因本地 GitHub 登录、用户勾选或自行编辑设置而显示 Connected / VERIFIED。当前检查连接按钮返回缺失验证能力与授权要求，而不是模拟成功。自动验证适配器仍 BLOCKED。

不修改 ChatGPT Memory、自定义指令或内部 Skills，不声称双向实时同步。ChatGPT 与 Codex 的账号连接分别由用户授权。

## 验证范围

测试使用 Mock OAuth/API 与真实临时文件系统；不访问开发者真实凭据，不创建真实用户仓库。两台临时“电脑”复用 Mock 远程文件，验证各自备份/同步/冲突。GUI 控件在云端 Windows/Xvfb 检查；这不等于独立 Windows 11 标准用户验收或真实 OAuth 成功。

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
python -m ruff check tools/personal_workspace.py tools/workspace_*.py tools/gui_installer.py tests/test_personal_workspace.py tests/test_workspace_*.py
python -m mypy --check-untyped-defs --follow-imports=silent --ignore-missing-imports tools/personal_workspace.py tools/workspace_*.py
```

Ruff/Mypy 范围为新 Workspace 模块/测试及修改的 GUI lint；未把整个旧代码库宣称 strict typed。具体统计、CI、失败与修复记录见 PR 和 evidence。真实 OAuth、系统凭据运行、独立 Windows 11、真实 GitHub 创建、真实 ChatGPT 连接均未以 Mock 充当通过。
