from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Label, Input, ListView, ListItem, Button
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import on
from rxos import storage
from rxos.utils.crypto import derive_key, new_salt, encrypt, decrypt, verify_key
from rxos.utils.clipboard import copy
import base64
import uuid

class UnlockModal(ModalScreen):
    CSS = """
    UnlockModal { align: center middle; }
    #modal-box {
        width: 50; height: 12;
        background: #13131f; border: round #6c63ff;
        padding: 2 4; align: center middle;
    }
    #modal-title { color: #6c63ff; text-style: bold; content-align: center middle; height: 3; }
    #master-input { width: 1fr; background: #0d0d14; color: #e2e2f0; border: solid #2a2a4a; }
    #modal-hint { color: #5a5a7a; content-align: center middle; height: 2; }
    """
    def __init__(self, is_new: bool = False):
        super().__init__()
        self.is_new = is_new

    def compose(self) -> ComposeResult:
        with Vertical(id="modal-box"):
            yield Label("🔐 VAULT UNLOCK", id="modal-title")
            yield Input(password=True, placeholder="Master password...", id="master-input")
            msg = "Set a new master password" if self.is_new else "Enter master password"
            yield Label(msg, id="modal-hint")

    def on_mount(self):
        self.query_one("#master-input", Input).focus()

    @on(Input.Submitted)
    def on_submitted(self, event: Input.Submitted):
        self.dismiss(event.value)

class AddEntryModal(ModalScreen):
    CSS = """
    AddEntryModal { align: center middle; }
    #add-box {
        width: 60; height: 18;
        background: #13131f; border: round #6c63ff;
        padding: 1 3;
    }
    #add-title { color: #6c63ff; text-style: bold; height: 3; content-align: center middle; }
    Input { background: #0d0d14; color: #e2e2f0; border: solid #2a2a4a; margin-bottom: 1; width: 1fr; }
    Label.field-label { color: #5a5a7a; height: 1; }
    #add-btn-row { height: 3; align: right middle; }
    Button { margin-left: 1; }
    #btn-save { background: #6c63ff; color: #fff; border: none; }
    #btn-cancel { background: #13131f; color: #e2e2f0; border: solid #2a2a4a; }
    """
    def compose(self) -> ComposeResult:
        with Vertical(id="add-box"):
            yield Label("➕ ADD ENTRY", id="add-title")
            yield Label("Name / Site", classes="field-label")
            yield Input(placeholder="e.g. GitHub", id="inp-name")
            yield Label("Username / Email", classes="field-label")
            yield Input(placeholder="user@email.com", id="inp-user")
            yield Label("Password", classes="field-label")
            yield Input(placeholder="password", password=True, id="inp-pass")
            yield Label("Notes (optional)", classes="field-label")
            yield Input(placeholder="any extra info", id="inp-notes")
            with Horizontal(id="add-btn-row"):
                yield Button("Cancel", id="btn-cancel")
                yield Button("Save", id="btn-save")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-cancel":
            self.dismiss(None)
        elif event.button.id == "btn-save":
            data = {
                "name": self.query_one("#inp-name", Input).value.strip(),
                "username": self.query_one("#inp-user", Input).value.strip(),
                "password": self.query_one("#inp-pass", Input).value,
                "notes": self.query_one("#inp-notes", Input).value.strip(),
            }
            self.dismiss(data)

class VaultScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("a", "add_entry", "Add"),
        Binding("d", "delete_entry", "Delete"),
        Binding("c", "copy_password", "Copy PW"),
        Binding("l", "lock_vault", "Lock"),
    ]

    CSS = """
    VaultScreen { background: #0d0d14; }
    #vault-header {
        height: 3; background: #13131f; color: #6c63ff;
        text-style: bold; content-align: center middle;
        border-bottom: solid #2a2a4a;
    }
    #entries-list { height: 1fr; }
    #detail-panel {
        height: 8; background: #13131f;
        border-top: solid #2a2a4a; padding: 1 2;
        color: #e2e2f0;
    }
    #hint-bar { height: 1; background: #13131f; color: #5a5a7a; padding: 0 2; }
    ListView > ListItem { padding: 0 1; color: #b0b0c8; }
    ListView > ListItem.--highlight { background: #1a1a2e; color: #e2e2f0; }
    """

    def __init__(self):
        super().__init__()
        self._key: bytes | None = None
        self._entries = []

    def compose(self) -> ComposeResult:
        yield Label(" 🔐 PASSWORD VAULT", id="vault-header")
        yield ListView(id="entries-list")
        yield Label("Select an entry to view details", id="detail-panel")
        yield Label("A add  C copy pw  D delete  L lock  ESC back", id="hint-bar")

    def on_mount(self):
        vault = storage.get("vault", {})
        is_new = "salt" not in vault
        self.app.push_screen(UnlockModal(is_new=is_new), self._on_unlock)

    def _on_unlock(self, password: str | None):
        if not password:
            self.app.pop_screen()
            return
        vault = storage.get("vault", {})
        if "salt" not in vault:
            salt_str = new_salt()
            salt = base64.b64decode(salt_str)
            self._key = derive_key(password, salt)
            # Store salt + verification token
            verify_token = encrypt("rxos_vault_ok", self._key)
            storage.set("vault", {"salt": salt_str, "verify": verify_token, "entries": []})
            self.notify("Vault created!", title="Vault")
        else:
            salt = base64.b64decode(vault["salt"])
            self._key = derive_key(password, salt)
            if not verify_key(vault.get("verify", ""), self._key):
                self.notify("Wrong password!", title="Vault", severity="error")
                self._key = None
                self.app.pop_screen()
                return
            self.notify("Vault unlocked!", title="Vault")
        self._load_entries()

    def _load_entries(self):
        vault = storage.get("vault", {})
        self._entries = vault.get("entries", [])
        lv = self.query_one("#entries-list", ListView)
        lv.clear()
        for e in self._entries:
            lv.append(ListItem(
                Label(f"  🔑 {e['name']}  ·  {e['username']}  ·  ••••••••"),
                id=f"vault-{e['id']}"
            ))

    def _get_selected_id(self):
        lv = self.query_one("#entries-list", ListView)
        if lv.highlighted_child:
            item_id = lv.highlighted_child.id
            if item_id and item_id.startswith("vault-"):
                return item_id[6:]
        return None

    @on(ListView.Highlighted)
    def on_entry_highlighted(self, event: ListView.Highlighted):
        if event.item is None or self._key is None:
            return
        item_id = event.item.id
        if item_id and item_id.startswith("vault-"):
            eid = item_id[6:]
            for e in self._entries:
                if e["id"] == eid:
                    try:
                        pw = decrypt(e["password_enc"], self._key)
                        display = (
                            f"Name: {e['name']}\n"
                            f"User: {e['username']}\n"
                            f"Pass: {'•' * len(pw)}\n"
                            f"Notes: {e.get('notes', '-')}"
                        )
                        self.query_one("#detail-panel", Label).update(display)
                    except Exception:
                        pass
                    break

    def action_add_entry(self):
        if self._key is None:
            return
        self.app.push_screen(AddEntryModal(), self._on_add_entry)

    def _on_add_entry(self, data: dict | None):
        if not data or not data.get("name") or not data.get("password"):
            return
        entry = {
            "id": str(uuid.uuid4())[:8],
            "name": data["name"],
            "username": data["username"],
            "password_enc": encrypt(data["password"], self._key),
            "notes": data.get("notes", ""),
            "created": storage.now_str(),
        }
        vault = storage.get("vault", {})
        vault.setdefault("entries", []).insert(0, entry)
        storage.set("vault", vault)
        self._load_entries()
        self.notify("Entry added!", title="Vault")

    def action_copy_password(self):
        eid = self._get_selected_id()
        if not eid or self._key is None:
            return
        for e in self._entries:
            if e["id"] == eid:
                try:
                    pw = decrypt(e["password_enc"], self._key)
                    if copy(pw):
                        self.notify("Password copied!", title="Vault")
                    else:
                        self.notify("Copy failed — termux-clipboard not available", severity="warning")
                except Exception:
                    self.notify("Decrypt error", severity="error")
                break

    def action_delete_entry(self):
        eid = self._get_selected_id()
        if not eid:
            return
        vault = storage.get("vault", {})
        vault["entries"] = [e for e in vault.get("entries", []) if e["id"] != eid]
        storage.set("vault", vault)
        self._load_entries()
        self.notify("Entry deleted.", title="Vault")

    def action_lock_vault(self):
        self._key = None
        self._entries = []
        self.app.pop_screen()
