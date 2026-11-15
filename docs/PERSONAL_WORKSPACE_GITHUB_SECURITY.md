# Personal workspace GitHub security

The adapter owns only repositories belonging to the authenticated personal account.
It verifies the API identity, exact owner/name/URL, private visibility and push
permission before initialization or snapshot reads. Creation and initialization
require separate explicit `confirmed=True` consent. Existing repositories are never
silently replaced.

## Authentication boundary

`GhClient` retains its controller-facing name for compatibility. Production
transport delegates to `tools.workspace_auth.AuthClient`: GitHub device OAuth,
OS credential storage and bounded HTTPS REST. `auth=` permits isolated test
transports. The legacy `executable` argument does not execute a process. Neither
`gh auth login`, `gh auth token`, global CLI configuration nor global CLI keyring
entries are used or changed. Credentials are never returned by this adapter.

A registered OAuth application's **public client ID** must be configured through
`AKA_WORKSPACE_OAUTH_CLIENT_ID`. Missing configuration reports
`OAUTH_CLIENT_ID_REQUIRED`; it cannot report Connected. See the auth module for
its requested scopes, OS credential-store prerequisites, device challenge,
cancellation, expiration and timeout handling. Token environment overrides and
plaintext credentials are forbidden there. ChatGPT authorization remains separate.

This design deliberately avoids claiming that a separate `GH_CONFIG_DIR` isolates
GitHub CLI credentials. Official GitHub CLI documentation states that login may
fall back to a plaintext file if the credential store is unavailable. The hidden
`--secure-storage` login flag is not a secure-only guarantee. Upstream source also
uses shared credential-store service names. Reusing those mechanisms would risk
changing another CLI account's credential state.

Sources inspected during implementation:

- [Official gh auth login manual](https://cli.github.com/manual/gh_auth_login)
- [Official gh login implementation](https://github.com/cli/cli/blob/trunk/pkg/cmd/auth/login/login.go)
- [Official gh credential configuration implementation](https://github.com/cli/cli/blob/trunk/internal/config/config.go)
- [GitHub Git trees API](https://docs.github.com/en/rest/git/trees)
- [GitHub Git references API](https://docs.github.com/en/rest/git/refs)

## Public initialization

Only `workspace.json` plus the nine public destination paths are accepted:

- `rules/AGENTS.md`
- `agents/research.toml`, `agents/coding.toml`, `agents/qa.toml`, `agents/automation.toml`
- `skills/chef-orchestrator/SKILL.md`
- `skills/verified-change-loop/SKILL.md`
- `skills/feature-journey-map/SKILL.md`
- `skills/skill-evaluation-gate/SKILL.md`

The manifest must have the exact schema, current owner/repository, manual sync,
exact target mappings and matching SHA-256 hashes. Local home directories,
conversations and credentials are never discovered or uploaded. Conventional
credential markers are rejected as an additional defense; this is not a general
secret classifier. The controller must construct exports from its trusted public
source allowlist, never arbitrary user input or local private state.

An empty repository needs a first commit before GitHub's Git tree/commit APIs are
usable. Initialization first seeds the public manifest through the Contents API,
then creates one complete tree and commit. It updates the branch without force.
A failed request can leave the public seed or an unreachable public commit.
Retry resumes only an exact manifest-only seed, or returns the immutable revision
for an exact completed initialization. Unexpected files, nonregular Git modes,
changed payloads or mismatching manifest cause refusal. No branches are deleted,
no force pushes are used and no private local data is included in either commit.
Concurrent changes may cause a safe refusal; retry must recheck the remote state.

## Immutable snapshot boundary

Reads resolve the default branch once to a full 40-character commit SHA. The
manifest, recursive tree and payloads are then fetched at that exact revision.
Only manifest-listed payloads are downloaded; SHA-256 integrity and Git regular
file mode `100644` are required. Traversal, duplicate paths, unsupported targets,
credential/state paths, symlinks, submodules and truncated trees are refused.
Per-file data is capped at 2 MiB, a snapshot at 16 MiB and a manifest at 100
payload entries; the auth transport independently bounds responses and rejects
redirects. There is no archive extraction, shell, Git checkout, hook execution or
remote code execution.

Failures contain fixed safe codes, never server bodies, raw exceptions or token
values. The adapter translates `HTTP_404` to `REPO_NOT_FOUND` and `HTTP_409` to
`API_CONFLICT`; the empty-repository reference-list preflight handles 409 as the
GitHub API's documented empty-repository case. Other failures remain safe codes.

## Verification limits

Tests use temporary local directories and injected mock authentication/API
transports. No real login, existing authentication read, repository creation,
network write or account mutation was performed. Real registered-app OAuth and
OS credential-store behavior require separate platform acceptance testing.
