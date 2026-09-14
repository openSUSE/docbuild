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
        }
    }
"""

from copy import deepcopy
from pathlib import Path
from typing import Annotated, Any, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_serializer,
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
    RUNTIME_DIR,
    STATE_HOME,
)
from ..language import LanguageCode
from ..path import WritablePath
from ..serverroles import ServerRole

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
    """General build configuration."""

    model_config = ConfigDict(extra="forbid")

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

    role: ServerRole = Field(
        default=ServerRole.PRODUCTION,
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

    # SPLIT: static base directory or remote destination
    target_base_dir: str = Field(
        default=f"{Path.home()}/Documents/{APP_NAME}/target",
        title="Target Server Base Directory",
        description="The static remote destination or base path for built documentation.",
        examples=["doc@10.100.100.100:/srv/docs"],
    )
    "The base destination for final built documentation."

    # SPLIT: dynamic suffix
    target_dir_dyn: str = Field(
        default="{{lang}}/{{product}}/{{docset}}",
        title="Target Directory Suffix",
        description="The dynamic suffix of the remote path containing runtime placeholders.",
        examples=["{{lang}}/{{product}}/{{docset}}"],
    )
    "Dynamic suffix for final remote destination."

    backup_dir: Path = Field(
        default=f"{STATE_HOME}/{{general.name}}/backup",
        title="Build Server Backup Directory",
        description="The location on the build server before it is synced to the target path.",
        examples=["/var/lib/docbuild/backups"],
    )
    "Local directory for storing build backups before deployment."


class EnvPaths(BaseModel):
    """Defines various application paths, including permanent storage and cache."""

    model_config = ConfigDict(extra="forbid")

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

    # --- Placeholder Resolution ---
    @model_validator(mode="before")
    @classmethod
    def _resolve_placeholders(cls, data: dict[str, Any]) -> dict[str, Any] | None:
        """Resolve placeholders before any other validation."""
        if isinstance(data, dict):
            try:
                return replace_placeholders(deepcopy(data))
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
        resolved_dict = replace_placeholders(raw_dict)
        return resolved_dict or {}
