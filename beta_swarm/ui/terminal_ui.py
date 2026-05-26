import os
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import print as rprint

console = Console()

class BetaSwarmUI:
    def show_logo(self):
        ascii_logo = """
        [cyan]██████╗ ███████╗████████╗ █████╗     ███████╗██╗    ██╗ █████╗ ██████╗ ███╗   ███╗[/]
        [cyan]██╔══██╗██╔════╝╚══██╔══╝██╔══██╗    ██╔════╝██║    ██║██╔══██╗██╔══██╗████╗ ████║[/]
        [magenta]██████╔╝█████╗     ██║   ███████║    ███████╗██║ █╗ ██║███████║██████╔╝██╔████╔██║[/]
        [magenta]██╔══██╗██╔══╝     ██║   ██╔══██║    ╚════██║██║███╗██║██╔══██║██╔══██╗██║╚██╔╝██║[/]
        [cyan]██████╔╝███████╗   ██║   ██║  ██║    ███████║╚███╔███╔╝██║  ██║██║  ██║██║ ╚═╝ ██║[/]
        [cyan]╚═════╝ ╚══════╝   ╚═╝   ╚═╝  ╚═╝    ╚══════╝ ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝[/]
                                [bold white]v3.1 Zero-Cost Autonomous Swarm[/]
        """
        console.print(ascii_logo)

    def show_agent_roster(self, agents):
        table = Table(title="[bold cyan]BETA SWARM AGENT ROSTER[/]", show_header=True, header_style="bold magenta")
        table.add_column("Category", style="dim")
        table.add_column("Agent ID", style="cyan")
        table.add_column("Status", justify="right")
        
        for category, roster in agents.items():
            for agent in roster:
                table.add_row(category, agent, "[green]Online[/]")
        console.print(table)

    def show_workflow_progress(self, stages):
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        ) as progress:
            for stage in stages:
                progress.add_task(description=f"[cyan]Executing {stage}...[/]", total=100)

    def show_summon_ready(self):
        console.print(Panel("[bold green]BETA SWARM IS READY. SUMMON ENGINE INITIALIZED.[/]", border_style="cyan"))

    def show_summon_result(self, result):
        console.print(Panel(f"[bold white]SUMMON RESULT:[/]\n[cyan]{result}[/]", border_style="magenta", title="Swarm Output"))

def get_ui():
    return BetaSwarmUI()
