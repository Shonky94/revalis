"""
PDF Text Extraction for ContextSnap
Extracts and preprocesses text from ArXiv PDFs with resume capability
"""

import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    import PyPDF2
    import pdfplumber
except ImportError:
    print("Required packages not installed. Please run:")
    print("pip install PyPDF2 pdfplumber")
    sys.exit(1)

from config import (
    ARXIV_PDFS_DIR, PROCESSED_DIR, PDF_CONFIG, 
    get_timestamp, get_checkpoint_file
)
from utils import (
    ProgressTracker, CheckpointManager,
    save_json, load_json, save_text_file, get_file_size_mb,
    validate_file_type
)

class PDFProcessor:
    """Extract text from PDF files with error handling and resume capability"""
    
    def __init__(self, resume: bool = True):
        self.resume = resume
        self.checkpoint_manager = CheckpointManager(
            get_checkpoint_file("pdf_processor"),
            interval=5  # Save checkpoint every 5 PDFs
        )
        
        # Statistics
        self.stats = {
            "total_pdfs": 0,
            "processed_pdfs": 0,
            "failed_pdfs": 0,
            "total_pages": 0,
            "total_characters": 0,
            "errors": []
        }
    
    def find_pdf_files(self) -> List[Path]:
        """Find all PDF files in the ArXiv directory"""
        pdf_files = []
        
        for pdf_path in ARXIV_PDFS_DIR.rglob("*.pdf"):
            if validate_file_type(pdf_path, ['.pdf']):
                size_mb = get_file_size_mb(pdf_path)
                if size_mb <= PDF_CONFIG["max_file_size_mb"]:
                    pdf_files.append(pdf_path)
                else:
                    print(f"Skipping large PDF: {pdf_path.name} ({size_mb:.1f}MB)")
        
        return pdf_files
    
    def extract_text_pypdf2(self, pdf_path: Path) -> Optional[str]:
        """Extract text using PyPDF2 (fallback method)"""
        try:
            text_content = []
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(reader.pages):
                    try:
                        text = page.extract_text()
                        if text.strip():
                            text_content.append(text)
                    except Exception as e:
                        pass
            
            return '\n'.join(text_content) if text_content else None
            
        except Exception as e:
            return None
    
    def extract_text_pdfplumber(self, pdf_path: Path) -> Optional[str]:
        """Extract text using pdfplumber (preferred method)"""
        try:
            text_content = []
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    try:
                        text = page.extract_text()
                        if text and text.strip():
                            text_content.append(text)
                        
                        # Update page count
                        self.stats["total_pages"] += 1
                        
                    except Exception as e:
                        pass
                
                return '\n'.join(text_content) if text_content else None
                
        except Exception as e:
            return None
    
    def extract_text_from_pdf(self, pdf_path: Path) -> Optional[str]:
        """Extract text from PDF using best available method"""
        
        # Try pdfplumber first (better accuracy)
        text = self.extract_text_pdfplumber(pdf_path)
        
        # Fallback to PyPDF2 if pdfplumber fails
        if not text:
            text = self.extract_text_pypdf2(pdf_path)
        
        if text:
            self.stats["total_characters"] += len(text)
            return text
        else:
            error_msg = f"Failed to extract text from {pdf_path.name}"
            self.stats["errors"].append(error_msg)
            return None
    
    def clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers/footers (common patterns)
        text = re.sub(r'\n\d+\n', '\n', text)
        text = re.sub(r'\nPage \d+\n', '\n', text)
        
        # Remove URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
        
        # Remove email addresses
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', text)
        
        # Remove excessive punctuation
        text = re.sub(r'[^\w\s\-.,;:()[\]{}]', ' ', text)
        
        # Clean up whitespace again
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_metadata(self, pdf_path: Path) -> Dict:
        """Extract metadata from PDF"""
        metadata = {
            "filename": pdf_path.name,
            "file_size_mb": get_file_size_mb(pdf_path),
            "processed_timestamp": get_timestamp(),
        }
        
        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                
                # Basic PDF info
                metadata["page_count"] = len(reader.pages)
                
                # Document info if available
                if reader.metadata:
                    doc_info = reader.metadata
                    metadata["title"] = str(doc_info.get("/Title", "")).strip()
                    metadata["author"] = str(doc_info.get("/Author", "")).strip()
                    metadata["subject"] = str(doc_info.get("/Subject", "")).strip()
                    metadata["creator"] = str(doc_info.get("/Creator", "")).strip()
                
        except Exception as e:
            pass
        
        return metadata
    
    def process_single_pdf(self, pdf_path: Path) -> Optional[Dict]:
        """Process a single PDF and return results"""
        try:
            # Extract text
            raw_text = self.extract_text_from_pdf(pdf_path)
            if not raw_text:
                return None
            
            # Clean text
            cleaned_text = self.clean_extracted_text(raw_text)
            if not cleaned_text:
                return None
            
            # Extract metadata
            metadata = self.extract_metadata(pdf_path)
            
            # Create result object
            result = {
                "metadata": metadata,
                "raw_text": raw_text[:1000] + "..." if len(raw_text) > 1000 else raw_text,  # Truncated for storage
                "cleaned_text": cleaned_text,
                "text_length": len(cleaned_text),
                "processing_status": "success"
            }
            
            self.stats["processed_pdfs"] += 1
            return result
            
        except Exception as e:
            error_msg = f"Failed to process {pdf_path.name}: {e}"
            self.stats["failed_pdfs"] += 1
            self.stats["errors"].append(error_msg)
            return None
    
    def process_all_pdfs(self) -> Dict:
        """Process all PDFs in the directory with resume capability"""
        pdf_files = self.find_pdf_files()
        if not pdf_files:
            return {"results": [], "stats": self.stats}
        
        self.stats["total_pdfs"] = len(pdf_files)
        
        # Load checkpoint if resuming
        checkpoint_data = {}
        processed_files = set()
        
        if self.resume:
            checkpoint_data = self.checkpoint_manager.load_checkpoint()
            processed_files = set(checkpoint_data.get("processed_files", []))
            
            # Restore statistics
            if "stats" in checkpoint_data:
                saved_stats = checkpoint_data["stats"]
                self.stats.update(saved_stats)
        
        # Filter out already processed files
        remaining_files = [f for f in pdf_files if str(f) not in processed_files]
        
        if processed_files:
            print(f"Resuming: {len(processed_files)} files already processed, "
                  f"{len(remaining_files)} remaining")
        
        # Process remaining files
        results = checkpoint_data.get("results", [])
        progress = ProgressTracker(len(remaining_files), "Processing PDFs")
        
        for pdf_path in remaining_files:
            result = self.process_single_pdf(pdf_path)
            
            if result:
                results.append(result)
                
                # Save full text to separate file for NLP processing
                text_file = PROCESSED_DIR / f"text_{pdf_path.stem}_{get_timestamp()}.txt"
                save_text_file(result["cleaned_text"], text_file)
                result["text_file"] = str(text_file)
            
            # Update checkpoint
            processed_files.add(str(pdf_path))
            self.checkpoint_manager.save_checkpoint({
                "processed_files": list(processed_files),
                "results": results,
                "stats": self.stats
            })
            
            progress.update()
        
        # Save final results
        output_file = PROCESSED_DIR / f"pdf_extraction_results_{get_timestamp()}.json"
        final_results = {
            "results": results,
            "stats": self.stats,
            "processing_completed": get_timestamp()
        }
        
        save_json(final_results, output_file)
        print(f"Results saved to {output_file}")
        
        # Cleanup checkpoint
        self.checkpoint_manager.cleanup()
        
        return final_results
    
    def print_summary(self, results: Dict) -> None:
        """Print processing summary"""
        stats = results["stats"]
        print(f"\n{'='*50}")
        print("PDF PROCESSING SUMMARY")
        print(f"{'='*50}")
        print(f"Total PDFs found: {stats['total_pdfs']}")
        print(f"Successfully processed: {stats['processed_pdfs']}")
        print(f"Failed: {stats['failed_pdfs']}")
        print(f"Total pages processed: {stats['total_pages']}")
        print(f"Total characters extracted: {stats['total_characters']:,}")
        
        if stats['errors']:
            print(f"\nErrors encountered: {len(stats['errors'])}")
            for error in stats['errors'][:5]:  # Show first 5 errors
                print(f"  - {error}")
            if len(stats['errors']) > 5:
                print(f"  ... and {len(stats['errors']) - 5} more")
        
        print(f"{'='*50}")

def main():
    """Main execution function"""
    print("ContextSnap PDF Processor")
    print("=" * 40)
    
    # Check if PDF directory exists and has files
    if not ARXIV_PDFS_DIR.exists():
        print(f"Error: PDF directory does not exist: {ARXIV_PDFS_DIR}")
        print("Please create the directory and add PDF files to process.")
        return
    
    pdf_files = list(ARXIV_PDFS_DIR.rglob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {ARXIV_PDFS_DIR}")
        print("Please add PDF files to the directory.")
        return
    
    print(f"Found {len(pdf_files)} PDF files")
    
    # Ask user if they want to resume or start fresh
    resume = True
    checkpoint_file = get_checkpoint_file("pdf_processor")
    if checkpoint_file.exists():
        response = input("Previous processing detected. Resume from checkpoint? (y/n): ").lower()
        resume = response.startswith('y')
        if not resume:
            checkpoint_file.unlink()  # Delete checkpoint
            print("Starting fresh processing...")
    
    # Initialize processor
    processor = PDFProcessor(resume=resume)
    
    try:
        # Process all PDFs
        results = processor.process_all_pdfs()
        
        # Print summary
        processor.print_summary(results)
        
        print(f"\nProcessed text files saved to: {PROCESSED_DIR}")
        
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user.")
        print("Progress has been saved. Run the script again to resume.")
    except Exception as e:
        print(f"Error during processing: {e}")
        print(f"Unexpected error occurred. Check the error details above.")

if __name__ == "__main__":
    main()
