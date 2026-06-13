from typer.testing import CliRunner

from corporate_rag.cli import cli


def test_cli_settings_command_prints_current_settings() -> None:
    runner = CliRunner()

    result = runner.invoke(cli, ["settings"])

    assert result.exit_code == 0
    assert '"app_name": "Corporate RAG"' in result.stdout
    assert '"environment": "local"' in result.stdout
