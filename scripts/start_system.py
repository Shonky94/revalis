"""
ContextSnap System Launcher
Starts the Redis cache and API server for the Chrome extension
"""

import subprocess
import sys
import time
from pathlib import Path

def check_redis_running():
    """Check if Redis server is running"""
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        client.ping()
        return True
    except:
        return False

def start_redis():
    """Instructions to start Redis"""
    print("⚠️  Redis is not running!")
    print("\nTo start Redis:")
    print("1. Download Redis from: https://redis.io/docs/getting-started/")
    print("2. Or use Docker: docker run -d -p 6379:6379 redis")
    print("3. Or on Windows with WSL: sudo service redis-server start")
    print("\nOnce Redis is running, run this script again.")
    return False

def setup_cache():
    """Setup Redis cache with definitions"""
    try:
        from redis_cache import DefinitionCache
        
        print("🔄 Setting up Redis cache...")
        cache = DefinitionCache()
        
        # Load definitions into cache
        count = cache.load_definitions_to_cache()
        print(f"✅ Loaded {count} definitions into Redis cache")
        
        return True
    except Exception as e:
        print(f"❌ Failed to setup cache: {e}")
        return False

def start_api_server():
    """Start the Flask API server"""
    try:
        print("🚀 Starting ContextSnap API server...")
        print("📡 Server will be available at: http://localhost:5000")
        print("🔍 Test endpoint: http://localhost:5000/api/definition?word=algorithm")
        print("\nPress Ctrl+C to stop the server\n")
        
        # Run the API server
        subprocess.run([sys.executable, "api_server.py"], check=True)
        
    except KeyboardInterrupt:
        print("\n⏹️  Server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start API server: {e}")

def main():
    """Main launcher function"""
    print("=== ContextSnap System Launcher ===")
    print("🎯 Local LLM Definition System")
    print()
    
    # Check Redis
    if not check_redis_running():
        if not start_redis():
            return
    else:
        print("✅ Redis server is running")
    
    # Setup cache
    if not setup_cache():
        return
    
    # Start API server
    start_api_server()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        print("Please check the error details above.")
