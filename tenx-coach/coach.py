#!/usr/bin/env python3
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

import store
import agent

app = typer.Typer(
    name="coach",
    help="TenX Coach — AI-powered idea validation pipeline.",
    no_args_is_help=True,
)
idea_app = typer.Typer(help="Manage your ideas.", no_args_is_help=True)
app.add_typer(idea_app, name="idea")

console = Console()


@idea_app.command("add")
def idea_add(text: str = typer.Argument(..., help="Your idea in one sentence.")):
    """Add a new idea to your pipeline."""
    idea_id = store.add_idea(text)
    console.print(f"[green]Added idea[/green] [bold]{idea_id}[/bold]: {text}")
    console.print(f"\n[dim]Validate it with:[/dim] coach idea validate {idea_id}")


@idea_app.command("list")
def idea_list():
    """List all ideas in your pipeline."""
    ideas = store.list_ideas()
    if not ideas:
        console.print("[yellow]No ideas yet. Add one with:[/yellow] coach idea add \"your idea\"")
        return

    table = Table(title="Your Idea Pipeline", show_lines=True)
    table.add_column("ID", style="dim", width=10)
    table.add_column("Idea", style="white")
    table.add_column("Validations", justify="center", width=12)
    table.add_column("Created", style="dim", width=20)

    for idea in ideas:
        n_validations = len(idea["validations"])
        validation_str = (
            f"[green]{n_validations}[/green]" if n_validations > 0 else "[dim]0[/dim]"
        )
        created = idea["created_at"][:10]
        table.add_row(idea["id"], idea["text"], validation_str, created)

    console.print(table)


@idea_app.command("validate")
def idea_validate(idea_id: str = typer.Argument(..., help="Idea ID to validate.")):
    """Run an interactive validation session for an idea."""
    idea = store.get_idea(idea_id)
    if not idea:
        console.print(f"[red]Idea {idea_id!r} not found. Run[/red] coach idea list [red]to see your ideas.[/red]")
        raise typer.Exit(1)

    result = agent.run_validation_session(idea["text"])
    store.save_validation(idea_id, result)
    console.print(f"\n[green]Validation saved for idea {idea_id}.[/green]")


@idea_app.command("show")
def idea_show(idea_id: str = typer.Argument(..., help="Idea ID to show.")):
    """Show an idea and its validation history."""
    idea = store.get_idea(idea_id)
    if not idea:
        console.print(f"[red]Idea {idea_id!r} not found.[/red]")
        raise typer.Exit(1)

    console.print(
        Panel(
            f"[bold]{idea['text']}[/bold]\n\n"
            f"[dim]Created:[/dim] {idea['created_at'][:10]}\n"
            f"[dim]Validations:[/dim] {len(idea['validations'])}",
            title=f"Idea [bold]{idea_id}[/bold]",
            border_style="cyan",
        )
    )

    for i, v in enumerate(idea["validations"], 1):
        console.print(f"\n[bold cyan]Validation #{i}[/bold cyan] ({v.get('saved_at', '')[:10]})")
        if v.get("verdict"):
            console.print(v["verdict"])


@idea_app.command("compare")
def idea_compare():
    """Ask the coach to compare all your ideas and recommend which to pursue."""
    ideas = store.list_ideas()
    if len(ideas) < 2:
        console.print("[yellow]Add at least 2 ideas before comparing.[/yellow]")
        raise typer.Exit(1)

    agent.run_compare_session(ideas)


@app.command()
def sprint():
    """Run a guided Clarity Sprint to pick your best idea (interactive)."""
    console.print(
        Panel(
            "[bold]Clarity Sprint[/bold]\n\n"
            "This will walk you through the 3-question filter for each of your ideas "
            "and help you commit to one worth pursuing.\n\n"
            "[dim]You need at least 1 idea added. Run [bold]coach idea add[/bold] first.[/dim]",
            border_style="magenta",
        )
    )
    ideas = store.list_ideas()
    if not ideas:
        console.print("[yellow]No ideas yet. Add one with:[/yellow] coach idea add \"your idea\"")
        raise typer.Exit(1)

    for idea in ideas:
        console.print(f"\n[bold]Validating:[/bold] {idea['text']} (ID: {idea['id']})")
        result = agent.run_validation_session(idea["text"])
        store.save_validation(idea["id"], result)

    console.print("\n[bold magenta]All ideas validated. Running comparison...[/bold magenta]\n")
    agent.run_compare_session(store.list_ideas())


if __name__ == "__main__":
    app()
