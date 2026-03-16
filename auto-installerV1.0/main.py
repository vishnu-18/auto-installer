"""Entry point for the Genius Auto Installer."""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Load .env if present (HF_API_TOKEN, HF_MODEL)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

from gui import App

if __name__ == "__main__":
    app = App()
    app.mainloop()
