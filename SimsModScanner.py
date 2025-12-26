import os
import zipfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

from tkinter.scrolledtext import ScrolledText
import ttkbootstrap as tb
from ttkbootstrap import Style

class SimsModScanner:
    def __init__(self, root):
        self.root = root
        self.root.title("Sims 4 Mod Scanner")
        self.root.geometry("700x500")
        self.style = Style("flatly")
        self.mods_folder = None

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
        tb.Label(self.start_page, text="Sims 4 Mod Scanner", font=("Arial", 22, "bold")).pack(pady=40)

        tb.Button(self.start_page, text="Select Mods Folder", command=self.choose_folder, bootstyle="primary outline").pack(pady=10)
        self.folder_label = tb.Label(self.start_page, text="No folder selected", bootstyle="secondary")
        self.folder_label.pack(pady=5)

        tb.Button(self.start_page, text="Start Scan", command=self.start_scan_thread, bootstyle="success outline").pack(pady=20)

    #Scan page
    def create_scan_page(self):
        #self.progress = tb.Progressbar(self.scan_page, bootstyle="success-striped", mode="indeterminate", length=500)
        #self.progress.pack(pady=10)
        tb.Label(self.scan_page, text="Scan Results", font=("Arial", 16, "bold")).pack(pady=10)

        self.output = ScrolledText(self.scan_page, height=20, font=("Consolas", 11))
        self.output.pack(fill="both", expand=True, pady=10)
        self.output.bind("<Key>", lambda e: "break")  # make read-only

        tb.Button(self.scan_page, text="Back", command=lambda: self.show_frame(self.start_page), bootstyle="secondary").pack(pady=10)

    #Folder selection
    def choose_folder(self):
        path = filedialog.askdirectory(title="Select Sims 4 Mods Folder")
        if path:
            self.mods_folder = path
            self.folder_label.config(text=path)

    #Start scan
    def start_scan_thread(self):
        if not self.mods_folder:
            messagebox.showerror("Error", "Please select a folder first.")
            return
        threading.Thread(target=self.scan_mods, daemon=True).start()

    #Scan mods
    def scan_mods(self):
        self.show_frame(self.scan_page)
        #self.progress.start()
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, "Scanning...\n\n")

        broken_files = 0
        total_files = 0
        buffer = []

        for root_dir, _, files in os.walk(self.mods_folder):
            for f in files:
                total_files += 1
                file_path = os.path.join(root_dir, f)
                try:
                    size = os.path.getsize(file_path)
                except Exception:
                    continue

                #Zero byte files (empty?)
                if size == 0:
                    buffer.append(f"[BROKEN] {f} (0 bytes)")
                    broken_files += 1

                #Scan .ts4script files (mods)
                elif f.lower().endswith(".ts4script") and not self.check_zip(file_path):
                    buffer.append(f"[CORRUPT SCRIPT] {f}")
                    broken_files += 1

                #Scan .package files (cc)
                elif f.lower().endswith(".package") and not self.check_package_advanced(file_path):
                    buffer.append(f"[CORRUPT PACKAGE] {f}")
                    broken_files += 1

                #Detect suspiciously large files (over 500MB)
                elif size > 500 * 1024 * 1024:
                    buffer.append(f"[SUSPICIOUS] {f} (Very large)")

                #Batch insert every 50 lines
                if len(buffer) >= 50:
                    self.output.insert(tk.END, "\n".join(buffer) + "\n")
                    self.output.see(tk.END)
                    buffer.clear()

        #Insert remaining files
        if buffer:
            self.output.insert(tk.END, "\n".join(buffer) + "\n")
            self.output.see(tk.END)

        self.output.insert(tk.END, f"\nScan Complete\n")
        self.output.insert(tk.END, f"Total Files: {total_files}\n")
        self.output.insert(tk.END, f"Broken Files: {broken_files}\n")

        #self.progress.stop()

    #File checks
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


#Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = SimsModScanner(root)
    root.mainloop()
