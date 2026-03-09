# Main Application Entry Point
from ui.controller import UIController

def main():
    print("Mastering Program Initializing...")
    controller = UIController()
    controller.run()

if __name__ == "__main__":
    main()
