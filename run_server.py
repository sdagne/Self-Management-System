"""
Start the Queue Management System server
"""
import uvicorn
from config import settings
import os

port = int(os.environ.get("PORT", settings.port))

if __name__ == "__main__":
    print("=" * 60)
    print(f"🇪🇹 {settings.app_name}")
    print(f"Version: {settings.version}")
    print("=" * 60)
    print(f"\n🚀 Starting server on http://{settings.host}:{port}")
    print(f"📖 API Documentation: http://localhost:{port}/docs")
    print(f"📊 Alternative Docs: http://localhost:{port}/redoc")
    print("\nPress CTRL+C to stop the server\n")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True
    )

