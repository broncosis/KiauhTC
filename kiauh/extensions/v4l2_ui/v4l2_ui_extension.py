# ======================================================================= #
#  v4l2-UI — KiauhTC Extension                                            #
#  https://github.com/nic335/v4l2-ui                                      #
#                                                                         #
#  Based on work by nic335 (https://github.com/nic335/v4l2-ui)           #
#  Original license: MIT                                                  #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

import subprocess
import textwrap
from typing import Dict, List

from components.moonraker.moonraker import Moonraker
from core.instance_manager.instance_manager import InstanceManager
from core.logger import Logger
from extensions.base_extension import BaseExtension
from extensions.v4l2_ui import (
    V4L2_DEFAULT_PORT,
    V4L2_DIR,
    V4L2_MOONRAKER_SECTION,
    V4L2_REPO,
    V4L2_SERVICE_FILE,
    V4L2_SERVICE_NAME,
)
from utils.config_utils import add_config_section, remove_config_section
from utils.fs_utils import check_file_exist, run_remove_routines
from utils.git_utils import git_clone_wrapper, git_pull_wrapper
from utils.input_utils import get_confirm
from utils.instance_utils import get_instances
from utils.sys_utils import get_ipv4_addr


class V4l2UiExtension(BaseExtension):
    def __init__(self, metadata: Dict[str, str]):
        super().__init__(metadata)

    def install_extension(self, **kwargs) -> None:
        Logger.print_status("Installing v4l2-UI ...")

        if not self._check_v4l2():
            return

        if V4L2_DIR.exists():
            if not get_confirm(
                "v4l2-UI already installed. Reinstall?", default_choice=False
            ):
                return

        try:
            git_clone_wrapper(V4L2_REPO, V4L2_DIR, force=True)
            self._install_dependencies()
            self._write_service()

            subprocess.run(["sudo", "systemctl", "daemon-reload"], check=False)
            subprocess.run(
                ["sudo", "systemctl", "enable", "--now", V4L2_SERVICE_NAME],
                check=False,
            )

            mr_instances: List[Moonraker] = get_instances(Moonraker)
            if mr_instances and get_confirm(
                "Add v4l2-UI to Moonraker update manager?", default_choice=True
            ):
                self._add_moonraker_section(mr_instances)

            ip = get_ipv4_addr()
            Logger.print_ok(
                f"v4l2-UI installed! Access it at http://{ip}:{V4L2_DEFAULT_PORT}"
            )

        except Exception as e:
            Logger.print_error(f"Installation failed: {e}")

    def update_extension(self, **kwargs) -> None:
        if not check_file_exist(V4L2_DIR):
            Logger.print_info("v4l2-UI is not installed. Nothing to update.")
            return

        try:
            Logger.print_status("Updating v4l2-UI ...")
            git_pull_wrapper(V4L2_DIR)
            subprocess.run(
                ["sudo", "systemctl", "restart", V4L2_SERVICE_NAME], check=False
            )
        except Exception as e:
            Logger.print_error(f"Update failed: {e}")
            return

        Logger.print_ok("v4l2-UI updated successfully!")

    def remove_extension(self, **kwargs) -> None:
        if not check_file_exist(V4L2_DIR) and not V4L2_SERVICE_FILE.exists():
            Logger.print_info("v4l2-UI is not installed. Nothing to remove.")
            return

        if not get_confirm("Remove v4l2-UI?", default_choice=False):
            return

        try:
            subprocess.run(
                ["sudo", "systemctl", "disable", "--now", V4L2_SERVICE_NAME],
                check=False,
            )
            if V4L2_SERVICE_FILE.exists():
                subprocess.run(["sudo", "rm", str(V4L2_SERVICE_FILE)], check=False)
                subprocess.run(["sudo", "systemctl", "daemon-reload"], check=False)
                Logger.print_ok("    Removed systemd service")

            mr_instances: List[Moonraker] = get_instances(Moonraker)
            remove_config_section(V4L2_MOONRAKER_SECTION, mr_instances)
            if mr_instances:
                InstanceManager.restart_all(mr_instances)

            run_remove_routines(V4L2_DIR)
        except Exception as e:
            Logger.print_error(f"Removal failed: {e}")
            return

        Logger.print_ok("v4l2-UI removed successfully!")

    def _check_v4l2(self) -> bool:
        result = subprocess.run(
            ["which", "v4l2-ctl"], capture_output=True
        )
        if result.returncode == 0:
            return True

        Logger.print_warn(
            "\nv4l2-utils does not appear to be installed."
        )
        Logger.print_info(
            "Install it with:  sudo apt-get install v4l-utils"
        )
        return get_confirm(
            "Continue installing v4l2-UI without v4l2-utils?",
            default_choice=False,
        )

    def _install_dependencies(self) -> None:
        req = V4L2_DIR / "requirements.txt"
        venv = V4L2_DIR / "venv"

        if not (venv / "bin" / "python").exists():
            Logger.print_status("    Creating Python virtual environment ...")
            subprocess.run(["python3", "-m", "venv", str(venv)], check=True)

        pip = venv / "bin" / "pip"
        if req.exists():
            Logger.print_status("    Installing Python requirements ...")
            subprocess.run([str(pip), "install", "-r", str(req)], check=True)
        else:
            subprocess.run([str(pip), "install", "flask", "waitress"], check=True)

    def _write_service(self) -> None:
        import getpass
        username = getpass.getuser()
        venv_python = V4L2_DIR / "venv" / "bin" / "python"

        # Try common entry points
        for entry in ("app.py", "main.py", "server.py"):
            if (V4L2_DIR / entry).exists():
                entrypoint = entry
                break
        else:
            entrypoint = "app.py"

        service = textwrap.dedent(f"""\
            [Unit]
            Description=v4l2-UI Camera Configuration Web Service
            After=network.target

            [Service]
            Type=simple
            User={username}
            WorkingDirectory={V4L2_DIR}
            ExecStart={venv_python} {V4L2_DIR}/{entrypoint}
            Restart=on-failure
            RestartSec=5

            [Install]
            WantedBy=multi-user.target
        """)

        Logger.print_status("    Writing systemd service (requires sudo) ...")
        result = subprocess.run(
            ["sudo", "tee", str(V4L2_SERVICE_FILE)],
            input=service.encode(),
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to write service file: {result.stderr.decode().strip()}"
            )
        Logger.print_ok("    Systemd service written.")

    def _add_moonraker_section(self, mr_instances: List[Moonraker]) -> None:
        add_config_section(
            section=V4L2_MOONRAKER_SECTION,
            instances=mr_instances,
            options=[
                ("type", "git_repo"),
                ("channel", "dev"),
                ("path", V4L2_DIR.as_posix()),
                ("origin", V4L2_REPO),
                ("managed_services", V4L2_SERVICE_NAME),
                ("primary_branch", "main"),
            ],
        )
        InstanceManager.restart_all(mr_instances)
        Logger.print_ok("Added v4l2-UI to Moonraker update manager.")
