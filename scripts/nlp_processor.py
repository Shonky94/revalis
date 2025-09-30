"""
NLP Word Extraction and Processing for ContextSnap
Extracts meaningful academic/technical terms from processed text with scoring
"""

import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import string

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

try:
    import spacy
    from spacy.lang.en.stop_words import STOP_WORDS
    from spacy.matcher import Matcher, PhraseMatcher
    from spacy.tokens import Span
except ImportError:
    print("spaCy not installed. Please run:")
    print("pip install spacy")
    print("python -m spacy download en_core_web_sm")
    sys.exit(1)

from config import (
    PROCESSED_DIR, WORD_LISTS_DIR, NLP_CONFIG, COMMON_WORDS,
    ACADEMIC_KEYWORDS, get_timestamp, get_checkpoint_file
)
from utils import (
    ProgressTracker, CheckpointManager,
    save_json, load_json, clean_word, is_technical_term,
    filter_academic_words, merge_word_lists
)

class NLPProcessor:
    """Extract and score academic/technical terms from text"""
    
    def __init__(self, resume: bool = True):
        self.resume = resume
        self.checkpoint_manager = CheckpointManager(
            get_checkpoint_file("nlp_processor"),
            interval=10  # Save checkpoint every 10 files
        )
        
        # Load spaCy model with ALL components for maximum accuracy
        try:
            self.nlp = spacy.load("en_core_web_sm")  # Enable all components including NER
            print("Loaded spaCy model with full pipeline (tokenizer, tagger, parser, NER)")
            
            # Initialize matchers for advanced pattern detection
            self.matcher = Matcher(self.nlp.vocab)
            self.phrase_matcher = PhraseMatcher(self.nlp.vocab, attr="LOWER")
            self._setup_advanced_patterns()
            
        except OSError:
            print("ERROR: spaCy model not found. Please install with:")
            print("python -m spacy download en_core_web_sm")
            raise
        
        # Combine stop words
        self.stop_words = STOP_WORDS.union(COMMON_WORDS)
        
        # Enhanced statistics
        self.stats = {
            "total_files": 0,
            "processed_files": 0,
            "total_words_extracted": 0,
            "single_words": 0,
            "compound_words": 0,
            "named_entities": 0,
            "noun_phrases": 0,
            "semantic_chunks": 0,
            "filtered_out_low_quality": 0,
            "unique_words": 0,
            "technical_words": 0,
            "errors": []
        }
    
    def find_text_files(self) -> List[Path]:
        """Find all processed text files"""
        text_files = []
        
        # Look for text files from PDF processing
        for text_file in PROCESSED_DIR.glob("text_*.txt"):
            text_files.append(text_file)
        
        print(f"Found {len(text_files)} text files to process")
        return text_files
    
    def _setup_advanced_patterns(self):
        """Setup advanced pattern matching for technical terms"""
        
        # Technical compound patterns
        technical_patterns = [
            # Algorithm patterns
            [{"LOWER": {"IN": ["machine", "deep", "reinforcement", "supervised", "unsupervised"]}}, 
             {"LOWER": "learning"}],
            [{"LOWER": {"IN": ["neural", "convolutional", "recurrent"]}}, 
             {"LOWER": {"IN": ["network", "networks"]}}],
            [{"LOWER": {"IN": ["gradient", "stochastic"]}}, 
             {"LOWER": "descent"}],
            
            # Data science patterns
            [{"LOWER": "data"}, {"LOWER": {"IN": ["mining", "analysis", "processing", "science", "engineering"]}}],
            [{"LOWER": {"IN": ["natural", "computational"]}}, 
             {"LOWER": "language"}, {"LOWER": "processing"}],
            [{"LOWER": {"IN": ["computer", "artificial"]}}, 
             {"LOWER": {"IN": ["vision", "intelligence"]}}],
            
            # Research methodology patterns
            [{"LOWER": {"IN": ["statistical", "experimental", "empirical"]}}, 
             {"LOWER": {"IN": ["analysis", "evaluation", "study", "method"]}}],
            [{"LOWER": {"IN": ["cross", "monte"]}}, 
             {"LOWER": {"IN": ["validation", "carlo"]}}],
            
            # Technical measurement patterns
            [{"LOWER": {"IN": ["precision", "recall", "f1"]}}, 
             {"LOWER": {"IN": ["score", "measure"]}}],
            [{"LOWER": {"IN": ["root", "mean"]}}, 
             {"LOWER": {"IN": ["square", "squared"]}}, {"LOWER": "error"}],
        ]
        
        # Add patterns to matcher
        for i, pattern in enumerate(technical_patterns):
            self.matcher.add(f"TECHNICAL_TERM_{i}", [pattern])
        
        # Academic discipline terms
        academic_phrases = [
            "machine learning", "deep learning", "neural network", "artificial intelligence",
            "computer vision", "natural language processing", "data mining", "big data",
            "reinforcement learning", "supervised learning", "unsupervised learning",
            "convolutional neural network", "recurrent neural network", "transformer model",
            "attention mechanism", "gradient descent", "backpropagation algorithm",
            "support vector machine", "random forest", "decision tree", "naive bayes",
            "k-means clustering", "principal component analysis", "linear regression",
            "logistic regression", "cross validation", "feature selection", "dimensionality reduction"
        ]
        
        # Convert to spaCy docs and add to phrase matcher
        academic_docs = [self.nlp(phrase) for phrase in academic_phrases]
        self.phrase_matcher.add("ACADEMIC_TERMS", academic_docs)
    
    def extract_named_entities(self, doc) -> List[Tuple[str, str, str, float]]:
        """Extract and score named entities relevant to academic text"""
        entities = []
        
        for ent in doc.ents:
            # Filter for relevant entity types
            relevant_labels = {
                "ORG",       # Organizations (universities, companies)
                "PRODUCT",   # Products (software, algorithms)  
                "EVENT",     # Events (conferences, workshops)
                "LAW",       # Laws, regulations, standards
                "LANGUAGE",  # Programming languages
                "WORK_OF_ART", # Publications, papers
                "FAC",       # Facilities (labs, institutions)
                "GPE",       # Geopolitical entities (countries for datasets)
                "NORP",      # Nationalities (for demographic studies)
            }
            
            if ent.label_ in relevant_labels:
                entity_text = ent.text.lower().strip()
                
                # Clean and validate entity
                if (len(entity_text) >= 3 and 
                    len(entity_text) <= 50 and 
                    not entity_text in self.stop_words):
                    
                    # Score entity based on relevance
                    score = self._score_named_entity(entity_text, ent.label_)
                    
                    if score >= 0.3:  # Only high-quality entities
                        entities.append((entity_text, "ENTITY", ent.label_, score))
        
        self.stats["named_entities"] += len(entities)
        return entities
    
    def _score_named_entity(self, entity_text: str, label: str) -> float:
        """Score named entity relevance for academic context"""
        score = 0.5  # Base score
        
        # Label-based scoring
        label_scores = {
            "ORG": 0.8,      # High value for organizations
            "PRODUCT": 0.7,  # Software, algorithms, tools
            "EVENT": 0.6,    # Conferences, workshops
            "LANGUAGE": 0.9, # Programming languages very relevant
            "LAW": 0.5,      # Standards, regulations
            "WORK_OF_ART": 0.6, # Papers, publications
        }
        
        score = label_scores.get(label, 0.4)
        
        # Content-based scoring
        academic_indicators = [
            "university", "institute", "lab", "research", "conference", "workshop",
            "python", "java", "tensorflow", "pytorch", "sklearn", "pandas",
            "ieee", "acm", "springer", "nature", "science", "arxiv",
            "algorithm", "framework", "library", "toolkit", "platform"
        ]
        
        for indicator in academic_indicators:
            if indicator in entity_text.lower():
                score += 0.2
                break
        
        return min(score, 1.0)
    
    def extract_noun_phrases(self, doc) -> List[Tuple[str, str, float]]:
        """Extract meaningful noun phrases using dependency parsing"""
        noun_phrases = []
        
        for chunk in doc.noun_chunks:
            # Clean and normalize chunk
            chunk_text = chunk.text.lower().strip()
            chunk_text = re.sub(r'\s+', ' ', chunk_text)
            
            # Filter noun phrases
            if (len(chunk_text) >= 6 and  # Minimum length
                len(chunk_text) <= 60 and  # Maximum length
                len(chunk_text.split()) >= 2 and  # Multi-word
                len(chunk_text.split()) <= 5 and  # Not too long
                not any(stop_word in chunk_text.split() for stop_word in self.stop_words[:50])):  # No common stop words
                
                # Score noun phrase
                score = self._score_noun_phrase(chunk_text, chunk)
                
                if score >= NLP_CONFIG["technical_score_threshold"]:
                    noun_phrases.append((chunk_text, "NOUN_PHRASE", score))
        
        self.stats["noun_phrases"] += len(noun_phrases)
        return noun_phrases
    
    def _score_noun_phrase(self, phrase_text: str, chunk) -> float:
        """Score noun phrase for technical relevance"""
        score = 0.3  # Base score
        
        # Length-based scoring (sweet spot for technical phrases)
        words = phrase_text.split()
        if 2 <= len(words) <= 3:
            score += 0.3
        elif len(words) == 4:
            score += 0.2
        
        # Technical word density
        technical_word_count = sum(1 for word in words if is_technical_term(word) >= 0.4)
        if technical_word_count >= len(words) * 0.5:  # At least 50% technical
            score += 0.4
        
        # POS pattern scoring (prefer noun-heavy phrases)
        pos_tags = [token.pos_ for token in chunk]
        noun_count = sum(1 for pos in pos_tags if pos in ["NOUN", "PROPN"])
        if noun_count >= len(pos_tags) * 0.6:  # At least 60% nouns
            score += 0.2
        
        # Academic field indicators
        for field_keywords in ACADEMIC_KEYWORDS.values():
            for keyword in field_keywords:
                if keyword in phrase_text:
                    score += 0.3
                    break
        
        return min(score, 1.0)
    
    def extract_semantic_chunks(self, doc) -> List[Tuple[str, str, float]]:
        """Extract semantic chunks using dependency parsing and pattern matching"""
        semantic_chunks = []
        
        # Use matcher to find technical patterns
        matches = self.matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            chunk_text = span.text.lower().strip()
            
            if (len(chunk_text) >= 5 and 
                len(chunk_text) <= 50 and
                chunk_text not in [item[0] for item in semantic_chunks]):  # Avoid duplicates
                
                score = 0.8  # High score for pattern-matched terms
                semantic_chunks.append((chunk_text, "SEMANTIC_CHUNK", score))
        
        # Use phrase matcher for academic terms
        phrase_matches = self.phrase_matcher(doc)
        for match_id, start, end in phrase_matches:
            span = doc[start:end]
            chunk_text = span.text.lower().strip()
            
            if chunk_text not in [item[0] for item in semantic_chunks]:  # Avoid duplicates
                score = 0.9  # Very high score for known academic terms
                semantic_chunks.append((chunk_text, "SEMANTIC_CHUNK", score))
        
        self.stats["semantic_chunks"] += len(semantic_chunks)
        return semantic_chunks
    
    def filter_compound_quality(self, compound_terms: List[str]) -> List[str]:
        """Filter out low-quality compound terms to reduce clutter"""
        filtered_terms = []
        
        # Quality filters
        useless_patterns = [
            r'^(the|a|an) ',           # Articles at start
            r' (the|a|an)$',           # Articles at end  
            r'^(and|or|but|so|yet) ',  # Conjunctions at start
            r' (and|or|but|so|yet)$',  # Conjunctions at end
            r'^(in|on|at|by|for|with|from|to) ', # Prepositions at start
            r' (in|on|at|by|for|with|from|to)$', # Prepositions at end
            r'^(this|that|these|those) ',        # Demonstratives
            r'^(some|many|few|several) ',        # Quantifiers
            r'\d+\s*(st|nd|rd|th|%)',           # Ordinals and percentages
            r'^[^\w\s-]+',                       # Starting with punctuation
            r'[^\w\s-]+$',                       # Ending with punctuation
        ]
        
        # Minimum quality requirements
        min_word_length = 3
        max_total_length = 40
        min_technical_words = 1
        
        for term in compound_terms:
            term_clean = term.strip().lower()
            
            # Skip if matches useless patterns
            if any(re.search(pattern, term_clean) for pattern in useless_patterns):
                self.stats["filtered_out_low_quality"] += 1
                continue
            
            # Skip if too short/long
            if len(term_clean) < 6 or len(term_clean) > max_total_length:
                self.stats["filtered_out_low_quality"] += 1
                continue
            
            # Check word quality
            words = term_clean.split()
            if len(words) < 2 or len(words) > 4:  # Reasonable compound length
                self.stats["filtered_out_low_quality"] += 1
                continue
            
            # Check if words are too short
            if any(len(word) < min_word_length for word in words):
                self.stats["filtered_out_low_quality"] += 1
                continue
            
            # Require at least one technical word
            technical_count = sum(1 for word in words if is_technical_term(word) >= 0.3)
            if technical_count < min_technical_words:
                self.stats["filtered_out_low_quality"] += 1
                continue
            
            # Check for meaningless combinations
            meaningless_combinations = [
                ["first", "second"], ["next", "previous"], ["left", "right"],
                ["up", "down"], ["before", "after"], ["start", "end"],
                ["begin", "finish"], ["old", "new"], ["big", "small"]
            ]
            
            if any(all(word in words for word in combo) for combo in meaningless_combinations):
                self.stats["filtered_out_low_quality"] += 1
                continue
            
            filtered_terms.append(term)
        
        return filtered_terms
    
    def extract_words_basic(self, text: str) -> List[str]:
        """Basic word extraction using regex (fallback method)"""
        # Remove punctuation and split on whitespace
        text = text.translate(str.maketrans('', '', string.punctuation))
        words = re.findall(r'\b[a-zA-Z]{3,25}\b', text.lower())
        
        # Filter out stop words and common words
        filtered_words = [word for word in words if word not in self.stop_words]
        
        return filtered_words
    
    def extract_words_spacy(self, text: str) -> Dict[str, List]:
        """Advanced word extraction using full spaCy pipeline with NER and semantic analysis"""
        extraction_results = {
            "single_words": [],
            "compound_terms": [],
            "named_entities": [],
            "noun_phrases": [],
            "semantic_chunks": []
        }
        
        try:
            # Process text in chunks for memory efficiency but larger chunks for better context
            max_length = 500000  # 500KB chunks for better linguistic context
            
            if len(text) > max_length:
                chunks = [text[i:i+max_length] for i in range(0, len(text), max_length)]
            else:
                chunks = [text]
            
            for chunk in chunks:
                doc = self.nlp(chunk)
                
                # 1. Extract single words with enhanced filtering
                for token in doc:
                    if (token.is_alpha and 
                        not token.is_stop and 
                        not token.is_punct and 
                        not token.is_space and
                        len(token.text) >= NLP_CONFIG["min_chars"] and
                        len(token.text) <= NLP_CONFIG["max_chars"] and
                        token.pos_ not in NLP_CONFIG["excluded_pos_tags"]):
                        
                        word = token.lemma_.lower()
                        if (word not in self.stop_words and 
                            not word.isdigit() and 
                            len(set(word)) > 1):  # Avoid repeated characters like "aaa"
                            extraction_results["single_words"].append((word, token.pos_, token.text))
                
                # 2. Extract named entities
                entities = self.extract_named_entities(doc)
                extraction_results["named_entities"].extend(entities)
                
                # 3. Extract noun phrases
                noun_phrases = self.extract_noun_phrases(doc)
                extraction_results["noun_phrases"].extend(noun_phrases)
                
                # 4. Extract semantic chunks
                semantic_chunks = self.extract_semantic_chunks(doc)
                extraction_results["semantic_chunks"].extend(semantic_chunks)
            
            # 5. Extract compound terms with quality filtering
            compound_terms_raw = self.extract_compound_terms(text)
            compound_terms_filtered = self.filter_compound_quality(compound_terms_raw)
            extraction_results["compound_terms"] = compound_terms_filtered
            
            return extraction_results
            
        except Exception as e:
            print(f"Advanced spaCy processing failed, using fallback: {e}")
            # Fallback to basic extraction
            basic_words = self.extract_words_basic(text)
            return {
                "single_words": [(word, "UNKNOWN", word) for word in basic_words],
                "compound_terms": [],
                "named_entities": [],
                "noun_phrases": [],
                "semantic_chunks": []
            }
    
    def score_word_importance(self, word: str, pos_tag: str, frequency: int, 
                            total_words: int, context: str = "") -> float:
        """Score word importance for academic/technical content"""
        base_score = is_technical_term(word, context)
        
        # Frequency-based adjustment (not too common, not too rare)
        freq_ratio = frequency / total_words
        if 0.001 <= freq_ratio <= 0.01:  # Sweet spot for meaningful terms
            base_score += 0.2
        elif freq_ratio < 0.001:
            base_score += 0.1  # Rare terms might be very specific
        elif freq_ratio > 0.05:
            base_score -= 0.3  # Very common terms less interesting
        
        # POS tag based scoring
        valuable_pos = ["NOUN", "ADJ", "VERB"]  # Nouns, adjectives, verbs
        if pos_tag in valuable_pos:
            base_score += 0.15
        
        # Length-based scoring refinement
        if 6 <= len(word) <= 12:
            base_score += 0.1
        elif len(word) > 15:
            base_score += 0.2  # Very long words often technical
        
        # Academic field detection
        word_lower = word.lower()
        for field, keywords in ACADEMIC_KEYWORDS.items():
            for keyword in keywords:
                if keyword in word_lower or word_lower in keyword:
                    base_score += 0.25
                    break
        
        return min(base_score, 1.0)
    
    def extract_compound_terms(self, text: str) -> List[str]:
        """Extract multi-word technical terms (e.g., 'machine learning', 'neural network')"""
        compound_terms = []
        
        # Common patterns for compound terms
        patterns = [
            r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # Title Case combinations
            r'\b[a-z]+-[a-z]+\b',             # Hyphenated terms
            r'\b[a-z]+ [a-z]+ing\b',          # algo + processing patterns
            r'\b[a-z]+ (analysis|method|algorithm|network|system|model)\b',  # Technical endings
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                clean_match = re.sub(r'[^\w\s-]', '', match).strip().lower()
                if (len(clean_match) >= 6 and 
                    len(clean_match.split()) <= 3 and
                    not any(stop_word in clean_match.split() for stop_word in self.stop_words)):
                    compound_terms.append(clean_match)
        
        return compound_terms
    
    def process_single_file(self, text_file: Path) -> Optional[Dict]:
        """Process a single text file and extract words"""
        try:

            
            # Read text content
            with open(text_file, 'r', encoding='utf-8') as f:
                text = f.read()
            
            if not text.strip():

                return None
            
            # Extract all types of terms with advanced spaCy processing
            extraction_results = self.extract_words_spacy(text)
            
            # Count frequencies for all term types
            single_word_counts = Counter([word for word, pos, original in extraction_results["single_words"]])
            compound_counts = Counter(extraction_results["compound_terms"])
            entity_counts = Counter([entity for entity, etype, label, score in extraction_results["named_entities"]])
            noun_phrase_counts = Counter([phrase for phrase, ptype, score in extraction_results["noun_phrases"]])
            semantic_counts = Counter([chunk for chunk, ctype, score in extraction_results["semantic_chunks"]])
            
            total_words = len(extraction_results["single_words"])
            
            # Score and rank all terms
            scored_words = []
            
            # 1. Process single words
            for word, count in single_word_counts.items():
                if count >= NLP_CONFIG["min_frequency"]:
                    # Find POS tag for this word
                    pos_tag = next((pos for w, pos, orig in extraction_results["single_words"] if w == word), "UNKNOWN")
                    
                    score = self.score_word_importance(word, pos_tag, count, total_words, text[:1000])
                    
                    if score >= NLP_CONFIG["technical_score_threshold"]:
                        scored_words.append({
                            "word": word,
                            "type": "single",
                            "frequency": count,
                            "pos_tag": pos_tag,
                            "score": score,
                            "extraction_method": "spacy_token"
                        })
            
            # 2. Process compound terms
            for term, count in compound_counts.items():
                if count >= max(1, NLP_CONFIG["min_frequency"] // 2):  # Lower threshold for compounds
                    score = self.score_word_importance(term, "COMPOUND", count, total_words, text[:1000])
                    
                    if score >= NLP_CONFIG["technical_score_threshold"]:
                        scored_words.append({
                            "word": term,
                            "type": "compound",
                            "frequency": count,
                            "pos_tag": "COMPOUND",
                            "score": score,
                            "extraction_method": "pattern_matching"
                        })
            
            # 3. Process named entities
            for entity, count in entity_counts.items():
                if count >= 1:  # Lower threshold for entities (they're usually important)
                    # Get entity details
                    entity_data = next((item for item in extraction_results["named_entities"] if item[0] == entity), None)
                    if entity_data:
                        _, etype, label, base_score = entity_data
                        
                        # Boost score based on frequency
                        score = min(1.0, base_score + (count - 1) * 0.1)
                        
                        scored_words.append({
                            "word": entity,
                            "type": "named_entity",
                            "frequency": count,
                            "pos_tag": f"ENTITY_{label}",
                            "score": score,
                            "extraction_method": "named_entity_recognition"
                        })
            
            # 4. Process noun phrases
            for phrase, count in noun_phrase_counts.items():
                if count >= 1:  # Lower threshold for noun phrases
                    # Get phrase details
                    phrase_data = next((item for item in extraction_results["noun_phrases"] if item[0] == phrase), None)
                    if phrase_data:
                        _, ptype, base_score = phrase_data
                        
                        # Boost score based on frequency
                        score = min(1.0, base_score + (count - 1) * 0.05)
                        
                        scored_words.append({
                            "word": phrase,
                            "type": "noun_phrase",
                            "frequency": count,
                            "pos_tag": "NOUN_PHRASE",
                            "score": score,
                            "extraction_method": "dependency_parsing"
                        })
            
            # 5. Process semantic chunks
            for chunk, count in semantic_counts.items():
                if count >= 1:  # All semantic chunks are valuable
                    # Get chunk details
                    chunk_data = next((item for item in extraction_results["semantic_chunks"] if item[0] == chunk), None)
                    if chunk_data:
                        _, ctype, base_score = chunk_data
                        
                        # Boost score based on frequency
                        score = min(1.0, base_score + (count - 1) * 0.1)
                        
                        scored_words.append({
                            "word": chunk,
                            "type": "semantic_chunk",
                            "frequency": count,
                            "pos_tag": "SEMANTIC",
                            "score": score,
                            "extraction_method": "pattern_semantic_matching"
                        })
            
            # Sort by score and limit results (increased limit for comprehensive extraction)
            scored_words.sort(key=lambda x: x["score"], reverse=True)
            scored_words = scored_words[:NLP_CONFIG["max_words_per_pdf"] * 2]  # Double the limit for comprehensive results
            
            # Update detailed statistics
            self.stats["total_words_extracted"] += total_words
            self.stats["single_words"] += len([w for w in scored_words if w["type"] == "single"])
            self.stats["compound_words"] += len([w for w in scored_words if w["type"] == "compound"])
            self.stats["named_entities"] += len([w for w in scored_words if w["type"] == "named_entity"])
            self.stats["noun_phrases"] += len([w for w in scored_words if w["type"] == "noun_phrase"])
            self.stats["semantic_chunks"] += len([w for w in scored_words if w["type"] == "semantic_chunk"])
            self.stats["processed_files"] += 1
            
            result = {
                "source_file": str(text_file),
                "text_length": len(text),
                "total_words_found": total_words,
                "unique_single_words": len(single_word_counts),
                "unique_compound_terms": len(compound_counts),
                "unique_entities": len(entity_counts),
                "unique_noun_phrases": len(noun_phrase_counts),
                "unique_semantic_chunks": len(semantic_counts),
                "scored_words": scored_words,
                "extraction_summary": {
                    "single_words": len(extraction_results["single_words"]),
                    "compound_terms": len(extraction_results["compound_terms"]),
                    "named_entities": len(extraction_results["named_entities"]),
                    "noun_phrases": len(extraction_results["noun_phrases"]),
                    "semantic_chunks": len(extraction_results["semantic_chunks"]),
                    "filtered_low_quality": self.stats["filtered_out_low_quality"]
                },
                "processing_timestamp": get_timestamp()
            }
            
            return result
            
        except Exception as e:
            error_msg = f"Failed to process {text_file.name}: {e}"
            print(error_msg)
            self.stats["errors"].append(error_msg)
            return None
    
    def process_all_files(self) -> Dict:
        """Process all text files with resume capability"""
        text_files = self.find_text_files()
        if not text_files:
            print("No text files found to process")
            return {"results": [], "stats": self.stats}
        
        self.stats["total_files"] = len(text_files)
        
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
        remaining_files = [f for f in text_files if str(f) not in processed_files]
        
        if processed_files:
            print(f"Resuming: {len(processed_files)} files already processed, "
                  f"{len(remaining_files)} remaining")
        
        # Process remaining files
        results = checkpoint_data.get("results", [])
        progress = ProgressTracker(len(remaining_files), "Processing Text Files")
        
        for text_file in remaining_files:
            result = self.process_single_file(text_file)
            
            if result:
                results.append(result)
            
            # Update checkpoint
            processed_files.add(str(text_file))
            self.checkpoint_manager.save_checkpoint({
                "processed_files": list(processed_files),
                "results": results,
                "stats": self.stats
            })
            
            progress.update()
        
        # Combine and deduplicate all words
        all_words = self.combine_all_words(results)
        
        # Save results
        output_file = WORD_LISTS_DIR / f"nlp_results_{get_timestamp()}.json"
        word_list_file = WORD_LISTS_DIR / f"word_list_{get_timestamp()}.json"
        
        final_results = {
            "individual_results": results,
            "combined_words": all_words,
            "stats": self.stats,
            "processing_completed": get_timestamp()
        }
        
        save_json(final_results, output_file)
        save_json(all_words, word_list_file)
        
        print(f"Results saved to {output_file}")
        print(f"Word list saved to {word_list_file}")
        
        # Update final statistics
        self.stats["unique_words"] = len(all_words)
        self.stats["technical_words"] = len([w for w in all_words if w["average_score"] >= 0.5])
        
        # Cleanup checkpoint
        self.checkpoint_manager.cleanup()
        
        return final_results
    
    def combine_all_words(self, results: List[Dict]) -> List[Dict]:
        """Combine words from all files, merging frequencies and scores with enhanced term type tracking"""
        word_data = defaultdict(lambda: {
            "total_frequency": 0,
            "files_count": 0,
            "scores": [],
            "pos_tags": set(),
            "type": "single",
            "extraction_methods": set(),
            "type_priority": 0  # Higher priority for better extraction methods
        })
        
        # Define type priority (higher = better)
        type_priorities = {
            "semantic_chunk": 5,
            "named_entity": 4,
            "noun_phrase": 3,
            "compound": 2,
            "single": 1
        }
        
        # Aggregate data from all files with enhanced type tracking
        for result in results:
            for word_info in result.get("scored_words", []):
                word = word_info["word"]
                current_type = word_info["type"]
                extraction_method = word_info.get("extraction_method", "unknown")
                
                word_data[word]["total_frequency"] += word_info["frequency"]
                word_data[word]["files_count"] += 1
                word_data[word]["scores"].append(word_info["score"])
                word_data[word]["pos_tags"].add(word_info["pos_tag"])
                word_data[word]["extraction_methods"].add(extraction_method)
                
                # Update type based on priority (keep the highest priority type)
                current_priority = type_priorities.get(current_type, 0)
                if current_priority > word_data[word]["type_priority"]:
                    word_data[word]["type"] = current_type
                    word_data[word]["type_priority"] = current_priority
        
        # Create final word list with enhanced metadata
        combined_words = []
        for word, data in word_data.items():
            # Calculate average score
            avg_score = sum(data["scores"]) / len(data["scores"])
            
            # Enhanced score boosting based on multiple factors
            boost_factors = 1.0
            
            # Multi-file appearance boost
            if data["files_count"] > 1:
                boost_factors *= (1 + 0.15 * min(data["files_count"] - 1, 4))  # Cap boost at 4 additional files
            
            # Extraction method quality boost
            method_quality_boost = {
                "pattern_semantic_matching": 1.2,
                "named_entity_recognition": 1.15,
                "dependency_parsing": 1.1,
                "pattern_matching": 1.05,
                "spacy_token": 1.0
            }
            
            best_method_boost = max([method_quality_boost.get(method, 1.0) 
                                   for method in data["extraction_methods"]])
            boost_factors *= best_method_boost
            
            # Type priority boost
            type_boost = {
                "semantic_chunk": 1.3,
                "named_entity": 1.25,
                "noun_phrase": 1.15,
                "compound": 1.1,
                "single": 1.0
            }
            boost_factors *= type_boost.get(data["type"], 1.0)
            
            final_score = min(1.0, avg_score * boost_factors)
            
            combined_words.append({
                "word": word,
                "type": data["type"],
                "total_frequency": data["total_frequency"],
                "files_count": data["files_count"],
                "average_score": final_score,
                "pos_tags": list(data["pos_tags"]),
                "extraction_methods": list(data["extraction_methods"]),
                "priority": final_score * (1 + 0.3 * min(data["files_count"], 5)),  # Enhanced composite priority
                "quality_indicators": {
                    "multi_file": data["files_count"] > 1,
                    "high_frequency": data["total_frequency"] >= 5,
                    "advanced_extraction": any(method in ["pattern_semantic_matching", "named_entity_recognition"] 
                                              for method in data["extraction_methods"]),
                    "compound_or_better": data["type"] in ["compound", "noun_phrase", "named_entity", "semantic_chunk"]
                }
            })
        
        # Sort by priority score
        combined_words.sort(key=lambda x: x["priority"], reverse=True)
        
        return combined_words
    
    def print_summary(self, results: Dict) -> None:
        """Print comprehensive processing summary with detailed statistics"""
        stats = results["stats"]
        combined_words = results.get("combined_words", [])
        
        print(f"\n{'='*60}")
        print("ENHANCED NLP PROCESSING SUMMARY")
        print(f"{'='*60}")
        
        # File processing stats
        print(f"📁 Files processed: {stats['processed_files']}")
        print(f"📝 Total words extracted: {stats['total_words_extracted']:,}")
        
        # Detailed extraction breakdown
        print(f"\n🔍 EXTRACTION BREAKDOWN:")
        print(f"   Single words: {stats['single_words']:,}")
        print(f"   Compound terms: {stats['compound_words']:,}")
        print(f"   Named entities: {stats['named_entities']:,}")
        print(f"   Noun phrases: {stats['noun_phrases']:,}")
        print(f"   Semantic chunks: {stats['semantic_chunks']:,}")
        print(f"   Filtered low-quality: {stats['filtered_out_low_quality']:,}")
        
        # Quality metrics
        total_extracted = stats['single_words'] + stats['compound_words'] + stats['named_entities'] + stats['noun_phrases'] + stats['semantic_chunks']
        print(f"\n📊 QUALITY METRICS:")
        print(f"   Total unique terms: {stats['unique_words']:,}")
        print(f"   High-value terms (score ≥ 0.5): {stats['technical_words']:,}")
        print(f"   Quality retention rate: {((total_extracted - stats['filtered_out_low_quality']) / max(1, total_extracted)) * 100:.1f}%")
        
        # Term type distribution
        if total_extracted > 0:
            print(f"\n📈 TERM TYPE DISTRIBUTION:")
            print(f"   Single words: {(stats['single_words'] / total_extracted) * 100:.1f}%")
            print(f"   Compound terms: {(stats['compound_words'] / total_extracted) * 100:.1f}%")
            print(f"   Named entities: {(stats['named_entities'] / total_extracted) * 100:.1f}%")
            print(f"   Noun phrases: {(stats['noun_phrases'] / total_extracted) * 100:.1f}%")
            print(f"   Semantic chunks: {(stats['semantic_chunks'] / total_extracted) * 100:.1f}%")
        
        # Top terms by category
        if combined_words:
            print(f"\n🏆 TOP TERMS BY PRIORITY:")
            
            # Group by type for better analysis
            by_type = {}
            for word_info in combined_words[:50]:  # Top 50 for analysis
                word_type = word_info.get('type', 'unknown')
                if word_type not in by_type:
                    by_type[word_type] = []
                by_type[word_type].append(word_info)
            
            for term_type, terms in by_type.items():
                if terms:
                    print(f"\n   📌 {term_type.replace('_', ' ').title()} (Top 3):")
                    for i, word_info in enumerate(terms[:3], 1):
                        method = word_info.get('extraction_method', 'unknown')
                        print(f"      {i}. {word_info['word']} "
                              f"(score: {word_info['average_score']:.3f}, "
                              f"freq: {word_info['total_frequency']}, "
                              f"method: {method})")
        
        # Error reporting
        if stats['errors']:
            print(f"\n⚠️  ERRORS ENCOUNTERED: {len(stats['errors'])}")
            for error in stats['errors'][:3]:
                print(f"   - {error}")
            if len(stats['errors']) > 3:
                print(f"   ... and {len(stats['errors']) - 3} more errors")
        
        print(f"\n{'='*60}")
        print("✅ Enhanced NLP processing completed successfully!")
        print("🎯 Maximum accuracy mode with NER, semantic chunking, and quality filtering")
        print(f"{'='*60}")

def main():
    """Main execution function"""
    print("ContextSnap NLP Processor")
    print("=" * 40)
    
    # Check if processed directory exists and has files
    if not PROCESSED_DIR.exists():
        print(f"Error: Processed directory does not exist: {PROCESSED_DIR}")
        print("Please run pdf_processor.py first.")
        return
    
    text_files = list(PROCESSED_DIR.glob("text_*.txt"))
    if not text_files:
        print(f"No processed text files found in {PROCESSED_DIR}")
        print("Please run pdf_processor.py first.")
        return
    
    print(f"Found {len(text_files)} text files")
    
    # Ask user if they want to resume or start fresh
    resume = True
    checkpoint_file = get_checkpoint_file("nlp_processor")
    if checkpoint_file.exists():
        response = input("Previous processing detected. Resume from checkpoint? (y/n): ").lower()
        resume = response.startswith('y')
        if not resume:
            checkpoint_file.unlink()
            print("Starting fresh processing...")
    
    # Initialize processor
    processor = NLPProcessor(resume=resume)
    
    try:
        # Process all files
        results = processor.process_all_files()
        
        # Print summary
        processor.print_summary(results)
        
        print(f"\nWord lists saved to: {WORD_LISTS_DIR}")
        
    except KeyboardInterrupt:
        print("\nProcessing interrupted by user.")
        print("Progress has been saved. Run the script again to resume.")
    except Exception as e:
        print(f"Error during processing: {e}")
        print(f"Unexpected error occurred. Check the error details above.")

if __name__ == "__main__":
    main()
