#!/usr/bin/env python3
"""
PyTerminal Web Launcher

Simple launcher script for the PyTerminal Web application.
"""

import os
import sys
import webbrowser
import time
from app import app

def main():
    """Launch the PyTerminal Web application."""
    print("=" * 60)
    print("            PyTerminal Web - AI-Powered Terminal")
    print("                designed by Abhinav Singh")
    print("=" * 60)
    print()
    
    # Check if OpenAI API key is set
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  Warning: OPENAI_API_KEY not set. AI features will be disabled.")
        print("   Set your API key: set OPENAI_API_KEY=your_key_here")
        print()
    
    print("🚀 Starting PyTerminal Web...")
    print("📱 Opening browser in 3 seconds...")
    print("🌐 URL: http://localhost:5000")
    print()
    print("Press Ctrl+C to stop the server")
    print("-" * 60)
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(3)
        webbrowser.open('http://localhost:5000')
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    # Start Flask app
    try:
        app.run(debug=False, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n\n👋 PyTerminal Web stopped. Goodbye!")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
