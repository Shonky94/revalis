"""
ContextSnap Management Script
Easy-to-use interface for running all processing scripts with resume capability
"""

import sys
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from config import (
    ARXIV_PDFS_DIR, PROCESSED_DIR, WORD_LISTS_DIR, DEFINITIONS_DIR,
    validate_config
)


class ContextSnapManager:
    """Main management interface for ContextSnap processing pipeline"""
    
    def __init__(self):

        self.scripts_dir = Path(__file__).parent
    
    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed"""
        required_packages = [
            ("PyPDF2", "PyPDF2"),
            ("pdfplumber", "pdfplumber"),
            ("spacy", "spacy"),
        ]
        
        missing_packages = []
        
        for package_name, import_name in required_packages:
            try:
                __import__(import_name)
                print(f"✓ {package_name} is installed")
            except ImportError:
                missing_packages.append(package_name)
                print(f"✗ {package_name} is missing")
        
        # Check spaCy model specifically
        try:
            import spacy
            spacy.load("en_core_web_sm")
            print("✓ spaCy English model is installed")
        except (ImportError, OSError):
            missing_packages.append("en_core_web_sm")
            print("✗ spaCy English model is missing")
        
        if missing_packages:
            print(f"\nMissing packages: {', '.join(missing_packages)}")
            print("Run the following commands to install:")
            print("pip install -r requirements.txt")
            print("python -m spacy download en_core_web_sm")
            return False
        
        return True
    
    def check_setup(self) -> Dict[str, bool]:
        """Check system setup and readiness"""
        status = {
            "config_valid": True,
            "dependencies": True,
            "directories": True,
            "pdf_files": False,
            "processed_files": False,
            "word_lists": False
        }
        
        # Check configuration
        config_errors = validate_config()
        if config_errors:
            print("Configuration errors:")
            for error in config_errors:
                print(f"  - {error}")
            status["config_valid"] = False
        
        # Check dependencies
        status["dependencies"] = self.check_dependencies()
        
        # Check for PDF files
        pdf_files = list(ARXIV_PDFS_DIR.glob("*.pdf"))
        status["pdf_files"] = len(pdf_files) > 0
        print(f"PDF files found: {len(pdf_files)}")
        
        # Check for processed files
        text_files = list(PROCESSED_DIR.glob("text_*.txt"))
        status["processed_files"] = len(text_files) > 0
        print(f"Processed text files: {len(text_files)}")
        
        # Check for word lists
        word_files = list(WORD_LISTS_DIR.glob("word_list_*.json"))
        status["word_lists"] = len(word_files) > 0
        print(f"Word list files: {len(word_files)}")
        
        return status
    
    def install_dependencies(self) -> bool:
        """Install required dependencies"""
        requirements_file = self.scripts_dir / "requirements.txt"
        
        if not requirements_file.exists():
            print(f"Requirements file not found: {requirements_file}")
            return False
        
        print("Installing Python packages...")
        try:
            subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)
            ], check=True)
            
            print("Installing spaCy English model...")
            subprocess.run([
                sys.executable, "-m", "spacy", "download", "en_core_web_sm"
            ], check=True)
            
            print("✓ Dependencies installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to install dependencies: {e}")
            return False
    
    def run_script(self, script_name: str, resume: bool = True) -> bool:
        """Run a specific script with error handling"""
        script_path = self.scripts_dir / f"{script_name}.py"
        
        if not script_path.exists():
            print(f"Script not found: {script_path}")
            return False
        
        print(f"\n{'='*50}")
        print(f"Running: {script_name}")
        print(f"{'='*50}")
        
        try:
            # Run the script
            result = subprocess.run([
                sys.executable, str(script_path)
            ], capture_output=False, text=True)
            
            if result.returncode == 0:
                print(f"✓ {script_name} completed successfully")
                return True
            else:
                print(f"✗ {script_name} failed with return code {result.returncode}")
                return False
                
        except KeyboardInterrupt:
            print(f"\n{script_name} interrupted by user")
            return False
        except Exception as e:
            print(f"✗ Error running {script_name}: {e}")
            return False
    
    def run_phase_1(self) -> bool:
        """Run complete Phase 1: PDF processing and NLP"""
        print("\n🚀 Starting Phase 1: PDF Processing & NLP")
        print("This will extract text from PDFs and identify technical terms.")
        
        # Check setup
        status = self.check_setup()
        
        if not status["config_valid"] or not status["dependencies"]:
            print("❌ Setup check failed. Please fix issues before continuing.")
            return False
        
        if not status["pdf_files"]:
            print("❌ No PDF files found in:", ARXIV_PDFS_DIR)
            print("Please add PDF files to process.")
            return False
        
        # Step 1: PDF Processing
        print("\n📄 Step 1: Processing PDF files...")
        if not self.run_script("pdf_processor"):
            print("❌ PDF processing failed")
            return False
        
        # Step 2: NLP Processing
        print("\n🧠 Step 2: Processing text with NLP...")
        if not self.run_script("nlp_processor"):
            print("❌ NLP processing failed")
            return False
        
        print("\n🎉 Phase 1 completed successfully!")
        print(f"📁 Processed files: {PROCESSED_DIR}")
        print(f"📝 Word lists: {WORD_LISTS_DIR}")
        
        return True
    
    def show_statistics(self) -> None:
        """Show current processing statistics"""
        print(f"\n📊 ContextSnap Processing Statistics")
        print(f"{'='*50}")
        
        # PDF files
        pdf_files = list(ARXIV_PDFS_DIR.glob("*.pdf"))
        print(f"PDF files available: {len(pdf_files)}")
        
        # Processed files
        text_files = list(PROCESSED_DIR.glob("text_*.txt"))
        print(f"Text files processed: {len(text_files)}")
        
        # Word lists
        word_files = list(WORD_LISTS_DIR.glob("word_list_*.json"))
        print(f"Word lists generated: {len(word_files)}")
        
        # Latest word list info
        if word_files:
            latest_word_file = max(word_files, key=lambda x: x.stat().st_mtime)
            try:
                from utils import load_json
                word_data = load_json(latest_word_file)
                print(f"Latest word list: {len(word_data)} unique words")
                
                # Show top words
                if word_data and len(word_data) > 0:
                    print("\nTop 5 technical terms:")
                    for i, word_info in enumerate(word_data[:5], 1):
                        word = word_info.get('word', 'N/A')
                        score = word_info.get('average_score', 0)
                        freq = word_info.get('total_frequency', 0)
                        print(f"  {i}. {word} (score: {score:.3f}, freq: {freq})")
                        
            except Exception as e:
                print(f"Error reading word list: {e}")
        
        print(f"{'='*50}")
    
    def clean_checkpoints(self) -> None:
        """Clean up checkpoint files"""
        checkpoints = list(PROCESSED_DIR.glob("checkpoint_*.json"))
        if checkpoints:
            response = input(f"Found {len(checkpoints)} checkpoint files. Delete them? (y/n): ")
            if response.lower().startswith('y'):
                for checkpoint in checkpoints:
                    checkpoint.unlink()
                print(f"Deleted {len(checkpoints)} checkpoint files")
        else:
            print("No checkpoint files found")
    
    def show_menu(self) -> None:
        """Show main menu"""
        print(f"\n🔬 ContextSnap Local LLM Manager")
        print(f"{'='*50}")
        print("1. Check system setup")
        print("2. Install dependencies")
        print("3. Run Phase 1 (PDF + NLP processing)")
        print("4. Run PDF processing only")
        print("5. Run NLP processing only")
        print("6. Run Phase 2 (Generate definitions)")
        print("7. Run Phase 3 (Setup Redis cache)")
        print("8. Start API server")
        print("9. Show processing statistics")
        print("10. Clean checkpoint files")
        print("11. Exit")
        print(f"{'='*50}")
    
    def run_interactive(self) -> None:
        """Run interactive menu"""
        while True:
            self.show_menu()
            
            try:
                choice = input("Select option (1-11): ").strip()
                
                if choice == "1":
                    self.check_setup()
                
                elif choice == "2":
                    self.install_dependencies()
                
                elif choice == "3":
                    self.run_phase_1()
                
                elif choice == "4":
                    self.run_script("pdf_processor")
                
                elif choice == "5":
                    self.run_script("nlp_processor")
                
                elif choice == "6":
                    self.run_script("definition_generator")
                
                elif choice == "7":
                    self.run_script("redis_cache")
                
                elif choice == "8":
                    self.run_script("start_system")
                
                elif choice == "9":
                    self.show_statistics()
                
                elif choice == "10":
                    self.clean_checkpoints()
                
                elif choice == "11":
                    print("👋 Goodbye!")
                    break
                
                else:
                    print("Invalid choice. Please select 1-11.")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")

def main():
    """Main entry point"""
    manager = ContextSnapManager()
    
    # If command line arguments provided, run non-interactively
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "setup":
            manager.check_setup()
        elif command == "install":
            manager.install_dependencies()
        elif command == "phase1":
            manager.run_phase_1()
        elif command == "pdf":
            manager.run_script("pdf_processor")
        elif command == "nlp":
            manager.run_script("nlp_processor")
        elif command == "stats":
            manager.show_statistics()
        else:
            print("Available commands: setup, install, phase1, pdf, nlp, stats")
    else:
        # Run interactive menu
        manager.run_interactive()

if __name__ == "__main__":
    main()
