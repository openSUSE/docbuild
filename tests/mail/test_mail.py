"""Unit tests for the mail notification subsystem."""

from email.message import EmailMessage
from unittest.mock import MagicMock, patch

from lxml import etree
import pytest

from docbuild.mail.models import FailureCollector, FailureRecord
from docbuild.mail.sender import (
    format_admin_digest,
    format_maintainer_email,
    notify_build_failures,
    send_email,
)
from docbuild.models.config.env import EnvConfig, EnvMail
from docbuild.models.deliverable import Deliverable
from docbuild.models.deliverable.view import DeliverableXMLView

# --- Config Tests ---


def test_env_mail_defaults() -> None:
    """Verify default values for EnvMail configuration."""
    mail = EnvMail()
    assert mail.admin_emails == []
    assert mail.sender == "docbuild-noreply@suse.com"
    assert mail.smtp_host == "localhost"
    assert mail.smtp_port == 25
    assert mail.smtp_tls is False
    assert mail.smtp_starttls is False
    assert mail.timeout == 30.0
    assert mail.smtp_user is None
    assert mail.smtp_password_env is None


def test_env_mail_custom() -> None:
    """Verify custom settings for EnvMail."""
    mail = EnvMail(
        admin_emails=["admin@example.com"],
        sender="ci@example.com",
        smtp_host="mail.example.com",
        smtp_port=587,
        smtp_starttls=True,
        timeout=15.0,
        smtp_user="ci-user",
        smtp_password_env="CI_SMTP_PASS",
    )
    assert mail.admin_emails == ["admin@example.com"]
    assert mail.sender == "ci@example.com"
    assert mail.smtp_host == "mail.example.com"
    assert mail.smtp_port == 587
    assert mail.smtp_starttls is True
    assert mail.timeout == 15.0
    assert mail.smtp_user == "ci-user"
    assert mail.smtp_password_env == "CI_SMTP_PASS"


def test_env_config_includes_mail() -> None:
    """Verify EnvConfig integrates the mail section."""
    config = EnvConfig()
    assert isinstance(config.mail, EnvMail)
    assert config.mail.smtp_port == 25


# --- Model and Extraction Tests ---


def test_maintainer_extraction_from_xml() -> None:
    """Verify DeliverableXMLView extracts maintainer contacts from product."""
    xml_data = """
    <portal>
      <product xml:id="test-prod">
        <name>Test Product</name>
        <maintainers>
          <contact>maintainer1@example.com</contact>
          <contact>  maintainer2@example.com  </contact>
        </maintainers>
        <docset xml:id="ds1" path="1.0">
          <resources>
            <locale lang="en-us">
              <deliverable xml:id="deliv1">
                <dc file="DC-test"/>
              </deliverable>
            </locale>
          </resources>
        </docset>
      </product>
    </portal>
    """
    root = etree.fromstring(xml_data)
    deliv_node = root.xpath("//deliverable")[0]
    view = DeliverableXMLView(deliv_node)

    assert view.maintainers == ["maintainer1@example.com", "maintainer2@example.com"]

    deliverable = Deliverable(deliv_node)
    assert deliverable.maintainers == [
        "maintainer1@example.com",
        "maintainer2@example.com",
    ]


def test_maintainer_extraction_when_absent() -> None:
    """Verify empty list is returned when maintainers are absent."""
    xml_data = """
    <portal>
      <product xml:id="test-prod">
        <name>Test Product</name>
        <docset xml:id="ds1" path="1.0">
          <resources>
            <locale lang="en-us">
              <deliverable xml:id="deliv1">
                <dc file="DC-test"/>
              </deliverable>
            </locale>
          </resources>
        </docset>
      </product>
    </portal>
    """
    root = etree.fromstring(xml_data)
    deliv_node = root.xpath("//deliverable")[0]
    view = DeliverableXMLView(deliv_node)
    assert view.maintainers == []


def test_failure_collector() -> None:
    """Verify FailureCollector thread-safe recording and grouping."""
    collector = FailureCollector()
    assert collector.failures == []

    f1 = FailureRecord(
        product_id="sles",
        docset="15-sp5",
        lang="en-us",
        format="html",
        stage="daps build",
        error="DAPS syntax error",
        maintainers=("sles@example.com",),
        dcfile="DC-sles",
    )
    f2 = FailureRecord(
        product_id="sles",
        docset="15-sp5",
        lang="de-de",
        format="pdf",
        stage="rsync",
        error="Target directory not writable",
        maintainers=("sles@example.com",),
    )
    f3 = FailureRecord(
        product_id="",
        stage="metadata generation",
        error="Global metadata validation failed",
    )

    collector.add(f1)
    collector.add(f2)
    collector.add(f3)

    assert len(collector.failures) == 3

    by_prod = collector.by_product()
    assert "sles" in by_prod
    assert len(by_prod["sles"]) == 2

    unatt = collector.unattributed()
    assert len(unatt) == 1
    assert unatt[0].stage == "metadata generation"


# --- Formatting Tests ---


def test_format_maintainer_email_single() -> None:
    """Verify single failure email formatting."""
    f = FailureRecord(
        product_id="sles-sap",
        docset="16.0",
        lang="en-us",
        format="html",
        stage="daps build",
        error="Referenced image 'installation.png' was not found.",
        maintainers=("sap@example.com",),
        dcfile="DC-SAP-about",
        title="SAP Installation Guide",
    )
    subj, body = format_maintainer_email("production", "production", "sles-sap", [f])
    assert "sles-sap/16.0" in subj
    assert "DC-SAP-about" in subj
    assert "html, en-us" in subj
    assert "Referenced image 'installation.png' was not found." in body
    assert "SAP Installation Guide" in body
    assert "Environment: production (production)" in body


def test_format_maintainer_email_multiple() -> None:
    """Verify multiple failures email formatting."""
    f1 = FailureRecord(product_id="sles", docset="15", error="err 1")
    f2 = FailureRecord(product_id="sles", docset="15", error="err 2")
    subj, body = format_maintainer_email("test-env", "production", "sles", [f1, f2])
    assert "Failed to build sles: 2 deliverable(s) failed" in subj
    assert "err 1" in body
    assert "err 2" in body


def test_format_admin_digest() -> None:
    """Verify administrator failure digest formatting."""
    f1 = FailureRecord(product_id="sles", docset="15", error="Error A")
    f2 = FailureRecord(product_id="", stage="metadata", error="Error Global")
    subj, body = format_admin_digest("staging", "staging", [f1, f2])
    assert "[Docbuild] Build failure digest: 2 failure(s) in staging" in subj
    assert "Error A" in body
    assert "Error Global" in body


# --- SMTP Dispatcher Tests ---


def test_send_email_empty_recipients() -> None:
    """Verify send_email returns False when recipients list is empty."""
    config = EnvMail()
    assert send_email(config, [], "Subject", "Body") is False


@patch("smtplib.SMTP")
def test_send_email_plain_smtp(mock_smtp_cls: MagicMock) -> None:
    """Verify send_email succeeds over unencrypted SMTP."""
    mock_server = mock_smtp_cls.return_value
    mock_server.__enter__.return_value = mock_server

    config = EnvMail(smtp_host="localhost", smtp_port=25)
    success = send_email(config, ["user@example.com"], "Test Subject", "Test Body")

    assert success is True
    mock_smtp_cls.assert_called_once_with("localhost", 25, timeout=30.0)
    mock_server.send_message.assert_called_once()
    msg: EmailMessage = mock_server.send_message.call_args[0][0]
    assert msg["From"] == "docbuild-noreply@suse.com"
    assert msg["To"] == "user@example.com"
    assert msg["Subject"] == "Test Subject"
    assert msg.get_content().strip() == "Test Body"


@patch("smtplib.SMTP")
def test_send_email_starttls_and_auth(
    mock_smtp_cls: MagicMock, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify send_email performs STARTTLS and authentication when configured."""
    monkeypatch.setenv("TEST_SMTP_PASS", "secret_pass")
    mock_server = mock_smtp_cls.return_value
    mock_server.__enter__.return_value = mock_server

    config = EnvMail(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_starttls=True,
        smtp_user="ci-user",
        smtp_password_env="TEST_SMTP_PASS",
    )
    success = send_email(config, ["recipient@example.com"], "Auth Test", "Body Content")

    assert success is True
    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("ci-user", "secret_pass")
    mock_server.send_message.assert_called_once()


@patch("smtplib.SMTP_SSL")
def test_send_email_direct_ssl(mock_ssl_cls: MagicMock) -> None:
    """Verify send_email uses SMTP_SSL when smtp_tls is True."""
    mock_server = mock_ssl_cls.return_value
    mock_server.__enter__.return_value = mock_server

    config = EnvMail(
        smtp_host="smtp.example.com",
        smtp_port=465,
        smtp_tls=True,
    )
    success = send_email(config, ["recipient@example.com"], "SSL Test", "Body Content")

    assert success is True
    mock_ssl_cls.assert_called_once()
    mock_server.send_message.assert_called_once()


@patch("smtplib.SMTP")
def test_send_email_handles_smtp_error(mock_smtp_cls: MagicMock) -> None:
    """Verify send_email logs errors and returns False without raising."""
    mock_smtp_cls.side_effect = OSError("Connection refused")

    config = EnvMail(smtp_host="invalid-host")
    success = send_email(config, ["recipient@example.com"], "Fail Test", "Body")
    assert success is False


# --- notify_build_failures Routing Tests ---


def test_notify_build_failures_disabled() -> None:
    """Verify notify_build_failures does nothing when enable_mail is False."""
    config = EnvConfig()
    config.general.enable_mail = False

    failures = [FailureRecord(product_id="sles", error="Error")]
    with patch("docbuild.mail.sender.send_email") as mock_send:
        notify_build_failures(config, failures)
        mock_send.assert_not_called()


def test_notify_build_failures_routing() -> None:
    """Verify routing to product maintainers and admin digest with deduplication."""
    config = EnvConfig()
    config.general.enable_mail = True
    config.mail.admin_emails = ["admin1@example.com", "admin2@example.com"]

    failures = [
        FailureRecord(
            product_id="sles",
            docset="15",
            error="Error 1",
            maintainers=("sles-maint@example.com", "shared@example.com"),
        ),
        FailureRecord(
            product_id="sles",
            docset="15",
            error="Error 2",
            maintainers=("sles-maint@example.com",),  # Duplicate contact
        ),
        FailureRecord(
            product_id="leap",
            docset="16",
            error="Error 3",
            maintainers=("leap-maint@example.com",),
        ),
        FailureRecord(
            product_id="",
            stage="metadata",
            error="Global Error",
            maintainers=(),
        ),
    ]

    with patch("docbuild.mail.sender.send_email") as mock_send:
        mock_send.return_value = True
        notify_build_failures(config, failures)

        # 3 calls expected: sles maintainers, leap maintainers, admin digest
        assert mock_send.call_count == 3

        calls = mock_send.call_args_list

        # Call 1: SLES maintainers (deduplicated)
        sles_call = next(c for c in calls if "sles-maint@example.com" in c[0][1])
        assert sles_call[0][1] == ["shared@example.com", "sles-maint@example.com"]
        assert "Failed to build sles: 2 deliverable(s) failed" in sles_call[0][2]

        # Call 2: Leap maintainers
        leap_call = next(c for c in calls if "leap-maint@example.com" in c[0][1])
        assert leap_call[0][1] == ["leap-maint@example.com"]

        # Call 3: Admin digest
        admin_call = next(c for c in calls if "admin1@example.com" in c[0][1])
        assert admin_call[0][1] == ["admin1@example.com", "admin2@example.com"]
        assert "[Docbuild] Build failure digest: 4 failure(s)" in admin_call[0][2]
