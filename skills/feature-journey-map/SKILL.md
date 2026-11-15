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

## Safety
Do not bypass authentication, permissions or Captcha. Request only minimum authorized access; avoid storing credentials.

## Provenance
Inspired by user-supplied Lauren Tan verification engineering fieldnotes; independently adapted for AKA.CRISTI. Not an official third-party Skill.
