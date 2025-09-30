"""
Redis Setup Helper for Windows
Downloads and sets up Redis easily without Docker
"""

import os
import subprocess
import sys
import time
import urllib.request
import zipfile
from pathlib import Path

def download_redis():
    """Download Redis for Windows"""
    
    print("=== Redis Setup for ContextSnap ===")
    print("Setting up Redis (super fast database for caching)...")
    
    # Create redis directory
    redis_dir = Path("redis")
    redis_dir.mkdir(exist_ok=True)
    
    redis_exe = redis_dir / "redis-server.exe"
    
    # Check if already downloaded
    if redis_exe.exists():
        print("✅ Redis already downloaded!")
        return redis_dir
    
    print("📥 Downloading Redis for Windows...")
    
    # Download Redis for Windows (unofficial but stable build)
    redis_url = "https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip"
    zip_file = redis_dir / "redis.zip"
    
    try:
        print("   Downloading from GitHub...")
        urllib.request.urlretrieve(redis_url, zip_file)
        
        print("   Extracting files...")
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(redis_dir)
        
        # Remove zip file
        zip_file.unlink()
        
        print("✅ Redis downloaded successfully!")
        return redis_dir
        
    except Exception as e:
        print(f"❌ Download failed: {e}")
        print("\nAlternative: Manual download")
        print("1. Go to: https://github.com/tporadowski/redis/releases")
        print("2. Download 'Redis-x64-5.0.14.1.zip'")
        print(f"3. Extract to: {redis_dir.absolute()}")
        return None

def start_redis(redis_dir):
    """Start Redis server"""
    
    redis_exe = redis_dir / "redis-server.exe"
    
    if not redis_exe.exists():
        print(f"❌ Redis executable not found at {redis_exe}")
        return None
    
    print("🚀 Starting Redis server...")
    
    try:
        # Start Redis server in background
        process = subprocess.Popen(
            [str(redis_exe)],
            cwd=str(redis_dir),
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        
        # Wait a moment for Redis to start
        time.sleep(3)
        
        # Test if Redis is running
        try:
            import redis
            client = redis.Redis(host='localhost', port=6379, db=0)
            client.ping()
            print("✅ Redis is running successfully!")
            print(f"   Process ID: {process.pid}")
            print("   Port: 6379")
            return process
        except:
            print("❌ Redis failed to start properly")
            return None
            
    except Exception as e:
        print(f"❌ Failed to start Redis: {e}")
        return None

def test_redis():
    """Test Redis connection"""
    
    print("\n🧪 Testing Redis connection...")
    
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        
        # Test basic operations
        client.set("test_key", "Hello ContextSnap!")
        value = client.get("test_key")
        
        if value == "Hello ContextSnap!":
            print("✅ Redis is working perfectly!")
            client.delete("test_key")
            return True
        else:
            print("❌ Redis test failed")
            return False
            
    except ImportError:
        print("⚠️  Redis Python package not installed")
        print("Installing redis package...")
        subprocess.run([sys.executable, "-m", "pip", "install", "redis"])
        return test_redis()
        
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False

def main():
    """Main setup function"""
    
    print("This will set up Redis for your ContextSnap definitions cache.")
    print("Redis is like a super-fast notebook that remembers your definitions!")
    print()
    
    # Download Redis
    redis_dir = download_redis()
    if not redis_dir:
        return
    
    # Start Redis
    process = start_redis(redis_dir)
    if not process:
        return
    
    # Test Redis
    if not test_redis():
        return
    
    print(f"\n{'='*50}")
    print("🎉 REDIS SETUP COMPLETE!")
    print(f"{'='*50}")
    print("✅ Redis is now running and ready for ContextSnap")
    print("✅ Your definitions will be cached for super-fast lookup")
    print("✅ You can now run: python start_system.py")
    print()
    print("📝 Important Notes:")
    print("- Redis will run in a separate window")
    print("- Keep that window open while using ContextSnap")
    print("- To stop Redis, close the Redis window")
    print("- Redis will remember your definitions between restarts")
    print()
    
    input("Press Enter to continue and start ContextSnap system...")

if __name__ == "__main__":
    main()
