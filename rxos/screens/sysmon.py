from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, ProgressBar
from textual.containers import Vertical, Horizontal, Container
from textual.binding import Binding
try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

class SysMonScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("r", "refresh", "Refresh"),
    ]

    CSS = """
    SysMonScreen { background: #0d0d14; }
    #sysmon-header {
        height: 3; background: #13131f; color: #6c63ff;
        text-style: bold; content-align: center middle;
        border-bottom: solid #2a2a4a;
    }
    #sysmon-body { padding: 1 2; height: 1fr; }
    .section-title {
        color: #6c63ff; text-style: bold;
        height: 2; margin-top: 1;
    }
    .stat-row { height: 2; layout: horizontal; }
    .stat-label { color: #5a5a7a; width: 20; }
    .stat-value { color: #e2e2f0; text-style: bold; width: 1fr; }
    .bar-row { height: 2; layout: horizontal; align: left middle; }
    .bar-label { color: #5a5a7a; width: 10; }
    #cpu-bar { width: 30; height: 1; }
    #mem-bar { width: 30; height: 1; }
    #disk-bar { width: 30; height: 1; }
    .proc-row { height: 1; layout: horizontal; }
    .proc-name { color: #b0b0c8; width: 25; }
    .proc-cpu  { color: #6c63ff; width: 10; }
    .proc-mem  { color: #00d4aa; width: 10; }
    #hint-bar { height: 1; background: #13131f; color: #5a5a7a; padding: 0 2; dock: bottom; width: 100%; }
    #update-label { color: #5a5a7a; height: 1; }
    """

    def compose(self) -> ComposeResult:
        yield Label(" 📊 SYSTEM MONITOR", id="sysmon-header")
        with Vertical(id="sysmon-body"):
            yield Label("── CPU ─────────────────────────", classes="section-title")
            with Horizontal(classes="stat-row"):
                yield Label("Usage:", classes="stat-label")
                yield Label("...", id="cpu-val", classes="stat-value")
            with Horizontal(classes="bar-row"):
                yield Label("", classes="bar-label")
                yield ProgressBar(total=100, id="cpu-bar", show_eta=False, show_percentage=False)
            with Horizontal(classes="stat-row"):
                yield Label("Cores:", classes="stat-label")
                yield Label("...", id="cpu-cores", classes="stat-value")
            with Horizontal(classes="stat-row"):
                yield Label("Frequency:", classes="stat-label")
                yield Label("...", id="cpu-freq", classes="stat-value")

            yield Label("── MEMORY ──────────────────────", classes="section-title")
            with Horizontal(classes="stat-row"):
                yield Label("Used / Total:", classes="stat-label")
                yield Label("...", id="mem-val", classes="stat-value")
            with Horizontal(classes="bar-row"):
                yield Label("", classes="bar-label")
                yield ProgressBar(total=100, id="mem-bar", show_eta=False, show_percentage=False)

            yield Label("── DISK ────────────────────────", classes="section-title")
            with Horizontal(classes="stat-row"):
                yield Label("Used / Total:", classes="stat-label")
                yield Label("...", id="disk-val", classes="stat-value")
            with Horizontal(classes="bar-row"):
                yield Label("", classes="bar-label")
                yield ProgressBar(total=100, id="disk-bar", show_eta=False, show_percentage=False)

            yield Label("── NETWORK ─────────────────────", classes="section-title")
            with Horizontal(classes="stat-row"):
                yield Label("Sent / Recv:", classes="stat-label")
                yield Label("...", id="net-val", classes="stat-value")

            yield Label("── TOP PROCESSES ───────────────", classes="section-title")
            yield Label("", id="proc-list")
            yield Label("", id="update-label")

        yield Label("R refresh  ESC back", id="hint-bar")

    def on_mount(self):
        self._refresh_data()
        self.set_interval(3, self._refresh_data)

    def _refresh_data(self):
        if not PSUTIL_OK:
            self.query_one("#cpu-val", Label).update("psutil not installed")
            self.query_one("#mem-val", Label).update("Run: pkg install python-psutil")
            self.query_one("#disk-val", Label).update("Then restart rxos")
            self.query_one("#net-val", Label).update("N/A")
            return
        # CPU
        cpu_pct = psutil.cpu_percent(interval=None)
        cores = psutil.cpu_count(logical=False)
        logical = psutil.cpu_count(logical=True)
        try:
            freq = psutil.cpu_freq()
            freq_str = f"{freq.current:.0f} MHz" if freq else "N/A"
        except Exception:
            freq_str = "N/A"

        self.query_one("#cpu-val", Label).update(f"{cpu_pct:.1f}%")
        self.query_one("#cpu-cores", Label).update(f"{cores} physical / {logical} logical")
        self.query_one("#cpu-freq", Label).update(freq_str)
        self.query_one("#cpu-bar", ProgressBar).progress = cpu_pct

        # Memory
        mem = psutil.virtual_memory()
        used_gb = mem.used / (1024**3)
        total_gb = mem.total / (1024**3)
        self.query_one("#mem-val", Label).update(
            f"{used_gb:.1f} GB / {total_gb:.1f} GB  ({mem.percent}%)"
        )
        self.query_one("#mem-bar", ProgressBar).progress = mem.percent

        # Disk
        disk = psutil.disk_usage("/")
        du = disk.used / (1024**3)
        dt = disk.total / (1024**3)
        self.query_one("#disk-val", Label).update(
            f"{du:.1f} GB / {dt:.1f} GB  ({disk.percent}%)"
        )
        self.query_one("#disk-bar", ProgressBar).progress = disk.percent

        # Network
        net = psutil.net_io_counters()
        sent_mb = net.bytes_sent / (1024**2)
        recv_mb = net.bytes_recv / (1024**2)
        self.query_one("#net-val", Label).update(
            f"↑ {sent_mb:.1f} MB  ↓ {recv_mb:.1f} MB"
        )

        # Top 5 processes
        try:
            procs = sorted(
                psutil.process_iter(["name", "cpu_percent", "memory_percent"]),
                key=lambda p: p.info.get("cpu_percent") or 0,
                reverse=True
            )[:5]
            lines = []
            for p in procs:
                name = (p.info.get("name") or "?")[:22]
                cpu = p.info.get("cpu_percent") or 0
                mem = p.info.get("memory_percent") or 0
                lines.append(f"  {name:<22} CPU:{cpu:5.1f}%  MEM:{mem:4.1f}%")
            self.query_one("#proc-list", Label).update("\n".join(lines))
        except Exception:
            pass

        from rxos import storage
        self.query_one("#update-label", Label).update(
            f"  Last updated: {storage.now_str()}"
        )

    def action_refresh(self):
        self._refresh_data()
        self.notify("Refreshed!", title="SysMon")
