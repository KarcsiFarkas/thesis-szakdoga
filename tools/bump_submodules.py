#!/usr/bin/env python3
"""
bump_submodules.py — Local-only Git orchestrator for submodule updates.
Requires: Python 3.12+, PyYAML, GitPython

Usage:
    python tools/bump_submodules.py [--tag v1.0] [--dry-run]
"""

from __future__ import annotations
import subprocess
import sys
import argparse
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field
from git import Repo, GitCommandError


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
    """Run a local git command with subprocess for transparency."""
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout.strip()


def bump_submodule(repo: Repo, mod: ModuleConfig, dry_run: bool = False) -> str:
    """Fast-forward the submodule to latest remote branch."""
    sub_path = Path(mod.name)
    if not sub_path.exists():
        raise FileNotFoundError(f"Submodule path not found: {mod.name}")

    print(f"\n📦 Updating submodule: {mod.name} ({mod.branch})")

    sub_repo = Repo(sub_path)
    sub_repo.git.fetch("origin", mod.branch)

    local_sha = sub_repo.head.commit.hexsha
    remote_sha = sub_repo.git.rev_parse(f"origin/{mod.branch}")

    if local_sha == remote_sha:
        print(f"✅ {mod.name} already up to date ({local_sha[:8]})")
        return local_sha

    if dry_run:
        print(f"🟡 [DRY-RUN] Would update {mod.name} from {local_sha[:8]} → {remote_sha[:8]}")
        return remote_sha

    # Fast-forward merge
    try:
        sub_repo.git.checkout(mod.branch)
        sub_repo.git.merge(f"origin/{mod.branch}", ff_only=True)
    except GitCommandError as e:
        raise RuntimeError(f"Failed to fast-forward {mod.name}: {e}")

    print(f"✅ Updated {mod.name} to {remote_sha[:8]}")
    return remote_sha


# ---------------------------
# Main logic
# ---------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Automate submodule updates.")
    parser.add_argument("--config", default="submodules.yaml", help="Path to YAML config.")
    parser.add_argument("--tag", help="Optional tag name for the superproject.")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes only.")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        sys.exit(f"❌ Config file not found: {config_path}")

    conf = SubmoduleConfig(**yaml.safe_load(config_path.read_text()))
    root = Repo(Path.cwd())

    if root.is_dirty():
        sys.exit("❌ Superproject has uncommitted changes. Commit or stash first.")

    updated = {}
    for mod in conf.modules:
        sha = bump_submodule(root, mod, dry_run=args.dry_run)
        updated[mod.name] = sha

    if args.dry_run:
        print("\n💡 Dry run complete — no commits made.")
        sys.exit(0)

    # Stage & commit updated submodules
    root.git.add(".gitmodules", *[m.name for m in conf.modules])
    commit_msg = "chore(submodules): bump to latest\n\n" + "\n".join(
        f"- {n}: {s[:8]}" for n, s in updated.items()
    )
    root.index.commit(commit_msg)
    print(f"\n📝 Committed submodule bumps:\n{commit_msg}")

    if args.tag:
        root.create_tag(args.tag)
        print(f"🏷️ Created tag {args.tag}")

    root.remote("origin").push()
    print("🚀 Pushed superproject changes successfully.")


if __name__ == "__main__":
    main()
