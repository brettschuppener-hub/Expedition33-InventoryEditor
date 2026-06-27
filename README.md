# Expedition 33 - Inventory Editor (v3.0.0)

Welcome to the **Expedition 33 Inventory Editor**! This tool allows you to safely add specific consumable items, upgrade materials, and boss drops to your existing save game without risking binary corruption.

---

## ⚠️ CRITICAL: Backup Your Save!
Before you make *any* changes, you **must** back up your original save file. If you ever want to revert your changes, you can simply swap your original file back in.

1. Press `Win + R` on your keyboard to open the Run dialog box.
2. Type `%LOCALAPPDATA%\Sandfall\Saved\SaveGames\######` and press **Enter**.
   *(Note: This is the standard Unreal Engine 5 save location. If you installed the game differently, look for your AppData\Local folder!)*
3. Look for your save files. They will end in `.sav` (for example, `EXPEDITION_0.sav`).
4. **Right-click** your save file, select **Copy**, and then paste it somewhere safe (like your Desktop or a new folder called "Expedition33_Backups").

---

## How to Use the Editor

1. Double-click `Expedition33_SaveEditor_v3.0.0.exe` to launch the application.
2. Click the **Load Save** button at the top right.
3. Navigate to your save folder (`%LOCALAPPDATA%\Sandfall\Saved\SaveGames\\######`) and select your `.sav` file.
4. You will see a list of items appear. In the text box next to an item, type the number of items you want to **ADD** to your current stash. 
   - *Example: If you currently have 5 Chroma Catalysts in-game and you type `10` in the box, you will end up with 15.*
5. Once you've entered your numbers, click **Add Items** at the bottom right.
6. A success message will appear. Close the editor, launch the game, and enjoy your new gear!

---

## Experimental Items (*)
Items marked with an asterisk `*` (such as "Shape of Energy") are progression-locked items that usually only drop from specific boss fights in the vanilla game. 

While this editor can successfully add these items to your inventory, we highly recommend making a secure backup before altering them, just in case the game's internal quest logic checks your boss-drop limits!

---

## Troubleshooting & FAQ

- **Max Limit:** The tool artificially caps your resulting item quantities at `9,999`. We do this to prevent the game engine from crashing due to number overflow bounds.
- **Can I remove items?** Currently, this tool is designed to incrementally add items. 
- **Is this safe?** Yes! Version 3.0.0 features a completely custom Unreal Engine 5 structural parser that safely reconstructs the binary map elements of your save file byte-for-byte, meaning it will never accidentally corrupt your other variables (like Weapons & Pictos levels, Quest Items, or playtime).
