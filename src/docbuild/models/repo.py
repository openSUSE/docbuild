"""A repository model that can be initialized from a URL or a short name."""

from dataclasses import dataclass, field
import re
from typing import ClassVar, Self


@dataclass(frozen=True, init=False)
class Repo:
    """A model for Git URL and SSH repositories.

    It can be initialized from another Repo object, a URL, or a short name.

    Initializing from an existing ``Repo`` object is a cheap operation that
    avoids re-parsing the URL. The ``default_branch`` parameter can be used
    to create a new ``Repo`` instance with a different branch. If provided,
    it will overwrite the original branch (or set one if the original
    ``Repo`` had no branch).

    This model can be compared directly with strings, which will check
    against the repository's abbreviated name (e.g., ``org/repo``).

    Two Repo objects are considered equal if their derived names are the same,
    regardless of the original URL (HTTPS vs. SSH).

    The class understands:

    *  A full URL like ``https://HOST/ORG/REPO.git`` or a URL pointing
       to a branch like ``https://HOST/ORG/REPO/tree/BRANCH``

    *  A SSH URL like ``git@HOST:ORG/REPO.git``.

    *  An abbreviated URL like ``SERVICE://ORG/REPO`` or ``SERVICE://ORG/REPO.git``
       The service part is a two to four letter alias for common Git hosting
       services, for example:

       * ``gh`` for GitHub (default)
       * ``gl`` for GitLab
       * ``bb`` for BitBucket
       * ``gt`` for Gitea
       * ``cb`` for Codeberg
       * ``ghe`` for GitHub Enterprise

       This makes the reference to a Git repo more readable.

    *  A plain notation like ``ORG/REPO`` which defaults to GitHub.

    Additionally, branches other than default branches (main or master) can be
    added by ``@BRANCH_NAME`` to any of the above URLs.

    .. code-block:: python

        >>> from docbuild.models.repo import Repo
        >>> repo = Repo("https://github.com/openSUSE/docbuild")
        >>> repo.url
        'https://github.com/opensuse/docbuild.git'
        >>> repo.name
        'opensuse/docbuild'
        >>> repo.surl
        'gh://opensuse/docbuild'
        >>> repo.treeurl
        'https://github.com/opensuse/docbuild/tree/main'

        >>> # Create a new Repo with a different branch from an existing one
        >>> r1 = Repo("gh://opensuse/docbuild@main")
        >>> r2 = Repo(r1, default_branch="v1")
        >>> r2.branch
        'v1'
        >>> r2.surl
        'gh://opensuse/docbuild@v1'
    """

    DEFAULT_HOST: ClassVar[str] = "https://github.com"
    """The default host to use when constructing a URL from a short name."""

    _MAP_SERVICE2URL: ClassVar[dict[str, str]] = {
        "bb": "https://bitbucket.org",
        "cb": "https://codeberg.org",
        "gh": "https://github.com",
        "ghe": "https://github.enterprise.com",
        "git@": "https://github.com",
        "gl": "https://gitlab.com",
        "gls": "https://gitlab.suse.de",
        "gt": "https://gitea.com",
    }

    _MAP_URL2SERVICE: ClassVar[dict[str, str]] = {
        v: k for k, v in _MAP_SERVICE2URL.items() if k != "git@"
    }

    _SERVICES: ClassVar[str] = "|".join(
        [k for k in _MAP_SERVICE2URL.keys() if k != "git@"]
    )

    _REPOS_PATTERN: ClassVar[re.Pattern] = re.compile(
        rf"""^                                 # Start of string
        (?:                               # Start of URL formats group
            # Option 1: HTTPS (Supports .git OR /tree/branch)
            (?:
                # Capture the repo name *without* the optional trailing
                # ".git" so that the canonical URL does not end up with
                # a duplicated suffix like "repo.git.git".
                (?P<https_schema>https?)://(?P<https_host>[^/]+)/(?P<https_org>[^/]+)/(?P<https_repo>[^/@\s?#]+?)
                (?:\.git
                   |
                   /tree/(?P<tree_branch>[^/\s?#]+)
                )?/?
            )
            |
            # Option 2: SSH
            (?:
                (?P<ssh_schema>git@)
                (?P<ssh_host>[^:]+):(?P<ssh_org>[^/]+)/(?P<ssh_repo>[^/@\s?]+?)(?:\.git)?/?
            )
            |
            # Option 3: Abbreviated protocol-style URL (e.g., gh://, gl://) + optional @branch
            (?:
                (?:(?P<gh_schema>{_SERVICES})://)?
                (?P<gh_org>[^/]+)/(?P<gh_repo>[^/@\s?]+?)(?:/|\.git)?
            )
        )                                 # End of URL formats group
        (?:@(?P<branch>[^@\s]+))?         # Consolidated optional @branch suffix
        $                                 # End of string
        """,
        re.VERBOSE | re.IGNORECASE,
    )
    """The regex to match for the different URL notations."""

    _TREE_PATTERN: ClassVar[dict[str, str]] = {
        "bb": "https://bitbucket.com/{owner}/{repo}/",
        "cb": "https://codeberg.org/{owner}/{repo}/src/branch/{branch}",
        "gh": "https://github.com/{owner}/{repo}/tree/{branch}",
        "ghe": "https://github.enterprise.com/{owner}/{repo}/tree/{branch}",
        "git@": "https://github.com/{owner}/{repo}/tree/{branch}",
        "gl": "https://gitlab.com/{owner}/{repo}/-/tree/{branch}",
        "gls": "https://gitlab.suse.de/{owner}/{repo}/-/tree/{branch}",
        "gt": "https://gitea.com/{owner}/{repo}/src/branch/{branch}",
    }
    """URL template for constructing tree URLs based on the service."""

    _default_branches = ("main", "master")

    url: str = field(repr=False)
    """The full URL of the repository."""

    treeurl: str = field(init=False, repr=False)
    """The full URL including the branch of the repository."""

    surl: str
    """The shortened URL version of the repository, for example gh://org/repo for
        a GitHub repo."""

    name: str = field(init=False, repr=False)
    """The abbreviated name of the repository (e.g., 'org/repo')."""

    branch: str | None = field(init=False, repr=False)
    """The branch of the repository"""

    origin: str = field(init=False, repr=False)
    """The original unchanged URL of the repository."""

    def __init__(self, value: Self | str, default_branch: str | None = None) -> None:
        """Initialize a repository model.

        :param value: A URL string, a short name (e.g., ``org/repo``), or an
            existing ``Repo`` object.
        :param default_branch: If the input ``value`` does not specify a branch,
            this branch is used. If ``value`` is another ``Repo`` object,
            this parameter can be used to override its branch.
        """
        if not value:
            raise ValueError("Repository value cannot be empty.")

        if isinstance(value, Repo):
            # Perform a cheap copy of attributes.
            for attribute in (
                "url", "treeurl", "surl", "name", "branch", "origin",
            ):
                object.__setattr__(self, attribute, getattr(value, attribute))

            # If a new branch is provided that differs from the original, update
            # branch-dependent attributes without re-parsing the whole URL.
            if default_branch is not None and default_branch != value.branch:
                service, _, _ = value.surl.partition("://")
                owner, repo = value.name.split("/", maxsplit=1)
                treeurl_template = self._TREE_PATTERN.get(service, self._TREE_PATTERN["gh"])

                object.__setattr__(self, "branch", default_branch)
                object.__setattr__(self, "surl", f"{service}://{value.name}@{default_branch}")
                object.__setattr__(
                    self,
                    "treeurl",
                    treeurl_template.format(
                        owner=owner, repo=repo, branch=default_branch
                    ),
                )
            return

        # Store the original string
        object.__setattr__(self, "origin", value)

        data = self._consolidate_match(value.lower())

        # Consolidate data from regex match
        name = f"{data['org']}/{data['repo']}"
        branch = data.get("branch") or default_branch
        service = data["service"]
        url = data["url"]

        # Build URLs
        surl = f"{service}://{name}"
        if branch:
            surl += f"@{branch}"

        # Create the effecive branch for tree URL: prioritize found branch (either
        # from /tree/ or @branch), then the given default branch, then defined defaults.
        effective_branch = branch or default_branch or self._default_branches[0]
        treeurl_template = self._TREE_PATTERN.get(service, self._TREE_PATTERN["gh"])
        treeurl = treeurl_template.format(
            owner=data["org"], repo=data["repo"], branch=effective_branch
        )

        # Use object.__setattr__ because the dataclass is frozen
        object.__setattr__(self, "url", url)
        object.__setattr__(self, "treeurl", treeurl)
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "surl", surl)
        object.__setattr__(self, "branch", branch)

    def _consolidate_match(self, value: str) -> dict:
        """Consolidate keys for a cleaner API."""
        match = self._REPOS_PATTERN.match(value)
        if not match:
            raise ValueError(
                f"Invalid repository value: '{value}'. "
                "Expected a full HTTPS URL, SSH URL, abbr notation, "
                "or an abbreviated name."
            )
        raw_data = match.groupdict()
        org = (
            raw_data.get("https_org")
            or raw_data.get("ssh_org")
            or raw_data.get("gh_org")
        )
        repo = (
            raw_data.get("https_repo")
            or raw_data.get("ssh_repo")
            or raw_data.get("gh_repo")
        )

        match raw_data:
            case {
                "https_schema": https_schema,
                "https_host": https_host,
            } if https_schema and https_host:
                service = self._MAP_URL2SERVICE.get(
                    f"{https_schema}://{https_host}", "gh"
                )
                url = f"{https_schema}://{https_host}/{org}/{repo}.git"
            case {"ssh_schema": "git@", "ssh_host": ssh_host} if ssh_host:
                service = self._MAP_URL2SERVICE.get(f"https://{ssh_host}", "gh")
                url = f"{self._MAP_SERVICE2URL.get(service, self.DEFAULT_HOST)}/{org}/{repo}.git"
            case _:
                service = raw_data.get("gh_schema") or "gh"
                url = f"{self._MAP_SERVICE2URL.get(service, self.DEFAULT_HOST)}/{org}/{repo}.git"

        result = {
            "org": org,
            "repo": repo,
            "service": service,
            "url": url,
        }

        # Branch Logic: Prioritize the /tree/ branch, fallback to @branch
        branch = raw_data.get("tree_branch") or raw_data.get("branch")
        result["branch"] = branch

        return result

    def __eq__(self, other: object) -> bool:
        """Compare Repo with another Repo (by name) or a string (by name).

        For example:

        .. code-block:: python

            >>> repo = Repo("opensuse/docbuild")
            >>> repo == "https://github.com/opensuse/docbuild.git"
            True
            >>> repo == "gh://opensuse/docbuild"
            True
            >>> repo == "opensuse/docbuild@v1"
            True
        """
        if isinstance(other, str):
            return self.name == Repo(other).name
        if isinstance(other, Repo):
            return self.name == other.name
        return NotImplemented

    def __str__(self) -> str:
        """Return the canonical URL of the repository."""
        return self.url

    def __hash__(self) -> int:
        """Hash the Repo object based on its canonical derived name."""
        return hash(self.name)

    def __contains__(self, item: str) -> bool:
        """Check if a string is part of the repository's abbreviated name."""
        if isinstance(item, str):
            return item.lower() in self.name
        return False

    @property
    def slug(self) -> str:
        """Return the slug name of the repository."""
        return self.url.translate(
            str.maketrans({":": "_", "/": "_", "-": "_", ".": "_"}),
        )


if __name__ == "__main__":
    # Run it as:
    # python -m src.docbuild.models.repo
    test_urls = [
        "https://github.com/lycheeverse/lychee/tree/relative-link-fixes",  # New #variant
        "https://GitHub.com/opensuse/docbuild.git",  # HTTPS no branch
        "git@github.com:openSUSE/docbuild.git",  # SSH no branch
        "gh://openSUSE/docbuild",  # Abbr no branch
        "gh://openSUSE/docbuild@v1",
    ]

    for url in test_urls:
        repo = Repo(url)
        print(f"┌ {url}")
        print(f"├─ {repo.treeurl=}")
        print(f"├─ {repo.surl=}")
        print(f"├─ {repo.name=}")
        print(f"├─ {repo.branch=}")
        print(f"└─ {repo.url=}")
        # print("└")
        print()
