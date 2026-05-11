from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Button, ProgressBar
from textual.containers import Vertical, Horizontal, Container
from textual.binding import Binding
from textual.reactive import reactive
import time

WORK_SECS = 25 * 60
BREAK_SECS = 5 * 60
LONG_BREAK_SECS = 15 * 60

class PomodoroScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("space", "toggle_timer", "Start/Pause"),
        Binding("r", "reset_timer", "Reset"),
        Binding("s", "skip_phase", "Skip"),
    ]

    CSS = """
    PomodoroScreen { background: #0d0d14; align: center middle; }
    #pomo-header {
        height: 3; background: #13131f;
        color: #6c63ff; text-style: bold;
        content-align: center middle;
        border-bottom: solid #2a2a4a;
        dock: top; width: 100%;
    }
    #pomo-body { align: center middle; height: 1fr; }
    #phase-label {
        color: #00d4aa; text-style: bold;
        content-align: center middle;
        width: 40; height: 3;
    }
    #timer-display {
        color: #e2e2f0; text-style: bold;
        content-align: center middle;
        width: 40; height: 7;
    }
    #session-label {
        color: #5a5a7a;
        content-align: center middle;
        width: 40; height: 3;
    }
    #progress-bar { width: 38; height: 3; }
    #btn-row {
        height: 5; align: center middle;
        width: 40;
    }
    #btn-row Button { width: 12; margin: 0 1; height: 3; }
    #btn-start { background: #6c63ff; color: #fff; border: none; }
    #btn-start:hover { background: #7c72ff; }
    #btn-reset { background: #13131f; color: #e2e2f0; border: solid #2a2a4a; }
    #btn-skip  { background: #13131f; color: #00d4aa; border: solid #2a2a4a; }
    #hint-bar {
        height: 1; background: #13131f; color: #5a5a7a;
        padding: 0 2; dock: bottom; width: 100%;
    }
    """

    _remaining = reactive(WORK_SECS)
    _running = False
    _phase = "work"  # "work" | "break" | "long_break"
    _sessions = 0
    _interval = None

    def compose(self) -> ComposeResult:
        yield Label(" ⏱ POMODORO TIMER", id="pomo-header")
        with Vertical(id="pomo-body"):
            yield Label("🍅 FOCUS SESSION", id="phase-label")
            yield Label(self._fmt(WORK_SECS), id="timer-display")
            yield ProgressBar(total=WORK_SECS, id="progress-bar", show_eta=False)
            yield Label("Sessions: 0  |  Best: focus!", id="session-label")
            with Horizontal(id="btn-row"):
                yield Button("▶ Start", id="btn-start")
                yield Button("↺ Reset", id="btn-reset")
                yield Button("⏭ Skip",  id="btn-skip")
        yield Label("SPACE start/pause  R reset  S skip  ESC back", id="hint-bar")

    def _fmt(self, secs: int) -> str:
        m, s = divmod(abs(secs), 60)
        return f"{m:02d}:{s:02d}"

    def _phase_duration(self) -> int:
        if self._phase == "work":
            return WORK_SECS
        elif self._phase == "long_break":
            return LONG_BREAK_SECS
        return BREAK_SECS

    def _tick(self):
        if not self._running:
            return
        self._remaining -= 1
        total = self._phase_duration()
        label = self.query_one("#timer-display", Label)
        label.update(self._fmt(self._remaining))
        pb = self.query_one("#progress-bar", ProgressBar)
        pb.progress = total - self._remaining
        if self._remaining <= 0:
            self._running = False
            self._advance_phase()

    def _advance_phase(self):
        if self._phase == "work":
            self._sessions += 1
            self._phase = "long_break" if self._sessions % 4 == 0 else "break"
            self.notify("🍅 Session done! Take a break.", title="Pomodoro")
        else:
            self._phase = "work"
            self.notify("⚡ Break over! Back to work.", title="Pomodoro")
        self._remaining = self._phase_duration()
        self._update_ui()

    def _update_ui(self):
        phase_texts = {
            "work": "🍅 FOCUS SESSION",
            "break": "☕ SHORT BREAK",
            "long_break": "🛌 LONG BREAK",
        }
        self.query_one("#phase-label", Label).update(phase_texts[self._phase])
        self.query_one("#timer-display", Label).update(self._fmt(self._remaining))
        total = self._phase_duration()
        pb = self.query_one("#progress-bar", ProgressBar)
        pb.total = total
        pb.progress = total - self._remaining
        self.query_one("#session-label", Label).update(
            f"Sessions completed: {self._sessions}"
        )
        btn = self.query_one("#btn-start", Button)
        btn.label = "⏸ Pause" if self._running else "▶ Start"

    def action_toggle_timer(self):
        self._running = not self._running
        if self._running and self._interval is None:
            self._interval = self.set_interval(1, self._tick)
        btn = self.query_one("#btn-start", Button)
        btn.label = "⏸ Pause" if self._running else "▶ Start"

    def action_reset_timer(self):
        self._running = False
        self._remaining = self._phase_duration()
        self._update_ui()

    def action_skip_phase(self):
        self._running = False
        self._advance_phase()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-start":
            self.action_toggle_timer()
        elif event.button.id == "btn-reset":
            self.action_reset_timer()
        elif event.button.id == "btn-skip":
            self.action_skip_phase()

    def on_mount(self):
        self._interval = self.set_interval(1, self._tick)
