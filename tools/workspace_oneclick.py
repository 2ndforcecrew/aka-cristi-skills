"""One-click Personal AI Workspace setup: sequence the existing controller.

No Tk imports. All writes go through WorkspaceController's existing confirmed
methods; this module only sequences them and reports per-step status. The
single consent dialog is driven by plan(); run() refuses to write until the
caller confirms that plan.
"""
from __future__ import annotations

import threading
from typing import Any, Callable

from tools.workspace_github import WorkspaceError


class OneClickSetup:
    """Sequential, resumable one-click setup over an existing WorkspaceController.

    No Tk imports. All writes go through the controller's existing confirmed
    methods; this module only sequences them and reports per-step status.
    """

    STEPS: tuple[str, ...] = ("connect", "repository", "initialize", "preview", "sync", "chatgpt")

    def __init__(self, controller: Any, on_step: Callable[[str, str], None] | None = None) -> None:
        self.controller = controller
        self._on_step = on_step

    def plan(self) -> dict[str, Any]:
        """Ordered list of writes for the single consent dialog."""
        return {"steps": [
            {"name": "connect",
             "writes": "GitHub Device Flow 授權（不寫檔案；user code 只顯示，不入 log）"},
            {"name": "repository",
             "writes": "建立私人倉庫 my-agent-workspace（已存在則改用現有倉庫，不覆蓋）"},
            {"name": "initialize",
             "writes": "寫入 10 個公開檔案到私人倉庫（9 個公開檔案 + workspace.json）"},
            {"name": "preview", "writes": "無寫入（僅預覽本地差異）"},
            {"name": "sync", "writes": "備份後拉取公開檔案到本機 Codex/Skills 目錄（直接套用預覽差異，不再二次確認）"},
            {"name": "chatgpt", "writes": "僅打開官方指南，不寫憑據、不改 ChatGPT 設定"},
        ]}

    def run(self, confirmed: bool = False, cancel_event: threading.Event | None = None,
            on_challenge: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
        """Run the six steps in order.

        confirmed=False raises CONFIRMATION_REQUIRED with zero writes. Any step
        failure stops the run; completed steps are kept and a later run resumes
        from the first incomplete step. Only fixed SAFE_ERRORS codes cross the
        boundary; no exception text, token or path is returned.
        """
        if not confirmed:
            raise WorkspaceError("CONFIRMATION_REQUIRED")
        completed: list[str] = []
        step: str | None = None
        try:
            step = "connect"
            self._emit(step, "started")
            self.controller.connect(cancel_event=cancel_event, on_challenge=on_challenge)
            completed.append(step)
            self._emit(step, "done")

            step = "repository"
            self._emit(step, "started")
            selected = self.controller.select_repository(confirmed=True)
            # Never silently consent to reuse an existing private repository.
            # The manual wizard must obtain a separate explicit reuse approval.
            if selected.get("status") == "REUSE_REQUIRED":
                raise WorkspaceError("REUSE_REQUIRED")
            if selected.get("status") != "SELECTED":
                raise WorkspaceError("OPERATION_FAILED")
            completed.append(step)
            self._emit(step, "done")

            step = "initialize"
            self._emit(step, "started")
            self.controller.initialize(confirmed=True)
            completed.append(step)
            self._emit(step, "done")

            step = "preview"
            self._emit(step, "started")
            preview = self.controller.preview_changes()
            if preview.get("conflicts"):
                raise WorkspaceError("SYNC_CONFLICT")
            completed.append(step)
            self._emit(step, "done")

            step = "sync"
            self._emit(step, "started")
            self.controller.sync_now(confirmed=True)
            completed.append(step)
            self._emit(step, "done")

            step = "chatgpt"
            self._emit(step, "started")
            self.controller.chatgpt_guide()
            completed.append(step)
            self._emit(step, "done")
        except WorkspaceError as exc:
            if step is not None:
                self._emit(step, "stopped")
            return self._result("STOPPED", completed, step, _safe_code(exc))
        except Exception:
            if step is not None:
                self._emit(step, "stopped")
            return self._result("STOPPED", completed, step, "OPERATION_FAILED")
        return self._result("COMPLETED", completed, "chatgpt", None)

    def _emit(self, step: str, state: str) -> None:
        if self._on_step is None:
            return
        try:
            self._on_step(step, state)
        except Exception:
            pass  # Progress reporting must never break the flow.

    def _result(self, status: str, completed: list[str], step: str | None,
                code: str | None) -> dict[str, Any]:
        try:
            current = self.controller.status()
        except Exception:
            current = {}
        if not isinstance(current, dict):
            current = {}
        return {"status": status, "completed": list(completed), "step": step, "code": code,
                "repository": current.get("repository"), "sync_status": current.get("sync_status"),
                "chatgpt_status": current.get("chatgpt_status")}


def _safe_code(exc: BaseException) -> str:
    """Map any raised error to a fixed SAFE_ERRORS code; never leak text."""
    code = getattr(exc, "code", None)
    if isinstance(code, str):
        # Deferred import: tools.personal_workspace imports this module for the CLI.
        try:
            from tools.personal_workspace import SAFE_ERRORS
        except Exception:
            return "OPERATION_FAILED"
        if code in SAFE_ERRORS:
            return code
    return "OPERATION_FAILED"
