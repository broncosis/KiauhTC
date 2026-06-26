# ======================================================================= #
#  v4l2-UI — KiauhTC Extension                                            #
#  https://github.com/nic335/v4l2-ui                                      #
#                                                                         #
#  Based on work by nic335 (https://github.com/nic335/v4l2-ui)           #
#  Original license: MIT                                                  #
#                                                                         #
#  This file may be distributed under the terms of the GNU GPLv3 license  #
# ======================================================================= #
from pathlib import Path

V4L2_REPO = "https://github.com/nic335/v4l2-ui.git"
V4L2_DIR = Path.home() / "v4l2-ui"
V4L2_SERVICE_NAME = "v4l2-ui"
V4L2_SERVICE_FILE = Path("/etc/systemd/system/v4l2-ui.service")
V4L2_DEFAULT_PORT = 8088
V4L2_MOONRAKER_SECTION = "update_manager v4l2-ui"
