# ======================================================================= #
#  Toolchanger Kit (klipper-toolchanger-easy) — KiauhTC Extension         #
#  https://github.com/Broncosis/KiauhTC                                   #
#                                                                         #
#  Copyright (C) 2026 Broncosis                                           #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from core.logger import Logger
from extensions.base_extension import BaseExtension

# ── Paths ─────────────────────────────────────────────────────────────── #
HOME = Path.home()
KLIPPER_DIR = HOME / "klipper"
KLIPPY_ENV = HOME / "klippy-env"
KLIPPER_EXTRAS = KLIPPER_DIR / "klippy" / "extras"
CONFIG_DIR = HOME / "printer_data" / "config"
MOONRAKER_CONF = CONFIG_DIR / "moonraker.conf"

TOOLCHANGER_EASY_REPO = "https://github.com/jwellman80/klipper-toolchanger-easy.git"
TOOLCHANGER_EASY_DIR = HOME / "klipper-toolchanger-easy"

# Last Klipper commit confirmed to work with tap-based probing.
# Several Klipper updates after this commit broke tap; pin here when needed.
KLIPPER_KNOWN_GOOD_COMMIT = "e605fd18560fbb5a7413ca12b72325ad4e18de16"


# ── Helpers ───────────────────────────────────────────────────────────── #

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


def _symlink_extras(src_dir: Path, extras_dir: Path) -> None:
    for py_file in sorted(src_dir.glob("*.py")):
        target = extras_dir / py_file.name
        if target.exists() or target.is_symlink():
            target.unlink()
        target.symlink_to(py_file.resolve())
        Logger.print_ok(f"    Linked {py_file.name}")


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


def _printer_cfg_include(include_line: str) -> None:
    printer_cfg = CONFIG_DIR / "printer.cfg"
    if not printer_cfg.exists():
        Logger.print_warn("printer.cfg not found — skipping include directive")
        return
    if include_line in printer_cfg.read_text():
        Logger.print_info("    Include already in printer.cfg")
        return
    with printer_cfg.open("a") as fh:
        fh.write(f"\n{include_line}\n")
    Logger.print_ok(f"    Added to printer.cfg: {include_line}")


def _svc(action: str, name: str) -> None:
    _run(["sudo", "systemctl", action, name], check=False)


# ── Extension ─────────────────────────────────────────────────────────── #

class ToolchangerKitExtension(BaseExtension):

    def __init__(self, metadata: Dict[str, str]):
        super().__init__(metadata)

    def install_extension(self, **kwargs) -> None:
        Logger.print_status("Installing klipper-toolchanger-easy ...")

        if not KLIPPER_DIR.exists():
            Logger.print_error(
                "Klipper not found at ~/klipper. "
                "Install Klipper via KIAUH before continuing."
            )
            return

        _git_clone_or_pull(TOOLCHANGER_EASY_REPO, TOOLCHANGER_EASY_DIR)

        for extras_subdir in ("extras", "klippy/extras"):
            src = TOOLCHANGER_EASY_DIR / extras_subdir
            if src.exists():
                _symlink_extras(src, KLIPPER_EXTRAS)
                break

        req = TOOLCHANGER_EASY_DIR / "requirements.txt"
        if req.exists():
            _pip_install(KLIPPY_ENV, requirements=req)

        probe_type = self._ask_probe_type()
        if probe_type == "tap":
            self._offer_klipper_rollback()

        tc_cfg = CONFIG_DIR / "toolchanger"
        readonly_dir = tc_cfg / "readonly-configs"
        tools_dir = tc_cfg / "tools"
        for d in (tc_cfg, readonly_dir, tools_dir):
            d.mkdir(parents=True, exist_ok=True)

        for cfg_subdir in ("config", "configs", "macros"):
            cfg_src = TOOLCHANGER_EASY_DIR / cfg_subdir
            if cfg_src.exists():
                for f in sorted(cfg_src.glob("*.cfg")):
                    target = readonly_dir / f.name
                    if target.exists() or target.is_symlink():
                        target.unlink()
                    target.symlink_to(f.resolve())
                    Logger.print_ok(f"    Linked config: {f.name}")
                break

        probe_map = {
            "tap":     ["probe_tap.cfg",    "toolhead_probe_tap.cfg"],
            "shuttle": ["probe_shuttle.cfg", "toolhead_probe_shuttle.cfg"],
        }
        for candidate in probe_map[probe_type]:
            probe_src = TOOLCHANGER_EASY_DIR / "configs" / candidate
            if probe_src.exists():
                shutil.copy2(str(probe_src), str(tc_cfg / "probe.cfg"))
                Logger.print_ok("    Copied probe config → toolchanger/probe.cfg")
                break

        for tools_subdir in ("tools", "example_tools"):
            tools_src = TOOLCHANGER_EASY_DIR / tools_subdir
            if tools_src.exists():
                for f in sorted(tools_src.glob("*.cfg")):
                    dst = tools_dir / f.name
                    if not dst.exists():
                        shutil.copy2(str(f), str(dst))
                        Logger.print_ok(f"    Copied tool template: {f.name}")
                break

        _printer_cfg_include(
            "[include toolchanger/readonly-configs/toolchanger-include.cfg]"
        )
        _moonraker_append(
            "[update_manager klipper-toolchanger-easy]\n"
            "type: git_repo\n"
            "channel: dev\n"
            f"path: {TOOLCHANGER_EASY_DIR}\n"
            "origin: https://github.com/jwellman80/klipper-toolchanger-easy.git\n"
            "managed_services: klipper\n"
            "primary_branch: main"
        )
        _svc("restart", "klipper")
        Logger.print_ok("klipper-toolchanger-easy installed.")

    def update_extension(self, **kwargs) -> None:
        if not TOOLCHANGER_EASY_DIR.exists():
            Logger.print_info("klipper-toolchanger-easy is not installed. Nothing to update.")
            return

        Logger.print_status("Updating klipper-toolchanger-easy ...")
        _git_clone_or_pull(TOOLCHANGER_EASY_REPO, TOOLCHANGER_EASY_DIR)
        for extras_subdir in ("extras", "klippy/extras"):
            src = TOOLCHANGER_EASY_DIR / extras_subdir
            if src.exists():
                _symlink_extras(src, KLIPPER_EXTRAS)
                break
        _svc("restart", "klipper")
        Logger.print_ok("klipper-toolchanger-easy updated.")

    def remove_extension(self, **kwargs) -> None:
        if not TOOLCHANGER_EASY_DIR.exists():
            Logger.print_info("klipper-toolchanger-easy is not installed. Nothing to remove.")
            return

        confirm = input("\nRemove klipper-toolchanger-easy? [y/N]: ").strip().lower()
        if confirm != "y":
            Logger.print_info("Aborted.")
            return

        if KLIPPER_EXTRAS.exists():
            for link in KLIPPER_EXTRAS.glob("*.py"):
                if link.is_symlink() and str(TOOLCHANGER_EASY_DIR) in str(link.resolve()):
                    link.unlink()
                    Logger.print_ok(f"    Removed symlink: {link.name}")

        shutil.rmtree(str(TOOLCHANGER_EASY_DIR))
        Logger.print_ok("    Removed ~/klipper-toolchanger-easy")

        _moonraker_remove("[update_manager klipper-toolchanger-easy]")
        Logger.print_warn(
            "Note: ~/printer_data/config/toolchanger/ was preserved."
            " Remove manually if no longer needed."
        )
        _svc("restart", "klipper")
        Logger.print_ok("klipper-toolchanger-easy removed.")

    def _ask_probe_type(self) -> str:
        print("\nProbe configuration:")
        print("  1) TAP probe per tool  (each tool has its own Z-probe)")
        print("  2) Shuttle-mounted probe  (single probe on the toolhead carrier)\n")
        while True:
            sel = input("Select probe type [1/2]: ").strip()
            if sel == "1":
                return "tap"
            if sel == "2":
                return "shuttle"
            print("  Please enter 1 or 2.")

    def _offer_klipper_rollback(self) -> None:
        Logger.print_warn(
            "\nWarning: several recent Klipper updates have broken tap-based probing."
        )
        Logger.print_warn(f"Known-good commit: {KLIPPER_KNOWN_GOOD_COMMIT}")
        print(
            "\nRolling back pins Klipper to that commit (detached HEAD).\n"
            "Moonraker will flag Klipper as 'dirty' until you re-attach to a branch.\n"
        )
        sel = input("Roll Klipper back to the known-good version? [y/N]: ").strip().lower()
        if sel != "y":
            Logger.print_info("Skipping Klipper rollback — continuing with current version.")
            return

        Logger.print_status("Pinning Klipper to known-good commit ...")
        try:
            _run(["git", "-C", str(KLIPPER_DIR), "checkout", KLIPPER_KNOWN_GOOD_COMMIT])
            Logger.print_ok(f"Klipper pinned to {KLIPPER_KNOWN_GOOD_COMMIT[:12]}")
        except subprocess.CalledProcessError:
            Logger.print_error("Checkout failed.")
            Logger.print_warn(
                "If Klipper was cloned shallow, run first: "
                "git -C ~/klipper fetch --unshallow"
            )
