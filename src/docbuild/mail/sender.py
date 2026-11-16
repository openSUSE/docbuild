"""Email composer and SMTP dispatcher for build failure notifications."""

from datetime import UTC, datetime
from email.message import EmailMessage
import logging
import os
import smtplib
import ssl

from ..models.config.env import EnvConfig, EnvMail
from .models import FailureRecord

log = logging.getLogger(__name__)


def send_email(
    config: EnvMail,
    to_addrs: list[str],
    subject: str,
    body: str,
) -> bool:
    """Send a notification email using standard-library SMTP.

    Errors are logged without raising to ensure the build exit status is not affected.

    :param config: Mail environment configuration.
    :param to_addrs: List of destination email addresses.
    :param subject: Email subject line.
    :param body: Plain text email body.
    :return: True if the email was successfully sent, False otherwise.
    """
    if not to_addrs:
        return False

    msg = EmailMessage()
    msg["From"] = config.sender
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg.set_content(body)

    password = None
    if config.smtp_password_env:
        password = os.environ.get(config.smtp_password_env)
        if not password:
            log.warning(
                "SMTP password environment variable %r is unset or empty.",
                config.smtp_password_env,
            )

    try:
        ssl_context = ssl.create_default_context()
        if config.smtp_tls:
            server: smtplib.SMTP = smtplib.SMTP_SSL(
                config.smtp_host,
                config.smtp_port,
                timeout=config.timeout,
                context=ssl_context,
            )
        else:
            server = smtplib.SMTP(
                config.smtp_host,
                config.smtp_port,
                timeout=config.timeout,
            )

        with server:
            if config.smtp_starttls and not config.smtp_tls:
                server.starttls(context=ssl_context)
            if config.smtp_user and password:
                server.login(config.smtp_user, password)
            server.send_message(msg)

        log.info("Build failure notification email sent to: %s", ", ".join(to_addrs))
        return True
    except Exception as exc:
        log.error("Failed to send build failure email to %s: %s", to_addrs, exc)
        return False


def _format_deliverable_block(failure: FailureRecord) -> str:
    """Format a single deliverable failure into an accessible text block."""
    header = failure.title or failure.dcfile or f"{failure.product_id}/{failure.docset}"
    details = [
        f"* {header}",
        f"  Stage:       {failure.stage}",
        f"  Product:     {failure.product_id or 'N/A'}",
        f"  Docset:      {failure.docset or 'N/A'}",
        f"  Language:    {failure.lang or 'N/A'}",
        f"  Format:      {failure.format or 'N/A'}",
        f"  DC File:     {failure.dcfile or 'N/A'}",
        f"  Repository:  {failure.repo_url or 'N/A'}",
        f"  Branch:      {failure.branch or 'N/A'}",
    ]
    if failure.commit:
        details.append(f"  Commit:      {failure.commit}")
    if failure.log_path:
        details.append(f"  Log:         {failure.log_path}")

    # Indent error message cleanly
    error_summary = failure.error.strip() if failure.error else "Unknown error"
    indented_error = "\n    ".join(error_summary.splitlines()[:20])
    details.append(f"  Error:\n    {indented_error}")

    return "\n".join(details)


def format_maintainer_email(
    env_name: str,
    env_role: str,
    product_id: str,
    failures: list[FailureRecord],
) -> tuple[str, str]:
    """Compose subject and body for a product maintainer notification."""
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")

    if len(failures) == 1:
        f = failures[0]
        desc = f.dcfile or f.title or f.docset
        subject = f"Failed to build {product_id}/{f.docset}: {desc} ({f.format or 'all'}, {f.lang or 'all'})"
    else:
        subject = f"Failed to build {product_id}: {len(failures)} deliverable(s) failed"

    blocks = "\n\n".join(_format_deliverable_block(f) for f in failures)
    body = (
        f"Cheerio!\n\n"
        f"Docbuild failed to build deliverable(s) for product '{product_id}':\n\n"
        f"Environment: {env_name} ({env_role})\n"
        f"Finished:    {timestamp}\n\n"
        f"Failed deliverables:\n\n"
        f"{blocks}\n\n"
        f"---\n"
        f"Automated notification from Docbuild.\n"
    )
    return subject, body


def format_admin_digest(
    env_name: str,
    env_role: str,
    failures: list[FailureRecord],
) -> tuple[str, str]:
    """Compose subject and body for a run-wide administrator digest."""
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    subject = (
        f"[Docbuild] Build failure digest: {len(failures)} failure(s) in {env_name}"
    )

    blocks = "\n\n".join(_format_deliverable_block(f) for f in failures)
    body = (
        f"Docbuild encountered build failure(s) in environment '{env_name}' ({env_role}).\n\n"
        f"Finished: {timestamp}\n"
        f"Total failed deliverables / stages: {len(failures)}\n\n"
        f"Failed deliverables:\n\n"
        f"{blocks}\n\n"
        f"---\n"
        f"Automated failure digest from Docbuild.\n"
    )
    return subject, body


def notify_build_failures(env: EnvConfig, failures: list[FailureRecord]) -> None:
    """Route failure records to maintainers and admins if email is enabled.

    :param env: The active environment configuration.
    :param failures: List of captured failure records.
    """
    if not env.general.enable_mail:
        log.debug("Email notifications are disabled (general.enable_mail=false).")
        return

    if not failures:
        return

    # 1. Product maintainer notifications (grouped by product_id)
    by_product: dict[str, list[FailureRecord]] = {}
    for f in failures:
        if f.product_id:
            by_product.setdefault(f.product_id, []).append(f)

    for product_id, prod_failures in by_product.items():
        # Deduplicate maintainer emails
        recipients = sorted({m for f in prod_failures for m in f.maintainers if m})
        if recipients:
            subject, body = format_maintainer_email(
                env.general.name,
                str(env.general.role),
                product_id,
                prod_failures,
            )
            send_email(env.mail, recipients, subject, body)
        else:
            log.debug("No maintainer emails configured for product %r.", product_id)

    # 2. Administrator run-wide digest
    if env.mail.admin_emails:
        admin_recipients = sorted(set(env.mail.admin_emails))
        subject, body = format_admin_digest(
            env.general.name,
            str(env.general.role),
            failures,
        )
        send_email(env.mail, admin_recipients, subject, body)
