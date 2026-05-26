import typer
import os
import sys
import logging
import asyncio
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
from rich.console import Console
from rich.logging import RichHandler

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("beta_swarm")
console = Console()

app = typer.Typer(name="beta-swarm", help="βeta Swarm v3.1 CLI")

@app.command()
def init(project_name: str = typer.Argument(..., help="Name of the project to initialize")):
    """Initialize a new project environment."""
    console.print(f"[bold cyan]Initializing project: {project_name}...[/]")
    project_path = os.path.abspath(os.path.join("projects", project_name))
    os.makedirs(project_path, exist_ok=True)
    console.print(f"[bold green]Project created at: {project_path}[/]")

@app.command()
def run(
    project_name: str = typer.Argument(..., help="Project to run"),
    idea: str = typer.Option(None, "--idea", "-i", help="Initial prompt or idea"),
    resume: bool = typer.Option(False, "--resume", help="Resume an existing project run")
):
    """Run the autonomous swarm pipeline for a project."""
    from beta_swarm.orchestrator import WorkflowEngine
    
    project_path = os.path.abspath(os.path.join("projects", project_name))
    if not os.path.exists(project_path):
        console.print(f"[bold red]Error: Project {project_name} not found. Run 'init' first.[/]")
        raise typer.Exit(code=1)

    engine = WorkflowEngine(project_name, project_path)
    engine.register_stages()
    
    if resume:
        console.print(f"[bold magenta]Resuming swarm for {project_name}...[/]")
        asyncio.run(engine.execute({"idea": "resume"}))
    else:
        if not idea:
            idea = typer.prompt("What should the swarm build?")
        console.print(f"[bold magenta]Launching swarm for {project_name} with idea: '{idea}'...[/]")
        asyncio.run(engine.execute({"idea": idea}))

@app.command()
def summon(audio: Optional[str] = typer.Option(None, help="Audio file to use for the summon engine")):
    """Summon the swarm via audio or text trigger."""
    from beta_swarm.ui.terminal_ui import get_ui
    ui = get_ui()
    ui.show_logo()
    
    if audio:
        console.print(f"[bold cyan]Processing audio summon: {audio}...[/]")
        # Placeholder for whisper pipeline
        console.print("[yellow]Whisper pipeline offline. Falling back to text summon.[/]")
    
    ui.show_summon_ready()
    idea = typer.prompt("Summoning prompt")
    
    # Simple one-off run for the summon
    from beta_swarm.orchestrator import run_project
    run_project("SummonedProject", "SummonTask", {"idea": idea})

@app.command()
def diagnose():
    """Run the comprehensive system diagnostic."""
    import subprocess
    subprocess.run([sys.executable, "system_diagnostic.py"])

@app.command()
def register():
    """Register all agents in the KuzuDB brain."""
    from beta_swarm.agents.register_all import register_all
    register_all()

if __name__ == "__main__":
    app()
