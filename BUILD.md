# Build Instructions

The *Expedition 33 Inventory Editor* is written entirely in Python and uses the built-in `tkinter` library for its GUI. No external game-specific libraries or proprietary SDKs are required.

To compile the source code into a standalone executable (as distributed in our releases), we use **PyInstaller**.

## Prerequisites
1. **Python 3.10+**: Ensure Python is installed and added to your system PATH.
2. **PyInstaller**: Install PyInstaller via pip.
   ```bash
   pip install pyinstaller
   ```

## Build Steps
1. Clone or download this repository.
2. Open a command prompt or terminal.
3. Navigate to the root folder of this project (where this `BUILD.md` is located).
4. Run the following PyInstaller command:
   ```bash
   pyinstaller --onefile --windowed src/Expedition33_InventoryEditor.py
   ```
   *Note: `--onefile` packages everything into a single `.exe`, and `--windowed` prevents a console window from spawning behind the UI.*

5. Once the build process completes, you will find the final executable located inside the newly generated `dist/` directory.

## Source Code Overview
- `src/Expedition33_InventoryEditor.py`: The main application entry point, containing the Tkinter UI and the `InventoryPatcher` class.
- `src/ue5_farchive_parser.py`: A custom Unreal Engine 5 structural binary parser designed to safely read and edit `FPropertyTag` structures without corrupting trailing data.
