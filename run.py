#!/usr/bin/env python3
"""
Eye Movement Assessment System - Launcher
Run this script to start the application.
"""

import sys
import os

# Add src directory to path
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

if __name__ == "__main__":
    from main_app import main
    main()
