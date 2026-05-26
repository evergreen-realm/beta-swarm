import tkinter as tk
from tkinter import ttk, messagebox
import os

class BetaSwarmWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("βeta Swarm v3.1")
        self.root.geometry("1000x700")
        self.root.configure(bg="#0d1117")
        
        self._setup_styles()
        self._create_header()
        self._create_sidebar()
        self._create_main_canvas()
        self._create_footer()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TFrame", background="#0d1117")
        style.configure("TLabel", background="#0d1117", foreground="#c9d1d9", font=("Arial", 10))
        style.configure("Header.TLabel", font=("Arial", 18, "bold"), foreground="#58a6ff")
        style.configure("Sidebar.TFrame", background="#161b22")
        style.configure("Summon.TButton", font=("Arial", 12, "bold"), foreground="#ffffff", background="#238636")

    def _create_header(self):
        header_frame = ttk.Frame(self.root)
        header_frame.pack(side="top", fill="x", padx=20, pady=10)
        
        logo_label = ttk.Label(header_frame, text="βeta Swarm", style="Header.TLabel")
        logo_label.pack(side="left")
        
        version_label = ttk.Label(header_frame, text="v3.1", foreground="#8b949e")
        version_label.pack(side="left", padx=10, pady=(5, 0))

    def _create_sidebar(self):
        sidebar = ttk.Frame(self.root, style="Sidebar.TFrame", width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        ttk.Label(sidebar, text="AGENT ROSTER", font=("Arial", 10, "bold"), foreground="#8b949e").pack(pady=10)
        
        categories = ["STAGE AGENTS", "REVIEW AGENTS", "BRAIN AGENTS", "GROWTH AGENTS"]
        for cat in categories:
            btn = tk.Button(sidebar, text=cat, bg="#161b22", fg="#c9d1d9", relief="flat", anchor="w", padx=10)
            btn.pack(fill="x", pady=2)

    def _create_main_canvas(self):
        self.canvas_frame = ttk.Frame(self.root)
        self.canvas_frame.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(self.canvas_frame, text="WORKFLOW PIPELINE", font=("Arial", 12, "bold")).pack(anchor="nw")
        
        self.canvas = tk.Canvas(self.canvas_frame, bg="#0d1117", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=10)
        
        # Drawing stages S1-S13
        for i in range(1, 14):
            x = 50 + (i-1)*60
            y = 100
            self.canvas.create_oval(x, y, x+40, y+40, fill="#1f6feb", outline="#58a6ff")
            self.canvas.create_text(x+20, y+20, text=f"S{i}", fill="#fff")

    def _create_footer(self):
        footer = ttk.Frame(self.root, height=50)
        footer.pack(side="bottom", fill="x", padx=20, pady=10)
        
        summon_btn = tk.Button(footer, text="SUMMON SWARM", bg="#238636", fg="#fff", font=("Arial", 12, "bold"), padx=20)
        summon_btn.pack(side="right")
        
        self.status_label = ttk.Label(footer, text="Status: IDLE", foreground="#8b949e")
        self.status_label.pack(side="left")

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = BetaSwarmWindow()
    app.run()
