import tkinter as tk

class ToolTip:
    """
    Creates a hover tooltip for a given Tkinter widget.
    """
    def __init__(self, widget, text='Widget Information'):
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<Motion>", self.motion)
        self.id = None
        self.tw = None
        self.x = 0
        self.y = 0

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def motion(self, event):
        self.x = event.x
        self.y = event.y
        if self.tw:
            # Dynamically follow mouse offset
            x = self.widget.winfo_rootx() + self.x + 15
            y = self.widget.winfo_rooty() + self.y + 10
            self.tw.wm_geometry(f"+{x}+{y}")

    def schedule(self):
        self.unschedule()
        # Wait 400ms before showing
        self.id = self.widget.after(400, self.showtip)

    def unschedule(self):
        id = self.id
        self.id = None
        if id:
            self.widget.after_cancel(id)

    def showtip(self, event=None):
        x = self.widget.winfo_rootx() + self.x + 15
        y = self.widget.winfo_rooty() + self.y + 10
        
        self.tw = tk.Toplevel(self.widget)
        self.tw.wm_overrideredirect(True) # Remove window borders
        self.tw.wm_geometry(f"+{x}+{y}")
        
        # Style to match the dark theme closely
        label = tk.Label(self.tw, text=self.text, justify='left',
                         background="#2A2D2E", foreground="#E0E0E0", 
                         relief='solid', borderwidth=1,
                         font=("Segoe UI", 9, "normal"), padx=8, pady=4)
        label.pack(ipadx=1)
        
        self.tw.attributes("-alpha", 0.95)

    def hidetip(self):
        tw = self.tw
        self.tw = None
        if tw:
            tw.destroy()
