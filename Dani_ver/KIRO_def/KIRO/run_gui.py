#!/usr/bin/env python3
"""Launcher for DNI-IM GUI application"""

import sys
import os

# Add src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import and run main application
from main_gui import main

if __name__ == '__main__':
    main()
