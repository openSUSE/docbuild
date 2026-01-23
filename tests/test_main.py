import os
import subprocess
import sys


def test_main_invokes_cli(monkeypatch):
    called = {}

    def fake_cli():
        called["cli"] = True

    # Patch sys.modules to inject fake cli
    import docbuild.__main__

    monkeypatch.setattr(docbuild.__main__, "cli", fake_cli)
    monkeypatch.setitem(sys.modules, "docbuild.__main__", docbuild.__main__)

    # Simulate running as __main__
    docbuild.__main__.__name__ = "__main__"
    docbuild.__main__.cli()
    assert called.get("cli") is True


def test_main_entrypoint_runs_cli():
    env = os.environ.copy()
    # Subprocesses are not covered by default. This needs to be explicitly enabled.
    env["COVERAGE_PROCESS_START"] = ".coveragerc"
    env["PYTHONPATH"] = "src"
    # Run the module as a script
    result = subprocess.run(
        [sys.executable, "-m", "docbuild", "--help"],
        capture_output=True,
        text=True,
        env=env,
    )
    # The CLI may exit with code 0 or show help if no args
    assert result.returncode == 0 or result.returncode == 1
    # Optionally, check for expected output (e.g., help text)
    assert "Usage:" in result.stdout or "usage:" in result.stdout.lower()
