import customtkinter as ctk
from PIL import Image, ImageTk
import os
import sys
import json
import pandas as pd
import subprocess
# Added openpyxl requirement for pandas excel export
try:
    import openpyxl
except ImportError:
    pass 
from tkinter import filedialog, messagebox

# --- 1. BUNDLING & PATH LOGIC ---
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        if getattr(sys, 'frozen', False):
            base_path = os.path.abspath(os.path.join(os.path.dirname(sys.executable), '..', 'Resources'))
        else:
            base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

sys.path.append(get_resource_path("."))
from Dash import show_dashboard as show_aptiv_dashboard
from Custdash import show_dashboard as show_customer_dashboard
from main4 import CustomerOwnedVDR, AptivInventory

# --- 2. CONFIGURATION PERSISTENCE ---
CONFIG_FILE = os.path.expanduser("~/.aptiv_config.txt")

def get_database_path():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            saved_path = f.read().strip()
            if os.path.exists(saved_path):
                return saved_path
    messagebox.showinfo("First Time Setup", "Please select the Database folder (OneDrive).")
    selected_path = filedialog.askdirectory(title="Select Database Location")
    if selected_path:
        with open(CONFIG_FILE, "w") as f:
            f.write(selected_path)
        return selected_path
    else:
        messagebox.showerror("Error", "A database path is required.")
        sys.exit()

DATABASE_PATH = get_database_path()
MOD2_BASE_PATH = os.path.join(DATABASE_PATH, "Customer Owned VDR")
MOD3_BASE_DIR = os.path.join(DATABASE_PATH, "Aptiv Inventory")
MOD3_DATA_FILE = os.path.join(MOD3_BASE_DIR, "inventory_data.json")
MASTER_DB_FILE = os.path.join(DATABASE_PATH, "master_items.json")

# --- 3. MASTER DB LOGIC ---
def get_master_instrument_types():
    defaults = ["CT1000", "CT600", "EP2000", "EP800", "EP2500", "RAD IO-temp", "RAD IO- ANA", "AT-48", "CAN HUB"]
    if os.path.exists(MASTER_DB_FILE):
        try:
            with open(MASTER_DB_FILE, "r") as f:
                custom_items = json.load(f)
                return sorted(list(set(defaults + custom_items)))
        except: return defaults
    return defaults

def go_home_logic(current_window):
    current_window.destroy()

class MasterItemManager(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Database Item Manager")
        self.geometry("400x500")
        self.attributes("-topmost", True)
        
        ctk.CTkLabel(self, text="Add New Item to Database", font=("Arial Bold", 16)).pack(pady=10)
        self.entry = ctk.CTkEntry(self, placeholder_text="Enter Item Name (e.g. LiDAR v2)", width=250)
        self.entry.pack(pady=5)
        
        ctk.CTkButton(self, text="Add to DB", fg_color="#218c53", command=self.add_item).pack(pady=10)
        
        self.listbox_frame = ctk.CTkScrollableFrame(self, width=350, height=250)
        self.listbox_frame.pack(pady=10, padx=10, fill="both", expand=True)
        self.refresh_list()

    def add_item(self):
        new_val = self.entry.get().strip()
        if not new_val: return
        current = []
        if os.path.exists(MASTER_DB_FILE):
            with open(MASTER_DB_FILE, "r") as f: current = json.load(f)
        if new_val not in current:
            current.append(new_val)
            with open(MASTER_DB_FILE, "w") as f: json.dump(current, f, indent=4)
            self.entry.delete(0, 'end')
            self.refresh_list()
            messagebox.showinfo("Success", f"'{new_val}' added to global database.")
        else:
            messagebox.showwarning("Warning", "Item already exists.")

    def delete_item(self, val):
        if messagebox.askyesno("Confirm", f"Remove '{val}' from database?"):
            with open(MASTER_DB_FILE, "r") as f: current = json.load(f)
            current.remove(val)
            with open(MASTER_DB_FILE, "w") as f: json.dump(current, f, indent=4)
            self.refresh_list()

    def refresh_list(self):
        for widget in self.listbox_frame.winfo_children(): widget.destroy()
        items = []
        if os.path.exists(MASTER_DB_FILE):
            with open(MASTER_DB_FILE, "r") as f: items = json.load(f)
        for item in items:
            row = ctk.CTkFrame(self.listbox_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=item).pack(side="left", padx=10)
            ctk.CTkButton(row, text="X", width=30, fg_color="#e74c3c", command=lambda v=item: self.delete_item(v)).pack(side="right")

# --- (ALL YOUR OTHER CODE REMAINS EXACTLY THE SAME, NO CHANGES) ---

# --- 6. MAIN LAUNCHER APP ---
ctk.set_appearance_mode("Dark")

class InventoryApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Aptiv Inventory Management System")
        self.geometry("1100x700") 
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.image_path = get_resource_path("Asset/Launchpage.jpg")
        self.bg_image_label = ctk.CTkLabel(self, text="")
        self.bg_image_label.grid(row=0, column=0, sticky="nsew")
        self.current_width, self.current_height = 0, 0
        self.setup_ui_buttons()
        self.bind("<Configure>", self.resizer)

    def resizer(self, event):
        if event.width == self.current_width and event.height == self.current_height: return
        self.current_width, self.current_height = event.width, event.height
        if os.path.exists(self.image_path):
            img = Image.open(self.image_path)
            img_w, img_h = img.size
            window_w, window_h = event.width, event.height
            img_aspect, window_aspect = img_w / img_h, window_w / window_h
            if window_aspect > img_aspect:
                new_width, new_height = window_w, int(window_w / img_aspect)
            else:
                new_height, new_width = window_h, int(window_h * img_aspect)
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            start_x, start_y = (new_width - window_w) // 2, (new_height - window_h) // 2
            final_img = resized_img.crop((start_x, start_y, start_x + window_w, start_y + window_h))
            self.bg_photo = ctk.CTkImage(final_img, size=(window_w, window_h))
            self.bg_image_label.configure(image=self.bg_photo)

    # ✅ UPDATED FUNCTION (ONLY CHANGE)
    def open_analytics_selector(self):
        selector = ctk.CTkToplevel(self)
        selector.title("Select Analytics")
        selector.geometry("400x250")
        selector.configure(fg_color="#1a1a1a")
        selector.attributes("-topmost", True)

        ctk.CTkLabel(selector, text="Choose Analytics Dashboard", font=("Arial Bold", 18)).pack(pady=20)

        pop_btn_style = {
            "width": 300,
            "height": 45,
            "font": ctk.CTkFont(size=14, weight="bold"),
            "fg_color": "#2D74BC",
            "hover_color": "#245D96"
        }

        def run_aptiv_dash():
            selector.destroy()
            show_aptiv_dashboard(self)

        def run_cust_dash():
            selector.destroy()
            show_customer_dashboard(self)

        ctk.CTkButton(selector, text="Aptiv Inventory Analytics", **pop_btn_style, command=run_aptiv_dash).pack(pady=10)
        ctk.CTkButton(selector, text="Customer Inventory Analytics", **pop_btn_style, command=run_cust_dash).pack(pady=10)

    def open_mod2(self): 
        CustomerOwnedVDR(self)

    def open_mod3(self):
        # TEAM MODE VERSION - Disable "Add Item to DB" button
        AptivInventory(self, team_mode=True)

    def setup_ui_buttons(self):
        btn_style = {"width": 320, "height": 55, "font": ctk.CTkFont(size=17, weight="bold"), "fg_color": "#2D74BC", "hover_color": "#245D96", "corner_radius": 10, "bg_color": "transparent"}
        self.btn1 = ctk.CTkButton(self, text="Show Analytics Dashboard", **btn_style, command=self.open_analytics_selector)
        self.btn1.place(relx=0.05, rely=0.35, anchor="nw")
        self.btn2 = ctk.CTkButton(self, text="Customer Owned Devices", **btn_style, command=self.open_mod2)
        self.btn2.place(relx=0.05, rely=0.46, anchor="nw")
        self.btn3 = ctk.CTkButton(self, text="Aptiv Inventory", **btn_style, command=self.open_mod3)
        self.btn3.place(relx=0.05, rely=0.57, anchor="nw")

if __name__ == "__main__":
    app = InventoryApp()
    app.mainloop()
