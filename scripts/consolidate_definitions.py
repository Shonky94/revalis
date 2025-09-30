"""
Definition Consolidation Utility for ContextSnap
Consolidates multiple definition files into one clean final version
"""

import json
from pathlib import Path
from collections import defaultdict
import sys
sys.path.append(str(Path(__file__).parent))

from utils import load_json, save_json, get_timestamp
from config import DEFINITIONS_DIR

def consolidate_definitions():
    """Consolidate all definition files into one clean final version"""
    
    print("=== ContextSnap Definition Consolidator ===")
    
    # Find all definition files
    all_files = list(DEFINITIONS_DIR.glob("definitions_*.json"))
    
    if not all_files:
        print("❌ No definition files found")
        return
    
    print(f"Found {len(all_files)} definition files to consolidate")
    
    # Collect all unique definitions
    all_definitions = {}
    file_stats = []
    
    for file_path in sorted(all_files):
        try:
            data = load_json(file_path)
            definitions = data.get("definitions", {})
            
            # Track stats for each file
            file_stats.append({
                "file": file_path.name,
                "count": len(definitions),
                "timestamp": data.get("generation_timestamp", "unknown")
            })
            
            # Merge definitions (later files override earlier ones if there are duplicates)
            for word, definition in definitions.items():
                if word not in all_definitions:
                    all_definitions[word] = definition
                elif definition != all_definitions[word]:
                    # If definitions differ, keep the longer/more detailed one
                    if len(definition) > len(all_definitions[word]):
                        all_definitions[word] = definition
            
        except Exception as e:
            print(f"⚠️  Error reading {file_path.name}: {e}")
    
    # Show consolidation stats
    print(f"\nConsolidation Results:")
    print(f"  Total unique definitions: {len(all_definitions)}")
    print(f"  Files processed: {len([f for f in file_stats if f['count'] > 0])}")
    
    # Find the most recent file for model info
    latest_file = max([f for f in all_files if f.name.startswith("definitions_")], 
                     key=lambda f: f.stat().st_mtime)
    latest_data = load_json(latest_file)
    
    # Create final consolidated file
    timestamp = get_timestamp()
    final_results = {
        "generation_timestamp": timestamp,
        "consolidation_info": {
            "source_files_count": len(all_files),
            "consolidation_date": timestamp,
            "total_unique_definitions": len(all_definitions)
        },
        "model_used": latest_data.get("model_used", "llama3"),
        "status": "COMPLETED",
        "definitions_count": len(all_definitions),
        "definitions": all_definitions
    }
    
    # Save final consolidated file
    final_file = DEFINITIONS_DIR / f"definitions_final_{timestamp}.json"
    save_json(final_results, final_file)
    
    print(f"✓ Consolidated definitions saved to: {final_file.name}")
    
    # Show sample definitions
    print(f"\nSample definitions (showing first 5):")
    sample_words = sorted(list(all_definitions.keys()))[:5]
    for word in sample_words:
        definition = all_definitions[word]
        preview = definition[:80] + "..." if len(definition) > 80 else definition
        print(f"  {word}: {preview}")
    
    # Ask about cleanup
    print(f"\nCleanup Options:")
    print(f"  {len(all_files)} intermediate files can be removed")
    print(f"  Final file: {final_file.name} ({len(all_definitions)} definitions)")
    
    return final_file, all_files, len(all_definitions)

def cleanup_intermediate_files(keep_files=None):
    """Remove intermediate definition files, keeping specified ones"""
    
    if keep_files is None:
        keep_files = []
    
    all_files = list(DEFINITIONS_DIR.glob("definitions_*.json"))
    
    # Keep the final file and any specified files
    files_to_remove = []
    for file_path in all_files:
        if (file_path.name.startswith("definitions_partial_") or 
            file_path.name == "definitions_in_progress.json"):
            if file_path not in keep_files:
                files_to_remove.append(file_path)
    
    if not files_to_remove:
        print("No intermediate files to remove")
        return
    
    print(f"\nRemoving {len(files_to_remove)} intermediate files...")
    
    for file_path in files_to_remove:
        try:
            file_path.unlink()
            print(f"  ✓ Removed: {file_path.name}")
        except Exception as e:
            print(f"  ❌ Failed to remove {file_path.name}: {e}")
    
    print(f"✓ Cleanup complete!")

def main():
    """Main consolidation function"""
    try:
        final_file, all_files, definition_count = consolidate_definitions()
        
        print(f"\n{'='*50}")
        print(f"CONSOLIDATION COMPLETE")
        print(f"{'='*50}")
        print(f"Final file: {final_file.name}")
        print(f"Total definitions: {definition_count}")
        print(f"Ready for Phase 3: Redis integration")
        
        # Ask user if they want to cleanup
        cleanup_response = input(f"\nDo you want to remove {len(all_files)-1} intermediate files? (y/n): ").strip().lower()
        
        if cleanup_response in ['y', 'yes']:
            cleanup_intermediate_files(keep_files=[final_file])
        else:
            print("Intermediate files kept. You can run cleanup manually later.")
        
    except Exception as e:
        print(f"❌ Error during consolidation: {e}")

if __name__ == "__main__":
    main()
