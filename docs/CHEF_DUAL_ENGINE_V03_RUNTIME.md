# CHEF Dual-Engine V0.3 isolated runtime proposal

Status: Draft implementation over PR #27 (`223d49d`), which stacks on the
PR #26 architecture (`17a16e0`). Neither upstream draft is merged by this work.
The six release gates in [SIX_GATE_STATUS.md](SIX_GATE_STATUS.md) remain BLOCKED.

## Design and scope

Keep the existing Python runtime, role definitions, Skills and read-only
`execute()` compatibility API. The CLI now uses `orchestrate()` with isolated
local Git clones rather than sharing the caller's checkout. Factory may propose
changes with Codex's workspace-write sandbox; Studio evaluates the actual
proposal and user journey read-only; QA runs a fresh, independent read-only
invocation with the actual deliverables and prior reports. Studio-only tasks
remain review tasks; a Studio finding requiring edits should be a new Factory
or hybrid task. No invocation success certifies acceptance or release.

The implementation choice is sequential, snapshot-based handoff rather than
concurrent writes or vendor-native subagents. This gives reproducible input
snapshots and avoids conflicting edits. It does **not** establish native
parent/child-agent evidence for release gate #13. A shared checkout was rejected
because roles could overwrite one another's deliverables. Adding another host
or UI is outside this proposal.

## Usage and storage

Use a trusted, clean, committed Git repository; preserve user changes first.
Place the database and artifacts outside the source repository:

```sh
python -m tools.chef_dual_engine --kind hybrid \
  --prompt 'Repair the issue; reproduce before changing it; evaluate the user journey' \
  --workspace /absolute/project --db /absolute/state/chef.sqlite3 --timeout 300
# Explicit recovery uses exactly the same arguments and source HEAD:
python -m tools.chef_dual_engine --kind hybrid \
  --prompt 'Repair the issue; reproduce before changing it; evaluate the user journey' \
  --workspace /absolute/project --db /absolute/state/chef.sqlite3 --timeout 300 \
  --resume TASK_UUID
```

Create the state parent directory beforehand. If `--db` is omitted it defaults
to a sibling of the source directory, so audit files do not dirty the source.
The CLI returns 0 for REVIEW_REQUIRED and 2 for a blocked invocation; 0 never
means QA PASS. The old `execute()` API remains read-only and non-isolated for
compatibility; callers needing the new guarantees must use `orchestrate()`.

SQLite `events` retains handoffs, STARTED and terminal evidence. `tasks` binds
task UUID to source HEAD, objective, engine, timeout and workspace. `attempts`
records an interrupted placeholder **before** launching the host and updates it
after completion. A separate SQLite exclusive mutex prevents duplicate workers
while allowing durable checkpoints. A killed controller leaves an interrupted
attempt; explicit resume counts it against the three-attempt role budget and
creates a fresh clone. Successful roles are reused only after checking snapshot
HEAD, clean working tree and patch SHA256. Configuration changes require a new
task, not silent reuse of old evidence.

Each handoff records role, objective, input outputs/workspaces, sandbox scope,
prohibitions, acceptance criteria, timeout, retries and escalation. Each role
has a separate directory and thread identity; missing or reused IDs and empty
reports block completion. Binary patches and complete parsed JSON events are
retained. Internal Git commits are local snapshots, with hooks/signing disabled,
not published commits. Git operations have a 60-second bound.

Codex invocations fix approval_policy=never and disable sandbox workspace
network access. The model connection itself needs a functioning authorized
host. Host MCP configuration and OS sandbox enforcement remain host trust
boundaries; these local clones are not a VM or a defense against a malicious
host. Use trusted projects/host integrations only. Timed-out or cancelled Codex
process groups are killed on POSIX; Windows uses taskkill /T /F and requires
real Windows verification. No permissive sandbox or credential replacement is
used to work around authentication errors.

New DB/lock files are created with POSIX mode 0600. Existing permissive or
non-regular logs are rejected without changing their permissions. Windows
requires a private state directory with appropriate inherited ACLs; POSIX modes
are not a substitute for Windows ACL verification.

Store DB/artifacts privately: prompts, reports and tool events may contain
project information. Keep the database, its lock file and `.runs` directory
together. The code never merges, publishes, installs Skills, clears gates or
modifies the source checkout. Subjective Studio decisions and independent
acceptance remain human review steps.

## Verification, evidence and limits

- Baseline: 128 tests, 3 skips.
- Final local Linux suite: 140 tests, 3 skips; compileall and diff whitespace
  checks passed. [Executed test log](evidence/chef-dual-engine-v03-unittest.txt).
- Twelve added offline tests cover snapshots, role separation, input handoff,
  read-only mutations, explicit recovery, crash accounting, retry exhaustion,
  evidence tampering, reused QA identity and private log permissions under umask 022 and database symlink rejection. The actual local CLI /
  Git / SQLite E2E uses a **scripted host**, including a failed Studio attempt,
  resume and separate QA. A real local subprocess test verifies a timed-out
  descendant cannot write afterward. Neither test is live AI acceptance.
- [Real Codex attempts](evidence/chef-dual-engine-v03-live-attempt.json): three
  bounded attempts on one task. First failed on read-only host initialization;
  retries created real thread IDs but failed with HTTP451, WebSocket and token
  refresh errors. Factory FAILED; Studio and runtime QA NOT_RUN. Real end-to-end
  acceptance remains BLOCKED. A login probe alone did not prove usable auth.
- An independent development reviewer inspected isolation, recovery, QA and
  release behavior. Findings led to snapshot checks, interrupted attempt
  accounting, external DB default, descendant cleanup, Git timeouts and signing
  overrides. That code review is separate from live runtime QA acceptance.
- Initial PR CI [43787736954](https://github.com/2ndforcecrew/aka-cristi-skills/actions/runs/43787736954)
  passed Linux/macOS but failed Windows test teardown: SQLite connection context
  managers do not close handles. Test fixtures now explicitly close connections;
  this preserves the real failure evidence and does not skip the checks.
- Existing three-platform PR CI runs this suite; local Linux success does not
  imply Windows/macOS, external UAT, visual UX or six-gate completion.

Next acceptance requires a usable authorized Codex host, a real representative
project, actual Factory patch/test outputs, Studio user-journey findings,
independent QA execution and human review. Do not relabel scripted evidence or
lower any threshold to obtain PASS. Do not change login credentials without
separate authorization.

Rollback: close the Draft PR or revert its commits. Original PR #26/#27 code and
all prior release rules remain available. Preserve runtime DB/artifacts for
review before deliberately deleting any local proposal snapshots.
