"""Cross-platform guarded source updater for a reviewed Git checkout.

Usage: python3 -m tools.update --interactive [--source-only]
Default is preview-only. Never overwrites local changes or private workspace.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

REPO = "2ndforcecrew/aka-cristi-skills"
ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    result = subprocess.run(["git", *args], cwd=ROOT, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=90, check=False)
    if result.returncode:
        raise RuntimeError(f"git {args[0]} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def inspect():
    origin = git("remote", "get-url", "origin")
    allowed = {
        f"https://github.com/{REPO}", f"https://github.com/{REPO}.git",
        f"git@github.com:{REPO}", f"git@github.com:{REPO}.git",
    }
    if origin not in allowed:
        raise RuntimeError("Unexpected Git origin; refusing update")
    if git("branch", "--show-current") != "main":
        raise RuntimeError("Update only supported from main branch")
    if git("status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("Local changes or untracked files detected; refusing update")
    local = git("rev-parse", "HEAD")
    git("fetch", "--no-tags", "origin", "main")
    remote = git("rev-parse", "refs/remotes/origin/main")
    git("merge-base", "--is-ancestor", local, remote)
    return local, remote


def run(interactive=False, apply=False, source_only=False):
    local, remote = inspect()
    if local == remote:
        print(f"[CHEF UPDATE] Source already current: {local}")
    else:
        print(f"[CHEF UPDATE] Current: {local}\n[CHEF UPDATE] Latest:  {remote}")
        print(git("diff", "--stat", "HEAD", "refs/remotes/origin/main"))
        if not apply:
            if not interactive or input("Type UPDATE to fast-forward source: ").strip() != "UPDATE":
                print("[CHEF UPDATE] Preview only; nothing applied")
                return 0
        git("merge", "--ff-only", "refs/remotes/origin/main")
        print("[CHEF UPDATE] Source updated")
    if source_only:
        print("[CHEF UPDATE] Installed Skills unchanged (--source-only)")
        return 0
    print("[CHEF UPDATE] Starting existing setup preview; install needs separate confirmation")
    cmd = [sys.executable, "-m", "tools.full_setup", "--interactive"]
    result = subprocess.run(cmd, cwd=ROOT, timeout=1200, check=False)
    if result.returncode:
        raise RuntimeError(f"Installer returned {result.returncode}; inspect its logs")
    print("[CHEF UPDATE] Installer finished. Live Agent activation NOT_RUN")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--apply", action="store_true",
                        help="Authorize Git fast-forward only; setup still asks separately")
    parser.add_argument("--source-only", action="store_true")
    args = parser.parse_args()
    try:
        return run(args.interactive, args.apply, args.source_only)
    except (RuntimeError, OSError, subprocess.TimeoutExpired, EOFError, KeyboardInterrupt) as exc:
        print(f"[CHEF UPDATE][BLOCKED] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
