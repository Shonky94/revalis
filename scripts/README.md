# ContextSnap Local LLM System - Phase 1

This directory contains the Phase 1 implementation for converting ContextSnap to use local LLM with Redis caching. Phase 1 focuses on PDF text extraction and NLP preprocessing to build a comprehensive word database.

## 🎯 Phase 1 Overview

**Goal**: Extract academic/technical terms from ArXiv PDFs and prepare them for definition generation.

**Components**:
1. **PDF Processor** - Extracts text from PDF files
2. **NLP Processor** - Identifies and scores technical terms
3. **Management Interface** - Easy-to-use script runner

## 🚀 Quick Start

### Option 1: Double-click launcher (Windows)
1. Double-click `run_manager.bat`
2. Follow the interactive menu

### Option 2: Command line
```bash
# Navigate to scripts directory
cd scripts

# Run interactive manager
python manage.py

# Or run specific commands
python manage.py setup     # Check system setup
python manage.py install   # Install dependencies
python manage.py phase1    # Run complete Phase 1
```

## 📁 Directory Structure

```
contextsnap/
├── scripts/                    # Processing scripts
│   ├── config.py              # Configuration settings
│   ├── utils.py               # Shared utilities
│   ├── pdf_processor.py       # PDF text extraction
│   ├── nlp_processor.py       # NLP word processing
│   ├── manage.py              # Management interface
│   ├── requirements.txt       # Python dependencies
│   └── run_manager.bat        # Windows launcher
├── data/                      # Data directories
│   ├── arxiv_pdfs/           # Place PDF files here
│   ├── processed/            # Extracted text files
│   ├── word_lists/           # Generated word lists
│   ├── definitions/          # Future: LLM definitions
│   └── logs/                 # Processing logs
└── [existing extension files]
```

## 📋 Setup Instructions

### 1. Install Dependencies
```bash
# Install required packages
pip install -r requirements.txt

# Install spaCy English model
python -m spacy download en_core_web_sm
```

### 2. Add PDF Files
- Place ArXiv PDF files in `data/arxiv_pdfs/`
- Supported: PDF files up to 50MB each
- Recommended: Academic papers from arXiv, PubMed, etc.

### 3. Run Processing
```bash
# Check everything is ready
python manage.py setup

# Run complete Phase 1
python manage.py phase1
```

## 🔧 Configuration

Edit `config.py` to customize processing:

```python
# PDF Processing
PDF_CONFIG = {
    "max_file_size_mb": 50,     # Maximum PDF size
    "chunk_size": 1000,         # Text processing chunks
    "min_word_length": 3,       # Minimum word length
    "max_word_length": 30,      # Maximum word length
}

# NLP Processing  
NLP_CONFIG = {
    "min_frequency": 2,         # Minimum word frequency
    "max_words_per_pdf": 500,   # Words per PDF to keep
    "technical_score_threshold": 0.3,  # Minimum technical score
}
```

## 🎛️ Script Management Features

### Resume Capability
- All scripts can resume from checkpoints if interrupted
- Checkpoints saved automatically every N processed items
- Safe to stop and restart processing

### Progress Tracking
- Real-time progress bars
- Estimated completion times
- Detailed logging

### Error Handling
- Graceful error recovery
- Detailed error logging
- Processing continues despite individual failures

## 📊 Output Files

### PDF Processing Output
- `processed/text_*.txt` - Extracted and cleaned text
- `processed/pdf_extraction_results_*.json` - Processing metadata

### NLP Processing Output
- `word_lists/word_list_*.json` - Final ranked word list
- `word_lists/nlp_results_*.json` - Detailed NLP analysis

### Word List Format
```json
[
  {
    "word": "neural-network",
    "type": "compound",
    "total_frequency": 45,
    "files_count": 12,
    "average_score": 0.842,
    "pos_tags": ["COMPOUND"],
    "priority": 0.954
  }
]
```

## 🔍 Usage Examples

### Process specific file types
```bash
# PDF processing only
python pdf_processor.py

# NLP processing only (requires processed text files)
python nlp_processor.py
```

### View statistics
```bash
python manage.py stats
```

### Clean up checkpoints
```bash
python manage.py
# Select option 7 to clean checkpoints
```

## 🐛 Troubleshooting

### Common Issues

**"No PDF files found"**
- Ensure PDFs are in `data/arxiv_pdfs/`
- Check file size is under 50MB limit

**"spaCy model not found"**
```bash
python -m spacy download en_core_web_sm
```

**"Memory error during processing"**
- Reduce `chunk_size` in config.py
- Process fewer PDFs at once
- Close other memory-intensive applications

**"Permission denied" errors**
- Run as administrator on Windows
- Check file permissions in data directories

### Getting Help

1. Check logs in `data/logs/` for detailed error information
2. Run `python manage.py setup` to verify configuration
3. Ensure all dependencies are installed: `pip install -r requirements.txt`

## 🔮 What's Next

Phase 1 prepares the foundation for:

**Phase 2**: Local LLM integration with Ollama
- Generate definitions for extracted words
- Batch processing with rate limiting
- Quality control and validation

**Phase 3**: Redis caching system
- Store word-definition pairs
- Fast lookup for extension
- Cache management and updates

**Phase 4**: Backend integration
- Modify extension backend to use cache
- Fallback to external APIs for cache misses
- Performance monitoring

## 📈 Performance Tips

1. **PDF Selection**: Use high-quality academic PDFs for best results
2. **Batch Size**: Process 10-50 PDFs at once for optimal performance
3. **Hardware**: More RAM = faster NLP processing
4. **Storage**: Ensure sufficient disk space (text files can be large)

## 🔒 Privacy & Security

- All processing is done locally
- No data sent to external servers
- PDF content remains on your machine
- Generated word lists can be shared safely (no original content)

---

**Ready to start?** Run `python manage.py` and select option 1 to check your setup!
