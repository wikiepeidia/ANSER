"""Shared branch-aware `.env` resolution for the 3 sibling apps in this repo.

This repo hosts 3 sibling Flask apps (San Xuat, Gateway, ANSER Retail) as
branches of ONE working directory (no submodules). Each app's entry point
(`app.py`) and its `core/config.py` used to call bare `load_dotenv()`
independently, with no branch awareness — fine for a single-clone-per-branch
setup, but it meant a dev working out of one shared clone had to hand-rename
a single root `.env` file every time they switched branches.

`load_project_env()` centralizes resolution into 4 steps, checked in order:

1. Root `.env` is a plain FILE -> load it directly. This is today's existing
   single-clone behavior, completely unchanged.
2. Root `.env` is a DIRECTORY -> look up the currently checked-out git branch
   against a fixed allowlist (`_BRANCH_ENV_FILES`) and load the matching file
   inside `.env/` if present. This is the new multi-branch-in-one-clone case.
3. Root `.env` is a DIRECTORY but step 2 found no branch-specific file (git
   unavailable, detached HEAD, unmapped branch, or the mapped file is simply
   missing) -> last-resort fallback to a generic `.env/.env` file, if one
   exists inside the directory. Lets a dev drop in one shared/default file
   that covers any branch not explicitly listed in `_BRANCH_ENV_FILES`.
4. None of the above resolved to a file -> fall back to a bare
   `load_dotenv()` call (today's existing no-op behavior when no `.env` is
   found anywhere — never crashes).

Env vars must be resolved and loaded into `os.environ` BEFORE
`core.config.Config`'s class body runs, since that class reads
`os.environ.get(...)` at import time — callers must call
`load_project_env()` before `from core.config import Config`.
"""
import os
import subprocess

from dotenv import load_dotenv

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_BRANCH_ENV_FILES = {
    'anser-san-xuat': '.env.sanxuat',
    'gateway': '.env.gateway',
    'anser-ban-le': '.env.banle',
}


def _current_branch():
    """Return the currently checked-out git branch name, or None.

    Returns None (never raises) if git is unavailable, the call times out,
    the working tree isn't a git repo, HEAD is detached, or stdout is empty.
    """
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=_PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except Exception:
        return None

    if result.returncode != 0:
        return None

    branch = result.stdout.strip()
    if not branch:
        return None

    return branch


def _resolve_env_path(root_dir):
    """Resolve which `.env` file (if any) should be loaded for root_dir.

    Returns an absolute/joined path string, or None if no file should be
    loaded (caller falls back to a bare load_dotenv() no-op in that case).
    """
    root_env = os.path.join(root_dir, '.env')

    if os.path.isfile(root_env):
        return root_env

    if os.path.isdir(root_env):
        branch = _current_branch()
        filename = _BRANCH_ENV_FILES.get(branch)
        if filename:
            branch_file = os.path.join(root_env, filename)
            if os.path.isfile(branch_file):
                return branch_file
        # Last resort: a generic `.env/.env` file, for branches not in
        # _BRANCH_ENV_FILES, detached HEAD, or git being unavailable.
        fallback_file = os.path.join(root_env, '.env')
        if os.path.isfile(fallback_file):
            return fallback_file
        return None

    return None


def load_project_env(root_dir=None):
    """Load env vars for the current app/branch. Never raises.

    Call this before importing `core.config.Config` (its class body reads
    `os.environ` at import time).
    """
    if root_dir is None:
        root_dir = _PROJECT_ROOT

    path = _resolve_env_path(root_dir)

    if path:
        load_dotenv(path)
    else:
        load_dotenv()
