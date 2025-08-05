import pandas as pd
import pymupdf  # PyMuPDF
import os
import sys
from pypdf import PdfWriter
import argparse
import glob
import re
import math
from rapidfuzz import fuzz, process  # pip install rapidfuzz

def clean_text(text):
    """Replace non-alphabetic characters with spaces and normalize whitespace"""
    if not isinstance(text, str):
        return ""
    # Replace non-alphabetic characters with spaces
    text = re.sub(r'[^a-zA-Z\s]', ' ', text)
    # Normalize whitespace (replace multiple spaces with single space)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def word_level_similarity(search_term, text):
    """
    Compare search term against each word in text and return highest similarity.
    
    Args:
        search_term (str): Single word to search for
        text (str): Text that may contain multiple words
        
    Returns:
        int: Highest similarity score (0-100)
    """
    if not isinstance(text, str) or not isinstance(search_term, str):
        return 0
    
    # Clean search term and text
    clean_search = clean_text(search_term).lower()
    clean_text_str = clean_text(text).lower()
    
    # Exact match gets 100
    if clean_search in clean_text_str.split():
        return 100
    
    # Split text into words
    words = clean_text_str.split()
    
    if not words:  # Empty text
        return 0
        
    # Calculate similarity for each word and return the maximum
    scores = [round(fuzz.ratio(clean_search, word)) for word in words]
    return max(scores) if scores else 0

def calculate_distance(x1, y1, x2, y2):
    """Calculate Euclidean distance between two points"""
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

def search_and_highlight(search_term, base_folder, output_directory='.', similarity_threshold=80, 
                         negation_terms=None, negation_distance=100):
    """
    Searches for a term in CSV files with text positions and creates a highlighted PDF.
    
    Parameters:
    search_term (str): Term to search for
    base_folder (str): Base folder where PDF files are stored
    output_directory (str): Directory where to save output files
    similarity_threshold (int): Minimum similarity score (0-100) to consider a match
    negation_terms (list): Terms that negate the search if found nearby
    negation_distance (float): Maximum distance to consider for negation
    """
    # Step 1: Get text position data
    try:
        df = pd.read_csv('big_text_with_position_may12.csv')
        print(f"Loaded {len(df)} text entries from CSV file")
    except FileNotFoundError:
        print("Error: big_text_with_position_may12.csv not found")
        return
    
    # Step 2: Perform fuzzy search
    print(f"Searching for '{search_term}' with similarity threshold {similarity_threshold}%...")
    if negation_terms and len(negation_terms) > 0:
        print(f"Will exclude results where any of these terms appears within {negation_distance} units: {', '.join(negation_terms)}")
    
    # First try exact substring search for efficiency
    exact_matches = df[df['text'].str.contains(search_term, case=False, na=False)].copy()
    print(f"Found {len(exact_matches)} exact matches")
    
    # Add similarity score of 100 for exact matches
    exact_matches['similarity'] = 100
    
    # For remaining entries, use fuzzy matching
    remaining_df = df.drop(exact_matches.index)
    print(f"Performing fuzzy matching on {len(remaining_df)} remaining entries...")
    
    # Apply fuzzy matching - this is computationally expensive for large datasets
    fuzzy_matches_chunks = []
    
    # Create chunks for processing to avoid memory issues
    chunk_size = 10000  # Adjust based on your system's memory
    total_chunks = (len(remaining_df) + chunk_size - 1) // chunk_size
    
    for i in range(0, len(remaining_df), chunk_size):
        chunk = remaining_df.iloc[i:i+chunk_size].copy()
        
        # Calculate word-level similarity scores for this chunk
        chunk['similarity'] = chunk['text'].apply(
            lambda x: word_level_similarity(search_term, x)
        )
        
        # Find matches above threshold
        chunk_matches = chunk[chunk['similarity'] >= similarity_threshold]
        fuzzy_matches_chunks.append(chunk_matches)
        
        print(f"Processed chunk {i//chunk_size + 1}/{total_chunks} - found {len(chunk_matches)} matches")
    
    # Combine all fuzzy matches from chunks
    fuzzy_matches = pd.concat(fuzzy_matches_chunks) if fuzzy_matches_chunks else pd.DataFrame()
    
    # Combine exact and fuzzy matches
    search_results = pd.concat([exact_matches, fuzzy_matches]).drop_duplicates()
    
    # Apply negation filtering if negation terms are provided
    if negation_terms and len(negation_terms) > 0 and len(search_results) > 0:
        print(f"Checking for negation terms near matches...")
        
        # Create a dictionary to track negation matches by term
        negation_matches_dict = {}
        total_negation_matches = 0
        
        # Find occurrences of each negation term
        for term in negation_terms:
            if 'text' in df.columns:
                # Use word boundaries to match whole words only
                # This pattern looks for the term as a whole word
                pattern = r'\b' + re.escape(term) + r'\b'
                term_matches = df[df['text'].str.contains(pattern, case=False, na=False, regex=True)].copy()
                negation_matches_dict[term] = term_matches
                total_negation_matches += len(term_matches)
                print(f"  - Found {len(term_matches)} occurrences of negation term '{term}'")
        
        if total_negation_matches > 0:
            print(f"Found {total_negation_matches} total occurrences of all negation terms")
            
            # For each search result, check if any negation term is nearby
            results_to_keep = []
            excluded_by_term = {term: 0 for term in negation_terms}
            
            for idx, row in search_results.iterrows():
                filename = row['filename']
                x1, y1 = row['bbx0'], row['bby0']
                
                # Check if any negation term is too close
                has_nearby_negation = False
                excluding_term = None
                min_distance = float('inf')
                
                # Process each negation term separately
                for term, term_matches in negation_matches_dict.items():
                    # Filter negation matches to the same file
                    file_negations = term_matches[term_matches['filename'] == filename]
                    
                    # Look at each negation instance
                    for neg_idx, neg_row in file_negations.iterrows():
                        x2, y2 = neg_row['bbx0'], neg_row['bby0']
                        distance = calculate_distance(x1, y1, x2, y2)
                        
                        # If this negation is close enough to exclude the match
                        if distance <= negation_distance and distance < min_distance:
                            has_nearby_negation = True
                            excluding_term = term
                            min_distance = distance
                            # Don't break here - we want to find the closest negation term
                
                # After checking all terms, record which term excluded this match
                if has_nearby_negation and excluding_term:
                    excluded_by_term[excluding_term] += 1
                    # Optionally add detailed logging about which term excluded the match
                    # print(f"Excluding match '{row['text']}' in {filename} due to nearby negation term '{excluding_term}' (distance: {min_distance:.2f})")
                else:
                    results_to_keep.append(idx)
            
            # Keep only results without nearby negation terms
            search_results = search_results.loc[results_to_keep]
            print(f"After negation filtering: {len(search_results)} matches remain")
            
            # Print negation term statistics
            for term, count in excluded_by_term.items():
                if count > 0:
                    print(f"  - Term '{term}' excluded {count} matches")
    
    if len(search_results) == 0:
        print(f"No results found for '{search_term}'")
        return
    
    print(f"Found total of {len(search_results)} occurrences - {len(exact_matches.index.intersection(search_results.index))} exact matches and {len(fuzzy_matches.index.intersection(search_results.index))} fuzzy matches")
    
    # Create output filename based on search term
    search_term_filename = search_term.replace(' ', '_')
    if negation_terms and len(negation_terms) > 0:
        negation_str = "_not_" + "_".join([term.replace(' ', '_') for term in negation_terms])
        search_term_filename += negation_str
    
    search_results_csv = f"search_results_{search_term_filename}.csv"
    output_pdf_path = os.path.join(output_directory, f"highlighted_{search_term_filename}.pdf")
    
    # Ensure we have date and page_number columns for sorting
    # If they don't exist, try to extract them from filename
    if 'date' not in search_results.columns:
        # Try to extract date from filename
        search_results['date'] = search_results['filename'].str.extract(r'(\d{4}-\d{2}-\d{2})')
    
    # Convert date to datetime for proper sorting
    if 'date' in search_results.columns:
        try:
            search_results['date'] = pd.to_datetime(search_results['date'])
        except:
            try:
                search_results['date'] = pd.to_datetime(search_results['date'], format='%Y-%m-%d', errors='coerce')
            except:
                print("Warning: Could not convert date column to datetime for sorting")
    
    # Ensure we have page numbers
    if 'page_number' not in search_results.columns:
        # Try to extract page number from filename
        search_results['page_number'] = search_results['filename'].str.extract(r'Page(\d+)').astype(int, errors='ignore')
    
    # Sort by date and page number for final ordering
    if 'date' in search_results.columns and pd.api.types.is_datetime64_dtype(search_results['date']):
        search_results = search_results.sort_values(
            by=['date', 'page_number'], 
            ascending=[True, True]
        )
    else:
        # If date conversion failed, sort by page number
        if 'page_number' in search_results.columns:
            search_results = search_results.sort_values(
                by=['page_number'], 
                ascending=[True]
            )
    
    # Convert back to string format for dates before saving CSV
    if 'date' in search_results.columns and pd.api.types.is_datetime64_dtype(search_results['date']):
        search_results['date'] = search_results['date'].dt.strftime('%Y-%m-%d')
    
    # Save search results to CSV with similarity score included
    search_results.to_csv(search_results_csv, index=False)
    print(f"Saved search results to {search_results_csv}")
    
    # Step 3: Highlight and create PDF
    # Create a PDF writer for the output file
    pdf_writer = PdfWriter()
    
    # Keep track of temporary files
    temp_files = []
    processed_count = 0
    highlighted_count = 0
    
    try:
        # Get unique filenames while preserving sort order
        unique_filenames = search_results['filename'].drop_duplicates().tolist()
        
        # Process each file in the sorted order
        for filename in unique_filenames:
            pdf_path = os.path.join(base_folder, filename)
            
            # Check if the file exists
            if not os.path.exists(pdf_path):
                print(f"Warning: File not found: {pdf_path}")
                continue
            
            # Get all highlights for this file
            file_results = search_results[search_results['filename'] == filename]
            
            try:
                # Open the PDF
                doc = pymupdf.open(pdf_path)
                page = doc[0]  # Single-page PDFs
                
                # Apply all highlights for this page
                hits_count = 0
                for _, row in file_results.iterrows():
                    # Create a rectangle from the bounding box coordinates
                    rect = pymupdf.Rect(row['bbx0'], row['bby0'], row['bbx1'], row['bby1'])
                    
                    # Add highlight annotation with color based on similarity
                    similarity = row['similarity']
                    if similarity == 100:  # Exact match - bright yellow
                        highlight_color = (1, 1, 0)  # Yellow
                    elif similarity >= 90:  # Very similar - light orange
                        highlight_color = (1, 0.8, 0.3)
                    elif similarity >= 80:  # Similar - light green
                        highlight_color = (0.6, 1, 0.6)
                    else:  # Less similar - light blue
                        highlight_color = (0.6, 0.8, 1)
                        
                    highlight = page.add_highlight_annot(rect)
                    highlight.set_colors(stroke=highlight_color)
                    highlight.update()
                    
                    hits_count += 1
                
                # Create a temporary highlighted PDF
                temp_path = f"_tmp_{filename.replace(' ', '_').replace(',', '').replace('.pdf', '')}.pdf"
                doc.save(temp_path, incremental=False)
                doc.close()
                
                # Track temp files
                temp_files.append(temp_path)
                
                # Add the temporary PDF to our output PDF
                pdf_writer.append(temp_path)
                
                processed_count += 1
                highlighted_count += hits_count
                
                # print(f"Highlighted {hits_count} occurrences in {filename}")
                
            except Exception as e:
                print(f"Error processing {pdf_path}: {e}")
        
        # Save the final PDF if we have any pages
        if processed_count > 0:
            pdf_writer.write(output_pdf_path)
            result_message = f"Created PDF with {processed_count} pages and {highlighted_count} highlighted terms at: {output_pdf_path}"
            if negation_terms and len(negation_terms) > 0:
                result_message += f"\nExcluded instances where any of these terms appears within {negation_distance} units: {', '.join(negation_terms)}"
            print(result_message)
            print(f"Pages are sorted by date and page number.")
            
            # Open the result
            if sys.platform.startswith("darwin"):
                os.system(f"open '{output_pdf_path}'")
            elif os.name == "nt":
                os.startfile(output_pdf_path)
            else:
                os.system(f"xdg-open '{output_pdf_path}'")
        else:
            print("No pages were successfully processed. No output PDF created.")
            
    finally:
        # Clean up temporary files
        print("Cleaning up temporary files...")
        for temp_path in temp_files:
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as e:
                    print(f"Failed to remove {temp_path}: {e}")
        
        # Catch any missed temporary files
        for temp_file in glob.glob("_tmp_*.pdf"):
            try:
                os.remove(temp_file)
            except Exception:
                pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Search for terms and create highlighted PDF with word-level fuzzy matching')
    parser.add_argument('search_term', help='Term to search for')
    parser.add_argument('--base_folder', default=r"C:\Users\denis\Documents\WWRDownloading\PDFs",
                        help='Base folder where PDF files are stored')
    parser.add_argument('--output_dir', default='.', help='Directory where to save output files')
    parser.add_argument('--threshold', type=int, default=80,
                        help='Similarity threshold (0-100) for fuzzy matching')
    parser.add_argument('--negation', action='append', dest='negation_terms',
                        help='Term that negates the match if found nearby (can be used multiple times)')
    parser.add_argument('--negation_distance', type=float, default=100.0,
                        help='Maximum distance for negation terms to affect match')
    
    args = parser.parse_args()
    
    search_and_highlight(
        args.search_term, 
        args.base_folder, 
        args.output_dir, 
        args.threshold, 
        args.negation_terms, 
        args.negation_distance
    )