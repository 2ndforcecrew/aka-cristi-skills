# 成长记录草稿 · Personal AI Workspace · 2026-11-16

**未部署到成长网站；仅随独立功能分支/Draft PR 交付。** 本轮明确禁止合并 main、发布 Release 或部署生产环境。

## 本轮新增

从“安装一套公开 CHEF 方法”推进到“每个人有自己的私人 AI Workspace”：独立账号授权、默认私人仓库、公开资产初始化、Codex 手动拉取、冲突保护、备份恢复和 Sync Center。

现有安装器和历史文件保留。默认 `my-agent-workspace / private / manual`；没有自动 Push，没有复制 AKA.CRISTI 私人规则或聊天记录。

## 已有实现与验证证据

- 真实 Python/Tk GUI 和 CLI 对接后端；不是静态页面。
- OAuth 设备流程、取消/失败/超时和只使用系统凭据库的实现由 Mock 请求验证；无真实授权。
- 私人仓库创建/复用/初始化只用 Mock API；真实适配器+HTTPS 请求边界也以注入传输集成测试，未创建真实仓库。
- Codex 同步使用真实临时文件，覆盖首次同步、同仓库两台隔离电脑、版本更新、用户修改冲突、预览失效、备份篡改、回滚和重试。
- 独立复核复现并修复：API 前导斜线契约、撤销凭据重授权、CLI user code 展示、进程崩溃残留锁、跨账号/profile 共用目标的并发覆盖、旧仓库选择写入，以及 restore 最终账本提交失败的可重试性。
- 详细命令、测试统计和云端 CI 链接在 Draft PR / evidence，不将条件跳过算作通过。

## 待验证 / 阻塞

- 维护者注册并启用 GitHub OAuth Device Flow 的公开 Client ID。程序不编造可用 ID。
- 真实 Windows 11 标准用户、原生凭据库及真实浏览器授权。
- ChatGPT 由用户另行连接自己的 GitHub；缺少可信回调时只能待验证，不能显示 Connected。
- 原有安全及六项发布门禁仍有效。本轮不发布“全部完成”。
