from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Label, Input, Button
from textual.containers import Vertical, Horizontal, Grid, ScrollableContainer
from textual.binding import Binding
from textual import on
import math

BUTTONS = [
    ["C", "(", ")", "⌫"],
    ["7", "8", "9", "÷"],
    ["4", "5", "6", "×"],
    ["1", "2", "3", "−"],
    ["±", "0", ".", "+"],
    ["√", "x²", "π",  "="],
]

MAP = {"÷": "/", "×": "*", "−": "-", "x²": "**2", "√": "sqrt(", "π": "str(math.pi)"}

class CalculatorScreen(Screen):
    BINDINGS = [
        Binding("escape", "app.pop_screen", "Back"),
        Binding("enter", "calculate", "="),
    ]

    CSS = """
    CalculatorScreen { background: #0d0d14; }
    #calc-header {
        height: 3; background: #13131f;
        color: #6c63ff; text-style: bold;
        content-align: center middle;
        border-bottom: solid #2a2a4a;
    }
    #history-area {
        height: 10; background: #0a0a10;
        border-bottom: solid #2a2a4a;
        padding: 0 2;
    }
    #history-area Label { color: #5a5a7a; }
    #display {
        height: 5; background: #13131f;
        color: #e2e2f0; text-style: bold;
        content-align: right middle;
        padding: 0 2;
        border-bottom: solid #2a2a4a;
        font-size: 2;
    }
    #expr-input {
        height: 3; background: #1a1a2e;
        color: #e2e2f0; border: none;
        padding: 0 2;
        border-bottom: solid #2a2a4a;
    }
    #btn-grid {
        height: 1fr;
        grid-size: 4;
        grid-gutter: 1;
        padding: 1;
    }
    Button {
        background: #13131f;
        color: #e2e2f0;
        border: solid #2a2a4a;
        height: 3;
    }
    Button:hover { background: #1a1a2e; border: solid #6c63ff; }
    Button.op { color: #6c63ff; text-style: bold; }
    Button.eq { background: #6c63ff; color: #ffffff; text-style: bold; }
    Button.eq:hover { background: #7c72ff; }
    Button.fn { color: #00d4aa; }
    #hint-bar { height: 1; background: #13131f; color: #5a5a7a; padding: 0 2; }
    """

    def __init__(self):
        super().__init__()
        self._expr = ""
        self._history = []

    def compose(self) -> ComposeResult:
        yield Label(" 🧮 CALCULATOR", id="calc-header")
        with ScrollableContainer(id="history-area"):
            yield Label("History will appear here...", id="history-label")
        yield Label("0", id="display")
        yield Input(placeholder="Type expression or use buttons...", id="expr-input")
        with Grid(id="btn-grid"):
            for row in BUTTONS:
                for btn in row:
                    classes = ""
                    if btn in ["÷", "×", "−", "+"]:
                        classes = "op"
                    elif btn == "=":
                        classes = "eq"
                    elif btn in ["√", "x²", "π", "±"]:
                        classes = "fn"
                    yield Button(btn, id=f"btn-{btn}", classes=classes)
        yield Label("Type expr + Enter, or click buttons | ESC back", id="hint-bar")

    @on(Button.Pressed)
    def on_btn_pressed(self, event: Button.Pressed):
        btn_id = event.button.id
        if not btn_id:
            return
        label = event.button.label.plain.strip()

        if label == "C":
            self._expr = ""
        elif label == "⌫":
            self._expr = self._expr[:-1]
        elif label == "=":
            self._do_calculate()
            return
        elif label == "±":
            if self._expr.startswith("-"):
                self._expr = self._expr[1:]
            else:
                self._expr = "-" + self._expr
        elif label == "√":
            self._expr += "sqrt("
        elif label == "x²":
            self._expr += "**2"
        elif label == "π":
            self._expr += "3.14159265"
        elif label in MAP:
            self._expr += MAP[label]
        else:
            self._expr += label

        self.query_one("#display", Label).update(self._expr or "0")
        self.query_one("#expr-input", Input).value = self._expr

    @on(Input.Changed, "#expr-input")
    def on_expr_changed(self, event: Input.Changed):
        self._expr = event.value
        self.query_one("#display", Label).update(self._expr or "0")

    def action_calculate(self):
        inp = self.query_one("#expr-input", Input)
        self._expr = inp.value
        self._do_calculate()

    def _do_calculate(self):
        expr = self._expr.strip()
        if not expr:
            return
        try:
            safe_globals = {
                "__builtins__": {},
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "log2": math.log2,
                "log10": math.log10,
                "abs": abs,
                "round": round,
                "floor": math.floor,
                "ceil": math.ceil,
                "pi": math.pi,
                "e": math.e,
                "math": math,
            }
            result = eval(expr, safe_globals)
            if isinstance(result, float) and result == int(result):
                result = int(result)
            result_str = str(result)
            self._history.append(f"{expr} = {result_str}")
            if len(self._history) > 20:
                self._history = self._history[-20:]
            hist_text = "\n".join(reversed(self._history))
            self.query_one("#history-label", Label).update(hist_text)
            self.query_one("#display", Label).update(result_str)
            self._expr = result_str
            self.query_one("#expr-input", Input).value = result_str
        except Exception as ex:
            self.query_one("#display", Label).update(f"Error: {ex}")
            self._expr = ""
            self.query_one("#expr-input", Input).value = ""
