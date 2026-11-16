# Personal AI Workspace GUI

从安装窗口点击 **Personal AI Workspace**。正常启动安装程序时，首次使用自动打开设置页；安装校验成功后会询问是否设置。测试和 `--smoke-test` 不会自动设置、访问账户或写入用户配置。

```bash
python -m tools.gui_installer
python -m tools.workspace_gui
python -m tools.workspace_gui --smoke-test
```

1. 若尚无预设的 OAuth 应用 ID，在高级设置填写维护者提供的 **OAuth public client ID**，点击 **保存应用 ID**。这是公开应用标识，不是密码或 Token；留空可以使用预设或环境配置。然后点击 **Connect GitHub**，按照浏览器设备授权提示操作。需要已配置的 GitHub OAuth public client ID 和系统凭据存储；缺少配置会阻止授权。窗口只显示一次性用户代码，不显示 Token。GitHub 授权范围与安全存储要求请参阅主 Workspace 文档。
需要切换账户或重新授权时，点击 **Disconnect GitHub** 并确认。仅清除此应用保存的凭据和仓库选择，不修改远程仓库；之后重新点击 **Connect GitHub**。

2. 保留默认 `my-agent-workspace`，或输入自己的仓库名称。创建和复用均需单独确认；只能使用当前账户拥有的 private 仓库。
3. **初始化公共配置** 需再次确认。只导出公共白名单内容。也可点击 **稍后设置**。
4. 在 Sync Center 点击 **检查更新**、**预览差异**。差异仅在本机显示。**Sync Now** 明确确认后创建备份并手动拉取；不会推送本机内容。
5. **已安装 Skills**、**错误日志**、**备份历史** 可检查本机状态。恢复需选择备份并确认，已有修改或冲突会阻止恢复。
6. ChatGPT 页面使用独立的官方指南和验证入口。GitHub 登录不会改变 ChatGPT 状态；没有实际验证服务时仍显示未连接、等待或阻塞。

操作在后台执行，进行中禁用设置和写入控件，防止改变任务参数。取消按钮仅在 GitHub 授权期间启用，取消和授权超时请求会传到授权过程。其他操作无法中途取消，超出等待时间后仍需等待安全结束，不强行杀死磁盘写入线程。窗口不会把原始异常、Token 或私有配置写入日志。Controller 返回的差异只供本机审阅。

GUI 自动测试使用临时目录和假 Controller；需要 Tk 图形桌面，Linux 可在 Xvfb 下运行。真实 Windows 用户验收、真实 OAuth 与 ChatGPT 验证需要另行完成。
