"""Pydantic models for application and environment configuration."""

from copy import deepcopy
from pathlib import Path
from typing import Annotated, Any, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    IPvAnyAddress,
    field_serializer,
    model_validator,
)

from ...config.app import (
    CircularReferenceError,
    PlaceholderResolutionError,
    replace_placeholders,
)
from ..language import LanguageCode
from ..path import EnsureWritableDirectory
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

    # Allows extra keys from the TOML file that aren't yet defined in the model schema.
    model_config = ConfigDict(extra="allow")

    command: str = Field(..., description="The base daps command.")
    meta: str = Field(..., description="The daps metadata command.")


class EnvBuildContainer(BaseModel):
    """Configuration for container usage."""

    model_config = ConfigDict(extra="allow")

    container: str = Field(..., description="The container registry path/name.")


class EnvBuild(BaseModel):
    """General build configuration."""

    model_config = ConfigDict(extra="forbid")

    daps: EnvBuildDaps
    container: EnvBuildContainer


# --- Configuration Models ---


class EnvServer(BaseModel):
    """Defines server settings."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        title="Server Name",
        description="A human-readable identifier for the environment/server.",
        examples=["documentation-suse-com", "docserv-suse-de"],
    )
    "The descriptive name of the server."

    role: ServerRole = Field(
        title="Server Role",
        description="The operational role of the environment.",
        examples=["production"],
    )
    "The environment type, used for build behavior differences."

    host: IPvAnyAddress | DomainName = Field(
        title="Server Host",
        description="The hostname or IP address the documentation is served from.",
        examples=["127.0.0.1", "docserver.example.com"],
    )
    "The host address for the server."

    enable_mail: bool = Field(
        title="Enable Email",
        description=(
            "Flag to enable email sending features (e.g., build notifications)."
        ),
        examples=[True],
    )
    "Whether email functionality should be active."


class EnvGeneralConfig(BaseModel):
    """Defines general configuration."""

    model_config = ConfigDict(extra="forbid")

    default_lang: LanguageCode = Field(
        title="Default Language",
        description=(
            "The primary language code (e.g., 'en') used for non-localized content."
        ),
        examples=["en-us", "de-de", "ja-jp"],
    )
    "The default language code."

    languages: list[LanguageCode] = Field(
        title="Supported Languages",
        description=(
            "A list of all language codes supported by this documentation instance."
        ),
        examples=[["en-us", "de-de", "fr-fr"]],
    )
    "A list of supported language codes."

    canonical_url_domain: HttpUrl = Field(
        title="Canonical URL Domain",
        description=(
            "The base domain used to construct canonical URLs for SEO purposes."
        ),
        examples=["https://docs.example.com"],
    )
    "The canonical domain for URLs."

    # --- NEW: Custom Serialization for LanguageCode Models ---
    @field_serializer("default_lang")
    def serialize_default_lang(self, lang_obj: LanguageCode) -> str:
        """Serialize the LanguageCode model back to a simple string (e.g., 'en-us')."""
        # Assumes LanguageCode has a 'language' attribute containing the full code.
        return lang_obj.language

    @field_serializer("languages")
    def serialize_languages(self, lang_list: list[LanguageCode]) -> list[str]:
        """Serialize the list of LanguageCode models back to a list of strings."""
        return [lang_obj.language for lang_obj in lang_list]


class EnvTmpPaths(BaseModel):
    """Defines temporary paths."""

    model_config = ConfigDict(extra="forbid")

    tmp_base_dir: EnsureWritableDirectory = Field(
        title="Temporary Base Directory",
        description="The root directory for all temporary build artifacts.",
        examples=["/var/tmp/docbuild/"],
    )
    "Root path for temporary files."

    tmp_path: EnsureWritableDirectory = Field(
        title="General Temporary Path for specific server",
        description=(
            "A general-purpose subdirectory within the base temporary path to "
            "distinguish between different servers."
        ),
        examples=["/var/tmp/docbuild/doc-example-com"],
        alias="tmp_dir",
    )
    "General temporary path."

    tmp_deliverable_path: EnsureWritableDirectory = Field(
        title="Temporary Deliverable Path",
        description=(
            "The directory where deliverable repositories are cloned and processed."
        ),
        examples=["/var/tmp/docbuild/doc-example-com/deliverable/"],
        alias="tmp_deliverable_dir",
    )
    "Path for temporary deliverable clones."

    tmp_metadata_dir: EnsureWritableDirectory = Field(
        title="Temporary Metadata Directory",
        description="Temporary directory for metadata files.",
        examples=["/var/tmp/docbuild/doc-example-com/metadata"],
    )
    "Temporary metadata directory."

    tmp_build_dir: str = Field(
        title="Temporary Build Directory",
        description=(
            "Temporary directory for intermediate files (contains placeholders)."
        ),
        examples=[
            "/var/tmp/docbuild/doc-example-com/build/{{product}}-{{docset}}-{{lang}}"
        ],
    )
    "Temporary build output directory."

    tmp_out_path: EnsureWritableDirectory = Field(
        title="Temporary Output Path",
        description=(
            "The final temporary directory where built artifacts land before "
            "deployment."
        ),
        examples=["/var/tmp/docbuild/doc-example-com/out/"],
        alias="tmp_out_dir",
    )
    "Temporary final output path."

    log_path: EnsureWritableDirectory = Field(
        title="Log Path",
        description="The directory where build logs and application logs are stored.",
        examples=["/var/tmp/docbuild/doc-example-com/log"],
        alias="log_dir",
    )
    "Path for log files."

    tmp_deliverable_name: str = Field(
        title="Temporary Deliverable Name",
        description=(
            "The name used for the current deliverable being built "
            "(e.g., branch name or version)."
        ),
        examples=["{{product}}_{{docset}}_{{lang}}_XXXXXX"],
    )
    "Temporary deliverable name."


class EnvTargetPaths(BaseModel):
    """Defines target paths."""

    model_config = ConfigDict(extra="forbid")

    target_path: str = Field(
        title="Target Server Deployment Path",
        description="The final remote destination for the built documentation",
        examples=["doc@10.100.100.100:/srv/docs"],
        alias="target_dir",
    )
    "The destination path for final built documentation."

    backup_path: Path = Field(
        title="Build Server Path",
        description=(
            "The location on the build server before it is synced to the target path."
        ),
        alias="backup_dir",
    )
    "Path for backups."


class EnvPathsConfig(BaseModel):
    """Defines various application paths, including permanent storage and cache."""

    model_config = ConfigDict(extra="forbid")

    config_dir: Path = Field(
        title="Configuration Directory",
        description=(
            "The configuration directory containing application and environment "
            "files (e.g. app.toml)"
        ),
        examples=["/etc/docbuild"],
    )
    "Path to configuration files."

    root_config_dir: Path = Field(
        title="Root Configuration Directory",
        description=(
            "The highest-level configuration directory containing common "
            "configuration files."
        ),
        examples=["/etc/docbuild"],
    )
    "Path to the root configuration files."

    jinja_dir: Path = Field(
        title="Jinja Template Directory",
        description="Directory containing environment-specific Jinja templates.",
        examples=["/etc/docbuild/jinja-doc-suse-com"],
    )
    "Path for Jinja templates."

    server_rootfiles_dir: Path = Field(
        title="Server Root Files Directory",
        description=(
            "Directory for files that should be placed in the root of the "
            "server deployment."
        ),
        examples=["/etc/docbuild/server-root-files-doc-suse-com"],
    )
    "Path for server root files."

    repo_dir: Path = Field(
        title="Permanent Repository Directory",
        description="The directory where permanent bare Git repositories are stored.",
        examples=["/var/cache/docbuild/repos/permanent-full/"],
    )
    "Path for permanent bare Git repositories."

    temp_repo_dir: Path = Field(
        title="Temporary Repository Directory",
        description=(
            "The directory used for temporary working copies cloned from "
            "the permanent bare repositories."
        ),
        examples=["/var/cache/docbuild/repos/temporary-branches/"],
    )
    "Path for temporary working copies."

    base_cache_dir: Path = Field(
        title="Base Cache Directory",
        description="The root directory for all application-level caches.",
        examples=["/var/cache/docserv"],
    )
    "Base path for all caches."

    base_server_cache_dir: Path = Field(
        title="Base Server Cache Directory",
        description="The base directory for server-specific caches.",
        examples=["/var/cache/docserv/doc-example-com"],
    )
    "Base path for server caches."

    meta_cache_dir: Path = Field(
        title="Metadata Cache Directory",
        description=(
            "Cache directory specifically for repository and deliverable metadata."
        ),
        examples=["/var/cache/docbuild/doc-example-com/meta"],
    )
    "Metadata cache path."

    base_tmp_dir: EnsureWritableDirectory = Field(
        title="Base Temporary Directory (System Wide)",
        description=(
            "The root directory for all temporary artifacts (used for "
            "placeholder resolution)."
        ),
        examples=["/var/tmp/docbuild"],
    )
    "Base system temporary path."

    tmp: EnvTmpPaths
    "Temporary build paths."

    target: EnvTargetPaths
    "Target deployment and backup paths."


class EnvConfig(BaseModel):
    """Root model for the environment configuration (env.toml)."""

    model_config = ConfigDict(extra="forbid")

    server: EnvServer = Field(
        title="Server Configuration",
        description="Configuration related to the server/deployment environment.",
    )
    "Server-related settings."

    config: EnvGeneralConfig = Field(
        title="General Configuration",
        description="General settings like default language and canonical domain.",
    )
    "General application settings."

    paths: EnvPathsConfig = Field(
        title="Path Configuration",
        description="All file system path definitions.",
    )
    "File system paths."

    # Build section integration
    build: EnvBuild = Field(
        title="Build Configuration",
        description="Settings for DAPS command execution and containerization.",
    )
    "Build process settings."

    xslt_params: dict[str, Any] = Field(
        default_factory=dict,
        alias="xslt-params",
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
            except (PlaceholderResolutionError, CircularReferenceError) as e:
                raise ValueError(f"Configuration placeholder error: {e}") from e
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Create an EnvConfig instance from a dictionary."""
        return cls.model_validate(data)
