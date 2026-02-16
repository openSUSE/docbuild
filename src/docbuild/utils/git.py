"""Git helper function."""

import asyncio
import logging
from pathlib import Path
from subprocess import CompletedProcess
from typing import ClassVar, Self

from ..constants import GITLOGGER_NAME
from ..models.repo import Repo
from ..utils.shell import execute_git_command

log = logging.getLogger(GITLOGGER_NAME)


class ManagedGitRepo:
    """Manages a bare repository and its temporary worktrees."""

    #: Class variable to indicate the update state of a repo
    _is_updated: ClassVar[dict[Repo, bool]] = {}
    _locks: ClassVar[dict[Repo, asyncio.Lock]] = {}

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the internal update-state cache.

        This is a small, explicit API intended primarily for tests
        to reset class-level state between test cases. It avoids
        tests touching the private `_is_updated` attribute directly.
        """
        cls._locks.clear()
        cls._is_updated.clear()

    def __init__(
        self: Self, repo: str | Repo, rootdir: Path, gitconfig: Path | None = None
    ) -> None:
        """Initialize the managed repository.

        :param repo: The remote URL or :class:`~docbuild.models.repo.Repo` instance of the repository to manage.
        Repo instance of the repository.
        :param permanent_root: The root directory for storing permanent bare clones.
        :param gitconfig: The path to a separate Git configuration file
           (=None, use the default config from etc/gitconfig)
        """
        if isinstance(repo, str):
            self._repo_model = Repo(repo)
        elif isinstance(repo, Repo):
            self._repo_model = repo
        else:
            raise TypeError(
                f"remote_url must be a string or Repo instance, got {type(repo)}"
            )
        self._permanent_root = rootdir
        # The Repo model handles the "sluggification" of the URL
        self.bare_repo_path = self._permanent_root / self._repo_model.slug
        # Initialize attribute for last subprocess result:
        self.result: None | CompletedProcess[str] = None
        self._gitconfig = gitconfig
        # Add repo into class variable
        type(self)._is_updated.setdefault(self._repo_model, False)

    def __repr__(self: Self) -> str:
        """Return a string representation of the ManagedGitRepo."""
        return (
            f"{self.__class__.__name__}(remote_url={self.remote_url!r}, "
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
            self.result = await execute_git_command(
                "clone",
                "--bare",
                "--progress",
                str(url),
                str(self.bare_repo_path),
                cwd=self._permanent_root,
                gitconfig=self._gitconfig,
            )
            # self.stdout = proc.stdout
            # self.stderr = proc.stderr
            log.info("Cloned '%s' successfully", url)
            return True

        except RuntimeError as e:
            log.error("Failed to clone '%s': %s", url, e)
            return False

    async def clone_bare(self: Self) -> bool:
        """Clone the remote repository as a bare repository.

        If the repository already exists, it updates the repo. Once the repo is
        updated, its status is stored. Further calls won't update the repo
        again to maintain a consistent state. This avoids different states betwen
        different times.

        :returns: True if successful, False otherwise.
        """
        url = self._repo_model.url
        repo_model = self._repo_model

        # Ensure a lock exists for this specific repository
        if repo_model not in self._locks:
            self._locks[repo_model] = asyncio.Lock()

        async with self._locks[repo_model]:
            # Re-check the update status after acquiring the lock
            if self._is_updated.get(repo_model, False):
                log.info("Repository %r already processed this run.", repo_model.name)
                return True

            result = False
            if self.bare_repo_path.exists():
                log.info(
                    "Repository already exists, fetching updates for %r",
                    repo_model.name,
                )
                result = await self.fetch_updates()
            else:
                log.info("Cloning '%s' into '%s'...", url, self.bare_repo_path)
                result = await self._initial_clone()

            if result:
                self._is_updated[repo_model] = True

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
                "Cannot create worktree. Bare repository does not exist at: "
                f"{self.bare_repo_path}"
            )

        clone_args = ["clone"]
        if is_local:
            clone_args.append("--local")
        clone_args.extend(["--branch", branch])
        if options:
            clone_args.extend(options)
        clone_args.extend([str(self.bare_repo_path), str(target_dir)])

        self.result = await execute_git_command(
            *clone_args,
            cwd=target_dir.parent,
            gitconfig=self._gitconfig,
        )

    async def fetch_updates(self: Self) -> bool:
        """Fetch updates for all branches from the remote.

        :return: True if successful, False otherwise.
        """
        if not self.bare_repo_path.exists():
            log.warning(
                "Cannot fetch updates: Bare repository does not exist at %s",
                self.bare_repo_path,
            )
            return False

        log.info("Trying to fetch updates for '%s'", self.slug)
        try:
            # To update *every* branch in the bare Git repo, we need to use
            # this weird 'git fetch' command:
            self.result = await execute_git_command(
                "fetch",
                "origin",
                "+refs/heads/*:refs/heads/*",
                "-v",
                "--prune",
                cwd=self.bare_repo_path,
            )
            log.info("Successfully fetched updates for '%s'", self.slug)
            return True

        except RuntimeError as e:
            log.error("Failed to fetch updates for '%s': %s", self.slug, e)
            return False

    async def ls_tree(self: Self, branch: str, recursive: bool = True) -> list[str]:
        """List all files in a specific branch of the bare repository.

        :param branch: The branch name to inspect.
        :param recursive: Whether to list files in subdirectories.
        :return: A list of file paths found in the branch.
        """
        if not self.bare_repo_path.exists():
            log.warning(
                "Cannot run ls-tree: Bare repository does not exist at %s",
                self.bare_repo_path,
            )
            return []

        args = ["ls-tree", "--name-only"]
        if recursive:
            args.append("-r")
        args.append(branch)

        try:
            # We use execute_git_command which already handles the 'git' prefix
            # and uses the bare_repo_path as the current working directory.
            self.result = await execute_git_command(
                *args,
                cwd=self.bare_repo_path,
                gitconfig=self._gitconfig,
            )

            if not self.result.stdout:
                return []

            return self.result.stdout.strip().splitlines()

        except RuntimeError as e:
            log.error(
                "Failed to run ls-tree on branch '%s' in '%s': %s",
                branch, self.slug, e
            )
            return []
