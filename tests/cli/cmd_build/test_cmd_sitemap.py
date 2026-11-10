"""Sitemap CLI progress and terminal behavior."""

import asyncio
from contextlib import suppress
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from click.testing import CliRunner
from lxml import etree
import pytest
from rich.text import Text

from docbuild.cli.cmd_build import cmd_sitemap
import docbuild.cli.cmd_cli as cmd_cli
from docbuild.cli.context import DocBuildContext
from docbuild.tasks import sitemap as sitemap_tasks


@pytest.mark.asyncio
async def test_live_directory_from_symlinked_english(tmp_path):
    """Real generation through an English symlink reaches the live display."""
    target = tmp_path / "target"
    target.mkdir()
    external = tmp_path / "external/en-us"
    for name in ("sles/16.0/index.html", "sles/16.0/html/page.html"):
        path = external / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<title>External build</title>", encoding="utf-8")
    (target / "en-us").symlink_to(external, target_is_directory=True)
    console = MagicMock(is_terminal=True, is_dumb_terminal=False)
    status = console.status.return_value.__enter__.return_value
    displayed = Event()
    worker_finished = Event()
    build_tree = sitemap_tasks.build_sitemap_tree

    def rendered(text):
        if text.plain == "Scanning HTML files: en-us/sles/16.0/html":
            displayed.set()

    status.update.side_effect = rendered

    def traverse(root, base_url, *, on_progress):
        def report(description, directory):
            on_progress(description, directory)
            if directory == target / "en-us/sles/16.0/html":
                if not displayed.wait(timeout=2):
                    raise TimeoutError("Live directory was not displayed")

        try:
            return build_tree(root, base_url, on_progress=report)
        finally:
            worker_finished.set()

    with (
        patch.object(cmd_sitemap, "console_err", console),
        patch.object(sitemap_tasks, "build_sitemap_tree", side_effect=traverse),
    ):
        wrapper = asyncio.create_task(
            cmd_sitemap.generate_sitemap_with_progress(target, "https://docs.test.com")
        )
        try:
            output = await asyncio.wait_for(wrapper, timeout=5)
        finally:
            displayed.set()  # Always release a worker waiting for the display.
            try:
                if not wrapper.done():
                    wrapper.cancel()
                with suppress(asyncio.CancelledError):
                    await asyncio.wait_for(wrapper, timeout=2)
            finally:
                finished = await asyncio.wait_for(
                    asyncio.to_thread(worker_finished.wait, 2), timeout=3
                )
                assert finished

    locations = etree.parse(output).xpath("//*[local-name()='loc']/text()")
    assert sorted(locations) == [
        "https://docs.test.com/sles/16.0/html/page.html",
        "https://docs.test.com/sles/16.0/index.html",
    ]
    console.status.return_value.__exit__.assert_called_once()
    assert not any(
        task.get_name() in {"build:sitemap", "build:sitemap:display"}
        for task in asyncio.all_tasks()
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "terminal,dumb,verbose",
    [
        (False, False, 0),
        (True, True, 0),
        (True, False, 1),
        (True, False, 2),
        (True, False, 3),
    ],
)
async def test_progress_disabled(tmp_path, terminal, dumb, verbose):
    """Pipes, dumb terminals and verbose logs receive no animation."""
    console = MagicMock(is_terminal=terminal, is_dumb_terminal=dumb)

    async def generate(target, base_url):
        assert asyncio.current_task().get_name() == "build:sitemap"
        return target / "sitemap.xml"

    with (
        patch.object(cmd_sitemap, "console_err", console),
        patch.object(
            cmd_sitemap, "generate_sitemap", side_effect=generate
        ) as generate_mock,
    ):
        output = await cmd_sitemap.generate_sitemap_with_progress(
            tmp_path, "https://docs.test.com", verbose=verbose
        )
    assert output == tmp_path / "sitemap.xml"
    generate_mock.assert_awaited_once_with(tmp_path, "https://docs.test.com")
    console.status.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
async def test_live_progress_and_cleanup(tmp_path: Path, outcome: str):
    """Worker updates coalesce, paths are literal, and the display always stops."""
    console = MagicMock(is_terminal=True, is_dumb_terminal=False)
    status = console.status.return_value.__enter__.return_value
    scanned = asyncio.Event()
    written = asyncio.Event()
    callback = None

    def rendered(text):
        assert isinstance(text, Text)
        if text.plain == "Scanning HTML files: en-us/[guide]":
            scanned.set()
        if text.plain == "Writing sitemap.xml: .":
            written.set()

    status.update.side_effect = rendered

    async def generate(target, base_url, *, on_progress):
        nonlocal callback
        callback = on_progress
        assert asyncio.current_task().get_name() == "build:sitemap"

        def traverse():
            for i in range(1000):
                on_progress("Scanning HTML files", target / str(i))
            on_progress("Scanning HTML files", target / "en-us/[guide]")

        await asyncio.to_thread(traverse)
        await asyncio.wait_for(scanned.wait(), 2)
        on_progress("Writing sitemap.xml", target)
        await asyncio.wait_for(written.wait(), 2)
        if outcome == "error":
            raise OSError("write failed")
        if outcome == "cancel":
            raise asyncio.CancelledError
        return target / "sitemap.xml"

    with (
        patch.object(cmd_sitemap, "console_err", console),
        patch.object(cmd_sitemap, "generate_sitemap", side_effect=generate),
    ):
        if outcome == "success":
            assert (
                await cmd_sitemap.generate_sitemap_with_progress(
                    tmp_path, "https://docs.test.com"
                )
                == tmp_path / "sitemap.xml"
            )
        else:
            error = OSError if outcome == "error" else asyncio.CancelledError
            with pytest.raises(error):
                await cmd_sitemap.generate_sitemap_with_progress(
                    tmp_path, "https://docs.test.com"
                )

    console.status.return_value.__exit__.assert_called_once()
    assert not any(
        task.get_name() == "build:sitemap:display" for task in asyncio.all_tasks()
    )
    count = status.update.call_count
    # A worker finishing after cancellation cannot touch a closed display.
    callback("Scanning HTML files", tmp_path / "late")
    assert status.update.call_count == count


def test_sitemap_command_forwards_configuration(tmp_path):
    """The standalone command uses the shared wrapper and preserves its message."""
    env = SimpleNamespace(
        paths=SimpleNamespace(target=SimpleNamespace(target_base_dir=tmp_path)),
        general=SimpleNamespace(canonical_url_domain="https://docs.test.com"),
    )
    context = DocBuildContext(envconfig=env, verbose=2)
    with patch.object(
        cmd_sitemap, "generate_sitemap_with_progress", new_callable=AsyncMock
    ) as generate:
        result = CliRunner().invoke(cmd_sitemap.sitemap, obj=context)
    assert result.exit_code == 0, result.output
    generate.assert_awaited_once_with(tmp_path, "https://docs.test.com", verbose=2)
    assert "Generated sitemap at" in result.output


@pytest.mark.parametrize("override", [False, True])
def test_sitemap_resolves_target_config(tmp_path, monkeypatch, override):
    """Explicit config selects the target, and --set-env takes precedence."""
    configured_target = tmp_path / "configured-target"
    override_target = tmp_path / "override-target"
    configured_target.mkdir()
    override_target.mkdir()
    env_file = tmp_path / "env.toml"
    env_file.write_text(
        "[general]\ncanonical_url_domain = 'https://docs.test.com/'\n"
        f"[paths.target]\ntarget_base_dir = '{configured_target.as_posix()}'\n",
        encoding="utf-8",
    )
    # Model validation creates writable paths. Keep every such path local to
    # this test, and avoid application logging and PID-lock side effects.
    paths = {
        name: str(tmp_path / name)
        for name in (
            "repo_dir",
            "tmp_repo_dir",
            "base_cache_dir",
            "base_server_cache_dir",
            "meta_cache_dir",
            "json_cache_dir",
            "runtime_base_dir",
            "lock_dir",
        )
    }
    paths["tmp"] = {
        name: str(tmp_path / name)
        for name in (
            "tmp_base_dir",
            "tmp_dir",
            "tmp_deliverable_dir",
            "tmp_metadata_dir",
            "tmp_build_base_dir",
            "tmp_out_dir",
            "log_dir",
        )
    }
    monkeypatch.setattr(cmd_cli, "DEFAULT_ENV_CONFIG", {"paths": paths})
    monkeypatch.setattr(cmd_cli, "CONFIG_PATHS", (tmp_path / "discovery",))
    args = ["-vvv", "--env-config", str(env_file)]
    if override:
        args += ["--set-env", f"paths.target.target_base_dir={override_target}"]
    context = DocBuildContext()
    with (
        patch.object(cmd_cli, "load_app_config"),
        patch.object(cmd_cli, "setup_logging_from_context"),
        patch.object(cmd_cli, "PidFileLock"),
        patch.object(
            cmd_sitemap, "generate_sitemap_with_progress", new_callable=AsyncMock
        ) as generate,
    ):
        result = CliRunner().invoke(
            cmd_cli.cli, [*args, "build", "sitemap"], obj=context
        )
    assert result.exit_code == 0, result.output
    assert context.envconfigfiles == (env_file,)
    assert not context.envconfig_from_defaults
    generate.assert_awaited_once_with(
        override_target if override else configured_target,
        "https://docs.test.com/",
        verbose=3,
    )


@pytest.mark.asyncio
async def test_cancel_wrapper_during_traversal(tmp_path: Path):
    """Outer cancellation stops the display even while the worker is running."""
    console = MagicMock(is_terminal=True, is_dumb_terminal=False)
    status = console.status.return_value.__enter__.return_value
    scanned = asyncio.Event()
    release_worker = Event()
    worker_started = Event()
    worker_finished = Event()
    build_tree = sitemap_tasks.build_sitemap_tree

    def rendered(text):
        if text.plain == "Scanning HTML files: en-us":
            scanned.set()

    status.update.side_effect = rendered

    def traverse(target, base_url, *, on_progress):
        worker_started.set()
        try:
            on_progress("Scanning HTML files", target / "en-us")
            if not release_worker.wait(timeout=5):
                raise TimeoutError("Test did not release the traversal worker")
            # to_thread cancellation does not stop a running worker. Its late
            # reports must be safe after the status context has closed.
            return build_tree(target, base_url, on_progress=on_progress)
        finally:
            worker_finished.set()

    with (
        patch.object(cmd_sitemap, "console_err", console),
        patch.object(sitemap_tasks, "build_sitemap_tree", side_effect=traverse),
    ):
        wrapper = asyncio.create_task(
            cmd_sitemap.generate_sitemap_with_progress(
                tmp_path, "https://docs.test.com"
            )
        )
        try:
            await asyncio.wait_for(scanned.wait(), timeout=2)
            wrapper.cancel()
            with pytest.raises(asyncio.CancelledError):
                await asyncio.wait_for(wrapper, timeout=2)

            assert not worker_finished.is_set()
            console.status.return_value.__exit__.assert_called_once()
            assert not any(
                task.get_name() in {"build:sitemap", "build:sitemap:display"}
                for task in asyncio.all_tasks()
            )
            updates_before_release = status.update.call_count
        finally:
            release_worker.set()
            try:
                if not wrapper.done():
                    wrapper.cancel()
                with suppress(asyncio.CancelledError):
                    await asyncio.wait_for(wrapper, timeout=2)
            finally:
                if worker_started.is_set():
                    finished = await asyncio.wait_for(
                        asyncio.to_thread(worker_finished.wait, 2), timeout=3
                    )
                    assert finished, "Traversal worker did not finish after release"

    assert status.update.call_count == updates_before_release
    assert not (tmp_path / "sitemap.xml").exists()
