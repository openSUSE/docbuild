"""Collect details of failed build operations and deliver product and admin digests."""

from collections import defaultdict
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import EmailMessage
import logging
import os
from pathlib import Path
import re
import smtplib
import ssl
from types import TracebackType
from typing import Self

from jinja2 import Environment, PackageLoader

from .logging import active_log_path
from .models.config.env import EnvConfig, EnvMail, validate_mailbox
from .models.deliverable import Deliverable

log = logging.getLogger(__name__)


@dataclass
class Failure:
    """Details retained alongside the pipeline's existing failure result."""

    stage: str
    summary: str
    deliverable: Deliverable | None = None
    format: str | None = None


_failures: ContextVar[dict[object, Failure] | None] = ContextVar(
    "build_failures", default=None
)


def record_failure(
    stage: str,
    error: object,
    deliverable: Deliverable | None = None,
    fmt: str | None = None,
    *,
    worktree: Path | None = None,
) -> None:
    """Keep a short diagnostic only while a mail-enabled build is running."""
    failures = _failures.get()
    if failures is not None:
        if isinstance(error, BaseExceptionGroup):
            for cause in error.exceptions:
                record_failure(stage, cause, deliverable, fmt, worktree=worktree)
            return
        if (
            deliverable is not None
            and next(deliverable.xml.node.iterancestors("product"), None) is None
        ):
            deliverable = None
        summary = (
            " ".join(str(error).splitlines()[-2:]).strip() or "No diagnostic output."
        )
        if worktree is not None:
            # A shared checkout directory can contain a different product's ID.
            summary = summary.replace(str(worktree), "<worktree>").replace(
                worktree.name, "<worktree>"
            )
        summary = re.sub(r"(://)[^/\s]+@", r"\1", summary)
        # The same cache entry can be visited directly and through a product xref.
        key = (
            (deliverable.xml.node, stage, fmt, summary)
            if deliverable is not None
            else object()
        )
        failures.setdefault(key, Failure(stage, summary[:500], deliverable, fmt))


class BuildNotifications:
    """Scope diagnostics to one CLI invocation, including its asynchronous workers."""

    def __init__(self, env: EnvConfig) -> None:
        self.env = env
        self.stage = "Build"
        self.result = 0
        self._records: dict[object, Failure] = {}
        self.token: Token | None = None

    @property
    def failures(self) -> list[Failure]:
        """Return distinct failures in the order they were recorded."""
        return list(self._records.values())

    def __enter__(self) -> Self:
        """Enable collection for the duration of this build."""
        self.token = _failures.set(
            self._records if self.env.general.enable_mail else None
        )
        return self

    def __exit__(
        self,
        typ: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Preserve the pipeline result even when notification preparation fails."""
        try:
            if not self.env.general.enable_mail or self.result == 130:
                return
            if isinstance(exc, Exception):
                record_failure(self.stage, exc)
            elif exc is not None or self.result == 0:
                return
            elif not self._records:
                record_failure(self.stage, f"Stage exited with status {self.result}")
            if self.env.mail is None:
                log.warning(
                    "Build failure email skipped: no [mail] settings configured"
                )
                return
            notify(self.env.mail, self.env.general.name, self.failures)
        except Exception as error:
            # Diagnostic formatting and mail delivery must never mask the build error.
            log.error("Cannot prepare build failure email (%s)", type(error).__name__)
        finally:
            if self.token is not None:
                _failures.reset(self.token)


def send_message(config: EnvMail, message: EmailMessage) -> None:
    """Deliver one digest through the configured relay."""
    username = os.environ.get("DOCBUILD_SMTP_USERNAME")
    password = os.environ.get("DOCBUILD_SMTP_PASSWORD")
    if bool(username) != bool(password):
        log.error(
            "SMTP authentication requires both DOCBUILD_SMTP_USERNAME and DOCBUILD_SMTP_PASSWORD"
        )
        return
    if config.tls == "implicit":
        connection = smtplib.SMTP_SSL(
            config.smtp_host,
            config.smtp_port,
            timeout=config.timeout,
            context=ssl.create_default_context(),
        )
    else:
        connection = smtplib.SMTP(
            config.smtp_host, config.smtp_port, timeout=config.timeout
        )
    with connection as client:
        if config.tls == "starttls":
            client.starttls(context=ssl.create_default_context())
        if username and password:
            client.login(username, password)
        refused = client.send_message(message)
        if refused:
            log.warning("SMTP relay refused %d recipient(s)", len(refused))


def notify(config: EnvMail, environment: str, failures: list[Failure]) -> None:
    """Send each product's failures to its contacts and all failures to admins."""
    groups: dict[str, list[Failure]] = defaultdict(list)
    contacts: dict[str, set[str]] = defaultdict(set)
    for failure in failures:
        d = failure.deliverable
        if d is None or not (product := d.xml.product_id):
            continue
        groups[product].append(failure)
        for text in d.xml.product_node.findall("maintainers/contact"):
            try:
                contacts[product].add(validate_mailbox(text.text or ""))
            except ValueError:
                log.warning("Ignoring invalid maintainer email for %s", product)

    template = Environment(
        loader=PackageLoader("docbuild"), trim_blocks=True
    ).get_template("build-failure.txt.jinja")
    finished = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    log_path = active_log_path()
    digests = [
        (f"Build failed: {p}", contacts[p], details) for p, details in groups.items()
    ]
    digests.append(
        (f"Build failure digest: {environment}", set(config.admin_emails), failures)
    )
    for subject, recipients, details in digests:
        if not recipients:
            continue
        try:
            message = EmailMessage()
            message["Subject"] = subject
            message["From"] = config.sender
            message["To"] = ", ".join(sorted(recipients))
            message.set_content(
                template.render(
                    environment=environment,
                    finished=finished,
                    failures=details,
                    log_path=log_path,
                )
            )
            send_message(config, message)
        except Exception as error:
            # A relay response may echo AUTH data. Only report the failure type.
            log.error("Could not send %s (%s)", subject, type(error).__name__)
