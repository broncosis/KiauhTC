# ======================================================================= #
#  Cartographer Probe — KiauhTC Extension                                 #
#  https://github.com/Cartographer3D/cartographer-klipper                 #
#                                                                         #
#  Based on work by Cartographer3D                                        #
#  Original license: GNU General Public License v3                        #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from core.logger import Logger
from extensions.base_extension import BaseExtension

HOME = Path.home()
KLIPPER_DIR = HOME / "klipper"
KLIPPY_ENV = HOME / "klippy-env"
KLIPPER_EXTRAS = KLIPPER_DIR / "klippy" / "extras"
MOONRAKER_CONF = HOME / "printer_data" / "config" / "moonraker.conf"

CARTOGRAPHER_REPO = "https://github.com/Cartographer3D/cartographer-klipper.git"
CARTOGRAPHER_DIR = HOME / "cartographer-klipper"
CARTOGRAPHER_MODULES = ["cartographer.py", "scanner.py", "idm.py"]


def _run(cmd: List[str], check: bool = True, **kwargs) -> subprocess.CompletedProcess:
    Logger.print_info(f"  $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, check=check, **kwargs)


def _git_clone_or_pull(repo: str, dest: Path) -> None:
    if dest.exists():
        Logger.print_status(f"Updating {dest.name} ...")
        _run(["git", "-C", str(dest), "pull"])
    else:
        Logger.print_status(f"Cloning {repo} ...")
        _run(["git", "clone", "--depth=1", repo, str(dest)])


def _pip_install(venv_dir: Path, *packages: str, requirements: Optional[Path] = None) -> None:
    pip = venv_dir / "bin" / "pip"
    if requirements and requirements.exists():
        _run([str(pip), "install", "-r", str(requirements)])
    elif packages:
        _run([str(pip), "install", *packages])


def _moonraker_present(header: str) -> bool:
    return MOONRAKER_CONF.exists() and header in MOONRAKER_CONF.read_text()


def _moonraker_append(section: str) -> None:
    header = section.splitlines()[0]
    if not MOONRAKER_CONF.exists():
        Logger.print_warn("moonraker.conf not found — skipping update_manager entry")
        return
    if _moonraker_present(header):
        Logger.print_info("    Moonraker section already present, skipping")
        return
    with MOONRAKER_CONF.open("a") as fh:
        fh.write(f"\n{section}\n")
    Logger.print_ok("    Added Moonraker update_manager section")


def _moonraker_remove(header: str) -> None:
    if not MOONRAKER_CONF.exists():
        return
    lines = MOONRAKER_CONF.read_text().splitlines(keepends=True)
    out, skip = [], False
    for line in lines:
        if line.strip() == header:
            skip = True
        elif skip and line.startswith("[") and line.strip() != header:
            skip = False
        if not skip:
            out.append(line)
    MOONRAKER_CONF.write_text("".join(out))
    Logger.print_ok(f"    Removed {header} from moonraker.conf")


def _svc(action: str, name: str) -> None:
    _run(["sudo", "systemctl", action, name], check=False)


class CartographerExtension(BaseExtension):

    def __init__(self, metadata: Dict[str, str]):
        super().__init__(metadata)

    def install_extension(self, **kwargs) -> None:
        Logger.print_status("Installing Cartographer probe plugin ...")

        if not KLIPPER_DIR.exists():
            Logger.print_error(
                "Klipper not found at ~/klipper. "
                "Install Klipper via KIAUH before continuing."
            )
            return

        _git_clone_or_pull(CARTOGRAPHER_REPO, CARTOGRAPHER_DIR)

        for module in CARTOGRAPHER_MODULES:
            src = CARTOGRAPHER_DIR / module
            if src.exists():
                target = KLIPPER_EXTRAS / module
                if target.exists() or target.is_symlink():
                    target.unlink()
                target.symlink_to(src.resolve())
                Logger.print_ok(f"    Linked: {module}")

        req = CARTOGRAPHER_DIR / "requirements.txt"
        if req.exists():
            Logger.print_status(
                "    Installing Python requirements (may take several minutes)..."
            )
            _pip_install(KLIPPY_ENV, requirements=req)

        _moonraker_append(
            "[update_manager cartographer-klipper]\n"
            "type: git_repo\n"
            "channel: dev\n"
            f"path: {CARTOGRAPHER_DIR}\n"
            "origin: https://github.com/Cartographer3D/cartographer-klipper.git\n"
            "managed_services: klipper\n"
            "primary_branch: master"
        )
        _svc("restart", "klipper")
        Logger.print_ok("Cartographer installed.")

    def update_extension(self, **kwargs) -> None:
        if not CARTOGRAPHER_DIR.exists():
            Logger.print_info("Cartographer is not installed. Nothing to update.")
            return

        Logger.print_status("Updating Cartographer ...")
        _git_clone_or_pull(CARTOGRAPHER_REPO, CARTOGRAPHER_DIR)
        for module in CARTOGRAPHER_MODULES:
            src = CARTOGRAPHER_DIR / module
            if src.exists():
                target = KLIPPER_EXTRAS / module
                if target.exists() or target.is_symlink():
                    target.unlink()
                target.symlink_to(src.resolve())
        _svc("restart", "klipper")
        Logger.print_ok("Cartographer updated.")

    def remove_extension(self, **kwargs) -> None:
        if not CARTOGRAPHER_DIR.exists():
            Logger.print_info("Cartographer is not installed. Nothing to remove.")
            return

        confirm = input("\nRemove Cartographer probe plugin? [y/N]: ").strip().lower()
        if confirm != "y":
            Logger.print_info("Aborted.")
            return

        for module in CARTOGRAPHER_MODULES:
            target = KLIPPER_EXTRAS / module
            if target.is_symlink():
                target.unlink()
                Logger.print_ok(f"    Removed symlink: {module}")

        shutil.rmtree(str(CARTOGRAPHER_DIR))
        Logger.print_ok("    Removed ~/cartographer-klipper")

        _moonraker_remove("[update_manager cartographer-klipper]")
        _svc("restart", "klipper")
        Logger.print_ok("Cartographer removed.")
