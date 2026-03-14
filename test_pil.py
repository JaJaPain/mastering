import sys
import os
try:
    from PIL import Image, ImageTk
    import tkinter as tk
    print("PIL and Tkinter imports successful")
    
    root = tk.Tk()
    img = Image.new('RGB', (100, 100), color='red')
    tk_img = ImageTk.PhotoImage(img)
    print("ImageTk conversion successful")
    root.destroy()
except Exception as e:
    print(f"FAILED: {e}")
    sys.exit(1)
