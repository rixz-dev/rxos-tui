from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, TextArea, ListView, ListItem, Button
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import on
from rxos import storage
from datetime import datetime, timedelta

MOODS = ["😐", "🙂", "😊", "🔥", "😴", "😤", "😔"]

class JournalScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("ctrl+s", "save_entry", "Save"),
        Binding("m", "cycle_mood", "Mood"),
        Binding("ctrl+e", "export_entry", "Export"),
    ]

    CSS = """
    JournalScreen { layout: horizontal; background: #0d0d14; }
    #journal-sidebar {
        width: 28%; min-width: 18;
        border-right: solid #2a2a4a;
        background: #0d0d14;
    }
    #journal-sidebar-header {
        height: 3; background: #13131f; color: #6c63ff;
        text-style: bold; content-align: center middle;
        border-bottom: solid #2a2a4a;
    }
    #entry-list { height: 1fr; }
    #journal-editor-area { width: 1fr; background: #0d0d14; }
    #journal-top-bar {
        height: 3; background: #13131f;
        border-bottom: solid #2a2a4a;
        padding: 0 2; layout: horizontal;
        align: left middle;
    }
    #date-label { color: #6c63ff; text-style: bold; width: 1fr; }
    #mood-label { color: #e2e2f0; width: 10; content-align: right middle; }
    #journal-editor {
        height: 1fr; background: #0a0a10;
        border: none; padding: 1 2; color: #e2e2f0;
    }
    #hint-bar { height: 1; background: #13131f; color: #5a5a7a; padding: 0 2; }
    ListView > ListItem { padding: 0 1; color: #b0b0c8; }
    ListView > ListItem.--highlight { background: #1a1a2e; color: #e2e2f0; }
    """

    def __init__(self):
        super().__init__()
        self._entries: dict = {}
        self._current_date = storage.today_str()
        self._mood_idx = 0

    def compose(self) -> ComposeResult:
        with Vertical(id="journal-sidebar"):
            yield Label(" 📓 JOURNAL", id="journal-sidebar-header")
            yield ListView(id="entry-list")
        with Vertical(id="journal-editor-area"):
            with Horizontal(id="journal-top-bar"):
                yield Label(self._current_date, id="date-label")
                yield Label(MOODS[self._mood_idx], id="mood-label")
            yield TextArea("", id="journal-editor")
            yield Label("^S save  M mood  ^E export  ESC back", id="hint-bar")

    def on_mount(self):
        self._load_all()
        self._load_date(self._current_date)

    def _load_all(self):
        self._entries = storage.get("journal", {})
        lv = self.query_one("#entry-list", ListView)
        lv.clear()
        sorted_dates = sorted(self._entries.keys(), reverse=True)
        for d in sorted_dates:
            entry = self._entries[d]
            mood = entry.get("mood", "😐")
            lv.append(ListItem(Label(f"  {mood} {d}"), id=f"jour-{d}"))

    def _load_date(self, date_str: str):
        self._current_date = date_str
        self.query_one("#date-label", Label).update(date_str)
        entry = self._entries.get(date_str, {})
        content = entry.get("content", "")
        mood = entry.get("mood", MOODS[0])
        self._mood_idx = MOODS.index(mood) if mood in MOODS else 0
        self.query_one("#journal-editor", TextArea).load_text(content)
        self.query_one("#mood-label", Label).update(MOODS[self._mood_idx])

    @on(ListView.Highlighted)
    def on_date_selected(self, event: ListView.Highlighted):
        if event.item is None:
            return
        item_id = event.item.id
        if item_id and item_id.startswith("jour-"):
            date_str = item_id[5:]
            self._load_date(date_str)

    def action_cycle_mood(self):
        self._mood_idx = (self._mood_idx + 1) % len(MOODS)
        self.query_one("#mood-label", Label).update(MOODS[self._mood_idx])

    def action_save_entry(self):
        content = self.query_one("#journal-editor", TextArea).text.strip()
        if not content:
            self.notify("Nothing to save.", severity="warning")
            return
        self._entries[self._current_date] = {
            "content": content,
            "mood": MOODS[self._mood_idx],
            "updated": storage.now_str(),
        }
        storage.set("journal", self._entries)
        self._load_all()
        self.notify("Journal entry saved!", title="RXOS")

    def action_export_entry(self):
        from pathlib import Path
        content = self.query_one("#journal-editor", TextArea).text
        entry = self._entries.get(self._current_date, {})
        mood = entry.get("mood", "")
        export_path = Path.home() / f"rxos_journal_{self._current_date}.md"
        with open(export_path, "w", encoding="utf-8") as f:
            f.write(f"# Journal — {self._current_date} {mood}\n\n")
            f.write(content)
        self.notify(f"Exported to {export_path}", title="RXOS")
