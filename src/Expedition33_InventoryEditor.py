import os
import struct
import tkinter as tk
import io
from tkinter import ttk, filedialog, messagebox
import logging
from ue5_farchive_parser import FArchive, UE5PropertyParser

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class InventoryPatcher:
    """
    Decoupled class for patching inventory quantities in an Expedition 33 save file.
    Enforces keyType validation, bounds checking, payload preservation, and empty string handling.
    """
    def __init__(self, filePath):
        self.filePath = filePath
        # Valid item types allowed for patching
        self.validKeyTypes = ["Item", "Weapon", "Armor", "Material", "KeyItem", "Consumable"]

    def patchQuantity(self, keyType, keyName, newQuantityStr):
        """
        Patches the quantity for a given keyName of type keyType.
        Returns a tuple of (bool success, str message).
        """
        # 1. Empty string handling
        if not newQuantityStr or newQuantityStr.strip() == "":
            logging.warning(f"Empty quantity provided for {keyName}. Skipping.")
            return False, "Empty quantity provided."

        # 2. KeyType validation
        if keyType not in self.validKeyTypes:
            logging.error(f"Invalid keyType '{keyType}' provided.")
            return False, f"Invalid keyType: {keyType}"

        # Parse quantity
        try:
            newQuantity = int(newQuantityStr)
        except ValueError:
            logging.error(f"Quantity must be an integer. Received: {newQuantityStr}")
            return False, "Quantity must be a valid integer."

        # 3. Bounds checking (< 10000)
        if newQuantity < 0 or newQuantity >= 10000:
            logging.error(f"Quantity {newQuantity} is out of bounds. Must be >= 0 and < 10000.")
            return False, "Quantity out of bounds (< 10000)."

        # 4. Binary Patching using FArchive parser
        if not os.path.exists(self.filePath):
            return False, "File does not exist."

        try:
            with open(self.filePath, 'rb') as f:
                fileData = bytearray(f.read())
        except Exception as e:
            return False, f"Failed to read file: {e}"

        try:
            ar = FArchive(fileData)
            parser = UE5PropertyParser(ar)
            res = parser.readMapPayload(b"InventoryItems")
            if not res:
                return False, "InventoryItems map not found in save file."
                
            hdr, payloadBytes, originalData, headerStart, remainder = res
            
            payloadAr = FArchive(payloadBytes)
            newPayloadIo = io.BytesIO()
            count = hdr["count"]
            found = False
            parsedCount = 0
            
            if hdr.get("valType") and hdr["valType"] != b"IntProperty\x00":
                return False, f"Unexpected value type in InventoryItems: {hdr.get('valType')}"
            
            keyBytes = keyName if isinstance(keyName, bytes) else keyName.encode('utf-8')
            if not keyBytes.endswith(b'\x00'):
                keyBytes += b'\x00'

            for i in range(count):
                try:
                    keyStr = payloadAr.readFString()
                except EOFError:
                    break
                    
                try:
                    val = payloadAr.readInt32()
                except EOFError:
                    # Missing value for last key?
                    break
                
                if keyStr == keyBytes:
                    val += newQuantity
                    if val > 9999:
                        val = 9999
                    found = True
                    
                outAr = FArchive()
                outAr.writeFString(keyStr)
                outAr.writeInt32(val)
                newPayloadIo.write(outAr.getBuffer())
                parsedCount += 1
                
            if not found:
                return False, f"Key '{keyName}' not found in save file."
                
            hdr["count"] = parsedCount
                
            parser.rewriteMapPayload(hdr, newPayloadIo.getvalue(), originalData, headerStart, remainder)
            
            with open(self.filePath, 'wb') as f:
                f.write(parser.ar.getBuffer())
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return False, f"Failed to patch file due to error: {e}"

        logging.info(f"Successfully patched {keyName} to {newQuantity}.")
        return True, "Success"

class ScrollableFrame(ttk.Frame):
    """
    A custom scrollable frame component for Tkinter.
    """
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        
        self.canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollableFrame = ttk.Frame(self.canvas)
        
        self.scrollableFrame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )
        
        self.canvas.create_window((0, 0), window=self.scrollableFrame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

class InventoryEditorApp:
    """
    Main Tkinter application class for the Inventory Editor.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Expedition 33 Inventory Editor")
        self.root.geometry("600x400")
        
        self.filePath = None
        self.patcher = None
        self.itemEntries = [] # Store references to item entry widgets to harvest values later
        
        self.setupUI()

    def setupUI(self):
        # File Selection Frame
        fileFrame = ttk.Frame(self.root, padding=10)
        fileFrame.pack(fill="x")
        
        self.fileLabel = ttk.Label(fileFrame, text="No save file selected.")
        self.fileLabel.pack(side="left", padx=5)
        
        loadBtn = ttk.Button(fileFrame, text="Load Save", command=self.loadSaveFile)
        loadBtn.pack(side="right", padx=5)

        # Inventory Frame (Scrollable Container)
        self.inventoryContainer = ScrollableFrame(self.root)
        self.inventoryContainer.pack(fill="both", expand=True, padx=10, pady=10)

        # Bottom Frame
        bottomFrame = ttk.Frame(self.root, padding=10)
        bottomFrame.pack(fill="x")

        warningLbl = tk.Label(bottomFrame, text="* Experimental items. Ensure you have a backup of your save file before modifying quantities.", fg="red")
        warningLbl.pack(side="left", padx=5)
        
        patchBtn = ttk.Button(bottomFrame, text="Add Items", command=self.applyPatch)
        patchBtn.pack(side="right", padx=5)

    def loadSaveFile(self):
        selectedPath = filedialog.askopenfilename(
            title="Select Expedition 33 Save File",
            filetypes=[("Save Files", "*.sav"), ("All Files", "*.*")]
        )
        if selectedPath:
            self.filePath = selectedPath
            self.fileLabel.config(text=self.filePath)
            self.patcher = InventoryPatcher(self.filePath)
            self.populateInventory()

    def populateInventory(self):
        # Clear existing rows if any
        for widget in self.inventoryContainer.scrollableFrame.winfo_children():
            widget.destroy()
        
        self.itemEntries.clear()

        # CONSUMABLES dictionary replacing dummy items
        CONSUMABLES = {
            "Chroma Catalyst": b"UpgradeMaterial_Level1",
            "Polished Chroma Catalyst": b"UpgradeMaterial_Level2",
            "Resplendent Chroma Catalyst": b"UpgradeMaterial_Level3",
            "Grandiose Chroma Catalyst": b"UpgradeMaterial_Level4",
            "Perfect Chroma Catalyst": b"UpgradeMaterial_Level5",
            "Color of Lumina": b"Consumable_LuminaPoint",
            "Colour of Skill": b"Consumable_Respec",
            "Recoat": b"Consumable_Respec",
            "Chroma Elixir Shard": b"ChromaPack_Regular",
            "Energy Tint Shard": b"EnergyTint_Shard",
            "Healing Tint Shard": b"HealingTint_Shard",
            "Revive Tint Shard": b"ReviveTint_Shard",
            "Shape of Energy 1*": b"ShapeOfEnergy_1",
            "Shape of Energy 2*": b"ShapeOfEnergy_2",
            "Shape of Health 1*": b"ShapeOfHealth_1",
            "Shape of Health 2*": b"ShapeOfHealth_2",
            "Shape of Life 1*": b"ShapeOfLife_1",
            "Shape of Life 2*": b"ShapeOfLife_2"
        }

        itemsList = []
        for name, byteKey in CONSUMABLES.items():
            itemsList.append({"type": "Consumable", "name": name, "byteKey": byteKey})

        # Build rows in the scrollable canvas
        for i, item in enumerate(itemsList):
            rowFrame = ttk.Frame(self.inventoryContainer.scrollableFrame)
            rowFrame.pack(fill="x", pady=2)
            
            nameLbl = ttk.Label(rowFrame, text=item["name"], width=25)
            nameLbl.pack(side="left", padx=5)
            
            qtyVar = tk.StringVar()
            qtyEntry = ttk.Entry(rowFrame, textvariable=qtyVar, width=10)
            qtyEntry.pack(side="left", padx=5)
            
            self.itemEntries.append({
                "type": item["type"],
                "name": item["name"],
                "qtyVar": qtyVar,
                "byteKey": item["byteKey"]
            })

    def applyPatch(self):
        if not self.patcher:
            messagebox.showerror("Error", "Please load a save file first.")
            return

        successCount = 0
        errorMessages = []

        for itemData in self.itemEntries:
            qtyStr = itemData["qtyVar"].get()
            
            # 1. Empty string handling at UI layer (optional, but handled by Patcher too)
            if qtyStr.strip() == "":
                continue

            success, msg = self.patcher.patchQuantity(
                keyType=itemData["type"], 
                keyName=itemData.get("byteKey", itemData["name"]), 
                newQuantityStr=qtyStr
            )
            
            if success:
                successCount += 1
            else:
                if msg != "Empty quantity provided.":
                    errorMessages.append(f"{itemData['name']}: {msg}")

        # Feedback to the user
        if errorMessages:
            messagebox.showwarning("Patch Issues", "\n".join(errorMessages))
        elif successCount > 0:
            messagebox.showinfo("Success", f"Successfully patched {successCount} items!")
        else:
            messagebox.showinfo("Info", "No items were patched.")

if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryEditorApp(root)
    root.mainloop()
