# ======================================================================= #
#  Spoolman Lane Sync — KiauhTC Extension                                 #
#  https://github.com/broncosis/spoolman-lane-sync                        #
#                                                                         #
#  Copyright (C) 2026 Broncosis                                           #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from pathlib import Path

SLS_REPO = "https://github.com/broncosis/spoolman-lane-sync.git"
SLS_DIR = Path.home() / "spoolman-lane-sync"
KLIPPER_DIR = Path.home() / "klipper"
KLIPPER_EXTRAS = KLIPPER_DIR / "klippy" / "extras"
SLS_MOONRAKER_SECTION = "update_manager spoolman-lane-sync"
