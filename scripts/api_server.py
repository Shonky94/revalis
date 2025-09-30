"""
ContextSnap API Server
Flask server to provide definitions to the Chrome extension with fuzzy matching
"""

import json
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

try:
    from redis_cache import DefinitionCache
except ImportError:
    print("Redis not available. Install with: pip install redis")
    DefinitionCache = None

app = Flask(__name__)
CORS(app)  # Allow requests from Chrome extension

# Global cache instance
cache = None

def init_cache():
    """Initialize the Redis cache"""
    global cache
    try:
        if DefinitionCache:
            cache = DefinitionCache()
            # Load definitions if not already loaded
            stats = cache.get_cache_stats()
            if stats['total_definitions'] == 0:
                cache.load_definitions_to_cache()
            print(f"✓ Cache initialized with {stats['total_definitions']} definitions")
        else:
            print("⚠️  Redis cache not available - using fallback mode")
    except Exception as e:
        print(f"⚠️  Redis cache failed to initialize: {e}")
        cache = None

@app.route('/api/definition', methods=['GET', 'POST'])
def get_definition():
    """Get definition for a word with fuzzy matching"""
    
    start_time = time.time()
    
    # Get word from query parameter or JSON body
    if request.method == 'GET':
        word = request.args.get('word', '').strip()
    else:
        data = request.get_json() or {}
        word = data.get('word', '').strip()
    
    if not word:
        return jsonify({
            "error": "No word provided",
            "usage": "GET /api/definition?word=example OR POST with {'word': 'example'}"
        }), 400
    
    try:
        if cache:
            # Use Redis cache with fuzzy matching
            result = cache.search_definition(word)
            return jsonify(result)
        else:
            # Fallback: direct file lookup (no fuzzy matching)
            return fallback_definition_lookup(word, start_time)
            
    except Exception as e:
        return jsonify({
            "query": word,
            "error": f"Server error: {str(e)}",
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }), 500

def fallback_definition_lookup(word: str, start_time: float) -> dict:
    """Fallback definition lookup when Redis is not available"""
    
    try:
        from utils import load_json
        from config import DEFINITIONS_DIR
        
        # Find the most recent definitions file
        definition_files = list(DEFINITIONS_DIR.glob("definitions_*.json"))
        if not definition_files:
            return jsonify({
                "query": word,
                "error": "No definitions available",
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }), 404
        
        latest_file = max(definition_files, key=lambda f: f.stat().st_mtime)
        data = load_json(latest_file)
        definitions = data.get("definitions", {})
        
        # Try exact match
        if word.lower() in [w.lower() for w in definitions.keys()]:
            # Find the exact match (case-insensitive)
            for original_word, definition in definitions.items():
                if original_word.lower() == word.lower():
                    return jsonify({
                        "query": word,
                        "match_type": "exact",
                        "definition": definition,
                        "original_word": original_word,
                        "similarity": 1.0,
                        "response_time_ms": round((time.time() - start_time) * 1000, 2),
                        "note": "Fallback mode - fuzzy matching not available"
                    })
        
        # No exact match found
        return jsonify({
            "query": word,
            "match_type": "none",
            "error": f"No definition found for '{word}'",
            "response_time_ms": round((time.time() - start_time) * 1000, 2),
            "note": "Fallback mode - fuzzy matching not available"
        }), 404
        
    except Exception as e:
        return jsonify({
            "query": word,
            "error": f"Fallback lookup failed: {str(e)}",
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    
    status = {
        "status": "healthy",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "redis_available": cache is not None
    }
    
    if cache:
        try:
            stats = cache.get_cache_stats()
            status["cache_stats"] = {
                "total_definitions": stats["total_definitions"],
                "source_file": stats["cache_metadata"].get("source_file", "unknown")
            }
        except Exception as e:
            status["cache_error"] = str(e)
    
    return jsonify(status)

@app.route('/api/search', methods=['GET', 'POST'])
def search_definitions():
    """Search for multiple words or get suggestions"""
    
    start_time = time.time()
    
    # Get search terms
    if request.method == 'GET':
        query = request.args.get('q', '').strip()
        limit = int(request.args.get('limit', 10))
    else:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        limit = int(data.get('limit', 10))
    
    if not query:
        return jsonify({
            "error": "No search query provided",
            "usage": "GET /api/search?q=search_term&limit=5"
        }), 400
    
    try:
        if cache:
            # Split query into words and search each
            words = [w.strip() for w in query.split() if w.strip()]
            results = []
            
            for word in words[:limit]:  # Limit number of words to search
                result = cache.search_definition(word)
                if result['match_type'] != 'none':
                    results.append(result)
            
            return jsonify({
                "query": query,
                "results": results,
                "total_found": len(results),
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            })
        else:
            return jsonify({
                "query": query,
                "error": "Search not available in fallback mode",
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }), 503
            
    except Exception as e:
        return jsonify({
            "query": query,
            "error": f"Search error: {str(e)}",
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }), 500

@app.route('/', methods=['GET'])
def index():
    """API documentation"""
    
    return jsonify({
        "name": "ContextSnap Definition API",
        "version": "1.0",
        "endpoints": {
            "GET /api/definition?word=example": "Get definition for a word",
            "POST /api/definition": "Get definition (send JSON: {'word': 'example'})",
            "GET /api/search?q=query&limit=5": "Search multiple words",
            "GET /api/health": "Health check and stats"
        },
        "features": [
            "Exact word matching",
            "Fuzzy matching with similarity scores",
            "Redis caching for performance", 
            "Alternative suggestions",
            "Response time metrics"
        ]
    })

if __name__ == "__main__":
    print("=== ContextSnap API Server ===")
    
    # Initialize cache
    init_cache()
    
    # Start server
    port = 5000
    print(f"🚀 Starting server on http://localhost:{port}")
    print(f"📚 API Documentation: http://localhost:{port}")
    print(f"🔍 Test endpoint: http://localhost:{port}/api/definition?word=algorithm")
    
    app.run(host="0.0.0.0", port=port, debug=False)
