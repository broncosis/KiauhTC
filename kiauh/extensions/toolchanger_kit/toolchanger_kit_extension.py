# ======================================================================= #
#  Toolchanger Kit — KIAUH Extension                                      #
#  https://github.com/Broncosis/toolchanger-installer                     #
#                                                                         #
#  Copyright (C) 2026 Broncosis                                           #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

import shutil
import subprocess
import textwrap
from pathlib import Path
from typing import Dict, List, Optional

from core.logger import Logger
from core.types.color import Color
from extensions.base_extension import BaseExtension

# ── Standard Klipper / printer-data paths ────────────────────────────── #
HOME = Path.home()
KLIPPER_DIR = HOME / "klipper"
KLIPPY_ENV = HOME / "klippy-env"
KLIPPER_EXTRAS = KLIPPER_DIR / "klippy" / "extras"
PRINTER_DATA = HOME / "printer_data"
CONFIG_DIR = PRINTER_DATA / "config"
MOONRAKER_CONF = CONFIG_DIR / "moonraker.conf"
MOONRAKER_ASVC = PRINTER_DATA / "moonraker.asvc"

# ── Upstream repositories ─────────────────────────────────────────────── #
TOOLCHANGER_EASY_REPO = (
    "https://github.com/jwellman80/klipper-toolchanger-easy.git"
)
TOOLCHANGER_EASY_DIR = HOME / "klipper-toolchanger-easy"

CARTOGRAPHER_REPO = (
    "https://github.com/Cartographer3D/cartographer-klipper.git"
)
CARTOGRAPHER_DIR = HOME / "cartographer-klipper"
CARTOGRAPHER_MODULES = ["cartographer.py", "scanner.py", "idm.py"]

AXISCOPE_REPO = "https://github.com/nic335/Axiscope.git"
AXISCOPE_DIR = HOME / "axiscope"
AXISCOPE_VENV = AXISCOPE_DIR / "axiscope-env"

# Last Klipper commit confirmed to work with tap-based probing.
# Several Klipper updates after this commit broke tap; pin here when needed.
KLIPPER_KNOWN_GOOD_COMMIT = "e605fd18560fbb5a7413ca12b72325ad4e18de16"


# ── Module-level helpers ──────────────────────────────────────────────── #

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
    """Symlink all .py files from src_dir into the Klipper extras directory."""
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


def _moonraker_section_present(header: str) -> bool:
    if not MOONRAKER_CONF.exists():
        return False
    return header in MOONRAKER_CONF.read_text()


def _append_moonraker_section(section: str) -> None:
    header = section.splitlines()[0]
    if not MOONRAKER_CONF.exists():
        Logger.print_warn("moonraker.conf not found — skipping update_manager entry")
        return
    if _moonraker_section_present(header):
        Logger.print_info("    Moonraker section already present, skipping")
        return
    with MOONRAKER_CONF.open("a") as fh:
        fh.write(f"\n{section}\n")
    Logger.print_ok("    Added Moonraker update_manager section")


def _remove_moonraker_section(header: str) -> None:
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


def _append_printer_cfg_include(include_line: str) -> None:
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


# ── Extension class ───────────────────────────────────────────────────── #

class ToolchangerKitExtension(BaseExtension):

    # Component registry: key → (directory, human name)
    COMPONENTS = {
        "toolchanger_easy": (TOOLCHANGER_EASY_DIR, "klipper-toolchanger-easy"),
        "cartographer":     (CARTOGRAPHER_DIR,      "Cartographer probe plugin"),
        "axiscope":         (AXISCOPE_DIR,           "Axiscope tool alignment"),
    }

    def __init__(self, metadata: Dict[str, str]):
        super().__init__(metadata)

    # ------------------------------------------------------------------ #
    # BaseExtension interface
    # ------------------------------------------------------------------ #

    def install_extension(self, **kwargs) -> None:
        Logger.print_status("Toolchanger Kit — Install")
        components = self._select_components("install")
        if not components:
            Logger.print_info("Nothing selected.")
            return

        if not KLIPPER_DIR.exists():
            Logger.print_error(
                "Klipper not found at ~/klipper. "
                "Install Klipper via KIAUH before continuing."
            )
            return

        if "toolchanger_easy" in components:
            self._install_toolchanger_easy()
        if "cartographer" in components:
            self._install_cartographer()
        if "axiscope" in components:
            self._install_axiscope()

        Logger.print_ok("\nInstallation complete!")

    def update_extension(self, **kwargs) -> None:
        Logger.print_status("Toolchanger Kit — Update")
        installed = self._detect_installed()
        if not installed:
            Logger.print_warn("No Toolchanger Kit components are installed.")
            return

        components = self._select_components("update", choices=installed)
        if not components:
            return

        if "toolchanger_easy" in components:
            self._update_toolchanger_easy()
        if "cartographer" in components:
            self._update_cartographer()
        if "axiscope" in components:
            self._update_axiscope()

        Logger.print_ok("\nUpdate complete!")

    def remove_extension(self, **kwargs) -> None:
        Logger.print_status("Toolchanger Kit — Remove")
        installed = self._detect_installed()
        if not installed:
            Logger.print_warn("No Toolchanger Kit components are installed.")
            return

        components = self._select_components("remove", choices=installed)
        if not components:
            return

        names = [self.COMPONENTS[c][1] for c in components]
        print(f"\nAbout to remove: {', '.join(names)}")
        confirm = input("Continue? [y/N]: ").strip().lower()
        if confirm != "y":
            Logger.print_info("Aborted.")
            return

        if "toolchanger_easy" in components:
            self._remove_toolchanger_easy()
        if "cartographer" in components:
            self._remove_cartographer()
        if "axiscope" in components:
            self._remove_axiscope()

        Logger.print_ok("\nRemoval complete!")

    # ------------------------------------------------------------------ #
    # Detection & selection helpers
    # ------------------------------------------------------------------ #

    def _detect_installed(self) -> List[str]:
        return [k for k, (d, _) in self.COMPONENTS.items() if d.exists()]

    def _select_components(
        self,
        action: str,
        choices: Optional[List[str]] = None,
    ) -> List[str]:
        available = {
            str(i + 1): (k, name)
            for i, (k, (_, name)) in enumerate(self.COMPONENTS.items())
            if choices is None or k in choices
        }

        print(f"\nSelect components to {action}:")
        for num, (_, name) in available.items():
            print(f"  {num}) {name}")
        print("  a) All of the above")
        print("  0) Cancel\n")

        sel = input("Selection: ").strip().lower()
        if not sel or "0" in sel:
            return []
        if "a" in sel:
            return [k for k, _ in available.values()]

        result = []
        for token in sel.split():
            if token in available:
                result.append(available[token][0])
        return result

    # ------------------------------------------------------------------ #
    # klipper-toolchanger-easy
    # ------------------------------------------------------------------ #

    def _install_toolchanger_easy(self) -> None:
        Logger.print_status("\n── klipper-toolchanger-easy ──")
        _git_clone_or_pull(TOOLCHANGER_EASY_REPO, TOOLCHANGER_EASY_DIR)

        # Python extras
        for extras_subdir in ("extras", "klippy/extras"):
            src = TOOLCHANGER_EASY_DIR / extras_subdir
            if src.exists():
                _symlink_extras(src, KLIPPER_EXTRAS)
                break

        # Python requirements (installed into Klipper's venv)
        req = TOOLCHANGER_EASY_DIR / "requirements.txt"
        if req.exists():
            _pip_install(KLIPPY_ENV, requirements=req)

        # Probe type
        probe_type = self._ask_probe_type()

        if probe_type == "tap":
            self._offer_klipper_rollback()

        # Config directory structure
        tc_cfg = CONFIG_DIR / "toolchanger"
        readonly_dir = tc_cfg / "readonly-configs"
        tools_dir = tc_cfg / "tools"
        for d in (tc_cfg, readonly_dir, tools_dir):
            d.mkdir(parents=True, exist_ok=True)

        # Symlink readonly macro/config files
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

        # Probe-specific config
        probe_map = {
            "tap":     ["probe_tap.cfg",     "toolhead_probe_tap.cfg"],
            "shuttle": ["probe_shuttle.cfg",  "toolhead_probe_shuttle.cfg"],
        }
        for candidate in probe_map[probe_type]:
            probe_src = TOOLCHANGER_EASY_DIR / "configs" / candidate
            if probe_src.exists():
                shutil.copy2(str(probe_src), str(tc_cfg / "probe.cfg"))
                Logger.print_ok(f"    Copied probe config → toolchanger/probe.cfg")
                break

        # Example tool configs (only if not already present — preserve user edits)
        for tools_subdir in ("tools", "example_tools"):
            tools_src = TOOLCHANGER_EASY_DIR / tools_subdir
            if tools_src.exists():
                for f in sorted(tools_src.glob("*.cfg")):
                    dst = tools_dir / f.name
                    if not dst.exists():
                        shutil.copy2(str(f), str(dst))
                        Logger.print_ok(f"    Copied tool template: {f.name}")
                break

        _append_printer_cfg_include(
            "[include toolchanger/readonly-configs/toolchanger-include.cfg]"
        )
        _append_moonraker_section(
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
        Logger.print_warn(
            f"Known-good commit: {KLIPPER_KNOWN_GOOD_COMMIT}"
        )
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

    def _update_toolchanger_easy(self) -> None:
        Logger.print_status("\n── Updating klipper-toolchanger-easy ──")
        _git_clone_or_pull(TOOLCHANGER_EASY_REPO, TOOLCHANGER_EASY_DIR)
        for extras_subdir in ("extras", "klippy/extras"):
            src = TOOLCHANGER_EASY_DIR / extras_subdir
            if src.exists():
                _symlink_extras(src, KLIPPER_EXTRAS)
                break
        _svc("restart", "klipper")

    def _remove_toolchanger_easy(self) -> None:
        Logger.print_status("\n── Removing klipper-toolchanger-easy ──")

        # Remove symlinks that point into the toolchanger-easy directory
        if KLIPPER_EXTRAS.exists():
            for link in KLIPPER_EXTRAS.glob("*.py"):
                if link.is_symlink():
                    resolved = link.resolve()
                    if str(TOOLCHANGER_EASY_DIR) in str(resolved):
                        link.unlink()
                        Logger.print_ok(f"    Removed symlink: {link.name}")

        if TOOLCHANGER_EASY_DIR.exists():
            shutil.rmtree(str(TOOLCHANGER_EASY_DIR))
            Logger.print_ok("    Removed ~/klipper-toolchanger-easy")

        _remove_moonraker_section("[update_manager klipper-toolchanger-easy]")
        Logger.print_warn(
            "Note: ~/printer_data/config/toolchanger/ was preserved."
            " Remove manually if no longer needed."
        )
        _svc("restart", "klipper")

    # ------------------------------------------------------------------ #
    # Cartographer
    # ------------------------------------------------------------------ #

    def _install_cartographer(self) -> None:
        Logger.print_status("\n── Cartographer probe plugin ──")
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

        _append_moonraker_section(
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

    def _update_cartographer(self) -> None:
        Logger.print_status("\n── Updating Cartographer ──")
        _git_clone_or_pull(CARTOGRAPHER_REPO, CARTOGRAPHER_DIR)
        for module in CARTOGRAPHER_MODULES:
            src = CARTOGRAPHER_DIR / module
            if src.exists():
                target = KLIPPER_EXTRAS / module
                if target.exists() or target.is_symlink():
                    target.unlink()
                target.symlink_to(src.resolve())
        _svc("restart", "klipper")

    def _remove_cartographer(self) -> None:
        Logger.print_status("\n── Removing Cartographer ──")
        for module in CARTOGRAPHER_MODULES:
            target = KLIPPER_EXTRAS / module
            if target.is_symlink():
                target.unlink()
                Logger.print_ok(f"    Removed symlink: {module}")

        if CARTOGRAPHER_DIR.exists():
            shutil.rmtree(str(CARTOGRAPHER_DIR))
            Logger.print_ok("    Removed ~/cartographer-klipper")

        _remove_moonraker_section("[update_manager cartographer-klipper]")
        _svc("restart", "klipper")

    # ------------------------------------------------------------------ #
    # Axiscope
    # ------------------------------------------------------------------ #

    def _install_axiscope(self) -> None:
        Logger.print_status("\n── Axiscope tool alignment ──")
        _git_clone_or_pull(AXISCOPE_REPO, AXISCOPE_DIR)

        # Isolated Python venv for the Flask web service
        venv_python = AXISCOPE_VENV / "bin" / "python"
        if not venv_python.exists():
            Logger.print_status("    Creating Python virtual environment ...")
            _run(["python3", "-m", "venv", str(AXISCOPE_VENV)])

        _pip_install(AXISCOPE_VENV, "flask", "waitress")

        # Klipper extra module
        for klipper_mod_path in (
            AXISCOPE_DIR / "klippy" / "extras" / "axiscope.py",
            AXISCOPE_DIR / "axiscope.py",
        ):
            if klipper_mod_path.exists() and KLIPPER_DIR.exists():
                target = KLIPPER_EXTRAS / "axiscope.py"
                if target.exists() or target.is_symlink():
                    target.unlink()
                target.symlink_to(klipper_mod_path.resolve())
                Logger.print_ok("    Linked Klipper module: axiscope.py")
                break

        # systemd service
        username = subprocess.check_output(["whoami"]).decode().strip()
        service_content = textwrap.dedent(f"""\
            [Unit]
            Description=Axiscope Tool Alignment Service
            After=network.target

            [Service]
            Type=simple
            User={username}
            WorkingDirectory={AXISCOPE_DIR}
            ExecStart={AXISCOPE_VENV}/bin/python -m waitress --port=3000 app:app
            Restart=on-failure
            RestartSec=5

            [Install]
            WantedBy=multi-user.target
        """)

        service_path = Path("/etc/systemd/system/axiscope.service")
        Logger.print_status("    Writing systemd service (requires sudo) ...")
        result = subprocess.run(
            ["sudo", "tee", str(service_path)],
            input=service_content.encode(),
            capture_output=True,
        )
        if result.returncode != 0:
            Logger.print_error("    Failed to write systemd service file.")
            Logger.print_error(f"    {result.stderr.decode().strip()}")
            return

        _run(["sudo", "systemctl", "daemon-reload"])
        _run(["sudo", "systemctl", "enable", "--now", "axiscope"])

        # Moonraker service registration
        if MOONRAKER_ASVC.exists():
            content = MOONRAKER_ASVC.read_text()
            if "axiscope" not in content:
                with MOONRAKER_ASVC.open("a") as fh:
                    fh.write("axiscope\n")
                Logger.print_ok("    Registered axiscope with Moonraker")

        _append_moonraker_section(
            "[update_manager axiscope]\n"
            "type: git_repo\n"
            f"path: {AXISCOPE_DIR}\n"
            "origin: https://github.com/nic335/Axiscope.git\n"
            "managed_services: axiscope\n"
            "primary_branch: main"
        )

        _svc("restart", "moonraker")
        _svc("restart", "klipper")
        Logger.print_ok(
            "Axiscope installed. Access the web UI at http://<printer-ip>:3000"
        )

    def _update_axiscope(self) -> None:
        Logger.print_status("\n── Updating Axiscope ──")
        _git_clone_or_pull(AXISCOPE_REPO, AXISCOPE_DIR)
        _pip_install(AXISCOPE_VENV, "flask", "waitress")
        _svc("restart", "axiscope")

    def _remove_axiscope(self) -> None:
        Logger.print_status("\n── Removing Axiscope ──")
        _svc("stop", "axiscope")
        _svc("disable", "axiscope")

        service_path = Path("/etc/systemd/system/axiscope.service")
        if service_path.exists():
            _run(["sudo", "rm", str(service_path)])
            _run(["sudo", "systemctl", "daemon-reload"])
            Logger.print_ok("    Removed systemd service")

        axiscope_extra = KLIPPER_EXTRAS / "axiscope.py"
        if axiscope_extra.is_symlink():
            axiscope_extra.unlink()
            Logger.print_ok("    Removed Klipper module symlink")

        if MOONRAKER_ASVC.exists():
            lines = MOONRAKER_ASVC.read_text().splitlines()
            cleaned = [ln for ln in lines if ln.strip() != "axiscope"]
            MOONRAKER_ASVC.write_text("\n".join(cleaned) + "\n")
            Logger.print_ok("    Deregistered from Moonraker")

        _remove_moonraker_section("[update_manager axiscope]")

        if AXISCOPE_DIR.exists():
            shutil.rmtree(str(AXISCOPE_DIR))
            Logger.print_ok("    Removed ~/axiscope")

        _svc("restart", "moonraker")
        _svc("restart", "klipper")
