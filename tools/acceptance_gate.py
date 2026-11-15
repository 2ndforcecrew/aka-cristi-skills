"""Fail-closed documentary preflight for six release gates.

This is NOT a verifier of human independence, signatures or scanner verdicts.
Even complete attachments yield REVIEW_REQUIRED, never PASS or permission to
announce completion. Independent review of original evidence remains mandatory.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path

REQUIRED = {
    '8': ('scanner_version', 'scanner_flags', 'scanner_mode', 'original_report_sha256',
          'finding_reviews', 'reviewer', 'rerun_evidence'),
    '9': ('version', 'archive_sha256', 'provenance_verification', 'publisher_identity',
          'negative_tests', 'installer_verification', 'reviewer'),
    '10': ('windows_11_standard_user', 'gui_observation', 'diff_consent', 'rollback',
           'cancellation', 'reinstall', 'reviewer'),
    '11': ('host_version', 'host_os', 'native_roles', 'authorization', 'invocation_logs',
           'completion_evidence', 'reviewer'),
    '12': ('platforms', 'step_outcomes', 'elapsed_seconds', 'permission_prompts', 'reviewer'),
    '13': ('codex_version', 'root_thread_id', 'four_role_correlations',
           'completed_replies', 'reviewer'),
}
LIMIT = 2 * 1024 * 1024


def _attachment(item, root):
    value = item.get('path')
    if not isinstance(value, str) or not value:
        return None, 'missing_evidence_path'
    path = Path(value)
    if path.is_absolute() or '..' in path.parts or path.suffix != '.json':
        return None, 'unsafe_evidence_path'
    root = Path(root).absolute()
    full = root / path
    ancestor = full
    while True:
        if ancestor.is_symlink() or (hasattr(ancestor, 'is_junction') and ancestor.is_junction()):
            return None, 'unsafe_evidence_path'
        if ancestor == root or ancestor.parent == ancestor:
            break
        ancestor = ancestor.parent
    try:
        if not full.is_file() or full.stat().st_size > LIMIT:
            return None, 'missing_or_oversize_attachment'
        raw = full.read_bytes()
        expected = item.get('sha256')
        if not isinstance(expected, str) or not re.fullmatch('[a-f0-9]{64}', expected) or hashlib.sha256(raw).hexdigest() != expected:
            return None, 'attachment_digest_mismatch'
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None, 'invalid_attachment'
        return data, None
    except (OSError, ValueError, UnicodeError):
        return None, 'unreadable_attachment'


def assess(record, evidence_root):
    """Check attachment integrity/presence without trusting claimed PASS fields."""
    if not isinstance(record, dict):
        record = {}
    sha = record.get('source_sha')
    valid_sha = isinstance(sha, str) and bool(re.fullmatch('[a-f0-9]{40}', sha))
    records = record.get('gates', {})
    if not isinstance(records, dict):
        records = {}
    gates = {}
    for issue, required in REQUIRED.items():
        reasons = []
        item = records.get(issue, {})
        if not isinstance(item, dict):
            item = {}
        if not valid_sha:
            reasons.append('missing_exact_source_sha')
        if item.get('evidence_kind') != 'observed':
            reasons.append('observed_evidence_required')
        data, error = _attachment(item, evidence_root)
        if error:
            reasons.append(error)
        if data is not None:
            if data.get('evidence_kind') != 'observed' or data.get('synthetic') is True:
                reasons.append('synthetic_or_unclassified_attachment')
            if data.get('source_sha') != sha:
                reasons.append('source_commit_mismatch')
            for key in required:
                if not data.get(key):
                    reasons.append('missing_' + key)
            if issue == '12':
                platforms = data.get('platforms', {})
                for platform in ('windows', 'macos', 'linux'):
                    details = platforms.get(platform, {}) if isinstance(platforms, dict) else {}
                    if not isinstance(details, dict) or not (
                        details.get('independent_tester') and details.get('standard_user') is True
                        and details.get('first_install') is True and details.get('host_activation') == 'PASS'
                    ):
                        reasons.append('missing_independent_' + platform + '_uat')
        gates[issue] = {'status': 'BLOCKED' if reasons else 'REVIEW_REQUIRED',
                        'reasons': reasons,
                        'meaning': 'Documentary preflight only; no acceptance verdict'}
    return {'schema_version': 1, 'status': 'BLOCKED' if any(g['reasons'] for g in gates.values()) else 'REVIEW_REQUIRED',
            'source_sha': sha if valid_sha else None, 'gates': gates,
            'completion_notification_allowed': False,
            'reason': 'Independent evidence review is required. This tool never authorizes completion or release.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Six release-gate documentary preflight (never auto-PASS)')
    parser.add_argument('record', type=Path)
    parser.add_argument('--evidence-root', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.record.stat().st_size > LIMIT:
            raise ValueError('oversize')
        record = json.loads(args.record.read_text(encoding='utf-8'))
        result = assess(record, args.evidence_root or args.record.parent)
    except (OSError, ValueError, UnicodeError):
        result = {'status':'BLOCKED', 'completion_notification_allowed':False,
                  'reason':'Missing or invalid evidence index'}
    print(json.dumps(result, indent=2))
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
