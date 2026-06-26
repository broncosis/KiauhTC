# ======================================================================= #
#  KlipperScreen Filament Lanes — KiauhTC Extension                       #
#  https://github.com/broncosis/KlipperScreen-filament-lanes              #
#                                                                         #
#  Copyright (C) 2026 Broncosis                                           #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

import subprocess
from typing import Dict, List

from components.moonraker.moonraker import Moonraker
from core.instance_manager.instance_manager import InstanceManager
from core.logger import Logger
from extensions.base_extension import BaseExtension
from extensions.klipperscreen_filament_lanes import (
    KLIPPERSCREEN_DIR,
    KLIPPERSCREEN_PANELS_DIR,
    KLIPPERSCREEN_STYLES_DIR,
    KSFL_DIR,
    KSFL_MOONRAKER_SECTION,
    KSFL_REPO,
)
from utils.config_utils import add_config_section, remove_config_section
from utils.fs_utils import check_file_exist, create_symlink, run_remove_routines
from utils.git_utils import git_clone_wrapper, git_pull_wrapper
from utils.input_utils import get_confirm
from utils.instance_utils import get_instances


class KlipperscreenFilamentLanesExtension(BaseExtension):
    def __init__(self, metadata: Dict[str, str]):
        super().__init__(metadata)

    def install_extension(self, **kwargs) -> None:
        Logger.print_status("Installing KlipperScreen Filament Lanes ...")

        if not self._check_klipperscreen():
            return

        if KSFL_DIR.exists():
            if not get_confirm(
                "KlipperScreen Filament Lanes already installed. Reinstall?",
                default_choice=False,
            ):
                return

        try:
            git_clone_wrapper(KSFL_REPO, KSFL_DIR, force=True)
            self._link_panels()
            self._link_styles()

            mr_instances: List[Moonraker] = get_instances(Moonraker)
            if mr_instances and get_confirm(
                "Add KlipperScreen Filament Lanes to Moonraker update manager?",
                default_choice=True,
            ):
                self._add_moonraker_section(mr_instances)
        except Exception as e:
            Logger.print_error(f"Installation failed: {e}")
            return

        self._restart_klipperscreen()
        Logger.print_ok("KlipperScreen Filament Lanes installed successfully!")

    def update_extension(self, **kwargs) -> None:
        if not check_file_exist(KSFL_DIR):
            Logger.print_info(
                "KlipperScreen Filament Lanes is not installed. Nothing to update."
            )
            return

        try:
            Logger.print_status("Updating KlipperScreen Filament Lanes ...")
            git_pull_wrapper(KSFL_DIR)
            self._link_panels()
            self._link_styles()
        except Exception as e:
            Logger.print_error(f"Update failed: {e}")
            return

        self._restart_klipperscreen()
        Logger.print_ok("KlipperScreen Filament Lanes updated successfully!")

    def remove_extension(self, **kwargs) -> None:
        if not check_file_exist(KSFL_DIR):
            Logger.print_info(
                "KlipperScreen Filament Lanes is not installed. Nothing to remove."
            )
            return

        if not get_confirm(
            "Remove KlipperScreen Filament Lanes?", default_choice=False
        ):
            return

        try:
            self._remove_links(KLIPPERSCREEN_PANELS_DIR)
            self._remove_links(KLIPPERSCREEN_STYLES_DIR)

            mr_instances: List[Moonraker] = get_instances(Moonraker)
            remove_config_section(KSFL_MOONRAKER_SECTION, mr_instances)
            if mr_instances:
                InstanceManager.restart_all(mr_instances)

            run_remove_routines(KSFL_DIR)
        except Exception as e:
            Logger.print_error(f"Removal failed: {e}")
            return

        self._restart_klipperscreen()
        Logger.print_ok("KlipperScreen Filament Lanes removed successfully!")

    def _check_klipperscreen(self) -> bool:
        if KLIPPERSCREEN_DIR.exists():
            return True

        Logger.print_warn(
            "\nKlipperScreen does not appear to be installed (~/KlipperScreen not found)."
        )
        Logger.print_warn(
            "Install KlipperScreen via KIAUH before installing this extension."
        )
        return False

    def _link_panels(self) -> None:
        panels_src = KSFL_DIR / "panels"
        if not panels_src.is_dir():
            Logger.print_info("No 'panels/' directory found in repo — skipping panel links.")
            return
        KLIPPERSCREEN_PANELS_DIR.mkdir(parents=True, exist_ok=True)
        for py in sorted(panels_src.glob("*.py")):
            create_symlink(py, KLIPPERSCREEN_PANELS_DIR / py.name)
            Logger.print_ok(f"    Linked panel: {py.name}")

    def _link_styles(self) -> None:
        styles_src = KSFL_DIR / "styles"
        if not styles_src.is_dir():
            return
        KLIPPERSCREEN_STYLES_DIR.mkdir(parents=True, exist_ok=True)
        for f in sorted(styles_src.iterdir()):
            create_symlink(f, KLIPPERSCREEN_STYLES_DIR / f.name)
            Logger.print_ok(f"    Linked style: {f.name}")

    def _remove_links(self, target_dir) -> None:
        if not target_dir.exists():
            return
        for link in target_dir.iterdir():
            if link.is_symlink() and str(KSFL_DIR) in str(link.resolve()):
                link.unlink()
                Logger.print_ok(f"    Removed symlink: {link.name}")

    def _add_moonraker_section(self, mr_instances: List[Moonraker]) -> None:
        add_config_section(
            section=KSFL_MOONRAKER_SECTION,
            instances=mr_instances,
            options=[
                ("type", "git_repo"),
                ("channel", "dev"),
                ("path", KSFL_DIR.as_posix()),
                ("origin", KSFL_REPO),
                ("managed_services", "KlipperScreen"),
                ("primary_branch", "main"),
            ],
        )
        InstanceManager.restart_all(mr_instances)
        Logger.print_ok("Added KlipperScreen Filament Lanes to Moonraker update manager.")

    def _restart_klipperscreen(self) -> None:
        Logger.print_status("Restarting KlipperScreen ...")
        subprocess.run(
            ["sudo", "systemctl", "restart", "KlipperScreen"], check=False
        )
