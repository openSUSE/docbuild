"""Git helper function."""

import logging
from pathlib import Path
from typing import ClassVar, Self

from ..constants import GITLOGGER_NAME
from ..models.repo import Repo
from ..utils.shell import execute_git_command

log = logging.getLogger(GITLOGGER_NAME)


class ManagedGitRepo:
    """Manages a bare repository and its temporary worktrees."""

    #: Class variable to indicate the update state of a repo
    _is_updated: ClassVar[dict[Repo, bool]] = {}

    def __init__(self: Self,
                 remote_url: str,
                 permanent_root: Path,
                 gitconfig: Path | None = None) -> None:
        """Initialize the managed repository.

        :param remote_url: The remote URL of the repository.
        :param permanent_root: The root directory for storing permanent bare clones.
        :param gitconfig: The path to a separate Git configuration file
           (=None, use the default config from etc/gitconfig)
        """
        self._repo_model = Repo(remote_url)
        self._permanent_root = permanent_root
        # The Repo model handles the "sluggification" of the URL
        self.bare_repo_path = self._permanent_root / self._repo_model.slug
        # Initialize attribute for output:
        self.stdout = self.stderr = None
        self._gitconfig = gitconfig
        # Add repo into class variable
        type(self)._is_updated.setdefault(self._repo_model, False)

    def __repr__(self: Self) -> str:
        """Return a string representation of the ManagedGitRepo."""
        return (
            f'{self.__class__.__name__}(remote_url={self.remote_url!r}, '
            f"bare_repo_path='{self.bare_repo_path!s}')"
        )

    @property
    def slug(self: Self) -> str:
        """Return the slug of the repository."""
        return self._repo_model.slug

    @property
    def remote_url(self: Self) -> str:
        """Return the remote URL of the repository."""
        return self._repo_model.url

    @property
    def permanent_root(self: Self) -> Path:
        """Return the permanent root directory for the repository."""
        return self._permanent_root

    async def _initial_clone(self: Self) -> bool:
        """Execute the initial 'git clone --bare' command.

        This is a helper for `clone_bare` and assumes the destination
        directory does not exist.

        :returns: True if the clone was successful, False on error.
        """
        url = self._repo_model.url
        try:
            self.stdout, self.stderr = await execute_git_command(
                'clone',
                '--bare',
                '--progress',
                str(url),
                str(self.bare_repo_path),
                cwd=self._permanent_root,
                gitconfig=self._gitconfig,
            )
            log.info("Cloned '%s' successfully", url)
            return True

        except RuntimeError as e:
            log.error("Failed to clone '%s': %s", url, e)
            return False

    async def clone_bare(self: Self) -> bool:
        """Clone the remote repository as a bare repository.

        If the repository already exists, it logs a message and returns.

        :returns: True if successful, False otherwise.
        """
        url = self._repo_model.url
        cls = type(self)

        if cls._is_updated.get(self._repo_model, False):
            log.info('Repository %r already processed this run.', self._repo_model.name)
            return True

        result = False
        if self.bare_repo_path.exists():
            log.info(
                'Repository already exists, fetching updates for %r',
                self._repo_model.name,
            )
            result = await self.fetch_updates()
        else:
            log.info("Cloning '%s' into '%s'...", url, self.bare_repo_path)
            result = await self._initial_clone()

        if result:
            cls._is_updated[self._repo_model] = True

        return result

    async def create_worktree(
        self: Self,
        target_dir: Path,
        branch: str,
        *,
        is_local: bool = True,
        options: list[str] | None = None,
    ) -> None:
        """Create a temporary worktree from the bare repository."""
        if not self.bare_repo_path.exists():
            raise FileNotFoundError(
                'Cannot create worktree. Bare repository does not exist at: '
                f'{self.bare_repo_path}'
            )

        clone_args = ['clone']
        if is_local:
            clone_args.append('--local')
        clone_args.extend(['--branch', branch])
        if options:
            clone_args.extend(options)
        clone_args.extend([str(self.bare_repo_path), str(target_dir)])

        self.stdout, self.stderr = await execute_git_command(
            *clone_args, cwd=target_dir.parent,
            gitconfig=self._gitconfig,
        )

    async def fetch_updates(self: Self) -> bool:
        """Fetch updates from the remote to the bare repository.

        :return: True if successful, False otherwise.
        """
        if not self.bare_repo_path.exists():
            log.warning(
                'Cannot fetch updates: Bare repository does not exist at %s',
                self.bare_repo_path,
            )
            return False

        log.info("Fetching updates for '%s'", self.slug)
        try:
            self.stdout, self.stderr = await execute_git_command(
                'fetch', '--all',
                cwd=self.bare_repo_path,
                gitconfig=self._gitconfig
            )
            log.info("Successfully fetched updates for '%s'", self.slug)
            return True

        except RuntimeError as e:
            log.error("Failed to fetch updates for '%s': %s", self.slug, e)
            return False
