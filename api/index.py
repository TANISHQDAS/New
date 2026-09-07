import sys
from pathlib import Path

# Add parent directory to sys.path so modules can be imported by Vercel serverless function
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from main import app
