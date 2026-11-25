---
name: feature-journey-map
description: Map a real product feature from entry and setup through actions, observable results and failure edges, then produce replayable test scenarios.
---

# Feature Journey Map

## When to use
Before implementing or verifying a web/app feature whose real user behavior is ambiguous, or when a test passes without proving the visible journey.

## Inputs
Current feature route/screen, expected outcome, relevant permissions, test account/fixture and observed behavior. Never copy secrets or private customer data into the map.

## Procedure
1. **Entry**: note exact route, screen and method for reaching it. Confirm it exists.
2. **Setup**: document authorized account state, seeded data, flags, device and access constraints. Use redacted example values.
3. **Actions**: list the sequence of user operations and reliable targets (role, label, accessible name or stable test ID); never rely on guessed selectors.
4. **Result**: specify observable success conditions (UI state, output file, confirmed database change or downstream event) and capture evidence.
5. **Edges**: cover empty state, invalid input, slow network, missing permission, retry paths and recovery.
6. **Replay**: test the actual journey in an isolated environment and preserve screenshots/logs/exit codes; mark untested routes `NOT RUN`.
7. **Maintain**: update the map when routes, state or permissions change; do not treat an old map as proof of current behavior.

## Deliverable template
```yaml
feature: example-name
entry: /known-route
setup: authorized fixture and expected state
actions:
  - target: accessible button name
    action: click
result: visible, verifiable outcome
edges:
  - missing permission
  - empty state
evidence: reference-to-saved-artifact
status: NOT RUN
```
Values above are illustrative, never operational evidence. Include owner, version, checked date and result when actually tested.

## Verification

A journey map is verified only when every check below holds. Anything else is a draft map, not evidence the feature works.

- [ ] Every scenario in the map is replayable: the entry route exists, each action has a reliable target (role, label, accessible name, or stable test ID), and the sequence was actually run.
- [ ] The real user journey was replayed in an isolated environment — the visible result was observed, not assumed from a passing unit test.
- [ ] Failure paths were replayed, not just listed: empty state, invalid input, slow network, missing permission, and retry/recovery.
- [ ] Evidence is preserved for each replay: screenshots, logs, and exit codes. A scenario without evidence is NOT_RUN.
- [ ] The map matches the current routes, state, and permissions. An old map is not proof of current behavior — update it or mark it stale.
- [ ] Observable success conditions were checked against the actual UI state, output file, database change, or downstream event — not against the map's own description of them.
- [ ] No secrets or private customer data were copied into the map or its evidence.

## Safety
Do not bypass authentication, permissions or Captcha. Request only minimum authorized access; avoid storing credentials.

## Provenance
Inspired by user-supplied Lauren Tan verification engineering fieldnotes; independently adapted for AKA.CRISTI. Not an official third-party Skill.

## Common Rationalizations

| Rationalization | Rebuttal |
| --- | --- |
| "I know this feature; I can map it from memory." | The map is built from the actual route and screen. Confirm the entry exists — memory is not evidence. |
| "The happy path works; edge cases are edge cases." | Empty state, invalid input, missing permission and retry paths are part of the deliverable, not optional extras. |
| "A passing unit test proves the journey." | A test passing without proving the visible journey is exactly the failure this skill guards against. |
| "The test found the button, so the selector is fine." | Never rely on guessed selectors. Use role, label, accessible name or a stable test ID. |
| "The map is from last month; it is still valid." | Routes, state and permissions change. An old map is not proof of current behavior — update it or mark it stale. |
| "Screenshots are optional; the log is enough." | Replay preserves screenshots, logs and exit codes. Untested routes are NOT_RUN, not verified. |

## Red Flags

- A map written without opening the actual route or screen.
- Edge cases listed but never replayed, or missing entirely.
- Guessed or brittle selectors in the actions list.
- An old map presented as current evidence after routes or permissions changed.
- Secrets or private customer data copied into the map.
- Status NOT_RUN reported as though the journey were verified.
