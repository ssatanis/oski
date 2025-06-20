#!/usr/bin/env python3

import sys
import os

# Add current directory to path
sys.path.append('.')

# Import the backend app
from backend import app

if __name__ == "__main__":
    print("🚀 Starting stable Rubricon backend...")
    print("📍 Server will run on http://localhost:5002")
    print("🔧 Azure OpenAI configured and ready")
    print("📋 Endpoints available:")
    print("   GET  /health - Health check")
    print("   POST /upload - Upload and process files")
    print("   POST /download - Download YAML files")
    print("=" * 50)
    print("✅ Server ready! Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Run the server without debug mode for stability
        app.run(
            host='127.0.0.1',
            port=5002,
            debug=False,
            use_reloader=False
        )
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Server error: {e}")
        sys.exit(1) 