"""
Quick test script for the ContextSnap API server
Tests definition lookup with fuzzy matching
"""

import requests
import time

def test_api():
    """Test the ContextSnap API endpoints"""
    
    base_url = "http://localhost:5000"
    
    print("=== ContextSnap API Test ===")
    print(f"Testing server at: {base_url}")
    
    # Test 1: Health check
    print("\n1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Health check passed")
            health_data = response.json()
            if health_data.get("redis_available"):
                print(f"✅ Redis cache available with {health_data.get('cache_stats', {}).get('total_definitions', 0)} definitions")
            else:
                print("⚠️  Redis cache not available - using fallback mode")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API server: {e}")
        print("Make sure the server is running with: python start_system.py")
        return False
    
    # Test 2: Exact match
    print("\n2. Testing exact match...")
    test_word = "algorithm"
    try:
        response = requests.get(f"{base_url}/api/definition?word={test_word}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found definition for '{test_word}'")
            print(f"   Match type: {data.get('match_type')}")
            print(f"   Definition: {data.get('definition', 'N/A')[:100]}...")
            print(f"   Response time: {data.get('response_time_ms')}ms")
        else:
            print(f"❌ Failed to get definition: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing exact match: {e}")
    
    # Test 3: Fuzzy match
    print("\n3. Testing fuzzy matching...")
    test_word = "machien"  # Typo for "machine"
    try:
        response = requests.get(f"{base_url}/api/definition?word={test_word}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('match_type') == 'fuzzy':
                print(f"✅ Found fuzzy match for '{test_word}'")
                print(f"   Matched word: {data.get('original_word')}")
                print(f"   Similarity: {data.get('similarity')*100:.1f}%")
                print(f"   Definition: {data.get('definition', 'N/A')[:100]}...")
                
                alternatives = data.get('alternative_matches', [])
                if alternatives:
                    alt_strings = [f"{alt['word']} ({alt['similarity']*100:.1f}%)" for alt in alternatives]
                    print(f"   Alternatives: {', '.join(alt_strings)}")
            else:
                print(f"⚠️  Expected fuzzy match but got: {data.get('match_type')}")
        else:
            print(f"❌ Failed to get fuzzy definition: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing fuzzy match: {e}")
    
    # Test 4: No match
    print("\n4. Testing no match...")
    test_word = "xyz123nonexistent"
    try:
        response = requests.get(f"{base_url}/api/definition?word={test_word}", timeout=5)
        data = response.json()
        if data.get('match_type') == 'none':
            print(f"✅ Correctly returned no match for '{test_word}'")
        else:
            print(f"⚠️  Expected no match but got: {data.get('match_type')}")
    except Exception as e:
        print(f"❌ Error testing no match: {e}")
    
    print(f"\n{'='*40}")
    print("✅ API testing complete!")
    print("You can now use the Chrome extension to select text and get definitions.")
    
    return True

if __name__ == "__main__":
    test_api()
