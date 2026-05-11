from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Input, RichLog
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import on, events
import asyncio
import os
import signal
import shlex


class TerminalScreen(Screen):
    BINDINGS = [
        Binding("escape",  "app.pop_screen", "Back",      priority=True),
        Binding("ctrl+c",  "interrupt",       "Kill"),
        Binding("ctrl+l",  "clear_log",       "Clear"),
        Binding("ctrl+d",  "app.pop_screen",  "Exit"),
    ]

    CSS = """
    TerminalScreen { background: #0a0a0f; }

    #term-header {
        height: 3;
        background: #13131f;
        color: #6c63ff;
        text-style: bold;
        content-align: center middle;
        border-bottom: solid #2a2a4a;
    }

    #term-log {
        height: 1fr;
        background: #080810;
        border: none;
        padding: 0 1;
        scrollbar-color: #2a2a4a;
        scrollbar-background: #0a0a0f;
    }

    #input-row {
        height: 3;
        background: #13131f;
        border-top: solid #2a2a4a;
        align: left middle;
        padding: 0 1;
    }

    #prompt-label {
        color: #6c63ff;
        text-style: bold;
        width: auto;
        min-width: 5;
        height: 3;
        content-align: left middle;
    }

    #cmd-input {
        background: #13131f;
        border: none;
        color: #e2e2f0;
        height: 3;
        width: 1fr;
    }

    #hint-bar {
        height: 1;
        background: #0a0a0f;
        color: #3a3a5a;
        padding: 0 2;
        dock: bottom;
    }
    """

    def __init__(self):
        super().__init__()
        self._cwd = os.path.expanduser("~")
        self._history: list[str] = []
        self._hist_idx = -1
        self._running_proc: asyncio.subprocess.Process | None = None

    # ── Helpers ────────────────────────────────────────────────────────

    def _prompt(self) -> str:
        home = os.path.expanduser("~")
        cwd = self._cwd
        if cwd.startswith(home):
            cwd = "~" + cwd[len(home):]
        return f" {cwd} $ "

    def _update_prompt(self):
        self.query_one("#prompt-label", Label).update(self._prompt())

    # ── Compose ────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Label(" 💻 TERMINAL", id="term-header")
        yield RichLog(id="term-log", markup=True, highlight=False, wrap=True)
        with Horizontal(id="input-row"):
            yield Label(self._prompt(), id="prompt-label")
            yield Input(placeholder="", id="cmd-input")
        yield Label(
            "^C kill  ^L clear  ↑↓ history  ESC back",
            id="hint-bar"
        )

    def on_mount(self):
        log = self.query_one("#term-log", RichLog)
        log.write("[bold #6c63ff]RXOS Terminal[/bold #6c63ff]"
                  "  [#5a5a7a]type commands · ESC to return[/#5a5a7a]")
        log.write("[#2a2a4a]" + "─" * 54 + "[/#2a2a4a]")
        self.query_one("#cmd-input", Input).focus()

    # ── Key handling for history navigation ────────────────────────────

    def on_key(self, event: events.Key) -> None:
        focused = self.focused
        if not (isinstance(focused, Input) and focused.id == "cmd-input"):
            return

        inp = self.query_one("#cmd-input", Input)

        if event.key == "up":
            event.prevent_default()
            if self._history and self._hist_idx < len(self._history) - 1:
                self._hist_idx += 1
                cmd = self._history[-(self._hist_idx + 1)]
                inp.value = cmd
                inp.cursor_position = len(cmd)

        elif event.key == "down":
            event.prevent_default()
            if self._hist_idx > 0:
                self._hist_idx -= 1
                cmd = self._history[-(self._hist_idx + 1)]
                inp.value = cmd
                inp.cursor_position = len(cmd)
            elif self._hist_idx == 0:
                self._hist_idx = -1
                inp.value = ""

    # ── Command submission ──────────────────────────────────────────────

    @on(Input.Submitted, "#cmd-input")
    def on_cmd_submitted(self, event: Input.Submitted) -> None:
        cmd = event.value.strip()
        event.input.value = ""
        self._hist_idx = -1

        if not cmd:
            return

        # Add to history (deduplicate consecutive)
        if not self._history or self._history[-1] != cmd:
            self._history.append(cmd)

        log = self.query_one("#term-log", RichLog)
        log.write(
            f"[bold #6c63ff]{self._prompt()}[/bold #6c63ff]"
            f"[#e2e2f0]{cmd}[/#e2e2f0]"
        )

        # ── Builtins ────────────────────────────────────────────────

        if cmd in ("clear", "cls"):
            log.clear()
            return

        if cmd in ("exit", "quit"):
            self.app.pop_screen()
            return

        if cmd.startswith("cd"):
            self._builtin_cd(cmd, log)
            return

        if cmd == "history":
            for i, h in enumerate(reversed(self._history[-20:]), 1):
                log.write(f"[#5a5a7a]  {i:>2}[/#5a5a7a]  [#b0b0c8]{h}[/#b0b0c8]")
            return

        if cmd == "pwd":
            log.write(f"[#c8c8e0]{self._cwd}[/#c8c8e0]")
            return

        # ── Async subprocess ─────────────────────────────────────────
        self.run_worker(
            self._run_cmd(cmd),
            exclusive=False,
            name="cmd_runner",
            thread=False,
        )

    def _builtin_cd(self, cmd: str, log: RichLog):
        try:
            parts = shlex.split(cmd)
        except ValueError:
            parts = cmd.split()

        if len(parts) < 2:
            target = os.path.expanduser("~")
        else:
            target = parts[1]

        target = os.path.expandvars(os.path.expanduser(target))
        if not os.path.isabs(target):
            target = os.path.join(self._cwd, target)
        target = os.path.normpath(target)

        if os.path.isdir(target):
            self._cwd = target
            self._update_prompt()
        else:
            log.write(
                f"[#ff5555]cd: {target}: No such file or directory[/#ff5555]"
            )

    async def _run_cmd(self, cmd: str) -> None:
        log = self.query_one("#term-log", RichLog)
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=self._cwd,
                env={**os.environ, "TERM": "dumb", "COLUMNS": "80"},
            )
            self._running_proc = proc

            assert proc.stdout is not None
            async for raw in proc.stdout:
                line = raw.decode("utf-8", errors="replace").rstrip("\n")
                # Escape Rich markup chars so they render as plain text
                line = line.replace("[", r"\[")
                log.write(line)

            await proc.wait()
            self._running_proc = None

            if proc.returncode not in (0, None, -2):  # -2 = SIGINT
                log.write(
                    f"[#ff5555](exit {proc.returncode})[/#ff5555]"
                )

        except FileNotFoundError:
            cmd_name = cmd.split()[0]
            log.write(
                f"[#ff5555]command not found: {cmd_name}[/#ff5555]"
            )
        except PermissionError:
            log.write("[#ff5555]permission denied[/#ff5555]")
        except Exception as e:
            log.write(f"[#ff5555]error: {e}[/#ff5555]")
        finally:
            self._running_proc = None

    # ── Actions ────────────────────────────────────────────────────────

    def action_interrupt(self) -> None:
        log = self.query_one("#term-log", RichLog)
        if self._running_proc and self._running_proc.returncode is None:
            try:
                self._running_proc.send_signal(signal.SIGINT)
                log.write("[#ff8800]^C[/#ff8800]")
            except ProcessLookupError:
                pass
        else:
            self.query_one("#cmd-input", Input).value = ""
            self._hist_idx = -1

    def action_clear_log(self) -> None:
        self.query_one("#term-log", RichLog).clear()

    # ── Cleanup ────────────────────────────────────────────────────────

    def _kill_running(self):
        if self._running_proc and self._running_proc.returncode is None:
            try:
                self._running_proc.terminate()
            except ProcessLookupError:
                pass

    def on_screen_suspend(self) -> None:
        self._kill_running()

    def on_unmount(self) -> None:
        self._kill_running()
