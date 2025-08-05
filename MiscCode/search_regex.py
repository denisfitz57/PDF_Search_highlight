import pandas as pd
import pymupdf  # PyMuPDF
import os
import sys
from pypdf import PdfWriter
import argparse
import glob
import re

def search_and_highlight(search_term, base_folder, output_directory='.', fuzzy_level=1):
    """
    Searches for a term in CSV files with text positions and creates a highlighted PDF.
    
    Parameters:
    search_term (str): Term to search for
    base_folder (str): Base folder where PDF files are stored
    output_directory (str): Directory where to save output files
    fuzzy_level (int): Level of fuzziness (0=exact, 1=moderate, 2=high)
    """
    # Step 1: Get text position data
    try:
        df = pd.read_csv('big_text_with_position.csv')
    except FileNotFoundError:
        print("Error: big_text_with_position.csv not found")
        return
    
    # Step 2: Create a fuzzy search pattern based on the fuzzy level
    if fuzzy_level == 0:
        # Exact search (case-insensitive)
        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
        search_results = df[df['text'].str.contains(pattern, na=False)]
    elif fuzzy_level == 1:
        # Moderate fuzzy search - allow for some character spacing variations
        # This creates a pattern where spaces are optional and characters can have optional spaces between them
        escaped_term = re.escape(search_term)
        flexible_spaces = escaped_term.replace(r'\ ', '\\s*')  # Make spaces flexible
        pattern = re.compile(flexible_spaces, re.IGNORECASE)
        search_results = df[df['text'].str.contains(pattern, regex=True, na=False)]
    else:
        # High fuzzy search - use more advanced techniques
        # First try with flexible spacing
        escaped_term = re.escape(search_term)
        flexible_spaces = escaped_term.replace(r'\ ', '\\s*')
        pattern = re.compile(flexible_spaces, re.IGNORECASE)
        primary_results = df[df['text'].str.contains(pattern, regex=True, na=False)]
        
        # Then look for words with similar characters (common OCR confusions)
        # Create alternative patterns with common OCR substitutions
        ocr_substitutions = {
            'o': '[o0]', 'O': '[O0]',
            'i': '[i1l|]', 'I': '[I1l|]',
            'l': '[l1I|]', 'L': '[Ll1|]',
            '0': '[0Oo]',
            '1': '[1Il|]',
            's': '[sS5]', 'S': '[Ss5]',
            '5': '[5Ss]',
            'z': '[z2]', 'Z': '[Z2]',
            '2': '[2Zz]',
            'n': '[nrh]', 'r': '[rn]', 'h': '[hn]',
            'm': '[mnn]'
        }
        
        fuzzy_term = search_term
        for char, replacements in ocr_substitutions.items():
            fuzzy_term = fuzzy_term.replace(char, replacements)
        
        # Make spaces optional in the fuzzy pattern
        fuzzy_term = fuzzy_term.replace(' ', '\\s*')
        fuzzy_pattern = re.compile(fuzzy_term, re.IGNORECASE)
        
        # Get additional results with the fuzzy pattern
        secondary_results = df[df['text'].str.contains(fuzzy_pattern, regex=True, na=False)]
        
        # Combine results, remove duplicates
        search_results = pd.concat([primary_results, secondary_results]).drop_duplicates()
    
    if len(search_results) == 0:
        print(f"No results found for '{search_term}'")
        return
    
    print(f"Found {len(search_results)} occurrences of '{search_term}' with fuzzy level {fuzzy_level}")
    
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
    parser.add_argument('--fuzzy', type=int, choices=[0, 1, 2], default=1,
                        help='Fuzzy search level: 0=exact, 1=moderate, 2=high')
    
    args = parser.parse_args()
    
    search_and_highlight(args.search_term, args.base_folder, args.output_dir, args.fuzzy)