# SPDX-License-Identifier: GPL-3.0-only
# Copyright (C) 2026 P1Onken (umetate)
"""The platform abstraction (docs/roadmap.md §12.8): everything POSIX runs in the
pinned container via `docker exec`, whilst device writes never use it.

A persistent container (`umetate-host`) of the pinned image runs with the repo
mounted read-write at `/work` and the `umetate-target` volume read-only at
`/opt/jieli`. On Windows the runner uses native `docker.exe` (Docker Desktop) and
falls back to `wsl docker`. `$UMETATE_DOCKER` overrides both.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

IMAGE = "umetate-host-build:latest"
CONTAINER = "umetate-host"
REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class HostProbe:
    docker: bool
    container_running: bool
    toolchain_volume: bool


def _docker() -> str | None:
    """The docker invocation: `$UMETATE_DOCKER`, native `docker`, else `wsl docker`."""
    override = os.environ.get("UMETATE_DOCKER")
    if override:
        return override
    if shutil.which("docker"):
        return "docker"
    if shutil.which("wsl"):
        return "wsl docker"
    return None


def _to_mount(path: Path) -> str:
    """A host path for a `-v` mount (Windows backslashes -> forward slashes)."""
    return str(path).replace("\\", "/")


def ensure_container() -> None:
    """Create/start the persistent `umetate-host` container (no-op if running)."""
    docker = _docker()
    if docker is None:
        raise RuntimeError("docker not found; is Docker Desktop running?")
    exists = subprocess.run(
        docker.split() + ["ps", "-a", "-q", "-f", f"name={CONTAINER}"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not exists:
        mount = f"{_to_mount(REPO_ROOT)}:/work"
        subprocess.run(
            docker.split()
            + [
                "run",
                "-d",
                "--name",
                CONTAINER,
                "--shm-size=512m",
                "-v",
                mount,
                "-v",
                "umetate-target:/opt/jieli:ro",
                IMAGE,
                "sleep",
                "infinity",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        return
    running = subprocess.run(
        docker.split() + ["ps", "-q", "-f", f"name={CONTAINER}"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not running:
        subprocess.run(docker.split() + ["start", CONTAINER], check=True)


def run(
    cmd: list[str], *, cwd: str = "/work", env: dict[str, str] | None = None
) -> int:
    """Run `cmd` in the container (docker exec); returns its exit code."""
    docker = _docker()
    if docker is None:
        raise RuntimeError("docker not found; is Docker Desktop running?")
    ensure_container()
    full = docker.split() + ["exec", "-w", cwd, CONTAINER] + cmd
    return subprocess.run(full, env=env).returncode


def run_writable(cmd: list[str]) -> int:
    """Run `cmd` in a throwaway container with `umetate-target` mounted read-write.

    `umetate setup` is the only legitimate writer to the volume, so the persistent
    container and every build keep it read-only. The repo is mounted at `/work`, so
    a `--toolchain/--sdk` path under the checkout stays visible.
    """
    docker = _docker()
    if docker is None:
        raise RuntimeError("docker not found; is Docker Desktop running?")
    full = (
        docker.split()
        + [
            "run",
            "--rm",
            "-v",
            f"{_to_mount(REPO_ROOT)}:/work",
            "-v",
            "umetate-target:/opt/jieli",
            "-w",
            "/work",
            IMAGE,
        ]
        + cmd
    )
    return subprocess.run(full).returncode


def probe() -> HostProbe:
    """The runner's read-only view: docker present? container up? volume present?"""
    docker = _docker()
    if docker is None:
        return HostProbe(docker=False, container_running=False, toolchain_volume=False)
    running = subprocess.run(
        docker.split() + ["ps", "-q", "-f", f"name={CONTAINER}"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    volume = (
        subprocess.run(
            docker.split() + ["volume", "inspect", "umetate-target"],
            capture_output=True,
            text=True,
        ).returncode
        == 0
    )
    return HostProbe(
        docker=True, container_running=bool(running), toolchain_volume=volume
    )
