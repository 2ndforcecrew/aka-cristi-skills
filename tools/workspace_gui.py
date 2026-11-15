"""Tk adapter for the personal workspace controller; no credentials live here."""
from __future__ import annotations

import argparse
import json
import queue
import threading
import time
import webbrowser
from collections.abc import Callable
from typing import Any


class WorkspaceWindow:
    """Controller-backed workspace UI, including explicit write confirmations."""

    def __init__(self, parent: Any, controller: Any = None, wizard: bool = False):
        import tkinter as tk
        from tkinter import ttk

        if controller is None:
            from tools.personal_workspace import WorkspaceController
            controller = WorkspaceController()
        self.controller = controller
        self.window = tk.Toplevel(parent)
        self.window.title("AKA.CRISTI — Personal AI Workspace")
        self.window.geometry("960x740")
        self.tk, self.ttk = tk, ttk
        self.busy = False
        self.job_kind = ""
        self.cancel_event = threading.Event()
        self.events: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.started = 0.0
        self.timeout = 200.0
        self.timed_out = False
        self.closed = False
        self.controls: list[Any] = []
        self.status = tk.StringVar(value="准备就绪；仅手动同步")
        self.account = tk.StringVar(value="GitHub：未连接")
        self.repository = tk.StringVar(value="my-agent-workspace")
        self.oauth_client_id = tk.StringVar(value="")
        self.summary = tk.StringVar(value="")
        self.chatgpt = tk.StringVar(value="ChatGPT：NOT_CONNECTED")
        self.backup_ids: list[str] = []
        outer = ttk.Frame(self.window, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Personal AI Workspace", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(outer, textvariable=self.summary, wraplength=880).pack(anchor="w", pady=8)
        self.tabs = ttk.Notebook(outer)
        self.tabs.pack(fill="both", expand=True)
        self.sync_page = ttk.Frame(self.tabs, padding=12)
        self.setup_page = ttk.Frame(self.tabs, padding=12)
        self.chatgpt_page = ttk.Frame(self.tabs, padding=12)
        self.tabs.add(self.sync_page, text="Sync Center")
        self.tabs.add(self.setup_page, text="GitHub 设置")
        self.tabs.add(self.chatgpt_page, text="ChatGPT")
        self._build_sync()
        self._build_setup()
        self._build_chatgpt()
        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Label(bottom, textvariable=self.status, wraplength=750).pack(side="left")
        self.cancel_button = ttk.Button(bottom, text="取消", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="right")
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self._refresh_status()
        if wizard:
            self.tabs.select(self.setup_page)
        self.poll_id = self.window.after(75, self.poll)

    def _button(self, parent: Any, label: str, command: Callable[[], Any]) -> Any:
        button = self.ttk.Button(parent, text=label, command=command)
        button.pack(side="left", padx=(0, 6), pady=5)
        self.controls.append(button)
        return button

    def _build_setup(self) -> None:
        ttk = self.ttk
        ttk.Label(self.setup_page, textvariable=self.account).pack(anchor="w")
        ttk.Label(self.setup_page, text="通过 GitHub 浏览器设备授权登录；需要配置 OAuth public client ID 和系统凭据存储。\n仓库必须属于当前账户、保持 private；同步模式固定为 manual。", wraplength=830).pack(anchor="w", pady=8)
        advanced = ttk.LabelFrame(self.setup_page, text="高级设置 · OAuth public client ID", padding=8)
        advanced.pack(fill="x", pady=8)
        ttk.Label(advanced, text="填写维护者提供的公开应用 ID；不是密码或 Token。留空可使用预设或环境配置。", wraplength=800).pack(anchor="w")
        row = ttk.Frame(advanced)
        row.pack(fill="x")
        self.oauth_entry = ttk.Entry(row, textvariable=self.oauth_client_id)
        self.oauth_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.controls.append(self.oauth_entry)
        self.configure_oauth_button = self._button(row, "保存应用 ID", self.configure_oauth)
        row = ttk.Frame(self.setup_page)
        row.pack(fill="x")
        self.connect_button = self._button(row, "Connect GitHub", self.connect)
        self.disconnect_button = self._button(row, "Disconnect GitHub", self.disconnect)
        self.skip_button = self._button(row, "稍后设置", self.skip)
        ttk.Label(self.setup_page, text="个人仓库名称").pack(anchor="w", pady=(16, 4))
        entry = ttk.Entry(self.setup_page, textvariable=self.repository)
        entry.pack(fill="x")
        self.controls.append(entry)
        row = ttk.Frame(self.setup_page)
        row.pack(fill="x")
        self.create_button = self._button(row, "创建 private 仓库", lambda: self.select_repository(False))
        self.reuse_button = self._button(row, "使用已有 private 仓库", lambda: self.select_repository(True))
        self.initialize_button = self._button(row, "初始化公共配置", self.initialize)
        self._button(row, "打开仓库", self.open_repository)
        ttk.Label(self.setup_page, text="初始化仅导出已审核的公共规则、Agent 和 Skill；不会上传本机私有配置、凭据或聊天记录。", wraplength=830).pack(anchor="w", pady=12)

    def _build_sync(self) -> None:
        row = self.ttk.Frame(self.sync_page)
        row.pack(fill="x")
        self.check_button = self._button(row, "检查更新", lambda: self.start("check", self.controller.check_updates))
        self.preview_button = self._button(row, "预览差异", lambda: self.start("preview", self.controller.preview_changes))
        self.sync_button = self._button(row, "Sync Now", self.sync)
        self._button(row, "已安装 Skills", lambda: self.start("skills", self.controller.installed_skills))
        self._button(row, "错误日志", lambda: self.start("logs", self.controller.error_logs))
        self.output = self.tk.Text(self.sync_page, wrap="none", state="disabled", font=("Consolas", 10))
        self.output.pack(fill="both", expand=True, pady=8)
        self.ttk.Label(self.sync_page, text="差异仅在本机显示；Sync Now 只拉取，不推送本机内容。备份先于写入。", wraplength=830).pack(anchor="w")
        row = self.ttk.Frame(self.sync_page)
        row.pack(fill="x")
        self._button(row, "备份历史", lambda: self.start("backups", self.controller.backup_history))
        self.backup_selection = self.tk.StringVar(value="")
        self.backup_combo = self.ttk.Combobox(row, textvariable=self.backup_selection, state="readonly", width=32)
        self.backup_combo.pack(side="left", padx=6)
        self.restore_button = self._button(row, "恢复所选备份", self.restore)

    def _build_chatgpt(self) -> None:
        self.ttk.Label(self.chatgpt_page, textvariable=self.chatgpt).pack(anchor="w")
        self.ttk.Label(self.chatgpt_page, text="ChatGPT 授权独立于 GitHub。只有真实验证结果才能显示 Connected；打开指南不表示已连接。", wraplength=820).pack(anchor="w", pady=12)
        row = self.ttk.Frame(self.chatgpt_page)
        row.pack(fill="x")
        self._button(row, "官方连接指南", lambda: self.start("guide", self.controller.chatgpt_guide))
        self._button(row, "检查连接状态", lambda: self.start("verify", self.controller.request_chatgpt_verification))

    def _confirm(self, title: str, text: str) -> bool:
        from tkinter import messagebox
        return bool(messagebox.askyesno(title, text, parent=self.window))

    def configure_oauth(self) -> None:
        client_id = self.oauth_client_id.get().strip()
        self.start("oauth_config", lambda: self.controller.configure_oauth_client(client_id))

    def connect(self) -> None:
        self.start("connect", lambda: self.controller.connect(
            cancel_event=self.cancel_event,
            on_challenge=lambda challenge: self.events.put(("challenge", challenge))))

    def disconnect(self) -> None:
        if not self.busy and self._confirm("确认断开 GitHub", "将清除此应用保存的 GitHub 凭据和仓库选择，以便切换账户或重新授权。不会修改远程仓库。继续？"):
            self.start("disconnect", lambda: self.controller.disconnect(confirmed=True))

    def skip(self) -> None:
        self.start("skip", self.controller.skip_setup)

    def select_repository(self, reuse: bool) -> None:
        name = self.repository.get().strip()
        action = "使用已有" if reuse else "创建新的"
        if not self.busy and self._confirm("确认仓库", f"将为当前 GitHub 账户{action} private 仓库 {name}。继续？"):
            self.start("repository", lambda: self.controller.select_repository(name=name, confirmed=True, reuse=reuse))

    def initialize(self) -> None:
        if not self.busy and self._confirm("确认初始化", "将向所选私人仓库写入审核过的公共配置。继续？"):
            self.start("initialize", lambda: self.controller.initialize(confirmed=True))

    def sync(self) -> None:
        if not self.busy and self._confirm("确认手动同步", "请先检查差异。将创建本机备份，并把仓库配置写入本机 Codex / Skills 目录。继续？"):
            self.start("sync", lambda: self.controller.sync_now(confirmed=True))

    def restore(self) -> None:
        backup_id = self.backup_selection.get()
        if not self.busy and backup_id in self.backup_ids and self._confirm("确认恢复", "将从所选本机备份恢复。后续本机修改会阻止恢复。继续？"):
            self.start("restore", lambda: self.controller.restore_previous(backup_id, confirmed=True))

    def open_repository(self) -> None:
        self.start("repository_url", self.controller.repository_url)

    def _refresh_status(self) -> None:
        try:
            state = self.controller.status()
            self.account.set("GitHub：" + (state.get("github_account") or "未连接"))
            repo = state.get("repository") or "未选择"
            self.summary.set(f"{self.account.get()}  |  仓库：{repo}  |  Codex 同步：{state.get('sync_status', 'UNKNOWN')}  |  manual")
            self.chatgpt.set("ChatGPT：" + str(state.get("chatgpt_status", "NOT_CONNECTED")))
        except Exception:
            self.status.set("状态读取失败；请检查设置后重试。")

    def start(self, kind: str, operation: Callable[[], Any]) -> None:
        if self.busy or self.closed:
            return
        self.busy = True
        self.job_kind = kind
        self.started = time.monotonic()
        self.timed_out = False
        self.cancel_event.clear()
        for widget in self.controls:
            widget.configure(state="disabled")
        self.backup_combo.configure(state="disabled")
        self.cancel_button.configure(state="normal" if kind == "connect" else "disabled")
        self.status.set("正在授权；可请求取消。" if kind == "connect" else "正在处理；请等待操作安全结束。")

        def worker() -> None:
            try:
                value = operation()
                self.events.put((kind, value))
            except Exception as exc:
                # Only explicitly allowlisted fixed identifiers may cross the boundary.
                code = getattr(exc, "code", None)
                self.events.put(("error", code if code == "OAUTH_CLIENT_ID_REQUIRED" else None))
        threading.Thread(target=worker, daemon=True).start()

    def cancel(self) -> None:
        if self.busy and self.job_kind == "connect":
            self.cancel_event.set()
            self.status.set("已请求取消授权；正在等待安全结束。")
        elif self.busy:
            self.status.set("此操作无法中途取消；请等待安全结束后关闭。")

    def _show(self, value: Any) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("end", str(value))
        self.output.configure(state="disabled")

    def _result(self, kind: str, value: Any) -> None:
        if kind == "error":
            self.status.set("需要先配置 GitHub OAuth public client ID（OAUTH_CLIENT_ID_REQUIRED）。"
                            if value == "OAUTH_CLIENT_ID_REQUIRED" else
                            "操作失败或被阻止；请检查账户、权限与配置冲突后重试。")
            return
        result_status = value.get("status") if isinstance(value, dict) else None
        guidance = {
            "REUSE_REQUIRED": "仓库已存在（REUSE_REQUIRED）。请点击“使用已有 private 仓库”单独确认复用，或修改名称后创建。",
            "FAILED_ROLLED_BACK": "操作失败，已恢复操作前状态（FAILED_ROLLED_BACK）。请检查错误日志与冲突，重新预览后再试。",
            "BLOCKED_ROLLBACK_REQUIRED": "操作已阻止，需要恢复（BLOCKED_ROLLBACK_REQUIRED）。请检查备份历史和错误日志，解决本机冲突后恢复；暂勿再次同步。",
        }
        if result_status in guidance:
            self.status.set(guidance[result_status])
            return
        self.status.set("操作完成。" + (f" 状态：{result_status}" if result_status else ""))
        if kind == "preview":
            changes = value.get("changes", []) if isinstance(value, dict) else []
            lines = [f"{item.get('action', '')} {item.get('path', '')}\n{item.get('diff', '')}" for item in changes]
            conflicts = value.get("conflicts", []) if isinstance(value, dict) else []
            self._show("\n\n".join(lines) + ("\n冲突：\n" + json.dumps(conflicts, ensure_ascii=False) if conflicts else ""))
        elif kind == "backups":
            self.backup_ids = [str(item["id"]) for item in value]
            self.backup_combo.configure(values=self.backup_ids)
            self.backup_selection.set(self.backup_ids[0] if self.backup_ids else "")
            self._show(json.dumps(value, ensure_ascii=False, indent=2))
        elif kind in {"guide", "repository_url"}:
            url = value.get("url") if isinstance(value, dict) else value
            if isinstance(url, str) and url.startswith("https://"):
                webbrowser.open(url)
            else:
                self._show(json.dumps(value, ensure_ascii=False, indent=2))
        elif kind in {"skills", "logs", "check", "verify"}:
            self._show(json.dumps(value, ensure_ascii=False, indent=2))
        if kind == "skip":
            self.tabs.select(self.sync_page)

    def poll(self) -> None:
        if self.closed:
            return
        try:
            kind, value = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            if kind == "challenge":
                code = value.get("user_code", "") if isinstance(value, dict) else ""
                uri = value.get("verification_uri", "") if isinstance(value, dict) else ""
                if uri == "https://github.com/login/device" and isinstance(code, str) and len(code) <= 32:
                    self.status.set(f"请在 https://github.com/login/device 输入一次性代码：{code}")
                self.poll_id = self.window.after(75, self.poll)
                return
            self.busy = False
            for widget in self.controls:
                widget.configure(state="normal")
            self.backup_combo.configure(state="readonly")
            self.cancel_button.configure(state="disabled")
            self._result(kind, value)
            self._refresh_status()
        if self.busy and not self.timed_out and time.monotonic() - self.started >= self.timeout:
            self.timed_out = True
            if self.job_kind == "connect":
                self.cancel_event.set()
                self.status.set("授权超时，已请求取消；等待操作安全结束后才能继续。")
            else:
                self.status.set("操作超出等待时间；此操作无法中途取消，请等待安全结束。")
        self.poll_id = self.window.after(75, self.poll)

    def close(self) -> None:
        if self.busy:
            self.cancel()
            return
        self.closed = True
        self.window.after_cancel(self.poll_id)
        self.window.destroy()


class _SmokeController:
    """Read-only stand-in; smoke must never initialize persistent state or OAuth."""

    def status(self) -> dict[str, Any]:
        return {"github_account": None, "repository": None, "sync_status": "NOT_RUN", "chatgpt_status": "NOT_CONNECTED"}

    def __getattr__(self, name: str) -> Callable[..., None]:
        return lambda *args, **kwargs: None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Personal AI Workspace")
    parser.add_argument("--smoke-test", action="store_true")
    args = parser.parse_args(argv)
    import tkinter as tk
    try:
        root = tk.Tk()
        root.withdraw()
        app = WorkspaceWindow(root, controller=_SmokeController() if args.smoke_test else None, wizard=not args.smoke_test)
        if args.smoke_test:
            root.update_idletasks()
            assert len(app.tabs.tabs()) == 3
            assert not app.busy
            app.close()
            root.destroy()
            print("PASS: workspace Tk smoke; OAuth/network/config writes NOT_RUN")
        else:
            app.window.bind("<Destroy>", lambda event: root.quit() if event.widget is app.window else None)
            root.mainloop()
            root.destroy()
    except (tk.TclError, RuntimeError):
        print("BLOCKED: graphical desktop/Tk unavailable")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
