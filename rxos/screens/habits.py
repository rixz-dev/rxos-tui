from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Input, ListView, ListItem, DataTable
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import on
from rxos import storage
from datetime import datetime, timedelta
import uuid

def last_n_days(n: int) -> list[str]:
    today = datetime.now()
    return [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(n - 1, -1, -1)]

def short_date(d: str) -> str:
    dt = datetime.strptime(d, "%Y-%m-%d")
    return dt.strftime("%d/%m")

class HabitScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("a", "add_habit", "Add"),
        Binding("d", "delete_habit", "Delete"),
        Binding("space", "toggle_today", "Check today"),
    ]

    CSS = """
    HabitScreen { background: #0d0d14; }
    #habit-header {
        height: 3; background: #13131f; color: #6c63ff;
        text-style: bold; content-align: center middle;
        border-bottom: solid #2a2a4a;
    }
    #grid-area { height: 1fr; padding: 1 1; }
    #add-row {
        height: 3; background: #13131f;
        border-top: solid #2a2a4a; padding: 0 1;
    }
    #add-input { width: 1fr; background: #13131f; border: none; color: #e2e2f0; }
    #hint-bar { height: 1; background: #13131f; color: #5a5a7a; padding: 0 2; }
    DataTable { height: 1fr; background: #0d0d14; }
    """

    def __init__(self):
        super().__init__()
        self._habits = []
        self._today = storage.today_str()
        self._days = last_n_days(14)

    def compose(self) -> ComposeResult:
        yield Label(" 🔥 HABIT TRACKER", id="habit-header")
        yield DataTable(id="habit-grid", zebra_stripes=True)
        with Horizontal(id="add-row"):
            yield Input(placeholder="A → type habit name → Enter", id="add-input")
        yield Label("A add  SPC check today  D delete  ESC back", id="hint-bar")

    def on_mount(self):
        table = self.query_one("#habit-grid", DataTable)
        table.add_column("Habit", width=22)
        table.add_column("🔥", width=5)
        for d in self._days:
            table.add_column(short_date(d), width=5)
        self._load()
        self.query_one("#add-input", Input).display = False

    def _streak(self, habit: dict) -> int:
        checks = habit.get("checks", {})
        streak = 0
        d = datetime.now()
        while True:
            ds = d.strftime("%Y-%m-%d")
            if checks.get(ds):
                streak += 1
                d -= timedelta(days=1)
            else:
                break
        return streak

    def _load(self):
        self._habits = storage.get("habits", [])
        table = self.query_one("#habit-grid", DataTable)
        table.clear()
        for h in self._habits:
            checks = h.get("checks", {})
            streak = self._streak(h)
            row = [h["name"], f"{streak}🔥"]
            for d in self._days:
                row.append("✓" if checks.get(d) else "·")
            table.add_row(*row, key=h["id"])

    def action_add_habit(self):
        inp = self.query_one("#add-input", Input)
        inp.display = True
        inp.value = ""
        inp.focus()

    @on(Input.Submitted, "#add-input")
    def on_add_submitted(self, event: Input.Submitted):
        val = event.value.strip()
        if val:
            new_habit = {
                "id": str(uuid.uuid4())[:8],
                "name": val,
                "checks": {},
                "created": storage.today_str(),
            }
            self._habits.insert(0, new_habit)
            storage.set("habits", self._habits)
        self.query_one("#add-input", Input).display = False
        self._load()
        self.query_one("#habit-grid", DataTable).focus()

    def action_toggle_today(self):
        table = self.query_one("#habit-grid", DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self._habits):
            return
        habit = self._habits[table.cursor_row]
        checks = habit.setdefault("checks", {})
        checks[self._today] = not checks.get(self._today, False)
        storage.set("habits", self._habits)
        self._load()
        status = "✓ Checked!" if checks[self._today] else "○ Unchecked"
        self.notify(f"{habit['name']}: {status}", title="RXOS")

    def action_delete_habit(self):
        table = self.query_one("#habit-grid", DataTable)
        if table.cursor_row < 0 or table.cursor_row >= len(self._habits):
            return
        self._habits.pop(table.cursor_row)
        storage.set("habits", self._habits)
        self._load()
        self.notify("Habit deleted.", title="RXOS")
