"""Build failure notification tests using real portal nodes and mocked SMTP."""

import asyncio
from email.message import EmailMessage
import smtplib
import ssl
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner
from lxml import etree
from pydantic import ValidationError
import pytest

from docbuild import notifications
from docbuild.cli.cmd_build import cmd_run
from docbuild.cli.context import DocBuildContext
from docbuild.models.config.env import EnvConfig, EnvMail
from docbuild.models.deliverable import Deliverable
from docbuild.tasks.metadata.daps import process_deliverable
from docbuild.tasks.worktrees import process_with_shared_worktrees


@pytest.fixture
def env(monkeypatch):
    monkeypatch.delenv("DOCBUILD_SMTP_USERNAME", raising=False)
    monkeypatch.delenv("DOCBUILD_SMTP_PASSWORD", raising=False)
    return EnvConfig.from_dict(
        {
            "general": {"enable_mail": True, "name": "staging"},
            "mail": {
                "sender": "build@example.test",
                "smtp_host": "relay",
                "admin_emails": ["admin@example.test", "admin@example.test"],
            },
        }
    )


def document(product, contacts=True):
    root = etree.fromstring(f"""
    <product xml:id="{product}">
      <maintainers>{(f"<contact>{product}@example.test</contact>" * 2) if contacts else ""}</maintainers>
      <docset path="1"><version>1.0</version><resources><git remote="gh://test/docs"/>
        <locale lang="en-us"><branch>main</branch><deliverable>
          <dc file="DC-{product}"><format html="1" pdf="1"/></dc>
        </deliverable></locale>
      </resources></docset>
    </product>""")
    return Deliverable(root.find(".//deliverable"))


def test_env_without_mail():
    env = EnvConfig.from_dict({})
    assert env.mail is None
    assert env.general.enable_mail is False


@pytest.mark.parametrize(
    "invalid",
    [
        {"smtp_port": 65536},
        {"timeout": 0},
        {"timeout": float("inf")},
        {"tls": "both"},
        {"tls": "none"},
        {"sender": "missing-domain"},
        {"admin_emails": ["one@site.test,two@site.test"]},
        {"smtp_password": "not-allowed"},
    ],
)
def test_invalid_mail(env, invalid):
    with pytest.raises(ValidationError):
        EnvMail.model_validate(env.mail.model_dump() | invalid)


def test_product_digests(env):
    alpha, beta, unowned = document("alpha"), document("beta"), document("gamma", False)
    with patch.object(smtplib, "SMTP") as smtp:
        client = smtp.return_value.__enter__.return_value
        client.send_message.return_value = {}
        with notifications.BuildNotifications(env) as run:
            notifications.record_failure("DAPS build", "image missing", alpha, "html")
            notifications.record_failure("Sync", "read-only target", alpha, "pdf")
            notifications.record_failure("Worktree", "missing branch", beta)
            notifications.record_failure("Metadata", "no owner", unowned)
            notifications.record_failure("Sitemap", "run-wide error")
            run.result = 1

    messages = {str(m["To"]): m for (m,), _ in client.send_message.call_args_list}
    assert len(client.send_message.call_args_list) == len(messages) == 3
    first = messages["alpha@example.test"]
    assert first["Subject"] == "Build failed: alpha"
    body = first.get_content()
    assert "alpha/1.0 — DC-alpha" in body
    assert "Language: en-us" in body and "Format: html" in body
    assert "image missing" in body and "read-only target" in body
    assert "test/docs, branch main" in body
    assert (
        "beta" not in body and "no owner" not in body and "run-wide error" not in body
    )
    second = messages["beta@example.test"].get_content()
    assert "missing branch" in second and "alpha" not in second
    admin = messages["admin@example.test"]
    assert admin["Subject"] == "Build failure digest: staging"
    assert admin.get_content().count("  Stage: ") == 5
    assert "run-wide error" in admin.get_content()
    assert "None" not in admin.get_content()


@pytest.mark.parametrize(
    ("enabled", "outcome", "exit_code", "count"),
    [
        (False, 7, 7, 0),
        (True, 0, 0, 0),
        (True, 7, 7, 1),
        (True, asyncio.CancelledError(), 130, 0),
        (True, KeyboardInterrupt(), 130, 0),
        (True, OSError("cannot parse portal"), 1, 1),
    ],
)
def test_cli_build_outcome(env, enabled, outcome, exit_code, count, caplog):
    env.general.enable_mail = enabled
    process = (
        AsyncMock(return_value=outcome)
        if isinstance(outcome, int)
        else AsyncMock(side_effect=outcome)
    )
    with (
        patch.object(cmd_run, "metadata_process", process),
        patch.object(cmd_run, "build_process", AsyncMock(return_value=0)),
        patch.object(smtplib, "SMTP", side_effect=ConnectionRefusedError) as smtp,
    ):
        result = CliRunner().invoke(
            cmd_run.run, ["--no-sitemap"], obj=DocBuildContext(envconfig=env)
        )
    assert result.exit_code == exit_code
    assert smtp.call_count == count
    if count:
        assert "ConnectionRefusedError" in caplog.text
    if isinstance(outcome, OSError):
        assert result.exception is outcome


@pytest.mark.parametrize("mode", ["starttls", "implicit"])
@pytest.mark.parametrize("authenticated", [True, False])
def test_transport(env, monkeypatch, mode, authenticated):
    env.mail.tls = mode
    if authenticated:
        monkeypatch.setenv("DOCBUILD_SMTP_USERNAME", "test-user")
        monkeypatch.setenv("DOCBUILD_SMTP_PASSWORD", "test-password")
    message = EmailMessage()
    with (
        patch.object(smtplib, "SMTP") as smtp,
        patch.object(smtplib, "SMTP_SSL") as secure,
    ):
        notifications.send_message(env.mail, message)
    constructor = secure if mode == "implicit" else smtp
    connection = constructor.return_value
    client = connection.__enter__.return_value
    assert constructor.call_args.args == ("relay", 587)
    assert constructor.call_args.kwargs["timeout"] == 10
    assert client.starttls.called == (mode == "starttls")
    kwargs = (
        client.starttls.call_args.kwargs
        if mode == "starttls"
        else constructor.call_args.kwargs
    )
    assert kwargs["context"].verify_mode == ssl.CERT_REQUIRED
    assert kwargs["context"].check_hostname
    expected = ["starttls"] if mode == "starttls" else []
    if authenticated:
        expected.append("login")
        client.login.assert_called_once_with("test-user", "test-password")
    else:
        client.login.assert_not_called()
    client.send_message.assert_called_once_with(message)
    assert [name for name, _, _ in client.method_calls] == [*expected, "send_message"]
    connection.__exit__.assert_called_once()


def test_starttls_failure_prevents_delivery(env, monkeypatch):
    monkeypatch.setenv("DOCBUILD_SMTP_USERNAME", "test-user")
    monkeypatch.setenv("DOCBUILD_SMTP_PASSWORD", "test-password")
    with patch.object(smtplib, "SMTP") as smtp:
        client = smtp.return_value.__enter__.return_value
        client.starttls.side_effect = ssl.SSLError
        with pytest.raises(ssl.SSLError):
            notifications.send_message(env.mail, EmailMessage())
    client.login.assert_not_called()
    client.send_message.assert_not_called()


def test_delivery_failure_isolated(env, monkeypatch, caplog):
    monkeypatch.setenv("DOCBUILD_SMTP_USERNAME", "private-user")
    monkeypatch.setenv("DOCBUILD_SMTP_PASSWORD", "private-secret")
    with patch.object(smtplib, "SMTP") as smtp:
        client = smtp.return_value.__enter__.return_value
        client.login.side_effect = [
            smtplib.SMTPAuthenticationError(535, b"private-user private-secret"),
            None,
        ]
        client.send_message.return_value = {}
        with notifications.BuildNotifications(env) as run:
            notifications.record_failure("Metadata", "bad XML", document("alpha"))
            run.result = 1
    assert client.login.call_count == 2
    assert client.send_message.call_args.args[0]["To"] == "admin@example.test"
    assert "SMTPAuthenticationError" in caplog.text
    assert "private-user" not in caplog.text and "private-secret" not in caplog.text


async def test_early_failure_details(env, tmp_path):
    doc = document("alpha")
    with notifications.BuildNotifications(env) as run:
        success, _ = await process_deliverable(
            doc,
            tmp_path,
            tmp_path,
            tmp_path,
            tmp_path,
            dapstmpl="",
            daps_list_srcfiles_tmpl="",
        )
        assert not success
        process = AsyncMock()
        failed = await process_with_shared_worktrees(
            [doc], tmp_path, tmp_path, 1, asyncio.Semaphore(1), process
        )
        assert failed == [doc]
        process.assert_not_awaited()
        assert [(f.stage, f.deliverable) for f in run.failures] == [
            ("Repository preparation", doc),
            ("Worktree creation", doc),
        ]
        assert "Bare repository missing" in run.failures[0].summary
        assert "Bare repository does not exist" in run.failures[1].summary


def test_missing_mail_settings_and_partial_credentials(env, monkeypatch, caplog):
    monkeypatch.setenv("DOCBUILD_SMTP_USERNAME", "only-user")
    with patch.object(smtplib, "SMTP") as smtp:
        with notifications.BuildNotifications(env) as run:
            run.result = 1
        env.mail = None
        with notifications.BuildNotifications(env) as run:
            run.result = 1
    smtp.assert_not_called()
    assert "no [mail] settings" in caplog.text
    assert "only-user" not in caplog.text


def test_propagating_exception_and_context_reset(env):
    with patch.object(notifications, "send_message") as send:
        with (
            pytest.raises(ValueError, match="invalid portal"),
            notifications.BuildNotifications(env),
        ):
            raise ValueError("invalid portal")
        msg = send.call_args.args[1]
        assert msg.get_content().count("invalid portal") == 1
        assert str(msg["To"]) == "admin@example.test"
        assert "Source:" not in msg.get_content()
        notifications.record_failure("Build", "stale failure")
        with notifications.BuildNotifications(env) as next_run:
            assert next_run.failures == []
        assert send.call_count == 1


def test_shared_worktree_diagnostic(env, tmp_path):
    worktree = tmp_path / "wt_alpha_DC-alpha_123"
    with notifications.BuildNotifications(env) as run:
        notifications.record_failure(
            "Worktree creation",
            f"clone into {worktree} from https://user:token@host.test/docs failed",
            document("beta"),
            worktree=worktree,
        )
        assert (
            run.failures[0].summary
            == "clone into <worktree> from https://host.test/docs failed"
        )


def test_unattributed_deliverable_and_empty_contacts(env):
    with patch.object(notifications, "send_message") as send:
        with notifications.BuildNotifications(env) as run:
            notifications.record_failure(
                "Metadata", "no product", Deliverable(etree.Element("deliverable"))
            )
            run.result = 1
        msg = send.call_args.args[1]
        assert str(msg["To"]) == "admin@example.test"
        assert "no product" in msg.get_content()
        send.reset_mock()
        env.mail.admin_emails = []
        with notifications.BuildNotifications(env) as run:
            notifications.record_failure(
                "Metadata", "no contacts", document("gamma", False)
            )
            run.result = 1
        send.assert_not_called()


async def test_prebuilt_metadata_failure(env, tmp_path):
    from docbuild.tasks.metadata import daps

    doc = document("alpha")
    node = doc.xml.node
    node.remove(node.find("dc"))
    with (
        patch.object(
            daps,
            "extract_prebuilt_metadata",
            side_effect=ValueError("invalid metadata"),
        ),
        notifications.BuildNotifications(env) as run,
    ):
        success, _ = await process_deliverable(
            doc,
            tmp_path,
            tmp_path,
            tmp_path,
            tmp_path,
            dapstmpl="",
            daps_list_srcfiles_tmpl="",
        )
        assert not success
        (failure,) = run.failures
        assert failure.deliverable is doc
        assert (
            failure.stage == "Prebuilt metadata"
            and failure.summary == "invalid metadata"
        )


@pytest.mark.parametrize("bad_metadata", ["{}", "invalid json"])
def test_cross_product_cache_failure_notifies_owner(env, tmp_path, bad_metadata):
    from docbuild.tasks.metadata.manifest import load_documents_from_deliverables

    portal = etree.Element("portal")
    source, target = document("sles"), document("sled")
    for doc in (source, target):
        portal.append(doc.xml.product_node)
    target.xml.node.set("{http://www.w3.org/XML/1998/namespace}id", "target-guide")
    source.xml.node.remove(source.xml.node.find("dc"))
    etree.SubElement(source.xml.node, "xref", linkend="target-guide")
    cache = tmp_path / target.paths.relpath / target.xml.dcfile
    cache.parent.mkdir(parents=True)
    cache.write_text(bad_metadata)
    with patch.object(notifications, "send_message") as send:
        with notifications.BuildNotifications(env) as run:
            assert load_documents_from_deliverables([target, source], tmp_path) == []
            assert len(run.failures) == 1
            run.result = 1
    messages = [call.args[1] for call in send.call_args_list]
    assert [str(msg["To"]) for msg in messages] == [
        "sled@example.test",
        "admin@example.test",
    ]
    for msg in messages:
        assert msg.get_content().count("Stage: Manifest generation") == 1
        assert "DC-sled" in msg.get_content() and "DC-sles" not in msg.get_content()


async def test_all_repository_failures_survive_first_exception(env, tmp_path):
    from docbuild.tasks.metadata.repos import update_repositories
    from docbuild.utils.git import ManagedGitRepo

    docs = [document(p) for p in ("alpha", "beta")]
    for doc in docs:
        doc.xml.product_node.find(".//git").set(
            "remote", f"gh://test/{doc.xml.product_id}"
        )
    error = ValueError("first failure")
    with (
        patch.object(
            ManagedGitRepo, "clone_bare", AsyncMock(side_effect=[error, False])
        ),
        notifications.BuildNotifications(env) as run,
        pytest.raises(ValueError) as caught,
    ):
        await update_repositories(docs, tmp_path)
    assert caught.value is error
    assert [failure.deliverable for failure in run.failures] == docs


async def test_global_worktree_failure_isolates_shared_diagnostic(env, tmp_path):
    from docbuild.tasks import worktrees

    docs = [document("alpha"), document("beta")]
    with (
        patch.object(
            worktrees,
            "_process_group",
            AsyncMock(side_effect=ValueError("group detail")),
        ),
        patch.object(notifications, "send_message") as send,
        notifications.BuildNotifications(env) as run,
    ):
        assert (
            await process_with_shared_worktrees(
                docs, tmp_path, tmp_path, 1, asyncio.Semaphore(1), AsyncMock()
            )
            == docs
        )
        run.result = 1
    bodies = {
        str(msg["To"]): msg.get_content()
        for _, msg in (call.args for call in send.call_args_list)
    }
    assert "group detail" in bodies.pop("admin@example.test")
    assert set(bodies) == {"alpha@example.test", "beta@example.test"}
    for recipient, body in bodies.items():
        assert "group detail" not in body and body.count("  Stage: Build pipeline") == 1
        assert f"DC-{recipient.split('@')[0]}" in body


@pytest.mark.parametrize(
    "scenario", ["disabled", "formats", "metadata", "worktree", "unavailable"]
)
def test_build_run_mail_pipeline(env, tmp_path, runner, monkeypatch, caplog, scenario):
    """Run Git, metadata and format workers from the CLI with a local source repository."""
    import subprocess

    from docbuild.cli.cmd_build import build

    source = tmp_path / "source"
    subprocess.run(["git", "init", "-q", "-b", "main", source], check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=test@example.test",
            "-c",
            "user.name=Test",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-q",
            "--allow-empty",
            "-m",
            "fixture",
        ],
        cwd=source,
        check=True,
    )
    paths = env.paths
    paths.repo_dir = tmp_path / "repos"
    paths.tmp_repo_dir = tmp_path / "trees"
    paths.tmp.tmp_build_base_dir = tmp_path / "build"
    paths.tmp.tmp_metadata_dir = tmp_path / "metadata"
    paths.meta_cache_dir = tmp_path / "meta-cache"
    paths.json_cache_dir = tmp_path / "json-cache"
    paths.target.target_base_dir = tmp_path / "target"
    for path in (paths.repo_dir, paths.tmp_repo_dir, paths.tmp.tmp_build_base_dir):
        path.mkdir()

    portal = etree.Element("portal")
    for product in ("sles", "sled"):
        doc = document(product)
        node = doc.xml.product_node
        node.find("docset").set("lifecycle", "supported")
        node.find("docset").set(
            "{http://www.w3.org/XML/1998/namespace}id", f"{product}.1"
        )
        doc.xml.node.set("{http://www.w3.org/XML/1998/namespace}id", f"{product}.guide")
        if scenario == "worktree":
            node.find(".//branch").text = "absent"
        portal.append(node)
    paths.main_portal_config = tmp_path / "portal.xml"
    etree.ElementTree(portal).write(str(paths.main_portal_config))
    subprocess.run(
        ["git", "clone", "-q", "--bare", source, paths.repo_dir / doc.git.slug],
        check=True,
    )

    # A failing command reports either its normal diagnostic or any leaked test value.
    fail = tmp_path / "fail-build"
    fail.write_text(
        '#!/bin/sh\necho "${DOCBUILD_SMTP_USERNAME-} ${DOCBUILD_SMTP_PASSWORD-} image missing" >&2\nexit 23\n'
    )
    fail.chmod(0o700)
    env.build.daps.html = env.build.daps.pdf = env.build.daps.meta = str(fail)
    env.build.daps.list_srcfiles = "true"
    env.general.enable_mail = scenario != "disabled"
    monkeypatch.setenv("DOCBUILD_SMTP_USERNAME", "synthetic-login")
    monkeypatch.setenv("DOCBUILD_SMTP_PASSWORD", "synthetic-password")
    with patch.object(smtplib, "SMTP") as smtp:
        client = smtp.return_value.__enter__.return_value
        client.send_message.return_value = {}
        if scenario == "unavailable":
            smtp.side_effect = ConnectionRefusedError
        args = ["run", "-S", "--no-sitemap", "//en-us"]
        if scenario != "metadata":
            args.insert(1, "-M")
        result = runner.invoke(build, args, obj=DocBuildContext(envconfig=env))
    assert result.exit_code == 1, (result.exception, result.output)
    messages = [call.args[0] for call in client.send_message.call_args_list]
    diagnostics = (
        result.output + caplog.text + "".join(msg.get_content() for msg in messages)
    )
    assert (
        "synthetic-login" not in diagnostics and "synthetic-password" not in diagnostics
    )
    if scenario != "worktree":
        assert "image missing" in caplog.text
    if scenario == "disabled":
        smtp.assert_not_called()
        return
    assert smtp.call_count == 3
    if scenario == "unavailable":
        assert caplog.text.count("ConnectionRefusedError") == 3 and not messages
        return
    stage = {
        "metadata": "Metadata generation",
        "formats": "DAPS build",
        "worktree": "Worktree creation",
    }[scenario]
    bodies = {str(msg["To"]): msg.get_content() for msg in messages}
    assert set(bodies) == {
        "sles@example.test",
        "sled@example.test",
        "admin@example.test",
    }
    for address, body in bodies.items():
        products = (
            {"sles", "sled"}
            if address == "admin@example.test"
            else {address.split("@")[0]}
        )
        assert {p for p in ("sles", "sled") if f"DC-{p}" in body} == products
        assert body.count(f"  Stage: {stage}") == len(products) * (
            2 if scenario == "formats" else 1
        )
