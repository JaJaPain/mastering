import ctypes
import os
from ui.controller import UIController

def minimize_console():
    """Minimizes the background Windows terminal on launch."""
    if os.name == 'nt':
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 6)

def main():
    print("Mastering Program Initializing...")
    minimize_console()
    controller = UIController()
    controller.run()

if __name__ == "__main__":
    main()
