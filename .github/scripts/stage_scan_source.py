"""Build a staged copy of the repo for SkillSpector scans.

SkillSpector has no --exclude / --ignore option (verified: `skillspector scan
--help`, local 2.12.0; no .skillspector* config in the repo), so historical
scan data is excluded by staging, not by the scanner: this script copies the
checkout to a staging directory without the paths listed in
.github/scan-exclusions.txt, and the security-scan workflow scans the staging
directory instead of ``.``.

Excluded is the scan input, not the disposition: the 165 findings the
excluded files attracted in the 2026-11-24 rescan are dispositioned item by
item in ~/workspace/aka-skills-review/wp-a-historical-165.md
(HISTORICAL_DATA_REVIEWED). The staging manifest records the sha256 of every
staged file AND every excluded file, so "what was scanned" stays auditable.

Build caches (``__pycache__/`` + ``*.pyc``, ``.mypy_cache/``,
``.ruff_cache/``) are hard-excluded in ``build()`` (see
``is_build_cache``): they are machine-generated, change on every local
run, and are not source. They are skipped silently -- not counted in
the manifest's ``excluded`` list, which is reserved for the
exclusion-file patterns. A fresh CI checkout has no caches, so CI
staging is unaffected; a local re-scan relies on this exclusion
instead of requiring a manual cleanup first.

Precedent: the old review did the same thing -- security-findings.json
``original_scan.scan_arguments`` is ``scan <exact staged source archive
root> --no-llm --format json``.

Usage:
    python .github/scripts/stage_scan_source.py \
        --repo . --out "$RUNNER_TEMP/staged-source" \
        --exclusions .github/scan-exclusions.txt \
        --manifest-out "$RUNNER_TEMP/staging-manifest.json" \
        --commit "$(git rev-parse HEAD)"

Fail-closed behaviour:
- the output directory must not already exist non-empty;
- the output directory must not be inside the repo;
- every exclusion pattern must match at least one path, or the run fails;
- after copying, the staged tree is re-checked: any excluded path found
  inside it fails the run;
- ``.git/`` is always excluded (the scanner excludes VCS metadata itself).

Stdlib only, Python >= 3.11.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_exclusions(path: Path) -> list[str]:
    patterns: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if any(ch.isspace() for ch in line):
            raise ValueError(f"exclusion pattern must not contain whitespace: {line!r}")
        patterns.append(line)
    if not patterns:
        raise ValueError(f"no exclusion patterns in {path}")
    return patterns


def is_excluded(rel: str, patterns: list[str]) -> bool:
    """rel is a '/'-separated path relative to the repo root."""
    if rel == ".git" or rel.startswith(".git/"):
        return True
    for pattern in patterns:
        if pattern.endswith("/"):
            base = pattern.rstrip("/")
            if rel == base or rel.startswith(pattern):
                return True
        elif fnmatch.fnmatch(rel, pattern):
            return True
    return False


def matched_patterns(rel: str, patterns: list[str]) -> set[str]:
    matched: set[str] = set()
    for pattern in patterns:
        if pattern.endswith("/"):
            base = pattern.rstrip("/")
            if rel == base or rel.startswith(pattern):
                matched.add(pattern)
        elif fnmatch.fnmatch(rel, pattern):
            matched.add(pattern)
    return matched


# Machine-generated caches are never scan input: bytecode and
# type-check/lint caches change on every local run, and staging them
# would leak ~100 stale .pyc files (plus .mypy_cache/.ruff_cache
# contents) into the scan. They are skipped silently in build() --
# NOT recorded in the manifest's "excluded" list, which is reserved
# for the exclusion-file patterns (historical scan data). A fresh CI
# checkout has no caches at all, so CI staging is unaffected; a local
# re-scan relies on this exclusion instead of a manual cleanup first.
BUILD_CACHE_DIRS = frozenset({"__pycache__", ".mypy_cache", ".ruff_cache"})


def is_build_cache(rel: str) -> bool:
    """True for machine-generated cache paths: any __pycache__ /
    .mypy_cache / .ruff_cache directory component, or a *.pyc file."""
    if rel.endswith(".pyc"):
        return True
    return any(part in BUILD_CACHE_DIRS for part in PurePosixPath(rel).parts)


def git_output(repo: Path, *args: str) -> str | None:
    try:
        proc = subprocess.run(["git", "-C", str(repo), *args],
                              capture_output=True, text=True, timeout=30, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def build(repo: Path, out: Path, exclusions_path: Path, manifest_out: Path,
          commit: str | None) -> dict:
    repo = repo.resolve()
    out = out.resolve()
    if out == repo or repo in out.parents:
        raise ValueError("staging output must not be inside the repo")
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"staging output already exists and is not empty: {out}")
    patterns = load_exclusions(exclusions_path)

    staged: list[dict] = []
    excluded: list[dict] = []
    matched: set[str] = set()
    out.mkdir(parents=True, exist_ok=True)
    for root, dirs, files in os.walk(repo, topdown=True, followlinks=False):
        root_path = Path(root)
        rel_dir = root_path.relative_to(repo).as_posix()
        # Count matches for every directory first (pruned ones included),
        # then prune .git and excluded directories before descending.
        for name in list(dirs):
            rel = (rel_dir + "/" + name) if rel_dir != "." else name
            if is_build_cache(rel):
                continue  # build cache: skipped silently, never staged,
                # never listed as excluded (see is_build_cache).
            matched |= matched_patterns(rel, patterns)
            if is_excluded(rel, patterns):
                if rel == ".git" or rel.startswith(".git/"):
                    continue  # VCS metadata: excluded by the scanner itself;
                    # do not enumerate the object store into the manifest.
                # Pruned directory: enumerate its files as excluded so the
                # manifest lists exactly what was left out (os.walk will not
                # visit them once the directory is pruned below).
                for sub_root, _sub_dirs, sub_files in os.walk(root_path / name):
                    for sub_name in sorted(sub_files):
                        sub_src = Path(sub_root) / sub_name
                        sub_rel = sub_src.relative_to(repo).as_posix()
                        if sub_src.is_symlink():
                            excluded.append({"path": sub_rel,
                                             "symlink_to": os.readlink(sub_src)})
                        else:
                            excluded.append({"path": sub_rel,
                                             "sha256": sha256_file(sub_src),
                                             "bytes": sub_src.stat().st_size})
        dirs[:] = sorted(d for d in dirs
                         if not is_excluded(
                             (rel_dir + "/" + d) if rel_dir != "." else d, patterns)
                         and not is_build_cache(
                             (rel_dir + "/" + d) if rel_dir != "." else d))
        for name in sorted(files):
            rel = (rel_dir + "/" + name) if rel_dir != "." else name
            if is_build_cache(rel):
                continue  # stray .pyc outside a cache dir, or a file
                # inside a cache dir os.walk still visits.
            src = root_path / name
            matched |= matched_patterns(rel, patterns)
            if is_excluded(rel, patterns):
                if src.is_symlink():
                    excluded.append({"path": rel, "symlink_to": os.readlink(src)})
                else:
                    excluded.append({"path": rel, "sha256": sha256_file(src),
                                     "bytes": src.stat().st_size})
                continue
            dest = out / PurePosixPath(rel)
            dest.parent.mkdir(parents=True, exist_ok=True)
            if src.is_symlink():
                if dest.exists() or dest.is_symlink():
                    dest.unlink()
                dest.symlink_to(os.readlink(src))
                staged.append({"path": rel, "symlink_to": os.readlink(src)})
            else:
                shutil.copy2(src, dest)
                staged.append({"path": rel, "sha256": sha256_file(dest),
                               "bytes": dest.stat().st_size})

    unmatched = [p for p in patterns if p not in matched]
    if unmatched:
        raise ValueError(f"exclusion pattern(s) matched nothing: {unmatched}")

    # Re-check: no excluded path may exist inside the staged tree.
    leaked = [str(p.relative_to(out).as_posix())
              for p in sorted(out.rglob("*"))
              if is_excluded(p.relative_to(out).as_posix(), patterns)]
    if leaked:
        raise ValueError(f"excluded path(s) present in staged tree: {leaked}")

    source_commit = commit or git_output(repo, "rev-parse", "HEAD") or "unknown"
    status = git_output(repo, "status", "--porcelain")
    worktree_clean = None if status is None else (status == "")

    manifest = {
        "schema_version": 1,
        "tool": ".github/scripts/stage_scan_source.py",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_commit": source_commit,
        "worktree_clean": worktree_clean,
        "exclusions_file": str(exclusions_path),
        "exclusions": patterns,
        "excluded": sorted(excluded, key=lambda e: e["path"]),
        "staged_files": sorted(staged, key=lambda e: e["path"]),
        "counts": {"staged": len(staged), "excluded": len(excluded)},
    }
    manifest_out.parent.mkdir(parents=True, exist_ok=True)
    manifest_out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--exclusions", type=Path,
                        default=Path(".github/scan-exclusions.txt"))
    parser.add_argument("--manifest-out", type=Path, required=True)
    parser.add_argument("--commit", default=None)
    args = parser.parse_args(argv)
    try:
        manifest = build(args.repo, args.out, args.exclusions,
                         args.manifest_out, args.commit)
    except (OSError, ValueError) as exc:
        print(f"stage_scan_source: FAIL: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({
        "status": "OK",
        "staged": manifest["counts"]["staged"],
        "excluded": manifest["counts"]["excluded"],
        "source_commit": manifest["source_commit"],
        "worktree_clean": manifest["worktree_clean"],
        "manifest": str(args.manifest_out),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
