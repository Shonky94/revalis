"""
Redis Cache Manager for ContextSnap Definitions
Handles caching, fuzzy matching, and serving definitions to the extension
"""

import json
import redis
import time
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import sys
sys.path.append(str(Path(__file__).parent))

from utils import load_json, get_timestamp
from config import DEFINITIONS_DIR

class DefinitionCache:
    """Redis-based definition cache with fuzzy matching capabilities"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, redis_db: int = 0):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_db = redis_db
        
        # Redis connection
        try:
            self.redis_client = redis.Redis(
                host=redis_host, 
                port=redis_port, 
                db=redis_db,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            print(f"✓ Connected to Redis at {redis_host}:{redis_port}")
        except redis.ConnectionError:
            print(f"❌ Could not connect to Redis. Please ensure Redis is running.")
            print(f"   Install Redis: https://redis.io/docs/getting-started/")
            raise
        
        # Cache keys
        self.definitions_key = "contextsnap:definitions"
        self.word_index_key = "contextsnap:word_index" 
        self.metadata_key = "contextsnap:metadata"
        
        # Fuzzy matching settings
        self.min_similarity = 0.8  # Minimum similarity for fuzzy matches
        self.max_fuzzy_results = 5  # Maximum fuzzy match results to return

    def load_definitions_to_cache(self, definitions_file: Optional[Path] = None) -> int:
        """Load definitions from JSON file into Redis cache"""
        
        if definitions_file is None:
            # Find the most recent definitions file
            definition_files = list(DEFINITIONS_DIR.glob("definitions_*.json"))
            if not definition_files:
                raise FileNotFoundError("No definitions files found")
            definitions_file = max(definition_files, key=lambda f: f.stat().st_mtime)
        
        print(f"Loading definitions from: {definitions_file.name}")
        
        try:
            data = load_json(definitions_file)
            definitions = data.get("definitions", {})
            
            if not definitions:
                raise ValueError("No definitions found in file")
            
            # Clear existing cache
            self.redis_client.delete(self.definitions_key)
            self.redis_client.delete(self.word_index_key)
            
            # Store definitions in Redis hash
            pipeline = self.redis_client.pipeline()
            
            for word, definition in definitions.items():
                # Store definition
                pipeline.hset(self.definitions_key, word.lower(), json.dumps({
                    "word": word,
                    "definition": definition,
                    "cached_at": get_timestamp()
                }))
                
                # Store word in index for fuzzy matching
                pipeline.sadd(self.word_index_key, word.lower())
            
            pipeline.execute()
            
            # Store metadata
            metadata = {
                "total_definitions": len(definitions),
                "loaded_at": get_timestamp(),
                "source_file": definitions_file.name,
                "model_used": data.get("model_used", "unknown"),
                "cache_version": "1.0"
            }
            self.redis_client.hset(self.metadata_key, mapping=metadata)
            
            print(f"✓ Loaded {len(definitions)} definitions into Redis cache")
            return len(definitions)
            
        except Exception as e:
            print(f"❌ Error loading definitions: {e}")
            raise

    def get_exact_definition(self, word: str) -> Optional[Dict[str, Any]]:
        """Get exact definition for a word"""
        
        result = self.redis_client.hget(self.definitions_key, word.lower())
        if result:
            return json.loads(result)
        return None

    def get_fuzzy_matches(self, word: str) -> List[Tuple[str, float, Dict[str, Any]]]:
        """Get fuzzy matches for a word with similarity scores"""
        
        word_lower = word.lower()
        
        # Get all words from index
        all_words = self.redis_client.smembers(self.word_index_key)
        
        # Calculate similarities
        matches = []
        for cached_word in all_words:
            similarity = SequenceMatcher(None, word_lower, cached_word).ratio()
            
            if similarity >= self.min_similarity:
                # Get the definition
                result = self.redis_client.hget(self.definitions_key, cached_word)
                if result:
                    definition_data = json.loads(result)
                    matches.append((cached_word, similarity, definition_data))
        
        # Sort by similarity (highest first) and limit results
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches[:self.max_fuzzy_results]

    def search_definition(self, word: str) -> Dict[str, Any]:
        """Search for a word definition with fallback to fuzzy matching"""
        
        start_time = time.time()
        
        # Try exact match first
        exact_match = self.get_exact_definition(word)
        if exact_match:
            return {
                "query": word,
                "match_type": "exact",
                "definition": exact_match["definition"],
                "original_word": exact_match["word"],
                "similarity": 1.0,
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        
        # Try fuzzy matching
        fuzzy_matches = self.get_fuzzy_matches(word)
        if fuzzy_matches:
            best_match = fuzzy_matches[0]  # Highest similarity
            cached_word, similarity, definition_data = best_match
            
            return {
                "query": word,
                "match_type": "fuzzy",
                "definition": definition_data["definition"],
                "original_word": definition_data["word"],
                "matched_word": cached_word,
                "similarity": round(similarity, 3),
                "alternative_matches": [
                    {
                        "word": match[2]["word"],
                        "similarity": round(match[1], 3)
                    }
                    for match in fuzzy_matches[1:3]  # Show top 2 alternatives
                ],
                "response_time_ms": round((time.time() - start_time) * 1000, 2)
            }
        
        # No matches found
        return {
            "query": word,
            "match_type": "none",
            "definition": None,
            "error": f"No definition found for '{word}'",
            "response_time_ms": round((time.time() - start_time) * 1000, 2)
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        
        metadata = self.redis_client.hgetall(self.metadata_key)
        definition_count = self.redis_client.hlen(self.definitions_key)
        word_count = self.redis_client.scard(self.word_index_key)
        
        return {
            "total_definitions": definition_count,
            "total_words_indexed": word_count,
            "cache_metadata": metadata,
            "redis_info": {
                "host": self.redis_host,
                "port": self.redis_port,
                "db": self.redis_db
            }
        }

    def test_fuzzy_matching(self, test_words: List[str] = None) -> None:
        """Test fuzzy matching with sample words"""
        
        if test_words is None:
            test_words = [
                "algorythm",  # algorithm
                "machien",    # machine  
                "netwrk",     # network
                "artifical",  # artificial
                "optmization" # optimization
            ]
        
        print("\n=== Fuzzy Matching Test ===")
        
        for test_word in test_words:
            result = self.search_definition(test_word)
            
            print(f"\nQuery: '{test_word}'")
            print(f"Match Type: {result['match_type']}")
            
            if result['match_type'] != 'none':
                print(f"Original Word: {result['original_word']}")
                print(f"Similarity: {result['similarity']}")
                print(f"Definition: {result['definition'][:100]}...")
                
                if 'alternative_matches' in result:
                    print("Alternatives:", [f"{alt['word']} ({alt['similarity']})" 
                                         for alt in result['alternative_matches']])
            else:
                print(f"No matches found")
            
            print(f"Response Time: {result['response_time_ms']}ms")

def main():
    """Test the cache system"""
    try:
        print("=== ContextSnap Redis Cache Setup ===")
        
        # Initialize cache
        cache = DefinitionCache()
        
        # Load definitions
        definitions_count = cache.load_definitions_to_cache()
        
        # Show stats
        stats = cache.get_cache_stats()
        print(f"\n=== Cache Statistics ===")
        print(f"Definitions loaded: {stats['total_definitions']}")
        print(f"Words indexed: {stats['total_words_indexed']}")
        print(f"Source file: {stats['cache_metadata'].get('source_file', 'unknown')}")
        
        # Test fuzzy matching
        cache.test_fuzzy_matching()
        
        print(f"\n✓ Redis cache ready for extension integration!")
        
    except Exception as e:
        print(f"❌ Error setting up cache: {e}")

if __name__ == "__main__":
    main()
