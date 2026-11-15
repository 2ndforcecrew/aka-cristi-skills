# AKA.CRISTI Skills｜中文功能说明

> **FROM EXPERIENCE TO CAPABILITY｜把协作经验转化为可复用能力。**

[GitHub 公开仓库](https://github.com/2ndforcecrew/aka-cristi-skills) · [英文 README](../README.md)

## 项目是什么？

**AKA.CRISTI Skills** 是一个面向 AI Agent 工作流的公开 Skill 集合，配备一个安全优先、可审计的本地安装工具。它帮助使用者将有效的开发、测试与协作方法整理为可复用的操作流程，减少重复沟通和遗漏验证。

当前发布的是 **方法论 Skills + 本地安装器 V0.1**，不是已经实现自动指挥所有 AI Agent 的完整协作平台。公开仓库与 AKA.CRISTI 的私有开发仓库独立，不包含内部管理规则、账号密钥、客户资料或私有提交历史。

## 当前包含的 3 个 Skills

### 1. Verified Change Loop｜可验证的修改闭环
[查看 Skill 原文](../skills/verified-change-loop/SKILL.md)

适用于程序报错、功能故障、CI 失败和需要验收的代码修改。

工作流程：
**确认范围 → 复现问题 → 收集证据 → 分析原因 → 最小修改 → 重跑相同场景 → 对比结果 → 复核交付**。

主要价值：
- 避免只凭“代码已修改”就宣布修复成功。
- 要求记录修改前后可比较的实际证据。
- 对未运行或未完成独立复核的项目明确标注 `NOT RUN`。
- 保留风险边界、回滚方案和待解决问题。

**限制：** 本 Skill 规定操作方法，不会自行获得项目权限、部署正式环境或保证每次修复都成功。

### 2. Feature Journey Map｜产品功能旅程地图
[查看 Skill 原文](../skills/feature-journey-map/SKILL.md)

适用于网站、App、后台系统、电商功能等真实用户流程的开发与测试。

工作流程：
**确认入口 → 准备测试状态 → 列出用户操作 → 定义可观察结果 → 覆盖异常场景 → 复测并留证**。

主要价值：
- 从用户能否完成操作的角度审视功能，而不是只检查代码是否通过。
- 记录按钮、页面、输入状态、权限和成功反馈。
- 覆盖空数据、无权限、输入错误、网络延迟等边界条件。
- 把需求整理成可复现的测试场景，供开发和验收复用。

**限制：** 测试场景必须基于真实页面与授权环境，不能把示例流程当作已执行结果。

### 3. Skill Evaluation Gate｜Skill 评估与发布关卡
[查看 Skill 原文](../skills/skill-evaluation-gate/SKILL.md)

适用于将成功经验沉淀为新 Skill，或评估已有 Skill 的升级、维护和淘汰。

工作流程：
**建立评估标准 → 准备隔离测试 → 执行真实场景 → 独立核查 → 修复复测 → 审批发布 → 持续维护**。

主要价值：
- 区分候选 Skill、完成测试、独立复核和获准发布几个不同状态。
- 关注功能效果、错误处理、兼容性、安全和回滚。
- 防止一次成功就被误认为在所有项目和环境中可靠。
- 为后续版本更新、性能退化检查和 Skill 淘汰提供规范。

**限制：** 评估关卡不等于自动生成、自动审核、自动发布功能都已完成；真实测试与审批仍需要相应执行环境。

## 本地 Skill Installer V0.1｜安装工具

[查看安装器源代码](../tools/skill_installer.py)

目前支持：
- **预览（preview）**：安装前检查内容及目标位置，默认不修改文件。
- **安装（install）**：只有明确加入 `--apply` 才写入。
- **完整性检查（verify）**：检查受管理 Skill 的文件内容是否与安装记录一致。
- **升级（upgrade）**：从新版本地 Skill 目录再次执行 `install --apply`，保留旧版备份。
- **回滚（rollback）**：在已有有效备份时恢复上一受管理版本。
- **卸载（uninstall）**：将受管理 Skill 移到备份目录，而不是直接永久删除。

安装器支持 **Codex 用户级 Skill 目录**（`~/.agents/skills`）和使用者指定的普通目录。核心安装器使用 Python 标准库，不需要安装额外的 Python 第三方依赖。

### 快速使用

环境：**Git + Python 3.11 或更新版本**。在 Windows PowerShell、macOS Terminal 或 Linux shell 执行：

```bash
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git
cd aka-cristi-skills

# 先预览：不修改文件
python -m tools.skill_installer preview skills/verified-change-loop --target codex

# 明确授权安装
python -m tools.skill_installer install skills/verified-change-loop --target codex --apply

# 验证安装记录和文件完整性
python -m tools.skill_installer verify verified-change-loop --target codex
```

若希望安装其他两个 Skills，将上面的 `verified-change-loop` 替换为 `feature-journey-map` 或 `skill-evaluation-gate`。

安装前建议先阅读目标 Skill 的 `SKILL.md`。安装后是否被 Codex 发现、加载和实际执行，需要在自己的 Codex 环境中另行验证；`verify` 的完整性 `PASS` **不代表 Agent 功能测试通过**。

### 更多维护命令

```bash
# 更新：使用已下载的新版本地 Skill 内容安装
python -m tools.skill_installer install skills/verified-change-loop --target codex --apply

# 回退到上一个已备份版本
python -m tools.skill_installer rollback verified-change-loop --target codex --apply

# 卸载并归档已管理的 Skill
python -m tools.skill_installer uninstall verified-change-loop --target codex --apply

# 在自定义测试目录中预览，避免动到正式 Codex 目录
python -m tools.skill_installer preview skills/verified-change-loop --target directory --root ./sandbox-agent-skills
```

## 安全原则

1. **默认只预览**：修改文件需要使用者明确添加 `--apply`。
2. **不覆盖未知文件**：遇到不由本工具管理的 Skill，或已被外部修改的受管理文件，拒绝覆盖。
3. **只从本地安装**：V0.1 不直接下载 GitHub URL、不运行下载脚本、不索取账号密码。
4. **备份与回退**：升级保留旧版本，卸载时执行归档；回滚依赖有效备份。
5. **输入约束**：拒绝符号链接、超大包、非法文件结构及不匹配的 Skill 名称。
6. **不夸大保障**：文件摘要和本地检查不能取代数字签名、恶意代码审计、真实执行测试或独立安全复核。

## 当前未实现的功能

- 从 GitHub 链接一键远程安装或图形化安装。
- 自动更新所有 Skills、无人值守批量安装。
- Hermes Agent、ChatGPT Plugin 等平台的一键安装适配。
- Agent 自动启动、实际调用成功率检测或跨 Agent 自动编排。
- 生产环境自动部署、完全自主审批或发布。
- 在所有 Windows、macOS、Linux 环境中的真实机器验收。

这些方向可以在未来版本逐步开发，但**不应将规划当成已完成功能**。

## 测试与验证说明

开发分支已有安装器单元测试以及相关项目 CI 通过记录，涵盖预览、安装、升级、回滚、卸载、冲突拒绝、格式检查和符号链接拒绝等测试路径。此记录**不代表**已在朋友的电脑上完成真实安装验收，也不代表安装后的 Agent 功能已实际激活。

## 如何参与

你可以阅读公开 Skill 的内容，在自己的授权测试环境里验证，并通过 GitHub Issues 提出可复现的问题、测试证据与改进建议。请勿在 Issue 中提交密码、Token、客户信息或未经授权的私有代码。

**AKA.CRISTI — DESIGN × CODE × AI × AUTOMATION × BUSINESS**
