import os
import sys

# Ensure backend directory is in sys.path for pytest discovery
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
