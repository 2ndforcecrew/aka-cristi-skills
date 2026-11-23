# CHEF portable event schema v1

Each event contains `task_id`, `actor`, `status`, `stage`, `timestamp`, `evidence_ref`, and `note`.
Statuses: PLANNED, STARTED, COMPLETED, FAILED, BLOCKED, REVIEW_REQUIRED, VERIFIED.
Actors are host-provided identifiers, not proof of an independently spawned Agent.
`timestamp` is UTC Unix seconds. `evidence_ref` is an opaque non-secret identifier, never a raw filesystem path, URL token, or log body.
Retries and approvals are **decisions**, not commands. Do not interpret event records as permission to execute.
Never put secrets, prompts, customer data, credentials or private paths in fields.
A real execution is verified only when the host returns matching tool/thread evidence; an event alone is not proof.
