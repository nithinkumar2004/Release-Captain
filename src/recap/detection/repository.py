from __future__ import annotations

import subprocess
from pathlib import Path

from recap.core.errors import RecapError


def find_repository(path: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError as exc:
        raise RecapError("Git is required but was not found on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise RecapError(f"{path} is not inside a Git repository.") from exc
    except subprocess.TimeoutExpired as exc:
        raise RecapError("Git repository detection timed out.") from exc
    return Path(result.stdout.strip()).resolve()
