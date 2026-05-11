from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, ListView, ListItem, Label, Input
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import on
from rxos import storage
import uuid

PRIORITIES = ["low", "med", "high"]
PRIORITY_COLORS = {"high": "red", "med": "yellow", "low": "green"}
PRIORITY_ICONS = {"high": "🔴", "med": "🟡", "low": "🟢"}

class TodoScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("a", "add_todo", "Add"),
        Binding("d", "delete_todo", "Delete"),
        Binding("space", "toggle_todo", "Toggle", show=True),
        Binding("p", "cycle_priority", "Priority"),
    ]

    CSS = """
    TodoScreen { background: #0d0d14; }
    #todo-header {
        height: 3; background: #13131f;
        color: #6c63ff; text-style: bold;
        content-align: center middle;
        border-bottom: solid #2a2a4a;
    }
    #add-row {
        height: 3; background: #13131f;
        border-top: solid #2a2a4a;
        padding: 0 1;
    }
    #add-input {
        width: 1fr; background: #13131f;
        border: none; color: #e2e2f0;
    }
    #todo-list { height: 1fr; background: #0d0d14; }
    #hint-bar {
        height: 1; background: #13131f;
        color: #5a5a7a; padding: 0 2;
    }
    ListView > ListItem { padding: 0 1; color: #b0b0c8; }
    ListView > ListItem.--highlight { background: #1a1a2e; color: #e2e2f0; }
    """

    def __init__(self):
        super().__init__()
        self._todos = []
        self._adding = False

    def compose(self) -> ComposeResult:
        yield Label(" ✅ TODO / CHECKLIST", id="todo-header")
        yield ListView(id="todo-list")
        with Horizontal(id="add-row"):
            yield Input(placeholder="Add task... (press A, then Enter)", id="add-input")
        yield Label("A add  SPC toggle  P priority  D delete  ESC back", id="hint-bar")

    def on_mount(self):
        self._load()
        self.query_one("#add-input", Input).display = False

    def _load(self):
        self._todos = storage.get("todos", [])
        lv = self.query_one("#todo-list", ListView)
        lv.clear()
        for todo in self._todos:
            done = todo.get("done", False)
            p = todo.get("priority", "low")
            icon = PRIORITY_ICONS[p]
            check = "✓" if done else "○"
            style = "dim" if done else ""
            label_text = f"  {check} {icon} {todo['title']}"
            lv.append(ListItem(Label(label_text), id=f"todo-{todo['id']}"))

    def _get_selected_id(self):
        lv = self.query_one("#todo-list", ListView)
        if lv.highlighted_child:
            item_id = lv.highlighted_child.id
            if item_id and item_id.startswith("todo-"):
                return item_id[5:]
        return None

    def action_add_todo(self):
        inp = self.query_one("#add-input", Input)
        inp.display = True
        inp.value = ""
        inp.focus()

    @on(Input.Submitted, "#add-input")
    def on_add_submitted(self, event: Input.Submitted):
        val = event.value.strip()
        if val:
            new_todo = {
                "id": str(uuid.uuid4())[:8],
                "title": val,
                "done": False,
                "priority": "low",
                "created": storage.now_str(),
            }
            self._todos.insert(0, new_todo)
            storage.set("todos", self._todos)
        self.query_one("#add-input", Input).display = False
        self._load()
        self.query_one("#todo-list", ListView).focus()

    def action_toggle_todo(self):
        tid = self._get_selected_id()
        if not tid:
            return
        for todo in self._todos:
            if todo["id"] == tid:
                todo["done"] = not todo["done"]
                break
        storage.set("todos", self._todos)
        self._load()

    def action_cycle_priority(self):
        tid = self._get_selected_id()
        if not tid:
            return
        for todo in self._todos:
            if todo["id"] == tid:
                cur = todo.get("priority", "low")
                idx = PRIORITIES.index(cur)
                todo["priority"] = PRIORITIES[(idx + 1) % len(PRIORITIES)]
                break
        storage.set("todos", self._todos)
        self._load()

    def action_delete_todo(self):
        tid = self._get_selected_id()
        if not tid:
            return
        self._todos = [t for t in self._todos if t["id"] != tid]
        storage.set("todos", self._todos)
        self._load()
        self.notify("Task deleted.", title="RXOS")
