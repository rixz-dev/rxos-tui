from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Input, ListView, ListItem
from textual.containers import Vertical, Horizontal
from textual.binding import Binding
from textual import on
import asyncio
import os
import socket
import json
import shutil


class MusicScreen(Screen):
    BINDINGS = [
        Binding("escape",    "app.pop_screen", "Back",    priority=True),
        Binding("space",     "toggle_pause",   "⏯ Pause"),
        Binding("s",         "stop_music",     "■ Stop"),
        Binding("ctrl+f",    "focus_search",   "Search"),
        Binding("equal",     "vol_up",         "Vol+"),
        Binding("minus",     "vol_down",       "Vol-"),
    ]

    CSS = """
    MusicScreen { background: #0d0d14; }

    #music-header {
        height: 3;
        background: #13131f;
        color: #6c63ff;
        text-style: bold;
        content-align: center middle;
        border-bottom: solid #2a2a4a;
    }

    #now-playing-bar {
        height: 4;
        background: #0f0f1c;
        border-bottom: solid #2a2a4a;
        padding: 0 2;
    }

    #np-title {
        color: #e2e2f0;
        text-style: bold;
        height: 2;
        content-align: left middle;
    }

    #np-status {
        color: #6c63ff;
        height: 2;
        content-align: left middle;
    }

    #search-row {
        height: 3;
        background: #0d0d14;
        border-bottom: solid #1e1e3a;
        padding: 0 1;
        align: left middle;
    }

    #search-label {
        color: #5a5a7a;
        width: 12;
        height: 3;
        content-align: left middle;
    }

    #search-input {
        background: #0d0d14;
        border: none;
        color: #e2e2f0;
        height: 3;
        width: 1fr;
        border-bottom: solid #6c63ff;
    }

    #results-list {
        height: 1fr;
        background: #0d0d14;
        scrollbar-color: #2a2a4a;
        scrollbar-background: #0d0d14;
    }

    ListView > ListItem {
        padding: 0 2;
        color: #b0b0c8;
        height: 2;
    }

    ListView > ListItem.--highlight {
        background: #1a1a2e;
        color: #e2e2f0;
    }

    #status-bar {
        height: 1;
        background: #0a0a10;
        color: #3a3a5a;
        padding: 0 2;
        dock: bottom;
    }
    """

    MPV_SOCKET = "/tmp/rxos_mpv.sock"

    def __init__(self):
        super().__init__()
        self._results: list[tuple[str, str, str]] = []  # (vid_id, title, duration)
        self._mpv_proc: asyncio.subprocess.Process | None = None
        self._is_playing = False
        self._is_paused = False

    # ── Compose ────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Label(" 🎵 MUSIC PLAYER", id="music-header")
        with Vertical(id="now-playing-bar"):
            yield Label("♪  Nothing playing", id="np-title")
            yield Label("  Stopped  ·  search something to begin", id="np-status")
        with Horizontal(id="search-row"):
            yield Label(" 🔍 Search:", id="search-label")
            yield Input(
                placeholder="artist / song name — press Enter to search",
                id="search-input"
            )
        yield ListView(id="results-list")
        yield Label(
            "SPACE pause  S stop  = vol+  - vol-  ↑↓ select  ENTER play  ESC back",
            id="status-bar"
        )

    def on_mount(self):
        self.query_one("#search-input", Input).focus()
        self._check_deps()

    def _check_deps(self):
        lv = self.query_one("#results-list", ListView)
        missing = []
        if not shutil.which("yt-dlp"):
            missing.append("yt-dlp  →  pip install yt-dlp")
        if not shutil.which("mpv"):
            missing.append("mpv     →  pkg install mpv")
        if missing:
            lv.append(ListItem(Label("  ⚠  Missing dependencies:")))
            for m in missing:
                lv.append(ListItem(Label(f"      {m}")))
            lv.append(ListItem(Label("  Run the commands above, then restart RXOS.")))

    # ── Search ─────────────────────────────────────────────────────────

    @on(Input.Submitted, "#search-input")
    def on_search(self, event: Input.Submitted) -> None:
        query = event.value.strip()
        if not query:
            return
        self.query_one("#np-status", Label).update(
            f"  🔍 Searching for  \"{query}\"..."
        )
        self.run_worker(
            self._do_search(query),
            exclusive=True,
            name="search",
        )

    async def _do_search(self, query: str) -> None:
        lv = self.query_one("#results-list", ListView)
        lv.clear()
        self._results = []

        try:
            proc = await asyncio.create_subprocess_exec(
                "yt-dlp",
                "--print", "%(id)s|||%(title)s|||%(duration_string)s",
                "--no-playlist",
                f"ytsearch5:{query}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=40)
            lines = stdout.decode("utf-8", errors="replace").strip().splitlines()

            for i, line in enumerate(lines):
                if "|||" not in line:
                    continue
                parts = line.split("|||")
                if len(parts) < 3:
                    continue
                vid_id   = parts[0].strip()
                title    = parts[1].strip()
                duration = parts[2].strip()
                self._results.append((vid_id, title, duration))

                disp = title[:46] + "…" if len(title) > 47 else title
                lv.append(ListItem(
                    Label(f"  {i + 1}. {disp:<49}  {duration}"),
                    id=f"result-{i}",
                ))

            if not self._results:
                lv.append(ListItem(Label("  No results found.")))
                self.query_one("#np-status", Label).update("  No results.")
            else:
                count = len(self._results)
                self.query_one("#np-status", Label).update(
                    f"  {count} results  ·  ↑↓ select  ·  ENTER to play"
                )

        except asyncio.TimeoutError:
            lv.append(ListItem(Label("  ⚠  Search timed out — check your connection.")))
            self.query_one("#np-status", Label).update("  Timed out.")

        except FileNotFoundError:
            lv.append(ListItem(Label("  ⚠  yt-dlp not found — pip install yt-dlp")))
            self.query_one("#np-status", Label).update("  yt-dlp missing.")

        except Exception as e:
            lv.append(ListItem(Label(f"  ⚠  Error: {e}")))
            self.query_one("#np-status", Label).update("  Error during search.")

    # ── Playback ───────────────────────────────────────────────────────

    @on(ListView.Selected, "#results-list")
    def on_result_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        if not item_id.startswith("result-"):
            return
        try:
            idx = int(item_id.split("-", 1)[1])
        except (IndexError, ValueError):
            return
        if idx < len(self._results):
            vid_id, title, _ = self._results[idx]
            self.run_worker(
                self._play(vid_id, title),
                exclusive=False,
                name="player",
            )

    async def _play(self, vid_id: str, title: str) -> None:
        np_title  = self.query_one("#np-title",  Label)
        np_status = self.query_one("#np-status", Label)

        # Stop existing playback first
        await self._stop_proc()

        np_title.update(f"♪  {title}")
        np_status.update("  ⏳ Resolving stream URL...")

        url = f"https://www.youtube.com/watch?v={vid_id}"

        # Step 1: resolve audio URL via yt-dlp
        try:
            proc = await asyncio.create_subprocess_exec(
                "yt-dlp",
                "-f", "bestaudio",
                "--get-url",
                "--no-playlist",
                url,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            audio_url = stdout.decode("utf-8", errors="replace").strip().splitlines()[0]
        except asyncio.TimeoutError:
            np_status.update("  ⚠  Timed out resolving stream.")
            return
        except (FileNotFoundError, IndexError):
            np_status.update("  ⚠  yt-dlp failed to resolve URL.")
            return
        except Exception as e:
            np_status.update(f"  ⚠  {e}")
            return

        # Step 2: play with mpv
        np_status.update("  ▶ Loading stream...")

        # Clean old IPC socket
        try:
            if os.path.exists(self.MPV_SOCKET):
                os.remove(self.MPV_SOCKET)
        except OSError:
            pass

        try:
            self._mpv_proc = await asyncio.create_subprocess_exec(
                "mpv",
                "--no-video",
                "--really-quiet",
                f"--input-ipc-server={self.MPV_SOCKET}",
                audio_url,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            self._is_playing = True
            self._is_paused  = False
            np_status.update("  ▶ Playing")

            await self._mpv_proc.wait()

            self._is_playing = False
            self._mpv_proc   = None
            # Only update if not already stopped manually
            try:
                cur = self.query_one("#np-status", Label)
                if "Playing" in str(cur.renderable):
                    cur.update("  ✓ Finished")
            except Exception:
                pass

        except FileNotFoundError:
            np_status.update("  ⚠  mpv not found — pkg install mpv")
            self._is_playing = False
        except Exception as e:
            np_status.update(f"  ⚠  {e}")
            self._is_playing = False

    async def _stop_proc(self):
        if self._mpv_proc and self._mpv_proc.returncode is None:
            try:
                self._mpv_proc.terminate()
                await asyncio.wait_for(self._mpv_proc.wait(), timeout=3)
            except (ProcessLookupError, asyncio.TimeoutError):
                try:
                    self._mpv_proc.kill()
                except ProcessLookupError:
                    pass
        self._mpv_proc   = None
        self._is_playing = False
        self._is_paused  = False

    # ── MPV IPC ────────────────────────────────────────────────────────

    def _mpv_ipc(self, command: list) -> bool:
        if not os.path.exists(self.MPV_SOCKET):
            return False
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            sock.connect(self.MPV_SOCKET)
            msg = json.dumps({"command": command}) + "\n"
            sock.sendall(msg.encode())
            sock.close()
            return True
        except Exception:
            return False

    # ── Actions ────────────────────────────────────────────────────────

    def action_toggle_pause(self) -> None:
        if not self._is_playing:
            return
        if self._mpv_ipc(["cycle", "pause"]):
            self._is_paused = not self._is_paused
            label = "  ⏸ Paused" if self._is_paused else "  ▶ Playing"
            self.query_one("#np-status", Label).update(label)

    def action_stop_music(self) -> None:
        self.run_worker(self._stop_proc(), name="stopper")
        self.query_one("#np-title",  Label).update("♪  Nothing playing")
        self.query_one("#np-status", Label).update("  Stopped")

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_vol_up(self) -> None:
        if self._mpv_ipc(["add", "volume", "10"]):
            self.notify("+10 volume", title="Music")

    def action_vol_down(self) -> None:
        if self._mpv_ipc(["add", "volume", "-10"]):
            self.notify("-10 volume", title="Music")

    # ── Cleanup ────────────────────────────────────────────────────────

    def on_unmount(self) -> None:
        if self._mpv_proc and self._mpv_proc.returncode is None:
            try:
                self._mpv_proc.terminate()
            except ProcessLookupError:
                pass
