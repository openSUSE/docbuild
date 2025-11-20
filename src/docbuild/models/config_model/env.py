"""Pydantic models for application and environment configuration."""

from copy import deepcopy
from typing import Any, Self, Annotated, Literal 
from pathlib import Path

from pydantic import BaseModel, Field, HttpUrl, IPvAnyAddress, model_validator, ConfigDict

from ...config.app import replace_placeholders
from ...config.app import CircularReferenceError, PlaceholderResolutionError


class LanguageCode(str):
    """Placeholder for the LanguageCode type."""
    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: Any):
        return handler(str)


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


# --- Configuration Models ---

class Env_Server(BaseModel):
    """Defines server settings."""

    model_config = ConfigDict(extra='forbid')

    name: str = Field(
        title="Server Name",
        description="A human-readable identifier for the environment/server.",
        examples=["documentation-suse-com", "docserv-suse-de"],
    )
    "The descriptive name of the server."

    role: Literal["development", "production", "staging"] = Field(
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
        description="Flag to enable email sending features (e.g., build notifications).",
        examples=[True],
    )
    "Whether email functionality should be active."


class Env_GeneralConfig(BaseModel):
    """Defines general configuration."""

    model_config = ConfigDict(extra='forbid')

    default_lang: LanguageCode = Field( 
        title="Default Language",
        description="The primary language code (e.g., 'en') used for non-localized content.",
        examples=["en-us", "de-de", "ja-jp"],
    )
    "The default language code."

    languages: list[LanguageCode] = Field( 
        title="Supported Languages",
        description="A list of all language codes supported by this documentation instance.",
        examples=[["en-us", "de-de", "fr-fr"]],
    )
    "A list of supported language codes."

    canonical_url_domain: HttpUrl = Field(
        title="Canonical URL Domain",
        description="The base domain used to construct canonical URLs for SEO purposes.",
        examples=["https://docs.example.com"],
    )
    "The canonical domain for URLs."


class Env_TmpPaths(BaseModel):
    """Defines temporary paths."""

    model_config = ConfigDict(extra='forbid')

    tmp_base_path: Path = Field(
        title="Temporary Base Path",
        description="The root directory for all temporary build artifacts.",
        examples=["/var/tmp/docbuild/"],
    )
    "Root path for temporary files."

    tmp_path: Path = Field(
        title="General Temporary Path for specific server",
        description="A general-purpose subdirectory within the base temporary path to distinguish between different servers.",
        examples=["/var/tmp/docbuild/doc-example-com"],
    )
    "General temporary path."
    
    tmp_deliverable_path: Path = Field(
        title="Temporary Deliverable Path",
        description="The directory where deliverable repositories are cloned and processed.",
        examples=["/var/tmp/docbuild/doc-example-com/deliverable/"],
    )
    "Path for temporary deliverable clones."

    tmp_build_dir: Path = Field(
        title="Temporary Build Directory",
        description="Temporary directory for intermediate files (contains placeholders).",
        examples=["/var/tmp/docbuild/doc-example-com/build/{{product}}-{{docset}}-{{lang}}"],
    )
    "Temporary build output directory."

    tmp_out_path: Path = Field(
        title="Temporary Output Path",
        description="The final temporary directory where built artifacts land before deployment.",
        examples=["/var/tmp/docbuild/doc-example-com/out/"],
    )
    "Temporary final output path."

    log_path: Path = Field(
        title="Log Path",
        description="The directory where build logs and application logs are stored.",
        examples=["/var/tmp/docbuild/doc-example-com/log"],
    )
    "Path for log files."

    tmp_deliverable_name: str = Field(
        title="Temporary Deliverable Name",
        description="The name used for the current deliverable being built (e.g., branch name or version).",
        examples=["{{product}}_{{docset}}_{{lang}}_XXXXXX"],
    )
    "Temporary deliverable name."


class Env_TargetPaths(BaseModel):
    """Defines target paths."""

    model_config = ConfigDict(extra='forbid')

    target_path: str = Field(
        title="Target Server Deployment Path",
        description="The final remote destination for the built documentation",
        examples=["doc@10.100.100.100:/srv/docs"],
    )
    "The destination path for final built documentation."

    backup_path: Path = Field(
        title="Build Server Path",
        description="The location on the build server before it is synced to the target path.",
    )
    "Path for backups."


class Env_PathsConfig(BaseModel):
    """Defines various application paths, including permanent storage and cache."""

    model_config = ConfigDict(extra='forbid')

    config_dir: Path = Field(
        title="Configuration Directory",
        description="The configuration directory containing application and environment files (e.g. app.toml)",
        examples=["/etc/docbuild"],
    )
    "Path to configuration files."

    repo_dir: Path = Field(
        title="Permanent Repository Directory",
        description="The directory where permanent bare Git repositories are stored.",
        examples=["/var/cache/docbuild/repos/permanent-full/"],
    )
    "Path for permanent bare Git repositories."

    temp_repo_dir: Path = Field(
        title="Temporary Repository Directory",
        description="The directory used for temporary working copies cloned from the permanent bare repositories.",
        examples=["/var/cache/docbuild/repos/temporary-branches/"],
    )
    "Path for temporary working copies."

    base_cache_dir: Path = Field(
        title="Base Cache Directory",
        description="The root directory for all application-level caches.",
        examples=["/var/cache/docserv"],
    )
    "Base path for all caches."

    meta_cache_dir: Path = Field(
        title="Metadata Cache Directory",
        description="Cache directory specifically for repository and deliverable metadata.",
        examples=["/var/cache/docbuild/doc-example-com/meta"],
    )
    "Metadata cache path."

    tmp: Env_TmpPaths
    "Temporary build paths."

    target: Env_TargetPaths
    "Target deployment and backup paths."


class EnvConfig(BaseModel):
    """Root model for the environment configuration (env.toml)."""
    
    model_config = ConfigDict(extra='forbid')

    server: Env_Server = Field(
        title="Server Configuration",
        description="Configuration related to the server/deployment environment.",
    )
    "Server-related settings."

    config: Env_GeneralConfig = Field(
        title="General Configuration",
        description="General settings like default language and canonical domain.",
    )
    "General application settings."

    paths: Env_PathsConfig = Field(
        title="Path Configuration",
        description="All file system path definitions.",
    )
    "File system paths."

    xslt_params: dict[str, str | int] = Field(
        default_factory=dict,
        alias='xslt-params',
        title="XSLT Parameters",
        description="Custom XSLT parameters passed directly to DAPS.",
    )
    "XSLT processing parameters."

    # --- Placeholder Resolution ---
    @model_validator(mode='before')
    @classmethod
    def _resolve_placeholders(cls, data: Any) -> Any:
        """Resolve placeholders before any other validation."""
        # This is the exact pattern used in your AppConfig
        if isinstance(data, dict):
            try:
                return replace_placeholders(deepcopy(data))
            except (PlaceholderResolutionError, CircularReferenceError) as e:
                raise ValueError(f"Configuration placeholder error: {e}") from e
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Convenience method to validate and return an instance."""
        return cls.model_validate(data)