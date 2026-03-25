"""CLI entry point for Product Builders.

Commands:
  analyze       Run heuristic analysis on a product repo
  generate      Regenerate rules from a cached product profile
  setup         Configure local governance for a contributor role
  export        Export rules/hooks/permissions to a product repo
  list          List all analyzed products
  bulk-analyze  Analyze multiple products from manifest or monorepo
  check-drift   Check if rules are stale vs. the codebase
  metrics       Show recent metrics events for a product
  feedback      Record feedback on a rule's accuracy
  wizard        Interactive quick start by roadmap phase (foundation → lifecycle)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import click
from pydantic import ValidationError
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table

from product_builders import __version__
from product_builders.config import Config, validate_product_name
from product_builders.models.heuristic_dimensions import HEURISTIC_PROFILE_FIELDS
from product_builders.models.profile import ProductMetadata, ProductProfile
from product_builders.profiles.base import get_profile, resolve_role

console = Console()

# Valid ProductProfile fields that analyzers can populate
_VALID_DIMENSIONS = frozenset(
    ProductProfile.model_fields.keys()
) - {"metadata", "scopes", "architecture_deep", "domain_model_deep", "implicit_conventions_deep"}


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        handlers=[RichHandler(console=console, show_path=False, markup=True)],
    )


@click.group()
@click.version_option(version=__version__, prog_name="product-builders")
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
@click.pass_context
def main(ctx: click.Context, verbose: bool) -> None:
    """Product Builders — Specialized Agent Generator.

    Analyze codebases and generate Cursor rules, governance, and onboarding guides.
    """
    _setup_logging(verbose)
    ctx.ensure_object(dict)
    ctx.obj["config"] = Config()
    ctx.obj["verbose"] = verbose


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------

@main.command()
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option("--name", "-n", required=True, help="Product name (used as profile directory name).")
@click.option("--heuristic-only", is_flag=True, help="Skip deep analysis bootstrap generation.")
@click.option("--sub-project", default=None, help="Relative path to sub-project in a monorepo.")
@click.pass_context
def analyze(
    ctx: click.Context,
    repo_path: str,
    name: str,
    heuristic_only: bool,
    sub_project: str | None,
) -> None:
    """Analyze a product codebase and generate a product profile.

    Phase 1: Runs heuristic analyzers (fully offline).
    Phase 2: Generates bootstrap meta-rule for Cursor deep analysis (unless --heuristic-only).
    """
    config: Config = ctx.obj["config"]
    repo = Path(repo_path)

    try:
        validate_product_name(name)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="'--name'") from e

    # Validate sub-project stays within the repo
    if sub_project:
        analysis_root = (repo / sub_project).resolve()
        if not analysis_root.is_relative_to(repo.resolve()):
            raise click.BadParameter(
                f"Sub-project path escapes repo root: {sub_project}",
                param_hint="'--sub-project'",
            )
        if not analysis_root.exists():
            raise click.BadParameter(
                f"Sub-project path does not exist: {analysis_root}",
                param_hint="'--sub-project'",
            )
    else:
        analysis_root = repo

    console.print(f"\n[bold blue]Analyzing[/bold blue] [green]{name}[/green] at {analysis_root}\n")

    profile = ProductProfile(
        metadata=ProductMetadata(
            name=name,
            repo_path=str(repo),
            sub_project=sub_project,
        ),
    )

    # Run all registered analyzers
    from product_builders.analyzers import registry

    analyzer_instances = registry.get_all_analyzers()
    if not analyzer_instances:
        console.print("[yellow]No analyzers registered yet. Profile will have default values.[/yellow]")
    else:
        results_table = Table(title="Analysis Results", show_lines=True)
        results_table.add_column("Analyzer", style="cyan")
        results_table.add_column("Status", style="bold")
        results_table.add_column("Details")

        for analyzer in analyzer_instances:
            if analyzer.dimension not in HEURISTIC_PROFILE_FIELDS:
                logging.getLogger(__name__).warning(
                    "Analyzer '%s' has unknown dimension '%s', skipping",
                    analyzer.name, analyzer.dimension,
                )
                continue

            result = analyzer.safe_analyze(analysis_root)
            setattr(profile, analyzer.dimension, result)

            status_style = {
                "success": "green",
                "partial": "yellow",
                "error": "red",
                "skipped": "dim",
            }.get(result.status.value, "white")

            details = result.error_message or ""
            results_table.add_row(
                analyzer.name,
                f"[{status_style}]{result.status.value}[/{status_style}]",
                details,
            )

        console.print(results_table)

    # Auto-detect scopes from project structure
    from product_builders.generators.scopes import generate_scope_config, save_scopes_yaml

    profile.scopes = generate_scope_config(profile, analysis_root)
    console.print(f"\n[green]Detected {len(profile.scopes.zones)} zones[/green]")

    # Record git HEAD for drift detection (repository root, not sub-project)
    from product_builders.gitutil import get_git_head_sha

    git_sha = get_git_head_sha(repo)
    if git_sha:
        profile.metadata.last_commit_sha = git_sha
        console.print(f"[dim]Recorded git HEAD {git_sha[:12]}… for drift checks[/dim]")

    # Save profile
    output_path = config.get_analysis_path(name)
    profile.save(output_path)
    console.print(f"[green]Profile saved:[/green] {output_path}")

    # Save scopes.yaml alongside the profile
    scopes_path = config.get_product_dir(name) / "scopes.yaml"
    save_scopes_yaml(profile.scopes, scopes_path)
    console.print(f"[green]Scopes saved:[/green] {scopes_path}")

    if not heuristic_only:
        console.print(
            "\n[bold]Next step:[/bold] Open the product repo in Cursor and run the "
            "4-step deep analysis using the generated bootstrap rule."
        )
    else:
        console.print("\n[dim]Deep analysis skipped (--heuristic-only).[/dim]")


# ---------------------------------------------------------------------------
# generate
# ---------------------------------------------------------------------------

@main.command()
@click.option("--name", "-n", required=True, help="Product name.")
@click.option("--profile", "-p", "role_alias", default=None, help="Contributor role (pm, designer, engineer, etc.).")
@click.option("--validate", is_flag=True, help="Run structural validation after generation.")
@click.pass_context
def generate(ctx: click.Context, name: str, role_alias: str | None, validate: bool) -> None:
    """Regenerate Cursor rules and governance from a cached product profile."""
    config: Config = ctx.obj["config"]

    try:
        profile_path = config.get_analysis_path(name)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="'--name'") from e

    if not profile_path.exists():
        raise click.ClickException(f"No profile found for '{name}'. Run 'analyze' first.")

    profile = ProductProfile.load(profile_path)

    overrides = config.load_overrides(name)
    if overrides:
        from product_builders.profiles.overrides import merge_overrides
        profile = merge_overrides(profile, overrides)
        console.print("[dim]Applied overrides from overrides.yaml[/dim]")

    role = None
    if role_alias:
        try:
            role = resolve_role(role_alias)
        except ValueError as e:
            raise click.BadParameter(str(e), param_hint="'--profile'") from e

    # Auto-detect scopes if not present
    if not profile.scopes.zones and profile.metadata.repo_path:
        from product_builders.generators.scopes import generate_scope_config
        repo_root = Path(profile.metadata.repo_path)
        if repo_root.is_dir():
            profile.scopes = generate_scope_config(profile, repo_root)

    console.print(f"\n[bold blue]Generating[/bold blue] rules for [green]{name}[/green]")
    if role:
        console.print(f"  Contributor profile: [cyan]{get_profile(role).display_name}[/cyan]")

    from product_builders.generators import registry as gen_registry
    from product_builders.generators.cursor_rules import CursorRulesGenerator

    company_standards = config.load_company_standards()
    if company_standards:
        console.print(f"  Loaded {len(company_standards)} company standards: {', '.join(company_standards.keys())}")

    generators = gen_registry.get_all_generators()
    output_dir = config.get_product_dir(name)

    all_files: list[Path] = []
    for gen in generators:
        if isinstance(gen, CursorRulesGenerator) and company_standards:
            gen.set_company_standards(company_standards)
        files = gen.generate(profile, output_dir, role=role)
        all_files.extend(files)

    if all_files:
        console.print(f"\n[green]Generated {len(all_files)} files in {output_dir}[/green]")
        for f in all_files:
            console.print(f"  {f.relative_to(output_dir)}")
    else:
        console.print("[yellow]No generators registered yet.[/yellow]")

    if validate:
        console.print("\n[bold]Running structural validation...[/bold]")
        from product_builders.metrics import record_event
        from product_builders.validation import validate_product_profile_dir

        report = validate_product_profile_dir(output_dir)
        for w in report.warnings:
            console.print(f"  [yellow]⚠[/yellow] {w}")
        for err in report.errors:
            console.print(f"  [red]✗[/red] {err}")
        if report.ok:
            console.print("[green]Validation passed (no errors).[/green]")
            record_event(output_dir, "validate_ok", errors=0, warnings=len(report.warnings))
        else:
            console.print(f"[red]Validation failed with {len(report.errors)} error(s).[/red]")
            record_event(
                output_dir,
                "validate_failed",
                errors=len(report.errors),
                warnings=len(report.warnings),
            )
            raise click.ClickException("Structural validation failed.")


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------

@main.command()
@click.option("--name", "-n", required=True, help="Product name.")
@click.option("--profile", "-p", "role_alias", required=True, help="Contributor role (pm, designer, engineer, qa, technical-pm).")
@click.pass_context
def setup(ctx: click.Context, name: str, role_alias: str) -> None:
    """Configure local governance for a contributor role.

    Reads the product profile and scopes, then generates:
    - .cursor/rules/ — role-specific Cursor rules
    - .cursor/hooks.json — smart blocking (Layer 2)
    - .cursor/cli.json — hard filesystem deny (Layer 3)
    - .cursor/contributor-profile.json — local role metadata
    """
    config: Config = ctx.obj["config"]

    try:
        role = resolve_role(role_alias)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="'--profile'") from e

    profile_def = get_profile(role)

    try:
        profile_path = config.get_analysis_path(name)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="'--name'") from e

    if not profile_path.exists():
        raise click.ClickException(
            f"No profile found for '{name}'. Run 'analyze' first.\n"
            "  product-builders analyze /path/to/repo --name <product>"
        )

    profile = ProductProfile.load(profile_path)
    cwd = Path.cwd()
    cursor_dir = cwd / ".cursor"

    console.print(f"\n[bold blue]Setting up[/bold blue] [cyan]{profile_def.display_name}[/cyan] profile for [green]{name}[/green]\n")

    # Write contributor profile metadata
    cursor_dir.mkdir(parents=True, exist_ok=True)
    contributor_profile_path = cursor_dir / "contributor-profile.json"
    contributor_profile_path.write_text(
        json.dumps(
            {
                "role": role.value,
                "display_name": profile_def.display_name,
                "install_scope_hooks": profile_def.install_scope_hooks,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    console.print(f"  [green]Wrote[/green] {contributor_profile_path.relative_to(cwd)}")

    # Auto-detect scopes if not already in profile
    if not profile.scopes.zones:
        from product_builders.generators.scopes import generate_scope_config
        profile.scopes = generate_scope_config(profile, cwd)
        console.print(f"  [green]Auto-detected[/green] {len(profile.scopes.zones)} zones")

    # Generate all 3 governance layers
    from product_builders.generators import registry as gen_registry
    from product_builders.generators.cursor_rules import CursorRulesGenerator

    company_standards = config.load_company_standards()

    all_files: list[Path] = []
    for gen in gen_registry.get_all_generators():
        if isinstance(gen, CursorRulesGenerator) and company_standards:
            gen.set_company_standards(company_standards)
        files = gen.generate(profile, cwd, role=role)
        all_files.extend(files)

    if all_files:
        console.print(f"\n[green]Generated {len(all_files)} files:[/green]")
        for f in all_files:
            try:
                console.print(f"  {f.relative_to(cwd)}")
            except ValueError:
                console.print(f"  {f}")

    console.print(f"\n[green]Setup complete.[/green] Profile: [bold]{profile_def.display_name}[/bold]")


# ---------------------------------------------------------------------------
# export
# ---------------------------------------------------------------------------

@main.command()
@click.option("--name", "-n", required=True, help="Product name.")
@click.option("--target", "-t", required=True, type=click.Path(exists=True, file_okay=False, resolve_path=True), help="Target product repo path.")
@click.option("--profile", "-p", "role_alias", default=None, help="Contributor role for profile-specific export.")
@click.pass_context
def export(ctx: click.Context, name: str, target: str, role_alias: str | None) -> None:
    """Export generated rules, hooks, and scopes to a product repo."""
    config: Config = ctx.obj["config"]
    target_path = Path(target)

    try:
        product_dir = config.get_product_dir(name)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="'--name'") from e

    if not product_dir.exists():
        raise click.ClickException(f"No profile found for '{name}'. Run 'analyze' first.")

    console.print(f"\n[bold blue]Exporting[/bold blue] [green]{name}[/green] → {target_path}\n")

    import shutil

    exported: list[str] = []

    # Scopes
    src_scopes = product_dir / "scopes.yaml"
    if src_scopes.exists():
        shutil.copy2(src_scopes, target_path / "scopes.yaml")
        exported.append("scopes.yaml")

    # Cursor rules
    src_rules = product_dir / ".cursor" / "rules"
    if src_rules.exists():
        dst_rules = target_path / ".cursor" / "rules"
        dst_rules.mkdir(parents=True, exist_ok=True)
        for rule_file in src_rules.glob("*.mdc"):
            shutil.copy2(rule_file, dst_rules / rule_file.name)
            exported.append(f".cursor/rules/{rule_file.name}")

    # Hooks.json
    src_hooks = product_dir / ".cursor" / "hooks.json"
    if src_hooks.exists():
        dst_hooks = target_path / ".cursor" / "hooks.json"
        dst_hooks.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_hooks, dst_hooks)
        exported.append(".cursor/hooks.json")

    # cli.json
    src_cli = product_dir / ".cursor" / "cli.json"
    if src_cli.exists():
        dst_cli = target_path / ".cursor" / "cli.json"
        dst_cli.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_cli, dst_cli)
        exported.append(".cursor/cli.json")

    # Onboarding docs
    src_docs = product_dir / "docs"
    if src_docs.exists():
        dst_docs = target_path / "docs"
        dst_docs.mkdir(parents=True, exist_ok=True)
        for doc_file in src_docs.glob("*.md"):
            shutil.copy2(doc_file, dst_docs / doc_file.name)
            exported.append(f"docs/{doc_file.name}")

    if exported:
        console.print(f"[green]Exported {len(exported)} files:[/green]")
        for f in exported:
            console.print(f"  {f}")
    else:
        console.print("[yellow]No files to export. Run 'generate' first.[/yellow]")


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

@main.command(name="list")
@click.pass_context
def list_products(ctx: click.Context) -> None:
    """List all analyzed products."""
    config: Config = ctx.obj["config"]
    products = config.list_products()

    if not products:
        console.print("[yellow]No products analyzed yet.[/yellow]")
        return

    table = Table(title="Analyzed Products")
    table.add_column("Product", style="cyan")
    table.add_column("Analyzed", style="green")
    table.add_column("Primary Language")
    table.add_column("Framework")

    log = logging.getLogger(__name__)
    for name in products:
        try:
            profile = ProductProfile.load(config.get_analysis_path(name))
            table.add_row(
                name,
                str(profile.metadata.analysis_timestamp.strftime("%Y-%m-%d %H:%M")),
                profile.tech_stack.primary_language or "—",
                ", ".join(f.name for f in profile.tech_stack.frameworks[:3]) or "—",
            )
        except (FileNotFoundError, OSError, json.JSONDecodeError, ValidationError) as e:
            log.debug("list: could not load profile for %r: %s", name, e, exc_info=True)
            table.add_row(name, "?", "?", "?")

    console.print(table)


# ---------------------------------------------------------------------------
# bulk-analyze
# ---------------------------------------------------------------------------

@main.command(name="bulk-analyze")
@click.option("--manifest", type=click.Path(exists=True, resolve_path=True), help="YAML manifest listing products to analyze.")
@click.option("--monorepo", type=click.Path(exists=True, file_okay=False, resolve_path=True), help="Path to monorepo (auto-discovers sub-projects).")
@click.pass_context
def bulk_analyze(ctx: click.Context, manifest: str | None, monorepo: str | None) -> None:
    """Analyze multiple products from a manifest or monorepo."""
    if not manifest and not monorepo:
        raise click.UsageError("Provide either --manifest or --monorepo.")

    if manifest and monorepo:
        raise click.UsageError("Provide --manifest or --monorepo, not both.")

    if manifest:
        import yaml

        manifest_data = yaml.safe_load(Path(manifest).read_text(encoding="utf-8"))
        if not isinstance(manifest_data, dict):
            raise click.ClickException("Invalid manifest: expected a YAML mapping with a 'products' key.")

        products = manifest_data.get("products", [])
        if not isinstance(products, list):
            raise click.ClickException("Invalid manifest: 'products' must be a list.")

        console.print(f"[bold blue]Bulk analyzing {len(products)} products from manifest[/bold blue]\n")
        log = logging.getLogger(__name__)
        for product in products:
            if not isinstance(product, dict):
                log.warning(
                    "bulk-analyze: skipping manifest entry (expected mapping, got %s)",
                    type(product).__name__,
                )
                continue
            product_name = product.get("name")
            product_path = product.get("path")
            if product_name and product_path:
                ctx.invoke(analyze, repo_path=product_path, name=product_name, heuristic_only=False, sub_project=None)
            else:
                log.warning(
                    "bulk-analyze: skipping manifest entry (missing name or path): %r",
                    product,
                )

    if monorepo:
        monorepo_path = Path(monorepo)
        console.print(f"[bold blue]Auto-discovering sub-projects in {monorepo_path}[/bold blue]\n")

        markers = ["lerna.json", "pnpm-workspace.yaml", "nx.json", "turbo.json"]
        found_marker = None
        for marker in markers:
            if (monorepo_path / marker).exists():
                found_marker = marker
                break

        if found_marker:
            console.print(f"  Detected monorepo marker: [cyan]{found_marker}[/cyan]")

        sub_projects: list[Path] = []
        for pkg_json in monorepo_path.glob("*/package.json"):
            sub_projects.append(pkg_json.parent)
        for pkg_json in monorepo_path.glob("*/*/package.json"):
            if pkg_json.parent not in sub_projects:
                sub_projects.append(pkg_json.parent)

        if sub_projects:
            console.print(f"  Found {len(sub_projects)} sub-projects\n")
            for sp in sorted(sub_projects):
                sp_name = sp.relative_to(monorepo_path).as_posix().replace("/", "--")
                ctx.invoke(
                    analyze,
                    repo_path=str(monorepo_path),
                    name=sp_name,
                    heuristic_only=False,
                    sub_project=str(sp.relative_to(monorepo_path)),
                )
        else:
            console.print("[yellow]No sub-projects found.[/yellow]")


# ---------------------------------------------------------------------------
# check-drift
# ---------------------------------------------------------------------------

@main.command(name="check-drift")
@click.option("--name", "-n", required=True, help="Product name.")
@click.option("--repo", "-r", required=True, type=click.Path(exists=True, file_okay=False, resolve_path=True), help="Path to the product repo.")
@click.option(
    "--full",
    is_flag=True,
    help="Re-run all heuristic analyzers and compare fingerprints (slower, no git required).",
)
@click.pass_context
def check_drift(ctx: click.Context, name: str, repo: str, full: bool) -> None:
    """Check if the cached profile is stale vs. the current codebase (git HEAD and/or heuristics)."""
    config: Config = ctx.obj["config"]

    try:
        profile_path = config.get_analysis_path(name)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="'--name'") from e

    if not profile_path.exists():
        raise click.ClickException(f"No profile found for '{name}'.")

    profile = ProductProfile.load(profile_path)
    repo_path = Path(repo)

    console.print(f"\n[bold blue]Checking drift[/bold blue] for [green]{name}[/green]\n")

    from product_builders.lifecycle.drift import run_drift_check
    from product_builders.metrics import record_event

    report = run_drift_check(profile, repo_path, full=full)

    if report.git_drift:
        console.print(f"[yellow]{report.git_message}[/yellow]")
    elif report.no_git_sha_in_profile or report.git_head_unreadable:
        console.print(f"[yellow]{report.git_message}[/yellow]")
    else:
        console.print(f"[green]{report.git_message}[/green]")

    if full:
        console.print()
        if report.full_check_failed:
            console.print(f"[red]{report.full_message}[/red]")
        elif report.full_drift:
            console.print(f"[yellow]{report.full_message}[/yellow]")
        elif report.full_message:
            console.print(f"[green]{report.full_message}[/green]")

    product_dir = config.get_product_dir(name)
    record_event(
        product_dir,
        "check_drift",
        git_drift=report.git_drift,
        full=full,
        full_drift=report.full_drift,
        full_check_failed=report.full_check_failed,
    )

    if report.full_check_failed:
        raise click.ClickException("Full heuristic check failed (see above).")

    any_issue = report.git_drift or (full and report.full_drift is True)
    if any_issue:
        console.print(
            "\n[dim]Tip: run[/dim] [cyan]product-builders analyze[/cyan] [dim]on the repo to refresh the profile, "
            "then[/dim] [cyan]generate[/cyan][dim].[/dim]"
        )
        raise click.ClickException("Drift detected.")


# ---------------------------------------------------------------------------
# metrics
# ---------------------------------------------------------------------------

@main.command("metrics")
@click.option("--name", "-n", required=True, help="Product name.")
@click.option("--limit", default=80, help="Max recent events to print.")
@click.pass_context
def show_metrics(ctx: click.Context, name: str, limit: int) -> None:
    """Show recent metrics events (JSON Lines) for a product profile."""
    config: Config = ctx.obj["config"]

    try:
        product_dir = config.get_product_dir(name)
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="'--name'") from e

    from product_builders.metrics import read_recent_events

    events = read_recent_events(product_dir, limit=limit)
    if not events:
        console.print("[yellow]No metrics.jsonl yet. Run validate, check-drift, etc.[/yellow]")
        return

    console.print(f"\n[bold]Recent metrics for[/bold] [green]{name}[/green] ({len(events)} events)\n")
    for ev in events:
        ts = ev.get("ts", "?")
        event = ev.get("event", "?")
        rest = {k: v for k, v in ev.items() if k not in ("ts", "event")}
        extra = f" {rest}" if rest else ""
        console.print(f"  [dim]{ts}[/dim]  [cyan]{event}[/cyan]{extra}")


# ---------------------------------------------------------------------------
# wizard (phased quick start)
# ---------------------------------------------------------------------------

@main.command("wizard")
@click.option(
    "--phase",
    type=click.IntRange(1, 5),
    default=None,
    help="Run only this phase (1=foundation through 5=lifecycle). Default: all phases in order.",
)
@click.option(
    "--repo",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    default=None,
    help="Repository path (for phase 2 / drift; skips prompt when set).",
)
@click.option("--name", "-n", default=None, help="Product profile name (phases 2 to 5).")
@click.option(
    "--profile",
    "-p",
    default=None,
    help="Contributor role alias for phase 3 generate (e.g. engineer, pm).",
)
@click.option(
    "--validate/--no-validate",
    default=None,
    help="For phase 3: run structural validation after generate (default: prompt).",
)
@click.option(
    "--heuristic-only",
    is_flag=True,
    help="For phase 2: analyze without bootstrap deep-analysis rule.",
)
@click.option(
    "-y",
    "--yes",
    is_flag=True,
    help="Non-interactive: skip between-phase confirmations; use with --phase and required args.",
)
@click.pass_context
def wizard_cmd(
    ctx: click.Context,
    phase: int | None,
    repo: str | None,
    name: str | None,
    profile: str | None,
    validate: bool | None,
    heuristic_only: bool,
    yes: bool,
) -> None:
    """Step through install, analyze, generate, and lifecycle, aligned with project phases.

    Phase 1: Foundation (Python, paths, pip hints).
    Phase 2: Core analysis (writes analysis.json).
    Phase 3: Rules, hooks, permissions, onboarding.
    Phase 4: Note on extended analyzers (already in analyze).
    Phase 5: Drift, metrics, feedback commands.

    Use -y --phase N with explicit --repo / --name when scripting.
    """
    if yes:
        if phase == 2 and (not repo or not name):
            raise click.UsageError("With -y and --phase 2, provide --repo and --name.")
        if phase == 3 and not name:
            raise click.UsageError("With -y and --phase 3, provide --name.")

    from product_builders.cli_wizard import run_wizard

    run_wizard(
        ctx,
        console=console,
        phase=phase,
        repo=repo,
        name=name,
        profile=profile,
        run_validate=validate,
        heuristic_only=heuristic_only,
        yes=yes,
    )


# ---------------------------------------------------------------------------
# feedback
# ---------------------------------------------------------------------------

@main.command()
@click.option("--name", "-n", required=True, help="Product name.")
@click.option("--rule", "-r", required=True, help="Rule name (e.g. 'database', 'security-and-auth').")
@click.option("--issue", "-i", required=True, help="Description of the inaccuracy or issue.")
@click.pass_context
def feedback(ctx: click.Context, name: str, rule: str, issue: str) -> None:
    """Record feedback on a rule's accuracy for the next regeneration cycle."""
    config: Config = ctx.obj["config"]

    import yaml

    try:
        feedback_path = config.get_product_dir(name) / "feedback.yaml"
    except ValueError as e:
        raise click.BadParameter(str(e), param_hint="'--name'") from e

    existing: list[dict] = []
    log = logging.getLogger(__name__)
    if feedback_path.exists():
        try:
            raw = feedback_path.read_text(encoding="utf-8")
            data = yaml.safe_load(raw)
        except (yaml.YAMLError, OSError, UnicodeDecodeError) as e:
            log.warning(
                "feedback: could not read existing %s, starting fresh: %s",
                feedback_path,
                e,
            )
            data = None
        if isinstance(data, list):
            existing = [x for x in data if isinstance(x, dict)]
        elif isinstance(data, dict):
            existing = [data]

    existing.append({
        "rule": rule,
        "issue": issue,
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    })

    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    feedback_path.write_text(
        yaml.dump(existing, default_flow_style=False, allow_unicode=True),
        encoding="utf-8",
    )
    console.print(f"[green]Feedback recorded[/green] for [cyan]{rule}[/cyan] on [green]{name}[/green]")


if __name__ == "__main__":
    main()
