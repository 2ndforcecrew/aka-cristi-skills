"""Read-only host discovery and adapter capability registry.

No installer side effects, network access, or unverified runtime claims.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True)
class Adapter:
    id: str
    display_name: str
    executable: str | None
    rule_file: str | None
    status: str
    skills: str
    orchestration: str


ADAPTERS: tuple[Adapter, ...] = (
    Adapter("codex", "OpenAI Codex", "codex", "AGENTS.md", "EXISTING_CANDIDATE", "CANDIDATE", "NOT_VERIFIED"),
    Adapter("claude", "Claude Code", "claude", "CLAUDE.md", "PROJECT_FILE_ONLY", "NOT_VERIFIED", "NOT_VERIFIED"),
    Adapter("gemini", "Gemini CLI", "gemini", "GEMINI.md", "DISCOVERY_ONLY", "NOT_VERIFIED", "NOT_VERIFIED"),
    Adapter("opencode", "OpenCode", "opencode", "AGENTS.md", "DISCOVERY_ONLY", "NOT_VERIFIED", "NOT_VERIFIED"),
    Adapter("hermes", "Hermes Agent", "hermes", None, "DISCOVERY_ONLY", "NOT_VERIFIED", "NOT_VERIFIED"),
    Adapter("custom", "Custom Agent", None, None, "ADAPTER_REQUIRED", "NOT_VERIFIED", "NOT_VERIFIED"),
)


def discover(*, path: str | None = None, home: Path | None = None,
             environment: Mapping[str, str] | None = None) -> list[dict[str, object]]:
    """Discover executable presence only; never infer host support from a binary."""
    env = os.environ if environment is None else environment
    search_path = env.get("PATH", os.defpath) if path is None else path
    user_home = Path.home() if home is None else home
    results: list[dict[str, object]] = []
    for adapter in ADAPTERS:
        binary = shutil.which(adapter.executable, path=search_path) if adapter.executable else None
        # Presence of a known config directory is a hint, not proof of installation.
        hint = {
            "codex": ".codex", "claude": ".claude", "gemini": ".gemini",
            "opencode": ".config/opencode", "hermes": ".hermes",
        }.get(adapter.id)
        config_hint = bool(hint and (user_home / hint).is_dir())
        item = asdict(adapter)
        item.update({
            "executable_detected": bool(binary),
            "config_hint_detected": config_hint,
            "available_for_install": False,
            "runtime_verified": False,
            "reason": "Host presence does not prove adapter compatibility or permission.",
        })
        results.append(item)
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only multi-agent capability discovery")
    parser.add_argument("action", choices=["list", "detect"])
    args = parser.parse_args(argv)
    data = [asdict(adapter) for adapter in ADAPTERS] if args.action == "list" else discover()
    print(json.dumps({"schema_version": 1, "adapters": data}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
