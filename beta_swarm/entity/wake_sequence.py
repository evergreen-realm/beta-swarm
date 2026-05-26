import tkinter as tk
import os
import threading
from PIL import Image, ImageTk

class WakeSequence:
    """Handles the 'Wake' animation overlay in a non-blocking thread."""
    
    def __init__(self, assets_dir: str):
        self.assets_dir = assets_dir

    def play(self):
        """Start the animation in a background thread to avoid blocking the tray icon."""
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        root = tk.Tk()
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", "black")
        root.config(bg="black")
        
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        
        current_x = screen_w - 100
        current_y = screen_h - 100
        
        label = tk.Label(root, bg="black")
        label.pack()

        # Preload 30 frames for faster animation
        frames = []
        for i in range(30):
            path = os.path.join(self.assets_dir, f"orb_wake_{i}.png")
            if os.path.exists(path):
                img = Image.open(path)
                scale = 1 + (i / 15)
                img = img.resize((int(64 * scale), int(64 * scale)), Image.Resampling.LANCZOS)
                frames.append(ImageTk.PhotoImage(img))

        def animate(idx):
            if idx < len(frames):
                nonlocal current_x, current_y
                target_x = screen_w // 2 - (frames[idx].width() // 2)
                target_y = screen_h // 2 - (frames[idx].height() // 2)
                
                current_x += (target_x - current_x) * 0.15
                current_y += (target_y - current_y) * 0.15
                
                root.geometry(f"+{int(current_x)}+{int(current_y)}")
                label.config(image=frames[idx])
                root.after(33, animate, idx + 1)
            else:
                root.after(500, root.destroy)

        root.geometry(f"250x250+{current_x}+{current_y}")
        animate(0)
        # Auto-kill fallback after 5 seconds to prevent ghost windows
        root.after(5000, root.destroy)
        root.mainloop()
