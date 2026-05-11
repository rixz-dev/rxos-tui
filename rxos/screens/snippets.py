from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Label, Input, TextArea, ListView, ListItem, Select, Button
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import on
from rxos import storage
from rxos.utils.clipboard import copy
import uuid

LANGS = ["python", "javascript", "typescript", "bash", "sql", "rust", "go", "html", "css", "other"]

class AddSnippetModal(ModalScreen):
    CSS = """
    AddSnippetModal { align: center middle; }
    #snip-box {
        width: 70; height: 22;
        background: #13131f; border: round #6c63ff;
        padding: 1 3;
    }
    #snip-title { color: #6c63ff; text-style: bold; height: 3; content-align: center middle; }
    Input { background: #0d0d14; color: #e2e2f0; border: solid #2a2a4a; margin-bottom: 1; width: 1fr; }
    Select { background: #0d0d14; color: #e2e2f0; border: solid #2a2a4a; margin-bottom: 1; width: 1fr; }
    #snip-editor { height: 8; background: #0d0d14; border: solid #2a2a4a; margin-bottom: 1; }
    #snip-btn-row { height: 3; align: right middle; }
    Button { margin-left: 1; }
    #btn-save { background: #6c63ff; color: #fff; border: none; }
    #btn-cancel { background: #13131f; color: #e2e2f0; border: solid #2a2a4a; }
    Label.field-label { color: #5a5a7a; height: 1; }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="snip-box"):
            yield Label("➕ ADD SNIPPET", id="snip-title")
            yield Label("Title", classes="field-label")
            yield Input(placeholder="e.g. FastAPI auth middleware", id="inp-title")
            yield Label("Language", classes="field-label")
            yield Select(
                [(lang.upper(), lang) for lang in LANGS],
                value="python", id="inp-lang"
            )
            yield Label("Code", classes="field-label")
            yield TextArea("", id="snip-editor")
            with Horizontal(id="snip-btn-row"):
                yield Button("Cancel", id="btn-cancel")
                yield Button("Save", id="btn-save")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            data = {
                "title": self.query_one("#inp-title", Input).value.strip(),
                "lang": self.query_one("#inp-lang", Select).value,
                "code": self.query_one("#snip-editor", TextArea).text,
            }
            self.dismiss(data)


class SnippetScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("a", "add_snippet", "Add"),
        Binding("d", "delete_snippet", "Delete"),
        Binding("c", "copy_snippet", "Copy"),
        Binding("/", "focus_search", "Search"),
    ]

    CSS = """
    SnippetScreen { layout: horizontal; background: #0d0d14; }
    #snip-sidebar {
        width: 35%; min-width: 22;
        border-right: solid #2a2a4a;
        background: #0d0d14;
    }
    #snip-sidebar-header {
        height: 3; background: #13131f; color: #6c63ff;
        text-style: bold; content-align: center middle;
        border-bottom: solid #2a2a4a;
    }
    #search-input {
        height: 3; background: #0a0a10; border: none;
        color: #e2e2f0; border-bottom: solid #2a2a4a;
    }
    #snip-list { height: 1fr; }
    #snip-preview { width: 1fr; background: #0d0d14; }
    #preview-header {
        height: 3; background: #13131f; color: #e2e2f0;
        text-style: bold; content-align: left middle;
        border-bottom: solid #2a2a4a; padding: 0 2;
    }
    #preview-editor {
        height: 1fr; background: #0a0a10;
        border: none; padding: 1 2;
    }
    #hint-bar {
        height: 1; background: #13131f; color: #5a5a7a;
        padding: 0 2; dock: bottom; width: 100%;
    }
    ListView > ListItem { padding: 0 1; color: #b0b0c8; }
    ListView > ListItem.--highlight { background: #1a1a2e; color: #e2e2f0; }
    """

    def __init__(self):
        super().__init__()
        self._snippets = []
        self._filtered = []
        self._current_id = None

    def compose(self) -> ComposeResult:
        with Vertical(id="snip-sidebar"):
            yield Label(" 📋 SNIPPETS", id="snip-sidebar-header")
            yield Input(placeholder="/ search...", id="search-input")
            yield ListView(id="snip-list")
        with Vertical(id="snip-preview"):
            yield Label("Select a snippet", id="preview-header")
            yield TextArea("", id="preview-editor", read_only=True)
        yield Label("A add  C copy  D delete  / search  ESC back", id="hint-bar")

    def on_mount(self):
        self._load()

    def _load(self, query: str = ""):
        self._snippets = storage.get("snippets", [])
        q = query.lower().strip()
        self._filtered = [
            s for s in self._snippets
            if not q or q in s.get("title", "").lower() or q in s.get("lang", "").lower()
        ]
        lv = self.query_one("#snip-list", ListView)
        lv.clear()
        lang_icons = {
            "python": "🐍", "javascript": "🟨", "typescript": "🔷",
            "bash": "🖥", "sql": "🗄", "rust": "🦀",
            "go": "🐹", "html": "🌐", "css": "🎨", "other": "📄",
        }
        for s in self._filtered:
            icon = lang_icons.get(s.get("lang", "other"), "📄")
            lv.append(ListItem(Label(f"  {icon} {s['title']}"), id=f"snip-{s['id']}"))

    def _get_selected_id(self):
        lv = self.query_one("#snip-list", ListView)
        if lv.highlighted_child:
            item_id = lv.highlighted_child.id
            if item_id and item_id.startswith("snip-"):
                return item_id[5:]
        return None

    @on(ListView.Highlighted)
    def on_snip_selected(self, event: ListView.Highlighted):
        if event.item is None:
            return
        item_id = event.item.id
        if item_id and item_id.startswith("snip-"):
            sid = item_id[5:]
            self._current_id = sid
            for s in self._filtered:
                if s["id"] == sid:
                    self.query_one("#preview-header", Label).update(
                        f" {s['title']}  [{s.get('lang','?').upper()}]"
                    )
                    self.query_one("#preview-editor", TextArea).load_text(s.get("code", ""))
                    break

    @on(Input.Changed, "#search-input")
    def on_search(self, event: Input.Changed):
        self._load(event.value)

    def action_focus_search(self):
        self.query_one("#search-input", Input).focus()

    def action_add_snippet(self):
        self.app.push_screen(AddSnippetModal(), self._on_add)

    def _on_add(self, data: dict | None):
        if not data or not data.get("title"):
            return
        new_snip = {
            "id": str(uuid.uuid4())[:8],
            "title": data["title"],
            "lang": data.get("lang", "other"),
            "code": data.get("code", ""),
            "created": storage.now_str(),
        }
        self._snippets.insert(0, new_snip)
        storage.set("snippets", self._snippets)
        self._load()
        self.notify("Snippet saved!", title="RXOS")

    def action_copy_snippet(self):
        sid = self._get_selected_id()
        if not sid:
            return
        for s in self._filtered:
            if s["id"] == sid:
                if copy(s.get("code", "")):
                    self.notify("Copied to clipboard!", title="RXOS")
                else:
                    self.notify("Copy failed", severity="warning")
                break

    def action_delete_snippet(self):
        sid = self._get_selected_id()
        if not sid:
            return
        self._snippets = [s for s in self._snippets if s["id"] != sid]
        storage.set("snippets", self._snippets)
        self._current_id = None
        self.query_one("#preview-editor", TextArea).load_text("")
        self.query_one("#preview-header", Label).update("Select a snippet")
        self._load()
        self.notify("Snippet deleted.", title="RXOS")
