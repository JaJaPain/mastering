import tkinter as tk
from ui.theme import Colors

class RangeSlider(tk.Canvas):
    """
    A custom dual-handle slider for selecting a range (Start/End).
    Used for setting loop markers.
    """
    def __init__(self, parent, height=30):
        super().__init__(parent, bg=Colors.BG_PANEL, height=height, highlightthickness=0)
        self.height = height
        self.start_val = 0.0 # 0.0 to 1.0
        self.end_val = 1.0   # 0.0 to 1.0
        self.on_change_callback = None
        
        self.active_handle = None # 'start' or 'end'
        
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self.bind("<Configure>", lambda e: self.draw())

    def set_range(self, start, end):
        self.start_val = max(0.0, min(1.0, start))
        self.end_val = max(0.0, min(1.0, end))
        # Ensure start is always before end
        if self.start_val > self.end_val:
            self.start_val, self.end_val = self.end_val, self.start_val
        self.draw()

    def on_click(self, event):
        w = self.winfo_width()
        if w < 40: return
        margin = 20
        pos = (event.x - margin) / (w - 2 * margin)
        pos = max(0.0, min(1.0, pos))
        
        # Determine which handle is closer
        dist_start = abs(pos - self.start_val)
        dist_end = abs(pos - self.end_val)
        
        if dist_start < dist_end:
            self.active_handle = 'start'
        else:
            self.active_handle = 'end'
            
        self.on_drag(event)

    def on_drag(self, event):
        w = self.winfo_width()
        if w < 40: return
        margin = 20
        pos = (event.x - margin) / (w - 2 * margin)
        pos = max(0.0, min(1.0, pos))
        
        if self.active_handle == 'start':
            self.start_val = min(pos, self.end_val - 0.01) # Keep tiny gap
        elif self.active_handle == 'end':
            self.end_val = max(pos, self.start_val + 0.01)
            
        self.draw()
        if self.on_change_callback:
            self.on_change_callback(self.start_val, self.end_val)

    def on_release(self, event):
        self.active_handle = None

    def draw(self):
        self.delete("all")
        self.update_idletasks() # Ensure width is accurate
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 40: return
        
        # Increased margin to ensure handles are never clipped or 'hidden' at the edges
        margin = 20
        track_w = w - 2 * margin
        
        # Draw background track
        self.create_rectangle(margin, h//2 - 2, w - margin, h//2 + 2, fill="#333333", outline="")
        
        # Draw active range highlight (Orange)
        x1 = margin + (self.start_val * track_w)
        x2 = margin + (self.end_val * track_w)
        self.create_rectangle(x1, h//2 - 3, x2, h//2 + 3, fill="#FF8C00", outline="")
        
        # Draw Handles (Vibrant Circular Handles for high visibility)
        r = 8
        # Start Handle
        self.create_oval(x1 - r, h//2 - r, x1 + r, h//2 + r, fill="#FFFFFF", outline="#FF8C00", width=2, tags="handle")
        # End Handle
        self.create_oval(x2 - r, h//2 - r, x2 + r, h//2 + r, fill="#FFFFFF", outline="#FF8C00", width=2, tags="handle")
