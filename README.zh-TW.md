# AKA.CRISTI Skills — 中文功能說明

🌐 **Language / 語言：** [English](README.md) · [簡體中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Français](README.fr.md)

**FROM EXPERIENCE TO CAPABILITY｜將協作經驗變成可複用能力**

## 項目是什麼

AKA.CRISTI Skills 是一套公開、可審查、可在本地安裝的 **AI Agent 工作流程技能包**，配套安全安裝器和 Codex 的 CHEF 協作配置。目標是讓 AI 在執行復雜任務時，不只輸出建議，而是遵循「明確目標 → 檢查環境 → 分工執行 → 驗證結果 → 錯誤恢復 → 記錄可複用經驗」的工作方法。

**需要區分：** Skill 是指導 Agent 如何工作的說明與流程，**不是**獨立運行的 AI 大腦，也不會自動獲得 GitHub、Codex、Hermes、Claude 或其他服務的登錄權限。是否能真正調用某個 Agent，取決於本機宿主版本、工具連接和授權。

本倉庫是公開發行版，與 AKA.CRISTI 的私有開發倉庫分離；不會發布私有工作規則、賬號信息、客戶數據、私有歷史記錄。

## 最新公開狀態：Codex Beta 已正式發佈

**[v1.0.0-beta.2 公開測試版](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.2)** 已發佈，提供 CHEF 工作規則、四個 Skills、四個 Codex 角色設定，以及 Windows 圖形安裝器和跨平台命令安裝。**Windows / macOS / Ubuntu CI、Windows EXE 建置和 GitHub 來源證明已通過。** 這是 Beta，仍需獨立用戶驗收，並非所有 Agent 已完成真實調用驗證。

Windows PowerShell（Git + Python 3.11+）：

```powershell
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git; if ($LASTEXITCODE -ne 0) { throw 'Clone failed' }; cd aka-cristi-skills; git checkout v1.0.0-beta.2; if ($LASTEXITCODE -ne 0) { throw 'Tag checkout failed' }; py -3 -m tools.quick_install --interactive
```

macOS / Ubuntu / Linux（Git + Python 3.11+）：

```bash
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git && cd aka-cristi-skills && git checkout v1.0.0-beta.2 && python3 -m tools.quick_install --interactive
```

先檢查變更預覽，只有明確輸入 `INSTALL` 才會修改檔案；`FILES_VERIFIED` 指檔案驗證，**不是實際啟動四個 Agent 的證據**。Windows EXE 尚未有 Authenticode 簽名，請驗證 GitHub 來源並在獨立測試環境使用。

**關於歷史掃描：** 舊版第三方 SkillSpector 的 `DO_NOT_INSTALL` 標記和檢測項目是當時固定快照的歷史資料，不是針對當前 `beta.2` 的即時安全判斷。它不是本專案安裝或發佈所必須的工具。歷史結果保留於 [審核記錄](docs/SECURITY_REVIEW_2026-11-15.md)，不能將「檢測項目」一概斷言為漏洞，也不能在沒有證據的情況下稱它們全部無風險。

## 一、核心功能

### 1. CHEF Orchestrator：AI 任務總指揮

文件：[chef-orchestrator/SKILL.md](skills/chef-orchestrator/SKILL.md)

- **目標與驗收：** 將用戶需求轉成可觀察的完成條件、授權邊界與停止條件。
- **Inspect：** 先讀取項目規則、現有配置、Git 狀態及可用工具，避免直接覆蓋工作成果。
- **任務分工：** 按需規劃 Research、Creative、Coding、QA、Automation、Knowledge 等職責。
- **可追蹤交接：** 明確任務 ID、使用的實際工具、文件範圍、輸入輸出、超時、重試次數和驗收標準。
- **實際執行：** 有真實連接才調用其他 Agent；不可用時明確記錄 `BLOCKED` 或 `NOT_RUN`，不僞造委派結果。
- **獨立驗證：** 檢查代碼、測試、日誌和實際用戶路徑，區分「已完成」與「已驗證」。
- **自動恢復方法：** 對失敗進行有邊界的診斷、最小修復和重複測試；涉及不可逆操作仍需授權。
- **經驗沉澱：** 僅將真實驗證過的重複流程提煉成待審覈 Skill，不自動公開或安裝。

### 2. Verified Change Loop：問題診斷與修復閉環

文件：[verified-change-loop/SKILL.md](skills/verified-change-loop/SKILL.md)

復現問題 → 檢查證據 → 最小可逆修改 → 重跑相同場景 → 對比結果 → 迴歸測試 → 交付驗收。適合代碼 Bug、CI 故障、網頁功能異常及複雜流程修復。

### 3. Feature Journey Map：真實用戶操作路徑

文件：[feature-journey-map/SKILL.md](skills/feature-journey-map/SKILL.md)

記錄用戶從入口、初始化、操作到可見結果的完整流程，並覆蓋空狀態、權限不足、錯誤輸入、慢網絡等異常路徑。避免只憑單元測試通過就宣稱產品可用。

### 4. Skill Evaluation Gate：技能質量審覈

文件：[skill-evaluation-gate/SKILL.md](skills/skill-evaluation-gate/SKILL.md)

通過實際場景、測試證據、獨立複覈和發佈授權判斷 Skill 是否可進入下一個階段；區分 Candidate、Tested、Reviewed、Approved / Released，不將安裝成功等同於運行成功。

### 5. CHEF Global Rules：跨項目工作規則

- 將**經過公開脫敏的** CHEF 規則寫入 `~/.codex/AGENTS.md` 或 `$CODEX_HOME/AGENTS.md`。
- 安裝前支持 `preview`；通過 `--apply` 才實際寫入。
- 採用受管理標記區塊追加規則，儘量保留用戶現有內容，已有文件會備份。
- 支持校驗和卸載受管理區塊；不等於自動同步所有電腦的私有規則。

技術說明：[CHEF Global Rules + Multi-Agent Starter](docs/CHEF_GLOBAL_AND_MULTIAGENT.md)。

### 6. Codex Native Subagents：四個角色

| 角色 | 名稱 | 主要職責 |
| --- | --- | --- |
| Research | `aka_research` | 搜索事實、整理來源和證據 |
| Coding | `aka_coding` | 在授權範圍內編程、修復和測試 |
| QA | `aka_qa` | 對最終版本進行獨立審查和驗證 |
| Automation | `aka_automation` | 設計安全、有邊界的自動化流程 |

倉庫提供四個原生 Codex 自定義 Agent 的 TOML 配置及安裝、校驗腳本。**安裝配置不代表四個 Agent 已實際啓動**，更不代表能夠調用其他廠商的賬戶。正式判斷需要真實 Codex 子線程和執行記錄。

詳細說明：[Codex Native Subagents V0.2](docs/CODEX_NATIVE_SUBAGENTS_V02.md)。

### 7. 本地安全 Skill 安裝器

- 支持本地預覽、安裝、文件完整性校驗、升級、回滾、卸載。
- 拒絕覆蓋不歸安裝器管理或已被外部改動的 Skill。
- 不從網絡自行下載代碼、不執行 Skill 內部腳本、不主動上傳密鑰。
- 卸載時保留歸檔；回滾依賴此前確實存在的備份。
- 這不是病毒掃描器或數字簽名校驗，現有 CLI 不等於一鍵 GUI；候選圖形界面仍需真實環境驗收。

## 二、朋友如何安裝（Windows 11 / macOS / Linux）

前置條件：安裝 [Git](https://git-scm.com/downloads) 與 Python 3.11 或更新版本；使用有權限的本機終端。先自行閱讀倉庫內容，安裝操作會修改當前用戶的本地 Codex 文件。

### 第一步：下載公開倉庫

```powershell
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git
cd aka-cristi-skills
```

### 第二步：預覽 CHEF 全局規則和主 Skill

```powershell
python -m tools.chef_global_rules preview
python -m tools.skill_installer preview skills/chef-orchestrator --target codex
```

### 第三步：明確授權本地安裝

```powershell
python -m tools.chef_global_rules install --apply
python -m tools.skill_installer install skills/chef-orchestrator --target codex --apply
python -m tools.skill_installer install skills/verified-change-loop --target codex --apply
python -m tools.skill_installer install skills/feature-journey-map --target codex --apply
python -m tools.skill_installer install skills/skill-evaluation-gate --target codex --apply
```

### 第四步：可選安裝四個原生 Codex 角色

```powershell
python -m tools.codex_subagents preview
python -m tools.codex_subagents install --apply
python -m tools.codex_subagents verify
```

### 第五步：檢查安裝文件

```powershell
python -m tools.chef_global_rules verify
python -m tools.skill_installer verify chef-orchestrator --target codex
python -m tools.skill_installer verify verified-change-loop --target codex
```

這些命令檢查**配置與文件**，並不證明 Codex 已調用 Skill 或啓動四個 Agent。請重新開啓 Codex 會話，測試真實委派，並保存實際執行證據。

若本機已安裝並登錄 Codex CLI，可以執行嚴格的四角色運行驗收（可能消耗 Codex 使用額度）：

```powershell
codex login status
python -m tools.verify_four_agents --timeout 600 --out four-agent-report.json
```

驗收結果應區分 `PASS`、`FAIL`、`INCONCLUSIVE`、`NOT_RUN`。沒有真實線程證據就不能聲稱通過。詳見：[四 Agent 真實運行驗收](docs/FOUR_AGENT_RUNTIME_ACCEPTANCE.md)。

## 三、真實能力與限制

| 項目 | 當前邊界 |
| --- | --- |
| 公開 Skill 文件與 CLI 安裝器 | 倉庫已提供；可閱讀、下載與本地運行 |
| CHEF 全局規則安裝 | 提供安全預覽、受管理區塊安裝與校驗 |
| 四個原生 Codex 角色配置 | 提供 TOML 與安裝/校驗工具 |
| 自動檢測並修復所有真實項目錯誤 | **不能保證**；仍依賴工具、權限、項目情況與實際測試 |
| 自動連接 Hermes、Claude、其他品牌 Agent | **未實現通用連接**；需要單獨的 API / MCP / CLI 適配 |
| 四 Agent 在用戶真實 Codex 環境運行通過 | **須在已登錄的真實 Codex 設備上單獨驗證** |
| 自動把成功經驗發佈爲 Skill | 有評估流程，**不是無需審覈的自動發佈系統** |
| 全設備自動同步與一鍵圖形安裝 | 尚非此公開發行版的已驗證功能 |

## 四、安全原則

- 不覆蓋現有私人規則或未託管 Skill；先預覽，再明確執行。
- 不上傳密碼、API Key、私人對話和客戶數據。
- 不將本地測試、模擬輸出或 Agent 自述誤判爲真實運行結果。
- 不自動進行付費操作、權限變更、生產發佈、刪除數據等高風險操作。
- 所有跨平臺 Agent 連接都需要獨立授權和真實驗收。

## 五、項目方向

以 **DESIGN × CODE × AI × AUTOMATION × BUSINESS** 爲方向，逐步完善更友好的安裝體驗、跨 Agent 適配、可審計任務日誌、技能評估與持續維護。未完成的能力只列爲規劃，不宣稱已交付。

---

**AKA.CRISTI · CREATE BEAUTIFULLY. BUILD INTELLIGENTLY. AUTOMATE EVERYTHING REASONABLE.**
