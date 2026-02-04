"""
Roblox Multi-Account Manager - Lite Edition (Account Management Only)
Simplified version without macro functionality
"""
import sys
import os

# Set path for bundled resources
if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))

from gui import RobloxBotGUI

def main():
    app = RobloxBotGUI()
    app.run()

if __name__ == "__main__":
    main()
