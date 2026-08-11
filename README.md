# MGS Light Manager for FS25

MGS Light Manager for FS25 is a Blender add-on created for Farming Simulator 25 modders. It provides quick UV positioning for the FS25 vehicle light texture layout, making it easier to assign common vehicle light types without manually moving UV islands between tiles.

## Download

Download the latest stable version from the [GitHub Releases](https://github.com/MyGameSteamOfficial/MGS-Light-Manager-FS25/releases/latest).

For normal installation, download `MGS_Light_Manager_FS25.zip` from the release **Assets**. Do not use GitHub's automatically generated source-code archives.

## Features

- Predefined FS25 light positions:
  - Default Light
  - Default Light & High Beam
  - High Beam
  - Bottom Light
  - Top Light
  - DRL
  - Turn Light Left
  - Turn Light Right
  - Back Light
  - Brake Light
  - Back & Brake Light
  - Reverse Light
  - Work Light Front
  - Work Light Back
  - Work Light Additional
  - Work Light Additional 2
- One-click UV positioning for supported FS25 light types.
- Smart preset behavior:
  - If UVs are selected, only the selected UVs are moved.
  - If no UVs are selected, the complete active UV map is moved.
- UV arrow controls for moving selected UVs one tile up, down, left, or right.
- Blender 5.x compatible UV-selection handling.
- Backward-compatible support for older Blender versions.

## Compatibility

- Blender 3.0 or newer.
- Includes compatibility handling for Blender 5.x.
- Designed for Farming Simulator 25 modding workflows.

## Installation

> **Important:** Download the latest release from the **Releases** section of this repository. Do not download the repository source code (`Source code.zip`) unless you intend to modify or develop the add-on.

1. Go to the latest GitHub release.
2. Under **Assets**, download `MGS_Light_Manager_FS25.zip`.
3. Do **not** extract the downloaded ZIP.
4. Open Blender.
5. Go to **Edit > Preferences > Add-ons**.
6. Click **Install...** and select `MGS_Light_Manager_FS25.zip`.
7. Enable **MGS Light Manager for FS25**.
8. Open the **UV Editor**.
9. Press **N** if the sidebar is hidden.
10. Open the **MGS** tab.


## Usage

### Predefined light buttons

1. Select a mesh and enter **Edit Mode**.
2. Open the **UV Editor**.
3. Open the **MGS** sidebar tab.
4. Select the UVs you want to modify.
5. Click the required light type.

If UVs are selected, only those UVs are moved to the selected FS25 light tile.

If no UVs are selected, the complete active UV map is moved instead.

### UV movement arrows

The arrow controls move the currently selected UVs by exactly one UV tile:

- Up: `+1 V`
- Down: `-1 V`
- Left: `-1 U`
- Right: `+1 U`

The arrow controls require one or more UVs to be selected.

## Version 1.1.0

- Added Blender 5.x compatibility.
- Added support for Blender 5.x UV selection API changes.
- Preserved compatibility with older Blender versions.
- Predefined light buttons now operate on selected UVs when a selection exists.
- If no UV selection exists, predefined light buttons continue to move the complete UV map.
- Improved UV movement reliability and error handling.
- Updated the add-on location to the UV Editor sidebar under the **MGS** tab.

## License

MGS Light Manager for FS25 is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.

See the included `LICENSE` file for the complete license text.

## Support

For questions, bug reports, or suggestions:

**admin@mygamesteam.com**

## Author

Developed by **MyGameSteam** for the Farming Simulator modding community.
