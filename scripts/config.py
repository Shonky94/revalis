"""
ContextSnap Local LLM Configuration
Centralized configuration for all scripts with easy reusability
"""

import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SCRIPTS_DIR = BASE_DIR / "scripts"

# Data directories
ARXIV_PDFS_DIR = DATA_DIR / "arxiv_pdfs"
WORD_LISTS_DIR = DATA_DIR / "word_lists"
PROCESSED_DIR = DATA_DIR / "processed"
DEFINITIONS_DIR = DATA_DIR / "definitions"
LOGS_DIR = DATA_DIR / "logs"

# Ensure all directories exist
for directory in [DATA_DIR, ARXIV_PDFS_DIR, WORD_LISTS_DIR, PROCESSED_DIR, DEFINITIONS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# PDF Processing Configuration
PDF_CONFIG = {
    "max_file_size_mb": 50,  # Maximum PDF file size in MB
    "chunk_size": 1000,      # Text chunk size for processing
    "min_word_length": 3,    # Minimum word length to consider
    "max_word_length": 30,   # Maximum word length to consider
    "languages": ["en"],     # Languages to process
}

# NLP Configuration
NLP_CONFIG = {
    "min_frequency": 2,      # Minimum word frequency to include
    "max_words_per_pdf": 500, # Maximum unique words per PDF
    "technical_score_threshold": 0.3,  # Minimum technical score
    "excluded_pos_tags": ["DT", "CC", "IN", "TO", "PRP", "PRP$"],  # POS tags to exclude
    "min_chars": 4,          # Minimum character count
    "max_chars": 25,         # Maximum character count
}

# Ollama Configuration
OLLAMA_CONFIG = {
    "base_url": "http://localhost:11434",
    "model": "llama3",
    "timeout": 30,
    "max_retries": 3,
    "retry_delay": 5,        # seconds
    "batch_size": 10,        # words to process in batch
    "rate_limit_delay": 1,   # delay between requests in seconds
}

# Redis Configuration
REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "decode_responses": True,
    "key_prefix": "contextsnap:",
    "definition_expiry": 86400 * 30,  # 30 days in seconds
}

# Script Management Configuration
SCRIPT_CONFIG = {
    "resume_from_checkpoint": True,
    "checkpoint_interval": 100,  # Save progress every N items
    "progress_update_interval": 10,  # Show progress every N items
    "parallel_processing": True,
    "max_workers": 4,
}

# File naming conventions
FILE_PATTERNS = {
    "raw_text": "raw_text_{timestamp}.txt",
    "word_list": "words_{timestamp}.json",
    "processed_words": "processed_{timestamp}.json",
    "definitions": "definitions_{timestamp}.json",
    "checkpoint": "checkpoint_{script}_{timestamp}.json",
    "log": "{script}_{timestamp}.log",
}

# Common words to exclude (expand as needed)
COMMON_WORDS = {
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", 
    "not", "on", "with", "he", "as", "you", "do", "at", "this", "but", "his", 
    "by", "from", "they", "we", "say", "her", "she", "or", "an", "will", "my",
    "one", "all", "would", "there", "their", "what", "so", "up", "out", "if",
    "about", "who", "get", "which", "go", "me", "when", "make", "can", "like",
    "time", "no", "just", "him", "know", "take", "people", "into", "year", "your",
    "good", "some", "could", "them", "see", "other", "than", "then", "now", "look",
    "only", "come", "its", "over", "think", "also", "back", "after", "use", "two",
    "how", "our", "work", "first", "well", "way", "even", "new", "want", "because",
    "any", "these", "give", "day", "most", "us", "is", "was", "are", "been", "has",
    "had", "were", "said", "each", "which", "did", "very", "where", "much", "too",
    "right", "still", "should", "such", "here", "old", "find", "may", "say", "part"
}

# Academic field keywords (helps identify technical terms)
ACADEMIC_KEYWORDS = {
    "computer_science": ["algorithm", "neural", "network", "machine", "learning", "artificial", "intelligence"],
    "mathematics": ["theorem", "proof", "equation", "matrix", "vector", "function", "derivative"],
    "physics": ["quantum", "relativity", "electromagnetic", "thermodynamic", "particle", "wave"],
    "biology": ["genome", "protein", "cellular", "molecular", "genetic", "enzyme"],
    "chemistry": ["molecular", "compound", "reaction", "synthesis", "catalysis", "polymer"],
    "medicine": ["clinical", "diagnostic", "therapeutic", "pathology", "pharmacology", "biomarker"],
}

def get_timestamp():
    """Get current timestamp for file naming"""
    from datetime import datetime
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def get_log_file(script_name):
    """Get log file path for a script"""
    timestamp = get_timestamp()
    filename = FILE_PATTERNS["log"].format(script=script_name, timestamp=timestamp)
    return LOGS_DIR / filename

def get_checkpoint_file(script_name):
    """Get checkpoint file path for a script"""
    timestamp = get_timestamp()
    filename = FILE_PATTERNS["checkpoint"].format(script=script_name, timestamp=timestamp)
    return PROCESSED_DIR / filename

def validate_config():
    """Validate configuration settings"""
    errors = []
    
    # Check required directories
    for name, path in [
        ("ARXIV_PDFS_DIR", ARXIV_PDFS_DIR),
        ("WORD_LISTS_DIR", WORD_LISTS_DIR), 
        ("PROCESSED_DIR", PROCESSED_DIR),
        ("DEFINITIONS_DIR", DEFINITIONS_DIR)
    ]:
        if not path.exists():
            errors.append(f"Directory {name} does not exist: {path}")
    
    # Check numeric ranges
    if PDF_CONFIG["min_word_length"] >= PDF_CONFIG["max_word_length"]:
        errors.append("PDF_CONFIG: min_word_length must be less than max_word_length")
    
    if NLP_CONFIG["min_chars"] >= NLP_CONFIG["max_chars"]:
        errors.append("NLP_CONFIG: min_chars must be less than max_chars")
    
    if OLLAMA_CONFIG["batch_size"] <= 0:
        errors.append("OLLAMA_CONFIG: batch_size must be positive")
    
    return errors

if __name__ == "__main__":
    # Validate configuration when run directly
    errors = validate_config()
    if errors:
        print("Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("Configuration is valid!")
        print(f"Base directory: {BASE_DIR}")
        print(f"Data directory: {DATA_DIR}")
        print(f"Scripts directory: {SCRIPTS_DIR}")
