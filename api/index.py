import os
import sys

# Add root directory to sys.path to ensure Vercel can resolve local imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from attendance_app import create_app

app = create_app()
