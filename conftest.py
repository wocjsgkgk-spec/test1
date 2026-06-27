from __future__ import annotations

import asyncio
import inspect
import sys
from pathlib import Path

asyncio.iscoroutinefunction = inspect.iscoroutinefunction


def _prepend_local_venv_site_packages() -> None:
    root = Path(__file__).resolve().parent
    venv = root / ".venv"
    if not venv.is_dir():
        return

    candidates = sorted(
        venv.glob("lib/python*/site-packages"),
        key=lambda path: path.as_posix(),
        reverse=True,
    )
    for site_packages in candidates:
        site_packages_str = str(site_packages)
        if site_packages_str not in sys.path:
            sys.path.insert(0, site_packages_str)
        break


_prepend_local_venv_site_packages()
