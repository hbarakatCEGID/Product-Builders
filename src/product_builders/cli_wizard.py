"""Interactive quick-start / installation wizard (phased onboarding).

Maps to the product roadmap phases:
  1 — Foundation (install, paths, env)
  2 — Core analysis (heuristic profile; Phase 2 analyzers)
  3 — Rules & governance (Phase 3 generators)
  4 — Extended profile (Phase 4 dimensions; included in analyze)
  5 — Lifecycle (validate, drift, metrics, feedback)
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from product_builders.config import Config


def run_wizard(
    ctx: click.Context,
    *,
    console: Console,
    phase: int | None,
    repo: str | None,
    name: str | None,
    profile: str | None,
    run_validate: bool | None,
    heuristic_only: bool,
    yes: bool,
) -> None:
    config: Config = ctx.obj["config"]
    last_repo: str | None = repo
    last_name: str | None = name

    phases = [phase] if phase is not None else [1, 2, 3, 4, 5]

    for p in phases:
        if not yes and phase is None and p > 1:
            if not click.confirm(f"\nContinue to phase {p}?", default=True):
                console.print("[dim]Stopped by user.[/dim]")
                break

        if p == 1:
            _phase_1_foundation(console, config, assume_yes=yes)
        elif p == 2:
            last_repo, last_name = _phase_2_analyze(
                ctx,
                console,
                last_repo,
                last_name,
                heuristic_only=heuristic_only,
                assume_yes=yes,
            )
        elif p == 3:
            last_name = _phase_3_generate(
                ctx,
                console,
                last_name,
                profile=profile,
                run_validate=run_validate,
                assume_yes=yes,
            )
        elif p == 4:
            _phase_4_extended(console, last_name)
        elif p == 5:
            _phase_5_lifecycle(ctx, console, last_name, last_repo, assume_yes=yes)

    console.print(
        "\n[bold green]Wizard finished.[/bold green] "
        "See README [bold]Quick start by phase[/bold] for copy-paste commands.\n"
    )


def _phase_1_foundation(console: Console, config: Config, *, assume_yes: bool) -> None:
    console.print(
        Panel.fit(
            "[bold]Phase 1 — Foundation[/bold]\n"
            "Install the tool, verify Python, and know where profiles live.",
            title="Installation",
        )
    )
    ok_py = sys.version_info >= (3, 11)
    console.print(
        f"  Python: [cyan]{sys.version.split()[0]}[/cyan] "
        f"({'[green]ok[/green]' if ok_py else '[red]need 3.11+[/red]'})"
    )
    if not ok_py:
        console.print("  [yellow]Install Python 3.11+ before continuing.[/yellow]")

    profiles = config.profiles_dir.resolve()
    standards = config.company_standards_dir.resolve()
    console.print(f"  [bold]PB_PROFILES_DIR[/bold] = {profiles}")
    console.print(f"  [bold]PB_STANDARDS_DIR[/bold]  = {standards}")

    t = Table(show_header=False, box=None)
    t.add_row("  [dim]Install (CLI + web + AST + dev)[/dim]", "[cyan]pip install -e .[/cyan]")
    console.print(t)

    if not profiles.is_dir():
        if assume_yes or click.confirm(f"Create profiles directory?\n  {profiles}", default=True):
            profiles.mkdir(parents=True, exist_ok=True)
            console.print(f"  [green]Created[/green] {profiles}")
    else:
        console.print("  [dim]Profiles directory exists.[/dim]")


def _phase_2_analyze(
    ctx: click.Context,
    console: Console,
    repo: str | None,
    name: str | None,
    *,
    heuristic_only: bool,
    assume_yes: bool,
) -> tuple[str | None, str | None]:
    console.print(
        Panel.fit(
            "[bold]Phase 2 — Core analysis[/bold]\n"
            "Runs offline heuristic analyzers (stack, DB, auth, errors, git, ...) "
            "and writes [cyan]analysis.json[/cyan] under your product profile.",
            title="Analyze",
        )
    )

    from product_builders.cli import analyze

    if not repo:
        repo = click.prompt(
            "Path to repository to analyze",
            type=click.Path(exists=True, file_okay=False, path_type=str),
        )
    if not name:
        name = click.prompt("Product name (profile folder name)", type=str)

    if not assume_yes and not heuristic_only:
        if not click.confirm(
            "Include bootstrap meta-rule for Cursor deep analysis? (say No for --heuristic-only)",
            default=True,
        ):
            heuristic_only = True

    console.print(f"\n[bold]Running:[/bold] analyze [green]{name}[/green] ← {repo}\n")
    ctx.invoke(
        analyze,
        repo_path=repo,
        name=name,
        heuristic_only=heuristic_only,
        sub_project=None,
    )

    if not heuristic_only:
        from rich.panel import Panel

        console.print(
            Panel.fit(
                "[bold]Deep Analysis Workflow[/bold]\n\n"
                "1. Open the product repo in Cursor\n"
                "2. Tell Cursor: [cyan]run deep analysis[/cyan]\n"
                "3. Cursor follows the bootstrap rule (3 sequential steps)\n"
                "4. Cursor writes findings to [cyan]deep-analysis.yaml[/cyan]\n"
                f"5. Run: [cyan]product-builders ingest-deep --name {name} --repo {repo}[/cyan]\n"
                f"6. Run: [cyan]product-builders generate --name {name}[/cyan] to refresh rules",
                title="Next: Cursor Deep Analysis",
            )
        )

    return repo, name


def _phase_3_generate(
    ctx: click.Context,
    console: Console,
    name: str | None,
    *,
    profile: str | None,
    run_validate: bool | None,
    assume_yes: bool,
) -> str | None:
    console.print(
        Panel.fit(
            "[bold]Phase 3 — Rules & governance[/bold]\n"
            "Generates Cursor rules, hooks, permissions, scopes, onboarding, checklist.\n\n"
            "[dim]Tip:[/dim] Create [cyan]profiles/<name>/overrides.yaml[/cyan] before this step "
            "to correct any analysis fields (stack, DB type, etc.).",
            title="Generate",
        )
    )

    from product_builders.cli import generate

    if not name:
        name = click.prompt("Product name (same as analyze)", type=str)

    role = profile
    if role is None and not assume_yes:
        if click.confirm("Generate for a specific contributor role?", default=False):
            role = click.prompt(
                "Role alias (e.g. engineer, pm, designer)",
                type=str,
                default="",
            )
            role = role.strip() or None

    do_validate = run_validate
    if do_validate is None and not assume_yes:
        do_validate = click.confirm("Run structural validation after generate?", default=False)
    elif do_validate is None:
        do_validate = False

    console.print(f"\n[bold]Running:[/bold] generate [green]{name}[/green]\n")
    ctx.invoke(generate, name=name, role_alias=role, validate=do_validate)
    return name


def _phase_4_extended(console: Console, name: str | None) -> None:
    console.print(
        Panel.fit(
            "[bold]Phase 4 — Extended dimensions[/bold]\n"
            "Security, testing, CI/CD, design, API, i18n, performance, and more are "
            "already filled when you run [cyan]analyze[/cyan]. No separate install step.\n\n"
            "After large repo changes, re-run:\n"
            "  [cyan]product-builders analyze <repo> --name <product>[/cyan]",
            title="Extended analyzers",
        )
    )
    if name:
        console.print(f"  [dim]Current product:[/dim] [green]{name}[/green]")


def _phase_5_lifecycle(
    ctx: click.Context,
    console: Console,
    name: str | None,
    repo: str | None,
    *,
    assume_yes: bool,
) -> None:
    console.print(
        Panel.fit(
            "[bold]Phase 5 — Lifecycle[/bold]\n"
            "[cyan]generate --validate[/cyan] · [cyan]check-drift[/cyan] · "
            "[cyan]metrics[/cyan] · [cyan]feedback[/cyan]",
            title="Operations",
        )
    )
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_row(
        "validate",
        "product-builders generate -n NAME --validate",
    )
    t.add_row(
        "drift (git)",
        "product-builders check-drift -n NAME -r /path/to/repo",
    )
    t.add_row(
        "drift (full)",
        "product-builders check-drift -n NAME -r /path/to/repo --full",
    )
    t.add_row("metrics", "product-builders metrics -n NAME")
    t.add_row("feedback", 'product-builders feedback -n NAME -r RULE -i "..."')
    console.print(t)

    from product_builders.cli import check_drift

    if assume_yes and name and repo:
        console.print("\n[bold]Running check-drift[/bold] ([dim]-y[/dim] non-interactive)\n")
        ctx.invoke(check_drift, name=name, repo=repo, full=False)
    elif not assume_yes and not name:
        if click.confirm("Run check-drift now?", default=False):
            name = click.prompt("Product name", type=str)
            if not repo:
                repo = click.prompt(
                    "Repository path",
                    type=click.Path(exists=True, file_okay=False, path_type=str),
                )
            console.print()
            ctx.invoke(check_drift, name=name, repo=repo, full=False)
    elif not assume_yes and name and repo:
        if click.confirm("Run check-drift now?", default=False):
            console.print()
            ctx.invoke(check_drift, name=name, repo=repo, full=False)
