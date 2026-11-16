"""Fail-closed summary of pinned SkillSpector scans.

Does not suppress findings, certify a package, or authorize a release.
Raw scan JSON is treated as untrusted data and stays in ephemeral CI storage.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def summarize(path: Path, scanner_exit: int) -> dict[str, Any]:
    result: dict[str, Any] = {"status": "BLOCKED", "scanner_exit": scanner_exit}
    try:
        raw = path.read_bytes()
        if not raw or len(raw) > 32 * 1024 * 1024:
            raise ValueError("missing or oversized scanner output")
        report = json.loads(raw)
        if not isinstance(report, dict):
            raise ValueError("scanner output must be an object")
        risk, coverage = report.get("risk_assessment"), report.get("analysis_completeness")
        if not isinstance(risk, dict) or not isinstance(coverage, dict):
            raise ValueError("missing required scanner sections")
        recommendation = risk.get("recommendation")
        percentage = coverage.get("coverage_percent")
        complete = coverage.get("is_complete") is True
        executed = report.get("execution_successful") is True and coverage.get("execution_successful") is True
        issues = report.get("issues")
        exceptions = coverage.get("ledger_exceptions")
        dep = coverage.get("dependency_inspection")
        if not isinstance(issues, list) or not isinstance(exceptions, list):
            raise ValueError("missing scanner issue/coverage ledger")
        suppressed = report.get("suppressed_count", 0)
        if not isinstance(suppressed, int) or suppressed != 0:
            raise ValueError("report contains suppressed or unverified findings")
        result.update({
            "report_sha256": hashlib.sha256(raw).hexdigest(),
            "recommendation": recommendation,
            "risk_score": risk.get("score"),
            "coverage_percent": percentage,
            "coverage_complete": complete,
            "execution_successful": executed,
            "issue_count": len(issues),
            "ledger_exception_count": len(exceptions),
            "suppressed_count": suppressed,
            "dependency_inspection_verified": False,
            "dependency_inspection_status": dep.get("status") if isinstance(dep, dict) else "UNKNOWN",
        })
        if (scanner_exit == 0 and recommendation == "SAFE" and complete and executed
                and percentage == 100 and not exceptions):
            result["status"] = "STATIC_SCAN_PASS_ONLY"
        elif not complete or percentage != 100 or not executed:
            result["status"] = "BLOCKED_INCOMPLETE"
        else:
            result["status"] = "BLOCKED_RISK"
    except (OSError, ValueError, TypeError, UnicodeError):
        result["status"] = "BLOCKED_INVALID_REPORT"
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize untrusted SkillSpector reports")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--source-exit", type=int, required=True)
    parser.add_argument("--package-exit", type=int, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--scanner-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    results = {
        "schema_version": 1,
        "source_commit": args.commit,
        "scanner_commit": args.scanner_commit,
        "full_source": summarize(args.source, args.source_exit),
        "deterministic_package": summarize(args.package, args.package_exit),
        "release_approved": False,
        "real_agent_isolation_verified": False,
    }
    results["status"] = ("STATIC_SCAN_PASS_ONLY" if all(
        results[key]["status"] == "STATIC_SCAN_PASS_ONLY"
        for key in ("full_source", "deterministic_package")) else "BLOCKED")
    output = json.dumps(results, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    args.output.write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if results["status"] == "STATIC_SCAN_PASS_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
