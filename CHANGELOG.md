# Changelog

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
