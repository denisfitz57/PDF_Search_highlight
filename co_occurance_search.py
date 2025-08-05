import pandas as pd
import re
import math
import os
import sys
import glob
import argparse
import datetime
from rapidfuzz import fuzz, process
from tqdm import tqdm
import pymupdf  # PyMuPDF
from pypdf import PdfWriter
from pdf_highlighter import highlight_search_results

def load_terms_from_file(file_path):
    """
    Load search terms from a file, one term per line.
    
    Parameters:
    file_path (str): Path to the file containing search terms
    
    Returns:
    list: List of search terms
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            # Read terms, strip whitespace, and filter out empty lines
            terms = [line.strip() for line in f if line.strip()]
        
        if not terms:
            print(f"Warning: No terms found in file {file_path}")
            return []
            
        print(f"Loaded {len(terms)} terms from {file_path}")
        return terms
    except Exception as e:
        print(f"Error loading terms from {file_path}: {str(e)}")
        return []

def search_documents_co_occurrence(terms, min_terms_required, csv_file='big_text_with_position_may12.csv', 
                                 negation_terms=None, negation_distance=100, 
                                 start_date=None, end_date=None):
    """
    Searches for co-occurrence of multiple terms on the same page.
    
    Parameters:
    terms (list): List of terms to search for
    min_terms_required (int): Minimum number of terms required to be present on a page
    csv_file (str): CSV file with text position data
    negation_terms (list or str): Term(s) that negate matches if found nearby
    negation_distance (float): Maximum distance to consider for negation
    start_date (str): Start date in YYYY-MM-DD format to filter results
    end_date (str): End date in YYYY-MM-DD format to filter results
    
    Returns:
    DataFrame: Search results with position data for co-occurring terms
    str: Message with search statistics
    """
    # Validate inputs
    if not isinstance(terms, list) or len(terms) < min_terms_required:
        return None, f"Error: You must provide at least {min_terms_required} search terms"
    
    # Convert single negation term to list for consistent handling
    if negation_terms and not isinstance(negation_terms, list):
        negation_terms = [negation_terms]
    
    # Step 1: Get text position data
    try:
        df = pd.read_csv(csv_file)
        search_stats = f"Loaded {len(df)} text entries from CSV file"
    except FileNotFoundError:
        return None, f"Error: {csv_file} not found"
    
    # Step 2: Search for each term individually
    search_stats += f"\nSearching for co-occurrence of terms: {', '.join(terms)}"
    search_stats += f"\nRequiring at least {min_terms_required} of {len(terms)} terms to be present on a page"
    
    # Store matches for each term
    term_matches = {}
    term_match_counts = {}
    
    # Find all matches for each term
    for term in terms:
        # Search for exact matches
        exact_matches = df[df['text'].str.contains(r'\b' + re.escape(term) + r'\b', 
                                                 case=False, na=False, regex=True)].copy()
        
        exact_matches['search_term'] = term
        exact_matches['match_type'] = 'exact'
        
        term_matches[term] = exact_matches
        term_match_counts[term] = len(exact_matches)
        
        search_stats += f"\n- Found {len(exact_matches)} matches for term '{term}'"
    
    # Step 3: Find pages with co-occurrences
    # Create groups by filename and page
    unique_pages = set()
    
    for term, matches in term_matches.items():
        if not matches.empty:
            # Extract unique filename/page combinations
            page_identifiers = matches[['filename', 'page_number']].drop_duplicates()
            for _, row in page_identifiers.iterrows():
                unique_pages.add((row['filename'], row['page_number']))
    
    search_stats += f"\nFound {len(unique_pages)} unique pages with at least one term"
    
    # Check each page for the required number of terms
    qualifying_pages = []
    page_term_counts = {}
    
    for filename, page_number in unique_pages:
        # Count how many of our search terms appear on this page
        terms_present = []
        
        for term, matches in term_matches.items():
            page_matches = matches[(matches['filename'] == filename) & 
                                   (matches['page_number'] == page_number)]
            
            if not page_matches.empty:
                terms_present.append(term)
        
        terms_count = len(terms_present)
        page_term_counts[(filename, page_number)] = terms_present
        
        if terms_count >= min_terms_required:
            qualifying_pages.append((filename, page_number, terms_count, terms_present))
    
    search_stats += f"\nFound {len(qualifying_pages)} pages with at least {min_terms_required} terms"
    
    # If no qualifying pages, return early
    if not qualifying_pages:
        return None, search_stats + f"\nNo pages found with at least {min_terms_required} terms co-occurring"
    
    # Step 4: Collect all matches from qualifying pages
    all_qualifying_matches = []
    
    for filename, page_number, terms_count, terms_present in qualifying_pages:
        for term in terms_present:
            page_matches = term_matches[term][
                (term_matches[term]['filename'] == filename) & 
                (term_matches[term]['page_number'] == page_number)
            ]
            all_qualifying_matches.append(page_matches)
    
    # Combine all matches
    search_results = pd.concat(all_qualifying_matches) if all_qualifying_matches else pd.DataFrame()
    
    # Add co-occurrence metadata
    search_results = search_results.copy()
    search_results['co_occurring_terms_count'] = search_results.apply(
        lambda row: len(page_term_counts.get((row['filename'], row['page_number']), [])), 
        axis=1
    )
    
    search_results['co_occurring_terms'] = search_results.apply(
        lambda row: ", ".join(page_term_counts.get((row['filename'], row['page_number']), [])),
        axis=1
    )
    
    # Apply negation filtering if negation terms are provided
    if negation_terms and len(negation_terms) > 0 and len(search_results) > 0:
        search_stats += f"\nChecking for negation terms near matches..."
        
        # Create a dictionary to track negation matches by term
        negation_matches_dict = {}
        total_negation_matches = 0
        
        # Find occurrences of each negation term
        for term in negation_terms:
            if 'text' in df.columns:
                # Use word boundaries to match whole words only
                pattern = r'\b' + re.escape(term) + r'\b'
                term_matches = df[df['text'].str.contains(pattern, case=False, na=False, regex=True)].copy()
                negation_matches_dict[term] = term_matches
                total_negation_matches += len(term_matches)
                search_stats += f"\n  - Found {len(term_matches)} occurrences of negation term '{term}'"
        
        if total_negation_matches > 0:
            search_stats += f"\nFound {total_negation_matches} total occurrences of all negation terms"
            
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
                            # Don't break - we want to find the closest negation term
                    
                # After checking all terms, record which term excluded this match
                if not has_nearby_negation:
                    results_to_keep.append(idx)
                elif excluding_term:
                    excluded_by_term[excluding_term] += 1
            
            # Keep only results without nearby negation terms
            search_results = search_results.loc[results_to_keep]
            search_stats += f"\nAfter negation filtering: {len(search_results)} matches remain"
            
            # Print negation term statistics
            for term, count in excluded_by_term.items():
                if count > 0:
                    search_stats += f"\n  - Term '{term}' excluded {count} matches"
                    
    # If all results were filtered out
    if len(search_results) == 0:
        return None, search_stats + "\nNo results remain after negation filtering"
    
    # Apply date filtering
    # Ensure we have date column for filtering
    if 'date' not in search_results.columns:
        # Try to extract date from filename
        search_results['date'] = search_results['filename'].str.extract(r'(\d{4}-\d{2}-\d{2})')
    
    # Convert date to datetime for proper filtering
    if 'date' in search_results.columns:
        try:
            search_results['date'] = pd.to_datetime(search_results['date'])
            
            # Apply date filtering if specified
            original_count = len(search_results)
            
            if start_date:
                start_dt = pd.to_datetime(start_date)
                search_results = search_results[search_results['date'] >= start_dt]
                
            if end_date:
                end_dt = pd.to_datetime(end_date)
                search_results = search_results[search_results['date'] <= end_dt]
                
            if (start_date or end_date) and len(search_results) < original_count:
                search_stats += f"\nDate filtering removed {original_count - len(search_results)} results"
                search_stats += f"\nRemaining after date filtering: {len(search_results)} results"
                
        except:
            try:
                search_results['date'] = pd.to_datetime(search_results['date'], format='%Y-%m-%d', errors='coerce')
                
                # Apply date filtering
                original_count = len(search_results)
                
                if start_date:
                    start_dt = pd.to_datetime(start_date)
                    search_results = search_results[search_results['date'] >= start_dt]
                    
                if end_date:
                    end_dt = pd.to_datetime(end_date)
                    search_results = search_results[search_results['date'] <= end_dt]
                    
                if (start_date or end_date) and len(search_results) < original_count:
                    search_stats += f"\nDate filtering removed {original_count - len(search_results)} results"
                    search_stats += f"\nRemaining after date filtering: {len(search_results)} results"
                    
            except:
                search_stats += "\nWarning: Could not convert date column to datetime for filtering"
    
    # If all results were filtered out by date
    if len(search_results) == 0:
        return None, search_stats + "\nNo results remain after date filtering"
    
    # Sort by page and co-occurrence count
    search_results = search_results.sort_values(
        by=['filename', 'page_number', 'co_occurring_terms_count', 'search_term'], 
        ascending=[True, True, False, True]
    )
    
    # Convert back to string format for dates 
    if 'date' in search_results.columns and pd.api.types.is_datetime64_dtype(search_results['date']):
        search_results['date'] = search_results['date'].dt.strftime('%Y-%m-%d')
    
    return search_results, search_stats

def save_co_occurrence_results(search_results, terms, min_terms_required, 
                             negation_terms=None, output_directory='.', date_range_str=""):
    """
    Save co-occurrence search results to a CSV file
    
    Parameters:
    search_results (DataFrame): Search results dataframe
    terms (list): Terms that were searched
    min_terms_required (int): Minimum number of terms required
    negation_terms (list or str): Term(s) that negated the search if any
    output_directory (str): Directory where to save the CSV file
    date_range_str (str): String representing date range for filename
    
    Returns:
    str: Path to the CSV file
    """
    # Convert single negation term to list for consistent handling
    if negation_terms and not isinstance(negation_terms, list):
        negation_terms = [negation_terms]
    
    # Create output directory if it doesn't exist
    if not os.path.exists(output_directory):
        try:
            os.makedirs(output_directory)
            print(f"Created output directory: {output_directory}")
        except Exception as e:
            print(f"Warning: Failed to create output directory {output_directory}: {e}")
            # Fall back to current directory if creation fails
            output_directory = '.'
    
    # Create a compact representation of the terms for the filename
    terms_str = "_".join([term.replace(' ', '-') for term in terms])
    filename_base = f"co_occur_{min_terms_required}_of_{len(terms)}_{terms_str[:50]}"
    
    if negation_terms and len(negation_terms) > 0:
        negation_str = "_not_" + "_".join([term.replace(' ', '_') for term in negation_terms])
        filename_base += negation_str
    
    # Add date range to filename if provided
    filename_base += date_range_str
    
    # Ensure filename isn't too long
    if len(filename_base) > 150:
        filename_base = filename_base[:150]
    
    results_csv = os.path.join(output_directory, f"{filename_base}.csv")
    
    # Add summary information to the dataframe
    search_results['search_terms'] = ", ".join(terms)
    search_results['min_terms_required'] = min_terms_required
    if negation_terms:
        search_results['negation_terms'] = ", ".join(negation_terms)
    
    # Save search results to CSV
    search_results.to_csv(results_csv, index=False)
    
    return results_csv

def search_and_highlight_co_occurrence(terms, min_terms_required, base_folder, 
                                     output_directory='.', negation_terms=None, 
                                     negation_distance=100, start_date=None, end_date=None):
    """
    Searches for co-occurrence of terms and creates highlighted PDF
    
    Parameters:
    terms (list): List of terms to search for
    min_terms_required (int): Minimum number of terms required to be present on a page
    base_folder (str): Base folder where PDF files are stored
    output_directory (str): Directory where to save output files
    negation_terms (list): Terms that negate the search if found nearby
    negation_distance (float): Maximum distance for negation terms to affect match
    start_date (str): Start date in YYYY-MM-DD format to filter results
    end_date (str): End date in YYYY-MM-DD format to filter results
    
    Returns:
    str: Path to the generated PDF file
    """
    # Step 1: Search for term co-occurrences and get results
    print(f"Searching for co-occurrence of {len(terms)} terms: {', '.join(terms)}")
    print(f"Requiring at least {min_terms_required} terms to be present on a page")
    
    search_results, search_stats = search_documents_co_occurrence(
        terms, 
        min_terms_required,
        'big_text_with_position_may12.csv', 
        negation_terms, 
        negation_distance,
        start_date,
        end_date
    )
    
    print(search_stats)
    
    if search_results is None:
        return None
    
    # Step 2: Save search results to CSV
    # Include date range in filename if specified
    date_range_str = ""
    if start_date and end_date:
        date_range_str = f"_{start_date}_to_{end_date}"
    elif start_date:
        date_range_str = f"_from_{start_date}"
    elif end_date:
        date_range_str = f"_until_{end_date}"
        
    csv_path = save_co_occurrence_results(
        search_results, 
        terms, 
        min_terms_required,
        negation_terms, 
        output_directory,
        date_range_str
    )
    print(f"Saved search results to {csv_path}")
    
    # Step 3: Create highlighted PDF
    print("Creating highlighted PDF...")
    pdf_path, status, pages, highlights = highlight_search_results(
        csv_path, 
        base_folder, 
        output_directory
    )
    
    if pdf_path:
        print(f"{status} at: {pdf_path}")
        # Summary of findings by page
        page_counts = search_results.groupby(['filename', 'page_number'])['search_term'].nunique()
        print(f"\nFound content on {len(page_counts)} pages:")
        
        # Print top 10 pages with most term variety
        top_pages = search_results.groupby(['filename', 'page_number'])['search_term'].agg(['nunique', 'count'])
        top_pages.columns = ['unique_terms', 'total_matches']
        top_pages = top_pages.sort_values('unique_terms', ascending=False).head(10)
        
        for i, ((filename, page), row) in enumerate(top_pages.iterrows(), 1):
            page_terms = search_results[(search_results['filename'] == filename) & 
                                       (search_results['page_number'] == page)]['search_term'].unique()
            print(f"{i}. {filename} (Page {page}): {row['unique_terms']} terms, {row['total_matches']} matches")
            print(f"   Terms: {', '.join(page_terms)}")
        
        return pdf_path
    else:
        print(status)
        return None
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Search for co-occurrence of terms and create highlighted PDF')
    
    # Create a mutually exclusive group for term input methods
    term_group = parser.add_mutually_exclusive_group(required=True)
    term_group.add_argument('--terms', nargs='+',
                        help='List of terms to search for')
    term_group.add_argument('--terms-file', 
                        help='Path to a file containing search terms (one per line)')
    
    parser.add_argument('--min_terms', type=int, default=2,
                        help='Minimum number of terms required to be present on a page')
    parser.add_argument('--base_folder', default=r"C:\Users\denis\Documents\WWRDownloading\PDFs",
                        help='Base folder where PDF files are stored')
    parser.add_argument('--output_dir', default='.', 
                        help='Directory where to save output files')
    parser.add_argument('--negation', action='append', dest='negation_terms',
                        help='Term that negates the match if found nearby (can be used multiple times)')
    parser.add_argument('--negation_distance', type=float, default=100.0,
                        help='Maximum distance for negation term to affect match')
    parser.add_argument('--start_date', 
                        help='Start date in YYYY-MM-DD format (e.g., 2020-01-01)')
    parser.add_argument('--end_date', 
                        help='End date in YYYY-MM-DD format (e.g., 2020-12-31)')

    args = parser.parse_args()
    
    # Load terms either from command line or file
    if args.terms:
        terms = args.terms
    elif args.terms_file:
        terms = load_terms_from_file(args.terms_file)
        if not terms:
            print("Error: No valid terms found in the specified file.")
            exit(1)
    else:
        print("Error: Either --terms or --terms-file must be specified.")
        exit(1)
    
    # Validate min_terms value
    if args.min_terms < 1 or args.min_terms > len(terms):
        print(f"Error: min_terms must be between 1 and {len(terms)}")
        exit(1)

    # Validate date formats if provided
    if args.start_date:
        try:
            datetime.datetime.strptime(args.start_date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Start date must be in YYYY-MM-DD format. Got: {args.start_date}")
            exit(1)
            
    if args.end_date:
        try:
            datetime.datetime.strptime(args.end_date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: End date must be in YYYY-MM-DD format. Got: {args.end_date}")
            exit(1)

    search_and_highlight_co_occurrence(
        terms,
        args.min_terms,
        args.base_folder,
        args.output_dir,
        args.negation_terms,
        args.negation_distance,
        args.start_date,
        args.end_date
    )