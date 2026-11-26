# 跨宿主适配（WP3，PR #66）

统一安装器把 6 个原生 skill 与 25 个 vendored skill（Addy Osmani
agent-skills，MIT，见 `vendor/addy-agent-skills/`）走同一条安装路径：
`aka-skills install` / `python -m tools.full_setup` /
`python -m tools.universal_chef` / `python -m tools.quick_install`。
Vendored `interview-me` 是参考（原生优先），永不安装；hooks 永不安装、
不接线；上游 Node 校验脚本只作参考，不进 CI、不作运行时依赖。

**诚实标注**：下表每一行都是「文件适配」——文件按宿主文档布局落盘，
但宿主是否真实加载、调用，一律 NOT_RUN（见 README §06 同款写法）。
WP4 做隔离安装演练（只验文件）；真实宿主加载须另行在真机上验收。

## 适配表

| 宿主 | Skills 安装路径 | Skill 发现机制 | Commands | Hooks | 状态 |
| --- | --- | --- | --- | --- | --- |
| Codex | 用户 `~/.agents/skills/<name>/`（quick_install codex 目标） | 原生渐进披露（先 name + description，选中才载全文）；`@skill` 调用；须 Codex CLI v0.122+ | 不装：直接 `@skill` 调用，`.claude/commands` 是 Claude 专属 | 不接线（上游插件亦不接） | 文件适配；加载 NOT_RUN |
| Claude Code | 项目 `.claude/skills/<name>/`，用户 `~/.claude/skills/` | 原生 Skills 发现（SKILL.md name + description） | 装 `.claude/commands/*.md`（10 个，含 `plan.md`）到 `.claude/commands/` | 可接 SessionStart 格式，默认不接 | 文件适配；加载 NOT_RUN |
| Gemini CLI | 项目 `.gemini/skills/`（或 `.agents/skills/`），用户 `~/.gemini/skills/` | 原生自动发现（`.gemini/skills/` 或 `.agents/skills/`）；`/skills list` 核对；激活前须用户确认 | 装 `.gemini/commands/*.toml`（10 个，`planning.toml`）到 `.gemini/commands/` | Session hooks 格式兼容，默认不接 | 文件适配；加载 NOT_RUN |
| OpenCode | 项目 `.opencode/skills/`，用户 `~/.config/opencode/skills/`；亦认 `.claude/skills/`、`.agents/skills/` 及其用户版 | `skill` 工具 + 项目 AGENTS.md 意图映射；按上述 6 条路径查找 | 不装：上游未发 `.opencode/commands/*.md`（PR #200 未合併） | 无上游接线定义，默认不接 | 文件适配；加载 NOT_RUN |
| WorkBuddy / CodeBuddy | 项目 `.codebuddy/skills/`，用户同路径放 home 下 | WorkBuddy 读其 skills 目录（应用重启刷新缓存） | 无上游定义格式，不装 | 无 | 文件适配；加载 NOT_RUN；路径待 PR #67 对齐（见下） |
| Hermes | 须显式 `--hermes-skills-root`（如 `~/.hermes/skills`）；无核实过的用户级规则路径 | DISCOVERY_ONLY，无核实过的原生加载 | 不装 | 无 | 文件适配；原生激活 BLOCKED |
| 通用 | 项目 `.agents/skills/<name>/` | 依宿主而定（任何读 Agent Skills 布局的 agent） | 不装（无通用格式） | 无 | 文件适配；加载 NOT_RUN |

依据：各宿主 setup 文档（`vendor/addy-agent-skills/docs/`：
`codex-setup.md`、`gemini-cli-setup.md`、`opencode-setup.md`、
`antigravity-setup.md`、`cursor-setup.md`、`windsurf-setup.md`、
`commandcode-setup.md`、`other-hosts.md`）与安装器源码
（`tools/quick_install.py`、`tools/universal_chef.py`）。

### WorkBuddy 路径说明

本分支安装器写 `.codebuddy/`（main 现状）。2026-11-25 已核实 WorkBuddy
应用读 `.workbuddy/skills/`；PR #67（Draft，未合併）把安装器路径改成
`.workbuddy/`。在 PR #67 合併前，WorkBuddy 行是「文件适配、路径待对齐」，
不要把 `.codebuddy/` 写成已对齐。WP3 不动 PR #67 的分支。

## Commands 三格式裁决

上游 10 条命令有三份平行格式，内容同一组（WP1b 已核对）：

| 格式 | 位置 | 安装器行为 |
| --- | --- | --- |
| `.claude/commands/*.md`（10 个） | `vendor/addy-agent-skills/.claude/commands/` | Claude 宿主装到项目 `.claude/commands/`（用户级则 `~/.claude/commands/`） |
| `.gemini/commands/*.toml`（10 个） | `vendor/addy-agent-skills/.gemini/commands/` | Gemini 宿主装到项目 `.gemini/commands/`（用户级则 `~/.gemini/commands/`） |
| `commands/*.toml`（10 个） | `vendor/addy-agent-skills/commands/` | 不装：这是 Antigravity 旧版格式，agy 1.1.x 下转换后的 wrapper 不出现（上游 #445）；Codex 亦不用命令文件，直接 `@skill` |

命名差异只记录、不统一：Claude 用 `plan.md`，Gemini 与通用格式用
`planning.toml`（`/plan` 与 Gemini CLI 内置命令重名，见
`gemini-cli-setup.md`）。命令文件与 rules/roles 共用同一份安装器状态
（`.aka-chef-install/<host>.json`），冲突拒绝、升级、卸载、verify 全覆盖。

## Manifest 解析

| Manifest | 解析根 | 结论 |
| --- | --- | --- |
| 根 `plugin.json`（我方新文件） | 仓库根 | 身份文件，agent-plugins.org schema，name `aka-cristi-skills`，v0.1.0；不含 skills/commands 字段（与上游根 plugin.json 同形）。license 字段省略：本仓无 LICENSE 文件（`docs/comparison.md:37` 已记），vendored 部分是 MIT（`vendor/addy-agent-skills/LICENSE` 原样保留）。 |
| `vendor/addy-agent-skills/plugin.json`（上游） | vendor 内 | name `agent-skills` v0.6.18，原样不动，只作参考；与我方根 plugin.json 是两个东西，不要混淆。 |
| `vendor/.../.claude-plugin/plugin.json` | vendor 内 | `commands: ["./.claude/commands", "./commands"]`、`skills: "./skills"` 均在 vendor 内解析通过；以 vendor 目录为插件根时可直接作 Claude 插件。 |
| `vendor/.../.codex-plugin/plugin.json` | vendor 内 | `skills: "./skills/"` 在 vendor 内解析通过；以 vendor 目录为插件根时可直接作 Codex 插件。 |
| `vendor/.../.agents/plugins/marketplace.json` | 插件根 | `source.path: "./"` 指插件根目录（即含 `skills/` 的那一级），不是 marketplace.json 所在目录。**决定**：本文件原样保留、只作参考；安装器不注册 marketplace。如需注册，marketplace 源必须指向 `vendor/addy-agent-skills/` 这一级——从本仓根注册会把 `"./"` 解成仓根，把 6 个原生 skill 误当成 agent-skills 插件。 |
| `vendor/.../.claude-plugin/marketplace.json` | 远程 | source 是 GitHub 远程指针（上游仓），无本地路径问题，只作参考。 |

## Symlink 裁决

`vendor/addy-agent-skills/.opencode/skills` → `../skills/` 原样保留在
vendor 内（git mode 120000），供把插件根直接指向 vendor 目录的宿主
（如 OpenCode）发现用。**安装器永不复制、永不重建 symlink**：

- `skill_installer.package()` 拒收包内任何 symlink；每个 skill 目录以
  真实文件复制落盘；已安装的 skill 是 symlink 时 `inspect()` 直接报错。
- 已安装布局是各宿主的 skills 目录，不是插件根，指向整棵 skills 树的
  symlink 在那里没有意义。
- 已实测：25 个 vendored skill 目录内 0 个 symlink；安装后 skills 根下
  0 个 symlink（见 `tests/test_quick_install.py`）。

## 已知限制

- `accessibility-engineering/SKILL.md` 引用了包外文件：
  `../frontend-ui-engineering/SKILL.md`（兄弟 skill）与
  `../../agents/accessibility-auditor.md`（vendor 内 persona）。在 vendor
  内两者都解析通过；单装一个 skill 时会悬空。缓解：安装器默认一次装
  31 个，兄弟 skill 一定在场。`agents/` persona 不由安装器安装，该引用
  在宿主安装里仍悬空，原因有三：能让 `../../agents/...` 解析的唯一位置
  就是已安装 skills 根的同级 `agents/` 目录，但对 Claude / Gemini /
  OpenCode / WorkBuddy 来说那正是宿主的 **live subagent 发现目录**（放
  进去会被当作 live subagent，不是纯参考）；Codex 的 skills 根与 agents
  根不在同一棵树下，任何单一落盘位置都不能让该相对链接在全部宿主下
  解析；5 个 persona 与 4 个原生角色的去重未经评审（code-reviewer、
  test-engineer 等存在 plausible 重叠），WP2 只审了 26 个 skill。
  需要该 persona 时，从仓库
  `vendor/addy-agent-skills/agents/accessibility-auditor.md` 原文复制
  （MIT 原样保留），不要改 skill 内的链接。另注：doubt-driven:110 用
  散文提到 `agents/` roster，同样只在仓库树内可解。vendor 文件逐字节
  原样，不改链接，此处只记录。
- 未 pin 版本的 `npx`（WP4 全树扫描的全部 55 项真问题，同一类）：
  22 个 vendored 文件里的 `npx lighthouse`、`npx -p
  chrome-devtools-mcp`、`npx skills add`、`npx tsc` 等都没有 pin 版本，
  有 rug-pull 风险。这些是文档／示例里用户显式执行的命令，非自动执行
  （安装器从不跑 `npx`）；使用时请自行 pin 版本，例如
  `npx -y lighthouse@<version>`。vendor 文件逐字节原样，不能在源头修，
  此处只提示。
- Codex 安装隔离：安装不传 `--skills-root` 时，skill 写进共享的
  `~/.agents/skills`（与该用户其他 Codex 配置共用一处）；要隔离请传
  `--skills-root <目录>`。WP4 演练无内容损坏（幂等重跑，mtime 未变），
  但共享目录意味着卸载／升级会影响同一目录下的其他内容。
- Antigravity 不是 7 个安装器宿主之一（只有上游文档）：
  `agy plugin install <repo>` 装到 `~/.gemini/config/plugins/`，
  skills 自动发现；旧版 `commands/*.toml` 转换 wrapper 在 agy 1.1.x
  不出现，改用 `/agent-skills:<skill>` 直接调用（上游 #445）。
- 上游 `npx skills add`（70+ agents）**不引入**为我方安装路径；对照见
  `docs/comparison.md:43,182`。我方安装路径只有 `aka-skills` CLI /
  `full_setup` / `quick_install`。
- Cursor、Windsurf、CommandCode、Copilot 只有上游文档、无安装器支持：
  Cursor 用 `.cursor/skills/<name>/SKILL.md`；Windsurf 无原生 skills
  目录，做法是把 2–3 个 SKILL.md 拼进 `.windsurfrules`；CommandCode
  用 `cmd skills add` 自行发现 SKILL.md；Copilot 见上游
  `copilot-setup.md` / `copilot-cli-setup.md`。
- `constraint-driven-development/scripts/quality-gate.mjs` 的 `.mjs`
  后缀不在校验器允许列表里，只报 SCRIPT_REVIEW 警告，不影响安装与
  validator 的 PREFLIGHT_ONLY 结论。
- 全部 7 个宿主的「加载 / 调用」均为 NOT_RUN；WP4 只做隔离安装演练
  （文件级），真机加载验收须用户在真实宿主里跑。
