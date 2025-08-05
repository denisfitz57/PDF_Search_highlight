import pandas as pd
import pymupdf  # PyMuPDF
import os
import sys
from pypdf import PdfWriter
import argparse
import glob
from rapidfuzz import fuzz, process  # pip install rapidfuzz

def search_and_highlight(search_term, base_folder, output_directory='.', similarity_threshold=80):
    """
    Searches for a term in CSV files with text positions and creates a highlighted PDF.
    
    Parameters:
    search_term (str): Term to search for
    base_folder (str): Base folder where PDF files are stored
    output_directory (str): Directory where to save output files
    similarity_threshold (int): Minimum similarity score (0-100) to consider a match
    """
    # Step 1: Get text position data
    try:
        df = pd.read_csv('big_text_with_position.csv')
    except FileNotFoundError:
        print("Error: big_text_with_position.csv not found")
        return
    
    # Step 2: Perform fuzzy search
    print(f"Searching for '{search_term}' with similarity threshold {similarity_threshold}%...")
    
    # Apply fuzzy matching to each text entry
    # First try exact substring search for efficiency
    exact_matches = df[df['text'].str.contains(search_term, case=False, na=False)]
    
    # For remaining entries, use fuzzy matching
    remaining_df = df.drop(exact_matches.index)
    
    # Apply fuzzy matching - this is computationally expensive for large datasets
    fuzzy_matches_indices = []
    
    # Create chunks for processing to avoid memory issues
    chunk_size = 10000  # Adjust based on your system's memory
    
    for i in range(0, len(remaining_df), chunk_size):
        chunk = remaining_df.iloc[i:i+chunk_size]
        
        # Calculate similarity scores for this chunk
        similarities = chunk['text'].apply(
            lambda x: fuzz.ratio(search_term.lower(), str(x).lower())
        )
        
        # Find matches above threshold
        chunk_matches = chunk[similarities >= similarity_threshold]
        fuzzy_matches_indices.extend(chunk_matches.index.tolist())
        
        print(f"Processed chunk {i//chunk_size + 1}...")
    
    # Get the fuzzy matches
    fuzzy_matches = df.loc[fuzzy_matches_indices]
    
    # Combine exact and fuzzy matches
    search_results = pd.concat([exact_matches, fuzzy_matches]).drop_duplicates()
    
    if len(search_results) == 0:
        print(f"No results found for '{search_term}'")
        return
    
    print(f"Found {len(search_results)} occurrences - {len(exact_matches)} exact matches and {len(fuzzy_matches)} fuzzy matches")
    
    # Create output filename based on search term
    search_results_csv = f"search_results_{search_term.replace(' ', '_')}.csv"
    output_pdf_path = os.path.join(output_directory, f"highlighted_{search_term.replace(' ', '_')}.pdf")
    
    # Save search results to CSV
    search_results.to_csv(search_results_csv, index=False)
    print(f"Saved search results to {search_results_csv}")
    
    # Rest of your existing code...
    # [...]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Search for terms and create highlighted PDF')
    parser.add_argument('search_term', help='Term to search for')
    parser.add_argument('--base_folder', default=r"C:\Users\denis\Documents\WWRDownloading\PDFs",
                        help='Base folder where PDF files are stored')
    parser.add_argument('--output_dir', default='.', help='Directory where to save output files')
    parser.add_argument('--threshold', type=int, default=80,
                        help='Similarity threshold (0-100) for fuzzy matching')
    
    args = parser.parse_args()
    
    search_and_highlight(args.search_term, args.base_folder, args.output_dir, args.threshold)