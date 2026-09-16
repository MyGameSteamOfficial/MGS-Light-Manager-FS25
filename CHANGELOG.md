# Changelog

## Version 1.1.2

### Added
- Added support for using selected geometry in the 3D View as the UV movement target.
- Added multi-part 3D selection support for light-type presets and directional UV movement.
- Added automatic selection-source handling between the UV Editor and 3D View.

### Fixed
- Fixed light-type presets applying one shared translation when selected light parts were located in different UV tiles.
- Light-type presets now move selected UVs into the requested FS25 light tile while preserving each UV's local position inside the tile.
- Directional arrow controls and light-type presets now use the same selection-targeting system.

### Improved
- Improved multi-object Edit Mode handling.
- Improved workflow when switching between direct UV selection and 3D mesh selection.
- Preserved Blender 3.x, Blender 4.x, and Blender 5.x compatibility handling.

### Known Limitation
- When all UVs remain selected in the UV Editor and the user then switches to a new 3D View selection, the previous UV selection may remain authoritative in some selection sequences. If this occurs, deselect the UV selection before using the new 3D selection.
- Selection synchronization between the UV Editor and 3D View may be improved in a future update.

## Version 1.1.1

### Fixed
- Fixed UV arrow controls only moving UVs from the active mesh when multiple mesh objects were being edited.
- Added proper multi-object Edit Mode support for UV movement.
- UV arrow controls now move selected UVs across all mesh objects currently in Edit Mode.
- Selecting all UVs in the UV Editor now correctly moves the complete selection across multiple objects.
- Selecting individual UVs or UV islands continues to move only the intended selection.
- Improved UV selection handling across supported Blender versions.

### Improved
- Updated UV movement logic to handle each edited mesh independently while preserving the complete UV selection.
- Improved compatibility between Blender 3.x, Blender 4.x, and Blender 5.x UV selection behavior.
- Light-type preset movement now supports UV selections spanning multiple mesh objects.

## 1.1.0

- Added Blender 5.x compatibility.
- Added compatibility handling for the Blender 5.x UV selection API.
- Fixed UV arrow controls on Blender 5.x.
- Added smart preset behavior for selected UVs.
- Preserved full-UV movement when no UV selection exists.
- Preserved compatibility with older Blender versions.
- Improved error handling for Edit Mode, mesh, UV map, and selection requirements.
- Moved the add-on interface to the UV Editor sidebar under the **MGS** tab.

## 1.0.0

- Initial release of MGS Light Manager for FS25.
- Added predefined FS25 vehicle light UV positions.
- Added one-click UV positioning.
- Added directional UV movement controls.
