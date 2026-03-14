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
        if w == 0: return
        pos = event.x / w
        
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
        if w == 0: return
        pos = max(0.0, min(1.0, event.x / w))
        
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
        w = self.winfo_width()
        h = self.winfo_height()
        if w < 10: return
        
        # Draw background track
        self.create_rectangle(0, h//2 - 2, w, h//2 + 2, fill="#333333", outline="")
        
        # Draw active range highlight (Orange)
        x1 = self.start_val * w
        x2 = self.end_val * w
        self.create_rectangle(x1, h//2 - 3, x2, h//2 + 3, fill="#FF8C00", outline="")
        
        # Draw handles
        handle_w = 8
        # Start Handle
        self.create_rectangle(x1 - handle_w/2, 2, x1 + handle_w/2, h - 2, fill="#FFFFFF", outline="#FF8C00")
        # End Handle
        self.create_rectangle(x2 - handle_w/2, 2, x2 + handle_w/2, h - 2, fill="#FFFFFF", outline="#FF8C00")
