"""Git helper function."""

import logging
from pathlib import Path

from ..constants import GITLOGGER_NAME
from ..models.repo import Repo
from ..utils.shell import execute_git_command

log = logging.getLogger(GITLOGGER_NAME)


class ManagedGitRepo:
    """Manages a bare repository and its temporary worktrees."""

    def __init__(self, remote_url: str, permanent_root: Path) -> None:
        """Initialize the managed repository.

        :param remote_url: The remote URL of the repository.
        :param permanent_root: The root directory for storing permanent bare clones.
        """
        self._repo_model = Repo(remote_url)
        self._permanent_root = permanent_root
        # The Repo model handles the "sluggification" of the URL
        self.bare_repo_path = self._permanent_root / self._repo_model.slug
        # Initialize attribute for output:
        self.stdout = self.stderr = None

    def __repr__(self) -> str:
        """Return a string representation of the ManagedGitRepo."""
        return (
            f'{self.__class__.__name__}(remote_url={self.remote_url!r}, '
            f"bare_repo_path='{self.bare_repo_path!s}')"
        )

    @property
    def slug(self) -> str:
        """Return the slug of the repository."""
        return self._repo_model.slug

    @property
    def remote_url(self) -> str:
        """Return the remote URL of the repository."""
        return self._repo_model.url

    @property
    def permanent_root(self) -> Path:
        """Return the permanent root directory for the repository."""
        return self._permanent_root

    async def clone_bare(self) -> bool:
        """Clone the remote repository as a bare repository.

        If the repository already exists, it logs a message and returns.
        """
        url = self._repo_model.url
        if self.bare_repo_path.exists():
            log.info('Repository already exists at %s', self.bare_repo_path)
            return True

        log.info("Cloning '%s' into '%s'...", url, self.bare_repo_path)
        try:
            self.stdout, self.stderr = await execute_git_command(
                'clone',
                '--bare',
                '--progress',
                str(url),
                str(self.bare_repo_path),
                cwd=self._permanent_root,
            )
            log.info("Cloned '%s' successfully", url)
            return True

        except RuntimeError as e:
            log.error("Failed to clone '%s': %s", url, e)
            return False

    async def create_worktree(
        self,
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
            *clone_args, cwd=target_dir.parent
        )
