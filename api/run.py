"""
Entry point for running the FastAPI dashboard server

Usage:
    python -m api.run
    
Or with uvicorn directly:
    uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""

import uvicorn
import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Run the FastAPI application with uvicorn"""
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )


if __name__ == "__main__":
    main()
