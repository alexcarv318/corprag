from typing import Annotated

import typer
import uvicorn

from corporate_rag.settings import load_app_settings

cli = typer.Typer(
    name="corporate-rag",
    help="Corporate RAG application commands.",
    no_args_is_help=True,
    add_completion=False,
)


@cli.command("serve")
def serve_command(
    host: Annotated[str, typer.Option("--host", help="Bind host.")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", help="Bind port.")] = 8088,
) -> None:
    uvicorn.run(
        "corporate_rag.app.main:create_app",
        host=host,
        port=port,
        factory=True,
    )


@cli.command("settings")
def settings_command() -> None:
    settings = load_app_settings()
    typer.echo(settings.model_dump_json(indent=2))


def main() -> None:
    cli()
