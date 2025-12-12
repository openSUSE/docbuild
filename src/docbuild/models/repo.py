"""A repository model that can be initialized from a URL or a short name."""

from dataclasses import dataclass, field
import re
from typing import ClassVar
from urllib.parse import urlparse


@dataclass(frozen=True, init=False)
class Repo:
    """A repository model that can be initialized from a URL or a short name.

    This model can be compared directly with strings, which will check
    against the repository's abbreviated name (e.g., 'org/repo').

    Two Repo objects are considered equal if their derived names are the same,
    regardless of the original URL (HTTPS vs. SSH).
    """

    DEFAULT_HOST: ClassVar[str] = 'https://github.com'
    """The default host to use when constructing a URL from a short name."""

    _MAP_SERVICE2URL: ClassVar[dict[str, str]] = {
        'gl': 'https://gitlab.com',
        'gls': 'https://gitlab.suse.de',
        'gh': 'https://github.com',
        'bb': 'https://bitbucket.org',
        'gt': 'https://gitea.com',
        'cb': 'https://codeberg.org',
        'ghe': 'https://github.enterprise.com',
    }
    _MAP_URL2SERVICE: ClassVar[dict[str, str]] = {
        v: k for k, v in _MAP_SERVICE2URL.items()
    }

    _SSH_PATTERN: ClassVar[re.Pattern] = re.compile(
        r'^(?P<user>[^@]+)@(?P<host>[^:]+):(?P<repo>.+?)(?:\.git)?$'
    )

    _SERVICE_PATTERN: ClassVar[re.Pattern] = re.compile(
        r'^(?P<abbr>[a-z]{2,4}):/{1,2}(?P<repo>.+?)(?:\.git)?$', re.IGNORECASE
    )

    _SCHEMA_PATTERN: ClassVar[re.Pattern] = re.compile(r'(?P<schema>https?)://')

    url: str = field(repr=False)
    """The full URL of the repository."""

    surl: str
    """The shortened URL version of the repository, for example gh://org/repo for
        a GitHub repo."""

    name: str = field(init=False, repr=False)
    """The abbreviated name of the repository (e.g., 'org/repo')."""

    def __init__(self, value: str) -> None:
        """Initialize a repository model from a URL or a short name.

        This initializer understands:

        * A full URL like ``https://host/org/repo.git``.
        * A SSH URL like ``git@host:org/repo.git``.
        * An abbreviated URL like ``gh://org/repo`` for a GitHub URL.
          The service part (before '://') is a two to four letter code:
          - ``gh`` for GitHub
          - ``gl`` for GitLab
          - ``bb`` for BitBucket
          - ``gt`` for Gitea
          - ``cb`` for Codeberg
          - ``ghe`` for GitHub Enterprise
        * An abbreviated name like ``org/repo`` which defaults to GitHub.
        """
        cls = type(self)
        if not value:
            raise ValueError('Repository value cannot be empty.')

        url: str
        name: str

        service_match = self._SERVICE_PATTERN.match(value)
        ssh_match = self._SSH_PATTERN.match(value)

        if 'https://' in value or 'http://' in value:
            parsed_original = urlparse(value.lower())
            name = parsed_original.path.strip('/').rsplit('.git', 1)[0]
            url = f'{parsed_original.scheme}://{parsed_original.netloc}/{name}.git'
            host = f'{parsed_original.scheme}://{parsed_original.netloc}'
            surl = f'{self._MAP_URL2SERVICE.get(host, "gh")}://{name}'

        elif service_match:
            service = service_match.group('abbr').lower()
            name = service_match.group('repo').lower().rstrip('/')
            host = self._MAP_SERVICE2URL.get(service)
            if not host:
                raise ValueError(f"Unknown repo abbreviation: '{service}'")
            url = f'{host}/{name}.git'
            surl = f'{service}://{name}'

        elif ssh_match:
            host = ssh_match['host'].lower()
            name = ssh_match['repo'].lower()
            name = name.rstrip('/')
            url = f'https://{host}/{name}.git'
            surl = f'{self._MAP_URL2SERVICE.get(host, "gh")}://{name}'

        elif '/' in value:
            value = value.lower()
            name = value.rsplit('.git', 1)[0].rstrip('/')
            url = f'{self.DEFAULT_HOST}/{name}.git'
            surl = f'gh://{name}'

        else:
            raise ValueError(
                f"Invalid repository value: '{value}'. "
                'Expected a full HTTPS URL, SSH URL, abbr notation, '
                'or an abbreviated name.'
            )

        # Use object.__setattr__ because the dataclass is frozen
        object.__setattr__(self, 'url', url)
        object.__setattr__(self, 'name', name)
        object.__setattr__(self, 'surl', surl)

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
            str.maketrans({':': '_', '/': '_', '-': '_', '.': '_'}),
        )
