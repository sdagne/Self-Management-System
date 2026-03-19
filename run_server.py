"""
Start the Queue Management System server
"""
import sys
import io
import uvicorn
from config import settings
import os

# Fix Windows console encoding for Unicode output
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

port = int(os.environ.get("PORT", settings.port))

if __name__ == "__main__":
    print("=" * 60)
    print(f"[ET] {settings.app_name}")
    print(f"Version: {settings.version}")
    print("=" * 60)
    print(f"\n>> Starting server on http://{settings.host}:{port}")
    print(f"   API Documentation: http://localhost:{port}/docs")
    print(f"   Alternative Docs:  http://localhost:{port}/redoc")
    print("\nPress CTRL+C to stop the server\n")
    print("=" * 60)

    reload = os.environ.get("ENV", "production") == "development"
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=reload
    )

