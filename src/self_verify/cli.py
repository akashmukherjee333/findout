"""CLI entry point for self-verify-pipelines.

Usage:
  self-verify run "your research query here"
  self-verify gate "is this casual or visionary?"
"""

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from self_verify.config import Config
from self_verify.pipeline import SelfVerifyPipeline
from self_verify.gate import Gate

app = typer.Typer(
    name="self-verify",
    help="Single-model, multi-pass verification pipelines for LLM outputs.",
)
console = Console()


@app.command()
def run(
    query: str = typer.Argument(..., help="The query to verify"),
    model: str = typer.Option(None, "--model", "-m", help="Model name override"),
    base_url: str = typer.Option(None, "--base-url", "-u", help="API base URL"),
    api_key: str = typer.Option(None, "--api-key", "-k", help="API key"),
    pipeline: str = typer.Option(
        "base", "--pipeline", "-p",
        help="Pipeline variant: base, consistency, hybrid",
    ),
    skip_gate: bool = typer.Option(
        False, "--skip-gate", "-g",
        help="Skip gate classifier, always run pipeline",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show intermediate steps"),
):
    """Run the verification pipeline on a query."""
    config = Config.from_env()

    # CLI overrides
    if model:
        config.llm.model = model
    if base_url:
        config.llm.base_url = base_url
    if api_key:
        config.llm.api_key = api_key

    console.print(f"[bold]Pipeline:[/bold] {pipeline}")
    console.print(f"[bold]Model:[/bold] {config.llm.model}")
    console.print(f"[bold]Query:[/bold] {query[:120]}")
    console.print()

    pipe = SelfVerifyPipeline(config)
    result = pipe.run(query, pipeline=pipeline, skip_gate=skip_gate)

    if result.skipped_pipeline:
        console.print("[yellow]Gate classified as casual — answering directly.[/yellow]")
        console.print()

    console.print(Markdown(result.answer))

    if verbose and result.citations:
        console.print()
        table = Table(title="Citations")
        table.add_column("#", style="dim")
        table.add_column("URL")
        for i, url in enumerate(result.citations, 1):
            table.add_row(str(i), url)
        console.print(table)

    if verbose and result.claims:
        console.print()
        t2 = Table(title="Claims Analysis")
        t2.add_column("Claim")
        t2.add_column("Status")
        for csr in result.search_results:
            status = (
                "[green]✓ Verified[/green]" if csr.supports_claim
                else "[red]✗ Contradicted[/red]" if csr.contradicts_claim
                else "[yellow]? Uncertain[/yellow]"
            )
            t2.add_row(csr.claim_text[:80], status)
        console.print(t2)

    if not verbose:
        console.print()
        console.print(
            f"[dim]Claims: {result.total_claims} total, "
            f"{result.verified_claims} verified, "
            f"{result.contradicted_claims} contradicted, "
            f"{result.uncertain_claims} uncertain[/dim]"
        )


@app.command()
def gate(
    query: str = typer.Argument(..., help="Query to classify"),
    model: str = typer.Option(None, "--model", "-m", help="Model name override"),
):
    """Classify a query as 'casual' or 'visionary' without running the pipeline."""
    config = Config.from_env()
    if model:
        config.llm.model = model

    g = Gate(config=config.pipeline.gate, llm_config=config.llm)
    decision, reason = g.classify_with_reason(query)

    if decision == "casual":
        console.print(f"[green]casual[/green] — {reason}")
    else:
        console.print(f"[yellow]visionary[/yellow] — {reason}")


if __name__ == "__main__":
    app()
