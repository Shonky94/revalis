"""
Recovery utility to check checkpoint status and extract existing definitions
"""

import json
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent))

from utils import load_json, save_json, get_timestamp
from config import DEFINITIONS_DIR

def check_checkpoint():
    """Check if checkpoint exists and extract definitions"""
    
    checkpoint_file = DEFINITIONS_DIR / "checkpoint_definitions.json"
    
    print("=== ContextSnap Definition Recovery ===")
    print(f"Checking checkpoint: {checkpoint_file}")
    
    if not checkpoint_file.exists():
        print("❌ No checkpoint file found")
        return
    
    try:
        checkpoint_data = load_json(checkpoint_file)
        
        definitions = checkpoint_data.get("definitions", {})
        completed = checkpoint_data.get("completed", 0)
        total = checkpoint_data.get("total", 0)
        
        print(f"✓ Checkpoint found!")
        print(f"  Definitions generated: {len(definitions)}")
        print(f"  Progress: {completed}/{total}")
        print(f"  Success rate: {len(definitions)/completed*100:.1f}%" if completed > 0 else "  Success rate: N/A")
        
        if definitions:
            # Save the existing definitions
            timestamp = get_timestamp()
            recovery_file = DEFINITIONS_DIR / f"definitions_recovered_{timestamp}.json"
            
            recovery_data = {
                "generation_timestamp": timestamp,
                "model_used": "llama3",
                "status": "RECOVERED_FROM_CHECKPOINT",
                "definitions_recovered": len(definitions),
                "definitions": definitions
            }
            
            save_json(recovery_data, recovery_file)
            print(f"✓ Definitions saved to: {recovery_file}")
            
            # Show sample definitions
            print(f"\nSample definitions:")
            sample_words = list(definitions.keys())[:5]
            for word in sample_words:
                print(f"  {word}: {definitions[word][:80]}{'...' if len(definitions[word]) > 80 else ''}")
        
        return len(definitions)
        
    except Exception as e:
        print(f"❌ Error reading checkpoint: {e}")
        return 0

if __name__ == "__main__":
    check_checkpoint()
