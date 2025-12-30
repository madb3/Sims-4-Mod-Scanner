import os
import zipfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from tkinter.scrolledtext import ScrolledText
import ttkbootstrap as tb
from ttkbootstrap import Style
import hashlib

class SimsModScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("Sims 4 Mod Scanner")
        self.root.geometry("700x500")
        self.style = Style("vapor")
        self.mods_folder = None
        self.cancel_scan = False

        #Container for pages
        self.container = tb.Frame(root)
        self.container.pack(fill="both", expand=True)

        self.start_page = tb.Frame(self.container)
        self.scan_page = tb.Frame(self.container)

        for frame in (self.start_page, self.scan_page):
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.create_start_page()
        self.create_scan_page()

        self.show_frame(self.start_page)

    #Page Switching
    def show_frame(self, frame):
        frame.lift()

    #Start page
    def create_start_page(self):
        tb.Label(self.start_page,
                text="Sims 4 Mod Scanner",
                foreground="white",
                font=("Arial", 22, "bold")).pack(pady=40)

        tb.Button(self.start_page, text="Select Mods Folder",
                command=self.choose_folder,
                bootstyle="primary").pack(pady=10)
        
        self.folder_label = tb.Label(self.start_page,
                                    text="No folder selected",
                                    bootstyle="secondary")
        self.folder_label.pack(pady=5)

        tb.Button(self.start_page,
                text="Start Scan",
                command=self.start_scan_thread,
                bootstyle="success").pack(pady=20)

    #Scan page
    def create_scan_page(self):
        tb.Label(self.scan_page,
                text="Scan Results",
                font=("Arial", 16, "bold"),
                foreground="white").pack(pady=10)

        #Progress bar
        self.progress = tb.Progressbar(
            self.scan_page,
            bootstyle="success-striped",
            mode="determinate",
            length=500
        )
        self.progress.pack(pady=10)

        #Status text
        self.status_label = tb.Label(self.scan_page, text="Waiting to start...")
        self.status_label.pack(pady=10)

        #Cancel scan button
        self.cancel_button = tb.Button(self.scan_page, text="Cancel Scan", command=self.cancel_scan_function, bootstyle="danger")
        self.cancel_button.pack(pady=10)

        #Output text box
        self.output = ScrolledText(self.scan_page, height=20, font=("Consolas", 11))
        self.output.pack(fill="both", expand=True, pady=10)
        self.output.bind("<Key>", lambda e: "break")

        #Back button
        tb.Button(self.scan_page, text="Back", command=lambda: self.show_frame(self.start_page), bootstyle="secondary").pack(pady=10)

    #Folder selection
    def choose_folder(self):
        path = filedialog.askdirectory(title="Select Sims 4 Mods Folder")
        if path:
            self.mods_folder = path
            self.folder_label.config(text=path)

    #Start scan
    def start_scan_thread(self):
        self.cancel_scan = False
        if not self.mods_folder:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        threading.Thread(target=self.scan_mods, daemon=True).start()

    def cancel_scan_function(self):
        self.cancel_scan = True
        self.status_label.config(text="Scan cancelled!")

    #Scan mods
    def scan_mods(self):
        self.show_frame(self.scan_page)
        self.output.delete("1.0", tk.END)

        total_files = 0 #Total number of files in mod folder
        for _, _, files in os.walk(self.mods_folder):
            total_files += len(files)
        
        self.progress.configure(maximum=total_files, value=0)

        #Scan variables
        broken_files = 0 #Total number of broken files
        scanned = 0 #Number of files scanned
        duplicates = 0 #Number of duplicate files
        buffer = [] #Buffer for output
        hashes_seen = {} #Dictionary of hashes

        for root_dir, _, files in os.walk(self.mods_folder):
            for f in files:
                if self.cancel_scan:
                    self.output.insert(tk.END, "Scan cancelled\n")
                    self.root.update_idletasks()
                    return
                scanned += 1
                file_path = os.path.join(root_dir, f)

                #Update progress
                self.status_label.config(foreground="white",text=f"Scanning... {scanned} / {total_files}")
                self.progress.configure(value=scanned)
                self.root.update_idletasks()

                try:
                    size = os.path.getsize(file_path)
                except Exception:
                    continue

                #Compute hash
                file_hash = self.hash_file(file_path)

                #Detect duplicates
                if file_hash in hashes_seen:
                    buffer.append(f"[DUPLICATE] {f}\n")
                    duplicates += 1
                else:
                    hashes_seen[file_hash] = f

                #Zero byte files (possibly empty?)
                if size == 0:
                    buffer.append(f"[BROKEN] {f} (0 bytes)\n")
                    broken_files += 1

                #Scan .ts4script files (mods)
                elif f.lower().endswith(".ts4script") and not self.check_zip(file_path):
                    buffer.append(f"[CORRUPT SCRIPT] {f}")
                    broken_files += 1

                #Scan .package files (cc)
                elif f.lower().endswith(".package") and not self.check_package_advanced(file_path):
                    buffer.append(f"[CORRUPT PACKAGE] {f}\n")
                    broken_files += 1

                #Detect suspiciously large files (over 500MB)
                elif size > 500 * 1024 * 1024:
                    buffer.append(f"[SUSPICIOUS] {f} (Very large)\n")

                #Batch insert every 50 lines to avoid lag or crashes
                if len(buffer) >= 50:
                    self.output.insert(tk.END, "\n".join(buffer) + "\n")
                    self.output.see(tk.END)
                    buffer.clear()
        
        summary = (
            f"Scan Complete\n"
            f"Total Files: {total_files}\n"
            f"Broken Files: {broken_files}\n"
            f"Duplicate Files: {duplicates}\n\n"
        )

        self.output.insert("1.0", summary)

        #Insert remaining files
        if buffer:
            self.output.insert(tk.END, "\n".join(buffer) + "\n")
            self.output.see(tk.END)

        self.status_label.config(text="Scan Complete!")

    #Check different types of files (zip files, package files, scripts)
    def check_zip(self, file_path):
        try:
            with zipfile.ZipFile(file_path, "r") as z:
                return z.testzip() is None
        except:
            return False

    def check_package_advanced(self, path):
        try:
            with open(path, "rb") as f:
                header = f.read(16)
                if header[0:4] != b"DBPF":
                    return False
            return True
        except:
            return False
        
    #Hash files using md5
    def hash_file(self, file_path):
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except:
            return None


#Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = SimsModScanner(root)
    root.mainloop()
