#!/usr/bin/env python3
"""
bump_submodules.py — Local-only Git orchestrator for submodule updates.
Requires: Python 3.12+, PyYAML, GitPython, Pydantic v2

Usage:
  python tools/bump_submodules.py [--config submodules.yaml] [--dry-run] [--tag v1.0] [--auto-stash]
"""

from __future__ import annotations
import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional, List, Dict

import yaml
from pydantic import BaseModel, Field
from git import Repo, GitCommandError, InvalidGitRepositoryError


# ---------------------------
# Models
# ---------------------------

class ModuleConfig(BaseModel):
    name: str
    url: str
    branch: str


class SubmoduleConfig(BaseModel):
    modules: List[ModuleConfig] = Field(..., description="List of submodules")


# ---------------------------
# Helpers
# ---------------------------

def run(cmd: List[str], cwd: Optional[Path] = None) -> str:
    """Run a local command (mainly git) and return stdout, raise on error."""
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(
            f"Command failed ({' '.join(cmd)}):\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )
    return res.stdout.strip()


def ensure_superproject(path: Path) -> Repo:
    try:
        return Repo(path)
    except InvalidGitRepositoryError as e:
        raise SystemExit(f"❌ Not a git repo: {path}") from e


def ensure_clean_superproject(repo: Repo, allow_dirty: bool = False) -> None:
    # superproject dirtiness does not include submodules; check separately
    if repo.is_dirty(untracked_files=True) and not allow_dirty:
        raise SystemExit("❌ Superproject has uncommitted changes. Commit/stash first.")


def ensure_submodules_initialized() -> None:
    # sync URLs from .gitmodules, then init/update recursively
    run(["git", "submodule", "sync", "--recursive"])
    # depth=1 keeps it fast; remove if you prefer full history
    run(["git", "submodule", "update", "--init", "--recursive", "--depth", "1"])


def fetch_remote(sub_repo: Repo, remote: str, branch: str) -> None:
    try:
        sub_repo.git.fetch(remote, branch)
    except GitCommandError as e:
        raise SystemExit(
            f"❌ Failed to fetch {remote}/{branch} in {sub_repo.working_dir}: {e}"
        ) from e


def current_sha(sub_repo: Repo) -> str:
    return sub_repo.head.commit.hexsha


def remote_sha(sub_repo: Repo, remote: str, branch: str) -> str:
    return sub_repo.git.rev_parse(f"{remote}/{branch}")


def checkout_tracking_branch(sub_repo: Repo, branch: str, remote: str = "origin") -> None:
    try:
        # If branch exists locally, switch to it
        sub_repo.git.checkout(branch)
    except GitCommandError:
        # Create it to track remote tip
        sub_repo.git.checkout("-B", branch, f"{remote}/{branch}")


def ff_to_remote(sub_repo: Repo, branch: str, remote: str = "origin") -> None:
    try:
        # Enforce fast-forward only
        sub_repo.git.merge(f"{remote}/{branch}", ff_only=True)
    except GitCommandError as e:
        raise SystemExit(
            f"❌ Fast-forward failed in {sub_repo.working_dir}. "
            f"Likely diverged history or local changes.\n{e}"
        ) from e


# ---------------------------
# Main bump logic
# ---------------------------

def bump_submodule(mod: ModuleConfig, dry_run: bool = False) -> tuple[str, str, bool]:
    """
    Return (name, new_sha, changed?)
    """
    sub_path = Path(mod.name)
    if not sub_path.exists():
        raise SystemExit(f"❌ Submodule path not found: {mod.name}")

    print(f"\n📦 {mod.name} @ {mod.branch}")

    sub_repo = Repo(sub_path)

    # Guard: submodule must be clean
    if sub_repo.is_dirty(untracked_files=True):
        raise SystemExit(f"❌ {mod.name} has uncommitted changes. Commit/stash first.")

    # Ensure we’re on the right branch and up-to-date with remote
    fetch_remote(sub_repo, "origin", mod.branch)
    checkout_tracking_branch(sub_repo, mod.branch, "origin")

    local = current_sha(sub_repo)
    remote = remote_sha(sub_repo, "origin", mod.branch)

    if local == remote:
        print(f"✅ Up to date ({local[:8]})")
        return (mod.name, local, False)

    if dry_run:
        print(f"🟡 [DRY-RUN] {local[:8]} → {remote[:8]}")
        return (mod.name, remote, True)

    ff_to_remote(sub_repo, mod.branch, "origin")
    new_sha = current_sha(sub_repo)
    print(f"✅ Updated to {new_sha[:8]}")
    return (mod.name, new_sha, True)


def main() -> None:
    ap = argparse.ArgumentParser(description="Automate submodule updates (local-only).")
    ap.add_argument("--config", default="submodules.yaml", help="Path to YAML config.")
    ap.add_argument("--tag", help="Optional tag name for the superproject.")
    ap.add_argument("--dry-run", action="store_true", help="Preview only; no changes.")
    ap.add_argument("--auto-stash", action="store_true", help="Stash parent before running and restore after.")
    args = ap.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"❌ Config file not found: {config_path}")

    conf = SubmoduleConfig(**yaml.safe_load(config_path.read_text()))
    root = ensure_superproject(Path.cwd())

    if args.auto_stash:
        # Note: we stash only the superproject index/worktree; submodules must be clean
        print("🧺 Auto-stash: parent repo")
        run(["git", "stash", "push", "-u", "-m", "pre-bump (parent)"])

    try:
        ensure_clean_superproject(root, allow_dirty=False)
        ensure_submodules_initialized()

        # Process modules
        changes: Dict[str, str] = {}
        for mod in conf.modules:
            name, sha, changed = bump_submodule(mod, dry_run=args.dry_run)
            if changed:
                changes[name] = sha

        if args.dry_run:
            print("\n💡 Dry run complete — no commits made.")
            return

        if not changes:
            print("\n✅ Nothing to bump; parent unchanged.")
            return

        # Stage submodule pointers and commit
        root.git.add(".gitmodules", *[m.name for m in conf.modules])
        msg_lines = [ "chore(submodules): bump to latest", "" ]
        msg_lines += [ f"- {name}: {sha[:8]}" for name, sha in changes.items() ]
        commit_msg = "\n".join(msg_lines)
        root.index.commit(commit_msg)
        print(f"\n📝 Committed:\n{commit_msg}")

        # Tag if requested
        if args.tag:
            root.create_tag(args.tag)
            print(f"🏷️ Created tag {args.tag}")

        # Push (include tags if any)
        push_args = ["git", "push", "--follow-tags"]
        run(push_args)
        print("🚀 Pushed superproject changes successfully.")

    finally:
        if args.auto_stash:
            print("🧺 Restoring parent stash (if any)")
            run(["git", "stash", "pop"], cwd=Path.cwd())
            # If no stash existed, this will error; you can wrap in try/except if desired


if __name__ == "__main__":
    main()
