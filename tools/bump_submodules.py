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


def check_branch_exists(repo: Repo, branch_name: str) -> bool:
    """Check if a branch exists locally in the repository."""
    try:
        repo.git.rev_parse("--verify", branch_name)
        return True
    except GitCommandError:
        return False


def create_new_branch_all_repos(conf: SubmoduleConfig, root: Repo, branch_name: str) -> None:
    """
    Create a new branch in the superproject and all submodules.
    First checks if the branch exists anywhere; if so, exits with error.
    Only creates the branch if it doesn't exist in any repo.
    """
    print(f"🔍 Checking if branch '{branch_name}' exists in any repo...")
    
    # Check superproject
    if check_branch_exists(root, branch_name):
        raise SystemExit(f"❌ Branch '{branch_name}' already exists in superproject. Aborting.")
    print(f"✅ Superproject: branch '{branch_name}' does not exist")
    
    # Check all submodules
    for mod in conf.modules:
        sub_path = Path(mod.name)
        if not sub_path.exists():
            raise SystemExit(f"❌ Submodule path not found: {mod.name}")
        
        sub_repo = Repo(sub_path)
        if check_branch_exists(sub_repo, branch_name):
            raise SystemExit(f"❌ Branch '{branch_name}' already exists in submodule '{mod.name}'. Aborting.")
        print(f"✅ {mod.name}: branch '{branch_name}' does not exist")
    
    print(f"\n🌿 Creating branch '{branch_name}' in all repos...")
    
    # Create and checkout branch in superproject
    root.git.checkout("-b", branch_name)
    print(f"✅ Superproject: created and checked out branch '{branch_name}'")
    
    # Create and checkout branch in all submodules
    for mod in conf.modules:
        sub_path = Path(mod.name)
        sub_repo = Repo(sub_path)
        sub_repo.git.checkout("-b", branch_name)
        print(f"✅ {mod.name}: created and checked out branch '{branch_name}'")
    
    print(f"\n🎉 Successfully created and checked out branch '{branch_name}' in all repos!")


def commit_all_repos(conf: SubmoduleConfig, root: Repo, commit_message: str) -> None:
    """
    Commit uncommitted versioned (tracked) files in the superproject and all submodules.
    Only commits files that are already tracked by git (modified or deleted), not untracked files.
    """
    print(f"📝 Committing changes in all repos with message: '{commit_message}'")
    
    committed_count = 0
    
    # Commit superproject
    if root.is_dirty(untracked_files=False):
        root.git.add("-u")  # Stage all modified/deleted tracked files
        root.index.commit(commit_message)
        print(f"✅ Superproject: committed changes")
        committed_count += 1
    else:
        print(f"ℹ️  Superproject: no changes to commit")
    
    # Commit all submodules
    for mod in conf.modules:
        sub_path = Path(mod.name)
        if not sub_path.exists():
            print(f"⚠️  {mod.name}: submodule path not found, skipping")
            continue
        
        sub_repo = Repo(sub_path)
        if sub_repo.is_dirty(untracked_files=False):
            sub_repo.git.add("-u")  # Stage all modified/deleted tracked files
            sub_repo.index.commit(commit_message)
            print(f"✅ {mod.name}: committed changes")
            committed_count += 1
        else:
            print(f"ℹ️  {mod.name}: no changes to commit")
    
    if committed_count > 0:
        print(f"\n🎉 Successfully committed changes in {committed_count} repo(s)!")
    else:
        print(f"\n✅ No uncommitted changes found in any repo.")


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
    ap.add_argument("--new_branch", help="Create and checkout a new branch in all repos (superproject + submodules).")
    ap.add_argument("--commit", help="Commit uncommitted versioned files in all repos with the provided message.")
    args = ap.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        raise SystemExit(f"❌ Config file not found: {config_path}")

    conf = SubmoduleConfig(**yaml.safe_load(config_path.read_text()))
    root = ensure_superproject(Path.cwd())

    # Handle new branch creation
    if args.new_branch:
        ensure_submodules_initialized()
        create_new_branch_all_repos(conf, root, args.new_branch)
        return

    # Handle commit all repos
    if args.commit:
        commit_all_repos(conf, root, args.commit)
        return

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
