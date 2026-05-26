import asyncio
from textual.app import App, ComposeResult
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, DataTable, ProgressBar, Log, Sparkline
from textual.reactive import reactive
from beta_swarm.dashboard.collector import SwarmCollector

class SwarmMetricCard(Static):
    """A JARVIS-style metric card with sparkline."""
    value = reactive(0.0)
    history = reactive([])

    def __init__(self, label: str, id: str):
        super().__init__(id=id)
        self.label = label

    def compose(self) -> ComposeResult:
        yield Static(self.label, classes="label")
        yield Static("0.0%", id="val_text")
        yield Sparkline(self.history, id="sparkline")

    def watch_value(self, value: float) -> None:
        self.query_one("#val_text", Static).update(f"{value:.1f}%")
        self.history = (self.history + [value])[-20:]
        self.query_one("#sparkline", Sparkline).data = self.history

class SystemVitals(Static):
    """Widget for system metrics."""
    def compose(self) -> ComposeResult:
        yield Static("SYSTEM VITALS", classes="title")
        yield SwarmMetricCard("CPU LOAD", id="cpu_card")
        yield SwarmMetricCard("RAM USAGE", id="ram_card")

    def update_metrics(self, cpu: float, ram: float):
        self.query_one("#cpu_card", SwarmMetricCard).value = cpu
        self.query_one("#ram_card", SwarmMetricCard).value = ram


class AgentFleet(Static):
    """Widget for agent statuses."""
    def compose(self) -> ComposeResult:
        yield Static("AGENT FLEET", classes="title")
        yield DataTable(id="agent_table")

    def on_mount(self) -> None:
        table = self.query_one("#agent_table", DataTable)
        table.add_columns("ID", "NAME", "STAGE", "STATUS")
        table.cursor_type = "row"

class SwarmDashboard(App):
    """JARVIS-style TUI for Beta Swarm."""
    
    CSS = """
    Screen {
        background: #050a0f;
    }
    
    .title {
        color: #00f2ff;
        text-align: center;
        background: #0a1929;
        border: solid #00f2ff;
        margin-bottom: 1;
    }
    
    #main_grid {
        grid-size: 2 2;
        grid-columns: 1fr 1fr;
        grid-rows: 1fr 1fr;
    }
    
    #log_panel {
        column-span: 2;
        height: 10;
        border: double #0077ff;
    }
    
    ProgressBar {
        color: #00f2ff;
    }
    
    DataTable {
        height: 1fr;
        border: solid rgba(0, 242, 255, 0.3);
    }
    """

    TITLE = "BETA SWARM // JARVIS HUD"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self):
        super().__init__()
        self.collector = SwarmCollector()

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main_grid"):
            yield SystemVitals(id="vitals")
            yield AgentFleet(id="fleet")
            with Vertical(id="log_panel"):
                yield Static("EVENT STREAM", classes="title")
                yield Log(id="swarm_logs")
        yield Footer()

    def on_mount(self) -> None:
        self.update_timer = self.set_interval(2, self.update_data)
        self.query_one("#swarm_logs", Log).write_line("Dashboard Engine Started.")

    async def update_data(self) -> None:
        """Fetch data from collector and update widgets."""
        snapshot = self.collector.get_full_snapshot()
        
        # Update Vitals
        vitals = self.query_one("#vitals", SystemVitals)
        vitals.update_metrics(snapshot["system"]["cpu_percent"], snapshot["system"]["ram_percent"])
        
        # Update Table
        table = self.query_one("#agent_table", DataTable)
        table.clear()
        for agent in snapshot["agents"]:
            table.add_row(agent["id"], agent["name"], agent["stage"], agent["status"])
            
        self.query_one("#swarm_logs", Log).write_line(f"Snapshot sync @ {snapshot['timestamp']}")

if __name__ == "__main__":
    app = SwarmDashboard()
    app.run()
