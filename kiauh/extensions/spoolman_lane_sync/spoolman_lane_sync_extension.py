# ======================================================================= #
#  Spoolman Lane Sync — KiauhTC Extension                                 #
#  https://github.com/broncosis/spoolman-lane-sync                        #
#                                                                         #
#  Copyright (C) 2026 Broncosis                                           #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

from typing import Dict, List

from components.klipper.klipper import Klipper
from components.moonraker.moonraker import Moonraker
from core.instance_manager.instance_manager import InstanceManager
from core.logger import Logger
from extensions.base_extension import BaseExtension
from extensions.spoolman import SPOOLMAN_DIR
from extensions.spoolman_lane_sync import (
    KLIPPER_DIR,
    KLIPPER_EXTRAS,
    SLS_DIR,
    SLS_MOONRAKER_SECTION,
    SLS_REPO,
)
from utils.config_utils import add_config_section, remove_config_section
from utils.fs_utils import check_file_exist, create_symlink, run_remove_routines
from utils.git_utils import git_clone_wrapper, git_pull_wrapper
from utils.input_utils import get_confirm
from utils.instance_utils import get_instances, stop_klipper_instances_interactively


class SpoolmanLaneSyncExtension(BaseExtension):
    def __init__(self, metadata: Dict[str, str]):
        super().__init__(metadata)

    def install_extension(self, **kwargs) -> None:
        Logger.print_status("Installing Spoolman Lane Sync ...")

        if not check_file_exist(KLIPPER_DIR):
            Logger.print_error(
                "Klipper not found at ~/klipper. "
                "Install Klipper via KIAUH before continuing."
            )
            return

        if not self._check_spoolman():
            return

        if SLS_DIR.exists():
            if not get_confirm(
                "Spoolman Lane Sync already installed. Reinstall?",
                default_choice=False,
            ):
                return

        kl_instances: List[Klipper] = get_instances(Klipper)
        if not stop_klipper_instances_interactively(
            kl_instances, "installation of Spoolman Lane Sync"
        ):
            return

        try:
            git_clone_wrapper(SLS_REPO, SLS_DIR, force=True)
            self._link_extras()

            mr_instances: List[Moonraker] = get_instances(Moonraker)
            if mr_instances and get_confirm(
                "Add Spoolman Lane Sync to Moonraker update manager?",
                default_choice=True,
            ):
                self._add_moonraker_section(mr_instances)
        except Exception as e:
            Logger.print_error(f"Installation failed: {e}")
            InstanceManager.start_all(kl_instances)
            return

        InstanceManager.start_all(kl_instances)
        Logger.print_ok("Spoolman Lane Sync installed successfully!")

    def update_extension(self, **kwargs) -> None:
        if not check_file_exist(SLS_DIR):
            Logger.print_info("Spoolman Lane Sync is not installed. Nothing to update.")
            return

        kl_instances: List[Klipper] = get_instances(Klipper)
        if not stop_klipper_instances_interactively(
            kl_instances, "update of Spoolman Lane Sync"
        ):
            return

        try:
            Logger.print_status("Updating Spoolman Lane Sync ...")
            git_pull_wrapper(SLS_DIR)
            self._link_extras()
        except Exception as e:
            Logger.print_error(f"Update failed: {e}")

        InstanceManager.start_all(kl_instances)
        Logger.print_ok("Spoolman Lane Sync updated successfully!")

    def remove_extension(self, **kwargs) -> None:
        if not check_file_exist(SLS_DIR):
            Logger.print_info("Spoolman Lane Sync is not installed. Nothing to remove.")
            return

        if not get_confirm("Remove Spoolman Lane Sync?", default_choice=False):
            return

        kl_instances: List[Klipper] = get_instances(Klipper)
        if not stop_klipper_instances_interactively(
            kl_instances, "removal of Spoolman Lane Sync"
        ):
            return

        try:
            self._remove_extras()
            mr_instances: List[Moonraker] = get_instances(Moonraker)
            remove_config_section(SLS_MOONRAKER_SECTION, mr_instances)
            if mr_instances:
                InstanceManager.restart_all(mr_instances)
            run_remove_routines(SLS_DIR)
        except Exception as e:
            Logger.print_error(f"Removal failed: {e}")

        InstanceManager.start_all(kl_instances)
        Logger.print_ok("Spoolman Lane Sync removed successfully!")

    def _check_spoolman(self) -> bool:
        if SPOOLMAN_DIR.exists():
            return True

        Logger.print_warn(
            "\nSpoolman does not appear to be installed (~/spoolman not found)."
        )
        Logger.print_warn(
            "Spoolman Lane Sync requires Spoolman to function correctly."
        )
        print(
            "\nYou can install Spoolman from the Extensions menu (Spoolman (Docker)).\n"
        )
        return get_confirm(
            "Continue installing Spoolman Lane Sync without Spoolman?",
            default_choice=False,
        )

    def _link_extras(self) -> None:
        for candidate in ("klippy/extras", "extras", "."):
            src = SLS_DIR / candidate
            if not src.is_dir():
                continue
            py_files = list(src.glob("*.py"))
            if not py_files:
                continue
            Logger.print_status(f"Linking extras from {src} ...")
            for py in sorted(py_files):
                create_symlink(py, KLIPPER_EXTRAS / py.name)
                Logger.print_ok(f"    Linked: {py.name}")
            return
        Logger.print_warn("No Python extras found in Spoolman Lane Sync repo.")

    def _remove_extras(self) -> None:
        for link in KLIPPER_EXTRAS.glob("*.py"):
            if link.is_symlink() and str(SLS_DIR) in str(link.resolve()):
                link.unlink()
                Logger.print_ok(f"    Removed symlink: {link.name}")

    def _add_moonraker_section(self, mr_instances: List[Moonraker]) -> None:
        add_config_section(
            section=SLS_MOONRAKER_SECTION,
            instances=mr_instances,
            options=[
                ("type", "git_repo"),
                ("channel", "dev"),
                ("path", SLS_DIR.as_posix()),
                ("origin", SLS_REPO),
                ("managed_services", "klipper"),
                ("primary_branch", "main"),
            ],
        )
        InstanceManager.restart_all(mr_instances)
        Logger.print_ok("Added Spoolman Lane Sync to Moonraker update manager.")
