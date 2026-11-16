# AKA.CRISTI Skills — 日本語機能説明

🌐 **Language / 言語：** [English](README.md) · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) · [日本語](README.ja.md) · [한국어](README.ko.md) · [Français](README.fr.md)

**FROM EXPERIENCE TO CAPABILITY｜協働の経験を再利用可能な能力へ**

## プロジェクトについて

AKA.CRISTI Skills は、公開され、査読可能で、ローカルにインストールできる **AI Agent ワークフロー・スキルパッケージ**です。安全なインストーラーと Codex 向けの CHEF 連携設定を備えています。AI が複雑なタスクを実行する際、提案を出すだけでなく、「明確な目標 → 環境の確認 → 分担して実行 → 結果の検証 → エラーからの復旧 → 再利用可能な経験の記録」という作業方法に従うことを目指します。

**区別が必要です：** Skill は Agent の働き方を定める説明と手順であり、**自律的に動作する AI の頭脳ではありません**。GitHub、Codex、Hermes、Claude、その他のサービスのログイン権限を自動で取得することもありません。実際にどの Agent を呼び出せるかは、お使いのホストのバージョン、ツールの接続、認可に依存します。

本リポジトリは公開配布版であり、AKA.CRISTI の非公開開発リポジトリとは分離されています。非公開の作業ルール、アカウント情報、顧客データ、非公開の履歴は公開しません。

## 現在の公開状況：Codex Beta リリース済み

**[v1.0.0-beta.2](https://github.com/2ndforcecrew/aka-cristi-skills/releases/tag/v1.0.0-beta.2)** は公開されたテスト版です。CHEF ルール、4つの Skills、4つの Codex ロール設定、Windows GUI、および Windows / macOS / Ubuntu 用の統一インストールコマンドを含みます。**3 OS の CI、Windows EXE ビルド、GitHub 由来証明は成功しました。** 独立ユーザー試験と実際の4 Agent 起動証明は引き続き必要です。

Git と Python 3.11+ が必要です。変更内容をプレビューし、`INSTALL` と入力した場合のみインストールします。

Windows PowerShell:

```powershell
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git; if ($LASTEXITCODE -ne 0) { throw 'Clone failed' }; cd aka-cristi-skills; git checkout v1.0.0-beta.2; if ($LASTEXITCODE -ne 0) { throw 'Tag checkout failed' }; py -3 -m tools.quick_install --interactive
```

macOS / Ubuntu / Linux:

```bash
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git && cd aka-cristi-skills && git checkout v1.0.0-beta.2 && python3 -m tools.quick_install --interactive
```

`FILES_VERIFIED` はファイル整合性の結果であり、Agent の実際の起動を証明しません。Windows EXE に Authenticode 署名はありません。隔離したテスト環境で GitHub の由来を確認してください。

**過去のスキャンについて：** 古い SkillSpector の `DO_NOT_INSTALL` 評価や検出項目は当時の固定スナップショットに対する履歴で、現在の Beta に対する最新の安全性評価ではありません。SkillSpector はインストールの必須要件ではありません。履歴は[監査記録](docs/SECURITY_REVIEW_2026-11-15.md)に保存し、未確認の検出項目をすべて脆弱性とも誤検知とも断定しません。

## 一、コア機能

### 1. CHEF Orchestrator：AI タスクの総指揮

ファイル：[chef-orchestrator/SKILL.md](skills/chef-orchestrator/SKILL.md)

- **目標と受け入れ条件：** ユーザーの要望を、観測可能な完了条件、認可の境界、停止条件に変換します。
- **Inspect：** まずプロジェクトのルール、既存の設定、Git の状態、利用可能なツールを確認し、作業成果を直接上書きしないようにします。
- **タスク分担：** 必要に応じて Research、Creative、Coding、QA、Automation、Knowledge などの責務を計画します。
- **追跡可能な引き継ぎ：** タスク ID、使用する実際のツール、ファイル範囲、入出力、タイムアウト、再試行回数、受け入れ基準を明確にします。
- **実際の実行：** 実際の接続がある場合にのみ他の Agent を呼び出します。利用できない場合は `BLOCKED` または `NOT_RUN` として明確に記録し、委任結果を偽造しません。
- **独立した検証：** コード、テスト、ログ、実際のユーザー経路を確認し、「完了」と「検証済み」を区別します。
- **自動復旧の方法：** 失敗に対して、境界を定めた診断、最小限の修正、再テストを行います。不可逆の操作には引き続き認可が必要です。
- **経験の蓄積：** 実際に検証された繰り返し可能な手順のみを、査読対象の Skill として抽出し、自動で公開・インストールすることはありません。

### 2. Verified Change Loop：問題診断と修正の閉ループ

ファイル：[verified-change-loop/SKILL.md](skills/verified-change-loop/SKILL.md)

問題の再現 → 証拠の確認 → 最小限で可逆の修正 → 同じシナリオの再実行 → 結果の比較 → 回帰テスト → 受け入れを伴う納品。コードのバグ、CI の障害、Web 機能の異常、複雑な修正に適しています。

### 3. Feature Journey Map：実際のユーザー操作経路

ファイル：[feature-journey-map/SKILL.md](skills/feature-journey-map/SKILL.md)

ユーザーが入口、初期化、操作から目に見える結果に至るまでの完全な流れを記録し、空の状態、権限不足、誤った入力、遅いネットワークなどの異常経路もカバーします。単体テストの通過だけで製品が使えると宣言することは避けます。

### 4. Skill Evaluation Gate：スキルの品質審査

ファイル：[skill-evaluation-gate/SKILL.md](skills/skill-evaluation-gate/SKILL.md)

実際のシナリオ、テスト証拠、独立した再審査、リリース認可によって、Skill が次の段階に進めるかを判断します。Candidate、Tested、Reviewed、Approved / Released を区別し、インストール成功と実行成功を同一視しません。

### 5. CHEF Global Rules：プロジェクト横断の作業ルール

- **公開用に無害化した** CHEF ルールを `~/.codex/AGENTS.md` または `$CODEX_HOME/AGENTS.md` に書き込みます。
- インストール前に `preview` に対応しています。`--apply` を付けて初めて実際に書き込みます。
- 管理対象のマーカーブロックを追加する方式でルールを追記し、既存の内容を可能な限り保持します。既存ファイルはバックアップされます。
- 管理対象ブロックの検証とアンインストールに対応しています。すべての PC の非公開ルールを自動同期することと等しくありません。

技術説明：[CHEF Global Rules + Multi-Agent Starter](docs/CHEF_GLOBAL_AND_MULTIAGENT.md)。

### 6. Codex Native Subagents：4つのロール

| ロール | 名称 | 主な責務 |
| --- | --- | --- |
| Research | `aka_research` | 事実の検索、出典と証拠の整理 |
| Coding | `aka_coding` | 認可された範囲でのプログラミング、修正、テスト |
| QA | `aka_qa` | 最終版に対する独立した審査と検証 |
| Automation | `aka_automation` | 安全で境界のある自動化フローの設計 |

リポジトリには、4つのネイティブ Codex カスタム Agent の TOML 設定と、インストール・検証スクリプトが含まれています。**設定のインストールは、4つの Agent が実際に起動したことを意味しません**。ましてや他社のアカウントを呼び出せることを意味しません。正式な判断には、実際の Codex サブスレッドと実行記録が必要です。

詳細：[Codex Native Subagents V0.2](docs/CODEX_NATIVE_SUBAGENTS_V02.md)。

### 7. ローカル安全 Skill インストーラー

- ローカルプレビュー、インストール、ファイル完全性チェック、アップグレード、ロールバック、アンインストールに対応しています。
- インストーラーの管理対象でない Skill や、外部で変更された Skill の上書きを拒否します。
- ネットワークからコードを自動ダウンロードせず、Skill 内部のスクリプトを実行せず、秘密情報をアップロードしません。
- アンインストール時はアーカイブを残します。ロールバックは、以前のバックアップが実際に存在する場合にのみ可能です。
- これはウイルススキャナーでもデジタル署名検証でもありません。既存の CLI はワンクリック GUI と等しくありません。候補のグラフィカルインターフェースは、実際の環境での受け入れが引き続き必要です。

## 二、友人向けインストール方法（Windows 11 / macOS / Linux）

前提条件：[Git](https://git-scm.com/downloads) と Python 3.11 以降をインストールし、権限のあるローカルターミナルを使用してください。まずリポジトリの内容を自分で読んでください。インストール操作は、現在のユーザーのローカル Codex ファイルを変更します。

### ステップ 1：公開リポジトリをダウンロードする

```powershell
git clone https://github.com/2ndforcecrew/aka-cristi-skills.git
cd aka-cristi-skills
```

### ステップ 2：CHEF グローバルルールとメイン Skill をプレビューする

```powershell
python -m tools.chef_global_rules preview
python -m tools.skill_installer preview skills/chef-orchestrator --target codex
```

### ステップ 3：ローカルインストールを明示的に承認する

```powershell
python -m tools.chef_global_rules install --apply
python -m tools.skill_installer install skills/chef-orchestrator --target codex --apply
python -m tools.skill_installer install skills/verified-change-loop --target codex --apply
python -m tools.skill_installer install skills/feature-journey-map --target codex --apply
python -m tools.skill_installer install skills/skill-evaluation-gate --target codex --apply
```

### ステップ 4：4つのネイティブ Codex ロールを任意でインストールする

```powershell
python -m tools.codex_subagents preview
python -m tools.codex_subagents install --apply
python -m tools.codex_subagents verify
```

### ステップ 5：インストールされたファイルを確認する

```powershell
python -m tools.chef_global_rules verify
python -m tools.skill_installer verify chef-orchestrator --target codex
python -m tools.skill_installer verify verified-change-loop --target codex
```

これらのコマンドは**設定とファイル**を確認するものであり、Codex が Skill を呼び出したことや、4つの Agent を起動したことを証明するものではありません。Codex セッションを開き直し、実際の委任をテストして、実際の実行証拠を保存してください。

お使いの PC に Codex CLI がインストールされ、ログイン済みであれば、厳格な4ロール実行受け入れを実行できます（Codex の利用枠を消費する可能性があります）。

```powershell
codex login status
python -m tools.verify_four_agents --timeout 600 --out four-agent-report.json
```

受け入れ結果は `PASS`、`FAIL`、`INCONCLUSIVE`、`NOT_RUN` で区別してください。実際のスレッド証拠がなければ、通過したと主張できません。詳しくは[4 Agent 実際の実行受け入れ](docs/FOUR_AGENT_RUNTIME_ACCEPTANCE.md)をご覧ください。

## 三、実際の能力と制限

| 項目 | 現在の境界 |
| --- | --- |
| 公開 Skill ファイルと CLI インストーラー | リポジトリで提供済み。読む、ダウンロードする、ローカルで実行できる |
| CHEF グローバルルールのインストール | 安全なプレビュー、管理対象ブロックのインストールと検証を提供 |
| 4つのネイティブ Codex ロール設定 | TOML とインストール／検証ツールを提供 |
| すべての実際のプロジェクトエラーを自動検出・修正する | **保証できない**。ツール、権限、プロジェクトの状況、実際のテストに依存する |
| Hermes、Claude、その他ブランドの Agent への自動接続 | **汎用接続は未実装**。個別の API / MCP / CLI 適応が必要 |
| 4 Agent がユーザーの実際の Codex 環境で実行に通過する | **ログイン済みの実際の Codex デバイスで個別に検証する必要がある** |
| 成功経験を自動で Skill として公開する | 評価フローはあるが、**審査なしの自動公開システムではない** |
| 全デバイスの自動同期とワンクリック・グラフィカルインストール | この公開配布版では、まだ検証された機能ではない |

## 四、安全原則

- 既存の非公開ルールや管理対象外の Skill を上書きしないこと。まずプレビューし、明示的に実行すること。
- パスワード、API Key、非公開の対話、顧客データをアップロードしないこと。
- ローカルのテスト、模擬出力、Agent の自己申告を、実際の実行結果と誤認しないこと。
- 支払い操作、権限変更、正式リリース、データ削除などの高リスク操作を自動で行わないこと。
- プラットフォームを横断するすべての Agent 接続には、独立した認可と実際の受け入れが必要です。

## 五、プロジェクトの方向性

**DESIGN × CODE × AI × AUTOMATION × BUSINESS** を方向性として、より使いやすいインストール体験、プラットフォーム横断の Agent 適応、監査可能なタスクログ、スキルの評価と継続的なメンテナンスを段階的に改善します。未完了の能力は計画としてのみ挙げ、納品済みとは宣言しません。

---

**AKA.CRISTI · CREATE BEAUTIFULLY. BUILD INTELLIGENTLY. AUTOMATE EVERYTHING REASONABLE.**
