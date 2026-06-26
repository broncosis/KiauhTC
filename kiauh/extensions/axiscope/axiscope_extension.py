# ======================================================================= #
#  Axiscope — KiauhTC Extension                                           #
#  https://github.com/nic335/Axiscope                                     #
#                                                                         #
#  Based on work by nic335                                                #
#  Original license: MIT                                                  #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path
from typing import Dict, List, Optional

from core.logger import Logger
from extensions.base_extension import BaseExtension

HOME = Path.home()
KLIPPER_DIR = HOME / "klipper"
KLIPPER_EXTRAS = KLIPPER_DIR / "klippy" / "extras"
MOONRAKER_CONF = HOME / "printer_data" / "config" / "moonraker.conf"
MOONRAKER_ASVC = HOME / "printer_data" / "moonraker.asvc"

AXISCOPE_REPO = "https://github.com/nic335/Axiscope.git"
AXISCOPE_DIR = HOME / "axiscope"
AXISCOPE_VENV = AXISCOPE_DIR / "axiscope-env"


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


class AxiscopeExtension(BaseExtension):

    def __init__(self, metadata: Dict[str, str]):
        super().__init__(metadata)

    def install_extension(self, **kwargs) -> None:
        Logger.print_status("Installing Axiscope tool alignment ...")

        if not KLIPPER_DIR.exists():
            Logger.print_error(
                "Klipper not found at ~/klipper. "
                "Install Klipper via KIAUH before continuing."
            )
            return

        _git_clone_or_pull(AXISCOPE_REPO, AXISCOPE_DIR)

        venv_python = AXISCOPE_VENV / "bin" / "python"
        if not venv_python.exists():
            Logger.print_status("    Creating Python virtual environment ...")
            _run(["python3", "-m", "venv", str(AXISCOPE_VENV)])

        _pip_install(AXISCOPE_VENV, "flask", "waitress")

        for klipper_mod_path in (
            AXISCOPE_DIR / "klippy" / "extras" / "axiscope.py",
            AXISCOPE_DIR / "axiscope.py",
        ):
            if klipper_mod_path.exists():
                target = KLIPPER_EXTRAS / "axiscope.py"
                if target.exists() or target.is_symlink():
                    target.unlink()
                target.symlink_to(klipper_mod_path.resolve())
                Logger.print_ok("    Linked Klipper module: axiscope.py")
                break

        self._write_service()

        _run(["sudo", "systemctl", "daemon-reload"])
        _run(["sudo", "systemctl", "enable", "--now", "axiscope"])

        if MOONRAKER_ASVC.exists() and "axiscope" not in MOONRAKER_ASVC.read_text():
            with MOONRAKER_ASVC.open("a") as fh:
                fh.write("axiscope\n")
            Logger.print_ok("    Registered axiscope with Moonraker")

        _moonraker_append(
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

    def update_extension(self, **kwargs) -> None:
        if not AXISCOPE_DIR.exists():
            Logger.print_info("Axiscope is not installed. Nothing to update.")
            return

        Logger.print_status("Updating Axiscope ...")
        _git_clone_or_pull(AXISCOPE_REPO, AXISCOPE_DIR)
        _pip_install(AXISCOPE_VENV, "flask", "waitress")
        _svc("restart", "axiscope")
        Logger.print_ok("Axiscope updated.")

    def remove_extension(self, **kwargs) -> None:
        if not AXISCOPE_DIR.exists():
            Logger.print_info("Axiscope is not installed. Nothing to remove.")
            return

        confirm = input("\nRemove Axiscope? [y/N]: ").strip().lower()
        if confirm != "y":
            Logger.print_info("Aborted.")
            return

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
            MOONRAKER_ASVC.write_text(
                "\n".join(ln for ln in lines if ln.strip() != "axiscope") + "\n"
            )
            Logger.print_ok("    Deregistered from Moonraker")

        _moonraker_remove("[update_manager axiscope]")

        import shutil
        shutil.rmtree(str(AXISCOPE_DIR))
        Logger.print_ok("    Removed ~/axiscope")

        _svc("restart", "moonraker")
        _svc("restart", "klipper")
        Logger.print_ok("Axiscope removed.")

    def _write_service(self) -> None:
        import getpass
        username = getpass.getuser()
        service = textwrap.dedent(f"""\
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
        Logger.print_status("    Writing systemd service (requires sudo) ...")
        result = subprocess.run(
            ["sudo", "tee", "/etc/systemd/system/axiscope.service"],
            input=service.encode(),
            capture_output=True,
        )
        if result.returncode != 0:
            Logger.print_error("    Failed to write systemd service file.")
            Logger.print_error(f"    {result.stderr.decode().strip()}")
            raise RuntimeError("Service file write failed")
        Logger.print_ok("    Systemd service written.")
