"""Monotonic build run ID generation and directory provisioning."""

import logging
from pathlib import Path

from ..constants import STATE_HOME

log = logging.getLogger(__name__)


def get_next_run_id(
    base_dir: Path | None = None,
    role: str = "production",
) -> tuple[int, Path]:
    """Allocate the next monotonic build run ID and provision its state directory.

    Build run directories follow the structure:
        ``~/.local/state/docbuild/<ROLE>/<NUMBER>``

    The allocation is atomic: filesystem directory creation guarantees mutual exclusion
    and prevents duplicate run IDs across concurrent processes.

    :param base_dir: Base state directory (defaults to STATE_HOME).
    :param role: Operational environment role (e.g. production, staging, development).
    :return: A tuple of (allocated_run_id_integer, allocated_run_dir_path).
    """
    root_base = base_dir or STATE_HOME
    role_dir = root_base / role
    role_dir.mkdir(parents=True, exist_ok=True)

    # 1. Determine the highest existing run number from directory entries
    max_num = 0
    try:
        for item in role_dir.iterdir():
            if item.is_dir() and item.name.isdigit():
                max_num = max(max_num, int(item.name))
    except OSError as err:
        log.warning("Could not list directories in %s: %s", role_dir, err)

    # 2. Check the .last_run_id marker file if present
    counter_file = role_dir / ".last_run_id"
    if counter_file.is_file():
        try:
            content = counter_file.read_text(encoding="utf-8").strip()
            if content.isdigit():
                max_num = max(max_num, int(content))
        except OSError:
            pass

    # 3. Atomically reserve the next available directory using mkdir(exist_ok=False)
    candidate = max_num + 1
    while True:
        run_dir = role_dir / str(candidate)
        try:
            run_dir.mkdir(parents=True, exist_ok=False)
            break
        except FileExistsError:
            candidate += 1

    # 4. Update the .last_run_id marker file atomically
    tmp_counter = role_dir / f".last_run_id.tmp.{candidate}"
    try:
        tmp_counter.write_text(str(candidate), encoding="utf-8")
        tmp_counter.replace(counter_file)
    except OSError as err:
        log.warning("Could not update last_run_id marker file in %s: %s", role_dir, err)

    log.debug("Allocated build run ID %d in %s", candidate, run_dir)
    return candidate, run_dir
