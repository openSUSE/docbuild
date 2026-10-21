"""Shell completion helpers for the docbuild CLI.

Click provides completion for subcommands and options out of the box. This
module adds value completion for the ``DOCTYPES`` arguments, segment by
segment (``PRODUCT/DOCSETS/LANGS``):

* products come from the :class:`~docbuild.models.product.Product` enum,
* docsets are read from the portal config of the environment,
* languages come from :data:`~docbuild.constants.ALLOWED_LANGUAGES`.

Completion must never break the shell: any problem while loading the
configuration falls back to the wildcard ``*``.
"""

import asyncio
from collections.abc import Iterable
import logging
from pathlib import Path

import click
from click.shell_completion import CompletionItem
from lxml import etree  # type: ignore

from ..config.load import handle_config
from ..config.xml.list import list_all_deliverables
from ..constants import ALLOWED_LANGUAGES, CONFIG_PATHS, DEFAULT_ENV_CONFIG_FILENAME
from ..models.config.env import EnvConfig
from ..models.deliverable import Deliverable
from ..models.doctype import Doctype
from ..models.product import Product
from ..tasks.portal import parse_portal_config
from .defaults import DEFAULT_ENV_CONFIG

log = logging.getLogger(__name__)

#: Errors from loading the environment and portal config during completion:
#: an unreadable file (:class:`OSError`), invalid TOML, settings or
#: ``xi:include`` (:class:`ValueError`, which covers
#: :class:`tomllib.TOMLDecodeError` and :class:`pydantic.ValidationError`),
#: a malformed ``--set-env`` (:class:`click.ClickException`), and invalid
#: XML (:class:`lxml.etree.LxmlError`).
CONFIG_ERRORS = (OSError, ValueError, click.ClickException, etree.LxmlError)


def collect_docsets(
    tree: etree._ElementTree | etree._Element, product: str
) -> set[str]:
    """Return all docset paths of a product found in the portal config.

    :param tree: The parsed portal config.
    :param product: The product acronym, for example ``sles``.
    :return: The set of docset paths, for example ``{"15-SP7", "16.0"}``.
    :raise ValueError: If ``product`` is not a valid product.
    """
    docsets: set[str] = set()
    for node in list_all_deliverables(tree, [Doctype.from_str(f"{product}/*/*")]):
        deli = Deliverable(_node=node)
        if deli.xml.docset_path:
            docsets.add(deli.xml.docset_path)
    return docsets


def load_portal_tree(ctx: click.Context) -> etree._ElementTree | None:
    """Load the portal config referenced by the environment config.

    During completion, the main ``cli`` callback does not run, so the
    environment config is loaded here. ``--env-config`` and ``--set-env``
    from the command line are honored.

    :param ctx: The Click context of the command being completed.
    :return: The parsed portal config, or ``None`` if it cannot be loaded.
    """
    params = ctx.find_root().params
    try:
        _, raw_envconfig, _ = handle_config(
            params.get("env_config"),
            CONFIG_PATHS,
            None,
            str(DEFAULT_ENV_CONFIG_FILENAME),
            DEFAULT_ENV_CONFIG,
        )
        # Imported here to avoid a circular import with the main CLI module
        from .cmd_cli import apply_override

        for override in params.get("env_overrides") or ():
            apply_override(raw_envconfig, override)  # type: ignore[arg-type]

        envconfig = EnvConfig.from_dict(raw_envconfig)  # type: ignore[arg-type]
        portal_config = Path(envconfig.paths.main_portal_config).expanduser()
        return asyncio.run(parse_portal_config(portal_config))

    except CONFIG_ERRORS as err:  # Completion must never break the shell
        log.debug("Cannot load portal config for completion: %s", err)
        return None


def _complete_list(
    prefix: str, incomplete: str, choices: Iterable[str]
) -> list[CompletionItem]:
    """Complete the last item of a comma-separated list.

    :param prefix: Everything before the segment, for example ``sles/``.
    :param incomplete: The segment typed so far, for example ``15-SP7,1``.
    :param choices: All valid values for the segment.
    :return: The matching completion items.
    """
    head, _, last = incomplete.rpartition(",")
    already = set(head.split(",")) if head else set()
    lead = f"{head}," if head else ""
    return [
        CompletionItem(f"{prefix}{lead}{choice}")
        for choice in sorted(choices)
        if choice.startswith(last) and choice not in already
    ]


def complete_doctypes(
    ctx: click.Context,
    param: click.Parameter,
    incomplete: str,
) -> list[CompletionItem]:
    """Complete a doctype (``PRODUCT/DOCSETS/LANGS``) segment by segment.

    Used as ``shell_complete`` callback for ``DOCTYPES`` arguments.

    :param ctx: The Click context of the command being completed.
    :param param: The parameter being completed.
    :param incomplete: The value typed so far.
    :return: The matching completion items.
    """
    segments = incomplete.split("/")

    match segments:
        case [product]:
            return [
                CompletionItem(item.acronym)
                for item in Product
                if item is not Product.ALL and item.acronym.startswith(product)
            ]

        case [product, docsets]:
            choices = {"*"}
            if product and product != "*":
                tree = load_portal_tree(ctx)
                if tree is not None:
                    try:
                        choices |= collect_docsets(tree, product)
                    except ValueError:
                        pass  # Unknown product; offer the wildcard only
            return _complete_list(f"{product}/", docsets, choices)

        case [product, docset, langs]:
            return _complete_list(
                f"{product}/{docset}/", langs, {"*", *ALLOWED_LANGUAGES}
            )

    return []
