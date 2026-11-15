# Personal workspace: manual pull and local recovery

`tools/workspace_sync.py` supplies an offline filesystem backend. It never
authenticates, downloads, executes incoming code, pushes changes, or removes
files omitted from a later manifest. The controller independently verifies that
the selected private repository belongs to the active GitHub account. The sync
backend validates manifest identity and binds subsequent receipts to that same
owner/repository and the supplied local roots.

## Manifest and permitted destinations

Schema version is exactly `1`, `sync_mode` is exactly `manual`, and the source
revision is an immutable, lowercase 40-character Git commit SHA. Every file must
have a verified lowercase SHA-256 digest. Unknown manifest keys, duplicate and
case-colliding paths, file/directory overlaps, extra payloads, missing payloads,
and mismatched digests are rejected before any target write.

| Repository path | Local destination |
| --- | --- |
| `rules/AGENTS.md` | `<codex_home>/AGENTS.md` |
| `agents/<safe-name>.toml` | `<codex_home>/agents/<safe-name>.toml` |
| `skills/<safe-name>/<safe-relative-file>` | `<skills_root>/<safe-name>/<safe-relative-file>` |

Names are bounded ASCII components. Traversal, hidden components, Windows
reserved device names, authentication/credential/chat/session filenames,
symbolic links, reparse points, hard-linked files, special files, and overlapping
roots are refused. Each file is at most 1 MiB, a snapshot is at most 16 MiB and
500 files. Recognizable private keys, GitHub/OpenAI tokens and non-placeholder
credential assignments are rejected on incoming sync too. This detector is an
additional safeguard, not a guarantee that arbitrary source text contains no
private information; review the local diff before confirming.

## Preview and apply

```python
from pathlib import Path
from tools.workspace_sync import SyncEngine

engine = SyncEngine(
    state_dir=Path("/private-workspace-state"),
    codex_home=Path("/codex-home"),
    skills_root=Path("/skills-root"),
)
# manifest/files/source_revision come from the verified repository adapter.
plan = engine.preview(manifest, files, source_revision)
# Display every plan["changes"] diff and plan["conflicts"] locally.
result = engine.apply(plan, confirmed=True)  # only after the user's confirmation
```

Preview returns `changes` entries with `path`, `action`, and `diff`; actions are
`CREATE`, `ADOPT`, `UPDATE`, `UNCHANGED`, or `CONFLICT`. Diffs include the complete
local and incoming content, with full-file context; non-UTF-8 data is represented
as base64. Diffs and opaque `_plan_id` values belong in the local preview only.
They must not be printed in diagnostics, sent to analytics, or copied into an
external issue. The displayed source revision is included in the result.

An existing unowned file with different bytes is a conflict. An identical
unowned file may be adopted, and its complete previous content/mode is backed
up. Later updates require the current file digest to match the last installed
digest. A deleted or locally edited tracked file is a conflict. Unrelated local
files and files absent from the incoming manifest are preserved.

Plans are process-local capabilities held by the same `SyncEngine` instance.
Payloads are immutable byte copies; later modification of the input dictionary
does not authorize different source bytes. Edited, fabricated, other-engine,
or stale plans are rejected. Any local target content/mode or sync-state change
since preview requires a fresh preview. Every apply and restore requires the
literal Boolean `confirmed=True`.

## Backups and restore

Before the first target write, the engine durably saves a local JSON receipt
with the original target bytes/modes, ownership metadata, source revision, and
the known expected post-write state. A private ledger records the receipt hash.
Each deterministic write produces a new immutable receipt revision; an atomic
ledger update selects that revision by filename and hash. Failed ledger writes
leave the previous referenced receipt intact. After a successful pointer commit,
only the same backup's immediately superseded committed receipt is reclaimed;
other backup IDs and unreferenced crash orphans remain untouched. This bounds
normal receipt storage to one current revision per backup, instead of one full
snapshot per file checkpoint. Observed arbitrary concurrent edits are never added
to the authorized rollback set. Files use atomic replacement and fsync.
Nonblocking locks protect both the state directory and each destination root.
The destination locks are shared across account/repository profiles, including
profiles that share only one destination root. Apply and restore acquire them
before revalidating their target preconditions. Lock files sit in each target
root's parent under an opaque deterministic name; preview never creates them.

On a normal filesystem failure, only known successful writes are undone. If
current files differ from the expected write set, automatic rollback stops with
`BLOCKED_ROLLBACK_REQUIRED` and preserves the receipt for manual review. A failed
operation that successfully undoes its writes returns `FAILED_ROLLED_BACK` and
can be retried with a fresh preview. Restore failures likewise attempt to return
to their known pre-restore contents and permit retry when that succeeds.

```python
engine.backups()  # [{"id": ..., "created_at": ..., "status": ...}]
engine.restore(backup_id, confirmed=True)
engine.installed_skills()  # names and INSTALLED / MODIFIED only
engine.audit_log()  # fixed event/status enums only
```

Restore validates receipt integrity, roots, allowlisted targets and all stored
content hashes before changing any target. It refuses post-sync user edits or
incompatible subsequent ownership state. A successful restore reinstates the
previous bytes/modes and ownership; files created by that transaction are
removed. Empty directories created along the way can remain. Existing unrelated
files and directories are never recursively removed.

An explicitly confirmed restore can also recover an interrupted `APPLYING` or
`RESTORING` receipt. It reconstructs the exact expected footprint from committed
`after` entries and the persisted `restore_progress`, verifies local contents
against that footprint, and restores the transaction's original `before` state.
It never resumes forward installation or treats a fresh arbitrary snapshot as
authorized recovery data. If a write occurred before its checkpoint was durably
saved, or another process edited a file, recovery refuses with
`ROLLBACK_CONFLICT` for manual review. Completed, failed rollback, and blocked
receipts keep their existing status guards.

On POSIX, local state directories are mode `0700` and receipts, lock, audit and
ledger files are `0600`. Windows uses a protected DACL granting only the current
process user's SID full access, with no plaintext/permissive fallback. The
Windows DACL path requires validation on a real Windows runner; Linux tests do
not establish Windows behavior. Existing destination file mode bits are retained
on replacement where the platform supports them; Windows destination ACLs follow
the destination directory's inheritance rules.

Constructor, `backups()`, `installed_skills()` and `audit_log()` do not create
directories when state is absent. Preview may create only its private state and
lock directories, never configuration destinations. Public errors expose fixed
codes through `WorkspaceSyncError.code`; audit entries contain only fixed
`event` and `status` values, without content, identities, tokens or paths.

## Verification and limits

Run the isolated integration tests from the repository root:

```bash
python -m unittest discover -s tests -p test_workspace_sync.py -v
python -m compileall -q tools/workspace_sync.py tests/test_workspace_sync.py
```

Coverage includes first pull, two independent machines, updates, adoption and
conflicts, stale/tampered previews, backup editing, apply/restore failures and
retry, unrecognized concurrent mutations, real cross-process locking, manifest
validation, secret rejection, owner-only POSIX modes, symlinks and unrelated
file preservation. Regression tests also cover different profiles racing to
write the same destination and a failed final restore-ledger commit followed by
reopening the engine and retrying. Further tests cover bounded receipt counts,
retaining crash orphans, recovery after interrupted apply/restore checkpoints,
and refusing an uncheckpointed write. No network, account, repository writes or
live authentication are involved.

The lock coordinates this application; it cannot stop another editor or a
hostile process from replacing directories between portable filesystem calls.
Close other configuration editors while applying/restoring. Deterministic
preconditions and rollback checks refuse observed edits, but this is not an
OS-wide filesystem transaction. Sudden power/process loss between a target
write and its next checkpoint can leave an incomplete transaction requiring
manual review. Immutable receipt revisions keep the prior committed ledger
pointer valid; a failed checkpoint is never silently declared successful. Local
receipts contain private configuration and must not be published or synchronized
to the workspace repository.
