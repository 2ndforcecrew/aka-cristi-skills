# Universal candidate verification — 2026-11-16

This is a development verification record, not release approval. No main merge, Release publication, permission change or production deployment is authorized.

## Code and regression evidence

The first recovery fix is 7054356a18314e82dc26a81f916817fe0c4d55f0, proposed in Draft PR #30 on top of #25. Its [three-platform CI](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43795572199) passed: Windows executed all 254 tests without skips; Linux/macOS exercised supported tests and Linux also ran the real Tk smoke under Xvfb. All 14 tests skipped on the local privilege-limited Windows 10 host executed successfully on the Windows CI runner.

The follow-up patch adds safe quoted Builder descriptions, Unicode separator preservation, checked destination consistency, fail-closed Lifecycle traversal/read errors, ancestor/junction checks, and explicit isolated Skill-probe startup/UTF-8 handling. Two unrelated security checks no longer depend on symlink privileges.

Local follow-up validation: Windows 10 Pro 19045, Python 3.13.11; 265 tests, 253 passed and 12 privilege-dependent skips. Builder/Lifecycle 15/15; expanded Ruff, Mypy over ten source files, compileall and diff checks passed. The actual Windows junction tests passed. Final follow-up CI must be read from PR #30 Checks; the earlier green run does not certify a later SHA.

## Real Codex evidence

- Codex CLI 0.169.0 using the existing ChatGPT login completed a real read-only feature-journey-map invocation. A successful Get-Content command returned the exact scanned Skill content and an unknown fixture nonce; the final answer used the Skill method and honestly marked unavailable application behavior NOT_RUN.
- Four real native roles (aka_research, aka_coding, aka_qa, aka_automation) completed a synthetic read-only handoff. The host now returns task_name rather than agent_id. The original automatic report is retained as INCONCLUSIVE.
- Independent reviewers supplemented that report with the official Codex app connector: the original call_id uniquely matches a started activity carrying the child UUID/task path; each exact child rollout confirms the same parent, role/path and a nonempty completed reply. Existing strict child_assessment checks passed at the actual run start time for all four roles. This is a scoped runtime PASS, not a claim that the legacy automatic parser supports the new shape.
- Private raw rollouts, account data and local paths are not published. Sanitized command/output hashes, connector identity links, metadata/completion summaries and reviewer records are retained locally for inspection.

## Skill scan scope

Four exact Skill Markdown files were staged separately and scanned with SkillSpector 2.12.0, --no-llm: recommendation SAFE, zero findings, successful execution, 100% file coverage, no analyzer failures. feature-journey-map has no unresolved references and was used for the temporary probe. Two other reports retain reference-resolution caveats for repository tools/runtime artifacts. These results do not certify the helper scripts, entire repository, any plugin or hosted backend.

## Formal gates

| Gate | Current state and next required evidence |
| --- | --- |
| #8 Security | BLOCKED: the original external 67/24 report/version/mode/source remains unavailable in the checked materials. Older separate Markdown SAFE scans do not replace it. Entire package security remains separate. |
| #9 Signed candidate | BLOCKED for this fix: build smoke is available, but the signing workflow restricts trusted refs. No allowlist, signing permission or publisher identity was broadened. |
| #10 GUI | Engineering tests/build smoke PASS in their observed environments; clean Windows 11 standard-user external journey remains NOT_RUN. Existing Tk poll callback messages still require follow-up. |
| #11 Cross-host | Codex scoped Skill/four-role runtime evidence PASS; Claude/Hermes/ChatGPT runtime acceptance remains NOT_RUN/BLOCKED. None of those native CLIs was found on this Windows host. |
| #12 Independent UAT | BLOCKED: no actual independent Windows/macOS/Linux user records were found in the supplied review materials. CI and another AI reviewer do not replace human external UAT. |
| #13 Four named Codex roles | Scoped live runtime PASS via strict cross-source identity and completion evidence; legacy CLI automatic schema support remains a documented limitation. |

The support matrix and release authorization are not expanded by this record. No gate is closed merely by changing a label. Remaining evidence must be obtained from real authorized environments/testers.
