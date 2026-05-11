from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, ListView, ListItem, Label, TextArea, Input, Button
from textual.containers import Horizontal, Vertical, Container
from textual.binding import Binding
from textual import on
from rxos import storage
import uuid

class NotesScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+n", "new_note", "New"),
        Binding("ctrl+d", "delete_note", "Delete"),
        Binding("ctrl+s", "save_note", "Save"),
    ]

    CSS = """
    NotesScreen {
        layout: horizontal;
    }
    #sidebar {
        width: 30%;
        min-width: 20;
        border-right: solid #2a2a4a;
        background: #0d0d14;
    }
    #sidebar-header {
        background: #13131f;
        color: #6c63ff;
        text-style: bold;
        content-align: center middle;
        height: 3;
        border-bottom: solid #2a2a4a;
        padding: 0 1;
    }
    #notes-list {
        height: 1fr;
    }
    #editor-area {
        width: 1fr;
        background: #0d0d14;
    }
    #editor-header {
        height: 3;
        background: #13131f;
        border-bottom: solid #2a2a4a;
        padding: 0 2;
        color: #e2e2f0;
        text-style: bold;
        content-align: left middle;
    }
    #title-input {
        background: #13131f;
        border: none;
        color: #e2e2f0;
        height: 3;
        border-bottom: solid #2a2a4a;
        padding: 0 2;
    }
    #content-editor {
        height: 1fr;
        background: #0d0d14;
        color: #e2e2f0;
        border: none;
        padding: 1 2;
    }
    #hint-bar {
        height: 1;
        background: #13131f;
        color: #5a5a7a;
        padding: 0 2;
        content-align: left middle;
    }
    ListView > ListItem {
        padding: 0 1;
        color: #b0b0c8;
    }
    ListView > ListItem.--highlight {
        background: #1a1a2e;
        color: #e2e2f0;
    }
    """

    def __init__(self):
        super().__init__()
        self._notes = []
        self._current_id = None

    def compose(self) -> ComposeResult:
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label(" 📝 NOTES", id="sidebar-header")
                yield ListView(id="notes-list")
            with Vertical(id="editor-area"):
                yield Input(placeholder="Note title...", id="title-input")
                yield TextArea("", id="content-editor")
                yield Label("^N new  ^S save  ^D delete  ESC back", id="hint-bar")

    def on_mount(self) -> None:
        self._load_notes()

    def _load_notes(self):
        self._notes = storage.get("notes", [])
        lv = self.query_one("#notes-list", ListView)
        lv.clear()
        for note in self._notes:
            preview = note.get("title", "Untitled")
            lv.append(ListItem(Label(f"  {preview}"), id=f"note-{note['id']}"))
        if self._notes:
            lv.focus()

    def _save_current(self):
        if self._current_id is None:
            return
        title = self.query_one("#title-input", Input).value.strip()
        content = self.query_one("#content-editor", TextArea).text
        for note in self._notes:
            if note["id"] == self._current_id:
                note["title"] = title or "Untitled"
                note["content"] = content
                note["updated"] = storage.now_str()
                break
        storage.set("notes", self._notes)

    @on(ListView.Highlighted)
    def on_note_selected(self, event: ListView.Highlighted) -> None:
        if event.item is None:
            return
        item_id = event.item.id
        if item_id and item_id.startswith("note-"):
            note_id = item_id[5:]
            for note in self._notes:
                if note["id"] == note_id:
                    self._current_id = note_id
                    self.query_one("#title-input", Input).value = note.get("title", "")
                    self.query_one("#content-editor", TextArea).load_text(note.get("content", ""))
                    break

    def action_new_note(self):
        self._save_current()
        new_note = {
            "id": str(uuid.uuid4())[:8],
            "title": "New Note",
            "content": "",
            "created": storage.now_str(),
            "updated": storage.now_str(),
        }
        self._notes.insert(0, new_note)
        storage.set("notes", self._notes)
        self._current_id = new_note["id"]
        lv = self.query_one("#notes-list", ListView)
        lv.clear()
        for note in self._notes:
            lv.append(ListItem(Label(f"  {note.get('title', 'Untitled')}"), id=f"note-{note['id']}"))
        self.query_one("#title-input", Input).value = "New Note"
        self.query_one("#content-editor", TextArea).load_text("")
        self.query_one("#title-input", Input).focus()

    def action_save_note(self):
        self._save_current()
        self._load_notes()
        self.notify("Note saved!", title="RXOS")

    def action_delete_note(self):
        if self._current_id is None:
            return
        self._notes = [n for n in self._notes if n["id"] != self._current_id]
        storage.set("notes", self._notes)
        self._current_id = None
        self.query_one("#title-input", Input).value = ""
        self.query_one("#content-editor", TextArea).load_text("")
        self._load_notes()
        self.notify("Note deleted.", title="RXOS")

    def on_screen_resume(self) -> None:
        self._load_notes()
