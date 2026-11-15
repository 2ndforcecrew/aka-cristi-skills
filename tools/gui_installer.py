"""Actual Tk graphical installer for a trusted local CHEF checkout.

No remote code or prerequisite installation. Can run from source or a candidate frozen EXE.
"""
import argparse
import hashlib
import json
import re
import os
from pathlib import Path
import queue
import shutil
import sys
import threading
import time

from tools import install_transaction as transaction
from tools.fs_safety import checked_path


BUNDLED_PUBLIC_FILES = (
    "templates/AGENTS.global.md",
    "agents/research.toml", "agents/coding.toml", "agents/qa.toml", "agents/automation.toml",
    "skills/chef-orchestrator/SKILL.md", "skills/verified-change-loop/SKILL.md",
    "skills/feature-journey-map/SKILL.md", "skills/skill-evaluation-gate/SKILL.md",
)


def default_source():
    """A frozen build uses only explicitly allowlisted public data, never CWD/home."""
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parents[1]
    bundle = checked_path(sys._MEIPASS)
    manifest_path = checked_path(bundle / "bundled-public-data.json")
    if not manifest_path.is_file() or manifest_path.stat().st_size > 64 * 1024:
        raise ValueError("Bundled public manifest missing or oversized")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("Invalid bundled public manifest")
    if not re.fullmatch(r"[0-9a-f]{40}", manifest.get("source_commit", "")):
        raise ValueError("Bundled source commit missing")
    files = manifest.get("files")
    if not isinstance(files, dict) or set(files) != set(BUNDLED_PUBLIC_FILES):
        raise ValueError("Unexpected bundled public data paths")
    source = checked_path(bundle / "public-source")
    for name in BUNDLED_PUBLIC_FILES:
        path = checked_path(source / name)
        if not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError("Bundled public data missing or unsafe")
        if hashlib.sha256(path.read_bytes()).hexdigest() != files[name]:
            raise ValueError("Bundled public data digest mismatch")
    return source


def prerequisites():
    return {"python": "AVAILABLE" if sys.version_info >= (3, 11) else "MISSING",
            "codex": "AVAILABLE" if shutil.which("codex") else "MISSING",
            "activation": "NOT_RUN"}


class InstallerWindow:
    def __init__(self, window):
        import tkinter as tk
        from tkinter import ttk
        self.tk, self.ttk, self.window = tk, ttk, window
        window.title("AKA.CRISTI — CHEF 本地安装")
        window.geometry("960x760")
        window.minsize(720, 600)
        self.events = queue.Queue()
        self.cancel_event = threading.Event()
        self.busy = False
        self.workspace_windows = []
        self.plan = None
        self.last_journal = None
        self.started = 0
        self.source = tk.StringVar(value=str(default_source()))
        self.home = tk.StringVar(value=os.environ.get("CODEX_HOME") or str(Path.home() / ".codex"))
        self.skills = tk.StringVar(value=str(Path.home() / ".agents" / "skills"))
        self.trusted, self.consent = tk.BooleanVar(value=False), tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="等待预览。真实 Agent 激活：NOT_RUN")
        outer = ttk.Frame(window, padding=18)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="CHEF 安装与恢复", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        deps = prerequisites()
        dependency_text = "Python 3.11+：" + deps["python"] + "    Codex CLI：" + deps["codex"]
        ttk.Label(outer, text=dependency_text).pack(anchor="w", pady=(5, 10))
        ttk.Label(outer, text="仅使用你已审查或完成验签的本地完整源码；不会联网下载、安装依赖或提权。",
                  wraplength=880).pack(anchor="w")
        for title, variable in (("本地源码目录", self.source), ("Codex 配置目录", self.home), ("Skills 目录", self.skills)):
            row = ttk.Frame(outer)
            row.pack(fill="x", pady=5)
            ttk.Label(row, text=title, width=17).pack(side="left")
            ttk.Entry(row, textvariable=variable).pack(side="left", fill="x", expand=True)
            ttk.Button(row, text="选择", command=lambda v=variable: self.choose(v)).pack(side="left", padx=(6, 0))
        self.tabs = ttk.Notebook(outer)
        self.tabs.pack(fill="both", expand=True, pady=10)
        self.diff = tk.Text(self.tabs, wrap="none", font=("Consolas", 10))
        self.log = tk.Text(self.tabs, wrap="word", font=("Consolas", 10), state="disabled")
        self.tabs.add(self.diff, text="AGENTS.md 差异与新增文件（仅本机显示）")
        self.tabs.add(self.log, text="进度日志（不含配置内容）")
        ttk.Checkbutton(outer, variable=self.trusted,
                        text="我已审查本地来源或验证发布签名，允许读取这些文件。",
                        command=self.refresh).pack(anchor="w")
        ttk.Checkbutton(outer, variable=self.consent,
                        text="我已检查差异，同意备份并写入上述用户目录。",
                        command=self.refresh).pack(anchor="w", pady=4)
        buttons = ttk.Frame(outer)
        buttons.pack(fill="x", pady=8)
        self.preview_button = ttk.Button(buttons, text="1 · 检查与预览", command=self.preview)
        self.preview_button.pack(side="left")
        self.install_button = ttk.Button(buttons, text="2 · 安装并校验文件", command=self.install, state="disabled")
        self.install_button.pack(side="left", padx=8)
        self.cancel_button = ttk.Button(buttons, text="取消并恢复", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="left")
        self.undo_button = ttk.Button(buttons, text="撤销本次安装", command=self.undo, state="disabled")
        self.undo_button.pack(side="left", padx=8)
        self.workspace_button = ttk.Button(buttons, text="Personal AI Workspace", command=self.open_workspace)
        self.workspace_button.pack(side="left", padx=6)
        ttk.Button(buttons, text="退出", command=self.close).pack(side="right")
        self.progressbar = ttk.Progressbar(outer, mode="indeterminate")
        self.progressbar.pack(fill="x", pady=4)
        ttk.Label(outer, textvariable=self.status, wraplength=880).pack(anchor="w")
        ttk.Label(outer, text="缺少 Codex：请先按官方说明安装并重开此窗口。依赖自动安装与 Windows 11 独立用户验收仍待完成。",
                  wraplength=880).pack(anchor="w", pady=(7, 0))
        window.protocol("WM_DELETE_WINDOW", self.close)
        window.after(100, self.poll)
        for var in (self.source, self.home, self.skills):
            var.trace_add("write", self.invalidate)
        self.refresh()

    def open_workspace(self, wizard=False):
        if self.busy:
            return
        try:
            from tools.personal_workspace import WorkspaceController
            from tools.workspace_gui import WorkspaceWindow
            controller = WorkspaceController(codex_home=Path(self.home.get()),
                                             skills_root=Path(self.skills.get()),
                                             source=Path(self.source.get()))
            workspace = WorkspaceWindow(self.window, controller=controller, wizard=wizard)
            self.workspace_windows.append(workspace)
            return workspace
        except Exception:
            self.status.set("Workspace 暂时无法打开；请检查本机设置与目录权限。")

    def first_run_workspace(self):
        try:
            from tools.personal_workspace import WorkspaceController
            if WorkspaceController().status().get("wizard_needed"):
                self.open_workspace(wizard=True)
        except Exception:
            self.status.set("Workspace 首次设置暂不可用；可稍后通过按钮重新打开。")

    def offer_workspace(self):
        from tkinter import messagebox
        if messagebox.askyesno("Personal AI Workspace", "安装已校验。现在设置个人 AI Workspace？", parent=self.window):
            self.open_workspace(wizard=True)

    def choose(self, variable):
        from tkinter import filedialog
        selected = filedialog.askdirectory(parent=self.window)
        if selected:
            variable.set(selected)

    def invalidate(self, *_):
        self.plan = None
        self.consent.set(False)
        self.refresh()

    def refresh(self):
        self.preview_button.configure(state="disabled" if self.busy or not self.trusted.get() else "normal")
        can_install = (not self.busy and self.plan is not None and self.consent.get()
                       and self.trusted.get() and prerequisites()["codex"] == "AVAILABLE")
        self.install_button.configure(state="normal" if can_install else "disabled")
        self.cancel_button.configure(state="normal" if self.busy else "disabled")
        self.workspace_button.configure(state="disabled" if self.busy else "normal")
        self.undo_button.configure(state="normal" if self.last_journal and not self.busy else "disabled")

    def append_log(self, event):
        self.log.configure(state="normal")
        self.log.insert("end", event + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def start(self, kind, operation):
        if self.busy:
            return
        self.busy, self.started = True, time.monotonic()
        self.cancel_event.clear()
        self.progressbar.start(15)
        self.refresh()
        self.status.set("处理中；取消将在安全检查点执行。真实 Agent 激活：NOT_RUN")
        def worker():
            try:
                self.events.put((kind, operation()))
            except Exception as exc:
                # Do not copy exception messages: they may contain private config or paths.
                self.events.put(("error", type(exc).__name__))
        threading.Thread(target=worker, daemon=True).start()

    def preview(self):
        if not self.trusted.get():
            return
        values = (self.source.get(), self.home.get(), self.skills.get())
        self.plan = None
        self.consent.set(False)
        self.start("preview", lambda: transaction.preview(*values))

    def install(self):
        if not self.plan or not self.consent.get() or not self.trusted.get():
            return
        if prerequisites()["codex"] != "AVAILABLE":
            return
        plan = self.plan
        self.start("install", lambda: transaction.install(
            plan, consent=True, cancel=self.cancel_event,
            progress=lambda event: self.events.put(("progress", event))))

    def cancel(self):
        self.cancel_event.set()
        self.status.set("已请求取消：等待安全检查点并恢复；请勿强制关闭。Agent 激活：NOT_RUN")

    def undo(self):
        from tkinter import messagebox
        if not self.last_journal or not messagebox.askyesno(
                "撤销确认", "将恢复本次安装前的配置。安装后有修改的文件会阻止恢复。继续？", parent=self.window):
            return
        journal = self.last_journal
        self.start("rollback", lambda: transaction.rollback(journal, consent=True))

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "progress":
                    self.append_log(value)
                    continue
                self.busy = False
                self.progressbar.stop()
                if kind == "preview":
                    # Reject a result if the user edited fields during preview.
                    if (value["source"], value["home"], value["skills"]) != tuple(
                            str(Path(v.get()).expanduser().absolute()) for v in (self.source, self.home, self.skills)):
                        self.status.set("目录已变更，请重新预览。Agent 激活：NOT_RUN")
                        self.refresh()
                        continue
                    self.plan = value
                    self.diff.delete("1.0", "end")
                    self.diff.insert("end", value["rules_diff"] + "\n预期文件操作：\n")
                    for item in value["additions"]:
                        self.diff.insert("end", str(item.get("role") or item.get("name")) + " : " + item["action"] + "\n")
                    self.status.set("预览完成。检查差异并勾选同意后可安装。Agent 激活：NOT_RUN")
                    self.append_log("preview_complete")
                elif kind == "error":
                    self.plan = None
                    self.consent.set(False)
                    self.append_log("blocked:" + value)
                    self.status.set("操作阻塞（" + value + "）：检查源码完整性、目录权限、链接或已有配置冲突；修复后重新预览。备份仅保留本机。")
                else:
                    self.append_log(value["status"])
                    self.status.set(value["status"] + "；真实 Agent 激活：NOT_RUN。备份日志仅保留本机，请勿上传。")
                    if kind == "install" and value["status"] == "FILES_VERIFIED":
                        self.last_journal = value["journal"]
                        self.window.after_idle(self.offer_workspace)
                    elif kind == "rollback":
                        self.last_journal = None
                    self.plan = None
                    self.consent.set(False)
                self.refresh()
        except queue.Empty:
            pass
        if self.busy and time.monotonic() - self.started > 60:
            self.cancel_event.set()
            self.status.set("操作超时：已请求安全取消。请等待磁盘操作结束；不会强制中断配置写入。")
        self.window.after(100, self.poll)

    def close(self):
        active = [workspace for workspace in self.workspace_windows
                  if not workspace.closed and workspace.busy]
        if active:
            for workspace in active:
                workspace.cancel()
            self.status.set("Workspace 正在处理；授权可请求取消，其他操作须等待安全结束后关闭。")
            return
        if self.busy:
            self.cancel()
            return
        self.window.destroy()


def main(argv=None):
    parser = argparse.ArgumentParser(description="CHEF local graphical installer")
    parser.add_argument("--smoke-test", action="store_true", help="Open real Tk widgets, inspect defaults, close; writes no user config")
    parser.add_argument("--workspace-smoke-test", action="store_true", help="Real workspace Tk controls only; no OAuth/config writes")
    args = parser.parse_args(argv)
    if sys.version_info < (3, 11):
        print("BLOCKED: Python 3.11+ required")
        return 2
    try:
        default_source()
    except (OSError, ValueError, AttributeError):
        print("BLOCKED: bundled public data validation failed")
        return 2
    if args.workspace_smoke_test:
        # Dependency import only; never inspect native credentials during smoke.
        try:
            import importlib
            backend = ('keyring.backends.Windows' if sys.platform == 'win32' else
                       'keyring.backends.macOS' if sys.platform == 'darwin' else 'keyring.backends.SecretService')
            importlib.import_module(backend)
            from tools.workspace_gui import main as workspace_main
            return workspace_main(['--smoke-test'])
        except ImportError:
            print('BLOCKED: native keyring dependency missing')
            return 2
    try:
        import tkinter as tk
    except ImportError:
        print("BLOCKED: Tk is unavailable; install the official Python/Tk package")
        return 2
    try:
        window = tk.Tk()
        app = InstallerWindow(window)
        if args.smoke_test:
            window.update_idletasks()
            assert str(app.install_button["state"]) == "disabled"
            assert not app.consent.get() and not app.trusted.get()
            window.destroy()
            print("PASS: real Tk widget smoke; Windows user acceptance and activation NOT_RUN")
        else:
            window.after_idle(app.first_run_workspace)
            window.mainloop()
    except (RuntimeError, tk.TclError) as exc:
        print("BLOCKED: graphical desktop/Tk unavailable (" + type(exc).__name__ + ")")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
