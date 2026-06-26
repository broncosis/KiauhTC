# ======================================================================= #
#  Toolchanger Menu — KiauhTC                                             #
#  https://github.com/broncosis/KiauhTC                                   #
#                                                                         #
#  Copyright (C) 2026 Broncosis                                           #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from __future__ import annotations

import importlib
import inspect
import json
import textwrap
from pathlib import Path
from typing import Dict, Type

from core.logger import Logger
from core.menus import Option
from core.menus.base_menu import BaseMenu
from core.types.color import Color
from extensions import EXTENSION_ROOT, GITHUB_ISSUES_URL
from extensions.base_extension import BaseExtension
from extensions.extensions_menu import ExtensionSubmenu


class ToolchangerMenu(BaseMenu):
    def __init__(self, previous_menu: Type[BaseMenu] | None = None):
        super().__init__()
        self.title = "Toolchangers Menu"
        self.title_color = Color.CYAN
        self.previous_menu: Type[BaseMenu] | None = previous_menu
        self.extensions: Dict[str, BaseExtension] = self._discover()

    def set_previous_menu(self, previous_menu: Type[BaseMenu] | None) -> None:
        from core.menus.main_menu import MainMenu

        self.previous_menu = previous_menu if previous_menu is not None else MainMenu

    def set_options(self) -> None:
        self.options = {
            i: Option(self._open_submenu, opt_data=self.extensions.get(i))
            for i in self.extensions
        }

    def _discover(self) -> Dict[str, BaseExtension]:
        ext_dict = {}

        for ext in EXTENSION_ROOT.iterdir():
            metadata_json = Path(ext).joinpath("metadata.json")
            if not metadata_json.exists():
                continue

            try:
                with open(metadata_json, "r") as m:
                    metadata = json.load(m).get("metadata")
                    if metadata.get("menu") != "toolchangers":
                        continue

                    index = str(metadata.get("index"))
                    if index in ext_dict:
                        existing_name = ext_dict[index].metadata.get("display_name")
                        duplicate_name = metadata.get("display_name")
                        Logger.print_warn(
                            f"Duplicate index '{index}' in Toolchangers menu: "
                            f"'{existing_name}' vs '{duplicate_name}'. "
                            f"Skipping '{duplicate_name}'."
                        )
                        continue

                    int(index)
                    module_name = metadata.get("module")
                    module_path = f"kiauh.extensions.{ext.name}.{module_name}"
                    module = importlib.import_module(module_path)

                    def predicate(o):
                        return (
                            inspect.isclass(o)
                            and issubclass(o, BaseExtension)
                            and o != BaseExtension
                        )

                    ext_class: type = inspect.getmembers(module, predicate)[0][1]
                    ext_instance: BaseExtension = ext_class(metadata)
                    ext_dict[index] = ext_instance

            except (
                IOError,
                json.JSONDecodeError,
                ImportError,
                TypeError,
                ValueError,
                AttributeError,
            ) as e:
                Logger.print_warn(
                    f"Failed loading toolchanger extension {ext}: {e}. "
                    f"Please report this at {GITHUB_ISSUES_URL}."
                )

        return dict(sorted(ext_dict.items(), key=lambda x: int(x[0])))

    def _open_submenu(self, **kwargs) -> None:
        ExtensionSubmenu(kwargs.get("opt_data"), self.__class__).run()

    def print_menu(self) -> None:
        line1 = Color.apply("Toolchanger Components:", Color.YELLOW)
        menu = textwrap.dedent(
            f"""
            ╟───────────────────────────────────────────────────────╢
            ║ {line1:<62} ║
            ║                                                       ║
            """
        )[1:]
        print(menu, end="")

        for extension in self.extensions.values():
            index = extension.metadata.get("index")
            name = extension.metadata.get("display_name")
            row = f"{index}) {name}"
            print(f"║ {row:<53} ║")
        print("╟───────────────────────────────────────────────────────╢")
