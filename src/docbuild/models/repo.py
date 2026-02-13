"""A repository model that can be initialized from a URL or a short name."""

from dataclasses import dataclass, field
import re
from typing import ClassVar


@dataclass(frozen=True, init=False)
class Repo:
    """A repository model that can be initialized from a URL or a short name.

    This model can be compared directly with strings, which will check
    against the repository's abbreviated name (e.g., 'org/repo').

    Two Repo objects are considered equal if their derived names are the same,
    regardless of the original URL (HTTPS vs. SSH).
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

    def __init__(self, value: str, default_branch: str | None = None) -> None:
        """Initialize a repository model from a URL or a short name.

        :param default_branch: The default branch to use if no branch is specified in the URL.

        This initializer understands:

        * A full URL like ``https://HOST/ORG/REPO.git`` or a URL pointing
            to a branch like ``https://HOST/ORG/REPO/tree/BRANCH``

        * A SSH URL like ``git@HOST:ORG/REPO.git``.

        * An abbreviated URL like ``SERVICE://ORG/REPO`` or ``SERVICE://ORG/REPO.git``
          The service part (before '://') is a two to four letter code:
            - ``gh`` for GitHub (default)
            - ``gl`` for GitLab
            - ``bb`` for BitBucket
            - ``gt`` for Gitea
            - ``cb`` for Codeberg
            - ``ghe`` for GitHub Enterprise
          This makes the reference to a Git repo more readable.

        * A plain notation like ``ORG/REPO`` which defaults to GitHub.

        Branches other than default branches (main or master) are added
        by ``@BRANCH_NAME`` to the URL.
        """
        if not value:
            raise ValueError("Repository value cannot be empty.")

        # Store the original string
        object.__setattr__(self, "origin", value)

        data = self._consolidate_match(value.lower())

        # Consolidate data from regex match
        name = f"{data['org']}/{data['repo']}"
        branch = data.get("branch")
        host = data.get("host")
        schema = data.get("schema")

        match schema:
            case "http" | "https":
                # For https, a host from regex does not include the schema
                service = self._MAP_URL2SERVICE.get(f"{schema}://{host}", "gh")
                url = f"{schema}://{host}/{name}.git"
            case "git@":
                # For ssh, map to service and get canonical URL
                service = self._MAP_URL2SERVICE.get(f"https://{host}", "gh")
                host = self._MAP_SERVICE2URL.get(service, self.DEFAULT_HOST)
                url = f"{host}/{name}.git"
            case _:
                # For abbreviations (gh://) or bare (org/repo)
                service = schema or "gh"
                host = self._MAP_SERVICE2URL.get(service, self.DEFAULT_HOST)
                url = f"{host}/{name}.git"

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
        result = {
            "schema": raw_data.get("https_schema")
            or raw_data.get("ssh_schema")
            or raw_data.get("gh_schema"),
            "host": raw_data.get("https_host") or raw_data.get("ssh_host"),
            "org": raw_data.get("https_org")
            or raw_data.get("ssh_org")
            or raw_data.get("gh_org"),
            "repo": raw_data.get("https_repo")
            or raw_data.get("ssh_repo")
            or raw_data.get("gh_repo"),
        }

        # Branch Logic: Prioritize the /tree/ branch, fallback to @branch
        branch = raw_data.get("tree_branch") or raw_data.get("branch")
        result["branch"] = branch

        return result

    def __eq__(self, other: object) -> bool:
        """Compare Repo with another Repo (by name) or a string (by name)."""
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
