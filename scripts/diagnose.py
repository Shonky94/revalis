"""
ContextSnap Diagnostic Tool
Checks what's working and what's not
"""

import requests
import sys
from pathlib import Path

def check_redis():
    """Check if Redis is running"""
    try:
        import redis
        client = redis.Redis(host='localhost', port=6379, db=0)
        client.ping()
        print("✅ Redis is running")
        return True
    except ImportError:
        print("❌ Redis Python package not installed")
        return False
    except Exception as e:
        print(f"❌ Redis not running: {e}")
        return False

def check_api_server():
    """Check if API server is running"""
    try:
        response = requests.get("http://localhost:5000/api/health", timeout=3)
        if response.status_code == 200:
            print("✅ API server is running")
            return True
        else:
            print(f"❌ API server error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API server not running: {e}")
        return False

def check_definitions():
    """Check if definitions are available"""
    try:
        from utils import load_json
        from config import DEFINITIONS_DIR
        
        # Check for definitions files
        definition_files = list(DEFINITIONS_DIR.glob("definitions_*.json"))
        if definition_files:
            latest_file = max(definition_files, key=lambda f: f.stat().st_mtime)
            data = load_json(latest_file)
            definitions = data.get("definitions", {})
            print(f"✅ Found {len(definitions)} definitions in {latest_file.name}")
            return True
        else:
            print("❌ No definition files found")
            return False
    except Exception as e:
        print(f"❌ Error checking definitions: {e}")
        return False

def test_api():
    """Test API with a sample word"""
    try:
        response = requests.get("http://localhost:5000/api/definition?word=algorithm", timeout=3)
        if response.status_code == 200:
            data = response.json()
            if data.get('definition'):
                print("✅ API working - sample definition found")
                return True
            else:
                print("⚠️  API working but no definition found")
                return False
        else:
            print(f"❌ API test failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ API test error: {e}")
        return False

def main():
    """Run all diagnostics"""
    print("=== ContextSnap Diagnostic ===")
    print("Checking system components...\n")
    
    # Check each component
    redis_ok = check_redis()
    api_ok = check_api_server()
    definitions_ok = check_definitions()
    
    if api_ok:
        api_test_ok = test_api()
    else:
        api_test_ok = False
    
    print(f"\n{'='*40}")
    print("DIAGNOSIS RESULTS:")
    print(f"{'='*40}")
    
    if redis_ok and api_ok and definitions_ok and api_test_ok:
        print("🎉 Everything looks good!")
        print("\nIf the extension still doesn't work:")
        print("1. Check Chrome Console (F12) for errors")
        print("2. Make sure you reloaded the extension")
        print("3. Try on a simple webpage first")
        
    else:
        print("🔧 Issues found:")
        if not redis_ok:
            print("- Start Redis: double-click redis-server.exe")
        if not definitions_ok:
            print("- Generate definitions: python definition_generator.py")
        if not api_ok:
            print("- Start API server: python start_system.py")
        if not api_test_ok:
            print("- API not responding correctly")

if __name__ == "__main__":
    main()
