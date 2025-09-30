"""
Definition Generator for ContextSnap
Generates academic/technical definitions using Ollama + Llama3 model
"""

import json
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict

# Add current directory to path for imports
import sys
sys.path.append(str(Path(__file__).parent))

from utils import (
    ProgressTracker, CheckpointManager,
    save_json, load_json, get_timestamp
)
from config import WORD_LISTS_DIR, DEFINITIONS_DIR, SCRIPT_CONFIG
CONFIG = SCRIPT_CONFIG

class DefinitionGenerator:
    """Generate definitions for academic/technical terms using Ollama + Llama3"""
    
    def __init__(self, model_name: str = "llama3", resume: bool = True):
        self.model_name = model_name
        self.resume = resume
        self.ollama_url = "http://localhost:11434/api/generate"
        
        # Ensure output directory exists
        DEFINITIONS_DIR.mkdir(parents=True, exist_ok=True)
        
        # Initialize checkpoint manager
        checkpoint_file = DEFINITIONS_DIR / "checkpoint_definitions.json"
        self.checkpoint_manager = CheckpointManager(checkpoint_file)
        
        # Template for generating definitions
        self.definition_template = """
You are an expert academic and technical dictionary. Your task is to provide clear, concise definitions for technical and academic terms.

For the term: "{word}"

Provide a definition that:
1. Is academic/technical in nature (avoid simple common words)
2. Explains the concept clearly and concisely (1-2 sentences max)
3. Includes context about the field it's from if specialized
4. Is suitable for someone learning the term

Respond with ONLY the definition, no extra formatting or explanations.
If the term is too common/basic (like "the", "and", "is"), respond with "SKIP".

Term: {word}
Definition:"""

    def test_ollama_connection(self) -> bool:
        """Test if Ollama is running and responsive"""
        try:
            response = requests.post(
                self.ollama_url,
                json={
                    "model": self.model_name,
                    "prompt": "Test connection. Reply with 'OK'",
                    "stream": False
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✓ Ollama connection successful with model: {self.model_name}")
                return True
            else:
                print(f"✗ Ollama connection failed: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"✗ Cannot connect to Ollama: {e}")
            print("Make sure Ollama is running with: ollama serve")
            return False

    def generate_definition(self, word: str, max_retries: int = 3) -> Optional[str]:
        """Generate a definition for a single word using Ollama"""
        
        prompt = self.definition_template.format(word=word)
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.ollama_url,
                    json={
                        "model": self.model_name,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,  # Lower temperature for more consistent definitions
                            "top_p": 0.9,
                            "top_k": 40
                        }
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    definition = result.get("response", "").strip()
                    
                    # Skip if model indicates it's too basic
                    if definition.upper() == "SKIP" or len(definition) < 10:
                        return None
                    
                    return definition
                else:
                    print(f"HTTP Error {response.status_code} for word: {word}")
                    
            except requests.exceptions.RequestException as e:
                print(f"Request failed for '{word}' (attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(1)  # Brief pause before retry
        
        return None

    def generate_batch_definitions(self, words: List[str], batch_size: int = 10) -> Dict[str, str]:
        """Generate definitions for a batch of words"""
        
        definitions = {}
        original_count = len(words)
        
        # Load existing progress if resuming
        if self.resume:
            checkpoint = self.checkpoint_manager.load_checkpoint()
            if checkpoint:
                definitions = checkpoint.get("definitions", {})
                processed_words = set(definitions.keys())
                remaining_words = [w for w in words if w not in processed_words]
                completed = checkpoint.get("completed", 0)
                successful_definitions = len(definitions)
                print(f"🔄 Resuming: {len(definitions)} definitions already generated")
                print(f"   Previous progress: {completed} words processed, {successful_definitions/(completed) if completed > 0 else 0:.1f}% success rate")
                print(f"   Remaining: {len(remaining_words)} words to process")
                words = remaining_words
        
        # Initialize progress tracker with the correct remaining count
        progress = ProgressTracker(len(words), "Generating definitions")
        
        # Use a single master definitions file that gets updated incrementally
        master_file = DEFINITIONS_DIR / f"definitions_master.json"
        successful_definitions = 0
        
        for i, word in enumerate(words):
            definition = self.generate_definition(word)
            
            if definition:
                definitions[word] = definition
                successful_definitions += 1
                
                # Update the single master file after each successful definition
                master_data = {
                    "generation_timestamp": get_timestamp(),
                    "model_used": self.model_name,
                    "status": "IN_PROGRESS",
                    "definitions_generated": len(definitions),
                    "last_word_processed": word,
                    "words_processed": f"{i+1}/{len(words)}",
                    "success_rate": f"{successful_definitions/(i+1)*100:.1f}%",
                    "definitions": definitions
                }
                save_json(master_data, master_file)
            
            # Update progress - show every 10 words processed
            if (i + 1) % 10 == 0 or definition:
                elapsed = time.time() - progress.start_time
                elapsed_str = f"{elapsed/60:.1f}m" if elapsed > 60 else f"{elapsed:.1f}s"
                success_rate = successful_definitions/(i+1)*100
                print(f"Progress: {i+1}/{len(words)} words processed | {successful_definitions} definitions generated | {success_rate:.1f}% success rate | Elapsed: {elapsed_str}")
            
            # Still update the internal progress tracker for ETA calculation
            progress.update(1)
            
            # Save checkpoint every 50 words for better performance (only internal checkpoint)
            if (i + 1) % 50 == 0:
                self.checkpoint_manager.save_checkpoint({
                    "definitions": definitions,
                    "completed": i + 1,
                    "total": len(words),
                    "successful_definitions": successful_definitions
                })
                print(f"💾 Checkpoint saved: {len(definitions)} definitions ({successful_definitions/(i+1)*100:.1f}% success rate)")
            
            # Small delay to be respectful to the model
            time.sleep(0.1)
        
        progress.complete()
        return definitions

    def load_word_lists(self) -> List[str]:
        """Load word lists from NLP processing results"""
        
        word_files = list(WORD_LISTS_DIR.glob("word_list_*.json"))
        
        if not word_files:
            print("No word lists found in word lists directory")
            return []
        
        # Use the most recent word list
        latest_file = max(word_files, key=lambda f: f.stat().st_mtime)
        print(f"Loading words from: {latest_file.name}")
        
        try:
            word_data = load_json(latest_file)
            
            # Handle new format where word_data is a list of word objects
            all_words = set()
            
            if isinstance(word_data, list):
                # New format: list of word objects
                for word_obj in word_data:
                    if isinstance(word_obj, dict) and "word" in word_obj:
                        word = word_obj["word"]
                        # Filter out very common words and short words
                        if len(word) >= 3 and word.isalpha():
                            all_words.add(word.lower())
            
            elif isinstance(word_data, dict):
                # Old format: dict with categories
                if "single_words" in word_data:
                    all_words.update(word_data["single_words"])
                if "named_entities" in word_data:
                    all_words.update(word_data["named_entities"])
                if "high_value_terms" in word_data:
                    all_words.update(word_data["high_value_terms"])
            
            # Filter out very common words
            common_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can", 
                          "had", "her", "was", "one", "our", "out", "day", "get", "has", 
                          "him", "his", "how", "man", "new", "now", "old", "see", "two", 
                          "way", "who", "boy", "did", "its", "let", "put", "say", "she", 
                          "too", "use"}
            
            filtered_words = [w for w in all_words if w not in common_words and len(w) >= 4]
            
            # Convert to sorted list for consistent processing
            word_list = sorted(filtered_words)
            print(f"Loaded {len(word_list)} unique words for definition generation")
            
            return word_list
            
        except Exception as e:
            print(f"Error loading word list from {latest_file}: {e}")
            return []

    def process_definitions(self) -> Dict[str, Any]:
        """Main processing function - generate definitions for all words"""
        
        print("=== ContextSnap Definition Generator ===")
        print(f"Model: {self.model_name}")
        
        # Test Ollama connection
        if not self.test_ollama_connection():
            raise ConnectionError("Cannot connect to Ollama. Please ensure it's running.")
        
        # Load words to process
        words = self.load_word_lists()
        if not words:
            raise ValueError("No words found to process")
        
        # Generate definitions
        print(f"\nGenerating definitions for {len(words)} words...")
        definitions = self.generate_batch_definitions(words)
        
        # Prepare results
        timestamp = get_timestamp()
        results = {
            "generation_timestamp": timestamp,
            "model_used": self.model_name,
            "total_words_processed": len(words),
            "definitions_generated": len(definitions),
            "success_rate": f"{len(definitions)/len(words)*100:.1f}%",
            "definitions": definitions
        }
        
        # Save results
        output_file = DEFINITIONS_DIR / f"definitions_{timestamp}.json"
        save_json(results, output_file)
        print(f"Results saved to {output_file}")
        
        # Cleanup checkpoint
        self.checkpoint_manager.cleanup()
        
        return results

    def print_summary(self, results: Dict[str, Any]) -> None:
        """Print a summary of definition generation results"""
        
        print("\n=== Definition Generation Summary ===")
        print(f"Model Used: {results['model_used']}")
        print(f"Total Words: {results['total_words_processed']}")
        print(f"Definitions Generated: {results['definitions_generated']}")
        print(f"Success Rate: {results['success_rate']}")
        
        # Show sample definitions
        definitions = results["definitions"]
        if definitions:
            print(f"\nSample Definitions:")
            sample_words = list(definitions.keys())[:5]
            for word in sample_words:
                print(f"  {word}: {definitions[word][:100]}{'...' if len(definitions[word]) > 100 else ''}")

def main():
    """Main execution function"""
    try:
        generator = DefinitionGenerator()
        results = generator.process_definitions()
        generator.print_summary(results)
        
        print("\n✓ Definition generation completed successfully!")
        
    except KeyboardInterrupt:
        print("\nGeneration interrupted by user.")
        print("Progress has been saved. Run the script again to resume.")
    except Exception as e:
        print(f"Error during definition generation: {e}")
        print(f"Unexpected error occurred. Check the error details above.")

if __name__ == "__main__":
    main()
