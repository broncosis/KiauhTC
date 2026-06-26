<p align="center">
    <img src="docs/assets/logo-large.png" alt="KIAUH Logo" height="181">
    <h1 align="center">KiauhTC — Klipper Installation And Update Helper</h1>
    <h3 align="center">with Toolchanger Kit support</h3>
</p>

<p align="center">
  A fork of <a href="https://github.com/dw-0/kiauh">KIAUH</a> with extra extensions
  for multi-tool and multi-lane filament printers — toolchanger macros, filament feeders,
  Spoolman lane sync, USB camera setup, and more.
</p>

<p align="center">
  <a><img src="https://img.shields.io/github/license/broncosis/KiauhTC"></a>
  <a><img src="https://img.shields.io/github/stars/broncosis/KiauhTC"></a>
  <a><img src="https://img.shields.io/github/forks/broncosis/KiauhTC"></a>
  <a><img src="https://img.shields.io/github/languages/top/broncosis/KiauhTC?logo=gnubash&logoColor=white"></a>
  <br />
  <a><img src="https://img.shields.io/github/last-commit/broncosis/KiauhTC"></a>
  <a><img src="https://img.shields.io/github/contributors/broncosis/KiauhTC"></a>
</p>

<hr>

<h2 align="center">
  📄️ Instructions 📄
</h2>

### 📋 Prerequisites

KIAUH is a script that assists you in installing Klipper on a Linux operating
system that has
already been flashed to your Raspberry Pi's (or other SBC's) SD card. As a
result, you must ensure
that you have a functional Linux system on hand.
`Raspberry Pi OS Lite (either 32bit or 64bit)` is a recommended Linux image
if you are using a Raspberry Pi.
The [official Raspberry Pi Imager](https://www.raspberrypi.com/software/)
is the simplest way to flash an image like this to an SD card.

* Once you have downloaded, installed and launched the Raspberry Pi Imager,
  select `Choose OS -> Raspberry Pi OS (other)`: \

<p align="center">
  <img src="docs/assets/rpi_imager1.png" alt="KIAUH logo" height="350">
</p>

* Then select `Raspberry Pi OS Lite (32bit)` (or 64bit if you want to use that
  instead):

<p align="center">
  <img src="docs/assets/rpi_imager2.png" alt="KIAUH logo" height="350">
</p>

* Back in the Raspberry Pi Imager's main menu, select the corresponding SD card
  to which
  you want to flash the image.

* Make sure to go into the Advanced Option (the cog icon in the lower left
  corner of the main menu)
  and enable SSH and configure Wi-Fi.

* If you need more help for using the Raspberry Pi Imager, please visit
  the [official documentation](https://www.raspberrypi.com/documentation/computers/getting-started.html).

These steps **only** apply if you are actually using a Raspberry Pi. In case you
want
to use a different SBC (like an Orange Pi or any other Pi derivates), please
look up on how to get an appropriate Linux image flashed
to the SD card before proceeding further (usually done with Balena Etcher in
those cases). Also make sure that KIAUH will be able to run
and operate on the Linux Distribution you are going to flash. You likely will
have the most success with
distributions based on Debian 11 Bullseye. Read the notes further down below in
this document.

### 💾 Download and use KIAUH

**📢 Disclaimer: Usage of this script happens at your own risk!**

* **Step 1:** \
  To download this script, it is necessary to have git installed. If you don't
  have git already installed, or if you are unsure, run the following command:

```shell
sudo apt-get update && sudo apt-get install git -y
```

* **Step 2:** \
  Once git is installed, use the following command to download KIAUH into your
  home-directory:

```shell
cd ~ && git clone https://github.com/broncosis/KiauhTC.git kiauh
```

* **Step 3:** \
  Finally, start KiauhTC by running the next command:

```shell
./kiauh/KiauhTC.sh
```

* **Step 4:** \
  You should now find yourself in the main menu of KIAUH. You will see several
  actions to choose from depending
  on what you want to do. To choose an action, simply type the corresponding
  number into the "Perform action"
  prompt and confirm by hitting ENTER.

<hr>

<h2 align="center">🔧 KiauhTC Extensions</h2>

All extensions below are found in the **Extensions** menu. They all register
with Moonraker's `update_manager` so they can be updated from the Mainsail or
Fluidd UI alongside Klipper.

---

### Toolchanger Kit

Installs and manages multi-tool components for toolchanger printers.

| Component | What it does |
|-----------|-------------|
| [klipper-toolchanger-easy](https://github.com/jwellman80/klipper-toolchanger-easy) | Python extras + macros for tool-change sequences |
| [Cartographer probe](https://github.com/Cartographer3D/cartographer-klipper) | Klipper plugin for Cartographer eddy-current probes |
| [Axiscope](https://github.com/nic335/Axiscope) | Tool alignment web service + Klipper module |

During installation you will be asked which probe type you are using:

- **TAP** — each tool has its own Z-probe. You will also be offered the option
  to roll Klipper back to a known-good commit, because several recent Klipper
  updates have broken tap-based probing.
- **Shuttle** — a single probe is mounted on the toolhead carrier.

> Klipper must be installed via KIAUH before running the Toolchanger Kit installer.

---

### [Filament Feeder](https://github.com/broncosis/Filament_feeder)

Klipper module for multi-lane filament feeding. Installs Python extras and
symlinks them into Klipper's extras directory.

---

### [Spoolman Lane Sync](https://github.com/broncosis/spoolman-lane-sync)

Syncs filament lane data to [Spoolman](https://github.com/Donkie/Spoolman).
During installation, KiauhTC will check whether Spoolman is installed and
suggest installing it first if it is not found.

---

### [KlipperScreen Filament Lanes](https://github.com/broncosis/KlipperScreen-filament-lanes)

Adds filament lane management panels to KlipperScreen. Requires KlipperScreen
to be installed first.

---

### [v4l2-UI](https://github.com/nic335/v4l2-ui)

Web UI for configuring USB cameras via v4l2 — browse and adjust camera
controls (brightness, contrast, focus, exposure, etc.) from a browser.
Runs as a lightweight systemd service; KiauhTC will check that `v4l2-utils`
is installed and print the access URL when setup completes.

<hr>

<h2 align="center">❗ Notes ❗</h2>

### **📋 Please see the [Changelog](docs/changelog.md) for possible important

changes!**

- Mainly tested on Raspberry Pi OS Lite (Debian 10 Buster / Debian 11 Bullseye)
    - Other Debian based distributions (like Ubuntu 20 to 22) likely work too
    - Reported to work on Armbian as well but not tested in detail
- During the use of this script you will be asked for your sudo password. There
  are several functions involved which need sudo privileges.

<hr>

<h2 align="center">🌐 Sources & Further Information</h2>

<table align="center">
<tr>
    <th><h3><a href="https://github.com/Klipper3d/klipper">Klipper</a></h3></th>
    <th><h3><a href="https://github.com/Arksine/moonraker">Moonraker</a></h3></th>
    <th><h3><a href="https://github.com/mainsail-crew/mainsail">Mainsail</a></h3></th>
</tr>
<tr>
    <th><img src="https://raw.githubusercontent.com/Klipper3d/klipper/master/docs/img/klipper-logo.png" alt="Klipper Logo" height="64"></th>
    <th><img src="https://avatars.githubusercontent.com/u/9563098?v=4" alt="Arksine avatar" height="64"></th>
    <th><img src="https://raw.githubusercontent.com/mainsail-crew/docs/master/assets/img/logo.png" alt="Mainsail Logo" height="64"></th>
</tr>
<tr>
    <th>by <a href="https://github.com/KevinOConnor">KevinOConnor</a></th>
    <th>by <a href="https://github.com/Arksine">Arksine</a></th>
    <th>by <a href="https://github.com/mainsail-crew">mainsail-crew</a></th>
</tr>

<tr>
    <th><h3><a href="https://github.com/fluidd-core/fluidd">Fluidd</a></h3></th>
    <th><h3><a href="https://github.com/KlipperScreen/KlipperScreen">KlipperScreen</a></h3></th>
    <th><h3><a href="https://github.com/OctoPrint/OctoPrint">OctoPrint</a></h3></th>
</tr>
<tr>
    <th><img src="https://raw.githubusercontent.com/fluidd-core/fluidd/master/docs/assets/images/logo.svg" alt="Fluidd Logo" height="64"></th>
    <th><img src="https://avatars.githubusercontent.com/u/31575189?v=4" alt="jordanruthe avatar" height="64"></th>
    <th><img src="https://raw.githubusercontent.com/OctoPrint/OctoPrint/master/docs/images/octoprint-logo.png" alt="OctoPrint Logo" height="64"></th>
</tr>
<tr>
    <th>by <a href="https://github.com/fluidd-core">fluidd-core</a></th>
    <th>by <a href="https://github.com/alfrix">alfrix</a></th>
    <th>by <a href="https://github.com/OctoPrint">OctoPrint</a></th>
</tr>

<tr>
    <th><h3><a href="https://github.com/nlef/moonraker-telegram-bot">Moonraker-Telegram-Bot</a></h3></th>
    <th><h3><a href="https://github.com/Kragrathea/pgcode">PrettyGCode for Klipper</a></h3></th>
    <th><h3><a href="https://github.com/TheSpaghettiDetective/moonraker-obico">Obico for Klipper</a></h3></th>
</tr>
<tr>
    <th><img src="https://avatars.githubusercontent.com/u/52351624?v=4" alt="nlef avatar" height="64"></th>
    <th><img src="https://avatars.githubusercontent.com/u/5917231?v=4" alt="Kragrathea avatar" height="64"></th>
    <th><img src="https://avatars.githubusercontent.com/u/46323662?s=200&v=4" alt="Obico logo" height="64"></th>
</tr>
<tr>
    <th>by <a href="https://github.com/nlef">nlef</a></th>
    <th>by <a href="https://github.com/Kragrathea">Kragrathea</a></th>
    <th>by <a href="https://github.com/TheSpaghettiDetective">Obico</a></th>
</tr>

<tr>
    <th><h3><a href="https://github.com/Clon1998/mobileraker_companion">Mobileraker's Companion</a></h3></th>
    <th><h3><a href="https://octoeverywhere.com/?source=kiauh_readme">OctoEverywhere For Klipper</a></h3></th>
    <th><h3><a href="https://github.com/crysxd/OctoApp-Plugin">OctoApp For Klipper</a></h3></th>
</tr>
<tr>
    <th><a href="https://github.com/Clon1998/mobileraker_companion"><img src="https://raw.githubusercontent.com/Clon1998/mobileraker/master/assets/icon/mr_appicon.png" alt="Mobileraker Logo" height="64"></a></th>
    <th><a href="https://octoeverywhere.com/?source=kiauh_readme"><img src="https://octoeverywhere.com/img/logo.svg" alt="OctoEverywhere Logo" height="64"></a></th>
    <th><a href="https://octoapp.eu/?source=kiauh_readme"><img src="https://octoapp.eu/octoapp.webp" alt="OctoApp Logo" height="64"></a></th>
</tr>
<tr>
    <th>by <a href="https://github.com/Clon1998">Patrick Schmidt</a></th>
    <th>by <a href="https://github.com/QuinnDamerell">Quinn Damerell</a></th>
    <th>by <a href="https://github.com/crysxd">Christian Würthner</a></th>
</tr>

<tr>
    <th><h3><a href="https://github.com/staubgeborener/klipper-backup">Klipper-Backup</a></h3></th>
    <th><h3><a href="https://simplyprint.io/">SimplyPrint for Klipper</a></h3></th>
</tr>
<tr>
    <th><a href="https://github.com/staubgeborener/klipper-backup"><img src="https://avatars.githubusercontent.com/u/28908603?v=4" alt="Staubgeroner Avatar" height="64"></a></th>
    <th><a href="https://github.com/SimplyPrint"><img src="https://avatars.githubusercontent.com/u/64896552?s=200&v=4" alt="" height="64"></a></th>
</tr>
<tr>
    <th>by <a href="https://github.com/Staubgeborener">Staubgeborener</a></th>
    <th>by <a href="https://github.com/SimplyPrint">SimplyPrint</a></th>
</tr>
</table>

<hr>

<h2 align="center">🎖️ Contributors 🎖️</h2>

<div align="center">
  <a href="https://github.com/dw-0/kiauh/graphs/contributors">
    <img src="https://contrib.rocks/image?repo=dw-0/kiauh" alt=""/>
  </a>
</div>

<hr>

<div align="center">
    <img src="https://repobeats.axiom.co/api/embed/a1afbda9190c04a90cf4bd3061e5573bc836cb05.svg" alt="Repobeats analytics image"/>
</div>

<hr>

<h2 align="center">✨ Credits ✨</h2>

* KiauhTC is a fork of [KIAUH](https://github.com/dw-0/kiauh) by
  [dw-0](https://github.com/dw-0) — all original credit goes to them and the
  KIAUH contributors.
* Thank you to [lixxbox](https://github.com/lixxbox) for the KIAUH logo.
* Thank you to [jwellman80](https://github.com/jwellman80) for
  klipper-toolchanger-easy, [Cartographer3D](https://github.com/Cartographer3D)
  for the Cartographer Klipper plugin, and [nic335](https://github.com/nic335)
  for Axiscope.
