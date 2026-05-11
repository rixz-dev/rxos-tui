from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Button, Footer
from textual.containers import Vertical, Horizontal, Grid, Container
from textual.binding import Binding
from textual import on
from rxos import storage
from rxos.screens.notes    import NotesScreen
from rxos.screens.todo     import TodoScreen
from rxos.screens.calculator import CalculatorScreen
from rxos.screens.pomodoro import PomodoroScreen
from rxos.screens.vault    import VaultScreen
from rxos.screens.snippets import SnippetScreen
from rxos.screens.journal  import JournalScreen
from rxos.screens.habits   import HabitScreen
from rxos.screens.sysmon   import SysMonScreen
from rxos.screens.terminal import TerminalScreen
from rxos.screens.music    import MusicScreen
from datetime import datetime
import random

QUOTES = [
    "Ship it. Fix it. Ship it again.",
    "Code is craft. Own it.",
    "Done is better than perfect.",
    "Build things that matter.",
    "Stay focused. Stay dangerous.",
    "The best code is the code that ships.",
    "Constraints breed creativity.",
    "Every expert was once a beginner.",
]

MENU_ITEMS = [
    ("📝", "Notes",        "N", NotesScreen),
    ("✅", "Todo",         "T", TodoScreen),
    ("🧮", "Calculator",   "C", CalculatorScreen),
    ("⏱",  "Pomodoro",    "P", PomodoroScreen),
    ("🔐", "Vault",        "V", VaultScreen),
    ("📋", "Snippets",     "S", SnippetScreen),
    ("📓", "Journal",      "J", JournalScreen),
    ("🔥", "Habits",       "H", HabitScreen),
    ("📊", "SysMon",       "M", SysMonScreen),
    ("💻", "Terminal",     "B", TerminalScreen),
    ("🎵", "Music",        "F", MusicScreen),
]


class HomeScreen(Screen):
    BINDINGS = [
        Binding("n", "open_notes",      "Notes"),
        Binding("t", "open_todo",       "Todo"),
        Binding("c", "open_calc",       "Calc"),
        Binding("p", "open_pomodoro",   "Pomodoro"),
        Binding("v", "open_vault",      "Vault"),
        Binding("s", "open_snippets",   "Snippets"),
        Binding("j", "open_journal",    "Journal"),
        Binding("h", "open_habits",     "Habits"),
        Binding("m", "open_sysmon",     "SysMon"),
        Binding("b", "open_terminal",   "Terminal"),
        Binding("f", "open_music",      "Music"),
        Binding("q", "app.exit",        "Quit"),
    ]

    CSS = """
    HomeScreen { background: #0d0d14; }

    #rx-header {
        height: 9; background: #0d0d14;
        border-bottom: solid #1e1e3a;
        padding: 1 3; layout: vertical;
        align: left top;
    }
    #rx-logo { color: #6c63ff; text-style: bold; height: 5; }
    #rx-sub  { color: #5a5a7a; height: 2; }

    #stats-bar {
        height: 3; background: #13131f;
        border-bottom: solid #1e1e3a;
        layout: horizontal; padding: 0 3;
        align: left middle;
    }
    .stat-chip { color: #5a5a7a; margin-right: 3; }

    #menu-grid {
        height: 1fr;
        grid-size: 3;
        grid-gutter: 1 2;
        padding: 1 2;
        background: #0d0d14;
    }

    .menu-btn {
        height: 6;
        background: #13131f;
        border: solid #1e1e3a;
        color: #b0b0c8;
        content-align: center middle;
        text-style: none;
    }
    .menu-btn:hover {
        background: #1a1a2e;
        border: solid #6c63ff;
        color: #e2e2f0;
    }
    .menu-btn:focus {
        background: #1a1a2e;
        border: solid #6c63ff;
    }

    #quote-bar {
        height: 2; background: #0a0a10;
        border-top: solid #1e1e3a;
        color: #3a3a5a; content-align: center middle;
        padding: 0 3;
    }
    #footer-hint {
        height: 1; background: #13131f;
        color: #3a3a5a; padding: 0 2;
        dock: bottom;
    }
    """

    def compose(self) -> ComposeResult:
        now = datetime.now()
        logo = (
            "  ██████╗ ██╗  ██╗ ██████╗ ███████╗\n"
            "  ██╔══██╗╚██╗██╔╝██╔═══██╗██╔════╝\n"
            "  ██████╔╝ ╚███╔╝ ██║   ██║███████╗\n"
            "  ██╔══██╗ ██╔██╗ ██║   ██║╚════██║\n"
            "  ██║  ██║██╔╝ ██╗╚██████╔╝███████║\n"
            "  ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
        )
        with Vertical(id="rx-header"):
            yield Label(logo, id="rx-logo")
            yield Label(
                f"  Personal OS  ·  {now.strftime('%A, %d %B %Y')}  ·  {now.strftime('%H:%M')}",
                id="rx-sub"
            )

        notes_count = len(storage.get("notes", []))
        todo_count  = len([t for t in storage.get("todos", []) if not t.get("done")])
        snip_count  = len(storage.get("snippets", []))
        streak      = self._best_streak()
        with Horizontal(id="stats-bar"):
            yield Label(f"Notes [bold]{notes_count}[/bold]",    classes="stat-chip", markup=True)
            yield Label(f"Pending [bold]{todo_count}[/bold]",   classes="stat-chip", markup=True)
            yield Label(f"Snippets [bold]{snip_count}[/bold]",  classes="stat-chip", markup=True)
            yield Label(f"Streak [bold]{streak}🔥[/bold]",      classes="stat-chip", markup=True)

        with Grid(id="menu-grid"):
            for icon, name, key, _ in MENU_ITEMS:
                yield Button(
                    f"{icon}  {name}\n  [{key}]",
                    id=f"btn-{name.lower()}",
                    classes="menu-btn"
                )

        yield Label(f'  "{random.choice(QUOTES)}"', id="quote-bar")
        yield Label("  Press key shortcut or click a tile  ·  Q to quit", id="footer-hint")

    def _best_streak(self) -> int:
        habits = storage.get("habits", [])
        best = 0
        for h in habits:
            checks = h.get("checks", {})
            streak = 0
            from datetime import timedelta
            d = datetime.now()
            while True:
                ds = d.strftime("%Y-%m-%d")
                if checks.get(ds):
                    streak += 1
                    d -= timedelta(days=1)
                else:
                    break
            best = max(best, streak)
        return best

    @on(Button.Pressed)
    def on_menu_btn(self, event: Button.Pressed) -> None:
        mapping = {
            "btn-notes":      NotesScreen,
            "btn-todo":       TodoScreen,
            "btn-calculator": CalculatorScreen,
            "btn-pomodoro":   PomodoroScreen,
            "btn-vault":      VaultScreen,
            "btn-snippets":   SnippetScreen,
            "btn-journal":    JournalScreen,
            "btn-habits":     HabitScreen,
            "btn-sysmon":     SysMonScreen,
            "btn-terminal":   TerminalScreen,
            "btn-music":      MusicScreen,
        }
        screen_cls = mapping.get(event.button.id)
        if screen_cls:
            self.app.push_screen(screen_cls())

    def action_open_notes(self):      self.app.push_screen(NotesScreen())
    def action_open_todo(self):       self.app.push_screen(TodoScreen())
    def action_open_calc(self):       self.app.push_screen(CalculatorScreen())
    def action_open_pomodoro(self):   self.app.push_screen(PomodoroScreen())
    def action_open_vault(self):      self.app.push_screen(VaultScreen())
    def action_open_snippets(self):   self.app.push_screen(SnippetScreen())
    def action_open_journal(self):    self.app.push_screen(JournalScreen())
    def action_open_habits(self):     self.app.push_screen(HabitScreen())
    def action_open_sysmon(self):     self.app.push_screen(SysMonScreen())
    def action_open_terminal(self):   self.app.push_screen(TerminalScreen())
    def action_open_music(self):      self.app.push_screen(MusicScreen())


class RxOSApp(App):
    TITLE = "RXOS-TUI"
    SUB_TITLE = "Personal OS by rixz"
    CSS = """
    App { background: #0d0d14; }
    Notification {
        background: #13131f;
        border: solid #6c63ff;
        color: #e2e2f0;
    }
    ProgressBar > Bar { color: #6c63ff; background: #1e1e3a; }
    ProgressBar > Bar > BarFill { color: #6c63ff; }
    """

    def on_mount(self) -> None:
        self.push_screen(HomeScreen())

    def action_exit(self):
        self.exit()
