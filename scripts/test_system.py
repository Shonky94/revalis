"""
ContextSnap System Validation Script
Test all components to ensure proper installation and setup
"""

import sys
import tempfile
from pathlib import Path
from typing import Dict, List

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

def test_imports() -> Dict[str, bool]:
    """Test all required imports"""
    results = {}
    
    # Core modules
    modules_to_test = [
        ("config", "Configuration module"),
        ("utils", "Utilities module"),
    ]
    
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            results[description] = True
            print(f"✓ {description}")
        except ImportError as e:
            results[description] = False
            print(f"✗ {description}: {e}")
    
    return results

def test_dependencies() -> Dict[str, bool]:
    """Test external dependencies"""
    results = {}
    
    # Required packages
    dependencies = [
        ("PyPDF2", "PDF processing"),
        ("pdfplumber", "Advanced PDF processing"),
        ("spacy", "NLP processing"),
    ]
    
    for package, description in dependencies:
        try:
            __import__(package)
            results[description] = True
            print(f"✓ {description} ({package})")
        except ImportError:
            results[description] = False
            print(f"✗ {description} ({package}) - Not installed")
    
    # Test spaCy model
    try:
        import spacy
        nlp = spacy.load("en_core_web_sm")
        results["spaCy English model"] = True
        print("✓ spaCy English model")
    except (ImportError, OSError):
        results["spaCy English model"] = False
        print("✗ spaCy English model - Not installed")
    
    return results

def test_configuration() -> Dict[str, bool]:
    """Test configuration validation"""
    results = {}
    
    try:
        from config import validate_config
        errors = validate_config()
        
        if not errors:
            results["Configuration validation"] = True
            print("✓ Configuration is valid")
        else:
            results["Configuration validation"] = False
            print("✗ Configuration errors:")
            for error in errors:
                print(f"    - {error}")
    
    except Exception as e:
        results["Configuration validation"] = False
        print(f"✗ Configuration test failed: {e}")
    
    return results

def test_utilities() -> Dict[str, bool]:
    """Test utility functions"""
    results = {}
    
    try:
        from utils import (
            clean_word, is_technical_term, ProgressTracker,
            save_json, load_json
        )
        
        # Test word cleaning
        test_word = clean_word("Test-Word123!")
        if test_word == "testword":
            results["Word cleaning"] = True
            print("✓ Word cleaning function")
        else:
            results["Word cleaning"] = False
            print(f"✗ Word cleaning failed: expected 'testword', got '{test_word}'")
        
        # Test technical scoring
        score = is_technical_term("algorithm")
        if 0 <= score <= 1:
            results["Technical scoring"] = True
            print("✓ Technical term scoring")
        else:
            results["Technical scoring"] = False
            print(f"✗ Technical scoring failed: invalid score {score}")
        
        # Test progress tracker
        tracker = ProgressTracker(10, "Test")
        tracker.update(5)
        results["Progress tracking"] = True
        print("✓ Progress tracking")
        
        # Test JSON operations
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_file = Path(f.name)
        
        test_data = {"test": "data", "number": 42}
        save_json(test_data, test_file)
        loaded_data = load_json(test_file)
        
        if loaded_data == test_data:
            results["JSON operations"] = True
            print("✓ JSON save/load operations")
        else:
            results["JSON operations"] = False
            print("✗ JSON operations failed")
        
        # Cleanup
        test_file.unlink()
    
    except Exception as e:
        results["Utility functions"] = False
        print(f"✗ Utility test failed: {e}")
    
    return results

def test_pdf_processing() -> Dict[str, bool]:
    """Test PDF processing capabilities"""
    results = {}
    
    try:
        # Test imports
        import PyPDF2
        import pdfplumber
        
        # Test basic functionality without actual PDF
        from pdf_processor import PDFProcessor
        
        # Just test instantiation
        processor = PDFProcessor(resume=False)
        results["PDF processor initialization"] = True
        print("✓ PDF processor can be initialized")
        
    except Exception as e:
        results["PDF processor initialization"] = False
        print(f"✗ PDF processor test failed: {e}")
    
    return results

def test_nlp_processing() -> Dict[str, bool]:
    """Test NLP processing capabilities"""
    results = {}
    
    try:
        # Test spaCy loading
        import spacy
        nlp = spacy.load("en_core_web_sm", disable=["parser", "ner"])
        
        # Test basic NLP functionality
        test_text = "This is a test sentence with technical algorithms and neural networks."
        doc = nlp(test_text)
        
        words = [token.lemma_.lower() for token in doc if token.is_alpha]
        
        if len(words) > 0:
            results["Basic NLP processing"] = True
            print("✓ Basic NLP processing works")
        else:
            results["Basic NLP processing"] = False
            print("✗ NLP processing returned no words")
        
        # Test NLP processor class
        from nlp_processor import NLPProcessor
        processor = NLPProcessor(resume=False)
        results["NLP processor initialization"] = True
        print("✓ NLP processor can be initialized")
        
    except Exception as e:
        results["NLP processing"] = False
        print(f"✗ NLP processing test failed: {e}")
    
    return results

def test_directories() -> Dict[str, bool]:
    """Test directory structure"""
    results = {}
    
    try:
        from config import (
            ARXIV_PDFS_DIR, PROCESSED_DIR, WORD_LISTS_DIR,
            DEFINITIONS_DIR, LOGS_DIR
        )
        
        directories = [
            (ARXIV_PDFS_DIR, "ArXiv PDFs directory"),
            (PROCESSED_DIR, "Processed files directory"),
            (WORD_LISTS_DIR, "Word lists directory"),
            (DEFINITIONS_DIR, "Definitions directory"),
            (LOGS_DIR, "Logs directory"),
        ]
        
        all_good = True
        for directory, name in directories:
            if directory.exists():
                results[name] = True
                print(f"✓ {name}: {directory}")
            else:
                results[name] = False
                print(f"✗ {name}: {directory} (does not exist)")
                all_good = False
        
        results["Directory structure"] = all_good
        
    except Exception as e:
        results["Directory structure"] = False
        print(f"✗ Directory test failed: {e}")
    
    return results

def main():
    """Run all validation tests"""
    print("🔬 ContextSnap System Validation")
    print("=" * 50)
    
    all_results = {}
    
    # Run all tests
    test_functions = [
        (test_imports, "Core Modules"),
        (test_dependencies, "Dependencies"),
        (test_configuration, "Configuration"),
        (test_directories, "Directory Structure"),
        (test_utilities, "Utility Functions"),
        (test_pdf_processing, "PDF Processing"),
        (test_nlp_processing, "NLP Processing"),
    ]
    
    for test_func, category in test_functions:
        print(f"\n📋 Testing {category}...")
        print("-" * 30)
        
        category_results = test_func()
        all_results[category] = category_results
    
    # Print summary
    print(f"\n📊 Validation Summary")
    print("=" * 50)
    
    total_tests = 0
    passed_tests = 0
    
    for category, results in all_results.items():
        category_passed = sum(1 for success in results.values() if success)
        category_total = len(results)
        
        total_tests += category_total
        passed_tests += category_passed
        
        status = "✓" if category_passed == category_total else "✗"
        print(f"{status} {category}: {category_passed}/{category_total}")
        
        # Show failed tests
        if category_passed < category_total:
            failed = [name for name, success in results.items() if not success]
            print(f"    Failed: {', '.join(failed)}")
    
    print("-" * 50)
    success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0
    print(f"Overall: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
    
    if success_rate >= 90:
        print("\n🎉 System is ready for processing!")
    elif success_rate >= 70:
        print("\n⚠️  System mostly ready, but some issues need attention.")
    else:
        print("\n❌ System needs setup before processing.")
        print("Run 'python manage.py install' to install missing dependencies.")
    
    return success_rate >= 70

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
