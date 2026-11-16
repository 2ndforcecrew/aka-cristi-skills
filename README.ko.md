# AKA.CRISTI Skills — 한국어 기능 소개

🌐 **Language / 언어：** [English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Français](README.fr.md)

**FROM EXPERIENCE TO CAPABILITY｜협업 경험을 재사용 가능한 능력으로**

## 프로젝트 소개

AKA.CRISTI Skills는 공개되고, 검토 가능하며, 로컬에 설치할 수 있는 **AI Agent 작업 흐름 스킬 패키지**입니다. 안전한 설치 프로그램과 Codex용 CHEF 협업 설정을 함께 제공합니다. AI가 복잡한 작업을 수행할 때 단순히 제안만 출력하는 것이 아니라 「명확한 목표 → 환경 확인 → 분담 실행 → 결과 검증 → 오류 복구 → 재사용 가능한 경험 기록」이라는 작업 방식을 따르도록 하는 것이 목표입니다.

**구분해야 할 점:** Skill은 Agent가 어떻게 일하는지를 안내하는 설명과 절차이며, **스스로 동작하는 AI 두뇌가 아닙니다**. GitHub, Codex, Hermes, Claude 또는 기타 서비스의 로그인 권한을 자동으로 얻지도 않습니다. 실제로 어떤 Agent를 호출할 수 있는지는 사용 중인 호스트 버전, 도구 연결 및 권한 부여에 따라 달라집니다.

이 저장소는 공개 배포판이며, AKA.CRISTI의 비공개 개발 저장소와 분리되어 있습니다. 비공개 작업 규칙, 계정 정보, 고객 데이터, 비공개 기록은 공개하지 않습니다.

## 현재 공개 상태: Codex Beta 출시됨

**[v1.0.0-beta.2](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.2)**는 공개 테스트 버전입니다. CHEF 규칙, Skills 4개, Codex 역할 설정 4개, Windows GUI 및 Windows / macOS / Ubuntu 통합 설치 명령을 제공합니다. **세 운영체제의 CI, Windows EXE 빌드, GitHub 출처 증명이 성공했습니다.** 외부 사용자 설치 검증과 실제 4 Agent 실행은 별도로 검증해야 합니다.

Git과 Python 3.11+가 필요합니다. 변경사항 미리보기를 보여주고 사용자가 `INSTALL`을 입력한 후에만 파일을 수정합니다.

Windows PowerShell:

```powershell
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git; if ($LASTEXITCODE -ne 0) { throw 'Clone failed' }; cd aka-cristi-skills; git checkout v1.0.0-beta.2; if ($LASTEXITCODE -ne 0) { throw 'Tag checkout failed' }; py -3 -m tools.quick_install --interactive
```

macOS / Ubuntu / Linux:

```bash
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git && cd aka-cristi-skills && git checkout v1.0.0-beta.2 && python3 -m tools.quick_install --interactive
```

`FILES_VERIFIED`는 파일 무결성 확인 결과이며 실제 Agent 시작을 보증하지 않습니다. Windows EXE에는 Authenticode 서명이 없습니다. 격리 환경에서 출처를 검증하세요.

**과거 검사에 관하여:** 이전 SkillSpector `DO_NOT_INSTALL` 및 검출 항목은 당시 특정 소스 버전의 기록이며 현재 Beta의 실시간 보안 판정이 아닙니다. 필수 설치/배포 도구가 아닙니다. [역사적 감사 기록](docs/SECURITY_REVIEW_2026-11-15.md)은 보존하되 검출 항목을 모두 실제 취약점 혹은 오탐이라 단정하지 않습니다.

## 1. 핵심 기능

### 1. CHEF Orchestrator: AI 작업 총지휘

파일: [chef-orchestrator/SKILL.md](skills/chef-orchestrator/SKILL.md)

- **목표와 수락 기준:** 사용자의 요구를 관찰 가능한 완료 조건, 권한 경계 및 중단 조건으로 전환합니다.
- **Inspect:** 먼저 프로젝트 규칙, 기존 설정, Git 상태 및 사용 가능한 도구를 읽어 작업 결과를 직접 덮어쓰지 않도록 합니다.
- **작업 분담:** 필요에 따라 Research, Creative, Coding, QA, Automation, Knowledge 등의 역할을 계획합니다.
- **추적 가능한 인계:** 작업 ID, 사용하는 실제 도구, 파일 범위, 입출력, 시간 제한, 재시도 횟수 및 수락 기준을 명확히 합니다.
- **실제 실행:** 실제 연결이 있을 때만 다른 Agent를 호출합니다. 사용할 수 없으면 `BLOCKED` 또는 `NOT_RUN`으로 명확히 기록하며, 위임 결과를 위조하지 않습니다.
- **독립적인 검증:** 코드, 테스트, 로그 및 실제 사용자 경로를 확인하고, 「완료」와 「검증됨」을 구분합니다.
- **자동 복구 방법:** 실패에 대해 경계가 있는 진단, 최소 수정 및 반복 테스트를 수행합니다. 되돌릴 수 없는 작업은 여전히 승인이 필요합니다.
- **경험 축적:** 실제로 검증된 반복 가능한 절차만 검토 대상 Skill로 추출하며, 자동으로 공개하거나 설치하지 않습니다.

### 2. Verified Change Loop: 문제 진단 및 수정 순환

파일: [verified-change-loop/SKILL.md](skills/verified-change-loop/SKILL.md)

문제 재현 → 증거 확인 → 최소·가역 수정 → 동일 시나리오 재실행 → 결과 비교 → 회귀 테스트 → 수락과 함께 전달. 코드 버그, CI 장애, 웹 기능 이상 및 복잡한 수정에 적합합니다.

### 3. Feature Journey Map: 실제 사용자 조작 경로

파일: [feature-journey-map/SKILL.md](skills/feature-journey-map/SKILL.md)

사용자가 진입, 초기화, 조작부터 눈에 보이는 결과에 이르는 전체 과정을 기록하고, 빈 상태, 권한 부족, 잘못된 입력, 느린 네트워크 등의 예외 경로도 다룹니다. 단위 테스트 통과만으로 제품을 사용할 수 있다고 선언하지 않습니다.

### 4. Skill Evaluation Gate: 스킬 품질 심사

파일: [skill-evaluation-gate/SKILL.md](skills/skill-evaluation-gate/SKILL.md)

실제 시나리오, 테스트 증거, 독립적인 재검토 및 릴리스 승인을 통해 Skill이 다음 단계로 진행할 수 있는지 판단합니다. Candidate, Tested, Reviewed, Approved / Released를 구분하고, 설치 성공과 실행 성공을 동일시하지 않습니다.

### 5. CHEF Global Rules: 프로젝트 간 작업 규칙

- **공개용으로 무해화한** CHEF 규칙을 `~/.codex/AGENTS.md` 또는 `$CODEX_HOME/AGENTS.md`에 기록합니다.
- 설치 전에 `preview`를 지원합니다. `--apply`를 붙여야 실제로 기록합니다.
- 관리 대상 표시 블록을 추가하는 방식으로 규칙을 덧붙여, 기존 내용을 최대한 유지합니다. 기존 파일은 백업됩니다.
- 관리 대상 블록의 검증과 제거를 지원합니다. 모든 컴퓨터의 비공개 규칙을 자동으로 동기화하는 것과 같지 않습니다.

기술 설명: [CHEF Global Rules + Multi-Agent Starter](docs/CHEF_GLOBAL_AND_MULTIAGENT.md).

### 6. Codex Native Subagents: 4개 역할

| 역할 | 이름 | 주요 책임 |
| --- | --- | --- |
| Research | `aka_research` | 사실 검색, 출처와 증거 정리 |
| Coding | `aka_coding` | 승인된 범위 내 프로그래밍, 수정 및 테스트 |
| QA | `aka_qa` | 최종 버전에 대한 독립적인 검토와 검증 |
| Automation | `aka_automation` | 안전하고 경계가 있는 자동화 흐름 설계 |

저장소는 4개의 네이티브 Codex 사용자 지정 Agent TOML 설정과 설치·검증 스크립트를 제공합니다. **설정을 설치했다고 해서 4개의 Agent가 실제로 시작된 것은 아닙니다**. 다른 업체의 계정을 호출할 수 있다는 의미도 아닙니다. 정식 판단에는 실제 Codex 서브스레드와 실행 기록이 필요합니다.

자세한 설명: [Codex Native Subagents V0.2](docs/CODEX_NATIVE_SUBAGENTS_V02.md).

### 7. 로컬 안전 Skill 설치 프로그램

- 로컬 미리 보기, 설치, 파일 무결성 검증, 업그레이드, 롤백, 제거를 지원합니다.
- 설치 프로그램이 관리하지 않거나 외부에서 변경된 Skill을 덮어쓰지 않습니다.
- 네트워크에서 코드를 자동으로 다운로드하지 않고, Skill 내부 스크립트를 실행하지 않으며, 비밀 정보를 업로드하지 않습니다.
- 제거 시 아카이브를 남깁니다. 롤백은 이전 백업이 실제로 존재할 때만 가능합니다.
- 바이러스 스캐너나 디지털 서명 검증이 아니며, 기존 CLI는 원클릭 GUI와 같지 않습니다. 후보 그래픽 인터페이스는 실제 환경에서의 수락이 여전히 필요합니다.

## 2. 친구 설치 방법 (Windows 11 / macOS / Linux)

사전 조건: [Git](https://git-scm.com/downloads)과 Python 3.11 이상을 설치하고, 권한이 있는 로컬 터미널을 사용하십시오. 먼저 저장소 내용을 직접 읽어보십시오. 설치 작업은 현재 사용자의 로컬 Codex 파일을 변경합니다.

### 1단계: 공개 저장소 다운로드

```powershell
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git
cd aka-cristi-skills
```

### 2단계: CHEF 전역 규칙과 주 Skill 미리 보기

```powershell
python -m tools.chef_global_rules preview
python -m tools.skill_installer preview skills/chef-orchestrator --target codex
```

### 3단계: 로컬 설치 명시적 승인

```powershell
python -m tools.chef_global_rules install --apply
python -m tools.skill_installer install skills/chef-orchestrator --target codex --apply
python -m tools.skill_installer install skills/verified-change-loop --target codex --apply
python -m tools.skill_installer install skills/feature-journey-map --target codex --apply
python -m tools.skill_installer install skills/skill-evaluation-gate --target codex --apply
```

### 4단계: 4개의 네이티브 Codex 역할 선택 설치

```powershell
python -m tools.codex_subagents preview
python -m tools.codex_subagents install --apply
python -m tools.codex_subagents verify
```

### 5단계: 설치된 파일 확인

```powershell
python -m tools.chef_global_rules verify
python -m tools.skill_installer verify chef-orchestrator --target codex
python -m tools.skill_installer verify verified-change-loop --target codex
```

이 명령들은 **설정과 파일**을 확인하는 것이며, Codex가 Skill을 호출했거나 4개의 Agent를 시작했음을 증명하지 않습니다. Codex 세션을 다시 열고 실제 위임을 테스트한 뒤, 실제 실행 증거를 저장하십시오.

사용 중인 컴퓨터에 Codex CLI가 설치되어 로그인되어 있다면, 엄격한 4개 역할 실행 수락을 수행할 수 있습니다(Codex 사용량이 소모될 수 있습니다).

```powershell
codex login status
python -m tools.verify_four_agents --timeout 600 --out four-agent-report.json
```

수락 결과는 `PASS`, `FAIL`, `INCONCLUSIVE`, `NOT_RUN`으로 구분해야 합니다. 실제 스레드 증거가 없으면 통과했다고 주장할 수 없습니다. 자세한 내용: [4개 Agent 실제 실행 수락](docs/FOUR_AGENT_RUNTIME_ACCEPTANCE.md).

## 3. 실제 능력과 제한

| 항목 | 현재 경계 |
| --- | --- |
| 공개 Skill 파일과 CLI 설치 프로그램 | 저장소에서 이미 제공. 읽고, 다운로드하고, 로컬에서 실행할 수 있음 |
| CHEF 전역 규칙 설치 | 안전한 미리 보기, 관리 대상 블록 설치와 검증을 제공 |
| 4개의 네이티브 Codex 역할 설정 | TOML과 설치/검증 도구를 제공 |
| 모든 실제 프로젝트 오류를 자동으로 감지하고 수정 | **보장할 수 없음**. 도구, 권한, 프로젝트 상황 및 실제 테스트에 의존 |
| Hermes, Claude, 기타 브랜드 Agent 자동 연결 | **범용 연결은 미구현**. 개별 API / MCP / CLI 적용이 필요 |
| 4개 Agent가 사용자의 실제 Codex 환경에서 실행 통과 | **로그인된 실제 Codex 기기에서 별도로 검증해야 함** |
| 성공 경험을 자동으로 Skill로 공개 | 평가 절차는 있지만, **심사 없는 자동 공개 시스템이 아님** |
| 전 기기 자동 동기화와 원클릭 그래픽 설치 | 이 공개 배포판에서 아직 검증된 기능이 아님 |

## 4. 안전 원칙

- 기존 비공개 규칙이나 관리 대상이 아닌 Skill을 덮어쓰지 않습니다. 먼저 미리 본 뒤 명시적으로 실행합니다.
- 비밀번호, API Key, 비공개 대화 및 고객 데이터를 업로드하지 않습니다.
- 로컬 테스트, 모의 출력 또는 Agent의 자기 진술을 실제 실행 결과로 오판하지 않습니다.
- 유료 작업, 권한 변경, 정식 릴리스, 데이터 삭제 등 고위험 작업을 자동으로 수행하지 않습니다.
- 모든 플랫폼 간 Agent 연결은 독립적인 승인과 실제 수락이 필요합니다.

## 5. 프로젝트 방향

**DESIGN × CODE × AI × AUTOMATION × BUSINESS**를 방향으로 삼아, 더욱 편리한 설치 경험, 플랫폼 간 Agent 적용, 감사 가능한 작업 로그, 스킬 평가와 지속적인 유지 관리를 단계적으로 개선합니다. 완료되지 않은 기능은 계획으로만 나열하고, 이미 전달된 것으로 선언하지 않습니다.

---

**AKA.CRISTI · CREATE BEAUTIFULLY. BUILD INTELLIGENTLY. AUTOMATE EVERYTHING REASONABLE.**
