"""Explain unresolved release gates without claiming unavailable real-world evidence.

Read-only: never alters release status or security decisions.
"""
import argparse
import json

GATES = {
    "8": ("SECURITY_REVIEW", "NEEDS_SOURCE_EVIDENCE", "Obtain original scanner report and reproduce exact baseline; triage each finding."),
    "9": ("SIGNED_RELEASE", "NEEDS_RELEASE_UAT", "Signed candidate passed; verify immutable release and installer fail-closed paths."),
    "10": ("WINDOWS_GUI", "NEEDS_LIVE_UAT", "EXE smoke passed; clean Windows 11 standard-user install/reinstall/rollback remains."),
    "11": ("HOST_ADAPTERS", "NEEDS_LIVE_HOST", "Prove actual non-Codex host invocation and completion."),
    "12": ("EXTERNAL_UAT", "NEEDS_INDEPENDENT_TESTERS", "Independent Windows/macOS/Linux users must supply redacted evidence."),
    "13": ("CODEX_SUBAGENTS", "NEEDS_LOCAL_DIAGNOSIS", "Inspect existing sanitized root/child rollout before consuming more quota."),
}

def report():
    return {
        "release_status": "BLOCKED",
        "explanation": "Candidate build and CI successes are preserved; remaining external evidence is not a code failure.",
        "gates": [
            {"issue": int(issue), "name": name, "workstream": status,
             "next_action": action, "release_pass": False}
            for issue, (name, status, action) in GATES.items()
        ],
    }

def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only CHEF release gate diagnosis")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    data = report()
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        for gate in data["gates"]:
            print(f"#{gate['issue']} {gate['workstream']}: {gate['next_action']}")
        print("Overall release: BLOCKED (not a claim that all engineering tests failed)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
