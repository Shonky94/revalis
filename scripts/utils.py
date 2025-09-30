"""
Common utilities for ContextSnap Local LLM system
Shared functions used across all scripts for consistency and reusability
"""

import json
import pickle
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from config import LOGS_DIR

def get_timestamp() -> str:
    """Get a timestamp string for file naming"""
    return datetime.now().strftime("%Y%m%d_%H%M%S")

class ProgressTracker:
    """Track and display progress for long-running operations"""
    
    def __init__(self, total: int, name: str = "Operation", update_interval: int = 10):
        self.total = total
        self.current = 0
        self.name = name
        self.update_interval = update_interval
        self.start_time = time.time()
        self.last_update = 0
    
    def update(self, increment: int = 1) -> None:
        """Update progress and optionally display"""
        self.current += increment
        
        if self.current - self.last_update >= self.update_interval or self.current >= self.total:
            self._display_progress()
            self.last_update = self.current
    
    def _display_progress(self) -> None:
        """Display current progress"""
        percentage = (self.current / self.total) * 100
        elapsed = time.time() - self.start_time
        
        if self.current > 0:
            eta = (elapsed / self.current) * (self.total - self.current)
            eta_str = f"ETA: {self._format_time(eta)}"
        else:
            eta_str = "ETA: calculating..."
        
        print(f"\r{self.name}: {self.current}/{self.total} ({percentage:.1f}%) - "
              f"Elapsed: {self._format_time(elapsed)} - {eta_str}", end="", flush=True)
        
        if self.current >= self.total:
            print()  # New line when complete
    
    def _format_time(self, seconds: float) -> str:
        """Format time in human readable format"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

class CheckpointManager:
    """Manage checkpoints for resumable operations"""
    
    def __init__(self, checkpoint_file: Path, interval: int = 100):
        self.checkpoint_file = checkpoint_file
        self.interval = interval
        self.counter = 0
        self.data = {}
    
    def load_checkpoint(self) -> Dict[str, Any]:
        """Load checkpoint data if exists"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
                    print(f"Loaded checkpoint from {self.checkpoint_file}")
                    return self.data
            except Exception as e:
                print(f"Failed to load checkpoint: {e}")
        return {}
    
    def save_checkpoint(self, data: Dict[str, Any], force: bool = False) -> None:
        """Save checkpoint data"""
        self.counter += 1
        self.data.update(data)
        
        if force or self.counter % self.interval == 0:
            try:
                with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=2)
                print(f"\nCheckpoint saved to {self.checkpoint_file}")
            except Exception as e:
                print(f"Failed to save checkpoint: {e}")
    
    def cleanup(self) -> None:
        """Remove checkpoint file after successful completion"""
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                print(f"Checkpoint cleaned up: {self.checkpoint_file}")
        except Exception as e:
            print(f"Failed to cleanup checkpoint: {e}")


def save_json(data: Any, filepath: Path, indent: int = 2) -> None:
    """Save data as JSON with error handling"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
    except Exception as e:
        raise Exception(f"Failed to save JSON to {filepath}: {e}")

def load_json(filepath: Path) -> Any:
    """Load JSON data with error handling"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError(f"JSON file not found: {filepath}")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in {filepath}: {e}")
    except Exception as e:
        raise Exception(f"Failed to load JSON from {filepath}: {e}")

def save_text_file(text: str, filepath: Path, encoding: str = 'utf-8') -> None:
    """Save text to file with error handling"""
    try:
        with open(filepath, 'w', encoding=encoding) as f:
            f.write(text)
    except Exception as e:
        raise Exception(f"Failed to save text to {filepath}: {e}")

def load_text_file(filepath: Path, encoding: str = 'utf-8') -> str:
    """Load text from file with error handling"""
    try:
        with open(filepath, 'r', encoding=encoding) as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Text file not found: {filepath}")
    except Exception as e:
        raise Exception(f"Failed to load text from {filepath}: {e}")

def clean_word(word: str) -> Optional[str]:
    """Clean and normalize a word"""
    if not word:
        return None
    
    # Remove non-alphabetic characters and convert to lowercase
    cleaned = ''.join(c for c in word if c.isalpha()).lower().strip()
    
    # Return None if empty or too short/long
    if not cleaned or len(cleaned) < 3 or len(cleaned) > 30:
        return None
    
    return cleaned

def is_technical_term(word: str, context: str = "", academic_fields: Set[str] = None) -> float:
    """
    Score how likely a word is to be a technical term (0.0 to 1.0)
    Higher score means more likely to be technical
    """
    score = 0.0
    
    # Length-based scoring (longer words often more technical)
    if len(word) >= 8:
        score += 0.3
    elif len(word) >= 6:
        score += 0.2
    elif len(word) >= 5:
        score += 0.1
    
    # Capitalization pattern (CamelCase, etc.)
    if word != word.lower() and word != word.upper():
        score += 0.2
    
    # Contains numbers or special patterns
    if any(c.isdigit() for c in word):
        score += 0.15
    
    # Suffix-based scoring (common technical suffixes)
    technical_suffixes = ['-tion', '-sion', '-ment', '-ness', '-ity', '-ism', '-ology', '-graphy', '-metry']
    for suffix in technical_suffixes:
        if word.endswith(suffix.replace('-', '')):
            score += 0.25
            break
    
    # Prefix-based scoring (common technical prefixes)
    technical_prefixes = ['bio-', 'geo-', 'neuro-', 'micro-', 'macro-', 'multi-', 'trans-', 'inter-', 'intra-']
    for prefix in technical_prefixes:
        if word.startswith(prefix.replace('-', '')):
            score += 0.2
            break
    
    # Context-based scoring
    if context:
        context_lower = context.lower()
        technical_indicators = ['algorithm', 'method', 'analysis', 'theory', 'model', 'system', 'process']
        for indicator in technical_indicators:
            if indicator in context_lower:
                score += 0.1
                break
    
    return min(score, 1.0)  # Cap at 1.0

def filter_academic_words(words: List[str], min_technical_score: float = 0.3) -> List[Tuple[str, float]]:
    """Filter words to keep only likely academic/technical terms"""
    from config import COMMON_WORDS
    
    filtered = []
    for word in words:
        cleaned = clean_word(word)
        if not cleaned or cleaned in COMMON_WORDS:
            continue
        
        technical_score = is_technical_term(cleaned)
        if technical_score >= min_technical_score:
            filtered.append((cleaned, technical_score))
    
    # Sort by technical score (highest first)
    filtered.sort(key=lambda x: x[1], reverse=True)
    return filtered

def merge_word_lists(*word_lists: List[Tuple[str, float]]) -> List[Tuple[str, float]]:
    """Merge multiple word lists, combining scores for duplicates"""
    word_scores = {}
    
    for word_list in word_lists:
        for word, score in word_list:
            if word in word_scores:
                # Average the scores for duplicates
                word_scores[word] = (word_scores[word] + score) / 2
            else:
                word_scores[word] = score
    
    # Convert back to list and sort
    result = [(word, score) for word, score in word_scores.items()]
    result.sort(key=lambda x: x[1], reverse=True)
    return result

def estimate_processing_time(item_count: int, items_per_second: float) -> str:
    """Estimate processing time in human readable format"""
    total_seconds = item_count / items_per_second
    
    if total_seconds < 60:
        return f"{total_seconds:.1f} seconds"
    elif total_seconds < 3600:
        minutes = total_seconds / 60
        return f"{minutes:.1f} minutes"
    elif total_seconds < 86400:
        hours = total_seconds / 3600
        return f"{hours:.1f} hours"
    else:
        days = total_seconds / 86400
        return f"{days:.1f} days"

def get_file_size_mb(filepath: Path) -> float:
    """Get file size in megabytes"""
    try:
        size_bytes = filepath.stat().st_size
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0.0

def validate_file_type(filepath: Path, expected_extensions: List[str]) -> bool:
    """Validate file has expected extension"""
    return filepath.suffix.lower() in [ext.lower() for ext in expected_extensions]

def create_backup(filepath: Path) -> Path:
    """Create a backup of a file with timestamp"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = filepath.parent / f"{filepath.stem}_backup_{timestamp}{filepath.suffix}"
    
    try:
        import shutil
        shutil.copy2(filepath, backup_path)
        return backup_path
    except Exception as e:
        raise Exception(f"Failed to create backup: {e}")

def get_available_memory_gb() -> float:
    """Get available system memory in GB"""
    try:
        import psutil
        return psutil.virtual_memory().available / (1024**3)
    except ImportError:
        return 4.0  # Default assumption

if __name__ == "__main__":
    # Test utilities
    print("Testing utilities...")
    
    # Test progress tracker
    print("\nTesting progress tracker:")
    tracker = ProgressTracker(100, "Test Operation")
    for i in range(100):
        time.sleep(0.01)  # Simulate work
        tracker.update()
    
    # Test word cleaning and scoring
    test_words = ["algorithm", "the", "neural-network", "cat", "bioinformatics", "and"]
    print(f"\nTesting word filtering:")
    for word in test_words:
        cleaned = clean_word(word)
        if cleaned:
            score = is_technical_term(cleaned)
            print(f"  {word} -> {cleaned} (score: {score:.2f})")
    
    print("\nUtilities test complete!")
