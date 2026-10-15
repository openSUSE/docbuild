"""Pydantic models for environment configuration.

This module defines the Pydantic models for parsing and validating the environment
configuration (``env.toml``). The models serve as the single source of truth for
default values.

Below is a complete example of the default configuration in JSON with comments
format, showing all available fields and their default values. Placeholders
like ``{general.name}`` are resolved from other values in the configuration.
Placeholders with double curly braces like ``{{product}}`` are resolved at
runtime during the build process.

.. code-block:: javascript

    {
        // General settings for the documentation server environment.
        // Corresponds to the EnvGeneral model.
        "general": {
            "name": "default-env",
            "role": "production",
            "enable_mail": false,
            "default_lang": "en-us",
            "languages": [
                "de-de", "en-us", "es-es", "fr-fr", "ja-jp", "ko-kr", "pt-br", "zh-cn"
            ],
            "canonical_url_domain": "https://documentation.suse.com"
        },
        // All file system path definitions.
        // Corresponds to the EnvPaths model.
        "paths": {
            "root_config_dir": "~/.config/docbuild",
            "config_dir": "{root_config_dir}/config.d",
            "main_portal_config": "{config_dir}/portal.xml",
            "portal_rncschema": "{root_config_dir}/portal-config.rnc",
            "jinja_dir": "~/.local/share/docbuild/jinja",
            "server_rootfiles_dir": "{root_config_dir}/server-root-files",
            "prebuilt_dir": "{base_server_cache_dir}/build",
            "tmp_repo_dir": "~/.local/state/docbuild/repos/branches",
            "repo_dir": "~/.local/state/docbuild/repos/permanent",
            "base_cache_dir": "~/.cache/docbuild",
            "base_server_cache_dir": "{base_cache_dir}/{general.name}",
            "meta_cache_dir": "{base_server_cache_dir}/meta",
            "json_cache_dir": "{base_server_cache_dir}/json",
            "runtime_base_dir": "/run/user/1000/docbuild",
            "lock_dir": "{runtime_base_dir}/locks",
            // Temporary paths, corresponds to the EnvTmpPaths model.
            "tmp": {
                "tmp_base_dir": "/tmp/docbuild",
                "tmp_dir": "{tmp_base_dir}/{general.name}",
                "tmp_deliverable_dir": "{tmp_dir}/deliverable",
                "tmp_metadata_dir": "{tmp_dir}/metadata",
                "tmp_build_base_dir": "{tmp_dir}/build",
                "tmp_build_dir_dyn": "{{product}}-{{docset}}-{{lang}}",
                "tmp_out_dir": "{tmp_dir}/out",
                "log_dir": "~/.local/state/docbuild/{general.name}/log",
                "tmp_deliverable_name_dyn": "{{product}}_{{docset}}_{{lang}}_XXXXXX"
            },
            // Target paths for deployment, corresponds to the EnvTargetPaths model.
            "target": {
                "target_base_dir": "~/Documents/docbuild/target",
                "target_dir_dyn": "{{lang}}/{{product}}/{{docset}}",
                "backup_dir": "~/.local/state/docbuild/{general.name}/backup"
            }
        },
        // Settings for DAPS and container builds.
        // Corresponds to the EnvBuild model.
        "build": {
            // DAPS command templates, corresponds to the EnvBuildDaps model.
            "daps": {
                "command": "daps",
                "meta": "daps --builddir={{builddir}} -d {{dcfile}} metadata --output {{output}}",
                "list_srcfiles": "{build.daps.command} -d {{dcfile}} list-srcfiles --hashes",
                "html": "{build.daps.command} --builddir={{builddir}} -d {{dcfile}} html",
                "pdf": "{build.daps.command} --builddir={{builddir}} -d {{dcfile}} pdf",
                "single_html": "{build.daps.command} --builddir={{builddir}} -d {{dcfile}} single-html",
                "epub": "{build.daps.command} --builddir={{builddir}} -d {{dcfile}} epub"
            },
            // Container settings, corresponds to the EnvBuildContainer model.
            "container": {
                "image": "registry.opensuse.org/documentation/containers/15.6/opensuse-daps-toolchain:latest"
            }
        },
        // Custom XSLT parameters passed to DAPS.
        // Corresponds to the EnvXslt model.
        "xslt": {
            "common": {},
            "html": {},
            "pdf": {}
        },
        // Remote destination for publishing built documentation.
        // Both keys are unset by default, so publish is disabled unless
        // [remote] is configured. Corresponds to the EnvRemote model.
        "remote": {"server": null, "path": null}
    }
"""

from copy import deepcopy
from pathlib import Path
import re
from typing import Annotated, Any, Final, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    IPvAnyAddress,
    field_serializer,
    field_validator,
    model_validator,
)

from ...config.app import (
    CircularReferenceError,
    PlaceholderResolutionError,
    PlaceholderSyntaxError,
    replace_placeholders,
)
from ...constants import (
    ALLOWED_LANGUAGES,
    APP_NAME,
    CACHE_HOME,
    CONFIG_HOME,
    DATA_HOME,
    DEFAULT_ENV_NAME,
    HOSTNAME_REGEX,
    RUNTIME_DIR,
    SSH_USERNAME_REGEX,
    STATE_HOME,
)
from ..envroles import EnvRole
from ..language import LanguageCode
from ..path import AbsolutePath, WritablePath

# --- Custom Types and Utilities ---

# A type for domain names, validated with a regex.
DomainName = Annotated[
    str,
    Field(
        pattern=r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$",
        title="Valid Domain Name",
        description="A string representing a fully qualified domain name (FQDN).",
        examples=["example.com", "sub.domain.net"],
    ),
]


# Patterns identifying rsync-style remote destinations in a path string.
REMOTE_URL_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    # Standard URI scheme (e.g., "https://", "git://", "ssh://")
    re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://"),
    # SCP-style remote location (e.g., "user@host:path/to/repo")
    re.compile(r"^[^/\s@:]+@[^/\s:]+:"),
    # Rsync daemon module access (e.g., "host::module/path")
    re.compile(r"^[^/\s@:]+::"),
    # Short SSH remote path without user (e.g., "host:/path/to/repo")
    re.compile(r"^[^/\s@:]+:/"),
)


def target_is_remote(value: str) -> bool:
    """Check whether *value* looks like an rsync-style remote destination.

    A value is remote if it matches one of the following forms:

    * ``scheme://`` (for example ``rsync://host/module`` or ``ssh://host/x``)
    * ``user@host:`` (for example ``user@host:/srv/docs``)
    * ``host::`` (for example ``host::module``)
    * ``host:/`` (for example ``host:/srv/docs``)

    Everything else is treated as local, including relative paths,
    ``my:dir`` and ``a:b/c`` (no drive-letter special cases are needed).

    :param value: The path string to inspect.
    :return: True if the value looks like a remote destination; False otherwise.
    """
    return any(pattern.match(value) for pattern in REMOTE_URL_PATTERNS)


# --- Build Sub-Models (To allow extra sections in env.toml) ---


class EnvBuildDaps(BaseModel):
    """Configuration for daps command execution."""

    model_config = ConfigDict(extra="allow")

    command: str = Field(
        default="daps",
        title="DAPS Command",
        description="The base daps command executable.",
        examples=["daps"]
    )
    "The base command used for DAPS execution."

    meta: str = Field(
        default="{build.daps.command} --builddir={{builddir}} -d {{dcfile}} metadata --output {{output}}",
        title="DAPS Metadata Subcommand",
        description="The daps metadata command for extracting info.",
        examples=["daps metadata"]
    )
    "The command used to extract DAPS metadata."

    list_srcfiles: str = Field(
        default="{build.daps.command} -d {{dcfile}} list-srcfiles --hashes",
        title="DAPS List Source Files Template",
        description="The template string to run list-srcfiles.",
    )
    "The command template used to list source files with hashes."

    html: str = Field(
        default="{build.daps.command} --builddir {{builddir}} -d {{dcfile}} html",
        title="DAPS HTML Command Template",
        description="The template string to build HTML.",
    )
    "The command template used to build HTML."

    pdf: str = Field(
        default="{build.daps.command} --builddir {{builddir}} -d {{dcfile}} pdf",
        title="DAPS PDF Command Template",
        description="The template string to build PDF.",
    )
    "The command template used to build PDF."

    single_html: str = Field(
        default="{build.daps.command} --builddir {{builddir}} -d {{dcfile}} single-html",
        title="DAPS Single HTML Command Template",
        description="The template string to build Single HTML.",
    )
    "The command template used to build Single HTML."

    epub: str = Field(
        default="{build.daps.command} --builddir {{builddir}} -d {{dcfile}} epub",
        title="DAPS EPUB Command Template",
        description="The template string to build EPUB.",
    )
    "The command template used to build EPUB."


class EnvBuildContainer(BaseModel):
    """Configuration for container usage."""

    model_config = ConfigDict(extra="allow")

    image: str = Field(
        default="registry.opensuse.org/documentation/containers/15.6/opensuse-daps-toolchain:latest",
        title="Container Image",
        description="The container registry path or image name.",
        examples=["registry.opensuse.org/documentation/containers/15.6/opensuse-daps-toolchain:latest"]
    )
    "The container image used for the build environment."


class EnvBuild(BaseModel):
    """Configuration for docbuild build execution."""

    model_config = ConfigDict(extra="allow")

    build_llmstxt: bool = Field(
        default=True,
        title="Build LLMs Text",
        description="Whether to generate Markdown files and llms.txt for AI bots.",
    )

    daps: EnvBuildDaps = Field(default_factory=EnvBuildDaps)
    container: EnvBuildContainer = Field(default_factory=EnvBuildContainer)


# --- Configuration Models ---


class EnvGeneral(BaseModel):
    """Defines general configuration."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        default=DEFAULT_ENV_NAME,
        title="Environment Name",
        description="A human-readable identifier for the environment.",
        examples=["documentation-suse-com", "docserv-suse-de"],
    )
    "The descriptive name of the environment."

    role: EnvRole = Field(
        default=EnvRole.PRODUCTION,
        title="Environment Role",
        description="The operational role of the environment.",
        examples=["production"],
    )
    "The environment type, used for build behavior differences."

    enable_mail: bool = Field(
        default=False,
        title="Enable Email",
        description="Flag to enable email sending features (e.g., build notifications).",
        examples=[True],
    )
    "Whether email functionality should be active."

    default_lang: LanguageCode = Field(
        default=LanguageCode(language="en-us"),
        title="Default Language",
        description="The primary language code (e.g., 'en') used for non-localized content.",
        examples=["en-us", "de-de", "ja-jp"],
    )
    "The default language code."

    languages: list[LanguageCode] = Field(
        default_factory=lambda: [LanguageCode(language=lang) for lang in ALLOWED_LANGUAGES],
        title="Supported Languages",
        description="A list of all language codes supported by this documentation instance.",
        examples=[["en-us", "de-de", "fr-fr"]],
    )
    "A list of supported language codes."

    canonical_url_domain: HttpUrl = Field(
        default=HttpUrl("https://documentation.suse.com"),
        title="Canonical URL Domain",
        description="The base domain used to construct canonical URLs for SEO purposes.",
        examples=["https://docs.example.com"],
    )
    "The canonical domain for URLs."

    # --- Custom Serialization for LanguageCode Models ---
    @field_serializer("default_lang")
    def serialize_default_lang(self, lang_obj: LanguageCode) -> str:
        """Serialize the default LanguageCode model to a string."""
        return lang_obj.language

    @field_serializer("languages")
    def serialize_languages(self, lang_list: list[LanguageCode]) -> list[str]:
        """Serialize the list of LanguageCode models to strings."""
        return [lang_obj.language for lang_obj in lang_list]


class EnvTmpPaths(BaseModel):
    """Defines temporary paths."""

    model_config = ConfigDict(extra="forbid")

    tmp_base_dir: WritablePath = Field(
        default=f"/tmp/{APP_NAME}",
        title="Temporary Base Directory",
        description="The root directory for all temporary build artifacts.",
        examples=["/var/tmp/docbuild/"],
    )
    "Root path for temporary files."

    tmp_dir: WritablePath = Field(
        default="{tmp_base_dir}/{general.name}",
        title="General Temporary Directory for specific server",
        description=(
            "A general-purpose subdirectory within the base temporary path to "
            "distinguish between different servers."
        ),
        examples=["/var/tmp/docbuild/doc-example-com"],
    )
    "General temporary directory."

    tmp_deliverable_dir: WritablePath = Field(
        default="{tmp_dir}/deliverable",
        title="Temporary Deliverable Directory",
        description="The directory where deliverable repositories are cloned and processed.",
        examples=["/var/tmp/docbuild/doc-example-com/deliverable/"],
    )
    "Directory for temporary deliverable clones."

    tmp_metadata_dir: WritablePath = Field(
        default="{tmp_dir}/metadata",
        title="Temporary Metadata Directory",
        description="Temporary directory for metadata files.",
        examples=["/var/tmp/docbuild/doc-example-com/metadata"],
    )
    "Temporary metadata directory."

    # SPLIT: static base directory (validated)
    tmp_build_base_dir: WritablePath = Field(
        default="{tmp_dir}/build",
        title="Temporary Build Base Directory",
        description="The base directory where intermediate build files are stored.",
        examples=["/var/tmp/docbuild/doc-example-com/build/"],
    )
    "Base path for build output."

    # SPLIT: dynamic suffix (string only, not validated as path)
    # Added a default value so it's not required in defaults.py or user configs
    tmp_build_dir_dyn: str = Field(
        default="{{product}}-{{docset}}-{{lang}}",
        title="Temporary Build Directory Suffix",
        description="The dynamic part of the build path containing runtime placeholders.",
        examples=["{{product}}-{{docset}}-{{lang}}"],
    )
    "Dynamic suffix for build directory."

    tmp_out_dir: WritablePath = Field(
        default="{tmp_dir}/out",
        title="Temporary Output Directory",
        description="The final temporary directory where built artifacts land before deployment.",
        examples=["/var/tmp/docbuild/doc-example-com/out/"],
    )
    "Temporary final output directory."

    log_dir: WritablePath = Field(
        default=f"{STATE_HOME}/{{general.name}}/log",
        title="Log Directory",
        description="The directory where build logs and application logs are stored.",
        examples=["/var/tmp/docbuild/doc-example-com/log"],
    )
    "Directory for log files."

    # RENAMED: To indicate this is a dynamic template
    tmp_deliverable_name_dyn: str = Field(
        default="{{product}}_{{docset}}_{{lang}}_XXXXXX",
        title="Temporary Deliverable Name (Dynamic)",
        description=(
            "The dynamic template name used for the current deliverable being built."
        ),
        examples=["{{product}}_{{docset}}_{{lang}}_XXXXXX"],
    )
    "Temporary deliverable name template."


class EnvTargetPaths(BaseModel):
    """Defines target paths."""

    model_config = ConfigDict(extra="forbid")

    # SPLIT: static local base directory
    target_base_dir: str = Field(
        default=f"{Path.home()}/Documents/{APP_NAME}/target",
        title="Target Base Directory",
        description=(
            "The local base directory where build writes its deliverables. "
            "The remote destination is configured in the [remote] section."
        ),
        examples=["~/Documents/docbuild/target"],
    )
    "The local base directory where build writes its deliverables."

    # SPLIT: dynamic suffix
    target_dir_dyn: str = Field(
        default="{{lang}}/{{product}}/{{docset}}",
        title="Target Directory Suffix",
        description=(
            "The dynamic suffix of the path under the local target_base_dir "
            "where build writes its deliverables."
        ),
        examples=["{{lang}}/{{product}}/{{docset}}"],
    )
    "Dynamic suffix for the target directory under target_base_dir."

    backup_dir: Path = Field(
        default=f"{STATE_HOME}/{{general.name}}/backup",
        title="Build Server Backup Directory",
        description="The location on the build server before it is synced to the target path.",
        examples=["/var/lib/docbuild/backups"],
    )
    "Local directory for storing build backups before deployment."

    @field_validator("target_base_dir")
    @classmethod
    def _reject_remote_target_base_dir(cls, value: str) -> str:
        """Reject remote-looking destination strings.

        Remote destinations are configured in the ``[remote]`` section instead
        of as rsync-style ``target_base_dir`` values.

        :param value: The configured ``target_base_dir`` value.
        :return: The unchanged value.
        :raises ValueError: If the value looks like a remote path.
        """
        if target_is_remote(value):
            raise ValueError(
                f"target_base_dir must be a local directory, but {value!r} looks like "
                "a remote destination. Migrate the remote destination to the [remote] "
                "section and keep target_base_dir local."
            )
        return value


class EnvPaths(BaseModel):
    """Configuration for file and directory paths."""

    model_config = ConfigDict(extra="allow")

    llmstxt_dir: str = Field(
        default="docs",
        title="LLMs Text Directory",
        description="Directory name to store the generated llms.txt and Markdown files.",
    )

    config_dir: Path = Field(
        default="{root_config_dir}/config.d",
        title="Configuration Directory",
        description="The configuration directory containing application and environment files (e.g. app.toml).",
        examples=["/etc/docbuild/config.d"],
    )
    "Path to configuration files."

    main_portal_config: Path = Field(
        default="{config_dir}/portal.xml",
        title="Main Portal XML Configuration File",
        description="Path of the main Portal XML configuration file.",
        examples=[
            "/etc/docbuild/config.d/portal.xml",
            " ~/.config/docbuild/config.d/portal.xml"
        ],
    )
    "Path to the main portal XML configuration file."

    portal_rncschema: Path = Field(
        default="{root_config_dir}/portal-config.rnc",
        title="Portal RELAX NG (RNC) Schema File",
        description=(
            "Path of the RELAX NG (RNC) schema file used for "
            "validating the Portal configuration."
        ),
        examples=[
            "/etc/docbuild/portal-config.rnc",
            " ~/.config/docbuild/portal-config.rnc"
        ],
    )
    "Path to the portal RELAX NG (RNC) schema file."

    root_config_dir: Path = Field(
        default=CONFIG_HOME,
        title="Root Configuration Directory",
        description="The highest-level directory containing common config files.",
        examples=["/etc/docbuild"],
    )
    "Path to the root configuration files."

    jinja_dir: Path = Field(
        default=f"{DATA_HOME}/jinja",
        title="Jinja Template Directory",
        description="Directory containing environment-specific Jinja templates.",
        examples=["/etc/docbuild/jinja-doc-suse-com"],
    )
    "Path for Jinja templates."

    server_rootfiles_dir: Path = Field(
        default="{root_config_dir}/server-root-files",
        title="Server Root Files Directory",
        description="Files placed in the root of the server deployment.",
        examples=["/etc/docbuild/server-root-files-doc-suse-com"],
    )
    "Path for server root files."

    prebuilt_dir: Path = Field(
        default="{base_server_cache_dir}/build",
        title="Prebuilt/External Directory",
        description="The base directory containing prebuilt external documentation (e.g., Antora).",
        examples=["/data/docserv2/external-builds/external-tree/"],
    )
    "Path to externally built documentation."

    # --- WRITABLE PATHS START HERE ---

    repo_dir: WritablePath = Field(
        default=f"{STATE_HOME}/repos/permanent",
        title="Permanent Repository Directory",
        description="The directory where permanent bare Git repositories are stored.",
        examples=["/var/cache/docbuild/repos/permanent-full/"],
    )
    "Path for permanent bare Git repositories."

    tmp_repo_dir: WritablePath = Field(
        default=f"{STATE_HOME}/repos/branches",
        title="Temporary Repository Directory",
        description="Directory used for temporary working copies cloned from permanent bare repos.",
        examples=["/var/cache/docbuild/repos/temporary-branches/"],
    )
    "Directory for temporary working copies."

    base_cache_dir: WritablePath = Field(
        default=CACHE_HOME,
        title="Base Cache Directory",
        description="The root directory for all application-level caches.",
        examples=["/var/cache/docserv", "~/.cache/docbuild"],
    )
    "Base path for all caches."

    base_server_cache_dir: WritablePath = Field(
        default="{base_cache_dir}/{general.name}",
        title="Base Server Cache Directory",
        description="The base directory for server-specific caches.",
        examples=["/var/cache/docserv/doc-example-com"],
    )
    "Base path for server caches."

    meta_cache_dir: WritablePath = Field(
        default="{base_server_cache_dir}/meta",
        title="Metadata Cache Directory",
        description="Cache specifically for repository and deliverable metadata.",
        examples=[
            "/var/cache/docbuild/doc-example-com/meta",
            "~/.local/state/docbuild/devel/meta/",
        ],
    )
    "Metadata cache path."

    json_cache_dir: WritablePath = Field(
        default="{base_server_cache_dir}/json",
        title="JSON Cache Directory",
        description="Cache specifically for JSON data used in the portal.",
        examples=[
            "/var/cache/docbuild/doc-example-com/json",
            "~/.local/state/docbuild/devel/json/",
        ],
    )
    "JSON cache path."

    runtime_base_dir: WritablePath = Field(
        default=RUNTIME_DIR,
        title="Base Runtime Directory (Per-Run)",
        description=(
            "The base directory for lightweight runtime artifacts such as "
            "lock files, PID files, and sockets (not for general build "
            "temporary data)."
        ),
        examples=["/run/user/1000/docbuild"],
    )
    "Base runtime path."

    lock_dir: WritablePath = Field(
        default="{runtime_base_dir}/locks",
        title="Lock Directory",
        description=(
            "Directory for lock files used to prevent concurrent builds or "
            "operations on the same deliverable or repository."
        ),
        examples=["/run/user/1000/docbuild/locks"],
    )
    "Directory for lock files."

    tmp: EnvTmpPaths = Field(default_factory=EnvTmpPaths)
    "Temporary build paths."

    target: EnvTargetPaths = Field(default_factory=EnvTargetPaths)
    "Target deployment and backup paths."


class EnvXslt(BaseModel):
    """Defines XSLT parameters separated by target format."""

    model_config = ConfigDict(extra="forbid")

    common: dict[str, Any] = Field(default_factory=dict, title="Common XSLT Parameters")
    html: dict[str, Any] = Field(default_factory=dict, title="HTML-specific XSLT Parameters")
    pdf: dict[str, Any] = Field(default_factory=dict, title="PDF-specific XSLT Parameters")


class SSHEndpoint(BaseModel):
    """SSH connection details for the host that receives published docs."""

    # HOSTNAME_REGEX uses a look-ahead assertion which the Rust regex engine
    # used by pydantic-core cannot compile; the python-re engine is required.
    model_config = ConfigDict(extra="forbid", frozen=True, regex_engine="python-re")

    user: Annotated[
        str | None,
        Field(
            default=None,
            pattern=SSH_USERNAME_REGEX.pattern,
            description="SSH login name. If unset, the ssh config or current user is used.",
            examples=["doc"],
        ),
    ] = None
    host: Annotated[
        IPvAnyAddress | Annotated[str, Field(pattern=HOSTNAME_REGEX.pattern)],
        Field(
            description="IP address or DNS name of the server.",
            examples=["192.0.2.10", "docs.example.com"],
        ),
    ]

    @model_validator(mode="before")
    @classmethod
    def _split_user_host(cls, data: object) -> object:
        """Parse the ``user@host`` string shorthand before field validation.

        A single string is split on the last ``@``: the part before is the
        user, the part after is the host. Without ``@`` the whole string is
        the host. Dictionaries and SSHEndpoint instances pass through
        unchanged. Port syntax (``host:port``) is not supported.

        :param data: The raw value from the configuration.
        :return: A dictionary with ``user``/``host`` keys for string input,
            or the unchanged input otherwise.
        :raises ValueError: If the string is empty or has surrounding
            whitespace (both "do not guess" cases that must be rejected).
        """
        if not isinstance(data, str):
            return data
        user: str | None = None
        host = data
        if "@" in data:
            user, host = data.rsplit("@", 1)
            if user == "":
                raise ValueError(f"invalid SSH endpoint {data!r}: empty user")
        if not host or host != host.strip():
            raise ValueError(
                f"invalid SSH endpoint {data!r}: "
                "the host must be non-empty and must not have surrounding whitespace"
            )
        return {"user": user, "host": host}

    @model_validator(mode="after")
    def _reject_control_characters(self) -> Self:
        r"""Reject whitespace and control characters in user and host.

        The python-re engine matches ``$`` before a trailing newline, so a
        pattern alone would accept ``user``/``host`` values that carry a
        trailing ``\\n``. This validator rejects any whitespace or control
        character (space, tab, ``\\n``, ``\\r``, ``\\x00``-``\\x1f``, ``\\x7f``)
        in the string fields. ``host`` may be an IP address object; it is
        converted to its string form before the check.
        """
        for name, value in (("user", self.user), ("host", str(self.host))):
            if value is not None and any(
                ord(char) < 0x20 or ord(char) == 0x7F or char.isspace()
                for char in value
            ):
                raise ValueError(
                    f"{name} must not contain whitespace or control characters"
                )
        return self

    def __str__(self) -> str:
        """Return the human-readable string representation (e.g., 'user@host').

        :return: Formatted SSH target string.
        """
        if self.user:
            return f"{self.user}@{self.host}"
        return str(self.host)


class EnvRemote(BaseModel):
    """Defines the remote destination for publishing built documentation."""

    model_config = ConfigDict(extra="forbid")

    server: SSHEndpoint | None = Field(
        default=None,
        title="Remote Server",
        description=(
            "The remote server that receives the built documentation. "
            "The default is 'no remote' (None); publish is disabled."
        ),
        examples=["doc@example.com"],
    )
    "The SSH server endpoint (``user@host`` or ``host``) used by publish, or None."

    path: AbsolutePath | None = Field(
        default=None,
        title="Remote Directory",
        description=(
            "The absolute directory on the remote server where documentation "
            "is published. The default is 'no remote' (None); publish is disabled."
        ),
        examples=["/srv/docs"],
    )
    "The absolute remote directory used by publish, or None."

    @model_validator(mode="after")
    def _both_or_neither(self) -> Self:
        """Require both 'server' and 'path', or neither.

        :return: The unchanged model instance.
        :raises ValueError: If exactly one of ``server`` or ``path`` is set.
        """
        if (self.server is None) != (self.path is None):
            msg = "The [remote] section needs both 'server' and 'path', or neither."
            raise ValueError(msg)
        return self


class EnvConfig(BaseModel):
    """Root model for the environment configuration (env.toml)."""

    model_config = ConfigDict(extra="forbid")

    general: EnvGeneral = Field(
        default_factory=EnvGeneral,
        title="General Configuration",
        description="General settings like environment name, role, and languages.",
    )
    "General application settings."

    paths: EnvPaths = Field(
        default_factory=EnvPaths,
        title="Path Configuration",
        description="All file system path definitions.",
    )
    "File system paths."

    # Build section integration
    build: EnvBuild = Field(
        default_factory=EnvBuild,
        title="Build Configuration",
        description="Settings for DAPS command execution and containerization.",
    )
    "Build process settings."

    xslt: EnvXslt = Field(
        default_factory=EnvXslt,
        title="XSLT Parameters",
        description="Custom XSLT parameters passed directly to DAPS.",
    )
    "XSLT processing parameters."

    remote: EnvRemote = Field(
        default_factory=EnvRemote,
        title="Remote Configuration",
        description="Settings for the remote destination used by publish.",
    )
    "Remote publish destination."

    # --- Placeholder Resolution ---
    @model_validator(mode="before")
    @classmethod
    def _resolve_placeholders(cls, data: dict[str, Any]) -> dict[str, Any] | None:
        """Resolve placeholders before any other validation."""
        if isinstance(data, dict):
            try:
                return replace_placeholders(deepcopy(data), keep_runtime=True)
            except (
                PlaceholderResolutionError,
                CircularReferenceError,
                PlaceholderSyntaxError
            ) as e:
                raise ValueError(f"Configuration placeholder error: {e}") from e
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create an EnvConfig instance from a dictionary."""
        return cls.model_validate(data)

    @classmethod
    def get_default_config(cls, resolve_placeholders: bool = True) -> dict[str, Any]:
        """Generate the default environment configuration from the model.

        :param resolve_placeholders: If True, resolve placeholders in the config.
        :return: The default configuration as a dictionary.
        """
        # 1. Create a raw instance with model-defined defaults
        raw_instance = cls.model_validate({})
        # 2. Dump to a dictionary
        raw_dict = raw_instance.model_dump(mode="json")

        if not resolve_placeholders:
            return raw_dict

        # 3. Resolve placeholders
        resolved_dict = replace_placeholders(raw_dict, keep_runtime=True)

        return resolved_dict or {}
