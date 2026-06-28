"""CLI entry point for findout."""

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table
from findout.config import Config, LLMConfig
from findout.pipeline import SelfVerifyPipeline
from findout.gate import Gate

app = typer.Typer(
    name="findout",
    help="Single-model, multi-pass verification pipeline for LLM outputs.",
)
console = Console()


def _build_config(
    model: str,
    base_url: str,
    api_key: str,
    timeout_seconds: int,
    max_tokens: int,
) -> Config:
    return Config(
        llm=LLMConfig(
            model=model,
            base_url=base_url,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            max_tokens=max_tokens,
        )
    )


@app.command()
def run(
    query: str = typer.Argument(..., help="The query to verify"),
    model: str = typer.Option(..., "--model", "-m", help="Model name"),
    base_url: str = typer.Option(..., "--base-url", "-u", help="API base URL"),
    api_key: str = typer.Option("", "--api-key", "-k", help="API key"),
    skip_gate: bool = typer.Option(
        False, "--skip-gate", "-g", help="Skip gate classifier, always run pipeline"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show intermediate steps"),
    timeout_seconds: int = typer.Option(120, "--timeout", help="Request timeout in seconds"),
    max_tokens: int = typer.Option(4096, "--max-tokens", help="Max generation tokens"),
):
    """Run the verification pipeline on a query."""
    config = _build_config(model, base_url, api_key, timeout_seconds, max_tokens)

    console.print("[bold]Pipeline:[/bold] base")
    console.print(f"[bold]Model:[/bold] {config.llm.model}")
    console.print(f"[bold]Query:[/bold] {query[:120]}")
    console.print()

    pipe = SelfVerifyPipeline(config)
    result = pipe.run(query, pipeline="base", skip_gate=skip_gate)

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
                "[green]✓ Verified[/green]"
                if csr.supports_claim
                else "[red]✗ Contradicted[/red]"
                if csr.contradicts_claim
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
    model: str = typer.Option(..., "--model", "-m", help="Model name"),
    base_url: str = typer.Option(..., "--base-url", "-u", help="API base URL"),
    api_key: str = typer.Option("", "--api-key", "-k", help="API key"),
    timeout_seconds: int = typer.Option(30, "--timeout", help="Request timeout in seconds"),
    max_tokens: int = typer.Option(4096, "--max-tokens", help="Max generation tokens"),
):
    """Classify a query as 'casual' or 'visionary' without running the pipeline."""
    llm = LLMConfig(
        model=model,
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
        max_tokens=max_tokens,
    )
    g = Gate(config=Config().pipeline.gate, llm_config=llm)
    decision, reason = g.classify_with_reason(query)

    if decision == "casual":
        console.print(f"[green]casual[/green] — {reason}")
    else:
        console.print(f"[yellow]visionary[/yellow] — {reason}")


if __name__ == "__main__":
    app()
